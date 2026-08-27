# Feature Research: Combat Tracker and Initiative Strip

**Date:** 2026-08-27  
**Slice:** 06 — combat tracker and initiative strip  
**Status:** research/discover only; no production code changed  
**Target file:** `docs/PLAYTABLE_FEATURE_RESEARCH_06_COMBAT_2026-08-27.md`

## 1. Status and input summary

This research pass examines Roll-Drauf's combat/initiative UI: current turn display, rounds counter, party portraits, next-actor preview, initiative editing, adding/removing combatants, turn transitions, player vs. DM controls, and mobile behavior.

The research answers these questions:

- How should the current turn and next actors be visually highlighted on desktop and mobile?
- What affordances are needed for DM-only actions (start combat, end combat, advance turn/round)?
- How should players see initiative order while respecting hidden/defeated states?
- When should initiative be editable, and what confirmations are necessary?
- How should turn progression work across network latency and concurrent updates?
- What live-region announcements must accompany turn changes for accessibility?

## 2. Current Roll-Drauf state and relevant file inventory

### Existing implementation seams

- **Combat model**: `CombatEncounter` (one per session, has `active_round`, `active_turn_index`) and `SessionInitiative` (manages encounter turns and participants). ([vtt/models/combat_encounter.py](../vtt/models/combat_encounter.py), [vtt/models/session_initiative.py](../vtt/models/session_initiative.py))

- **Token initiative field**: `TokenState.initiative` (numeric or null). Stored as simple initiative value, sorted descending for turn order. ([vtt/models/token_state.py](../vtt/models/token_state.py))

- **Combat events**: Encounters emit server-side events for turn/round changes: `initiativeTurnChanged`, `initiativeUpdated`. Payload includes the entire initiative order and current turn state. ([vtt/play/routes.py](../vtt/play/routes.py), [vtt/static/js/play-client.js](../vtt/static/js/play-client.js) lines 377–378)

- **UI widget**: `#turnOrderWidget` displays the current initiative list, a summary of the active turn, and DM-only combat controls. ([vtt/templates/play.html](../vtt/templates/play.html) lines 1678–1694)
  - Summary line: "Aktuell: {name} ({initiative})"
  - List: initiative entries sorted by score, with current turn highlighted
  - DM controls: "Kampf starten", "Nächster Zug", "Kampf beenden", "Initiative auswürfeln"

- **Rendering logic**: `_renderTurnOrder()` and `_getInitiativeEntries()` build the display from tokens and `bootstrap.state_payload.initiative`. ([vtt/static/js/play-ui.js](../vtt/static/js/play-ui.js) lines 2480–2684)

- **Initiative actions**: 
  - Roll initiative: `_rollInitiativeForTokens()` rolls d20 + modifier for all tokens without initiative
  - Sync from Beyond20: integration receives initiative updates from external integration ([vtt/static/js/play-ui.js](../vtt/static/js/play-ui.js) lines 449–465)
  - Update token initiative: currently requires direct token update via token widget

- **Mobile responsiveness**: `#turnOrderWidget` moves from desktop floating panel into `#tableSheet` at mobile breakpoint. ([vtt/templates/play.html](../vtt/templates/play.html) lines 1370, 1472)

- **Permissions**: Initiative controls are DM-only (`if (operator)` check). Players see read-only initiative list if they are currently viewing the scene.

### Files not yet modified

- `vtt/static/js/play-ui.js` — widget rendering and interaction
- `vtt/static/js/play-client.js` — server sync
- `vtt/static/js/play-socket.js` — realtime updates
- `vtt/templates/play.html` — HTML and layout
- `vtt/play/routes.py` — combat endpoint handlers

## 3. Web research and source-backed findings

### Foundry VTT combat tracker model

Foundry distinguishes between combat design and UI presentation: ([Foundry Combat](https://foundryvtt.com/article/combat/))

1. **Turn tracking**: Each encounter has an `active_turn_index` pointing to the current combatant in the initiative order. The tracker shows the previous/next buttons to move through turns sequentially.

2. **Round management**: Each turn increment checks if a new round should begin. Advancing a round sets the turn to the first combatant.

3. **Initiative order**: Built from combatants' initiative scores, sorted descending. Ties are broken by a system-specific tiebreaker (typically initiative modifier, then dexterity).

4. **Visibility model**: Combatants can be marked "hidden" (not shown to players), "defeated" (faded appearance), or visible. The GM always sees the full order.

5. **Encounter scope**: One encounter per scene; multiple simultaneous encounters are possible but are separate turn orders.

6. **Action economy**: The tracker does not enforce action counts; system rules define when a character can act within a turn.

### Modern VTT combat tracker patterns

Research on current VTT UI trends shows: ([GitHub OmerCora/draw-steel-combat-tracker](https://github.com/OmerCora/draw-steel-combat-tracker), [Foundry Hub Combat Tracker Extensions](https://www.foundryvtt-hub.com/package/combat-tracker-extensions/), [TTRPG Games Initiative Trackers](https://www.ttrpg-games.com/blog/top-10-initiative-trackers-for-ttrpgs))

1. **Side-based layout**: Party heroes on the left, enemies on the right, current turn in center. Reduces scanning distance for common "whose turn?" question.

2. **Portrait-driven**: Each combatant shows a portrait, name, and initiative score. Groups display as pill containers with captain and minions.

3. **Configurable visibility**: Hide NPC names, obscure initiative until revealed, reverse order for surprise, group by party/faction, show current turn index (e.g., "3 / 8").

4. **Turn control**: Obvious Previous/Next Turn buttons for DMs. Keyboard shortcut (spacebar or arrow) for speed. Right-click to jump to a specific turn (context menu).

5. **Round display**: Large, obvious round counter. Clear indication of whose turn it is and how many combatants remain this round.

6. **Popped-out windows**: Desktop VTTs allow the combat tracker to be dragged into a floating, resizable window. Mobile VTTs integrate the tracker into the main interface or a bottom sheet.

### W3C/MDN patterns for live updates and focus

**Live regions** (`aria-live`, `aria-atomic`): For a combat tracker, every turn change must be announced to screen readers. W3C APG specifies three live region types:

- `aria-live="polite"` — announce after a short delay, without interrupting current content
- `aria-live="assertive"` — announce immediately, even if it interrupts
- `aria-atomic="true"` — announce the entire region, not just the change

For turn changes, a "polite" region is appropriate: "It is now Gandalf's turn. Initiative score: 18." ([W3C ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/))

**Focus restoration**: When a turn changes, do not steal focus from the player's current task. Use a live region to announce the change, and optionally update the displayed turn order. If the player opens the combat widget, focus the current-turn entry.

**Keyboard shortcuts**: Combat progression often uses Space/Enter to advance the turn (common in tabletop tools). Ensure shortcuts do not fire while focus is inside an input, chat, or menu.

**Pointer Events and drag**: A combat tracker should be draggable/resizable on desktop (pointer capture for smooth movement). Mobile should use the existing sheet pattern instead of custom drag.

### Mobile and touch considerations

- Right-click context menus do not work on touch. Provide a visible button (e.g., "⋯" menu) for turn-jump and other actions.
- Initiative entry should be tappable to select or open details, not require hover.
- On mobile, the turn-order list may be a short carousel or a full-screen section of the table sheet.
- Touch targets should be at least 44×44 CSS pixels for reliable tap interaction.

## 4. Good examples

### Example 1: Foundry VTT Encounter Tracker Sidebar

**Why it works**: Foundry's sidebar tracker shows a compact list of combatants sorted by initiative. The current turn is highlighted. Previous/Next Turn buttons are obvious. Hidden combatants show "Unknown" to non-GMs, not their names. The GM sees full details and can click a combatant to select its token on the map.

**Applicable to Roll-Drauf**: Render the current-turn entry with a distinct visual style (bold, background color, or ring). Show a compact initiative score beside each name. For DM mode, show all names and initiative. For player mode, hide names of hidden combatants and faded appearance for defeated tokens. Clicking an entry should select the corresponding token on the map.

([Foundry Combat](https://foundryvtt.com/article/combat/))

### Example 2: Draw Steel Combat Tracker Module

**Why it works**: The tracker uses a dual-pane layout: left shows party/heroes, right shows enemies, center shows round and current turn prominently. Groups show collapsed/expanded states. Groups roll initiative together and act on the same turn. Supports named vs. unnamed minions.

**Applicable to Roll-Drauf**: For groups or party-based games, add a grouping mode to show party vs. enemies. Show the current turn prominently in a larger font or card layout. If Roll-Drauf encounters support party/enemy grouping, expose group toggling.

([GitHub OmerCora/draw-steel-combat-tracker](https://github.com/OmerCora/draw-steel-combat-tracker))

### Example 3: TouchVTT Tablet Interface

**Why it works**: TouchVTT optimizes Foundry for tablets by enlarging touch targets, removing hover-only UI, and placing the combat tracker in a collapsible sidebar or bottom sheet. Long-press opens a context menu (visible button as primary path).

**Applicable to Roll-Drauf**: On mobile, use the existing `#tableSheet` pattern for the turn-order list. Ensure DM control buttons are always visible and at least 44×44 pixels. Provide long-press or a visible "more" menu for per-combatant actions (e.g., remove from combat, edit initiative).

## 5. Bad examples and failure modes

### Failure 1: Hover-only turn control

**Problem**: The current turn is indicated only by hover or tooltip. On mobile and with keyboard navigation, the active turn is invisible. Players cannot discover which turn they are in.

**Impact**: High — combat becomes confusing; players cannot follow the action.

**Fix**: Always show the current turn visually (color, bold, marker, or background). Use a live region to announce turn changes.

### Failure 2: Initiative order updates without live-region announcement

**Problem**: A turn changes on the server, the tracker updates silently, but screen-reader users have no notification.

**Impact**: High — accessibility failure; blind/low-vision players cannot follow combat.

**Fix**: Emit a live-region announcement on every turn/round change: "It is now {name}'s turn."

### Failure 3: DM control buttons visible to players

**Problem**: Players see "Start Combat", "Next Turn", "End Combat" buttons and can click them (or attempt to if permissions are enforced).

**Impact**: Medium — confusion, accidental clicks, permission failures if not checked server-side.

**Fix**: Hide DM controls behind `if (operator)` checks. Show a read-only "Current turn: {name}" summary to players.

### Failure 4: Slow or stale turn updates

**Problem**: A DM clicks "Next Turn", the client updates immediately (optimistic), but the server transaction fails silently. The turn revertslocally, but the UI still shows the old turn.

**Impact**: High — DM/player desynchronization; confusion about whose turn it actually is.

**Fix**: Always validate turn changes server-side. On conflict, reset to the server's current state. Announce the result with a brief message ("Turn advanced" or "Error: could not advance turn").

### Failure 5: Initiative editing without confirmation

**Problem**: A DM can edit a token's initiative by clicking in a text field and pressing Enter, but there is no confirmation. The change applies immediately and affects the entire turn order.

**Impact**: Medium — accidental changes; no audit trail.

**Fix**: Require explicit confirmation for initiative changes (e.g., "Update initiative?" button or a small confirmation popover). Log the change in the chat/audit log.

## 6. Lessons learned

1. **Live regions are not optional**: Every turn/round change must be announced with `aria-live="polite"`. This is the only way for assistive-technology users to follow combat.

2. **Visible affordances over hover**: Right-click and hover are shortcuts only. Every action (start combat, advance turn, jump to turn, remove combatant) must have a visible button or keyboard path.

3. **Round and turn are separate concepts**: A "round" is the cycle through all combatants' turns. A "turn" is one combatant's action. Display both clearly: "Round 3, Turn 4 of 6" or similar.

4. **Initiative is mutable, but changes have side effects**: Editing a token's initiative reorders the entire turn sequence. Players see the new order immediately (if not hidden). Confirm the change and announce it to the group.

5. **Hidden combatants need special handling**: Showing "Unknown" or "Hidden Enemy" to players is a deliberate choice. The tracker must respect the hidden state everywhere: list, portrait, turn announcement (do not say the name if hidden), and permissions.

6. **Turn progression is atomic**: A "next turn" action should be one server-side operation. Do not emit separate "decrement old turn, increment new turn" events. Emit one "turn changed to X" event so watchers reconcile from a single source of truth.

7. **Keyboard shortcuts need context awareness**: Combat tracker keyboard shortcuts (Space to advance turn, arrow keys to select) should not fire while focus is in an input, chat, or dialog. Use a focus-aware event delegation pattern.

## 7. Community favorites

Based on community discussions and VTT module trends:

**Opinion**: Many VTT players prefer a side-based layout (party left, enemies right) because it mirrors the common "us vs. them" mental model and reduces scanning time. ([TTRPG Games Initiative Trackers](https://www.ttrpg-games.com/blog/top-10-initiative-trackers-for-ttrpgs))

**Opinion**: The "compact strip" style (portraits + names + initiative in a horizontal row) is preferred for mobile and popped-out windows over a vertical list, because it keeps the map visible and context-dense.

**Opinion**: Anecdotal evidence: many tables appreciate a per-turn summary displayed as "{Actor} acts. Round {n}, turn {t} of {total}." to orient players who join late or get distracted.

**Opinion**: DMs often request a quick keyboard shortcut to advance the turn (Space or >, frequently configurable) to speed up play.

**Opinion**: Some tables use "hidden initiative" (only the GM sees the order until the first turn), but this is game-design preference, not a UI feature Roll-Drauf must support initially.

## 8. Roll-Drauf fit and explicit non-goals

### Fits well

- **Turn-order tracking**: Roll-Drauf already tracks `CombatEncounter.active_turn_index` and `TokenState.initiative`. The server-side model is stable.
- **Realtime synchronization**: Combat events are already broadcast to all players (except hidden names/states). The socket layer is in place.
- **DM vs. player visibility**: Permissions and hidden state are already enforced.
- **Initiative rolling**: `_rollInitiativeForTokens()` already works; it just needs better UI/confirmation.
- **Mobile sheet integration**: The existing `#tableSheet` pattern works for combat on touch.

### Does not fit without adjustment

- **Group initiative**: If Roll-Drauf wants to support group/party-based turns (e.g., "The party acts together"), that requires a schema change. Defer grouping to a later slice.
- **Surprise rounds**: Some D&D 5e tables use surprise rounds with special rules. This is system/rule-set specific; Roll-Drauf should not hardcode it.
- **Contested initiative**: Some systems re-roll initiative mid-combat or use reactive turns. Roll-Drauf's simple "sort by score" model is sufficient for standard turn-based d20 games.
- **Multiple simultaneous encounters**: Foundry supports this; Roll-Drauf currently assumes one active encounter per scene. If needed, defer to a later slice.

### Proposed scope for this slice

1. Render the turn-order widget with a visually distinct current-turn entry.
2. Show a compact summary of the active turn (name, initiative, round/turn count).
3. Provide DM-only buttons to start/end combat and advance turn/round.
4. Emit live-region announcements on turn/round changes.
5. Support adding/removing combatants (already works via token creation/deletion).
6. Handle initiative editing for a selected token.
7. Respect hidden and defeated states for player visibility.
8. Adapt the layout for mobile (use `#tableSheet` pattern).

**Explicit non-goals for this slice**:

- Group/party-based initiative
- Surprise rounds or special turn mechanics
- Custom combat phase/action-economy systems
- Multiple simultaneous encounters
- Initiative re-rolling mid-combat
- Rich turn/round history or undo

## 9. Proposed interface/data/permission contracts

### Display state

```
turnOrder = {
  encounterActive: boolean,
  currentRound: number,
  currentTurnIndex: number,
  entries: [
    {
      tokenId: string,
      name: string,
      initiative: number,
      hp: number | null,
      hpMax: number | null,
      isCurrentTurn: boolean,
      isHidden: boolean,        // DM sees real value; players see "Hidden"
      isDefeated: boolean,      // optional visual style
      portrait: string | null,
    },
    ...
  ],
  participants: number,  // total combatants
}
```

### DM actions (operator role only)

- `POST /combat/start` — initialize encounter if not active
- `POST /combat/turn/next` — advance turn (with server-side round-boundary logic)
- `POST /combat/turn/previous` — go back one turn
- `POST /combat/turn/set/{tokenId}` — jump to a specific combatant's turn
- `POST /combat/end` — end active encounter
- `PUT /combat/participants/{tokenId}` — edit initiative or remove from combat
- `POST /combat/initiative/roll` — roll d20 for all tokens without initiative

### Server-side validation

- Turn advances should be atomic: one "turn changed" event, not separate updates.
- Initiative changes should be logged (audit trail or chat message).
- If a token is deleted, remove it from initiative order.
- Stale version conflict: if a concurrent update happens, reject and return the current state.

### Live region contract

Every turn or round change emits a live-region update:

```
aria-live="polite"
"It is now {tokenName}'s turn. Initiative score: {score}. Round {round}, turn {turnIndex} of {total}."
```

For hidden combatants (players viewing):
```
"Turn advanced. Round {round}. {visibleCount} visible combatants remain."
```

### Permission model

- **DM/Operator**: Full view of initiative, hidden combatants, and all control buttons.
- **Player**: Read-only view of non-hidden combatants. Cannot see names of hidden entries (shown as "Unknown" or "???"). No access to combat controls.
- **Read-only mode** (observer): Same as player, but cannot interact at all.

## 10. Risks and assumptions with severity labels

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Turn changes do not emit live-region announcements | **HIGH** | Add a fixed `aria-live="polite"` region. Emit text on every turn/round change. |
| Initiative editing is not confirmed, causing accidental changes | **MEDIUM** | Add a small confirmation popover or button. Log changes to audit/chat. |
| Slow network causes DM to click "Next Turn" twice, resulting in skipped turn | **MEDIUM** | Disable button while request is in flight. Return the actual server state on conflict. |
| Players can see hidden-combatant names or initiative scores in debug/network traffic | **MEDIUM** | Validate player role server-side. Never send hidden data in payloads to non-DMs. |
| Initiative order is visually identical to player list (no "current turn" styling) | **MEDIUM** | Use bold, background color, or ring to mark current turn. Test with zoom, mobile, and reduced-motion settings. |
| Touch targets for DM buttons are <44px, causing missed taps | **LOW** | Ensure buttons are 44×44 or larger. Test on actual tablets. |
| Dragging the turn-order widget on desktop leaves a ghost image or loses pointer | **LOW** | Use pointer capture (already in use for other widgets). Test drag on 100%, 200%, 300% zoom. |

## 11. Acceptance criteria

### Desktop

- [ ] DM sees the turn-order widget with a list of combatants sorted by initiative descending.
- [ ] Current turn is visually distinct (bold, background, or ring).
- [ ] Summary shows: "Round {n}, Turn {m} of {total}" and current combatant's name and initiative.
- [ ] "Kampf starten", "Nächster Zug", "Kampf beenden", "Initiative auswürfeln" buttons are visible and functional for DM only.
- [ ] Clicking a combatant name selects the corresponding token on the map (if implementation supports it).
- [ ] Advancing turn updates the display and emits a live-region announcement.
- [ ] Widget is draggable and resizable without losing pointer or showing ghost images.
- [ ] Collision avoidance: widget does not cover the selected token or critical map controls.

### Mobile

- [ ] Turn-order list moves into `#tableSheet` on mobile breakpoint.
- [ ] Combatants are tappable (44×44 touch targets minimum).
- [ ] DM control buttons are visible and functional.
- [ ] List can scroll independently of the sheet backdrop without trapping focus.
- [ ] Live-region announcements are still emitted for turn changes.

### Keyboard

- [ ] Tab navigates to the turn-order widget, first combatant entry, and DM control buttons.
- [ ] Enter/Space on a combatant entry selects it (same as mouse click).
- [ ] Spacebar on "Next Turn" button advances the turn (if focus is on the button).
- [ ] Escape closes any open menu (future: context menu for per-combatant actions).
- [ ] Keyboard shortcut for "Next Turn" (e.g., Space globally) should not fire while focus is in an input, chat, or dialog.

### Permissions and roles

- [ ] DM/Operator sees all combatants, full initiative, and all control buttons.
- [ ] Player sees only non-hidden combatants. Hidden entries show "Unknown" or "???" (no name, no initiative).
- [ ] Player sees a read-only list; no buttons to start/end combat or advance turn.
- [ ] Read-only observer sees the same as a player, with no interaction possible.
- [ ] Initiative changes are logged (audit trail or chat message visible only to DM).

### Realtime updates and conflicts

- [ ] When a remote DM advances a turn, the local display updates and announces the change.
- [ ] If a conflict occurs (two DMs click "Next Turn" simultaneously), the server resolves it and returns the canonical state.
- [ ] Turn-order widget updates reflect the server's state, not optimistic local edits.
- [ ] A "next turn" request is atomic: one server-side operation, one event broadcast.

### Error handling

- [ ] If starting combat fails (e.g., no tokens with initiative), show a brief message: "No combatants with initiative to start combat."
- [ ] If advancing turn fails (e.g., server error), revert the local display and show an error message.
- [ ] DM control buttons are disabled during a pending request, re-enabled on success/error.

### Destructive actions

- [ ] "Kampf beenden" (end combat) is only available when combat is active. It clears the turn-order display and hides the combat controls.
- [ ] Ending combat does not delete tokens or reset initiative values. Tokens retain their initiative scores for re-engagement.

## 12. Apply handoff: decisions still needed before implementation

1. **Live-region granularity**: Should the announcement include the combatant's HP, conditions, and spell slots ("Gandalf's turn, 45/62 HP, no concentration spells"), or just name and initiative? (Recommendation: keep it brief—name and initiative. Full state is visible in the widget/HUD.)

2. **Round reset on initiative editing**: If a DM changes a token's initiative during combat, does the turn order immediately recompute, or does it apply on the next turn? (Recommendation: recompute immediately, as it's closer to how d20 tables work. Announce the change in chat.)

3. **Hidden combatant announcement**: If a hidden combatant becomes the current turn, should non-DM players hear an announcement like "Turn advanced. Round 3, turn 2 of 5", or should it be silent? (Recommendation: announce "Turn advanced" without the name, to avoid meta-game leakage.)

4. **Group/party collapse**: Should the UI ever show combatants grouped (party vs. enemies, or named NPCs vs. minions)? (Recommendation: defer grouping to a later slice. Start with a flat list sorted by initiative.)

5. **Mobile layout variant**: Should mobile use a horizontal carousel of combatants (showing initiative order left-to-right), or a vertical list like desktop? (Recommendation: vertical list to match desktop and reduce horizontal scrolling. Desktop floating widget and mobile sheet are the two layouts.)

6. **Keyboard shortcut scope**: Should Space advance the turn globally (even outside the widget), or only when focus is on the "Next Turn" button? (Recommendation: focus-aware—Space advances only if the button is focused or explicitly armed. This prevents accidental advances while typing.)

7. **Integration with token selection**: Should selecting a token on the map highlight its row in the turn-order widget? Should clicking a turn-order entry select the token? (Recommendation: yes to both, for bidirectional visual context. Ensure the widget does not cover the selected token.)

8. **Initiative re-roll UI**: The current "Initiative auswürfeln" button rolls initiative for all tokens without a value. Should it also support re-rolling for a selected token, or remain a bulk action only? (Recommendation: keep it as a bulk action for the first slice. Per-token re-roll can be added to the token HUD "more" menu later.)

---

## Sources

**Primary (Official Documentation & Standards)**

- [Foundry VTT Combat](https://foundryvtt.com/article/combat/)
- [W3C ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [MDN Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events)
- [MDN `<dialog>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog)

**Community Sources & Examples**

- [GitHub OmerCora/draw-steel-combat-tracker](https://github.com/OmerCora/draw-steel-combat-tracker) — draw-steel combat tracker module for Foundry VTT
- [Foundry Hub Combat Tracker Extensions](https://www.foundryvtt-hub.com/package/combat-tracker-extensions/)
- [TTRPG Games Initiative Trackers for TTRPGs](https://www.ttrpg-games.com/blog/top-10-initiative-trackers-for-ttrpgs)

**Roll-Drauf Reference**

- `vtt/models/combat_encounter.py` — encounter state model
- `vtt/models/session_initiative.py` — initiative tracking
- `vtt/models/token_state.py` — token fields including initiative
- `vtt/play/routes.py` — combat API endpoints
- `vtt/static/js/play-ui.js` — turn-order rendering and interaction logic
- `vtt/templates/play.html` — turn-order widget HTML
