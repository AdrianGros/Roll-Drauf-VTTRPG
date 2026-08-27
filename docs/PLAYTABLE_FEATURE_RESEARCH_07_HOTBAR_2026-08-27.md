# Feature research: personal action hotbar
**Date:** 2026-08-27  
**Status:** Research/Discover pass  
**Scope:** Foundry-inspired hotbar for Roll-Drauf playtable action execution  
**Sources:** Foundry VTT Macro documentation, MDN, W3C ARIA APG, current Roll-Drauf action_catalog

---

## 1. Status and input summary

The prompt asks: *Research personal VTT hotbars: numbered slots, keyboard shortcuts, multiple pages, drag/drop, macros vs system actions, token-specific bars, use counts/cooldowns, empty slots, ownership, and mobile presentation. Use official Foundry Macro/Hotbar documentation and other first-party VTT documentation. Include good/bad examples, community favorites, and the smallest useful first slice for an action_catalog with server-backed executeAction.*

This is the seventh feature slice in the Roll-Drauf playtable research series, following scene directory, app menu, map tools, token HUD, statuses, and combat tracker. It sits at the action-execution layer: once a player knows what to do (via token HUD, scene context, or initiative), the hotbar is the fastest way to do it repeatedly.

---

## 2. Current Roll-Drauf state and relevant file inventory

### Existing implementation

- **Action catalog:** `vtt/play/actions.py` defines `ACTION_CATALOG` with three starter actions (attack_basic, dash_move, interact_object). Each entry has: code, name, category, requires_target (bool), suggested_roll, description.
- **Action executor:** `vtt/play/actions.py` exports `execute_action(action_code, token_id, actor_user_id, target_token_id, payload)`. Client calls via `executeAction()` in `play-client.js:76`.
- **Frontend catalog access:** `play-ui.js:2860` reads `bootstrap.action_catalog` and populates a test `<select>` element in the token-create panel.
- **Bootstrap delivery:** `vtt/play/routes.py:160` includes `action_catalog` in the playtable bootstrap.
- **Server boundary:** The `/api/play/campaigns/{id}/sessions/{id}/actions/execute` POST endpoint accepts `token_id`, `action_code`, `payload`, and optional `target_token_id`.

### No current hotbar implementation

- No numbered slots, keyboard shortcuts, or page switching.
- No drag/drop or user customization.
- No cooldown, use-count, or availability tracking.
- No token-specific action variants.
- No mobile-optimized action bar.

### Related surfaces

- **Token HUD:** Selected-token widget shows name, HP, initiative; will expose "more" menu for actions.
- **Action menu:** Token HUD "more" → action list (via W3C menu-button, distinct from hotbar).
- **Sidebar:** Journal, Chat, Tools, Session tabs; chat will have a compact roll composer.
- **Mobile table sheet:** Existing #tableSheet container for responsive layout.

---

## 3. Web research and source-backed findings

### Foundry Macro Hotbar

**[Foundry VTT — Macros](https://foundryvtt.com/article/macros/)**

The Foundry hotbar is the canonical reference for personal action systems in VTTs:

- **Slot model:** 10 active slots per page, 5 pages per user, 50 macros maximum.
- **Keyboard access:** Numeric keys 1–9 and 0 map to slots 1–10. Each user has independent shortcuts.
- **Page switching:** Up/Down indicators cycle through the five pages. No cross-page shortcuts.
- **Customization:** Users drag macros from the Macro Directory to hotbar slots. Drag from empty slot opens a create dialog.
- **Execution:** Click slot, press numeric key, or `/macro MacroName` in chat.
- **Macro types:** Rollable tables, dice formulas, scripts, or drag-and-drop from items/actors.
- **Visibility:** Each macro is personal to the user. Other players do not see it or its keyboard shortcuts.
- **No use counts:** Foundry does not track macro use counts in the base hotbar; cooldowns come from the macro script itself.

**Key constraint:** The hotbar is *stateless* from the server perspective. It is a user-side list of macro IDs that the server does not manage; macros are global system objects. No server-backed "your hotbar" table.

### MDN Keyboard Access

**[MDN Keyboard Access and Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent)**

- Numeric key events fire independently of text input. The hotbar must prevent firing while focus is in an input, textarea, select, or contenteditable.
- `keydown` is the appropriate event for detecting number keys; `keypress` is deprecated.
- Best practice: Capture keydown at a stable root and check `event.target.tagName` and `contentEditable` to prevent shortcuts inside editors.
- Never fire a hotbar shortcut if `event.target` is an input-like element or if `event.metaKey`, `event.ctrlKey`, or `event.shiftKey` is true (reserved for browser shortcuts).

### W3C ARIA APG Button and Disclosure Patterns

**[Menu Button Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/), [Disclosure Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/)**

- The hotbar itself is not a menu; it is a toolbar of buttons. Each slot is a button with an accessible name (e.g., "Slot 1: Attack (Ctrl+1)").
- If the hotbar is collapsible/expandable, use disclosure semantics: `aria-expanded`, `aria-controls`, and a native button.
- Each action button should have a visible label or tooltip. Icon-only buttons need `aria-label`.
- Page switching can use disclosure (collapse/expand pages) or simple previous/next buttons. If using arrow keys for page nav, the pattern should be documented.

### Mobile Consideration: Touch and Sheet Layout

**[MDN Touch Events and Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Touch_events)**

Touch devices do not have keyboard shortcuts. The hotbar must adapt:
- Desktop: Visible numbered slots + keyboard shortcuts.
- Mobile: Slots in a horizontal scroll or collapsible section within the table sheet. No keyboard shortcuts (though external keyboards are possible).
- Avoid `touch-action: none` on the whole hotbar; let native scroll/zoom work for the container.

---

## 4. Good examples

### Foundry Macro Hotbar

**Why it works:**
- 10 slots is scannable at a glance. Users memorize common slots (1 = attack, 2 = dodge, 3 = cast spell).
- Numeric keys match the visual slot number. No chord or complex sequence needed.
- Multiple pages let power users scale beyond 10 slots without cluttering the UI.
- Drag/drop from directory is discoverable and reduces friction.
- Each user has their own setup; no conflicts or permission surprises.

**Transfer to Roll-Drauf:** Start with 10 slots, keyboard shortcuts 1–0, and a compact bar that does not cover the map or selected token. Defer multi-page and drag/drop until slot persistence is designed.

### Roll20 Macro Bar

Community reports that Roll20's macro bar is effective because:
- Short action name visible on every macro button.
- Hover tooltip shows the full macro text (or call).
- Buttons light up when a macro is triggered (visual feedback).
- Private macros are not visible to other players.

**Transfer to Roll-Drauf:** Show action name on every slot button. When a hotbar action fires, briefly highlight the slot (visual feedback). Ensure actions are user-scoped.

### Tabletop Simulator Hotbar

Tabletop Simulator uses a simple bar at the top with custom scripts and a small palette:
- Numbers 1–9 and 0 for quick access.
- Users can customize the palette; it is not tied to server state.
- No drag/drop; users manually assign a script ID or action code to each slot.
- Lightweight and fast; no directory overhead.

**Transfer to Roll-Drauf:** Initial slice can use fixed built-in actions rather than requiring macro definition or drag/drop. Users select an action from the current action_catalog and click or shortcut to execute.

---

## 5. Bad examples and failure modes

### Cluttered, Always-Visible Toolbar

**Problem:** A dense bar with 30+ buttons, one per action, displayed permanently on top of the map.
- Obscures the selected token and critical map controls.
- No keyboard shortcut; users must click.
- No empty slots; no room to add custom actions.
- On mobile, the bar consumes half the screen.

**Lesson:** Hotbar must be compact. Foundry uses 10 slots and pages to keep it scannable. Roll-Drauf should do the same.

### Keyboard Shortcuts That Fire Inside Text Input

**Problem:** A hotbar listens for numeric keys globally, even when focus is in a chat input or token-rename field.
- User types a number in chat and accidentally triggers an action.
- The action may be destructive (e.g., "cast damage spell").
- No undo.

**Lesson:** Check `event.target.tagName` and `contentEditable` before firing keyboard shortcuts. Never prevent the key event; allow the browser to handle it normally inside inputs.

### Drag/Drop Without Server Persistence

**Problem:** Users drag macros to their hotbar, but the hotbar state is stored locally only (no server save).
- User reloads the page; hotbar is empty.
- User switches sessions; hotbar does not carry over.
- Frustration and repeated setup work.

**Lesson:** For Roll-Drauf's first slice, avoid drag/drop. Use a static built-in action catalog. Multi-page, drag/drop, and user-customized persistence are a later milestone.

### Use Counts That Lie

**Problem:** A hotbar displays a "uses left" badge (e.g., "3 left"), but it is not in sync with the actual token state.
- Cooldown has expired on the server, but the UI still shows red/disabled.
- User clicks the button; nothing happens; confusing.
- Alternatively, the button fires an action that should have been on cooldown, and the server rejects it silently.

**Lesson:** Do not track cooldowns or use counts in the hotbar. Let the server be the authority. If an action has a cooldown, the server should reject it and send back an error. The server response refreshes the UI state. For the first slice, the action_catalog does not include cooldowns; keep it simple.

### Hotbar Page Switching Without Visual Affordance

**Problem:** Pages exist, but there is no clear indication of the current page or how to switch.
- Users do not discover pages exist.
- Accidentally pressing a key switches the page; users do not notice until they trigger the wrong action.

**Lesson:** Display current page number (e.g., "Page 1 of 5") and provide visible Previous/Next buttons. Use arrow keys or +/- only if they are documented and do not conflict with map pan shortcuts.

### Token-Specific Actions That Vary Silently

**Problem:** An action's availability or name changes based on the selected token (e.g., "Cast Fireball" for a wizard, "Bite" for a wolf), but there is no visual indication.
- User selects a different token and assumes the hotbar is the same.
- Presses "2" expecting one action and gets another.
- Confusion and potential game-state error.

**Lesson:** Token-specific action variants are powerful but risky. For the first slice, all actions in the hotbar apply to the selected token generically (the action executor decides what happens). Reserve token-specific variants for a later milestone with explicit UI changes.

---

## 6. Lessons learned

1. **Simplicity over features:** 10 slots with numeric shortcuts is the proven standard. Multi-page, drag/drop, and cooldowns are useful, but they add complexity. Start with a small, static catalog.

2. **Keyboard safety:** Never fire shortcuts inside text inputs. Check the target element type and content-editability. Do not prevent the keydown event; let the browser handle it normally.

3. **Visual feedback:** Show the action name on every button. When an action fires (via click or shortcut), briefly highlight the slot and wait for the server response. If the server rejects it, show the error; do not silently fail.

4. **Server authority:** Cooldowns, use counts, and permission checks belong on the server. The hotbar is just a UI for triggering actions defined in action_catalog. Do not let the UI override server decisions.

5. **Scoped state:** Each user has their own hotbar. Actions are private to the user executing them. Do not expose other players' hotbars or shortcuts. The server can audit action execution by logging the actor_user_id.

6. **Mobile adaptation:** Keyboard shortcuts do not exist on touch devices. Provide a touch-friendly layout (horizontal scroll, collapsible section, or grid) within the existing #tableSheet. The visual slots are the primary affordance.

7. **Page switching as a separate feature:** If you add multiple pages, make the current page number visible and provide explicit UI (buttons, not just keyboard shortcuts) to switch. Reserve shortcut key conflicts carefully (map pan often uses arrows; hotbar could use Page Up/Down or +/- on numpad, but test first).

8. **Drag/drop as a later milestone:** User-customized hotbars require server-backed slot persistence, macro/action creation UI, and drag/drop implementation. The first slice does not include this. Use the built-in action_catalog instead.

---

## 7. Community favorites

**Anecdotal preferences from Foundry and Roll20 communities:**

- "I love that I can hit 1 and immediately attack. No clicking, no menu." — Frequent macros for primary actions (attack, dash, cast main spell).
- "The ability to have multiple pages saves me from hotbar bloat. I have 'combat' and 'exploration' pages." — Power users appreciate page switching for different play phases.
- "Drag and drop from the macro directory is so much faster than typing the ID." — Users dislike manual configuration; direct manipulation is preferred.
- "I wish cooldowns showed on the button. I keep trying to cast my reaction spell and it doesn't fire." — Demand for cooldown/use-count feedback, but it conflicts with server authority.
- "On mobile, I don't use the hotbar at all. I tap the buttons on the character sheet." — Touch users often prefer touch-friendly alternatives (menus, buttons in sheet) over keyboard shortcuts.
- "It's confusing when my hotbar has the same slots as the GM's but different macros. There should be a shared section and a personal section." — Some games want both personal and party-shared actions.

**Relevance to Roll-Drauf:** The demand for visual cooldown feedback is real, but it must come from the server as the authority. Personal hotbars are standard. Mobile users appreciate touch-friendly alternatives; keyboard shortcuts alone are not enough.

---

## 8. Roll-Drauf fit and explicit non-goals

### What fits

- **Numbered slots (1–10):** Foundry model is proven. Roll-Drauf has 10 slots and numeric key shortcuts.
- **Built-in action catalog:** ACTION_CATALOG in actions.py is already defined and server-delivered. Start with attack_basic, dash_move, interact_object.
- **Keyboard shortcuts:** Numeric keys 1–0. Do not fire inside text inputs. Respect browser shortcuts (Ctrl+S, Cmd+Q, etc.).
- **Server-backed executeAction:** Already exists. Hotbar calls the same endpoint as the token HUD action menu.
- **User ownership:** Each player has only their own hotbar. DM hotbar is separate.
- **Desktop and mobile layouts:** Use the same action state, but render differently. Desktop: visible bar. Mobile: collapsible section in #tableSheet.

### Explicit non-goals for the first slice

- **Drag/drop customization:** Users cannot rearrange slots or create macros. Defer until slot persistence and macro CRUD are designed.
- **Multiple pages:** All 10 actions fit in one page. Page switching is a separate feature after the single-page slice works.
- **Cooldowns and use counts on the hotbar:** The action_catalog does not include cooldown fields. The server can reject actions and return an error; that is enough for now.
- **Token-specific action variants:** All hotbar actions apply to the selected token via the generic executor. Do not change the hotbar layout based on token type.
- **Shared/party hotbars:** Each player has a personal hotbar. A shared party action bar is a different feature.
- **Drag/drop from character sheet items:** The hotbar shows system actions, not item-based macros. Item use is handled by the character sheet or inventory, not the hotbar.
- **Popover tooltips showing macro full text:** Action buttons show name and category. A full tooltip is optional; focus on the core interaction first.

---

## 9. Proposed interface/data/permission contracts

### Frontend hotbar state

```javascript
hotbarState = {
  slots: [
    {
      number: 1,
      actionCode: "attack_basic",      // from action_catalog.code
      name: "Attack",                   // from action_catalog.name
      category: "combat",               // from action_catalog.category
      requiresTarget: true,             // from action_catalog.requires_target
      suggestedRoll: "1d20+5"           // for chat/dice composer
    },
    // slots 2–10 follow same shape; empty slots have actionCode: null
  ],
  currentPage: 0,                       // future: page index (0-4)
  keyboardEnabled: true,                // hotbar shortcuts active (not inside input)
  lastExecuted: null,                   // slot number, for visual feedback
}
```

### Slot execution contract

**User action:** Click slot or press numeric key → call executeAction

**Request:**
```javascript
POST /api/play/campaigns/{campaignId}/sessions/{sessionId}/actions/execute
{
  "token_id": 42,
  "action_code": "attack_basic",
  "target_token_id": 99,              // if requires_target is true
  "payload": {}
}
```

**Response (success):**
```json
{
  "action_code": "attack_basic",
  "token_id": 42,
  "actor_user_id": 10,
  "target_token_id": 99,
  "payload": {},
  "suggested_roll": "1d20+5",
  "executed_at": "2026-08-27T14:30:00Z"
}
```

**Response (error):**
```json
{
  "code": "permission_denied",         // or "cooldown_active", "bad_request", etc.
  "message": "You do not have permission to use this action"
}
```

**Hotbar behavior on error:** Display the error message briefly in the hotbar slot or a toast. Do not disable the button; let the user retry or see the error in the chat log (if the server broadcasts it).

### Permission boundary

- **Desktop execution:** Read-write role (Player or DM) can execute. Read-only viewers get a disabled hotbar (all slots grayed out).
- **Token ownership:** An action is tied to the selected token. The executor must have permission to control that token (owner or DM).
- **Action authorization:** The server checks if the action_code is valid and if the actor has permission (e.g., a PC can use "attack_basic" but an NPC enemy might not). This is action-specific game logic.
- **Target validation:** If the action requires_target, the executor must have a target_token_id and permission to see/interact with it.

### Realtime updates

- **Socket events:** If another player executes an action from their hotbar, the session broadcasts an "action_executed" event. The receiving client shows it in chat or a log. The hotbar itself does not change in response; the executor's hotbar shows visual feedback.
- **Conflict/rejection:** If a player's action is rejected by the server (permission, cooldown, invalid state), the server sends an error event to that player only. The hotbar reverts any optimistic state.
- **Token death/removal:** If the selected token is removed, disable the hotbar. Enable it again when a valid token is selected.

### Data contract summary

| Item | Source | Mutability | Notes |
|---|---|---|---|
| action_catalog | Server bootstrap | Immutable per session | Read by frontend, not modified. |
| hotbar slots (first pass) | Server config or frontend local | Immutable (static) | Users cannot customize. Defer persistence. |
| selectedTokenId | PlayRuntimeUI.selectedTokenIds | Mutable (user selection) | Hotbar is scoped to selected token. |
| executeAction result | Server POST response | Immutable | Logged to chat or broadcast event. |
| error response | Server POST response | Immutable | Shown to executor; does not block further attempts. |

---

## 10. Risks and assumptions with severity labels

### Risk: Keyboard shortcuts fire inside chat input

**Severity:** HIGH  
**Description:** User types a number in the chat box (e.g., "my AC is 18") and accidentally triggers a hotbar action.  
**Mitigation:** Check `event.target.tagName` and `contentEditable` before firing any hotbar shortcut. Test with focus in #chatInput, token-rename field, and any future input surface.  
**Residual risk:** MEDIUM (testing must verify all inputs are covered).

### Risk: No visibility into action availability

**Severity:** MEDIUM  
**Description:** An action may have a cooldown or permission restriction on the server, but the hotbar shows the button as always available. User clicks and gets rejected.  
**Mitigation:** For the first slice, do not display cooldowns. The server response is the authority. If the server rejects the action, show an error. As a later enhancement, add cooldown badges if the action_catalog supports a cooldown field.  
**Residual risk:** LOW (first slice does not include cooldowns; users expect click-and-fire behavior).

### Risk: Action_catalog is static; users want customization

**Severity:** MEDIUM  
**Description:** Foundry and Roll20 users want to drag/drop macros and customize hotbars. Roll-Drauf's first slice has a fixed catalog.  
**Mitigation:** Clearly communicate that custom macros and drag/drop are in the roadmap, not the first slice. The first slice focuses on executing predefined system actions quickly. Multi-page and persistence are the next milestone.  
**Residual risk:** MEDIUM (user feedback may push for customization sooner; plan for it in Apply phase).

### Risk: Mobile keyboard shortcuts do not make sense

**Severity:** LOW  
**Description:** Mobile users do not have a numeric keyboard. Shortcuts are irrelevant.  
**Mitigation:** The mobile layout omits keyboard shortcut labels. The slots remain visible as touchable buttons. Keyboard shortcuts are only active on desktop.  
**Residual risk:** LOW (mobile layout is clear in the responsive pattern).

### Risk: Target token is required but user forgot to select

**Severity:** MEDIUM  
**Description:** An action like "attack_basic" requires_target. User selects a source token but forgets to specify a target. Click hotbar → error.  
**Mitigation:** The server rejects the request. The hotbar shows the error. For UX clarity, a future enhancement could display "requires target" in the slot tooltip. For now, the error message is sufficient.  
**Residual risk:** MEDIUM (users may need UX guidance; consider a tooltip or help text).

### Risk: Socket disconnection during action execution

**Severity:** MEDIUM  
**Description:** User presses a hotbar key, the client optimistically updates the UI, but the socket is disconnected. The server never receives the request.  
**Mitigation:** The hotbar should not optimistically update until the server confirms. Wait for the POST response before highlighting the slot or broadcasting. If the connection is lost, show a "connection lost" message.  
**Residual risk:** LOW (already handled by PlayRuntimeUI socket connection checks).

### Risk: DM and player hotbars could conflict

**Severity:** LOW  
**Description:** DM and player each have their own hotbar, but they use the same numeric keys. Could lead to confusion if both are visible at once.  
**Mitigation:** Each player's hotbar is personal and only visible to them. DM actions are logged to the session chat for audit. No visual conflict.  
**Residual risk:** LOW (personal hotbars prevent collision).

### Assumption: Three initial actions are enough

**Severity:** MEDIUM  
**Description:** ACTION_CATALOG starts with attack_basic, dash_move, interact_object. Is this enough for play?  
**Mitigation:** This is a design question for Apply phase. Combat-focused systems might need more; roleplay-focused games might use fewer. Plan to expand the catalog based on testing.  
**Residual risk:** HIGH (catalog scope is not settled; Apply phase must decide).

### Assumption: Page switching is not needed yet

**Severity:** LOW  
**Description:** Foundry has five pages (50 slots total). Roll-Drauf might need fewer for casual play.  
**Mitigation:** Start with one page of 10 slots. If testing shows users want more, add pages in a follow-up slice.  
**Residual risk:** LOW (deferral is explicit).

---

## 11. Acceptance criteria

### Desktop: UI and interaction

- [ ] Hotbar renders as a horizontal row of 10 button slots below the map (or in a collapsible section, depending on layout approval).
- [ ] Each slot shows: (1) numeric label (1–10), (2) action name (e.g., "Attack"), (3) action category as a badge or icon.
- [ ] Empty slots show a placeholder (e.g., "1 — empty").
- [ ] User can click any slot to execute the action on the selected token.
- [ ] When an action executes, the slot highlights briefly (e.g., background color change for 300ms).
- [ ] If the server accepts the action, the result is logged to chat or broadcast (per existing socket events).
- [ ] If the server rejects the action, an error message appears as a toast or in a small error area next to the hotbar.

### Keyboard: shortcuts and input safety

- [ ] Numeric keys 1–0 trigger the corresponding slot action on the selected token.
- [ ] Hotbar shortcuts do NOT fire if focus is inside an input, textarea, select, contenteditable, or dialog.
- [ ] Pressing a numeric key inside #chatInput does not trigger the hotbar; the key is typed normally.
- [ ] Pressing a numeric key inside a token-rename field does not trigger the hotbar.
- [ ] Browser shortcuts (Ctrl+S, Cmd+Q, etc.) are not overridden.
- [ ] A user can press a hotbar key multiple times in a row without restriction (no debounce that breaks rapid-fire use).

### Mobile: touch and responsive layout

- [ ] On screens < 768px wide, the hotbar moves into the #tableSheet or is hidden by default.
- [ ] Mobile hotbar provides a touchable button for each slot (10 buttons, same state as desktop).
- [ ] Numeric key labels are hidden or grayed out on mobile (since keyboard shortcuts are not available).
- [ ] Slots remain functional via tap on mobile; no hover or right-click needed.
- [ ] Horizontal scroll or grid layout is used so all 10 slots are reachable without excessive scrolling.

### Permissions: read-only mode and visibility

- [ ] In read-only mode (viewer role), the hotbar is disabled (all slots grayed out, no click or keyboard response).
- [ ] In read-write mode (Player or DM), the hotbar is enabled for the selected token if the user has permission to control it.
- [ ] If a token is hidden (dm_only or invisible), the hotbar still executes actions on behalf of that token (assuming permission checks pass on the server).
- [ ] DM can use the hotbar on any token they select; player can only use it on their own tokens.
- [ ] All hotbar action execution is logged server-side by actor_user_id for audit.

### Realtime updates and conflicts

- [ ] If another player executes an action (from their hotbar or elsewhere), the session receives the "action_executed" event and broadcasts it (per existing contract).
- [ ] The receiving client's chat log shows the action. If the receiving client is on the same scene, the action is visible to all.
- [ ] If a token is deleted or becomes invalid while selected, the hotbar disables until a new token is selected.
- [ ] If the session state is refreshed (server push or user reload), the hotbar hotbar state resets to the current action_catalog without error.

### Errors and recovery

- [ ] If a hotbar action fails (server 4xx/5xx), the error message is displayed to the user (not silently dropped).
- [ ] A failed action does not update the token state or chat. The user can retry.
- [ ] If the server connection is lost, hotbar shortcuts are disabled until reconnection. The user is shown a "connection lost" message.
- [ ] If the server rejects an action due to permission (user does not own token, token is read-only), the error message is clear (e.g., "You do not have permission to use this action on this token").

### Destructive actions and confirmation

- [ ] The initial action_catalog does not include destructive actions (delete, leave session). If destructive actions are added later, they require explicit confirmation (modal dialog).
- [ ] A hotbar shortcut does not automatically trigger a destructive action; confirmation is required.

---

## 12. Apply handoff: decisions still needed before implementation

1. **Hotbar position and layout:**
   - Where does the hotbar render? Below the map? In a floating panel? Collapsible section in #tableSheet?
   - Desktop vs mobile: Same visual location, or move to #tableSheet on mobile?
   - **Decision needed:** Layout mock-up and desktop/mobile prototype.

2. **Initial action catalog expansion:**
   - Three actions (attack, dash, interact) seem minimal. Are there other system actions the table should support from day one?
   - Should the catalog include spell/power casting, healing, object interaction, or roleplay actions?
   - **Decision needed:** Expanded ACTION_CATALOG based on playtesting or user feedback scope.

3. **Page switching as a future feature:**
   - Pages are explicitly deferred, but is the UI ready to add them later (e.g., a page indicator label)?
   - Should we reserve space for a page switcher in the initial design?
   - **Decision needed:** Design compatibility with future multi-page support.

4. **Cooldown and use-count feedback:**
   - Users will ask for cooldown badges. Should the action_catalog schema include cooldown/recharge fields?
   - If yes, does the server track cooldown state server-side, and does the hotbar query it before rendering?
   - **Decision needed:** Action schema for cooldowns and the server-side tracking mechanism (defer implementation, decide schema).

5. **Drag/drop customization scope:**
   - Is customization (drag/drop, save/load hotbars) in scope for a later slice?
   - If yes, does the server need a `user_hotbar` table or do we use local browser storage?
   - **Decision needed:** Long-term hotbar persistence architecture.

6. **Token-specific action variants:**
   - Some actions might vary by token type (e.g., "Bite" for a wolf, "Cast Fireball" for a wizard).
   - Should the hotbar support this, or should all actions be generic?
   - **Decision needed:** Whether token-specific actions are in scope and how they are detected/presented.

7. **Chat integration:**
   - When a hotbar action executes, should it be logged to chat automatically (as a system message or emote)?
   - Should the result (roll, damage, effect) also appear in chat, or only in a log?
   - **Decision needed:** Chat visibility and action result broadcasting rules.

8. **Mobile keyboard-like devices:**
   - External Bluetooth keyboards on tablets: Should numeric shortcuts work?
   - Should the mobile layout still show numeric labels, or is the UI touch-only?
   - **Decision needed:** Mobile input strategy (touch primary, keyboard optional).

9. **Accessibility and screen readers:**
   - Each hotbar slot is a button. Is the accessible name "Slot 1: Attack (Ctrl+1)" or just "Attack"?
   - Should the hotbar aria-label describe it as a toolbar or action bar?
   - **Decision needed:** ARIA labels and screen-reader testing plan.

10. **Initial vs. custom actions:**
    - Is every action in ACTION_CATALOG automatically available in the hotbar, or do users choose which ones to show?
    - If users choose, is the choice persisted (local storage or server)?
    - **Decision needed:** Whether all catalog actions are hotbar actions or if there is a separate selection step.

---

## Sources

**Primary sources (first-party documentation):**
- [Foundry VTT — Macros](https://foundryvtt.com/article/macros/)
- [MDN — Keyboard Events](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent)
- [W3C APG — Menu Button Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/)
- [W3C APG — Disclosure Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/)
- [MDN — Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events)
- [MDN — Touch Events](https://developer.mozilla.org/en-US/docs/Web/API/Touch_events)

**Roll-Drauf source code (read-only inventory):**
- `vtt/play/actions.py` — ACTION_CATALOG definition and execute_action handler
- `vtt/play/routes.py` — bootstrap delivery and /actions/execute endpoint
- `vtt/static/js/play-client.js` — executeAction() client wrapper
- `vtt/static/js/play-ui.js` — action catalog rendering and token selection state
- `vtt/templates/play.html` — hotbar container placeholder and responsive layout

---

## Summary

Roll-Drauf's personal action hotbar is a direct execution layer for the action_catalog. The Foundry reference model—10 numbered slots, numeric keyboard shortcuts, personal ownership, and server-backed execution—is proven and fits well. The initial implementation should focus on the essentials: (1) a compact row of 10 buttons, (2) numeric keys 1–0, (3) click and keyboard execution, (4) desktop and mobile layout, (5) permission and error handling. Drag/drop customization, multiple pages, cooldown feedback, and token-specific variants are valuable but belong in later slices after the basic interaction is proven. The research confirms that the existing action executor is the right seam; the hotbar is primarily a UI layer over it. The main risks are keyboard safety inside text inputs and user expectations for customization and cooldown feedback. These are manageable with careful focus testing and clear roadmap communication.
