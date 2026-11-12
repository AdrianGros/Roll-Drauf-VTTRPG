# Apply C08 – common existing-character writer boundary

Approved C08 semantics remain: typed catalog additions for own nonarchived SRD
characters, 24h transactional UUID receipts, existing progression choices only.
The additional writer inventory is in DADM_DISCOVER_CODEX_C08_WRITERS_2026-11-12.

Use one small Character writer helper with SELECT FOR UPDATE + populate_existing.
An explicit writer parameter on existing Character access helpers selects it;
GET/read/preview routes keep reads. Acquire before dependent InventoryItem queries
or action closures; then recheck current ownership/campaign/system/deletion using
fresh Character state. Integrate owner SRD inventory, DM handout/take-back,
legacy inventory CRUD and loot recipient paths. Related SRD JSON writers use the
same explicit boundary (progression/management, sharing and appearance) so they
cannot overwrite inventory state from a stale Character object. Imports and
copies create new destination IDs; do not alter their rules or add a global lock.
Existing batch XP awards keep their transaction and lock affected Character IDs
in ascending order. The CE race handoff already locks Character in its own fresh
Session and needs no new mechanism.
No new owner/DM/player permissions and no table guard bypass. Lock Character
before inventory/loot mutation; release at commit before existing token pushes.

New catalog route commits receipt, item changes and immutable confirmation in
one transaction. Replay checks current owner/nonarchived SRD authority first.
The response contains that saved confirmation and a separate per-request table
refresh status (sent, pending, or replay); a push failure never repeats inventory.
Targets search/filter/pagination are owner scoped; only existing typed catalog
IDs offer add. Spells/feats/classes link to the existing progression section with
real progression.status, never direct generic Spell or unchecked bonuses.

Acceptance: current and legacy rights unchanged, concurrent old/new catalog
writers and table/handout quantity writers preserve committed state, JSON fields
remain together, failed transaction leaves neither item delta nor receipt, replay
and changed payload behave correctly, normal compendium -> own figure -> actual
inventory/progression journey at 390/1440 DE/EN paper/night. One additive receipt
table after backup; old image ignores it. Focused regressions include existing
inventory/party/progression and role-separation boundaries. No unresolved Medium
is deferred to deployment; this is the explicit handoff for those bounded edits.

Primary documentation checked 12 November 2026: PostgreSQL 16
[explicit row locking](https://www.postgresql.org/docs/16/explicit-locking.html)
explains transaction-held row locks and the need for consistent ordering;
SQLAlchemy 2.0 [populate_existing](https://docs.sqlalchemy.org/en/20/orm/queryguide/api.html#populate-existing)
explains that existing ORM identity-map rows must be refreshed. The exact writer
scope and response projection here are repository design decisions.

The inventory confirmation links to the existing inventory tab through the fixed
section key inventory; the closed section-ID map gains only srdInventory.

Browser acceptance exposed a pre-existing Compendium startup/search race: a late
initial category/facet read or queued search could close a deliberately opened
entry. Bound the new action surface to the current entry, cancel queued list
reads on entry selection and ignore stale category responses; keep results
unclickable while a category is being replaced. Verify both normal role journeys
and a committed action whose delayed response arrives after switching dialogs.
