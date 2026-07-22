# DAD-M Research: Book UI Spread Family M11

Date: 2026-04-01
Milestone: M11
Status: approved
Scope: overview, list/detail, and dashboard-like spread routes

## Sources

- https://carbondesignsystem.com/elements/2x-grid/overview/
- https://carbondesignsystem.com/elements/spacing/overview/
- https://www.w3.org/WAI/WCAG21/Understanding/reflow

## Evidence Summary

- Dense overview screens benefit from a fixed spacing rhythm and visible key lines.
- Mixed layouts work best when orientation and content zones stay structurally consistent across breakpoints.
- Reflow remains a hard requirement for non-workspace routes; overview routes should collapse cleanly instead of forcing horizontal scrolling.

## Repo Implications

- The spread family should converge through shared surface and spacing primitives, not bespoke page CSS per route.
- Dashboard cards, campaigns hub cards, character cards, tabs, filters, and empty states should align to one spacing rhythm.
- M12 should prefer scoped CSS overrides inside the existing spread pages instead of broader markup surgery.

## Approved M12 Constraints

- one feature slice only: spread-surface harmonization
- prefer one shared CSS file over multi-template rewrites
- no routing or data behavior changes

## Approval

Research complete. The smallest safe implementation path is shared spread CSS.
