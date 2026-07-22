# DAD-M SOLL: Book UI Layout Rules

Date: 2026-04-01
Scope: `login`, `signup`, `register`, `dashboard`, `campaigns`, `characters`, `character-sheet`, `lobby`
Exception: `play` is not a normal book route. It is an explicit mode-switch from book navigation into tabletop mode.

## Goal

The VTT should read as a persistent book object, not as a normal application wrapped in parchment styling.
The viewport is only the stage.
The UI itself lives inside the book.

## Core Layout Rules

1. The book is a centered object.
   It must stay visually centered in the viewport and may not degrade into a full-screen flat panel.

2. The spine is the structural center.
   The middle of the layout is the book binding, not a decorative divider and not the origin of a generic screen animation.

3. Every non-`play` route must read as a spread or a focus page inside the same book family.
   Navigation should feel like moving through the same object, not loading another website.

4. Left and right page geometry must be explicit.
   Each spread needs clear left-page and right-page surfaces with consistent inner margins and gutter spacing.

5. Cards across the spread must be symmetrical where they are peers.
   If a component on the left and right page plays the same structural role, they should align in width, rhythm, and vertical start.

6. The book shell owns depth.
   Cover, paper stack, spine, shadows, and perspective belong to the shell layer, not to individual route templates.

7. Route families and mode families must not be confused.
   `dashboard`, `campaigns`, `characters`, `character-sheet`, `login`, `signup`, `register`, and `lobby` are book-mode surfaces.
   `play` is table-mode and must be treated separately.

## Spread Rules

1. A spread consists of:
   left page, gutter/spine zone, right page, optional shared lower band.

2. Shared top ribbons stay aligned across both pages.
   The ribbon may be sticky, but it must still feel embedded in the paper rather than like a web app header.

3. Left and right page cards start on the same visual baseline.
   Heading block, meta chips, first major card, and lower notes should not drift arbitrarily between pages.

4. The lower utility band spans the whole spread.
   It should sit below both pages as one shared layer, not as an accidental overflow block.

5. Overflow should prefer vertical book growth.
   Content may extend the spread downward; the book should scroll vertically rather than clipping important paper content.

## Component Rules

1. Use one paper language.
   Border radius, border opacity, inner glow, and card shadow should come from shared rules, not per-route improvisation.

2. Use one spacing rhythm.
   Headings, chips, cards, notes, and footer modules should follow a repeatable spacing scale.

3. Decorative page stacks must stay subordinate.
   They may suggest thickness, but must never overpower content or visibly break outside the book silhouette.

4. The spine must support, not dominate.
   It should be visible through light, shadow, and geometry, but not appear as a heavy center bar unless a specific scene calls for it.

5. Focus routes may densify content, but keep the same material system.
   `character-sheet` can be denser than `dashboard`, but should still feel printed into the same book family.

## Motion Rules

1. The book shell remains mounted.
   Route or state changes should happen inside the shell.

2. Page turns rotate around the spine-side edge of the active page.
   Never around the visual center of the viewport or a flat container.

3. Underlying content swaps at the correct animation moment.
   The next spread appears beneath the turning page, not before the turn begins.

4. No fake replacements.
   Avoid fullscreen fades, screen-wide slides, carousel logic, or card-flip substitutes.

## UI Modes

The application should now be reasoned about in modes, not only routes.

1. `BOOK_MODE`
   Open centered book, spread/focus navigation, page-turn logic.

2. `BOOK_TO_TABLE_TRANSITION`
   Staged exit from book navigation into the session space.

3. `TABLE_MODE`
   Tabletop session surface, no strict left/right spread contract.

4. `TABLE_TO_BOOK_TRANSITION`
   Inverse staged return from the table back into the book.

## Accessibility And Responsiveness

1. Reduced motion must disable non-essential page drama.
   The book structure remains, but animation complexity drops sharply.

2. Small screens may collapse spread layout to stacked pages.
   The metaphor should stay intact even when left/right pages become a vertical reading order.

3. Readability beats ornament.
   Decorative shadows, stacks, or engravings must be reduced if they harm legibility.

## Play Exception

`play` is no longer treated as a loose book-route exception.
`play` is an explicit transition out of `BOOK_MODE` into `TABLE_MODE`.

### Required behavior for entering `play`

1. The current book remains visible as a physical object.
2. The book closes visibly before table mode fully takes over.
3. The camera or scene reframes away from the front-facing book toward a tabletop surface.
4. The session UI appears on a table surface / tabletop scene, not in strict spread geometry.

### Rules for `play`

1. `play` may break the fixed left/right page symmetry.
2. `play` may leave the strict spread layout.
3. `play` must still belong to the same visual family.
   Materials, light mood, ornament language, and motion quality should still feel like the same product world.
4. The result should feel like the book transformed into a play space, not like a hard cut to a different app.

### Not allowed for `play`

- a normal full-screen route replace
- a flat dashboard replacement
- a hard cut away from the book with no staged transition
- an unrelated game screen with no visual continuity
- optimizing `play` toward book-card symmetry when the table needs different geometry

### Return behavior

Returning from `play` should be modeled as the inverse mode transition:
`TABLE_MODE -> TABLE_TO_BOOK_TRANSITION -> BOOK_MODE`

## Acceptance Rules

1. The book remains visible as the primary object.
2. The spine remains the anchor of the layout system.
3. Left/right peer cards are symmetrical unless there is a clear content reason not to be.
4. Lower shared bands do not clip or detach from the spread.
5. Navigation inside non-`play` routes reads as book navigation, not route replacement.
6. New pages inherit shell rules instead of redefining their own layout language.

## Acceptance Rules For `play`

1. `play` does not read as a normal book spread.
2. The transition into `play` is visibly staged.
3. The book closes before table mode fully takes over.
4. The camera reframes toward a tabletop surface.
5. The session UI is presented in table mode, not strict spread mode.
6. Visual continuity with the book family remains intact.
7. Returning from `play` can be implemented as the inverse transition.
