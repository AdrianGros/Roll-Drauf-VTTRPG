# Mapmaker DAO review — requirements and completeness

**Date:** 2026-10-24, 11:50 UTC. **Phase:** DAD-M Monitor, standard runtime cards. **Status:** independent requirements review complete; branding and interaction reviews run separately. **Scope:** source and existing proof inspection; no source edits, live database, production scan or campaign writes.

The current editor contains the essential first-value world/regional mapmaking loop: open an editable example or blank document, paint terrain, place symbols and named places with lore, revise with layers/undo, save an editable project, and export a usable PNG. I found no missing implementation that independently blocks that bounded prototype. It does not yet constitute an integrated worldbuilding database or full Inkarnate/GIMP equivalent. Those are documented subsequent workstreams. The requested VTT branding pass is new work and is not covered by the earlier prototype acceptance.

## Input and evidence boundary

The user requested a first most valuable usable prototype, Inkarnate-like mapmaking, GIMP-like brush editing, curated free assets, Claude coding with Codex review, and subsequently VTT brand harmonization and agent testing. “DAO” was clarified to mean agents exercising actions, reviewing visual structure and checking completeness, rather than a data-access architecture test.

Evidence was independently read from the product modules and UI, current curated asset files, earlier research and the original DAD-M record. Seven static checks were freshly executed. Prior browser results are identified as recorded evidence, not falsely presented as freshly rerun here. Other agents own fresh exhaustive interaction/visual testing. Current JS SHA-256 hashes are in `inventory.json` so this assessment can be tied to the source reviewed.

## Earlier research found

- `docs/DADM_DISCOVER_MMO_META_LAYER_CONCEPT_2026-07-21.md:38`: F-02 identifies terrain painting, custom layering and the asset-marketplace gap, and explicitly separates a proper map editor from MMO progression. This is a research foundation, not a complete implemented editor specification.
- `docs/UI_ANALYSE_WORLD_ATLAS_HOME_2026-08-18.md:628`: §10.5 identifies a separate world/atlas model instead of overloading tactical `CampaignMap`. §§15 and 20 defer free world positioning and hierarchical world-model work. The dashboard atlas is navigation, distinct from authoring a map.
- `docs/PLAYTABLE_FEATURE_RESEARCH_03_MAP_TOOLS_2026-08-27.md`: relevant input/accessibility experience, but it concerns tactical measurement, not a specification for this terrain editor.
- Repo-wide text searches found no separate Paritar requirement or prior GIMP editor specification. I cannot confirm what “Paritar” denotes from repository evidence. It is not silently treated as a missing contracted feature.

## Requirement-to-evidence matrix

“Recorded” below refers to `docs/MAPMAKER_PROTOTYPE_DADM_2026-10-24.md:341` and its linked proof files, plus inspection of the named actual tests. “Fresh” means executed in this review.

| User need / bounded promise | Implementation and visible surface | Evidence / missing limit | Assessment |
|---|---|---|---|
| A useful first map, immediately editable | `js/starter.js:104` supplies three raster layers, symbols and labels; `createStarterMap` seeds geography, settlements and lore; “Neue Karte” offers example or empty document (`index.html:206`) | Saved proof independently parsed: 2400×1600, 5 layers, 60 stamps using 22 distinct curated assets, 13 labels, 7 places, all 7 with nonempty lore | Present; useful starting content rather than a decorative preview |
| GIMP-like brush editing | `js/brush.js:1` stroke mask/compositing; 11 terrain materials (`:7`); UI size, opacity, softness, pressure checkbox and preview (`index.html:132`) | Recorded browser cases verify measurable size/opacity/softness/pen pressure changes, cancellation, exact undo/redo and erasing land to sea; physical stylus not established by those tests | Present for the agreed prototype controls; not full image-editor parity |
| Inkarnate-like cartographic composition | Stamp palette, size/rotation/flip/variation/scatter (`index.html:146`); selection/move and label tools; procedural sea/coast/texture rendering | Source and recorded tests cover place/move/delete/scatter; vector road/border tools, mask tools and marketplace are absent and deferred | Present at first-value level |
| Free assets, judged and sorted for integration | `assets/kenney-cartography/manifest.json`, README, original License.txt; loader `js/stamps.js:111` | **Fresh:** all 40 images decode and match manifest dimensions and SHA-256. 38 stamps in 5 groups, 2 textures; 1,380,589 bytes total. 38 stamp categories: terrain 6, vegetation 7, settlements 10, adventure 12, navigation 3. License text is CC0 with optional attribution. Sources/original filenames/retrieval/archive hash retained | Present and integrated; no paid/external fetch dependency |
| Usable layers and safe revisions | Layer add/delete/rename/order/visibility/opacity/coast (`js/app.js:381`, `js/ui.js:425`); bounded history `js/history.js:5` | Recorded browser tests cover layer changes and undo. Budget is 60 commands/64 MiB, 32 total layers, 8 raster layers, ≤32 million raster pixels; not unlimited editing | Present; memory limits are explicit |
| Minimal worldbuilding, not only a painting | Named places, six place kinds, styled labels, 500-character lore, selectable linear Orte list (`js/document.js:24`, `js/ui.js:315`, `:528`) | Fresh saved-proof inspection confirms lore data retained in JSON. Recorded test verifies literal hostile text and place editing. No quests, factions, relationships, nested regions or journal integration | Present for short local place notes; deeper worldbuilding intentionally unbuilt |
| Preserve editable work and move to another device | `.rdmap.json` import/export (`js/app.js:802`), PNG bytes with document v1 contract (`js/document.js`); browser-local IndexedDB single autosave (`js/storage.js:3`) | Recorded round-trip/restore/rejection/concurrent-save regressions; malformed imports leave the map intact. **No account sync, server drafts, multi-document gallery or simultaneous editing** | Present as local-file workflow; do not describe as cloud persistence |
| Use the result in the VTT | PNG 1×/2× export (`js/app.js:842`), campaign handoff hint (`index.html:225`) | Actual existing `campaigns.html:2849` accepts PNG/JPEG/WebP ≤50 MiB, uploads `asset_type=map`, then posts map `background_url` and size. Source path matches the instructions. **Campaign import was not executed by this review.** PNG flattens layers and labels; lore is not transferred into campaign entities | Appropriate manual prototype handoff; semantic/clickable world integration remains future work |
| Entry point and discoverability | `/mapmaker` template redirects to `/static/mapmaker/index.html`; preview `/mapmaker/` | Fresh static checks confirm entry/resource contract. Recorded Flask browser test covers app serving under real CSP. No existing VTT navigation link; deliberate dirty-tree boundary | Reachable by known URL; app-wide discoverability is a small follow-up |
| Mobile-friendly authoring | Six tools, tabbed panel and ≤760 px bottom sheet; touch/pen pointer handling | Recorded 1440/390 viewport and synthetic second-finger tests. Safari, physical phones/stylus, low-memory-device performance remain unproven | Prototype coverage present; not a physical-device certification |
| VTT brand harmony | Current reviewed header still has generic star and “Kartenwerkstatt”; CSS uses teal editor chrome and Literata tool body | Canonical product tokens are in `vtt/static/css/theme.css`. This task's aesthetic work is pending/parallel, so old acceptance cannot establish the new requirement | New task requirement; requires fresh visual review after aesthetic changes |
| Claude implementation with independent Codex review | Prototype DAD-M record assigns Claude implementation and Codex review; saved regression/proof artifacts exist | Prior record lists 34 passing static/browser checks and five corrected medium correctness issues. This review read those artifacts and code; it did not re-perform every browser action | Process evidence present; new agent findings must still be triaged independently |

## Findings and practical limits

No new medium/high completeness finding was established in this bounded review. The following limits matter to the handoff:

1. **Low — VTT discoverability.** The working editor has no main-app navigation entry, and the export hint is text rather than an actionable link. The existing design explicitly excluded existing dirty navigation files (`MAPMAKER_PROTOTYPE_DADM...:73`). A URL is sufficient to review this prototype; a normal product release should supply a deliberate entry and return path.
2. **Info — semantic worldbuilding is local.** Lore remains in the project file/browser draft. The campaign path only receives a flattened background image, as confirmed by `campaigns.html:2894` and `vtt/models/campaign_map.py:8`. Do not promise clickable lore or world→region→battlemap navigation from this delivery.
3. **Low — validation boundary.** Existing screenshot/Chromium evidence and synthetic pressure do not prove real mobile/stylus behavior or low-memory performance. Manual campaign transfer has a valid code path but was not demonstrated end to end here.
4. **Info — aesthetic acceptance is separate.** Branding harmonization is explicitly requested now; this review of the pre-pass source does not close it. Preserve map content/export colors when adjusting editor chrome.
5. **Info — Paritar remains unidentified.** No repo evidence defines that term. Do not invent requirements or claim competitor parity from it.

These are not reasons to add a marketplace, MMO layer, permission model, collaborative server storage, or full image-editing suite inside the aesthetic pass. New defects from independent agents should be severity-triaged as their own evidence.

## Fresh verification

- `/tmp/roll-drauf-mapmaker/test-venv/bin/python -m pytest tests/test_mapmaker_static.py -q -p no:cacheprovider` → **7 passed in 0.46 s**.
- Read-only Pillow/JSON/SHA-256 inventory → **40/40 valid images; zero hash/dimension/missing-asset errors**; all saved-proof Kenney IDs exist in the current manifest.
- Parsed saved editable sample → exact counts above; all seven place descriptions present. This validates the retained artifact, not a new UI save interaction.
- No production requests, server/database writes, dependency installation or source changes.

## Recommended next bounded action

Consolidate this matrix with the interaction, visual and independent Claude security reports. Close the requested aesthetic iteration only after its new visual acceptance and behavior regressions pass; any reproduced medium-or-higher defect needs explicit disposition under the repo governance. For the next product milestone, the highest practical value is a deliberate VTT entry/return and a proven PNG campaign transfer before broader world-model functionality.

**Artifacts and retention:** this report and `inventory.json` are review evidence; retain with the DAO run. **Risks and assumptions:** assessments use the prototype's documented bounded scope, not full competitor parity. **Product files changed:** none.
