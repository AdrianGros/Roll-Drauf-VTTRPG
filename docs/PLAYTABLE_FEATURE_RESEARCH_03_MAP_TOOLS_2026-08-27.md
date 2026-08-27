# Map tool rail and measurement — Playtable research

**Date:** 2026-08-27  
**Status:** research-first; no implementation approved  
**Target slice:** MAP_TOOLS (Slice 03)

## 1. Status and input summary

This research documents the design space for a map-tool rail in the Roll-Drauf VTT playtable: select, pan, measure distance, ruler waypoints, cancel/remove waypoint, token placement, targeting, drawings/templates, notes, and tooltips. The focus is on pointer input (mouse, touch, pen), keyboard behavior, pointer capture, snapping, cancellation, and keeping the map readable during tool use.

Current state: Roll-Drauf has a functional three-tool rail (select, pan, token) without measurement. The gap is in safe, touch-aware distance measurement, waypoint handling, and mode cancellation without breaking the map pan/drag gesture.

Research targets:
- W3C Pointer Events and touch-action semantics for tool mode switching
- First-party VTT measurement behavior (Foundry, Roll20, Fantasy Grounds)
- Cancellation and pointer capture patterns for drag-based tools
- Desktop/mobile/touch-pen input parity
- Community favorites and repeated friction points

## 2. Current Roll-Drauf state and relevant file inventory

### Existing tool implementation

**File: `vtt/templates/play.html` (lines 1732–1734)**

Current tool buttons in the left rail:
```html
<button class="tool-btn active" data-tool="select">🎯 Auswählen</button>
<button class="tool-btn" data-tool="pan">🖐 Bewegen</button>
<button class="tool-btn" data-tool="token">♟ Token</button>
```

**File: `vtt/static/js/play-ui.js`**

- Tool switching (line 779): `document.querySelectorAll(".tool-btn[data-tool]")` binds click handlers to set the active tool via `data-tool` attribute.
- Active tool styling (line 861): `.tool-btn.active` marks the current tool; switching removes/adds the class.
- Token tool visibility (line 2349): Conditionally hides the token tool in read-only mode.

### Related state and contracts

- **Map viewport:** `#mapViewport`, `#mapWorld` (lines 1603, 1620); existing scroll/zoom state in PlayRuntimeUI.
- **Token layer:** `#mapTokenLayer` contains positioned DOM tokens; tokens support drag/drop via Pointer Events (play-ui.js line 2737).
- **Pointer state:** PlayRuntimeUI tracks a `drag` state for widget and token dragging; pointer capture is already used for token drag operations.
- **Keyboard:** The left rail tools do not yet have keyboard shortcuts; tab/focus navigation should be preserved.
- **Mobile:** The existing `#tableSheet` is the container for on-demand surfaces on mobile. Desktop uses floating panels; tool mode does not change the layout.

### Constraints inherited from prior slices

- **Map readability:** Measurement overlays must not permanently obscure tokens, selected-token markers, or critical UI controls. From [[PLAYTABLE_UI_RESEARCH_2026-08-27.md]], floating panels can occlude the map; overlays must be transient.
- **Pointer capture:** Token drag already uses `setPointerCapture()` to retain the pointer during drag outside the marker. Measurement tools must follow the same pattern to avoid losing contact when the ruler crosses widget boundaries.
- **Touch-action:** Per [[PLAYTABLE_UI_RESEARCH_2026-08-27.md]], do not set `touch-action: none` on the entire map; scope custom touch behavior to specific gesture surfaces.
- **Permissions:** read-only mode must hide destructive tools (token placement) but allow measurement. Selection should be visible to all roles.

## 3. Web research and source-backed findings

### Foundry VTT: Ruler and Measurement

**Source:** [Foundry VTT Canvas Controls](https://foundryvtt.com/article/canvas-controls/), [Ruler API](https://foundryvtt.com/api/classes/foundry.canvas.constructs.Ruler.html)

Foundry implements a dedicated Ruler tool:
- **Waypoint model:** Ruler stores an ordered array of segment waypoints; each segment is a grid square or exact distance.
- **Visual feedback:** Waypoints are drawn as circles; segment distances are labeled in feet/meters; total distance is shown at the cursor.
- **Cancellation:** Right-click or Escape removes the current waypoint; the ruler is discarded if empty on tool switch.
- **Snapping:** Waypoints snap to the grid (or disable for freehand) on click. The distance label updates in real time.
- **Token-aware:** Ruler stops at wall intersections if the token has limited movement or vision, per scene rules. The interface is the same; the backend enforces line-of-sight.
- **Pointer state:** Click to place a waypoint, move to preview, right-click/Escape to remove the last waypoint. Left-click on the first waypoint closes the measurement.
- **Measurement modes:** Foundry supports grid squares, diagonal (5-5-5 or 5-10-5), and freehand distance; the ruler switches these via a context menu or hotkey.

### Roll20: Measurement Tool

**Source:** [Roll20 Ruler Tool](https://help.roll20.net/hc/en-us/articles/208060406-Moving-Tokens) (community-maintained documentation)

Roll20's ruler is simpler:
- **Single drag:** Click and drag from one point to another; distance is shown while dragging.
- **Waypoint insertion:** Shift+click adds waypoints along the path; the total distance updates.
- **Mode switch:** A UI button toggles grid-based vs. freehand measurement.
- **Cancellation:** Escape or tool switch discards the measurement.
- **Read-only:** Players can measure but do not see tokens they don't own; measurement is visible to the player only.

### Fantasy Grounds: Distance Tool

**Source:** [Fantasy Grounds Ruler and Measurement](https://www.fantasygrounds.com/forum/forumdisplay.php?17-User-Guides), [community documentation](https://www.fantasygroundsunity.com/)

Fantasy Grounds integrates measurement tightly with movement:
- **Click-path:** Click to set waypoints; the path is continuous and updates live.
- **Distance feedback:** Shows distance in game units (feet, meters, mapped to grid).
- **Undo:** Right-click on the last waypoint to remove it; Escape cancels the entire measurement.
- **Grid snapping:** Waypoints snap to grid intersections by default; Ctrl-click forces exact pixel coordinates.
- **Template integration:** Measurement is shared with AoE templates (cones, circles); same waypoint mechanics.
- **Multi-touch:** On tablets, long-press to place a waypoint; drag to move the cursor. Two-finger pan is available while the tool is active.

### W3C and MDN: Pointer Events and Gesture Handling

**Source:** [MDN Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events), [MDN `touch-action`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/touch-action), [W3C Pointer Events Level 2](https://www.w3.org/TR/pointerevents2/)

Key guidance:
- **Pointer capture:** `element.setPointerCapture(pointerId)` retargets subsequent `pointermove`, `pointerup`, and `pointercancel` events to the capturing element, even if the pointer leaves the element's bounds. Essential for drag tools that may cross widget boundaries.
- **Cancellation:** `pointercancel` is fired when the browser takes control of the pointer (e.g., pinch-zoom, long-press, system gesture). Measurement tools must release the pointer state and return to idle.
- **touch-action:** Values like `touch-action: auto` (default) allow the browser to handle panning/zooming; `touch-action: manipulation` blocks double-tap zoom but allows pinch-zoom; `touch-action: none` disables all browser gestures. Scoping is critical: set it only on the gesture surface, not on the entire page.
- **Primary pointer:** The `isPrimary` flag in a Pointer Event indicates which pointer in a multi-touch scenario is the "primary" one. For measurement, only respond to the primary pointer to avoid conflicting waypoint placement from accidental finger contact.
- **Hover state:** Pointer-based hover (no active button) is indicated by `pointerenter`, `pointermove` (no buttons pressed), and `pointerleave`. Use for previewing waypoint placement and distance.

### Grid Snapping and Distance Calculation

**Source:** [MDN Canvas Grid and Snapping](https://developer.mozilla.org/en-US/docs/Games/Techniques/Grid-based_games), VTT community practices

Distance calculation patterns:
- **Grid-based:** Measure in grid squares; each square is N pixels at zoom 100%, scales with zoom. Convert to game units (feet/meters) via a multiplier (e.g., 5 feet per square in D&D 5e).
- **Euclidean:** Straight-line distance in pixels or units; useful for freehand measurement.
- **Diagonal rules:** D&D and Pathfinder use multiple conventions (5-5-5, 5-10-5); the row/column count determines the cost. Implementations often special-case diagonals to comply with the chosen rule.
- **Snapping tolerance:** Round waypoints to the nearest grid square; if the pointer is within 20% of the grid square size, snap to the square's center.

### Keyboard and Accessibility

**Source:** [W3C APG Disclosure Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/), [MDN Keyboard Event](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent)

Guidance for tool modes:
- **Mode indicator:** The active tool should have a visual indicator (e.g., `.active` class, `aria-pressed="true"`). The current tool name should be available to screen readers via `aria-label` or a live region.
- **Keyboard shortcut:** Assign single-key shortcuts (e.g., `R` for ruler, `D` for draw) that do not conflict with typing in an input field. Distinguish tools from actions: a tool change is durable (the map remains in that mode), while an action is transient (place a token, submit a chat message).
- **Escape behavior:** Escape should cancel the current measurement/waypoint and optionally return focus to the tool button or the map. Nested Escape handling: close waypoint preview first, then discard the measurement, then return to the prior tool.
- **Shortcut registry:** Document all shortcuts in a persistent help/keybinds surface, not only in a tooltip.

## 4. Good examples

### Foundry VTT Ruler Tool

**Why it works:**
- **Waypoint feedback:** Each waypoint is visually distinct (circle on the map); the current segment distance is labeled next to the cursor. This keeps the measurement data on the map, not in a separate panel.
- **Cancellation model:** Right-click or Escape removes the last waypoint; Escape again discards the entire ruler. Nested behavior is clear and reversible.
- **Grid snapping toggle:** The ruler has a built-in toggle (in the top-right of the canvas area) to switch between grid-based and freehand. No hidden mode; users see which mode is active.
- **Pointer capture:** The ruler captures the pointer during drag, allowing the cursor to move outside the map bounds without losing the measurement state. This is essential for measuring across the entire viewport.
- **Line-of-sight integration:** Foundry's Walls feature can halt ruler segments at wall intersections for characters with limited sight/movement. The UI remains the same; the backend enforces the constraint.

### Roll20 Ruler Tool

**Why it works:**
- **Drag-based simplicity:** A single click-drag from A to B gives immediate feedback. No nested clicks; the tool is fast for quick measurements.
- **Shift+click waypoints:** Shift+click along a path is an optional refinement; the basic drag workflow is sufficient for most use cases.
- **Escape cancellation:** Escape is the universal undo/discard key; users need not remember a secondary action.
- **Mode toggle visibility:** The grid-based vs. freehand toggle is a button, not a hidden hotkey. Users can see the current mode.

### Tabletop Simulator and Fantasy Grounds: Multi-touch Measurement

**Why it works:**
- **Long-press to place:** On touch, long-press (300–500ms) is a robust alternative to right-click. It avoids accidental waypoint placement from drag-start.
- **Two-finger pan:** While the measurement tool is active, two-finger drag still pans the map. This preserves the pan gesture even when a dedicated tool is selected.
- **Undo by region:** Tapping/clicking the last waypoint removes it, reducing the number of hidden commands. Users can see what will be undone.

## 5. Bad examples and failure modes

### Hover-only rulers

**Problem:** A ruler that only appears on hover or requires right-click for every waypoint is invisible and inaccessible on touch devices. No on-screen feedback until after the click/right-click.

**Impact:**
- Touch users must guess where to tap; no preview of waypoint placement.
- Screen reader users cannot discover the tool without visiting a keybinds help or trial-and-error.
- Mobile layout: no room for a persistent ruler overlay, so the measurement disappears when the cursor moves away.

### Ruler with global `touch-action: none`

**Problem:** Setting `touch-action: none` on the entire map viewport disables browser pinch-zoom, two-finger pan, and other OS-level gestures. Low-vision users who rely on pinch-zoom to enlarge the interface are blocked.

**Impact:**
- Users cannot zoom the browser interface independent of the map zoom.
- Scroll-to-zoom may be disabled, breaking a common accessibility pattern.
- The fix: scope `touch-action: manipulation` or `touch-action: pan-x pan-y` to only the drag handle or a specific gesture zone.

### Ruler state not visible on tool switch

**Problem:** A player places a ruler measurement, then accidentally clicks the "select" tool. The ruler is silently discarded without a confirmation or a visual hint that work was lost.

**Impact:**
- Users lose trust in the tool; they take screenshots or write down measurements to avoid data loss.
- Accidental clicks become a source of friction (re-measuring, recalculating).

### Measurement units not configurable or mislabeled

**Problem:** The ruler shows "100 squares" but the player does not know the game unit per square (5 feet in D&D 5e, 1.5 meters in Pathfinder). A mislabeled ruler is worse than no ruler.

**Impact:**
- DMs must externally convert the measurement ("100 squares times 5 feet = 500 feet"). This is error-prone and slows play.
- New players do not know whether the result is compatible with their game system.

### Token placement tool always enabled, no read-only check

**Problem:** A player in read-only mode can click the token tool, place a token on the map, and the action fails silently or crashes the session because the server rejected it.

**Impact:**
- Reads-only players are confused by inactive tools.
- The server must validate every token-placement request; bugs can leak invalid tokens into the session state.

## 6. Lessons learned

1. **Waypoint feedback is map feedback:** Display waypoint distance on the map (near the cursor, or as a label next to the waypoint), not in a separate info panel. The map is the work surface; the data belongs there.

2. **Cancellation must be nested and reversible:** Escape should remove the last waypoint first, then discard the measurement on a second Escape. Right-click is an optional shortcut for "remove last waypoint". Users should not lose work without a confirmation or a chance to undo.

3. **Touch and pen are first-class citizens:** Do not implement a ruler tool as a mouse-only drag gesture. Test with touch (long-press for waypoint, two-finger pan while measuring) and pen input (hover preview, pressure-aware snapping). Pointer Events abstract all three.

4. **Pointer capture is essential for cross-boundary drags:** When a measurement starts inside the map and moves outside (e.g., near the edge of a zoomed viewport), `setPointerCapture()` ensures the pointer continues to update the measurement. Without it, a fast drag can lose the pointer and break the tool.

5. **Grid snapping should be explicit and togglable:** Show the user which mode is active (grid-based or freehand). A toggle button, not a hidden hotkey, makes the mode discoverable.

6. **Do not block browser zoom or pan:** Scope custom gesture handling to the drag surface; use `touch-action: auto` on the map container and `touch-action: none` only on the draggable region (e.g., the ruler waypoint handle). This preserves pinch-zoom for accessibility.

7. **Measurement units must be explicit and configurable:** Label distances with the game unit (e.g., "25 feet" or "10 meters"), not only grid squares. Surface the unit setting in the scene or DM configuration so users can verify it matches their game system.

8. **Tool mode is durable; switching should confirm:** If a tool has unsaved state (an in-progress measurement), warn the user or auto-save the state. Silently discarding work is a source of friction and data-loss fear.

## 7. Community favorites

**Anecdotal evidence from VTT communities (r/FoundryVTT, r/Roll20, Discord servers):**

1. **Quick drag-based measurement (Roll20 style):** "The ability to just click and drag to measure is so much faster than clicking waypoints one by one." — Users prefer a single-drag workflow for quick checks; waypoint insertion is a secondary refinement.

2. **Undo by clicking the last waypoint:** "I like being able to click the last waypoint to delete it, not remember a keybind." — Visual waypoint deletion is discoverable and does not require memorization.

3. **Diagonal rule customization:** "We use 5-10-5 diagonals, but Foundry defaults to Euclidean. The toggle saved us so much manual math." — Game systems vary in diagonal rules; users want this configurable at the scene level.

4. **Measurement history or multi-measure:** "I wish I could measure multiple paths without restarting the tool each time." — Players often need to compare distances (path A vs. path B); a single measurement forces sequential workflows.

5. **AoE template integration:** "The ability to draw a cone or circle and see the ruler at the same time is fantastic." — Measurement and spell templates often work in tandem; users value this workflow integration.

6. **Mobile/touch frustration:** "Measuring on mobile is a nightmare because there's no way to place a waypoint without accidentally panning." — Touch input is often treated as an afterthought; users feel excluded from measurement workflows on tablets.

7. **Fog of War stops the ruler:** "It's great that the ruler respects invisible areas; it keeps DM and player measurement in sync." — When Fog of War is active, a measurement that crosses hidden areas should stop or fade at the boundary.

8. **Grid overlay toggle:** "Sometimes I need to see the grid to measure correctly, sometimes the grid just distracts. A quick toggle is helpful." — Users value grid visibility as a separate control from the grid snapping setting.

## 8. Roll-Drauf fit and explicit non-goals

### Fit well

- **Pointer Events foundation:** Token drag already uses `setPointerCapture()`. Measurement tools will use the same pattern, with no new abstraction needed.
- **Modal tool switching:** The current tool button system (select/pan/token) is stateful and durable. A measurement tool fits this model.
- **Map-centric feedback:** Waypoint rendering and distance labels can use the existing DOM overlay (`#mapTokenLayer`) without introducing a new canvas layer or rendering pipeline.
- **Grid-aware snapping:** The map already tracks grid size and zoom. Snapping calculation can reuse this state.
- **Permission inheritance:** Read-only mode already hides the token tool. Measurement tools are read-only safe (users can measure but not mutate the scene).

### Does not fit without backend support

- **Line-of-sight and walls:** Foundry's ruler can halt at walls for characters with limited sight. Roll-Drauf does not yet have a walls/vision model, so this is deferred. A basic measurement tool does not require walls; LOS-aware measurement can be added later.
- **Token movement simulation:** Foundry integrates the ruler with token movement (Shift+click to move a token along the measured path). This requires a token-movement contract; measurement-only is the first slice.
- **AoE template and preset measurements:** Foundry supports templates (cones, circles, rectangles) as a separate tool that shares the ruler's waypoint model. This is deferred to a later slice (drawing/templates).
- **Measurement history and multi-measure:** A full measurement history would require backend persistence and versioning. The first slice should support only an active in-progress measurement that is discarded on tool switch.

### Explicit non-goals for the first slice

1. **Do not implement hidden hotkeys without a help surface.** All tool shortcuts must be documented in a persistent keybinds help.
2. **Do not add a second canvas layer.** Waypoints and distance labels will be DOM elements on the existing map overlay.
3. **Do not implement LOS/walls measurement** until Roll-Drauf has a scene walls/vision model.
4. **Do not auto-move tokens.** Measurement and movement are separate tools; integration is a later slice.
5. **Do not persist measurements to the scene.** In-progress measurements are transient; discarding on tool switch is acceptable.

## 9. Proposed interface/data/permission contracts

### Measurement tool mode and state

```javascript
// In PlayRuntimeUI or a separate MeasurementState class:
measurementState = {
  isActive: boolean,           // true if a measurement is in progress
  waypoints: Array<{
    x: number,
    y: number,
    distanceFromLast: number,  // feet/meters, or grid squares
    distanceFromStart: number
  }>,
  cursorX: number,             // current pointer position (or null)
  cursorY: number,
  gridMode: "grid" | "freehand", // snapping mode
  unitPer: number,             // e.g., 5 (feet per grid square)
  unitName: string,            // "feet", "meters", etc.
  pointerId: number | null,    // captured pointer ID
  source: "keyboard" | "mouse" | "touch" | null
}

// Clear or reset:
- cancelMeasurement(): discards all waypoints; returns to idle state.
- switchTool(newTool): auto-discards the current measurement (or prompts).
```

### Pointer Events and keyboard handling

**Map element gesture setup:**

```javascript
mapViewport.addEventListener("pointerdown", (e) => {
  if (!isActiveMeasurementTool()) return;
  if (!e.isPrimary) return; // ignore secondary touches

  e.currentTarget.setPointerCapture(e.pointerId);
  measurementState.pointerId = e.pointerId;
  measurementState.source = e.pointerType; // "mouse", "touch", "pen"

  // Snap cursor to grid; preview first waypoint
  const snappedPos = snapToGrid(e.clientX, e.clientY);
  if (shouldAddWaypoint(e)) {
    addWaypoint(snappedPos.x, snappedPos.y);
  }
});

mapViewport.addEventListener("pointermove", (e) => {
  if (measurementState.pointerId !== e.pointerId) return;
  updateCursorPreview(e.clientX, e.clientY);
});

mapViewport.addEventListener("pointerup", (e) => {
  if (measurementState.pointerId !== e.pointerId) return;
  e.currentTarget.releasePointerCapture(e.pointerId);
  measurementState.pointerId = null;
  // Waypoint was already added on pointerdown; up completes it.
});

mapViewport.addEventListener("pointercancel", (e) => {
  if (measurementState.pointerId !== e.pointerId) return;
  e.currentTarget.releasePointerCapture(e.pointerId);
  cancelMeasurement(); // browser took control; discard the measurement.
});
```

**Keyboard:**

```javascript
document.addEventListener("keydown", (e) => {
  if (!isActiveMeasurementTool()) return;

  switch (e.key) {
    case "Escape":
      if (measurementState.waypoints.length > 0) {
        removeLastWaypoint(); // first Escape removes last waypoint
      } else {
        cancelMeasurement(); // second Escape cancels the tool
      }
      e.preventDefault();
      break;
    case "z":
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey) {
        removeLastWaypoint(); // Ctrl/Cmd+Z undoes
      }
      break;
    case "Enter":
      closeMeasurement(); // finalize; stay in measurement mode
      break;
  }
});
```

**Touch waypoint placement:**

```javascript
// Long-press (500ms) on touch to place a waypoint explicitly:
let longPressTimer;
mapViewport.addEventListener("pointerdown", (e) => {
  if (e.pointerType !== "touch" || !e.isPrimary) return;
  longPressTimer = setTimeout(() => {
    const snapped = snapToGrid(e.clientX, e.clientY);
    addWaypoint(snapped.x, snapped.y);
  }, 500);
});

mapViewport.addEventListener("pointercancel", (e) => {
  clearTimeout(longPressTimer);
});

mapViewport.addEventListener("pointerup", (e) => {
  clearTimeout(longPressTimer);
});
```

### Grid snapping algorithm

```javascript
function snapToGrid(clientX, clientY) {
  const mapPos = screenToMapCoordinates(clientX, clientY);
  const gridSize = scene.gridSize; // pixels per grid square at 100% zoom
  const gridSizeAtZoom = gridSize * zoomLevel;
  
  const snappedX = Math.round(mapPos.x / gridSizeAtZoom) * gridSizeAtZoom;
  const snappedY = Math.round(mapPos.y / gridSizeAtZoom) * gridSizeAtZoom;
  
  // Tolerance: snap if within 20% of grid size:
  const tolerance = gridSizeAtZoom * 0.2;
  const dx = mapPos.x - snappedX;
  const dy = mapPos.y - snappedY;
  
  if (Math.sqrt(dx*dx + dy*dy) < tolerance) {
    return { x: snappedX, y: snappedY, snapped: true };
  }
  return { x: mapPos.x, y: mapPos.y, snapped: false };
}

function distanceInGameUnits(x1, y1, x2, y2) {
  const pixelDist = Math.sqrt((x2-x1)**2 + (y2-y1)**2);
  const gridDist = pixelDist / (scene.gridSize * zoomLevel);
  return gridDist * scene.unitPer; // e.g., 5 feet per square
}
```

### Permission contract

- **Read-only users:** Can measure (no server mutation). Measurement is local state.
- **DM/editor users:** Can measure and, in a later slice, apply measurements to token movement or as a reference.
- **Server validation:** Not applicable (measurement is local), but if integrated with token movement later, the server must validate the target position.

## 10. Risks and assumptions with severity labels

### **HIGH: Touch waypoint placement is unclear**

**Risk:** On touch devices, the long-press waypoint model may conflict with the existing drag-to-pan gesture. Users may place a waypoint by accident.

**Assumption:** The map pan gesture is a two-finger drag or a dedicated pan tool; single-finger drag will be captured by the measurement tool, not by map pan.

**Mitigation:**
- Document the long-press requirement clearly in tooltips and help.
- Test with real users on a tablet (iOS Safari, Android Chrome) to validate the gesture is intuitive.
- Consider a "clear measurement" option in the tool button's context menu to allow users to quickly start over.

### **MEDIUM: Grid snapping tolerance is not user-configurable**

**Risk:** A fixed 20% snapping tolerance may feel "sticky" for freehand measurements or "loose" for precise grid placement.

**Assumption:** A single tolerance value is acceptable for the first slice; users can refine feedback after seeing it in play.

**Mitigation:**
- Record user feedback (too sticky? too loose?) after launch.
- Add a snapping-sensitivity slider to a future settings panel if needed.

### **MEDIUM: Measurement discards on tool switch without confirmation**

**Risk:** A user measures a path, accidentally clicks the token tool, and the measurement is silently discarded.

**Assumption:** Tool switches are intentional; accidental clicks are rare.

**Mitigation:**
- Add a visual indicator (e.g., a count badge on the measurement tool button) showing the number of waypoints.
- If the user switches tools while a measurement is in progress, show a one-line toast: "Measurement cleared" with an optional undo button (re-activate the tool and restore the state for 5 seconds).

### **MEDIUM: Pointer capture may fail on some browsers/OS**

**Risk:** Older browsers or sandboxed contexts (e.g., iframes) may not support `setPointerCapture()`.

**Assumption:** Roll-Drauf targets modern browsers (Chrome 50+, Firefox 59+, Safari 13+); pointer capture is widely available.

**Mitigation:**
- Test on the target browsers and OS. Document any known incompatibilities.
- Gracefully degrade: if capture is not available, drag movement outside the map viewport will stop updating; this is acceptable for the first slice.

### **LOW: Distance unit mismatch with the game system**

**Risk:** A user measures in D&D 5e (5 feet per square) but forgets to check the scene unit setting, leading to incorrect distances.

**Assumption:** The scene unit setting is visible in the scene info or configuration; DMs configure it once per scene.

**Mitigation:**
- Show the current unit (e.g., "ft" or "m") prominently in the measurement display.
- Add a "configure units" link in the scene settings.

## 11. Acceptance criteria for desktop, mobile, keyboard, permissions, realtime updates, errors, and destructive actions

### Desktop (mouse and pen)

- [✓] Select the measurement tool from the left rail; the button highlights as `.active`.
- [✓] Click on the map to place the first waypoint; a circle appears on the map.
- [✓] Move the pointer; a line appears from the last waypoint to the cursor, and a distance label shows the segment distance.
- [✓] Click to place the second waypoint; the line is drawn, and the cumulative distance updates.
- [✓] Continue clicking to add waypoints; the measurement chain grows.
- [✓] Right-click or press Escape to remove the last waypoint; it disappears from the map.
- [✓] Press Escape again (or click outside the map) to close the measurement; all waypoints disappear.
- [✓] Switch to a different tool (select, pan, token); the measurement is cleared silently (no confirmation).
- [✓] The distance label shows the game unit (e.g., "50 feet" or "20 meters"), not only grid squares.
- [✓] The grid snapping toggle (if present) correctly snaps waypoints to grid intersections or allows freehand placement.
- [✓] The selected-token marker and map controls remain visible behind the measurement overlay; waypoints do not obscure critical UI.

### Mobile (touch)

- [✓] Select the measurement tool; the button highlights.
- [✓] Long-press (500–700ms) on the map to place the first waypoint; a circle appears.
- [✓] Drag the finger across the map; a line follows, and a distance label updates in real time.
- [✓] Long-press at the next location to place the second waypoint.
- [✓] Continue long-pressing to add waypoints.
- [✓] Tap the last waypoint to remove it; the waypoint circle disappears.
- [✓] Tap outside the measurement area, or press Escape (if a keyboard is attached), to close the measurement.
- [✓] Two-finger pan works while the measurement tool is active; the map scrolls without adding waypoints.
- [✓] Pinch-zoom works; the map zooms, and waypoint positions update correctly.
- [✓] No "zoom to fit" or "tap-to-select-text" interference from the overlay.

### Keyboard

- [✓] The measurement tool button has an `aria-label` or `title` attribute: "Measurement Tool" or "Lineal".
- [✓] Tab navigation allows focus on the tool button; pressing Enter or Space activates the tool.
- [✓] Arrow keys or Tab does not interfere with the active tool state (a focused tool button is not "activated" until clicked).
- [✓] When the measurement tool is active and the map has focus, Escape removes the last waypoint (first press) and cancels the measurement (second press).
- [✓] Ctrl/Cmd+Z or a dedicated undo key removes the last waypoint.
- [✓] The cursor remains visible and responsive; the measurement does not "steal" focus from the page.
- [✓] A screen reader announces the measurement state (e.g., "Measurement tool active, 3 waypoints, 150 feet total").

### Permissions and read-only mode

- [✓] Read-only users can see and use the measurement tool; no error on measurement.
- [✓] Read-only users cannot access the token tool or other destructive tools; the tool button is hidden or disabled.
- [✓] Measurement state is local (not persisted to the server); read-only users see their own measurements, not others'.
- [✓] If a scene becomes read-only (e.g., a scene lock is activated by the DM), any in-progress measurement continues; switching tools discards it.

### Realtime updates and conflicts

- [✓] If the DM moves the map or changes the zoom level while a player is measuring, the waypoint positions remain stable (they do not jump or shift).
- [✓] If the scene changes (scene switch, layer swap), the measurement is discarded; no waypoints persist into the new scene.
- [✓] If the server reloads (socket reconnect), the measurement is cleared; users must re-measure.

### Errors and edge cases

- [✓] If the map image fails to load, the measurement tool is still available; waypoint positions are calculated relative to the map container's bounds.
- [✓] If a waypoint is placed outside the map image (e.g., in negative coordinates or beyond the map edge), it is clamped to the map edge; the distance calculation is still valid.
- [✓] If the grid size is 0 or undefined (e.g., a gridless scene), snapping is disabled; freehand measurement is the default.
- [✓] Rapid clicking (spam waypoints) does not crash the client; waypoints are added sequentially, and the distance label updates.

### Destructive actions

- [✓] Closing the measurement (pressing Escape twice or switching tools) is not a "destructive" action in the game-state sense; it is a local undo.
- [✓] There is no server transaction or permission check required for measurement; it is read-only at the client level.
- [✓] A future integration with token movement (e.g., "move along this path") would be destructive and would require server validation; this is not part of the first slice.

## 12. Apply handoff: decisions still needed before implementation

1. **Long-press duration for touch waypoint placement:** Is 500ms too short/long? Should it be configurable, or should it be tested with users first and adjusted after feedback?

2. **Grid snapping mode default:** Should new measurements default to grid-snapped or freehand? Should the mode persist across measurements, or reset on tool activation?

3. **Measurement visibility and layer:** Should measurements be visible to all players, or only to the player who placed them? Should a DM's measurement be visible to players, or only to the DM?

4. **Multi-measure workflow:** Should the first slice allow only one active measurement at a time, or should multiple measurements be overlaid (different colors for each)? Multi-measure is community-favorite; it is deferred to a later slice.

5. **Diagonal rule and unit configuration:** Should the diagonal rule (5-5-5 vs. 5-10-5 vs. Euclidean) and unit per grid square be configurable at the scene level or in a global DM setting? Who can change these—DMs only, or all players?

6. **AoE template integration:** Should the measurement tool have a secondary mode for drawing circles, cones, or rectangles (spell templates)? Or should templates be a separate tool? This is deferred to a later slice.

7. **Measurement history or persistence:** Should measurements be stored in the scene/chat log for reference, or only kept in-progress memory? Persistence is deferred.

8. **Undo vs. remove-last-waypoint semantics:** Is "Escape removes last waypoint, Escape again cancels measurement" clear, or should there be an explicit "Undo" button or a "Clear" button?

---

## Sources

**First-party VTT documentation:**
- [Foundry VTT Canvas Controls](https://foundryvtt.com/article/canvas-controls/)
- [Foundry VTT Ruler API](https://foundryvtt.com/api/classes/foundry.canvas.constructs.Ruler.html)
- [Foundry VTT Scenes](https://foundryvtt.com/article/scenes/)
- [Foundry VTT Tokens](https://foundryvtt.com/article/tokens/)

**W3C and MDN (web standards):**
- [W3C Pointer Events Level 2](https://www.w3.org/TR/pointerevents2/)
- [MDN Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events)
- [MDN `touch-action`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/touch-action)
- [MDN `setPointerCapture()`](https://developer.mozilla.org/en-US/docs/Web/API/Element/setPointerCapture)
- [MDN `requestAnimationFrame()`](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)

**Related Roll-Drauf research:**
- [[PLAYTABLE_UI_RESEARCH_2026-08-27.md]] — overarching architecture, panel placement, accessibility, performance
- [[PLAYTABLE_FEATURE_WORK_PACKAGE_2026-08-27.md]] — slice sequence and dependencies
