# DAD-M Research: Book UI Spread Screens (M11)

Date: 2026-04-01
Milestone: M11
Phase: RESEARCH
Status: approved

## Goal

Freeze the best-practice guidance for responsive spread layouts, card grids, spacing rhythm, and overview/detail content surfaces.

## Sources Used

- W3C WCAG 2.1 Reflow:
  - https://www.w3.org/WAI/WCAG21/Understanding/reflow
- web.dev responsive web design basics:
  - https://web.dev/articles/responsive-web-design-basics
- Carbon spacing overview:
  - https://carbondesignsystem.com/elements/spacing/overview/
- Carbon 2x Grid usage:
  - https://carbondesignsystem.com/elements/2x-grid/usage/

## Findings

### R-01

Spread routes must be content-led, not device-led.

web.dev recommends choosing breakpoints based on where content no longer fits naturally, not on product-specific device assumptions.

Implication:

- spread pages should keep fluid card grids and stacked controls
- breakpoint logic should follow content pressure, not a hard-coded screen taxonomy

### R-02

Horizontal scrolling is a failure mode for overview routes.

W3C reflow guidance requires normal task completion without loss of information or functionality at narrow widths and high zoom.

Implication:

- tabs, filters, and cards should wrap or stack
- spread routes should not depend on wide fixed panes

### R-03

Spacing consistency is a systems problem, not a per-template decision.

Carbon treats spacing as shared infrastructure and ties readable layouts to repeatable spacing tokens and rhythm.

Implication:

- shared spread card, panel, and filter spacing should move into common CSS
- local one-off spacing should be reduced where possible

### R-04

Grid and overview surfaces should preserve hierarchy and continuity.

Carbon's grid guidance emphasizes hierarchy, rhythm, continuity, and contrast rather than equal treatment for every block.

Implication:

- stats, tabs, filters, detail panels, and cards should belong to one family but still keep distinct emphasis levels
- the shell should orient, while the interior surfaces should repeat recognizable paper fragments

## Derived Rules For M12

### Rule A

Prefer one shared CSS normalization slice over multi-template restructuring.

### Rule B

Improve tabs, filters, cards, and detail panels together only if they can be normalized from shared styles.

### Rule C

Do not re-architect route logic or modal behavior in this spread polish pass.

## Approval

- scope_kept: yes
- live_check_used: no
- approved_to_proceed: yes
