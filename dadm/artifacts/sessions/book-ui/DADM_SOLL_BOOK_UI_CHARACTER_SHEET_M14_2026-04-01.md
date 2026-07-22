# DAD-M Soll: Book UI Character Sheet M14

Date: 2026-04-01
Milestone: M14
Status: approved
Scope: `character-sheet.html` as focus mode

## Target Model

- Character sheet becomes a `focus` route: still visibly inside the spellbook system, but zoomed toward productive sheet work.
- Chrome should shrink to a calm header and a short framing block; most space belongs to sheet panels.
- Dense fields remain readable and keyboard-friendly.

## Layout Rules

- Top area: chapter identity, mode label, and compact navigation.
- Main area: wide focus grid with content panels on parchment-like surfaces.
- Mobile: single-column collapse without breaking edit/view semantics.

## Interaction Rules

- edit/view mode stays as-is
- no workflow expansion beyond current CRUD affordances
- confirmation and error messaging remain visible near the working surface

## Approval

Target state is defined and ready for implementation research in M15.
