# M13 Deploy Output: Realtime Resilience and Sync Robustness

```
artifact: deploy-output
milestone: M13
phase: DEPLOY
status: complete
date: 2026-03-27
```

---

## Scope Delivered

- Hardened socket mutation contract:
  - `token:update` now requires `base_version`
  - `token:delete` now requires `base_version`
  - socket mutation events require `client_event_id`
- Added replay/idempotency guard for duplicate client mutation events.
- Added per-session realtime sequencing envelope (`event_seq`, `server_time`, `campaign_id`, `session_id`) for state-changing emits.
- Added room-safety behavior on `session:join` (leave prior play-session room before joining a new one).
- Added resilience metrics:
  - `vtt_socket_conflicts_total`
  - `vtt_socket_resync_requests_total`
  - `vtt_socket_reconnect_recoveries_total`
- Updated frontend socket runtime with stale-event drop and gap-triggered resync request behavior.
- Added targeted resilience tests for:
  - missing `base_version` rejection
  - duplicate `client_event_id` dedupe
  - session room switch isolation

---

## Primary Implementation Areas

- `vtt_app/socket_handlers.py`
- `vtt_app/play/routes.py`
- `vtt_app/campaigns/routes.py`
- `vtt_app/utils/realtime.py`
- `vtt_app/static/js/play-socket.js`
- `vtt_app/static/js/play-ui.js`
- `vtt_app/ops/routes.py`
- `vtt_app/__init__.py`
- `tests/test_tokens_realtime.py`
- `tests/test_play_rejoin_socket.py`
- `tests/test_ops_endpoints.py`

---

## Acceptance Criteria Check

- AC-M13-01: enforced optimistic concurrency on socket token mutate paths -> **met**
- AC-M13-02: duplicate client mutation dedupe contract -> **met**
- AC-M13-03: deterministic sequencing metadata on realtime state events -> **met**
- AC-M13-04: resync path on gap/conflict foundation in place -> **met**
- AC-M13-05: repeated join room isolation behavior -> **met**
- AC-M13-06: resilience counters exposed in `/metrics` -> **met**
- AC-M13-07: targeted tests green -> **met**

---

## Known Residual Debt

- Dedupe cache is in-memory (process-local) and not durable across restarts.
- Stale-drop metric is not yet exported as a first-class backend counter.
- Existing SQLAlchemy/deprecation warnings remain and are tracked separately from M13 scope.

