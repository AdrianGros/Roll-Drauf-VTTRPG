# Discover: playable homebrew Species from Eagle Homebrew

Date: 2026-10-26. Phase: Discover. Worktree: `feat/eagle-homebrew` at `776778e`.
This records facts and the safe boundary for Apply; it does not select an implementation.

## Input and observed current state

The requested journey is to author a custom character race in Matt's Eagle Homebrew editor and use it as a fully playable character race in Roll Drauf VTT. Eagle Homebrew remains the live Creation Engine editor. The live SRD 5.2.1 character builder, sheet, level-up flow and playtable are the consumers to inspect. The earlier G1 Creation Engine is archived, not loaded by the app.

The live database has one authored 2024 Species pair (one personal world row and one library row). Its stored document has creature type, 30 ft movement and 60 ft darkvision, but no advancement entries. This is structural evidence only; no author content was copied into this report.

## Relevant inventory and dependencies

| Area | Current evidence | Consequence for the journey |
|---|---|---|
| Authoring | `frontend/eagle-homebrew-host/src/entry.ts`, `src/vtt-context.ts`, `vtt/creation_engine/routes.py`, `documents.py`, `models.py` | Eagle creates Foundry-shaped `Item` documents with subtype `race`; world and library copies are stored as mutable JSON documents. The server checks type, name, JSON shape/depth and size, but does not validate VTT gameplay semantics. |
| Foundry model | Eagle catalog names the item `Species` and stores subtype `race`; it supports Size, Trait, ItemGrant, ItemChoice, ScaleValue and AbilityScoreImprovement advancements in its editor. | These are Foundry advancement records, not native VTT character grants. The VTT has no Foundry Actor advancement runner. |
| Availability | `vtt/creation_engine/routes.py:68-105,231-239,292-307` | Only the author sees a personal library; only campaign owner/DM/Co-DM can open a campaign authoring world. Players cannot currently discover a GM's campaign Species through the creator. |
| Character creation | `vtt/characters/srd_creator.py:69-89,245-279`; `vtt/rules_content/creator_rules.py:26-28,200-222`; `vtt/static/js/srd-creator-steps.js:289-300` | The builder lists only Species from generated SRD JSON. Its evaluation and finalization never load Eagle documents. |
| Rules and source pins | `vtt/rules_content/creator_sources.py:1-73`; `vtt/rules_content/creator_drafts.py:148-187` | The source registry admits only the published SRD package. Finished characters store state and a derived snapshot, with no homebrew Species revision/source pin. |
| Sheet and play | `vtt/characters/sheet_link.py:24-31`; `vtt/characters/srd_progression.py:355-426`; `vtt/templates/character-sheet.html:1440-1500`; `vtt/characters/srd_party.py:104-127` | Rolls, level-ups, party view and tokens re-evaluate the static SRD data. A race name alone is insufficient to preserve or execute its grants. |
| Archived G1 | `archive/creation-engine-g1/README.md:35-46`; `archive/creation-engine-g1/vtt/creation_engine/compiler/homebrew.py`; `archive/creation-engine-g1/vtt/creation_engine/homebrew_runtime.py`; `vtt/ce_compat.py:1-23` | The manual race-to-sheet adapter only displayed prose. The executable race compiler/sandbox handled typed grants, choices, resources and spells only in private test scopes; the production sheet adapter was never built. The current compatibility seam always returns `None`. |

The live builder is for 2024 SRD 5.2.1. Eagle can author documents marked 2014 or 2024. The two editions therefore have different available character journeys today. No currently deployed code consumes an Eagle Species on an SRD character.

## User-journey gaps and inconveniences

1. After saving a Species, the editor presents it as a document, but offers no playability verdict or next step into character creation. A player cannot select it in the Species step.
2. The Eagle interface exposes Foundry-specific advancement concepts and UUID references. The VTT stores them, yet does not resolve them into character choices, sheet values, rolls or resources. A creator could believe a rule is active when it is only data in a document.
3. The pair of mutable world/library documents has no character-facing immutable revision. Editing or deleting either side could change or remove an origin unless a separate pin exists.
4. A campaign GM can author a Species, but the player-facing creator has no published campaign catalog or permission rule for selecting it. A private library must stay private until explicitly shared.
5. The SRD evaluator has special cases for its published Species, including human/elf and dwarf behavior; it has no generic path for arbitrary trait grants or race-owned limited-use abilities. The sheet roll API covers standard ability/save/skill/spell/weapon rolls, not an arbitrary Species action.
6. Older G1 could describe or privately simulate a race, but its data shape differs from Eagle's Foundry Item and it is archived. Re-enabling the old editor would introduce a second authoring source rather than completing the current journey.

## Risks and assumptions

- **High — misleading playability:** silently accepting unsupported advancements would produce a character whose numbers or actions differ from the authored race. A future acceptance gate needs explicit supported/unsupported results.
- **High — character stability:** mutable Eagle documents and static SRD re-evaluation can cause drift during sheet reads and level-up. Existing characters need stable race identity and rules content.
- **High — access boundary:** author-only library and GM-only campaign worlds cannot be exposed wholesale to players. Sharing has to respect author/campaign permissions and existing character readers.
- **Medium — edition compatibility:** the live creator implements 2024 SRD; 2014 authoring has no equivalent playable builder.
- **Medium — scope of automation:** typed modifiers, proficiencies, resistances, resources, spell grants and active trait actions span creator, sheet, play, level-up, export and token projection. The current G1 sandbox covers only a subset of D&D 5e rules and has no live-character adapter.
- **Medium — data conversion:** Eagle's Foundry advancement/Item reference model and G1's typed-grant model differ; conversion loss must be visible rather than inferred from prose.
- **Assumption to validate in Apply:** “fully playable” means authored rules that the VTT claims to support affect sheet values and play, while any unsupported rule is clearly labelled for manual adjudication and cannot be published as automated.

## Open questions for Apply

1. What exact capability set qualifies the first Species as playable: passive numbers, choices, proficiencies/resistances, resources, spells, active actions, and level-dependent grants?
2. Which Eagle advancement/reference forms can be translated without loss, and how should the creator display unsupported forms?
3. How will an author publish a Species to a personal or campaign character catalog, and what is the immutable revision a draft and character pin?
4. Which existing SRD and G1 calculations can be reused safely, and which need a new adapter for sheet, playtable, progression and export?
5. How are 2014 Species treated until a 2014 character builder exists?

## Verification and next step

Read-only production inspection found exactly two `race` rows forming one 2024 personal/library pair; no advancement entries. Baseline `pytest -q tests/test_creation_engine_eagle.py tests/test_srd_creator_api.py` passed **51 tests** (124 existing warnings) on this worktree. No application code or production data was changed.

Next phase: Apply. Define a versioned Eagle-Species-to-VTT contract, publication/access rules, a playability verdict for every authored mechanic, and an end-to-end acceptance journey covering authoring, player selection, finalization, sheet/rolls, level-up, persistence and export. Decide what is automated versus explicitly manual before Deploy.
