# DAD-M Apply: Access Gate and Book Scene V2

Date: 2026-04-01
Phase: APPLY
Status: complete

## Objective

Apply the first correction block after the M01-M20 rollout:

- remove the public-signup bypass
- pilot a persistent-book login -> dashboard experience

## Scope Kept

Changed areas:

- auth registration gate
- onboarding templates
- login scene pilot

Primary files:

- [routes.py](/home/admin/projects/roll-drauf-vtt/vtt_app/auth/routes.py)
- [signup.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/signup.html)
- [register.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/register.html)
- [login.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/login.html)
- [book-scene.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/book-scene.js)
- [book-scene.css](/home/admin/projects/roll-drauf-vtt/vtt_app/static/css/book-scene.css)

## Applied Changes

### A-01

Registration now requires a valid registration key on the canonical registration path.

`/api/auth/register` no longer creates accounts without key validation and now aligns with the key-gated policy.

### A-02

The signup UI no longer represents a public bypass.

`signup.html` now asks for a registration key and submits it with registration.

### A-03

The key-based register path and signup path now tell the same product story.

### A-04

`book-scene v2` now pilots the requested login -> dashboard flow in the same book object.

After successful login:

- the user stays inside the spellbook scene
- the transition turns into an in-book dashboard reveal
- the first authenticated page now uses a page-native menu ribbon and mockup-like composition

### A-05

The dashboard pilot now uses live authenticated data where available for campaigns and characters while staying bounded to the login scene.

## Known Tradeoff

This is intentionally a pilot:

- the login -> dashboard experience is now book-native
- the standalone `/dashboard` route is not yet the same experience

## Approval

- scope_kept: yes
- live_check_used: no
- approved_to_proceed: yes
