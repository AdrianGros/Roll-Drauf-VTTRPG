# Kartenwerkstatt: Turtonia usability pass (2026-10-26)

## Discover — complete

**Input summary.** The Chromium/Playwright Turtonia baseline in `docs/proofs/turtonia-protocol-2026-10-26/` exposed friction in file safety, layer targeting, precise controls, dense objects, and linked places. The editor is a local, untracked prototype; production does not serve it yet.

**Current state and inventory.** `app.js` replaces a dirty document after import; `ui.js` focuses the discard choice in recovery and routes only the Land swatch to a layer. Range controls have output text but no direct number entry. `tools.js` picks the topmost object and can leave Space panning inactive when a control has focus. `document.js` v1 stores labels and stamps separately. `render.js` draws a place pin and label. `tests/test_mapmaker_browser.py` exercises the real editor under the production CSP. The starter has named Land, Gelände, and Flüsse & Wege raster layers.

**Dependencies.** Keep document version 1, bundled palette, CSP, autosave, undo, and old files compatible. No new package or service. The baseline proof is retained as historical evidence.

**Risks and assumptions.** High data-loss risk: replacing a dirty map can lose edits even if the single browser draft is saved. Medium usability risk: discard-focused recovery. Medium compatibility risk: any new place symbol field must be optional and validated against bundled assets. Low risk: custom layer names cannot be inferred from material names; routing should prefer canonical starter IDs and otherwise preserve the current layer. Open question: whether a larger atlas milestone should add vector roads, collision layout, and one-file publish/export. These require separate document and interaction designs.

**Next step.** Apply a bounded safety and editing design below.

## Apply — complete

**Target state and boundary.** This pass fixes the directly actionable editing friction without changing the map format version or adding dependencies. Opening or creating a map when the current map has file-unsaved edits asks whether to save the current map as a file, discard it, or cancel; Save continues only after a successful download. Recovery focuses Restore and never discards on Escape. Material choices route to the canonical raster layer (Land, Gelände, Flüsse & Wege) when present and visible. Brush and stamp sizes accept typed numbers and use the same clamped state as the sliders. Alt+click cycles through overlapping labels and stamps. A place can own one optional palette symbol, rendered at its anchor and moved/saved with it. On narrow screens, centering a selected place accounts for the open sheet, with a control to reveal the map. Holding Space while a non-text toolbar button has focus still pans the canvas when dragging; releasing Space on the button preserves its normal keyboard activation.

**Contracts.** Optional `symbol` on a label is `null` or `{asset, size}`; import validates the asset and size, old labels normalize to `null`, serialization includes the field. A linked symbol replaces the red pin visually when present. `hitTestAll` keeps visual layer order; Alt+click cycles only among hits under that pointer. Dirty replacement is guarded before `loadDocument`, and cancellation leaves the original document and draft intact.

**Acceptance criteria.** Dirty open/new can cancel without loss, and Save downloads before replacement. Restore is the default focused action. Material swatches pick intended starter layers. Typed sizes are exact and clamped. An overlapping lower object can be selected. Place symbol survives save/reopen and moves with the place. Mobile selection remains visible above the sheet. Space-drag pans from button focus without painting. Existing browser tests and the Turtonia roundtrip still pass.

**Tradeoffs and risks.** Guarding all dirty map replacements adds a decision step; this is justified by the single-draft data-loss risk. An embedded symbol is one object, not a general-purpose symbol/place relationship. Road geometry, automatic collision placement, map-title decoration, and unified editable/image publishing remain separately scoped follow-ups. No approval or dependency gate is triggered by this bounded local edit.

**Deploy handoff.** Implement in `index.html`, editor/controller, UI, renderer, document validator, input handler, CSS, and targeted browser tests; replay the existing protocol and record Monitor results here.

## Deploy — complete

**Input summary.** Implement the Apply design in the local Kartenwerkstatt prototype while preserving version 1 and unrelated workspace changes.

**Implementation summary and files changed.** `vtt/static/mapmaker/index.html` adds the replacement decision, numeric size fields, place-symbol controls, mobile map button, and overlap shortcut help. `js/app.js` guards document replacement, supports layered hit testing and an embedded place symbol, and centers around the mobile sheet. `js/ui.js` wires those controls, routes materials, and defaults recovery focus to Restore. `js/document.js` validates and persists optional place symbols. `js/render.js` draws them as part of their place. `js/tools.js` cycles overlap hits and honors Space-drag from button focus. `mapmaker.css` sizes the controls. `tests/test_mapmaker_browser.py` adds browser acceptance coverage and updates the dirty-import expectation. No dependency, schema-version, or deployment change.

**Proofs and verification.** The full Chromium/Playwright suite passed: 31 tests, 8 pre-existing dependency/ORM warnings, no test failure (256.96 s). After the Space and linked-symbol assertions were added, relevant targeted checks passed (4 and 2 tests respectively). All 7 static mapmaker checks passed. The original Turtonia protocol replay passed with zero browser errors, six named places, 98 stamps, exact raster/item reopen, and the same 2400×1600 PNG SHA-256 as the baseline (`d8bc00add4c337ecb8196be78f77a2a36c0ad838736acf4a88cb92d1b24a30cb`). Its separate proof is in `docs/proofs/turtonia-fixes-2026-10-26/`. The copied protocol script emits some original friction entries unconditionally; those entries are historical prompts, not evidence that the corresponding new controls failed.

**Acceptance checklist.** Dirty import/new cancellation and save-first import: pass. Safe recovery focus: pass. Material routing and exact typed sizes: pass. Overlap selection: pass. Linked place symbol, movement, validation, and reopen: pass. Mobile place visibility: pass. Space-drag from button focus: pass. Existing map editor suite and Turtonia pixel baseline: pass.

**Risks and assumptions.** Low: direct number entry avoids slider pointer imprecision, while the slider itself still snaps to its native track. Low: canonical material routing relies on starter layer IDs and preserves custom-layer choice if those IDs are absent. Low: place symbols can overlap nearby artwork; automatic layout remains outside this pass.

**Next step.** Monitor against the Turtonia journey and scope the remaining authoring improvements separately.

## Monitor — complete

**Input summary and observed results.** The saved map opens with the same items and raster data; the PNG hash exactly matches the original Turtonia run. The new controls and guard paths pass browser interaction checks. No regression was observed in the full existing suite.

**Artifacts (retention).** This plan and the browser tests are durable working artifacts. `docs/proofs/turtonia-protocol-2026-10-26/` is the immutable baseline; `docs/proofs/turtonia-fixes-2026-10-26/` is the retained follow-up replay. The local map editor source remains untracked in this workspace and is not yet deployed.

**Residual findings.** Medium usability: dense mountains and labels still collide; Alt+click makes hidden items selectable but does not compose the map automatically. Low usability: landmass drawing, roads/rivers as raster, and large symbol ranges still require manual work. Low workflow: startup uses a starter map, title lettering is a separate label, and PNG plus editable JSON are separate exports. Low environment: the preview is local and the phone reference remains partly obscured. The prepared browser environment is root-only; proof permissions are corrected after capture.

**Recommendation / next action.** Close this bounded usability pass. A separate Apply design should cover editable path geometry, repeatable terrain clusters, optional on-map title, collision hints, and a clearer export/publish journey before those are implemented. Do not treat the local preview as a production release.
