# M16 Discover Output: Session Workspace and Asset Upload Foundation

```
artifact: discover-output
milestone: M16
phase: DISCOVER
status: complete
date: 2026-03-27
```

---

## Input Summary

- Existing backend runtime and session architecture in:
  - `vtt_app/campaigns/routes.py`
  - `vtt_app/play/routes.py`
  - `vtt_app/play/service.py`
  - `vtt_app/socket_handlers.py`
  - `vtt_app/models/*`
- Frontend runtime shell in:
  - `vtt_app/templates/play.html`
  - `vtt_app/static/js/play-ui.js`
  - `vtt_app/templates/campaigns.html`
- Existing tests for maps/session/tokens/realtime:
  - `tests/test_maps.py`
  - `tests/test_session_state.py`
  - `tests/test_tokens_realtime.py`
  - `tests/test_play_bootstrap_api.py`
- Existing milestone and roadmap context:
  - `milestone_plan.md`
  - `dadm-framework/framework/templates/discover-output.md`

---

## Current-State Summary

- Session runtime model is already persisted and session-scoped (`SessionState`, `TokenState`, `GameSession`): relevant.
- Realtime room isolation by campaign/session exists in socket handlers: relevant.
- Map catalog exists (`CampaignMap`) and supports CRUD via JSON: relevant.
- Token state exists and supports CRUD + optimistic versioning: relevant.
- File upload pipeline (multipart upload, storage, serving, metadata, lifecycle): missing.
- Asset library model (map/token image assets with ownership and scope): missing.
- Upload-specific security controls (type whitelist, max size, sanitization): missing.
- Campaign UI currently does not expose map management/upload workflows: relevant gap.
- Play UI currently displays state but has no file ingestion UX for maps/tokens: relevant gap.
- Legacy non-session API module (`vtt_app/api.py`) exists but is marked as legacy and not app-factory runtime: relevant risk for confusion, not implementation blocker.

---

## Inventory

| # | Name | Description | Location | Status |
|---|---|---|---|---|
| I1 | Session state envelope | One persisted runtime state per game session (`active_map_id`, versioning) | `vtt_app/models/session_state.py` | present |
| I2 | Token runtime state | Session/map-scoped token persistence with soft delete and versioning | `vtt_app/models/token_state.py` | present |
| I3 | Campaign map catalog | Reusable map records with `background_url` only (no upload object) | `vtt_app/models/campaign_map.py` | present |
| I4 | Map CRUD API | JSON map creation/update including `background_url` | `vtt_app/campaigns/routes.py` | present |
| I5 | Session bootstrap API | Play bootstrap returns state payload, scene stack, mode, read-only flags | `vtt_app/play/routes.py` | present |
| I6 | Realtime state sync | `session:join`, `state:snapshot`, token create/update/delete events scoped to room | `vtt_app/socket_handlers.py` | present |
| I7 | Frontend play shell | Runtime controls, layer activation, token list, action bar | `vtt_app/templates/play.html`, `vtt_app/static/js/play-ui.js` | present |
| I8 | Campaign management UI | Sessions/members/community workflows but no map upload flow | `vtt_app/templates/campaigns.html` | present (gap) |
| I9 | Character token URL field | Character stores `token_url` as raw string only | `vtt_app/models/character.py` | present (gap) |
| I10 | Upload endpoint/API | Multipart upload endpoint and asset serving path | backend APIs | missing |
| I11 | Asset storage configuration | Upload directory/object storage config and retention policy | app config | missing |
| I12 | Upload tests | API tests for file upload validation, authz, and serving | `tests/` | missing |

---

## Dependencies

| # | Dependency | Version | Status |
|---|---|---|---|
| D1 | Flask | 2.3.3 | present |
| D2 | Flask-SQLAlchemy | 3.0.5 | present |
| D3 | Flask-SocketIO | 5.3.6 | present |
| D4 | Flask-JWT-Extended | 4.5.2 | present |
| D5 | Flask-Limiter | 3.5.0 | present |
| D6 | Local/Cloud file storage abstraction | unknown | missing |
| D7 | Image validation/inspection (Pillow or equivalent) | unknown | missing |
| D8 | Alembic migration workflow for schema evolution | partial (migrations folder minimal) | unclear |

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Without upload API, DM workflow depends on externally hosted URLs and blocks practical map/token onboarding. | `high` | yes |
| R2 | Current model stores only URL strings; no canonical asset ownership/scope prevents reliable lifecycle and cleanup. | `high` | yes |
| R3 | No explicit file validation (mime/size/image sanity) creates abuse and stability risk once upload is added quickly without guardrails. | `high` | yes |
| R4 | Campaign detail UI does not surface map workflows, so even existing map API capability remains low-visibility for users. | `medium` | yes |
| R5 | Legacy runtime module may confuse operational flow if referenced accidentally; risk of dual API behavior. | `medium` | no |
| R6 | Assumption: first release can use local filesystem storage, with future swap to object storage. | `low` | no |
| R7 | Assumption: map uploads are DM-only; token uploads are DM or owner-scoped. | `medium` | yes |

---

## Open Questions

| # | Question | Priority | Owner |
|---|---|---|---|
| Q1 | Storage target for MVP upload: local disk only or S3-compatible from day one? | blocking | Product + Backend |
| Q2 | Maximum file size limits for map and token uploads (separate caps)? | blocking | Product + Ops |
| Q3 | Should player token uploads be allowed directly, or only DM-approved library items? | blocking | Product + Game Design |
| Q4 | Do we require image dimension normalization (for token circles/squares) at upload time? | important | Backend |
| Q5 | Should assets be global user library + campaign references, or campaign-only storage for M16? | important | Product + Backend |

---

## Next Step

Start APPLY for M16 with a concrete delivery slice: authenticated asset upload API + session/campaign integration + minimal map/token upload UI + test coverage for authz/validation/session scoping.

