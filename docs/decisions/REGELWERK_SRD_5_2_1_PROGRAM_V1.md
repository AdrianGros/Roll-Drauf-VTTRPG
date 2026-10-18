# DAD-M Program: German SRD 5.2.1 Regelwerk

version: 1
status: approved — R0-R6 corpus complete and reviewed; R7 preview live on the test environment, acceptance pending
date: 2026-10-16
phase: R3 Monitor complete (corpus run R3-R6)
basis: `docs/DADM_APPLY_REGELWERK_SRD_5_2_1_2026-10-15.md`

## Program goal

Write, verify, publish, and display the complete German SRD 5.2.1 as Roll Drauf VTT's main
human-readable ruleset, with `/regelwerk` as the canonical in-product rules destination.

## Fixed constraints

- The licensed source is the digest-pinned official German SRD 5.2.1 PDF.
- Only CC BY 4.0 SRD content and clearly separated original Roll Drauf content may enter the
  corpus.
- SRD 5.1/2014 content is not part of this package.
- Published package versions are immutable.
- `/regelwerk` is the canonical published surface; other VTT surfaces link to stable rule IDs.
- Incomplete content is labelled preview and cannot become the main published ruleset.
- Rules-reference delivery does not silently activate executable character mechanics.
- Every milestone runs Discover → Apply → Deploy → Monitor before the next milestone begins.
- Cross-milestone scope changes require a new plan version and human approval.

## Priority and dependency order

```text
R0 Source and rights lock
  -> R1 Reader vertical slice
    -> R2 Core play and character creation
      -> R3 Classes, origins, and feats
        -> R4 Equipment and spells
          -> R5 Glossary, toolbox, and magic items
            -> R6 Monsters and animals
              -> R7 Canonical activation and VTT references
```

All milestones are P1 for the full-project goal. R0 and R1 are the first authorization boundary.

## R0 — Source, rights, and corpus foundation

- **Goal:** Establish the immutable source identity, licensing artifacts, semantic schemas, and
  validation boundary required before SRD content is transcribed.
- **Scope:** source manifest, SHA-256 verification, exact attribution artifact, license page
  contract, package/document schemas, safe block vocabulary, rule-ID rules, validation commands,
  coverage model, initial fixtures.
- **Constraints:** no public main-ruleset activation; no non-SRD source; no arbitrary content HTML;
  no new runtime parsing dependency.
- **Deliverables:** package skeleton; versioned schemas; attribution/source ledger; validator;
  coverage-report fixture; negative security fixtures; Deploy and Monitor evidence.
- **Acceptance criteria:** source URL and SHA match the approved plan; attribution matches the
  official German PDF; valid fixtures pass; malformed, cross-edition, arbitrary-markup, missing
  provenance, and unstable-ID fixtures fail; published-state immutability is tested.
- **Risks and assumptions:** low residual licensing transcription risk; human source reviewer must
  be named before publication.
- **Dependencies:** none.
- **Priority:** P1.

## R1 — Regelwerk reader vertical slice

- **Goal:** Prove the canonical path from one reviewed SRD section to a public, searchable,
  accessible Regelwerk page.
- **Scope:** `/regelwerk`; versioned document route; public manifest/document/search interfaces;
  one representative core-rules chapter; Book Scene Regelwerk tab; table of contents; search;
  deep links; license route; print view; preview status.
- **Constraints:** the content stays preview; generated assets are derived; no character mechanics
  are changed.
- **Deliverables:** one end-to-end content slice; reader shell; shared navigation entry; generated
  navigation/search/coverage artifacts; route, browser, accessibility, and source-fidelity proofs.
- **Acceptance criteria:** anonymous and authenticated reads work; the tab is visible on the main
  navigation surfaces; a stable rule link survives reload; search resolves the fixture rule;
  unsafe content is escaped; narrow-screen, keyboard, reduced-motion, and print checks pass;
  attribution is visible.
- **Risks and assumptions:** low residual Book Scene integration risk after route-contract tests.
- **Dependencies:** R0 complete.
- **Priority:** P1.

## R2 — Core play and character creation corpus

- **Goal:** Publish reviewed German SRD sections for the basic game loop and character creation.
- **Scope:** `Die Spielregeln` and `Charaktererstellung`, including combat, damage/healing,
  exploration, advancement, higher-level starts, multiclassing, and trinkets.
- **Constraints:** retain official structure and terminology; substantive adaptations require an
  explicit change record; rules remain preview.
- **Deliverables:** reviewed documents and rule IDs; cross-references; source-page checklist;
  updated search/navigation/coverage; representative sheet/help deep links.
- **Acceptance criteria:** every official subsection in the selected ranges is present; all numeric
  rules and exception callouts receive full comparison; no broken internal references; sampled
  searches and direct links pass.
- **Risks and assumptions:** medium raw fidelity risk reduced to low by numeric/exception full
  review and human sign-off.
- **Dependencies:** R1 complete.
- **Priority:** P1.

## R3 — Classes, character origins, and feats corpus

- **Goal:** Publish all SRD 5.2.1 German character-building options included in the official
  package.
- **Scope:** all twelve included classes; their included subclasses; class tables and spell lists;
  backgrounds; species; feats.
- **Constraints:** no omitted non-SRD classes, subclasses, species, or feats are reconstructed in
  this milestone; original Roll Drauf options remain separate.
- **Deliverables:** class/origin/feat documents; structured progression and option tables;
  cross-references; source-page reviews; representative character-sheet links.
- **Acceptance criteria:** all included classes and their one SRD subclass are accounted for; every
  progression table, resource formula, choice level, and spell-list reference is fully reviewed;
  all included backgrounds, species, and feats appear exactly once; search and navigation tests
  cover every category.
- **Risks and assumptions:** high raw transcription impact for progression tables is mitigated by
  full table comparison and independent review before milestone closure.
- **Dependencies:** R2 complete.
- **Priority:** P1.

## R4 — Equipment, spellcasting, and spells corpus

- **Goal:** Publish the complete licensed equipment and spell reference needed for player-facing
  use.
- **Scope:** coins, weapons, mastery properties, armor, tools, adventuring gear, mounts, vehicles,
  expenses, crafting, spellcasting rules, spell lists, and every included spell description.
- **Constraints:** only SRD-included items and spells; no content sourced from D&D Beyond listings
  or purchased books.
- **Deliverables:** equipment and spell documents; stable entity/rule IDs; tables and indexes;
  source-page reviews; representative character-sheet spell/equipment links.
- **Acceptance criteria:** all official entries are covered exactly once; costs, weights, damage,
  ranges, durations, levels, components, saving throws, and scaling receive structured or manual
  full checks as applicable; search resolves German names and approved aliases; internal spell and
  condition links resolve.
- **Risks and assumptions:** high raw volume and numeric-risk surface are mitigated by generated
  inventory counts, full field review, and category-level sign-off.
- **Dependencies:** R3 complete.
- **Priority:** P1.

## R5 — Glossary, gameplay toolbox, and magic items corpus

- **Goal:** Publish the complete rules glossary, game-master toolbox material, and licensed magic
  items.
- **Scope:** glossary terms; travel pace; background creation; curses and magical contagions;
  environments; fear/stress; poisons; traps; combat encounters; magic-item rules and entries.
- **Constraints:** official SRD scope only; original GM guidance is separately labelled.
- **Deliverables:** glossary resolver; toolbox chapters; magic-item catalog; cross-references;
  source-page review; representative VTT condition/action links.
- **Acceptance criteria:** every glossary term has one canonical rule ID; all cross-references
  resolve; trap, poison, encounter, and item numbers are fully checked; direct links from
  representative VTT actions reach the correct rule.
- **Risks and assumptions:** medium risk of circular/ambiguous glossary links is mitigated by graph
  validation and explicit alias rules.
- **Dependencies:** R4 complete.
- **Priority:** P1.

## R6 — Monsters and animals corpus

- **Goal:** Publish every monster and animal stat block included in the German SRD 5.2.1.
- **Scope:** monster rules, alphabetical monsters, animal stat blocks, indexes, traits, actions,
  reactions, legendary material where included, and references to glossary terms.
- **Constraints:** no omitted branded creature is added; official SRD-safe names are retained.
- **Deliverables:** monster/animal documents and stat blocks; complete source inventory; index and
  search coverage; source-page reviews.
- **Acceptance criteria:** inventory counts match the official source ranges; every stat block is
  present exactly once; armor class, hit points, speed, abilities, saves, skills, senses,
  challenge data, attacks, damage, save DCs, and recharge text receive full comparison; rendering
  remains usable on narrow screens and in print.
- **Risks and assumptions:** high raw numeric-risk surface is mitigated by structured stat blocks,
  inventory reconciliation, and independent source review.
- **Dependencies:** R5 complete.
- **Priority:** P1.

## R7 — Canonical activation and VTT reference adoption

- **Goal:** Make the complete reviewed package the VTT's main ruleset and establish Regelwerk as
  the canonical target for in-product rule references.
- **Scope:** final coverage/legal/fidelity audit; main-package activation; preview removal; stable
  anonymous URLs; representative rule references from character sheet, Creation Engine, and play;
  rollback rehearsal; user walkthrough.
- **Constraints:** no comprehensive automation cutover; no activation while any corpus partition
  is incomplete or unapproved.
- **Deliverables:** published immutable package; activation decision record; final coverage and
  acceptance report; navigation rollout; representative VTT references; rollback proof; Monitor
  report.
- **Acceptance criteria:** all global criteria in the Apply design pass; named human acceptance
  owner signs the release; anonymous and authenticated walkthroughs succeed; every top-level
  corpus section is searchable; representative character and play references resolve correctly;
  the previous package can be restored without data loss or URL mutation.
- **Risks and assumptions:** low residual rollout risk after feature-flag and rollback rehearsal;
  publication still receives the planned legal/fidelity sign-off.
- **Dependencies:** R6 complete.
- **Priority:** P1.

## Program-wide decision log

| Date | Decision | Reason | Decided by | References |
| --- | --- | --- | --- | --- |
| 2026-10-15 | Use German SRD 5.2.1 as the main Roll Drauf ruleset | It is the current, broad, officially localized CC BY corpus | human product direction | Apply design §1–3 |
| 2026-10-15 | Make `/regelwerk` the canonical published rules destination | Prevent divergent prose across sheets, help text, and tools | human product direction | Apply design §2, §6 |
| 2026-10-15 | Keep 2014 rules in a future separate package | Existing Creation Engine contract prohibits silent edition mixing | Apply design | Apply design §2–3 |
| 2026-10-15 | Use semantic JSON with renderer-owned markup | Stable IDs, safe rendering, deterministic search, no new runtime parser | Apply design | Apply design §3, §5 |
| 2026-10-15 | Approve program version 1 and authorize R0 Deploy | The human owner explicitly approved the plan and said to proceed | human product owner | `docs/decisions/APPROVAL_REGELWERK_SRD_5_2_1_V1_2026-10-15.md` |
| 2026-10-15 | Close R0 and permit R1 Discover | R0 source, rights, schema, digest, coverage, and regression evidence passed Monitor | DAD-M Monitor under approved program | `docs/DADM_MONITOR_REGELWERK_SRD_5_2_1_R0_2026-10-15.md` |
| 2026-10-16 | Name Donutarian as VTT integration lead and source-fidelity reviewer for R1 | R1 Deploy required both roles named before closure; human product owner self-assigned both | human product owner (Donutarian) | `docs/DADM_DEPLOY_REGELWERK_SRD_5_2_1_R1_2026-10-16.md` |
| 2026-10-16 | Close R1 and permit R2 Discover | Reviewer sign-off received on pages 6-8; coverage ledger, regenerated artifacts, and full route/regression suite passed Monitor | DAD-M Monitor under approved program | `docs/DADM_MONITOR_REGELWERK_SRD_5_2_1_R1_2026-10-16.md` |
| 2026-10-16 | Name Donutarian as R2 content lead; authorize transcription to begin | R2 Deploy required the role named; human product owner self-assigned and said go ahead | human product owner (Donutarian) | `docs/DADM_APPLY_REGELWERK_SRD_5_2_1_R2_2026-10-16.md` |
| 2026-10-16 | Close R2 and permit R3 Discover | Reviewer sign-off received on pages 5, 9-32; coverage ledger, regenerated artifacts, and full route/regression suite passed Monitor | DAD-M Monitor under approved program | `docs/DADM_MONITOR_REGELWERK_SRD_5_2_1_R2_2026-10-16.md` |
| 2026-10-18 | Run the R3-R6 corpus as one cadence-based transcription with per-range reviewer sign-off | Human owner directed continuous progress with a DM review after each range and status DM per cycle | human product owner (Donutarian) | `docs/DADM_DEPLOY_REGELWERK_SRD_5_2_1_R3_2026-10-18.md` |
| 2026-10-18 | Close the R3-R6 corpus run and permit R7 Discover | Reviewer "Lgtm" on pages 5-412; 101 documents; coverage complete; build check and 39 tests green; package still `preview` | DAD-M Monitor under approved program | `docs/DADM_MONITOR_REGELWERK_SRD_5_2_1_R3_2026-10-18.md` |
| 2026-10-18 | Activate the Regelwerk reader as `preview` on the live VTT (= test environment, no separate production) | Human owner asked for a readable "Regelwerk" tab to be able to accept; image `regelwerk-7bfe069`, `REGELWERK_PREVIEW=true`; rollback via compose backup + old image; `published` still requires named acceptance owner |

This log is append-only after plan approval.

## Roles and approval gates

- Product owner / final acceptance owner: to be named in the approval record.
- Content lead: **Donutarian**, named 2026-10-16.
- Source-fidelity reviewer(s): **Donutarian**, named 2026-10-16. Independent from the transcriber
  (the transcription was produced by an AI agent under this program, not by the reviewer).
  Reviewer sign-off on the R1 slice (pages 6-8) is tracked in
  `docs/DADM_MONITOR_REGELWERK_SRD_5_2_1_R1_2026-10-16.md` once given.
- VTT integration lead: **Donutarian**, named 2026-10-16.
- Legal/licensing sign-off: product owner, with counsel review optional but recommended before R7
  public activation.

R0 Deploy needs plan approval. R1 and every later milestone need the preceding Monitor result.
`published` status additionally needs the named acceptance owner and source-fidelity sign-off.

## Program acceptance

Program acceptance is the complete checklist in
`docs/DADM_APPLY_REGELWERK_SRD_5_2_1_2026-10-15.md` §13. A milestone cannot waive a global item;
it may only provide evidence toward it.

## Rollback boundary

- Before R7, disabling `REGELWERK_PREVIEW` removes the reader entry without changing characters,
  campaigns, sessions, or active mechanics.
- Published packages are retained and can be reactivated by package identity.
- Content corrections create new versions; rollback never edits historical package bytes.
- Representative VTT rule references degrade to an explicit unavailable state if the referenced
  package is disabled; they never resolve against a different edition.

## Artifacts and retention

- This milestone program: retention class `versioned`; approval freezes version 1.
- Per-milestone Discover, Apply, Deploy, and Monitor records: `immutable` after phase closure.
- Approval and activation decisions: `immutable`, append-only.
- Working transcriptions before publication: `mutable` within the active milestone.
- Published content packages: `immutable`.

## Next step

Human approval of program version 1. Record that approval, then begin only R0 Deploy. Do not begin
R1 or bulk SRD transcription until R0 Monitor has closed its acceptance criteria.
