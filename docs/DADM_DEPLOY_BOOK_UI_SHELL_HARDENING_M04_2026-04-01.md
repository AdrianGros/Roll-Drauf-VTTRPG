# DAD-M Deploy: Book UI Shell Hardening (M04)

Date: 2026-04-01
Milestone: M04
Phase: DEPLOY
Status: approved

## Goal

Apply the approved shell hardening slice to the shared runtime without broadening the route surface.

## Deployment Scope

- `vtt_app/static/js/book-shell.js`
- `vtt_app/static/css/book-shell.css`

## Planned Verification

- static diff review
- `git diff --check`
- one bounded live verification only if needed later in the milestone

## Applied Changes

- hardened shell runtime state in [book-shell.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/book-shell.js)
- added navigation guards against same-route and duplicate route turns
- added shell state classes and dataset signaling for loading, ready, and navigating
- added reduced-motion shell signaling
- added visible active-route styling and navigation lock styling in [book-shell.css](/home/admin/projects/roll-drauf-vtt/vtt_app/static/css/book-shell.css)

## Verification

- scope review: passed
- file-scope rule: passed
- `git diff --check`: passed
- live verification: not used in this milestone

## Decision

M04 deploy scope is accepted.
