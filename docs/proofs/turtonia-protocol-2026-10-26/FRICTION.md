# Turtonia protocol — friction log

Observed while authoring from a blank map in Chromium with Playwright on 2026-10-26. Every recorded inconvenience is listed separately, including repeated slider misses. The machine-readable observations are in [results.json](results.json).

## 1. Preview-only access — low

**Observed:** The currently deployed VTT container does not serve this uncommitted map editor  
**Workaround:** Use the local map editor preview with the VTT CSP; keep production untouched

## 2. Reference legibility — low

**Observed:** The reference is a phone screenshot with toolbar overlays and partly illegible place names  
**Workaround:** Match the visible geography and readable names; record approximations

## 3. Root-only test environment — low

**Observed:** The prepared Playwright virtualenv is inside a root-only temporary directory  
**Workaround:** Run the browser journey as root and restore admin ownership on proof artifacts afterward

## 4. Proof-file permissions — low

**Observed:** Files created in the root-run proof directory inherit root ownership and a restrictive umask  
**Workaround:** Restore admin ownership and readable modes after the run

## 5. Stamp variation default — low

**Observed:** The stamp tool starts with slight random size/rotation variation enabled  
**Workaround:** Turn it off in the visible controls for a repeatable reference journey

## 6. Starter-map entry — low

**Observed:** The editor first opens Die Silbermark rather than a blank canvas  
**Workaround:** Use Datei → Neue Karte → Leere Karte before authoring

## 7. Imprecise slider — low

**Observed:** #brushSize: requested 180, first click got 170.0  
**Workaround:** Adjust with the keyboard after the pointer click

## 8. Large landmass by hand — low

**Observed:** The visible brush tops out at 400 map pixels, so a continent outline needs many overlapping strokes and cleanup  
**Workaround:** Use broad strokes, then smaller coastal strokes and eraser cuts

## 9. Manual material targets — low

**Observed:** Forest and rock material selection does not reliably choose a terrain layer  
**Workaround:** Use the Layers tab to set Gelände before each material

## 10. Raster river/road editing — low

**Observed:** Fluss and Weg become raster paint; individual bends cannot be selected as path objects  
**Workaround:** Keep river/road work on its dedicated layer and use Undo or eraser for corrections

## 11. Imprecise slider — low

**Observed:** #stampSize: requested 68, first click got 88.0  
**Workaround:** Adjust with the keyboard after the pointer click

## 12. Imprecise slider — low

**Observed:** #stampSize: requested 102, first click got 88.0  
**Workaround:** Adjust with the keyboard after the pointer click

## 13. Imprecise slider — low

**Observed:** #stampSize: requested 75, first click got 88.0  
**Workaround:** Adjust with the keyboard after the pointer click

## 14. Imprecise slider — low

**Observed:** #stampSize: requested 74, first click got 88.0  
**Workaround:** Adjust with the keyboard after the pointer click

## 15. Symbol-by-symbol terrain — low

**Observed:** Mountain ranges and forests require many individual stamp placements to resemble the dense reference  
**Workaround:** Use repeatable seeded placement coordinates and the curated Kenney palette

## 16. Unlinked town icons and places — low

**Observed:** Settlement symbols and named places are separate objects positioned by eye  
**Workaround:** Use fixed coordinates for both and inspect the exported image

## 17. Separate file and painted titles — low

**Observed:** The project title in the header does not draw a title onto the map  
**Workaround:** Place TURTONIA as a separate text label

## 18. Two export formats — low

**Observed:** The PNG is a flattened image; editable layers, place data, and lore stay in the separate .rdmap.json download  
**Workaround:** Save both files and explicitly test reopening the project

## 19. Asynchronous import state — low

**Observed:** An initial check of hidden loading overlay ran before the file import had begun, causing a false failure  
**Workaround:** Wait for the imported title and lore in a fresh context

## 20. Crowded symbol/label placement — medium

**Observed:** Mountain stamps and several names overlap in the exported image; the editor does not avoid collisions  
**Workaround:** Record the screenshot for manual cartographic refinement

