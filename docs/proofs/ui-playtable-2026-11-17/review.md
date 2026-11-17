# Independent UI/Playtable risk review

Date: 2026-11-17. Reviewer: `play_review`, independent read-only code review;
this report is the reviewer's only repository edit. Scope: the complete Apply
contract and the new scene settings, hierarchy, initiative, illumination,
coordinate handling, Conversations history and Playtable feedback UI.

No unresolved release-blocking finding remains in this reviewed scope after the
source recheck. This is a source/targeted-check conclusion, not production acceptance.

## Findings and verified corrections

| Finding | Severity | Correction checked in source |
| --- | --- | --- |
| Failed projection requests removed Player fog protection. | High | `play-feedback.js:24–54`: initial/new-map opaque cover, retain a valid same-map projection on errors, restore cell fog when projection is disabled. Response `map_id`, local map and request sequence are checked; mismatched map responses trigger cover and bootstrap refresh. |
| Legacy map dimensions produced undersized masks; grid changes moved map art relative to tokens. Tiny normalized dimensions could be interpreted twice as cells. | High | `vision.py:163–178`, `scene_settings.py:55–70`, `lighting_routes.py:47`, `play-feedback.js:31–34`, `play-ui.js:4359–4373`: common world-coordinate contract; freeze dimensions and token positions before changing grid; preserve metadata and mark normalized dimensions with `light_rules.dimensions_mode='pixel'`, including dimensions below 201. Existing exploration requires explicit reset confirmation. |
| Library clones silently lost finite sight limits. | Medium | Both creation constructors now validate and persist `sight_range`: `campaigns/routes.py:1556–1577`, `socket_handlers.py:1086–1109`. Linked-character creation still reapplies canonical character HP. |
| Structural/batch token events left stale illumination. | Medium | The central scheduled token render calls both feedback refresh methods in `play-ui.js:3267–3270`; DM refresh invalidates a removed preview token and restores marker visibility. |
| Parent selection also activated the map; map changes left DM markers hidden after preview. | Medium | Row click/key handlers exclude native interactive controls in `play-ui.js`; `play-feedback.js:26` and DM preview handlers save/restore marker visibility. Privileged handlers remain in the dynamically loaded DM module. |
| Square measurement jumped across axes; southwest circle labels appeared inside. | Medium | `play-ui.js:1471–1490`: explicitly labelled centre-first square and outward radial label positioning/text anchor. |
| Darkness projection disagreed with fog exclusion. | Medium | `illumination.py:76–89`: darkness retains the flat exclusion zone used by the fog engine. Previously reproduced point `(50,50)` had fog visibility false but projection alpha 0; corrected targeted test expects alpha 255. |

## Verification performed by this reviewer

Existing isolated Docker test image, repository mounted read-only, no network:

```text
python -m pytest -q --disable-warnings --maxfail=1 -p no:cacheprovider
  tests/test_ui_playtable_complete.py::test_grid_settings_require_dm_context_and_revision
  tests/test_ui_playtable_complete.py::test_lighting_is_a_private_wall_clipped_image_and_preview_does_not_write_fog
  tests/test_ui_playtable_complete.py::test_new_template_token_preserves_finite_sight_and_rejects_bad_values
  tests/test_ui_playtable_complete.py::test_darkness_matches_fog_exclusion_and_large_light_radius_is_bounded
4 passed, 67 warnings in 11.23s
```

After the final map-response guard and explicit dimension marker edits, reread all
affected source and reran the darkness/radius/world-size test, now including the
`128×96` explicit-pixel assertion: **1 passed, 1 warning in 4.05s**.

These checks cover DM versus Player/owner-in-Player context, preserved grid token
positions, wall-clipped private PNG delivery, preview without fog writes, finite
sight creation and invalid values, Darkness consistency, and large-radius output.
The new affine radial sampler allocates the projection plus a fixed gradient,
rather than a radius-sized intermediate bitmap.

## Limits and residual observations

No full suite, browser rerun, commit, deployment or live acceptance was performed
by this reviewer. Socket sight persistence, click bubbling, measurement geometry,
map mismatch recovery and final mask sizing were source-checked; the release owner
must retain their targeted/browser/live verification evidence separately.

A cold polygon probe with 400 walls produced 2,504 points in 0.732 seconds in the
test image. Static polygon caching helps, but unusually complex maps can still
make movement projections expensive; this single measurement does not establish
a production performance failure. No new role-escalation path was found in the
reviewed changes: privileged operations still depend on server-authorized table
contexts, and historical chat selects only public, visible, nondeleted rows after
membership/sanction checks.
