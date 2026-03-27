# M7 Deploy Output: Community and Moderation Stack

```
artifact: deploy-output
milestone: M7
phase: DEPLOY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Approved design baseline:
  - `milestone_m7_apply_output.md`
- Human approval:
  - `APPROVED: M7 Deploy`
- Deployment scope:
  - session chat persistence + API
  - reporting + moderation action workflows
  - role/policy enforcement (Player, DM, Admin)
  - room-scoped community/moderation realtime fanout
  - global social broadcast leak fix
  - minimal campaign UI integration for chat/report/moderation
  - M7 test coverage + regression verification

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m7_deploy_output.md` | M7 deployment execution + proof record | `immutable` after phase close | active draft in this turn |

---

## Implementation Summary

Implemented M7 community/moderation foundation end-to-end:

- Added new persisted community domain entities:
  - `ChatMessage` (session-scoped chat persistence, idempotency token, moderation state, soft-delete metadata)
  - `ModerationReport` (report intake + triage state)
  - `ModerationAction` (append-only action ledger with active/revoked lifecycle)
- Added dedicated community module:
  - `vtt_app/community/policy.py` for role/authority checks
  - `vtt_app/community/service.py` for chat/report/action rules and side effects
  - `vtt_app/community/routes.py` for REST API contracts
- Registered new community blueprint in app factory (`/api` namespace).
- Implemented chat endpoints:
  - list paginated messages
  - create message (idempotent retry support via `client_event_id`)
  - patch message (owner window + moderator redact)
  - soft-delete message (owner window + moderator delete)
- Implemented report workflow endpoints:
  - report creation by campaign members
  - DM/Admin queue list
  - assign and resolve transitions
- Implemented moderation endpoints:
  - create actions (`warn`, `mute`, `delete_message`, `kick`, `ban`)
  - list actions with filters
  - revoke action (ban revoke admin-only)
  - DM/Admin authority matrix enforced server-side
- Implemented voice readiness stub:
  - `GET /api/campaigns/<campaign_id>/sessions/<session_id>/voice/config`
  - feature-flag based response (`VOICE_ENABLED`, default false)
- Realtime hardening:
  - added moderator socket room flow (`mod:join`, `mod:leave`)
  - room-scoped community events (`chat:*`, `moderation:*`)
  - fixed `roll_dice` from global broadcast to campaign/session scoped emission
- UI integration:
  - added `vtt_app/static/js/community.js`
  - extended `campaigns.html` with:
    - session chat panel
    - report-on-message action
    - DM/Admin moderation quick controls and queue view

---

## Files Changed

- `vtt_app/models/chat_message.py` (new)
- `vtt_app/models/moderation_report.py` (new)
- `vtt_app/models/moderation_action.py` (new)
- `vtt_app/models/__init__.py`
- `vtt_app/community/__init__.py` (new)
- `vtt_app/community/policy.py` (new)
- `vtt_app/community/service.py` (new)
- `vtt_app/community/routes.py` (new)
- `vtt_app/__init__.py`
- `vtt_app/socket_handlers.py`
- `vtt_app/config.py`
- `vtt_app/static/js/community.js` (new)
- `vtt_app/templates/campaigns.html`
- `tests/test_chat_api.py` (new)
- `tests/test_reports_api.py` (new)
- `tests/test_moderation_actions.py` (new)
- `tests/test_community_realtime.py` (new)
- `milestone_m7_deploy_output.md` (new)

---

## Proofs

Executed command:

`.\.venv\Scripts\python -m pytest tests/test_chat_api.py tests/test_reports_api.py tests/test_moderation_actions.py tests/test_community_realtime.py -q`

Result:

- `14 passed`

Executed command:

`.\.venv\Scripts\python -m pytest tests/test_auth.py tests/test_campaigns.py tests/test_characters.py tests/test_combat_api.py tests/test_tokens_realtime.py -q`

Result:

- `60 passed`

Notes:

- Test runs report existing legacy/deprecation warnings in the repo (`Query.get()`, `datetime.utcnow()`), plus a known drop-order warning from the new moderation FK cycle in in-memory SQLite tests.

---

## Acceptance Checklist

- [x] AC-M7-01: Session chat messages persist and can be paged by authenticated campaign members.
- [x] AC-M7-02: Muted users receive `403` on chat post attempts while mute is active.
- [x] AC-M7-03: Users can submit reports with message/user targets and triage metadata is persisted.
- [x] AC-M7-04: DM/Admin can view and manage campaign report queue; players cannot.
- [x] AC-M7-05: Moderation actions are persisted with actor/subject/timestamp/audit linkage.
- [x] AC-M7-06: DM can apply warn/mute/kick/delete_message, but cannot apply `ban`.
- [x] AC-M7-07: Admin can apply and revoke `ban` actions with campaign override capability.
- [x] AC-M7-08: Chat/moderation realtime events are emitted only to authorized campaign/session rooms.
- [x] AC-M7-09: Global broadcast leakage class removed for `dice_rolled` and new community events.
- [x] AC-M7-10: M7 suites and selected core regression suites pass in local `.venv`.

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Moderation tables form an FK cycle (`moderation_actions` <-> `moderation_reports`), producing SQLite drop-order warnings in tests. | `medium` | no |
| R2 | Existing repo-wide technical debt warnings (`Query.get`, `datetime.utcnow`) remain and are outside M7 scope. | `medium` | no |
| R3 | Rate limiting still uses `memory://`, so multi-process abuse resistance is not yet production-grade. | `medium` | accepted |
| R4 | Voice is intentionally feature-flagged and deferred to M7.1 for full signaling/TURN implementation. | `low` | accepted |

Assumption A1: M7 acceptance prioritizes safe community moderation workflows over full voice rollout.

---

## Next Step

Proceed to **M7 Monitor**:

1. validate moderation UX and operator workflows in manual session runs,
2. capture moderation policy refinements (DM/Admin precedence documentation),
3. decide whether FK-cycle migration hardening is done in M7.1 or M8 infra track.
