# DAD-M Apply: Book UI Character Sheet Focus (M16)

Date: 2026-04-01
Milestone: M16
Phase: APPLY
Status: approved

## Goal

Translate `character-sheet` into a spellbook focus route without changing its core sheet behavior.

## Delegation

Implementation was delegated as a bounded worker task with this owned write scope:

- `/home/admin/projects/roll-drauf-vtt/vtt_app/templates/character-sheet.html`

The orchestrator reviewed the returned result locally before approval.

## Applied Changes

### A-01

Wrapped the route in the shared spellbook shell and focus framing.

### A-02

Added chapter metadata, folio markers, and route-aware navigation cues.

### A-03

Kept the existing read/edit logic, save flow, spells, equipment, and inventory behavior intact while moving the surface into the book language.

### A-04

Split orientation and dense editing more clearly:

- left side for mode/context/summary/navigation
- right side for actual sheet work

## Review Result

- scope remained within one template
- no backend or API behavior changed
- output matches the `M14` focus target

## Approval

- scope_kept: yes
- live_check_used: no
- approved_to_proceed: yes
