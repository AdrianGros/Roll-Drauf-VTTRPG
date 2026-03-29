# M55 Session Shell Baseline

Date: 2026-03-27
Status: draft
Basis: Roll20-like session environment baseline before enhancements

## Milestone Definition

- Goal: Rebuild the session page as a Roll20-like tabletop shell with clear spatial zones.
- Scope: header, left tool rail, central stage, right sidebar, floating widgets, responsive layout.
- Constraints: preserve existing IDs and functional entry points; no backend redesign.
- Deliverables: updated `play.html`, layout CSS/JS adjustments, tab switching, responsive behavior.
- Acceptance criteria: the page visually reads like a tabletop, not an admin form.
- Risks: layout regression, broken IDs, mobile overflow, confusing control duplication.
- Dependencies: current play runtime and existing session bootstrap.
- Priority: `P1`

## DISCOVER Prompt

```text
You are working on M55 (Session Shell Baseline) for the Roll-Drauf VTT using DADM Discover only.

Goal:
Collect facts about the current session shell and identify exactly what exists, what is missing, and what must not change.

What to inspect:
- Current `vtt_app/templates/play.html` structure
- Current `vtt_app/static/js/play-ui.js` behavior
- Current `vtt_app/static/js/play-client.js` and `play-socket.js` entry points
- Existing DOM IDs used by the runtime
- Current header, panels, buttons, and sidebar behavior
- Responsive behavior on desktop and mobile

What to produce:
- Current-state summary of the session shell
- Inventory of UI zones and controls
- Dependencies and constraints
- Risks and assumptions with severity labels
- Open questions that block safe design
- A one-line next step into Apply

Hard rules:
- Do not design a new solution yet
- Do not implement code
- Do not delete or propose replacement of existing runtime IDs without evidence
- Do not widen scope beyond the session shell

If a required fact is missing, state that clearly and mark it `unclear`.
If a high-risk finding appears, classify it and explain whether it blocks Apply.
```

## APPLY Prompt

```text
You are working on M55 (Session Shell Baseline) using DADM Apply only.

Goal:
Turn the Discover facts into a concrete session-shell design that can be implemented without ambiguity.

Design requirements:
- Header with session status badges and concise identity
- Left vertical tool rail with Roll20-like interaction affordances
- Center stage as the main tabletop area
- Right sidebar with tabbed secondary functions
- Floating widgets for map/layer, turn order, token overview
- Responsive layout for desktop and tablet
- Clear separation of primary play surface vs secondary panels

What to produce:
- Architecture overview of the page layout
- DOM/container plan
- UI interaction contract for tabs, tool selection, zoom, and panel visibility
- Mapping of existing IDs to new or preserved UI regions
- Acceptance criteria, written as measurable binary checks
- Risks and assumptions with severity labels
- Open TBDs if any design detail is still unresolved
- A one-line next step into Deploy

Hard rules:
- No implementation code
- No hidden scope expansion
- Do not invent new backend APIs
- Do not bypass unresolved medium-or-higher risks

The design should preserve current runtime compatibility while making the page feel like a real tabletop.
```

## DEPLOY Prompt

```text
You are working on M55 (Session Shell Baseline) using DADM Deploy only.

Goal:
Implement the approved session-shell design and record proof.

Implementation expectations:
- Rework `vtt_app/templates/play.html` into a Roll20-like tabletop shell
- Add or adjust CSS for the shell layout
- Add JS support for sidebar tabs and tool selection if needed
- Preserve existing functional IDs and runtime hooks
- Ensure the layout remains responsive

Do not:
- change architecture beyond the approved design
- introduce new backend behavior
- silently remove existing runtime functionality
- add unrelated visual experiments

Required output:
- Implementation summary
- Files changed
- Proofs
- Acceptance checklist
- Residual risks
- Next step

Proofs should include:
- grep or DOM presence checks for key IDs
- basic render verification or syntax verification
- any relevant smoke test results

If implementation forces a design change, stop and escalate to Apply.
```

## MONITOR Prompt

```text
You are working on M55 (Session Shell Baseline) using DADM Monitor only.

Goal:
Validate that the deployed session shell is usable and matches the approved baseline.

What to verify:
- Header renders correctly
- Left tool rail is visible and usable
- Center stage is the primary visual focus
- Right sidebar tabs switch correctly
- Floating widgets do not block core interaction
- The page is responsive enough for the target devices

What to produce:
- Validation result
- Evidence summary
- Residual findings with severity
- Recommendation: close, rework, or continue

Hard rules:
- No new feature design
- No silent fixes that should reopen Deploy
- Escalate if a critical or unresolved medium-or-higher issue remains
```
