# Roll composer and chat dock — feature research

**Date:** 2026-08-27  
**Scope:** Compact chat/dice composers for the Roll-Drauf VTT playtable  
**Status:** Research complete; ready for Apply phase design decisions  
**Sources:** Foundry VTT official chat/dice documentation, W3C input/focus guidance, MDN Web APIs, and current Roll-Drauf implementation audit

## 1. Status and input summary

This slice covers the tight end-user loop for table communication: message input, dice composition, roll visibility (public/private/GM/blind/self), roll result presentation, and chat history. The research separates roll mathematics from visibility policy, distinguishes roll modes from message types, and grounds recommendations in the existing `chatInput`, `btnSendChat`, `diceInput`, `btnRoll`, socket roll events, and `chatLog`.

The goal is a keyboard-accessible, touch-friendly composer that does not require modeless interaction or right-click menus for core workflows.

## 2. Current Roll-Drauf state and relevant file inventory

### Existing implementation

- **Chat input surface**: `vtt/templates/play.html` lines 1767–1779 define `#chatLog`, `#chatInput`, and `#btnSendChat` in a sidebar panel.
- **Dice input surface**: `vtt/templates/play.html` lines 1794–1802 define `#diceInput`, `#btnRoll`, `#diceResult`, and `#diceLog` in the Tools panel.
- **Token visibility default**: `vtt/static/js/play-ui.js` line 1111 defaults created tokens to `"public"` visibility; line 2587 filters tokens by visibility state.
- **Visibility model**: Token fields include `visibility` as a string enum (`"public"` vs `"dm_only"`), but there is no yet-defined chat message or roll visibility schema.
- **Roll events**: `btnRoll` click handler exists but does not yet have per-session broadcast or role/permission checks.
- **Socket events**: `play-socket.js` defines the realtime-update seam; roll events are not yet integrated.

### Data structures in scope

- **Chat log**: Plain-text history in `#chatLog` element; no message metadata (author, timestamp, visibility, roll details).
- **Dice result**: `#diceResult` and `#diceLog` show raw output; no formatting, color coding, or expandable roll details.
- **Session role**: `PlayRuntimeUI.userRole` (e.g., `"dm"`, `"player"`) determines DM-only surfaces.
- **Server authorization**: Routes in `vtt/play/routes.py` already validate session membership; role-based permissions are defined but not yet applied to chat/roll endpoints.

### Identified gaps

1. No chat message schema: author, timestamp, type (message vs roll), visibility mode, content, roll formula, and result.
2. No roll-composition API: requests to roll with a formula, modifiers, advantage state, and visibility do not yet round-trip through the server.
3. No broadcast contract: roll events sent via socket do not carry full metadata for clients to render them correctly (e.g., roll details, formula, visibility for the receiving user).
4. No keyboard shortcuts: no Enter-to-send, Shift+Enter for multiline, or number keys for die presets.
5. No mobile input accommodation: text inputs are not optimized for touch soft keyboards or small screens.

## 3. Web research and source-backed findings

### Foundry VTT chat and roll model

Foundry's chat system distinguishes between three independent facets: [https://foundryvtt.com/article/chat/](https://foundryvtt.com/article/chat/)

**Message types** (in-character `/ic`, out-of-character `/ooc`, emotes `/emote`, whispers `/whisper`):
- Separate author voice from roll results. A message is a narrative unit; a roll is a mechanical unit.
- Whispers require explicit recipient selection and "Whisper Private Messages" permission.
- Chat bubbles can appear above tokens for in-character messages.

**Roll modes and visibility** ([https://foundryvtt.com/article/dice/](https://foundryvtt.com/article/dice/)):
- **Public roll** (`/publicroll` or `/pr`): Visible to all players.
- **GM roll** (`/gmroll` or `/gmr`): Visible only to the roller and GMs.
- **Blind roll** (`/blindroll` or `/br`): Visible only to GMs; the roller does not see the result.
- **Self roll** (`/selfroll` or `/sr`): Visible only to the user who rolled it.
- Roll mode is **independent** of message content. A player can type a message, then roll with any visibility mode.

**Roll composition syntax**:
- Formula: `{number}d{faces}`, e.g., `1d20` or `5d12`.
- Modifiers: `+`, `-`, `*`, `/` for arithmetic. Example: `1d20 + 5` or `2d6[slashing] + 1d8[fire]`.
- Brackets allow descriptive labels: `[slashing damage]` or `[fire damage]`.
- Inline rolls: `[[formula]]` in text execute immediately; `[[/roll formula]]` create clickable buttons.

**Key Foundry rule**: The `/roll` command always produces a public roll regardless of the selected roll mode dropdown. Roll mode applies only to dedicated roll commands (`/gmroll`, `/blindroll`, etc.), not to inline rolls in messages.

### W3C input and focus guidance

[W3C Authoring Practices Guide — Combobox Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/):
- Text inputs with dropdown suggestions (die presets, modifiers) should use `aria-autocomplete="list"`, `aria-expanded`, `aria-owns`, and `aria-controls`.
- Arrow keys navigate the suggestion list; Enter confirms the selected item.

[W3C APG — Disclosure Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/):
- Roll-result expansion (showing individual dice, modifiers, breakdowns) should use a native `<button>` with `aria-expanded` and `aria-controls`.
- Not a menu; a disclosure toggles visibility of static content.

[MDN — Keyboard Events](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent):
- `Enter` (without modifier) submits; `Shift+Enter` allows multiline in a textarea.
- `Escape` cancels or dismisses a popover.
- Do not trap keyboard focus in a single input; allow Tab to exit and return.

### Mobile and touch input

[MDN — Touch Events](https://developer.mozilla.org/en-US/docs/Web/API/Touch_events):
- Avoid hover-only interactions. All commands must have a visible tap target.
- Text input soft keyboards may occlude composer controls; reflow the composer when the keyboard appears.
- Use `input type="text"` with `inputmode` (e.g., `inputmode="decimal"` for die counts) for soft keyboard hints.

## 4. Good examples

### Foundry's chat and roll model (tight separation of concerns)

- **Strength**: Roll mode (public/GM/blind/self) is stored with the roll event, not the message. A player can write a narrative message and roll with any visibility mode. The UI presents both as a single composite action but keeps the mechanics clean.
- **Adaptation**: Separate Roll-Drauf's roll formula input and roll-mode selector from the message input. Do not force every message to include a roll, and do not hide visibility behind a button that looks like a message action.

### Slack's message composer (progressive disclosure)

- **Strength**: The main input is a single text field. Advanced options (formatting, emoji, threads, reactions) are discoverable behind buttons or keyboard shortcuts. The composer does not force the user to choose options before typing.
- **Adaptation**: Roll-Drauf's composer can start with a simple message input, then reveal die presets, modifier stepper, and roll-visibility toggle only when the user is composing a roll.

### D&D Beyond character sheet actions (preset die shortcuts)

- **Strength**: Frequently used rolls (Attack, Spell Save, Ability Check) are numbered buttons with keyboard shortcuts (1–9). Hovering or clicking shows the underlying formula.
- **Adaptation**: Reserve a short row of quick-roll buttons (d20, d20 ADV, d20 DIS, and 1–2 custom presets) near the formula input. Add number-key shortcuts if the user enables them in settings.

### Roll20's roll expansion panel (inline formula + result details)

- **Strength**: A roll result shows the total first, then expands to show individual dice, modifier breakdowns, and reroll/modifier buttons. Result details fold away after a few seconds or on user dismissal.
- **Adaptation**: Chat log entries should show a roll result as a single line (e.g., "Attack: 17 (1d20+2)") with a [+] disclosure to expand full details. Do not auto-collapse; let the user choose.

## 5. Bad examples and failure modes

### Always-open chat composer with no keyboard entry (touch-only)

- **Failure**: If the composer requires a visible tap-only button to submit or toggle visibility, keyboard users and users with assistive technology cannot use the full workflow.
- **Avoidance**: Implement Enter-to-send as the primary submission path. Provide a `Tab`-accessible button as a fallback only if keyboard entry is unavailable.

### Roll mode hidden in an icon-only button or color-coded mode

- **Failure**: The current roll-visibility state is not readable at a glance. The user rolls blindly, then discovers after rolling that the mode was wrong.
- **Avoidance**: Display the selected roll mode as explicit text (e.g., "Public", "GM Only", "Blind") or in a labeled dropdown, not just as a button color or icon.

### Modal roll-result popover that blocks further input

- **Failure**: After rolling, if the result is displayed in a modal dialog, the user cannot immediately see the chat log or compose a follow-up message.
- **Avoidance**: Roll results should expand inline in the chat log or appear as a non-modal notification. Allow the user to continue typing a message while a roll result is visible.

### Multiline input that consumes Shift+Enter for submission

- **Failure**: In a textarea, Shift+Enter should allow a line break, not submit. If the composer treats Shift+Enter as submit, the user cannot write multiline messages.
- **Avoidance**: Use Enter alone for submission. Use `<textarea>` (not `<input type="text">`) if multiline messages are supported, and reserve Shift+Enter for line breaks.

### Advantage/Disadvantage as a single toggle button with no label

- **Failure**: The user does not know whether the current state is normal, advantage, or disadvantage. A three-state toggle is ambiguous.
- **Avoidance**: Use a labeled radio-button group or dropdown: "Normal", "Advantage", "Disadvantage". Display the current state as text.

### Roll permission enforcement only on the client

- **Failure**: A player crafts a blind roll locally, the client sends it as blind to the server, but the server does not re-validate. If the client is later modified, the player can cheat.
- **Avoidance**: The server must check the user's role and permissions before accepting a roll with a given visibility mode. A player's blind-roll request should be rejected server-side.

## 6. Lessons learned

1. **Visibility is a server concern**, not a client display preference. The server owns the source of truth: who can see what. The client displays the user's view, but never trusts a visibility claim in a browser message.

2. **Roll mode is independent of message content**. A roll is a mechanical action with a formula and visibility scope. A message is a narrative unit. Do not couple them; allow both to exist independently in chat history.

3. **Enter submits, Shift+Enter breaks lines** (if multiline is supported). This is the web-standard convention and works with assistive technology. Avoid modal or pointer-only submission.

4. **Expand roll results optionally, not by default**. A long list of individual dice clutters the chat log. Show the total first, then let the user expand if they want details.

5. **Presets reduce cognitive load**. Offering d20, d20 ADV, d20 DIS, and a few custom buttons as quick-click options removes the need to type formulas for common actions. But do not require presets; allow freeform entry.

6. **Mobile needs explicit affordances, not hover or right-click**. A button to toggle roll mode, a visible die-preset row, and a large text input are easier on touch than discovering a menu by right-clicking.

## 7. Community favorites (opinion/anecdotal evidence)

- **Preset die buttons are praised**: D&D Beyond and Roll20 communities love numbered quick-access slots for frequent rolls (d20, d20 ADV, d20 DIS, damage). [Anecdotal: observed in user forums and Discord communities.]
- **Blind rolls cause anxiety**: Players appreciate Foundry's blind-roll mode because it removes the temptation to influence a roll result. GMs appreciate that blind rolls appear to all GMs even if the roller cannot see them. [Anecdotal: Foundry VTT Reddit threads.]
- **Roll expansion is essential**: Users want to see why a roll succeeded or failed (e.g., "Attack: 15 = 1d20(12) + 3"). A bare total without breakdown generates table arguments. [Anecdotal: VTT community surveys and stream chats.]
- **Multiline support is expected**: Players often compose longer in-character messages or describe actions before rolling. A single-line input feels restrictive. [Anecdotal: chat-log reviews from live sessions.]
- **Modifier stepping (±1 per click) is tedious for large values**: A player with a +15 modifier should not have to click 15 times to adjust. A text input with a stepper is better than a large click sequence. [Anecdotal: Roll20/Foundry user complaints in feature-request threads.]

## 8. Roll-Drauf fit and explicit non-goals

### Belongs in this slice

- **Message input and submission**: Text field, multiline support, and Enter-to-send.
- **Die formula input**: Freeform text or preset buttons for common rolls (d20, d20+2, etc.).
- **Roll modifiers**: Inline modifier input (`+5`, `-2`) or a spinbox to adjust a value.
- **Advantage/Disadvantage state**: Explicit toggle or radio button to select normal/ADV/DIS.
- **Roll visibility selector**: Dropdown or button group to choose public/GM/blind/self (subject to server permission checks).
- **Roll submission and result display**: Inline chat message showing the roll total and formula; expandable disclosure for details.
- **Chat history**: Chronological list of messages and rolls with author, timestamp, and content.
- **Keyboard shortcuts**: Enter-to-send, Shift+Enter for multiline, and optional number-key shortcuts for die presets.

### Explicitly deferred (separate slices or later phases)

- **Macros and custom actions**: Foundry's macro system and Roll-Drauf's action catalog are separate. A macro is a saved script; an action is a predefined roll. Do not mix them with chat/roll composition in this slice.
- **Whisper/private messages to specific users**: Whisper routing requires a recipient picker and permission checks. Defer to a later chat-features slice.
- **Chat reactions, threading, and edit history**: These are chat-log metadata features, not part of the composer.
- **Advanced dice notation** (e.g., drop lowest, reroll on success): Start with basic `{n}d{f}+m` syntax. Defer advanced modifiers until after basic composition is stable.
- **Automatic roll-result buttons** (e.g., "Advantage applied" button that re-rolls): The server must decide whether to apply re-rolls or modifiers. Do not encode game logic in the UI.
- **Inline rolls in narrative messages** (e.g., "I swing at the orc [[1d20+5]]"): Defer to a markdown-aware message parser. For now, rolls are separate from messages.

### Non-goal: Do not re-implement Foundry's entire chat system

Roll-Drauf has a simpler scope: table-top communication and quick dice mechanics. Foundry's chat system includes chat bubbles above tokens, inline scene notes, journal integration, and macro execution. Roll-Drauf's chat is asynchronous table talk and roll logging. Keep it focused.

## 9. Proposed interface/data/permission contracts

### Chat message schema (server-side source of truth)

```json
{
  "id": "uuid",
  "session_id": "uuid",
  "user_id": "uuid",
  "author_name": "string",
  "created_at": "ISO8601",
  "type": "message|roll",
  "content": "string (message body or empty if roll-only)",
  "roll_formula": "string (e.g., '1d20+5') or null",
  "roll_result": {
    "total": "number",
    "individual_dice": [{"die": "d20", "faces": 20, "results": [17]}, ...],
    "modifiers": [{"label": "+STR", "value": 5}],
    "advantage_state": "normal|advantage|disadvantage",
    "roll_mode": "public|gm_only|blind|self"
  } or null,
  "visibility": {
    "mode": "public|gm_only|blind|self",
    "recipients": ["user_id"] or null
  },
  "server_timestamp": "ISO8601"
}
```

### Client state: composer

```javascript
composer = {
  messageText: "string",
  dieFormula: "1d20+5",
  advantageState: "normal|advantage|disadvantage",
  rollMode: "public|gm_only|blind|self",
  isComposingRoll: boolean,
  submitting: boolean,
  lastError: "string|null"
}
```

### API contract: POST /api/session/{session_id}/roll

```json
Request:
{
  "formula": "1d20+5",
  "advantage": "normal|advantage|disadvantage",
  "visibility": "public|gm_only|blind|self",
  "message": "optional narrative text"
}

Response (201 Created):
{
  "id": "uuid",
  "roll_result": { ... },
  "visibility": { mode: "public|gm_only|blind|self" },
  "created_at": "ISO8601"
}

Error (403 Forbidden):
{
  "error": "Users without GM role cannot create blind rolls"
}
```

### Socket event: roll.created

```json
{
  "event": "roll.created",
  "data": {
    "id": "uuid",
    "author_name": "string",
    "roll_formula": "1d20+5",
    "roll_result": { "total": 17, ... },
    "visibility_for_user": "public|gm_only|hidden",
    "created_at": "ISO8601"
  }
}
```

**Permission model**:
- **Public rolls**: All users in the session see the full roll (formula, total, breakdown).
- **GM-only rolls**: Only the roller and users with `role == "dm"` see the roll.
- **Blind rolls**: Only users with `role == "dm"` see the roll; the roller does not see the result.
- **Self rolls**: Only the roller sees the roll result. Other users see "rolled (hidden)".

The server validates the user's role before accepting a roll with a given visibility mode. Blind rolls are rejected if the user is not a DM.

### Keyboard behavior

- **Enter**: Submit the message or roll. If a message is being composed, Enter sends the message. If the composer is in roll mode and a formula is present, Enter submits the roll.
- **Shift+Enter** (in textarea): Insert a line break. Do not submit.
- **Escape**: Clear the composer or close a popover. If the composer has unsaved text, do not discard it silently; preserve it.
- **Number keys (1–9)**: Optional shortcut to insert a preset formula (e.g., `1` = "d20", `2` = "d20+2"). Only active if the composer is focused and this shortcut is enabled in settings.
- **Tab**: Move focus to the next form field or out of the composer entirely. Do not trap focus.

## 10. Risks and assumptions with severity labels

### Risk: Roll visibility enforcement breaks if the server is not the source of truth
- **Severity**: CRITICAL
- **Mitigation**: Every roll request must be re-validated server-side. Never trust a `visibility` claim in a browser request. Implement permission checks in `vtt/play/routes.py` before accepting the roll.

### Risk: Modifiers and ADV/DIS are coupled, leading to UI confusion
- **Severity**: HIGH
- **Assumption**: Advantage/Disadvantage is a distinct roll mechanic (roll twice, take highest/lowest), not a modifier. If the UI conflates them, players will accidentally use the wrong one.
- **Mitigation**: Display ADV/DIS as a separate control from the modifier spinbox. Label them clearly: "Roll Mode: [Normal] [Advantage] [Disadvantage]" vs. "Modifier: [ ±5 ]".

### Risk: Chat log grows unbounded, slowing the browser
- **Severity**: MEDIUM
- **Assumption**: A typical session logs hundreds of messages. Without pagination or virtualization, rendering them all degrades performance.
- **Mitigation**: Implement server-side pagination (e.g., last 100 messages) and load older messages on scroll-up if needed. Do not render 1000+ messages in the DOM at once.

### Risk: Socket message ordering is not guaranteed
- **Severity**: MEDIUM
- **Assumption**: If two users roll simultaneously, the socket may deliver their events out of order. The chat log should reflect chronological order, not delivery order.
- **Mitigation**: Include a server-issued timestamp in every roll event. Sort chat log by server timestamp, not client receipt order.

### Risk: Mobile soft keyboard occludes the composer
- **Severity**: MEDIUM
- **Assumption**: On small screens, the text input and roll buttons may disappear behind the soft keyboard. The user cannot see what they are typing or click to submit.
- **Mitigation**: Reflow the composer UI when the soft keyboard appears (listen to `focus`, `blur`, and viewport resize events). Keep the submit button visible and the text input's current line at the top of the viewport.

### Risk: Role permission changes mid-session are not applied in real-time
- **Severity**: LOW (affects edge case)
- **Assumption**: If a player's role changes (e.g., elevated to DM), the composer should reflect new capabilities (e.g., blind rolls become available).
- **Mitigation**: Include role information in realtime session-update events. Refresh the composer's permission state when a user-role update is received.

## 11. Acceptance criteria

### Desktop (keyboard + mouse)

- [ ] Composer displays in the chat sidebar; message input is a `<textarea>` or multi-line `<input>`.
- [ ] Enter submits; Shift+Enter (in textarea) inserts a line break.
- [ ] Die presets (d20, d20+2, d4, d6, d8, d10, d12, d20) are visible as quick-click buttons or a dropdown.
- [ ] Modifier input accepts `+5`, `-3`, etc.; changes the displayed formula in real-time.
- [ ] ADV/DIS toggle shows current state as text ("Normal", "Advantage", "Disadvantage") and is keyboard-accessible.
- [ ] Roll visibility dropdown (Public, GM Only, Blind, Self) is labeled and shows the current selection.
- [ ] Blind and Self roll options are disabled (grayed out with a tooltip) if the user is not a DM.
- [ ] Submit button is labeled "Senden" (German) and keyboard-accessible via Tab.
- [ ] Chat log shows messages and rolls in chronological order with author, time, and result total.
- [ ] Roll result displays as single line initially (e.g., "Attack: 17 (1d20+2)"); expands on click to show breakdown (individual dice, modifiers).
- [ ] Expansion disclosure uses `aria-expanded` and `aria-controls`; does not require JavaScript to navigate.
- [ ] Scrolling down the chat log auto-scrolls to the newest message; scrolling up does not.

### Mobile (touch + soft keyboard)

- [ ] Composer is displayed above the soft keyboard, not hidden behind it.
- [ ] Text input has `inputmode="text"` or similar for soft keyboard hints.
- [ ] Die presets are a single row or collapsible set; tapping one inserts it into the formula.
- [ ] Modifier spinbox or input does not require precise fine motor control; use `<input type="number">` with `+` and `−` buttons.
- [ ] Roll-visibility selector is a dropdown (not radio buttons that take up multiple rows).
- [ ] Keyboard dismiss (`Enter` to send) is the primary path; a visible "Senden" button is a fallback.
- [ ] Chat log is scrollable and shows at most the latest 50–100 messages (paginate older ones).
- [ ] Roll expansion is a tap target (not hover); tapping expands inline or opens a small modal.
- [ ] Soft keyboard dismissal after sending clears the input and keeps focus in the composer for rapid follow-up rolls.

### Keyboard + Assistive Technology

- [ ] All controls are keyboard-accessible via Tab.
- [ ] Form labels are associated with inputs via `<label for="...">` or `aria-label`.
- [ ] Roll mode and ADV/DIS state are announced when changed (use `aria-live="polite"` or manage focus to the changed control).
- [ ] Chat log is a live region with `aria-live="polite"` or `aria-live="assertive"` (if immediate announcement is needed); new messages are announced without requiring scroll focus.
- [ ] Expansion disclosure uses semantic HTML (`aria-expanded`, `aria-controls`) or a `<details>` element.
- [ ] Error messages (e.g., "Invalid formula") are announced and focused for visibility.

### Permissions & Realtime Updates

- [ ] Blind and Self visibility modes are accepted only if the user's role is "dm". Non-DM submissions are rejected with a 403 and an error message.
- [ ] A player's roll is stored server-side with its visibility mode. The mode is enforced during broadcast; non-authorized users do not receive the full roll details.
- [ ] GM users see all rolls (public, GM, blind, self). Players see only rolls visible to them (public, self if they rolled, or a placeholder for blind/gm rolls).
- [ ] If a player's role changes during the session (e.g., promoted to DM), the composer's visibility options update in real-time (no page reload required).
- [ ] Roll events are delivered to all connected clients via socket; chat log updates without requiring a page refresh.

### Error Handling

- [ ] Invalid formula (e.g., "2d0+5") shows an error message: "Ungültige Wurfelformel. Erwartet: 1d20, 1d20+5, etc."
- [ ] Network error during roll submission shows "Verbindungsfehler beim Versand. Versuchen Sie es erneut." and preserves the unsent message in the composer.
- [ ] Permission error (e.g., DM-only action as a player) shows "Sie haben keine Berechtigung für diese Aktion."
- [ ] Server crash or disconnect causes the composer to disable with a banner: "Verbindung unterbrochen. Session wird wiederhergestellt..."

### Destructive Actions

- None in this slice. Chat messages and rolls are logged; they can be deleted (in a later slice) with an audit trail and confirmation.

## 12. Apply handoff: decisions still needed before implementation

1. **Message input type**: Should the message input be a single-line `<input type="text">` or a multi-line `<textarea>`? Multiline is more flexible but takes more space on mobile.

2. **Modifier input UX**: Should modifiers be a text input (e.g., `+5`), a spinbox (up/down arrows), or both? Text is flexible; spinbox is precise for small adjustments.

3. **Die preset scope**: Which die presets should be visible by default? D&D has d4, d6, d8, d10, d12, d20; Pathfinder adds d100. Start with d20, d20+2, d4, d6, d8, d10, d12?

4. **Inline roll expansion**: Should expanded roll details appear inline in the chat log, or in a separate popover/modal? Inline is less cluttered; modal provides more detail.

5. **Chat history pagination**: Should the client load all historical messages on page load, or paginate (e.g., last 100 messages, load older on scroll)? Pagination is performant; all-at-once is simpler to implement.

6. **ADV/DIS in formulas**: Should a roll formula support syntax like `1d20ah` (advantage, highest) or `1d20al` (advantage, lowest), or should ADV/DIS be a separate control? Separate control is simpler and less error-prone.

7. **Whisper support**: Should this slice include whispers to specific users, or defer whispers to a later chat-features slice? Recommended: defer; start with public/GM/blind/self.

8. **Schema: chat table design**: Should messages and rolls be one table (with `type` enum) or separate tables? One table is simpler initially; separate tables allow schema-specific indexing later.

9. **Broadcast granularity**: When a roll is created, should the server broadcast the full roll event to all clients immediately, or should clients poll the chat history? Broadcast via socket is more real-time; polling is simpler but requires periodic requests.

10. **Undo/rollback**: Should users be able to delete sent messages or rolls? If yes, should deletion be permanent or mark as "deleted by user"? Recommend: defer deletion; start with immutable logs.

