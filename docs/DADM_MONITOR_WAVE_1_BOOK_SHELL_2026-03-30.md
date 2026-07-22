# DAD-M Monitor: Wave 1 Book Shell

Date: 2026-03-30
Phase: MONITOR
Track: BOOK-SHELL-WAVE-1
Decision: conditional-pass

## Scope Reviewed

Reviewed Wave 1 shell conversion for:

- `vtt_app/templates/dashboard.html`
- `vtt_app/templates/campaigns.html`
- `vtt_app/templates/characters.html`

Shared shell layer reviewed:

- `vtt_app/static/css/book-shell.css`
- `vtt_app/static/css/book-page.css`
- `vtt_app/static/js/book-routes.js`
- `vtt_app/static/js/book-shell.js`

`play.html` remained intentionally out of scope.

## Evidence

Static validation:

- `xmllint --html --noout` passed for all three Wave-1 templates
- no `BookScene`, `book-scene.css`, or `book-animation.js` references remain in the Wave-1 templates
- shell markers and folios are present on all three routes

Local runtime proof:

- local app served on `http://127.0.0.1:5012`
- proof used mocked API responses in Playwright to avoid live-domain request consumption
- desktop and mobile screenshots were generated for all three Wave-1 routes
- no page errors or console errors were observed during the local Playwright pass

Proof artifacts:

- `docs/proofs/wave1-book-shell-proof.json`
- `docs/proofs/wave1-dashboard-desktop.png`
- `docs/proofs/wave1-dashboard-mobile.png`
- `docs/proofs/wave1-campaigns-desktop.png`
- `docs/proofs/wave1-campaigns-mobile.png`
- `docs/proofs/wave1-characters-desktop.png`
- `docs/proofs/wave1-characters-mobile.png`

## What Passed

- all three routes resolve to `body[data-book-mode="spread"]`
- shell frame and spread layout render on desktop and mobile
- folio markers render as expected:
  - dashboard `1/2`
  - campaigns `3/4`
  - characters `5/6`
- dashboard keeps both campaign and character surfaces inside the right page
- campaigns keeps tabs on the left page and detail panel on the right page
- characters keeps filters on the left page and roster on the right page
- character creation modal still opens above the shell
- runtime was clean under the mocked local proof run

## Findings

### Medium

1. Current-route highlighting is not actually visible in Wave 1 navigation.

The shell logic can mark `[data-book-route]` elements with `aria-current="page"`, but the converted headers only expose sibling-route buttons. There is no route-marked button for the current page on:

- `dashboard.html`
- `campaigns.html`
- `characters.html`

Result: the route-chrome active-state capability exists in code but does not surface in the Wave-1 UI. This does not break navigation, but it leaves the shell metadata partially unexpressed.

### Low

1. The local campaigns proof used mocked sample data that did not fully satisfy the page's existing ownership filtering, so the right-page campaign grid screenshot is structurally valid but not content-rich.

This is acceptable for shell validation, but not the final proof for campaign-content presentation quality.

2. The proof run was local and mocked by design.

That matches the current request-budget constraint, but it is still distinct from a later integrated proof against a dedicated test environment.

## Decision Rationale

`conditional-pass` is appropriate.

Wave 1 successfully establishes the shared shell, keeps the approved route scope, survives desktop and mobile proof, and does not introduce observed runtime errors in the local monitored pass. The remaining gap is not a shell failure but a polish/integration issue: current-route highlighting is not yet visible in the header navigation design.

## Recommended Next Step

Proceed to a narrow follow-up track for shell polish:

- add an explicit current-route indicator or chapter marker per Wave-1 page
- optionally move to a dedicated test environment for richer integrated proof without touching the main domain
