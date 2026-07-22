# DAD-M Discover: Book UI Entry Flow IST (M05)

Date: 2026-04-01
Milestone: M05
Phase: DISCOVER
Status: approved

## Goal

Capture the real current state of the entry-flow family so later entry milestones can improve one coherent journey instead of three adjacent pages.

## Entry Routes In Scope

- [login.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/login.html)
- [signup.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/signup.html)
- [register.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/register.html)
- [routes.py](/home/admin/projects/roll-drauf-vtt/vtt_app/auth/routes.py)
- [auth.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/auth.js)

## Current User Flow

### Login

- primary threshold entry route
- rendered as a theatrical 3D cover/page scene
- supports:
  - username/password
  - MFA continuation
  - optional Discord login
- successful login sets cookie-based session state through `/api/auth/login`
- redirects into `/dashboard`

### Sign Up

- public self-service registration route
- already presented as a productive spread inside the shared shell
- checks existing auth state first
- submits to `/api/auth/register`
- creates account only
- returns user to login instead of starting a session

### Register

- key-based provisioning route
- also already presented as a productive spread inside the shared shell
- checks existing auth state first
- submits to `/api/auth/register-with-key`
- creates account and immediately establishes the authenticated session
- continues directly to `/dashboard`

## Findings

### F-01 — The entry family is visually closer than functionally aligned

All three routes clearly belong to the same spellbook universe, but the runtime model is still split:

- `login` is `cover`
- `signup` and `register` are `spread`

That split is acceptable as a design decision, but it means the entry family still behaves like two architectures.

### F-02 — Success behavior is not yet one coherent journey

Current success paths differ materially:

- `login` creates session and enters app
- `signup` creates account but does not log in
- `register` creates account and does log in

This may be correct product behavior, but it is currently not framed as one intentional journey contract.

### F-03 — Error handling depth is inconsistent

- `login` has the richest field-level and alternate-path feedback
- `register` maps backend responses to specific fields reasonably well
- `signup` is still comparatively shallow and often falls back to `generalError`

This means the auth family does not yet present one consistent confidence model.

### F-04 — Auth options are asymmetrical

Only `login` currently exposes Discord login.

That creates a meaningful product asymmetry:

- the threshold route supports identity federation
- the follow-up account-creation routes do not

This is not necessarily wrong, but it must be treated as a deliberate decision in the later SOLL step.

### F-05 — Password-rule communication is inconsistent

The backend validator currently requires:

- minimum length `8`
- uppercase
- lowercase
- digit
- one special character from the shared rule set

But the current UI language diverges:

- `signup` communicates `8+` characters
- `register` communicates and validates `12+` characters in the page logic

So the entry family currently describes password expectations inconsistently.

### F-06 — Shell consistency already exists for the productive auth pages

`signup` and `register` already share:

- `book-shell-app`
- `book-shell-frame`
- `book-spread`
- shared shell/page CSS
- route metadata runtime

This is a strong baseline for later entry-flow refinement.

## Discover Conclusion

The entry-flow family is already in the same visual language, but not yet in the same behavioral contract.

The main gaps are:

- split architectural treatment between `cover` and `spread`
- inconsistent success-path expectations
- inconsistent error depth
- inconsistent password-rule communication
- unresolved product stance on Discord identity outside login

## Approval

- scope_kept: yes
- live_check_used: no
- residual_risks: none beyond later entry-flow design work
- approved_to_proceed: yes
