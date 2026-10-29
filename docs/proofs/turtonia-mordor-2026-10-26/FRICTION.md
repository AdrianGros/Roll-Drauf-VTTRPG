# Turtonia ash-basin journey — observed inconveniences

This log includes the first failed authoring attempt, visual review, and the final two identical replays on 2026-10-26. `results.json` records the final replay's in-script observations. Entries here distinguish resolved authoring mistakes from remaining product friction.

1. **Local preview only — low.** The editor is still not deployed, so the journey uses a local server with the VTT Content Security Policy. No authenticated campaign import was tested.
2. **Small original reference — low.** The phone screenshot is partly covered and several original labels are hard to read. The established six Turtonia names from the baseline were reused; the new terrain is an original interpretation.
3. **Starter-first entry — low.** A blank map requires Datei → Neue Karte → Leere Karte after the starter map loads.
4. **Large landmass by hand — low.** The 400 px maximum brush needs multiple broad passes, narrower strokes, and eraser cuts for the mainland, peninsula and islet.
5. **Raster paths — medium.** Roads and the frontier waterway are painted pixels. A bend cannot be selected and moved after the stroke, so corrections require Undo or erasing part of the path.
6. **Stamp variation defaults on — low.** The first stamp would vary in size/rotation. The script disabled variation through the UI before placing the 108 stamps so the image would be reproducible.
7. **A decorative label intercepted place creation — medium, resolved in the journey.** In the first attempt, the wide “DIE ASCHENMARK” label covered Dorum's intended click point. The editor selected and renamed that label, and the lore field stayed disabled; Playwright timed out. The script now places semantic locations before decorative labels and asserts that the label count rises after each place click. This remains a discoverability risk when authoring by hand.
8. **Roads initially dominated the export — low, resolved in the journey.** The first complete export used 16 px strokes, which looked too heavy at map scale. The final journey sets 9 px through the exact number field and replays the whole map.
9. **Project title versus painted title — low.** “Turtonia – Die Aschenmark” in the header does not draw on the map. A separate “TURTONIA” realm label was needed.
10. **Separate outputs — low.** PNG carries the image; `.rdmap.json` carries editable layers, linked symbols, and lore. Both downloads must be kept.
11. **Palette limits dark fantasy mood — low.** The available rock and steppe materials are light parchment colors, and the volcano stamps are monochrome. The result conveys the ash basin through mountain enclosure and ruins rather than a literal black/red Mordor palette.
12. **Dense mountain-label proximity — low.** Some ridges approach labels, especially the region name and eastern fortress road. Reserving room around six place anchors kept the names readable, but the editor still has no collision guidance.
13. **Temporary browser environment and proof permissions — low.** The installed Playwright environment is root-only, and generated files initially inherited restrictive modes. Proof ownership and readable modes were corrected after the run.

The exact typed-size fields, automatic material routing, and linked place symbols worked in this journey. The PNG SHA-256 matched across two unchanged final replays, and reopening preserved all six linked symbols and lore.
