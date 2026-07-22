# DAD-M Soll: Book UI Character Sheet Focus (M14)

Date: 2026-04-01
Milestone: M14
Phase: SOLL
Status: approved

## Goal

Define how `character-sheet` should behave as a focus-mode route inside the spellbook system.

## Target Model

### S-01

`character-sheet` remains a focused work surface, not a spread overview.

### S-02

The book identity returns through:

- shell frame
- chapter and section metadata
- folio markers
- route-aware navigation

### S-03

The layout still splits orientation from dense editing:

- left side for context, quick summary, and navigation
- right side for actual editable work

### S-04

No data behavior rewrite is needed in this milestone.

- read/edit logic stays intact
- CRUD flows for spells, equipment, and inventory stay intact

## Approval

- scope_kept: yes
- live_check_used: no
- approved_to_proceed: yes
