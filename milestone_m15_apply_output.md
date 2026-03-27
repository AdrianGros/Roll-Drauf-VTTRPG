# M15 Apply Output: MVP Launch Handover and Operating Playbook

```
artifact: apply-output
milestone: M15
phase: APPLY
status: complete
date: 2026-03-27
```

---

## Chosen Implementation

1. Create `ops/monitor/mvp_rehearsal.py` as orchestration entrypoint.
2. Runner executes:
   - `release_gate_evidence.py`
   - targeted regression (`test_ops_endpoints.py`, `test_play_rejoin_socket.py`)
3. Runner supports optional steps:
   - `RUN_BROWSER_SMOKE=1`
   - `RUN_FULL_REGRESSION=1`
4. Runner writes consolidated JSON report with per-step pass/fail and output tails.
5. Update docs and milestone plan so the operational method is explicit.

