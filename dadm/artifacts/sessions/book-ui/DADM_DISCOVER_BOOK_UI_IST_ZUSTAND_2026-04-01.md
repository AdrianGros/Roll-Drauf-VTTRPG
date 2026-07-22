# DAD-M Discover: Book UI Ist-Zustand

Date: 2026-04-01
Phase: DISCOVER
Scope: Real frontend baseline after the current spread-shell rollout
Status: complete

## Objective

Capture the actual repository state after the initial book-shell rollout, not the earlier pre-Wave-1 baseline.

## Evidence Reviewed

- [login.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/login.html)
- [dashboard.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/dashboard.html)
- [campaigns.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/campaigns.html)
- [characters.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/characters.html)
- [signup.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/signup.html)
- [register.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/register.html)
- [lobby.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/lobby.html)
- [play.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/play.html)
- [book-scene.css](/home/admin/projects/roll-drauf-vtt/vtt_app/static/css/book-scene.css)
- [book-scene.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/book-scene.js)
- [book-shell.css](/home/admin/projects/roll-drauf-vtt/vtt_app/static/css/book-shell.css)
- [book-page.css](/home/admin/projects/roll-drauf-vtt/vtt_app/static/css/book-page.css)
- [book-shell.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/book-shell.js)
- [book-routes.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/book-routes.js)
- [DADM_APPLY_BOOK_SHELL_2026-03-30.md](/home/admin/projects/roll-drauf-vtt/docs/DADM_APPLY_BOOK_SHELL_2026-03-30.md)

## Current State Summary

The repo is no longer in the old “login-only book effect” state.

It is now in a transitional post-Wave-2 state:

- login uses a separate theatrical 3D book scene
- dashboard, campaigns, characters, signup, register, and lobby now use the shared spellbook shell
- character-sheet, play, and admin surfaces still sit outside that shared system

## Findings

### F-01 — A real shell system now exists for non-login routes

The following shared files are present and wired:

- `book-shell.css`
- `book-page.css`
- `book-shell.js`
- `book-routes.js`

This confirms that the implementation direction approved in APPLY has started, even though it is not yet complete.

### F-02 — Spread mode now covers the primary non-play routes

The following templates now share the same shell primitives:

- `dashboard.html`
- `campaigns.html`
- `characters.html`
- `signup.html`
- `register.html`
- `lobby.html`

These routes now share:

- `body.book-shell-app`
- `book-shell-frame`
- `book-shell-ribbon`
- `book-spread`
- left-page / right-page structure
- route metadata via `data-book-route`
- route-turn scripting via `book-shell.js`

This is now a real product-shell rollout, not just a first proof on one or two pages.

### F-03 — Login still uses a separate architecture

The login route remains powered by:

- `book-scene.css`
- `book-scene.js`
- DOM injection into `#login-content`

That is intentional for `cover` mode, but it also means login and non-login pages still do not share one unified template structure.

### F-04 — Route coverage is stronger, but still incomplete

Current route groups:

- `cover` implemented:
  - `login.html`
- `spread` implemented:
  - `dashboard.html`
  - `campaigns.html`
  - `characters.html`
  - `signup.html`
  - `register.html`
  - `lobby.html`
- `focus` still old-style:
  - `character-sheet.html`
  - `play.html`
- second-wave admin surface still old-style:
  - `admin/asset_manager.html`

### F-05 — Shared shell exists, but shared partials do not

The repo still has duplicated shell markup inside each converted template.

Missing pieces from the approved contract:

- `vtt_app/templates/partials/book_shell.html`
- `vtt_app/templates/partials/book_page_frame.html`

This means the design language is improving faster than the template architecture.

### F-06 — Focus mode is declared, but not yet expressed in the UI

`book-routes.js` already declares `focus` for:

- `/character-sheet`
- `/play`

But the corresponding templates are still conventional dense application layouts.

So the metadata model is ahead of the actual route implementations.

### F-07 — The strongest remaining gap has moved to focus-mode and partial reuse

The main break in product continuity is now:

- untouched focus-mode pages
- missing shared partial templates
- the separate login architecture boundary

The next step should therefore focus on template reuse and true focus-mode implementation, not on revisiting the spread-mode direction.

## Route Status Matrix

| Route | Intended Mode | Current Reality |
|---|---|---|
| `login.html` | `cover` | implemented with separate 3D scene |
| `dashboard.html` | `spread` | implemented in shared shell |
| `campaigns.html` | `spread` | implemented in shared shell |
| `characters.html` | `spread` | implemented in shared shell |
| `signup.html` | `spread` | implemented in shared shell |
| `register.html` | `spread` | implemented in shared shell |
| `lobby.html` | `spread` | implemented in shared shell |
| `character-sheet.html` | `focus` | still old standalone page |
| `play.html` | `focus` | still old tabletop shell |

## Discover Conclusion

The repo has crossed the line from concept to system for nearly all spread-mode routes.

The real Ist-Zustand on 2026-04-01 is:

- book language exists as a reusable shell
- all primary spread-mode routes now use it
- focus-mode routes and template partialization are the largest remaining continuity gap

## Next Step

Continue rollout in this order:

1. introduce shared template partials to reduce duplicate shell markup
2. implement true `focus` mode for `character-sheet.html` and `play.html`
3. decide whether login remains a dedicated cover implementation or should share more shell structure with the rest of the app
