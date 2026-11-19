# K22 implementation and integration handoff

19 November 2026. Implementation of the bounded, accepted [Apply](DADM_APPLY_REVIEW_FLOORS_2026-11-18.md), base `49e8b9944`. No deployment, production data, dependency installation or remote push. Parent owns normal PlayUI wiring and final delivery.

## Implemented behavior

Private, ordered PNG artwork levels share an existing map's world dimensions. The server composes only the active level and lower levels. Transparent pixels and explicit rectangular openings reveal lower art only where the level's `reveal_below` is enabled; otherwise those pixels are opaque black. Higher levels never enter the composition. The server applies the existing wall/light/fog projection to the actual output pixels for a Player or DM token preview, then encodes opaque RGB PNG. Removing a browser overlay or alpha channel cannot recover concealed artwork.

Sources use the existing StorageAdapter at private `users/<campaign owner>/map-floors/...` keys, without Asset rows, public URLs or source references in a Player response. Raw sources, catalogue and all mutations require a current DM table context. An actual campaign member and an owner sitting as Player are denied those endpoints. Player requests can only project the session's active map; token previews are operator-only and never write exploration.

All writers reserve the campaign owner's quota under the existing owner row lock before locking the map; a deck revision supplies CAS. Upload requests deduplicate by map/request ID and input digest; deleted requests retain a DB tombstone. Canonical PNG re-encoding strips ancillary metadata. Limits: 8 sources, 4 MiB per source, 16 MiB sources per map, 16 million aggregate source pixels, 2048 pixels per side, exactly the current map world size, 32 bounded integer rectangles per source. Partial upload failures release the transaction and delete the unique partial object. Delete commits quota release and then cleans storage; cleanup failures use the existing logged best-effort policy. A realtime notification failure after commit does not delete a committed object. View/config/source responses are private/no-store.

The common module polls every 4 seconds, binds responses to map/preview generation and uses an opaque black loading/error surface. The DM module exposes upload, activation, active selection, ordering, per-level reveal-below and numeric rectangle controls in a separate window. The visible limitation is: artwork levels retain shared 2D tokens, walls, lights and fog; no height simulation or inter-floor movement.

## Exact parent integration

The shared registry, template, PlayUI and feedback files were deliberately not edited in this worktree.

1. In `vtt/models/__init__.py`, import `from .map_floor import MapFloorDeck, MapFloorImage`. In app blueprint setup, import `from vtt.play.floor_layers import floor_layers_bp`, then `app.register_blueprint(floor_layers_bp, url_prefix='/api/play')`. Additive tables must exist before feature routes are enabled.
2. Load common `/static/css/play-floor.css` and `/static/js/play-floor-view.js` before `play-ui.js`. Append `/static/js/play-floor-dm.js` to the existing server-authorized DM-only loader beside `play-feedback-dm.js`.
3. Immediately after existing feedback/feedbackDM creation:

```javascript
this.floorView = new window.PlayFloorView(this);
if (this._composedOperator) this.floorDM = new window.PlayFloorDM(this);
```

4. In `_renderMapCanvas`, select the background with:

```javascript
const background = this.floorView
    ? this.floorView.background(activeMap)
    : activeMap?.background_url;
```

Use `background` in the existing source/display block instead of `activeMap.background_url`. `background()` returns the old URL only after the server confirms the deck is disabled; during loading/error it returns an opaque cover, and for enabled floors it returns the final PNG.

5. Alongside existing `feedbackDM?.refresh()` calls, call `this.floorDM?.refresh(); this.floorView?.refresh();`. `refresh` already throttles/binds requests; DM refresh reloads only on map change.
6. In `PlayFeedback.lighting`, retain the existing token preview visibility update, then before assigning `result.overlay`:

```javascript
if (this.ui.floorView?.masked) {
    this.image.hidden = true;
    this.ui._illuminationActive = true;
    document.querySelectorAll('#visionLayer .fog-cell')
        .forEach(node => { node.style.display = 'none'; });
    return;
}
```

This prevents applying lighting a second time to the already masked floor image. The map's token filtering/preview logic remains active.

7. In DM preview `onchange`, immediately after assigning `ui.feedback.previewToken`, call `ui.floorView?.refresh(true)`. This synchronously replaces the prior DM raster with the black cover before awaiting the preview request. Keep existing preview status/marker handling. Ensure any `_renderVisionLayer` legacy-cell guard respects `_illuminationActive` as it does for existing precise lighting.

## Additive schema

`MapFloorDeck` / `map_floor_decks`: `map_id` Integer PK/FK `campaign_maps.id`; nonnull `revision` Integer default 0, `enabled` Boolean default false; nullable `active_floor_id` Integer, validated against the same map's live source set in every write. The active ID deliberately avoids a circular FK; all removal/selection/order mutations run under the map lock.

`MapFloorImage` / `map_floor_images`: Integer PK `id`; indexed nonnull FK `map_id`; nonnull `order_index`, `name` String(80), `reveal_below` Boolean, `openings` JSON, private `storage_key` String(512), `storage_provider` String(20), `png_sha256` String(64), `size_bytes`, `width`, `height`, `request_id` String(80), `input_digest` String(64), FK `created_by`, `created_at`; nullable `deleted_at`. Unique `(map_id,request_id)`. No existing table fields or rows are changed for maps without an enabled deck.

## Verification

- `tests/test_floor_layers.py`: **19 passed**, including actual-member and owner-as-Player raw access/config/mutation denial; same-map lookup and revoked context; real red/green/blue balcony pixels; no higher artwork; reveal-off black openings; alpha/reorder/delete active neighbor; opaque RGB wall/darkness/fog pixels; preview without fog writes; role/actor view keys and unchanged responses; CAS, replay/tombstone, quota reservation/release, partial upload cleanup, PNG validation, exact dimensions, real 8-floor and 16M-pixel limits, narrowed canonical-byte budget, missing/changed-source fail-closed and no Asset rows; old map behavior.
- `tests/test_floor_layers_browser.py`: **1 passed** in real Chromium against the isolated live Flask API. Actual shipped modules run unchanged in a small host of the parent-owned UI integration contract. DM uploads two PNGs, edits and saves an opening, enables/selects the balcony. An authenticated member gets red lower art through the opening, green active art elsewhere and actual black pixels behind a wall; reload persists behavior. DM preview covers the privileged raster immediately and returns wall-clipped pixels. Member source/config reads return 403, no DM module or button exists, and failed view refresh covers prior artwork.
- Existing regression batch `tests/test_ui_playtable_complete.py tests/test_playtable_vision_fog.py tests/test_vision_engine.py`: **34 passed**, preserving prior map settings, walls/lights, fog, visibility and token behavior. View requests are limited to 60/minute per account; the 4-second polling interval leaves room for simultaneous DM/Player tabs and manual refreshes.
- Browser screenshots inspected: [DM editor and preview](proofs/review-floors-2026-11-19/floor-dm-editor-preview.png), [member raster](proofs/review-floors-2026-11-19/floor-member-raster.png), [member error cover](proofs/review-floors-2026-11-19/floor-member-failure-cover.png).
- All tests used the existing `roll-drauf-vtt-mobile-tests:20261115` image, own checkout at `/app`, network disabled and read-only browser cache. No production environment/database. Initial browser harness run failed because a Playwright callback received its Request argument in a default HTML parameter; corrected fixture and successful rerun, no application workaround.

Normal table integration, combined role/source inspection and normal-page browser coverage remain the parent's required final gate. The small browser host proves modules and API, not that parent wiring has already shipped.
