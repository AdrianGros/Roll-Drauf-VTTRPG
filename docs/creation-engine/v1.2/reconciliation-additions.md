## 26. Architecture research incorporated after the approved baseline

**Status: informative research.** This section retains the research from the withdrawn draft. It does not reopen G0, select new dependencies, or change the approved G1 scope. References to earlier sections describe lessons or proposed changes, not amendments to their active contracts. The comparator sample is qualitative; it does not establish which defects are statistically most common.

{{RESEARCH}}

### 26.1 Research source register

{{SOURCES}}

## 27. Clean coding and the implementation already underway

**Status: compatible guidance and proposed additional evidence.** The framework-free core, adapters, shared command boundary, PostgreSQL unit of work, and dependency choices are already described in the approved G1 plan and A1. They are not new architecture proposals. WP1–WP4 implement parts of them. The recommendations below explain how the research supports those boundaries. More specific new checks remain mapped proposals in §29; they do not silently add G1 exit criteria or invalidate completed work.

{{CLEAN}}

### 27.5 Current implementation choices retained

The approved G1 design uses the existing application's isolated engine package, PostgreSQL/SQLAlchemy persistence, RFC 8785 canonicalization, JSON Schema validation, property tests with Hypothesis, and the approved Redis delivery integration. These choices are not reopened by this consolidation. The remaining public policy/transport work is WP6, legacy integration is WP7, authoring is WP8, and milestone evidence is WP9. Future service extraction, a replacement evaluator, or changed deployment topology would be separate changes. CEL and Temporal remain research comparables; Import Linter remains an optional way to enforce already-required dependency direction.

## 28. Research changes and their contract boundaries

**Status: scoped change proposals, except the already accepted spatial product direction.** Sections 1–24, core wire 1.1.3, registry A1 and the approved G1 plan continue to govern current implementation. The terms below express the proposed behavior if the affected change is adopted. They are not runtime commands registered by this document. Each proposal has an affected gate, compatibility analysis and future evidence in §29.

### 28.1 Accepted spatial direction and its boundary with G1

The accepted direction is one authoritative spatial presence per EntityInstance in a RuntimeScope. A presence record is either unplaced or placed in one scene/frame with one position and footprint. Several live views may project that location; reference markers may show other locations without mechanical authority. Independent creatures have separate instances. Shared resources across multiple simultaneous physical bodies require a later explicit capability.

This direction belongs to spatial mechanics, principally G5. The approved E4 distinction remains: moving a token on a map without declared spatial mechanics is an ungated representation edit (T55); moving a mechanical token during another active action on a map with declared spatial mechanics is refused (T56). Under the proposed presence model, an ordinary map marker remains a reference representation. Dragging it does not place or move the authoritative presence, including when the same occurrence also has a presence on another map. Mechanical placement, movement and transfer are explicit operations subject to the gate. This reconciles the accepted direction with E4; it does not turn all token movement into a mechanical command.

The G1 adapter still maps token and sheet resources to the occurrence and leaves ordinary x/y representation edits alone as A1 specifies. No presence table, four-command rollout or ExecutionLock shape change is added to the current G1 work packages by this document.

The following detailed spatial design is retained for the affected gate's design work. New SceneRef/RepresentationRef shapes, coordinate/geometry types, authority rules and migration behavior require a versioned registry/lock compatibility design before they become an implementation contract. Existing commands and immutable schema IDs must not be redefined.

{{SPATIAL}}

### 28.2 Stable cost identity and transaction ownership

The approved kernel already owns atomic checkpoints, source-occurrence spending and durable idempotency. The research adds a proposed explicit cost key `(actionId, checkpointId, costId, boundedOccurrenceIndex)` to distinguish a repeated delivery from two legitimate costs on the same pool. Costs sharing a pool should be checked against aggregate availability while retaining distinct identities. Existing WP4 proofs remain evidence for their recorded scope; they are not automatically evidence for this additional cost-key convention. T57 and T58 add targeted review cases.

The proposal to distinguish a durable admission/attempt record from a committed checkpoint is a clarification of the boundary, not a requirement to change current public receipt shapes. A pending record is never proof that resources changed. Public output remains `PublicReceipt`, filtered under current permissions, without an outcome digest or omitted-event count. Receipt recovery must retain the original identity and respect current account/read access; it cannot turn a stale retry into a fresh mutation.

### 28.3 Deterministic provenance refinement

Full and incremental result/provenance equivalence is already required by §7. The following ordering is a refinement proposal; it is not retroactively imposed on the pinned WP2 evaluator without a compatibility comparison and version decision.

{{PROVENANCE}}

The internal semantic input/lock digests in that proposal remain private whenever they cover unreadable facts. Clients receive permitted projected explanations and, when binding an answer to private context, the approved opaque `contextToken`. No proposed presence or provenance field reintroduces the withdrawn public `contextDigest` contract.

### 28.4 Logical fuel and operational retry proposal

The approved §18 limits and locked evaluator semantics remain the current contract. The research recommends distinguishing deterministic logical charges from the amount of work caused by database failures. The five-attempt recovery episode, durable attempt ledger and cache/reference-charge rules below are new detailed proposals. They require an impact review of the existing evaluator and kernel, a lock/version strategy where behavior changes, and focused acceptance evidence; they are not an instruction to rewrite WP2/WP4 or defer WP5 now.

{{FUEL}}

The references to §9 above concern checkpoint history. `OPERATION_RETRY_EXHAUSTED`, episode records and their proposed handling are not added to the currently approved API merely by appearing here. Client-facing statuses and an error/registry addition must be reviewed together with the implementation change. Existing decisions still obey the approved clock-anomaly handling, internal lease fence versus authority epoch, and decision-specific expected-version rules.

### 28.5 Migration, persistence and verification refinements

Scope-level migration authority from E1 remains mandatory: no engine action may read a legacy-authoritative mechanical dependency, and there is no per-character cutover inside one active scope. The future presence migration adds explicit resolution of conflicting token locations; it must not choose the last viewed token or infer a location from a timestamp. This is additional spatial migration design, not a replacement for the existing scope migration protocol.

Fresh-session JSON reloads, same-command transport comparisons, cache comparisons and architecture import checks are proposed evidence for existing or refined invariants. They should be assigned to the affected work package after checking what its tests already establish. Inert `legacyMetadata`, explicit adjustment-bound policy, typed Predicates, UTC timestamps, exact source occurrences, and current-policy projection remain approved behavior, not optional research suggestions.

## 29. Acceptance reconciliation and change disposition

T01–T56 and the 20 approved requirement rows in §§21 and 23 retain their exact approved meanings. Their historical catalogue status is not a current test dashboard; implementation evidence is recorded by work package in the G1 program. G0 approval and the WP1–WP4 records are retained. The tests below are proposed additions, not executed results or automatic new G1 exit criteria.

The withdrawn draft had reused T47–T56 for unrelated research scenarios. The corrected mapping shifts its T47–T64 to T57–T74. Always qualify an old citation as `withdrawn-v1.2:Txx` before translating it; an unqualified approved T49 still means source-occurrence isolation, for example. Original research RA01–RA10 map to T57–T66.

| ID | Setup / adversarial action | Required observable result |
| --- | --- | --- |
{{NEW_CASES}}

### 29.1 Proposed requirement mappings

These six IDs are proposed additions. They do not replace CE-MANUAL-01 or CE-RULESET-01, and they do not change the approved requirement-to-case mappings in §23. References here identify the proposal's clauses and tests rather than declaring the whole section normative for current G1.

| Requirement | Proposed contract | Acceptance IDs |
| --- | --- | --- |
| CE-PRESENCE-01 | Occurrence-owned presence with E4-compatible representation edits; §28.1 | T59, T66–T71 |
| CE-PROVENANCE-01 | Stable contribution identities/order and pure projection; §§27, 28.3 | T60, T65, T74 |
| CE-RETRY-01 | Logical fuel separate from bounded operational recovery; §28.4 | T64, T74 |
| CE-ARCH-01 | Explicit dependency, type and side-effect evidence; §27 | T58, T60–T61, T72–T73 |
| CE-PERSIST-01 | Whole-checkpoint ownership and real-backend/fresh-session evidence; §§27, 28.2 | T57–T58, T61, T67 |
| CE-TEST-01 | Additional lock, policy, recovery and adapter evidence; §§27–28 | T57–T74 |

### 29.2 Disposition by change, without restarting G1

| Change | Authority / compatibility | Affected work and adoption condition |
| --- | --- | --- |
| Approved E1–E4 corrections and registry A1 | Retained in full, with existing schemas, IDs and gates | Continue current G1 plan; no new approval or audit needed merely to retain them |
| Clean-code boundaries and checkpoint ownership | Already supported by approved plan/A1; additional fixtures are proposals | Apply existing boundaries in remaining WPs; add new checks through ordinary scoped review |
| Single authoritative presence | Product direction accepted; detailed contract not yet approved for implementation | G5 spatial design; preserve E4 and ordinary G1 representation editing |
| Spatial commands and geometry/lock fields | Breaking additions cannot be smuggled into frozen wire 1.1.3 | Design a versioned registry and lock extension at the spatial gate; migration/compatibility review then |
| Explicit cost identity | Refines existing spending guarantees | Kernel impact review; retain valid WP4 results and add only necessary fixtures |
| Canonical provenance tuple | More specific than current equivalence requirement | Evaluator compatibility comparison and version decision before changing locked output |
| Five-attempt episodes and cache-independent logical charge | New detailed budget/recovery behavior | Separate evaluator/kernel change proposal; not a prerequisite for the current WP5 contract |
| Research findings already covered by existing tests | Evidence can be reused only for demonstrated behavior | Map tests to both IDs with their scope; do not rerun or relabel all work as unproven |

## 30. Active contract, implementation status and next action

**The project remains in G1 Deploy.** G0 passed on 24 September 2026. The approved specification is v1.1.4, the core wire contract is 1.1.3, and registry A1 supplies 24 additional commands. The core supplies three, for 27 approved command shapes. A documentation revision number does not bump any of these protocol identifiers.

The approved plan records WP1 (canonical types), WP2 (evaluator), WP3 (content store and RDL subset) and WP4 (transactional kernel) as implemented and committed. It records a WP4 full regression run of 1,067 passing tests and a final focused engine run of 435 passing tests. Those are historical results with their own scope. At reconciliation, HEAD was `66b6fc447c5bf5b15886aeec559961a2b68e30b9`; WP5 decision/deadline work was present as uncommitted changes. This documentation task neither executes those engine tests nor certifies the unfinished changes.

The next implementation action is to finish and verify WP5 against v1.1.4/core 1.1.3/A1, then continue WP6 policy/public transport, WP7 legacy integration, WP8 three authoring modes, and WP9 milestone evidence and user study. The user-approved locales remain German, English and French. The RDL subset, flame sword/private curse fixture, applicability rulings and approved dependencies remain as recorded in D1–D8. No live cutover is authorized by this reconciliation.

Future research deltas receive a narrow review when their affected package/gate is ready. They do not invalidate the passed G0 or require repeating G1 discovery and architecture. A discovered implementation defect against the current contract should be fixed against that contract; it is not a reason to replace it with an unapproved draft.

The repository's `docs/creation-engine/README.md` is the entry point. It names the approved specification, wire schemas, approval record and implementation program. This v1.2 document is their reconciled reading edition plus an explicitly bounded research change register. The source manifest and verifier check that the approved body, acceptance identities, schemas and A1 remain intact. The withdrawn package is historical evidence only.
