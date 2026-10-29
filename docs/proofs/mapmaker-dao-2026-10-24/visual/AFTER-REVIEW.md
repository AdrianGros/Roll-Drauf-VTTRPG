# Visual review — after branding (completion, 2026-10-24)

**Phase:** DAD-M Monitor. **Author:** Claude Opus 5.5, completing the review the Codex visual agent left as "after review pending". [`REVIEW.md`](REVIEW.md) and every `before-*` artifact stay immutable.

## Evidence used

The Codex visual agent captured these with its own harnesses (`capture.py`, `probe.py`) on the final source. [`after-source-hashes.json`](after-source-hashes.json) equals the current `index.html` `6c10750b…`, `mapmaker.css` `c79b0932…` and all JS, so no re-capture was needed.
- `after-*.png`: 49 screenshots, including `after-journey.png`.
- `after-metrics.json`: 40 states, 0 runtime errors.
- `after-probes.json`: 5 viewports.

I viewed these final screenshots:
- `after-smallphone-help-top.png` and `after-smallphone-help.png`;
- `after-landscape-help-top.png` and `after-tablet-help.png`;
- `after-desktop-layers.png` and `after-smallphone-layers.png`;
- `after-smallphone-file.png` and `after-phone-place-probe.png`.

I also viewed the Deploy captures in `../branding/shots/`, including all 5 `initial`, `help`, `help-end`, `file` and `focus` views. A paper-surface keyboard-focus screenshot was missing from the after set, so I added one: `../journeys/final-source-rerun/desktop-paper-focus.png`.

## Finding status on final source

| ID | Before | After (evidence) | Status |
|---|---|---|---|
| V1 header reachability | Help off-screen at 320, partly at 390; root scrolled | Help at x280 (320), x350 (390), x627 (667), x978/x1394. All 6 header controls inside the viewport and no document overflow (`after-probes.json`, `../branding/deploy-after-metrics.json`) | **Resolved** |
| V2 help clipping/overlap | Desktop/tablet column overlap; 320/667 overflow | Help scrollWidth = clientWidth and grid scrollWidth = width at all 5 viewports. Screenshots show wrapped keys, no overlap, no cut descriptions. The Deploy probe checks dt/dd/kbd inside their own cell with no mid-word breaks | **Resolved** |
| V3 selected mobile place behind sheet | Marker covered at 390/320/667 | Unchanged: `coveredBy: tab-layers` at 390 (y416 vs sheet 410.6), 320 (278 vs 256.1) and 667 (181.5 vs 148). `after-phone-place-probe.png` shows Hohenfurt behind the inspector | **Open (medium)**. JS fix excluded from the aesthetic pass |
| V4 focus contrast | `#f2c66d` ring on pale paper, 1.32–1.61:1 | Paper focus `rgb(138,107,32)`: 4.79:1 on panel, 4.15:1 on selected tint. Plum surfaces 6.75/5.18:1. Visible in `desktop-paper-focus.png` and `deploy-after-*-focus.png` | **Resolved** |
| V5 help initial scroll | scrollTop 300 (320), 198 (667) | 269 (320), 183 (667). JS focus behavior unchanged | **Open (low)** |
| V6 brand | Teal chrome, generic star, no Roll Drauf | Plum binding, paper panels, rubric primary, gold ornament `icon-book-sparkles.svg`, "Roll Drauf / Kartenwerkstatt" (ornament only at ≤760 px), UI sans / Cinzel / Literata by role. Consistent across the viewed states | **Resolved** |

## Remaining visual observations

- **Off-map stage backdrop.** It stays dark slate because `app.js` paints it.
- **Landscape 667×375.** The Help dialog fills the height and scrolls vertically. This was accepted.
- **Default blue tap highlight.** Chrome's default highlight shows on touched controls.
- **320 px tool rail.** The last tool is partly clipped (pre-existing scroller).

None of these is medium or higher.

**Verdict:** aesthetic visual acceptance is met for V1, V2, V4 and V6. Visual/usability closure for the prototype still depends on V3.
