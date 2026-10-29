# Kartenwerkstatt (world/regional map-maker prototype) — DAD-M record

**Milestone:** MAPMAKER-P1 · **Date:** 2026-10-24 · **Profile:** strict governance rules, lightweight artifacts
**Roles:** Claude Opus 5.5 = planning + coding; Codex = independent review + curated free assets.
**Runtime loaded:** `dadm/framework/runtime/AI_BIOS.md`, `file-registry.yaml`, cards `core-rules`, `phase-map`,
`deliverables-min`, `governance-min`, `human-decision-card`, `discover-card`, `apply-card`, `deploy-card`,
`monitor-card`; `governance/governance-matrix.md`, `governance/rework-and-escalation.md`;
skills `dadm-discover`, `dadm-apply`, `dadm-deploy`.

---

## 1. DISCOVER — status: **closed (immutable)**

**input_summary:** Plan a first usable Inkarnate-inspired world/regional map-maker with GIMP-like brush
controls for roll-drauf-vtt. No new runtime dependencies, schema migrations, production deployment or live
database writes. Preserve the large dirty worktree.

**artifacts:** this section (retention: immutable).

### Current state (evidence)
- Serving: `vtt/__init__.py:175` `Flask(__name__)` → default static folder `vtt/static` at `/static/<path>`.
  Flask does **not** serve `index.html` for a directory, so the canonical URL is
  `/static/mapmaker/index.html`. The catch-all `/<path:path>` (`vtt/__init__.py:326-354`) serves any
  `vtt/templates/<name>.html` raw at `/<name>`, so a new template yields `/mapmaker` without Python edits.
- CSP (`vtt/__init__.py:216`) applies whenever `DEBUG` is falsy, including `TestingConfig`
  (`vtt/config.py:238`): `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self'
  'unsafe-inline'; img-src 'self' data: https:; font-src 'self'`. `blob:` images are blocked.
- Maps: `CampaignMap` (`vtt/models/campaign_map.py`) is a tactical record with `background_url`; no world-map
  model. Atlas doc §10.5 advises not to overload it; F-02 (`docs/DADM_DISCOVER_MMO_META_LAYER_CONCEPT_2026-07-21.md:38-42`)
  wants the editor as its own workstream.
- Existing PNG→map path: `vtt/templates/campaigns.html:2849` `uploadStandaloneMap` ("Karte hinzufügen",
  `:3158`) → `POST /api/assets/campaigns/<id>/upload` (`asset_type=map`, editor-only, 50 MB, Pillow-verified,
  `vtt/endpoints/assets.py:291-434`, `vtt/upload_security.py:48,95`) → `POST /api/campaigns/<id>/maps`
  (DM-only, `vtt/campaigns/routes.py:1027`).
- Fonts: Cinzel, Literata, BadScript vendored in `vtt/static/fonts/` (OFL); `css/fonts.css` uses absolute
  paths. `assets/sternenstaub/backgrounds/background-old-paper.jpg` is CC BY-SA 4.0.
- Curated assets (delivered by Codex during Apply review): `vtt/static/mapmaker/assets/kenney-cartography/`
  — 38 stamps (128 px Retina PNG), 2 textures, `manifest.json` (ids like `kenney:mountains`, German labels,
  groups, `w/h`, `defaultSize`), `License.txt` (CC0), `README.md`. Owned by Codex; read-only for Claude.
- Tests: Playwright browser tests follow `tests/test_srd_sheet.py:80` (`create_app("testing")` +
  `make_server` thread, widths 1440/390). The repo `venv/` is broken (points at `/usr/sbin/python3`); Codex
  prepared `/tmp/roll-drauf-mapmaker/test-venv` (pytest + Playwright; Flask not yet installed there).

### Risks and assumptions
| ID | Severity | Finding | Disposition |
|---|---|---|---|
| D1 | medium | `blob:` image URLs break under CSP | resolved in Apply (no blob images) |
| D2 | medium | Dirty files incl. `vtt/__init__.py`, `campaigns.html`, dashboard → no nav edit | resolved (additive only) |
| D3 | medium (security) | Imported JSON text → XSS if rendered as HTML | resolved (validation + `textContent`) |
| D4 | medium | Raster base64 can exceed localStorage quota | resolved (IndexedDB) |
| D5 | low (license) | CC BY-SA paper texture in exports | allowed with note: use CC0 Kenney parchment |
| D6 | low | Asset pack delivered in parallel | closed: delivered |
| D7 | low | ~15 MB per 2400×1600 RGBA layer | allowed with note (bounded history/limits) |
| D8 | info | Public static page, no server data | allowed |

**next_step:** Apply.

---

## 2. APPLY — status: **closed (immutable)**, accepted by Codex review with amendments 1–6

**input_summary:** Design inside the Discover boundary, plus review amendments: (1) canonical Flask URL
`/static/mapmaker/index.html`; (2) curated Kenney stamps are the primary palette and are used in the starter
map, CC0 parchment may be used; (3) strict import validation before any replacement; (4) undo bounded to
~64 MB / 60 steps, no per-move full snapshots, coherent pointer cancel, Space ignored in text fields;
(5) use the prepared test venv; (6) attractive, genuinely editable first render, no placeholder controls.

**artifacts:** this section (immutable); the file set in §2.4 (retention: working until Monitor closes).

### 2.1 Decisions
1. Self-contained static app in `vtt/static/mapmaker/` with ES modules and only relative URLs.
   Flask: `/static/mapmaker/index.html`. Preview: `python3 -m http.server -d vtt/static 8765` → `/mapmaker/`.
2. Entry stub `vtt/templates/mapmaker.html` → `/mapmaker` redirects to `/static/mapmaker/index.html`.
   No existing file is edited; no nav link (D2).
3. No campaign API publishing in v1. Export dialog documents: PNG exportieren → Kampagnen → Kampagne öffnen →
   „Karte hinzufügen“ (Spielleitung).
4. Canvas 2D only, no `ctx.filter`; coast glow via `shadowBlur`. No dependencies.
5. Autosave in IndexedDB (raster as PNG bytes); images decoded via `createImageBitmap(Blob)` — never via
   `blob:` URLs.
6. Stamps: curated Kenney pack is primary. Built-ins are only a compass and a pin, plus mountain/tree/house/
   castle fallbacks shown solely when the pack fails to load. Parchment: Kenney `parchment.png` (CC0) as a
   subtle multiply overlay. Fonts via own `@font-face` with `../fonts/` paths.

### 2.2 Prototype scope
- Starter map „Die Silbermark“ 2400×1600 from a seeded generator (coast, island, lake, terrain, river, road),
  Kenney stamps (mountains, forests, settlements, ship, compass), 7 places with lore, realm/region/water labels.
- Tools: Bewegen, Pinsel, Radierer, Stempel, Ort, Auswählen.
- Brush: size 2–400, opacity 0–100 %, softness 0–100 %, spacing 12 %; pen pressure (size + alpha) when a
  pen is detected; stroke buffer composited once per stroke (no overlap build-up); eraser `destination-out`.
  Materials: Land, Wiese, Wald, Steppe, Wüste, Schnee, Sumpf, Fels, Flachwasser, Fluss, Weg. (*Tiefsee* was
  dropped: carving sea is done with the eraser on the Land layer, which keeps the coast effect correct.)
- Layers: name, visibility, opacity, reorder, add, delete, rename, coast effect; limits 32 layers / 8 raster.
- History: command stack, **≤ 60 steps and ≤ 64 MB**; raster steps store before/after `ImageData` of the
  stroke's dirty rectangle only; a single step larger than the budget clears history with a notice.
- Pan/zoom 10–400 %, wheel at cursor, Space/middle/pan tool, two-finger pinch; Fit.
- File: `.rdmap.json` save/load; PNG export 1×/2×; IndexedDB autosave with restore dialog and visible states.
- Responsive: desktop tool rail + tabbed panel; ≤ 760 px bottom tool bar + bottom sheet.

### 2.3 Data contract `rd-mapmaker` v1 (final)
```json
{"format":"rd-mapmaker","version":1,
 "meta":{"title":"Die Silbermark","seed":1337,"created":"ISO","modified":"ISO"},
 "size":{"w":2400,"h":1600},"sea":{"top":"#2f5d6e","bottom":"#7fa9a8"},
 "layers":[
  {"id":"land","name":"Land","kind":"raster","visible":true,"opacity":1,"effects":{"coast":true},
   "png":"data:image/png;base64,..."},
  {"id":"sym","name":"Symbole","kind":"stamps","visible":true,"opacity":1,
   "items":[{"id":"s1","asset":"kenney:mountains","x":800,"y":540,"size":88,"rot":0,"flip":false}]},
  {"id":"txt","name":"Beschriftung","kind":"labels","visible":true,"opacity":1,
   "items":[{"id":"p1","x":1210,"y":700,"text":"Hohenfurt","style":"city","size":40,"rot":0,
             "color":"#3b2a1a","pin":false,"place":{"kind":"city","lore":"..."}}]}]}
```
Stamp `size` (px, longest side) replaces the earlier `scale` sketch (bounded implementation detail, fixed here
before Deploy).

**Import validation — all checks pass before anything replaces the current map:**
file ≤ 50 MB; JSON object; exact `format`/`version`; integer size 256–4096; title ≤ 80 chars; colors
`#rrggbb`; 1–32 layers, ≤ 8 raster; layer/item ids `^[A-Za-z0-9_-]{1,40}$` unique across the document; names
≤ 40; kinds/styles/place kinds from fixed sets; finite bounded numbers (x/y within −size…2×size, stamp size
4–512, label size 8–200, rotation −360…360, opacity 0–1); ≤ 2000 items; strings stripped of control chars and
length-limited (label 80, lore 500); `png` must be `data:image/png;base64,` (no external URLs), decoded bytes
must carry the PNG signature and an IHDR whose width/height equal the document size **before** browser decode;
cumulative raster area ≤ 32 000 000 px; stamp asset ids must exist in the loaded palette. Failures show a German
error dialog; the current document and history stay untouched. All user text reaches the DOM only via
`textContent`/`value`.

### 2.4 File ownership (all new)
| Path | Owner |
|---|---|
| `vtt/static/mapmaker/index.html`, `mapmaker.css`, `ATTRIBUTIONS.md` | Claude |
| `vtt/static/mapmaker/js/*.js` | Claude |
| `vtt/static/mapmaker/assets/kenney-cartography/**` | Codex (read-only for Claude) |
| `vtt/templates/mapmaker.html` | Claude |
| `tests/test_mapmaker_static.py`, `tests/test_mapmaker_browser.py` | Claude |
| `docs/MAPMAKER_PROTOTYPE_DADM_2026-10-24.md` | Claude |

### 2.5 Acceptance criteria
See §3.4 (checked during Deploy).

### 2.6 Risks and tradeoffs
| ID | Severity | Item |
|---|---|---|
| A1 | low | Raster layers are fixed to the document size; no canvas resize in v1 |
| A2 | low | Pen pressure only via Pointer Events `pointerType==='pen'` |
| A3 | low | Labels are canvas-rendered; screen readers use the Orte list instead |
| A4 | info | No server persistence; JSON file + local autosave only |

No human-decision trigger fires (no critical/high security finding, no dependency or cross-milestone change).

**next_step:** Deploy, in the order: document/schema + history → render + starter → brush + tools → stamps →
UI + responsive → storage/export/autosave → tests → this record.

---

## 3. DEPLOY — status: **complete, awaiting Codex review (Monitor)**

**input_summary:** Implement §2 exactly; additive files only; no dependency, schema, deployment or live-data
change. Test runtime: `/tmp/roll-drauf-mapmaker/test-venv` (Python 3.12, pytest, Playwright; Flask stack was
importable at run time) with the headless-shell browser
`/home/admin/.cache/ms-playwright/chromium_headless_shell-1234/…` and the Codex-staged libraries in
`/tmp/roll-drauf-mapmaker/browser-libs` (`LD_LIBRARY_PATH`). The repo `venv/` was **not** used (broken).

### 3.1 Implementation summary
- **Editor shell** `index.html` + `mapmaker.css`: map-first canvas, left tool rail (6 tools), tabbed panel
  (Werkzeug / Ebenen / Orte), file menu, undo/redo, zoom group, status pill, five native `<dialog>`s
  (restore, new map, PNG export with campaign workflow hint, error, help). ≤ 760 px: bottom tool bar + bottom
  sheet; the map is top-aligned so the open sheet does not cover it.
- **Document/validation** `js/document.js`: limits, id helpers, PNG signature + IHDR check, full import
  validation (§2.3) producing a fresh normalized object, `materialize()` decodes via
  `createImageBitmap(Blob)`, `serialize()` (data URLs for files, raw bytes for autosave, per-layer re-encode
  only when changed).
- **History** `js/history.js`: `HISTORY_MAX_STEPS = 60`, `HISTORY_MAX_BYTES = 64 MB` (both stacks counted);
  oversize single step clears history with a visible notice.
- **Brush** `js/brush.js`: 11 procedurally textured materials, cached radial tips (size × softness),
  `StrokeEngine` with one base copy per stroke (at pointerdown), stroke mask at full strength, per-frame
  re-composite of the dirty rectangle only, opacity applied once, eraser `destination-out`, pen pressure
  (size 25–100 %, alpha 35–100 %), `cancel()` restores the touched region.
- **Rendering** `js/render.js`: cached map-resolution composite updated per dirty region; sea gradient +
  engraved waves; coast effect (surf glow + ink edge via `shadowBlur`, 64 px region pad); CC0 parchment
  pre-scaled once so partial and full renders are pixel-identical; vignette and double frame; PNG export
  renders the same pipeline at 1×/2×.
- **Stamps** `js/stamps.js`: loads the curated manifest (id/file pattern checks, ≤ 200 entries, per-image
  failure tolerance) as the primary palette; built-ins = compass + pin, plus mountain/tree/house/castle only
  when the pack is unavailable.
- **Starter** `js/starter.js`: seeded (1337) landmass, island, lake, 7 terrain zones clipped to land, tapered
  river + brook, dashed roads, 60 Kenney stamps, 7 places with lore and 6 region/water/realm labels.
- **Input** `js/tools.js`: pointer capture (tolerant of synthetic pointers), coalesced events, second touch
  cancels the running gesture and starts pinch-zoom, `pointercancel` reverts, wheel zoom at cursor,
  Space/middle-button pan, tool keys, `[`/`]`, Delete/Escape; shortcuts and Space are ignored while typing.
- **UI** `js/ui.js`: palette, materials with live brush preview, inspector with one undo step per committed
  edit, layer list (visibility, active, up/down, rename, delete, add, opacity, coast), Orte list (jump +
  edit), status texts, export/restore/error flows; all user text via `textContent`/`value`.
- **Persistence** `js/storage.js` + `app.js`: IndexedDB draft 1.5 s after the last change, restore dialog,
  states `idle/pending/saving/saved/failed/unavailable` with a one-time toast on failure, `beforeunload`
  warning only when autosave failed/unavailable and the map was not saved as a file.
- **Automation hook** `window.rdMapmaker` (frozen): `ready`, `summary()`, `docToClient()`, `sampleRegion()` —
  read-only views used by the browser suite.
- **Entry** `vtt/templates/mapmaker.html`: `/mapmaker` → `/static/mapmaker/index.html`.

### 3.2 Files changed (all new; no existing file modified)
```
vtt/static/mapmaker/index.html
vtt/static/mapmaker/mapmaker.css
vtt/static/mapmaker/ATTRIBUTIONS.md
vtt/static/mapmaker/js/{app,brush,document,history,render,stamps,starter,storage,tools,ui}.js
vtt/templates/mapmaker.html
tests/test_mapmaker_static.py
tests/test_mapmaker_browser.py
docs/MAPMAKER_PROTOTYPE_DADM_2026-10-24.md
```
`vtt/static/mapmaker/assets/kenney-cartography/**` (Codex) and `docs/proofs/mapmaker-2026-10-24/` (appeared
during this session, not created by Claude) were not touched. `git status --porcelain` after implementation
shows the same 29 pre-existing modified files as at session start; all other entries are untracked additions.

### 3.3 Verification run (proofs)
| Command | Result |
|---|---|
| `/tmp/roll-drauf-mapmaker/test-venv/bin/python -m pytest tests/test_mapmaker_static.py tests/test_mapmaker_browser.py -q -p no:cacheprovider -W ignore` | **27 passed** in 166 s (7 static + 20 browser, incl. the Flask serving test) |
| Same browser file earlier without `-W ignore` | 20 passed, 8 warnings — all pre-existing (eventlet deprecation, reportlab, SQLAlchemy relationship overlaps in existing models) |
| Screenshot runs (scratch scripts in `/tmp/roll-drauf-mapmaker/claude/`) | desktop 1440 and mobile 390 renders reviewed; proofs in `/tmp/roll-drauf-mapmaker/claude/proofs/` |

Browser suite coverage (real input, pixels read from the rendered composite):
starter render at 1440/390 · brush stroke + exact undo/redo (button, Ctrl+Z, Ctrl+Shift+Z, Ctrl+Y) · size,
opacity and softness measurably change pixels · synthetic pen pressure 0.2 vs 1.0 · second finger reverts the
partial stroke, adds no history step and pinch-zooms · eraser on „Land“ reveals sea (undoable) · stamp place,
move, delete, undo · scatter = one undo step · layer hide/reorder/rename (HTML-like name stays literal)/delete
+ undo/add · place with `<img onerror>` lore stays literal, nothing executes, Space in the name field types a
space · tool keys ignored in the title field · wheel zoom/fit/+ · JSON save → change → load round trip with
exact pixels, 11 malformed/hostile files rejected with the current map unchanged · PNG export 2400×1600 and
4800×3200 · autosave → reload → restore (pixel-exact), „Neue Startkarte“ path · IndexedDB blocked →
„nicht verfügbar“, write failure → „fehlgeschlagen“ · manifest 404 → simple fallback stamps · narrow sheet,
tools and painting · Flask: `/mapmaker` redirect, `/static/mapmaker/index.html` with CSP, end-to-end load. Every
browser test asserts no page errors, no console errors and no CSP violations.

**Not run:** the repository's wider test suite (out of scope; broken repo venv); real touch hardware and real
pen tablets (only synthetic Pointer Events); Safari/Firefox (Chromium headless shell only); low-memory mobile
devices.

### 3.4 Acceptance checklist
- [x] `/mapmaker` redirects to `/static/mapmaker/index.html`; Flask serves it; preview `/mapmaker/` serves it.
- [x] Starter renders (sea ≠ land), „Die Silbermark“ + 7 places in the Orte list; curated stamps primary.
- [x] Brush changes pixels; undo restores exactly; redo reapplies; size/opacity/softness measurable.
- [x] Pen pressure 0.2 vs 1.0 differs; pressure toggle appears only after a pen is seen.
- [x] Eraser removes land.
- [x] Stamp place/move/delete with undo; scatter as one step.
- [x] Layer hide/reorder/rename/delete with undo; add layer; limits enforced in UI.
- [x] Place with lore add/edit; hostile lore shown literally.
- [x] Wheel zoom changes the indicator; Fit resets.
- [x] JSON round trip; malformed imports rejected without touching the current map (validation per §2.3).
- [x] PNG export 1× and 2× with correct dimensions.
- [x] Autosave restore; blocked and failing IndexedDB states visible.
- [x] No page errors/CSP violations under the app CSP; no horizontal overflow at 390 px; usable at 1440/390.
- [x] Works without the Kenney manifest; Kenney groups shown when present.
- [x] Only new files; pre-existing modifications untouched.
- [x] Undo budget 60 steps / 64 MB documented (§2.2, `js/history.js`); no per-move full snapshots.

### 3.5 Residual risks
| ID | Severity | Item |
|---|---|---|
| R1 | low | Memory: 3 starter raster layers + composite + paper + sea + 3 stroke scratch canvases ≈ 9 × 15 MB ≈ 140 MB GPU/CPU canvas memory at 2400×1600, plus ≤ 64 MB history; may be heavy on low-end phones |
| R2 | low | Touch/pen verified only with synthetic Pointer Events in Chromium; Safari (iPad + Pencil) untested |
| R3 | medium (ops, not code) | **All new files are `root:root` with mode `0600`/`0700`** (agent umask 077) — both Claude's files and Codex's `vtt/static/mapmaker/` + `assets/` subtree — while the repo convention is `admin:admin 0644`. Running the app or git as `admin` cannot read them (404s / permission errors). Claude's attempt to `chown`/`chmod` its own files needed an approval that was not available in this session. Fix before review as `admin`/any deployment: `chown -R admin:admin vtt/static/mapmaker vtt/templates/mapmaker.html tests/test_mapmaker_static.py tests/test_mapmaker_browser.py docs/MAPMAKER_PROTOTYPE_DADM_2026-10-24.md && chmod -R u=rwX,go=rX` on the same paths. Tests passed because they ran as root |
| R4 | low | First load generates the starter map client-side (noticeable on slow devices; a loading overlay is shown) |
| R5 | info | Labels are canvas-rendered; screen-reader access is via the Orte list and inspector only |
| R6 | info | `/mapmaker` is public like every page template; it carries no server data and makes no API calls |

No medium-or-higher **code** finding is open from Deploy. R3 is an operational file-ownership item outside the
agent's granted permissions; it is handed to the human/Codex with the exact command above.

**next_step:** Monitor (Codex): independent browser interaction, security/robustness review of
import/autosave/input paths, and defect reports back to Claude.

---

## 3b. DEPLOY rework — Codex review R1–R5 — status: **complete, awaiting Codex Monitor**

**input_summary:** Codex reproduced five MEDIUM implementation findings in Chromium
(`/tmp/roll-drauf-mapmaker/review-feedback.md`). Rework attempt 1 of 2 per finding (rework limit 2). Same
additive file boundary; no design change, no relaxed validation, no asset or pre-existing file touched.
Discover/Apply sections unchanged (no typo corrections needed).

**artifacts:** this ledger (immutable once Monitor closes); changed files `js/document.js`, `js/app.js`,
`js/tools.js`, `js/ui.js`, `tests/test_mapmaker_browser.py`.

### Review ledger
| ID | Finding (Codex) | Fix | Regression test(s) |
|---|---|---|---|
| R1 | `layerPngBytes` cached old bytes under a newer `rev`; async serialization could mix versions | `serialize()` now captures meta, items and raster pixels **synchronously** at call time (pixel copy unless the cached revision matches); encoded bytes are cached under the revision captured *before* async work, never overwriting a newer entry. `layerPngBytes()` kept with the same snapshot semantics | `test_r1_serialize_snapshots_synchronously_and_cache_tracks_revisions` (module level: red/A/x10 snapshot vs blue/B/x99 later); `test_r1_r4_async_file_save_keeps_newer_edits_unsaved` (held `toBlob`: first file = pre-edit snapshot, second save not stale) |
| R2 | Autosave persisted live stamp drags/scatter that were later cancelled | One predicate `editor.isMutating()` (stroke, scatter, moved drag via `input.mutating()`); `runAutosave` defers instead of saving, `gestureEnded()` (called on every pointerup/cancel) requeues it | `test_r2_cancelled_drag_is_never_autosaved`, `test_r2_scatter_cancelled_by_second_touch_is_never_autosaved` (timer fires mid-gesture → stays „pending“; after cancel the IndexedDB draft holds the committed state) |
| R3 | Adding a raster could exceed the 32 Mpx import limit | `canAddRaster()` = import contract (count ≤ 8, count × w × h ≤ 32 000 000), checked in `addLayer` **before** `createLayer` allocates; „+ Malebene“ disabled with explanation | `test_r3_raster_area_limit_and_2x_export_limit_on_a_4096_map` (4096² import, forced add rejected, layers/history unchanged, saved file re-imports) |
| R4 | `saveFile` cleared dirty state for edits made during encoding; autosave claimed „saved“ for outdated snapshots | Single `editor.generation` counter (bumped by `markChanged`, inspector live edits and document replacement); file save advances `fileGeneration` only to the snapshot's generation; autosave reports „saved“ only if the generation is unchanged, otherwise „pending“ + requeue; `beforeunload` uses `generation !== fileGeneration` | `test_r1_r4_async_file_save_keeps_newer_edits_unsaved` (unsaved + `beforeunload` blocks after the async save, clean after a second save), `test_r4_autosave_does_not_claim_saved_when_edits_arrive_during_encoding` (state sequence + restored draft contains the late stroke) |
| R5 | Off-map placement/drags wrote out-of-contract coordinates → unloadable export | Stamp/label placement (incl. scatter points) outside the map is rejected with a toast; created items and drags are clamped to `[0, w] × [0, h]` (subset of the import contract; partially off-map artwork still possible) | `test_r5_off_map_placement_is_rejected_and_drags_stay_in_contract` (10 % zoom, outside clicks rejected, edge stamp → (0,0), label → (2400,1600), export → import) |
| — | Codex final verification (full Chromium 1243): implicit `GET /favicon.ico` 404 tripped `assert_clean` in the R1 test (headless shell never requested it) | `index.html` now declares `<link rel="icon" type="image/svg+xml" href="../icons/icon-maps-compass.svg">` (existing self-hosted asset, relative path for Flask and preview); no other source change | existing cleanliness check in the browser suite; rerun by Codex |
| — | 2× export limit (already resolved) | Kept the dialog limit; added the same bound in `exportPng` (`MAX_EXPORT_PIXELS = 16 777 216`) before any allocation | covered in the R3 test (2× disabled, forced 2× shows an error, no download) |

### Deploy evidence (rework)
| Command | Result |
|---|---|
| `/tmp/roll-drauf-mapmaker/test-venv/bin/python -m pytest tests/test_mapmaker_browser.py -q -p no:cacheprovider -W ignore -k "r1 or r2 or r3 or r4 or r5"` | **7 passed** (78.8 s) |
| Mutation check: temporarily re-introduced the R2 guard (`isMutating` = `strokeActive`) and R4 dirty clearing, ran `-k "r2_cancelled_drag or r2_scatter or async_file_save"` | **3 failed as expected** (`unsavedFile` False; `mutating` False; autosave `saved` during scatter); fixes restored, marker grep = 0 |
| `/tmp/roll-drauf-mapmaker/test-venv/bin/python -m pytest tests/test_mapmaker_static.py tests/test_mapmaker_browser.py -q -p no:cacheprovider -W ignore` | **34 passed** (256.5 s): 7 static + 27 browser incl. Flask |

**Gaps:** the full run used the fixture defaults (headless shell `chromium_headless_shell-1234` +
`/tmp/roll-drauf-mapmaker/browser-libs`) because environment-variable-prefixed commands required an approval not
available in this session; Codex's exact environment (`chromium-1243`, `VTT_PROOF_DIR`) was not exercised by
Claude, so no proof screenshots were refreshed. Codex's `/tmp/roll-drauf-mapmaker/review-async.py` and
`review-placement.py` were not re-run by Claude (they need the preview server on port 8765); `layerPngBytes`
remains exported so the async script still applies. R3 (file ownership/mode, §3.5) is unchanged and still
needs the human/Codex command.

**Residual (rework):** none at medium or higher from R1–R5. Low: snapshotting copies each changed raster
layer once per save (≈ 15 MB transient per 2400×1600 layer).

**next_step:** independent Monitor by Codex.

---

## 4. MONITOR — status: **complete (owner: Codex)**

**Run the prototype**
- Flask: start the app as usual and open `/mapmaker` (→ `/static/mapmaker/index.html`).
- Preview: `python3 -m http.server -d vtt/static 8765` → `http://127.0.0.1:8765/mapmaker/` (no CSP header
  in this mode; the browser suite adds the app CSP itself).
- Tests: `/tmp/roll-drauf-mapmaker/test-venv/bin/python -m pytest tests/test_mapmaker_static.py tests/test_mapmaker_browser.py -q`
  (optional: `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`, `MAPMAKER_BROWSER_LIBS`, `VTT_PROOF_DIR`).

**Suggested review focus:** import validator bypasses (`js/document.js`), autosave restore of tampered drafts,
pointer edge cases (pen hover, palm rejection, lost capture), mobile sheet ergonomics, long sessions against the
64 MB history budget, PNG export on large documents.

**PNG → campaign workflow (documented, not automated):** Datei → Als PNG exportieren → Kampagnen → Kampagne
öffnen → „Karte hinzufügen“ (Spielleitung; existing upload + `POST /api/campaigns/<id>/maps`).

**Later roadmap (unchanged from Apply, not in this prototype):** campaign publish button, nav entry,
vector rivers/borders/hex overlay, scatter/texture brushes and masks, world→region→battlemap drill-down,
`world_atlas_nodes`, player reveal/fog, server-side drafts.


### 4.1 Independent Monitor completion (Codex)

**status:** complete. **input_summary:** independently validate the first useful world/regional map-maker prototype after Claude’s Deploy and bounded review rework.

**observed_results:** the prototype meets the acceptance checklist. Five medium correctness findings from Codex review are fixed and regression-covered. A missing favicon discovered in full Chromium is fixed. The operational ownership/permissions finding from §3.5 is closed: only newly added prototype and proof paths were normalized to `admin:admin`, 0644 files / 0755 directories, and read access was verified as `admin`.

**validation_evidence:** the full two-file suite passed34 tests in Claude’s headless-shell environment. Codex independently ran the seven new review regressions plus Flask serving on Chromium 1243; seven passed and the remaining test’s only failure was an automatic favicon404. After that one-line icon fix, Codex reran the failed case and seven static checks:8 passed in7.63 s. Independent async-snapshot and minimum-zoom off-map placement reproductions pass. Fresh1440 × 1000 and390 × 844 views have no page/console errors or horizontal overflow. Actual UI downloads produced a valid 2400 × 1600 PNG and an editable v1 project. All 40 asset hashes match, and all 49 pre-existing modified/untracked files retain their original contents. No unrelated tracked or staged changes.

**artifacts (retention: immutable proof):**
- [Independent review and resolved findings](proofs/mapmaker-2026-10-24/codex-review.md)
- [Machine-readable validation and source hashes](proofs/mapmaker-2026-10-24/codex-verification.json)
- [Desktop preview](proofs/mapmaker-2026-10-24/prototype-desktop.png) / [phone preview](proofs/mapmaker-2026-10-24/prototype-mobile.png)
- [Editable sample](proofs/mapmaker-2026-10-24/silbermark.rdmap.json) / [exported PNG](proofs/mapmaker-2026-10-24/silbermark.png)
- [Curated asset manifest](../vtt/static/mapmaker/assets/kenney-cartography/manifest.json), original license and review notes

**risks_and_assumptions:** low—Safari/Firefox and physical touch/pen hardware remain untested; synthetic pressure/multitouch and both viewport sizes passed in Chromium. Low—canvas and transient save snapshots can use substantial memory on low-end phones. Info—drafts are browser-local; campaign transfer uses the existing PNG upload path. Wider unrelated repository tests were not run; no production release was performed.

**next_step:** close this prototype milestone and use the working editor. A subsequent Apply pass can scope campaign publishing/server drafts and the world → region → battlemap links; those later workstreams remain outside this prototype.
