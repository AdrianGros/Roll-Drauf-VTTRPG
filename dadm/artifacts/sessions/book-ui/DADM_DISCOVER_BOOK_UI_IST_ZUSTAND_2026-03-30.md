# DAD-M Discover: Book UI Ist-Zustand

Date: 2026-03-30
Phase: DISCOVER
Scope: Current frontend state for extending the book/parchment style from login to the full VTT
Status: complete

## Objective

Document the real frontend baseline before defining a system-wide spellbook UI.

## Evidence Reviewed

- [login.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/login.html)
- [book-scene.css](/home/admin/projects/roll-drauf-vtt/vtt_app/static/css/book-scene.css)
- [book-scene.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/book-scene.js)
- [theme.css](/home/admin/projects/roll-drauf-vtt/vtt_app/static/css/theme.css)
- [components.css](/home/admin/projects/roll-drauf-vtt/vtt_app/static/css/components.css)
- [dashboard.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/dashboard.html)
- [campaigns.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/campaigns.html)
- [play.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/play.html)
- [M2_DISCOVER_Book_UI_Audit.md](/home/admin/projects/roll-drauf-vtt/M2_DISCOVER_Book_UI_Audit.md)
- [M2_VISUAL_TARGET_Reference.md](/home/admin/projects/roll-drauf-vtt/M2_VISUAL_TARGET_Reference.md)

## Current State Summary

The repo does not yet have a unified “book application shell.” It has one well-developed book scene for login, a token-based parchment theme layer, and several non-book product pages that still render as conventional full-screen application layouts.

## Findings

### 1. The login screen is the only real book-shell implementation

- The book shell lives in `book-scene.css` and `book-scene.js`.
- The shell is a fixed 3D object (`#book`) sized at `550x700`.
- The opened login content is not a full page spread. It is a small card-like content zone inside the shell.
- The actual interactive form area is even narrower than the book:
  - `.login-book-wrapper` is `232px` wide
  - sidecar copy sits separately at `118px`
- This works for auth, but not for data-dense surfaces like dashboard, campaign management, character management, or play.

### 2. The book effect is visual, not yet architectural

- `BookScene.create()` injects a shell and moves `#login-content` into it.
- `BookScene.pageTurn(url)` provides only a route-level overlay animation.
- The current navigation model is hardcoded and partial:
  - `dashboard -> campaigns -> characters`
- There is no reusable page abstraction such as:
  - left page / right page
  - single focused page
  - zoomed writing surface
  - route metadata for page-turn behavior

### 3. The theme layer exists, but adoption is inconsistent

- `theme.css` defines a parchment-and-plum token system.
- `components.css` defines reusable parchment-form/button patterns.
- `login.html` partially follows that token system.
- `dashboard.html`, `campaigns.html`, and `play.html` still ship with page-local inline styles and different visual systems.
- Result: the repo currently has theme fragments, not one coherent design system.

### 4. Current non-login pages are structurally incompatible with the current book size

- `dashboard.html` uses a broad hub layout with header, stats row, multi-card grids, and a large content container.
- `campaigns.html` uses tabs, dense cards, header actions, and broad grids.
- `play.html` uses a persistent tabletop shell with toolbar, stage, viewport, map world, and right panel.
- These pages assume wide rectangular canvases, not a 232px page body.

### 5. The current book implementation will break if generalized naively

- The current shell depends on `transform-style: preserve-3d`, `backface-visibility`, and a tightly controlled stacking context.
- The current content model uses `opacity` transitions and multiple positioned layers.
- Generalizing this pattern to dense app views without re-architecting layout modes will likely create:
  - unusable content width
  - broken focus order
  - fragile z-index interactions
  - animation/layout coupling

### 6. The current repo has no explicit distinction between “book chrome” and “work surface”

- Today, decorative shell and interactive surface are fused together.
- For a full product shell, they must separate into:
  - persistent book chrome: cover, spine, parchment context, page edges, tabs, page-turn framing
  - route work surface: forms, cards, grids, table-like structures, maps, side panels

## Constraints Discovered

### Product constraints

- Login can tolerate a small, theatrical book.
- The rest of the VTT cannot.
- The play/tabletop surface will remain a dense 2D workspace even under a parchment aesthetic.

### Technical constraints

- The stack is server-rendered HTML plus shared CSS/JS, not a modern SPA shell.
- The current book effect is written as direct DOM injection and page-level scripting.
- A system-wide rollout should preserve the current stack unless there is a deliberate decision to migrate.

### UX constraints

- The product needs more space than the current “small open book” can provide.
- The book metaphor must survive scale changes and zoom states.
- Route-to-route page-turns can be expressive.
- Within-page controls must stay productive, fast, and readable.

## Severity Assessment

- High: current page area is too small for general VTT use.
- High: current app pages are visually and structurally inconsistent with the login shell.
- High: current shell is not reusable as-is for play/dashboard/campaign management.
- Medium: navigation and page-turn logic is not generalized.
- Medium: theme adoption is partial and split across inline styles and shared tokens.
- Medium: current 3D effect may become brittle when expanded without clear shell/content separation.

## Discover Conclusion

The repo is not one step away from “book everywhere.” It is at an intermediate state:

- book-themed login shell exists
- parchment tokens exist
- major application routes still use conventional layout models

The next design work must not be “scale the login book up a little.” It must define a real shell model for:

- reading spread views
- focused single-page views
- dense workspace exceptions

## Next Step

Move to Soll-Zustand discovery and define the intended shell modes for the full VTT.
