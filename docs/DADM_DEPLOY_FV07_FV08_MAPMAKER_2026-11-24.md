# FV07 + FV08 — Deploy (implementation) and handoff to Codex

Status: **implemented and tested locally; not deployed, not pushed.** Live delivery, push and live acceptance
belong to Codex (`CLAUDE.md`). Design: [DADM_APPLY_FV07_FV08_MAPMAKER_2026-11-24.md](DADM_APPLY_FV07_FV08_MAPMAKER_2026-11-24.md).

- Worktree `/home/admin/projects/roll-drauf-vtt-fv07-fv08-20261124`, branch `feat/mapmaker-fv07-fv08-20261124`
  (same repository as the harness worktree, so it can be merged directly).
- Base `11384877a` (harness `fix/feedback-harness-20261123` at handoff time).
- Commits: `25e449ac6` feature + tests + i18n fragment + Apply; `77d005c0f` regenerated UI catalogue only.
  The catalogue commit can be dropped and regenerated on integration if newer FV01 labels arrive first.

## What a user gets (Kartenwerkstatt, `/mapmaker`, any signed-in editor user)

| Packet | Entry | Behaviour |
| --- | --- | --- |
| FV07 E16 | Panel tab **Objekte** | Every path, symbol, label and tile group (per tile layer and tile type), top layer first; filters Art / Ebene / Objekte suchen; count "x von y Objekten"; click selects on the map and centres it, Shift/Ctrl-click extends; map clicks highlight the row; hidden-layer rows are disabled and marked. 250-row cap with a note. |
| FV07 E17 | Objekte → **Auswahl bearbeiten**; path tool hint | Opens the inspector and focuses "Name des Wegs" (or the label name). Unnamed paths read "Weg/Fluss ohne Namen". |
| FV07 N12 | Ort/Beschriftung tool (T), mouse or pen hover | 55 % preview of the label a click places, with pin/symbol; no id, no history, no generation change. Not shown on touch (no hover). |
| FV07 N13 | Inspector of a symbol or label | Buttons −90°/−45°/0°/45°/90°/180° under "Drehung"; same stored `rot` as the slider, one undo step. |
| FV08 E12 | Wege tool (W) → Zeichnen: **Punkte setzen** | Click per node (set on release; drags/pinch add none); Enter, double-click or **Weg fertigstellen** finishes; Rücktaste/Entf, **Letzten Punkt entfernen** or Strg+Z remove the last node; Esc or **Abbrechen** cancels; tool/mode switch or opening a map discards with a toast; nodes are integer map pixels. |
| FV08 E14 | Wege tool → **Wegpunkte bearbeiten (V)**; path inspector → **Neuen Weg zeichnen (W)** | Explicit switch to the delivered select/node mode and back. Freehand stays the default and is unchanged. |

No document, schema, server validator, export, ZIP or snapshot change; all new state is page/editor state.

## Files

`vtt/static/mapmaker/js/{app,tools,ui,selection,render}.js`, `vtt/static/mapmaker/index.html`,
`vtt/static/mapmaker/mapmaker.css`, `tools/i18n/tasks/fv07-fv08-mapmaker.json` (30 DE/EN strings),
`tests/test_fv07_fv08_mapmaker_browser.py` (7 browser tests), generated `vtt/static/i18n/ui.{de,en}.json` and
`vtt/static/js/ui-catalog.js`. `render.js` only exports the existing `drawLabel`; `selection.js` only adds
`chooseTiles(layerId, keys)`.

## Verification actually run (headless Chromium, static preview server with production CSP, no database)

- `tests/test_fv07_fv08_mapmaker_browser.py`: 7/7 passed (object list ↔ map selection, filters, tile groups,
  hidden layers, name-field route; phone layout at 390 px without horizontal overflow; label preview pixels on the
  display canvas without document change; rotation presets vs slider plus saved file; node mode Enter/double-click/
  Backspace/Undo/Esc, Undo/Redo of the committed path, file save and reopen with identical points; draft buttons and
  tool-switch discard; freehand unchanged and the draw/edit buttons).
- Regression on the pre-rebase tree: `test_c27_mapmaker_browser.py`, `test_mapmaker_browser.py`,
  `test_review_maps_browser.py`, `test_full_version_layers_browser.py`, `test_c04_mapmaker_browser.py`,
  `test_feedback_b06_browser.py`, `test_feedback_b05_browser.py`, `test_mapmaker_static.py`: 130 passed, 6 failed.
  All 6 fail identically (same assertion and line) on an untouched copy of base `0252d1b06`, so they are
  pre-existing and FV18 material:
  - `test_c27…::test_escape_cancels_first_then_leaves_the_placement_tool` and
    `test_mapmaker_browser::test_place_with_lore_is_rendered_as_literal_text` — `#selText` not focused.
  - `test_mapmaker_browser::test_narrow_viewport_sheet_and_tools` — `#brushSize` not in viewport.
  - `test_mapmaker_browser::test_tile_tool_paints_grid_cells_with_undo_size_and_file_roundtrip` — `32 == 48`.
  - `test_c04…::test_dm_library_to_table_firefox_player_sees_card_source_unchanged_and_retry_uploads_once` —
    `#layersWidgetBody` hidden (playtable).
  - `test_mapmaker_static::test_index_uses_only_relative_local_resources` — `/login.html` absolute link.
- After rebasing onto `11384877a` (final tree): FV07/FV08 tests, `test_c27…`, `test_full_version_layers_browser.py`
  and `test_mapmaker_static.py`: 37 passed, 2 failed — only the known baseline failures
  `test_escape_cancels_first_then_leaves_the_placement_tool` and `test_index_uses_only_relative_local_resources`.
- `python3 tools/i18n/build_catalog.py --check`: 3826 sources, DE/EN complete. `node --check` on all changed modules.

Not run: live deployment, live DM/Player journeys, Firefox, real touch devices, the full repository suite.

## Handoff steps for Codex

1. Merge or cherry-pick `25e449ac6` onto the current integration branch; regenerate the UI catalogue
   (or take `77d005c0f` if nothing else changed the catalogue) and run `build_catalog.py --check`.
2. Run `tests/test_fv07_fv08_mapmaker_browser.py` plus the map regression set above; compare against the six
   known baseline failures.
3. Build the overlay image on the live source, activate with the usual backup/rollback, verify `/health/live`.
4. Live acceptance as a signed-in user in `/mapmaker` (1440 and 390 px): the journeys in the table above.
   No schema step and no data migration.

## Residual risks

- The label preview needs hover, so phones show none (placement itself is unchanged).
- While a node path is open, the toolbar Undo button is disabled on a map without history; keyboard Undo and the
  draft buttons still work.
- The object list rebuilds on every selection change while it is open (bounded at 250 rows, rows built from at
  most 2000 items + tile groups).
- Open decisions stay with FV09/FV13: node types/curve handles, line styles, path ↔ place relations, draw-mode
  shortcut keys.
