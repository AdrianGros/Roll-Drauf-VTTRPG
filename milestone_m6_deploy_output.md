# M6 Deploy Output: Character Sheets and Combat Automation

```
artifact: deploy-output
milestone: M6
phase: DEPLOY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Approved design baseline:
  - `milestone_m6_apply_output.md`
- Human approval:
  - implicit go after M6 Apply completion
- Deployment scope:
  - character sheet API expansion (spells/equipment/inventory)
  - session-scoped combat persistence + lifecycle endpoints
  - room-scoped realtime combat broadcasts
  - minimal UI wiring for sheet + combat controls
  - M6 automated test coverage + regression verification

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m6_deploy_output.md` | M6 deployment execution + proof record | `immutable` after phase close | active draft in this turn |

---

## Implementation Summary

Implemented M6 combat-lite and character-sheet stack end-to-end:

- Added new persisted combat domain entities:
  - `CombatEncounter` for encounter lifecycle (round/turn/version/active token)
  - `CombatEvent` for append-only event logging
- Added combat service layer (`vtt_app/combat/service.py`) for:
  - encounter start
  - initiative ordering
  - turn advancement
  - HP adjustment with linked character mirror
  - encounter end
- Extended campaign API with DM-guarded combat endpoints:
  - combat state
  - start
  - initiative set
  - turn advance
  - hp adjust
  - end
- Added room-scoped combat realtime fanout (`combat:started`, `combat:updated`, `combat:turn`, `combat:hp`, `combat:ended`) on REST mutations.
- Extended character API with full sheet/resource endpoints:
  - `GET /api/characters/<id>/sheet`
  - spells CRUD
  - equipment CRUD
  - inventory CRUD
- Updated frontend flow:
  - `characters.html` View/Edit now routes to real sheet page
  - new `character-sheet.html` supports core editing and resource management
  - `campaigns.html` now provides minimal combat state + DM controls

---

## Files Changed

- `vtt_app/models/combat_encounter.py` (new)
- `vtt_app/models/combat_event.py` (new)
- `vtt_app/models/__init__.py`
- `vtt_app/combat/__init__.py` (new)
- `vtt_app/combat/service.py` (new)
- `vtt_app/characters/routes.py`
- `vtt_app/campaigns/routes.py`
- `vtt_app/socket_handlers.py`
- `vtt_app/templates/characters.html`
- `vtt_app/templates/character-sheet.html` (new)
- `vtt_app/templates/campaigns.html`
- `tests/test_character_sheet_resources.py` (new)
- `tests/test_combat_api.py` (new)
- `tests/test_combat_realtime.py` (new)
- `milestone_m6_deploy_output.md` (new)

---

## Proofs

Executed command:

`.\.venv\Scripts\python.exe -m pytest -q tests\test_character_sheet_resources.py tests\test_combat_api.py tests\test_combat_realtime.py`

Result:

- `10 passed`

Executed command:

`.\.venv\Scripts\python.exe -m pytest -q tests\test_auth.py tests\test_campaigns.py tests\test_characters.py tests\test_maps.py tests\test_session_state.py tests\test_tokens_realtime.py tests\test_character_sheet_resources.py tests\test_combat_api.py tests\test_combat_realtime.py`

Result:

- `74 passed`

Notes:

- Test runs report known pre-existing SQLAlchemy overlap and legacy/deprecation warnings (same warning class as prior milestones).

---

## Acceptance Checklist

- [x] AC-M6-01: Character sheet endpoint returns core character + spells + equipment + inventory in one payload.
- [x] AC-M6-02: Spell/equipment/inventory sub-resource CRUD exists with owner-only mutation enforcement.
- [x] AC-M6-03: Combat encounter can be started for a session with persisted encounter state.
- [x] AC-M6-04: Initiative ordering is deterministic and persisted, with round/turn pointers maintained.
- [x] AC-M6-05: Turn advance updates active token and round transitions correctly.
- [x] AC-M6-06: HP adjustment clamps safely and mirrors linked character HP.
- [x] AC-M6-07: Combat mutations enforce DM authorization (`403` on non-DM).
- [x] AC-M6-08: Encounter version conflicts return `409` with authoritative state.
- [x] AC-M6-09: Combat updates are broadcast only to matching campaign/session room.
- [x] AC-M6-10: M6 suites and core regression suites pass in local `.venv`.

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Existing ORM overlap warnings and legacy `Query.get()` usage remain technical debt. | `medium` | accepted |
| R2 | Existing `datetime.utcnow()` deprecation warnings remain across legacy code paths. | `medium` | accepted |
| R3 | DM-only combat mutation model is conservative and may need player-action expansion in later milestone. | `low` | accepted |
| R4 | No migration framework (Alembic/Flask-Migrate) still increases schema evolution risk. | `low` | no |

Assumption A1: M6 completion targets stable combat-lite automation, not strict/full 5e simulation.

---

## Next Step

Proceed to **M6 Monitor**:

1. validate gameplay loop behavior in integrated UI/manual run,
2. capture residual risks and hardening backlog,
3. confirm milestone close readiness.
