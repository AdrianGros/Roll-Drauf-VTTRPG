# M7 Monitor Output: Community and Moderation Validation

```
artifact: monitor-output
milestone: M7
phase: MONITOR
status: complete
date: 2026-03-26
```

---

## Input Summary

- Deployment baseline:
  - `milestone_m7_deploy_output.md`
- Scope monitored:
  - chat/report/moderation API behavior
  - community realtime room isolation and moderation channel fanout
  - security and resilience guardrails (auth + rate-limit presence)
  - regression impact on M3-M6 modules

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m7_monitor_output.md` | M7 validation record and close recommendation | `immutable` after phase close | active draft in this turn |

---

## Validation Results

### Test suites

- `.\.venv\Scripts\python -m pytest tests/test_chat_api.py tests/test_reports_api.py tests/test_moderation_actions.py tests/test_community_realtime.py -q`
  - `14 passed`
- `.\.venv\Scripts\python -m pytest tests/test_auth.py tests/test_campaigns.py tests/test_characters.py tests/test_combat_api.py tests/test_tokens_realtime.py -q`
  - `60 passed`

### Endpoint / contract checks

Community route surface in `vtt_app/community/routes.py`:

- chat:
  - `GET /chat/messages`
  - `POST /chat/messages`
  - `PATCH /chat/messages/<id>`
  - `DELETE /chat/messages/<id>`
- reporting:
  - `POST /reports`
  - `GET /reports`
  - `POST /reports/<id>/assign`
  - `POST /reports/<id>/resolve`
- moderation:
  - `POST /moderation/actions`
  - `GET /moderation/actions`
  - `POST /moderation/actions/<id>/revoke`
- voice readiness:
  - `GET /voice/config`

App registration check:

- `community_bp` is registered in `vtt_app/__init__.py` under `/api`.

### Access-control smoke checks

Verified with unauthenticated client:

- `GET /api/campaigns/1/sessions/1/chat/messages` -> `401`
- `POST /api/campaigns/1/sessions/1/chat/messages` -> `401`
- `POST /api/campaigns/1/sessions/1/reports` -> `401`
- `GET /api/campaigns/1/reports` -> `401`
- `POST /api/campaigns/1/moderation/actions` -> `401`
- `GET /api/campaigns/1/sessions/1/voice/config` -> `401`

### Realtime/QoS checks

- Community event emissions are room-scoped:
  - `chat:message_created`
  - `moderation:report_created`
- Moderator room flow exists:
  - `mod:join`, `mod:leave`
- `roll_dice` no longer uses global `broadcast=True` in active handler path (`vtt_app/socket_handlers.py`).
- Community rate-limit guards are present on mutating moderation/chat/report endpoints in `vtt_app/community/routes.py`.

---

## Findings

- M7 community scope is functionally complete and test-backed.
- DM/Admin moderation boundaries are enforced as designed (including admin-only `ban` path).
- Realtime community fanout is isolated to authorized campaign/session (and mod) rooms.
- Critical unauthenticated access paths return `401` as expected.
- No regressions detected in monitored M3-M6 suites.

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | `moderation_actions` and `moderation_reports` create an FK cycle that triggers SQLite drop-order warnings in tests. | `medium` | accepted |
| R2 | Legacy module `vtt_app/sockets.py` still contains global `broadcast=True` patterns, though not active in app factory wiring. | `medium` | no |
| R3 | Existing repo-wide technical-debt warnings (`Query.get()`, `datetime.utcnow()`) remain. | `medium` | accepted |
| R4 | Rate limiter backend remains `memory://`, limiting multi-process abuse resistance until infra hardening milestone. | `medium` | accepted |
| R5 | Full voice signaling remains intentionally deferred (M7.1/M8 track). | `low` | accepted |

Assumption A1: M7 acceptance prioritizes moderation-safe text community workflows over full voice stack rollout.

---

## Milestone Status

M7 is ready to close:

- Discover: complete
- Apply: complete
- Deploy: complete
- Monitor: complete

---

## Next Step

Start **M8 Discover** (Production Readiness):

1. inventory deployment, backup, observability, and policy gaps,
2. assess scale-readiness for 200 users / 40 campaigns target,
3. define production hardening boundary for M8 Apply.
