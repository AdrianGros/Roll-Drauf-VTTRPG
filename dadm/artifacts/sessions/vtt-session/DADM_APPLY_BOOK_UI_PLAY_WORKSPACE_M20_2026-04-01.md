# DAD-M Apply: Book UI Play Workspace (M20)

Date: 2026-04-01
Milestone: M20
Phase: APPLY
Status: approved

## Goal

Pilot the spellbook workspace shell on `play` while preserving the tabletop as a large, productive surface.

## Delegation

Implementation was delegated as a bounded worker task with this owned write scope:

- `/home/admin/projects/roll-drauf-vtt/vtt_app/templates/play.html`

The orchestrator reviewed the returned result locally before approval.

## Applied Changes

### A-01

Wrapped the route in book-shell framing and chapter metadata.

### A-02

Kept the map, toolbar, widgets, and right-sidebar structure intact as the primary workspace.

### A-03

Positioned the spellbook identity around the table instead of inside the interaction surface.

## Review Result

- scope remained within one template
- existing play scripts and route behavior were preserved
- the result matches the `M18` workspace-exception target

## Approval

- scope_kept: yes
- live_check_used: no
- approved_to_proceed: yes
