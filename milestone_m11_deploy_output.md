# M11 Deploy Output: Hardening, Performance, Monitoring

```
artifact: deploy-output
milestone: M11
phase: DEPLOY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Baseline:
  - `milestone_m11_discover_output.md`
  - `milestone_m11_apply_output.md`
- Human approval:
  - `Approved: M11 - M14`
- Deploy scope:
  - runtime debt burn-down
  - observability v2 uplift
  - load/CI validation hardening

---

## Implementation Summary

### Track A: Runtime hardening

- Removed runtime legacy patterns in app code:
  - `.query.get()` / `Query.get()` -> `db.session.get(...)` on core runtime paths.
  - `datetime.utcnow()` removed from `vtt_app` runtime modules in favor of shared `utcnow()`.
- Introduced shared UTC helper:
  - `vtt_app/utils/time.py` (`utcnow()`).
- Extended utcnow migration into core model/service runtime hotspots:
  - user/session/session_state/game_session/campaign_member/invite/mfa/combat runtime paths.

### Track B: Observability v2

- Added request correlation and completion logging:
  - incoming `X-Request-ID` passthrough or generated UUID.
  - response header propagation via `X-Request-ID`.
  - structured completion log fields: `request_id`, `method`, `path`, `route`, `status_code`, `duration_ms`.
- Expanded metrics store and `/metrics` output with:
  - `vtt_requests_by_route_total`
  - `vtt_request_latency_bucket_total`
  - `vtt_socket_events_total`
  - `vtt_socket_events_by_name_total`
  - `vtt_play_transitions_total`
  - `vtt_play_transitions_by_target_total`
- Added socket metric increments and play-transition metric increments in runtime handlers.

### Track C: Performance and validation

- Removed per-request role-seeding query from request path:
  - moved role init to startup-only in `app.py`.
- Upgraded load script:
  - `ops/load/k6_smoke.js` now covers health + auth-check + `/api/play` contract checks.
- Added CI browser smoke pipeline:
  - new `browser-smoke` job in `.github/workflows/ci.yml`
  - Playwright Chromium install + app boot + smoke execution.
- Added browser smoke script:
  - `ops/monitor/browser_smoke.py` covering `/login.html`, `/campaigns.html`, `/play?...`.

### Test coverage uplift

- Extended ops tests:
  - request-id passthrough + auto-generation assertions.
  - metrics assertions for new M11 series and normalized route metric output.

---

## Files Changed

- `.github/workflows/ci.yml`
- `ops/load/k6_smoke.js`
- `ops/monitor/browser_smoke.py` (new)
- `tests/test_ops_endpoints.py`
- `vtt_app/config.py`
- `vtt_app/combat/service.py`
- `vtt_app/models/user.py`
- `vtt_app/models/session_state.py`
- `vtt_app/models/game_session.py`
- `vtt_app/models/campaign_member.py`
- `vtt_app/models/session.py`
- `vtt_app/models/invite_token.py`
- `vtt_app/models/mfa_backup_code.py`
- `milestone_m11_deploy_output.md` (new)

---

## Proofs

Executed command:

`.\.venv\Scripts\python -m pytest tests/test_ops_endpoints.py tests/test_auth.py tests/test_campaigns.py tests/test_combat_api.py -q`

Result:

- `42 passed`

Executed command:

`.\.venv\Scripts\python -m pytest -q`

Result:

- `112 passed`
- warnings reduced from M11 discover baseline (`2749`) to current (`981`)

Runtime debt checks:

- `rg "datetime\.utcnow\(" vtt_app -n` -> no matches
- `rg "\.query\.get\(|Query\.get\(" vtt_app -n` -> no matches

---

## Acceptance Checklist

- [x] AC-M11-01: full regression remains green.
- [x] AC-M11-02: runtime `Query.get` usage eliminated in core request/socket paths.
- [x] AC-M11-03: runtime timestamps in updated modules use timezone-safe helper.
- [x] AC-M11-04: request correlation id propagated and completion log emitted.
- [x] AC-M11-05: `/metrics` exposes latency + normalized route counters.
- [x] AC-M11-06: socket + play transition metric series present.
- [x] AC-M11-07: no per-request role-seed DB query in request path.
- [x] AC-M11-08: load script includes `/api/play` contract checks.
- [x] AC-M11-09: CI includes browser smoke baseline job.

---

## Risks and Follow-up

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Remaining warning volume is still substantial, but now dominated by tests + mapper overlap warnings. | medium | no |
| R2 | Browser smoke job is added in CI, but local workstation currently has no Playwright package installed. | low | no |
| R3 | SQLAlchemy relationship-overlap warnings should be addressed explicitly in model relationship config (future debt item). | medium | no |

---

## Next Step

Proceed to **M11 Monitor**:

1. evidence-run for correlation + metrics behavior,
2. verify stable regression signal after hardening rollout,
3. close M11 and start M12 UX/operator discover.
