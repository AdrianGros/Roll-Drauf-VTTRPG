# DAD-M Discover: Book UI Character Sheet Focus (M13)

Date: 2026-04-01
Milestone: M13
Phase: DISCOVER
Status: approved

## Goal

Freeze the true starting point of `character-sheet` before the focus-mode pass.

## Current State

### D-01

Before this milestone block, `character-sheet` already had strong data behavior but lived outside the shared book shell language.

### D-02

The route already contained the right product density:

- core stats
- spells
- equipment
- inventory
- read/edit split

### D-03

The primary gap was presentational and navigational:

- dark app-shell styling instead of book framing
- no shared shell metadata
- no folio or chapter cues
- page-turn continuity depended on legacy `BookScene` fallback logic

## Discovery Conclusion

The focus-mode job is not to reduce density. It is to keep the density while reintroducing book identity and shell continuity around it.

## Approval

- scope_kept: yes
- live_check_used: no
- approved_to_proceed: yes
