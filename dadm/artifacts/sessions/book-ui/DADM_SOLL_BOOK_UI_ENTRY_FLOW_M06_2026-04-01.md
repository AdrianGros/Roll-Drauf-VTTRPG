# DAD-M Soll: Book UI Entry Flow Target Model (M06)

Date: 2026-04-01
Milestone: M06
Phase: SOLL
Status: approved

## Goal

Define the target entry-flow model so `login`, `signup`, and `register` behave as one intentional journey, even though they do not all share the same shell mode.

## Target Product Statement

The entry family should read as one continuous onboarding journey with two visual intensities:

- `login` as the theatrical threshold
- `signup` and `register` as productive parchment zoom-ins

The user should experience these as adjacent chapters of the same book, not as three unrelated auth pages.

## Binding Target Assertions

### T-01 — The entry family is one journey with two modes

The product intentionally keeps:

- `login` in `cover` mode
- `signup` and `register` in `spread` mode

This split is not a defect by itself. The defect would be if the three routes feel behaviorally disconnected.

### T-02 — Login is the threshold, not the universal auth layout

`login.html` should remain the high-theater entry moment.

Its job is:

- identity handoff
- return-user reentry
- optional MFA continuation
- optional Discord identity path

It should not define the density, proportions, or layout rules for the productive auth pages.

### T-03 — Signup and register are productive auth chapters

`signup.html` and `register.html` should behave like focused parchment work surfaces.

Their job is:

- low-friction account creation
- readable validation
- clear next-step messaging
- route continuity back to login or forward into the app

### T-04 — The entry family must share one language for trust and feedback

All three routes should converge on the same quality bar for:

- tone of validation messages
- clarity of success states
- field-level vs page-level error hierarchy
- reduced-motion behavior
- shell navigation cues

They do not need identical UI widgets, but they do need one confidence model.

### T-05 — Password and credential rules must be communicated consistently

The entry family must stop describing password requirements differently from page to page.

The target is:

- one canonical rule set
- one consistent frontend explanation
- one predictable error shape

Whether the rule set itself stays at `8+` or is raised later is a later decision, but the communication must be unified.

### T-06 — Success behavior must feel intentional, not accidental

The family must clearly distinguish two allowed success outcomes:

- account created, then return to login
- account created, then immediate authenticated continuation

If `signup` and `register` intentionally differ here, the difference should be explicit and user-facing, not merely a side effect of backend implementation.

### T-07 — Identity options must be framed as route policy

If Discord login remains available only on `login`, that must be treated as a conscious route policy.

The target is not necessarily “Discord everywhere”.

The target is:

- clear identity-option boundaries
- no surprising dead ends
- no contradictory mental model between account creation and sign-in

## Target Journey Model

### Login

- strongest visual threshold
- fastest path for returning users
- explicit alternative identity path if Discord is enabled
- low-friction exit to `signup` or `register`

### Signup

- public self-service account creation
- productive spread layout
- clear rule communication
- explicit post-success handoff

### Register

- invite/key redemption chapter
- productive spread layout
- key-specific validation and recovery messaging
- explicit post-success handoff, currently allowed to continue directly into the app

## Intentionally Deferred Until M07/M08

These points should remain open for research and later implementation, not decided prematurely in M06:

1. Whether `signup` should continue to return to login or should auto-authenticate after successful registration.
2. Whether Discord identity should remain login-only or gain an adjacent path in the broader entry family.
3. Whether the canonical password minimum stays at `8+` or is deliberately raised for the entire family.
4. How much of the `login` cover runtime should be shared or mirrored in the productive auth pages, if any.
5. How far field-level error mapping should be standardized versus allowed to vary by route-specific context.

## Approval

- scope_kept: yes
- live_check_used: no
- residual_risks: deferred product choices intentionally held for M07/M08
- approved_to_proceed: yes
