# DAD-M Closeout: Book UI Realign

Date: 2026-04-01
Status: closeout_ready
Scope: consolidate current IST vs current SOLL after the realign wave and define the next polishing program

## Objective

Close the realign phase honestly, record what is now truly implemented, identify the remaining gaps and quality risks, and replace milestone-theater with a practical next wave plan.

## Basis

- `docs/DADM_REALIGN_BOOK_UI_PROGRAM_STATUS_2026-04-01.md`
- `docs/DADM_MONITOR_CAMPAIGNS_CHARACTERS_BOOK_SCENE_2026-04-01.md`
- `docs/DADM_MONITOR_CHARACTER_SHEET_REALIGN_2026-04-01.md`
- `docs/DADM_MONITOR_PLAY_REALIGN_2026-04-01.md`
- current live route templates and book scene assets

## IST vs SOLL Closeout

### Entry Journey

IST:

- `login` stays inside the book object
- auth success transitions into the in-book dashboard
- registration key gating is restored

SOLL:

- cover opens into the next folio instead of dropping into a normal app shell

Assessment:

- aligned
- the architectural break is closed

### Spread Journey

IST:

- `dashboard`, `campaigns`, and `characters` load as book pages in the persistent scene
- the ribbon sits on the page
- the page can scroll vertically and the ribbon stays fixed

SOLL:

- authenticated navigation should read like turning through a storybook
- dashboard-family routes should remain parchment pages, not generic application views

Assessment:

- aligned at architecture level
- still in visual and interaction polish

### Character Sheet

IST:

- `character-sheet` now uses the same page-native book language
- route has embedded ribbon, titlebar chips, and focus parchment shell
- underlying character data flows remain intact

SOLL:

- sheet should feel like a focused folio inside the same book family

Assessment:

- aligned for this realign wave
- not yet fully consolidated into the shared `book-scene.js` runtime, but no longer a plain external interface

### Play Workspace

IST:

- `play` now presents as a book-native workspace exception
- ribbon and page titlebar are inside the book family
- map and session workspace remain large and productive

SOLL:

- play should remain part of the same enchanted object while preserving real usability for the table

Assessment:

- aligned for this realign wave
- still needs live-session polish and density tuning

## What Is Now Truly Complete

- Access gate and key-controlled registration are restored.
- The book-camera direction is no longer only conceptual; it is live across the main authenticated route family.
- `login -> dashboard -> campaigns -> characters` now behaves as one coherent book journey.
- `character-sheet` is realigned into the same visual language instead of sitting in generic app chrome.
- `play` is realigned as a workspace exception inside the same family instead of reading like a separate admin tool.

## Remaining Gaps

- Browser-level perceptual validation is still thinner than the source-level live checks.
- Mobile and small-height behavior still need a dedicated pass across all realigned routes.
- Reduced-motion behavior needs one explicit quality pass in the newer book-camera flow.
- `character-sheet` and `play` share the book language, but they are not yet deeply unified under one runtime orchestration model.
- `campaigns` and `characters` still carry older detail and modal behavior that has not yet been rewritten into the full book grammar.
- The page-turn and zoom feeling is present in direction, but not yet at the strongest Prezi-like polish level the target vision implies.

## Quality Risks

- Visual drift: route-local shells can slowly diverge from the shared book scene if spacing, chips, headers, and panel language are not normalized.
- Architectural split: `book-scene` for spread routes and route-local shells for focus/workspace routes are compatible, but still a dual system.
- Scroll and sticky risk: fixed ribbon behavior can become cramped on low viewport heights if header density is not tuned.
- Workspace clutter risk: `play` can regress into a decorated interface if ribbon, chips, and controls compete too hard with the map.
- Validation risk: several approvals were based on live HTML and asset checks, not on full browser walkthroughs with richer user state.

## True Program Position

The honest position is no longer `M20 incomplete`, but it is also not `fully polished`.

The real state now is:

- Realign architecture across the primary route families: complete
- Live rollout of the new book family: complete
- Cross-route quality normalization and experiential polish: next active wave

Operationally, the program has moved from `realign` into `polishing`.

## Next Polishing Wave

### P1: System Polish

- normalize ribbon behavior, chip language, page spacing, and parchment density
- run dedicated mobile, tablet, and small-height passes
- verify reduced-motion and scroll behavior across book routes

### P2: Interaction Polish

- strengthen page-turn and zoom continuity between chapter routes
- pull first in-book actions deeper into `campaigns` and `characters`
- reduce any remaining moments that feel like a normal dashboard utility app

### P3: Architecture Consolidation

- decide whether `character-sheet` and `play` should remain route-local book shells or move deeper into a unified shared scene runtime
- consolidate reusable book-header, titlebar, and status primitives so future pages do not fork the language again

## Decision

The realign wave should be considered closed.

From this point forward, progress should be reported as:

- `Book UI Realign: complete`
- `Book UI Polish Wave P1: active`

This keeps the reporting honest and gives the next work a concrete target instead of pretending the remaining issues are still milestone-discovery questions.
