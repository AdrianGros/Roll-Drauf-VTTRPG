# Discover C08 – inventory writers beyond the original handoff

Input: approved C08 Apply, explicit Codex takeover, current live source a935a3ca0.
Current state: SRD inventory writes in srd_creator.py use owner checks but no row
lock. DM handout/take-back in srd_party_routes.py call the same commit helper
but resolve their Character/InventoryItem independently. Legacy inventory
POST/PUT/DELETE in characters/routes.py and table loot transfer in play/routes.py
also mutate InventoryItem for SRD recipients; there is no SRD exclusion there.
Imports/duplicates create new Character IDs and do not write an existing inventory.

Related dependency: SRD progression/archive/companions, sharing and appearance
write copies of the same Character JSON that contains srdInventory. Protecting
only the new catalog route would leave stale JSON and quantity writers possible.
Character-dependent InventoryItem queries must happen after a common row lock
and fresh ORM load; refreshing after an action closure captured a row is too late.

Medium risks: lost quantities across inventory, DM handout and table loot writers;
lost JSON changes across inventory coins/starting-package state and progression or
management. Current role/table guards must remain unchanged. Lock ordering must
be explicit; no implicit global POST lock in the generic Character read helper.
Low: duplicate/import snapshots have their own new IDs, do not require locking a
nonexistent destination. No new product decision or dependency is needed.

Next Apply: extend the exact file boundary to explicit writer-mode access helpers,
legacy inventory and loot recipient locking. Keep authorization after fresh reload,
read routes pure, one-character transaction scope, post-commit pushes, existing
party/DM permissions and inventory semantics. Verify real PostgreSQL contention.
