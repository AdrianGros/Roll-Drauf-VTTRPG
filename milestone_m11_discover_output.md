# M11 Discover Output: Hardening, Performance, Monitoring

```
artifact: discover-output
milestone: M11
phase: DISCOVER
status: complete
date: 2026-03-26
```

---

## Input Summary

- Human approval:
  - `APPROVED: M11 Discover`
- Baseline:
  - M10 deploy/monitor completed and green
  - full suite currently stable
- Focus:
  - runtime hardening
  - observability depth
  - performance readiness toward MVP load targets

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m11_discover_output.md` | M11 hardening/perf/monitor discover baseline | `immutable` after phase close | active draft in this turn |

---

## Current-State Snapshot

- Functional baseline is healthy:
  - `.\.venv\Scripts\python -m pytest -q` -> `110 passed`
  - M10 suites -> `19 passed`
- Warning pressure is high:
  - full run reports `2749 warnings`
- Deprecation debt (measured):
  - `datetime.utcnow(` occurrences:
    - `vtt_app`: `43`
    - `tests`: `75`
  - `Query.get()` / `.query.get()` occurrences:
    - `vtt_app`: `27`
    - `tests`: `3`
- Observability is minimal:
  - `/metrics` exposes request totals + status/path counters only
  - no request correlation fields (`request_id`, `trace_id`) found in app code
  - no dedicated Socket.IO telemetry endpoint/series
- CI/automation gaps:
  - no browser automation in CI (`playwright`/`selenium`/`cypress` not present)
  - load script exists (`ops/load/k6_smoke.js`) but checks only health endpoints
- Runtime capacity risk:
  - production config currently `gunicorn` with `workers=1`, `worker_class=eventlet`

---

## Key Discover Findings

### F1 — Warning debt is now operationally relevant

The warning volume is high enough to mask real regressions and reduce signal quality in monitor phases.

Primary sources:

- timezone deprecations (`datetime.utcnow`)
- SQLAlchemy legacy API (`Query.get`)
- relationship overlap warnings from campaign/game-session/member mappings

### F2 — Request-level observability is insufficient for live incident triage

Current JSON logs include only:

- `timestamp`
- `level`
- `logger`
- `message`

Missing:

- request id / correlation id
- user id (where available)
- route template and latency
- socket event metrics and error rates

### F3 — Metrics cardinality and depth need hardening

`/metrics` currently stores by raw path (`request.path`), which can become high-cardinality under dynamic IDs.
No histograms/counters for:

- request latency buckets
- auth failures by endpoint
- socket event rates/errors
- play mode transition outcomes

### F4 — Avoidable request-time overhead exists in hot path

`app.py` performs role-initialization check in `@before_request`:

- `Role.query.first()` runs at request time.

This creates unnecessary DB load on every request.

### F5 — Load-readiness validation does not yet cover gameplay behavior

Current k6 smoke script validates only:

- `/health/live`
- `/health/ready`

No load scenario currently exercises:

- `/api/play/bootstrap`
- session transitions
- token/action endpoints
- socket join/rejoin behavior under concurrency

### F6 — CI coverage misses browser runtime regressions

M10 introduced significant frontend runtime logic (`play.html`, `play-ui.js`), but CI has no browser-level checks for:

- page boot sequence
- runtime control wiring
- websocket reconnect UX

---

## Consolidated Decision Log (M11)

| ID | Decision | Consequence | Risk if Deferred |
|---|---|---|---|
| D1 | Introduce timezone-safe time utility and replace `datetime.utcnow` in app runtime first | lower warning noise + future compatibility | hidden time-related breakage later |
| D2 | Replace `Query.get` with `db.session.get` in runtime code paths first | removes SQLAlchemy 2.x legacy usage in core flows | growing legacy lock-in |
| D3 | Add request correlation (`request_id`) and structured request completion logs | actionable production debugging | poor incident traceability |
| D4 | Expand metrics with low-cardinality route labels + latency buckets | meaningful SLO monitoring | blind spots in latency/error spikes |
| D5 | Add Socket.IO telemetry counters (join, reconnect, error, event fail) | visibility into live-session health | undetected realtime degradation |
| D6 | Remove per-request role-seed DB check from hot path | lower per-request overhead | unnecessary DB load under concurrency |
| D7 | Add gameplay-aware load profile (play bootstrap + transitions + action endpoints) | realistic capacity validation | false confidence from health-only load |
| D8 | Add minimal CI browser smoke for `/campaigns` -> `/play` path | protects live UX contracts | frontend regressions pass unnoticed |

---

## M11 Apply Scope Proposal

### Track A: Runtime Debt Burn-Down (high impact, low product risk)

- replace runtime `datetime.utcnow` usage
- replace runtime `Query.get` usage
- reduce top SQLAlchemy overlap warnings in core models

### Track B: Observability Foundation v2

- request id middleware + response header propagation
- structured request-end log line (`method`, route, status, duration_ms, request_id, user_id when known)
- `/metrics` enhancement:
  - low-cardinality route key
  - latency histogram-style buckets
  - play/session transition counters
  - socket event counters

### Track C: Performance Validation Surface

- remove `before_request` role-check pattern in `app.py`
- add gameplay-oriented load script (REST first, socket second if feasible)
- add CI browser smoke (headless) for `/play` bootstrap path

---

## Acceptance Targets for M11 Deploy (Draft)

- AC-M11-01: full suite still green after hardening changes.
- AC-M11-02: runtime `datetime.utcnow` usage reduced to near-zero in `vtt_app` (or centrally wrapped).
- AC-M11-03: runtime `Query.get` removed from hot paths (`auth`, `campaigns`, `play`, `socket`, `community`, `characters`).
- AC-M11-04: each HTTP request emits correlation-aware structured completion log.
- AC-M11-05: `/metrics` includes low-cardinality route series and latency series.
- AC-M11-06: socket telemetry counters visible via metrics.
- AC-M11-07: no per-request role-seed DB query in request pipeline.
- AC-M11-08: load script includes at least one `/api/play` user-flow scenario.
- AC-M11-09: CI includes at least one automated browser smoke for `/play`.

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Broad timestamp/API migration can touch many files and create merge risk. | `medium` | yes |
| R2 | Over-instrumentation can increase metric cardinality and runtime cost if not bounded. | `medium` | yes |
| R3 | Browser automation toolchain setup (Playwright) adds CI runtime and maintenance cost. | `low` | no |
| R4 | Socket telemetry depth may require staged rollout to avoid noisy dashboards. | `low` | no |

Assumption A1: M11 prioritizes reliability/observability over new gameplay features.  
Assumption A2: M11 keeps scope to hardening + monitoring, not feature expansion.

---

## Next Step

Proceed to **M11 Apply**:

1. finalize implementation plan by track (A/B/C),
2. lock change order to minimize regression risk,
3. define exact metrics/log schema and CI additions before coding.
