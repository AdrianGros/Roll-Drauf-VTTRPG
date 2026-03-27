# M12 Deploy Output: Play UX and Operator Ergonomics

```
artifact: deploy-output
milestone: M12
phase: DEPLOY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Apply baseline:
  - `milestone_m12_apply_output.md`
- Deploy scope:
  - simplify `/play` controls
  - improve role/state affordances
  - reduce action execution friction

---

## Implementation Summary

### Play shell restructuring (`play.html`)

- Split controls into logical groups:
  - Navigation
  - Setup Controls
  - Session Lifecycle
- Added explicit read-only notice surface.
- Added persistent `Activity Feed` panel.
- Reworked action form inputs:
  - actor token select
  - target token select
- Improved presentation blocks for ready-check status.

### Runtime UI behavior upgrade (`play-ui.js`)

- Added role helpers and operator checks.
- Implemented control-state gating matrix:
  - enables/disables lifecycle actions by role + runtime status.
- Added structured ready-check rendering:
  - blockers and warnings shown as separate sections.
- Switched action flow from manual id typing to token selectors.
- Added persistent activity logging for:
  - transitions
  - action execution events
  - dice broadcasts
  - user/system messages
- Added read-only notice behavior and stronger inline validation.

### Architecture guardrail

- No backend API contract changes.
- Existing `/api/play` endpoints remain the single source of truth.

---

## Files Changed

- `vtt_app/templates/play.html`
- `vtt_app/static/js/play-ui.js`
- `milestone_m12_deploy_output.md` (new)

---

## Proofs

Executed command:

`.\.venv\Scripts\python -m pytest tests/test_play_bootstrap_api.py tests/test_play_permissions.py tests/test_ready_check.py tests/test_play_rejoin_socket.py tests/test_ops_endpoints.py -q`

Result:

- `15 passed`

Executed command:

`.\.venv\Scripts\python -m pytest -q`

Result:

- `112 passed`

---

## Acceptance Checklist

- [x] AC-M12-01: controls are grouped and state-aware.
- [x] AC-M12-02: read-only and role limits are explicit in UI.
- [x] AC-M12-03: action execution now uses token selectors.
- [x] AC-M12-04: ready-check output is structured for decision speed.
- [x] AC-M12-05: activity feed captures key session/runtime events.
- [x] AC-M12-06: full regression remains green.

---

## Risks and Follow-up

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Browser-level UX assertions are still mostly CI smoke + manual behavior checks. | low | no |
| R2 | Activity feed is in-memory client state and does not persist across full reload. | low | no |
| R3 | Remaining warning debt is mostly tests + mapper overlaps, not this deploy. | medium | no |

---

## Next Step

Proceed to **M12 Monitor**:

1. run live-flow browser check focused on new control gating and activity feed,
2. collect operator usability evidence,
3. lock M12 closure and advance to M13 resilience cycle.
