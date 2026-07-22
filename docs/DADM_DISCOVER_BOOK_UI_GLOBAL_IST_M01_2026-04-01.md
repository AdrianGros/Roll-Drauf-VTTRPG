# DAD-M Discover: Book UI Global IST (M01)

Date: 2026-04-01
Milestone: M01
Phase: DISCOVER
Status: approved

## Goal

Freeze the actual starting baseline for the 20-milestone Book UI rollout.

## Baseline Summary

Current route classes:

- `cover`:
  - `login.html`
- `spread`:
  - `dashboard.html`
  - `campaigns.html`
  - `characters.html`
  - `signup.html`
  - `register.html`
  - `lobby.html`
- `focus` not yet implemented as intended:
  - `character-sheet.html`
  - `play.html`

Current shell/runtime assets:

- `vtt_app/static/css/book-shell.css`
- `vtt_app/static/css/book-page.css`
- `vtt_app/static/js/book-shell.js`
- `vtt_app/static/js/book-routes.js`
- `vtt_app/static/css/book-scene.css`
- `vtt_app/static/js/book-scene.js`

## Findings

### F-01

A reusable non-login shell already exists and is active on the main spread routes.

### F-02

Login remains a separate cover implementation with 3D injection and should be treated as a deliberate exception until proven otherwise.

### F-03

The largest remaining delivery gap has moved from spread routes to:

- focus-mode routes
- shell markup reuse via partials
- play/workspace integration

### F-04

The repo already contains enough architecture and discovery material to begin milestone orchestration without re-opening foundational ambiguity.

## Evidence

- [DADM_DISCOVER_BOOK_UI_IST_ZUSTAND_2026-04-01.md](/home/admin/projects/roll-drauf-vtt/docs/DADM_DISCOVER_BOOK_UI_IST_ZUSTAND_2026-04-01.md)
- [DADM_APPLY_BOOK_SHELL_2026-03-30.md](/home/admin/projects/roll-drauf-vtt/docs/DADM_APPLY_BOOK_SHELL_2026-03-30.md)
- [dashboard.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/dashboard.html)
- [campaigns.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/campaigns.html)
- [characters.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/characters.html)
- [signup.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/signup.html)
- [register.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/register.html)
- [lobby.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/lobby.html)
- [play.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/play.html)

## Decision

M01 is complete.

The approved baseline for the remaining program is:

- spread-mode family exists and is usable
- focus-mode family remains the highest-value implementation gap
- future milestone work should continue from this baseline instead of re-auditing the same routes

## Approval

- scope_kept: yes
- live_check_used: no
- residual_risks: none beyond documented program scope
- approved_to_proceed: yes
