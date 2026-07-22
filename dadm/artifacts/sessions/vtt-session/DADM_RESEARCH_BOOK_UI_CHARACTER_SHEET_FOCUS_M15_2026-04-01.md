# DAD-M Research: Book UI Character Sheet Focus (M15)

Date: 2026-04-01
Milestone: M15
Phase: RESEARCH
Status: approved

## Goal

Freeze the implementation rules for dense form editing, keyboard navigation, and focus visibility on the character-sheet route.

## Sources Used

- W3C WCAG 2.1 Focus Order:
  - https://www.w3.org/WAI/WCAG21/understanding/focus-order.html
- W3C WCAG 2.2 Focus Visible:
  - https://www.w3.org/WAI/WCAG22/Understanding/focus-visible
- W3C WCAG 2.2 Focus Not Obscured:
  - https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum
- web.dev keyboard focus:
  - https://web.dev/focus/
- Carry-forward form guidance from `M07`:
  - https://www.w3.org/WAI/WCAG21/Understanding/labels-or-instructions.html

## Findings

### R-01

Dense editor routes still need a logical focus sequence.

W3C focus-order guidance centers on preserving meaning and operability during sequential navigation.

Implication:

- the shell and sheet should keep DOM order aligned with reading and editing order
- no artificial positive `tabindex` sequence should be introduced

### R-02

Visible focus cannot be sacrificed for aesthetics.

W3C requires a visible focus indicator, and web.dev warns against disrupting natural focus order or replacing native interactive behavior unnecessarily.

Implication:

- buttons and inputs should keep obvious focus treatment
- native controls remain preferable to custom focusable shells

### R-03

Sticky or dense chrome must not hide focused controls.

W3C focus-not-obscured guidance matters especially on dense work surfaces with headers or pinned controls.

Implication:

- character-sheet framing should stay light enough that the actual working controls remain visible
- summary and shell elements should orient, not obscure

## Derived Rules For M16

### Rule A

Re-skin and reframe the sheet, but do not alter its logical editing order.

### Rule B

Keep native form controls and buttons in the natural focus flow.

### Rule C

Use shell framing and summary context to support dense work, not to compete with it.

## Approval

- scope_kept: yes
- live_check_used: no
- approved_to_proceed: yes
