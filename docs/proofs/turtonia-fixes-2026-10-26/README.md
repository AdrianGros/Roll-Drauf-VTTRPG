# Turtonia follow-up replay

The original visible-UI Chromium/Playwright protocol was copied and rerun against the locally updated map editor. It passed with zero browser errors. The 2400×1600 PNG is byte-identical to the baseline (`d8bc00add4c337ecb8196be78f77a2a36c0ad838736acf4a88cb92d1b24a30cb`), and the editable project reopened with matching raster and item data, six named places, and 98 stamps.

`run.py` is the original protocol script. Several entries in its `results.json` friction array are emitted unconditionally as reminders of the original journey, including manual layer selection and unlinked symbols. They are **not** fresh measurements of the updated controls. The actual post-fix checks for dirty replacement, default recovery focus, material routing, typed size, linked place symbols, overlap selection, mobile placement, and Space-drag are in `tests/test_mapmaker_browser.py` and summarized in `docs/MAPMAKER_TURTONIA_FIXES_2026-10-26.md`.

The PNG remains visually the same because this replay deliberately follows the old authoring steps and uses separate town stamps. It checks for regressions; it does not demonstrate every new control.
