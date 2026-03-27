# M11 Apply Output: Hardening, Performance, Monitoring

```
artifact: apply-output
milestone: M11
phase: APPLY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Discover baseline:
  - `milestone_m11_discover_output.md`
- Human approval:
  - `Approved: M11 - M14` (batch approval)
- Scope:
  - reliability hardening
  - observability uplift
  - performance/readiness validation improvements

---

## Recommended Decision Set

1. **Runtime-debt first:** remove hot-path `Query.get` + `datetime.utcnow` usage in core modules before adding new instrumentation.
2. **Low-cardinality observability:** introduce request and socket metrics with bounded label sets only.
3. **Correlation baseline:** enforce `request_id` log propagation and response header for end-to-end tracing.
4. **Hot-path DB cleanup:** remove per-request role initialization checks from request lifecycle.
5. **Reality-based validation:** upgrade load + CI checks from health-only toward gameplay runtime paths.

---

## Scope and Work Tracks

### Track A: Runtime Hardening

- Replace runtime `Query.get` calls with `db.session.get` in:
  - `auth`, `campaigns`, `characters`, `community`, `socket_handlers`
- Replace runtime `datetime.utcnow` use with timezone-safe helper in:
  - logging, play/session transitions, ops, moderation/combat timestamps
- Keep test-only debt out of M11 critical path unless needed for test stability.

### Track B: Observability v2

- Add request correlation middleware:
  - incoming `X-Request-ID` passthrough or generated UUID
  - expose request id via response header
- Add structured request completion logs:
  - `request_id`, method, route, status, duration_ms, user_id (if available)
- Extend metrics:
  - request latency buckets
  - request counters by normalized route key (no raw-ID path labels)
  - socket event counters (`session_join`, `rejoin`, `state_error`, `action_executed`, `dice_rolled`)

### Track C: Performance and Validation

- Move role seeding out of `before_request` path.
- Expand `ops/load/k6_smoke.js` with basic play-flow calls:
  - auth/check
  - play bootstrap
  - ready-check (read-only path)
- Add CI browser smoke:
  - headless open/login/campaign-to-play bootstrap validation.

---

## Implementation Order (Deploy Plan)

1. Track A hardening changes + targeted tests.
2. Track B instrumentation + metrics/log tests.
3. Track C load/CI updates + smoke validation.
4. Full regression + artifact packaging.

---

## Planned Deploy Artifacts

- `vtt_app/__init__.py`
- `app.py`
- `vtt_app/ops/routes.py`
- `vtt_app/socket_handlers.py`
- `vtt_app/auth/routes.py`
- `vtt_app/campaigns/routes.py`
- `vtt_app/characters/routes.py`
- `vtt_app/community/routes.py`
- `vtt_app/community/service.py`
- `vtt_app/play/routes.py`
- `vtt_app/play/service.py`
- `vtt_app/play/actions.py`
- `ops/load/k6_smoke.js`
- `.github/workflows/ci.yml`
- `tests/test_ops_endpoints.py` (extend)
- new observability-focused tests (M11)
- `milestone_m11_deploy_output.md`

---

## Acceptance Criteria for M11 Deploy

- AC-M11-01: full regression remains green.
- AC-M11-02: runtime `Query.get` usage eliminated in core request/socket paths.
- AC-M11-03: runtime timestamps use timezone-safe pattern in updated modules.
- AC-M11-04: each request emits correlation id and completion log line.
- AC-M11-05: `/metrics` includes latency + normalized route counters.
- AC-M11-06: socket metrics include join/rejoin/error/action/dice series.
- AC-M11-07: no per-request role-seed DB query in request path.
- AC-M11-08: load script includes at least one `/api/play` contract check.
- AC-M11-09: CI adds browser smoke baseline (or explicit gated job).

---

## Risks and Guardrails

| # | Risk | Mitigation |
|---|---|---|
| R1 | Broad timestamp/API edits can create regressions | apply module-by-module + run focused suites first |
| R2 | Metrics cardinality explosion | enforce normalized labels and fixed event taxonomy |
| R3 | CI runtime increase from browser checks | isolate as smoke job and keep scenario minimal |

---

## Next Step

Start **M11 Deploy** with the three-track order above and run targeted + full regression verification before closeout.
