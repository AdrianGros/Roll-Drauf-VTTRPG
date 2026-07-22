# DAD-M Research: Book UI Character Sheet M15

Date: 2026-04-01
Milestone: M15
Status: approved
Scope: dense form/editor focus mode

## Sources

- https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html
- https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html
- https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html

## Evidence Summary

- Dense editable screens must keep a persistent visible focus indicator for keyboard users.
- Labels and input rules still need to stay explicit even when the page is space-constrained.
- Errors should stay attributable to the relevant task area instead of collapsing into vague global failure states.

## Repo Implications

- Focus-shell styling must strengthen keyboard focus, not hide it under decorative book framing.
- Inputs should keep stable labels and generous spacing even when many fields are visible at once.
- M16 should focus on shell/frame conversion and field readability, not on changing the data model.

## Approved M16 Constraints

- one feature slice: character-sheet focus-shell translation
- keep CRUD logic and endpoint wiring intact
- prefer one template plus shared CSS support

## Approval

Research complete. M16 is authorized.
