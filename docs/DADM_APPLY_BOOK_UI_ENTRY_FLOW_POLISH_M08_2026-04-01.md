# DAD-M Apply: Book UI Entry Flow Polish (M08)

Date: 2026-04-01
Milestone: M08
Phase: APPLY
Status: approved

## Goal

Apply one bounded polish slice to the entry flow so `signup` and `register` communicate the same auth rules and return more precise validation feedback without changing the underlying backend flow.

## Scope Kept

Feature slice:

- auth feedback consistency

Touched interaction points:

- password rule communication
- field-level error routing

Files changed:

- `/home/admin/projects/roll-drauf-vtt/vtt_app/templates/signup.html`
- `/home/admin/projects/roll-drauf-vtt/vtt_app/templates/register.html`

## Applied Changes

### A-01

`register.html` now matches backend password truth instead of advertising a stricter `12+` rule that the server does not actually enforce.

### A-02

`register.html` now shows the same visible password requirement list used by `signup.html`, including live requirement highlighting while typing.

### A-03

`signup.html` now routes common backend validation responses to the relevant field instead of sending every failure to the generic error area.

### A-04

Both entry pages now use the same backend-aligned special-character rule for client-side guidance.

## Review Result

- implementation matches `M05` discover findings
- implementation matches `M06` entry-flow target
- implementation follows `M07` guidance without expanding into new auth features

## Approval

- scope_kept: yes
- live_check_used: no
- residual_risks: login success handoff copy remains intentionally untouched in this slice
- approved_to_proceed: yes
