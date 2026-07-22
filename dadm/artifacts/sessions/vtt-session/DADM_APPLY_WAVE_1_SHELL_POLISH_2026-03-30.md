# DAD-M Apply: Wave 1 Shell Polish

Date: 2026-03-30
Phase: APPLY
Track: BOOK-SHELL-WAVE-1-POLISH
Status: approved

## Objective

Convert the `conditional-pass` result from Wave 1 monitor into a narrow, binding polish contract.

This track exists to close the real open finding from monitor without reopening Wave 1 layout architecture.

## Input Finding

From `DADM_MONITOR_WAVE_1_BOOK_SHELL_2026-03-30.md`:

- current-route highlighting is not visibly expressed in Wave-1 navigation

The shared shell can already compute active route state, but the converted headers do not expose a route-marked element for the current page.

## Decision Summary

Wave 1 Shell Polish will:

- make the active route visibly present in shell chrome
- reuse the existing `BookShell` route-state system
- stay strictly presentation-level

Wave 1 Shell Polish will not:

- redesign the spread geometry
- alter page-content allocation between left and right pages
- touch `play.html`
- introduce live-domain proof dependency

## Binding Decisions

### 1. The active route must be visible in header-level navigation

Approved:

- each Wave-1 page must expose a visible current-route marker in the shell header area
- the marker must be driven by route metadata, not hardcoded visual hacks
- the current route should read as part of a small route rail or chapter navigation strip

Rejected:

- relying only on folio numbers or page title text as route orientation
- leaving active-state logic hidden in JS without visible UI output

### 2. Reuse the existing route-state mechanism

Approved:

- continue to use `data-book-route`
- continue to use `BookShell.updateRouteChrome()` active-state logic
- surface `is-active` / `aria-current="page"` through visible chrome

Rejected:

- adding a second route-highlighting system
- page-specific custom JS for each Wave-1 route

### 3. Polish scope stays presentational

Approved:

- template header/nav adjustments
- shell CSS additions for active route presentation
- optional metadata-chip refinement if it supports the same orientation goal

Rejected:

- backend changes
- API changes
- DB changes
- content model changes

### 4. Campaign content richness is explicitly deferred

Approved:

- the low-severity campaign mock-data limitation remains outside this polish track
- richer campaign-grid validation belongs to a later dedicated test-environment proof step

Rejected:

- broadening this polish track into a content-data or ownership-filter debugging pass

## Implementation Contract

### Files allowed in scope

- `vtt_app/templates/dashboard.html`
- `vtt_app/templates/campaigns.html`
- `vtt_app/templates/characters.html`
- `vtt_app/static/css/book-shell.css`
- `vtt_app/static/js/book-shell.js`

### Files explicitly out of scope

- `vtt_app/static/js/book-routes.js`
  - unless a tiny metadata addition becomes strictly necessary
- `vtt_app/static/css/book-page.css`
  - unless a very small support rule is required
- `play.html`
- auth/backend/python files

## Acceptance Criteria

Polish is ready for monitor when all of the following are true:

- each Wave-1 page visibly shows its own active route in shell navigation
- active route state is consistent with `aria-current="page"` or equivalent route-state output
- desktop and mobile proofs still render the shell cleanly
- no new page errors or console errors are introduced
- character modal still works on `characters.html`
- no live main-domain proof is required for this track

## Recommended Next Step

Proceed to:

- `DEPLOY Wave 1 Shell Polish`
