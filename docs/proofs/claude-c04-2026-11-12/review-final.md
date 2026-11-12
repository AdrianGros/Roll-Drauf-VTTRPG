# C04 follow-up verdict: Medium and Low (eraser canvases) closed, ready for integration (conditional)

This is from static source reading only. I executed nothing, and the dense-scatter and mixed-layer browser tests have not been run by me.

## Closed

- **Medium, scatter with grid** (`tools.js`, lines 260-275):
  - When the grid is on, the gesture computes `ed.stampPoint(point)`. That is the same function the preview and `createStamp` use.
  - It skips placement if a stamp already placed in this gesture has the same x and y. The pointer-down stamp is in `gesture.items`, so it is covered too.
  - `gesture.last` is left unchanged on a skip, so the next sample in a fresh grid cell is placed immediately.
  - Normal scatter without a grid is unchanged, and so is cancel: `removeLive(gesture.items)` only sees the stamps that were actually placed.
  - Scope: dedup works within one gesture, which is the original bug. A scatter that lands on a grid point used by an earlier gesture still stacks, same as single stamps do today.

- **Low, temporary eraser canvases** (`app.js`, `disposeGestureEngines`, lines 1150-1193):
  - It zeroes only the per-gesture engines' `base`, `mask` and `work` canvases and skips the editor's shared `this.engine`.
  - `cancelErase` disposes in a `finally`, after `engine.cancel()` has restored the layer from the base copy. Tile and stamp restore uses data structures, not those canvases.
  - `endErase` calls `engine.end()` first, then disposes in a `finally`.

## Undo/redo ImageData is preserved

`StrokeEngine.end()` builds `before` from `base.getContext("2d").getImageData(...)` and `after` from `layer.canvas.getContext("2d").getImageData(...)`. These are independent pixel copies. They are read before `disposeGestureEngines` runs, and the command closures hold only them. Setting the scratch canvas width and height to 0 therefore cannot touch the undo or redo data. `putRaster` writes onto the layer canvas, which is never disposed.

## Non-blocking notes

- In `endErase`, the `gesture.refused` branch and the later `if (gesture.refused)` return are dead code. Nothing sets `refused`.
- If `engine.cancel()` itself threw, the `finally` would still dispose but the layer would not be restored. This is a theoretical edge case and not a regression.

## Retained Lows (not re-reviewed)

- Tile variants ignore a newly selected palette tile.
- A frozen retry state keeps the old name and grid after a definitive 4xx.
- A replay after a project resize or delete returns `dimension_mismatch` or 404 before the receipt lookup.

## Conditional test gap

- The new dense scatter pointer, undo/redo and cancel test, run together with the existing mixed-layer case, is the only evidence that the dedup and dispose paths work in a real browser. Until it passes, they are source-reviewed only.
- A worthwhile assertion if it is not already there: the stamp count after a dense grid scatter equals the number of distinct grid cells, and undo and redo restore the same raster pixels after the dispose.

**Verdict: ready_for_integration.** It is conditional on the coordinator's browser run passing. This is not deployment approval or live delivery.
