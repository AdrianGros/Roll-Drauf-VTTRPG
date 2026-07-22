# DADM Prompt Pack: Session Baseline / Roll20-Parity

Stand: 2026-03-27

Basis:
- DADM Framework: `dadm-framework`
- Current target: Roll20-like session environment as a stable baseline before improvements
- Existing app state: authenticated VTT with campaigns, sessions, play runtime, map/layer/token groundwork

This pack is structured for approval per milestone.
Each milestone contains four phase prompts:
- `DISCOVER` = facts only
- `APPLY` = solution design only
- `DEPLOY` = implementation only, no new architecture
- `MONITOR` = validation and review only

Use each milestone as one approval unit.

---

## M55 - Session Shell Baseline

### Milestone definition

- Goal: Rebuild the session page as a Roll20-like tabletop shell with clear spatial zones.
- Scope: header, left tool rail, central stage, right sidebar, floating widgets, responsive layout.
- Constraints: preserve existing IDs and functional entry points; no backend redesign.
- Deliverables: updated `play.html`, layout CSS/JS adjustments, tab switching, responsive behavior.
- Acceptance criteria: the page visually reads like a tabletop, not an admin form.
- Risks: layout regression, broken IDs, mobile overflow, confusing control duplication.
- Dependencies: current play runtime and existing session bootstrap.
- Priority: `P1`

### DISCOVER prompt

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

### APPLY prompt

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

### DEPLOY prompt

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

### MONITOR prompt

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

---

## M56 - Map Canvas and Layer Stack

### Milestone definition

- Goal: Turn the center stage into a real tabletop map canvas with grid, zoom, layers, and token overlay.
- Scope: map rendering, grid overlay, zoom controls, active layer display, token placement rendering, map metadata.
- Constraints: preserve current session bootstrap; no new scene engine.
- Deliverables: map canvas UI, layer display, zoom mechanics, token overlay.
- Acceptance criteria: an active map is visibly playable in the session.
- Risks: broken scaling, token misalignment, weak map metadata, regression in mobile view.
- Dependencies: M55 complete.
- Priority: `P1`

### DISCOVER prompt

```text
You are working on M56 (Map Canvas and Layer Stack) using DADM Discover only.

Goal:
Collect factual information about the current map, layer, token, and bootstrap state so the map canvas can be designed safely.

Inspect:
- `vtt_app/play/service.py`
- `vtt_app/play/routes.py`
- `vtt_app/static/js/play-ui.js`
- `vtt_app/templates/play.html`
- current state payload shape from play bootstrap
- current session and map serialization

Find:
- What data already exists for active maps, layers, tokens, and dimensions
- Which fields are available for map rendering
- Which values represent grid size, width, height, background URL, and token positions
- Which interaction paths are already implemented and which are missing

Produce:
- Current-state summary
- Inventory of map/layer/token data
- Dependencies
- Risks and assumptions with severity
- Open questions blocking design
- One-line next step into Apply

Do not:
- design the canvas yet
- introduce new rendering logic
- assume token coordinate semantics without evidence
```

### APPLY prompt

```text
You are working on M56 (Map Canvas and Layer Stack) using DADM Apply only.

Goal:
Design the tabletop map canvas so the center stage supports Roll20-like play.

Design must cover:
- map image/background handling
- grid overlay
- map scaling and zoom controls
- token overlay placement
- active layer indication
- map metadata display
- how the layer widget influences the canvas

Also define:
- coordinate handling rules
- how token size should be rendered
- how the UI behaves when no map is active
- how the UI behaves when no tokens are present

Produce:
- architecture overview
- interface contract between data and canvas rendering
- token and layer rendering rules
- acceptance criteria
- risks and assumptions
- open TBDs
- next step into Deploy

Hard rules:
- No implementation
- No backend redesign
- No new game mechanics
- Keep the design compatible with existing session bootstrap data
```

### DEPLOY prompt

```text
You are working on M56 (Map Canvas and Layer Stack) using DADM Deploy only.

Goal:
Implement the approved map canvas design.

Implement:
- central map canvas rendering
- grid overlay
- zoom controls
- active map display
- layer widget rendering
- token overlay rendering
- map metadata readout

Constraints:
- Use the approved data model only
- Preserve existing runtime IDs
- Keep the canvas stable on resize
- Do not add new backend APIs unless Apply explicitly approved them

Required output:
- Implementation summary
- Files changed
- Proofs
- Acceptance checklist
- Residual risks
- Next step

Proofs should include:
- render verification
- token and layer DOM checks
- any available smoke test or screenshot evidence
```

### MONITOR prompt

```text
You are working on M56 (Map Canvas and Layer Stack) using DADM Monitor only.

Goal:
Validate the map canvas as a usable play surface.

Check:
- map is visible and centered
- zoom controls work
- layer state is readable
- token overlay appears in the right place
- no clipping or broken scrolling

Output:
- validation result
- evidence summary
- residual findings with severity
- recommendation
```

---

## M57 - Chat, Journal, Activity

### Milestone definition

- Goal: Make the right sidebar a meaningful secondary workspace for communication and context.
- Scope: chat tab, journal tab, activity log, session info, tab switching, input affordances.
- Constraints: do not break existing tools or session controls.
- Deliverables: sidebar tabs, chat panel, journal/info panel, activity log.
- Acceptance criteria: users can communicate and orient themselves without leaving the session.
- Risks: duplicated information, non-persistent chat expectations, confusing tab labels.
- Dependencies: M55 complete.
- Priority: `P1`

### DISCOVER prompt

```text
You are working on M57 (Chat, Journal, Activity) using DADM Discover only.

Goal:
Gather the factual basis for building the sidebar communication areas.

Inspect:
- existing sidebar structure in `play.html`
- activity logging in `play-ui.js`
- any existing chat or journal data sources
- runtime event flow for session updates
- user-facing labels and empty states

Produce:
- current-state summary
- inventory of existing sidebar content and events
- dependencies
- risks and assumptions with severity
- open questions
- next step into Apply

Do not:
- invent persistent chat storage yet
- redesign the session shell
- implement code
```

### APPLY prompt

```text
You are working on M57 (Chat, Journal, Activity) using DADM Apply only.

Goal:
Design a right-sidebar communication/workspace model that is clear, Roll20-like, and DAU-friendly.

Design must cover:
- tab structure
- chat panel behavior
- journal/info panel behavior
- activity log behavior
- session info summary
- empty states and labels
- how the panels behave when the session is read-only

Produce:
- sidebar architecture
- interaction rules
- label/terminology plan
- acceptance criteria
- risks and assumptions
- open TBDs
- next step into Deploy

Hard rules:
- No implementation
- No new backend requirements unless explicitly approved
- Keep the design compatible with the current play runtime
```

### DEPLOY prompt

```text
You are working on M57 (Chat, Journal, Activity) using DADM Deploy only.

Goal:
Implement the approved sidebar communication areas.

Implement:
- sidebar tab switching
- chat panel UI
- journal/info panel UI
- activity log rendering
- session info panel
- DAU-friendly labels and empty states

Constraints:
- Preserve existing functionality
- Do not create a hidden backend dependency unless approved
- Keep the sidebar responsive and compact

Required output:
- Implementation summary
- Files changed
- Proofs
- Acceptance checklist
- Residual risks
- Next step
```

### MONITOR prompt

```text
You are working on M57 (Chat, Journal, Activity) using DADM Monitor only.

Goal:
Validate the sidebar as a real secondary workspace.

Check:
- tabs switch correctly
- chat area is usable
- journal/info is readable
- activity log updates
- read-only behavior is clear

Output:
- validation result
- evidence summary
- residual findings
- recommendation
```

---

## M58 - Turn Order and Initiative

### Milestone definition

- Goal: Turn order becomes visible and operational as a core gameplay mechanic.
- Scope: initiative list, current turn marker, next turn control, initiative display, sync hooks.
- Constraints: use the existing session model; no combat engine rewrite.
- Deliverables: turn-order widget, current turn highlight, GM controls, clear initiative feedback.
- Acceptance criteria: the DM can manage initiative without leaving the session.
- Risks: stale data, unclear turn ownership, redundant initiative concepts.
- Dependencies: M56 complete.
- Priority: `P1`

### DISCOVER prompt

```text
You are working on M58 (Turn Order and Initiative) using DADM Discover only.

Goal:
Collect the facts needed to build a reliable initiative and turn-order experience.

Inspect:
- current initiative models and APIs
- how token state currently stores initiative
- how the session UI currently displays turn order, if at all
- any socket or event hooks related to turn changes

Produce:
- current-state summary
- initiative/turn-order inventory
- dependencies
- risks and assumptions with severity
- open questions
- next step into Apply

Do not:
- design turn mechanics yet
- invent new combat rules
- implement code
```

### APPLY prompt

```text
You are working on M58 (Turn Order and Initiative) using DADM Apply only.

Goal:
Design initiative display and turn-order management for the tabletop.

Design must include:
- visible turn-order widget
- sorting and highlighting rules
- current turn representation
- GM controls for advancing turns
- empty-state behavior
- how initiative relates to tokens on the map

Produce:
- architecture overview
- UI contract
- state update rules
- acceptance criteria
- risks and assumptions
- open TBDs
- next step into Deploy

Hard rules:
- No implementation
- No combat redesign beyond approved scope
- No new backend concepts unless they are in the Discover facts
```

### DEPLOY prompt

```text
You are working on M58 (Turn Order and Initiative) using DADM Deploy only.

Goal:
Implement the approved initiative and turn-order behavior.

Implement:
- turn-order widget
- initiative rendering
- current-turn highlight
- next-turn control if approved
- clear empty states and feedback

Constraints:
- Preserve session runtime compatibility
- No silent architecture changes
- Keep the UI readable in the sidebar or floating widget

Required output:
- Implementation summary
- Files changed
- Proofs
- Acceptance checklist
- Residual risks
- Next step
```

### MONITOR prompt

```text
You are working on M58 (Turn Order and Initiative) using DADM Monitor only.

Goal:
Validate that initiative is visible and operational.

Check:
- initiative list renders
- current turn is obvious
- advancing turn is understandable
- empty and populated states both behave sensibly

Output:
- validation result
- evidence summary
- residual findings
- recommendation
```

---

## M59 - Token Core

### Milestone definition

- Goal: Tokens become interactive as the primary play object.
- Scope: select, move, create, delete, drag-and-drop, token info, rights checks, movement sync.
- Constraints: keep server-side permission checks; do not weaken security.
- Deliverables: token interaction layer, drag behavior, selection state, visual feedback.
- Acceptance criteria: a token can be manipulated as a core gameplay object.
- Risks: desync, permission mistakes, accidental moves, misaligned coordinates.
- Dependencies: M56 and M58 complete.
- Priority: `P1`

### DISCOVER prompt

```text
You are working on M59 (Token Core) using DADM Discover only.

Goal:
Establish the factual basis for token interactions.

Inspect:
- token models and session state models
- current token rendering in the play UI
- current permission checks around token movement or creation
- any realtime sync behavior for token events

Produce:
- current-state summary
- token inventory
- dependencies
- risks and assumptions with severity
- open questions
- next step into Apply

Do not:
- invent drag-and-drop logic yet
- design new token semantics without evidence
- implement code
```

### APPLY prompt

```text
You are working on M59 (Token Core) using DADM Apply only.

Goal:
Design the token interaction model for the tabletop.

Design must include:
- selection model
- drag-and-drop movement rules
- create/delete interaction boundaries
- server-side permission rules
- visual feedback for move/select/lock state
- how tokens connect to map/layer context

Produce:
- architecture overview
- interaction contracts
- data update rules
- acceptance criteria
- risks and assumptions
- open TBDs
- next step into Deploy

Hard rules:
- No implementation
- No security weakening
- No new game mechanic beyond token interaction
```

### DEPLOY prompt

```text
You are working on M59 (Token Core) using DADM Deploy only.

Goal:
Implement the approved token interaction model.

Implement:
- token selection
- drag-and-drop movement
- create/delete interactions if approved
- movement feedback
- state sync to the existing runtime

Constraints:
- Enforce permissions server-side
- Do not break map rendering
- Keep token movement stable and understandable

Required output:
- Implementation summary
- Files changed
- Proofs
- Acceptance checklist
- Residual risks
- Next step
```

### MONITOR prompt

```text
You are working on M59 (Token Core) using DADM Monitor only.

Goal:
Validate that token interactions work as a core gameplay behavior.

Check:
- token selection is visible
- drag/drop works or is deliberately restricted
- movement is reflected correctly
- permissions are honored

Output:
- validation result
- evidence summary
- residual findings
- recommendation
```

---

## M60 - Session Lifecycle and Onboarding

### Milestone definition

- Goal: Make the path into and through the session unambiguous for DM and players.
- Scope: ready check, start, pause, resume, end, onboarding hints, state feedback.
- Constraints: keep compatibility with the current session state machine.
- Deliverables: lifecycle UI, onboarding copy, status messaging, role-aware guidance.
- Acceptance criteria: the DM can run a session without guessing the next action.
- Risks: confusing state transitions, duplicated controls, unclear permissions.
- Dependencies: M55 complete.
- Priority: `P1`

### DISCOVER prompt

```text
You are working on M60 (Session Lifecycle and Onboarding) using DADM Discover only.

Goal:
Collect the facts needed to make session flow obvious for DM and players.

Inspect:
- session lifecycle routes and models
- current readiness and state transition behavior
- onboarding hints and first-step notices
- DM versus player behavior in the current runtime

Produce:
- current-state summary
- lifecycle inventory
- dependencies
- risks and assumptions with severity
- open questions
- next step into Apply

Do not:
- redesign lifecycle behavior yet
- implement code
- assume any transition rule without evidence
```

### APPLY prompt

```text
You are working on M60 (Session Lifecycle and Onboarding) using DADM Apply only.

Goal:
Design clear session lifecycle UX for both DM and players.

Design must cover:
- ready/start/pause/resume/end flow
- status presentation in the UI
- onboarding hints for first-time users
- role-aware guidance
- failure and warning messaging

Produce:
- lifecycle UX design
- state/message mapping
- acceptance criteria
- risks and assumptions
- open TBDs
- next step into Deploy

Hard rules:
- No implementation
- No new lifecycle semantics unless approved
- Keep the design compatible with the current session model
```

### DEPLOY prompt

```text
You are working on M60 (Session Lifecycle and Onboarding) using DADM Deploy only.

Goal:
Implement the approved lifecycle and onboarding UX.

Implement:
- lifecycle controls
- session status display
- onboarding hints
- role-aware messages
- readiness/warning presentation

Constraints:
- Preserve current state transitions
- Keep messaging clear and DAU-friendly
- Do not break the play runtime

Required output:
- Implementation summary
- Files changed
- Proofs
- Acceptance checklist
- Residual risks
- Next step
```

### MONITOR prompt

```text
You are working on M60 (Session Lifecycle and Onboarding) using DADM Monitor only.

Goal:
Validate that the session flow is understandable and operable.

Check:
- DM can start the session without confusion
- players see what to do next
- status changes are visible
- warnings are understandable

Output:
- validation result
- evidence summary
- residual findings
- recommendation
```

---

## M61 - Roll20 Parity Polish

### Milestone definition

- Goal: Refine the session UI so it feels familiar to Roll20 users without losing the new baseline.
- Scope: typography, spacing, labels, visual hierarchy, empty states, minor motion.
- Constraints: no feature expansion; preserve core interaction behavior.
- Deliverables: polish pass for the session shell.
- Acceptance criteria: a Roll20 user understands the workspace instantly.
- Risks: over-polishing, visual clutter, inconsistent terminology.
- Dependencies: M55 through M60 complete or stable.
- Priority: `P2`

### DISCOVER prompt

```text
You are working on M61 (Roll20 Parity Polish) using DADM Discover only.

Goal:
Gather the factual basis for a visual and wording polish pass that increases Roll20 familiarity.

Inspect:
- current labels and terminology in the session UI
- spacing, typography, and panel hierarchy
- empty states and helper texts
- points where the UI already resembles Roll20 and where it does not

Produce:
- current-state summary
- polish inventory
- dependencies
- risks and assumptions with severity
- open questions
- next step into Apply

Do not:
- design new gameplay
- implement code
- expand scope beyond polish
```

### APPLY prompt

```text
You are working on M61 (Roll20 Parity Polish) using DADM Apply only.

Goal:
Design a polish pass that improves familiarity and reduces friction.

Design must cover:
- typography choices
- spacing/hierarchy
- button and panel styling
- empty state wording
- terminological consistency
- subtle motion, if justified

Produce:
- polish design
- terminology plan
- acceptance criteria
- risks and assumptions
- open TBDs
- next step into Deploy

Hard rules:
- No new functionality
- No redesign of the shell
- No implementation code
```

### DEPLOY prompt

```text
You are working on M61 (Roll20 Parity Polish) using DADM Deploy only.

Goal:
Implement the approved polish pass.

Implement:
- visual refinement
- wording refinement
- empty state improvements
- minor motion only if approved

Constraints:
- Keep the core session shell intact
- Do not introduce clutter
- No backend changes unless explicitly approved

Required output:
- Implementation summary
- Files changed
- Proofs
- Acceptance checklist
- Residual risks
- Next step
```

### MONITOR prompt

```text
You are working on M61 (Roll20 Parity Polish) using DADM Monitor only.

Goal:
Validate that the session feels familiar and cleaner without losing clarity.

Check:
- terminology is consistent
- UI feels closer to Roll20
- no regressions in readability
- no new friction introduced

Output:
- validation result
- evidence summary
- residual findings
- recommendation
```

---

## M62 - Hardening and Evidence

### Milestone definition

- Goal: Stabilize, test, and document the session baseline.
- Scope: smoke tests, manual verification, handoff notes, residual risks, handbuch updates.
- Constraints: no new features; no hidden changes.
- Deliverables: validation evidence, updated handbuch, residual risk register.
- Acceptance criteria: the baseline is demonstrably usable and documented.
- Risks: regression, undocumented edge cases, missing evidence.
- Dependencies: M55-M61 stable.
- Priority: `P1`

### DISCOVER prompt

```text
You are working on M62 (Hardening and Evidence) using DADM Discover only.

Goal:
Collect the facts needed to validate and document the current session baseline.

Inspect:
- current tests and smoke checks
- session shell state
- play runtime entry points
- handbuch and existing milestone docs

Produce:
- current-state summary
- validation inventory
- dependencies
- risks and assumptions with severity
- open questions
- next step into Apply

Do not:
- design new features
- implement fixes
- assume missing evidence exists
```

### APPLY prompt

```text
You are working on M62 (Hardening and Evidence) using DADM Apply only.

Goal:
Design the validation and documentation package for the session baseline.

Design must include:
- which smoke tests are required
- which user journeys must be proven
- how the handbuch should be updated
- how residual risks should be recorded
- what counts as acceptable baseline closure

Produce:
- validation plan
- evidence plan
- documentation plan
- acceptance criteria
- risks and assumptions
- open TBDs
- next step into Deploy

Hard rules:
- No implementation
- No scope expansion
- Keep the validation bounded to the session baseline
```

### DEPLOY prompt

```text
You are working on M62 (Hardening and Evidence) using DADM Deploy only.

Goal:
Implement the approved hardening and evidence tasks.

Implement:
- smoke tests or verification checks
- handbuch updates
- evidence capture
- residual risk notes

Constraints:
- No new features
- No hidden fixes outside approved scope
- Proof must be concrete and reviewable

Required output:
- Implementation summary
- Files changed
- Proofs
- Acceptance checklist
- Residual risks
- Next step
```

### MONITOR prompt

```text
You are working on M62 (Hardening and Evidence) using DADM Monitor only.

Goal:
Validate that the session baseline is stable enough for the next iteration.

Check:
- smoke tests pass or documented equivalent evidence exists
- handbuch is current
- residual risks are explicit
- no unresolved medium-or-higher issues remain

Output:
- validation result
- evidence summary
- residual findings
- recommendation: close, rework, or continue
```

---

## Approval note

This pack is ready to be approved milestone by milestone.

Suggested order:
1. Approve M55
2. Approve M56
3. Approve M57
4. Approve M58
5. Approve M59
6. Approve M60
7. Approve M61
8. Approve M62

If you want, I can now turn this into a stricter DADM operator format with:
- separate `Discover/Apply/Deploy/Monitor` artifacts per milestone
- explicit `status`, `retention`, `dependencies`, `risk gate`
- a short `approval` block after each milestone for clean sign-off
