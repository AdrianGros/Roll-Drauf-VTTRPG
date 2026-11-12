## C02 exact diff review: findings

I found nothing at Medium severity or above. I only read the diff, the Apply contract and the source ranges named below. I ran nothing, and every pass count in the brief is the coordinator's claim, not something I checked.

### Verified by reading
- **Backend (`vtt/characters/routes.py`):** `_sheet_permissions` and `_attach_sheet_permissions` are owner-only and read-only. They are attached only in GET `/sheet`, never stored, and don't touch the PUT/POST/DELETE checks (`char.user_id != user.id` at lines 384, 557, 615 and others). A DM, campaign owner or shared reader who isn't the owner gets false. I found no authorization change.
- **Fail closed (`character-sheet.html`, `resolveSheetPermissions`):** a missing or invalid `permissions` object gives `editCore` and `editIdentity` false. The mode button and `#sfManageImages` stay hidden. `mode=edit` is not used as proof of ownership.
- **Lock and view for the SRD panels:**
  - `SheetLock.locked` is `explicitView || editLocked` and only removes actions.
  - Manage uses `canEdit() = state.canEdit && !SheetLock.locked`, which gates Duplicate, Archive, Campaign/Share, JSON export, companion fields and the add and remove buttons.
  - Progression hides level-up, level-down and manage when locked, and guards `startWizard`, `save`, `confirmLevelDown` and `confirmLevelUp`.
  - Inventory reads the global `editable`, which `applySheetPermissions` sets, and `renderSrdInventory` redraws it.
- **DM XP:** a non-owner DM at the normal entry has `SheetLock.locked == false`, so the server's `canManage` still applies. No client authority was added.
- **Stale composer:** `loadSheet` checks `seq` before applying permissions. The section opener checks `token === srdRenderToken` and `sectionOpened`. The identity handlers re-check `canEditIdentity` at pick time and at remove time.
- **Wrong query URL:** `sheetUrlWith` builds from `entryParams`, captured at script start, so `campaign_id`, `session_id` and unknown parameters survive. A bound table session overrides the entry value and an unbound one removes it. The path is fixed, so there is no open redirect. `section` is a fixed-key map lookup and never a selector.
- **Computed fields and copy:**
  - Computed SRD fields stay disabled, per the `editable` and `disabled` handling in the template, which I only partly read.
  - I didn't re-read the duplicate backend. The UI copy is the existing Manage Duplicate gated by server `canEdit`, with a confirm step.
- **Findings and selectors (`SC.correctFinding`, `focusPath`):** the path is only compared to `data-focus-path` strings, or turned into an id for `levels.*` from state-derived indices. Unknown paths still go to the step. The message text and rule quote remain visible.
- **Feat selection:** `takenFeatIds` uses the same sources as the server's `taken_feats` (origin feat, versatile feat, other advancements) and mirrors the server's saved-order rule through `earlierOnly`. The `select` helper does support a disabled third tuple element. The saved selection is kept and explained, nothing is silently dropped, and the server `feat-repeat` rule is untouched.
- **Rollback:** the change is additive and there is no new schema or dependency.

### Findings

| # | Severity | File / symbol | Trigger | Impact and smallest fix |
|---|---|---|---|---|
| 1 | Low | `srd-progression-ui.js` `render()` | Locking while a level-up wizard is open sets `current.wizard = null` and `confirmDown = false`. | Open wizard state is lost without a confirm, and unlocking doesn't restore it. It is UI-only and no data is written. Optionally keep the wizard but disable its confirm, or document the behavior. Not blocking. |
| 2 | Low | `srd-manage-ui.js` `act` and `saveCompanions` | They have no `locked()` guard, unlike progression. | No UI path reaches them while locked, because the buttons are not rendered. The server stays authoritative. Optional guard for symmetry. |
| 3 | Low | `srd-creator-steps.js` `takenFeatIds` | It counts every advancement entry with a `featId`, including ones the server skips (invalid slot or unknown feat). | The picker could disable a feat the server would accept. It errs on the safe side and the server stays the authority. Not blocking. |
| 4 | Low / Info | `character-sheet.html` `SheetLock = {locked: explicitView}` | A non-owner DM who opens a sheet with an explicit `mode=view` loses the XP actions. | This follows the contract (explicit view is read-only). I found no in-repo link that does this: `srd_party.py`, `campaigns.html` and `play-ui.js` send no `mode`. Record it as a deliberate behavior. |
| 5 | Info | Default entry | Table and list links without a `mode` now open an owner's sheet editable. | This is contract intent and the lock button exists. Live acceptance should confirm it is acceptable for Player table links. |
| 6 | Info | Frontend and backend rollback | New UI against an old backend, which has no `permissions`, makes the sheet read-only even for the owner. | It fails safe, but the two must ship and roll back together. Rolling back only the backend would hide editing. |
| 7 | Info | `goStep` via the fix button | `SC.correctFinding` calls `goStep`, which sets `dirty` and schedules a draft autosave. | It saves unchanged state, not a character mutation. It is existing behavior and not blocking. |

### Verification gaps
- **Wire-up retest pending:** the final native lock wiring needs the focused reruns. The earlier run had 22 passed and 1 failed (`localLock` not wired), and I did not rerun it.
- **Coverage gap in the diff's tests:** the lock and view test covers only the Manage panel (`#srdManageDuplicate`, Add companion). I saw no browser assertion that Progression and Inventory are locked or redrawn, nor one that the normal entry preserves DM-XP `canManage` for a non-owner DM.
- **Visual and viewport coverage:** I did not verify DE/EN and narrow-width layout, the picker with a real image, or the valid PNG decode. These rest on the coordinator's reports.
- **Not checked:** the full test suite, the generated 2818-entry catalog (coordinator-owned), the production source/live match, and the live journey with test characters.

**Verdict: ready_for_integration.** That is conditional on the focused browser rerun of the final `localLock` wiring passing and on the live checks above. This is neither deployment approval nor live delivery.
