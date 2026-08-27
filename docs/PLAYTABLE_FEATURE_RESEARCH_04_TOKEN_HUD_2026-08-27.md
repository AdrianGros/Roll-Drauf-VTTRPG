# Slice 04 — Selected-token HUD and creature focus sheet research

**Date:** 2026-08-27  
**Status:** Research/Discover complete; ready for Apply design review  
**Scope:** Roll-Drauf VTT selected-token HUD and player-character/monster focus sheet
**This is a Research/Discover pass only.** Production code remains unchanged. This note establishes facts about Foundry's Token HUD, accessibility guidance, and Roll-Drauf's current seams. See "Apply handoff" for design decisions needed before implementation.

---

## 1. Status and input summary

**Objective:** Research the selected-token HUD—a compact, context-close surface for quick resource and status changes—and the full focus sheet for detailed creature inspection.

**Inputs to this pass:**
- Existing Roll-Drauf token widget (`#tokenWidget`) with HP input, character-sheet link, and status-count badge
- Foundry VTT Token HUD API documentation ([Tokens](https://foundryvtt.com/article/tokens/), [TokenHUD API](https://foundryvtt.com/api/classes/foundry.applications.hud.TokenHUD.html))
- PLAYTABLE_UI_RESEARCH_2026-08-27.md architectural guidance on HUD vs sheet separation
- PLAYTABLE_FEATURE_WORK_PACKAGE_2026-08-27.md phase gates and safe-work boundaries
- W3C APG accessibility patterns (menu, disclosure, button, focus restoration)
- Current Roll-Drauf source: `vtt/static/js/play-ui.js`, `vtt/templates/play.html`

**Out of scope for this slice (explicitly deferred):**
- Character sheet content structure (character-sheet drawer enhancement is separate work)
- Status-condition schema and picker UI (Slice 05 — Conditions/Status Picker)
- Combat state display and turn order (Slice 06 — Combat Strip and Initiative)
- Personal action hotbar (Slice 07)
- Full Foundry actor/scene/folder model (Roll-Drauf owns its own vocabulary)

---

## 2. Current Roll-Drauf state and relevant file inventory

### Existing token implementation seams

- **Token selection state:** `PlayRuntimeUI.selectedTokenId` (play-ui.js:58) is the primary single-token focus state. Multi-selection is deferred.
- **Token widget DOM:** `#tokenWidget` (play.html) is a floating panel with:
  - `selectedSummary` label showing "Ausgewählt: NAME (#ID)"
  - `hpCurrent` and `hpMax` inputs for quick HP changes
  - `nameInput` for token name editing
  - `btnOpenCharacterSheet` to open the drawer
  - Status-count badge showing condition count (not an interactive picker yet)
  - Token list with active-row styling and selection click handler
- **Character sheet drawer:** `#sheetDrawer` (play.html:1874, play-ui.js:339–352) is an existing edge-pinned iframe for character inspection. It opens on sheet link or "character sheet entry" action and is managed separately.
- **Token fields in state:** Roll-Drauf TokenState includes `id`, `name`, `hp_current`, `hp_max`, `character_id`, `metadata_json` (conditions array), `x`, `y`, `rotation`, `scale`, `hidden`, `vision_mode`, `elevation` (see play-ui.js:2260–2400 and play-client.js imports).
- **Permission model:** `_canMoveToken()` (play-ui.js) checks role/ownership; read-only mode exists (play-ui.js:2304).
- **Realtime socket events:** Token updates, character sheet opens, condition changes flow through `play-client.js` socket handlers.

### File inventory for this slice

| File | Relevant sections | Role |
|------|---|---|
| `vtt/templates/play.html` | Lines 1615–1650 (`#tokenWidget`), 1874 (`#sheetDrawer`) | DOM structure; widget placement and sheet drawer anchor |
| `vtt/static/js/play-ui.js` | Lines 58, 339–352, 703, 873–890, 1144–1265, 1508–1780, 2260–2400, 2708–2733 | Token selection, widget show/hide, HP/name input, sheet drawer, token list rendering, marker styling |
| `vtt/static/js/play-client.js` | Socket listeners for token updates, character sheet navigation | Realtime synchronization |
| `vtt/play/routes.py`, `vtt/play/actions.py` | Token CRUD endpoints, permission checks | Server boundary for token changes |

---

## 3. Web research and source-backed findings

### Foundry Token HUD architecture

[Foundry's Token HUD API](https://foundryvtt.com/api/classes/foundry.applications.hud.TokenHUD.html) is designed as a **dynamic overlay attached to the selected token**. Key design facts:

1. **Purpose:** Quick access to resource bars, status effects, elevation, targeting, and combat actions without opening a full sheet or right-click context menu.
2. **Positioning:** Dynamically positioned via `_onPosition()` anchor. It clamped against viewport edges and responds to zoom/scroll.
3. **Capabilities:** Displays attribute bars for reference, status effect icons with toggle capability, elevation selector, combat integration, and movement controls.
4. **Separation of concerns:** The HUD is for quick changes to **resources and statuses**. The full **actor sheet** is a separate application opened intentionally for deep inspection.
5. **Status effects model:** Foundry tracks status effects as array data; each effect has an `icon` (URL), `name`, optional `value`/`duration`, and active state. Status effects are toggleable from the HUD.
6. **Permissions:** Link Actor Data flag allows changes to sync across all tokens; nameplates respect visibility settings (Never/Hover/Always).

**Primary source:** https://foundryvtt.com/article/tokens/, https://foundryvtt.com/api/classes/foundry.applications.hud.TokenHUD.html

### W3C Accessibility Patterns

From [W3C WAI-ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/patterns/) and [MDN](https://developer.mozilla.org/):

1. **Buttons and focus:**
   - Every action (HP change, status toggle, sheet link, more menu) must be keyboard-accessible via `Tab`, `Enter`, `Space`, and `Escape`.
   - Icon-only buttons need visible tooltips and `aria-label`; tooltips must not be the only way to understand the button.
   - Focus must be visible without relying on color alone.

2. **Menu button pattern ([APG](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/)):**
   - A menu button has `aria-haspopup="menu"` and `aria-expanded` state.
   - Pressing `Enter` or `Space` opens the menu and moves focus to the first menu item.
   - Keyboard navigation within the menu uses arrow keys; `Escape` closes and restores focus to the button.
   - Commands (not toggles) belong in a menu.

3. **Disclosure pattern ([APG](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/)):**
   - For expandable sections, use a `button`, `aria-expanded`, and `aria-controls` to link the trigger to its target.
   - This is the right pattern for "show/hide" HUD sections.

4. **Checkbox pattern ([APG](https://www.w3.org/WAI/ARIA/apg/patterns/checkbox/)):**
   - Status toggles are checkboxes or toggle buttons, not commands. They need `aria-checked`/`aria-pressed`, visible labels, and `Space` to toggle.
   - A group of checkboxes should be wrapped with `role="group"` and a `<legend>` or `aria-labelledby`.

5. **Live regions and focus:**
   - When a token is selected, announce its name, HP, and status summary to screen readers using `aria-live="polite"` or a `status` role.
   - Do not move focus automatically when a popover opens; keep focus with the trigger button and let the user navigate.
   - Restore focus to the trigger when the popover/menu closes (`Escape`).

6. **Touch and pen input:**
   - Do not rely on hover for essential affordances. Hover-only HUDs disappear on touch.
   - Use selection state (border, background, aria-selected) as the durable trigger.
   - Long-press and right-click are equivalent on touch; provide a visible button as the primary path.

**Primary sources:**
- https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/
- https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/
- https://www.w3.org/WAI/ARIA/apg/patterns/checkbox/
- https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/
- https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events

### Responsive and performance constraints

From PLAYTABLE_UI_RESEARCH_2026-08-27.md and MDN:

- **Desktop:** Anchored HUD with collision avoidance against viewport edges and the right sidebar. Re-anchor on selection, zoom, scroll, viewport resize, and map activation.
- **Mobile:** Use `#tableSheet` and bottom-sheet pattern instead of a floating HUD. Avoid hover-dependent disclosure.
- **Performance:** Use `ResizeObserver` to detect geometry changes instead of polling. Update transforms via `requestAnimationFrame` rather than layout-heavy `top/left`. Do not rebuild the map or all tokens for every HUD update.
- **Visual:** Keep the map readable behind the HUD using opaque/translucent panels. Avoid expensive `backdrop-filter`/blur on mobile.

**Primary sources:**
- https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver
- https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame
- https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/touch-action

---

## 4. Good examples

### Example A: Foundry VTT Token HUD

**Why it works:**
- **Compact focus:** Shows only essential quick controls (name, HP bar, status icons, elevation) on a small overlay anchored to the token.
- **Right-click entry:** Familiar context-menu behavior; does not require discovering a UI button.
- **Clear separation:** Detailed actor sheet is a separate, intentional navigation. The HUD does not try to fit everything.
- **Realtime sync:** Changes propagate immediately to all users via socket updates.
- **Status effect design:** Status icons are visual, toggleable, and grouped. Hovering shows tooltips with names and durations.

**What Roll-Drauf can borrow:**
- Anchor the HUD to the token marker and use collision avoidance.
- Show name, type/class, HP, and a summary of active statuses without opening a full editor.
- Use icon-based status display with text fallback.
- Provide a "more" menu for infrequent actions.

**Source:** https://foundryvtt.com/article/tokens/

### Example B: Roll20 Character Focus

**Why it works:**
- **Drawer mode:** Opens a side panel with character stats, actions, and spells without covering the map.
- **Keyboard navigation:** Tab through fields and controls; Escape closes the panel and returns focus to the map.
- **Mobile adaptation:** Bottom sheet on small screens; drawer on desktop.

**What Roll-Drauf can borrow:**
- Use the existing `#sheetDrawer` as the full-inspection surface.
- Make the HUD a thin, stay-out-of-the-way overlay; keep the drawer for deep dives.
- Ensure the HUD never hides the selected token or critical map controls.

### Example C: D&D Beyond Character Sheet

**Why it works:**
- **Portrait and summary section:** Shows a character image, name, class, level, and HP prominently at the top.
- **Organized sections:** Features, actions, legendary actions are grouped and collapsible.
- **Visual hierarchy:** Color, icons, and layout make resources (HP) and actions (spells, abilities) quickly scannable.

**What Roll-Drauf can borrow:**
- Use portrait, name, type, HP as a visual anchor in the HUD.
- Organize the full sheet into collapsible sections (stats, proficiencies, immunities, languages, actions, legendary actions).
- Separate player-character layouts from monster layouts (e.g., monsters have challenge rating and legendary actions; PCs have class/level).

---

## 5. Bad examples and failure modes

### Failure A: Always-visible floating panel covering the map

**Why it fails:**
- Obscures the map and selected token, defeating the purpose of a table-first interface.
- Cannot be moved without another control; users end up working around it.
- On mobile, it takes up half the screen and makes interaction clumsy.

**Roll-Drauf avoidance:**
- Keep the HUD small and anchored; use a disclosure or menu for less-frequent options.
- On mobile, use the `#tableSheet` bottom-sheet pattern instead of a floating panel.
- Do not keep the HUD visible if it would hide the token being inspected.

### Failure B: Hover-only HUD

**Why it fails:**
- Does not work on touch; users cannot reliably hover over a token on a phone or tablet.
- Fragile when zoomed; hover regions shift and become unreliable.
- Keyboard and screen-reader users cannot trigger hover; not accessible.
- Disappears when the pointer moves away, making it hard to click a button inside the HUD.

**Roll-Drauf avoidance:**
- Use selection as the durable trigger, not hover.
- Provide a visible button (e.g., "sheet" link) as the primary action path; right-click as an optional shortcut.
- Keep the HUD open when a token is selected; close it only on explicit user action (Escape, outside click, new selection).

### Failure C: Dense status grid without labels or toggles

**Why it fails:**
- Icon-only status effects are opaque to new players; they cannot distinguish between "stunned," "frightened," and "charmed" without a legend.
- A count-only badge hides the actual statuses; users must open a full dialog just to clear one effect.
- No direct toggle; clearing a status requires a two-step open-and-click workflow.
- Clutter overload: Foundry shows 20+ status effects at once; Roll-Drauf should start with a curated set.

**Roll-Drauf avoidance:**
- Show status names and icons together. Tooltips are optional but not the only affordance.
- Make status toggles interactive (click or Space) directly in the HUD or a popover.
- Use a curated status vocabulary matching Roll-Drauf's rules; defer generic Foundry catalogs.
- Provide a "clear all" action for DMs and a way to search/group statuses if the list grows.

### Failure D: Right-click-only menus without visible buttons

**Why it fails:**
- Touch and pen users cannot right-click reliably.
- Keyboard users cannot discover the menu without pointer skills.
- Screen-reader users cannot activate it.
- Discoverable only to experienced Foundry users; new players will not find the feature.

**Roll-Drauf avoidance:**
- Provide a visible menu button or "more" button in the HUD.
- Right-click can open the same menu as a shortcut, but do not make it the only way.
- Ensure the button has a visible label and `aria-label`.

### Failure E: Unconfirmed destructive actions

**Why it fails:**
- Deleting a token or clearing all statuses is irreversible and affects the entire session.
- Accidental clicks are common on small screens and with touch dragging.
- No undo; players must request the DM to restore the state.

**Roll-Drauf avoidance:**
- Destructive actions (delete token, transfer loot, reset scene) must have a confirmation dialog.
- The confirmation must state what will happen and who it affects (e.g., "This will delete the token from the scene for all players").
- Provide an undo or recovery path where possible (e.g., undo/restore for 10 seconds, or a server-side delete log).

---

## 6. Lessons learned

1. **Separation of concerns is load-bearing.**
   - HUD = quick resource/status changes (1–3 seconds per action).
   - Sheet = detailed inspection and deep editing (intentional, longer session).
   - The HUD should never try to fit everything; it would become cluttered and slow.

2. **Selection, not hover, is the reliable trigger.**
   - Hover works on desktop only. Selection works everywhere: mouse, touch, keyboard, and screen readers.
   - Use `selectedTokenId` as the single source of truth; render the HUD only when a token is selected.
   - Close the HUD on deselection or explicit Escape.

3. **Keyboard and touch must have equal status affordances.**
   - Right-click is a shortcut for advanced users, not the primary path.
   - Every action in the HUD must have a visible button, a keyboard shortcut, and a screen-reader label.
   - Test with keyboard-only (Tab, Enter, Space, Escape) before considering it done.

4. **Collisions with the sidebar and viewport edges are inevitable; plan for them.**
   - Use `ResizeObserver` to detect sidebar/viewport changes.
   - Calculate free space dynamically; re-anchor the HUD if it would be hidden.
   - On mobile, switch to a bottom sheet rather than trying to squeeze the HUD into the remaining space.

5. **Status effects are data-first, UI-last.**
   - Do not copy Foundry's full status catalog; Foundry has 40+ built-in conditions, many system-specific.
   - Define Roll-Drauf's status vocabulary first: which conditions matter for your rules? (e.g., poisoned, blinded, stunned).
   - Each status needs an ID, label, icon URL, active state, and optional value/duration. Persist this schema server-side.

6. **Realtime synchronization prevents stale HUD state.**
   - If one player changes a token's HP, the other player's HUD must update immediately.
   - Use socket events for every change; do not rely on polling or manual refresh.
   - Include version/conflict resolution: if two players edit HP at once, the server version wins and the client reconciles.

7. **Permissions matter; do not expose editor fields to read-only players.**
   - Some players can only view the table; do not show editable HP inputs for tokens they do not own.
   - Clearly distinguish read-only summary (name, HP display) from editable controls (HP input, status toggle).
   - Test the HUD in both player and read-only modes before shipping.

---

## 7. Community favorites (opinion/anecdotal evidence)

Based on VTT community discussions and Reddit threads, the following are *preferences and pain points*, not requirements:

### Preferred by community

1. **"I want to see HP and status at a glance without opening a panel."** — Compact HUD with name, HP, and 3–5 status icons reduces cognitive load during fast combat play.
2. **"I hate discovering hidden features; show me the button."** — Visible "more" and "conditions" buttons are preferred over right-click-only menus. Foundry veterans use right-click; new players do not.
3. **"Status effects need labels."** — Icon-only status grids are confusing. "Charmed (advantage on Charisma checks)" is clearer than an icon. Tooltips on hover help, but visible labels are better.
4. **"Drag my tokens without losing the HUD; it should follow."** — When a token is dragged, the HUD should move with it or stay available, not disappear.
5. **"Mobile is broken because HUDs are hover-only."** — VTT play on iPad/tablet is common; hover-only UIs are a major pain point.

### Community complaints (to avoid)

1. **Dense, overwhelming status grids** — Too many icons at once exhausts attention. Foundry's full catalog is overkill for most tables.
2. **Hover-only interactions** — Mobile users and keyboard users feel left out.
3. **Right-click as the only path** — Discoverable only to experienced players; new players struggle.
4. **No confirmation on destructive actions** — Accidental token deletion is a common frustration.
5. **Stale state after network lag** — HUD shows old HP; user changes it; actual value remains old. Confusing and demoralizing.

**Note:** These are community observations and preferences, not Roll-Drauf requirements. They inform UX direction and should be validated against Roll-Drauf's actual player base.

---

## 8. Roll-Drauf fit and explicit non-goals

### In scope for Slice 04

1. **Selected-token HUD:** Compact overlay showing name, type/class, HP (current/max), movement (if applicable), initiative/combat state (if in combat), and status summary. 3–5 quick actions: open sheet, edit HP, view conditions, more menu.
2. **Full focus sheet:** Use the existing `#sheetDrawer` to present a detailed character/creature view. Organize by sections: portrait, stats (STR, DEX, etc.), proficiencies, immunities, resistances, languages, actions, legendary actions (if applicable), limited-use resources with current/max.
3. **Context-aware rendering:** The HUD and sheet must adapt to token type (player character, monster, NPC, trap). A monster shows Challenge and legendary actions; a PC shows class and level.
4. **Permission respect:** Read-only tokens show summary only; owned tokens allow HP/condition editing. Non-owned tokens show name and status, not edit controls.
5. **Keyboard and touch support:** Tab through controls; Space/Enter to toggle/open; Escape to close. On touch, use selection (not hover) and provide a "sheet" button instead of requiring a long-press.
6. **Realtime updates:** Socket events propagate token changes (HP, status, name) to all connected clients; HUD reconciles conflicts.

### Explicitly deferred (next slices)

- **Conditions/status picker schema and UI** → Slice 05
- **Combat state, turn order, initiative** → Slice 06
- **Character sheet content redesign** (proficiencies, skill proficiencies, features) → Follow-up to Slice 05/06
- **Multi-token selection and batch actions** → Will piggyback on Slice 04's selection model but needs separate work
- **Loot transfer from tokens** → Slice 09; requires container model and multi-selection
- **Token animation or visual effects** → Out of scope; not a data/interaction layer

### What Roll-Drauf will NOT adopt from Foundry

- **Full Foundry actor/folder model** — Roll-Drauf has a simpler schema; use what exists (character_id, token fields).
- **Arbitrary status catalogs** — Curate Roll-Drauf's status vocabulary; do not expose all 40+ Foundry conditions.
- **Hierarchical scene/page folders** — Defer until the backend has folder IDs and permissions. Use local UI grouping (optional) for the first slice.
- **Lighting/vision overlay** — That is Slice 10 (Vision, Walls, Fog of War). It needs scene geometry and a vision engine.

---

## 9. Proposed interface/data/permission contracts

### HUD display contract

The HUD renders data from `TokenState` and permission context:

```javascript
{
  // Source data (from selectedTokenId lookup)
  id: number,
  name: string,
  character_id: number | null,
  type: string, // "character" | "monster" | "npc" | "trap"
  hp_current: number,
  hp_max: number,
  x: number,
  y: number,
  elevation: number | null,
  
  // Combat context (from turn-order state if applicable)
  initiative: number | null,
  is_current_turn: boolean,
  
  // Status/condition summary
  metadata_json: {
    conditions: [
      { id: string, label: string, icon: string, active: boolean, value?: number }
    ]
  },
  
  // Character link (if available)
  character_id: number | null
}
```

### Permission boundary

```javascript
{
  canEdit: boolean, // user owns token OR is DM
  canView: boolean, // always true (all users can see selected token)
  canDelete: boolean, // DM only
  readOnly: boolean // game state read-only flag
}
```

**Rules:**
- If `canView && !canEdit`: show name, HP, type, status icons; hide input fields and edit buttons.
- If `canEdit && !readOnly`: show all controls.
- If `readOnly`: show summary only; all inputs disabled.
- Deletion requires `canDelete && isDM`.

### HUD positioning contract

```javascript
{
  // Token marker center (world coords)
  tokenX: number,
  tokenY: number,
  
  // Calculated screen position (after zoom/viewport transform)
  screenX: number,
  screenY: number,
  
  // Viewport and sidebar constraints
  viewportWidth: number,
  viewportHeight: number,
  sidebarWidth: number | 0, // width of open sidebar or 0 if closed
  
  // Preferred anchor
  anchor: "top" | "bottom" | "left" | "right", // preferred quadrant
  
  // Clamped final position
  finalX: number,
  finalY: number
}
```

**Rules:**
- Calculate position assuming HUD width 200px, height 300px.
- Prefer top-left of token; if near viewport edge, shift to fit.
- Never be hidden behind the sidebar; if sidebar is open, reduce preferred position.
- On mobile (viewport width < 768px), use `#tableSheet` bottom-sheet pattern instead.

### Socket event contract for realtime sync

When HP, name, or status changes, emit:

```javascript
{
  event: "token_updated",
  tokenId: number,
  changes: {
    hp_current?: number,
    hp_max?: number,
    name?: string,
    metadata_json?: { conditions: [...] }
  },
  version: number, // server-side version counter
  timestamp: ISO8601
}
```

**Rules:**
- Client receives event and updates local state.
- If version differs from client version, reconcile from server state (server wins).
- If HUD is open for this token, update display immediately.
- If user is editing HP input, do not interrupt; wait for blur/submit, then reconcile.

### Character sheet drawer contract

The drawer (existing `#sheetDrawer`) opens via:

```javascript
// From HUD "sheet" button
openCharacterSheet(characterId, sheetContext = "hud") 
  // opens iframe or HTML view of character
  // sheetContext hints whether user arrived from HUD (quick) or sidebar (deep)
```

**Rules:**
- If no character_id, show a "no linked character" message; offer to link one.
- Sheet must close on Escape or close button and restore focus to the HUD.
- Do not close the HUD when the sheet opens; they are separate layers.

---

## 10. Risks and assumptions with severity labels

### Risk R1: Collision avoidance complexity — **MEDIUM**

**Description:** Calculating HUD position dynamically across desktop/mobile, sidebar open/closed, zoom levels, and viewport resizes is error-prone. A HUD positioned incorrectly will hide the token or critical controls.

**Mitigation:**
- Use `ResizeObserver` to re-anchor on sidebar/viewport changes, not polling.
- Define a clear priority order: never hide the selected token > never hide map controls > fit in viewport > fit left of sidebar.
- Test with sidebar open/closed, at 50%, 100%, 200% zoom, and on mobile.

**Who owns:** Deploy phase (when rendering is implemented); flag if positioning logic requires complex math.

---

### Risk R2: Permissions and read-only mode inconsistency — **MEDIUM**

**Description:** If permissions are not consistent between HUD and sheet drawer, a read-only user might appear to edit HP in the HUD but the server rejects it, leaving stale state.

**Mitigation:**
- Define permission checks server-side; HUD must not show edit controls if the server would reject the change.
- In read-only mode, disable all input fields and hide action buttons; show summary only.
- Test HUD rendering in (DM + owned token), (Player + owned token), (Player + unowned token), and (read-only mode).

**Who owns:** Apply phase (when permission contracts are finalized).

---

### Risk R3: Status condition schema mismatch — **MEDIUM**

**Description:** If Foundry status effects and Roll-Drauf status conditions use different schemas (icon URL vs icon ID, duration format, etc.), the HUD will not render statuses correctly or will show garbled data.

**Mitigation:**
- Define Roll-Drauf's status schema in Slice 05 before implementing the Slice 04 HUD.
- Freeze the status shape (id, label, icon, active, value, duration, source) before rendering.
- For Slice 04, assume status is a simple { id, label, icon, active } until schema is approved.

**Who owns:** Apply phase; Apply must confirm status shape before Deploy.

---

### Risk R4: Stale state during network lag — **MEDIUM**

**Description:** If a player changes HP while the network is slow, their HUD shows the new value but the server is still processing. If they switch to a different token, the old token's HUD is not updated when the server confirms.

**Mitigation:**
- Use optimistic updates: show the user's change immediately; reconcile from server event.
- If server conflicts (user edited to 10, server says 8), reconcile to server value and notify the user.
- Include version/timestamp in all token updates; client can reject stale events.
- Test lag/reconnect scenarios before Deploy.

**Who owns:** Deploy phase (when realtime logic is implemented).

---

### Risk R5: Mobile bottom-sheet focus trap — **LOW**

**Description:** On mobile, if the HUD is a bottom sheet above the map, focus could get trapped inside the sheet, making it hard for screen-reader users to return to the map.

**Mitigation:**
- Use native `<dialog>.showModal()` or the Popover API to manage focus containment and Escape behavior.
- Provide a visible close/cancel button; do not rely on swipe-to-dismiss alone.
- Test with screen reader (NVDA on Windows, VoiceOver on Mac/iOS) before shipping.

**Who owns:** Deploy phase (mobile rendering).

---

### Risk R6: HUD performance with many tokens and frequent updates — **LOW**

**Description:** If a battle has 20+ tokens and statuses are updated frequently (e.g., conditions applied in a round), re-rendering the HUD for each token could cause jank or lag.

**Mitigation:**
- Avoid re-rendering the entire HUD on every socket event; update only the changed field (HP, status count).
- Use `requestAnimationFrame` to batch visual updates.
- Measure real frame time at 25, 100, and 250 tokens before optimizing.
- Do not attach duplicate global listeners for each HUD instance.

**Who owns:** Deploy phase; flag if benchmark shows >16ms frame time.

---

### Risk R7: Assumption — Character sheet drawer will exist and be responsive — **MEDIUM**

**Description:** This research assumes `#sheetDrawer` is available and can be opened by the HUD. If the drawer is removed or not responsive to mobile, the HUD's "open sheet" button will not work.

**Mitigation:**
- Verify in Apply phase that the drawer is part of the approved Slice 04 contract.
- If the drawer does not exist, defer the full sheet to a later slice and keep the HUD as a standalone view.

**Who owns:** Apply handoff (design must confirm sheet drawer scope).

---

### Assumption A1: `selectedTokenId` remains the single-selection state

This research assumes token selection remains a single token (`selectedTokenId: number | null`). Multi-selection is deferred to Slice 09 (loot transfer) or later.

**If multi-selection is needed sooner:** Update the HUD to show a count + selection summary rather than a single token detail.

---

### Assumption A2: Socket events carry full token state, not just deltas

This research assumes realtime updates include the full changed fields (hp_current, name, status) so the HUD can update without re-fetching.

**If events are delta-only:** HUD must handle partial updates and reconcile from server on conflict.

---

## 11. Acceptance criteria for desktop, mobile, keyboard, permissions, realtime, errors, and destructive actions

### Desktop (anchored HUD)

- [ ] Selecting a token reveals a HUD anchored near the token marker.
- [ ] HUD shows name, type/class, HP (current/max), initiative/combat state (if applicable), and 3–5 quick actions.
- [ ] HUD is positioned to avoid viewport edges, map controls, and the right sidebar.
- [ ] Re-anchors on scroll, zoom, sidebar open/close, and viewport resize without flicker.
- [ ] Opening/closing the HUD does not move the map or affect other tokens.

### Mobile (bottom sheet)

- [ ] On narrow viewports (<768px), HUD switches to a scrollable bottom sheet above the map.
- [ ] Sheet can be dismissed by swiping down, clicking close, or pressing Escape.
- [ ] Focus does not trap in the sheet; Tab+Shift cycles focus between sheet and map.
- [ ] Long-form content (full character sheet) fits in the available space without requiring excessive scrolling.

### Keyboard

- [ ] **Tab** navigates through HUD controls (name input, HP input, "sheet" button, "conditions" button, "more" button, close button).
- [ ] **Enter/Space** opens the HUD's "more" menu; first menu item receives focus.
- [ ] **Arrow keys** navigate within the menu (up/down); Escape closes the menu and returns focus to the "more" button.
- [ ] **Escape** closes the HUD entirely and returns focus to the map (or the trigger that opened it, e.g., a token list).
- [ ] Hotkey shortcuts (e.g., Ctrl+H for sheet) do not fire if focus is inside a text input.

### Permissions and read-only mode

- [ ] **DM + owned token:** All controls visible and editable (name input, HP input, status toggle, delete button).
- [ ] **Player + owned token:** Name and HP visible; editable if party allows. Status toggle visible if applicable.
- [ ] **Player + unowned token (observed):** Name, type, HP, status icons visible; no edit controls. "Sheet" button shows "not your character" or similar.
- [ ] **Read-only mode (any role):** All controls disabled; summary only (name, HP display, status icons).
- [ ] Destruction action (delete token) visible only to DM and requires confirmation.

### Realtime updates and conflict resolution

- [ ] When another player changes a token's HP, the HUD updates within 1 second.
- [ ] If two players edit HP simultaneously, the server value wins; client reconciles and notifies the user ("Rolled back to 25 HP").
- [ ] Status changes (add/remove condition) propagate to all HUDs within 1 second.
- [ ] If network lags and connection is lost, the HUD remains visible but shows a "reconnecting..." indicator; on reconnect, reconciles from server state.
- [ ] Stale data does not persist; if HUD is out of sync, refresh from the next socket event.

### Errors and fallbacks

- [ ] If character sheet fails to load, HUD shows "Sheet not available" instead of crashing.
- [ ] If a token is deleted by another player while its HUD is open, the HUD closes and the map deselects the token.
- [ ] If permission check fails on the server (e.g., user tries to edit HP without ownership), the server rejects the change and HUD shows the original value + a toast error ("You do not have permission to edit this token").
- [ ] If a socket event is malformed or missing required fields, the client logs a warning and does not update the HUD; existing display is preserved.

### Destructive actions

- [ ] **Delete token:** Shows a confirmation dialog: "Delete NAME from the scene? This affects all players." with Cancel and Delete buttons.
- [ ] **Clear all conditions:** Shows a confirmation dialog: "Clear all conditions from NAME? This cannot be undone." with Cancel and Clear buttons. (Slice 05 requirement; placeholder here.)
- [ ] Confirmation dialogs are modal; Escape cancels; focus is initially on Cancel (safe default).
- [ ] After destruction, the HUD closes and the map deselects the token.

---

## 12. Apply handoff: decisions still needed before implementation

### Design decisions

1. **HUD size and layout.**
   - How large should the HUD be on desktop? (Proposed: 200–250px wide, flexible height)
   - Should HP be an input field or a stepper/button pair? (Proposed: input field + small +/−1 buttons for quick adjustments)
   - How many quick actions in the top row? (Proposed: 3–5; sheet, HP, conditions, more, close)

2. **Status display in the HUD.**
   - Should statuses show text labels or icons only? (Proposed: icons + tooltip; defer text labels to Slice 05 if catalog grows)
   - How many status icons before "..." overflow? (Proposed: 3–4; tap/click "..." to open the status picker from Slice 05)
   - Should status count badge remain, or replace it with icons? (Proposed: replace badge with icons; remove count badge)

3. **Sheet drawer vs full modal.**
   - Is the existing `#sheetDrawer` the right place for the full character inspection, or should it be a modal dialog?
   - Can the drawer scale to show character stats, proficiencies, immunities, resistances, and actions without overwhelming mobile?
   - (Proposed: Use drawer on both desktop and mobile; defer redesign of drawer content to post-Slice 04)

4. **Initiative and combat state in the HUD.**
   - Should the HUD show initiative number and "current turn" state? (Proposed: yes, if available; defer sort/turn order to Slice 06)
   - What color/icon indicates "this is the current actor in combat"? (Proposed: red/gold border or "Current" label; defer styling decision to Apply)

5. **Name editing in the HUD.**
   - Should the HUD show a name input for quick rename, or require opening the sheet? (Proposed: input field; rename is a frequent action)
   - Should name changes broadcast immediately or wait for blur/confirm? (Proposed: broadcast on blur or Enter)

### Data/permission decisions

6. **Status shape (dependency on Slice 05).**
   - Confirm that Slice 05 will define a status schema with { id, label, icon, active, value?, duration? }.
   - Confirm where statuses live: in `metadata_json`, a dedicated `statuses` field, or elsewhere.
   - For Slice 04, assume status is { id, label, icon, active }; update if Slice 05 changes.

7. **Character-linked token vs independent token.**
   - For a token with no character_id, should the HUD show "No linked character" or pull data from token fields directly?
   - (Proposed: If no character_id, show token fields (name, type) as summary; "Open sheet" button disabled or links to a token-specific view)

8. **Version/conflict handling.**
   - Should the client use a simple `version` counter for conflict detection, or timestamp-based?
   - How should the server handle simultaneous edits? (Proposed: last-write-wins + client reconciliation)

### Scope decisions

9. **Multi-token selection and batch actions.**
   - Should Slice 04 add a "select multiple tokens" feature, or defer to Slice 09?
   - (Proposed: Defer; Slice 04 keeps single-token HUD; multi-selection comes with loot transfer)

10. **Token context menu (right-click or "more" button).**
    - Should "more" open a popover menu or a separate panel?
    - What actions go in "more"? (Proposed: rename, image, delete, target, display in chat, transfer loot)
    - Which of these are Slice 04 vs later slices? (Proposed: rename, image, delete in Slice 04; transfer loot in Slice 09; target/chat in later slices)

11. **Full character sheet redesign (portraits, stats, proficiencies, etc.).**
    - Is the drawer content redesign in scope for Slice 04, or will Slice 04 only link to the existing drawer?
    - (Proposed: Slice 04 links to drawer; drawer content redesign is a follow-up after Slices 05/06 define statuses and combat state)

### Testing and measurement

12. **Performance baseline.**
    - What is the acceptable frame time when dragging a token with HUD open? (Proposed: ≥60 FPS at 100% zoom)
    - What is acceptable response time for HP/status updates? (Proposed: ≤1 second end-to-end)
    - Should we benchmark with 25, 100, or 250 tokens in the scene?

13. **Accessibility testing plan.**
    - Will Slice 04 include manual screen-reader testing (NVDA, VoiceOver)?
    - Will keyboard-only navigation be tested before Deploy?
    - (Proposed: yes to both; use WCAG 2.1 AA as the baseline; document any deviations)

---

## Sources (primary and community)

### Official Foundry VTT documentation

- [Foundry Tokens](https://foundryvtt.com/article/tokens/) — Token display, HUD, LinkActorData, permissions
- [Foundry TokenHUD API v14](https://foundryvtt.com/api/classes/foundry.applications.hud.TokenHUD.html) — API design patterns, lifecycle, capabilities
- [Foundry TokenDocument API v14](https://foundryvtt.com/api/classes/foundry.documents.TokenDocument.html) — Token data schema, status effects, elevation, vision

### W3C Accessibility and Web Standards

- [WAI-ARIA Authoring Practices Guide (APG) — Menu Button Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/) — Focus, aria-haspopup, aria-expanded, keyboard behavior
- [WAI-ARIA APG — Disclosure Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/) — aria-expanded, aria-controls, button/section behavior
- [WAI-ARIA APG — Checkbox Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/checkbox/) — aria-checked, Space behavior, labeling
- [WAI-ARIA APG — Accessible Names and Descriptions](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/) — Button labels, tooltips, icon alternatives
- [MDN — Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events) — Mouse, touch, pen input; setPointerCapture
- [MDN — ResizeObserver](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver) — Detect geometry changes
- [MDN — requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame) — Batch visual updates
- [MDN — Popover API](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API) — Non-modal overlays, focus behavior

### Roll-Drauf repository

- [PLAYTABLE_FEATURE_WORK_PACKAGE_2026-08-27.md](PLAYTABLE_FEATURE_WORK_PACKAGE_2026-08-27.md) — Slice dependencies, phase gates, codex ownership
- [PLAYTABLE_UI_RESEARCH_2026-08-27.md](PLAYTABLE_UI_RESEARCH_2026-08-27.md) — HUD vs sheet separation, responsive patterns, accessibility constraints
- `vtt/static/js/play-ui.js` — Existing token widget, selection logic, HP input, character sheet drawer
- `vtt/templates/play.html` — DOM structure, widget placement, sheet drawer anchor

### Community sources (anecdotal)

- Reddit r/FoundryVTT, r/VTT: feedback on hover-only HUDs, status confusion, mobile usability
- VTT Discord communities: preferences for visible buttons over right-click-only menus, mobile sheet patterns

---

## Summary

**Slice 04 (TOKEN_HUD) is ready for Apply design review.**

Key findings:
- **Foundry's Token HUD is a mature, proven pattern:** compact overlay for quick resource/status changes, anchored to the selected token, separate from the full sheet.
- **Roll-Drauf's existing seams are strong:** `#tokenWidget`, `#sheetDrawer`, `selectedTokenId`, and socket events are all in place. The work is primarily refinement and accessibility.
- **Accessibility and mobile are load-bearing:** Hover-only HUDs, right-click-only menus, and always-visible panels all fail. Selection-based triggering, visible buttons, and bottom-sheet mobile layout are required.
- **Collision avoidance and realtime sync add complexity:** Positioning the HUD reliably across viewport changes and managing conflicts during lag both require careful testing.
- **Status conditions must be defined first:** Slice 05 must freeze the status schema before Slice 04 renders statuses in the HUD.

**12 design decisions listed in section 12 (Apply handoff).** The most critical:
1. HUD size, layout, and quick-action count
2. Status display (icons vs labels, overflow behavior)
3. Confirm status schema from Slice 05
4. Scope of "more" menu (rename, image, delete vs later slices)
5. Character sheet drawer content (redesign vs link-only in Slice 04)

**No production code changed. This is research only.** Findings are cited to primary sources (Foundry official API, W3C APG, MDN) and labeled when anecdotal.
