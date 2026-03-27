# M6 Monitor Output: Character Sheets and Combat Automation Validation

```
artifact: monitor-output
milestone: M6
phase: MONITOR
status: complete
date: 2026-03-26
```

---

## Input Summary

- Deployment baseline:
  - `milestone_m6_deploy_output.md`
- Scope monitored:
  - character sheet API/resource behavior
  - combat lifecycle/API/realtime behavior
  - regression impact on M3-M5 modules

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m6_monitor_output.md` | M6 validation record and close recommendation | `immutable` after phase close | active draft in this turn |

---

## Validation Results

### Test suites

- `.\.venv\Scripts\python.exe -m pytest -q tests\test_character_sheet_resources.py tests\test_combat_api.py tests\test_combat_realtime.py`
  - `10 passed`
- `.\.venv\Scripts\python.exe -m pytest -q tests\test_auth.py tests\test_campaigns.py tests\test_characters.py tests\test_maps.py tests\test_session_state.py tests\test_tokens_realtime.py tests\test_character_sheet_resources.py tests\test_combat_api.py tests\test_combat_realtime.py`
  - `74 passed`

### Endpoint / contract checks

Character sheet route surface in `vtt_app/characters/routes.py`:

- `GET /api/characters/<id>/sheet`
- spells CRUD sub-resources
- equipment CRUD sub-resources
- inventory CRUD sub-resources

Combat route surface in `vtt_app/campaigns/routes.py`:

- `GET /combat/state`
- `POST /combat/start`
- `POST /combat/initiative`
- `POST /combat/turn/advance`
- `POST /combat/hp-adjust`
- `POST /combat/end`

Realtime contract presence:

- Room-broadcast combat events emitted from `vtt_app/campaigns/routes.py`:
  - `combat:started`
  - `combat:updated`
  - `combat:turn`
  - `combat:hp`
  - `combat:ended`
- Socket read-path event in `vtt_app/socket_handlers.py`:
  - `combat:state:request`

### Access-control smoke checks

Verified with unauthenticated test client:

- `GET /api/characters/1/sheet` -> `401`
- `GET /api/campaigns/1/sessions/1/combat/state` -> `401`
- `POST /api/campaigns/1/sessions/1/combat/start` -> `401`

### UI placeholder check

Pattern scan across `characters.html`, `campaigns.html`, `character-sheet.html`:

- `NO_PLACEHOLDER_ALERTS_FOUND`

---

## Findings

- M6 character-sheet scope is functionally complete and test-backed.
- Combat-lite lifecycle (start/initiative/turn/hp/end) is functional with version/conflict enforcement.
- Combat updates are room-scoped and validated by realtime tests.
- Access control is enforced on monitored critical endpoints (unauthenticated requests receive `401`).
- No regressions detected across previously stabilized auth/campaign/character/map/session/token suites.

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | SQLAlchemy relationship-overlap warnings remain (legacy model configuration debt). | `medium` | accepted |
| R2 | `Query.get()` legacy warnings remain across modules. | `medium` | accepted |
| R3 | `datetime.utcnow()` deprecation warnings remain across modules. | `medium` | accepted |
| R4 | Test JWT secret-length warning remains in testing configuration only. | `low` | accepted |
| R5 | DM-only combat mutation policy is intentionally conservative and may require M6.1/M7 evolution for richer player actions. | `low` | accepted |

Assumption A1: M6 acceptance targets stable combat-lite gameplay loop and sheet integration, not full strict 5e automation.

---

## Milestone Status

M6 is ready to close:

- Discover: complete
- Apply: complete
- Deploy: complete
- Monitor: complete

---

## Next Step

Start **M7 Discover** (Community and Moderation):

1. inventory current chat/voice/moderation capabilities,
2. map moderation control points and abuse/reporting flows,
3. define M7 boundary and prioritized implementation surface.
