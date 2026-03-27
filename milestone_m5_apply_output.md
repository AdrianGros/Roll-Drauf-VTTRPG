# M5 Apply Output: Map, Token, Session-State Stabilization Design

```
artifact: apply-output
milestone: M5
phase: APPLY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Discover baseline:
  - `milestone_m5_discover_output.md`
- Human-approved defaults:
  1. Persistence unit: `GameSession` runtime state + campaign-level map catalog.
  2. Socket boundaries: strict campaign/session room scoping + member authorization.
  3. Consistency: server-validated writes with last-write-wins fallback.
  4. Scale: Redis/socket horizontal scaling deferred (design should stay compatible).
- Constraints:
  - Current stack only (Flask, SQLAlchemy, Flask-SocketIO, JWT cookies).
  - No implementation in Apply phase.

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m5_apply_output.md` | M5 solution design baseline for Deploy | `immutable` after phase close | active draft in this turn |

---

## Decision Log (M5 Apply)

```
date: 2026-03-26
decision: use dual-layer state model (campaign map catalog + session runtime state)
reason: supports reusable maps while isolating live play state per session
decided-by: human+agent
refs: milestone_m5_discover_output.md
```

```
date: 2026-03-26
decision: enforce socket auth and room scoping by campaign/session membership
reason: closes cross-session leakage and unauthorized mutation risks
decided-by: human+agent
refs: milestone_m5_discover_output.md
```

```
date: 2026-03-26
decision: use server-validated token writes with LWW fallback and version fields
reason: practical conflict control without introducing heavy distributed locking
decided-by: human+agent
refs: milestone_m5_discover_output.md
```

```
date: 2026-03-26
decision: defer Redis message queue to later milestone, keep interface redis-ready
reason: avoid unapproved dependency expansion in M5 while preserving upgrade path
decided-by: human+agent
refs: milestone_m5_discover_output.md
```

---

## Solution Design

### 1) Architecture (target M5)

State is split into two bounded layers:

- Campaign map catalog (durable reusable map definitions).
- Session runtime state (active map + token state tied to one `GameSession`).

Execution model:

- REST: authoritative CRUD for map catalog and state bootstrap.
- Socket.IO: realtime token/session deltas within one room per active session.
- DB write-through on all state mutations; no process-local canonical game state.

### 2) Data model design

#### A. `campaign_maps` (new)

Purpose: reusable map definitions per campaign.

Fields:

- `id` (PK)
- `campaign_id` (FK -> campaigns.id, indexed)
- `name` (string, required)
- `description` (text, optional)
- `grid_type` (string enum: `square` default)
- `grid_size` (int, default `32`)
- `width` (int, required)
- `height` (int, required)
- `background_url` (text, optional)
- `fog_enabled` (bool, default false)
- `light_rules` (json, optional)
- `created_by` (FK -> users.id)
- `created_at`, `updated_at`
- `archived_at` (nullable soft delete)

Rules:

- DM/owner manages catalog.
- Archived maps hidden from default listing.

#### B. `session_states` (new)

Purpose: one durable runtime state envelope per game session.

Fields:

- `id` (PK)
- `game_session_id` (FK -> game_sessions.id, unique, indexed)
- `campaign_id` (FK -> campaigns.id, indexed)
- `active_map_id` (FK -> campaign_maps.id, nullable until selected)
- `state_status` (enum: `preparing`, `live`, `paused`, `completed`)
- `snapshot_json` (json, optional lightweight aggregate snapshot)
- `version` (int, default 1)
- `last_synced_at` (datetime)
- `created_at`, `updated_at`

Rules:

- created lazily on first session map bootstrap or session start.
- one authoritative row per `GameSession`.

#### C. `token_states` (new)

Purpose: canonical token positions/properties for one session.

Fields:

- `id` (PK)
- `session_state_id` (FK -> session_states.id, indexed)
- `campaign_id` (FK -> campaigns.id, indexed)
- `game_session_id` (FK -> game_sessions.id, indexed)
- `map_id` (FK -> campaign_maps.id, indexed)
- `character_id` (FK -> characters.id, nullable)
- `owner_user_id` (FK -> users.id, nullable)
- `name` (string, required)
- `token_type` (enum: `player`, `npc`, `monster`, `object`)
- `x`, `y` (int, required)
- `size` (int, default 1)
- `rotation` (int, default 0)
- `hp_current`, `hp_max` (nullable int)
- `initiative` (nullable int)
- `visibility` (enum: `public`, `dm_only`, `owner_only`)
- `metadata_json` (json, optional)
- `version` (int, default 1)
- `updated_by` (FK -> users.id, nullable)
- `created_at`, `updated_at`
- `deleted_at` (soft delete marker)

Rules:

- hard unique guard: (`game_session_id`, `id`) scoped by session.
- all live token updates bump `version`.

### 3) API interface design (M5)

#### Map catalog

1. `POST /api/campaigns/<campaign_id>/maps`
- auth required, DM/owner only
- creates map definition

2. `GET /api/campaigns/<campaign_id>/maps`
- auth required, active member
- lists non-archived maps

3. `GET /api/campaigns/<campaign_id>/maps/<map_id>`
- auth required, active member

4. `PUT /api/campaigns/<campaign_id>/maps/<map_id>`
- auth required, DM/owner only

5. `DELETE /api/campaigns/<campaign_id>/maps/<map_id>`
- auth required, DM/owner only
- soft archive (`archived_at`)

#### Session state bootstrap/control

6. `GET /api/campaigns/<campaign_id>/sessions/<session_id>/state`
- auth required, active member
- returns:
  - session metadata
  - active map
  - token list
  - state version

7. `POST /api/campaigns/<campaign_id>/sessions/<session_id>/maps/activate`
- auth required, DM/owner only
- body: `{ map_id }`
- sets active map in `session_states`

#### Durable token fallback endpoints

8. `POST /api/campaigns/<campaign_id>/sessions/<session_id>/tokens`
- auth required
- member create (role policy below)

9. `PUT /api/campaigns/<campaign_id>/sessions/<session_id>/tokens/<token_id>`
- auth required
- server validates ownership/DM override

10. `DELETE /api/campaigns/<campaign_id>/sessions/<session_id>/tokens/<token_id>`
- auth required
- soft delete token

### 4) Socket contract design (M5)

Room model:

- canonical room id: `campaign:{campaign_id}:session:{session_id}`.
- no global token broadcasts.

Connection/auth:

- read JWT access cookie from socket handshake.
- resolve user identity and campaign membership before join.
- reject unauthenticated/unauthorized events with structured error ack.

Client -> server:

- `session:join` `{ campaign_id, session_id }`
- `session:leave` `{ campaign_id, session_id }`
- `state:request` `{ campaign_id, session_id }`
- `token:create` `{ campaign_id, session_id, token, client_event_id? }`
- `token:update` `{ campaign_id, session_id, token_id, patch, base_version, client_event_id? }`
- `token:delete` `{ campaign_id, session_id, token_id, base_version, client_event_id? }`
- `map:activate` `{ campaign_id, session_id, map_id }` (DM only)

Server -> client:

- `session:joined` `{ campaign_id, session_id, server_time }`
- `state:snapshot` `{ version, active_map, tokens }`
- `token:created` `{ token, version }`
- `token:updated` `{ token, version }`
- `token:deleted` `{ token_id, version }`
- `map:activated` `{ map_id, version }`
- `state:conflict` `{ token_id, expected_version, actual_token }`
- `state:error` `{ code, message }`

### 5) Authorization and consistency rules

Authorization:

- active campaign membership required for all state reads/joins.
- DM/owner-only: map create/update/archive and map activation.
- token mutation:
  - DM can mutate any token.
  - player can mutate only owned token (or assigned character token).

Consistency:

- server is source of truth for version increments.
- updates validated against `base_version`.
- on version mismatch:
  - reject with `state:conflict`,
  - send authoritative token state.
- LWW fallback:
  - if `base_version` missing, accept update and increment version using server timestamp order.

### 6) Migration and rollout strategy (M5 Deploy target)

Given no Alembic in repo, deploy sequence:

1. Add new SQLAlchemy models (`campaign_maps`, `session_states`, `token_states`).
2. Wire model imports in `vtt_app/models/__init__.py`.
3. Extend `game_sessions.map_id` from placeholder int to FK-compatible relation path.
4. Replace in-memory canonical socket state with DB-backed read/write flow.
5. Keep legacy `api.py` and `game_state.py` unused; mark deprecated in code comments and docs.

No new infrastructure dependency in M5:

- keep SocketIO single-process mode,
- keep event names and payloads redis-queue compatible for later M8 scale-out.

### 7) Test strategy (M5 Deploy target)

Backend tests:

- `tests/test_maps.py`
  - map CRUD authorization + archive behavior
- `tests/test_session_state.py`
  - state bootstrap, map activation, version increments
- `tests/test_tokens_realtime.py`
  - token CRUD via API fallback
  - version conflict behavior

Socket tests (Flask-SocketIO test client):

- unauthorized join denied
- non-member join denied
- room isolation (session A events not visible in session B)
- DM-only map activation enforced
- token update conflict emits `state:conflict`

Regression:

- existing `test_auth.py`, `test_campaigns.py`, `test_characters.py` must remain green.

---

## Acceptance Criteria (for M5 Deploy)

AC-M5-01: Map definitions persist per campaign and are retrievable by active members.  
AC-M5-02: Session runtime state persists per `GameSession` and survives process restart.  
AC-M5-03: Token state persists in DB and is scoped to campaign/session/map boundaries.  
AC-M5-04: Socket events are room-scoped; no cross-session token leakage.  
AC-M5-05: Socket auth enforces active membership before state access/mutation.  
AC-M5-06: DM-only operations (map management/activation) are enforced server-side.  
AC-M5-07: Versioned token updates detect conflicts and return authoritative state.  
AC-M5-08: No new infrastructure dependency (Redis) is required for M5 acceptance.  
AC-M5-09: M5 tests cover API + socket happy/negative paths and pass with existing suites.

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Absence of migration framework increases schema rollout risk in production-like environments. | `medium` | accepted for M5 |
| R2 | Single-process Socket.IO remains a scaling limit until Redis-backed deployment phase. | `medium` | accepted for M5 |
| R3 | Legacy unused modules may cause confusion if not clearly deprecated in Deploy docs. | `low` | no |

Assumption A1: Session-scoped persistence and auth isolation are sufficient for M5 completion before advanced combat/initiative logic.  
Assumption A2: Multi-map support in M5 means catalog + active-map switching, not full map editor tooling.

---

## Planned Deploy Artifacts

- `vtt_app/models/campaign_map.py` (new)
- `vtt_app/models/session_state.py` (new)
- `vtt_app/models/token_state.py` (new)
- `vtt_app/models/__init__.py` (update imports)
- `vtt_app/campaigns/routes.py` (map/session-state endpoints)
- `vtt_app/socket_handlers.py` (room/auth/persistence rewrite)
- `tests/test_maps.py` (new)
- `tests/test_session_state.py` (new)
- `tests/test_tokens_realtime.py` (new)
- `milestone_m5_deploy_output.md` (new)

---

## Next Step

Start **M5 Deploy** and implement the approved design in one pass:

1. DB models and relationships
2. REST endpoints for map catalog + session state
3. socket room/auth + versioned token mutation pipeline
4. test suite and deploy proof artifact
