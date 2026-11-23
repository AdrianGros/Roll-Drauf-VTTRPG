# Deploy FV04 layers and the first FV05 safety slice

Status: implemented, pushed, deployed and verified through both authenticated live journeys. The [Monitor](DADM_MONITOR_FULL_VERSION_LAYERS_2026-11-23.md) records the final source/image, rollback, QA cleanup and remaining scope. Retention permanent. [Apply contract](DADM_APPLY_FULL_VERSION_LAYERS_2026-11-23.md). Full goal remains FV01–FV18; this is the first implemented packet, not the whole version.

## Result

Paths respect the selected compatible layer and retain that target throughout a pointer gesture. Hidden or missing targets refuse the stroke before writing; the first vector path creates a distinctly named layer in one Undo action. Existing raster layers are unchanged.

The canvas has compact native layer radios and visibility controls. Narrow screens use an explicit disclosure and management action. The full panel filters by kind, object/layer name, actual empty/filled content and use during the editor session; it shows counts and permits recent-use sorting. Raster presence is checked in bounded strips and cached by revision. Filtered reorder buttons still use document stack positions.

The stamp palette precedes rare placement options, with size directly available and advanced options collapsed initially. Active scatter/area mode remains visible in the summary. Selection inspectors follow the stable tool controls. Label placement keeps canvas focus; the explicit edit-label action focuses the existing field. File-menu Escape no longer also changes the placement tool.

Occupied tile grids refuse in-place size changes and offer a new empty layer with Undo. The reference-grid switch keeps the grid with all tools without changing snapping or content. Arbitrary calibration, new snap patterns and cell rotation remain FV05 work; the rest of the brush/shortcut/radial work remains FV06 work.

## Verification and review

- On the unchanged source, both real browser reproductions fail at the intended assertions: lower path target and occupied grid movement.
- First new browser set: 11 passed. A separate first regression set had five passes and two navigation failures because advanced controls now require opening their disclosure; the tests were updated to use that real action without weakening their assertions.
- The combined rework run has 18 passes and one area-fill failure. Its start point lay under the new two-row desktop strip. Compacting the desktop strip to a single row resolves that interaction. The final six-case run passes: content/name/raster filtering, desktop and narrow keyboard controls, gesture-target recent ordering, non-active-layer recent ordering and the original area-fill budget/Undo journey. A separate non-active ordering case also passes. These overlapping runs are not summed into an invented total.
- Named path connections, context-layer keyboard selection at 390/1440, pixel-asset storage/roundtrip, label-font roundtrip, mixed eraser scopes and dense scatter/grid behavior passed in the combined run. New tests also verify first-path Undo/raster preservation, hidden-layer refusal, safe new tile layer/Undo, view-only reference grid, stable panels and tile-as-symbol preview/placement.
- Claude performed an independent source review, identified incorrect recent-use bookkeeping, and verified the correction in a second read-only review. Actual affected layer refs now flow through drawing, layer, item, tile, selection and eraser commits. Undo/Redo leaves the session usage order unchanged. No tests or production actions by Claude. The later content-filter addition received Codex source review and the final targeted browser checks.
- DE/EN catalogs and JS/Python syntax checks are recorded in the machine-readable proof. No fully green repository suite is claimed. The inherited FV18 failures remain outside this slice.

## Files and delivery handoff

Application files: mapmaker `app.js`, `tools.js`, `ui.js`, `selection.js`, `index.html`, `mapmaker.css`, generated `ui-catalog.js` and DE/EN JSON. Tests retain existing behavior assertions while adding the new UI navigation. New strings come from `tools/i18n/tasks/full-version-layers.json`.

The [proof directory](proofs/full-version-layers-2026-11-23) contains tests/review metadata, the committed-source overlay builder and normal live journeys. The builder checks all shipped Python/JS/CSS/HTML plus changed JSON against committed content, inherits untouched artwork from the checked base image and preserves intentionally absent superseded G1 files. It does not change dependencies or schema.

Delivery completed at source `207c8e9fc`: pushed, overlaid on the checked base image, backed up without migration, activated with rollback and verified through both normal Maps journeys. Actual file save/reload and complete synthetic QA cleanup pass. FV04 is closed in the register; FV01 has a separately reviewed language design and candidate inventory, without locale implementation yet. Full release evidence is in the Monitor.
