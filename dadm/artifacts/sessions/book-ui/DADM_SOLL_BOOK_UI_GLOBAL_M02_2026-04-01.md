# DAD-M Soll: Book UI Global Target Model (M02)

Date: 2026-04-01
Milestone: M02
Phase: SOLL
Status: approved

## Goal

Define the binding target model for the full Book UI program so future milestones optimize toward one system instead of a series of attractive but disconnected screens.

## Target Product Statement

The VTT should feel like one spellbook product with multiple reading modes, not a login gimmick followed by unrelated app pages.

The correct target is:

- one visual language
- one route-aware shell system
- multiple route modes
- productive surfaces inside the book metaphor

## Binding Target Assertions

### T-01 — The spellbook is a system, not a component

The final UI is not “the login book reused everywhere”.

It is a system composed of:

- cover treatment
- spread treatment
- focus treatment
- workspace exception handling

### T-02 — Route class determines shell mode

Every major route must explicitly belong to one shell mode.

Approved route classes:

- `cover`
- `spread`
- `focus`
- `focus + workspace exception`

### T-03 — Cover mode is reserved for threshold moments

Use `cover` only where theatrical entry adds value and does not block productivity.

Primary route:

- `login.html`

Characteristics:

- strongest motion
- smallest usable content footprint
- high ornament
- entry-only intensity

### T-04 — Spread mode is the default for readable product pages

Use `spread` for routes whose job is orientation, browsing, setup, summary, or moderate-density management.

Primary routes:

- `signup.html`
- `register.html`
- `dashboard.html`
- `campaigns.html`
- `characters.html`
- `lobby.html`
- admin browsing/config surfaces where compatible

Characteristics:

- two-page layout on large screens
- one-page parchment fallback on narrow widths
- visible chapter identity
- readable rather than theatrical density

### T-05 — Focus mode is the zoomed writing surface

Use `focus` where the user needs materially more working room than spread mode should provide.

Primary routes:

- `character-sheet.html`
- similar editor-heavy routes

Characteristics:

- reduced shell chrome
- larger parchment work plane
- still recognizably inside the spellbook

### T-06 — Play is a justified workspace exception

The tabletop must not be forced into decorative open-book proportions.

For `play.html`, the target is:

- book identity at route boundary and shell framing
- parchment treatment for side panels, trays, inspectors, toolbars
- a dense central map/workspace that stays productively large

### T-07 — Shell and content must stay separated

The outer shell owns:

- chapter framing
- spine/gutter language
- ribbon/bookmark cues
- route transitions

The inner content owns:

- forms
- cards
- lists
- editors
- tables
- tabletop controls

Dense content must not be deeply nested inside fragile 3D scene mechanics.

### T-08 — Motion is expressive only at route significance

Expressive motion belongs to:

- cover open
- route transition
- chapter shift

Productive interactions such as tabs, filters, disclosure, validation, hover, and editor control changes must remain restrained.

### T-09 — Reflow is mandatory outside justified workspace exceptions

Non-exception routes must remain usable at narrow widths and high zoom.

Implications:

- spread routes collapse to one parchment column
- focus routes reflow where possible
- only the genuine 2D workspace may retain exceptional density

### T-10 — Shared structure is part of the target, not optional polish

The final target includes architectural reuse, not only visual similarity.

That means the program should end with:

- shared route metadata
- shared shell runtime
- shared page-surface primitives
- shared partials for repeated shell markup

## Route Classification Matrix

| Route | Target Mode | Decision |
|---|---|---|
| `login.html` | `cover` | keep separate threshold treatment unless later simplification is proven better |
| `signup.html` | `spread` | productive auth page inside shell |
| `register.html` | `spread` | productive key redemption page inside shell |
| `dashboard.html` | `spread` | orientation and summary spread |
| `campaigns.html` | `spread` | browse/manage spread |
| `characters.html` | `spread` | browse/create spread |
| `lobby.html` | `spread` | staging and join/control spread |
| `character-sheet.html` | `focus` | larger writing/editor surface |
| `play.html` | `focus + workspace exception` | parchment shell around a productive map workspace |
| `admin/asset_manager.html` | `spread` unless proven otherwise | only if the density remains manageable |

## Decisions No Longer Open

These points are already settled by prior project documentation and are not re-opened by M02:

- the product should not use a single fixed-size login-book shell everywhere
- the system needs multiple shell modes
- play is an explicit workspace exception
- route metadata should remain central
- reduced motion is a hard requirement

## Approval

- scope_kept: yes
- live_check_used: no
- residual_risks: none beyond later implementation work
- approved_to_proceed: yes
