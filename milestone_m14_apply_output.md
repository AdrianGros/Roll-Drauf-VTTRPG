# M14 Apply Output: Scale Readiness and Release Gate

```
artifact: apply-output
milestone: M14
phase: APPLY
status: complete
date: 2026-03-27
```

---

## Chosen Architecture

1. **Release gate endpoint**
   - Add `GET /health/release` with explicit `go`/`no-go` status.
   - Return detailed per-check diagnostics (`checks.*`).

2. **Configurable thresholds**
   - Add release-gate config keys in `vtt_app/config.py`:
     - `RELEASE_GATE_MIN_UPTIME_SECONDS`
     - `RELEASE_GATE_MIN_REQUESTS`
     - `RELEASE_GATE_MAX_5XX_RATE`
     - `RELEASE_GATE_MAX_SLOW_REQUEST_RATE`
     - `RELEASE_GATE_MAX_SOCKET_RESYNC_RATE`
     - `RELEASE_GATE_MAX_SOCKET_CONFLICT_RATE`
     - `RELEASE_GATE_REQUIRE_RUNBOOKS`
     - `RELEASE_GATE_REQUIRED_FILES`

3. **Rollback readiness check**
   - If enabled, verify required runbooks/scripts exist in repo.

4. **Evidence automation**
   - Add `ops/monitor/release_gate_evidence.py` to capture health + metrics + release gate evidence into JSON artifact.

5. **Verification**
   - Extend `tests/test_ops_endpoints.py` for:
     - release gate success
     - error-budget failure
     - missing-runbook failure

