# FV04/FV05/FV06 source review, MONITOR phase

This review is based only on the supplied diff, the Apply contract and the tests. It is not a test result or a live approval.

## Blocking high/medium issues

**No supported high-severity blockers.** I found one medium contract deviation. It does not lose data.

### M1: Recent use is credited to the active layer, not the layer actually written

- **Where:** `app.js` `commit()` calls `this.ui.noteLayerUse(this.activeLayer())` for every command.
- **Contract:** recent use means a deliberate selection or a successful write to that layer.
- **Triggers:**
  1. Draw a path while the active layer is a raster or stamp layer. `pathTarget()` falls back to the top visible paths layer, but the raster/stamp layer gets the recent mark.
  2. In the journey `test_path_keeps_gesture_target_when_keyboard_changes_active_layer`, the stroke lands on `lower`, but the layer selected by Alt+↑ is credited. That layer was already marked by `setActiveLayer`, so `lower` loses its write credit.
  3. Toggling visibility of a non-active layer from the strip or panel credits the active layer. Reorder, rename and opacity do the same.
- **Effect:** "Zuletzt genutzt" ordering is wrong after cross-layer writes. This is view-only, with no document, export or Undo impact.
- **Smallest correction:** stop marking in `commit()`. Call `noteLayerUse(layer)` where the target is known:
  - `addItems(layer, …)` and the item-update paths
  - tile/brush/erase commits, using their resolved target
  - `addPath`, using the resolved or created layer

  For `layerCommand`, either mark the affected layer or skip marking if a visibility toggle shouldn't count as a write. Add one assertion to the existing gesture-target test that sorts by recent use and expects `lower` first.

## Checked areas with no supported defect

- **Path targeting and hidden layers:**
  - `pathTarget()` delegates to `targetLayer("paths")` whenever any paths layer exists.
  - A hidden selected layer, or all paths layers hidden, returns `false` before `commitEdit()` and before preview, so nothing is written and no duplicate is created.
  - A new layer is created only when no paths layer exists, and only at commit. It is a single command, so one Undo step.
  - New layers are named "Wege (Vektor)", which never collides with or converts the "Flüsse & Wege" raster.
- **Gesture capture:**
  - `targetId` is fixed at pointerdown.
  - At commit, `addPath(item, targetId)` re-resolves by id and refuses if the layer is missing, hidden or the wrong kind.
  - If a layer is deleted and the deletion is undone, the same layer comes back with the same id, which is acceptable.
- **Occupied-grid refusal:**
  - `setLayerProp(gridSize)` returns before any command when `layer.cells.size > 0`, so cells and raster pixels can't move.
  - Empty layers keep the existing off-map check and the undoable command.
  - `newTileLayer` goes through `addLayer`, so it is one undoable step, and it restores `tileOpts.size` on failure. The test covers grid, cells, Undo and dirty state.
- **Filtering and reordering:**
  - Up/down disabled states use `ed.doc.layers.indexOf(layer)`, and `moveLayer` moves within the real stack.
  - The stage strip renders the unfiltered list, so filters only change the panel view.
  - Use data lives in a `WeakMap` on `UI`. It is not part of document, autosave or Undo state.
- **Native radios and focus:**
  - The radios share one `name`.
  - On `change`, `setActiveLayer` rebuilds the list, then focus returns to the same layer and `data-layer-control` with `preventScroll`. The newly checked radio stays focused, which the test confirms.
  - Panel `scrollTop` and strip `scrollLeft` are restored.
- **Disclosure and placement stability:**
  - `#stampAdvanced` is static DOM that nothing re-renders, so its open state survives selection, Undo and tool changes.
  - The inspector now sits after the tool options, so a new selection can't push the options down.
  - Label placement no longer steals focus. `editPlacedLabel` opens the existing field.
- **File menu Escape (FV06):** `preventDefault` plus `stopPropagation` on the handled Escape. The test verifies the tool is unchanged and focus returns to the button.

## Low-severity notes (not blocking, optional)

1. **Stale tile-grid offer.** `tileGridOffer` is cleared on load, on an empty-layer resize and after creation. It is not cleared on Undo or when the active tile layer changes, so the notice and button can linger with a misleading message. It still does nothing until clicked. Fix: call `clearTileGridOffer()` in `setActiveLayer`.
2. **Reference-grid size source.** `this.stampOpts.grid` is used as a size. Confirm it holds a number, or `0`/`null` when snapping is off, not a boolean. The test asserts only that the canvas changed.
3. **`aria-expanded` on desktop.** `syncStageLayers` sets `aria-expanded="true"` on desktop while `aria-controls` points at `pane-layers`, which may be hidden. Consider dropping `aria-expanded` when the button just navigates.
4. **Breakpoint match.** `isNarrow()` must use the same 760px breakpoint as the CSS and the `matchMedia` listener. It isn't in the diff, so please confirm.
5. **Refresh on every history change.** `onHistoryChange → refreshLayers` now runs on every history change. If collaborative or remote updates use this path, an open inline rename input in `#layerList` would be destroyed. Check whether `renameLayer` survives a refresh.
6. **Catalog keys.** New strings need DE/EN catalog entries, which the pending catalog check should catch: "{count} Elemente", "Rasterbild", "Sichtbarkeit von {name}", "Keine passende Ebene.", "Wege (Vektor)", the grid offer texts, "Alle Ebenentypen", "Zeichenreihenfolge" and "Zuletzt genutzt". Also, "1 Elemente" is ungrammatical.
7. **Hidden active placement modes.** Area/scatter mode, and its status line `#stampAreaInfo`, are now inside the closed disclosure, so an active fill mode isn't visible when collapsed. This matches the contract; a later refinement could show active non-default options in the `<summary>`.
8. **Tile-as-symbol preview untested.** The contract asks to reproduce preview and placement separately, but the test covers placement only.

## Scope

The remaining FV05 items (calibration, snap anchors, cell rotation) and the other FV06 controls are open by contract and are not counted as defects. No migrations, dependencies, backend or schema changes appear in the diff.

**Verdict:** no supported blockers. Fix M1 before Deploy if recent ordering is part of acceptance. The low notes can be follow-ups.
