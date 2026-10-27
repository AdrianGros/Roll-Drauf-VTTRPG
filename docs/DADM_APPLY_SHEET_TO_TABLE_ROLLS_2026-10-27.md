# Apply — character sheet to live table

## Design summary
The SRD character sheet remains the authoritative source of roll choices and computed modifiers. Opening it from a table carries that table's session ID. A sheet click sends its roll choice and session ID to the existing server roll endpoint, which validates the destination and broadcasts the result to the same table's existing dice/chat channel. A standalone sheet shows whether it has an unambiguous live destination before the player rolls.

## Solution boundary and contracts
- Extend the existing roll endpoint with optional `sessionId`; when present, reject a session outside the character's campaign or not in progress. Do not silently redirect to another session. Preserve current local rolls when no live session exists.
- Add a small authenticated roll-context read for the sheet: candidate active sessions, chosen session, and whether the click will reach a table. A standalone sheet with multiple active sessions requires an explicit choice before broadcasting.
- The play drawer and a separate-tab sheet link pass the current session ID. The sheet keeps it through view/edit navigation and displays the destination near the roll controls.
- The VTT dice/chat summary shows the server-provided label (for example, “Arkane Kunde” or the weapon name) along with the dice and result. Preserve scoped visibility behavior.
- Keep existing ability/save/skill/initiative/spell attack/weapon rolls. Make the important combat and spell roll actions discoverable in the sheet without inventing unsupported spell-resource mechanics.
- Duckfolk's non-dice Species action uses the same explicit table binding when declared from the sheet. With multiple live sessions and no binding, it must ask for a choice; an ended or foreign binding must never fall back to a different table.

## Acceptance criteria
1. In Chromium, open a running play table and its character sheet in a second tab, click a skill and a weapon roll, and see each result in the VTT dice/chat log without a reload.
2. The result uses evaluated server modifiers, persists once in the correct session, and remains after table reload.
3. Wrong or ended explicit session IDs never redirect or log elsewhere; unauthorized users cannot roll another player's character.
4. The sheet reports when a roll stays local and does not imply a table delivery.
5. Existing sheet, inventory, roll, and play socket tests remain green. No new dependency or schema migration.

## Risks and tradeoffs
This delivers the two-tab click-to-roll parity path, not every D&D Beyond rule automation feature. Spell slots, rest accounting, attack targeting, and arbitrary spell damage need separate rule contracts before being presented as automatic.

## Deploy handoff
Implement this bounded behavior in the existing sheet, roll endpoint, and play UI. Add targeted API and Chromium journey tests. Review the diff and run those tests before any production rollout.
