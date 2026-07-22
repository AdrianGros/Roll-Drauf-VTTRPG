# DAD-M Apply: Book UI Shell Hardening (M04)

Date: 2026-04-01
Milestone: M04
Phase: APPLY
Status: approved

## Goal

Harden the shared shell layer before further route-family work expands on top of it.

## Scope

This milestone is intentionally constrained to one feature slice:

- route-navigation and shell-state hardening

Allowed implementation surface:

- [book-shell.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/book-shell.js)
- [book-shell.css](/home/admin/projects/roll-drauf-vtt/vtt_app/static/css/book-shell.css)

Out of scope:

- route-template rewrites
- new route families
- focus-mode implementation
- login cover refactor
- shared partial extraction

## Approved Changes

### 1. Navigation safety

The shell may harden:

- duplicate-click handling
- repeated navigation suppression
- same-target no-op handling
- defensive guards around animation startup

### 2. Shell state signaling

The shell may expose shared body state for:

- reduced-motion mode
- shell-ready state
- route transition in-progress state
- active-route styling hooks

### 3. Active navigation feedback

The shell may add clear active-state styling for route controls already carrying `data-book-route`.

## Acceptance Criteria

- navigating to the current route does not trigger unnecessary animation
- repeated clicks or rapid keyboard input do not spawn multiple route turns
- reduced-motion users get a clean low-motion path
- active route controls are visibly distinct
- existing spread routes keep working without template changes

## Risks

- some existing templates still use local `goTo()` helpers and inline handlers; this milestone can reduce shell fragility but cannot fully normalize template wiring
- cover-mode login remains outside this shared runtime

## Approval

- scope_kept: yes
- live_check_used: no
- approved_to_proceed: yes
