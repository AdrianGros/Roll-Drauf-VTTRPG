# M63 Session Hub and Game-Details Parity

Date: 2026-03-27
Status: draft
Basis: Roll20-style session entry flow copied first, then improved
Reference baseline: official Roll20 docs for My Games, Game Details, Invite Players, Launch Game

## Milestone Definition

- Goal: Create a Roll20-like session hub where DM and players understand the campaign state, session state, invite state, and the next obvious action without technical detours.
- Scope: campaign/session overview, launch entry, invite summary, readiness checklist, DM/player affordances, next-step guidance.
- Constraints: preserve current campaign/session runtime behavior; no backend redesign; no API-only user journey.
- Deliverables: session hub view, lobby summary block, DM action block, player entry block, launch/enter flow, clear empty and failure states.
- Acceptance criteria: the correct next action is obvious for both DM and player without reading documentation.
- Risks: duplicate navigation, unclear role boundaries, mismatched lobby/session state, confusing launch flow.
- Dependencies: existing campaigns dashboard, current session model, current launch path, live play shell.
- Priority: `P1`

## DISCOVER Prompt

```text
You are working on M63 (Session Hub and Game-Details Parity) for the Roll-Drauf VTT using DADM Discover only.

Goal:
Collect factual information about the current campaign hub, lobby, and session entry path so the Roll20-like session hub can be designed safely.

Primary reference intent:
- Roll20-style `My Games` -> `Game Details` -> `Invite Players` -> `Launch Game`
- We are copying the workflow first, not inventing a new one.

What to inspect:
- `vtt_app/templates/campaigns.html`
- `vtt_app/templates/play.html`
- session launch routes and campaign detail routes
- any lobby or invitation panels already rendered in the UI
- existing role checks for DM, owner, and player
- existing session state data exposed to templates or JavaScript
- any readiness / checklist / status UI already present

What to identify:
- What is the current hub entry point for DM and player?
- What data is shown before a session is launched?
- What invite and join affordances already exist?
- What differs between DM and player view today?
- What state is already available for campaign readiness, session readiness, and launch eligibility?
- What elements are already close to Roll20 parity and can be reused?

What to produce:
- Current-state summary of hub and entry flow
- Inventory of entry points, controls, status labels, and role gates
- Dependencies and constraints
- Risks and assumptions with severity labels
- Open questions that block safe design
- A one-line next step into Apply

Hard rules:
- Do not design the new hub yet
- Do not implement code
- Do not assume invitation, launch, or readiness behaviors that are not evidenced
- Do not widen scope into asset library or map placement

If a required fact is missing, mark it `unclear`.
If a medium-or-higher risk appears, say whether it blocks Apply.
```

## APPLY Prompt

```text
You are working on M63 (Session Hub and Game-Details Parity) using DADM Apply only.

Goal:
Turn the Discover facts into a concrete session-hub design that mirrors the Roll20 mental model for DM and player entry.

Design requirements:
- hub is the central campaign/session control surface
- DM sees campaign state, invite state, readiness, and launch state
- player sees a simple entry path and the minimum necessary context
- launch and enter actions are visually obvious and not hidden in admin controls
- empty states explain what to do next in plain language
- role separation must be clear without feeling punitive

What the design must include:
- campaign summary block
- session status block
- invite summary / join block
- readiness checklist or step indicator
- primary launch/enter CTA
- failure and empty states
- DM vs player view differences
- terminology that stays close to Roll20 mental models

Questions the design must answer:
- What is the single primary action for the DM?
- What is the single primary action for the player?
- Which information is always visible and which is secondary?
- How do we prevent duplicate navigation between campaigns, lobby, and play?
- How do we show that a campaign is ready, waiting, live, paused, or ended?
- What happens when no session exists yet?
- What happens when a user lacks permission?

What to produce:
- Solution design for the hub layout and information hierarchy
- DOM/container plan for hub sections
- interaction contract for launch, enter, invite, and status refresh
- role-based visibility rules
- acceptance criteria written as binary checks
- risks and assumptions with severity labels
- open TBDs if any design detail is still unresolved
- a one-line next step into Deploy

Hard rules:
- No implementation code
- No new backend architecture
- No feature expansion into asset management yet
- No bypass of unresolved medium-or-higher risk

The design should feel like the obvious place a DM or player lands before the session begins.
```

## DEPLOY Prompt

```text
You are working on M63 (Session Hub and Game-Details Parity) using DADM Deploy only.

Goal:
Implement the approved session-hub design and record proof.

Implementation expectations:
- reshape the campaign/session entry page into a Roll20-like hub
- make the DM entry flow obvious
- make the player entry flow obvious
- surface invite and readiness state in a simple, visible layout
- preserve existing routes, roles, and functional IDs unless the approved design explicitly changes them
- keep launch / enter behavior consistent with current runtime state

Do not:
- introduce a new backend flow outside the approved design
- silently remove existing navigation
- hide role-specific controls without a replacement
- expand into asset library or map upload functionality

Required output:
- Implementation summary
- Files changed
- Proofs
- Acceptance checklist
- Residual risks
- Next step

Proofs should include:
- DOM or grep checks for key hub elements
- route or template verification
- a basic smoke test of DM and player entry behavior

If implementation forces a design change, stop and escalate back to Apply.
```

## MONITOR Prompt

```text
You are working on M63 (Session Hub and Game-Details Parity) using DADM Monitor only.

Goal:
Validate that the deployed hub is understandable and that the DM/player next step is obvious.

What to verify:
- DM lands on a clear hub rather than a technical screen
- player sees a simple entry path
- invite state is visible or clearly omitted when unavailable
- launch / enter CTA is prominent and not hidden
- empty and failure states explain what to do next
- role separation feels clear

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

## Human-Test Checkpoint

- Test with one DM and one player if available
- Verify they can each identify the next action in under one minute
- Record confusion points, misclicks, and missing labels
- If the primary entry path is not obvious, keep the milestone open

