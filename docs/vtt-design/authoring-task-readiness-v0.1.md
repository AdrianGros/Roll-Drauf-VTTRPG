# Authoring task readiness v0.1 — 27 September 2026

**Status:** Apply handoff for the user's instruction to resolve the study-task gaps.
**Retention:** repository design and contracts; implementation evidence is recorded separately.
**Authority:** [active G1 contract](../creation-engine/active-contract.json), spec §15
and T45. This is an authoring extension, not a protocol upgrade or G2 runtime implementation.

## Discovery and cause

The G1 program requires four T45 authoring tasks but WP8 implements one registered
flame-item interview. The post-hit yes/no prompt is a runtime response, not an authored
choice. Item prose can preserve lore, but Guided mode asks about flame mechanics first.
The gap is between the study's task breadth and the implemented authoring profiles.
It does not require reopening G0 or replacing the approved specification.

`catalog.py` exposes only the flame type; the authoring store compares every draft's
entire pinned registry with that registry. Adding types to the existing registry would
strand existing drafts and invalidate native revision provenance. The native runtime
only supports the separately pinned flame profile. These are compatibility constraints.

## Solution boundary

Add three explicitly selected private authoring profiles alongside the existing item:

| Profile | Required author decisions | Supported output |
| --- | --- | --- |
| Conditional effect (manual) | Name; affected value; applicability condition; change; end/removal condition | A complete manual instruction card, saved as Sheet-ready. No condition is interpreted or value changed by the engine. |
| Choice (manual) | Name; prompt/eligibility instructions; two to six distinct alternatives and each consequence; number to select | A manual choice card, saved as Sheet-ready. Authors define the alternatives; players resolve the choice and its consequences manually. No grants, prerequisites, selection ledger or undo semantics are executed. |
| Lore | Title and prose | A standalone Lore-only revision, with no flame/mechanical questions and no inferred mechanics or world graph. |

The task prompts must disclose manual resolution where applicable. An acceptance owner
must assess whether these manual tasks satisfy the intended T45 evaluation **before**
scoring the study. This extension supplies real authoring forms and persisted definitions;
it does not declare the human gate passed or rebrand a response as choice authoring.
If automated execution is required for these tasks, design/authorize the G2 extension
explicitly and leave acceptance open in the meantime.

## Interfaces and compatibility contracts

- **AT-C01 — Explicit intent.** Existing item creation remains available. Starting another
  profile requires an explicit selection. Visiting/reloading chooses no answers and creates
  no content. A draft cannot change profile implicitly.
- **AT-C02 — Same draft commands.** Use the existing A1 CreateDraft, RecordDraftDecision,
  Skip/Retraction, Revert and Commit operations with current owner checks, expected versions,
  retry receipts and answer provenance. No database migration, dependency or command diff.
- **AT-C03 — Immutable registry identity.** Keep the original flame registry and compiler
  byte-identical. Each new profile has a separate versioned registry artifact. Resolve a
  draft by its registered type and compare its pinned bytes; unknown or changed registrations
  fail closed. No silent migration of answers or revisions.
- **AT-C04 — No creative defaults.** Required text, alternative count/content and selection
  cardinality have no prefilled answer. Selecting an alternative count exposes blank slots;
  reducing/changing it invalidates all dependent alternatives/cardinality while preserving
  history. Use the existing dependency graph in all three modes and all three locales.
- **AT-C05 — Honest quality.** Incomplete drafts remain saveable. Description requires a name
  and meaningful prose for lore; Sheet-ready manual cards require all applicable answers,
  distinct option labels, and a selection count within the authored alternatives. Runtime-ready
  and Automation-complete are always rejected for these profiles. Lore has no Sheet-ready claim.
- **AT-C06 — Honest preview.** Show author-supplied fields with a persistent localized manual
  or descriptive-only explanation. Render text literally. Manual revisions do not enter the
  executable sandbox catalogue; flame presets are unavailable for non-flame drafts on server
  and client. No runtime writes result from viewing the card.
- **AT-C07 — Recovery and accessibility.** Reuse existing input preservation, conflict,
  access-loss, focus and keyboard behavior. New controls have labels and no inaccessible JSON
  requirement in Guided/Structured modes; Advanced retains typed JSON.

## Risks and tradeoffs

- **Medium, acceptance:** manual cards may not meet the acceptance owner's intended task
  depth. Mitigation: explicit task classification and unresolved acceptance mapping; no waiver.
- **Medium, compatibility:** changing the original global registry would strand old content.
  Mitigation: separate registries and a byte-preservation regression, plus existing draft/native tests.
- **Low, bounded scope:** manual choices have two to six alternatives and select a specified
  number. This is a readable manual card, not the full ChoiceSlot/grant system.
- **Low, rollback:** hide new creation entries to roll back UI availability while retaining
  registered readers and data; removing registrations would strand newly authored drafts.

## Deploy handoff and acceptance

Implement profile registrations, per-type store dispatch, explicit editor creation controls,
localized manual explanations and focused tests. Verify incomplete/invalid quality claims,
dependency invalidation, duplicate choices, forbidden preset application, old-registry identity,
private access, immutable persistence, and browser creation/edit/save across modes/locales.
Use disposable PostgreSQL and automated browsers. No live deployment or user sessions.

Record exact source hashes and results, then update task readiness and the Tuesday run manifest.
G1 remains in Deploy; WP9 human acceptance, participant roster/time, browser/device evidence
and the G1 exit report remain separate obligations. Human testing stays deferred until
Tuesday, 29 September 2026, Europe/Berlin.
