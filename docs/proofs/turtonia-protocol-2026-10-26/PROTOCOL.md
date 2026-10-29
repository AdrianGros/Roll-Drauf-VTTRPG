# Turtonia protocol — map creator baseline

**Date:** 2026-10-26  
**Status:** passed as a bounded desktop authoring journey; visual fidelity is approximate.  
**Reference:** [the supplied phone screenshot](reference.jpg).  
**Artifacts and retention:** this directory is retained as `user_journey_proof` for future map-editor reviews.

## Discover

**Input summary:** recreate the visible Turtonia map in Roll Drauf's cartographic style using Chromium and Playwright, and record every inconvenience encountered.

**Current state:** the editor exists in the local working tree at `vtt/static/mapmaker/`; the running VTT container returned 404 for its main editor file. The reference is a 576×1280 phone screenshot whose map is small and partly covered by VTT controls. Its dominant visible features are one broad mainland, an eastern mountain peninsula, a separate southern island, western forests, two volcanic peaks, settlements, and labels. Some names cannot be read confidently.

**Dependencies and risks:** the editor is a static Canvas app with five default layers and curated Kenney stamps. Chromium, Playwright and Pillow were available in a temporary root-only environment. **Medium:** the small reference limits exact tracing and text transcription. **Low:** the preview is local, not a production user journey.

**Next step into Apply:** define a repeatable, UI-driven journey that covers the composition and editable-file lifecycle.

## Apply

**Design summary and boundary:** start from the editor's blank map, use only visible pointer/keyboard/file controls to draw the mainland and island, paint forest/rock/rivers/roads, place symbols and named places with lore, then download both project and PNG. Reopen the project in a fresh browser context and compare its saved content. No product code, database, campaign, or production deployment is changed.

**Interface and acceptance contract:** `rd-mapmaker` v1 remains the editable interchange format; PNG is a visual export. A passing run creates the target composition with at least six named places and 80 stamps, exports a 2400×1600 PNG, and proves every saved layer's raster PNG and object data survive reopening. The browser must report zero page errors. The image is judged against visible reference features, not pixel equality with the obstructed phone screenshot.

**Tradeoffs and deploy handoff:** broad brush strokes and a fixed, seeded stamp sequence approximate the geography. Stamp variation is turned off for a stable exported image. Place names that are hard to read are approximations. The standalone [run.py](run.py) implements this bounded journey.

## Deploy

**Implementation summary:** [run.py](run.py) launches Chromium, serves the local editor with the current VTT Content Security Policy, and performs all authoring through Playwright UI actions. It emits [step screenshots](screenshots/), [editable project](turtonia.rdmap.json), [PNG](turtonia.png), [reopened project](turtonia-reopened.rdmap.json), and [machine-readable results](results.json). Product source files were not changed.

**Verification:** the final replay passed in 88.9 seconds. It created five layers with raster content, 98 stamps, six named places with lore, and two decorative labels. A fresh browser reopened the downloaded project; all layer properties, embedded raster PNGs and objects matched the first download. The 2400×1600 PNG had the same SHA-256 on two successive runs with stamp variation disabled: `d8bc00add4c337ecb8196be78f77a2a36c0ad838736acf4a88cb92d1b24a30cb`. No JavaScript page errors were recorded.

**Acceptance checklist:** blank-map UI path passed; geography and labels authored; project and PNG downloaded; fresh-context import passed; lore and full document round trip passed; visual export inspected; inconveniences recorded in [FRICTION.md](FRICTION.md).

To replay in this workspace:

```bash
/tmp/roll-drauf-mapmaker/test-venv/bin/python docs/proofs/turtonia-protocol-2026-10-26/run.py
```

Future environments need Python with `playwright` and `Pillow` plus Chromium. `TURTONIA_CHROMIUM` can select a Chromium executable, and `TURTONIA_BROWSER_LIBS` can select a shared-library directory. The script uses Playwright's browser installation when the current workspace executable is absent.

## Monitor

**Observed result:** the recreated map captures the broad island layout and the Roll Drauf parchment/ink style. It is an exploratory cartographic interpretation. The coastline is smoother, roads are more schematic, and mountains and some labels are more crowded than in the reference. The editor has no automatic collision avoidance; visual refinement remains necessary for a finished map.

**Residual risks:** **high, pre-existing editor behavior:** importing into a dirty editor can discard unsaved edits, so this protocol imports only in a fresh browser context. **Medium:** settlement icons and semantic places are separate objects aligned by eye; crowded mountain stamps can obscure text. **Low:** rivers and roads are raster strokes rather than selectable paths. This run did not test authenticated VTT campaign import, mobile authoring, or production hosting.

**Recommended next action:** retain this as the E0 desktop user journey, rerun it after editor safety fixes, and use [FRICTION.md](FRICTION.md) to prioritize usability changes. Compare the exported PNG and project content rather than requiring identical internal object IDs or timestamps.
