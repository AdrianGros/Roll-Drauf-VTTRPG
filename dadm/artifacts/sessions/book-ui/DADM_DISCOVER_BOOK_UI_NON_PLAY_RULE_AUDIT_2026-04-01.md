# DAD-M Discover: Non-Play Route Audit Against Book UI Layout Rules

Date: 2026-04-01
Scope: `login`, `signup`, `register`, `dashboard`, `campaigns`, `characters`, `character-sheet`, `lobby`
Excluded: `play`
Reference: [DADM_SOLL_BOOK_UI_LAYOUT_RULES_2026-04-01.md](/home/admin/projects/roll-drauf-vtt/docs/DADM_SOLL_BOOK_UI_LAYOUT_RULES_2026-04-01.md)

## Audit Goal

Check every non-`play` route against the updated centered-book contract.
Main question:
Which routes already behave like true `BOOK_MODE` pages, and which routes still behave like older shell pages or transitional layouts?

## Summary Status

### Strongly aligned

- `login`
- `dashboard`
- `campaigns`
- `characters`

### Partially aligned

- `character-sheet`

### Weakly aligned / older shell family

- `signup`
- `register`
- `lobby`

## Route Findings

### `login`

Status: strong alignment

What is already right:

- centered persistent book object
- explicit left/right spread
- visible book shell and page-turn runtime
- login and welcome page rendered as a first spread
- login success uses book-internal navigation instead of instant route replace

Remaining gaps:

- final visual polish on exact spread balance and turn feel
- still needs final production-quality tuning of paper symmetry and shadow subtlety

### `dashboard`

Status: strong alignment

What is already right:

- boots through `BookScene`
- lives inside the centered book object
- uses explicit spread composition
- respects shared ribbon and in-book navigation language
- lower shared band exists as a distinct spread-level zone

Remaining gaps:

- route template still contains older fallback shell markup underneath the scene bootstrap
- repo contains dual concepts: current `BookScene` spread runtime and older `book-shell` framing artifacts

### `campaigns`

Status: strong alignment

What is already right:

- boots through `BookScene`
- explicit left/right spread logic is present
- campaign shelf and companion notes are separated across the spread
- navigation remains in-book

Remaining gaps:

- template still keeps legacy spread markup for fallback/classic mode
- detail density and card alignment still need later polish against the symmetry rule

### `characters`

Status: strong alignment

What is already right:

- boots through `BookScene`
- archive shelf and companion page are separated across the spread
- current route uses the shared centered-book runtime

Remaining gaps:

- legacy/fallback spread markup still exists in the route template
- archive grid vs. guide content can still be better balanced for strict peer symmetry

### `character-sheet`

Status: partial alignment

What is already right:

- stays in the same visual family
- uses shared ribbon, chips, paper language, and focus framing
- does not fall back to a generic app layout

What is not yet aligned:

- it is not rendered inside the same persistent `BookScene` runtime as `dashboard/campaigns/characters`
- it behaves like a focus route in the family, but not yet like a first-class page in the same mounted book object
- focus composition is still based on older shell/focus framing instead of the newer spread/focus scene architecture

Interpretation:

`character-sheet` is visually related, but architecturally still on the older branch.

### `signup`

Status: weak alignment

What is already right:

- parchment/book styling is present
- readable two-page shell exists
- motion is calmer and form-first

What is not aligned:

- route is not in the persistent centered-book scene
- uses older `book-shell` spread layout instead of `BookScene`
- still feels like a styled shell page rather than a true page inside the mounted book object

Interpretation:

`signup` belongs to the same world, but not yet to the same runtime contract.

### `register`

Status: weak alignment

What is already right:

- same material system and onboarding tone
- uses readable book-shell spread framing

What is not aligned:

- not part of the persistent `BookScene`
- still treated as a standalone shell route
- not yet mapped to the newer centered-book geometry and page-turn contract

### `lobby`

Status: weak alignment

What is already right:

- still visibly within the book family
- uses spread framing and shell styling

What is not aligned:

- not yet realigned into the persistent `BookScene`
- remains an older shell spread rather than a current book-mode page
- routing and lifecycle are not yet unified with the stronger `dashboard/campaigns/characters` runtime

## Rule-Level Audit

### Rule: centered persistent book object

Pass:

- `login`
- `dashboard`
- `campaigns`
- `characters`

Partial:

- `character-sheet`

Fail / older shell path:

- `signup`
- `register`
- `lobby`

### Rule: spine as structural center

Pass:

- `login`
- `dashboard`
- `campaigns`
- `characters`

Partial:

- `character-sheet`

Weak:

- `signup`
- `register`
- `lobby`

### Rule: explicit left/right page geometry

Pass:

- `login`
- `dashboard`
- `campaigns`
- `characters`

Partial:

- `character-sheet` as focus reinterpretation

Older implementation:

- `signup`
- `register`
- `lobby`

### Rule: non-play navigation reads as book navigation

Pass:

- `login -> dashboard -> campaigns -> characters`

Partial:

- `character-sheet`

Weak:

- `signup`
- `register`
- `lobby`

## Main Architectural Finding

The current non-`play` surface is split across two families:

1. `BookScene` family
   `login`, `dashboard`, `campaigns`, `characters`

2. older `book-shell` family
   `signup`, `register`, `lobby`, and still partly `character-sheet`

This is now the main source of inconsistency.
The biggest remaining gap is no longer theme styling.
It is runtime fragmentation.

## Priority Gaps

### P1

Move `signup`, `register`, and `lobby` onto the same persistent centered-book runtime as the main spread family.

### P2

Realign `character-sheet` from visual-family compliance to full runtime compliance.

### P3

After runtime unification, run a strict symmetry and spacing pass across all non-`play` routes.

## Recommendation

Do not spend the next wave on isolated per-route cosmetics first.
The highest-value next step is:

1. unify the remaining non-`play` routes under the `BookScene` contract
2. then run one symmetry/spacing/overflow polish pass across the whole non-`play` family

## Honest Current Position

The project now has a real book-mode center of gravity.
But non-`play` routes are not yet fully unified under one architectural book runtime.
That is the real remaining alignment problem.
