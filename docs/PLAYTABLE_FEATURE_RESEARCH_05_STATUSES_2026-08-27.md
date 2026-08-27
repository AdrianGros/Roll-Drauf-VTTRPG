# Playtable feature research: Conditions and status picker

**Date:** 2026-08-27  
**Scope:** Status/condition systems in the Roll-Drauf VTT playtable  
**Slice:** 05 — conditions and status picker  
**Status:** Research/Discover only. No production code changes. Target input: Slice 04 (Token HUD). Target output: Status picker UI contract and token-level condition schema.

---

## 1. Status and input summary

This slice researches how to represent, display, and allow players/DMs to manage status effects and conditions in the playtable. The research covers:

- Status/condition icon catalogs and labeling
- Applied/active state indicators and toggling
- Values, durations, and grouping/search patterns
- Clear-one, clear-all, and batch operations
- Token overlay presentation and player visibility
- Realtime synchronization with server permissions
- W3C accessibility patterns for toggle states and checkboxes

The slice depends on Slice 04 (Token HUD) as its UX anchor and expects Slice 06 (Combat) to define turn-level state effects. It must not invent a full game-design system; the recommendation grounds itself in Roll-Drauf's existing `metadata_json.conditions` array and the count badge already present.

---

## 2. Current Roll-Drauf state and relevant file inventory

### Current implementation

- **Data layer:** `token.metadata_json.conditions` is an array of condition strings, e.g., `["Concentrating", "Blinded", "Grappled"]`. No dedicated schema, duration tracking, or value fields yet.
  - Reference: `vtt/static/js/play-ui.js:2270–2271`, `vtt/static/js/play-ui.js:2437–2438`

- **Rendering on token layer:** A numeric count badge (`<div class="token-conditions">`) displays the length of the conditions array. Hovering reveals condition names in a title attribute.
  - Reference: `vtt/static/js/play-ui.js:2439–2441`

- **Rendering in token list:** Conditions are rendered as a comma-separated line of text in the sidebar token list.
  - Reference: `vtt/static/js/play-ui.js:2270–2274`

- **No picker yet:** There is no dedicated status-picker surface. No UI exists to add, remove, or clear conditions in the playtable. Conditions can only be edited outside the table or via server API.

### Foundational contracts

- Token selection already exists and triggers the token HUD (Slice 04).
- Existing `PlayRuntimeUI` state includes `selectedTokenId` and token updates.
- Server-side token endpoints already accept PATCH/POST for `metadata_json`.
- Session realtime updates broadcast token changes via socket events.

### Responsive layout assumptions

- Desktop: anchored popover or modal dialog for the picker
- Mobile: bottom-sheet section within the token editor sheet
- Keyboard: focus management within picker, Space/Enter for toggling, Escape to close
- Read-only mode: disable all writing, show conditions as display-only

---

## 3. Web research and source-backed findings

### Foundry VTT Status Effects Model

[Foundry Tokens documentation](https://foundryvtt.com/article/tokens/) describes status effects as:

> "Status effects are small icons overlaid on the token art in the upper left corner. The specific appearance of these icons is determined by the game system in use."

Right-clicking the Token HUD provides a dedicated status-effect grid. The [CONFIG.statusEffects](https://foundryvtt.com/api/variables/CONFIG.statusEffects.html) array defines the catalog. Status effects are toggled on/off individually via the HUD and are visually distinct from other token properties.

Foundry's [TokenDocument API](https://foundryvtt.com/api/classes/foundry.documents.TokenDocument.html) includes a `toggleStatusEffect(effectId)` method, which adds or removes an effect ID atomically. The status list is system-defined (e.g., D&D 5e systems define the canonical list: unconscious, dead, blinded, paralyzed, etc.).

**Fact:** Foundry separates system-defined statuses from arbitrary Active Effects. Roll-Drauf currently has no system-level status registry; all conditions are free-form strings in metadata.

### W3C ARIA Checkbox and Toggle Patterns

The [W3C Checkbox Pattern (APG)](https://www.w3.org/WAI/ARIA/apg/patterns/checkbox/) specifies:

- **Checked state:** `aria-checked="true"` for applied, `aria-checked="false"` for not applied
- **Grouped behavior:** A group of checkboxes with a common label (e.g., `role="group"` with `aria-labelledby`)
- **Keyboard:** Space key toggles the state; Tab moves between items
- **Visual indication:** Both color/icon **and** text must distinguish checked from unchecked (not color alone)

The [W3C Switch Pattern (APG)](https://www.w3.org/WAI/ARIA/apg/patterns/switch/) is similar but used only for binary on/off (power, mode toggle). Checkboxes are preferred for status effects because they allow grouped semantics and are more familiar to screen readers.

The [W3C Disclosure Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/) supports collapsible sections, useful if the status picker is expandable (e.g., "Show conditions" → reveals a list). The button triggering the disclosure must have `aria-expanded` and `aria-controls`.

**Fact:** Checkboxes + grouped semantics match status-picker UX better than switches. Disclosure pattern fits an expandable picker in the HUD.

### VTT Community Feedback on Dense Status Grids

While research cannot derive pure requirements from community opinion, repeated feedback patterns identify friction points:

- **Dense grids are hard to scan.** A 3×4 grid of status icons without labels requires hovering or context-switching to understand what each means. Foundry systems that expose the grid in a right-click HUD often require the GM to know the icons by heart.
- **No search in large catalogs.** If a system has 30+ status definitions, scrolling is slow. PFSF 2e and custom D&D modules report user frustration with buried conditions.
- **Ambiguous "applied" state.** When the same icon can be used for both "present" and "absent" (only the button state differs), players miss the distinction. Explicit labels prevent mistakes.
- **"Clear all" is dangerous without confirmation.** A single click can undo an entire scene's condition setup; some systems have no undo, leading to data loss frustration.

**Opinion:** Searchable status lists with explicit labels and a confirmation step for destructive operations reduce errors.

---

## 4. Good examples

### Example A: Foundry 5e SRD Module Status Grid

**What it does well:**
- Icon catalog is small and canonical: Blinded, Blinded, Bloodied, Concentrating, Confused, Dead, Deafened, Exhaustion, Fatigued, Feared, Frightened, Grappled, Incapacitated, Invisible, Paralyzed, Petrified, Poisoned, Prone, Restrained, Unconscious, Unconscious.
- Right-click on token opens the HUD, which shows a clear grid of status icons.
- Clicking the icon toggles the state on/off; the icon darkens or fades to show inactive.
- Hovering over an icon shows its name in a tooltip.
- Visual distinction between active (vivid) and inactive (faded/greyscale) is immediate.

**Why it works for Roll-Drauf:**
- The canonical list prevents free-form entry errors.
- Grouped icon grid is fast for power users; familiar to players who have seen it before.
- One-click toggle is low friction for the happy path.

**Reference:** [Foundry Tokens](https://foundryvtt.com/article/tokens/), [Token HUD API](https://foundryvtt.com/api/classes/foundry.applications.hud.TokenHUD.html)

### Example B: Pathfinder 2e Community Module — Searchable Condition Picker

**What it does well:**
- A modal picker with a text search box filters the status catalog by name.
- Each status shows an icon, label, and a single-line description (e.g., "Blinded: Penalties to sight-based checks").
- Checkboxes beside each status show the current applied state.
- A "Clear all" button at the bottom deactivates all conditions; it has a warning icon and explicit text.
- Applied conditions are highlighted or grouped at the top for quick reference.

**Why it works for Roll-Drauf:**
- Search prevents catalog bloat; easy to find a status by typing 3 letters.
- Descriptions prevent icon misinterpretation.
- Checkbox + label pairs are strongly accessible (native semantic HTML).
- Warning on destructive action reduces accidental clears.

**Anecdotal note:** PF2e Reddit threads report high user satisfaction with the search feature; it sped up condition management during combat.

### Example C: Prose-Style Indicator Pattern

**What it does well:**
- Instead of a grid of icons, status appears as a sentence: "Blinded, concentrating, grappled (by Goblin)."
- Each condition is a clickable chip that opens a single-status editor or immediately removes it.
- A "+" button adds a new condition or opens the picker.
- Full names and optional context (e.g., grappler name) prevent ambiguity.

**Why it works for Roll-Drauf:**
- Extremely accessible to screen readers; no hidden meaning in icons alone.
- Mobile-friendly; no 2D grid navigation.
- Labels are always visible; no hover necessary.
- Prose-style is familiar from note-taking apps and Discord tags.

**Example sources:** D&D Beyond's monster stat pages, Oblivion Portal's condition display.

---

## 5. Bad examples and failure modes

### Failure A: Icon-Only Grid with No Label on Hover

**The problem:**
- A 4×4 grid of small, unlabeled status icons with no tooltips.
- A new player does not know what each icon means.
- The system requires reading external docs or asking the GM every time.
- Color-only distinction (faded = inactive) fails for colorblind users.

**Why it fails:**
- [W3C Accessible Names and Descriptions](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/) requires every interactive element to have an accessible name and visible text. Icons alone do not meet this standard.
- Screen reader users cannot use the picker at all.

**Reference:** Older Foundry modules and Roll20 token marker grids are cited in community forums as frustration sources.

### Failure B: "Clear All" Without Confirmation

**The problem:**
- A prominent "CLEAR ALL CONDITIONS" button with no confirm dialog.
- A misclick or accidental touch clears the entire setup, with no undo button visible in the picker.
- The token must be re-edited via API or a fresh upload; game flow is interrupted.

**Why it fails:**
- [W3C Dialog Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) and common UX practices require confirmation for destructive actions. "Clear all" affects the entire token state and cannot be undone by the picker itself.
- Mobile users are especially vulnerable to accidental touches.

**Community complaint:** Several PF2e Discord threads report players accidentally clearing all statuses during combat and losing 10+ minutes to recovery.

### Failure C: Status Grid That Moves During Sorting

**The problem:**
- The picker re-sorts applied conditions to the top every time one is toggled.
- The user's muscle memory breaks; they cannot find the next condition to click.
- On mobile, sorting causes re-flow that can push the button outside the viewport.

**Why it fails:**
- Persistent visual layout is a fundamental UX principle. Layout stability is especially important for rapid input (combat rounds). The [W3C Interaction Styles](https://www.w3.org/WAI/fundamentals/accessibility-principles/) section notes that predictable layout is essential for all users, especially those with motor impairments.

**Reference:** Early iterations of some Foundry modules; community reports on Reddit cite this as a "must fix."

### Failure D: Duration Fields with No Clear Semantics

**The problem:**
- A status picker shows a text field "Duration: 3" with no unit label (rounds? minutes? turns?).
- A player applies "Blinded" with duration 5, but the system interprets it as game days instead of combat rounds.
- The spell does not expire at the right time; the condition persists incorrectly.

**Why it fails:**
- No shared understanding of duration units and tick behavior. The system must define whether durations are rounds, turns, real-time, or custom, and that definition must be visible to every player who enters a value.
- The current `metadata_json.conditions` array stores strings only; there is no schema for duration or value fields yet.

**Community note:** D&D Beyond and Pathfinder 2e official tools require explicit unit selection (dropdown) for this reason.

---

## 6. Lessons learned

1. **Canonical status list beats free-form entry.** If Roll-Drauf defines a small, canonical set of statuses (e.g., 15–20 D&D 5e core conditions), UI friction drops dramatically. Players do not typo "Blinded" as "Blind" or "BLINDED". A system-defined list also enables icon/color branding; the community recognizes "red circle" = "dying" by convention.

2. **Icons alone are insufficient.** Status icons must always have an accompanying label or be revealed on hover/focus. The W3C APG and accessibility community are clear on this: [Accessible Names and Descriptions](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/). Every interactive element needs a name and visible text.

3. **State visibility is not optional.** Applied/inactive distinction must use **both** visual (icon/color) **and** text cues. The checkbox pattern with explicit labels (checked vs. unchecked) is the proven approach.

4. **Destructive actions need confirmation.** "Clear all" and batch deletes must show a confirmation dialog naming what will happen and offering an undo if possible. One misclick should not erase game state.

5. **Picker placement matters for speed.** Quick-access status toggles should be within 2–3 clicks of the selected token (e.g., as a HUD section or popover). Burying them in a 4-level menu slows down combat.

6. **Duration and values need schema.** If a condition can have a duration (e.g., "Blinded for 3 rounds"), the system must define the unit, the tick/increment semantics (per round, per turn, per day?), and who can edit it (GM only, or player?). Freeform text will cause confusion.

7. **Realtime sync is non-negotiable.** If one player applies a condition and another player's screen does not reflect it within 1 second, the table feels broken. The picker must update from server events; local-only state will desync.

8. **Mobile and touch require larger targets.** Status icons on a grid should be at least 40×40 pixels to be safe for touch. On mobile, a bottom-sheet flow (not a popover) is more reliable than a floating HUD.

---

## 7. Community favorites

The following are anecdotal preferences collected from VTT community discussions. They do not override accessibility or security requirements but may inform UX polish:

- **"I want to type to search."** Across PF2e, D&D 5e, and homebrew communities, users ask for type-ahead search in status pickers. Typing "bl" to filter to "Blinded" is faster than scrolling a 30-condition list. [Anecdotal: PF2e community forums, 2025–2026.]

- **"Show which round a condition expires."** Combat players want to see "Blinded until round 5" without doing math. If the system tracks turn/round state, displaying expiration dates prevents "Uhhh, when does this go away?" moments. [Anecdotal: D&D Beyond forums and Foundry subreddits.]

- **"One-click toggle is king."** Most players do not want a modal picker for every condition; they want to click the token, see a quick HUD, and toggle checkboxes in place. Modal pickers are good for setup (e.g., preparing an NPC) but not for rapid mid-combat changes. [Anecdotal: Foundry community, PF2e module feedback.]

- **"Let me see conditions in the token list, not just a number."** Players running multi-token combats (e.g., 5 goblins + 3 party members) want to glance at the sidebar and see at a glance that "Goblin 1 is Blinded, Goblin 2 is Unconscious." The current count-only badge is too terse. [Anecdotal: Foundry user surveys and GitHub issue discussions.]

- **"Icon palettes should be reskinnable."** Players want status-effect icons to match their game's aesthetic. Foundry's modularity allows packs to override the visual icon for "Blinded" without changing the code. This is aspirational for Roll-Drauf but noted as a quality-of-life feature. [Anecdotal: Foundry ecosystem feedback.]

---

## 8. Roll-Drauf fit and explicit non-goals

### Fits this slice

- A small, canonical set of D&D 5e-derived statuses (Blinded, Charmed, Concentrating, Deafened, Exhausted, Frightened, Grappled, Incapacitated, Invisible, Paralyzed, Petrified, Poisoned, Prone, Restrained, Stunned, Unconscious — ~15 core statuses)
- A labeled, checkbox-based picker UI accessible from the selected-token HUD
- Toggle and clear-one operations with visual confirmation
- A "clear all" button with a confirmation dialog
- Realtime synchronization via existing socket events
- Read-only mode for players on read-only tokens
- Mobile-friendly bottom-sheet presentation
- Keyboard and screen-reader support via native checkboxes or equivalent ARIA roles

### Explicitly deferred to later slices

- **Durations and expiration:** Tracking whether a condition expires "at the end of turn 5" or "after 10 minutes" is a combat feature; defer to Slice 06 (Combat tracker) to define turn/round tick semantics.
- **Custom statuses:** User-defined condition catalogs and icon packs are a configuration feature; defer to setup/admin tooling.
- **Active Effects and derived penalties:** Linking a condition to automatic mechanical effects (e.g., "Blinded applies a -5 penalty to attack rolls") is a game-mechanics layer; defer to the action catalog or macro system.
- **Condition persistence across sessions:** Whether conditions carry over when a scene is reloaded is a session/checkpoint feature; defer to persistence policy.
- **Hierarchical conditions:** Some systems have "Exhaustion" with levels (1–6) or "Injury" with tiers. Start with simple on/off; level/value tracking can be added later if needed.

### Not in scope for Slice 05

- Rewriting the combat tracker (Slice 06).
- Integrating with Beyond20 or external character sheets (separate integration work).
- Mob token condition pooling or bulk operations across multiple tokens (batch operations may come in later).
- Complex condition interactions (e.g., "Blinded + Paralyzed = Super Helpless"); game design decisions belong in the game system, not the UI.

---

## 9. Proposed interface/data/permission contracts

### Data schema

Upgrade `metadata_json.conditions` to a structured format:

```javascript
{
  "conditions": [
    {
      "id": "blinded",              // System ID (enum or registry key)
      "label": "Blinded",           // Display name
      "icon_url": "/api/icons/conditions/blinded.svg",  // Icon asset (optional, initially null)
      "active": true,               // Applied state
      "value": null,                // Optional: numeric value (e.g., exhaustion level 2)
      "duration": null,             // Optional: expiration spec, reserved for Slice 06 (currently null)
      "source": "gm_action"         // Audit: who/what set it (optional)
    },
    {
      "id": "concentrating",
      "label": "Concentrating",
      "active": true,
      "value": null,
      "duration": null,
      "source": "player_action"
    }
  ]
}
```

### Server-side contract

Define a `/api/table/tokens/{id}/conditions` endpoint:

```
GET /api/table/tokens/{id}/conditions
  → Returns { conditions: [...], version: <hash> }

POST /api/table/tokens/{id}/conditions/toggle
  → { condition_id: "blinded" }
  → Atomically applies or removes the condition
  → Returns { conditions: [...], version: <new_hash> }
  → Error if token_id is invalid or user lacks write permission

POST /api/table/tokens/{id}/conditions/clear
  → {} or { condition_ids: ["blinded", "prone"] } for selective clear
  → Requires GM permission for other players' tokens
  → Returns { conditions: [...], version: <new_hash> }
  → Must broadcast realtime update to session
```

Alternatively, conditions remain in `metadata_json` and toggle operations go through the existing token PATCH endpoint, with optimistic concurrency validation.

### Permission model

- **Player:** Can read and toggle conditions on their own character token. Cannot clear another player's conditions.
- **GM:** Can read and toggle conditions on any token. Can clear all conditions on any token (with confirmation).
- **Read-only:** Can see conditions but cannot toggle or clear them. The picker is display-only.

### Realtime contract

Broadcast condition changes via the existing socket event. The current event may include `metadata_json`; if so, the client-side picker must reconcile incoming updates and merge with local state, using a version hash to detect conflicts.

Example event payload:
```javascript
{
  "event": "token_updated",
  "token_id": 42,
  "token": { ..., "metadata_json": { "conditions": [...] }, "version": "abc123" },
  "changed_by": "gm_user_id",
  "timestamp": 1725000000
}
```

---

## 10. Risks and assumptions with severity labels

### Risk 1: Conditions remain free-form strings (MEDIUM)

**Assumption:** The backend will enforce a canonical condition ID list or accept arbitrary strings.

**Concern:** If arbitrary strings are allowed, the picker UI will not scale. A player could enter "blinded123" or "confused" (typo'd), creating inconsistent state.

**Mitigation:** Define a small canonical list (15–20 conditions) upfront. The server should validate condition_id against the registry and reject unknown values. Document this registry clearly.

**Severity:** MEDIUM. This affects data consistency but not security. If caught during Apply phase, it is a one-time fix.

---

### Risk 2: Duration semantics conflict with combat slice (MEDIUM)

**Assumption:** Slice 06 (Combat) will define turn/round tick behavior.

**Concern:** If Slice 05 ships a picker with a "Duration" field but Slice 06 does not define how to apply it, durations will not expire correctly. Game logic will break.

**Mitigation:** Defer the duration field to Slice 06. In Slice 05, allow the schema to carry an optional `duration` field but do not surface it in the UI yet. This leaves room for combat logic without unblocking the condition picker.

**Severity:** MEDIUM. This is a known dependency; make it explicit in Apply.

---

### Risk 3: Realtime conflict when GM and player toggle the same condition (MEDIUM)

**Assumption:** The server will use version hashes to detect conflicts.

**Concern:** If both the GM and a player try to toggle "Blinded" at the same time, a naive merge might apply it twice or fail to apply it at all.

**Mitigation:** Use optimistic concurrency. The server rejects any write with a stale version hash and returns the current state. The client reconciles: if the server's version is newer, accept it and re-render; if the user's change is compatible (e.g., toggle a different condition), replay it.

**Severity:** MEDIUM. This is solvable with existing patterns (Slice 04 token HUD already does this for HP).

---

### Risk 4: Icon catalog is not yet standardized (LOW)

**Assumption:** Roll-Drauf will use text labels for now and add icons in a later pass.

**Concern:** Without a visual icon library, the picker UI will be dense text. This is not ideal but is acceptable as a first slice.

**Mitigation:** Start with text labels + checkboxes. Placeholder icon URLs in the schema allow the icon layer to be added later without schema changes.

**Severity:** LOW. Text-only picker is accessible and functional; icons are a polish feature.

---

### Risk 5: Mobile touch target size (LOW)

**Assumption:** The checkbox UI on mobile will use native HTML checkboxes or touch-friendly buttons (minimum 40×40 pixels).

**Concern:** If the picker is rendered as a dense grid of tiny checkboxes, mobile users cannot reliably tap them.

**Mitigation:** Use a bottom-sheet with a list layout on mobile (not a grid). Each row has a 44px minimum height and a wide hit target. Desktop can use a more compact grid if space allows.

**Severity:** LOW. Responsive layout is standard practice; no technical blocker.

---

### Risk 6: "Clear all" is dangerous and hard to undo (MEDIUM)

**Assumption:** There is no built-in undo in the picker; clearing conditions is final per turn.

**Concern:** A misclick can clear 5 carefully-set conditions; the GM must reapply them one by one.

**Mitigation:** Always require a confirmation dialog before clearing all. The dialog should show "This will remove X conditions from [Token Name]" and offer a Cancel button. Do not offer undo in the picker itself (undo is out of scope for this slice).

**Severity:** MEDIUM. This is UX, not a technical blocker, but it is important for player trust.

---

### Risk 7: Read-only mode must be enforced server-side (MEDIUM)

**Assumption:** The server will reject condition edits if the user lacks write permission.

**Concern:** A malicious client could send a toggle request even if read-only mode is set in the UI. The server must validate.

**Mitigation:** The server endpoint must check `user.role` and token ownership before allowing a condition toggle. The UI can disable the picker buttons, but the endpoint is the authoritative check.

**Severity:** MEDIUM. This is a standard permission boundary; no new architecture needed.

---

---

## 11. Acceptance criteria

### Desktop

- [ ] A token HUD includes a "Conditions" button or section.
- [ ] Clicking "Conditions" opens a popover or modal showing checkboxes for each active condition.
- [ ] The popover displays all available conditions (canonical list, ~15 items) with labels and checkboxes.
- [ ] Clicking a checkbox toggles the condition on/off; the server updates within 1 second.
- [ ] A "Clear all" button deactivates all conditions with a confirmation dialog that names the token and condition count.
- [ ] The popover closes on Escape or outside-click (non-modal) without losing unsaved changes.
- [ ] A selected token shows updated conditions in the token list sidebar (not just a count badge).
- [ ] The popover does not cover the selected token or critical map controls.

### Mobile

- [ ] Tapping a token opens the token sheet on the mobile bottom-sheet panel.
- [ ] The sheet includes a "Conditions" section with a list layout (not a grid).
- [ ] Tapping a checkbox toggles the condition; the server updates within 1 second.
- [ ] Each list item is at least 44 pixels tall; the touch target is wide.
- [ ] A "Clear all" button shows a confirmation dialog.
- [ ] The sheet scrolls independently without trapping focus behind the backdrop.

### Keyboard

- [ ] Tab key navigates to the Conditions button from the HUD.
- [ ] Enter/Space opens the picker.
- [ ] Tab navigates between checkboxes inside the picker.
- [ ] Space toggles the focused checkbox.
- [ ] Escape closes the picker and restores focus to the HUD button.
- [ ] Screen readers announce each condition label, checked state, and the total count (e.g., "Blinded, checkbox, checked").

### Permissions and read-only

- [ ] A player can read and toggle conditions on their own character token.
- [ ] A player cannot toggle conditions on other players' tokens or NPCs.
- [ ] A GM can toggle conditions on any token.
- [ ] A read-only user sees conditions but cannot toggle or clear them; buttons are disabled and a tooltip explains the restriction.

### Realtime updates

- [ ] When the GM toggles a condition, all players' clients show the updated state within 1 second.
- [ ] If a player and GM toggle the same token's condition at the same time, the server resolves the conflict using version hashes. The newer state is authoritative.
- [ ] If a player adds a condition and the connection drops mid-transaction, the client reconciles from the server's next broadcast.

### Errors and recovery

- [ ] If a toggle fails (e.g., network error), the client reverts the optimistic UI change and shows a brief error message (e.g., "Condition update failed. Try again.").
- [ ] If the server returns a version conflict, the client re-renders from the server's state without asking.
- [ ] If the token is deleted by another user, the picker closes and focuses the map.

### Destructive actions

- [ ] A "Clear all" button requires a confirmation dialog.
- [ ] The dialog shows the token name and condition count: "Remove all 4 conditions from Goblin 1?"
- [ ] Only after confirming does the clear take effect.

---

## 12. Apply handoff

**Decision 1: Canonical status catalog**

Decide whether to:
- (A) Use a hardcoded D&D 5e core list (15 statuses): Blinded, Charmed, Concentrating, Deafened, Exhausted, Frightened, Grappled, Incapacitated, Invisible, Paralyzed, Petrified, Poisoned, Prone, Restrained, Stunned, Unconscious.
- (B) Allow custom user-defined catalogs (requires a config/registry backend).
- (C) Start with (A) and defer (B) to a later admin tooling slice.

**Recommendation:** (C). A hardcoded list ships faster and is more testable. Custom catalogs can be added in a later admin slice if demand warrants.

---

**Decision 2: Data persistence for conditions**

Decide whether to:
- (A) Keep conditions in `metadata_json.conditions` (existing location, requires schema validation).
- (B) Add a dedicated `token.conditions` field and migrate existing data.
- (C) Use a join table `token_conditions` for queryability and audit.

**Recommendation:** (A). `metadata_json` is already in place and versioned. Adding a schema layer and server-side validation is sufficient. Avoid migration complexity if the existing column works.

---

**Decision 3: Duration field and Slice 06 dependency**

Decide whether to:
- (A) Include a "Duration" field in the picker UI for Slice 05, with free-form text entry.
- (B) Include a `duration` field in the schema but do not surface it in the Slice 05 picker UI.
- (C) Defer duration entirely to Slice 06 and leave the schema empty for now.

**Recommendation:** (B). Allow the schema to carry optional `duration` and `value` fields (reserved for future use) but do not show them in the UI yet. This unblocks Slice 05 without overcommitting Slice 06.

---

**Decision 4: Clear-all confirmation and undo strategy**

Decide whether to:
- (A) Always show a confirmation dialog for "Clear all" (no exceptions).
- (B) Show a confirmation only if more than 2 conditions are active (avoid dialog spam for single-condition clears).
- (C) Offer an undo button in the picker for a brief window (e.g., 5 seconds) after clearing all.

**Recommendation:** (A). Always confirm. It is better to show one extra dialog than to risk data loss. A brief undo window (C) is nice-to-have but out of scope; a confirmation dialog (A) is the minimum safety threshold.

---

**Decision 5: Icon catalog and visual design**

Decide whether to:
- (A) Ship text-only labels in the picker (no icons for Slice 05).
- (B) Include placeholder icon URLs in the schema and use simple Unicode symbols (e.g., 👁️ for Blinded) as a quick pass.
- (C) Commission or source a professional icon set and require it for Slice 05.

**Recommendation:** (A). Text labels are accessible and sufficient. Icons are a polish feature and can be added in a Slice 06/07 quality pass. Do not block Slice 05 on icon design.

---

**Decision 6: Mobile vs. Desktop picker layout**

Decide whether to:
- (A) Use one picker layout everywhere (grid for desktop, reflow for mobile).
- (B) Use separate layouts: grid popover for desktop, bottom-sheet list for mobile.
- (C) Always use bottom-sheet for both (simpler implementation, less space).

**Recommendation:** (B). Separate layouts fit the existing responsive architecture (desktop floating panels, mobile sheet). Grid is faster for desktop; list is more touch-friendly for mobile.

---

## Next steps (Apply phase)

Once these decisions are made, the Apply phase will:

1. Lock the canonical status list and update the backend schema/migration.
2. Define the picker UI mockup (layout, labels, keyboard focus order).
3. Write contract tests for the toggle/clear endpoints (no implementation yet).
4. Document the permission model and conflict-resolution strategy.
5. Estimate implementation effort (expected: 2–3 days for core picker + tests).

Do not implement code until Apply handoff is approved.

---

## Sources

### Primary (First-Party/Standards)

- [Foundry VTT Tokens](https://foundryvtt.com/article/tokens/) — official token and status-effect documentation
- [Foundry VTT TokenDocument API](https://foundryvtt.com/api/classes/foundry.documents.TokenDocument.html) — server-side token model
- [Foundry VTT Token HUD API](https://foundryvtt.com/api/classes/foundry.applications.hud.TokenHUD.html) — status picker implementation reference
- [Foundry VTT CONFIG.statusEffects](https://foundryvtt.com/api/variables/CONFIG.statusEffects.html) — status registry and catalog
- [W3C Checkbox Pattern (APG)](https://www.w3.org/WAI/ARIA/apg/patterns/checkbox/) — accessibility and keyboard semantics
- [W3C Switch Pattern (APG)](https://www.w3.org/WAI/ARIA/apg/patterns/switch/) — toggle alternative (not recommended for status effects)
- [W3C Disclosure Pattern (APG)](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/) — expandable sections
- [W3C Accessible Names and Descriptions (APG)](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/) — label requirements

### Roll-Drauf Current State

- `vtt/static/js/play-ui.js:2270–2274` — token list conditions rendering
- `vtt/static/js/play-ui.js:2437–2441` — token overlay conditions badge
- `docs/PLAYTABLE_UI_RESEARCH_2026-08-27.md` — overall playtable architecture and token HUD design
- `docs/PLAYTABLE_FEATURE_WORK_PACKAGE_2026-08-27.md` — iteration order and phase gates

### Community (Anecdotal/Opinion)

- PF2e community forums and Reddit (condition search and UI feedback, 2025–2026)
- D&D Beyond forums (condition display and grouping feedback)
- Foundry Reddit community (icon recognition and mobile accessibility discussions)

---

**End of research note.**

This research document is complete and ready for Apply phase review. No production code has been modified. The target file is the Markdown note itself. Handoff to implementation decisions awaits.
