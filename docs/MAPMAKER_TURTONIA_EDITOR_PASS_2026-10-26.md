# Turtonia editor pass — Discover / Apply

## Discover

Input: the Turtonia and Mordor user journey proofs under `docs/proofs/turtonia-*` and the request to plan and implement their editor improvements.

Current state: the label tool may select a broad existing label where the user meant to place another; roads and rivers are raster strokes; the terrain brush stops at 400 px; stamp variation starts on; place symbols start at a fixed size; the map title does not appear on the map; and PNG and editable project require separate downloads. The editor uses a version 1 JSON document, raster/stamp/label layers, a shared renderer for canvas and PNG, and browser undo/autosave.

Relevant inventory: `vtt/static/mapmaker/index.html`, `js/{app,tools,document,render,ui,brush,storage}.js`, `mapmaker.css`, and `tests/test_mapmaker_browser.py`. Existing `.rdmap.json` files and autosave drafts must still load. New document fields must be optional. No server migration is needed.

Risks and assumptions: path nodes must be bounded in import validation; a large brush can consume more raster history memory; a title painted automatically can overlap a label the author added; ZIP must be readable by standard tools. Local Chromium is available for end-to-end verification. The editor remains German-language. No unresolved medium or high risk requires external input.

Next step: Apply the bounded design below, then Deploy and Monitor in local Chromium.

## Apply

Target state: the Ort tool always creates a new item; Select or the places list edits an existing item. Selection shows overlap guidance. A new Wege tool draws editable road/river polylines with a small bounded number of points; selection can move the whole line or a node, and the inspector changes material and width. The first path stroke creates its layer atomically, preserving legacy map layer counts. Old raster roads remain valid.

Document contract: keep `rd-mapmaker` version 1. Add `paths` as a layer kind with items `{id,x,y,material,width,points}`; `points` are offsets from `(x,y)`, start at `(0,0)`, contain 2–128 finite points, and stay within import bounds. Add optional `meta.showTitle`, default false. Existing documents retain their appearance. Add ash, basalt and lava terrain presets, an 800 px brush maximum, and sea gradient color controls. The title option renders `meta.title` at the top of the map. Stamp variation defaults off; new place symbol size is adjustable.

Export contract: keep PNG export; add a ZIP download containing one PNG at the selected scale and one editable `.rdmap.json` from the same document state. No third-party ZIP dependency.

Acceptance: overlap placement adds a new location without changing the old one; paths survive undo/redo and save/open, can be selected and edited, and reject malformed files; terrain/title/sea settings round-trip; a standard ZIP reader opens both files; the existing browser suite and Turtonia journey remain usable. Deploy only these editor changes and focused tests. Monitor with Chromium and record any residual friction.

## Deploy

Implementation: `vtt/static/mapmaker/index.html` and `js/{app,tools,document,render,ui,brush,zip}.js` now support the new controls and document fields. `tests/test_mapmaker_browser.py` exercises overlap creation, path node and whole-path editing, path validation/round-trip, terrain/style controls, and ZIP contents. The two protocol `run.py` files accept `TURTONIA_OUT` so compatibility replays do not overwrite their original artifacts. No unrelated tree changes were touched.

Verification: the complete mapmaker browser/static suite passed: **42 tests** in Chromium. After the visual title fix, the affected browser/static checks passed: **11 tests**; the path gesture and title/style screenshot tests passed separately. A Python standard-library `zipfile.ZipFile` read both bundle members and checked the 2400×1600 PNG and map data. Existing JSON files load because the path kind and `meta.showTitle` are additive and optional.

Acceptance checklist: new location over existing label ✓; overlap hint ✓; editable road/river paths, whole-path drag and Shift-drag node ✓; undo/redo/save/open and invalid path rejection ✓; 800 px brush and ash/basalt/lava ✓; stamp variation off and adjustable linked place symbol size ✓; title and sea controls ✓; ZIP export ✓; local browser regression ✓.

## Monitor

Observed results: [proof screenshots](proofs/turtonia-editor-pass-2026-10-26/) show a selected editable waterway and the dark sea/title controls. Both old visible-UI journeys completed with no browser errors and reopened their editable maps with matching layers/items. Mordor's PNG SHA-256 stayed `17807efa196512477f61a9410cd571f89841d92acdd1c632716262a3257d6c07`.

Residual risks: the original Turtonia script clicks approximate slider positions. Increasing the brush slider maximum changed some chosen sizes; its output SHA-256 is now `7296aec1929b30ce002b54345deae96c99326f4918016df220a917f01374b645` instead of the old `d8bc00add4c337ecb8196be78f77a2a36c0ad838736acf4a88cb92d1b24a30cb`, though the journey and structural round-trip pass. Its friction entries are historical and often emitted unconditionally. Existing raster roads remain raster; only the new Wege tool creates editable paths. The editor is still exercised locally, not through a production campaign import.

Recommended next action: use exact number inputs in a versioned Turtonia replay so future changes can compare a stable PNG while retaining the original journey as historical evidence. Then validate the map creator through the deployed VTT campaign import flow when deployment is in scope.
