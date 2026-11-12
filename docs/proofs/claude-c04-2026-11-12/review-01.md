# C04 independent review: no blocking findings (static source reading only)

**Scope:** I read `review-input.diff` and the C04 files it touches, plus these existing code paths:
- `vtt/play/receipts.py`
- `vtt/play/contexts.py`
- `vtt/upload_security.py`
- `vtt/endpoints/mapmaker.py`
- the `brush.js` stroke engine
- `history.js`
- `play-ui.js`'s existing table map upload
- `auth.js`

I executed nothing. I did not review the `tests/test_c04_*` files or `tasks/c04.json`, because they are not in the diff.

## Confirmed in source
- **DM-only route:** `create_map_library_snapshot` requires `g.table_context.mode == "dm"` and an operator role, so owning the campaign does not lift a Player context. It re-validates the context under the user-row lock.
- **Project ownership:** the project is looked up with `owner_id=user.id`, so another user's project returns 404.
- **Revision and dimensions:** these are re-checked after the lock and refresh. A stale revision returns 409.
- **Quota:** the same shared `storage_used_gb` counter as other uploads. It is reserved in the transaction and rolled back on failure.
- **Receipt:** the digest covers the normalized fields plus `png_sha256` and the credits, as `receipts.claim` expects. The claim has a 24h expiry. `_release` frees a claim whose failure left no side effects.
- **Cleanup after a throwing write:** keys are registered before `storage.upload`, so a write-then-raise is cleaned up in `finally`.
- **Thumbnail failure:** it is cleaned up separately and does not abort the request.
- **Commit with unknown outcome:** the `except` path checks for a completed receipt before cleanup, so a commit that actually succeeded keeps its files.
- **PNG validation:** `validate_upload` does not re-encode, so the stored bytes are exactly the uploaded bytes. The route checks the signature, a size cap and `Image.load`. Players cannot reach the route.
- **Player never imports the module:** `play-map-library.js` is only dynamically imported from `play-dm.js`. That call is gated by `_composedOperator`, and the button lives only in `dm.json`. No template references the module. I did not confirm how `play-dm.js` itself is delivered; that is existing composition.
- **Snapshot helper:**
  - Asset URLs resolve via `import.meta.url` in `stamps.js`.
  - There is no global fetch/`Image` shim.
  - `loadSnapshotFonts` awaits all five faces before rendering.
  - Credits come from the document.
  - The two-stage retry reuses one `request_id` and does not re-upload once `pending.mapId` is set.
- **History preflight:** `canFit` plus `strict` refuses an oversized step without clearing earlier undo steps. Brush strokes and the eraser both preflight and cancel their gesture.
- **Eraser scope:** it covers only raster, tiles and stamps. Paths and labels are untouched. `eraseTargets` follows the active layer or the explicit visible scope, with no silent layer switch. Cancel restores raster, tiles and stamps. The 8 bytes per pixel estimate matches the real before/after sizes.
- **Stamp grid and tile variants:** the stamp preview and placement share `stampPoint`. Variant selection is memoized once per cell per gesture in `gesture.choice`.
- **Locale markers:** hashes for four of the new markers are present in `locale-markers.json` (grep count 4). I did not check the JS `VTTUi(...)` strings against `tasks/c04.json`.

## Findings

**Medium**
- **Stamp grid with scatter**, `tools.js` scatter branch → `createStamp` → `stampPoint`:
  - **Trigger:** grid is on, scatter is on, and the grid is larger than the scatter spacing (`max(12, size*0.75)`). A grid of 128 with a size-88 stamp (spacing 66) is enough.
  - **Impact:** several scattered stamps snap to the same point and stack as duplicates. They eat into `LIMITS` and make the scatter look wrong.
  - **Smallest fix:** in the scatter branch, skip `createStamp`/`placeLive` when the snapped position equals one already in `gesture.items`.
  - **Blocking?** No. Undo recovers it, and it affects only an option combination.

**Low**
- **Tile variants**, `app.js` `chooseTile` and the `ui.js` variant UI:
  - **Trigger:** variants exist and the user selects a different palette tile.
  - **Impact:** the pool is only the variants, so the new selection is silently ignored while it shows as selected.
  - **Fix:** clear the variants on a plain palette selection, or show a "variant mode active" hint in `tileTarget`.
- **Eraser memory**, `beginErase`:
  - **Trigger:** "all visible layers" scope on a large map with several raster layers.
  - **Impact:** each raster layer gets its own `StrokeEngine` with 3 full-size canvases, and none are released after the gesture.
  - **Fix:** set `width = 0` on `engine.base`, `engine.mask` and `engine.work` in `endErase` and `cancelErase`.
- **Frozen retry state**, `play-map-library.js` `submit`:
  - **Trigger:** a definitive 4xx failure before stage 1 completes (for example 400 or 507), then the user edits the name or grid and retries.
  - **Impact:** `pending` keeps the old name and grid, so the edit is silently ignored until the dialog is closed and reopened.
  - **Fix:** reset `pending` on definitive 4xx responses other than 409 `request_in_progress`. Keep it on network or unknown outcomes, where the same request ID is the point.
- **Replay edge case**, `map_library.py` `_read_png`:
  - **Trigger:** a retry after the project was resized or deleted in another tab.
  - **Impact:** the route returns `dimension_mismatch` or 404 before the receipt lookup, instead of the stored 201.
  - **Fix:** none needed to integrate. Optionally look up the receipt before the PNG dimension check.

## Conditional or unexecuted evidence (not run by me)
- The browser harness table rerun after the 30s DM roster timeout increase (9 passed, 1 failed before).
- The API and static runs (26 passed after rework).
- The 5 existing editor browser cases that passed earlier.
- Real pointer, library-to-table, Player and retry journeys exist only as the pending harness cases, not as a live run.
- No live C04 evidence exists yet.

## Verification gaps
- No test files, `tasks/c04.json` or compiled locale files were read.
- I did not confirm every new `VTTUi` string has a DE/EN entry.
- I did not verify that the player surface cannot load `play-dm.js` beyond the absence of template references.
- Decompression-bomb limits rest on project dimensions being capped at creation (not checked here) and the client's 64M-pixel snapshot limit.

**Verdict: ready_for_integration.** This is conditional on the coordinator's browser rerun passing. The Medium and Low items are recommended follow-ups, not blockers. This is not deployment approval or live delivery.
