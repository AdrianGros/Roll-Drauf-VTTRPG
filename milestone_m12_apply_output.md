# M12 Apply Output: Session UX and Operator Ergonomics

```
artifact: apply-output
milestone: M12
phase: APPLY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Discover baseline:
  - `milestone_m12_discover_output.md`
- Human approval:
  - `Approved: M11 - M14`
- Scope:
  - reduce control overload in `/play`
  - improve role/mode/read-only affordances
  - reduce action execution friction

---

## Recommended Decision Set

1. **Phase-aware controls:** separate setup vs lifecycle controls.
2. **UI-level gating:** disable impossible actions by role/mode/state before API call.
3. **Guided action selection:** token selectors instead of raw id typing.
4. **Persistent feedback:** keep transient toast plus activity feed for auditability.
5. **Low backend risk:** ship UX improvements without changing `/api/play` contracts.

---

## Scope and Work Tracks

### Track A: Cockpit simplification

- group controls into setup/lifecycle blocks
- visually isolate destructive operations
- keep navigation separate from live controls

### Track B: Interaction clarity

- explicit read-only notice banner
- stricter button disablement matrix by role/mode/state
- clearer ready-check presentation (blockers vs warnings)

### Track C: Action ergonomics

- actor/target token selectors from active state payload
- ownership-first actor token ordering
- persistent activity feed for action/state/dice feedback

---

## Implementation Order

1. template structure update (`play.html`)
2. runtime UI behavior update (`play-ui.js`)
3. regression validation (targeted play suites + full suite)
4. M12 deploy artifact generation

---

## Acceptance Criteria for M12 Deploy

- AC-M12-01: controls are grouped and state-aware.
- AC-M12-02: read-only and role limitations are visible before user interaction.
- AC-M12-03: action execution uses guided token selectors.
- AC-M12-04: ready-check output is structured and decision-friendly.
- AC-M12-05: persistent activity feed records key runtime events.
- AC-M12-06: full regression remains green.

---

## Risks and Guardrails

| # | Risk | Mitigation |
|---|---|---|
| R1 | UI gating can drift from backend transition rules | keep backend as source of truth; UI only pre-validates |
| R2 | Increased JS state logic can regress reconnect behavior | preserve bootstrap reload flow and socket callbacks |
| R3 | UX scope can expand toward redesign | keep changes to existing play shell and controls only |

---

## Next Step

Execute **M12 Deploy** with focused frontend-only changes and regression validation.
