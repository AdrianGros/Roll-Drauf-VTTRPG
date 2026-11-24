# FV07 + FV08 — Apply: object list, label preview, rotation presets, node-by-node paths

Phase: APPLY, then DEPLOY in the same worktree on owner assignment (2026-11-24: "yes take FV07 and FV08").
Worktree `/home/admin/projects/roll-drauf-vtt-fv07-fv08-20261124`, branch `feat/mapmaker-fv07-fv08-20261124`,
base `0252d1b06` (harness HEAD; FV04 `207c8e9fc` and the C27-S1 slice `e2c599f1d` included).
Codex keeps integration, the shared i18n bundle, deployment and live acceptance.

Sources: `docs/plans/VTT_NEXT_FULL_VERSION_2026-11-23.md` (FV07, FV08), `docs/CLAUDE_HANDOFF_MAPMAKER_27_2026-11-23.md`
(M3: E12, E14, E16, E17), `docs/DADM_APPLY_CLAUDE_MAPMAKER_2026-11-23.md` (proposals S3, S6),
`docs/DADM_DISCOVER_EDITOR_CREATOR_FEEDBACK_2026-11-23.md` (N12, N13).

## Boundary

No document, schema, server validator, export, ZIP or snapshot change. Every new state is editor/page state.
Files: `vtt/static/mapmaker/js/{tools,app,ui,selection,render}.js`, `index.html`, `mapmaker.css`,
new `tests/test_fv07_fv08_mapmaker_browser.py`, new `tools/i18n/tasks/fv07-fv08-mapmaker.json`.
Generated catalogue files (`ui-catalog.js`, `ui.{de,en}.json`) are rebuilt here for the tests but are
coordinator-owned: Codex regenerates them on integration because its FV01 work changes the same files.

## FV07

### E16 object list (new "Objekte" tab)
- Fourth panel tab `Objekte` (`#tab-objects`, `#pane-objects`), next to Werkzeug/Ebenen/Orte.
- Rows, top layer first and topmost item first (the hit-test order):
  - one row per path, stamp and label (the replaced title label is skipped, as in hit testing);
  - tile content: one row per (tile layer, tile asset) group with its cell count. A row selects
    exactly those cells through the existing tile selection, so the group can be moved or deleted.
- Filters: kind (all/paths/stamps/tiles/labels), layer (all/each layer) and a name search. The count line
  reads "{shown} von {total} Objekten". Rendering stops at 250 rows with a "narrow the filter" note.
- Click selects on the map (switches to Auswählen), centres the view on it and keeps the list open.
  Shift-/Ctrl-click extends the selection with existing `select(id, true)`. Map selection and list
  share `selectionSet`; selected rows carry `aria-pressed="true"`.
- Rows of hidden layers are shown disabled with "Ebene ausgeblendet": hidden content is never selected.
- The list rebuilds only while its pane is visible (it is marked stale otherwise), so live edits stay cheap.
- `Auswahl bearbeiten` opens the inspector in the Werkzeug tab; for a path or label it focuses the name field.

### E17 path naming discoverability
- Unnamed paths appear as "Weg ohne Namen"/"Fluss ohne Namen", named ones by their name; the search
  matches names. Path rows lead to the name field through `Auswahl bearbeiten`.
- The path tool hint names the route: select the path (V), then "Name des Wegs". No place relation (FV09).

### N12 label + symbol preview
- In the label tool, the pointer shows the label that a click would place: `createLabel(cursor)` is
  drawn at 55 % opacity with the exported `drawLabel`, including pin or symbol. No id is allocated for it.
- Placement stays one click; no option has to be set beforehand. Touch has no hover, so no preview there.

### N13 rotation presets
- Buttons −90°, −45°, 0°, 45°, 90°, 180° under the rotation sliders of the stamp and label inspectors.
- A preset writes the existing `rot` via `liveEdit` + `commitEdit`: one undo step, same stored value as the slider.

## FV08

### E12 click-to-add-node mode
- Path tool option `Zeichnen`: `Freihand ziehen` (default, unchanged) or `Punkte setzen` (`ed.pathOpts.mode`,
  page-session only).
- `Punkte setzen`: a tap/click (pointer moved < 6 CSS px, no pinch) adds a node. The first node fixes the
  target layer exactly like freehand; nodes are rounded to map pixels and clamped to the map, so the
  committed, saved and reloaded paths are identical. A click within 3 screen px of the last node adds nothing.
- Preview: the draft path plus a rubber-band segment to the pointer and its node handles.
- Finish: Enter, double-click, or `Weg fertigstellen`. A path needs ≥ 2 nodes and must leave its start by ≥ 5 px
  (the freehand rule); then one undo step "Weg zeichnen"/"Fluss zeichnen" and the new path is selected.
- Remove last node: Rücktaste/Entf or `Letzten Punkt entfernen`; Strg+Z and the Undo button do the same
  while a draft exists (no document step is undone mid-draft); redo is ignored while drafting.
- Cancel: Esc or `Abbrechen` (Esc with a draft is "busy", so the staged Esc does not leave the tool).
  Switching tool, switching the draw mode or opening/replacing a map discards the draft with the toast
  "Unfertiger Weg verworfen." A pinch only cancels the pending tap; hiding the browser tab keeps the draft.
- 128 nodes maximum (`LIMITS.pathPoints`), then a toast; Space/middle/right pan and wheel zoom keep working.

### E14 explicit draw/edit switch
- Path tool: button `Wegpunkte bearbeiten (V)` switches to Auswählen with node mode on (the delivered
  select/node controls; the drawn path stays selected).
- Path inspector: button `Neuen Weg zeichnen (W)` switches back to the path tool.
- Existing paths are never changed by drawing; node mode only changes a path when a node is dragged.

## Acceptance (automated, `tests/test_fv07_fv08_mapmaker_browser.py`)
1. List ↔ map: paths, stamps, labels and a tile group selected from the list are the map selection and
   vice versa; kind/layer/search filters and counts; hidden-layer rows disabled; 1440 and 390 px without
   horizontal overflow.
2. Label preview draws pixels at the pointer before a click, without changing items, history or generation.
3. Rotation preset and slider store the same `rot`; one undo step per preset.
4. Node mode: clicks → finish with Enter and with double-click; Backspace and Undo remove nodes; Esc cancels;
   no change to existing paths; Undo/Redo of the committed path; saved file and reopened map keep the
   exact points.
5. Freehand drawing is unchanged; draw/edit buttons switch tools and node mode; a node drag edits the path.
Regression set: `test_c27_mapmaker_browser.py`, `test_mapmaker_browser.py`, `test_review_maps_browser.py`,
`test_full_version_layers_browser.py` if present, i18n `build_catalog.py --check`.

## Open, not decided here
Node types/curve handles and line styles (FV09), path ↔ place relations (FV09/FV13), shortcut keys for the
draw modes (D13), a persistent object-list preference. Live acceptance stays with Codex.
