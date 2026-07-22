# DAD-M Discover: Book UI Spread Screens (M09)

Date: 2026-04-01
Milestone: M09
Phase: DISCOVER
Status: approved

## Goal

Freeze the real current state of the spread-family routes:

- `dashboard`
- `campaigns`
- `characters`
- `lobby`

## Current State

### D-01

All four routes already sit inside the shared spellbook shell and route metadata system.

Evidence:

- shared `book-shell.css`
- shared `book-page.css`
- shared `book-shell.js`
- route metadata in `book-routes.js`

### D-02

The structural model is already directionally correct.

- left page is mostly orientation, controls, and guidance
- right page is mostly live content, cards, lists, or roster work
- header chrome and chapter metadata are already consistent

### D-03

The remaining inconsistency is not shell absence but surface drift.

Observed drift:

- `dashboard`, `campaigns`, and `characters` still rely heavily on page-local legacy classes such as `.card`, `.campaign-card`, `.char-card`, `.tabs`, `.tab`, `.detail-panel`, and `.filter-bar`
- the shell is consistent, but interior cards and controls still carry mixed pre-book styling
- spacing and card textures vary more than the shell language suggests

### D-04

`lobby` is currently the closest to the target spread language because it already uses more book-specific utility classes on the content surface.

## Discovery Conclusion

The spread block does not need another large route migration. It needs one shared polish pass that brings the interior control and card vocabulary closer to the shell.

## Approval

- scope_kept: yes
- live_check_used: no
- approved_to_proceed: yes
