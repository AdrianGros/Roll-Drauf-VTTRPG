# M14 Discover Output: Scale Readiness and Release Gate

```
artifact: discover-output
milestone: M14
phase: DISCOVER
status: complete
date: 2026-03-27
```

---

## Discover Focus

- Release criteria and go/no-go signal quality
- SLO-style operational thresholds for launch readiness
- Rollback readiness evidence (runbooks + scripts)

---

## Key Findings

1. Existing health model (`/health/live`, `/health/ready`) is necessary but not sufficient for release decisions.
2. `/metrics` is rich enough for threshold checks, but no consolidated release-gate endpoint existed.
3. Rollback documentation/scripts existed, but there was no machine-checkable readiness check.
4. Evidence runs were manual and fragmented across commands.

---

## Decision Set (M14)

- D1: Introduce `GET /health/release` as a consolidated go/no-go endpoint.
- D2: Drive gate checks from configurable thresholds in app config.
- D3: Include rollback/runbook file checks in release gate for production mode.
- D4: Add evidence collector script for reproducible monitor runs.
- D5: Validate with dedicated ops tests plus full regression.

---

## Risks

- Overly strict defaults could cause false no-go outcomes in non-production.
- Metrics with very low traffic can skew ratios; minimum request volume gate is needed.
- Runbook checks must be configurable to avoid local/dev friction.

