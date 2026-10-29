# Mapmaker desktop end-user journey + CRUD review (Claude, 2026-10-25)

DAD-M **Monitor** pass, standard profile, read-only product. Reviewer: Claude Opus 5.5 (`claude-opus-5-5`).
Bounded assignment: the existing `/mapmaker/` prototype, **desktop** UX and element CRUD only. Codex verifies
independently afterwards; the parent task writes the research comparison. No product code, tests or config
were changed.

## 1. Setup and method

| Item | Value |
| --- | --- |
| Target | `http://127.0.0.1:8765/mapmaker/`: the existing local preview (`SimpleHTTP/0.6 Python/3.12.3`). It sends **no CSP header**. I did not build an ephemeral CSP server. |
| Browser | Playwright Chromium 1243, headless, `--no-sandbox`, fresh context for each size and for reopen |
| Order | (1) Blind UI run: visible DOM, mouse and keyboard only, every cited screenshot viewed. (2) Source read afterwards, for root causes and the CRUD matrix. (3) Standalone replay. |
| Internal API | Not used in the UI run. The replay helper only awaits `rdMapmaker.ready`. |
| Product hashes | 57 files under `vtt/static/mapmaker` + `vtt/templates/mapmaker.html`. Aggregate before = after = `2dbf7e5aaa7eb93b23a7df4e59b35a9b60acb632416e9adf04f12b377ec71b5b` (`hashes-before.json`, `hashes-after.json`). |
| Writes | Only this directory and `/tmp/roll-drauf-mapmaker/research-2026-10-25/claude/`. `git status` at the end shows one other new untracked file, `docs/WORLDBUILDING_ATLAS_PLAN_2026-10-25.md`. It was not written by this review and was not read, to keep the review independent. |

The exploratory run went through a persistent driver (`harness/repl.py`). Every executed step and its output is
kept verbatim in `harness/transcript/NNN.py|.out`, including failed selector attempts. `harness/replay_journey.py`
is a standalone UI-only replay of the core journey plus the defects. Its last run: **14/14 checks reproduced**
(`replay/replay-result.json`). Evidence totals about 68 MB: 102 screenshots (56 MB) and two downloads (9 MB). Each
file's sha256 is in `artifact-manifest.json`.

## 2. Outcome summary

**Scenario:** a DM builds their own region from a **blank** map. They paint land and coast, add forest and rock on
terrain, add a river and a road, place mountains and settlements, and create three places with lore. They also add a
painted title and a project title, run CRUD and undo, save, export, and reopen in a new context.

**Result:** the scenario can be completed through the UI. The saved file and the PNG contain exactly the authored
map. There are no starter labels, and the only "starter" word in the file is "Silberlauf", which comes from my own
lore text. All lore survives save and reopen. Two journeys fail, though, and eight need a workaround or carry a
material defect.

| Status | Count | Journeys |
| --- | --- | --- |
| pass | 16 | J01 tool access, J02 blank map, J03 land/coast, J06 stamps, J07 places+lore, J08 reselect/update, J09 delete/undo, J10 overlap move, J13 save, J14 PNG, J15 reopen, J16 recovery, J17 hidden-layer guidance, J18 wheel safety, J21 typing safety, J23 layer CRUD |
| partial | 8 | J04 forest/rock layer routing, J05 river/road routing, J11 double-click rename, J12 title vs painted title, J20 select vs pan, J22 eraser residue, J25 draft restore, J26 asset lookup |
| fail | 2 | **J19** Space-pan paints after a tool click, **J24** Open discards unsaved work |
| gap | 1 | J27 object list / multi-select / group / lock / place↔symbol link |
| info | 1 | J28 geometry |

Details, exact repro steps and artifacts for each journey are in `journeys.json`. The entity CRUD matrix is in
`crud-matrix.json`.

## 3. Findings (severity-labelled)

### F1 — HIGH — "Öffnen" replaces unsaved work without warning and cannot be undone (J24)
- **Impact:** Edits made since the last file save are lost for good. The undo history is cleared, and the browser
  draft is immediately overwritten with the opened file (`markChanged()` after load). "Neue Karte" does warn in
  the same situation (j02), so users get no consistent safety net.
- **Repro:** Place any stamp; the status shows "Ungespeicherte Änderungen". Then Datei → Öffnen (.rdmap.json) … →
  choose a file. No dialog appears, the map is replaced, and Undo is disabled.
- **Evidence:** `screenshots/j66-open-with-unsaved-changes.png`, `j70-open-replaced-unsaved-work.png`, replay `D3`.
- **Root cause (source):** `ui.js:113` opens the file picker directly. `app.js:819-835` `openFile()` never checks
  `hasUnsavedFileChanges()` (`app.js:728`).

### F2 — MEDIUM — Space-hold pan paints instead of panning when a button has focus (J19)
- **Impact:** This is the most common desktop sequence: click a tool, then hold Space and drag to move the view. It
  leaves a stroke on the active layer. Undo recovers it, but the user has to notice first.
- **Repro:** Pinsel tool active. Click the "Pinsel" rail button (or "Einpassen"), hold Space, drag on the map. A
  stroke appears and the last undo reads "Pinselstrich". With the canvas focused, the same gesture pans (cursor `grab`).
- **Evidence:** `j40-after-space-drag-pan.png`, `j42-space-drag-focus-tool-button.png` vs `j42-space-drag-focus-canvas.png`, `replay/rp-space-drag-after-tool-click.png`, replay `D2`.
- **Root cause:** `tools.js:262-263` returns early on Space whenever `isControl(event.target)` (any button).

### F3 — MEDIUM — Material → layer routing only works one way (J04/J05)
- **Impact:** Choosing "Land" switches to the coast layer and shows a toast. Choosing Wald, Fels, Fluss or Weg
  afterwards keeps "Malt auf: Land". Forest, rock, river and road all end up baked into the Land layer, which means:
  - hiding or erasing them separately is impossible;
  - erasing a road on Land would cut the coast;
  - the dedicated "Gelände" and "Flüsse & Wege" layers stay empty.

  A first-time blank-map author hits this almost by construction, because the first material they choose is Land.
- **Repro:** Leere Karte → Land → paint → Wald → paint → Fluss → paint. Hiding Land removes everything.
- **Evidence:** `j08-forest-rock-river-road.png`, `j09-land-layer-hidden-everything-gone.png`. Workaround: pick the
  layer row by hand (`j15`). Replay `D1`.
- **Root cause:** `ui.js:174-182` only special-cases `material.id === "land"`.

### F4 — MEDIUM — The project title and the painted title are unrelated, with no hint (J12)
- **Impact:** On the starter map, renaming the header to "Nordmark" produces `nordmark.png`, but the image still
  says **DIE SILBERMARK**. A blank map gets no painted title at all; the user has to discover that the Ort tool with
  Stil "Reich" and Ortsart "Nur Beschriftung" makes one. The header input also looks like static text.
- **Evidence:** `j69-starter-header-title-vs-painted.png`, `j46`, `j47`. JSON shows `meta.title` and a separate
  `realm` label.

### F5 — MEDIUM — The draft-restore dialog focuses the discard option, and there is one draft slot (J25)
- **Impact:** After a reload, Enter or Space selects "Neue Startkarte". The first edit afterwards overwrites the
  only browser draft. Work that was never saved to a file is then gone.
- **Evidence:** `j67-reload-restore-dialog.png` (focus ring on "Neue Startkarte"), `j71`, `j73` (the third reload
  offers "Die Silbermark" instead of "Das Tarnland"), replay `D4`.
- **Root cause:** `ui.js:697-713` `showModal()` focuses the first button in DOM order (`restoreNo`).

### F6 — MEDIUM (workflow gap, atlas-relevant) — Places are not linked to symbols, and there is no object list (J27)
- **Impact:**
  - A place (label + kind + lore) and its settlement stamp are independent. Moving the stamp leaves the place
    behind (`j34`, the town moved away from the "Brückenfeste" pin).
  - The Orte list shows places only. Stamps and plain labels have no list, so an item that is fully covered can
    only be reached by moving whatever covers it.
  - There is no multi-select (Shift-click selects one item, a drag pans), no group and no lock.
- **Classification:**
  - Needed before a hierarchical atlas: place↔symbol link, an object list, and stable visible IDs.
  - Later advanced scope: lock, group, multi-select.
- **Evidence:** `j58`, `j59`, `j32`–`j34`, `crud-matrix.json`.

### F7 — LOW-MEDIUM — Cramped workspace at 1024 px wide or at 125% scaling; palette has no search (J26/J28)
- **Impact:** The right panel is a fixed 312 px and cannot be collapsed. At 1024×768 the fitted map is 600×400 CSS
  px (30% of the viewport). The stamp palette shows 265–414 px of its 1144 px of content, with no search or category
  jump, and long names are truncated. At 1280×720@125% the brush pane itself needs scrolling (477/506 px). Zooming
  and panning keep these sizes usable, so the impact is comfort rather than blocking. See §4.

### F8 — LOW — A new paint layer is inserted above the active layer, which may be "Symbole" (J23)
- Selecting a stamp silently makes "Symbole" the active layer (`app.js:553-556`). "+ Malebene" then inserts above
  it (`app.js:396-397`), so painting covers the symbols until the user presses ↓. The layers hint ("Oben liegende
  Ebenen verdecken …") explains the result, but not why it happened. Evidence: `j60`, `j62`, `j63`.

### F9 — LOW — Layer rename by double-click is wired but unreachable (J11)
- `ui.js:469` binds `dblclick`, but the first click calls `setActiveLayer → refreshLayers → replaceChildren`, so the
  second click lands on a new element. This happens even on the already-active row. The pencil button works.
  Evidence: `j74`, `j75`, replay `D5`.

### F10 — LOW — Opening a label for editing does not focus the Name field (J11)
- A double-click with Auswählen, or a click with the Ort tool on an existing label, opens the inspector, but focus
  stays on the canvas, so renaming takes an extra click. Newly placed labels do autofocus and preselect. Evidence:
  `j36`, `j37`.

### F11 — LOW — Status pill wording blurs "browser autosave" and "file saved" (J13/J15)
- After "Als Datei speichern" the pill says "Lokal gespeichert". Right after *opening* a file it says
  "Ungespeicherte Änderungen". Evidence: `j48`, `j51`.

### F12 — LOW — Lore is a 500-character "Kurzbeschreibung" that truncates silently (J07)
- The field uses `maxlength="500"`. I typed 544 characters, 500 were kept, and the only feedback was the counter
  reading 500/500. The textarea is 4 rows. This works for a hook, not for session notes. Evidence: `j23`.

### F13 — LOW — Two sets of Stil/Ortsart controls are visible while editing (J07)
- The inspector (the selected place) and the placement defaults (the next place) are stacked in the same pane.
  Evidence: `j20`, `j23`.

### F14 — LOW — Deleting an item gives no feedback
- A stamp or place disappears without a toast; undo works and is labelled "Löschen". Deleting a layer does show a
  toast. Evidence: `j34`.

### F15 — LOW — Eraser at equal brush size leaves a residue (J22)
- Default opacity 90% and softness 45% leave a faint streak on a road painted at the same size. Evidence: `j38`.

### Info
- **Undo:** every step is labelled. Visibility toggles count as undo steps. Open, New and reload clear the history.
  The budget is 60 steps / 64 MB (`history.js:5-6`); budget exhaustion by large land strokes was not tested.
- **Cursor:** stays `default` over selectable items, and the active "Auswählen" rail label is clipped (`j26`).
- **Hidden layers:** the guidance only appears after a blocked attempt, as a clear toast. The tool pane does not
  show the hidden state beforehand.

### Confirmed working (keep)
- One click to every tool, with labels, tooltips, shortcuts and `aria-pressed`.
- "Malt auf / Setzt auf" shows the active layer.
- The mouse wheel zooms and never paints.
- Typing in the title, name and lore fields never triggers tool shortcuts. Delete, Backspace and Ctrl+Z stay
  inside the field.
- Clicking at an overlap picks the topmost label.
- Layer delete shows "Strg+Z holt sie zurück".
- The export dialog explains PNG vs the editable file and the campaign import path.
- Filenames follow the project title.
- Reopening in a fresh context is lossless: visuals, 5 layers, 9 stamps, 3 places with byte-identical lore.

## 4. Geometry (fresh context, blank map, brush tool)

125% is emulated as CSS viewport × devicePixelRatio 1.25, not through the browser's own zoom UI.

| Screen | CSS viewport | Canvas element | Right panel | Fit zoom | Map on screen (CSS px) | Map / viewport | Stamp palette visible / content | Pane scroll needed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1440×900 | 1440×900 | 1052×848 | 312×848 | 43% | 1032×688 | 55% | 414 / 1144 | no |
| 1280×720 | 1280×720 | 892×668 | 312×668 | 36% | 864×576 | 54% | 331 / 1144 | no |
| 1024×768 | 1024×768 | 636×716 | 312×716 | 25% | 600×400 | 31% | 353 / 1144 | no |
| 1440×900 @125% | 1152×720 | 764×668 | 312×668 | 31% | 744×496 | 45% | 331 / 1144 | no |
| 1280×720 @125% | 1024×576 | 636×524 | 312×524 | 25% | 600×400 | 41% | 265 / 1144 | brush 477/506, stamp 477/518 |

These sizes do not change across viewports:

| Element | Size |
| --- | --- |
| Header height | 52 px |
| Tool rail width | 76 px |
| Tool buttons | 59×56 px |
| Undo / Redo / Help buttons | 34×34 px |
| Title input | 420 px wide (402 px at 1024) |

At every size, the place editor (Name, Kurzbeschreibung, Fertig, Auswahl löschen) and the export dialog's
"Exportieren" button stay inside the viewport.

## 5. Answers to the review questions

| Question | Answer |
| --- | --- |
| Canvas big enough at laptop heights? | Yes at 1280×720 and above (the fitted map is 864×576). Tight at 1024 wide and at 125% on 1280×720 (600×400 map, non-collapsible 312 px panel). |
| One click to a tool icon? | Yes, for all six tools. |
| Brush options clear? | Mostly yes: there are size/opacity/softness sliders with values and a live preview stroke. The problem is layer routing (F3), not the options themselves. |
| Active layer visible? | Yes: "Malt auf/Setzt auf: X" in the tool pane and a highlighted row in Ebenen. It is not prominent enough to prevent F3. |
| Select vs pan clear? | Partly. There is a separate Bewegen tool. With Auswählen, dragging empty space pans (no marquee). Space-pan depends on focus (F2). |
| Accidental paint while scrolling? | Not with the wheel. Yes with Space+drag after a tool click (F2). |
| Project title vs painted title? | Not obvious (F4). |
| Editable file vs PNG? | Clear in the export dialog. The status pill wording blurs it (F11). |
| Output matches the authored map? | Yes, for both the PNG and the JSON. |
| Keyboard vs text input? | Safe. |
| Asset lookup? | Category grid only, no search (F7). |
| Layer controls from the UI? | Yes. |
| Object selection from the UI? | Yes, for single items. |
| Double-click rename? | Partial (F9, F10). |

## 6. Prototype CRUD scope vs later scope

- **Required for the prototype CRUD (present):**
  - layer create/rename/reorder/opacity/visibility/delete with undo;
  - stamp create/move/resize/rotate/flip/delete with undo;
  - place create/read (list)/update (name, kind, lore)/delete with undo and lore round-trip;
  - project save, open and PNG export.
- **Required but defective:** F1 (open safety), F2 (space-pan), F3 (layer routing), F5 (draft default).
- **Missing; needed before an atlas foundation (not bugs today):** place↔symbol link, an object/outline list,
  stable visible IDs, and map-size choice for a new map.
- **Later / advanced:** lock, group, multi-select, palette search, collapsible panel.
- **Absent and not promised:** root-level project/map management beyond one file plus one browser draft, any
  world→region→city hierarchy, sub-map navigation, multi-user/multi-DM collaboration. No UI or contract hints at
  these yet; the v1 contract has no field for them.

## 7. Reference criteria (user-provided sources; past competitor changelogs not cited as current bugs)

- **GIMP 3.0 Move tool** separates "pick a layer under the pointer" from "move the active layer". Here it is
  pick-only, the pick changes the active layer silently, and that feeds F8. A covered item cannot be targeted
  (F6).
- **GIMP 3.0 save vs export** keeps the editable format (.xcf) apart from export formats. The prototype mirrors
  this well (J14). The weak spots are open/discard safety (F1, F5).
- **Inkarnate 2.0** (custom layers, brushes, masks, object workflows) and **Wonderdraft** (land, rivers, roads,
  symbol brush, labels) are the benchmarks for:
  - automatic per-material layer targeting (contrast F3);
  - object workflows (contrast F6);
  - asset search (contrast F7).

  This review makes no claims about their current behaviour.

## 8. Monitor result and next action

- **Validation result:** The prototype meets the core authoring and round-trip promise on desktop: 16 of 28
  journeys pass outright, and every save/export/reopen outcome matched intent. It does **not** meet strict
  acceptance yet, with one HIGH (F1) and four MEDIUM findings (F2–F5) plus the F6 workflow gap.
- **Residual risk:** I tested in Chromium only, emulated 125% instead of using the browser's zoom UI, did not run
  the 2× export, and did not exercise pen, touch or mobile (deferred by user priority). The `not_tested` list in
  `journeys.json` has the full set.
- **Recommendation:** **rework before atlas work.** A small Apply→Deploy milestone should cover:
  - F1: confirm on Open when there are unsaved file changes;
  - F2: make Space-pan work when a non-text button has focus;
  - F3: route each material to its layer, or warn when the target is unexpected;
  - F5: focus "Entwurf wiederherstellen" by default;
  - F9 and F10.

  A separate Apply design should then decide the place↔symbol link and object list (F6) as the atlas foundation.
  Codex should independently re-run `harness/replay_journey.py` and the journeys in `journeys.json`.
