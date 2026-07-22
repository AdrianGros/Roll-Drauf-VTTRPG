# DAD-M Discover: Book UI Best Practices

Date: 2026-03-30
Phase: DISCOVER
Scope: Primary-source guidance for building the spellbook UI correctly
Status: complete

## Objective

Map the desired spellbook UI against primary-source guidance for accessibility, motion, spacing, performance, and architecture discipline.

## Primary Sources Used

- W3C WCAG 2.1 Reflow:
  - https://www.w3.org/WAI/WCAG21/Understanding/reflow.html
- W3C WCAG 2.1 Animation from Interactions:
  - https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions.html
- MDN `backface-visibility`:
  - https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/backface-visibility
- MDN `transform-style`:
  - https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/transform-style
- web.dev animation performance:
  - https://web.dev/articles/animations-guide
- IBM Carbon spacing:
  - https://v10.carbondesignsystem.com/guidelines/spacing/overview/
- IBM Carbon 2x Grid:
  - https://v10.carbondesignsystem.com/guidelines/2x-grid/overview/
- IBM Carbon motion:
  - https://v10.carbondesignsystem.com/guidelines/motion/overview/
- Microsoft architecture design specification:
  - https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-design-specification

## Best-Practice Findings

### 1. Reflow and zoom are hard requirements, not polishing

W3C’s Reflow guidance says non-excepted content must work without loss of information or functionality down to the equivalent of `320 CSS px` width, and it explicitly distinguishes ordinary content from complex two-dimensional exceptions.

Implication for this project:

- browse/admin/list/detail pages should reflow
- content should often collapse toward a single readable parchment column
- the full application shell must not depend on a narrow fixed book viewport
- dense two-dimensional zones like tabletop/map can be treated as exceptions, but surrounding content still needs to reflow

### 2. Route-level motion may be expressive; local interactions should be productive

IBM Carbon distinguishes productive motion from expressive motion and says expressive motion should be reserved for significant moments, while productive motion should stay subtle and task-oriented.

Implication:

- cover opening and chapter/page transitions can be expressive
- button hover, accordion reveal, form validation, tab changes, drawers, filters, and local disclosures should be productive
- the current login animation language should not be copied unchanged into every interaction

### 3. Non-essential motion must be suppressible

W3C’s Animation from Interactions guidance requires that motion triggered by interaction can be disabled unless it is essential.

Implication:

- page-turn animation needs a reduced-motion path
- “parchment zoom” and “page flip” must degrade to instant or minimal transitions when motion reduction is active
- shell beauty cannot override accessibility

### 4. 3D book effects have concrete CSS fragility rules

MDN documents two key realities:

- `backface-visibility` controls whether the back of a rotated 3D element shows through
- `transform-style: preserve-3d` is required to keep descendants in 3D
- some property combinations force flattening, including:
  - `overflow` other than `visible` or `clip`
  - `opacity < 1`
  - `filter`
  - `isolation: isolate`

Implication:

- the 3D shell must stay isolated from ordinary content containers
- route content should not be deeply nested inside the fragile 3D transform stack
- content surfaces should usually sit on a stable “page plane,” while the outer shell handles the theatrical 3D frame

### 5. Animation performance should stay on transform/opacity wherever possible

web.dev recommends keeping animations to `transform` and `opacity` where possible and using `will-change` sparingly.

Implication:

- page turns, cover movement, zoom transitions, and fade choreography should use transform/opacity first
- do not animate layout-heavy properties for broad page transitions
- expensive visual effects should not be the mechanism that makes navigation work

### 6. Spacing and grid must become first-class system rules

IBM Carbon states that spacing creates relationships and hierarchy, and its grid guidance frames layout structure as a foundational system, not an afterthought.

Implication:

- the spellbook UI needs a spacing scale and layout grammar
- decorative margins, gutters, folio areas, and content widths must be tokenized
- “book feeling” should come from structure and rhythm, not only textures and gradients

### 7. Architecture documentation should capture tradeoffs explicitly

Microsoft’s architecture design specification guidance emphasizes clear design choices, justifications, functional and nonfunctional consequences, rollout details, and storage with project documentation.

Implication:

- the book-shell rollout needs an explicit architecture record
- route classes, exceptions, animation policy, and responsive modes should be documented before implementation
- this is especially important because the shell affects every page, not one widget

## Best-Practice Rules Derived for This Repo

### Rule A: Separate shell motion from content usability

- 3D shell handles theatrical movement
- page content stays on a stable readable plane

### Rule B: Build around multiple route modes

- cover mode
- reading spread mode
- focused page mode

### Rule C: Treat map/tabletop as a justified two-dimensional exception

- the map can remain dense
- the rest of the page chrome still must reflow and remain readable

### Rule D: Use expressive motion only for route/section changes

- page turns
- chapter shifts
- shell open/close

Everything else should be calmer.

### Rule E: Define spacing, page margins, gutters, tabs, and parchment widths as tokens

- no ad-hoc per-template sizing if the goal is one spellbook product

## Discover Conclusion

Best practice does not fight the spellbook idea. It narrows it:

- make content reflow where possible
- isolate 3D theatrics from normal layout
- reserve dramatic motion for important transitions
- treat dense workspaces as exceptions, not as proof that the whole metaphor should collapse

## Next Step

Define architecture options that fit the existing Flask/server-rendered stack and these best-practice constraints.
