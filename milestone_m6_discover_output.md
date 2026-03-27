# M6 Discover Output: Character Sheets and Combat Workflow

```
artifact: discover-output
milestone: M6
phase: DISCOVER
status: complete
date: 2026-03-26
```

---

## Input Summary

- Prior milestone baseline:
  - `milestone_m5_deploy_output.md`
  - `milestone_m5_monitor_output.md`
- Runtime method:
  - `dadm-framework/runtime/AI_BIOS.md`
  - `dadm-framework/runtime/file-registry.yaml`
  - profile: `standard`
  - route card: `discover`
- M6 objective from plan:
  - Discover: D&D model scope, combat workflow
  - Apply: modular sheet/combat engine design
  - Deploy: character CRUD + automation

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m6_discover_output.md` | M6 current-state evidence and boundary definition | `immutable` after phase close | active draft in this turn |
| terminal evidence (commands, probes) | support evidence for discovery | `mutable` | not canonical |

---

## Current-State Summary

- Relevant: Character CRUD API is implemented and authenticated (`POST/GET/PUT/DELETE` for `/api/characters*`).
- Relevant: Character model already contains D&D-style core stats and relationships to spells, equipment, and inventory entities.
- Relevant: M5 foundation provides persisted `SessionState` + `TokenState` with HP and `initiative` fields plus optimistic concurrency/version conflict handling.
- Relevant: Realtime room-scoped token flows (`session:join`, `token:create/update/delete`) and conflict events are present and tested.
- Relevant: Character frontend has a working create flow (wizard with ability score logic), list, filter, and delete.
- Relevant: Character edit/view flows are placeholders in UI (`alert(...)`) and not feature-complete.
- Relevant: Spell, Equipment, and Inventory models exist, but dedicated character sub-resource APIs are not implemented.
- Not relevant for M6 Discover boundary: deeper moderation/community features (M7 scope).

---

## Inventory

| # | Name | Description | Location | Status |
|---|---|---|---|---|
| I1 | Character CRUD routes | Create/list/get/update/delete character endpoints | `vtt_app/characters/routes.py` | present |
| I2 | Character domain model | Core sheet fields (stats, AC/HP, class/race, JSON payload) | `vtt_app/models/character.py` | present |
| I3 | Spell model | Character-linked spell data model | `vtt_app/models/spell.py` | present |
| I4 | Equipment model | Character-linked equipment model | `vtt_app/models/equipment.py` | present |
| I5 | Inventory model | Character-linked inventory item model | `vtt_app/models/inventory_item.py` | present |
| I6 | Spell/equipment/inventory APIs | Character sub-resource CRUD endpoints | `vtt_app/characters/*` | missing |
| I7 | Character page UI | Character list + create wizard + delete flow | `vtt_app/templates/characters.html` | partial |
| I8 | Character view/edit UI routes | Dedicated editor/sheet pages and wiring | `vtt_app/templates/*` | missing |
| I9 | Session state API | Session state payload with active map and tokens | `vtt_app/campaigns/routes.py` | present |
| I10 | Token state model | Persistent token state incl. HP/initiative/version | `vtt_app/models/token_state.py` | present |
| I11 | Token realtime handlers | Realtime token create/update/delete and join/leave | `vtt_app/socket_handlers.py` | present |
| I12 | Combat encounter model | Structured encounter/round/turn state entity | `vtt_app/models/*` | missing |
| I13 | Combat workflow API | Start combat, roll initiative, advance turn, resolve action | `vtt_app/*/routes.py` | missing |
| I14 | Combat UI surface | Initiative tracker and turn controls in live session UI | `vtt_app/templates/*` | missing |
| I15 | Character CRUD tests | Endpoint coverage for current character API | `tests/test_characters.py` | present |
| I16 | Combat rules tests | Deterministic tests for turn order/action resolution | `tests/*` | missing |

---

## Dependencies

| # | Dependency | Version | Status |
|---|---|---|---|
| D1 | Flask | 2.3.3 | present |
| D2 | Flask-SQLAlchemy | 3.0.5 | present |
| D3 | Flask-JWT-Extended | 4.5.2 | present |
| D4 | Flask-SocketIO | 5.3.6 | present |
| D5 | python-socketio | 5.8.0 | present |
| D6 | Flask-Limiter | 3.5.0 | present |
| D7 | pytest + pytest-flask | 7.4.3 / 1.3.0 | present |
| D8 | Existing M5 session/token persistence layer | current codebase | present |
| D9 | Migration tooling (Alembic/Flask-Migrate) | not configured | missing |

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Combat-relevant fields (`hp_current`, `initiative`) exist on tokens, but no canonical encounter lifecycle defines order/state transitions. | `high` | yes |
| R2 | Missing spell/equipment/inventory APIs blocks full character sheet functionality despite existing models. | `high` | yes |
| R3 | Character UI edit/view placeholders prevent complete player sheet workflow from frontend. | `medium` | yes |
| R4 | No dedicated combat API/service boundary increases risk of ad-hoc logic spread across routes/sockets. | `high` | yes |
| R5 | No automated combat-rule test suite increases regression risk once turn logic is added. | `medium` | yes |
| R6 | Model helper methods that commit inside entity methods (`take_damage`, `heal`, `equip`, `use`) can create transaction-coupling risks during orchestration. | `low` | no |
| R7 | Missing migration framework increases schema-change risk for upcoming combat entities. | `low` | no |

Assumption A1: M6 should build on existing M5 session/token persistence and realtime transport rather than replacing it.

Assumption A2: M6 MVP can target combat-lite automation (initiative order, turn progression, HP updates, basic action logging) before advanced 5e rule automation.

---

## Open Questions

| # | Question | Priority | Owner |
|---|---|---|---|
| Q1 | What exact rules depth is in M6 scope: pure tracker, combat-lite automation, or strict 5e mechanics? | blocking | human |
| Q2 | What is the canonical combat container: one encounter per `GameSession`, or multiple encounters per session? | blocking | human + backend |
| Q3 | Should initiative be stored only per token, or as separate ordered turn-state snapshots with history? | blocking | backend |
| Q4 | Which actions must be automated in M6 (attack roll, damage roll, saves, concentration, conditions)? | important | human + backend |
| Q5 | Who can mutate combat state (DM-only progression vs controlled player actions on owned tokens)? | blocking | human |
| Q6 | Are spell/equipment/inventory sub-resource APIs required in M6 Deploy, or can they be staged into M6.1? | important | human |
| Q7 | Should combat logs be persisted for replay/audit, or only emitted realtime? | important | human + backend |

---

## Next Step

Proceed to **M6 Apply** to design:

1. a modular combat domain model (encounter + turn lifecycle) integrated with existing token/session state,
2. character sheet API expansion for spells/equipment/inventory,
3. clear REST + Socket.IO combat contracts and authorization rules,
4. frontend integration boundaries (character sheet + initiative surface),
5. test strategy for deterministic combat flow and regression control.
