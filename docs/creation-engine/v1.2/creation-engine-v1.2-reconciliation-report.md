# Creation Engine contract reconciliation and cause analysis

**Date:** 25 September 2026. **Status:** documentation divergence corrected; G1 remains in Deploy. **Input:** approved v1.1.4, E1–E4, core wire 1.1.3, registry A1, approval D1–D8, the implementation program, and the withdrawn research rewrite. **Boundary:** documents, schemas and their verification; no application implementation, database migration or change to the current milestone authorization.

## Outcome

The reconciled v1.2 is a reading edition of the approved contract plus a scoped research change register. It does not become a new implementation baseline merely because its document version is higher. The approved body, 20 requirements, T01–T56, core schema and A1 are preserved. The earlier v1.2 rewrite and its seven-command wire 1.2 schema are withdrawn from authority and archived.

The project did not need to return to specification discovery. G0 had passed and G1 implementation had been authorized. WP1–WP4 remain completed for their recorded backend scope; WP5 remains the next implementation work. Finishing this documentation reconciliation does not require re-approving those decisions or rerunning all their tests. New research changes are reviewed only where they affect a later package or gate.

## Why the documents diverged

The immediate error was using a stale contract as the rewrite base. I selected the earlier task workspace's v1.1 specification/schema/acceptance files, then treated the repository's newer implementation as outside the rewrite. That separation was appropriate for avoiding application edits, but wrong for discovering the authoritative specification. I should have followed the repository's updated CONTEXT.md pointer, approval record and G1 plan before writing any supersession language.

There were four compounding errors:

1. **Wrong input boundary.** The v1.2 source manifest pinned v1.1 and the research companion, not the approved v1.1.4 contract, E1–E4, A1 or the deployment authorization. Research freshness was mistaken for contract freshness.
2. **Detected drift was not acted on.** On 25 September I recorded HEAD `66b6fc4` and that CONTEXT.md had changed. I still used the old inputs. The newer contract was discoverable; this was not an unavoidable absence of information.
3. **Validation checked the wrong baseline.** The draft preserved T01–T46 and checked its own schemas, references and PDFs. It did not compare against the approved 56 cases, 20 requirements or the implemented wire 1.1.3 contract. Its T47–T56 therefore reused IDs already assigned by the audit, and a syntactically valid new schema discarded approved privacy and source-occurrence protections.
4. **Phase and authority were conflated.** A request to rewrite documentation was described as a new specification candidate awaiting implementation handoff. It should have been a reconciliation within a project already in G1 Deploy. That wording suggested a project reset even though the existing approval and code remained in place.

Contributing documentation ambiguity also existed: the evolving G1 program still contained its original “nothing implemented” planning sentence, and the immutable approval record starts with its pre-authorization context before recording approval at the end. Those are historical statements, not the current status. The updated entry point and program annotation make that distinction explicit. They do not excuse the missed contract lookup.

There is no evidence in the inspected checkout that implementation was rolled back or that the withdrawn schema was adopted by the engine. The source of the apparent move “back into spec” was my parallel rewrite and status framing. I take responsibility for that error.

## Evidence and chronology

| Event | Evidence | Meaning |
| --- | --- | --- |
| Research sampled the earlier application state | Withdrawn manifest: research HEAD `87ff37f`, v1.1 input hashes | A valid historical sample, not the later approved contract |
| G0 closures and G1 authorization recorded on 24 September | Approval record's final G0/Deploy rows; E4 errata | v1.1.4 approved; core remains 1.1.3; A1 approved; G1 authorized |
| Approved packet and plan present in repository history | Commit `646e4e4`, recorded author date 24 September | Contract and approval available in the implementation checkout |
| Backend implementation proceeded | WP1 `e17ae9c`, WP2 `825b8ad`, WP3 `d7a8fd0`, WP4 `66b6fc4` | The project had moved beyond theory |
| Rewrite resumed on 25 September | Withdrawn source manifest records HEAD `66b6fc4`, changed CONTEXT.md and WP5 files | Drift was visible but the contract source was not refreshed |
| Incorrect v1.2 package delivered | Archived spec/schema/catalogue and their hashes | It reverted wire protections, reused acceptance IDs and overstated supersession |
| Status check found divergence | Current CONTEXT.md, v1.1.4 errata and G1 program | Prompted this correction rather than an implementation restart |

The approval record is the source for decision dates; identical commit author timestamps do not establish the precise order of conversations. This analysis uses repository artifacts and this conversation, not an inferred account of other contributors' intentions.

## Approved corrections restored

The complete approved body is preserved in §§1–25 of the reading edition, with only three enumerated editorial status/provenance updates. The full G0-01…G0-20 closure table remains in §23. Notable protections that the withdrawn rewrite omitted or weakened are:

| Approved contract | Correct reconciled behavior |
| --- | --- |
| G0-01 privacy | Opaque `contextToken`; separate `PublicReceipt`; no public outcome digest or omitted-event count; audience-bound delivery |
| G0-02 migration | Migration authority belongs to the whole runtime scope; no mixed per-character cutover |
| G0-03 source identity | Tagged `actorInstance` and `sourceInstance`; costs resolve to the exact source occurrence; tagged resource target |
| G0-04 / G0-06 decisions | Suspension at the mandatory deadline; decision-specific expected-version/context-token admission |
| G0-07 fencing | Internal worker fences remain distinct from the authority epoch; restore advances the authority epoch |
| G0-08 / G0-09 authority and bounds | Explicit controller/operator relationships and resource adjustment-bound policy |
| G0-10 / G0-12 typed data | Approved numeric core functions, Predicate schema and inert legacyMetadata |
| G0-14 / G0-19 requirement identity | CE-MANUAL-01 and CE-RULESET-01 retained, including original case mappings |
| G0-15 / G0-18 decision timing | Fixed candidate order per reaction slot and explicit forward-clock-anomaly handling |
| G0-16 / G0-17 / G0-20 edge cases | Precommit cancellation; distinct capacity/budget responses; schema-aligned fields and UTC timestamps |
| G0-11 registry | All 24 A1 operations and their four envelope families retained with immutable IDs |
| G0-13 / E4 map behavior | Ordinary-map movement remains ungated representation state; declared spatial mechanics obey the action gate |
| D1–D8 implementation decisions | Approval, applicability rulings, RDL subset, dependencies, flame sword/private curse fixture and German/English/French locales retained |

## How the research is retained without changing the current contract

The accepted single-presence direction remains the target for spatial mechanics. Ordinary map markers are nonmechanical reference representations; moving one does not move a future authoritative presence. That interpretation preserves E4 and the current G1 adapter behavior. Detailed presence storage, four spatial commands, geometry/lock changes and migration fixtures stay assigned to the spatial design, principally G5.

Cost identities, a canonical provenance tuple, cache-independent logical fuel and a five-attempt recovery episode are concrete refinements. They are not facts about the existing pinned engine and were not approved by the earlier G1 decision. They remain scoped change proposals with compatibility and evidence obligations. Existing architectural boundaries are retained as adopted design; extra verification suggestions do not silently enlarge the G1 exit gate.

The active command schemas are exact copies of approved core 1.1.3 plus A1: **27 approved command shapes**, not the withdrawn set of seven. The document's v1.2 label is not a protocol upgrade. No new spatial operation is registered by the reconciliation.

## Acceptance identity repair

T01–T56 and all 20 approved requirement rows remain unchanged. The withdrawn draft's 18 research cases are reassigned to T57–T74. RA01–RA10 map to T57–T66. The six research requirements are marked proposed, leaving 20 approved plus six proposed requirements. There are 56 approved plus 18 proposed scenarios; this is not a claim of 74 executed tests.

| Withdrawn draft | Correct research ID | Existing approved meaning retained |
| --- | --- | --- |
| T47 → cost deduplication | T57 | Approved T47 remains privacy against hidden-value enumeration |
| T48 → helper commit | T58 | Approved T48 remains scope-level migration authority |
| T49 → spatial presence | T59 | Approved T49 remains source-occurrence resource isolation |
| T50 → recomputation | T60 | Approved T50 remains labelled manual adjudication |
| T51 → JSON persistence | T61 | Approved T51 remains reaction ordering |
| T52 → lock artifacts | T62 | Approved T52 remains precommit cancellation |
| T53 → output policy | T63 | Approved T53 remains capacity/budget behavior |
| T54 → work budgets | T64 | Approved T54 remains clock anomalies |
| T55 → canonical JSON | T65 | Approved T55 remains ungated ordinary-map movement |
| T56 → spatial decision recovery | T66 | Approved T56 remains gated mechanical-map movement |
| T57–T64 → additional spatial/architecture cases | T67–T74 | No approved case overwritten |

The machine-readable catalogue includes a qualified `withdrawn-v1.2:Txx` translation map. An unqualified test ID in existing implementation evidence keeps its approved meaning.

## Prevention and remaining risks

| Finding | Severity / disposition | Prevention or boundary |
| --- | --- | --- |
| Approved security clauses missing in a competing draft | High documentation regression; corrected | Restore approved body and exact schema bytes; reject the withdrawn public digest and missing-source command shapes |
| Acceptance ID collisions | High traceability defect; corrected | Preserve approved case text; append new IDs; qualify historical mappings |
| G1 phase presented as unapproved design | Medium process defect; corrected | Repository entry point and program status annotation; approval record remains authoritative |
| Baseline drifts during future document work | Medium recurrence risk; guarded | Pin the active contract in source manifest; verifier fails if local approved source/schema hashes change |
| Research proposals mistaken for adopted behavior | Medium scope risk; bounded | Separate approved/proposed catalogue entries; explicit affected gates; no automatic wire or exit-gate change |
| Current WP5 changes not verified here | Scope limitation | Preserve application files; finish WP5 under its existing implementation authorization and test plan |

The verifier checks approved-body preservation, original case/requirement identity, G0 closure retention, active wire version and A1 resolution, source hashes, privacy/source-identity negative examples, remapped proposal IDs, and rendered outputs. It checks all 24 A1 examples and rejects spoofed principals, extra payload keys, missing epochs and the withdrawn wire version. These checks establish document compatibility, not runtime conformance.

## Next action

Continue the approved G1 program at WP5. Review and finish pending decisions, deadlines, revocation, interventions and manual resolution against v1.1.4/core 1.1.3/A1. Then proceed through WP6–WP9. Do not stop that work for a fresh G0 or for future spatial/retry design. When a research proposal becomes relevant, assess its narrow contract/fixture/lock impact and record the decision before implementing it.

Artifacts are retained in the repository's `docs/creation-engine/v1.2/`. The old package is archived in the research workspace and its original hash is recorded in the new source manifest. The approved historical packets and approval record remain untouched.
