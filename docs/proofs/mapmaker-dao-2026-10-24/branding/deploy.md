# Mapmaker branding — DAD-M Deploy record (2026-10-24)

**Phase:** Deploy (closed) → handed to Monitor. **Implementer:** Claude Opus 5.5 (`claude-opus-5-5`), sole product coder.
**Contract:** `../PLAN.md` § "Apply — aesthetic contract". **Status:** implemented and verified within the CSS/HTML boundary; V3 functional defect is out of scope and still open.

## Implementation summary

The editor chrome now uses the canonical VTT book material: a plum/deep-plum binding (header, tool rail, zoom, overlays), paper/card/panel surfaces, ink and muted ink, gold ornament/focus, and rubric primary/danger actions. UI controls use the canonical system sans, Cinzel is used for brand and headings, and Literata for prose (hints, lore, dialog text). The header shows the existing gold `icon-book-sparkles.svg` ornament and the wordmark **Roll Drauf** with **Kartenwerkstatt** below it. Two confirmed CSS defects were fixed: V1 (header Help off-screen) and V2 (Help shortcut grid clipping/overlap).

## Files changed (exactly two product files)

| File | SHA-256 before | SHA-256 after | Diff |
|---|---|---|---|
| `vtt/static/mapmaker/index.html` | `f501fb0675c5ebd65da05a02748698e407af4a4e4146bee1317843b9a3249414` | `6c10750b1b4c3e4b61b4356198e7898ffc9253a63ab741b50351c276bf76327d` | +3 −3 (brand block only) |
| `vtt/static/mapmaker/mapmaker.css` | `b93d5e3958552ef77f4b232a81a4849a8179c3a897159db9e4cee77a5695de97` | `c79b0932227ef05783e13a5ebc9d544d6bf8f4d4f71c71a010954b217ea90343` | +129 −90 |

The full unified diff is in [`deploy.diff`](deploy.diff), and the pre-Deploy sources are in [`pre-deploy/`](pre-deploy/). One process slip: my planned `.orig` backups were never written because the compound shell command was blocked, and `vtt/static/mapmaker/` is untracked in git. I rebuilt both originals, and [`rebuild_index_orig.py`](rebuild_index_orig.py) proves them byte-identical to the pre-Deploy SHA-256 values above. The parent's independent copies (`/tmp/roll-drauf-mapmaker/acceptance/before-*.{css,html}`) also match those hashes.

A third CSS state existed briefly, `mapmaker.css` `0b8ece7a…`: my first write, before the help-grid rule was made global and narrowed to 46%. The mobile DAU journeys happened to run against it (see `../journeys/report.md`). It differs from the final only in help-grid rules.

**Unchanged, verified by hash:** all 10 JS modules, all mapmaker assets, `ATTRIBUTIONS.md`, `vtt/static/css/theme.css` and `vtt/static/icons/icon-book-sparkles.svg`. [`hashes-before.json`](hashes-before.json) vs [`hashes-after.json`](hashes-after.json): 58 files, changed = exactly `index.html` and `mapmaker.css`. Parent baseline confirms all 1459 original repo paths unchanged except exactly those two files. No tests, templates, schema, dependencies or shared styles were touched.

## Bounded design decisions (per contract)

1. **Tokens.** `theme.css` is not imported (it styles global `body`/headings). Existing mapmaker aliases now resolve as `var(--vtt-<canonical>, <exact current fallback>)`, for example `--parchment: var(--vtt-paper, #f8f3e9)` and `--chrome: var(--plum-deep)` → `var(--vtt-plum-deep, #2f1638)`. A few local aliases were added in the same pattern so canonical roles exist locally: `--plum`, `--plum-deep`, `--gold-deep`, `--rubric`, `--rubric-deep`, `--success`, `--parchment-panel`, `--parchment-soft`, `--field-border`, `--font-ui`, `--font-heading`, `--font-body`. Tints use `color-mix()` on those aliases (chrome line/hover/muted, gold-on-chrome, selected tint, shadow), so there is no second palette. `--sea` and `--gold-bright` were retired.
2. **Remapped chrome constants.** Teal header gradient/hover (`#24332f`, `#314245`), teal zoom/overlay/backdrop rgba, brown primary (`#523b25`), cream `#fffaf0`/`#fbf4e1`/`#fff` surfaces, saved-green `#9fd3a4`, failed `#ffb4a0`/`#8a4a3c`, swatch-frame brown and the teal link `--sea`.
3. **Kept on purpose.** `.mm-stage { background: #1c2628 }` matches the off-map backdrop that `app.js:251` paints into the canvas, so no seam appears. Map art, material swatches, stamp canvases, the brush preview (`ui.js`), BadScript place names and all export colors are JS/document-owned and unchanged.
4. **Brand markup.** `<img class="mm-brand-mark" src="../icons/icon-book-sparkles.svg" alt="">` (existing relative asset; satisfies the static relative-resource test and CSP `img-src 'self'`). The old `aria-hidden` was removed so assistive tech reads "Roll Drauf Kartenwerkstatt". At ≤760 px the wordmark is visually hidden (sr-only pattern) and only the 24 px ornament shows, so the brand never consumes canvas.
5. **V1 header.** `.mm-top-actions` changed from `min-width: 0` (it shrank below its content, pushing Help out) to `flex: none`. The title input absorbs the squeeze. At ≤760 px header/action gaps are 4/2 px; at ≤360 px the Datei button padding is 6 px. Every control stays visible; nothing is hidden.
6. **V2 help grid.** Applied at every width, because the visual review also showed the desktop/tablet overlap. Each column has `min-width: 0`. The keys column uses `fit-content(46%)` and wraps; descriptions use `minmax(0, 1fr)`. The grid minimum is `min(190px, 100%)`. At ≤760 px the help dialog padding is 16 px.
7. **Focus/selection.** On paper the focus ring is `--gold-deep`; on the plum binding it is the lighter `--gold-on-chrome`. Selected tool, swatch, stamp, layer and place use a plum border, gold ring/bar and a soft gold tint. `::selection` uses a gold tint.

## Verification run

| Check | Result |
|---|---|
| `tests/test_mapmaker_static.py` (own run, isolated venv) | **7 passed** |
| [`verify_branding.py`](verify_branding.py): fresh context per viewport, awaits `window.rdMapmaker.ready`, at 1440×1000, 1024×768, 390×844, 320×568, 667×375 | **ALL CHECKS PASS**: all 6 header controls in viewport; no document or header horizontal overflow; help dt/dd/kbd inside their grid cell and the dialog, with no mid-word breaks; console/page errors 0 |
| Same harness on the pre-Deploy source ([`deploy-before-metrics.json`](deploy-before-metrics.json)) | Reproduced V1 (390: Help out; 320: status + Help out, document overflow) and V2 (320 and 667 descriptions outside the dialog). The desktop overlap was found by viewing screenshots and the stricter cell probe was then added |
| Parent full final-source regression (`/tmp/roll-drauf-mapmaker/acceptance/regression.txt`) | **34 passed in 255.33 s**. Credit: parent orchestrator, run after the source settled |

Measured contrast, final source ([`deploy-after-metrics.json`](deploy-after-metrics.json); sRGB relative luminance; style observation, not a full WCAG audit):

| Pair | Ratio |
|---|---|
| Brand word on plum-deep | 14.25 |
| Brand subtitle (gold-on-chrome) | 6.75 |
| Tool label on rail | 9.1 |
| Pressed tool | 11.25 |
| Datei button | 10.92 |
| Status text | 9.1 |
| Tab on tab bar | 5.87 |
| Selected tab | 11.25 |
| Hint/h3 on panel | 6.41 |
| Primary (rubric) button | 8.16 |
| Focus ring on panel | 4.79 (was 1.54) |
| Focus ring on selected tint | 4.15 |
| Focus ring on plum-deep / plum | 6.75 / 5.18 |

Screenshots (in `shots/`, prefixed `deploy-` so they never collide with the immutable `../visual/` baselines):
- `deploy-after-<viewport>-{initial,help,help-end,file,focus}.png` for all 5 viewports.
- `deploy-before-{smallphone,phone}-initial.png` and `deploy-before-{smallphone,desktop,landscape}-help.png` for comparison.

## Acceptance checklist (contract)

- [x] Canonical plum/paper/ink/gold/rubric chrome; canonical fonts by role; exact fallbacks documented.
- [x] Existing gold ornament asset; Roll Drauf wordmark with Kartenwerkstatt subordinate where room; no banner; canvas area unchanged.
- [x] V1: no horizontally unreachable header control at 320/390/667; no page horizontal scroll.
- [x] V2: help readable, wrapped, no overlap/clipping at all 5 viewports. Vertical scroll in the dialog is accepted.
- [x] Tool, swatch, stamp, layer and place selection stays obvious; focus visible on paper and on plum.
- [x] No JS, asset, test, template, schema, dependency or shared-CSS change (hash-verified).
- [x] Static tests pass (own run); full regression passes (parent run).
- [ ] V3 (selected mobile place behind sheet) is **not** addressed: JS/functional, out of this boundary, still open.

## Gaps and residual risks

- **Off-map backdrop.** It stays dark slate `#1c2628` because JS paints it (`app.js:251`). It reads as a neutral backdrop next to the plum binding. Recoloring needs a one-constant JS change in a separate bounded pass.
- **`color-mix()` support.** Requires Chromium 111+, Safari 16.2+ and Firefox 113+. Older engines drop those declarations. Only Chromium was verified.
- **Field borders.** These use the canonical `--vtt-field-border-strong` at about 2.1:1 on panel, inherited from the VTT token rather than introduced here. Focus rings carry the interaction contrast.
- **Standalone fallbacks.** These must be re-checked when the canonical tokens in `theme.css` change.
- **Unchanged by this pass:** V5 (Help opens scrolled to its Close button on short viewports; JS focus behavior), the partially clipped last tool in the 320 px rail (pre-existing horizontal scroller), and Chrome's default blue tap highlight on touched controls.
