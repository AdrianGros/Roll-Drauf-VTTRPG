# DAD-M Soll: Book UI Spread Screens (M10)

Date: 2026-04-01
Milestone: M10
Phase: SOLL
Status: approved

## Goal

Define the target behavior for spread-family routes without collapsing them into focus-mode workspaces.

## Target Model

### S-01

Spread routes keep the two-page reading model.

- left page = orientation, filters, tabs, route notes, quick actions
- right page = cards, rosters, lists, and the main working set

### S-02

Interior surfaces should feel like part of the same parchment system as the shell.

- cards should read as paper fragments, not detached dark panels
- tabs and filters should feel like chapter controls, not generic app chrome
- status and detail panels should sit inside the same tonal family

### S-03

Reflow remains mandatory.

- spread controls must collapse vertically on narrower widths
- card grids must gracefully reduce column count
- horizontal scrolling is not an acceptable normal mode for these routes

### S-04

This block does not absorb focus-mode density.

- character deep editing belongs in `character-sheet`
- tabletop density belongs in `play`
- spread routes should remain readable overview pages first

## Milestone Implication

`M12` should prefer one shared surface-normalization slice over multiple template rewrites.

## Approval

- scope_kept: yes
- live_check_used: no
- approved_to_proceed: yes
