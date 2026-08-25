# Agent-Report 2/4 — VTT-Desktop-Layout-Patterns (Web-Recherche, 2026-08-25)

(Voller Report des Research-Agenten; Synthese in docs/FIX_RESEARCH_DESKTOP_AUDIT_2026-08-25.md §5.)

## 1. Per-product findings

### Foundry VTT
- **Full-bleed canvas + HTML overlay UI.** Canvas fills the window; all UI absolutely positioned over it. Expanding the right sidebar does NOT resize the canvas — tokens near the right edge are simply covered.
- **Collapsed-first in v13:** the redesign made the sidebar a full-height cabinet that **starts collapsed by default "to draw the eye to the canvas"**; clicking the active tab collapses again. Foundry mitigates occlusion by making collapsed the resting state, not by reflowing. https://foundryvtt.com/api/v13/classes/foundry.applications.sidebar.Sidebar.html · https://foundryvtt.com/releases/13.339
- **Not user-movable/resizable in core** — an ecosystem of modules patches this (sidebar-resizer, resize-sidebar, vance-sidebar-resizer, Minimal UI). Module demand = evidence of persistent friction.
- **Z-order trick:** chrome above canvas; app windows above chrome; floating widgets never collide with the sidebar because they're all anchored LEFT — the right edge is reserved exclusively for the sidebar. **One edge = one owner.**

### Roll20
- **Reflow (true split).** Right sidebar is a sibling column; map area is the remaining width. Sidebar **user-draggable in width**, **collapsible via tab handle**; collapsed = map gets full width. Nothing on the map is ever hidden by the sidebar. https://app.roll20.net/forum/post/335010/just-the-sidebar · https://app.roll20.net/forum/post/33/how-do-i-resize-the-chat-panel

### Owlbear Rodeo 2.x
- Full-bleed canvas + edge-anchored chrome **with explicit collision logic**: action bubbles are "anchored to the closest corner … and adjust to UI already present … a bubble on the bottom will dynamically flow around the dock". Clearest documented constraint-based floating-widget collision avoidance in a VTT. https://blog.owlbear.rodeo/owlbear-rodeo-2-0-dev-log-2/ · https://blog.owlbear.rodeo/owlbear-rodeo-2-2-release-notes/

### Alchemy
- Fixed multi-panel dashboard; map is one panel among several. Reviewers call the arrangement "confusing and awkward" — caution against making the map share status with panels. https://help.alchemyrpg.com/en/articles/9821384-player-orientation · https://www.numtini.com/2025/01/14/alchemy-vtt-changing-gold-into-lead/

### Talespire
- 3D viewport with slim overlay toolbars; panels transient. Inspiration for minimal-chrome "the scene is the product" posture.

### General app patterns
- **Figma UI3 is the decisive data point:** shipped floating panels over the canvas, then **reversed before full rollout** — panels "cramped the canvas", content "distractingly peeked out from behind them". Final UI3: **fixed (docked, reflowing) resizable panels**. Content sliding under panels is exactly the failure mode Figma retreated from. https://www.figma.com/blog/our-approach-to-designing-ui3/ · https://www.figma.com/blog/behind-our-redesign-ui3/ · https://medium.com/x-periment-asteroid/why-figmas-floating-panels-missed-the-mark-8813872d1689
- **VS Code / Photoshop:** side bars and panels always **reflow** the editor/canvas; collapsible, draggable, persisted. https://code.visualstudio.com/docs/configure/custom-layout

**Pattern summary:** persistent work panels (Roll20, Figma-final, VS Code, Photoshop) reflow; transient panels (Foundry, Owlbear, Talespire) overlay — and the overlay camp compensates with collapsed-by-default resting states and corner-anchoring collision logic. A panel open for long stretches (chat/journal during a session) behaves persistent and therefore wants reflow.

## 2. CSS approach for "sidebar opens → map reflows"

- Grid shell: `grid-template-columns: 1fr var(--sidebar-w)`; canvas cell `min-width:0; overflow:hidden`. Toggle `1fr 0fr` ↔ `1fr minmax(280px, 22rem)` — animatable (Firefox 66+); collapsing track must be `0fr`. Alternative: fixed-width flex sidebar + `transition: width`. https://web.dev/articles/css-animated-grid-layouts · https://css-tricks.com/animating-css-grid-how-to-examples/
- **Cost:** animating tracks/width = layout+paint per frame, not compositor-accelerated. Pragmatic: (a) short ~200ms transition, re-fit canvas backing store only when settled; or (b) snap the track, animate only the sidebar transform. Nobody re-renders WebGL at 60fps during a panel transition. https://blog.logrocket.com/new-in-firefox-66-animating-css-grid-b4ed90ac32f5/
- **Canvas re-fit:** ResizeObserver on the canvas element (`devicePixelContentBoxSize` × DPR fallback), debounced via rAF. Never poll `window.resize` — sidebar toggle doesn't fire it. https://webglfundamentals.org/webgl/lessons/webgl-resizing-the-canvas.html · https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver
- **Anchor-jump pitfall:** naive resize keeps top-left world coordinate fixed → map appears to slide. Fix: record world point at old viewport center, resize, re-solve pan offset so that point maps to the new center (same math as zoom-to-cursor), inside the same rAF as the buffer resize.

## 3. Collision-free floating widgets

- **Owned-edge rail** (Foundry's implicit rule): each edge/corner belongs to exactly one system. Floating widgets anchor relative to the *map area*, not the viewport — which reflow gives for free.
- **Inset custom properties as safe areas:** shell exposes `--map-inset-right/bottom` (0 closed, panel width open); every widget uses `right: calc(12px + var(--map-inset-right))`. One variable transition moves all widgets in sync — mirrors Owlbear's bubbles-flow-around-dock.
- **CSS Anchor Positioning is Baseline in early 2026:** Chrome/Edge 125+, Firefox 132+, Safari 18.2+ (~88–91%); `@position-try` needs Safari 18.4+; @oddbird polyfill ~8KB. Use for small collisions (e.g. anchor layers panel below the page chip); don't build the whole layout on it yet. https://caniuse.com/css-anchor-positioning · https://www.joshwcomeau.com/css/anchor-positioning/
- **Stacking:** explicit z-scale (map 0 → widgets 10 → chrome/sidebar 20 → dialogs 30 → toasts 40), never two layers in one band. The current bug is widgets and chrome competing in the same band AND edge.

## 4. Very large monitors (2560px+)

- No VTT caps the canvas — Foundry, Roll20, Owlbear, Talespire let the map own every pixel not taken by chrome. Max-width guidance (1140px-ish, 60–75ch) applies to TEXT, not viewports. Cap instead: sidebar (rem, not %), text columns (~65ch), and keep related controls clustered per corner on ultrawides. https://martech.zone/optimal-web-page-width/ · https://design.canada.ca/styles/layouts.html

## Recommendation

**Hybrid — reflow for the sidebar, overlay only for transient UI.** For a book-styled VTT thematically right: opening Journal/Chat reads as opening the book wider, the map page yields space — not a card over the map.

1. **Sidebar reflows the map** (grid shell, ~200ms, ResizeObserver re-fit with center-stable pan correction). Eliminates the tokens-widget collision structurally: the widget rides the shrinking map edge.
2. **Collapsed-affordant** (Foundry v13 lesson): slim always-visible tab rail (~48px, part of the grid, never overlaying); optional drag-resize with rem-capped max width.
3. **Floating widgets:** owned corners of the *map cell*, positioned via `--map-inset-*`; fix layers-panel/page-chip clip with anchor positioning.
4. **Overlay stays right for transient things:** context menus, token HUDs, dice trays.
5. **2560px+:** map owns all remaining width — no canvas cap. Sidebar ~22–24rem, inner text ~65ch.
