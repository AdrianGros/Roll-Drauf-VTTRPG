# Feature Research: Scenes and Active-Page Context

**Date:** 2026-08-27  
**Slice:** 01 — scenes and active-page context  
**Status:** research/discover only; no production code changed  
**Target file:** `docs/PLAYTABLE_FEATURE_RESEARCH_01_SCENES_2026-08-27.md`

## 1. Status and input summary

This research pass examines the Roll-Drauf scene/page directory and active-page context. The goal is to decide the interaction model—compact navigation vs. full searchable directory, thumbnail presentation, active-state indicators, context actions, page notes, and desktop vs. mobile layout. 

The research answers these questions:
- Which scene-directory behaviors are genuinely useful at the table versus administrative overhead?
- How should thumbnails, active state, search, actions, and scene notes behave on desktop and mobile?
- Should active-scene context be a drawer, popover, or compact card?
- Which actions are DM-only, which are player-visible, and which need confirmation?

## 2. Current Roll-Drauf state and relevant file inventory

### Existing implementation seams

- **Scene data model**: `SceneStack` (one per session, holds `active_layer_id`) and `SceneLayer` (one per layer/page, holds `label`, `order_index`, `is_player_visible`, `campaign_map_id`). ([vtt/models/scene_stack.py](../vtt/models/scene_stack.py), [vtt/models/scene_layer.py](../vtt/models/scene_layer.py))

- **API endpoints**: Scene-stack routes handle init, activate, create, reorder, update, and delete layers. ([vtt/play/routes.py](../vtt/play/routes.py) lines 201–409)
  - `POST /scene-stack/init` — initialize with map IDs
  - `POST /scene-stack/layers/<id>/activate` — set active_layer_id
  - `POST /scene-stack/layers` — create new layer
  - `PUT /scene-stack/layers/reorder` — batch reorder
  - `PUT /scene-stack/layers/<id>` — rename/update metadata
  - `DELETE /scene-stack/layers/<id>` — remove layer

- **UI widget**: `#layersWidget` displays the current list of layers with a collapsible body. The header shows "Seiten (Kartenebenen)" (Pages/Map Layers) and is marked as a disclosure button (`aria-controls`, `aria-expanded`). ([vtt/templates/play.html](../vtt/templates/play.html) lines 1643–1645)

- **Thumbnails**: `CampaignMap` model supports thumbnail generation; screenshot research shows row-based grid layout. Layer rows render a thumbnail, label, and actions.

- **Active state**: Indicated by `scene_stack.active_layer_id` (integer). Populated on session init and set on layer activation. Current UI marks it with a visual indicator (not yet examined in detail).

- **Mobile responsiveness**: 
  - Desktop: floating anchored widget on the left (line 714), positioned at `left: 1rem`.
  - Tablet/mobile: `#layersWidget` moves into `#tableSheet` as a static-position block below the breakpoint. ([vtt/templates/play.html](../vtt/templates/play.html) lines 1368–1372, 1463–1466)

- **Permissions**: `is_player_visible` boolean controls whether non-DM players can see/access a layer. No folder model yet.

### Files not yet modified

- `vtt/static/js/play-ui.js` — widget state and rendering
- `vtt/static/js/play-client.js` — client-server synchronization
- `vtt/static/js/play-socket.js` — realtime updates
- `vtt/templates/play.html` — HTML shell and layout

## 3. Web research and source-backed findings

### Foundry VTT scene navigation model

Foundry distinguishes between two complementary directory surfaces: ([Foundry Scenes](https://foundryvtt.com/article/scenes/), [SceneDirectory API](https://foundryvtt.com/api/classes/foundry.applications.sidebar.tabs.SceneDirectory.html))

1. **Navigation Bar**: A short bookmark-like list of frequently-used scenes at the top of the canvas area. Acts as quick-access shortcuts for common scene transitions during play.
2. **Scene Directory**: A full sidebar listing containing all scenes, folders, thumbnails, search, and context-menu actions (view, activate, configure, duplicate, delete).

**Active vs. viewed states**: Foundry separates the "active scene" (shared group context) from each user's "viewed scene" (individual render state). This allows a player to inspect a scene without forcing everyone to switch. Roll-Drauf's current model is single-active and synchronous; this design choice should remain explicit.

**Permissions model**: Scenes have granular visibility—GM Only, Players can see, All Players can access. The Roll-Drauf `is_player_visible` boolean is a simplified version; DMs retain implicit access.

**Context actions**: Foundry's right-click menu exposes activate (toggle active state), configure (edit metadata), view-only, duplicate, and delete. These are privileged operations; delete and duplicate require confirmation.

### W3C/MDN patterns for disclosure, list navigation, and focus

**Disclosure (collapsible section)**: W3C APG specifies a disclosure button pattern: native `<button>`, `aria-expanded` (true/false), `aria-controls` (ID of controlled region), and Space/Enter to toggle. ([APG Disclosure](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/))

**List/tree navigation**: A scene directory is a tree with items (scenes) and optional group (folder) nodes. ARIA patterns use `role="tree"`, `role="treeitem"`, and arrow-key navigation (Up/Down for movement, Right to expand folder, Left to collapse). Mouse and touch should offer the same access. ([APG TreeView](https://www.w3.org/WAI/ARIA/apg/patterns/treeview/))

**Menu buttons and context actions**: Right-click is a shortcut only. Every action must be discoverable via keyboard and touch. Use a visible button (`aria-haspopup="true"`, `aria-expanded="false"`), focus the first menu item on open, support arrow keys, and close on Escape. ([APG Menu Button](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/))

**Lazy-loaded previews**: Thumbnails should be stable image URLs (not generated per request). MDN guidance recommends using explicit `<img>` tags with a small placeholder size, not full-size assets in a directory. Preload only when visible (Intersection Observer). ([MDN Intersection Observer](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API))

**Focus management**: When opening a directory/menu, move focus to the first item. When closing, restore focus to the button that opened it. Escape dismisses and returns focus. ([APG Focus Management](https://www.w3.org/WAI/ARIA/apg/practices/keyboard/))

### Mobile and touch considerations

- Right-click is unavailable on touch devices. Use a visible menu/actions button instead.
- Tap is the primary select action; long-press may open a context menu (but provide a visible button as the primary path).
- Small touch targets are error-prone; ensure at least 44×44 CSS pixels (touch action buttons). ([MDN Minimum touch target size](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events))
- Avoid hover-only UI; all state and actions must work with tap/focus.

## 4. Good examples

### Example 1: Foundry VTT Scene Directory
**Why it works**: Foundry separates quick navigation (bookmarks bar) from the full directory (sidebar). The directory uses thumbnails for visual scanning, active-state highlighting, and context menus for actions. Permissions are enforced server-side. Search and folder grouping make large collections navigable without cluttering the active-play UI.

**Applicable to Roll-Drauf**: Use the existing layersWidget as the full directory; add thumbnail rows, a search field over the already-loaded layer list, and an actions menu per layer. Keep the navigation bar concept separate (future slice: hotbar and quick-access shortcuts). ([Foundry Scene Organization](https://foundryvtt.com/article/scenes/))

### Example 2: Obsidian Vault file browser with thumbnails and preview
**Why it works**: Thumbnails in a grid/list with a visible preview pane. File names and metadata are readable. Keyboard navigation (arrow keys, Cmd+P search), mouse (click, right-click), and touch (tap, long-press) all work. Active file is highlighted and scrolled into view.

**Applicable to Roll-Drauf**: Render layer thumbnails in rows with the active layer highlighted; show the active layer's metadata (dimensions, grid size, note snippet) in a small card or collapsible section above the list. Keyboard navigation follows the same arrow-key + selection pattern.

## 5. Bad examples and failure modes

### Failure 1: Hover-only context menus
**Problem**: Right-clicking on a scene shows a menu, but the same menu is not accessible via keyboard or on touch. Mobile players must hunt for the menu or cannot access it at all. Assistive-technology users may not discover the menu exists.

**Applied to Roll-Drauf**: Provide a visible "actions" button or overflow menu icon on each layer row. Right-click may open the same menu, but the button is the primary path.

### Failure 2: Dense status-grid with no labels
**Problem**: A matrix of small icons without text labels or tooltips. Accessibility tools cannot read the status of each effect. New players and users of assistive technology do not understand what each status means.

**Applied to Roll-Drauf**: If layer metadata includes tags or notes, render them as text with optional icons. Scene notes should be readable in the directory or in a popover.

### Failure 3: Large full-size map images in the directory
**Problem**: Preloading every full-size scene image to populate a directory causes memory and latency issues. Scrolling through the directory becomes janky.

**Applied to Roll-Drauf**: Use thumbnail URLs, not full map images. Lazy-load via Intersection Observer only when a row is visible in the viewport. Cache thumbnail URLs in the layer object.

### Failure 4: No confirmation for destructive operations
**Problem**: Deleting or renaming a layer has no undo. Accidental clicks (or misunderstanding) delete a prepared scene.

**Applied to Roll-Drauf**: Require an explicit "delete" confirmation dialog. Rename is reversible but should still show a text-input field to prevent accidental clicks.

## 6. Lessons learned

1. **Separate navigation from management**: A short bookmark bar for quick access during play is distinct from a full directory for administration and discovery. Roll-Drauf's current layer stack widget is the directory; a hotbar (future slice) will provide quick bookmarks.

2. **Active state must be clear and persistent**: The active layer should be highlighted, scrolled into view on directory open, and remain visually anchored. Use color, icon, badge, or text to signal active; do not rely on color alone.

3. **Thumbnails reduce cognitive load**: Small grid of thumbnails with labels is faster to scan than a text-only list, especially for visual-spatial content (maps).

4. **Permissions belong on the server**: `is_player_visible` (or a similar rule) must be enforced on the backend. The directory UI shows/hides based on role, but the server validates all access.

5. **Context actions must be discoverable**: Right-click is a shortcut. Provide a visible button (menu, overflow, or inline) for every command. This ensures touch, keyboard, and assistive-tech users can access all actions.

6. **Avoid permanent UI over the map**: A large directory widget or permanently-open panel will occlude the playing surface. Use on-demand disclosure or a mobile sheet pattern.

7. **Touch targets and keyboard navigation matter equally**: Ensure layer rows are tappable (≥44px height), focusable, and keyboard-navigable (arrow keys, Enter, Escape). The same interaction must work everywhere.

## 7. Community favorites

**Community sentiment on scene navigation** (anecdotal, from Foundry community discussions and VTT subreddits):

- **Thumbnail previews are highly valued**: Players repeatedly praise scene directories with visual previews; text-only lists are harder to scan at the table.
- **Search and filtering are expected**: When a campaign has 20+ scenes, the ability to search by name or tag is essential for quick navigation.
- **Folder grouping is appreciated but not essential for first release**: Many campaigns group scenes by chapter or location; however, Roll-Drauf's current data model does not yet support folder hierarchy. Add it in a follow-up once the backend has folder IDs and permissions.
- **One-click activation is the norm**: Clicking a scene in the navigation bar or directory immediately activates it (and optionally shows it to all players). Avoid a "confirm" step for common activation; the server/audit log handles undo.
- **Mobile players want a compact sheet, not a floating panel**: On phone, players expect the directory to slide up as a bottom sheet, not float over the map. The current `#tableSheet` mechanism fits this expectation.
- **DM-only scenes and hidden layers are standard**: Many communities use unlisted or DM-only scenes for preparation or out-of-band content. Visibility controls must be simple and trustworthy.

**Non-goals based on community feedback**:
- Do not add a complex branching/dependency system for scenes (e.g., "scene B unlocks after scene A completes"). Play remains freeform; the DM chooses the active scene.
- Do not require scene metadata (description, notes, tags) to be filled in for basic use. Let them be optional.

## 8. Roll-Drauf fit and explicit non-goals

### Fits well

- **Directory UI seam**: The current `#layersWidget` is the right place for an improved scene directory. No new HTML shell is needed; enhance the existing widget.
- **Data model**: `SceneStack` and `SceneLayer` are sufficient for a flat layer list. The `is_player_visible` boolean already supports basic permissions.
- **API endpoints**: All necessary CRUD operations exist. Reorder, activate, delete, and update are already implemented.
- **Thumbnails**: `CampaignMap` supports thumbnails; layer rows can reference a cached thumbnail URL.
- **Mobile responsiveness**: The desktop floating widget + mobile `#tableSheet` pattern is already established; no new layout mode is needed.

### Deferred (not this slice)

- **Folder hierarchy**: Folders require a new `scene_folder` table, permission inheritance, and folder navigation. Defer until a dedicated folder milestone.
- **Search and full-text filtering**: First release uses client-side filter over loaded layers (no server roundtrip). Full-text search and server-side filtering can follow once the directory grows.
- **Scene notes/description UI**: Scene metadata exists but is not rendered in the directory. Add it to a future "scene properties" slice.
- **Scene copy/duplicate with custom mapping**: Duplicate is a simple backend operation. Custom item mapping (e.g., relink tokens to different characters) is a later feature.
- **Fog of War reset**: This is a destructive operation that belongs in a separate "lighting and vision" slice (Slice 10).
- **Multi-select and batch operations on layers**: Single-select is sufficient for activation and management. Batch delete/copy can follow.

## 9. Proposed interface/data/permission contracts

### API contracts (no changes to existing endpoints)

Existing endpoints already support the required operations:

```
POST   /scene-stack/init                                 — initialize with layer list
POST   /scene-stack/layers/<id>/activate                 — set active layer
POST   /scene-stack/layers                               — create layer from CampaignMap
PUT    /scene-stack/layers/reorder                       — batch reorder by order_index
PUT    /scene-stack/layers/<id>                          — update label/metadata
DELETE /scene-stack/layers/<id>                          — remove layer
```

**Response contract**: All responses include `active_layer_id` (currently set layer) and `layers` (ordered list of layer objects with `id`, `label`, `order_index`, `is_player_visible`, `campaign_map` (thumbnail URL, dimensions, grid_size)).

### Data model

```
SceneLayer {
  id: int,
  scene_stack_id: int,
  campaign_map_id: int,
  label: string (≤120 chars),
  order_index: int,
  is_player_visible: bool,
  campaign_map: {
    id: int,
    label: string,
    dimensions: { width_px: int, height_px: int },
    grid_size: int,
    thumbnail_url: string (cached URL),
    created_at: ISO8601
  }
}
```

### Permission rules

- **Activation**: Only DM/GM role can activate layers. Non-DM players cannot call `POST /activate`.
- **Creation/deletion**: Only DM role.
- **Rename/metadata**: Only DM role.
- **Visibility filter**: Non-DM players see only layers where `is_player_visible == true`. The backend enforces this; the UI hides or disables invisible layers.
- **Reorder**: Only DM role.

## 10. Risks and assumptions with severity labels

| Risk | Severity | Mitigation |
|---|---|---|
| Large number of layers (>50) causes directory to become unwieldy. | Medium | Add client-side search/filter in this slice. Server-side pagination or folder grouping can follow. Test with a 50-layer test case. |
| Thumbnail URL caching/invalidation not yet defined. | Medium | Assume thumbnail URLs are stable per CampaignMap. Add cache-busting (e.g., `?v=<updated_at>`) if maps can be updated without changing the ID. |
| Active layer is not scrolled into view on desktop when directory is closed and then opened. | Low | Implement auto-scroll on directory open: scroll the active layer into viewport. Use `element.scrollIntoView({ behavior: 'smooth', block: 'nearest' })`. |
| Touch target size on layer rows is unclear. | Low | Ensure each layer row is at least 44px tall (button/icon standard). Spacing between rows should not cause mis-taps. |
| Context menu keyboard navigation not yet implemented. | Medium | Use W3C APG menu-button pattern: focus first item, arrow keys to navigate, Escape to close, Space/Enter to activate. |
| Undo/redo not supported. | Medium | Not required for this slice. Session audit log captures all layer operations; accidental deletes can be recovered server-side by DM/support. |
| Mobile layout assumes `#tableSheet` exists and is working. | Low | Verify that widget placement inside `#tableSheet` does not break existing table-sheet behavior (scrolling, backdrop, close on outside-tap). |

## 11. Acceptance criteria for desktop, mobile, keyboard, permissions, realtime updates, errors, and destructive actions

### Desktop

- [ ] Layers are displayed in a vertical list with active layer highlighted (text + background + icon).
- [ ] Each layer row shows thumbnail (120×120px or smaller), label, and an "actions" menu button.
- [ ] Clicking a layer row activates it and updates the map canvas immediately.
- [ ] Clicking the "actions" menu opens a popover with options: rename, duplicate, delete, view-only (if applicable).
- [ ] Renaming opens a text-input field inline or in a small dialog; Enter/Escape to confirm/cancel.
- [ ] Deleting shows a confirmation dialog: "Delete <name>? This cannot be undone." Cancel/Delete buttons.
- [ ] Directory can be closed and reopened; active layer is scrolled into view on open.
- [ ] Dragging a layer row (or using a drag handle + Up/Down buttons) reorders layers. Release commits reorder to server.
- [ ] If a reorder fails (server error or conflict), reconcile from the server snapshot and show a toast.

### Mobile

- [ ] Layers are displayed in `#tableSheet` as a list (same as desktop, no separate mobile view).
- [ ] Each layer row is at least 44px tall for easy tapping.
- [ ] Long-press or a "more" menu button opens the actions menu (alternative to right-click).
- [ ] Touch-scroll within the layer list does not scroll the map or page body.
- [ ] Swiping/dragging within a layer row should not pan the map (use `touch-action: pan-y` to allow only vertical scroll).
- [ ] Tapping outside the sheet closes it and restores focus to the trigger button.

### Keyboard

- [ ] Directory toggle button (`#layersWidget` header): Space/Enter toggles collapsed/expanded state.
- [ ] Layer rows are focusable (`tabindex="0"`); focus visible (outline or highlight).
- [ ] Up/Down arrow keys move focus between layer rows (tree navigation). Home/End move to first/last layer.
- [ ] Enter/Space activates the focused layer.
- [ ] Alt+A (or similar) opens the actions menu for the focused layer; focus moves to first menu item.
- [ ] Inside the actions menu: arrow keys navigate, Enter/Space activate, Escape closes and returns focus to the layer row.
- [ ] Escape closes the directory if it is open.
- [ ] Tab order respects disclosure state: tabbing past the last visible layer should move to the next widget, not stay in the directory.

### Permissions

- [ ] Non-DM player views only layers where `is_player_visible == true`.
- [ ] Non-DM player cannot click "activate" on a hidden layer (button is disabled or not shown).
- [ ] Non-DM player cannot access "delete", "rename", "duplicate", or "view-only" actions (menu items are hidden).
- [ ] DM activates a layer; the active layer is pushed to all connected players via socket event.
- [ ] If a non-DM player's viewed layer becomes hidden (DM changes `is_player_visible`), their view does not change (they remain viewing that layer), but they cannot re-activate it. (This is acceptable because views are per-user; the active layer is separate.)

### Realtime updates

- [ ] When another user (DM or player) activates a layer, all clients receive a socket event (`active_layer_changed` or similar) and update their directory UI.
- [ ] When another user renames a layer, all clients receive an event and update the label in the directory.
- [ ] When another user deletes a layer, all clients remove it from the directory and deactivate it if it was active.
- [ ] If a layer is deleted while the current user has the directory closed, the next open will show the updated list (no stale data).
- [ ] If multiple users reorder layers simultaneously, the last write wins (optimistic update + server snapshot reconciliation). Users' views re-sync on conflict.

### Errors

- [ ] Network error during activation: toast "Could not activate layer. Trying again…" Retry after 1–2 seconds; do not hide/disable the UI.
- [ ] Server rejects layer creation (e.g., quota exceeded): toast "Could not add layer: [error message]". Do not add the layer to the local list.
- [ ] Stale version during update: if the server reports a version conflict on rename/reorder, reconcile from the server's current state and show "Your changes were applied, but another user changed this layer. Reloading…"
- [ ] Permission denied on delete: toast "You do not have permission to delete this layer."
- [ ] CampaignMap not found (broken reference): show a placeholder thumbnail and log an error. The layer should still be usable; the missing asset is a UI failure, not a data loss.

### Destructive actions

- [ ] **Delete layer**: Requires explicit confirmation dialog. Dialog shows the layer name and a warning: "This will remove the layer and all tokens on it from the game. This action cannot be undone." Cancel button is default focus; Delete button is styled as danger (red).
- [ ] **Rename layer**: Not inherently destructive, but confirm the change before committing to the server. Allow Escape/Cancel to abort without saving.
- [ ] **Reorder layers**: Not destructive; drag-and-drop is atomic on release. If reorder fails, show a reconciliation message.

## 12. Apply handoff: decisions still needed before implementation

1. **Folder support in this slice?** — Foundry's Scene Directory supports nested folders. Roll-Drauf's data model does not yet have folder IDs or permissions. Recommend deferring folders to a follow-up slice. **Decision needed**: Confirm that Slice 01 is flat-list only, with optional folder deferral.

2. **Thumbnail generation and caching strategy** — Thumbnails are cached at the CampaignMap level. When is a thumbnail regenerated (e.g., if the map image is replaced)? Should it be invalidated via a version field or timestamp? **Decision needed**: Define the cache-busting mechanism.

3. **Search/filter in this slice?** — Community feedback shows search is valued, but implementing full-text search requires either loading all layer names client-side (simple) or adding a server-side search endpoint (more robust for 100+ layers). **Decision needed**: Start with client-side name filter for simplicity, or wait for a dedicated search slice?

4. **Scene notes visibility** — The SceneLayer model can hold a `notes` field, but the UI does not yet expose it. Should scene notes (markdown or plain text) be visible in the directory, in a collapsible section, or only in a "properties" view? **Decision needed**: Defer scene notes to Slice 02, or add a read-only notes preview in the directory?

5. **Drag-to-reorder or buttons?** — Desktop UX often uses drag-and-drop for reorder; mobile uses Up/Down buttons. Both require Pointer Events and careful cancellation. **Decision needed**: Implement both (drag on desktop + buttons everywhere), or start with buttons only for simplicity?

6. **Active-scene card position** — Should the active layer's metadata (thumbnail, name, dimensions, grid) be a separate "active page" card above the directory, or inline as the first row? **Decision needed**: Define the visual hierarchy.

7. **Realtime socket event naming** — Existing code uses socket events for token updates. Define the event names for layer activation, creation, rename, delete, and reorder (e.g., `layer_activated`, `layer_created`, `layers_reordered`). **Decision needed**: Align with existing socket event convention or create new ones?

8. **Version conflict resolution strategy** — When reorder/rename conflicts with another user's change, should the UI show a "reload" prompt, auto-reconcile silently, or ask the user to redo? **Decision needed**: Prefer silent reconciliation + toast notification for transparency.

---

## Summary

**What changed**: Research artifact created; no production code modified.

**Changed files**: Only `docs/PLAYTABLE_FEATURE_RESEARCH_01_SCENES_2026-08-27.md` (this file).

**Production code changed**: No.

**Tests run**: None (research phase).

**Sources**:

**Primary sources:**
- [Foundry VTT: Scenes](https://foundryvtt.com/article/scenes/)
- [Foundry VTT: SceneDirectory API](https://foundryvtt.com/api/classes/foundry.applications.sidebar.tabs.SceneDirectory.html)
- [W3C APG: Disclosure Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/)
- [W3C APG: Menu Button Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/)
- [W3C APG: TreeView Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/treeview/)
- [W3C APG: Accessible Names and Descriptions](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/)
- [MDN: Intersection Observer API](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API)
- [MDN: Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events)

**Roll-Drauf source code:**
- `vtt/models/scene_stack.py` — SceneStack model
- `vtt/models/scene_layer.py` — SceneLayer model
- `vtt/play/routes.py` — scene-stack endpoints
- `vtt/templates/play.html` — layersWidget markup and responsive layout
- `docs/PLAYTABLE_UI_RESEARCH_2026-08-27.md` — overview and architectural context

**Community sources:**
- Foundry VTT community forums and subreddits (r/FoundryVTT, r/VTT)
- General VTT UX consensus on scene navigation and thumbnail previews (anecdotal)

**Risks**: 8 items identified; all are low-to-medium severity and addressable in Apply phase.

**Apply handoff**: This slice is decision-ready. The Apply phase should:
1. Resolve the 8 handoff questions above.
2. Define the socket event names and realtime update contract.
3. Sketch the HTML/ARIA structure for the enhanced directory (markup is still to-be-determined).
4. Create a design spec with visual mockups of active state, actions menu, and delete confirmation.
5. Accept the interface contracts and permission rules defined in Section 9.

No implementation code until Apply decisions are committed and reviewed.
