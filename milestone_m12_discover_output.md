# M12 Discover Output: Session UX and Operator Ergonomics

```
artifact: discover-output
milestone: M12
phase: DISCOVER
status: complete
date: 2026-03-26
```

---

## Input Summary

- Baseline:
  - `milestone_m10_monitor_output.md`
  - `milestone_m11_monitor_output.md`
- Human approval:
  - `Approved: M11 - M14` (batch)
- Discover focus:
  - DM/player cockpit friction
  - state clarity and control ergonomics
  - low-risk UX improvements for next deploy cycle

---

## Artifacts Reviewed

- `vtt_app/templates/play.html`
- `vtt_app/static/js/play-ui.js`
- `vtt_app/static/js/play-client.js`
- `vtt_app/static/js/play-socket.js`
- `tests/test_play_permissions.py`
- `tests/test_ready_check.py`

---

## Key Discover Findings

### F1 - Control surface overload on first paint

Current `/play` presents many controls in one undifferentiated row:

- `Init Scene Stack`
- `Ready Check`
- `Set Ready`
- `Start Live`
- `Pause`
- `Resume`
- `End Session`

Impact:

- high operator cognitive load
- no progressive disclosure by session phase

### F2 - State and permission affordances are too subtle

Role/mode/read-only are shown as badges, but controls remain visually similar.

Impact:

- users can attempt invalid actions and only learn via runtime errors
- read-only states feel ambiguous for players/observers

### F3 - Action execution flow is operator-centric, not player-centric

Action bar currently requires manual numeric IDs:

- `token_id`
- optional `target_token_id`

Impact:

- high friction for players
- error-prone input model
- slower table flow during combat pressure

### F4 - Ready-check output is technically correct but hard to parse quickly

Ready-check output is textual and packed into one block.

Impact:

- blockers/warnings are not visually prioritized
- DM decisions during start flow are slower than necessary

### F5 - Transient feedback can hide important information

Messages auto-dismiss after 3.5s and there is no persistent timeline panel.

Impact:

- important operation feedback can be missed
- weak post-action explainability in live sessions

### F6 - Scene/token areas lack quick filter/navigation helpers

Scene layer list and token list are present, but no fast filtering/pinning/scope view.

Impact:

- DM scanning time rises with map/token count
- hard to run fast multi-step actions under load

---

## Consolidated Decision Log (M12 Discover)

| ID | Decision | Consequence | Risk if Deferred |
|---|---|---|---|
| D1 | Introduce phase-aware control groups (setup/live/end) | reduces visual overload and misclicks | growing operator fatigue |
| D2 | Enforce UI-level action gating by mode/role/read-only | fewer invalid requests and cleaner UX | continued error-driven interaction |
| D3 | Replace manual token-id inputs with guided selectors | faster and safer action execution | persistent player friction |
| D4 | Convert ready-check to structured cards (blocking vs warning) | faster start decisions | startup hesitation and missed blockers |
| D5 | Add persistent event/activity rail in play UI | stronger feedback and troubleshooting | invisible transient failures |
| D6 | Keep backend contracts stable in M12 where possible | lower regression risk, faster rollout | unnecessary backend scope growth |

---

## M12 Apply Scope Proposal

### Track A - DM cockpit simplification

- group controls by session phase
- disable/hide impossible transitions
- keep destructive controls visually separated

### Track B - Player action ergonomics

- token selector with ownership-aware defaults
- target selector from visible session tokens
- clearer inline validation before API call

### Track C - Feedback clarity

- ready-check structured presentation
- persistent activity log panel (state/action/dice/error)
- explicit read-only banner when interaction is blocked

---

## Acceptance Targets for M12 Deploy (Draft)

- AC-M12-01: mode/role/read-only gating reflected directly in control availability.
- AC-M12-02: action flow no longer requires raw numeric IDs as primary UX path.
- AC-M12-03: ready-check output clearly separates blockers and warnings.
- AC-M12-04: operator receives persistent, non-ephemeral action/session feedback.
- AC-M12-05: full regression remains green after UX changes.

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Frontend UX changes can create regressions in event binding/state refresh flows. | medium | yes |
| R2 | Over-polish risk: M12 may drift beyond ergonomic core into redesign scope. | medium | yes |
| R3 | Without lightweight browser checks locally, some UX regressions may surface later. | low | no |

Assumption A1: M12 prioritizes usability gains without altering core play domain contracts.  
Assumption A2: Existing `/api/play` endpoints remain primary integration surface.

---

## Next Step

Proceed to **M12 Apply**:

1. lock minimal UI change set with highest friction payoff,
2. map each UI improvement to existing API contracts,
3. define focused tests for gating and action-flow behavior.
