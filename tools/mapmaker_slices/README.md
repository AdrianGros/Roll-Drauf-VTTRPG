# Reviewed tilesheet slices

One JSON profile per asset pack. `tools/mapmaker_sheet_slicer.py build <pack>`
compiles it into normal PNG stamps and grid tiles in
`vtt/static/mapmaker/assets/<pack>/` and rebuilds palette, inventory and credits.
Detection only proposes boundaries; the reviewed profile decides. Every output
pixel is copied from the pinned sheet, and builds are byte-reproducible.

## Adding a pack

1. `detect <pack> --sheet <originalPath> --grid 32x32 --out <dir>` for grid
   sheets, or `--grid 0x0` for freestanding art without a grid (isometric
   sheets). Look at `<dir>/<pack>-detected.png`.
2. Write `<pack>.json` from the draft:
   - **grid-alpha-v1**: `regions` (rectangles with label, group, `kind`),
     `cells` (single-cell overrides), `composites` (`cells` as list or
     `{"rect": [col, row, w, h]}`, or `rows` recipes). `kind: tile` → tile
     palette (square cells only), `object` → stamp, `exclude` + `reason` →
     not offered. `hideParts` hides the cells of an assembled object.
   - **components-v1**: `params` (`gap`, `minArea`) and `objects` keyed by the
     detected box `x,y,w,h`; every detected object must be listed.
3. Set `review.status` to `reviewed`, record `method` and `deviations`
   (where the review overrode detection), then `build <pack>`.
4. `tests/test_mapmaker_sheet_slicer.py` recomposes every slice from the sheet.

Published slice IDs (`color:<pack>_<hash of sheet + layout>`) must keep
resolving: a later review that drops one keeps it hidden in the manifest.
Exact duplicate tile images are offered once.
