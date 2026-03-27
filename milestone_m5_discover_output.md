# M5 Discover Output: Map, Token, Session-State Stabilization

```
artifact: discover-output
milestone: M5
phase: DISCOVER
status: complete
date: 2026-03-26
```

---

## Input Summary

- Prior milestone baseline:
  - `milestone_m4_deploy_output.md`
  - `milestone_m4_monitor_output.md`
- Runtime method:
  - `dadm-framework/runtime/AI_BIOS.md`
  - `dadm-framework/runtime/file-registry.yaml`
  - profile: `standard`
  - route card: `discover`
- M5 objective from plan:
  - map/grid/light persistence
  - persisted multi-map campaign support
  - sync/load stabilization

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m5_discover_output.md` | M5 current-state evidence and boundary definition | `immutable` after phase close | active draft in this turn |
| terminal evidence (commands, probes) | support evidence for discovery | `mutable` | not canonical |

---

## Current-State Summary

- Relevant: Socket.IO is initialized in app factory and event handlers are registered (`vtt_app/socket_handlers.py`).
- Relevant: Current live socket map/token state is in-memory only (`game_state` dict in `socket_handlers.py`), not database-backed.
- Relevant: Token events are global broadcast and not segmented by campaign/session room.
- Relevant: Campaign and `GameSession` entities exist from M4, but no persisted map/token/session-state model is linked to them.
- Relevant: No authenticated socket identity check is enforced in current socket handlers.
- Relevant: Legacy map/token REST endpoints exist in `vtt_app/api.py` but are not registered in app factory, so they are unreachable at runtime.
- Relevant: Legacy frontend map client (`index.html` + `src/main.js`) is not integrated with current template routing.
- Relevant: Verification probe in testing app:
  - `GET /api/game/state` -> `404 {"error":"not found"}`
  - `GET /api/tokens` -> `404 {"error":"not found"}`
  - `GET /src/main.js` returns HTML fallback (not JS asset delivery)
- Not relevant for M5 Discover boundary: auth-cookie architecture and M4 campaign CRUD details (already validated in M4).

---

## Inventory

| # | Name | Description | Location | Status |
|---|---|---|---|---|
| I1 | Socket server bootstrap | Flask-SocketIO initialized and handlers registered | `vtt_app/__init__.py`, `vtt_app/extensions.py` | present |
| I2 | Active realtime handlers | `get_map_state`, `token_create/update/delete`, `roll_dice` | `vtt_app/socket_handlers.py` | present |
| I3 | Active map state store | Global process-local dict (`tokens`, `effects`) | `vtt_app/socket_handlers.py` | present |
| I4 | Legacy state class | Alternative in-memory map/token store | `vtt_app/game_state.py` | present (not integrated) |
| I5 | Legacy token REST API | `/api/game/state`, `/api/tokens/*` endpoints | `vtt_app/api.py` | present (not integrated) |
| I6 | Legacy socket module | Alternate handler registration path | `vtt_app/sockets.py` | present (not integrated) |
| I7 | Persisted campaign sessions | Campaign and game-session models from M4 | `vtt_app/models/campaign.py`, `vtt_app/models/game_session.py` | present |
| I8 | Persisted map model | Dedicated map table/entity (campaign/session scoped) | `vtt_app/models/*` | missing |
| I9 | Persisted token state model | Dedicated token table/entity with ownership and position | `vtt_app/models/*` | missing |
| I10 | Persisted session state snapshot | Structured runtime state for active session restore | `vtt_app/models/*` | missing |
| I11 | Game session UI route/page | Current app-integrated page for live map session | `vtt_app/templates/*` | missing |
| I12 | Automated tests for map/socket synchronization | Pytest coverage for socket and map state flows | `tests/*` | missing |

---

## Dependencies

| # | Dependency | Version | Status |
|---|---|---|---|
| D1 | Flask | 2.3.3 | present |
| D2 | Flask-SocketIO | 5.3.6 | present |
| D3 | python-socketio | 5.8.0 | present |
| D4 | Flask-SQLAlchemy | 3.0.5 | present |
| D5 | JWT cookie auth stack | existing M3 architecture | present |
| D6 | Migration tooling (Alembic/Flask-Migrate) | not configured | missing |
| D7 | Distributed Socket.IO backend (Redis message queue) | not configured | missing |
| D8 | Frontend build integration for `/src/main.js` runtime client | not configured in current app routing | missing |

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | In-memory map/token state is lost on process restart (no persistence). | `high` | yes |
| R2 | Global shared token state can bleed across campaigns/sessions (single state container). | `high` | yes |
| R3 | Broadcast-only events without room isolation expose cross-session update leakage. | `high` | yes |
| R4 | Missing socket auth enforcement enables unauthorized token manipulation risk. | `high` | yes |
| R5 | Legacy map/token modules are present but not wired, creating divergence and maintenance confusion. | `medium` | yes |
| R6 | No automated socket/map synchronization tests increase regression risk for M5 changes. | `medium` | yes |
| R7 | Legacy map frontend assets are not served as executable JS in current routing model. | `medium` | yes |
| R8 | No migration framework increases schema-change risk for upcoming persisted map/token models. | `low` | no |

Assumption A1: M5 acceptance requires persistence and session isolation for map/token state, not just transient realtime movement.

Assumption A2: M5 may introduce new DB entities and API/socket contracts aligned with M4 campaign/session authorization boundaries.

---

## Open Questions

| # | Question | Priority | Owner |
|---|---|---|---|
| Q1 | What is the canonical persistence unit: per campaign, per game session, or both (snapshot + live)? | blocking | human + backend |
| Q2 | Should one campaign support multiple reusable maps in M5 (and map switching inside session)? | blocking | human |
| Q3 | What minimum map schema is required in M5 (grid type, dimensions, background, fog/light fields)? | blocking | human + backend |
| Q4 | What token schema is mandatory in M5 (position, size, hp, initiative, visibility, owner)? | important | human + backend |
| Q5 | Should socket authorization be strict member-based for all map/token events in M5 scope? | blocking | human |
| Q6 | What consistency target is required for sync conflicts (last-write-wins vs server-validated turns/locks)? | important | human + backend |
| Q7 | Is Redis/socket horizontal scale required now or deferred to later production-readiness milestone? | important | human |

---

## Next Step

Proceed to **M5 Apply** to design:

1. the persisted map/token/session-state data model,
2. campaign/session scoped realtime contract (auth + room boundaries),
3. API and socket interface definitions,
4. migration and test strategy for M5 deployment.
