# Monitor — global Species and character-sheet rolls

## Observed results
The app started on the new image and the public pages and assets responded normally. The main navigation survived the release overlay. Unauthenticated calls to the new private APIs were refused as expected. Production has zero global Species revisions and zero Duckfolk publications, so the compendium is ready for contributions but Duckfolk is not yet selectable there. No production character or campaign data was modified for the smoke check.

## Validation evidence
- The focused run finished with **85 passed**, including a Chromium scenario with the VTT table and sheet open in separate tabs. A skill and weapon roll appeared without a table reload, persisted after reload, and a standalone sheet with two active tables required an explicit choice.
- API tests covered another contributor publishing global Duckfolk for a separate campaign, private revision isolation, table mismatch/ended-session refusal, and Duckfolk action targeting.
- Live HTTP health, sheet, editor, play JavaScript, and Duckfolk starter returned 200. Live route/auth checks returned 401 without credentials. Container image and feature flags matched the intended release.

## Inconveniences and residual risks
- The play sheet drawer's close control was outside the drawer because a shared header rule gave its header viewport width. The drawer header was constrained to its own width and the Chromium test now opens and closes it.
- Before this change, a standalone sheet could silently choose the wrong running table and gave no destination cue before rolling. It now shows the destination and refuses ambiguous choices.
- The sheet delivers its supported SRD rolls and Duckfolk's object-moving action. Full D&D Beyond parity still needs separate rule contracts for spell damage, spell slots, rest accounting, attack targeting, and broader class resources.
- The VTT-wide catalog currently publishes **playable Species only**. Eagle spells, items, classes, and other documents still need adapters before they can be selected or used as rules.
- A real production two-tab roll was not issued during smoke testing because that would write to a live campaign. The disposable browser journey is the end-to-end proof; a consenting live game can validate the user experience later.
- Duckfolk awaits attribution to a VTT account before its first global publication. Until then, the starter is available in the editor, but players cannot select Duckfolk from the live catalog.

## Recommended next action
Once the owner account is identified, create Duckfolk from the reviewed starter in that account's personal workshop, run the normal playability check, publish to `global`, and confirm an unrelated account can see it in the character creator. Continue mechanical parity in bounded slices beginning with spell use and resource accounting.
