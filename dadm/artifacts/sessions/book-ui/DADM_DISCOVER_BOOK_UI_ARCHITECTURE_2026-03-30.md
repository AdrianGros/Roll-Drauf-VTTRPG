# DAD-M Discover: Book UI Architecture Options

Date: 2026-03-30
Phase: DISCOVER
Scope: Architecture options for rolling the spellbook shell through the whole VTT
Status: complete

## Objective

Identify the architecture shapes available for extending the book UI and recommend the one that fits this repo, this stack, and the discovered constraints.

## Architectural Context

- Stack is server-rendered Flask templates with shared CSS and JavaScript.
- Existing book effect is already progressive enhancement, not a framework component.
- Major routes are still independent page templates.
- The rollout target is broad and cross-cutting.

## Option A: Per-page bespoke book implementations

### Description

Each template gets its own local “book mode” HTML, CSS, and JS adaptations.

### Advantages

- fast for one page at a time
- low up-front architecture work

### Risks

- guaranteed drift between templates
- duplicated page-turn logic
- duplicated sizing logic
- repeated accessibility mistakes
- inconsistent shell behavior across routes

### Assessment

Reject as primary architecture.

This option may feel fast at first, but it will turn the spellbook into multiple unrelated implementations.

## Option B: One rigid global book wrapper for every route

### Description

Every page uses one literal open-book layout with the same dimensions and page anatomy.

### Advantages

- visually consistent
- simple mental model

### Risks

- dashboard/campaigns may fit awkwardly
- play/tabletop will not
- character/editor surfaces will become cramped
- forces the product into the login-shell proportions

### Assessment

Reject as primary architecture.

It solves branding but not usability.

## Option C: Shared spellbook shell with route modes

### Description

Build one shared shell system with route metadata and multiple display modes.

Core idea:

- one visual language
- one shell runtime
- multiple content modes per route class

### Modes

- `cover`
- `spread`
- `focus`
- optional `workspace-exception` behavior within focus mode

### Advantages

- preserves one product identity
- respects route differences
- supports phased rollout
- fits current server-rendered stack
- avoids forced SPA migration

### Risks

- needs disciplined metadata and shared partials
- requires up-front shell/content separation

### Assessment

Recommended.

This is the best fit for the repo and the discovered space problem.

## Option D: Full SPA shell migration

### Description

Replace route-level templates with one client-side application shell and page-state router.

### Advantages

- maximal control over transitions and shell persistence
- easiest place to centralize route metadata long-term

### Risks

- high rewrite cost
- broad regression surface
- not aligned with current codebase shape
- delays visual rollout behind platform migration

### Assessment

Defer.

This is not the right first move unless the product already intends a frontend platform rewrite.

## Recommended Architecture

### Recommendation

Adopt Option C: shared spellbook shell with route modes.

### Proposed Building Blocks

#### 1. Book shell layer

Shared outer frame:

- cover/spine/page edge visuals
- bookmark / chapter tab zone
- route transition overlay
- reduced-motion aware animation hooks

Possible files:

- `vtt_app/static/css/book-shell.css`
- `vtt_app/static/js/book-shell.js`

#### 2. Page surface layer

Shared page content primitives:

- parchment page
- spread layout
- focus layout
- gutter / folio / margin tokens
- page header / page footer / section marker

Possible files:

- `vtt_app/static/css/book-page.css`
- `vtt_app/templates/partials/book_shell.html`
- `vtt_app/templates/partials/book_page_frame.html`

#### 3. Route metadata layer

Each route declares:

- shell mode: `cover | spread | focus`
- chapter / section label
- whether page-turn is expressive or reduced
- whether page is a dense workspace exception

Possible file:

- `vtt_app/static/js/book-routes.js`

#### 4. Content adapters

Each existing template is adapted into the shared page surface:

- dashboard
- campaigns
- characters
- lobby
- register / signup
- play

### How play/tabletop should fit

Do not force the map into a literal book spread.

Instead:

- the route enters through a book transition
- the page frame keeps parchment identity
- controls and side panels become parchment artifacts
- the map remains a dense central work surface

This treats play as a legitimate two-dimensional workspace exception while preserving the spellbook brand.

## Rollout Sequence

### Wave 1

- lock tokens and shell primitives
- convert dashboard, campaigns, characters

### Wave 2

- convert register/signup/lobby
- add bookmarks, chapter tabs, consistent page headers/folios

### Wave 3

- convert character sheet/editor into focus mode

### Wave 4

- adapt play/tabletop into focus/workspace mode

## Architecture Decision Summary

### Adopt

- shared shell
- route metadata
- multiple shell modes
- progressive enhancement over server-rendered pages

### Avoid

- bespoke per-template shells
- one rigid fixed book size for all routes
- premature SPA migration

## Discover Conclusion

The correct architecture is not “make every page look like the login.” It is:

- one spellbook shell system
- one shared page-surface system
- route-class-based modes
- explicit exceptions for dense workspaces

## Next Step

Move to APPLY and define:

- shell mode contract
- route classification matrix
- first-wave implementation order
- acceptance criteria for spread mode and focus mode
