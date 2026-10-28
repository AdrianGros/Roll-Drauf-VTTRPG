# DAD-M program: Roll Drauf character creation and play parity

version: 1
status: draft
date: 2026-10-28
basis: [current Discover audit](../DADM_DISCOVER_CHARACTER_CREATOR_PROGRAM_2026-10-28.md), [phone UX audit](../DADM_DISCOVER_CREATOR_UX_PARITY_2026-10-28.md), [original 48-point scope](../DADM_DISCOVER_CHARACTER_CREATOR_2026-10-18.md)

## Goal and acceptance boundary

Deliver an original Roll Drauf character-creation system with the documented **functional** creation paths of D&D Beyond—guided, genuinely quick, premade and constrained random—plus a rule-valid, immediately playable sheet connected to the VTT, Play Hub and DM Hub. The content boundary remains German SRD 5.2.1 and authorized Roll Drauf/user publications. Functional parity does not mean copying another product's visuals, code, text, proprietary content or account model.

The earlier P1–P12 work is the baseline, not work to repeat. The old 48-point matrix is a scope ledger, not evidence that every point was accepted. This program closes its remaining gaps and requires an independent acceptance record for every point. The [official D&D Beyond creation guide](https://www.dndbeyond.com/posts/1059-how-to-create-your-first-dungeons-dragons), [October 2026 changelog](https://www.dndbeyond.com/changelog/) and [2026 roadmap](https://www.dndbeyond.com/posts/2132-d-d-beyonds-2026-development-roadmap) define the dated public behavioral benchmark; roadmap promises are excluded until shipped and audited. A future benchmark change requires a new plan version, not silent scope growth.

## Design decisions and solution boundary

1. **One creator state and one evaluator.** Guided, quick, premade and random starts all produce the existing versioned draft state; the server's rules evaluator remains authoritative for preview and finalization. A UI may suggest or prefill values but cannot bypass blocker validation. Generated defaults must be explainable, editable, deterministic for a pinned source set, and marked as generated in the draft history. Invalid/unavailable combinations fall back to a guided choice instead of silently dropping a rule.
2. **Three layers of content.** SRD is the required base; accessible global publications and campaign/owner content become optional sources subject to server-side scope, licensing/provenance and campaign gates. Every selected item references an immutable source revision and structured rule effects. Display prose is never executable. Existing characters keep their pinned version if a publication changes; stale/missing content gets an explicit review state.
3. **Creation means ready to play.** Finalization must materialize selected starting gear and relevant resources on the sheet, then offer a clear route to open the sheet, enter a campaign/session and roll to the correct table. The sheet, token and hubs consume the same character identity and rule state. Any remaining manual choice is surfaced before finalization or explicitly explained after it.
4. **Progressive disclosure.** A novice sees one decision at a time and context help; an expert can inspect details without a 14,000px form. On a 390×844 screen the first actionable choice is visible in the first viewport, step changes place focus at the new content, and each validation finding can take the user to its control. The shared navigation stays consistent.
5. **Compatibility and safety.** Existing SRD drafts, finalized characters, Roll Drauf Light data, JSON export, live tokens and sheet-to-table rolls remain readable and usable. All mutations use existing auth/CSRF/owner checks. Public content publishing stays attributable and scoped. No new third-party runtime dependency is assumed by this plan.

The implementation details of a new type adapter, source catalog and generated-default contract are **not** preapproved here. Each milestone Apply record must specify exact schema/API changes and migration before Deploy. This program fixes user-visible behavior and invariants; it does not hide those decisions inside deployment.

## Interface and data contracts to preserve or design

| Contract | Required behavior and owner |
|---|---|
| `POST/PUT /api/srd-creator/drafts`, evaluate, finalize | Server owns legality and persists incomplete drafts; new creation modes are additive and preserve existing draft versions. Finalize is atomic with the ready-to-play handoff or reports a recoverable blocker. |
| Draft source references | Source identity, revision/version, digest, license/provenance, scope and access status are explicit; existing SRD pins and old drafts migrate or remain readable. A changed/withdrawn source cannot silently rewrite a character. |
| Generated defaults and templates | Versioned provenance for quick/premade/random values; the player can inspect and edit them. Defaults pass the same evaluator as manual choices. If seed-based randomization is used, the seed is stored for reproducibility. |
| Creation Engine → creator | Only published, validated, authorized revisions become selectable. Per-type adapters map allowlisted structured effects into canonical rule state; unsupported mechanics are labeled or blocked, never treated as playable because prose exists. |
| Character → sheet/token/hubs | Stable character ID and derived columns remain authoritative; inventory/resources/actions and the bound table update consistently. Campaign/DM capabilities are checked on the server. |
| Error and analytics events | Machine-readable path/step/control IDs for actionable findings; anonymous aggregate completion/drop-off/error telemetry only, with no character prose or private homebrew body in events. |

## Order, priority and dependency map

`P1` means required for a credible first playable creator; `P2` is required for the old full-parity promise but can follow the first playable release; `P3` is polish that must still close before claiming the whole program complete. Each milestone is a separate Discover → Apply → Deploy → Monitor cycle. A cycle only enters Deploy after its exact Apply design and applicable decision gates are complete. Its Monitor output feeds the next Discover; medium/high findings get resolved or explicitly accepted through governance before phase transition.

| ID | Milestone | Priority | Depends on | Matrix trace |
|---|---|---|---|---|
| C0 | Freeze evidence, parity ledger and protocol | P1 | none | 1–48 |
| C1 | Guided mobile journey and recovery | P1 | C0 | 2–3, 8–11, 36 |
| C2 | True quick build | P1 | C1, C4 | 1, 5–7, 12, 14 |
| C3 | Premade and constrained random starts | P2 | C2 | 1, 12–13, 37 |
| C4 | Origin, spell and progression choice completeness | P1 | C0 | 3–4, 7, 11, 15–17, 20, 32 |
| C5 | Ready-to-play inventory and resource loop | P1 | C2, C4 | 6, 13, 21–27, 29 |
| C6 | Source discovery and campaign gates | P1 | C0, C1 | 3, 14, 35, 43, 45, 47 |
| C7 | Playable homebrew backgrounds, feats, spells and items | P2 | C4, C6 | 7, 29–30, 35, 46–48 |
| C8 | Playable homebrew class/subclass and creature contracts | P2 | C5, C7 | 15–17, 20, 27, 33, 46–48 |
| C9 | Sheet, table and DM parity | P2 | C5, C8 | 18, 22–28, 31–36, 38, 43–44 |
| C10 | Character lifecycle and portable records | P2 | C3, C7, C9 | 19, 33, 37, 39–42 |
| C11 | Whole-journey accessibility, reliability and parity sign-off | P1 final gate | C1–C10 | 1–48 |

Parallel work is allowed only where dependencies permit and separate Apply records show a safe boundary. C4 and C6 may be discovered while C1 is implemented; C2 waits for rule-complete choices from C4. Production activation still follows each milestone's Monitor gate. C11 is the release claim gate, not a substitute for earlier verification.

## Milestone specifications

### C0 — Evidence and protocol baseline

- **Goal/scope:** turn the 48-point matrix into an evidence ledger with `accepted / partial / open / intentionally inapplicable` states, mapped to current code and browser proofs; freeze the dated competitor behavior and six representative user journeys. No feature implementation.
- **Constraints/deliverables:** preserve historical P1–P12 records; deliver a machine-checkable acceptance ledger, fixtures/accounts setup, screenshot/measurement protocol and source-rights note.
- **Acceptance:** each of 48 points has an owner, observable criterion, proof path and mapped milestone; no “implemented” row is treated as accepted solely because a P-document exists. Baseline re-runs include guided Fighter, global Duckfolk, sheet→table and phone layout.
- **Risk/assumption:** medium evidence gap, reduced by re-running focused browser tests and marking unavailable signed-in competitor detail as unverified. **Deploy handoff:** documentation/test harness only. **Monitor:** ledger reproduces on a fresh checkout and no baseline regression is introduced.

### C1 — Guided mobile journey and recovery

- **Goal/scope:** make the eight-step path calm and segmented: first decision above the fold, compact progress, contextual help, step-local actions, search/filter for growing origin catalogs, direct finding→control navigation, correct scroll/focus and preserved drafts.
- **Constraints/deliverables:** no rules change; preserve accessibility semantics and existing draft API. Deliver phone/desktop screenshots, keyboard/focus checks and a guided novice journey.
- **Acceptance:** at 390×844 the class choice is visible without scrolling; each step opens at its own heading/control; no horizontal overflow; a blocker jump focuses the exact field; reload/back/forward never discards a saved choice; class/species/background search is usable with keyboard.
- **Risk/assumption:** medium layout regression across shared navigation. **Deploy handoff:** scoped template/CSS/JS change and browser tests. **Monitor:** phone completion and error recovery, plus desktop and existing sheet layout smoke.

### C2 — True quick build

- **Goal/scope:** replace the all-sections “Schnellbau” meaning with a level-1 path asking class, species and name, auto-completing legal background, abilities, skills, equipment and spell/feature choices using documented defaults; offer “edit details” into Guided.
- **Constraints/deliverables:** same server evaluator/finalize and source pins; keep existing drafts recoverable, with migration/renaming for old `quick` mode. Deliver default-policy table for all supported SRD classes and species, API contract, rule tests and phone browser journey.
- **Acceptance:** a fresh user can reach a valid sheet after those three decisions; all generated choices are visible and editable; reload retains them; no illegal or missing prerequisite is silently ignored; unsupported published homebrew routes to Guided with a clear reason. Measure decision count, not a promised human completion time.
- **Risk/assumption:** medium rules-default coverage. **Deploy handoff:** exact defaults and migration in milestone Apply. **Monitor:** cohort quick completion/blocker rate and a focused rollback of the new entry path if invalid builds appear.

### C3 — Premade and constrained random starts

- **Goal/scope:** add reviewable, source-pinned premade character templates with class/species/level filters; expose random constraints for level, class, species and optional name before generation. Both start editable drafts.
- **Constraints/deliverables:** no direct finalized-character insertion; templates contain choices/IDs, not copied rule prose. Deliver template schema, provenance and license review, filter UI, seeded random policy if adopted, and browser tests.
- **Acceptance:** a premade or constrained random character is valid through the same evaluator, editable before finalization, and retains its origin/template provenance; filters and empty states work at 390px; invalid/unavailable source combinations are explained.
- **Risk/assumption:** medium stale template/source version. **Deploy handoff:** versioned template fixtures and a source-drift policy. **Monitor:** template validity after content updates and no duplicate ownership/access leakage.

### C4 — Complete rule choices at creation and level-up

- **Goal/scope:** model origin-feat subchoices, species-granted spells, custom background where SRD permits it, languages and tool proficiencies, resistances/senses, spell swap/preparation gaps, and multiclass choice grants consistently in creation, progression and sheet display.
- **Constraints/deliverables:** provenance-linked structured choices, no prose execution; preserve old character data and make missing historical choices visible. Deliver rule-data audit against SRD, evaluator/DTO changes, migration and representative class/species/level tests.
- **Acceptance:** every supported origin/feat option with a required subchoice blocks finalization until chosen; granted spells/tools/languages appear on the sheet and in relevant rolls; level-up and multiclass use the same semantics; old characters can resolve newly exposed choices without losing existing state.
- **Risk/assumption:** medium rule-text modeling and migration. **Deploy handoff:** per-feature rule tables and backward-compatible state contract. **Monitor:** zero newly invalid existing characters without a repair path; spot-check diverse SRD examples.

### C5 — Character ready to play on finalization

- **Goal/scope:** materialize selected starting equipment and currency at finalization; support high-level start equipment guidance and catalog purchase/search/filter; complete hit-dice, short/long rest, spent spell slots, prepared spell/spellbook/ritual controls, concentration and feature resource accounting with sheet/token continuity. Verify containers, weight, currency conversion and attunement limits against the original inventory scope.
- **Constraints/deliverables:** atomic/idempotent gear grant; current HP/AC and live-token contracts remain intact; no auto-spending without a user action. Deliver state transition contract, resource rules, sheet controls and creator→table browser test.
- **Acceptance:** finalize a level-1 Fighter and spellcaster and open a sheet with selected gear and correct initial resources; spend a slot/use a feature, rest, and observe correct recovery; duplicate clicks do not duplicate gear; a higher-level start either has explicit gear choices or a clear DM-assigned handoff, never an unexplained empty inventory.
- **Risk/assumption:** medium transactional and rules complexity. **Deploy handoff:** database/idempotency plan and regression checks. **Monitor:** compare sheet, token, table and campaign state after reload and reconnect.

### C6 — Discoverable sources and campaign content policy

- **Goal/scope:** player-facing source preferences, clear SRD/global/campaign labels, origin discovery/search, stable rule-detail links, publication collection/version views, and DM policy for what a campaign permits; make unavailable choices and version drift intelligible.
- **Constraints/deliverables:** server access checks, immutable publication revisions, mandatory SRD attribution; no private content in public catalog responses. Deliver source catalog/permission contract, campaign policy UI, audit tests across unrelated accounts.
- **Acceptance:** player sees only authorized options; a DM restriction applies to new drafts and is explained on existing ones; global Duckfolk is discoverable to an unrelated account; private revisions never leak; source changes do not silently rewrite finalized characters.
- **Risk/assumption:** medium authorization and source-drift risk. **Deploy handoff:** negative permission tests and rollout flag. **Monitor:** 403/404 and catalog mismatch rates, plus manual two-account smoke.

### C7 — Playable common homebrew types

- **Goal/scope:** make published backgrounds, feats, spells and items from the Creation Engine selectable where relevant, with safe typed effects and sheet/roll behavior; preserve global, campaign and personal publication scopes.
- **Constraints/deliverables:** per-type allowlists and validators; unsupported Foundry-shaped fields must be labeled nonplayable, not silently accepted. Deliver adapter contract and one authored→published→unrelated-player→VTT journey per type.
- **Acceptance:** a player can build and play a character using one published example of each type, with visible provenance, computed effects and correct table action/roll; a private revision is hidden; invalid mechanics cannot be published as “playable.”
- **Risk/assumption:** medium semantic mismatch between Foundry documents and Roll Drauf rules. **Deploy handoff:** per-type Apply slices may be separate Deploys but each closes its own Monitor. **Monitor:** DTO/render parity, publication rollback and regression on existing Duckfolk.

### C8 — Advanced homebrew character and creature contracts

- **Goal/scope:** typed class and subclass progression, choice grants, spell lists and resources; rule-evaluated companion/creature blocks where a character or DM action uses them. Complete the old matrix's remaining Creation Engine categories.
- **Constraints/deliverables:** no executable script from user content; levels 1–20 and multiclass interactions must be validated; separate character options from DM creature catalog access. Deliver versioned schemas/adapters, migration story, exhaustive advancement examples and negative security tests.
- **Acceptance:** an authored class/subclass can be published and used from level 1 through representative high-level and multiclass transitions; its features appear on sheet/actions/rests; a published creature works as an authorized companion/DM block; bad or incomplete effects fail with actionable feedback.
- **Risk/assumption:** medium-to-high rules complexity, resolved in milestone Discover/Apply before implementation; if a strategic effect-model tradeoff has no clear safe choice, route to DAD-M human decision. **Monitor:** advancement and publication correctness across revisions.

### C9 — Sheet, table and DM parity

- **Goal/scope:** close sheet-side partials: explicit manual overrides with provenance, death saves/inspiration/exhaustion/conditions, condition/token sync, full action/spell targeting and damage where rules support it, structured companion actions, complete rule links, DM co-edit permission, XP/milestone awards, party state and live table feedback.
- **Constraints/deliverables:** preserve owner/DM access boundaries and table binding; history records overrides and shared edits. Deliver endpoint/permission contracts, phone sheet/party journeys and simultaneous-tab tests.
- **Acceptance:** the same character state is seen on sheet, token, Play Hub and DM Hub after actions and reconnect; roll destinations are unambiguous; a DM edit is attributable and a player sees it; no unauthorized spectator mutation; action summaries show actual values, including Duckfolk's range/weight.
- **Risk/assumption:** medium concurrency and authorization. **Deploy handoff:** socket/API compatibility tests and staged activation. **Monitor:** stale-state, duplicate-roll and permission error rates.

### C10 — Lifecycle, sharing and portable records

- **Goal/scope:** finish list search/sort/filter, archive/restore/trash, reconstructable change history and undo, respec that preserves linked data, private/public read-only sharing, import/export round-trips, and a useful printable/PDF record including feature references.
- **Constraints/deliverables:** no foreign account import or proprietary format guarantee; existing JSON remains readable. Deliver versioned export schema, import compatibility policy, history/undo boundaries and two-account share tests.
- **Acceptance:** a character can be duplicated, archived, restored, rebuilt/respecced, exported and re-imported without losing selected equipment, required rule choices or provenance; owner and viewer permissions hold; print/PDF includes the information needed to play offline, with licensed attribution.
- **Risk/assumption:** medium data-loss risk. **Deploy handoff:** backup, migration and round-trip fixtures. **Monitor:** import failures, permission checks and sampled restored records.

### C11 — Full journey release gate

- **Goal/scope:** audit all 48 matrix entries plus the four creation paths and integration journeys; remove remaining blockers for accessibility, localization, performance, reliability and privacy. No new feature design is hidden in this gate; defects return to their owning milestone.
- **Constraints/deliverables:** acceptance ledger with proof links, release notes, rollback and Monitor report; benchmark remains dated. Test 390×844 phone and desktop, keyboard/screen reader semantics, reduced motion, slow/reload/offline recovery, and two-account publication/campaign boundaries.
- **Acceptance:** 48/48 points have passed proof or an explicit owner-approved scope exception; guided novice, three-decision quick, premade, constrained random, global Duckfolk and homebrew type journeys finalize a playable sheet; a sheet roll arrives at the bound VTT table; no unresolved medium-or-higher finding is waved through. Production canary smoke and post-release monitor pass before the program is marked complete.
- **Risk/assumption:** medium integration drift; failure returns to the relevant earlier milestone. **Deploy handoff:** release candidate, not new architecture. **Monitor:** real completion/drop-off/error, source access, invalid finalization, and sheet/table consistency over the agreed observation window.

## Common DAD-M cycle and verification protocol

For **each** C-milestone: Discover records current behavior, files, dependencies and severity-labeled findings; Apply freezes exact schemas/routes/migrations and acceptance tests; Deploy makes only that design's changes and records files, targeted tests, browser proofs and acceptance checklist; Monitor checks the released outcome, regressions and residual risks. Each phase record contains `status`, `input_summary`, `artifacts` with retention class, `risks_and_assumptions` with severity, and `next_step`. High/critical security/privacy, critical findings, cross-milestone scope changes, new dependencies outside the agreed boundary or unresolved strategic tradeoffs use the repo's human-decision gate. An approved plan version is the baseline; material changes get v2 and approval.

The reusable protocol should run: (1) novice guided Fighter on a phone; (2) three-decision quick spellcaster and return to edit; (3) premade and constrained random at different levels; (4) a class/origin combination with required subchoices; (5) author→global publication→unrelated player→campaign/DM; (6) finalized character→gear/resources→two-tab sheet roll→table/token/reconnect. Assert server legality and persistence after reload, not only DOM visibility. Take screenshots at the first decision, choice details, validation recovery, final sheet and DM/table result. Track completion, abandonment, blocker category and page errors using aggregate events that contain no private character text.

## Rollout and stop conditions

Activate new creation modes and content adapters behind reversible flags. Migrate/test existing drafts before switching the default entry. Keep old draft/read routes until compatibility checks pass. Run targeted unit/API tests, the six Chromium journeys, accessibility/phone checks and a production read-only smoke before activation; then use disposable accounts for write-path canaries where permitted. Roll back a flag or image if finalization errors rise, source access leaks, gear duplicates, or sheet/table state diverges. A rollback must preserve already finalized records; destructive data rewrites require a separate reviewed migration.

**Plan artifacts (retention):** this versioned decision record (keep), Discover audit and 48-point ledger (keep), per-milestone phase records/proofs (keep), disposable test accounts/data (delete under test policy). **Risks and assumptions:** the Discover risk table remains active until each owning milestone closes it; future licensed content is outside this version. **Next step:** C0 Discover and Apply, then its bounded Deploy/Monitor; only then advance to C1. This document is a draft program plan, not a claim of implemented parity or approval to deploy code.
