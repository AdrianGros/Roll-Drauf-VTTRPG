# Monitor — two agentic friction journeys

## Status and input summary
`complete`. The user asked for two agentic friction tests after the global Duckfolk and two-tab sheet-roll releases. I ran Chromium journeys with disposable users and sessions, inspected their screenshots as a player/author/DM, and checked the current production image and served assets. No application code or production game data was changed.

## Test 1 — Duckfolk author → public catalog → player → DM
The Chromium journey in `tests/test_creation_engine_eagle_browser.py::test_duckfolk_publish_creator_sheet_and_live_action` passed (**1 passed**, 40.03 s, 1280×900). An unrelated contributor created and published Duckfolk globally; a player selected it, chose its skill, finalized a character, declared telekinesis at a bound table, and the DM viewed the origin in the party hub. The run reported no page errors. Screenshots: [publication](proofs/agentic-friction-2026-10-28/01-published.png), [creator](proofs/agentic-friction-2026-10-28/02-creator.png), [DM party](proofs/agentic-friction-2026-10-28/03-dm-party.png).

## Test 2 — character sheet in a second tab → live VTT roll
The Chromium journey based on `tests/test_sheet_to_table_browser.py::test_a_sheet_roll_in_a_second_tab_appears_live_at_the_table_and_stays` passed (**1 passed**, 41.56 s, 1440×1000). A skill and dagger attack clicked on the sheet appeared immediately in the VTT chat and remained after reload. The table URL stayed bound through sheet edit mode. A standalone sheet with two live sessions refused a roll until one table was selected. The run reported no page errors. Screenshots: [live table](proofs/agentic-friction-2026-10-28/04-live-rolls.png), [standalone table choice](proofs/agentic-friction-2026-10-28/05-sheet-choose-table.png). The second run used a temporary copy of the same test with screenshot calls; the original test and application code were not edited.

## Findings and user friction
| Severity | Checkpoint | Observed inconvenience | Evidence and likely cause |
| --- | --- | --- | --- |
| **Medium** | DM party, Duckfolk action | The action heading says `undefined ft · undefined lb` instead of its 30 ft range and 10 lb limit. The full rule paragraph still gives the numbers, but the prominent summary is misleading. | [DM screenshot](proofs/agentic-friction-2026-10-28/03-dm-party.png). `vtt/characters/srd_party.py` sends action `id`, `name`, and `summary` only; `vtt/static/js/srd-party-ui.js` reads `rangeFeet` and `maxWeightLb` from that reduced object. The currently served production JS contains the same read. |
| **Medium** | Character sheet | A full-page sheet captured at 6,511 px, with a second large core/stat block far below the playable roll area. This creates a long search and scroll path even though the sticky roll controls help. | [Sheet screenshot](proofs/agentic-friction-2026-10-28/05-sheet-choose-table.png); screenshot dimensions 1440×6069 for the standalone state and 1440×6511 for the bound state. |
| **Low** | DM party layout | At 1280 px the only character card is about 270 px wide while most of the row is empty; the action text wraps into many short lines. | [DM screenshot](proofs/agentic-friction-2026-10-28/03-dm-party.png). |
| **Low** | Table → separate sheet | The tab link becomes usable after opening the token widget and selecting the token. The journey needs those two preparatory clicks before the sheet action is exposed. | The ordered steps in `tests/test_sheet_to_table_browser.py` and [table screenshot](proofs/agentic-friction-2026-10-28/04-live-rolls.png). |
| **Low** | Global Species authoring | The publication form is about 2,482 px tall at a 900 px viewport. The check and publish controls follow the detailed supplement fields, requiring a long scroll. The document list also exposes English `race` and `Edit with Eagle Homebrew` labels in an otherwise German flow. | [Publication screenshot](proofs/agentic-friction-2026-10-28/01-published.png). |

## Positive observations
The global Duckfolk choice and its provenance are visible in character creation. The sheet announces its table destination before rolling, names the action in the live chat entry, preserves the binding through edit mode, and prevents an ambiguous standalone roll. Both tests completed without backtracking or unexpected server responses. The live app health returned HTTP 200 on 2026-10-28; `official-publisher-20261027-v4` was running with zero restarts.

## Boundaries, risks, and next step
- **Medium, test coverage:** These are isolated browser runs using the current repository code. Their fixtures prepare users, drafts, inventory, and sessions through APIs, so they do not measure login/dashboard onboarding or every wizard click. The isolated templates do not include all production navigation overlays. No authenticated production roll was made. These limits prevent a claim of complete live user-journey parity.
- **Low, viewport:** Both runs were desktop Chromium; phone, keyboard-only, Firefox, and WebKit friction remain unmeasured here.

Recommended next bounded action: fix the DM action DTO/render mismatch first, then simplify the sheet's repeated lower core section and expose the separate-tab sheet action closer to the character/token entry point. Repeat the same two journeys after those changes, including one phone pass. This report and the five screenshots are retained as repository proof artifacts.
