# M5 Deploy Output: Map, Token, Session-State Stabilization

```
artifact: deploy-output
milestone: M5
phase: DEPLOY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Approved design baseline:
  - `milestone_m5_apply_output.md`
- Human approval:
  - `APPROVED: M5 Deploy`
- Deployment scope:
  - persisted map catalog + session/token state models
  - campaign/session state REST endpoints
  - room-scoped authenticated Socket.IO state sync
  - M5 test coverage for maps, state, realtime token flows

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m5_deploy_output.md` | M5 deployment execution + proof record | `immutable` after phase close | active draft in this turn |

---

## Implementation Summary

Implemented M5 core persistence and isolation layer:

- Added durable model layer for map catalog, session state, and token state.
- Extended campaign routes with map CRUD, session-state bootstrap, map activation, and token CRUD endpoints.
- Replaced in-memory/global socket state flow with DB-backed, auth-validated, room-scoped realtime events.
- Preserved existing M3/M4 auth and campaign flows while integrating M5 state updates.

---

## Files Changed

- `vtt_app/models/game_session.py`
- `vtt_app/models/__init__.py`
- `vtt_app/models/campaign_map.py` (new)
- `vtt_app/models/session_state.py` (new)
- `vtt_app/models/token_state.py` (new)
- `vtt_app/campaigns/routes.py`
- `vtt_app/socket_handlers.py` (rewritten)
- `tests/test_maps.py` (new)
- `tests/test_session_state.py` (new)
- `tests/test_tokens_realtime.py` (new)
- `milestone_m5_deploy_output.md` (new)

---

## Proofs

Executed command:

`.\.venv\Scripts\python.exe -m pytest -q tests\test_maps.py tests\test_session_state.py`

Result:

- `9 passed`

Executed command:

`.\.venv\Scripts\python.exe -m pytest -q tests\test_tokens_realtime.py`

Result:

- `5 passed`

Executed command:

`.\.venv\Scripts\python.exe -m pytest -q tests\test_auth.py tests\test_campaigns.py tests\test_characters.py tests\test_maps.py tests\test_session_state.py tests\test_tokens_realtime.py`

Result:

- `64 passed`

---

## Acceptance Checklist

- [x] AC-M5-01: Map definitions persist per campaign and are retrievable by active members.
- [x] AC-M5-02: Session runtime state persists per `GameSession` (DB-backed bootstrap path).
- [x] AC-M5-03: Token state persists and is scoped to campaign/session/map.
- [x] AC-M5-04: Socket events are room-scoped per campaign/session.
- [x] AC-M5-05: Socket auth enforces authenticated active membership.
- [x] AC-M5-06: DM-only map management/activation enforced server-side.
- [x] AC-M5-07: Version conflict path implemented (`state:conflict` / HTTP `409`).
- [x] AC-M5-08: No Redis or new infrastructure dependency introduced.
- [x] AC-M5-09: New M5 suites and existing regression suites pass.

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | SQLAlchemy relationship overlap warnings still exist (pre-existing model debt). | `medium` | accepted |
| R2 | `Query.get()` and `datetime.utcnow()` deprecation warnings remain technical debt. | `medium` | accepted |
| R3 | Single-process Socket.IO remains non-horizontal until future Redis-backed scaling. | `medium` | accepted |

Assumption A1: Current M5 completion focuses on persistence/isolation correctness rather than horizontal scale rollout.

---

## Next Step

Proceed to **M5 Monitor**:

1. validate endpoint/socket behavior against acceptance criteria in one monitoring artifact,
2. record residual risks and hardening backlog (deprecations, relationship overlaps),
3. confirm milestone close readiness.
