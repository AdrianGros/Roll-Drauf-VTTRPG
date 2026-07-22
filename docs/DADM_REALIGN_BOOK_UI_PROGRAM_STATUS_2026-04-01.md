# DAD-M Realign: Book UI Program Status

Date: 2026-04-01
Status: post-realign
Scope: compare current IST against current SOLL and pinpoint true position after the realign wave

## Objective

Reconcile the original M01-M20 milestone ledger with the actual product state now present in repo and live rollout, after the later pivot toward a persistent book-camera journey.

## Sources Used

- `milestone_program_book_ui_20.md`
- `docs/DADM_ORCHESTRATOR_BOOK_UI_PROTOCOL_2026-04-01.md`
- `docs/DADM_DISCOVER_BOOK_UI_BOOK_CAMERA_FLOW_2026-04-01.md`
- `docs/DADM_SOLL_BOOK_UI_BOOK_CAMERA_FLOW_2026-04-01.md`
- `docs/DADM_MONITOR_CAMPAIGNS_CHARACTERS_BOOK_SCENE_2026-04-01.md`
- `docs/DADM_MONITOR_CHARACTER_SHEET_REALIGN_2026-04-01.md`
- `docs/DADM_MONITOR_PLAY_REALIGN_2026-04-01.md`
- current route templates and `vtt_app/static/js/book-scene.js`

## Realign Summary

The original orchestrator ledger marks `M01-M20` as approved, but that ledger no longer reflects the product truth with enough precision unless it is read through the later realign work.

Reason:

- the program pivoted from general spellbook-shell rollout to a stronger `persistent book object + camera zoom + page-native navigation` model
- that newer model is more specific than the original spread/focus/workspace baseline
- implementation has now materially advanced across entry, spread, focus, and workspace, but the remaining work sits in polish and consolidation rather than in first-wave rollout

## Current IST vs Current SOLL

### Area A: Entry / Book Continuity

IST:

- `login` lives in `book-scene`
- successful auth transitions into the same spellbook scene
- registration key gate is restored

SOLL:

- user should remain inside one book object before and after login
- auth success should feel like `open cover -> turn page -> zoom into page`

Assessment:

- largely aligned
- the major continuity break from earlier state is closed
- motion and theatricality may still be polished further, but architecture is now correct

Status:

- `on target`

### Area B: Dashboard / Campaigns / Characters as Book Pages

IST:

- `dashboard`, `campaigns`, and `characters` boot into the same `book-scene`
- page-native ribbon exists on the parchment
- direct route loads and reloads stay in the book flow
- page size, sticky ribbon, and vertical scroll behavior were actively corrected in later follow-up fixes

SOLL:

- authenticated navigation should feel like moving through a storybook
- menu belongs on the page
- dashboard and follow-up pages should read like composed parchment pages

Assessment:

- structurally aligned
- this is the strongest completed part of the current rollout
- remaining gap is mostly quality/polish, not architecture

Status:

- `implemented, in polish/validation`

### Area C: Character Sheet Focus Mode

IST:

- `character-sheet.html` has page-native book treatment
- route uses embedded ribbon, focus parchment shell, and title/status chips
- underlying sheet interactions remain intact inside the new shell

SOLL:

- sheet should be a real focus-mode route
- it should stay clearly inside the spellbook system

Assessment:

- aligned for the current realign scope
- the route now reads as part of the same book family
- remaining question is architecture consolidation, not shell absence

Status:

- `implemented, in polish/validation`

### Area D: Play Workspace Exception

IST:

- `play.html` uses a page-native book workspace shell
- the route now includes the in-book ribbon and a title/status band inside the same family
- the map and productive workspace stay large

SOLL:

- play should be a justified workspace exception inside the same spellbook system
- map must remain productive, not decorative

Assessment:

- aligned for the current realign scope
- the workspace exception is now visually and structurally inside the book family
- remaining work is density and live-session polish

Status:

- `implemented, in polish/validation`

## Milestone Truth Table

### Trustworthy as Complete

- `M01-M07`
  - discovery, soll, research, and entry-policy definition work remain valid

- `M08`
  - valid in substance because entry continuity and key-gated registration are now implemented

- `M09-M11`
  - valid as planning/discovery baseline

### Complete but Superseded by Stronger Target

- `M12`
  - spread-family polish happened, but later evolved into the stronger `book-scene` page model
  - treat as `complete but superseded`

### Completed in Realign Wave

- `M16`
  - character-sheet focus route now lives in the same page-native book family

- `M20`
  - play workspace route now lives in the same page-native book family

## True Program Position

The project is no longer honestly described as `M20 incomplete`, but it is also not honestly described as `fully polished`.

The more accurate position is:

- foundation and entry family: complete
- spread family: implemented and live in the new model
- focus/workspace family: realigned and live in the same family
- remaining work: polish, validation, and consolidation

Operationally, that places the project in:

- `post-realign`
- `pre-polish-wave`

## Immediate Next Plan Position

Current active development should be treated as:

1. `Polish Wave P1`
   - normalize spacing, sticky ribbon behavior, motion, and small-screen behavior

2. `Polish Wave P2`
   - deepen the in-book interactions and strengthen the page-turn / zoom feel

3. `Consolidation Wave P3`
   - decide how deeply focus/workspace routes should unify with the shared book runtime

## Recommended Plan Reset

Do not continue pretending the old ledger alone is enough.

Use this reframing:

- `Completed Core`
  - M01-M12 concept + spread/book-scene rollout

- `Completed Realign`
  - character-sheet focus
  - play workspace

- `Current Development Stage`
  - post-realign polish and consolidation

## Decision

From this point onward, progress should be reported against:

- `spread/book-scene live quality`
- `focus/workspace polish`
- `cross-route consolidation`

instead of repeating the old statement that `M01-M20` alone are the useful story.
