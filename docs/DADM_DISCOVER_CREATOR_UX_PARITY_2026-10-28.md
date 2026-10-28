# DAD-M Discover: character creator journey and functional parity

**Status:** Discover complete, 2026-10-28. No implementation in this pass.

## Input summary

Assess whether the current character creator is a usable, minimal, segmented starting point for a D&D Beyond-like creation journey. The comparison is about behavior and usability, with Roll Drauf's own presentation and SRD/homebrew content.

## Current state and evidence

- The live `/srd-creator` scripts and stylesheet have the same SHA-256 hashes as this worktree; production adds the shared navigation overlay to the template. The audited route is the live implementation.
- The guided builder has eight steps: class, origin, abilities, choices, equipment, spells, description, review. It has server-validated drafts, autosave, resume, a live derived-stat summary, rule-text dialogs, point buy/standard array/rolling/manual abilities, 1–20 progression and multiclassing, campaign assignment and finalization. Browser tests finalized a valid Fighter and exercised quick mode at 390px (**2 passed**). Earlier Duckfolk and sheet-to-table browser journeys exercise the published-species handoff.
- The bundled catalog has 12 classes, 12 subclasses, 9 species, 4 backgrounds, 17 feats and 339 spells. Published homebrew Species can be selected; the source registry contains only the SRD package. Other Creation Engine content types are not selectable in this builder.
- On a 390×844 phone, the class section panel begins around y=744 after global navigation, title, toolbar, summary and step pills; the actual class choices are below the first viewport. The quick-mode full-page capture is 14,765px tall. See [first viewport](proofs/creator-ux-audit-2026-10-28/mobile-first-viewport.png). There is no horizontal document overflow in the existing browser test.
- Guided step changes call `window.scrollTo(0, 0)` in `srd-creator.js`, returning a phone user to the top of the chrome before each new section. The mobile summary is explicitly ordered ahead of the step navigation in `srd-creator.css`.
- The builder displays the live summary and error/open counts before the player starts. Review findings are text rows; step badges navigate to sections, but findings do not link to the particular control. The final action is blocked until server validation succeeds.

## Benchmark

D&D Beyond's [official first-character guide](https://www.dndbeyond.com/posts/1059-how-to-create-your-first-dungeons-dragons) describes four starts: Premade, Standard, Quick Build and Randomize. Its Quick Build asks for species, class and name, then fills other choices. Standard includes character preferences and sources, followed by class, background, species, abilities and equipment. The [October 2026 changelog](https://www.dndbeyond.com/changelog/) still refers to Quickbuilder as an active product surface. This comparison is based on public official documentation, not a signed-in D&D Beyond session.

## Relevant inventory

| Journey area | Current result | Finding |
|---|---|---|
| Guided build | End-to-end working for supported SRD choices | Strong functional foundation; eight steps and dense panels need usability review |
| Quick build | All eight sections rendered on one page | **High UX gap:** not an actual three-choice, automatically completed quick build |
| Premade | No premade selection journey | **Medium functional gap** |
| Random | Valid random character generation; home entry starts level 1 | **Medium functional gap:** no pre-generation constraints for class, species or level |
| Preferences and sources | SRD is fixed; published homebrew Species are appended | **Medium functional gap:** no player-facing source controls or help-text preference |
| Origin/feature choices | Species and background selectors exist | **Medium rules gap:** origin-feat subchoices and species-granted spells are explicitly unfinished in `srd-creator-steps.js` |
| Discovery at scale | All species/background cards render without search/filter | **Low now, medium as content grows:** hard to browse a global compendium |
| Mobile first action | Class panel begins around y=744; choices are lower; each guided step returns to page top | **Medium UX gap:** the initial screen is mostly chrome and status, repeatedly |
| Validation recovery | Counts and findings, with step navigation | **Medium UX gap:** no direct jump from a finding to its control; errors are front-loaded |
| Builder to play | Finalized sheet, inventory, campaign link and VTT roll handoff exist | Usable core; spell-slot/rest/resource automation and some feature mechanics remain separate follow-up work |

## Dependencies, risks and assumptions

- **High, product expectation:** calling the all-fields view “Schnellbau” implies D&D Beyond-like Quick Build, but it does not auto-complete a character from a few choices.
- **Medium, rules completeness:** origin-feat subchoices and species spells are visible TODOs. A character can be finalized without these selections represented as active mechanics.
- **Medium, cohesion:** the Creation Engine and character builder connect through published Species, not through all content types. The global compendium is therefore not yet a general creator source.
- **Medium, mobile usability:** large pre-content chrome and a very long all-fields mode increase effort on a phone, though horizontal overflow is controlled.
- **Low, benchmark limit:** public D&D Beyond documentation may omit newer signed-in details. The 2026 changelog confirms Quickbuilder remains active; this audit does not claim pixel or exhaustive feature equivalence.

## Open questions and next step

The next Apply phase should define acceptance journeys for (1) a genuinely fast, minimal build, (2) a guided novice build, and (3) an expert edit path, then scope the smallest coherent implementation. It should decide how source preferences and missing origin choices fit into those journeys while preserving server validation and existing drafts. No user decision is needed to confirm that the current experience falls short of full parity.
