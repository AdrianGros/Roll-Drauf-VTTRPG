# Agent-Report 4/4 — Code-Analyse Spieltisch-Layout (D14–D18) (2026-08-25)

(Voller Report des Code-Agenten, read-only; Synthese in docs/FIX_RESEARCH_DESKTOP_AUDIT_2026-08-25.md §5.)

## 1. Current layout mechanics (evidence base)

### 1.1 Shell
- `.tabletop-shell`: 2-column grid `54px 1fr`, `position:relative` — `play.html:322-329`. Containing block of the sidebar.
- `.stage`: `position:relative; overflow:hidden` — :365-370; contains `.map-viewport` (absolute, inset:0, overflow:auto — :371-376), `.stage-topbar`, and all three floating widgets (DOM children of `<section class="stage">` at :1470; `#layersWidget` :1522, `#tokenWidget` :1575).
- Width chain (D17): `body.play-workspace-realign main { width: min(1680px, calc(100vw - 24px)); margin: 0 auto; }` — `vtt/static/css/book-scene.css:580-585`; camera/page/shell flex/height 100% (:114-135, 167-171); `.play-workspace-page .book-shell-frame { overflow:hidden }` (:101-105).

### 1.2 Sidebar
- `.right-sidebar`: absolute overlay in the shell — `top/right/bottom:0; width:340px; max-width:88vw; z-index:26; transform:translateX(100%); transition:transform 240ms` — :759-775; `.is-open { transform:translateX(0) }` — :776-778. M3 comment (:756-758): old fixed 370px grid column was "the single biggest tax on map screen space".
- JS: toggle/close/tab-click — `play-ui.js:744-767`. No resize/refit hook on open/close.
- **Existing dodge precedent:** `.tabletop-shell:has(.right-sidebar.is-open) .stage-topbar { right: calc(340px + 1rem) }` (280px variant under max-height:720px) — :544-551; comment history shows this collision fought twice for the topbar (:534-543).

### 1.3 Floating widgets
- `.floating`: absolute, z 18, width 280, max-height 40%, overflow auto — :571-581; collapsible (:587-606); JS default state: layers open, others collapsed — `play-ui.js:1205-1214`.
- Anchors: `#turnOrderWidget { left:1rem; bottom:1rem; width:220px }` :611-615; `#layersWidget { left:1rem; top:3.4rem; width:320px; max-height:54% }` :616-621; `#tokenWidget { right:1rem; bottom:1rem; width:300px }` :735-739.
- `#activePagePill` ("Seite: …") inside `.stage-topbar`, `margin-right:auto`, `pointer-events:none`, z 20 — :713-734, markup :1472.

### 1.4 Z-order (desktop)
map 1/2/4 (:408,422,428) → floating 18 (:577) → pill 20 (:732) → **sidebar 26 (:771)** → topbar 30 (:537; dragging token :461) → curtains 80/85 (:191,207). Sidebar(26) > widgets(18) = D14; topbar(30) escaped only via the slide-left rule.

### 1.5 Media queries
- max-width:1280 — narrower rail, widgets 260px (:1091-1096). max-height:860/720 — compaction; sidebar 280px (:1097-1143).
- max-width:1040 — mobile regime (:1149-1387): bottom toolbar ribbon (z 40), full-width sidebar, widgets **reparented by JS into `#tableSheet`** (z 60, backdrop 55) via matchMedia in `_setupTableSheet()` — `play-ui.js:1217-1256`, markup :1460-1468; sheet neutralizes floating anchors with `position:static !important` — :1243-1257. (= the commit-08f77d1 "Tisch sheet" pattern.)
- `.sidebar-close` visible only <1040 (:789-793).

### 1.6 Zoom/fit
- `_zoomFit()` fits world to `clientWidth/Height − 48`, cap 150% — `play-ui.js:942-952`; `#btnZoomFit` wiring :787.
- Auto-fit ONCE per newly activated map (`autoFitMapId` guard) — :2192-2198, init :59-61. No resize/sidebar-toggle re-fit; manual zoom sticks.

### 1.7 Role gating today
- Role source `this.bootstrap.session_role`; `normalizeRole`/`isOperatorRole` (DM, CO_DM) — `play-ui.js:21-27`; `roleBadge` display-only (:1762-1766, markup play.html:1426).
- `readOnly` is server-driven (`payload.read_only`, :227, :1509, :1635) — false for interactive PLAYER.
- DM-only hiding pattern to copy: `_renderState()` — `layerAddRow.hidden = !operator || this.readOnly` + session controls `disabled = !canOperate` (:2064-2072, :1785-1810); token upload row :2099-2100; `#initiativeControls` operator-gated (:2071-2081, markup play.html:1567). CSS lesson: `.layer-add-row[hidden] { display:none }` because a flex class beat `hidden` — play.html:694-697.

## 2. D14 — sidebar covers #tokenWidget

Root cause: overlay z26/340px spans the full right edge; widget right:1rem z18. Viewport-independent ≥1041.

- **(a) Reflow — M:** shell grid `54px 1fr auto`; sidebar becomes grid item (static, width 0/340, animate width, overflow hidden). Collision impossible by construction; topbar hack :544-551 deletable; D15 class disappears. Map narrows 340px while open (M3 objection was about a PERMANENT column; on demand it's the user's trade). Canvas harmless (overflow:auto; no auto re-fit exists); optional `_zoomFit()` on toggle when zoom was the auto-fit one. Touches play.html:322-329, 544-551, 759-778.
- **(b) Safe-area inset — S:** `.tabletop-shell:has(.right-sidebar.is-open) .stage #tokenWidget { right: calc(340px + 1rem); }` + 280px variant + `transition:right 240ms`. Smallest diff, mirrors accepted mechanism. Cons: third copy of magic 340/280 → hoist `--sidebar-w`; at 1041–1280 the shifted widget can crowd `#turnOrderWidget`/map center (1199: widget lands x≈540 — acceptable).
- **(c) Dock widgets as sidebar tabs / desktop table-sheet — L:** reuse `_setupTableSheet()` reparenting (IDs stay stable, comment play-ui.js:1218-1221; mobile path proves it, play.html:1243-1257). Changes desktop interaction model ("Tokens + Chat gleichzeitig" dies) — UX decision, not asked for.

**Recommendation: (b) now (S) with `--sidebar-w`; (a) as structural end-state; (c) only as deliberate UX decision.**
Robot pin: fullsession real UI clicks on #tokenWidget with sidebar open; play.json contract "with .is-open, elementFromPoint(center of #tokenWidget header) resolves inside #tokenWidget" across 1199/1201/1440/1920/2560.

## 3. D15 — off-canvas invariant

Today hidden by ONLY `transform:translateX(100%)` (:772); no visibility/pointer-events/display. Not clipped by the shell (no overflow, :322-329); saved by ancestor `.book-shell-frame { overflow:hidden }` (:101-105) + centered main width under 1200 (book-scene.css:582). Fragile: any overflow/stacking change turns it into click theft.

- **S (recommended):** on `.right-sidebar`: `visibility:hidden; pointer-events:none; transition: transform 240ms ease, visibility 0s 240ms;` — on `.is-open`: `visibility:visible; pointer-events:auto; transition: transform 240ms ease, visibility 0s;`. Plus `inert` attribute toggle in the handlers (play-ui.js:747-755) — kills focusability/AT exposure (Tab-focus into closed drawer is an unprobed variant).
- M: reflow (2a) makes it moot (width:0 — nothing off-canvas).

Gate (play.json): closed state — for each interactive element in `.right-sidebar`, elementFromPoint at center must NOT resolve into the sidebar; computed `visibility === "hidden"`; `document.activeElement` never enters via Tab. Template: the audit's sliver evidence (screenshot + hit-test JSON).

## 4. D16 — layers header clips under page chip

Geometry: topbar at top:0.85rem + padding 0.42rem + ~28px controls ends ~y55; `#layersWidget` top:3.4rem ≈ 54.4px (:520-533, :616-621). Pill (topbar z30) paints over widget h3 (z18) on every load — layers is the one widget defaulted open (play-ui.js:1205-1210).

- **S (recommended):** stop overlapping — `.stage-topbar { --topbar-h:44px }`, `#layersWidget { top: calc(0.85rem + var(--topbar-h) + 0.5rem) }`; adjust max-height:860 compaction blocks (:1102-1106) likewise.
- S-alt (rejected): pill is pointer-events:none, could lower it visually — keeps text-over-text.
- M: ResizeObserver-measured offset — only needed if the topbar wraps (it can: flex-wrap, :527, at very narrow desktop + long page names).

Pin: R6 table baseline + play.json assertion: bounding boxes of `#activePagePill` and `#layersWidget > .widget-toggle` never intersect on load across the desktop matrix.

## 5. D17 — 1624px map cap

Source: `book-scene.css:580-585` — `min(1680px, calc(100vw − 24px))` on main (shared with character-sheet-focus-realign). 1680 − 54 (toolbar col, play.html:324) − 2 (borders) = **1624** — matches the measurement at 1920 AND 2560. Generic book-shell cap is 1480 (book-shell.css:121-125) — play already overrides upward once; the Satzspiegel argument is half-abandoned on this page.

- **S (recommended): lift for the table only** — play.html inline override: `body.play-workspace-realign main { width: calc(100vw - 24px); max-width:none; }` (or min(2560px,…) as sanity ceiling). Character sheet keeps 1680. Canvas: pure win; auto-fit runs per map activation with final layout.
- S-alt: keep 1680 deliberately → document as Soll + freeze (`mapW === 1624 ± 2` gate at 1920/2560).
- Adrian's decision per Hausregel; engineering recommendation: lift.

Pin either way: map-share gate at 1920/2560 (floor from the audit's D21 positive: 85–99% up to 1920).

## 6. D18 — players see layer-management controls

Where: `_renderLayers()` — play-ui.js:1821-1877 — renders for EVERY role: rename input (:1841), up/down (:1846-1847), visibility eye (:1848), delete (:1849), "Aktivieren" (:1834-1836). Only gate is `this.readOnly` (:1857-1876) — interactive PLAYER has readOnly=false → live controls whose API calls (`updateLayer`/`deleteLayer`/`activateLayer`, :1952-1984) can only 403. Sibling add-row is correctly gated (:2065-2070).

- **S (recommended): operator-gate row controls, same pattern.** `const operator = isOperatorRole(this.bootstrap?.session_role || "")` (identical to :2007); non-operator: label as plain div (no input), omit `.layer-actions-row` entirely, omit "Aktivieren" (write path, rejected for players — passive "aktiv" chip stays); also skip `_renderLayerAddControl` for non-operators (currently only readOnly-skipped, :1879-1881 — same bug class: fires a maps API call). innerHTML templating → simply not emitting markup is the cleanest (nothing to un-hide by CSS accident; cf. play.html:694-697 lesson).
- M: server-sent `capabilities` object in bootstrap (e.g. `can_edit_layers`) — architecturally nicer (client stops deriving role logic), needs backend change; the S fix uses server-shipped `session_role` (server truth, not guessing). Consider M when bootstrap payload is next touched (aligns with playtable-P0 direction, cf. play-ui.js:2116).
- L: full role-aware component split — not warranted.

Pin: play.json with role dimension — as PLAYER, `#layerList [data-act="rename"|"visibility"|"delete"|"up"|"down"]` must not exist/be visible; as DM they must exist with post-conditions (rename persists, eye toggles is_player_visible, delete removes row). Companion R12 gate: player table session produces zero 4xx from layer endpoints.

## 7. Summary table

| Finding | Recommended fix | Size | Robot pin |
|---|---|---|---|
| D14 | Safe-area inset via `:has(.is-open)` + `--sidebar-w` (end-state: grid-column reflow) | S (a: M) | fullsession UI click + elementFromPoint contract |
| D15 | visibility+pointer-events+delayed transition, `inert` in JS | S | off-canvas never visible/hit-testable/focusable |
| D16 | `--topbar-h`-derived widget offset | S | R6 baseline + no-intersection assertion |
| D17 | Lift 1680 cap for play only (Adrian; else document as Soll) | S | map-share gate 1920/2560 |
| D18 | Operator-gate `_renderLayers` rows (mirror layerAddRow), players get read-only rows; skip add-control for non-operators | S | role-dimension contract + zero-4xx gate |

Key files: `vtt/templates/play.html` (inline table CSS), `vtt/static/js/play-ui.js`, `vtt/static/css/book-scene.css:580-585`, `tools/robots/contracts/` (play.json new, on the fleet doc's open list).
