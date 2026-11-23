# Monitor FV04 and the first full version delivery

Status: FV04 delivered and verified. FV05 and FV06 have explicitly partial deliveries; FV01 has reviewed design and a candidate inventory. The complete FV01–FV18 goal remains active. Retention permanent.

## Delivered behavior

Normal entry is main navigation → Maps → new or existing map. The same personal editor is available to the intended DM and Player accounts. [Apply](DADM_APPLY_FULL_VERSION_LAYERS_2026-11-23.md) and [implementation](DADM_DEPLOY_FULL_VERSION_LAYERS_2026-11-23.md) define the scope.

| Scope | Evidence and outcome |
| --- | --- |
| FV04 layer targeting | Lower selected path layer receives the stroke; changing active layer mid-gesture cannot redirect it. Hidden targets refuse before drawing, and no duplicate is created. First path/layer is one Undo step; raster pixels stay unchanged. |
| FV04 compact controls | Native radios select layers, keyboard selection keeps focus and the active radio visible, and separate eye buttons use the existing undoable visibility command. The desktop strip occupies one row; the narrow disclosure opens the compact list or full management panel. |
| FV04 overview | Filter by kind, layer/object/asset name, empty/filled content or use during the session. Counts reflect items/cells; bitmap presence is read from bounded alpha strips and cached by revision. Reorder actions use actual stack positions. |
| FV04 usage and panel stability | Actual edited layers receive recent-use credit, including captured strokes and group/erase writes. Usage is transient and absent from exports. Palette and size precede rare options; native disclosure state is retained and active scatter/area mode stays visible. New label placement keeps controls and canvas focus stable; explicit editing reuses the existing field. |
| FV05 partial | Occupied tile layers refuse grid resizing and offer a new empty layer at the requested supported size. Undo restores the prior document. Reference grid persists across tools without enabling snapping; it retains the existing overlay's density cutoff at very low zoom. Calibration, new snap patterns and native cell rotation remain open. |
| FV06 partial | File-menu Escape closes that menu and restores its button focus without exiting placement. Colors, opacity/brush shortcuts and radial palette remain open. |

Tile-as-symbol preview and placement were separately exercised for the chosen fixture asset, with no lost image. No unsupported catalog reclassification or new artwork was introduced; the remaining catalog/report-specific work stays in FV11. Mixed raster/tile/stamp erase scopes retain their previous behavior.

## Verification

The initial browser reproductions failed at both intended baseline assertions: wrong path target and occupied-grid movement. The first new set passed eleven cases. After the source-review correction, the combined run passed eighteen cases and exposed one desktop overlay interaction in the existing area-fill journey. A narrower one-row strip corrected that; the final six-case run includes the unchanged area-fill budget/Undo assertions and passes. Two final desktop/narrow native-radio visibility cases also pass. The added object/raster-content case and recent-target assertions cover the review rework. Full results and earlier failed runs remain in [verification.json](proofs/full-version-layers-2026-11-23/verification.json); overlapping runs are not added into a suite total.

Existing waypoint connection, keyboard layer choice at 390/1440, private pixel-image roundtrip, label-font roundtrip, mixed eraser and dense scatter/grid journeys passed. Two old test journeys were adapted to open the newly introduced placement disclosure; their behavior assertions were preserved. DE/EN generation and `--check` pass with 3772 sources; all four changed JavaScript modules and new Python scripts pass syntax checks.

Claude's [first source review](proofs/full-version-layers-2026-11-23/claude-review-initial.md) identified one medium recent-use deviation. Codex fixed actual-target bookkeeping and added captured-target/non-active-layer assertions. The [second review](proofs/full-version-layers-2026-11-23/claude-review-final.md) confirms that source correction. Subsequent content filters were reviewed by Codex and verified in the final focused cases. No test or production action was delegated to Claude. The existing subscription was used without provider or extra-usage fallback.

Two **authenticated live journeys pass on the final image**: Chromium DM at 1440/DE/night and Firefox Player at 390/EN/paper. They use the ordinary dashboard → Maps entry and real controls, verify lower target/no duplicates, native keyboard focus, filters/recent controls, occupied-grid preservation, explicit new layer/Undo, active disclosure summary, menu Escape and independent reference-grid control. Real file download and upload are checked with an observed document generation change, preserved path/layer identity and unchanged tile cells. Neither journey reports a browser error or page overflow. [Live results](proofs/full-version-layers-2026-11-23/live.json), [DM image](proofs/full-version-layers-2026-11-23/layers-chromium-1440-de.png), [Player image](proofs/full-version-layers-2026-11-23/layers-firefox-390-en.png).

The narrow live helper uses the real Tool tab when the layer sheet is open and language-independent file-menu button IDs. An earlier local picture probe closed the narrow layer sheet by clicking its already-active tab; the helper was corrected to open it only when necessary. Application behavior was not changed for that probe.

## Source and operations

- Source: `207c8e9fc8a465168c23d5528836ae3c95f3a619`, pushed to `origin/fix/feedback-harness-20261123`.
- Image: `roll-drauf-vtt-app:full-version-layers-20261123-207c8e9fc`; identity `sha256:384ab8657919735f893eaa2dad1e249c5ead23ad03108494778103ec1851146c`.
- Base: `7e0a3c859`, image `sha256:fd604eee0ca2481eddad4658262a32cc112327a60db847b4a18a02893abc1af7`. Baseline and built source checks pass for 334 shipped source/changed-JSON files. All nine overlay files match their committed hashes in the running app. Untouched artwork is inherited from the checked immutable base; superseded G1 files remain absent.
- PostgreSQL archive: 539343 bytes, `pg_restore --list` successful. No migration or dependency change; a full restore was not exercised. Only the app was recreated. Database, Redis and mailserver retain identity/start times; `/health/live` is `ok`.
- Rollback: `/srv/migration/2026-11-11/feedback-full-version-layers-20261123/207c8e9fc/rollback.sh`, syntax checked, not executed. It restores the protected preceding app image/configuration.
- QA cleanup passed: two synthetic users, three campaigns, two sessions and all their prepared dependent rows removed. Host/container credentials are removed. Local downloaded maps are retained only as synthetic release evidence; no real user project was modified. [Cleanup](proofs/full-version-layers-2026-11-23/qa-cleanup.json), [source and health](proofs/full-version-layers-2026-11-23/live-source-health.json), [release record](proofs/full-version-layers-2026-11-23/delivery.json).

## Remaining full version work

FV01's [reviewed language design](DADM_APPLY_FV01_CHARACTER_LANGUAGE_2026-11-23.md) keeps the canonical mechanics separate from presentation. The reproducible [inventory](proofs/full-version-layers-2026-11-23/fv01-inventory.py) finds candidate matches for all 339 spells: 310 single-candidate signatures and 29 ambiguous cases. No identity is approved by this inventory. Every pair needs semantic entry comparison and a reviewed mapping before it can change character display. Creator/editor language behavior is not implemented yet.

The other full-version packets remain as recorded in the [active register](plans/VTT_NEXT_FULL_VERSION_2026-11-23.md). Open public AI-content policy and identification of the older 0% control/clipped asset have been requested asynchronously; no answer or default approval is assumed. These inputs do not block independent technical packets. The inherited FV18 suite/timing, physical keyboard and real external/OAuth checks remain open. No full-version completion or fully green repository suite is claimed.

Recommendation: close FV04, retain partial FV05/FV06 statuses and proceed with the validated FV01 presentation crosswalk and module-scoped locale implementation. Preserve this live layer/grid work in every following release.
