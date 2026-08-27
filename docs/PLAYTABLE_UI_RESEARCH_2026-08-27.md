# Playtable UI research — scene directory, token HUD, and status controls

**Date:** 2026-08-27  
**Scope:** Roll-Drauf VTT playtable; advisory only, no production code changed  
**Sources:** first-party Foundry VTT documentation/API, W3C ARIA Authoring Practices Guide, and MDN Web API/CSS documentation  
**Inputs:** the six attached UI screenshots plus a read-only inspection of the current repository

## Executive recommendation

Adopt the interaction ideas, not the entire Foundry UI:

1. Keep the map as the primary surface and make the selected token the primary context.
2. Turn the existing pages widget into a real scene/page directory with thumbnails, active state, search, and an actions menu.
3. Turn the existing token widget into a compact token HUD: quick resources and actions near the selected token on desktop, an accessible bottom sheet on mobile.
4. Represent statuses as explicit toggles with a clear “applied” state. Do not keep a count-only badge as the main status UI.
5. Use one overlay state model and one server-backed source of truth. Do not add a second canvas renderer or duplicate controls in every surface.

Foundry’s own model separates scene navigation/directory, canvas controls, and a selected-token HUD. Its scene documentation describes the navigation bar as a short list of commonly used scenes while the full scene directory contains the rest and exposes context actions such as view, activate, configure, duplicate, and delete. Its Token HUD is explicitly intended for quick changes to resources and status effects. ([Scenes](https://foundryvtt.com/article/scenes/), [Tokens](https://foundryvtt.com/article/tokens/), [SceneDirectory API](https://foundryvtt.com/api/classes/foundry.applications.sidebar.tabs.SceneDirectory.html), [TokenHUD API](https://foundryvtt.com/api/classes/foundry.applications.hud.TokenHUD.html))

## 1. Patterns derived from the screenshots

These are observations from the attached screenshots, not claims about the source products.

| Screenshot pattern | Interaction value | Adaptation for Roll-Drauf |
|---|---|---|
| Tall scene browser with folders, search, thumbnails, and a compact action cluster | Makes a large collection scannable while keeping the current scene obvious | Use a “Seiten” directory with thumbnail rows, active-page styling, search, and a per-page overflow menu. Keep folder grouping optional until the data model supports folders. |
| Token HUD attached to the selected token | Keeps the next useful action close to the object being manipulated | Show a small anchored HUD for name, HP, initiative/combat state, character sheet, and “more”. Move the full editor to a sheet/drawer. |
| Action menu opened from a token HUD | Prevents the map from being covered by every possible control | Put infrequent actions—rename, image, delete, target, display in chat—behind one menu. Use a menu only for commands, not for persistent status toggles. |
| Portrait/stat sheet overlay | Gives the player a high-information inspection mode without abandoning the table | Reuse the existing character-sheet drawer/iframe as the full inspection surface; make its entry point part of the HUD. |
| Dense status-effect matrix with “clear all” | Makes many conditions visible at once and makes cleanup fast | Use a searchable or grouped status picker with applied states, labels, and “clear all”. Start with the project’s current condition vocabulary, not Foundry’s full catalog. |
| Vertical quick-control rail beside a token and resource pills | Exposes frequent actions without requiring a large modal | Use at most 3–5 high-frequency controls: select, sheet, HP, conditions, and more. On touch, a tap opens the same controls in a bottom sheet rather than relying on hover or right-click. |

The screenshots also show a useful visual rule: the map remains readable behind contextual UI. The dense directory and status grid are intentionally secondary surfaces, while the selected token remains visually anchored. That rule fits Roll-Drauf better than copying the screenshots’ exact dark palette or icon density.

### Follow-up screenshots: hotbars, chat, and loot transfer

The additional screenshots add three related but distinct surfaces:

| Pattern | What it is good for | Roll-Drauf fit |
|---|---|---|
| Multi-row numbered hotbar | Repeatable actions with visible keyboard slots and page switching | Add a compact personal action bar below the map or above the mobile sheet. Populate it from the existing action catalog first; reserve drag/drop customization for a later action-definition milestone. |
| Compact chat/dice dock | Fast message entry and immediate visibility of public/private rolls | Keep chat in the existing sidebar, but add a compact dock trigger with message input, roll mode, and a link to the full log. Treat private GM rolls as visibility-scoped events, not merely styled chat text. |
| Roll composer controls | Quick die presets, modifier changes, advantage/disadvantage, and roll visibility | Use a progressively expandable composer: message/formula input, common die buttons, modifier stepper, one explicit ADV/DIS toggle, and a labeled roll-visibility control. Keep the selected mode visible in text, not only by icon color. |
| Escape/application menu | A single exit point for session navigation and application-level commands | Add a separate Escape/Menu button that opens a small command menu. Keep “return to campaign”, “leave session”, help/shortcuts, and settings there; do not mix it with the workspace sidebar or token actions. |
| Actor/creature focus sheet | High-information inspection of a player character or monster | Reuse the character-sheet drawer, but define separate player/creature sections for stats, proficiencies, immunities, resistances, languages, actions, legendary actions, and limited-use resources. Keep this out of the always-visible token HUD. |
| Active-scene card | Gives context for the current map without occupying the map permanently | Show the active page thumbnail, title, dimensions/grid, and notes at the top of the page directory or as an optional scene-info drawer. Reuse the current map metadata surface. |
| Darkness/vision overlay | Makes token sight and light state visible during play | Treat this as a separate map capability, not a CSS treatment. It needs scene walls, light sources, vision rules, and permission-aware server data; defer it until that model exists. |
| Fog of War reset | Resets exploration for every player in the active scene | Put it in a DM-only lighting/map-tools group with a strong warning and confirmation. It must announce that all players are affected and invalidate/reload exploration state after the server confirms the reset. |
| “Transfer loot from selected token(s)” | A batch operation over one or more selected tokens | Add this as a contextual action in the token action menu, not as an always-visible rail button. It requires multi-selection and a real loot/container contract; the current single `selectedTokenId` state and character inventory CRUD are not enough. |

Foundry’s hotbar is a useful model for the first surface: it gives users ten numbered slots, multiple pages, and keyboard shortcuts, while keeping the directory/configuration work separate. Its chat model similarly treats chat messages and dice rolls as one readable log with explicit public, GM, blind, and self visibility modes. ([Macro Hotbar](https://foundryvtt.com/article/macros/), [Chat Messages](https://foundryvtt.com/article/chat/), [Basic Dice](https://foundryvtt.com/article/dice/))

The roll composer should keep three independent values rather than folding them into one button state:

```text
formula/die  +  modifier  +  advantage state  +  visibility mode
  d20             +5            normal             public
```

`ADV`/`DIS` is a roll modifier, while Public/Private GM/Blind/Self is a visibility rule. The server event must carry both. Enter should submit a normal message or roll; Shift+Enter should remain available for a multiline message. Foundry documents the same separation between chat messages, roll modes, and roll expansion. ([Chat Messages](https://foundryvtt.com/article/chat/), [Basic Dice](https://foundryvtt.com/article/dice/))

The Escape menu should remain a separate application command surface. The current `btnBack` returns to the campaign view and `btnSidebarToggle` opens Journal/Chat/Tools/Session, so one of those should not be overloaded to do both jobs. The Fog of War screenshot is a different class again: Foundry describes reset as affecting all users in the scene, and its lighting system depends on walls and vision state. That makes it a privileged, server-confirmed map operation with a confirmation step—not a normal toggle. ([Foundry Lighting](https://foundryvtt.com/article/lighting/), [Foundry Scenes](https://foundryvtt.com/article/scenes/), [Foundry Walls](https://foundryvtt.com/article/walls/))

The loot button implies this interaction sequence:

```text
select one or more source tokens
  → open token actions
  → Transfer loot
  → choose recipient / shared party stash
  → review item and quantity diff
  → confirm one server transaction
  → broadcast inventory + audit event
```

Do not implement this by directly editing a character’s inventory from the browser. A transfer must validate source ownership/permissions, recipient eligibility, quantities, stack behavior, and conflicts atomically on the server. The current `InventoryItem` model is character-owned and supports CRUD, but there is no token loot container or transfer endpoint yet.

## 2. Current Roll-Drauf table: what fits and what does not

### Current implementation seams

The `/play` template is already structured around a map-first table:

- `#mapViewport` scrolls the world; `#mapWorld` contains the map image, grid, and `#mapTokenLayer` DOM overlay. This current playtable surface is an image plus positioned DOM elements, not a new `<canvas>` layer. ([play.html](../vtt/templates/play.html#L1603))
- `#layersWidget`, `#turnOrderWidget`, `#tokenWidget`, and `#tokenCreatePanel` are existing floating panels. ([play.html](../vtt/templates/play.html#L1615))
- The left rail already provides select, pan, token, table, menu, and back controls; the right sidebar already contains Journal, Chat, Tools, and Session surfaces. ([play.html](../vtt/templates/play.html#L1729))
- Mobile already has `#tableSheet` and a backdrop for moving table panels into a sheet; the character sheet already has `#sheetDrawer`. ([play.html](../vtt/templates/play.html#L1597), [play.html](../vtt/templates/play.html#L1874))
- `PlayRuntimeUI` already has a selected-token state, server/API clients, zoom/pan state, widget drag state, and a token index. ([play-ui.js](../vtt/static/js/play-ui.js#L40))
- Token selection already reveals the token widget, and token dragging already uses Pointer Events and pointer capture. ([play-ui.js](../vtt/static/js/play-ui.js#L881), [play-ui.js](../vtt/static/js/play-ui.js#L2737))
- Current statuses are only a `metadata_json.conditions` array. The map renders a numeric badge and the token list renders a text line; the table does not yet provide an explicit status picker. ([play-ui.js](../vtt/static/js/play-ui.js#L2437), [play-ui.js](../vtt/static/js/play-ui.js#L2266))

### Fits well

| Foundry-inspired idea | Why it fits |
|---|---|
| Directory separate from the map | The current layer list already has ordered pages, thumbnails, active state, activation, rename, delete, and add/copy flows. It is the right seam for a better directory. |
| Contextual token HUD | Token selection and `#tokenWidget` already exist. The work is primarily presentation, focus, and status modeling rather than a new navigation system. |
| Quick resource controls | HP inputs and character-sheet linkage already exist in the selected-token detail. The HUD can expose them without changing the map coordinate model. |
| Full inspection drawer | `#sheetDrawer` already provides an in-table character-sheet surface. The screenshot’s full-screen sheet should be a responsive presentation of that existing capability. |
| Desktop floating panels plus mobile sheet | The repository already switches widget placement below the mobile breakpoint. Preserve that responsive distinction instead of forcing one layout everywhere. |

### Does not fit without adjustment

- A permanently open, multi-column control wall would repeat the earlier failure mode: floating panels can obscure the map and selected tokens. The table’s map is the work surface; directories and editors must be on demand.
- Right-click-only actions do not cover touch, keyboard, pen, or assistive technology. Keep right-click as an optional shortcut, but provide a visible button and a keyboard path for every command.
- Foundry’s complete scene/document/folder model is larger than the current Roll-Drauf layer model. Do not invent folder persistence in the UI. Use local grouping or defer folders until the backend has stable folder IDs and permissions.
- A status grid copied literally from the screenshot would be too dense and would expose labels without a defined Roll-Drauf status contract. First normalize each status to an ID, label, icon, active state, and optional value/duration.
- A HUD rendered by hover would disappear on touch and is fragile when the map is zoomed. Use selection as the durable trigger and re-anchor on viewport/zoom changes.

## 3. Recommended information architecture

```text
Playtable
├── Persistent: session/status strip
├── Persistent: map viewport
│   ├── map/grid
│   ├── token markers
│   └── selected-token affordance
├── Primary tools: select, pan, place token, table, workspace sidebar, escape menu
├── Active-page context (inside page directory)
│   ├── thumbnail/title/grid metadata
│   └── optional notes and scene controls
├── Page directory (on demand)
│   ├── search and active page
│   ├── page thumbnail/list
│   └── page actions menu
├── Selected-token HUD (on selection)
│   ├── name/type/HP/combat summary
│   ├── 3–5 quick actions
│   └── more menu → editor, conditions, image, delete, loot transfer, chat
├── Personal action bar
│   ├── numbered quick-action slots
│   ├── optional pages
│   └── action directory/configuration
├── Token editor (responsive sheet/dialog)
│   ├── overview/resources
│   ├── actions
│   ├── conditions
│   └── character sheet
└── Existing workspace drawer
    ├── journal
    ├── chat
    ├── tools/dice
    └── session
```

Desktop should use an anchored directory/HUD where there is room, with collision avoidance against the right sidebar and viewport edges. Mobile should use the existing table sheet/bottom-sheet mechanism for directories and editors. The selected token should retain a visible ring/label even when its HUD is closed.

The existing sidebar tabs should be promoted to a real tabs pattern if they remain tabs: a `tablist`, `tab` elements with `aria-selected`/`aria-controls`, and `tabpanel` elements with reciprocal labels. The W3C APG specifies this relationship and arrow-key behavior for horizontal tabs. ([Tabs Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/))

## 4. Interaction and state model

Use one table interaction state rather than independent booleans scattered across widgets:

```text
tableState = {
  selectedTokenIds,
  openSurface: null | "pages" | "token-hud" | "token-editor" | "status-picker" | "sheet" | "sidebar" | "app-menu",
  openMenu: null | "page-actions" | "token-actions",
  returnFocusId,
  viewport: { zoom, scrollLeft, scrollTop },
  drag: null | { kind, pointerId, id },
  permissions: { readOnly, role },
  serverVersions: { tokenId: version, layerId: version }
}
```

Suggested transitions:

| Event | Result |
|---|---|
| Select/tap token | Set the focused token in `selectedTokenIds`, update the marker, open or focus the token HUD, and reveal its controls. |
| Ctrl/Cmd-click or a selection modifier | Add/remove a token from `selectedTokenIds`; show a count and enable only batch-safe actions. |
| Keyboard focus on token proxy | Use Enter/Space for the same selection action; do not require a pointer-only canvas hit test. |
| HUD “conditions” | Open a non-modal status popover on desktop or the status section of the mobile editor. |
| HUD “more” | Open an action menu and move focus to its first item. |
| Loot transfer | Require at least one valid source and an explicit recipient; open a review surface, then commit one server-side transaction. |
| Page trigger | Open the page directory; preserve active page and current focus. |
| Escape/Menu button | Open the application command menu and focus its first command. Keep it distinct from the workspace sidebar. |
| Escape | Close the topmost menu/popover/sheet; restore focus to its invoker. |
| Outside click/tap | Light-dismiss a non-modal popover; do not silently discard an editor draft. |
| Drag token/widget | Capture the pointer, update only visual position during movement, and commit once on release. |
| Server conflict/error | Reconcile from the newest snapshot and announce a concise error; never leave the HUD showing an unconfirmed value. |

Use a real menu only for a list of commands. The W3C menu-button pattern requires `aria-haspopup`, `aria-expanded`, focus moving to the first menu item on Enter/Space, and menu keyboard behavior after opening. ([Menu Button Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/))

Use disclosure semantics for expandable widget bodies: a native button, `aria-expanded`, and `aria-controls`. That is the APG model for show/hide sections and maps directly to the current collapsible widgets. ([Disclosure Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/))

For statuses, model the picker as a labeled group of native checkboxes or equivalent toggle buttons, not a command menu. A status toggle must expose its current state, have a persistent accessible name, and support Space. The APG checkbox pattern explicitly defines the checked state, label, group, and Space-key behavior. ([Checkbox Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/checkbox/))

## 5. Technical implementation sequence

### Phase 1 — contract and surface inventory

1. Freeze the existing API contracts for layers, tokens, combat, character sheet, permissions, and Beyond20 condition updates.
2. Define a small status schema: `id`, `label`, `icon`, `active`, optional `value`, optional `duration`, and source/permission metadata.
3. Decide whether statuses remain in `metadata_json` for the first slice or receive a dedicated API field. If they remain there, validate the shape server-side and preserve optimistic-concurrency/version checks.
4. Add interaction contracts for keyboard, touch, read-only mode, hidden tokens, and conflict rollback before visual changes.

### Phase 2 — page directory vertical slice

1. Refactor the current layers widget into a semantic directory shell while keeping the existing layer endpoints.
2. Render thumbnail rows with active state, page label, and a single actions menu. Keep the upload/copy flow as the primary “add page” action.
3. Add search/filter only over data already loaded; use thumbnail URLs, not full map images. Foundry’s Scene directory and scene docs support the split between a short navigation list and a fuller directory, including thumbnails and context actions. ([Scenes](https://foundryvtt.com/article/scenes/), [SceneDirectory API](https://foundryvtt.com/api/classes/foundry.applications.sidebar.tabs.SceneDirectory.html))
4. Use the desktop anchored surface and the existing mobile table sheet; do not create a second layer stack.

### Phase 3 — selected-token HUD vertical slice

1. Keep `selectedTokenIds` as the source of truth and render one primary HUD from the focused token, plus a compact selection count for batch operations.
2. Show name, type, HP, initiative/combat state, and status summary; expose sheet, HP, conditions, and more as the initial actions.
3. Place the HUD using `transform`/coordinates derived from the marker, then clamp it against the viewport, the map edge, and the open sidebar. Reposition on selection, zoom, scroll, resize, and map activation.
4. Keep the full editor in the existing sheet/drawer. The Foundry Token HUD documentation supports this division: quick resource/status changes in the HUD, deeper data in the actor/sheet surfaces. ([Tokens](https://foundryvtt.com/article/tokens/), [TokenHUD API](https://foundryvtt.com/api/classes/foundry.applications.hud.TokenHUD.html))

### Phase 3b — personal action bar and chat/dice dock

1. Render a single row of numbered quick-action slots from `action_catalog`; keep the existing action executor as the server boundary.
2. Add page switching only after slot persistence has a defined ownership model. The first slice can use stable built-in slots rather than inventing macro CRUD.
3. Keep the full chat log in the sidebar, but expose a compact dock trigger for message entry and roll mode. Public, GM, blind, and self rolls must remain distinct in the event payload and visibility filter.
4. Ensure hotbar keyboard shortcuts never fire while focus is inside an input, select, dialog, or chat composer.

### Phase 4 — status picker and realtime reconciliation

1. Render status icons on the token from the normalized status data, with text alternatives and an applied-state indicator.
2. Add toggle, clear-one, and clear-all operations. Keep the picker grouped/searchable if the catalog grows beyond a small set.
3. Persist status changes through the same server-authoritative update/realtime path as HP and token movement, with role checks and version conflict handling.
4. Use Foundry’s concept only as an information-architecture reference: status effects are system-defined, appear as token overlays, and can be toggled through a Token HUD; Roll-Drauf should own its own vocabulary and rules. ([Active Effects](https://foundryvtt.com/article/active-effects/), [TokenDocument API](https://foundryvtt.com/api/classes/foundry.documents.TokenDocument.html), [Status effect configuration](https://foundryvtt.com/api/interfaces/CONFIG._StatusEffectConfig.html))

### Phase 5 — loot transfer foundation

1. Add a session-facing loot/container model or an explicit token-to-container relation; do not overload character-owned `InventoryItem` rows.
2. Add a server-side transfer command that accepts source token IDs, a recipient character/stash ID, item IDs, quantities, and an idempotency key.
3. Validate permissions, source availability, positive quantities, stack rules, and stale versions inside one transaction. Return the committed diff and broadcast it to the session.
4. Build the review dialog only after the command contract exists. The UI should show “from”, “to”, each quantity delta, and the resulting inventory state before confirmation.

### Phase 6 — responsive and acceptance pass

1. Desktop: verify collision avoidance and that the HUD never hides the selected token or critical map controls.
2. Touch: verify tap selection, long-press/right-click alternatives, drag cancellation, and the bottom-sheet workflow.
3. Keyboard/screen reader: verify every directory row, menu item, status toggle, editor field, and close path.
4. Re-test DM/player visibility, read-only mode, stale versions, socket reconnect, and opening the character sheet without leaving the table.

## 6. Accessibility constraints

- Prefer native `button`, `input`, `select`, `dialog`, and `label` elements. The APG names-and-descriptions guidance says all focusable interactive elements need an accessible name and recommends visible text/native HTML techniques over placeholder/title fallbacks. ([Providing Accessible Names and Descriptions](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/))
- For a blocking editor, prefer native `<dialog>.showModal()` or an equivalent implementation that makes the underlying page inert, contains the tab sequence, closes on Escape, includes a visible close/cancel control, and restores focus. Those are the W3C modal-dialog requirements; MDN also documents the native modal behavior and `::backdrop`. ([Dialog Modal Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/), [MDN `<dialog>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog))
- Use the Popover API only for non-modal contextual surfaces such as the page actions or token actions menu. MDN explicitly states that Popover API popovers are non-modal; use a dialog for a modal editor. Declarative invoker relationships also provide focus-order and ARIA behavior, but feature-detect the API and keep a class-based fallback for older browsers. ([Popover API](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API), [Using the Popover API](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API/Using))
- Do not make a whole map or page `touch-action: none`. MDN notes that it disables native panning/zooming and can inhibit browser zoom needed by low-vision users. Scope custom touch behavior to the map gesture surface or drag handle, keep browser/page zoom available, and retain explicit keyboard zoom controls. ([MDN `touch-action`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/touch-action))
- Use Pointer Events for mouse, touch, and pen. On token/widget drag, capture the active pointer and release it on `pointerup`/`pointercancel`; MDN describes pointer capture as retargeting later events to the chosen element, which prevents a drag from losing contact when the pointer leaves the marker. ([MDN Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events), [`setPointerCapture()`](https://developer.mozilla.org/en-US/docs/Web/API/Element/setPointerCapture))
- Keep selected-token state visible without relying on color alone. Use name, icon/shape, ring, and text status. Every icon-only action needs a visible tooltip plus an accessible name; tooltips must not be the only way to understand the action.
- Respect `prefers-reduced-motion`, avoid focus jumps during zoom, and ensure the mobile sheet can scroll independently without trapping focus behind the backdrop.

## 7. Performance constraints

- Keep the map art and token marker layer as the existing DOM surface. Render the HUD as a small DOM overlay; do not redraw the full map or rebuild all controls for every pointer move.
- Coalesce drag/re-anchor writes into `requestAnimationFrame`, and update transforms rather than layout-heavy `top/left` where possible. MDN defines `requestAnimationFrame()` as a callback before the next repaint and notes that it is paused in background tabs, making it the appropriate scheduling boundary for visual movement. ([MDN `requestAnimationFrame()`](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame))
- Use `ResizeObserver` on the map viewport, sidebar, and HUD anchor container so the overlay is repositioned only when geometry changes, rather than polling. ([MDN `ResizeObserver`](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver))
- Directory rows should use thumbnails and lazy loading; never preload every full-size map solely to populate the directory. A separate preview URL is already consistent with the current layer-row thumbnail approach.
- Avoid permanent `backdrop-filter`/large blur effects over the map. Prefer opaque/translucent panels with a modest shadow; reduce expensive effects on mobile.
- Do not attach duplicate global `pointermove`, `pointerup`, resize, or keydown listeners when panels re-render. Delegate from a stable table root or clean up listeners with the panel lifecycle.
- Measure the real bottlenecks before optimizing: frame time while dragging at 100%, 200%, and 300% zoom; DOM node count with 25/100/250 tokens; thumbnail load cost; and time-to-interactive after opening a large page directory.

## 8. Definition of done for the first implementation slice

- A DM can find and activate a page from a searchable thumbnail directory without covering the entire map permanently.
- Selecting a token exposes its name, HP/combat state, character-sheet link, conditions, and a clearly labeled actions menu.
- Statuses can be applied, removed, and cleared with explicit state, realtime reconciliation, and read-only/permission handling.
- The same actions work by mouse, touch, keyboard, and screen reader; Escape and outside dismissal behave predictably.
- Desktop and phone layouts use the same state and commands, with anchored popovers on desktop and the existing sheet/drawer pattern on mobile.
- Dragging remains smooth, does not lose the pointer, and does not trigger accidental widget collapse or command activation.
- No full-size scene assets are loaded just to render the directory, and no overlay update requires rebuilding the complete map.

## Primary source register

- Foundry VTT: [Scenes](https://foundryvtt.com/article/scenes/), [Tokens](https://foundryvtt.com/article/tokens/), [Active Effects](https://foundryvtt.com/article/active-effects/), [Player Orientation](https://foundryvtt.com/article/player-orientation/), [SceneDirectory API v14](https://foundryvtt.com/api/classes/foundry.applications.sidebar.tabs.SceneDirectory.html), [TokenHUD API v14](https://foundryvtt.com/api/classes/foundry.applications.hud.TokenHUD.html), [TokenDocument API v14](https://foundryvtt.com/api/classes/foundry.documents.TokenDocument.html), [status-effect configuration API](https://foundryvtt.com/api/interfaces/CONFIG._StatusEffectConfig.html)
- W3C WAI-ARIA APG: [Menu Button](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/), [Dialog Modal](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/), [Disclosure](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/), [Tabs](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/), [Checkbox](https://www.w3.org/WAI/ARIA/apg/patterns/checkbox/), [Accessible Names and Descriptions](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/)
- MDN: [Popover API](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API), [Using the Popover API](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API/Using), [`<dialog>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog), [Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events), [`setPointerCapture()`](https://developer.mozilla.org/en-US/docs/Web/API/Element/setPointerCapture), [`touch-action`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/touch-action), [`requestAnimationFrame()`](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame), [ResizeObserver](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver)
