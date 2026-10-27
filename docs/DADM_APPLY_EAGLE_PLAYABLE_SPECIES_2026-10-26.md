# Apply: Eagle Species as playable VTT character origins

Date: 2026-10-26. Phase: Apply. Input: [Discover](DADM_DISCOVER_EAGLE_PLAYABLE_SPECIES_2026-10-26.md). This is a design and Deploy handoff, not an implementation claim.

## Design summary and solution boundary

Keep Matt's Eagle Homebrew editor and its Foundry-shaped documents unmodified. Add a VTT-owned playable-Species adapter beside that editor. The adapter gives an authored Species an explicit playability report, snapshots a validated revision, publishes it to the permitted character catalog, and supplies a VTT-native rule profile to the 2024 SRD creator, character sheet, level-up flow and playtable. The archived G1 typed-grant rules, choice validation and private sandbox are reference implementations to extract from; its editor, workspace/kernel and database tables do not return to production.

First delivery targets **2024** characters because the live creator is SRD 5.2.1. Eagle 2014 Species remain editable, but cannot be marked playable until a 2014 character journey exists. Existing SRD characters, existing Eagle documents and the one live Species pair are untouched by default.

“Playable” means that a published profile's mechanical grants and choices which the VTT presents as active are actually applied on the server and survive save/reload/level-up. Narrative traits remain visible for GM adjudication. Unknown Foundry advancements, dangling item references or mechanics beyond the VTT capability set produce specific blocking diagnostics; no silent partial publication as a playable race.

## Contracts and workflow

1. **Author and inspect.** Eagle continues writing the world/library pair. A VTT companion action beside a Species opens “Spielbarkeit prüfen”. The server reads the world document and referenced world/library Items under the author's current rights. It reports, per field/advancement/reference, whether it converts to a VTT rule, is narrative-only, or blocks publication. The report links back to the editable Species and exact unsupported field. It never infers mechanics from prose.
2. **VTT rule profile.** The adapter emits a versioned, strict profile with race name, edition, creature type, size choices, movement and senses; feature IDs and descriptions; fixed and chosen grants; any level conditions; provenance for each grant; and explicit active actions/resources. Reuse the old G1 grant vocabulary where it fits (modifiers, proficiencies, resistances, resources, spells, choices), but map it into the current SRD evaluator rather than requiring a G1 class or sandbox actor. Preserve the original Eagle document as provenance, not as an executable schema.
3. **Authoring gaps.** Eagle's Species has no Activities/Effects editor. The companion action needs a bounded VTT rule section for race mechanics Eagle cannot express directly, such as a limited-use action. It is attached to the Species revision and uses typed fields and validation. It must never modify the pinned vendor code or hide unsupported Foundry fields.
4. **Immutable publication.** A successful publish stores the source UUID, source document revision/digest, versioned VTT profile, conversion report, author, rules version and publication scope in an immutable revision. Republishing after an Eagle edit creates a new revision. Deleting/editing the Eagle pair does not alter characters already using the old revision. Reject publish if the source changes between inspection and commit.
5. **Visibility.** A personal publication is selectable only by its author. A campaign publication is selectable by members of that campaign after a campaign owner/DM/Co-DM publishes it. Library drafts and unreviewed world documents are never listed to players. Server-side authorization applies to catalog, preview, draft selection and finalization; a client-provided revision ID cannot bypass it.
6. **Character creation.** The Species step lists the authorized published revisions alongside the SRD Species and labels their author/source. Selecting one stores its immutable revision ID and required choices in the draft state. The server validates all choices and computes fixed/choice grants; finalization records the revision ID, digest and effective profile snapshot with the character's SRD block. Other SRD class/background steps stay intact.
7. **Character lifecycle.** All re-evaluation entry points—sheet, rolls, progression, inventory/encumbrance, party/token projection, duplicate/rebuild, PDF and portable export/import—must resolve the character's pinned profile through one shared function. Existing SRD-only characters keep the current calculation path. A newer published revision is opt-in through an explicit character migration preview that shows stat/resource deltas.
8. **Play state.** A race action has server-defined activation, roll/effect and resource cost. Use an atomic command with an idempotency key, expected character state/version and event receipt so retrying cannot spend or roll twice. Rest recovery follows the resource's authored rule. Trait bonuses and resistance are applied in the same server calculations used by sheet rolls and combat, with a source label. Narrative traits are readable on the sheet without claiming automation.

The exact Eagle advancement mapping is a Deploy prerequisite: capture fixtures from the pinned Eagle/dnd5e 5.3.3 editor for Size, Trait, AbilityScoreImprovement, ItemGrant, ItemChoice and ScaleValue, plus linked feat/spell documents. Specify a mapping test for each supported form and a blocking diagnostic fixture for every unimplemented form before enabling publication. This avoids guessing Foundry's JSON semantics.

## Acceptance criteria

- An author creates a 2024 Species in Eagle, checks playability, fixes diagnostics, and publishes a revision; an authorized player can find it in the SRD creator and an unauthorized player cannot.
- The player resolves every required race choice, completes a character, reloads it, and sees the chosen race's size, creature type, movement, senses, features and source revision on the sheet.
- A fixture Species demonstrates a fixed skill proficiency, one player choice, a resistance, a bounded resource and an active action. The server computes relevant sheet/roll/combat outcomes once; spending and resting persist, and a repeated action request returns the same receipt.
- Level-up and level-down recompute from the pinned race revision without duplicate grants or restoring spent resources incorrectly. Editing or deleting the Eagle source does not change the existing character.
- A GM sees the race and its effects on the party/token view. Export/import, PDF, duplicate and rebuild either preserve the pinned profile and mechanics or clearly reject unsupported transfer with no partial write.
- SRD characters and Eagle documents without a published profile behave as before. A 2014 Species cannot be published as playable through the 2024 creator.
- End-to-end Chromium testing covers author → publish → player create → sheet → play action → rest → level-up → reload; targeted server tests cover ownership, edition, stale source, invalid choice/reference, rollback and retry.

## Risks and tradeoffs

- The supported rules subset must be explicit. Arbitrary Foundry effects, formulas and modules do not become runnable just because the JSON is stored; blocking diagnostics make the boundary visible.
- A second VTT-owned mechanics panel increases authoring work, but it is needed for actions/effects absent from Eagle's Species editor. Keep it focused on that gap and show source-linked previews.
- Immutable profile snapshots duplicate some source data. This prevents character drift and permits exact export/replay; size and retention limits should be enforced.
- Campaign publication changes who can read authored content. Require an explicit publish action and test both author-only and campaign-member access.
- Mechanical rules touch combat and persistence. Deploy behind a separate feature flag, test on a disposable database and browser account, then enable only after the full acceptance journey passes. Do not auto-convert the existing production pair or old G1 drafts.

## Deploy handoff

Implement in the clean Eagle worktree in bounded order: fixtures/converter and diagnostics; immutable revisions and access; creator selection/finalization; shared evaluation and lifecycle consumers; race actions/resources; browser journey. Each slice must keep the publication gate closed until all acceptance criteria for its offered capabilities pass. Add an additive migration and a rollback that disables the new flag without deleting pinned character data. The baseline before implementation is 51 passing Eagle/SRD creator API tests.
