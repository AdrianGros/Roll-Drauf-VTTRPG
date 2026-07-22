# DAD-M Apply: Book Shell

Date: 2026-03-30
Phase: APPLY
Scope: Binding design decisions for a system-wide spellbook shell
Status: approved

## Objective

Convert the four Discover artifacts into a binding implementation contract for the book-shell rollout.

## Decision Summary

The VTT will not reuse the current login book as a universal layout component.

The approved target is a shared spellbook shell system with route modes:

- `cover`
- `spread`
- `focus`

This shell system will be applied progressively across the server-rendered Flask templates.

## Binding Design Decisions

### 1. Shell and content are separate layers

Approved:

- shell chrome handles:
  - cover/spine/page edges
  - bookmarks/tabs
  - route-level page-turn transitions
  - parchment framing
- content surfaces handle:
  - forms
  - grids
  - lists
  - editors
  - map/workspace panels

Rejected:

- deeply nesting dense application content directly inside the fragile 3D shell stack
- making the current login card geometry the universal page area

### 2. The product uses multiple route modes

#### `cover`

Use for:

- login

Characteristics:

- strongest expressive motion
- smallest, most theatrical shell
- entry-only treatment

#### `spread`

Use for:

- dashboard
- campaigns
- characters
- register
- signup
- lobby
- admin asset manager

Characteristics:

- two-page spread on large screens
- single-page parchment fallback on smaller screens
- strong book identity
- moderate data density

#### `focus`

Use for:

- character-sheet
- play

Characteristics:

- “zoom into the parchment”
- shell chrome reduced
- usable writing/work area expanded
- page-turn retained at route boundaries, not on every local interaction

### 3. Play is an explicit workspace exception

Approved:

- the tabletop/map surface is allowed to remain a dense 2D work surface
- side panels, trays, and inspectors should become parchment/book artifacts
- route entry and exit should still belong to the spellbook language

Rejected:

- shrinking the play surface to fit a decorative open-book proportion

### 4. Motion policy is split between expressive and productive

Approved:

- expressive motion:
  - cover open
  - route-to-route page turn
  - chapter/section transitions
- productive motion:
  - tabs
  - drawers
  - hover states
  - validation
  - local disclosure
  - dense UI interactions

### 5. Reflow and reduced motion are hard requirements

Approved:

- non-exception pages must remain usable at narrow widths
- mobile mode collapses to a single parchment page
- reduced-motion users must get a low-motion or near-instant transition path

Rejected:

- fixed-width desktop-only shell assumptions
- mandatory theatrical motion

## Route Classification Matrix

| Route / Template | Approved Mode | Notes |
|---|---|---|
| `login.html` | `cover` | keep dramatic entry treatment |
| `dashboard.html` | `spread` | first-wave conversion |
| `campaigns.html` | `spread` | first-wave conversion |
| `characters.html` | `spread` | first-wave conversion |
| `register.html` | `spread` | second wave |
| `signup.html` | `spread` | second wave |
| `lobby.html` | `spread` | second wave |
| `admin/asset_manager.html` | `spread` | second wave, if admin UX stays aligned |
| `character-sheet.html` | `focus` | third wave |
| `play.html` | `focus` | fourth wave, workspace exception |

## Implementation Contract

### Shared files to introduce

- `vtt_app/static/css/book-shell.css`
- `vtt_app/static/css/book-page.css`
- `vtt_app/static/js/book-shell.js`
- `vtt_app/static/js/book-routes.js`
- `vtt_app/templates/partials/book_shell.html`
- `vtt_app/templates/partials/book_page_frame.html`

### Shared responsibilities

#### `book-shell.css`

- shell chrome
- outer book framing
- spine/page-edge/bookmark visuals
- route-mode shell variants

#### `book-page.css`

- page surface
- spread/focus/page-width rules
- folio/page margins/gutters
- parchment content containers

#### `book-shell.js`

- shell bootstrapping
- route-level transitions
- reduced-motion handling
- shell-state hooks

#### `book-routes.js`

- route metadata registry
- shell mode lookup
- section labels / chapter identity
- transition policy

#### partial templates

- server-rendered shell wrapper
- page frame primitives
- consistent structure across route templates

## Wave Plan

### Wave 1: shell primitives + spread pilot

Approved scope:

- create shared shell and page primitives
- convert:
  - `dashboard.html`
  - `campaigns.html`
  - `characters.html`

Reason:

- these routes are broad enough to test spread mode
- these routes are simpler than `play.html`
- they validate whether the shell scales beyond login

### Wave 2: auth-secondary and lobby routes

Approved scope:

- convert:
  - `register.html`
  - `signup.html`
  - `lobby.html`
  - optionally `admin/asset_manager.html`

### Wave 3: focus-mode editor/read surfaces

Approved scope:

- convert `character-sheet.html`
- if needed, split sheet and editor submodes

### Wave 4: tabletop integration

Approved scope:

- convert `play.html` into focus/workspace mode
- adapt side panels/toolbars to parchment shelling
- preserve dense map surface

## Acceptance Criteria

### Shell-level acceptance

- one shared shell codepath exists for non-login routes
- route metadata determines shell mode
- reduced-motion path exists
- shell does not trap focus or block form interaction

### Spread-mode acceptance

- desktop renders a convincing two-page reading layout
- tablet/mobile collapse to one readable parchment page
- content width is materially larger than current login page width
- dashboard/campaigns/characters remain fully usable without horizontal overflow in normal tasks

### Focus-mode acceptance

- content surface is meaningfully larger than spread mode
- route still reads as part of the spellbook system
- dense workflows remain usable without decorative compression

### Motion acceptance

- route transitions use transform/opacity-based motion
- local interactions remain shorter and quieter than route transitions
- reduced-motion users get a non-theatrical path

## Risks Accepted

- Wave 1 introduces cross-template structural changes, not only styling
- the current login-specific book scene may later need refactoring to converge with the shared shell runtime
- full consistency will not exist until all waves complete

## Risks Rejected

- no attempt to push `play.html` into Wave 1
- no attempt to solve all routes with one fixed-size open-book component
- no premature SPA migration

## Deploy Boundary

This Apply decision authorizes only the following next deploy track:

- shared shell primitives
- Wave 1 spread pilot
- no live main-site proofing for each micro-step

The request-budget constraint means implementation should rely on local/dev rendering and bundled proof passes rather than repeated production-site hits.

## Next Allowed Step

`DEPLOY Wave 1 Book Shell`

Bounded scope:

1. create shared shell primitives
2. convert `dashboard.html`
3. convert `campaigns.html`
4. convert `characters.html`
5. leave `play.html` untouched
