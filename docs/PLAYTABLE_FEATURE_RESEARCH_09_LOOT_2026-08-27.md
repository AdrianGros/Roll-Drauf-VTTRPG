# Playtable feature research: Loot transfer and inventory

**Date:** 2026-08-27  
**Status:** research/discover phase; no production implementation approved  
**Scope:** Safe VTT loot transfer from token containers to character inventories

## 1. Status and input summary

Slice 09 investigates safe, atomic loot transfer from selected tokens (e.g., dead enemies, treasure chests) to player character inventories or shared party stash. The table needs to go beyond single-character inventory CRUD to support multi-source selection, container ownership, recipient eligibility, quantity review, permission checks, transaction atomicity, idempotent retry, conflict handling, audit trails, and undo/recovery.

Research inputs:
- Current Roll-Drauf `InventoryItem` model: character-owned, CRUD-only, no stacking/transfer contract.
- Current `TokenState`: has `character_id` and `owner_user_id`; no container or loot relations.
- Current action executor: single-token, single-action; no batch or multi-step operations.
- Foundry VTT item/actor/container semantics and community loot modules.
- ACID transaction principles and idempotency patterns for inventory systems.

## 2. Current Roll-Drauf state and relevant file inventory

### Existing implementation seams

**Character Inventory (character-owned CRUD only):**
- `vtt/models/inventory_item.py`: `InventoryItem` with `character_id`, `quantity`, `weight_per_unit`, `is_consumable`, `is_cursed`, `cost`, and `effects`. Includes `.use(amount)` to consume and delete. Serialized with `.serialize()`.
- No dedicated container model or loot-specific metadata.

**Token State:**
- `vtt/models/token_state.py`: `TokenState` has `character_id` (optional, for player tokens), `owner_user_id` (player owning this token), `name`, `token_type` (player/enemy/object), `metadata_json`, and `version` for optimistic concurrency.
- No `loot_container` relation, no `inventory_source` flag, no multi-selection state.

**Session and Permission Boundary:**
- `vtt/play/routes.py` and `vtt/play/actions.py`: single-token action executor via `execute_action(action_code, token_id, actor_user_id, ...)`.
- Permission model: character-owned items are tied to `character_id`; tokens owned by users are tied to `owner_user_id`.
- No loot-transfer endpoint or multi-token batch executor yet.

**Frontend State:**
- `play-ui.js`: `selectedTokenId` (single); no multi-selection or batch-action state.
- Token widget shows name, HP, conditions; no loot-transfer action yet.
- Action catalog in `play/actions.py` lists basic actions (attack, dash, interact); no loot action.

## 3. Web research and source-backed findings

### Foundry VTT Item and Loot Model

Foundry VTT distinguishes **Items** (reusable, world-level templates) from **Owned Items** (embedded documents copied to an actor sheet). Drag-and-drop transfer from the Items Directory onto an actor creates a new Owned Item entry; changes to the original item template do not affect existing copies. ([Foundry Items documentation](https://foundryvtt.com/article/items/))

Foundry's core system does not provide a native built-in loot or container system. Instead, community modules extend the model:

- **Loot Sheet NPC 5E** and **Loot Sheet NPC Pathfinder1**: Use the NPC sheet as a loot UI. GMs can mark NPCs as loot containers, and players can drag items to their character sheets. The drag-and-drop mechanics rely on the actor/item relationship. ([Loot Sheet NPC 5E](https://foundryvtt.com/packages/lootsheetnpc5e/))
- **Item Piles**: Represents items as interactive on-canvas tokens (piles or chests) with open/close state, weight tracking, and drag-to-actor transfer. Piles are their own actor-like entities with an item list. ([Item Piles](https://foundryvtt.com/packages/item-piles/))
- **Pick-Up-Stix**: Allows placing interactive container tokens on the map; players click to open an inspection dialog and drag items to their inventory. ([Pick-Up-Stix](https://foundryvtt.com/packages/pick-up-stix/))
- **Item Collection** and **Transfer Stuff**: Modules for bag-like items or direct actor-to-actor transfer without duplication. Transfer Stuff increases quantity if the same item type already exists on the recipient. ([Item Collection](https://foundryvtt.com/packages/itemcollection/), [Transfer Stuff](https://foundryvtt.com/packages/transfer-stuff/))

**Key lesson:** Foundry's drag-and-drop model works for low-risk transfers because the source remains authoritative and the browser cannot apply transfers without server validation. VTT modules extend this with container actors, explicit UI workflows, and conflict resolution.

### Transaction, Inventory, and Security Principles

**Atomicity (ACID properties):** An atomic transaction is a sequence of database operations executed as a single unit—all succeed or all fail, with no partial state. ([Atomic Transactions in Databases](https://www.datacamp.com/tutorial/atomicity)) In inventory systems, this means: transfer source quantity -= N, recipient quantity += N, and audit log entry all commit together. If any step fails, the entire transfer rolls back.

**Idempotency:** An idempotent request can be safely repeated without changing the outcome beyond the first submission. In inventory contexts, if a client retries a failed transfer (due to network timeout), the server must recognize the retry and return the same result without double-transferring items. Implementations use idempotency keys (unique request IDs) to track completed operations. ([Using Atomic Transactions to Power an Idempotent API](https://www.geeksforgeeks.org/dbms/using-atomic-transactions-to-power-an-idempotent-api/), [Idempotent Transaction Requests](https://image-ppubs.julius.uspto.gov/dirsearch-public/print/downloadPdf/11449490))

**Conflict handling:** When network delays cause stale client state, version numbers or timestamps let the server detect conflicts and reject or reconcile updates. Financial and inventory systems use this to prevent double-spending or over-withdrawal.

**Permission boundary:** Character-owned inventory is tied to character permissions; loot sources are tied to token ownership and location (e.g., a corpse in a public scene, or a locked chest). The server must validate that the actor requesting the transfer owns or has permission for the source tokens and the recipient character.

### VTT Loot Workflows (Community Favorites)

From Foundry community modules and player feedback:
1. **Dead enemy loot:** Right-click or open the NPC sheet, see its inventory, drag items to player sheet. No explicit permission prompt if the token is in a public scene or the actor is DM-owned.
2. **Treasure chest container:** A token with a special "loot" flag can be opened as a dialog. Players see the items, click to add to inventory. The chest updates in real-time.
3. **Party stash/shared bag:** A special character or token acts as a shared inventory. Players can deposit or withdraw items, with audit logged per-player.
4. **Quantity review:** Some modules show a dialog: "Transfer 5x Potion of Healing from [NPC] to [Player]?" before commit. Others auto-add if the item already exists (stacking).
5. **Undo/recovery:** Few VTT modules provide true undo; most rely on audit logs and manual reversal by the DM.

**Community anecdotal preferences** (not requirements):
- Drag-and-drop is fast but fragile over network delays.
- A confirmation dialog prevents accidental transfers, especially for cursed items or one-of-a-kind treasure.
- Real-time broadcast of transfers to the table prevents confusion ("wait, did you get that?").
- Clear audit trails in chat or a log answer questions days later.
- A "collect all" button for mass transfers (e.g., all coins from defeated enemies).

## 4. Good examples

| Example | What works | Why it fits Roll-Drauf |
|---------|-----------|------------------------|
| **Foundry drag-and-drop items** | Source remains authoritative; browser cannot commit without server validation. Owned Item copies are independent of the template. | Aligns with server-first permission model. Transfer must be validated server-side even if UI shows real-time preview. |
| **Item Piles container tokens** | Interactive on-canvas objects with open/close state, weight tracking, and per-user/per-party access. Piles update in real-time as players take items. | Matches "selected token context" architecture. A corpse or chest can be a container token with items, permissions, and audit. |
| **Transfer Stuff (actor-to-actor)** | Transfers by dragging; if recipient already has the item type, increments quantity instead of duplicating. Idempotent retry via request ID. | Natural UI and stacking behavior; non-destructive on network retry. |
| **Loot Sheet NPC 5E** | NPC sheet shows items as a loot list; click to mark as source; drag to player. Audit in chat. | Reuses existing sheet drawer pattern; familiar to D&D players. |
| **Server-side atomicity (financial systems)** | Transactions use database locks, version checks, or event log to ensure transfer and audit commit together. Conflicts rejected or reconciled via version snapshot. | Prevents race conditions when multiple players transfer from the same source or receive into the same stash simultaneously. |

## 5. Bad examples and failure modes

| Failure mode | Why it's bad | Lesson |
|---|---|---|
| **Client-side item deletion** | Browser deletes from source inventory and adds to recipient without server confirmation. Network failure leaves inconsistent state. Attacker can dupe items by replaying add without delete. | Never trust client state for destructive operations. Always validate and execute server-side. |
| **Unconfirmed quantity change** | UI shows "transfer 5x"; client submits but network timeout; user retries. Server processes both attempts: 10x transferred. | Idempotency key required. Assign a unique request ID per transfer; server tracks completed IDs and rejects duplicates. |
| **No permission check on source** | Player tokens transfer items from any token on the map, including locked chests or DM-only NPCs. | Validate that the actor requesting transfer has permission for source ownership/location. |
| **Stale version overwrite** | Token HP is version 5; player sees "10 HP" in HUD from version 3; updates to "5 HP". Concurrent DM damage event increments version to 6 with "15 HP". Player's update gets rejected, then silently ignored. | Use pessimistic or optimistic version checks. Reject stale submissions; reconcile with server snapshot; notify user of conflict. |
| **No audit trail** | Items vanish from NPC sheet with no log. Players dispute who took what. DM cannot undo or investigate theft. | Emit audit events for every transfer: source, quantity, recipient, actor, timestamp. Append to session chat or separate audit log. |
| **Undo impossible** | Player transfers the only copy of a quest item to wrong character. No undo; must ask DM to manually re-transfer. | Idempotent transfer lets client safely retry; server state resets on network error. For accidental transfers, log operations and provide DM-level undo command. |
| **No multi-selection** | Can only transfer from one token at a time. Players must open each NPC/chest one by one. | Add multi-select checkbox, count badge, and "collect from all" action. Batch operations reduce UI friction and confusion. |
| **Missing container model** | `InventoryItem` is character-owned only; no way to represent a chest or corpse as a source of items. | Add explicit `TokenLoot` or `Container` relation linking tokens to item sources. Allow tokens to act as containers without needing a full character. |

## 6. Lessons learned

1. **Server-side atomicity is non-negotiable.** All transfers must validate, execute, and audit in one database transaction. Browser state is optimistic preview only; server is source of truth.

2. **Idempotency keys prevent retry disasters.** Every transfer request needs a unique ID. Server marks completed transfers and rejects or deduplicates retries. Without idempotency, network timeouts cause duplication.

3. **Permissions are tied to ownership and context.** A token's items belong to the owning player or the scene/DM. Source-permission checks prevent unprivileged transfer. Recipient eligibility checks prevent transferring to off-session characters.

4. **Containers are not characters.** A corpse, chest, or loot pile is a token with an item list, not a full character. Avoid inflating `InventoryItem` to every entity. Use a separate `TokenLoot` or `LootContainer` model for sources.

5. **Multi-selection is UX not just convenience.** Batch transfers ("collect from all defeated enemies") reduce clicks and mistakes. UI must track a set of sources, show a count, and validate all sources together.

6. **Quantity review before commit prevents accidents.** A dialog showing "from X to Y: 5x Potion +3 Longsword" lets players spot mistakes before irreversible commit. Network errors are recoverable; wrong recipient is not.

7. **Audit trails are required for trust.** VTT loot involves valuable items and player disputes. Every transfer must log: source token/character, quantity, recipient, actor, timestamp. Make logs searchable and exportable for DM investigation.

8. **Conflicts require reconciliation, not silent failure.** When concurrent updates happen (DM adds item; player transfers), version conflict must be explicit: reject, offer merge options, or auto-merge by appending quantity. Never silently ignore a conflict.

## 7. Community favorites

(Anecdotal preferences from VTT community; not requirements; may vary by campaign style.)

- **Drag-and-drop loot UI is preferred over dialogs**, but confirmation dialogs are expected for high-value or cursed items. ([Item Piles](https://foundryvtt.com/packages/item-piles/), [Transfer Stuff](https://foundryvtt.com/packages/transfer-stuff/))
- **"Collect all" button for coins/loot** is frequently requested. Players want to sweep defeated enemies for treasure in one click, not drag each item. (Community feedback in Foundry module discussions)
- **Real-time loot updates** so the table sees items move. If one player takes a potion, others see the count decrement immediately. (Anecdotal: reduces "did you get that?" confusion.)
- **Undo/revert for accidental transfers** is wanted but rarely implemented. Most VTTs rely on DM manual reversal. (Feedback in Loot Sheet NPC discussions)
- **Shared party stash** is a popular pattern for tracking group treasure and expenses. One character acts as the bank. (Anecdotal: many campaigns use a "Stash" or "Party" character entry.)
- **Clear ownership:** Players want to know who owns a loot source—is this enemy corpse DM-controlled, or is it a player's fallen ally? (Context matters for permission and roleplay.)

## 8. Roll-Drauf fit and explicit non-goals

### Belongs in Slice 09

- **Safe multi-source selection:** Extend `selectedTokenIds` to allow Ctrl/Cmd-click multi-select or checkbox toggle.
- **Recipient eligibility:** Define who can be a transfer recipient (party-member characters in the session, shared stash characters, on-session constraints).
- **Quantity review dialog:** Show source, item list, quantities, recipient, and commit-or-cancel flow.
- **Server-side transfer command:** New `POST /play/session/:session_id/transfer-loot` endpoint validating permissions, quantities, versions, atomicity.
- **Idempotency contract:** Request includes an idempotency key; server returns cached result on retry or processes once on first submission.
- **Audit and chat event:** Log transfer to session chat or audit table with clear attribution.
- **Item stacking:** If recipient already has the item type, merge quantities instead of creating duplicate entries.
- **Permission and ownership checks:** Validate that source tokens are DM-owned, in the active scene, or otherwise eligible; recipient character is in the session.
- **Version conflict handling:** Detect stale transfers via `TokenState.version`; reject or offer reconciliation.

### Explicitly deferred (Slices 10-11 or later)

- **Container/bag items** (items that hold other items): Defer until a dedicated container data model is approved. Use simple linear inventory for now.
- **Encumbrance or weight limits:** Calculate total weight but do not block transfers. Warn if over limit; let DM override.
- **Cursed or special-handling items:** No special curse logic yet. Treat cursed items as regular inventory with a metadata flag.
- **Undo/revert command:** Defer until audit log schema and DM command API are approved.
- **Merchant/NPC sell/buy UI:** Defer to a separate commerce slice. Loot transfer is one-way move only.
- **Multi-session or cross-party transfers:** Keep transfers scoped to the active session. Cross-session moves (e.g., between campaigns) require additional permission and character-status logic.
- **Reduced-motion or large-token-count performance:** Addressed in Slice 11 (Quality pass).

## 9. Proposed interface/data/permission contracts

### Frontend Multi-Selection State

Extend `tableState` (from Slice 2-4 research) with:
```
selectedTokenIds: [tokenId, ...],  // One or more sources for batch operations
batchAction: null | "transfer-loot" | "...",
transferContext: {
  sourceTokenIds: [tokenId, ...],  // Selected sources
  recipientCharacterId: characterId,  // Target character or stash ID
  idempotencyKey: uuid,  // Unique request ID for retry safety
  preview: {
    itemsBySource: { tokenId: [{ id, name, quantity, ... }, ...] },
    recipientBefore: { characterId: { items: [...], total_weight } },
    recipientAfter: { items: [...], total_weight },
  },
}
```

### Server Transfer Endpoint

```
POST /play/session/:session_id/transfer-loot
{
  "idempotency_key": "uuid",
  "source_token_ids": [tokenId, ...],
  "recipient_character_id": characterId,
  "items": [
    {
      "source_token_id": tokenId,
      "item_id": inventoryItemId,
      "quantity": 5,
    },
    ...
  ],
}

Response (201 Created):
{
  "status": "transferred",
  "idempotency_key": "uuid",
  "audit_log_id": logId,
  "source_deltas": {
    "tokenId": { "item_id": quantity_removed, ... },
  },
  "recipient_deltas": {
    "character_id": { "item_id": quantity_added, ... },
  },
  "event_id": socketEventId,  // Broadcast to session
}

Error responses:
{
  "status": "conflict",
  "code": "stale_version",
  "current_version": token.version,
  "message": "Token has been modified; please refresh and retry.",
}
{
  "status": "permission_denied",
  "code": "source_not_owned",
  "message": "You do not have permission to transfer from this token.",
}
{
  "status": "bad_request",
  "code": "insufficient_quantity",
  "message": "Item quantity not available in source.",
}
```

### Data Model Extensions

**New table: `loot_transfers` (audit/idempotency)**
```
id (PK)
idempotency_key (UNIQUE)
session_id
actor_user_id
source_token_ids (JSON array)
recipient_character_id
items_transferred (JSON: { item_id: quantity, ... })
response_cached (JSON: the cached 201 response for retry)
created_at
```

**TokenState extension (optional loot flag):**
```
is_loot_source (BOOL, default False)  // Marks token as eligible loot container
loot_container_type (VARCHAR: "corpse", "chest", "stash", ...)
```

**New relation: `TokenLoot` (or extend TokenState.metadata_json)**
For tokens that represent containers:
```
token_id (FK TokenState)
item_id (FK InventoryItem)
quantity_available (INT, for sourcing)
is_active (BOOL, for soft-delete or container closed)
```

**Character extension:**
```
is_party_stash (BOOL, default False)  // Special character acting as shared treasury
```

### Permission Model

- **Source permission:** Token must be in the active scene, and the requesting actor must be the token owner, a session DM, or the game session DM.
- **Recipient permission:** Character must be assigned to the active session and owned by an active player or the DM.
- **Batch permission:** All sources must satisfy the permission check; if any fail, entire batch is rejected.
- **Read-only session:** Transfers are disallowed if the session is read-only or archived.

## 10. Risks and assumptions with severity labels

| Risk | Severity | Mitigation | Notes |
|------|----------|-----------|-------|
| **Network retry causes duplication** | CRITICAL | Idempotency key + server-side deduplication. Log every attempt; return cached response on retry. | Without this, timeouts lead to duplication. |
| **Stale version overwrites** | HIGH | Version conflict check on source token. Reject or reconcile; do not silently ignore. | UI must show version check result; do not apply transfer if stale. |
| **Unprivileged transfer (player steals from DM NPC)** | HIGH | Validate source ownership and scene location. DM tokens are off-limits unless DM-approved. | Permission check is server-side only. |
| **Multi-select UX confusion** | MEDIUM | Clear visual feedback: checkboxes, count badge, source list in dialog. Test with multiple tokens/items. | Users may not realize they selected multiple sources. |
| **Race condition (concurrent transfers from same source)** | MEDIUM | Database row lock or version increment during transfer. Reject second request if first is processing. | Rare in normal play; may happen if network jitter retries fast. |
| **Audit log missing on crash** | MEDIUM | Commit audit log in same transaction as transfer. If DB transaction fails, entire request fails. | Audit must never be out of sync with transfer. |
| **Recipient over-encumbered** | LOW | Calculate weight; warn but allow. DM can override or enforce later. | Depends on campaign rules; defer enforcement. |
| **Item ID mismatch (client sends wrong ID)** | LOW | Validate item ID exists on source token before transfer. Return 400 if not found. | Client can be out of sync; always re-verify. |
| **No undo in early release** | LOW | Document as limitation. DM-level revert command can be added later. | Audit log exists for manual reversal. |
| **Multi-item stacking edge case** | LOW | Test transfer of 5x Potion when recipient has 3x. Verify result is 8x, not duplicate entry. | Stacking logic must be correct in first release. |

## 11. Acceptance criteria

### Desktop

- [ ] User can Ctrl/Cmd-click or tap checkbox to multi-select tokens on the map.
- [ ] Selected tokens show a count badge and highlight.
- [ ] Right-click or menu on any selected token opens a token-actions menu with "Transfer loot" option.
- [ ] Clicking "Transfer loot" opens a non-modal dialog showing:
  - Source token names and item list (with quantities).
  - Recipient character dropdown (showing eligible session characters + party stash if it exists).
  - A confirm/cancel button.
- [ ] On confirm, the server processes the transfer atomically. If successful, the dialog closes and both source and recipient inventories update in real-time.
- [ ] If the transfer fails (stale version, permission denied, insufficient quantity), an error banner appears with a clear message and a "Retry" or "Dismiss" button.
- [ ] Transfer audit event appears in session chat: "@Player transferred 5x Potion of Healing from Goblin (Loot) to Player Character".
- [ ] No items are duplicated or lost; quantities reconcile correctly.

### Mobile

- [ ] Multi-select works via long-press or checkbox tap (not Ctrl-click, which is not available on touch).
- [ ] The transfer dialog adapts to mobile height: scrollable item list, dismissible via outside tap or Escape.
- [ ] The dialog's cancel/confirm buttons remain visible without scrolling.
- [ ] Transfer result updates the bottom sheet or sheet drawer in real-time.

### Keyboard

- [ ] Selected tokens are keyboard-focusable and selectable via Space/Enter.
- [ ] The transfer dialog can be navigated via Tab, opened/closed via Escape, and submitted via Enter.
- [ ] Recipient dropdown is a native `<select>` or accessible combobox with arrow-key navigation.

### Permissions

- [ ] A player cannot transfer from a token owned by a different player (permission denied).
- [ ] A player cannot transfer from DM-only NPCs unless explicitly permitted.
- [ ] A player can always transfer into their own character (if in the session).
- [ ] A player can transfer into a party stash if the character is marked as shared and belongs to the session.
- [ ] DM can transfer from any token.
- [ ] Read-only session users cannot initiate transfers; they see a disabled menu option.

### Realtime Updates

- [ ] When a transfer completes, all connected clients in the session receive a broadcast event.
- [ ] Source and recipient inventories update instantly without a page reload.
- [ ] If a client is offline and reconnects, it reconciles and fetches the latest token/character state.

### Errors and Destructive Actions

- [ ] If a source token is deleted before transfer, an error appears: "Source token no longer exists."
- [ ] If the network times out, the client can safely retry using the idempotency key (no duplication).
- [ ] If the recipient character is removed from the session mid-transfer, an error appears and the transfer is rolled back.
- [ ] If quantity is insufficient (e.g., trying to take 10x but only 3x available), transfer fails with a clear message: "Only 3x available; requested 10x."
- [ ] Concurrent transfers from the same source are serialized; the second request returns a conflict with the current state.

## 12. Apply handoff: decisions still needed before implementation

1. **Container model:** Should we add a `is_loot_source` flag to `TokenState` and a separate `TokenLoot` junction table for items on corpses/chests? Or store loot in `TokenState.metadata_json` as `{ loot_items: [...] }`?

2. **Recipient scope:** Should transfers be allowed only to characters in the active session, or also to off-session party-member characters (e.g., a character on a different map)? This affects permission validation.

3. **Shared stash model:** Should a party stash be a special character flag (`is_party_stash`), or a dedicated `PartyStash` entity? Affects permission model and UI.

4. **Undo/revert:** Should we add a DM-level undo command in the first release, or defer to Slice 11? Audit log makes manual reversal possible; automatic undo requires additional schema and rollback logic.

5. **Cursed item handling:** Should cursed items block transfer, require DM approval, or transfer freely with a warning? Defer game-rule decision to Apply phase.

6. **Weight/encumbrance:** Should the transfer be rejected if the recipient would exceed weight limit, or allowed with a warning? Depends on campaign style; propose warning-only for now.

7. **Idempotency storage:** Should idempotency keys be stored indefinitely or pruned after 24 hours? Affects database size and retry window.

8. **Audit destination:** Should transfer events appear in session chat (visible to players) or in a separate audit log (DM-only), or both? Affects visibility and player experience.

9. **Item preview:** Should the transfer dialog show only summary (count of items) or detailed list (each item with name, quantity, cost)? Affects dialog complexity and scroll behavior.

10. **Multi-step workflow:** Should we support adding more sources or recipients after opening the dialog, or lock them on open? Affects stateful UI and scope of "cancel".

---

## Primary source register

**Foundry VTT Documentation:**
- [Items](https://foundryvtt.com/article/items/)
- [Loot Sheet NPC 5E](https://foundryvtt.com/packages/lootsheetnpc5e/)
- [Item Piles](https://foundryvtt.com/packages/item-piles/)
- [Item Collection](https://foundryvtt.com/packages/itemcollection/)
- [Transfer Stuff](https://foundryvtt.com/packages/transfer-stuff/)
- [Pick-Up-Stix](https://foundryvtt.com/packages/pick-up-stix/)

**Transaction and Inventory Systems:**
- [Atomic Transactions in Databases (DataCamp)](https://www.datacamp.com/tutorial/atomicity)
- [Using Atomic Transactions to Power an Idempotent API (GeeksforGeeks)](https://www.geeksforgeeks.org/dbms/using-atomic-transactions-to-power-an-idempotent-api/)
- [Idempotent Transaction Requests (USPTO Patent)](https://image-ppubs.julius.uspto.gov/dirsearch-public/print/downloadPdf/11449490)
- [Why Atomicity Breaks the Moment You Add a Network Call (The Architect's Notebook)](https://thearchitectsnotebook.substack.com/p/ep-127-why-atomicity-breaks-the-moment)

**Related Roll-Drauf Documentation:**
- `vtt/models/inventory_item.py`: Current character-owned inventory model.
- `vtt/models/token_state.py`: Token with character binding and metadata.
- `vtt/play/actions.py`: Current single-token action executor.
- `PLAYTABLE_FEATURE_WORK_PACKAGE_2026-08-27.md`: Slice dependencies and sequencing.
- `PLAYTABLE_UI_RESEARCH_2026-08-27.md`: Table interaction state model and responsiveness constraints.
