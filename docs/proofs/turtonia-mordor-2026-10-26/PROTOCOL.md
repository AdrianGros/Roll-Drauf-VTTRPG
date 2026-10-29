# Turtonia protocol — ash-basin interpretation

## Discover — complete

**Status:** complete. **Input summary:** rerun the Turtonia baseline user journey in Chromium/Playwright, this time using Mordor as visual inspiration. The previous journey and reference are retained in `../turtonia-protocol-2026-10-26/`.

**Current state and inventory:** the local Kartenwerkstatt preview supports a blank 2400×1600 map, raster land/terrain/road layers, Kenney mountain, crag, volcano, citadel, ruin and marsh-adjacent symbols, linked place symbols, editable JSON download, and PNG export. The revised controls provide typed brush/stamp sizes and automatic starter-layer routing. `../turtonia-fixes-2026-10-26/` proves the editor still reproduces the earlier map byte-for-byte.

**Dependencies:** installed Chromium, Playwright and Pillow in the existing temporary environment; local static server with the VTT Content Security Policy. No production hosting or application changes.

**Risks and assumptions:** low: the palette is parchment-toned, so darkness must come from composition and symbol density rather than a custom dark theme. Low: roads remain raster. Low: the source phone screenshot has small, obscured names; retain the six established Turtonia place names from the first protocol. **Open question:** none blocking this bounded creative journey.

**Next step:** Apply a repeatable authored map journey.

## Apply — complete

**Status:** complete. **Design summary:** keep Turtonia’s mainland, eastern peninsula and southern islet as continuity, but make the eastern interior a barren ash basin ringed by jagged mountains. Put twin volcanoes and a black citadel at its center, marsh and sparse woodland on the western frontier, ruined watch posts at the passes, and roads that lead toward the basin. Use original Turtonia names and lore with a darker tone. Do not copy a published Mordor map or its place names.

**Solution boundary and interface:** author through visible editor controls only. Read-only page evaluation may convert document coordinates to pointer coordinates. Use the same `rd-mapmaker` v1 editable file and 2400×1600 PNG as the baseline; optional linked place symbols must survive import/export.

**Acceptance criteria:** six named places with lore, at least 80 terrain/structure stamps, a legible volcanic composition, zero page errors, a PNG and editable file, and exact item/raster roundtrip in a fresh browser. Record actual new inconveniences separately from old scripted friction.

**Risks and tradeoffs:** dense mountain clusters can collide with labels; manually reserve clear basins for text. Custom sea coloring and editable paths are outside the editor UI. No product-code changes or dependency changes.

**Deploy handoff:** create a new `run.py` using the baseline journey structure, inspect its export visually, adjust through UI actions if needed, then save results, screenshots and friction notes here.

## Deploy — complete

**Status:** complete. **Input summary:** author the ash-basin Turtonia map through the updated local editor and retain a replayable proof.

**Implementation summary and files changed:** [run.py](run.py) drives the map creator through visible Playwright UI controls. It paints mainland and islet, rock/steppe/swamp terrain, roads and waterway; stamps ridges, twin volcanoes, frontier ruins and watch posts; creates six named places with lore and linked symbols; exports PNG and editable JSON; reopens in a fresh browser and compares every layer. This proof directory adds [step screenshots](screenshots/), [PNG](turtonia-ashenmark.png), [editable project](turtonia-ashenmark.rdmap.json), [reopened project](turtonia-ashenmark-reopened.rdmap.json), [results](results.json), and [friction log](FRICTION.md). No application source or production service changed.

**Verification and proofs:** the final run passed twice without JavaScript page errors. It created 108 stamps, six named places with lore and six linked palette symbols. The 2400×1600 PNG had the same SHA-256 on both unchanged final runs: `17807efa196512477f61a9410cd571f89841d92acdd1c632716262a3257d6c07`. Fresh-browser import preserved every layer's embedded PNG and object list, including linked place symbols. The final export was visually inspected after reducing oversized road strokes from 16 to 9 px.

**Acceptance checklist:** blank-map entry passed; original volcanic composition authored; six linked places and 80+ stamps passed; PNG and editable downloads passed; fresh-browser roundtrip passed; zero page errors passed; inconveniences recorded.

**Risks and next step:** the light parchment palette limits the darkness of the theme, and raster roads are still cumbersome to revise. Monitor the exported image for visual clarity and retain this as a second user-journey fixture.

## Monitor — complete

**Status:** complete. **Observed results:** the map visibly reads as a volcanic basin with an enclosing north/east/south mountain ring, two central volcanoes, ash ground, western marsh, roads to a citadel, ruins, and a southern island. Its geography remains recognizably Turtonia and uses the Roll Drauf parchment style. All six places remain readable and inspectable with lore after reopening. Repeated export yielded the same PNG hash.

**Evidence and artifact retention:** this directory is retained as `user_journey_proof`; the original baseline in `../turtonia-protocol-2026-10-26/` remains unchanged. [FRICTION.md](FRICTION.md) lists every inconvenience encountered across the failed first attempt, visual revision, and final replay.

**Residual findings:** medium usability: raster roads and waterways cannot be reshaped, and decorative label hit boxes can intercept place creation. Low visual: mountain clusters still approach a few labels; the palette has no dark/lava materials. Low workflow: blank-map entry, map title, and dual exports require extra steps. The map was not deployed or imported into an authenticated campaign.

**Recommendation:** close this bounded creative replay. Future map-editor work can use the original Turtonia PNG for regression equality and this ash-basin PNG for a second visual scenario covering linked places and dense terrain.
