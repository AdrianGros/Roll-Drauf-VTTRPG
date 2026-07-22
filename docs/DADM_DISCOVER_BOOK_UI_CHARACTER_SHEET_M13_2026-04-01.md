# DAD-M Discover: Book UI Character Sheet M13

Date: 2026-04-01
Milestone: M13
Status: approved
Scope: `character-sheet.html`

## Current State

- The sheet is still a dark standalone app surface, not a book-native focus route.
- It already separates dense panels sensibly: core, spells, equipment, inventory.
- It supports both view and edit mode with minimal JS branching and stable API calls.

## Main Gaps

- No spellbook shell or focus-shell framing.
- Header actions and dense content feel detached from the established book language.
- The page is usable, but it reads as a different product from the spread routes.

## Constraint

- The underlying CRUD behavior is already acceptable and should not be disturbed.
- The main problem is presentation and spatial framing, not workflow logic.

## Approval

Discovery is sufficient to define a focus-mode target for M14.
