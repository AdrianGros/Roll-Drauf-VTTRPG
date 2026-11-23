# Apply FV04 and the first FV05 safety slice

Status: implementation contract defined against `44fa2da96`; the active full-version goal authorizes delivery. Profile standard. Retention permanent. Input: the November 23 editor reviews, the S2/S4 proposal and the [full-version register](plans/VTT_NEXT_FULL_VERSION_2026-11-23.md). Previous goal turn made progress by defining and committing that register. Current live source is still `7e0a3c859`, image `sha256:fd604eee0ca2481eddad4658262a32cc112327a60db847b4a18a02893abc1af7`.

## Facts and boundary

`addPath` currently chooses the top visible paths layer rather than the selected compatible one; when all paths layers are hidden it creates another layer. Path pointerdown starts a preview without validating the target. `setLayerProp(gridSize)` changes the grid used to interpret existing cell positions and rejects only off-map cells. The layer panel already exposes selection, visibility, ordering and layer creation. The stamp palette currently follows placement/own-image configuration and rare options remain expanded. No document-format change is required for this slice.

Codex owns `mapmaker/js/app.js`, `tools.js`, `ui.js`, `selection.js` (affected-layer bookkeeping only), `index.html`, `mapmaker.css`, the bounded browser tests and i18n fragment. Paths are under `vtt/static/`. No dependency, backend, permission, schema or catalog-asset changes. Claude separately inspects FV01 language design using read-only tools; it does not edit these files.

## Layer targeting

- Resolve an existing path layer with the same `targetLayer("paths")` contract as other tools: deliberately selected compatible layer first, otherwise the top visible compatible layer. A hidden selected compatible layer is an explicit refusal, not a fallback.
- Check the target before beginning the pointer gesture and retain its identity until commit. If that layer becomes hidden or is removed, refuse the stroke. Create a paths layer only when no paths layer exists at all; layer plus path remains one Undo step. Name new vector layers distinctly; never convert the starter raster called Flüsse & Wege.
- Keep the existing raster/tile/stamp erase scopes. Reproduce tile-as-symbol preview and placement separately from palette visibility before changing any asset behavior.

## Compact layers and panels

- Show a compact layer strip on the canvas at desktop widths. Use native radios for selection and separate visibility buttons, with visible names/type and the current layer. On narrow screens the existing layer button reveals the compact list; an explicit management action opens the full panel. Escape closes only the transient compact list and returns focus.
- Reuse `setActiveLayer` and `setLayerProp`. Filter the full panel by type and name, show item/cell counts and permit ordering by recent use. Recent use means deliberate selection or a successful write in the current editor page session; it is not document data, autosave state or an Undo command. Raster rows report raster content rather than an invented vector-object count.
- Filtering/sorting changes only the view. Reorder buttons use real document positions, not positions in the filtered list. Preserve focus on refresh, including native radio arrow navigation and visibility actions.
- Search layer and object names, including label/path names and referenced asset names. Content filters distinguish empty/filled and used-in-session layers. Raster presence is checked only for an explicit content filter, in bounded 64-row strips cached by raster revision; never infer an empty bitmap from its name or revision number alone.
- Credit a committed edit to its actual affected layers, including captured gesture targets and group/erase edits, rather than whatever layer happens to be selected. Undo/Redo preserves this page-session usage ordering rather than creating a new usage event.
- Put the symbol palette before less-used settings. Keep size directly available; group rotation/variation/snapping/area options in a native disclosure, closed by default. Keep disclosure state through selection, Undo and tool changes. Maintain the visible tool panel's scroll anchor during placement and inspector updates.
- Keep the selection inspector after the stable tool options. Placing a label keeps canvas focus and the current options position; a visible edit-selected-label action deliberately opens/focuses its existing name field. Existing labels remain editable without mandatory preconfiguration or a second naming form.

Native radio and disclosure behavior follows [MDN radio inputs](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/input/radio) and [MDN details](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/details); browser checks must verify the actual focus and panel behavior.

## Grid safety and reference grid

- A tile layer containing cells cannot change its cell grid size in place. Restore the visible control and explain why. Offer an explicit new empty tile layer at the chosen size; old cells and raster pixels remain unchanged, and layer creation supports Undo.
- Empty tile layers may still change size within the existing supported values. Reference grid visibility is an independent page-session preference, drawn from the active tile target or stamp-grid/tool size. It does not enable stamp snapping or transform content.
- Arbitrary calibration, the exact snap-anchor pattern and native cell rotation remain required FV05 follow-ups with their own format contracts. FV05 is not closed by this safety slice.

The FV06 File-menu Escape follow-up is also bounded here: consume the menu's handled Escape event so closing it cannot also exit the placement tool. Other FV06 controls remain outstanding.

## Acceptance and rollout

First reproduce the lower-path-target and occupied-grid-movement failures through existing UI on the unchanged source. Then verify lower target/no duplicates, all-hidden refusal, first-path one-step Undo, stable old raster pixels, filtering/recent ordering/reorder limits, native radio keyboard selection, narrow disclosure, independent reference grid, explicit safe new tile layer, tile-as-symbol placement, palette position/disclosure/scroll stability and File-menu Escape. Use real browser input with isolated static/SQLite fixtures; verify save/reload where document content changes.

Run the relevant existing waypoint, layer, tile, brush/erase and storage regressions plus DE/EN catalog checks. Commit/push, compare actual live source and Compose state, build a bounded overlay, back up PostgreSQL without migrations, retain rollback, replace only the app and repeat normal Maps UI journeys with named synthetic QA users. Remove QA data and credentials. Record source/image, role/navigation entry, checks and remaining packets; update the full-version register from evidence.

Medium risks addressed in the contract: hidden-layer writes and gesture target drift are refused; grid changes cannot silently move old content; view-only layer metadata is excluded from exports; filtered ordering retains real stack positions; focus/scroll/disclosure stability is tested. No open product decision blocks this format-preserving slice. Next phase: Deploy implementation and verification of this contract.
