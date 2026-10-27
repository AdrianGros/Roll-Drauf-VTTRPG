# Discover — character sheet to live table

## Input
The requested journey is a D&D Beyond-style character sheet in one browser tab: click a roll on that sheet and see it appear in the VTT tab, comparable to using Beyond20 with Roll20. The sheet should become a practical play surface, not just a static record.

## Current state and inventory
- `vtt/templates/character-sheet.html` renders the SRD sheet. Ability checks, saves, skills, initiative, death saves, and spell attacks are clickable. `vtt/static/js/srd-inventory-ui.js` adds weapon attack, damage, critical, and versatile rolls.
- `POST /api/srd-creator/characters/<id>/roll` in `vtt/characters/srd_creator.py` computes authoritative sheet rolls server-side. `vtt/characters/sheet_link.py` logs them to an in-progress session and broadcasts `dice_rolled`.
- `vtt/static/js/play-ui.js` already receives `dice_rolled` and appends it to the dice and chat logs. It also embeds the sheet in a drawer, but the sheet URL contains only a character ID.
- `tests/test_srd_rolls.py` checks server calculation, permission, logging, and token linkage. `tests/test_srd_sheet.py` checks click-to-roll in the sheet browser. Neither proves two browser tabs with the live table receiving a sheet click.
- The live session chosen by `roll_target_session` is the linked token's active session or the newest in-progress session of the character's campaign. The request does not identify which table the player is using.

## Dependencies
JWT cookie authentication, active campaign membership, Flask-SocketIO room membership, the SRD evaluator, and the existing play UI roll event path. No new external service is needed for the same-origin sheet journey.

## Risks and assumptions
- **Medium:** If a campaign has concurrent in-progress sessions, a sheet opened outside the table may send a roll to the wrong session. A session-bound request must be validated against the character's campaign and active status.
- **Medium:** A roll can succeed locally while not reaching a table. The UI currently reports this only after the click. The player needs a clear destination state before rolling.
- **Medium:** Full D&D Beyond mechanical parity spans class resources, spell slots, rest rules, and system automation absent from the current data model. This pass should prove the core sheet-to-table roll contract and clearly expose supported actions.
- **Low:** The current VTT broadcast summary omits the sheet roll label, making a skill or weapon roll less clear than its persisted chat record.

## Open questions and next step
No blocking question: use the existing SRD system and live VTT session, with explicit table context when opened from play. In Apply, define the session binding, sheet status, browser journey, and a bounded set of play-facing improvements.
