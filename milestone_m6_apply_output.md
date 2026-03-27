# M6 Apply Output: Character Sheets and Combat Automation Design

```
artifact: apply-output
milestone: M6
phase: APPLY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Discover baseline:
  - `milestone_m6_discover_output.md`
- Human approval:
  - `APPROVED: M6 Apply`
- Constraints and method:
  - DAD-M runtime profile `standard`
  - Apply phase only: architecture, contracts, acceptance criteria (no implementation code)
  - Build on existing M5 session/token persistence and realtime room model

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m6_apply_output.md` | M6 solution design baseline for Deploy | `immutable` after phase close | active draft in this turn |

---

## Recommended Decision Set (for M6 Deploy)

1. **Combat scope = combat-lite automation**  
   Initiative, turn progression, HP updates, and action log are in scope; full strict 5e rules engine is deferred.

2. **Combat authority = DM-controlled mutations**  
   Active members can read combat state, but combat mutations (start/end/turn/hp changes) are DM-only in M6.

3. **Write path = REST authoritative, Socket.IO broadcast-only**  
   Mutations go through REST for consistent auth/version handling; sockets distribute state updates to room members.

---

## Design Tradeoffs

| Topic | Option A | Option B | Selected | Reason |
|---|---|---|---|---|
| Rules depth | strict 5e automation | combat-lite engine | **B** | Delivers usable combat loop in M6 without rules explosion risk |
| Mutation authority | mixed DM/player writes | DM-only writes | **B** | Lower cheating/race-condition risk and simpler enforcement |
| Realtime write path | socket+REST writes | REST writes + socket fanout | **B** | One canonical validation path and easier conflict handling |
| Encounter persistence | ephemeral memory | DB-backed encounter state | **B** | Required for restart safety and monitorability |

---

## Solution Design

### 1) Architecture (target M6)

M6 Deploy extends existing modules with bounded responsibilities:

- `characters` blueprint:
  - keep existing character CRUD
  - add character sheet sub-resources (spells/equipment/inventory)
- `campaigns` blueprint:
  - add session-scoped combat endpoints under campaign/session context
- service layer:
  - `vtt_app/combat/service.py` for encounter lifecycle, initiative ordering, and HP automation rules
- realtime:
  - reuse M5 room model (`campaign:{id}:session:{id}`)
  - emit combat state events on successful REST mutations

### 2) Data model design

#### A. Reused existing entities

- `characters` (owner/campaign-scoped character data)
- `spells`, `equipment`, `inventory_items` (already present)
- `session_states`, `token_states` (M5 persisted runtime state with `initiative`, HP, versioning)

#### B. `combat_encounters` (new)

Purpose: one persisted combat lifecycle per session at a time.

Fields:

- `id` (PK)
- `campaign_id` (FK -> campaigns.id, indexed)
- `game_session_id` (FK -> game_sessions.id, indexed)
- `session_state_id` (FK -> session_states.id, indexed)
- `status` (enum/string: `preparing`, `active`, `paused`, `completed`)
- `round_number` (int, default 1)
- `turn_index` (int, default 0)
- `active_token_id` (FK -> token_states.id, nullable)
- `initiative_order_json` (json array of token ids in turn order)
- `version` (int, default 1)
- `started_by` (FK -> users.id)
- `ended_by` (FK -> users.id, nullable)
- `started_at`, `ended_at`, `created_at`, `updated_at`

Rules:

- one active/preparing encounter per `game_session_id` (enforced in service validation).
- version increments on every mutating combat operation.

#### C. `combat_events` (new)

Purpose: append-only combat audit trail for monitor/replay and debugging.

Fields:

- `id` (PK)
- `encounter_id` (FK -> combat_encounters.id, indexed)
- `sequence_no` (int, monotonically increasing per encounter)
- `event_type` (enum/string: `start`, `initiative_set`, `turn_advanced`, `hp_adjusted`, `end`, `note`)
- `actor_token_id` (FK -> token_states.id, nullable)
- `target_token_id` (FK -> token_states.id, nullable)
- `payload_json` (json)
- `created_by` (FK -> users.id)
- `created_at` (datetime)

Rules:

- append-only (no update/delete in M6).
- service assigns sequence numbers.

### 3) API interface design (M6)

#### Character sheet expansion

1. `GET /api/characters/<char_id>/sheet`
- auth required
- owner or active campaign member can read
- returns: character core + spells + equipment + inventory

2. `GET /api/characters/<char_id>/spells`
3. `POST /api/characters/<char_id>/spells`
4. `PUT /api/characters/<char_id>/spells/<spell_id>`
5. `DELETE /api/characters/<char_id>/spells/<spell_id>`

6. `GET /api/characters/<char_id>/equipment`
7. `POST /api/characters/<char_id>/equipment`
8. `PUT /api/characters/<char_id>/equipment/<item_id>`
9. `DELETE /api/characters/<char_id>/equipment/<item_id>`

10. `GET /api/characters/<char_id>/inventory`
11. `POST /api/characters/<char_id>/inventory`
12. `PUT /api/characters/<char_id>/inventory/<item_id>`
13. `DELETE /api/characters/<char_id>/inventory/<item_id>`

Mutation policy:
- owner-only for create/update/delete
- campaign members read-only where access is permitted

#### Combat endpoints (session-scoped)

14. `GET /api/campaigns/<campaign_id>/sessions/<session_id>/combat/state`
- auth required, active campaign member
- returns current encounter + active token snapshot

15. `POST /api/campaigns/<campaign_id>/sessions/<session_id>/combat/start`
- DM-only
- body:
  - `mode`: `manual` or `auto`
  - `participant_token_ids` optional
- behavior:
  - validates active map/session state
  - creates encounter + initial order

16. `POST /api/campaigns/<campaign_id>/sessions/<session_id>/combat/initiative`
- DM-only
- body: `{ base_version, entries: [{ token_id, initiative }] }`
- behavior: updates token initiatives + recalculates encounter order

17. `POST /api/campaigns/<campaign_id>/sessions/<session_id>/combat/turn/advance`
- DM-only
- body: `{ base_version }`
- behavior: advances turn pointer; increments round when wrapping

18. `POST /api/campaigns/<campaign_id>/sessions/<session_id>/combat/hp-adjust`
- DM-only
- body:
  - `base_version`
  - `target_token_id`
  - `delta` (negative damage, positive heal)
  - `reason` optional
- behavior:
  - clamp HP to `[0, hp_max]`
  - mirror to linked `Character.hp_current` when `character_id` exists
  - append `combat_event`

19. `POST /api/campaigns/<campaign_id>/sessions/<session_id>/combat/end`
- DM-only
- body: `{ base_version }`
- behavior: marks encounter completed, persists final event

### 4) Realtime contract design (M6)

Client mutation remains REST-only. Server pushes updates to session room:

- `combat:started` `{ encounter, state_version }`
- `combat:updated` `{ encounter, change, state_version }`
- `combat:turn` `{ encounter_id, round_number, active_token_id, turn_index, version }`
- `combat:hp` `{ token_id, hp_current, hp_max, encounter_id, version }`
- `combat:ended` `{ encounter_id, ended_at, version }`
- `combat:error` `{ code, message }`

Conflict handling:

- mutating endpoints require `base_version` (except first start)
- mismatch returns `409` with authoritative encounter state

### 5) Workflow and consistency rules

Combat start:

1. Validate campaign membership and DM permission.
2. Validate session has active map + token set.
3. Select participants:
   - default: non-deleted tokens on active map with type in `player|npc|monster`
   - optional filtered set via `participant_token_ids`
4. Build initiative order:
   - `auto`: roll d20 + dex modifier (if linked character exists), fallback d20 only
   - `manual`: use existing token `initiative` values
5. Set `round_number = 1`, `turn_index = 0`, `active_token_id = first`.

Turn advance:

- increment `turn_index`
- if at end of order: set `turn_index = 0`, increment `round_number`
- skip deleted tokens and optionally zero-hp tokens (configurable rule fixed in M6: skip tokens with `hp_current == 0`)

HP adjust:

- update `token_states.hp_current`
- if linked character exists, mirror value to `characters.hp_current`
- bump both token version and encounter version

### 6) UI integration boundaries (M6 Deploy)

Character UI:

- replace placeholder `Edit/View` actions in `characters.html`
- add lightweight sheet view/editor route (`/character-sheet.html?id=<id>`) backed by new sheet endpoints
- include tabs/sections: Core, Spells, Equipment, Inventory

Campaign/session UI:

- extend campaign detail session card with minimal combat controls for DMs:
  - Start Combat
  - Set Initiative
  - Next Turn
  - HP Adjust
  - End Combat
- members see read-only encounter status summary

### 7) Test strategy (M6 Deploy target)

Backend tests:

- `tests/test_character_sheet_resources.py` (new)
  - spell/equipment/inventory CRUD + auth boundaries
- `tests/test_combat_api.py` (new)
  - encounter start/state/initiative/turn/hp/end + conflict/permission paths
- `tests/test_combat_realtime.py` (new)
  - room-scoped combat broadcasts and no cross-session leakage

Regression suites to keep green:

- `tests/test_auth.py`
- `tests/test_campaigns.py`
- `tests/test_characters.py`
- existing M5 suites (`test_maps.py`, `test_session_state.py`, `test_tokens_realtime.py`)

---

## Acceptance Criteria (for M6 Deploy)

AC-M6-01: Character sheet endpoint returns core character + spells + equipment + inventory in one payload.  
AC-M6-02: Spell/equipment/inventory sub-resource CRUD exists with owner-only mutation enforcement.  
AC-M6-03: Combat encounter can be started for a session with persisted encounter state.  
AC-M6-04: Initiative ordering is deterministic and persisted, with round/turn pointers maintained.  
AC-M6-05: Turn advance updates active token and round transitions correctly.  
AC-M6-06: HP adjustment updates token HP safely (clamp) and mirrors linked character HP.  
AC-M6-07: Combat mutations require DM authorization and return `403` for unauthorized actors.  
AC-M6-08: Encounter version conflicts return `409` with authoritative state payload.  
AC-M6-09: Combat state updates are broadcast only to the correct campaign/session room.  
AC-M6-10: M6 tests plus existing core regression suites pass in local `.venv`.

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | DM-only mutation model reduces abuse risk but may feel restrictive for player-driven flows. | `medium` | accepted for M6 |
| R2 | REST-only mutation path may add small latency vs direct socket writes, but improves consistency. | `low` | accepted for M6 |
| R3 | Combat-lite scope may not satisfy expectations for full 5e automation in first release. | `medium` | accepted for M6 |
| R4 | Missing migration framework still increases schema evolution risk for new combat tables. | `low` | no |
| R5 | Existing ORM/deprecation technical debt can surface warnings during M6 changes. | `low` | no |

Assumption A1: M6 acceptance targets a stable playable combat loop, not a complete tabletop rules engine.

Assumption A2: Existing M5 session/token architecture remains canonical and is extended, not replaced.

---

## Planned Deploy Artifacts

- `vtt_app/models/combat_encounter.py` (new)
- `vtt_app/models/combat_event.py` (new)
- `vtt_app/models/__init__.py` (update imports)
- `vtt_app/combat/__init__.py` (new)
- `vtt_app/combat/service.py` (new)
- `vtt_app/characters/routes.py` (character sheet sub-resource endpoints)
- `vtt_app/campaigns/routes.py` (combat endpoints)
- `vtt_app/socket_handlers.py` (combat event broadcasts)
- `vtt_app/templates/characters.html` (replace view/edit placeholders)
- `vtt_app/templates/character-sheet.html` (new)
- `vtt_app/templates/campaigns.html` (minimal combat controls + status)
- `tests/test_character_sheet_resources.py` (new)
- `tests/test_combat_api.py` (new)
- `tests/test_combat_realtime.py` (new)
- `milestone_m6_deploy_output.md` (new)

---

## Next Step

Start **M6 Deploy** and implement the approved design in one pass:

1. add combat persistence/service layer,
2. extend character sheet APIs,
3. implement session-scoped combat API + realtime fanout,
4. wire minimal UI flows,
5. execute M6 + regression test suite and record proofs.
