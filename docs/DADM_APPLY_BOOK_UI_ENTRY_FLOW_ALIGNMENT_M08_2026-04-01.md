# DAD-M Apply: Book UI Entry Flow Alignment (M08)

Date: 2026-04-01
Milestone: M08
Phase: APPLY
Status: approved

## Goal

Make the entry family more coherent without broad auth refactors.

## Scope

This milestone is intentionally constrained to one feature slice:

- entry-flow confidence alignment

Allowed implementation surface:

- [login.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/login.html)
- [signup.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/signup.html)
- [register.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/register.html)

Out of scope:

- backend auth behavior changes
- Discord expansion beyond login
- auto-login product changes for public signup
- auth API redesign

## Approved Changes

### 1. Password rule truth

The key-registration route communicates and validates the same password minimum as the backend validator:

- minimum length `8`
- uppercase
- lowercase
- digit
- supported special character set

### 2. Explicit success handoff

Public signup returns the user to `login` with a visible success status so the journey feels intentional instead of abrupt.

## Acceptance Criteria

- `register` does not invent a stricter minimum than the backend
- the user can understand on the login page why they were returned there after public signup
- the change remains bounded to entry-flow UI, not backend auth behavior

## Risks

- `signup` still has shallower field-level backend error mapping than `register`
- login remains a separate cover runtime by design

## Approval

- scope_kept: yes
- live_check_used: no
- approved_to_proceed: yes
