# DAD-M Soll: Book UI Spread Family M10

Date: 2026-04-01
Milestone: M10
Status: approved
Scope: dashboard, campaigns, characters, lobby

## Target Model

- Left page: orientation, filtering, chapter notes, and light controls.
- Right page: the actual working surface for lists, cards, detail panes, and quick actions.
- Shared shell chrome remains stable across routes; only chapter metadata and content change.

## Visual Rules

- Spread routes should read like parchment pages, not dark app dashboards embedded inside a book frame.
- Cards, stat blocks, tabs, and empty states should inherit one shared surface language.
- Route-specific emphasis is allowed, but not a second competing design system per page.

## Interaction Rules

- Primary actions may sit on the left page if they start a flow, but resulting lists and detail states belong to the right page.
- Mobile collapse may stack left before right, but reading order must remain orientation first, work second.
- The spread family should stay low-motion; chapter transitions belong to the shell, not the inner cards.

## Non-Goals

- no rewrite of deep modal systems in this milestone block
- no conversion of character-sheet or play into spread mode
- no broad data-flow changes

## Approval

Target state is clear enough for focused research and a bounded M12 implementation slice.
