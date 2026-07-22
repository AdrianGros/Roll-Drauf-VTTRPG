# DAD-M Deploy: Wave 1 Book Shell

Date: 2026-03-30
Phase: DEPLOY
Track: BOOK-SHELL-WAVE-1
Status: implemented

## Scope

Wave 1 converts the approved shell targets into a shared spellbook spread:

- `/dashboard`
- `/campaigns`
- `/characters`

Out of scope for this deploy:

- `/play`
- character-sheet focus workspace
- live-site proof loops against the main domain

## Implemented

Shared shell assets are now active:

- `vtt_app/static/css/book-shell.css`
- `vtt_app/static/css/book-page.css`
- `vtt_app/static/js/book-routes.js`
- `vtt_app/static/js/book-shell.js`

Wave-1 templates now use the shared shell:

- `vtt_app/templates/dashboard.html`
- `vtt_app/templates/campaigns.html`
- `vtt_app/templates/characters.html`

Behavioral changes in this deploy:

- each Wave-1 page now renders inside a two-page parchment spread
- chapter, section, and folio chrome are driven by `BookRoutes`
- route navigation now uses `BookShell.navigate(...)`
- left page acts as index/orientation surface
- right page acts as main working surface
- old page-local `BookScene` and page-load animation usage were removed from Wave 1

Page-specific outcomes:

- `dashboard.html`
  - left page holds summary, stats, and travel notes
  - right page holds recent campaigns and recent characters
- `campaigns.html`
  - left page holds title, status message, tabs, and reading guidance
  - right page holds campaign grid and detail panel
- `characters.html`
  - left page holds title, filters, and archive guidance
  - right page holds the character grid
  - existing character modal remains in place above the shell

## Evidence

Static proof completed locally without additional main-site requests:

- `xmllint --html --noout` passed for all three updated templates
- `rg` confirmed Wave-1 templates no longer reference `BookScene`, `book-scene.css`, or `book-animation.js`
- `rg` confirmed all three templates include:
  - `book-shell.css`
  - `book-page.css`
  - `book-routes.js`
  - `book-shell.js`
  - shared shell markers such as `book-shell-frame`, `book-spread`, and `data-book-folio`

Tooling note:

- `node --check` could not run because `node` is not installed in the current environment

## Open Risks

- no browser proof in this deploy step because request budget against the main site is intentionally constrained
- existing inline page CSS is still present in the converted templates and may deserve later reduction once the shell stabilizes
- `play.html` remains a separate focus-mode follow-up and is intentionally untouched

## Recommended Next Step

Proceed to `MONITOR Wave 1 Book Shell`.
