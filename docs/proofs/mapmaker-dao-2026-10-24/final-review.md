# Mapmaker DAO run — final review (2026-10-24)

**Phase:** DAD-M Monitor (standard profile). **Reviewer:** Claude Opus 5.5 (`claude-opus-5-5`), completing evidence reviews left unfinished by agents that hit usage limits. Product source was read-only during this Monitor pass.

**Verdict:**
- The **aesthetic branding milestone is accepted**: V1, V2, V4 and V6 are resolved on the final source, with only the two contracted files changed.
- The **prototype as a whole is not unconditionally accepted**: one medium functional finding (V3) remains open and needs its own bounded Apply/Deploy.
- **Security is not assessed as passed**: the separate security review is static-only and its report is not yet in this folder.

## Final source

| Item | Value |
|---|---|
| `vtt/static/mapmaker/index.html` | `6c10750b1b4c3e4b61b4356198e7898ffc9253a63ab741b50351c276bf76327d` |
| `vtt/static/mapmaker/mapmaker.css` | `c79b0932227ef05783e13a5ebc9d544d6bf8f4d4f71c71a010954b217ea90343` |
| JS modules (10) | Unchanged throughout the DAO run (`app.js` `80e451e0…`, `ui.js` `e76ec140…`, …) |

Matches between this final source and the saved snapshots ([`review-helpers/monitor_check.py`](review-helpers/monitor_check.py)):
- `branding/hashes-after.json` (58 files): equal.
- `visual/after-source-hashes.json` (12 files): equal.
- Pre-Deploy snapshots and `actions/matrix.json` differ in exactly `index.html` and `mapmaker.css`.
- The parent baseline confirms all 1459 original paths unchanged except those two.

## Results by stream

| Stream | Evidence | Result |
|---|---|---|
| Aesthetic Deploy | [`branding/deploy.md`](branding/deploy.md), `deploy.diff`, `verify_branding.py` | Canonical plum/paper/ink/gold/rubric chrome and fonts by role; `icon-book-sparkles` ornament with "Roll Drauf / Kartenwerkstatt". Five viewports: header controls in viewport, no horizontal overflow, help readable, 0 errors. Static tests: 7 passed |
| Regression (parent) | `/tmp/roll-drauf-mapmaker/acceptance/regression.txt` | **34 passed, 255.33 s** on final source (credit: parent orchestrator) |
| Visual (Codex captures, Claude completion) | [`visual/REVIEW.md`](visual/REVIEW.md) (immutable), [`visual/AFTER-REVIEW.md`](visual/AFTER-REVIEW.md) | V1, V2, V4, V6 resolved; V3 open (medium); V5 open (low) |
| Actions (Codex) | [`actions/report.md`](actions/report.md), `matrix.json`, [`actions/ADDENDUM-branding.md`](actions/ADDENDUM-branding.md) | **226 unique: 221 pass, 2 fail (A1 low, V3 medium), 2 not-tested (no symbol search control; other browsers), 1 blocked (physical stylus)**. Recounted from the matrix. The "hashes unchanged: False" is explained by the two aesthetic files only |
| DAU journeys (Codex screenshots, Claude report + final rerun) | [`journeys/report.md`](journeys/report.md), [`journeys/tasks.json`](journeys/tasks.json), `journeys/final-source-rerun/` | **23 tasks: 20 pass, 1 partial (T1 trap), 2 fail (V3 at 390/320)**. Final-source rerun at 1440 and touch 320: 14/14 steps |
| Completeness (Codex) | [`coverage/report.md`](coverage/report.md) | Essential first-value loop present (starter/empty map → paint → symbols → places with lore → layers/undo → editable file → PNG). No medium/high completeness gap. Low: no VTT navigation entry |
| Campaign handoff (parent) | [`handoff/results.json`](handoff/results.json) | Existing PNG → upload 201 → preview 200 → create map 201 → list 200, matching PNG bytes; ephemeral SQLite and temp storage. **API integration only, not an authenticated campaign UI E2E** |
| Security (separate Claude session) | `security/` currently holds only source-hash helpers | **Static-only review, report pending.** Its dynamic harness was rejected by a safety classifier and was not retried. No security pass is claimed here |

## Severity ledger

| ID | Severity | Status | Summary |
|---|---|---|---|
| V3 | **medium** | **open** | Choosing a place in *Orte* on phones (390/320/667) centers the marker behind the open sheet. Reconfirmed on final source. JS/layout fix, outside the aesthetic boundary |
| V1 | medium | resolved | Header Help/status off-screen at 320/390 |
| V2 | medium | resolved | Help shortcut grid overlap (desktop/tablet) and clipping (320/667) |
| V4 | medium | resolved | Paper-surface focus ring 1.32–1.61:1 → 4.79:1 (4.15:1 on selected tint) |
| V6 | medium | resolved | VTT brand harmonization |
| A1 | low | open | Double-click layer rename has no effect (rename button works) |
| V5 | low | open | Help opens scrolled to Close on short viewports |
| T1 | low | open | Dragging a symbol under a label moves the label; the unintended move was saved |
| T2 | low | open | Project title rename does not change the painted map title / PNG |
| C1 | low | open | No VTT navigation entry/return to the editor |
| I1–I5 | info | noted | (1) JS-painted slate off-map backdrop; (2) default blue tap highlight; (3) 320 px rail clips its last tool; (4) "Ungespeicherte Änderungen" right after opening a file; (5) `color-mix()` needs modern engines (Chromium-only verification) |

No high or critical finding was established by these functional, visual, journey or completeness reviews. Security is not part of that statement.

## Honest gaps

- **Browsers and devices:** only Chromium. Physical touch/stylus, Safari/Firefox and assistive-technology use were not tested.
- **No human user study:** the DAU journeys are agent-driven UI runs.
- **Campaign upload:** the authenticated browser campaign upload was not exercised (API proof only).
- **Journey revisions:** the preceding desktop journeys ran on pre-branding CSS and the mobile journeys on an intermediate CSS (JS identical). The final-source rerun covers the core loop at 1440 and 320 only, not landscape.
- **Security:** remains a separate, static-only stream with its report outstanding.

## Recommended next bounded action

Open a functional DAD-M Apply → Deploy for **V3**: keep the selected place inside the uncovered map area when the sheet is open at 390/320/667, without changing desktop behavior, zoom or selection. Re-run M04/S04 and `visual/probe.py` (after phase), then the full browser suite. Bundle A1 and V5 only if they stay small and separately verified. Close the DAO milestone after V3 is resolved or explicitly accepted, and after the security report is filed and triaged.
