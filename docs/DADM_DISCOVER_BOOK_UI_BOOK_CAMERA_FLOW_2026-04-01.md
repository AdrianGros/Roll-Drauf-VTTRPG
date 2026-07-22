# DAD-M Discover: Book Camera Flow

Date: 2026-04-01
Phase: DISCOVER
Status: complete
Scope: gap analysis between current UI and the new mockup-driven book journey

## Objective

Capture the real divergence between the current implementation and the desired "maerchenbuch" experience shown in the new dashboard mockup.

## Evidence Reviewed

- [login.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/login.html)
- [dashboard.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/dashboard.html)
- [book-scene.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/book-scene.js)
- [book-scene.css](/home/admin/projects/roll-drauf-vtt/vtt_app/static/css/book-scene.css)
- user mockup screenshot from this thread
- user feedback from this thread

## Mockup Reading

The mockup communicates a very specific interaction model:

- the dashboard is not a normal app page
- it is one visible parchment page inside the same book object
- the top navigation is an in-page `menu ribbon`, not a detached app header
- the page content is arranged as one story page:
  - top ribbon row
  - upper content row with `Meine Kampagnen` and `Charaktere`
  - lower wide widget panel
- the whole thing reads like a zoom onto a page that already exists inside the book

## Current-State Findings

### F-01

The login route still feels like a separate 3D scene that hands off to a different application shell.

`book-scene.js` currently opens the book cover and then routes out to `/dashboard`. After that, the authenticated area is rendered as a separate shell page rather than staying in the same book object.

### F-02

The current dashboard still reads as an application screen placed in a shell, not as a single designed book page.

It still contains:

- detached top header controls
- app-like stat tiles
- generic "recent campaigns / recent characters" sections
- normal layout conventions instead of page-composition logic

### F-03

The current authenticated flow breaks the intended story illusion.

User expectation:

- login
- page turn
- zoom into next page

Current reality:

- login in a 3D book scene
- navigate to a different route shell
- arrive in something that still resembles a normal interface

### F-04

The access-control model currently contradicts the intended onboarding policy.

The repo still exposes public registration through `/api/auth/register` and [signup.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/signup.html), which means account creation is possible without a registration key.

If registration keys from the Discord bot are the intended gate, then the current public signup route is functionally a bypass.

## Discover Conclusion

The main gap is no longer "book theme missing". The real gap is:

- the authenticated area does not stay inside one persistent book object
- the dashboard composition does not match the mockup's page logic
- the onboarding journey currently violates the intended key-based access gate

## Implication

The next design/program step should not be another shell polish pass.

It should be a new architecture pass:

1. keep the user inside one persistent book scene
2. turn auth success into `page turn + camera zoom`
3. redesign dashboard as one composed page inside the book
4. close the public-signup access-control bypass
