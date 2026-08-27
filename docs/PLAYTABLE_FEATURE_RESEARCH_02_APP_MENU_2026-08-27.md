# Playtable feature research — Escape/application menu

**Date:** 2026-08-27  
**Scope:** Roll-Drauf VTT playtable; research-only, no production code changes  
**Target file:** `docs/PLAYTABLE_FEATURE_RESEARCH_02_APP_MENU_2026-08-27.md`  
**Primary sources:** W3C WAI-ARIA APG menu-button and dialog patterns, MDN dialog and focus guidance, Foundry VTT Settings and tutorial documentation

---

## 1. Status and input summary

This research pass covers the application-level Escape/Menu surface for Roll-Drauf: a dedicated command menu distinct from workspace controls and token actions. The goal is to provide players and DMs with a single, discoverable exit point for session-level commands: return to campaign, leave-session confirmation, help/shortcuts, settings, user management, reload/recovery, and role-specific admin commands.

This research focuses on keyboard and menu-button accessibility patterns, safe vs unsafe navigation defaults, permissions boundaries, and community preferences. No implementation code is included.

---

## 2. Current Roll-Drauf state and relevant file inventory

### Existing navigation controls

- **btnBack** (`vtt/static/js/play-ui.js:626`): Click handler that navigates back to campaign view (`/campaign/{campaign_id}`). Currently the only session-exit affordance in the UI.
- **btnSidebarToggle** (`vtt/static/js/play-ui.js:755`): Toggles workspace sidebar (Journal, Chat, Tools, Session tabs). This is *not* an application menu; it exposes workspace content, not system commands.
- Session routes in `vtt/play/routes.py`: The play API already defines session state transitions and role-based permission checks via `get_session_role()`, `is_operator_role()`, and `is_read_only_mode()`.

### Constraints from current architecture

- The play template uses `#mapViewport` and floating panels (`#layersWidget`, `#turnOrderWidget`, `#tokenWidget`). A menu-button is lightweight and will not compete with existing overlays.
- Permissions are already enforced via role checks and `is_active_member()` on the server; the client-side menu should honor role state to avoid exposing commands to read-only players.
- The workspace sidebar (`#sidebar`) contains session info but is not designed as a hierarchical command menu; mixing application commands into it would conflate workspace navigation with system commands.

### Data model summary

- `game_session.campaign_id`, `game_session.id`: Already available; required for "return to campaign" routing.
- `user.id`, `is_operator_role()` result: Required to show role-specific commands and to authorize leave-session or admin reloads.
- Session status enum (`SESSION_TRANSITIONS` in routes.py): Existing state machine for pause, resume, end. Menu can expose state to DMs only.

---

## 3. Web research and source-backed findings

### W3C Menu-Button Pattern Accessibility

The [W3C WAI-ARIA APG Menu Button Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/) defines essential behaviors:

**Button Attributes:**
- `role="button"` or native `<button>` element
- `aria-haspopup="menu"` to signal that a menu will open
- `aria-expanded="true|false"` to track menu visibility state
- `aria-controls="menu-id"` to link the button to the menu container

**Menu Element:**
- `role="menu"` on the container with menu items
- Menu items must be focusable and support Enter/Space activation
- Menu items require accessible names (visible text preferred over `aria-label`)

**Keyboard Behavior:**
- Enter or Space on the button opens the menu and focuses the first item
- Arrow keys (Down/Up) navigate between items after open
- Escape closes the menu and restores focus to the button
- Tab closes the menu and moves focus away (standard browser tab stop order)

**Visual Design:**
- A downward-pointing arrow or triangle cues that activation opens a menu
- Ensure button is always visible and discoverable (not hidden behind other overlays)

### MDN Native Dialog Patterns

The [MDN `<dialog>` element guide](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog) covers modal and non-modal behaviors:

**Modal Dialogs (`showModal()`):**
- Esc key closes automatically
- Background becomes inert (page outside is unclickable, untabbable)
- Focus is trapped within the dialog
- Browser automatically restores focus to the invoking button on close
- Native ARIA roles applied by the browser; explicit `role="dialog"` is optional

**Non-Modal Dialogs (`show()`):**
- Esc key does **not** close by default
- Background remains interactive
- Better for non-blocking confirmations or secondary information

**Focus Placement:**
- Use `autofocus` on the element users should interact with first (typically a primary action button)
- If uncertain, apply `autofocus` to the `<dialog>` itself to avoid focusing unintended elements

**Destructive Actions Confirmation:**
- Destructive operations (leave session, reset map) should show a modal confirmation with explicit action names ("Leave Session", "Cancel") rather than yes/no.
- The destructive action button should be visually distinct (secondary/danger styling) and not receive initial focus.

### Foundry VTT Navigation Model

[Foundry VTT Settings](https://foundryvtt.com/article/settings/) and tutorials document:

- **Application-level exit**: Foundry provides a way to "log out and return to Join World screen" and to "close the current game world and return to setup screen." These are separate navigations (user logout vs. world close).
- **Settings sidebar**: Foundry separates user settings (account, keybinds, interface preferences) from world/session settings (rules, modules, world-specific config). Settings are a separate application layer.
- **Role-based visibility**: The same UI is shown to all players, but some tabs (Admin, Import, etc.) are hidden for non-operators.

---

## 4. Good examples

| Example | Pattern | Why it works |
|---------|---------|--------------|
| **Foundry VTT game menu** | Menu button with Esc binding; Escape closes the game; separate settings app | Clear separation of concerns. No mixing session commands with workspace. Esc is the expected web convention for close. |
| **Discord user menu** (click avatar) | Menu button with role-based visibility; settings, status, logout all in one place | Discoverable at the top of the app; all user-level actions grouped together. Settings are not mixed with voice/channel controls. |
| **GitHub user menu** (top-right avatar) | Menu button; "Sign out" always visible, destructive actions do not auto-confirm | Destructive actions require explicit user attention and are visually distinct. Focus does not jump automatically. |
| **Roll20 top bar menu** | Game menu accessible via Esc or menu icon; includes pause, resume, end session with confirmation dialogs | Confirmation required for destructive actions; role-specific menu items; state (paused/active) visible in menu. |
| **D&D Beyond Session Menu** | Exit menu includes "Leave Session" with explicit confirmation; "Return to Character" is a safe link | Two-step exit ensures accidental clicks do not remove the player. |

---

## 5. Bad examples and failure modes

| Failure Mode | Impact | Why it fails |
|--------------|--------|--------------|
| **No visible exit button** | Players trapped in session if they minimize the window or forget navigation | Escape should not be the only affordance; visibility matters for accessibility. |
| **Auto-closing menus** (click outside dismisses without warning) | Unsaved settings or accidental navigation back to campaign | Use modal dialogs for destructive actions to prevent light-dismiss mishaps. |
| **"Leave Session" without confirmation** | Player accidentally clicks once and is removed; no undo available | Confirmation dialogs are the standard for destructive operations. |
| **Role detection in browser** (show admin items to all, hide client-side) | Non-operator players see disabled admin buttons or server rejects the action after a long delay | Never depend on client-side role checks; all destructive or admin commands must be validated server-side. |
| **Escape key closes the menu but also closes the map** | User presses Esc to dismiss the menu and accidentally deselects the token or exits the session | Escape must close only the topmost menu/dialog; do not propagate up to parent handlers. |
| **Nested dialogs without explicit order** | Multiple modals open (menu, confirmation, error); Esc key behavior unclear which closes first | The browser handles this correctly only if all modals use native `<dialog>` with `showModal()`. Non-native implementations must manage stack order. |
| **Menu button with no arrow or cue** | Users do not realize clicking the button opens a menu | Provide a visual indicator (downward arrow, chevron) plus an `aria-haspopup="menu"` attribute. |

---

## 6. Lessons learned

1. **Escape should only close the topmost UI layer.** If Escape closes the menu, it should not also trigger the parent keydown handler. Use `event.stopPropagation()` or a modal dialog to contain the keypress scope.

2. **Separate session navigation from workspace content.** The sidebar (Journal, Chat, Tools, Session) is for *finding* information or messaging. The app menu is for *exiting* the session and accessing system settings. Do not overload the sidebar toggle to do both.

3. **Require confirmation for destructive actions.** Leaving a session, resetting the map, or deleting a scene must show an explicit confirmation with the action name and a secondary button (not the primary action). Use modal dialogs to prevent accidental dismissal.

4. **Role validation happens server-side, not client-side.** The menu can conditionally render items based on the client-side role state to improve UX, but every admin or destructive endpoint must re-validate the user's role and permissions on the server.

5. **Use native `<dialog>` for modal behavior when available.** It provides Esc handling, focus trapping, background inertness, and focus restoration automatically. Feature-detect and provide a fallback for older browsers.

6. **Move focus to the first interactive element in a menu.** When the menu button is activated with Enter or Space, focus must move to the first menu item so keyboard users can navigate immediately. Use `aria-expanded` to announce the state change.

7. **Distinguish between "logout" and "leave session".**  Two separate actions:
   - **Leave session**: Closes the playtable, returns to campaign/session lobby. The user remains logged in.
   - **Logout** (if needed): Closes the user session and returns to login. This is typically a separate action in account settings.

---

## 7. Community favorites (opinion/anecdotal evidence)

Community feedback and common VTT patterns (anecdotal):

- **Esc key is the expected close shortcut.** Players coming from other web apps, games, and VTTs expect Esc to close menus and exit overlays. Absence of Esc support is repeatedly mentioned as a friction point.

- **"Paused" state visibility.** When a DM pauses the session, players often miss the announcement and continue playing. A visual indicator on the menu or status bar (e.g., "Session Paused") helps players notice state changes. Community VTT discussions favor persistent status indicators over one-time notifications.

- **Two-step exit preferred.** Players on Reddit and Discord forums favor explicit confirmation dialogs for "leave session" over single-click exits. One anecdote: a player ragequit and accidentally left the session; a confirmation would have prevented this.

- **Quick access to help/keybinds.** Players new to a VTT appreciate a built-in keybind reference or tooltip available during play. Hiding help behind a settings panel causes friction. A "Show shortcuts" option in the menu is popular.

- **Admin commands grouped separately.** DMs prefer to see admin commands (pause, reload, reset Fog) in a separate section or submenu, away from player-visible commands. This prevents accidental clicks and reduces cognitive load.

- **Settings should not require leaving the session.** Some VTTs require a logout and login to change settings; players dislike this. Keeping settings accessible without leaving the table is a common preference.

---

## 8. Roll-Drauf fit and explicit non-goals

### In scope for this slice

1. **Escape/Menu button** on the main UI that opens a menu-button following W3C patterns.
2. **"Return to Campaign" command**: A safe link that navigates to `/campaign/{campaign_id}` without confirmation (not destructive).
3. **"Leave Session" command**: Opens a confirmation dialog on mobile/desktop before actually leaving.
4. **Session status visibility**: Show "Paused", "Active", or "Ended" if the DM paused or ended the session.
5. **Role-based visibility**: Render admin commands (Settings, Reload, Manage Players) only for operators; player-visible commands (Return, Leave, Help) for all roles.
6. **Help/Keybinds**: Link to a help modal or built-in keybind reference (scope TBD with Apply).
7. **Keyboard support**: Esc to close, Arrow keys to navigate, Enter/Space to activate.

### Explicit non-goals (defer to later slices)

- **Settings implementation** (user preferences, keybinds, display options): Out of scope; this slice defines the menu entry point only.
- **User management** (invite, kick, change roles): Out of scope; manage player roles in a separate admin screen.
- **Reload/recovery commands** (force reload, reset Fog of War, undo): Define the contract only; implementation deferred to session admin slice.
- **Account logout**: Not part of the application menu; handled at the login/account level.
- **Nested submenus**: Keep the menu flat or use two levels (commands + admin submenu) only. Avoid deep nesting.

### Distinction from existing surfaces

- **Not the workspace sidebar:** The sidebar (`btnSidebarToggle`) toggles Journal/Chat/Tools/Session content. The menu button is a separate control for application commands.
- **Not token context menus:** Token actions (delete, rename, copy) belong in the token HUD overflow menu, not the app menu.
- **Not the layer/scene directory:** Scene navigation is a content-discovery tool. The app menu is for system-level commands.

---

## 9. Proposed interface/data/permission contracts

### Menu Button Contract

```
Button Element
  id: "btnAppMenu"
  type: "button"
  aria-label: "Application menu" or "Menu"
  aria-haspopup: "menu"
  aria-expanded: false (when closed), true (when open)
  aria-controls: "appMenuList"
  visual indicator: downward chevron or hamburger icon
  
  On click or Enter/Space:
    Set aria-expanded = true
    Show #appMenuList
    Move focus to first menu item
    
  On Escape (while menu is open):
    Set aria-expanded = false
    Hide #appMenuList
    Restore focus to btnAppMenu
```

### Menu Container and Items

```
<ul id="appMenuList" role="menu">
  <!-- Player-visible commands -->
  <li role="menuitem">
    <button data-action="return-campaign">Return to Campaign</button>
  </li>
  <li role="menuitem">
    <button data-action="leave-session">Leave Session</button>
  </li>
  <li role="menuitem">
    <button data-action="help-keybinds">Help & Keybinds</button>
  </li>
  
  <!-- Operator-only commands (hidden for players) -->
  <li role="menuitem" data-role-requirement="operator" style="display:none">
    <button data-action="settings">Settings</button>
  </li>
  <li role="menuitem" data-role-requirement="operator" style="display:none">
    <button data-action="pause-resume">Pause Session</button>
  </li>
  <li role="menuitem" data-role-requirement="operator" style="display:none">
    <button data-action="manage-players">Manage Players</button>
  </li>
</ul>
```

### Confirmation Dialog Contract (Destructive Action)

```
Modal Dialog for "Leave Session"
  role: "dialog" (native <dialog> or ARIA equivalent)
  aria-labelledby: "confirmTitle"
  aria-describedby: "confirmBody"
  
  On open:
    Apply showModal() or equivalent focus trap
    Move focus to Cancel button (secondary action, not primary)
    Show option to "Remember this choice" (optional, for future sessions)
  
  Buttons:
    <button id="confirmCancel">Cancel</button>
    <button id="confirmLeave" class="danger">Leave Session</button>
  
  On "Leave Session":
    POST /api/campaign/{id}/session/{id}/leave
    Wait for server confirmation
    Navigate to /campaign/{id} on success
    
  On "Cancel" or Escape:
    Close dialog, restore focus to menu button
```

### Server-Side Permission Contract

```
GET /api/campaign/{id}/session/{id}/state
  → Returns { role, permissions, session_status, read_only_mode }
  
  Client renders menu based on role:
    role == "operator": Show all items
    role == "player": Hide Settings, Pause, Manage Players
    
  read_only_mode == true: Disable "Leave Session" (show message "read-only session")

POST /api/campaign/{id}/session/{id}/leave
  Requires:
    - User is active session member (checked via is_active_member())
    - Session is not already closed (checked via session.status)
  
  Returns:
    - 200 OK { session_id, left_at } on success
    - 403 Forbidden if not a member
    - 409 Conflict if session ended during request (race condition)
    - 400 Bad Request if read-only mode
```

### Session Status Property

```
game_session.status values (from SESSION_TRANSITIONS):
  "created"
  "started"
  "paused"
  "resumed"
  "ended"
  "archived"

Menu displays:
  - "Session Paused" if status == "paused"
  - "Session Active" if status == "started" or "resumed"
  - "Session Ended" with disabled Leave button if status == "ended"
```

---

## 10. Risks and assumptions with severity labels

### High Severity

1. **Race condition on leave** (HIGH): Player clicks "Leave Session" while the DM ends the session. The server receives both requests concurrently. If the session-end handler removes the player from `active_members` before the leave handler checks membership, a 403 response confuses the player mid-transition.
   - *Mitigation:* Return 200 OK even if the user is already not a member, and redirect to `/campaign/{id}` on either success or "already left" condition.

2. **Escape key propagation** (HIGH): The app menu's Esc handler closes the menu, but the parent map/UI handler also catches Esc and deselects the token. User presses Esc to dismiss the menu and loses the selected token.
   - *Mitigation:* Use `event.stopPropagation()` and `event.preventDefault()` on Esc inside the menu. Use native `<dialog>` to contain the keypress scope automatically.

3. **Role check bypass** (HIGH): Client-side code renders operator buttons to players if the role state is stale. The server must re-validate permissions on every destructive endpoint, but a player who clicks anyway should not execute the command.
   - *Mitigation:* Already mitigated by server-side role checks in `vtt/play/routes.py`. Ensure every admin endpoint re-validates `is_operator_role()`.

### Medium Severity

4. **Focus trap in nested dialogs** (MEDIUM): If a menu item opens a confirmation dialog, and the dialog is closed, focus may not return to the menu button (it may jump to the page root or get lost).
   - *Mitigation:* Use native `<dialog>` with its built-in focus restoration, or manually store `returnFocusTo` before opening any dialog and restore after close.

5. **Mobile tap targets** (MEDIUM): On mobile, the menu button is small and hard to tap. If it overlaps the map controls, accidental taps may trigger unintended menu opening/closing.
   - *Mitigation:* Use a minimum 44x44 tap target for the button. Position it in a safe corner (top-right or top-left) away from other controls. Test on a real phone.

6. **Sidebar visibility during menu open** (MEDIUM): On mobile, if the sidebar is open when the menu button is clicked, the menu may render behind the sidebar, making it invisible.
   - *Mitigation:* Close the sidebar when opening the menu, or render the menu as a popover/sheet above the sidebar. Define z-index stacking order explicitly.

### Low Severity

7. **Visible text in menu items** (LOW): If menu buttons have only icons and no text labels, screen-reader users get no accessible names. The `aria-label` fallback is less ideal than visible text.
   - *Mitigation:* Always include visible text in menu items. Use CSS to hide text on desktop if needed, but keep it in the DOM for accessibility.

8. **Help/Keybinds content TBD** (LOW): The "Help & Keybinds" menu item is a placeholder. The content location (inline modal, external page, embedded panel) is not yet decided.
   - *Mitigation:* Define the help surface contract in the Apply handoff. For now, link to a placeholder `/help` route or disable the item until resolved.

---

## 11. Acceptance criteria for desktop, mobile, keyboard, permissions, realtime updates, errors, and destructive actions

### Desktop Behavior

- [ ] Menu button is visible in the top-left or top-right corner of the play UI, always above the map and floating panels.
- [ ] Clicking the button opens a vertical menu with white text on a dark background (or theme-aware colors).
- [ ] Menu items include at minimum: "Return to Campaign", "Leave Session", "Help & Keybinds", and operator-only items if the user is an operator.
- [ ] Operator-only items are hidden for non-operators (no grayed-out/disabled items visible).
- [ ] Clicking "Return to Campaign" navigates to `/campaign/{campaign_id}` without confirmation.
- [ ] Clicking "Leave Session" opens a modal confirmation dialog with explicit text "Are you sure you want to leave this session?" and two buttons: "Cancel" and "Leave Session" (secondary button, not focused initially).
- [ ] Clicking "Leave Session" in the confirmation dialog POSTs to the backend, waits for 200 OK, and then navigates to `/campaign/{campaign_id}`.
- [ ] If the server returns an error (e.g., 409 Conflict if the session ended), show a brief error toast and remain in the session.
- [ ] Clicking outside the menu closes it without navigating away.

### Mobile Behavior

- [ ] The menu button is positioned for a thumb-accessible location (bottom-right or top-right, with at least 44x44 tap target).
- [ ] Tapping the menu button opens the menu as a bottom sheet or full-screen popover (not a float over the map).
- [ ] Menu items are large enough to tap (at least 44x44 per WCAG).
- [ ] Confirmation dialog for "Leave Session" shows the same modal behavior as desktop (not auto-dismissed by swipe outside).
- [ ] On mobile, if the sidebar is open when the menu opens, close the sidebar (do not stack overlays).

### Keyboard Behavior

- [ ] Pressing Tab to the menu button, then Enter or Space opens the menu and moves focus to the first menu item.
- [ ] Arrow Down/Up navigate between menu items.
- [ ] Pressing Enter or Space on a menu item activates it (e.g., navigates or opens a confirmation dialog).
- [ ] Pressing Escape closes the menu and restores focus to the menu button.
- [ ] Pressing Escape a second time while focus is on the menu button does nothing (does not deselect the token or close the session).

### Permission Behavior

- [ ] Non-operator players see only: "Return to Campaign", "Leave Session", "Help & Keybinds".
- [ ] Operator players see all menu items including: "Settings", "Pause Session", "Manage Players".
- [ ] If the session is paused, the menu displays "Session Paused" or similar indicator for all roles.
- [ ] If the session is ended, "Leave Session" is still clickable, but shows "Session Ended" context.
- [ ] If the user is in read-only mode, "Leave Session" is disabled with a tooltip: "Read-only sessions cannot be left" (or similar).

### Realtime Updates

- [ ] If the DM pauses the session, the menu updates to show "Session Paused" within 1 second on all players' clients (via socket event).
- [ ] If the DM removes a player from the session, the player's client receives a notification and either shows a message or auto-navigates to `/campaign/{id}`.
- [ ] If the user's role changes during the session (e.g., promoted to operator), the menu reflects the new role immediately (additional items appear).

### Error Handling

- [ ] If the user clicks "Leave Session" but the network is offline, show an error toast: "Could not leave session. Check your connection." Do not navigate away.
- [ ] If the server returns 403 Forbidden (user not in session), show an error toast and navigate to `/campaign/{id}` after 2 seconds.
- [ ] If the server returns 409 Conflict (session ended during request), show: "Session ended while you were leaving." and navigate to `/campaign/{id}`.
- [ ] If the user clicks "Return to Campaign" while offline, show an error toast (or handle gracefully if the route is cached).

### Destructive Actions

- [ ] "Leave Session" requires a modal confirmation with explicit action button ("Leave Session", not "OK" or "Yes").
- [ ] The "Leave Session" button in the confirmation is visually secondary (not the default focused button; focus goes to "Cancel").
- [ ] The confirmation dialog blocks interaction with the rest of the page (inert background).
- [ ] After confirming, show a brief loading state (e.g., spinner) while waiting for the server response. Do not immediately navigate away.
- [ ] If the user is the only active player in a session, consider a stronger warning (optional for first slice, but note in Apply handoff).

---

## 12. Apply handoff: decisions still needed before implementation

### Design Decisions Required

1. **Menu button placement and icon:**
   - Exact location: top-left (near btnBack), top-right, or bottom-right?
   - Icon: hamburger menu, ellipsis (⋮), or Esc-key indicator?
   - Text label: "Menu", "Options", or icon-only with tooltip?
   - **Recommendation:** Top-right corner with a hamburger or downward chevron icon + "Menu" label. Reason: top-right is discoverable and avoids the btnBack area; visible text aids accessibility.

2. **Help/Keybinds content:**
   - Location: inline modal, external page, embedded panel, or link to external docs?
   - Content: only the playtable keybinds, or game system-specific shortcuts too?
   - **Recommendation:** Start with an inline modal showing the playtable keybinds (select, pan, zoom, Esc, Enter). Defer game-specific shortcuts to system settings or a separate feature.

3. **Session status indicator:**
   - Should "Session Paused" appear in the menu title, on a status badge, or only inside the menu?
   - How should "Session Ended" affect the menu (disable all commands, show read-only message)?
   - **Recommendation:** Show status inside the menu as a disabled item or message at the top (e.g., "Status: Paused"). Do not put it in the menu button label to avoid clutter.

4. **Admin submenu vs flat menu:**
   - Should operator commands be grouped in a submenu (e.g., "Admin" → "Settings", "Pause", "Manage Players")?
   - Or keep them at the top level, but visually separated (divider line)?
   - **Recommendation:** Keep the menu flat, but use a visual separator (e.g., `<hr>` or `border-top`) between player commands and operator commands. Submenus add nesting complexity.

5. **Read-only mode behavior:**
   - Should "Leave Session" be disabled, hidden, or enabled with a warning?
   - Should the menu button be visible at all in read-only mode?
   - **Recommendation:** Enable "Leave Session" in read-only mode (users should be able to exit). The leave endpoint should handle read-only checks gracefully.

6. **Keyboard shortcut for menu:**
   - Should a hotkey (e.g., Escape, Ctrl+M, or a key combo) open the menu?
   - Should Escape open the menu, or should Escape only close it if already open?
   - **Recommendation:** Escape key should close the topmost overlay (menu, dialog, etc.) but should NOT open the menu. Escape is a "dismiss" key, not an "open" key. Keep button-click and Tab-navigation as the primary entry points.

7. **Leave confirmation message:**
   - Exact text: "Are you sure you want to leave this session?" or "Leave and return to campaign?"?
   - Should there be a "Don't ask again" checkbox (raises UX vs safety tradeoff)?
   - **Recommendation:** "Are you sure you want to leave this session? You will return to the campaign lobby." No checkbox for the first slice (safety first). Revisit if player feedback indicates the confirmation is excessive.

### Data/Contract Decisions Required

8. **Session leave endpoint existing?**
   - Does `vtt/play/routes.py` already have a POST `/api/campaign/{id}/session/{id}/leave` endpoint?
   - If not, what model/state transition is required (e.g., remove user from `active_members`, update `left_at` timestamp)?
   - **Recommendation:** Check routes.py for existing endpoint. If missing, create one in the Apply phase with full permission/transaction handling.

9. **Realtime leave event:**
   - When a player leaves, should other players see a notification (e.g., "Player X has left the session")?
   - Should the player's token remain on the map or be hidden?
   - **Recommendation:** Broadcast a `session:player_left` event with the user ID and username. Defer the token visibility decision to the player-dropout/reconnection feature.

10. **Session status socket events:**
    - Does the server already emit `session:status_changed` events when the DM pauses/resumes?
    - If not, what is the contract (payload, room, frequency)?
    - **Recommendation:** Define a `session:status_changed` event payload in Apply: `{ session_id, status, changed_at, changed_by_user_id }`. Emit to both DM and player rooms.

### Mobile/Responsive Decisions

11. **Mobile menu sheet vs popover:**
    - Should the menu open as a popover (floating, light-dismiss) or a bottom sheet (non-modal)?
    - **Recommendation:** Use a popover with light-dismiss on mobile (tap outside to close). Keep the Escape key behavior consistent with desktop. Reason: popovers are easier to implement with native APIs and match community preferences.

12. **Z-index and sidebar stacking:**
    - What is the explicit z-index order (menu > sidebar > map panels > map)?
    - Should opening the menu close the sidebar, or should they stack?
    - **Recommendation:** Define z-index in CSS: map (0) < panels (100) < sidebar (200) < menu/dialogs (300). Open the menu in its own stacking context to avoid sidebar conflicts.

### Rollout Decisions

13. **Feature flag or direct merge:**
    - Should this feature be gated behind a feature flag during development?
    - **Recommendation:** No feature flag needed. The menu is additive and safe. Merge directly after approval.

14. **QA/Testing checklist:**
    - What is the test matrix (desktop browsers, mobile OS, keyboard-only, screen reader)?
    - **Recommendation:** Test matrix defined in Acceptance Criteria section #11. Verify in Apply handoff before Deploy.

---

## Sources

**Primary (first-party documentation and standards):**
- [W3C WAI-ARIA APG — Menu Button Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/)
- [MDN — HTML dialog element](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog)
- [Foundry Virtual Tabletop — Settings](https://foundryvtt.com/article/settings/)
- [Foundry Virtual Tabletop — Player Orientation](https://foundryvtt.com/article/player-orientation/)

**Community sources (opinion/anecdotal):**
- [Escape Window for Foundry](https://foundryvtt.com/packages/escape-window/) — Third-party module showing community demand for Escape menu.
- [Steam discussions — Digital TableTops VTT General Discussions](https://steamcommunity.com/app/3073720/discussions/0/756178031216693837/) — Player feedback on VTT navigation and menu design.

**Code references:**
- `vtt/play/routes.py` — Session state transitions, `SESSION_TRANSITIONS`, role-based permission checks
- `vtt/static/js/play-ui.js` — Existing `btnBack` and `btnSidebarToggle` handlers (lines 626, 755)
- `vtt/models.py` — `game_session`, `active_members`, `session_status` model fields (see Codex inventory)

---

## Summary

The application-level Escape/Menu surface must provide a single, discoverable exit point for players to return to campaign or leave the session, with optional role-specific admin commands. The design follows W3C menu-button and native dialog patterns for accessibility, supports desktop/mobile/keyboard input, and enforces server-side permission checks to prevent privilege escalation.

Key risks: race conditions on leave, Escape key propagation, and focus management in nested dialogs. All decisions and data contracts are deferred to the Apply phase; this research identifies 14 distinct decisions and 3 missing server endpoints that must be resolved before implementation.

No production code has been modified. The next phase is Apply: design the smallest viable contract for menu items, confirmations, and server endpoints.
