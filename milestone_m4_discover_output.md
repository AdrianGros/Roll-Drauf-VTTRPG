# M4 Discover Output: Campaign and Session Core Loop

```
artifact: discover-output
milestone: M4
phase: DISCOVER
status: complete
date: 2026-03-26
```

---

## Input Summary

- Runtime method (dad-m-light):
  - `dadm-framework/runtime/AI_BIOS.md`
  - `dadm-framework/runtime/file-registry.yaml`
  - profile: `standard`
  - loaded cards: `core-rules`, `phase-map`, `deliverables-min`, `governance-min`, `discover-card`
- Existing milestone artifacts:
  - `milestone_m4_apply_output.md`
  - `milestone_m4_monitor_output.md`
- Current codebase evidence:
  - `vtt_app/campaigns/routes.py`
  - `vtt_app/models/{campaign,campaign_member,game_session,invite_token}.py`
  - `vtt_app/templates/{campaigns,lobby}.html`
  - `tests/{test_campaigns,test_auth,test_characters}.py`

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m4_discover_output.md` | Discover phase evidence record | `immutable` after phase close | active draft in this turn |
| runtime notes (terminal analysis) | ephemeral analysis support | `mutable` | not retained as canonical artifact |

---

## Current-State Summary

- Relevant: Campaign domain models exist and persist in DB (`Campaign`, `CampaignMember`, `GameSession`, `InviteToken`).
- Relevant: Cookie-based auth and CSRF-enabled auth utilities are live and tested, so M4 can rely on authenticated session context.
- Relevant: Campaign backend currently exposes 6 routes:
  - `GET /api/campaigns`
  - `POST /api/campaigns`
  - `GET /api/campaigns/mine`
  - `POST /api/campaigns/<id>/invite`
  - `POST /api/campaigns/<id>/accept-invite`
  - `POST /api/campaigns/<id>/sessions`
- Relevant: Campaign UI exists (`campaigns.html`, `lobby.html`) but key actions are placeholders (`alert(...)`) rather than real flows.
- Relevant: Campaign test suite is passing for implemented subset (create/list/invite/create-session).
- Relevant: Static routing supports extensionless routes (`/campaigns`, `/dashboard`, etc.).
- Not relevant for M4 core loop: map realtime token synchronization in `socket_handlers.py` (belongs mainly to M5).
- Unclear: target depth for realtime campaign/session events in M4 vs defer to M5.

---

## Inventory

| # | Name | Description | Location | Status |
|---|---|---|---|---|
| I1 | Campaign model | Core campaign entity with owner, status, max_players, soft delete | `vtt_app/models/campaign.py` | present |
| I2 | CampaignMember model | Membership table with DM/Player role + invite/active states | `vtt_app/models/campaign_member.py` | present |
| I3 | GameSession model | Session entity with schedule/start/end timestamps | `vtt_app/models/game_session.py` | present |
| I4 | InviteToken model | Secure invite tokens with expiry and used marker | `vtt_app/models/invite_token.py` | present |
| I5 | Campaign API (subset) | 6 implemented campaign/session endpoints | `vtt_app/campaigns/routes.py` | present |
| I6 | Campaign detail/update/archive API | GET by id, PUT, DELETE for campaigns | `vtt_app/campaigns/routes.py` | missing |
| I7 | Campaign member listing API | List members endpoint | `vtt_app/campaigns/routes.py` | missing |
| I8 | Session lifecycle APIs | list/start/end session endpoints | `vtt_app/campaigns/routes.py` | missing |
| I9 | Campaign UI actions | create/join/view/delete workflows in UI | `vtt_app/templates/campaigns.html` | partial |
| I10 | Lobby workflow actions | create/join/enter actions in lobby | `vtt_app/templates/lobby.html` | partial |
| I11 | Realtime campaign/socket events | Campaign/session-specific socket event layer | `vtt_app/socket_handlers.py` | missing |
| I12 | M4 tests (backend subset) | Cookie-auth campaign tests for current endpoints | `tests/test_campaigns.py` | present |

---

## Dependencies

| # | Dependency | Version | Status |
|---|---|---|---|
| D1 | Flask | 2.3.3 | present |
| D2 | Flask-SQLAlchemy | 3.0.5 | present |
| D3 | Flask-JWT-Extended | 4.5.2 | present |
| D4 | Flask-Limiter | 3.5.0 | present |
| D5 | Flask-SocketIO | 5.3.6 | present |
| D6 | Flask-CORS | 4.0.0 | present |
| D7 | pytest + pytest-flask | 7.4.3 / 1.3.0 | present |
| D8 | Database migrations (Alembic/Flask-Migrate) | not configured | missing |

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Endpoint surface is incomplete versus M4 target workflow (campaign CRUD + full session lifecycle). | `medium` | yes |
| R2 | Invite endpoint does not guard against duplicate membership before insert; unique constraint can cause runtime failure path. | `medium` | yes |
| R3 | Campaign and lobby UI are partially stubbed, so users cannot complete end-to-end flow from UI alone. | `medium` | yes |
| R4 | No campaign/session-specific Socket.IO events yet; realtime coordination expectations may be unmet for M4 demos. | `low` | no |
| R5 | SQLAlchemy overlap/legacy warnings (`Query.get`, relationship overlaps) increase maintenance risk but do not currently break flow. | `low` | no |
| R6 | Missing migration layer means schema evolution for upcoming milestones carries operational risk. | `low` | no |

Assumption A1: For M4 completion, backend-first closure is acceptable if UI/Realtime deltas are explicitly scoped and tracked.

---

## Open Questions

| # | Question | Priority | Owner |
|---|---|---|---|
| Q1 | Should M4 include the full 12-endpoint contract now, or mark some endpoints as M4.1/M5? | blocking | human |
| Q2 | Are campaign/session realtime events mandatory for M4 acceptance, or explicitly deferred to M5? | blocking | human |
| Q3 | Do we want to ship full UI action wiring in M4, or allow API-complete + UI-partial for milestone close? | blocking | human |
| Q4 | Should invite tokens be one-time per invitee only, or reusable links per campaign within expiry? | important | human + backend |

---

## Next Step

Proceed to M4 Apply by designing a **delta plan** that closes the blocking gaps (API completeness, invite guardrails, and UI flow definition) within a single approval-scoped implementation pass.

