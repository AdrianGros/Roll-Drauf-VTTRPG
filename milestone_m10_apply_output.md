# M10 Apply Output: Vertical Slice Architecture (Lobby -> Play -> End)

```
artifact: apply-output
milestone: M10
phase: APPLY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Discover baseline:
  - `milestone_m9_discover_output.md`
- Human approval:
  - `APPROVED: M10 Apply`
- Constraints and method:
  - DAD-M runtime profile `standard`
  - Apply phase only: architecture, contracts, acceptance criteria (no implementation code)
  - strict vertical-slice scope (no full platform expansion)

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m10_apply_output.md` | M10 solution design baseline for Deploy | `immutable` after phase close | active draft in this turn |

---

## Recommended Decision Set (for M10 Deploy)

1. **Play-route-first recommendation: implement dedicated `/play` shell with bootstrap contract**
   Keep campaign management in `/campaigns`; live runtime enters via `/play?campaign_id=&session_id=`.

2. **Compatibility-first recommendation: build M10 on top of existing session/token state services**
   Reuse current `SessionState`, `TokenState`, socket room model, and existing campaign endpoints wherever possible.

3. **Scope-lock recommendation: scene-stack + action-bar v1 only, no full rules engine**
   Deliver one playable vertical slice with clear state transitions, not complete D&D automation.

---

## Design Tradeoffs

| Topic | Option A | Option B | Selected | Reason |
|---|---|---|---|---|
| Live entry UX | stay on `/campaigns` | dedicated `/play` route | **B** | clean product separation and lower UI overload |
| Session transitions | fixed `start/end` only | explicit state machine (`scheduled/ready/in_progress/paused/ended`) | **B** | supports waiting room and pause/resume |
| Scene model | single map pointer | scene stack with ordered layers | **B** | aligns with core product differentiation |
| Action system | full rules automation now | generic action bar v1 + explicit dice | **B** | keeps scope controllable and preserves table feel |
| Persistence scope | broad new schema | minimal new entities + reuse existing state models | **B** | lower migration risk in vertical slice |

---

## Solution Design

### 1) Target Runtime Flow (M10)

Primary user journey:

1. user opens campaign/session in management UI
2. user enters `/play?campaign_id=<id>&session_id=<id>`
3. frontend requests bootstrap payload
4. frontend joins session socket room and receives authoritative snapshot
5. state-driven runtime mode applies:
   - waiting room (read-only for players)
   - live play
   - paused mode
6. session ends and recap snapshot is persisted

Key design rule:

- `/campaigns` remains orchestration/setup
- `/play` is the only live session surface

### 2) Session State Machine (canonical)

Session lifecycle states:

- `scheduled`
- `ready`
- `in_progress`
- `paused`
- `ended`

Allowed transitions:

- `scheduled -> ready`
- `ready -> in_progress`
- `in_progress -> paused`
- `paused -> in_progress`
- `in_progress -> ended`
- `paused -> ended`

Compatibility note:

- existing `completed` is normalized to `ended` in M10 serializers.
- legacy `cancelled` remains backward-compatible but not part of default M10 flow.

### 3) RBAC and Permissions

Roles in session runtime:

- `DM`
- `CO_DM`
- `PLAYER`
- `OBSERVER`

Authority matrix (runtime):

| Capability | DM | CO_DM | PLAYER | OBSERVER |
|---|---|---|---|---|
| start/ready/pause/resume/end session | yes | yes | no | no |
| run ready-check and bypass warnings | yes | yes | no | no |
| activate scene layer | yes | yes | no | no |
| create/update/delete any token | yes | yes | no | no |
| move/update owned token | yes | yes | yes | no |
| use action bar on owned token | yes | yes | yes | no |
| post chat/report | yes | yes | yes | yes (configurable, default yes) |
| view live state | yes | yes | yes | yes |

Implementation compatibility:

- owner still maps to DM authority.
- campaign member role is extended with `CO_DM` and `OBSERVER` values.

### 4) Scene Stack and Layer Model (M10 v1)

#### New/extended domain entities

1. `SceneStack`
- `id`
- `campaign_id`
- `game_session_id`
- `name`
- `active_layer_id`
- `created_by`
- `created_at`

2. `SceneLayer`
- `id`
- `scene_stack_id`
- `campaign_map_id` (reuse existing `CampaignMap` asset)
- `label` (e.g. "Floor 1", "Tower Top")
- `order_index`
- `is_player_visible`
- `created_at`

3. `SessionSnapshot` (minimal recap persistence)
- `id`
- `game_session_id`
- `snapshot_type` (`start`, `end`)
- `state_version`
- `payload_json`
- `created_by`
- `created_at`

M10 minimal rule:

- one active `SceneStack` per session
- 2-3 layers sufficient for vertical slice
- switching active layer updates `SessionState.active_map_id` for compatibility with existing token/state logic

### 5) API Contract Design (M10)

#### A. Play bootstrap and runtime state

1. `GET /api/play/campaigns/<campaign_id>/sessions/<session_id>/bootstrap`
- returns:
  - authenticated user and session role
  - session lifecycle state
  - read-only flag for current user
  - scene stack + layers + active layer
  - current state snapshot (`SessionState`, active map, tokens)
  - action catalog v1

2. `POST /api/play/campaigns/<campaign_id>/sessions/<session_id>/transition`
- body: `{ "target_state": "...", "ignore_warnings": false }`
- enforces state machine + RBAC
- returns updated session + state metadata

#### B. Ready-check

3. `GET /api/play/campaigns/<campaign_id>/sessions/<session_id>/ready-check`
- returns:
  - `blocking_issues[]`
  - `warnings[]`
  - `can_start` boolean

Minimal blockers:

- session has no scene layers
- user lacks operator role

Soft warnings examples:

- no player tokens on active layer
- no map background on active layer
- no active participants connected

#### C. Scene stack operations (M10 minimal)

4. `POST /api/play/campaigns/<campaign_id>/sessions/<session_id>/scene-stack/init`
- initializes default stack from selected maps if absent

5. `POST /api/play/campaigns/<campaign_id>/sessions/<session_id>/scene-stack/layers/<layer_id>/activate`
- DM/CO_DM only
- updates active layer + `SessionState.active_map_id`

#### D. Action bar v1

6. `POST /api/play/campaigns/<campaign_id>/sessions/<session_id>/actions/execute`
- body:
  - `token_id`
  - `action_code`
  - `target_token_id` optional
  - `payload` optional
- server validates ownership/permission and returns deterministic action result envelope
- dice roll remains explicit and visible; action response may include suggested roll expression

### 6) Socket/Rejoin Contract (M10)

Reuse existing room model with play-specific handshake:

- client emits `session:join` (existing)
- server emits:
  - `session:joined`
  - `state:snapshot`
  - `play:mode` (`waiting`, `live`, `paused`, `ended`, plus `read_only`)

New/extended events:

- `session:state_changed`
- `scene:layer_activated`
- `action:executed`

Reconnect protocol:

1. client reconnects and re-joins room
2. server sends authoritative snapshot + state version
3. client drops stale optimistic state if version mismatch
4. UI re-enters correct mode (`waiting/live/paused/ended`)

### 7) Play UI Structure (M10)

`/play` page regions:

- top bar:
  - campaign/session identity
  - lifecycle status
  - start/pause/resume/end controls (role-gated)
- center:
  - map canvas + token layer (active scene layer)
- right cockpit:
  - ready-check panel
  - scene layer switcher
  - session participants summary
- bottom:
  - action bar v1 (card-like action tiles)
  - explicit dice interaction

Waiting-room mode behavior:

- players/observers:
  - read-only scene view, chat, participant state
  - no token/action mutation
- DM/CO_DM:
  - full setup controls

### 8) Content and Licensing Boundary (M10 implementation guardrail)

- action catalog and token systems must be content-agnostic and SRD-safe.
- do not hardcode non-SRD class/spell/monster content in runtime core.
- keep content layer separable so licensed or custom packs can be added later.

### 9) Test Strategy (M10 Deploy target)

New suites:

- `tests/test_play_bootstrap_api.py`
- `tests/test_session_state_machine.py`
- `tests/test_ready_check.py`
- `tests/test_scene_stack_api.py`
- `tests/test_play_permissions.py`
- `tests/test_play_rejoin_socket.py`
- `tests/test_action_bar_v1.py`

Regression suites to keep green:

- `tests/test_auth.py`
- `tests/test_campaigns.py`
- `tests/test_maps.py`
- `tests/test_session_state.py`
- `tests/test_tokens_realtime.py`
- `tests/test_combat_api.py`
- `tests/test_chat_api.py`

---

## Acceptance Criteria (for M10 Deploy)

AC-M10-01: `/play` route exists and loads authenticated session runtime by `campaign_id` + `session_id`.  
AC-M10-02: Bootstrap endpoint returns role, mode, scene/layer metadata, and authoritative state payload.  
AC-M10-03: Session lifecycle supports `scheduled`, `ready`, `in_progress`, `paused`, `ended` with enforced valid transitions.  
AC-M10-04: DM and CO_DM can transition session state; players/observers cannot.  
AC-M10-05: Waiting-room mode is read-only for players before `in_progress`.  
AC-M10-06: Scene stack/layer model supports at least one stack with 2-3 switchable layers per session.  
AC-M10-07: Layer activation updates active play map consistently across REST and socket state.  
AC-M10-08: Action bar v1 supports server-validated basic action execution on owned tokens.  
AC-M10-09: Dice roll interaction remains explicit and visible in live flow.  
AC-M10-10: Reconnect restores authoritative state and correct runtime mode without manual refresh hacks.  
AC-M10-11: Start/end snapshots are persisted for recap flow.  
AC-M10-12: M10 test suites plus selected regressions pass in local `.venv`.

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Introducing scene-stack schema and keeping backward compatibility with existing map/state code can cause integration regressions. | `high` | yes |
| R2 | Session RBAC expansion (`CO_DM`, `OBSERVER`) across REST and Socket paths is easy to mismatch. | `high` | yes |
| R3 | UI scope can balloon if DM cockpit attempts to include too many controls in first cut. | `medium` | yes |
| R4 | Action system may drift toward full rules engine if vertical-slice limits are not enforced. | `high` | yes |
| R5 | Existing deprecation warnings may hide meaningful M10 failures in noisy test output. | `low` | no |

Assumption A1: M10 prioritizes playable session flow over deep automation depth.  
Assumption A2: Non-SRD branded content is out of scope for M10 implementation.

---

## Planned Deploy Artifacts

- `vtt_app/play/__init__.py` (new)
- `vtt_app/play/routes.py` (new)
- `vtt_app/play/service.py` (new)
- `vtt_app/play/actions.py` (new, action catalog v1)
- `vtt_app/models/scene_stack.py` (new)
- `vtt_app/models/scene_layer.py` (new)
- `vtt_app/models/session_snapshot.py` (new)
- `vtt_app/models/campaign_member.py` (role-value extension handling)
- `vtt_app/models/game_session.py` (state normalization support)
- `vtt_app/models/__init__.py` (new model registrations)
- `vtt_app/campaigns/routes.py` (transition compatibility and helper reuse)
- `vtt_app/socket_handlers.py` (play mode/state/layer events + reconnect guarantees)
- `vtt_app/__init__.py` (register play blueprint)
- `vtt_app/templates/play.html` (new)
- `vtt_app/static/js/play-client.js` (new)
- `vtt_app/static/js/play-socket.js` (new)
- `vtt_app/static/js/play-ui.js` (new)
- `vtt_app/templates/campaigns.html` (enter-session links to `/play`)
- `tests/test_play_bootstrap_api.py` (new)
- `tests/test_session_state_machine.py` (new)
- `tests/test_ready_check.py` (new)
- `tests/test_scene_stack_api.py` (new)
- `tests/test_play_permissions.py` (new)
- `tests/test_play_rejoin_socket.py` (new)
- `tests/test_action_bar_v1.py` (new)
- `milestone_m10_deploy_output.md` (new)

---

## Next Step

Start **M10 Deploy** and implement the approved vertical slice in one pass:

1. add `/play` runtime shell and bootstrap contract,
2. implement lifecycle transitions + ready-check + waiting-room mode,
3. implement minimal scene-stack/layer activation integrated with existing state model,
4. add action bar v1 with explicit dice-preserving flow,
5. implement reconnect/state-authority guarantees and execute M10 + regression suites.
