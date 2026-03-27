# M11 Monitor Output: Correlation, Metrics, and Regression Stability

```
artifact: monitor-output
milestone: M11
phase: MONITOR
status: complete
date: 2026-03-26
```

---

## Input Summary

- Deployment baseline:
  - `milestone_m11_deploy_output.md`
- Monitored scope:
  - request-id correlation behavior
  - new metrics series visibility
  - regression quality and warning pressure
  - readiness for transition into M12 UX cycle

---

## Evidence Run

### 1) Regression integrity

Executed:

`.\.venv\Scripts\python -m pytest -q`

Result:

- `112 passed`
- `981 warnings`

Interpretation:

- functional baseline remains stable after M11 hardening.
- warning signal quality improved versus M11 discover baseline (`2749` -> `981`).

### 2) Correlation + metrics evidence

Executed local evidence script against testing app:

- `/health/live` with `X-Request-ID: evidence-m11`
- `/api/auth/check`
- `/metrics`

Observed outputs:

- `header_request_id evidence-m11` (passthrough confirmed)
- `vtt_requests_by_route_total True`
- `vtt_request_latency_bucket_total True`
- `vtt_socket_events_total True`
- `vtt_play_transitions_total True`
- `route_live_metric True`

Additional runtime log evidence captured:

- structured `http.request` log lines include:
  - `request_id`
  - `method`
  - `path`
  - `route`
  - `status_code`
  - `duration_ms`

### 3) CI/browser monitor readiness

- Browser smoke job present in CI:
  - installs Playwright + Chromium
  - starts app in testing mode
  - runs `ops/monitor/browser_smoke.py`
- Local browser smoke execution was not run because `playwright` is not installed in local `.venv`.
- Script syntax was validated locally:
  - `python -m py_compile ops/monitor/browser_smoke.py` (pass)

---

## Findings

- M11 objectives are met for runtime hardening and observability baseline.
- Correlation and metrics are now actionable for incident triage.
- Regression quality gate remains green after changes.
- Remaining warning debt is now concentrated in:
  - test fixtures still using `datetime.utcnow`
  - SQLAlchemy relationship overlap warnings
  - legacy `.query.get` usage in a few tests

---

## Risk Register

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Mapper overlap warnings can mask new warnings in CI logs. | medium | no |
| R2 | Browser smoke confidence in local dev still depends on optional Playwright install. | low | no |
| R3 | Warning backlog in test fixtures may hide future deprecations if left unattended. | medium | no |

---

## Milestone Status

M11 is ready to close:

- Discover: complete
- Apply: complete
- Deploy: complete
- Monitor: complete

---

## Next Step

Start **M12 Discover** focused on operator ergonomics:

1. reduce DM click-path and control overload in `/play`,
2. improve state clarity/read-only affordances for all roles,
3. define minimal UX upgrades with low backend risk for M12 Apply.
