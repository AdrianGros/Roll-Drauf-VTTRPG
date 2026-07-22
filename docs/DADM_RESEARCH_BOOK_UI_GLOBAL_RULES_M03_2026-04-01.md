# DAD-M Research: Book UI Global Rules (M03)

Date: 2026-04-01
Milestone: M03
Phase: RESEARCH
Status: approved

## Goal

Lock the implementation rules for the Book UI system using primary or official sources so later milestones can execute without re-litigating fundamentals.

## Sources Used

Primary and official sources reviewed:

- W3C WCAG 2.1 Reflow:
  - https://www.w3.org/WAI/WCAG21/Understanding/reflow
- W3C WCAG 2.1 Animation from Interactions:
  - https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions.html
- MDN `transform-style`:
  - https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/transform-style
- web.dev animation performance:
  - https://web.dev/articles/animations-guide
- Carbon Design System motion:
  - https://carbondesignsystem.com/elements/motion/overview/
- Carbon Design System spacing:
  - https://carbondesignsystem.com/elements/spacing/overview/
- Carbon Design System 2x Grid:
  - https://carbondesignsystem.com/elements/2x-grid/overview/

## Research Findings

### R-01 — Reflow is a hard baseline for non-workspace routes

W3C states that content should work without loss of information or functionality at the equivalent of a `320 CSS pixel` width for vertically scrolling content. The same guidance also acknowledges that some interfaces are legitimately dimension-constrained or authoring-oriented exceptions.

Implication for this program:

- `signup`, `register`, `dashboard`, `campaigns`, `characters`, and `lobby` must reflow
- `character-sheet` should reflow where practical
- `play` may remain a justified 2D exception, but surrounding chrome and controls should still respond sensibly

### R-02 — Non-essential interaction-triggered motion must be suppressible

W3C says animation triggered by user interaction must be disableable unless it is essential to the functionality or information being conveyed.

Implication:

- route page-turns are allowed only with a reduced-motion fallback
- decorative parchment zooms, page flips, and shell reveals must collapse to minimal or instant transitions when motion reduction is active
- no milestone may introduce mandatory theatrical motion

### R-03 — 3D shell mechanics are structurally fragile

MDN documents that `transform-style: preserve-3d` can be effectively flattened by grouping properties and values such as:

- `overflow` other than `visible` or `clip`
- `opacity` below `1`
- `filter` other than `none`
- `clip-path`
- `isolation: isolate`
- paint containment-related values

Implication:

- the 3D cover implementation should stay isolated
- dense product content should live on stable page planes, not inside a fragile 3D descendant stack
- shell chrome and work surfaces must remain separated

### R-04 — Route transitions should prefer transform and opacity

web.dev recommends restricting animation to `transform` and `opacity` where possible so the browser can keep work on the compositing stage. It also recommends using `will-change` sparingly and only when a real issue exists.

Implication:

- route-turn animations should be based on transform/opacity
- page architecture must not depend on animating layout-heavy properties
- `will-change` must not become a blanket styling habit

### R-05 — Motion should be productive by default, expressive only at milestones

Carbon frames motion as a way to guide users efficiently and distinguishes broader UI motion from component-level microinteractions. The search snippet for Carbon’s motion guidance emphasizes that productive motion should help users move forward quickly.

Implication:

- page-turns and chapter shifts may be expressive
- tabs, filters, drawers, validation, modal transitions, and table/list interactions should stay calm and task-oriented

### R-06 — Spacing and grid are system-level decisions

Carbon’s grid and spacing guidance emphasizes structural rhythm rather than ad hoc spacing. The 2x Grid overview centers work around a repeatable mini-unit, while spacing guidance treats consistent spacing as core design infrastructure.

Implication:

- gutters, folio spacing, page padding, panel spacing, and card rhythm should come from a shared scale
- later milestones should reduce one-off route spacing decisions
- shell consistency should come from structure first, texture second

## Derived Rules For This Repo

### Rule A

Keep `login.html` as the only heavy 3D cover surface unless later evidence justifies wider use.

### Rule B

All non-play spread pages must remain usable at narrow widths and high zoom without 2D scrolling in normal tasks.

### Rule C

All route-level dramatic motion must have a reduced-motion path.

### Rule D

Focus-mode and workspace routes should inherit book identity through framing and navigation cues, not by shrinking productive work areas.

### Rule E

Animations that exist mainly for delight must never be the mechanism that makes navigation or comprehension possible.

### Rule F

New shell work should prefer shared tokens, shared spacing, and shared route metadata over per-template improvisation.

## Approval

- scope_kept: yes
- live_check_used: no
- residual_risks: Carbon source detail was partially available via official search snippets rather than full page render, but the derived rules align with stronger primary sources from W3C/MDN/web.dev
- approved_to_proceed: yes
