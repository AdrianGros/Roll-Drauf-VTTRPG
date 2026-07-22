artifact: apply-output
date: 2026-04-01
status: applied

## Scope

Realign `signup` and `register` from the legacy `book-shell` family into the persistent `BookScene` runtime.

## Changes

- extended [book-scene.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/book-scene.js) with route support for:
  - `signup`
  - `register`
- added external scene-template rendering and per-route initializer hooks in [book-scene.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/book-scene.js)
- replaced legacy standalone shells in [signup.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/signup.html) and [register.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/register.html) with `BookScene` templates
- updated [login.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/login.html) so dashboard entry no longer depends on spread index order

## Behavioral Result

- direct visits to `/signup.html` and `/register.html` now boot into the centered book runtime
- `signup` keeps the existing key-gated account creation flow
- `register` keeps the key-redemption flow and can turn directly into the authenticated dashboard runtime
