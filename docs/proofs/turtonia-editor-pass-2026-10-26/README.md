# Turtonia editor pass — visual and browser proof

- [Editable river and path inspector](screenshots/mapmaker-vector-path.png): one selected vector waterway with point handles, type and width controls.
- [Dark sea and automatic title](screenshots/mapmaker-map-style.png): title from the editor header appears once; an existing top realm heading is temporarily suppressed while automatic title is enabled.

`tests/test_mapmaker_browser.py` contains the repeatable overlap, path, terrain, title, ZIP and file-validation cases. The complete mapmaker browser/static suite passed 42 tests in Chromium; focused checks after the title adjustment also passed.

The historical [Turtonia](../turtonia-protocol-2026-10-26/) and [Mordor](../turtonia-mordor-2026-10-26/) `run.py` scripts were replayed with `TURTONIA_OUT` pointing to temporary directories, preserving their original proof files. Both finished with no browser errors and matching editable reopen data. Mordor's PNG is byte-identical to its original proof. The classic script's PNG changed because it selects brush size through approximate slider clicks and the slider range grew to 800 px; its friction messages describe its old workflow and are not updated feature assessments.
