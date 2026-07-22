# DAD-M Research: Book UI Entry Flow Best Practices (M07)

Date: 2026-04-01
Milestone: M07
Phase: RESEARCH
Status: approved

## Goal

Lock the implementation rules for the auth journey so `login`, `signup`, and `register` can evolve as one entry family without drifting away from accessibility, mobile usability, or backend truth.

## Sources Used

Primary and official sources reviewed:

- web.dev sign-in form best practices:
  - https://web.dev/articles/sign-in-form-best-practices
- W3C WCAG 2.1 Labels or Instructions:
  - https://www.w3.org/WAI/WCAG21/Understanding/labels-or-instructions.html
- W3C WCAG 2.1 Error Identification:
  - https://www.w3.org/WAI/WCAG21/Understanding/error-identification.html
- W3C WCAG 2.2 Target Size (Minimum):
  - https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
- W3C WCAG 2.2 Status Messages:
  - https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html
- W3C WCAG 2.2 Accessible Authentication (Minimum):
  - https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum.html
- W3C WCAG 2.1 Animation from Interactions:
  - https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions.html

## Research Findings

### R-01 - Visible labels and format hints are mandatory on auth fields

W3C requires labels or instructions for user inputs and explicitly calls out format hints and special input rules as necessary when a field has stricter expectations.

Implication for this repo:

- auth pages must not rely on placeholders alone
- password, username, MFA, and registration-key rules should be visible before failure, not only after submission
- any password summary shown in the UI must match the backend validator exactly

### R-02 - Errors must identify the failing field in text

W3C states that when an input error is detected, the item in error must be identified and the error described in text.

Implication:

- field-level messages beat generic banner-only failure
- `signup` should avoid collapsing everything into `generalError` where the backend already reveals the failing field
- `register` and `login` should keep text feedback plain and specific

### R-03 - Success messages should be announced without stealing focus

W3C's status-message guidance says non-focus-changing messages should still be programmatically exposed so assistive tech can announce them.

Implication:

- success handoff from `signup` back to `login` should be surfaced with an announced status region
- non-blocking login and register banners should use stable `aria-live` behavior

### R-04 - Touch and pointer targets need a minimum usability floor

W3C 2.5.8 uses `24 by 24 CSS pixels` as the minimum target size baseline or requires enough spacing for smaller targets.

Implication:

- auth action buttons, route links, and password helpers should stay comfortably touchable
- book styling cannot shrink controls into decorative but fiddly chrome

### R-05 - Authentication must not depend on avoidable cognitive burden

W3C 3.3.8 treats remembering or transcribing auth secrets as a cognitive-function burden and favors alternative or assistive mechanisms.

Implication:

- the existing `autocomplete` usage is correct and should be preserved
- MFA should remain a conditional continuation step, not a permanently cluttered requirement
- Discord login can remain optional, but the core auth path must stay clear without memory puzzles beyond the actual credentials

### R-06 - Standard HTML and browser autofill are part of the UX, not an implementation detail

web.dev recommends native form controls, stable `id` and `name` values, correct `autocomplete` tokens, and a dedicated form element for sign-in/sign-up.

Implication:

- do not replace native auth fields with custom widgets
- keep `autocomplete="current-password"` and `autocomplete="new-password"`
- preserve stable field identity across shells and animations

### R-07 - Avoid unnecessary double entry and unnecessary friction

web.dev warns against doubling inputs such as repeated email or password entry unless there is a strong reason, because it adds effort and abandonment risk.

Implication:

- `register` can justify password confirmation because it is key-based account provisioning with immediate session creation
- `signup` should stay single-password unless product or security requirements change

### R-08 - Showmanship is allowed only when it does not block task completion

web.dev advises keeping branding consistent on auth pages, and W3C requires interaction-triggered motion to remain suppressible when non-essential.

Implication:

- `login` may remain theatrical as the cover
- `signup` and `register` should stay calmer productive spreads
- success handoffs and route changes must still work with reduced motion

## Derived Rules For This Repo

### Rule A

All entry pages must expose visible labels and the real validation rules for inputs with stricter formatting.

### Rule B

When the backend returns a field-specific auth error, the UI should place it on that field before falling back to a general banner.

### Rule C

Success states that do not take focus must still be announced through an `aria-live`-capable status region.

### Rule D

`signup` stays single-password, `register` may keep confirmation, and neither route may invent stricter password requirements than the backend enforces.

### Rule E

Auth motion remains secondary to clarity: cover theatrics only on `login`, productive parchment on `signup` and `register`.

## Approval

- scope_kept: yes
- live_check_used: no
- residual_risks: best-practice guidance from web.dev is advisory rather than normative, but it aligns with the W3C accessibility baseline and the repo's current architecture
- approved_to_proceed: yes
