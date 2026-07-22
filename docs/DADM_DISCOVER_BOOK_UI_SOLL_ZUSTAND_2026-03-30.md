# DAD-M Discover: Book UI Soll-Zustand

Date: 2026-03-30
Phase: DISCOVER
Scope: Target state for a system-wide animated spellbook UI
Status: complete

## Objective

Define the intended product state for carrying the animated book/pergament theme across the whole VTT without collapsing usability.

## Design Intent

The application should feel like one magical book, not a login gimmick plus unrelated app screens. The book metaphor must become the product’s navigation language, visual shell, and content framing system.

## Target Product Model

### 1. The VTT becomes a persistent spellbook shell

Every major route should feel like a page or section inside the same book:

- login
- dashboard
- campaigns
- characters
- lobby
- registration / signup
- admin surfaces where appropriate

The shell should contribute:

- cover / spine / page-edge framing
- parchment materials
- chapter tabs / bookmarks
- page-turn transitions between route-level destinations
- consistent decorative hierarchy

### 2. The product needs more than one book mode

A single fixed-size open book is not enough. The system needs at least three route modes.

#### Mode A: Cover / Opening mode

Use for:
- login
- splash-like entry moments

Characteristics:
- theatrical opening
- constrained content
- strong ornament
- clear first impression

#### Mode B: Reading spread mode

Use for:
- dashboard
- campaigns
- characters
- list/detail views
- profile/settings-like pages

Characteristics:
- two-page spread on large screens
- single-page fallback on smaller screens
- visible spine/gutter
- page tabs/bookmarks
- generous parchment content area

#### Mode C: Focused page / zoom mode

Use for:
- character sheet/editor
- play/tabletop
- any dense interface that needs significant working area

Characteristics:
- visually still inside the spellbook universe
- but effectively “zoomed into the parchment”
- shell chrome reduces
- content surface expands
- route keeps book identity via frame, tabs, page-edge cues, page-turn entry/exit

This is the critical answer to the space problem: some pages must visually read as “inside the book,” while functionally getting more usable paper area.

## Soll-Zustand by Route Type

### Login

- Keep the dramatic opening.
- Keep the smaller theatrical shell.
- Do not let login define the scale rules for the whole app.

### Dashboard / Campaigns / Characters

- Use reading spread mode.
- Left and right pages can hold:
  - navigation and summary
  - content grid and actions
- On smaller screens these collapse into a single readable parchment page.

### Character Sheet / Editor

- Use focused page mode.
- Preserve book identity, but prioritize readable forms, dense stats, and editing workflows.

### Play / Tabletop

- Treat the map/tabletop as an allowed dense workspace inside a parchment-framed environment.
- Do not force the map to obey the small-book proportions.
- Use parchment shelling for side panels, toolbars, trays, inspector panels, and section transitions.

## Required Target Traits

### Visual

- Persistent parchment identity
- stronger page-edge, margin, and paper depth cues
- visible chaptering / section markers
- consistent typography and tokenized materials

### Interaction

- route transitions feel like page turns or chapter shifts
- local interactions are quicker and subtler than route transitions
- shell never blocks form use or dense workflows

### Responsive

- desktop: spread or focused page based on route type
- tablet: reduced spread or focused page
- mobile: one parchment page, simplified shell chrome, motion-reduced path available

### Accessibility

- zoom/reflow must remain usable
- reduced motion must be first-class
- keyboard use cannot be trapped by theatrics

## Non-Goals

- Not every screen needs a literal two-page open book at all times.
- Not every interaction should trigger a dramatic page-turn.
- The play/map screen should not be artificially shrunk just to preserve a decorative metaphor.

## Product Decision Statement

The target is not “mini-book everywhere.”

The target is:

- one spellbook design language
- multiple shell modes
- route-level page identity
- parchment-first usability

## Discover Conclusion

The correct Soll-Zustand is a shell system, not a single component. The book metaphor must scale from dramatic entry to readable spread to zoomed work surface.

## Next Step

Translate the Soll-Zustand into best-practice constraints from primary sources.
