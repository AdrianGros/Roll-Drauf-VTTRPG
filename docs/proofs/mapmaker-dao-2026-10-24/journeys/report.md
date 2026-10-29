# Mapmaker first-time-user (DAU) journeys — report (2026-10-24)

**Phase:** DAD-M Monitor. **Status:** complete. Two task failures are the known medium V3; one partial is a discoverability trap.
**Not claimed:** a human user study, real devices, Safari/Firefox, or an authenticated campaign browser upload.

## Input and attribution

A Codex DAU agent drove the editor like a first-time user and saved screenshots `01`–`43`, three editable projects and one PNG. It stopped at its usage limit before writing a report. Its harness `/tmp/roll-drauf-mapmaker/dau-journeys/harness.py` only records first load; the later steps were driven interactively. I (Claude Opus 5.5, Monitor) re-judged every task outcome from the saved screenshots and parsed project files ([`../review-helpers/inspect_journey_files.py`](../review-helpers/inspect_journey_files.py)). I did not read app source to infer success.

The previous runs did not use the final source:
- **Desktop journeys** (`source-hashes-start.txt`) ran on the pre-branding CSS/HTML.
- **Mobile journeys** (`source-hashes-mobile-start.txt`) ran on the final `index.html` and an intermediate Deploy CSS (`0b8ece7a…`, help-grid rules only).
- **JS** was byte-identical to final in all of them.

To close that gap and the missing 320 px PNG artifact, I re-ran one bounded UI journey on the final source (desktop 1440 and touch 320) into [`final-source-rerun/`](final-source-rerun/). The numbered evidence was preserved.

## Task-level results ([`tasks.json`](tasks.json))

| Area | Tasks | Result |
|---|---|---|
| Desktop 1440 (preceding) | first load, paint forest, erase, find+place mountain, place+lore, layers hide/reorder/undo, help/file menu, save JSON + PNG (2400×1600), fresh reopen, reload keeps local work | **10 pass, 1 partial** (move mountain: T1) |
| Phone 390 (preceding) | tools, paint/erase, place+lore, help/file, save + fresh reopen | **4 pass, 1 fail** (see place on map: V3) |
| Phone 320 (preceding, final-rerun confirmation) | help/tools, paint/erase, place+lore, save + PNG | **4 pass, 1 fail** (V3) |
| Final source rerun | desktop 1440 and touch 320: title, paint (raster change verified in saved file), place+lore, Orte list, save JSON, PNG 2400×1600, fresh-context reopen with lore, zero console/page errors | **14/14 steps pass** ([`results.json`](final-source-rerun/results.json)) |

**Overall: 23 tasks — 20 pass, 1 partial, 2 fail.**

Saved-file facts:
- `Dornwachts-Waldmark.rdmap.json` (place *Dornwacht* with lore).
- `Mondfurt390.rdmap.json` (*Mondfurt390*).
- `Nebelpass320.rdmap.json` (*Nebelpass320*).
- Each is a v1 `rd-mapmaker` document with 5 layers, and each new place is pinned with its typed lore.

## Genuine failure

**V3 (medium, open).** On phones, choosing a place in *Orte* selects and centers it, but the marker sits behind the open inspector sheet (`28`, `41`). The independent visual after-probe reconfirms this on the final source at 390, 320 and 667 (`../visual/after-probes.json`: `coveredBy: tab-layers`). Collapsing the sheet reveals the marker (`29`), but a first-time user is not told this. The fix is JS/layout behavior and was deliberately excluded from the aesthetic pass.

## Discoverability traps (not failures of a requested function)

- **T1 (low): labels capture drags over symbols.** The new mountain was placed under "Silberlauf". Dragging it moved the label instead (`06`, `07`). The user retried with a second mountain (`13`). The saved project keeps the label displaced from (1125,802) to (1365,1021) and the first mountain unmoved. The behavior is internally consistent (labels are the top layer, and the action review verified it), but it caused an unnoticed edit.
- **T2 (low): project title ≠ map title.** Renaming the project to "Dornwachts Waldmark" changes the header and file name. The painted title label and the exported PNG still read DIE SILBERMARK (`16`, `Dornwachts-Waldmark.png`).
- **T3 (info): status after opening a file.** It reads "Ungespeicherte Änderungen" until autosave reports "Lokal gespeichert" (`17` vs `19`).
- **T4 (info): 320 px tool rail.** The last tool is partly clipped in the horizontally scrolling rail.
- **Help on short viewports (V5, low).** Help opens scrolled to its Close button (`34`/`35`).

## Partial coverage and limits

- Campaign use is documented in the export dialog only. The parent's `../handoff/results.json` proves the API path (upload 201, preview 200, create map 201, list 200, identical PNG bytes) with ephemeral SQLite and temp storage. That is **API integration, not an authenticated campaign UI journey**.
- Not covered here:
  - landscape 667 as a journey (the visual and action reviews cover it);
  - double-click layer rename (A1, action review);
  - symbol search (no such control);
  - physical stylus.
- Chrome mobile emulation shows the browser's default blue tap highlight on touched tools and tabs (`23`, `29`). This is cosmetic.

## Recommended next action

Run a bounded functional Apply/Deploy for V3: keep the selected place visible in the uncovered map area at 390, 320 and 667, covering both the closed→open and the already-open sheet cases. Re-run M04/S04 and the full browser suite. T1 and T2 are candidates for a later usability pass (for example, a hint when a drag selects a label instead of a symbol, and offering to update the map title label).
