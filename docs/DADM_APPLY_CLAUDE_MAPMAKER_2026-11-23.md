# C27-PLAN — Apply: Mapmaker M1–M6 + map-related N items

Phase: APPLY (planning only). Base `2fcd28deb4d39403b882fccf05f9941ed71e859f` on `fix/claude-editor-20261123`.
Sources read: AGENTS.md, DAD-M apply card, `docs/CLAUDE_HANDOFF_MAPMAKER_27_2026-11-23.md`,
`docs/DADM_DISCOVER_MAPMAKER_REVIEW_2026-11-23.md`, `docs/DADM_DISCOVER_EDITOR_CREATOR_FEEDBACK_2026-11-23.md`,
mapmaker `tools.js`, `ui.js`, `app.js`, `stamps.js`, `starter.js`, `document.js` (+ `vtt/mapmaker_document.py` grep),
`index.html`, `mapmaker.css`, tests `test_mapmaker_browser.py`, `test_review_maps_browser.py`, `test_feedback_b06_browser.py`.
Nothing was executed (no shell, no tests, no browser). Everything below is static code evidence or labelled inference.

## Context
The owner's first review (E01–E27) and the second review (N01–N26) report editor defects and wishes. Codex owns
T1–T4, i18n generation, tests, commits, deploy. Claude owns M1–M6 and the map-related N items. This plan
covers a small first slice that adds no dependencies and does not change the document format, plus bounded
follow-up slices.

## S1 — first slice: E03, E22, E26, E11 + N02, N17 (+N16a if D4 is accepted)
Files Claude will edit (DEPLOY): `vtt/static/mapmaker/js/tools.js`, `vtt/static/mapmaker/js/ui.js`,
`vtt/static/mapmaker/js/app.js` (drawOverlay node handles only), `vtt/static/mapmaker/index.html`,
`vtt/static/mapmaker/mapmaker.css`, new `tests/test_c27_mapmaker_browser.py`.
String table goes to Codex for `tools/i18n/tasks/c27-mapmaker.json` + `build_catalog.py`/`--check`. Claude writes that file only if Codex assigns it.
Files left alone: document.js, mapmaker_document.py, storage/zip/snapshot/history/atlas-bridge, render.js, and all shared nav/i18n/book-frame files.
No format, schema, server, dependency or persistence change.

### E03 — DE/US bracket hotkeys (tools.js keydown)
Cause in the code: `tools.js:442` `if (mod || event.altKey) return;` runs before the bracket check at :455.
- W3C UI Events §4.3.1: "Some operating systems simulate the AltGraph modifier key with the combination of the Alt and Control modifier keys" (https://www.w3.org/TR/uievents/#keys-modifiers).
- MDN getModifierState (Firefox table): on Windows, Alt and Control are each "Either … or AltGr key pressed". On Mac, AltGraph means "⌥ Option key pressed". On Linux GTK it is Level 3 Shift (https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/getModifierState).
- MDN key: `key` reflects modifiers and layout (https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key).

Inference, to be verified live: DE Windows (AltGr arrives as Ctrl+Alt) and DE macOS (Option = Alt) hit the early return. DE Linux probably works today. A second defect follows from the code: softness uses `shiftKey`, but on DE `{`/`}` are AltGr+7/0 with no Shift, so softness can't be reached on DE at all.

Target (decision D1): map the produced character, not Shift. `[`→size−, `]`→size+, `{`→softness−, `}`→softness+.
US behaviour stays the same, because Shift+[ already produces `{`.
```js
// Bracket characters depend on the layout: DE/macOS type them with AltGr/Option, which
// arrives as Ctrl+Alt (Windows), Alt (macOS) or the AltGraph state (Linux). Match the character.
const BRACKET_NUDGE = { "[": ["size", false], "]": ["size", true], "{": ["softness", false], "}": ["softness", true] };
const altGraph = (event) => event.getModifierState?.("AltGraph") || (event.ctrlKey && event.altKey);
```
In keydown, after the Alt+Arrow block and before `if (mod || event.altKey) return;`:
```js
const nudge = BRACKET_NUDGE[event.key];
if (nudge && !event.metaKey && (!event.ctrlKey || altGraph(event))) {
    ed.ui.nudge(nudge[0], nudge[1]);
    event.preventDefault();
    return;
}
```
Then delete the old block at :455–460.
- Unchanged: `if (typing) return` still runs first, so text, search, number and select inputs are protected. Ctrl+Z/Y/S, Alt+↑/↓, zoom keys, tool letters, Space-pan, wheel zoom, Alt+wheel reorder and middle/right pan all keep working.
- Cmd+[ / Cmd+] (macOS Back/Forward) and Ctrl-only+[ are left to the browser.
- Known side effect, accepted: Alt+[ on a US layout now nudges; before it did nothing.
- Text changes in index.html: brush hint line 225 `<kbd>Umschalt</kbd>+<kbd>[</kbd> <kbd>]</kbd>` → `<kbd>{</kbd> <kbd>}</kbd>`, reusing the existing `Weichheit.` key. Same change in the help `dt` at line 469. Add `<p id="helpBracketNote" class="mm-hint">` after the Bearbeiten `dl`, filled in `bindReviewControls` with "Deutsche Tastatur: AltGr+8/9 für [ ], AltGr+7/0 für { }."

### E22 — per-asset tool size for the session (ui.js)
Cause in the code: `ui.js:738` resets `ed.stampOpts.size` to `stamp.defaultSize` (or the crop size) on every selection, including re-selecting the same asset.
Target (D2): an in-memory map that lives for the page lifetime. Nothing is saved, autosaved or put in undo, and it is not cleared when you open another map. Asset IDs are stable or content-addressed, so this is safe across maps. Reload resets it, which the handoff explicitly allows.
- Constructor: `this.stampSizes = new Map(); this.recentStamps = [];`
- `stampSizeKey(id, crop)` → `crop ? \`${id}@${crop.x},${crop.y},${crop.w},${crop.h}\` : id`. A crop and the whole sheet have different natural sizes, so they get separate entries.
- `rememberStampSize()` stores `ed.stampOpts.size` under the key of the current asset and crop.
- Record a size in three places: the `stampSize` range onInput in `bindStamp` (covers slider and number field), the stamp branch of `nudge` after `this.stampSize.set`, and in `chooseStamp` when an explicit `size` is passed.
- `chooseStamp` resolves the size in this order: explicit `size` → remembered → crop-derived → `stamp.defaultSize`. Clamp to 16..320 as today. Also unshift `id` into `recentStamps` (dedupe, max 12).
- Not affected: inspector sizes of placed objects (`selStampSize`), `placeSymbolSize` and tile grid size.

### E26 — honest standard/custom filter semantics (ui.js renderPalette)
Cause in the code: `ui.js:684-685`. Catalogue assets match a style only as `pixel`+`pixelArt`, and never match a perspective. Catalogue manifests declare only `pixelArt` (stamps.js:229). `packs.json` has no style or perspective fields. Custom assets always carry style and perspective (the validators default to `other`/`top`).
Target (D3): strict matching on declared traits, an explicit "no claim" bucket, an honest count, and a reset button. No metadata is invented. `pixelArt:true` stays the only catalogue claim. The pack `kenney-iso` is not classified from its name; that waits for the M4b audit.
```js
const TRAIT_UNKNOWN = "unknown";
/** Declared traits only: own images state style/perspective; catalogue packs only state pixel art. null = no claim. */
function assetTraits(stamp) {
    return stamp.custom ? { style: stamp.style || null, perspective: stamp.perspective || null }
        : { style: stamp.pixelArt ? "pixel" : null, perspective: null };
}
const traitMatches = (value, filter) => !filter || (filter === TRAIT_UNKNOWN ? value === null : value === filter);
```
- `STYLE_FILTERS`/`PERSPECTIVE_FILTERS`: add `unknown: VTTUi("Ohne Angabe")` as the last option.
- Filter callback: check pack, category and search first. Then compute the traits. Return true if both trait filters match. Otherwise count `undeclared += 1` when every failing trait failed only because its value is null and its filter is concrete (not "unknown").
- Results text:
  - n>0: the existing text, plus ` · {count} weitere ohne Stil-/Perspektivangabe ausgeblendet` when undeclared > 0.
  - n=0 and undeclared>0: "Keine Symbole mit dieser Angabe. {count} passende Symbole haben keine Stil-/Perspektivangabe – „Ohne Angabe“ zeigt sie."
  - Otherwise the existing empty-state text.
- Replace the `title` tooltip at ui.js:243 with a visible `<p id="stampTraitHint" class="mm-hint">` under the field row: "Stil und Perspektive geben nur eigene Bilder an; Katalogpakete kennen nur „Pixelgrafik“."
- Add `<button id="stampFilterReset" class="mm-btn mm-btn-small">` "Filter zurücksetzen" next to `#stampResults`. It clears search, pack, category, style and perspective, sets page 0 and re-renders. It is hidden when every filter is at its default.
- The tile palette is unchanged.

### E11 — make existing node editing discoverable (ui.js, tools.js, app.js, css)
Cause in the code: after drawing, `tools.js:351` selects the new path but the tool stays "path". The inspector then shows "Wegpunkte bearbeiten" and node handles (app.js:347-358 draws them in every tool). But pointerdown in the path tool always starts a new path (tools.js:114). Node drag exists only in the select tool with Shift or `editPathNodes` (tools.js:159-168). So following the on-screen hint in the path tool draws a new path. This is code evidence, not yet reproduced in a browser.
Target (D5): no second editor, and no node editing inside the path tool (starting a new path at an existing endpoint must keep working).
- In the `pathNodeMode` change handler (ui.js:939): set `ed.editPathNodes`. If it is checked and the tool is not select, call `ed.setTool("select")` (the selection survives, see app.js:1893) and toast "Auswählen (V): Wegpunkte ziehen. Ohne Haken verschiebt Ziehen den ganzen Weg."
- `refreshInspector` path branch: when `ed.tool === "path"`, set `#pathEditHint` to "Im Wege-Werkzeug zeichnet Ziehen immer einen neuen Weg. „Wegpunkte bearbeiten“ wechselt zu Auswählen (V)." Otherwise keep the existing text.
- tools.js: extract `nodeUnder(item, point)`, the same 9/zoom tolerance used at :162, and use it in pointerdown. In pointermove without a gesture, when the tool is select, one path is selected and `(ed.editPathNodes || event.shiftKey)`, set `canvas.dataset.cursor = nodeUnder(...) >= 0 ? "node" : "select"`.
- css: `#mapCanvas[data-cursor="node"] { cursor: move; }`
- app.js drawOverlay: when `this.editPathNodes && this.tool === "select"`, draw the handles at radius 6/zoom with fill `#f2c66d`, so node mode is visible.
- Help: add `<dt><kbd>Umschalt</kbd>+<span id="helpNodeKey"></span></dt><dd id="helpNode"></dd>`, filled with "Ziehen" / "Wegpunkt des ausgewählten Wegs verschieben (Auswählen)".

### N02 — explain why the image brush greys out material colour (ui.js)
Cause in the code: `syncBrush` disables colour and texture on purpose (ui.js:432), but `syncMaterials` still marks the old material swatch as checked.
Target, with original image colours kept:
- In `syncMaterials`, when the image brush is active, no swatch has `aria-checked="true"` and the first swatch gets `tabIndex 0`. WAI APG: "If none of the radio buttons are checked, focus is set on the first radio button in the group" (https://www.w3.org/WAI/ARIA/apg/patterns/radio/).
- Call `syncMaterials()` from `syncBrush`.
- Append " Ein Material wählen, um wieder mit Materialfarbe zu malen." to the `#brushImageInfo` text.
- Add `aria-describedby="brushImageInfo"` to `#brushColorEnabled`, `#brushColor` and `#brushTexture`. No tinting.

### N17 — the place-symbol picker follows deliberate sources (ui.js updateSymbolOptions)
Cause in the code: ui.js:701/762 fills `placeSymbol`/`selSymbol` from the current page of the hidden stamp palette, which by default is the first Kenney page (trees and bushes).
Target (D6): the options are "Kein Symbol", then an optgroup "Zuletzt gewählte Symbole" (`recentStamps` filtered by `assetAvailable`), then an optgroup "Aktuelle Symbolpalette" (the page IDs, same filters as E26). Duplicates are removed. The current value and `labelOpts.symbol` are kept through `ensureSymbolOption`; `select.options` includes optgroup children.
- `renderPalette` stores `this.palettePageIds`. `chooseStamp` re-runs `updateSymbolOptions(this.palettePageIds || [])`.
- Hint under `#placeSymbol`: "Zuletzt gewählte Symbole und die aktuelle Seite der Symbolpalette (mit deren Suche und Filtern)."
- This adds no second catalogue.

### N16a (optional, only if D4 is accepted) — Escape leaves placement mode (tools.js)
Today Escape cancels the gesture and clears the selection; it never changes the tool. Proposed: `const busy = !!gesture || ed.selectionSet.count > 0;` keep the existing cancel and deselect, then if `!busy && ["stamp","label","tile","path"].includes(ed.tool)` call `ed.setTool("select")` and toast "Platzieren beendet – Auswählen (V)."
Repeated placement by clicking is unchanged. Brush and eraser are unchanged. The layout half of N16 goes to S4.

### S1 tests — new `tests/test_c27_mapmaker_browser.py` (imports fixtures as `test_review_maps_browser.py:17` does)
1. `test_bracket_keys_us_layout`: stamp tool → `keyboard.press("BracketRight")` raises `#stampSize`. Brush tool → `]`/`[` change `#brushSize`; `Shift+BracketLeft` (key `{`) changes `#brushSoftness` only.
2. `test_bracket_keys_altgr_and_option_events`: dispatch KeyboardEvents on the focused canvas, using `modifierAltGraph` from the EventModifierInit dict (https://www.w3.org/TR/uievents/#dom-eventmodifierinit-modifieraltgraph).
   - Windows DE: `{key:"[",code:"Digit8",ctrlKey,altKey}` → size; `{key:"}",code:"Digit0",ctrlKey,altKey}` → softness.
   - macOS DE: `{key:"[",code:"Digit5",altKey}` → size.
   - Linux: `{key:"]",modifierAltGraph:true}` → size.
   - Negative: `{key:"[",ctrlKey}` and `{key:"[",metaKey}` change nothing and are not `defaultPrevented`.
3. `test_bracket_keys_ignored_while_typing`: focus `#stampSearch`, type "[{" → the field value contains them and the sizes are unchanged. Also: Alt+ArrowUp still switches layer, Ctrl+Z still undoes, the plain wheel still zooms.
4. `test_asset_size_is_kept_per_asset_in_session`: A→16 via `#stampSizeNumber` → choose B (shows B's default) → choose A → `16`. Place → item size 16. `]` → 18 → B → A → 18. `historySteps` unchanged by size changes. Reload → A back at its default.
5. `test_filters_distinguish_declared_and_undeclared_traits`: empty map.
   - Style `painted` → 0 `.mm-stamp`, results mention "ohne Stil", reset button visible.
   - Style `unknown` → >0, no `custom:` IDs.
   - Pack `kenney-cartography` + style `pixel` → 0 with an undeclared count.
   - Upload/pixel-draw an own image (helper `make_pixel_asset`) → with pack `custom` it appears under `pixel`/`top`, not under `unknown`.
   - Reset → all five controls at their defaults and the full count. The existing assertions at test_review_maps_browser.py:116-126 stay valid.
6. `test_node_mode_checkbox_switches_to_select_and_moves_node`: path tool draw → `summary().tool=="path"`, path selected → check `#pathNodeMode` → tool is `select`. Plain drag on node 1 → points[1] moved, path count unchanged. Ctrl+Z / Ctrl+Shift+Z. Hover over the node → `#mapCanvas[data-cursor=node]`. Save/reopen keeps the points.
7. `test_image_brush_explains_disabled_colour`: as test_feedback_b06:105-109, plus no `.mm-swatch[aria-checked=true]` and the hint is visible. Clicking a material re-enables `#brushColor`.
8. `test_place_symbol_picker_offers_recent_symbols`: choose two stamps from different packs → label tool → `#placeSymbol optgroup` holds both. Place → the label symbol has the chosen asset. `scrollWidth <= innerWidth+1` at 1440 and 390.
9. (N16a) `test_escape_leaves_placement_tool`: stamp tool, Esc → `select`. Label tool with a selection, Esc → still `label` and deselected; a second Esc → `select`.

Codex also runs the regression set: `tests/test_mapmaker_browser.py`, `test_review_maps_browser.py`, `test_feedback_b06_browser.py`, `test_c04_mapmaker_browser.py`, plus the i18n build `--check`.
Live acceptance (Codex): on /mapmaker, log keydown `key/code/ctrlKey/altKey/getModifierState("AltGraph")` on Windows DE, macOS DE, Linux DE and US, then repeat the E22/E26/E11 journeys as a logged-in user.

### S1 new strings (DE source → EN)
- Ohne Angabe → Not specified
- {count} weitere ohne Stil-/Perspektivangabe ausgeblendet → {count} more without a style/perspective tag hidden
- Keine Symbole mit dieser Angabe. {count} passende Symbole haben keine Stil-/Perspektivangabe – „Ohne Angabe“ zeigt sie. → No symbols with this tag. {count} matching symbols have no style/perspective tag – “Not specified” shows them.
- Stil und Perspektive geben nur eigene Bilder an; Katalogpakete kennen nur „Pixelgrafik“. → Only own images state style and perspective; catalogue packs only mark “Pixel art”.
- Filter zurücksetzen → Reset filters
- Deutsche Tastatur: AltGr+8/9 für [ ], AltGr+7/0 für { }. → German keyboard: AltGr+8/9 for [ ], AltGr+7/0 for { }.
- Auswählen (V): Wegpunkte ziehen. Ohne Haken verschiebt Ziehen den ganzen Weg. → Select (V): drag waypoints. Unchecked, dragging moves the whole path.
- Im Wege-Werkzeug zeichnet Ziehen immer einen neuen Weg. „Wegpunkte bearbeiten“ wechselt zu Auswählen (V). → In the path tool, dragging always draws a new path. “Edit waypoints” switches to Select (V).
- Ziehen → Drag
- Wegpunkt des ausgewählten Wegs verschieben (Auswählen) → Move a waypoint of the selected path (Select)
- Ein Material wählen, um wieder mit Materialfarbe zu malen. → Choose a material to paint with material colour again.
- Zuletzt gewählte Symbole → Recently chosen symbols
- Aktuelle Symbolpalette → Current symbol palette
- Zuletzt gewählte Symbole und die aktuelle Seite der Symbolpalette (mit deren Suche und Filtern). → Recently chosen symbols and the current page of the symbol palette (with its search and filters).
- Platzieren beendet – Auswählen (V). → Placement finished – Select (V). (N16a only)

## Follow-up slices (each needs its own DEPLOY task and file ownership)
| Slice | IDs | Contract, acceptance and decision with recommended default |
|---|---|---|
| S2 M2a layer targets + compact layer bar | E20, E09, E10, E21-lite, N03, N01 repro, N05 | `addPath` uses `targetLayer("paths")` semantics: active paths layer → topmost visible → refuse hidden with a toast. It creates a layer only when no paths layer exists. Check the target at pointerdown so a stroke is not lost. The starter raster "Flüsse & Wege" is never retyped (D7: new vector layers are named "Wege (Vektor)"; existing names stay). Compact stage layer bar reuses `setActiveLayer`/`setLayerProp`: WAI radio group, eye toggle, disclosure at 390 behind `activeLayerJump`. E21: kind filter plus item counts; "zuletzt verwendet" means used in this session, not saved (D8). N05: view-only "Raster anzeigen", separate from snapping; grid = active tile layer or stamp grid (D9). Acceptance as in the handoff M2: drawing lands on a lower compatible layer, no duplicate, raster pixels kept, 390/1440 reachable. |
| S3 M3a labels/objects UX (no schema) | N12, N13, E16, E17-discoverability | N12: label ghost in drawOverlay from `createLabel(cursor)` via an exported `drawLabel` at alpha 0.55; pointermove repaints in the label tool. Pre-configuring stays optional. N13: 0/45/90/135/−45 presets write the existing `rot` (one undo per click). E16: object list (paths, stamps, tile layers, labels) extending `refreshPlaces` in the Orte tab, filter by kind/layer; list and map select the same item; no schema. Reuse fonts, rotation and path names. |
| S4 M2b progressive panel | E23, N16b, N10 | Stamp palette before rare options (`<details>`, WAI disclosure, open state kept for the session). After placing a label the tool options stay where they were. N10: repro first in Brave and Chrome at 1440/390, measuring `scrollWidth`, `#stage` and `#panel` boxes with a long select open. Hypotheses only: pane scrollbar (`scrollbar-gutter`), select intrinsic width, shared frame (Codex-owned). |
| S5 M1b input | E02, E04, E07 | E02: last 8 custom colours recorded on committed strokes, localStorage `rd.mapmaker.recentColors.v1` (D10), shown as selectable swatches. E04: digits 1–0 set opacity 10–100 % in brush/eraser with canvas focus (D11; layout-independent). E07: Shift+wheel changes size in brush/eraser/stamp using `deltaY||deltaX` (D12). Ctrl+wheel/pinch zoom, Alt+wheel reorder and middle pan are untouched. Acceptance: slider, preview and keys show the same state. |
| S6 M3b path modes (no schema) | E12, E14 | Path sub-mode "Punkte setzen": click adds a node, Enter or double-click finishes, Backspace removes the last, Esc cancels. It writes the existing `points`. The draw/edit toggle reuses the W/V tools and node mode (D13 key). Old paths are never rewritten. |
| S7 M3c line/label schema | E13, E15, E19, E18, E17-relation, N15 | One versioned format change, applied to client and server validators, render, snapshot, ZIP, PNG and Atlas. Optional fields only, absent means today's behaviour: per-node `corner`/tension (D14), line style enum road/trail/river/border plus dash (D15), optional path `color`, river-to-sea end colour (D16), optional `places:[id]` relation (D17), label `tracking` (D18). No silent migration. |
| S8 M5 own content | E24, E25 | E24a: explain the existing upload, crop and pixel entry, and add it to the tile tool. E24b: tileset import = PNG sheet + grid + optional JSON, using the existing `LIMITS` checked before decoding (D19 format). E25: keep source, licence and rights confirmation. An optional "KI-generiert" provenance field only after an owner decision (D20). The public policy stays undecided: no ban, no blanket permission. |
| S9 M4b catalogue personalisation + audit | E27, N08 | Hidden assets and personal sets per account or localStorage (D21), applied after S1 filters. Pack-level trait claims (e.g. `kenney-iso` perspective) only after an inventory review, with recorded provenance. No bulk retagging, no new asset sourcing. |
| S10 grid contracts | N06, N07, N04, N09 | N06: a non-empty tile layer's grid change must not silently move content. Recommended: refuse it and offer "neue Kachelebene mit Größe X" or an explicit rescale (D22). N07 calibration, N04 snap pattern (2×2 example), N09 cell rotation (format change) each get their own Apply. |
| S11 deferred | E01, E05, E06, E08, N14 | Fill only inside the active raster layer's closed outline, one undo, sea and other layers untouched (D23). Rough/triangle tips next to image tips. Coast waves. Radial menu must avoid middle-button pan (D24). Curved text after S3/S7. |

N11 (Atlas/world relations) is T5, outside this assignment. The Atlas bridge is reused unchanged.

## Risks resolved by S1
- Shortcut conflicts: Meta and Ctrl-only shortcuts stay with the browser; the typing guard runs first; zoom, pan, undo and reorder are unchanged.
- Misclassification: only declared traits are used; unknown is shown, not assumed.
- Document/undo compatibility: no doc fields; the size cache is not document state.
- Asset IDs are unchanged.

Residual: the AltGr reports per OS are inferred from the specs until the live event log; nudge in non-brush tools still changes brush size (unchanged); N10 is unproven.
