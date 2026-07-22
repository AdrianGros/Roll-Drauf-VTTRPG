# DAD-M Discover: Book UI Spread Family M09

Date: 2026-04-01
Milestone: M09
Status: approved
Scope: dashboard, campaigns, characters, lobby

## Current State

- `dashboard.html` already uses the spellbook shell and a left/right spread split, but its cards, stats, and empty states still lean on older dark dashboard styling.
- `campaigns.html` already lives inside the shell and supports tabs, roster, detail, and hub-like management on the right page; visual density still mixes dark admin panels with parchment surfaces.
- `characters.html` uses the shell and keeps filters on the left page, roster on the right page, and a preserved modal flow above it; many cards and modal surfaces still follow older dark UI tokens.
- `lobby.html` is the cleanest spread conversion so far: orientation on the left, operational cards on the right, and relatively consistent parchment treatment.

## Structural Findings

- The spread family already shares route-level shell grammar.
- The main inconsistency is no longer layout, but surface language and density inside the right page.
- Most remaining divergence can be reduced through shared spread-surface CSS rather than route-by-route rewrites.

## Risks

- Over-correcting with per-page rewrites would exceed the milestone budget.
- Leaving legacy dark surfaces untouched weakens the “zoomed into the book page” illusion.

## Approval

Current-state discovery is sufficient to define the target model in M10.
