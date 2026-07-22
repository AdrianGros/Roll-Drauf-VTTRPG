# DAD-M Research: Book UI Play Workspace (M19)

Date: 2026-04-01
Milestone: M19
Phase: RESEARCH
Status: approved

## Goal

Freeze the implementation rules for wrapping the tabletop in book chrome without regressing responsiveness or interaction performance.

## Sources Used

- web.dev animations guide:
  - https://web.dev/articles/animations-guide
- web.dev RAIL model:
  - https://web.dev/rail/
- MDN `transform-style`:
  - https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/transform-style
- Carry-forward W3C reduced-motion guidance from `M03`:
  - https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions.html

## Findings

### R-01

High-density work surfaces should avoid layout-heavy decorative motion.

web.dev emphasizes transform and opacity for animation work and frames performance around response budgets that keep interaction feeling immediate.

Implication:

- the workspace shell should add framing, not expensive in-surface animation
- map interaction must stay dominant over shell theatrics

### R-02

3D mechanics remain fragile and are a poor container for live-table interaction.

MDN's `transform-style` guidance reinforces the earlier decision to keep 3D cover behavior isolated.

Implication:

- `play` should use a stable shell frame, not a nested 3D book interior

### R-03

Reduced-motion discipline still applies even on a dense workspace.

Implication:

- route-level book identity is acceptable
- live table operations must never depend on decorative motion

## Derived Rules For M20

### Rule A

Wrap the workspace in book chrome, but do not reduce the effective working area more than necessary.

### Rule B

Preserve existing play logic and interaction structure.

### Rule C

Keep the pilot focused on shell translation, not gameplay redesign.

## Approval

- scope_kept: yes
- live_check_used: no
- approved_to_proceed: yes
