# Roll Drauf Creation Engine

## Research and Technical Specification v1.2

**Status:** proposed normative baseline, Audit Candidate 2; single spatial presence accepted as the design direction. **Date:** 25 September 2026. **Scope:** the complete Creation Engine target, with explicitly bounded conformance profiles and release gates. **Work phase:** Apply / specification design. Implementation conformance, production migration, and deployment require their separate gates.

This document replaces v1.1 as the complete specification candidate. It incorporates the architecture research of 24 September, the agreed single-presence spatial model, explicit implementation boundaries, deterministic provenance, and separate semantic and operational work limits. It carries forward the full product scope and all thirteen original audit responses. Readers do not need to combine earlier specifications or the research companion to recover the normative contracts. Historical documents remain evidence of the design's evolution.

Acceptance of the spatial direction does not establish implementation correctness or approve an infrastructure vendor. The remaining detailed defaults in this revision are concrete design proposals for independent review. Written closure, schema validity, executable acceptance, and production readiness are separate claims.

The creator decides what content means. The platform translates supported intent into explicit definitions; validates, versions, executes, explains, and renders those definitions; and preserves the distinction between creative decisions and technical interpretation.

Companion artifacts: `creation-engine-v1.2-contracts.schema.json`, `creation-engine-v1.2-acceptance.json`, `creation-engine-v1.2-wire-examples.json`, `creation-engine-v1.2-change-report.md`, and the source/verification manifests. All acceptance cases are specified but unexecuted by this documentation task; this status is not a verdict on tests in the separate implementation work. Sections 1–2, 4–24 and 26 define the target contracts; §3 and §25 record research evidence; §27 records decision status and the remaining implementation handoff.

## 1. Normative authority and review boundary

MUST and MUST NOT are conformance requirements. SHOULD requires a documented exception and a test demonstrating why the exception preserves the affected invariant. MAY indicates optional functionality. Descriptive research does not impose behavior. The normative body, its requirement catalogue, and companion schemas MUST agree; a discovered contradiction blocks conformance for that feature. No implementation may silently choose the weaker interpretation. Examples illustrate the body and are invalid if they conflict with it.

The requirement catalogue maps authoritative sections to acceptance scenario IDs. The schemas define the wire syntax of the selected core contracts; the body additionally defines relational, authorization, state-transition, and transaction constraints that JSON Schema cannot express. Passing schema validation alone never authorizes execution. Unspecified executable behavior is unsupported and MUST fail closed or remain explicitly manual. An extension cannot make an undefined behavior valid by inventing an unregistered enum or key.

This document chooses proposed defaults so the next audit can challenge concrete decisions. Those choices are design proposals within the user's request, not evidence that the team has approved implementation, production risk, or a public launch. Persistence vendor, deployment topology, and UI toolkit are intentionally outside this contract. Their selection MUST satisfy the observable semantics here. No choice of database is allowed to weaken atomicity or authorization.

The VTT integration observations were rechecked on 24 September against local HEAD `87ff37f61fa186d251001bbe42b2e3534318cd0b`; the selected source hashes matched the research manifest when this revision began. Four pre-existing untracked documentation files were preserved. On resumption on 25 September, the checkout had advanced to `66b6fc447c5bf5b15886aeec559961a2b68e30b9` with ongoing Creation Engine changes; among the earlier inspected files, CONTEXT.md and requirements.txt had changed. The selected legacy route/model/transport observations still matched their recorded hashes. The newer implementation was not audited or modified for this rewrite. These observations are a dated static sample, not a production inventory, complete writer inventory, or conformance verdict on ongoing work. The application uses local accounts and campaign roles; Discord is an optional linked identity. Workspace membership MUST NOT be inferred from a Discord server ID alone.

## 2. Product contract and full target scope

The target includes guided homebrew authoring; structured and advanced editing; reusable rules/content packages; character creation and progression; live VTT activities and effects; NPCs, lore, settlements, maps, relationships and timelines; semantic presentation and publishing; controlled imports/exports; and an eventual trusted extension ecosystem.

All authoring surfaces MUST emit the same authorized semantic commands. They MUST NOT maintain different mechanical rules implementations. The server's committed canonical state is authoritative. Client calculations are previews labelled with their input revision; they cannot debit resources or establish a roll outcome.

Creative assistance and prose import produce proposals. They MUST NOT bypass confirmation, content validation, entitlement checks, or the command boundary. The deterministic interview can operate without an LLM; this specification makes no promise to understand arbitrary prose deterministically.

Manual play is a supported operating mode. A manually adjudicated action records its declared outcome, authorized adjudicator, affected values, and reason. The UI MUST distinguish it from an outcome established by the rules evaluator. Manual fallback cannot grant a player otherwise unavailable mutation privileges or convert an unreviewed package into executable content.

Official, publisher, homebrew, and imported content use the same runtime contracts when execution and rights permit. Their provenance, entitlement, and redistribution permissions remain distinct. The system MUST NOT equate technical importability with permission to redistribute.

| Capability profile | Required behavior | Excluded from that profile |
| --- | --- | --- |
| `core-safe-1` | Typed acyclic formulas; declarative effects; bounded activities; resources; authorized human predicates; immutable revisions; locked dependencies; safe rendering | Arbitrary code, fixed-point evaluation, external network calls from rules |
| `progression-1` | Choice/grant ledger; reversible derived entitlements; explicit conflicts for irreversible consequences | Pretending past gameplay can be erased by removing a level |
| `world-1` | Campaign occurrences, typed scoped relationships, permission-aware mentions/transclusion, at most one authoritative spatial presence per occurrence | Simultaneous physical bodies sharing one occurrence; population/economy simulation unless separately declared |
| `interop-1` | Canonical lossless authorized export; previewed imports; adapter capability/loss reports | Implicit lossless round trips through other platforms |
| Future executable extension profile | Separately versioned isolation, capability, reproducibility, and resource contracts | Third-party script execution under `core-safe-1` |

These profiles sequence delivery; they do not remove future target capabilities. Unsupported mechanics remain authored and renderable at manual quality. The UI must explain the exact automation boundary rather than imply full support.

## 3. Research synthesis, comparables, and failure evidence

This section is informative. The architecture research used a targeted qualitative sample of primary documentation, original architecture descriptions, maintainer release notes, and first-hand upstream issue reports. It does not establish a statistical ranking of the most frequent defects. Priorities reflect relevance and possible impact on Roll Drauf. No competitor bug was reproduced locally.

Evidence classes: **A** = primary technical specification, inspected source, or maintainer-recorded fix; **B** = primary product behavior or declared design without corresponding implementation verification; **I** = first-hand issue report whose reproduction or root cause has not been independently established here; **C** = secondary/community material; **D** = unsupported marketing. A closed issue is historical evidence, not a claim of a current defect. Applying a comparator's lessons to this platform is a design inference. Neither a familiar name nor a shared JSON shape proves equivalent execution semantics.

| Comparable | Evidence and useful lesson | Boundary of inference |
| --- | --- | --- |
| Foundry D&D5e | A; distinct activities and advancement support explicit activation and construction contracts [S01–S02] | Does not prove Roll Drauf checkpoint, rollback, or server-authority semantics |
| Foundry PF2e | A; typed declarative elements, ChoiceSet, and explicit grant reevaluation/deletion behavior [S03] | PF2e's selectors and stacking rules are not our generic core; declarative content still needs bounds |
| Dungeon Master's Vault / OrcPub | A for the original-author architecture description; hierarchical choices derive character attributes through modifiers [S04] | Character construction does not make consumed/transferred gameplay state reversible |
| DiceCloud | B; primary README corroborates value provenance and equipment-dependent recalculation [S05] | Its internal graph algorithm, library rules, and concurrency behavior were not inspected; inherited community guides remain C |
| Kanka | B; member-view permission testing with owner-private restrictions [S06] | Its documented editable member view differs from Roll Drauf's explicitly read-only intersection model |
| Homebrewery | A; documented Legacy/V3 render evolution and output compatibility concerns [S07] | Render equivalence does not establish exact publication bytes or authorization |
| Temporal | A; deterministic durable workflows, version-aware resumption, and historical replay checks [S08] | An architectural analogue, not a selected dependency; database effects and game semantics remain our responsibility |
| CEL | A; host-provided data, constrained expressions, and explicit complexity obligations [S09–S10] | Not selected as the evaluator: exact rationals, units, staged reads, unknown values, fuel, and provenance require our conformance proof |

Foundry's token documentation distinguishes scene-specific token positions from linked resource data [S27]. The single authoritative presence chosen here is a Roll Drauf design decision, not an assertion that Foundry implements that model.

Primary entries S01–S27 are linked in §25. The earlier market/workflow references R01–R31 and community entries C01–C06 remain a historical register with their checking status. Roll20, D&D Beyond, Fantasy Grounds, World Anvil, LegendKeeper, and statblock tools remain product research context; their inherited descriptions are not used here to assert unverified current capabilities or implementation contracts.

The following evidence directly informs this revision. Issue reports are not treated as verified root-cause analyses:

| Failure family | Evidence | Contract response |
| --- | --- | --- |
| A logical resource cost applies twice | Historical first-hand Foundry report #1239 [S11] | Explicit cost identity and one checkpoint owner; §§7–9, T47 |
| Shared tokens disagree on conditions | Foundry #7470 reports linked-token falling conflicts across positions/scenes; closed when checked [S15] | One occurrence-owned presence; §§4, 16, T49 |
| Separate creatures share a cadence key | Foundry #7483 reports region behavior for unlinked tokens; closed as not planned; suggested cause unconfirmed [S16] | Instance identity plus explicit cadence buckets; §11, T61 |
| Derived HP or rules edition applied incorrectly | Maintainer notes record fixes #5785 and #5787 [S17] | Recompute from source inputs and exact locks; §§6–7, 12, T50, T52 |
| A secondary view exposes an inaccessible link | Maintainer notes record fix #5840 [S17] | Current-policy projection on every output; §14, T53 |
| Transport order mistaken for durable delivery | Socket.IO delivery contract and outbox guidance [S12–S13] | Durable receipts, atomic outbox, deduplication and recovery; §§8–10 |
| ORM helper commits early or misses nested JSON changes | SQLAlchemy documentation plus selected local code observations [S14, S19] | Explicit transaction ownership and persistence tests; §§5, 26, T48, T51 |
| Declarative content hides unbounded work | CEL language/cost specification [S10] | Meter compound work and separate retry budgets; §18, T54, T64 |

Original clean-architecture and ports-and-adapters descriptions support isolating domain rules behind explicit interfaces [S23–S24]. Their application here is §26's testable dependency and side-effect contract, not a mandate for a particular number of classes, services, or layers. Hypothesis and Import Linter are optional implementation candidates [S25–S26]; no new runtime/test dependency is selected by this specification.

The market-gap thesis remains a hypothesis: expressive mechanics may be useful when authors can reach them through a clear interview. It MUST be tested through the representative creation tasks in §22. Competitor roadmaps cannot establish a launch deadline, staffing estimate, or permission to bypass correctness gates.

## 4. Identity, scope, revisions, and ownership

The system MUST distinguish these records:

| Record | Identity and owner | Mutable state |
| --- | --- | --- |
| Definition | Stable logical content ID within an owning workspace/publisher | Name/index pointer and administrative metadata; never the bytes of a published revision |
| Revision | Immutable revision ID and canonical content digest | None; superseding content creates another revision |
| Draft | Stable draft ID, owner workspace, monotonically increasing draft version | Proposed definition and unanswered decisions |
| EntityInstance | Stable occurrence ID, owning runtime scope, pinned revision, optional world identity | Runtime resources, equipment state, decisions, explicitly permitted overlays; owns its SpatialPresence record |
| SpatialPresence | Exactly one versioned record per live occurrence, addressed by its InstanceRef | Unplaced or one authoritative scene/frame/position/footprint; never two concurrent placed locations |
| RuntimeScene | Stable SceneRef inside one RuntimeScope | Versioned mechanical geometry, registered coordinate frame, and scene access policy |
| WorldEntity | Stable identity within one world scope | World facts and links, each governed by version and access policy |
| Representation | Token, sheet, map pin, alias, or publication reference to an occurrence/world identity | Display configuration and reference-marker layout; live mechanical position is projected from SpatialPresence |
| PackageVersion | Package ID plus immutable version and manifest digest | None; withdrawal is separate registry metadata |
| ExecutionLock | Immutable resolved content and evaluator closure | None; replacement is an explicit campaign migration |

An ID is an opaque ASCII string of 1–128 characters using letters, digits, `.`, `_`, `:`, and `-`. Its text is never authorization. Logical IDs are globally unique within their registered namespace; import collisions MUST be resolved by verified identity or an explicit remap, never overwritten. IDs are not reused after deletion. Human names are mutable labels. Semver labels never substitute for a content digest or immutable revision identity.

A revision contains typed, namespaced components; activity, effect, resource, choice and advancement definitions; semantic presentation bindings; and source metadata. All executable references inside a published revision resolve through its ExecutionLock. Instance overlays may change only paths declared overrideable by the pinned schema and permitted by the campaign. Overrides are versioned commands with reason and provenance; arbitrary patches are forbidden.

`DefinitionRef`, `RevisionRef`, `InstanceRef`, `WorldRef`, `SceneRef`, and `RepresentationRef` are distinct tagged wire types. Instance, scene, and representation references include their RuntimeScope; WorldRef includes its world scope. A relationship schema declares accepted source/target reference kinds, entity capabilities, cardinality, temporal validity and inverse behavior. Content-template relations refer to definitions/revisions; campaign relations refer to instances/world entities. Scene and representation references are allowed only where explicitly registered. Runtime lookup MUST NOT automatically substitute one reference kind for another.

A named NPC package supplies a reusable definition. Installing it in campaigns A and B creates independent world identities and instances. Two representations of the same individual in A reference the same occurrence, resources, and authoritative spatial presence. A live view derives its spatial geometry from that presence. A reference marker may have different display coordinates, including on another map, but cannot independently establish range, occupancy, targeting, auras, or vision. An intentionally independent creature receives a new occurrence with independent resources, presence, and cadence. A disguise is a separately permissioned view, not another HP pool or physical body.

The single-presence constraint is per occurrence within one RuntimeScope, not per browser, selected token, active scene, or connected user. Several campaigns may each have their own independent occurrence of the same personal character or definition. One occurrence can be unplaced for preparation or manual play. Two simultaneous bodies sharing its state require a later explicit capability with damage, conditions, cadence, and targeting semantics; duplicating a token cannot enable that capability.

Publications and packages MUST NOT contain campaign occurrences or secrets implicitly. A user can explicitly fork permitted content into a new definition; provenance records the origin without retaining unauthorized read access. Cross-world live mechanical links are unsupported in the baseline. Cross-campaign transfers require an explicit export/import or later transfer protocol; they cannot participate in one baseline action transaction.

Deleting a live reference target requires impact analysis. Soft-deleted objects leave a tombstone with no unauthorized name or metadata. Deleting a representation does not delete or unplace its occurrence. Deleting a scene containing placed occurrences requires explicit authorized transfers or unplacements and resolution of pending-action conflicts before scene removal. Referenced immutable revisions remain retained under the applicable retention/rights policy. Hard deletion that makes replay impossible must record that limitation and remove the exact-replay claim; it must not silently bind the ID to replacement content.

## 5. VTT integration and migration contract

The first integration target is existing Roll Drauf Light characters. The first full reference ruleset is separately versioned D&D 5e, with 2014 and 2024-compatible variants explicitly distinguished. Neither is silently applied to Roll Drauf Light. The first slice uses a deliberately small test ruleset plus a real legacy-character adapter; passing it is not a claim of complete D&D coverage. A campaign selects one ruleset composition and one ExecutionLock. Mixed editions require a named compatibility profile and fixtures; otherwise combination is rejected.

The existing VTT's integer character/equipment/token IDs are mapped to new opaque IDs in a bijective migration ledger keyed by source type, source ID, and migration version. The original identifiers remain available for compatibility routing. Local account identities remain authoritative authentication principals. Campaign role, profile tier, platform staff role, and workspace membership are independent checks.

| Current persisted data | Authority after explicit migration | Legacy-write behavior |
| --- | --- | --- |
| AC, proficiency, maximum resources and similar calculated values | Projection from bases, choices, grants and effects; manual overrides are explicit inputs | Translate to an authorized override command or reject with `LEGACY_FIELD_READ_ONLY`; never write projection columns directly |
| Current HP, charges, mana and other current resources | Runtime resource ledger | Translate to a resource adjustment under the same commit protocol |
| Ability scores | Declared base plus progression/effect contributions | Translate to base edit or explicit override according to the field contract |
| Equipment / inventory rows | Instance and ownership records, preserving quantity and custom descriptions | Translate equip, transfer, split, consume and edit commands |
| Character content/progression JSON | Imported snapshot plus recognized selections/grants | Recognized edits translate; unknown metadata stays inert and round-trips |
| Token HP copied from character | View of shared occurrence state | All HP writers invoke the same resource command |
| Token position and footprint used by mechanics | Occurrence-owned SpatialPresence | Translate placement/movement/transfer to authorized presence commands; never write token geometry as another mechanical authority |
| Overview/preparation marker coordinates and camera state | Presentation state | May remain display edits under presentation permission; cannot trigger mechanics or grant vision |
| Legacy exports | Versioned compatibility projection | Import through preview; no direct ORM mutation shortcut |

Unknown historical calculations MUST NOT be reverse-engineered as invented author intent. An unexplained total becomes a clearly labelled legacy baseline or override with an imported provenance marker. Known effects must not be applied again on top of an imported total without an explicit reconciliation. Unrecognized data remains inert metadata or a manual capability; it never becomes executable because a key happens to resemble a current schema field.

If historical linked tokens disagree on position or shared resources, the migration preview lists the conflict. An authorized campaign operator explicitly chooses the initial presence or unplaced state and resource reconciliation. The importer MUST NOT choose the last viewed scene, latest browser event, smallest token ID, or last writer as an implicit mechanical answer. Other retained tokens become reference views unless they faithfully project the selected presence. Independent creatures derived from one template remain independent occurrences.

The selected local seams are `vtt/characters/routes.py` for direct field writes/full `character_data` output; `vtt/models/character.py` for internally committing damage/heal helpers; `vtt/combat/service.py` for token/character HP writes; and `vtt/socket_handlers.py` plus `vtt/utils/realtime.py` for process-local deduplication/sequences. These paths MUST be included in the implementation writer inventory. Calling an internally committing helper from an engine checkpoint is prohibited. Nested JSON updates MUST persist through explicit replacement or a verified mutation-tracking contract and be checked after a fresh-session reload. Compatibility serializers MUST project current permissions before any restricted engine components are exposed.

The implementation handoff records every writer and caller affecting migrated fields, including jobs, imports, operator tools, model callbacks, and legacy endpoints. Each maps to a semantic command, remains sole authority in LEGACY/SHADOW, or is disabled for ENGINE records. Process-local caches may optimize transport, but cannot own engine receipt identity, scope sequence, authority, or leases. The declared Python/Flask/SQLAlchemy stack and default SQLite test configuration are integration facts, not evidence of deployed database isolation or multi-worker correctness.

Migration states are `LEGACY`, `SHADOW`, `FROZEN_FOR_CUTOVER`, `ENGINE`, and `ROLLBACK_REVIEW`. In LEGACY/SHADOW the legacy writer remains sole authority; shadow evaluation cannot mutate live resources. A migration preview lists every mapped field, unresolved discrepancy, and unsupported behavior. No character enters ENGINE until its declared parity checks pass or each intentional difference is explicitly approved by its authorized controller and campaign operator.

Cutover fences all writers for the affected runtime scope, captures a consistent snapshot, verifies no pending actions, commits the migration ledger and authority switch atomically, then releases the fence. Requests carry an authority epoch; a stale client receives `AUTHORITY_EPOCH_MISMATCH` plus an authorized refresh instruction. Compatibility routes are adapters, not second writers. Any denormalized display cache is labelled by authority epoch, scope state version and ExecutionLock digest.

Immediate rollback is allowed only before post-cutover engine mutations. After that, rollback requires a verified reverse migration or forward compensation plan covering every committed change. Restoring an old database snapshot over subsequent gameplay is forbidden. Unsupported reverse mappings block rollback and produce an impact report. A backup is disaster recovery evidence, not proof of lossless semantic rollback.

## 6. Canonical bytes, types, and schema evolution

Published content is UTF-8 JSON conforming to a registered schema version. Object hashing uses RFC 8785 JSON Canonicalization Scheme [R30], then SHA-256. Duplicate JSON keys, non-finite numbers, invalid Unicode, and schema-unknown fields are rejected on commit. Strings are preserved without silent Unicode normalization; identifier grammars are restricted as above. Semantically equivalent content is not necessarily byte-identical; hashes identify exact canonical bytes, not author intent.

Duplicate-key rejection occurs while decoding source bytes, before a language's ordinary object parser can discard earlier keys. A sorted-key serializer is not a substitute for JCS. Supported runtimes MUST pass common canonicalization vectors covering supplementary Unicode keys, escaping, numeric boundaries, and equivalent input serialization. Canonical JSON bytes and the domain's semantic ordering rules are distinct: JCS does not sort arrays or decide whether a collection is a set.

Mechanical numbers use exact rational values `{numerator: integer, denominator: positive integer}` in reduced form, with zero encoded as `0/1`. Wire integers are restricted to the exact safe integer range ±9,007,199,254,740,991. Intermediate arithmetic is exact and bounded by the evaluation profile; overflow or denominator zero is an error, never NaN or saturation. Units are namespaced registered identifiers with exact conversion ratios. Incompatible units cannot be added. Currency, distance, duration, and dimensionless values are distinct types.

Rounding is an explicit typed operation: `floor`, `ceil`, `truncate`, or `nearest_ties_even`. Default arithmetic does not round. A ruleset must name the rounding point for every conversion to a discrete resource, die count, or choice cardinality. Collections are either ordered sequences or mathematical sets as declared by schema; their interpretation cannot change by consumer.

Formulas are a typed AST containing literals, schema-bound reads, conditionals, boolean operators, bounded arithmetic and registered pure functions. Reads identify base or a specific earlier evaluation stage; they cannot address arbitrary object paths, permissions, credentials, filesystem/network state, wall clock, or randomness. Missing required data is an explicit unresolved value. Unknown is not false, zero, or an empty list. Rules may test `is_known`; an unresolved executable result blocks that checkpoint.

Schema registries map type ID and version to wire schema, semantic validator, allowed references, permissions, evaluator identity, migration rules, guide metadata, and renderer fallback. The registry is trusted platform/ruleset configuration. Ordinary content cannot register privileged code. Schema migrations create new bytes and record input/output digests; published revisions are never rewritten. Unsupported schema versions can be stored inert only through an explicit archival import profile.

Fixed-point evaluation is excluded from `core-safe-1`. Cycles in formula reads or stage dependencies are invalid. Supporting a fixed-point profile later requires bounded iterations, convergence criterion, tie behavior, and non-convergence fixtures. Temporal feedback is modelled as ordered state transitions, not hidden dependency cycles.

## 7. Rules primitives and deterministic evaluation

Each primitive has stable namespaced identity within a revision. Activity, Effect, Resource, Predicate, ChoiceSlot and Advancement remain separate schemas. Presentation bindings and world relationships use the same identity infrastructure without gaining mutation authority over rules state.

An Activity declares activation mode, target selector, ordered resolution windows, requirements, costs with spend windows, typed rolls, effect applications, bounded child activities, and declared outputs. Selectors execute against an authoritative snapshot within one runtime scope. They declare maximum targets and stable ordering. An activity cannot obtain more targets by following unrestricted graph links. Hidden legal targets can be resolved server-side, but only authorized output may be returned to the invoker.

Each declared cost has a stable cost ID within its activity revision and a declared checkpoint. The logical debit identity is `(actionId, checkpointId, costId, boundedOccurrenceIndex)`. A hook, UI control, adapter, or retry MUST NOT create another debit for that identity. Distinct declared costs against one pool remain distinct costs: the coordinator aggregates their amounts to validate availability and records their separate provenance. Deduplicating only by resource ID would incorrectly discard legitimate costs. Cost evaluation is pure; only checkpoint commit mutates the resource ledger.

A Resource declares unit, owner scope, maximum expression, current-value policy, spend/recovery triggers and visibility. Current amounts are ledger state, not formula side effects. For bounded resources, `0 <= current <= max` is invariant. A maximum decrease with excess current is a conflict unless the ruleset explicitly specifies a named conversion policy, such as preserving spent amount or clamping with a reported delta. An author cannot silently select that policy through an omitted field.

Predicates return true, false, or unresolved. AUTO uses permitted snapshot reads. Human predicates reference a question contract and authorized responder selector. Manual toggles have explicit scope, owner, expiry and version; they are not global booleans. A predicate cannot execute arbitrary script under the baseline. Missing evidence never authorizes an action by default.

Effect applications carry `applicationId`, source instance, source revision, originating action/grant, target, stack group, stage, priority, duration, cadence, visibility and typed changes. Definition IDs do not substitute for application IDs. Re-equipping or retrying a command cannot accidentally create another application of the same logical effect.

Numeric targets evaluate through fixed stages: base -> set -> add -> multiply -> clamp -> final rounding. Base values are immutable inputs during a single evaluation. SET candidates choose the highest numeric priority; equal highest-priority candidates with unequal values produce `EFFECT_CONFLICT`, rather than picking by arrival order. Equal-valued candidates coalesce while retaining all provenance. ADD values are summed; SUBTRACT is normalized to a negative ADD. MULTIPLY factors are multiplied. Lower bounds take the greatest bound; upper bounds take the least. An empty interval is `EFFECT_CONFLICT`. Rounding is the target schema's explicit final operator, not a per-client choice.

Example: base 10, ADD 2 and MULTIPLY 2 produces 24 under this profile regardless of serialization order. A mechanic that requires multiplication before addition must express a separate typed intermediate value or a different versioned evaluator profile; it cannot manipulate an undocumented priority to reorder stages. Cross-stat formulas name their dependency stage and must remain acyclic.

Stack policy is one of `all`, `unique_by_source`, `highest`, or `exclusive`. It is applied within an explicit stack-group ID and evaluation stage before numeric reduction. `unique_by_source` uses the source-instance-plus-feature identity declared by the ruleset; repeated applications from that same key coalesce only if their mechanical payloads match, otherwise conflict. `highest` requires comparable same-unit scalar values and retains all equal winning provenance. `exclusive` rejects multiple active distinct sources unless a prior explicit choice selects one. Priority does not grant permission to ignore a stack conflict.

Set-valued additions/removals are sourced membership contributions, not destructive array edits. Removing one contribution does not remove another source's grant. APPEND applies only to ordered presentation sequences with explicit order keys, never to a mechanical set. GRANT is the grant-ledger operation defined in §13. UPGRADE and DOWNGRADE from v1.0 are removed as ambiguous core operators; a ruleset must express their exact semantics through the operators above or register a separately conformed evaluator.

Incremental evaluation is an optimization. Its result, unresolved-state markers and provenance MUST equal a full recomputation for the same input snapshot, lock and evaluation profile. Implementations must compare the two in conformance fixtures. A broad dependency invalidation may legitimately recalculate an entire actor; the system must still meet the declared workload budget or report that the workload is unsupported.

Full recomputation starts from retained bases, choices, live source contributions, and permitted overrides. It MUST NOT feed a prior projected total back into the base or create/revoke persistent grants as a side effect. Repeated evaluation of the same snapshot is observationally idempotent. Transforming, re-equipping, or reloading an occurrence does not reapply its existing contribution. An incremental cache entry binds the input dependency versions, complete lock, target stage, and evaluator identity; a miss or invalidation cannot change semantics.

Internal provenance is a typed acyclic graph with stable semantic node identities. Each contribution identifies target binding, stage, source kind, source occurrence/revision where applicable, contribution ID, and change index. Unordered contributor lists are sorted lexicographically by that tuple, using fixed stage ordinals and ASCII identifier order; absent optional source fields sort before present fields. Semantic priority still determines SET selection before this presentation order. Source identities are assigned by originating commands or definitions, never allocated by a cache or renderer. Node IDs are digests of their canonical semantic identity under the input/lock digest. Equal-valued winning sources all remain recorded.

Canonical provenance cannot depend on hash-map iteration, database row order, worker completion order, locale, or cache warmth. Explicit ordered sequences keep their declared order. Public explanations first apply current policy and permitted disclosure, then order the remaining permitted nodes; they expose neither omitted nodes nor their original indexes/counts. Internal provenance digests are not automatically public. The pinned evaluator defines a reference evaluation order and its logical work charge as specified in §18.

## 8. Runtime authority, scopes, and command admission

A RuntimeScope is a campaign's authoritative mechanical state, or a personal sandbox explicitly separate from a campaign. A live instance belongs to exactly one RuntimeScope. A character used in two campaigns has distinct runtime occurrences; the system MUST NOT allow two scopes to mutate one HP/charge pool without a separately specified cross-scope protocol. Shared personal identity and source definitions do not imply shared runtime state.

Each scope has a durable monotonically increasing `stateVersion`, `authorityEpoch`, `eventSequence`, active ExecutionLock and policy version. Drafts have their own versions. Neither process-local counters nor client clocks establish any of these values. Multiple server workers must observe the same committed order. A restarted worker cannot acquire authority by reusing an old in-memory lease; writers use durable fencing epochs.

Every mutation passes authentication, current usable-account status, scope membership, operation capability, resource relationship, schema validation, semantic validation, expected-version checks, execution-profile checks, and transactional revalidation. Principal identity is derived from authenticated server context. A wire `actorInstanceId` selects the game actor, not the authenticated person. Any delegated service identity is explicit and restricted to its declared capabilities.

Commands carry command ID, idempotency key, expected scope/draft version, authority epoch, lock digest where mechanical, and a typed payload. All reads used to authorize, validate costs, select targets or compute changes belong to the transaction's consistency boundary. The baseline guarantees serializable observable outcomes within a scope; implementations may use serializable transactions or equivalent locking/version checks. Per-row optimistic checks without a scope-wide consistency argument are insufficient.

Idempotency identity is `(authenticated principal, mutation scope, idempotency key)`. The canonical request digest excludes transport-only metadata and includes operation, payload, relevant expected versions and lock. Reusing a key with another digest returns `IDEMPOTENCY_KEY_REUSE` without executing. Admission atomically claims one operation identity. A committed checkpoint receipt and every mechanical change it reports commit together; a separately persisted pending admission or attempt record is not evidence of mechanical success. In-flight duplicates return the same operation ID/status. Terminal duplicates return the original receipt filtered under current read permissions; loss of access does not replay an old secret response.

For an existing identity, receipt lookup and digest matching occur before new-execution expected-version and gate checks. A legitimate retry can carry its original now-stale expected version and still recover its outcome. It cannot mutate anything under a stale authority epoch or bypass current read permissions. The authenticated principal and scope namespace must still be safely established; inaccessible historical receipts return only the allowed inaccessible/status representation. A first accepted operation binds one durable identity; concurrent claims are resolved atomically by a uniqueness constraint or an equivalent proven mechanism. Distinct command IDs with the same matching idempotency identity resolve to the original operation.

The application checkpoint coordinator owns one complete unit of work. Framework request/session cleanup, ORM callbacks, domain methods, and transport handlers MUST NOT commit or roll back fragments of it. The consistency proof covers the scope gate, all resource/target reads, scene geometry/presence versions, current account and policy dependencies, receipt, and full mutation set. Policy changes and worker fences must participate in a serial order or an equivalent validated commit fence. A pre-transaction permission check alone is insufficient. Database and deployment choices remain open, but this proof and tests on the selected backend are mandatory before implementation acceptance.

Durable deduplication keys and outcome digests are retained for the scope's supported lifetime, including restored backups. Compacted histories retain non-executable tombstones sufficient to reject re-execution. Deleting a scope makes its mutation namespace permanently unavailable. Rate limits and size limits also apply to invalid or duplicate traffic, but do not cause a previously committed command to execute again. Transport ACK means accepted receipt only; success means the receipt identifies a committed checkpoint.

## 9. Activity state machine, atomic checkpoints, and randomness

Human decisions and reactions can separate observable steps of one activity. The protocol therefore promises atomic **checkpoints**, not an impossible database transaction held open across a person's response. Every checkpoint is all-or-nothing for its costs, state changes, grants, cadence consumption, domain events, audit linkage, receipt and notification-outbox records. Earlier visible checkpoints are durable history and are never silently rolled back because a later decision is cancelled.

The action states are `PROPOSED`, `WAITING_PRECOMMIT`, `ACTIVE`, `WAITING_DECISION`, `SUSPENDED`, `COMPLETED`, `CANCELLED`, and `FAILED_PRECOMMIT`. Allowed transitions are: PROPOSED to WAITING_PRECOMMIT, ACTIVE, CANCELLED or FAILED_PRECOMMIT; WAITING_PRECOMMIT to ACTIVE, CANCELLED or FAILED_PRECOMMIT; ACTIVE to WAITING_DECISION, SUSPENDED or COMPLETED; WAITING_DECISION to ACTIVE or SUSPENDED; SUSPENDED to ACTIVE or an operator-finalized COMPLETED outcome. CANCELLED is allowed only before the first authoritative activation/roll checkpoint, including explicit cancellation or expiry of a PROPOSED operation. Once a roll or cost is committed, stopping the action is a recorded resolution or compensation, not deletion or precommit cancellation.

A scope admits at most one active root mechanical action. Before activation, interviews/proposals may coexist but do not reserve authority. Activation atomically acquires the durable scope gate and revalidates the full read set. During an active root, only declared reaction/child actions, its resolution commands, and authorized operator interventions may mutate mechanical state. Unrelated mechanical commands receive `SCOPE_BUSY` and may be retried with a new command after refresh; read/chat/draft authoring continue. The gate covers presence placement/movement/transfer/unplacement, mechanical scene geometry, rests, progression, equipment changes and package updates. Camera movement and reference-marker layout remain nonmechanical presentation edits. This deliberately favors correctness over simultaneous mechanical editing; a future concurrency profile requires separate proof.

The scope gate is a durable state record, not an expiring lock that silently releases an unfinished action. Worker execution leases may expire and be reassigned with a higher fencing epoch; reassignment resumes the same action/receipts. An expired worker cannot commit with its old fence. Admission limits bound stored precommit proposals per principal and scope so an author cannot exhaust persistence by opening unanswered proposals.

Activities declare a finite ordered window sequence using registered window IDs such as declare, before-roll, after-roll, before-apply, after-apply and finish. Requirements, costs and effects name their checkpoint/window explicitly. There are no default spend/refund points. An activity missing that metadata is not runtime-ready. A cost due at activation is spent at activation; a cost due after a confirmed hit is spent in that hit-resolution checkpoint. Failed checks and invalid targets do not decide refunds implicitly; the ruleset's declared outcome branch does.

The server obtains random input and records the exact dice/raw outcomes, algorithm identity, checkpoint ID and relevant rules snapshot before exposing any result to a client. Dice are stateful roll operations, never formula reads. Sampling and its durable receipt must make any retry return the same recorded result. Uncommitted random draws are never broadcast. Clients cannot provide authoritative random results except through a separately labelled, permissioned manual-roll command. Hidden future draws are not returned in seeds or debug data. Replay consumes recorded outcomes and performs no new draws.

Within a checkpoint: verify authority and gate ownership; load a consistent state; recheck permissions and prior decisions; validate all costs and target versions; evaluate bounded pure calculations; obtain or reuse checkpoint randomness; prepare the complete mutation set; then commit changes, results, receipt, events and outbox together. No committed-result notification is sent before commit. Delivery from the outbox is at least once; consumer deduplication and snapshot recovery provide one application of each event, rather than claiming exactly-once network delivery.

Failure before a checkpoint commits changes nothing from that checkpoint. Failure after commit returns its durable outcome on retry. If a later checkpoint cannot complete because of a conflict, evaluator fault or budget violation, the action becomes SUSPENDED. Earlier checkpoints remain effective. An operator can resume from the same recorded inputs after a compatible operational recovery, or issue a recorded manual resolution/compensation. Changing evaluator/content mid-action is forbidden; if the locked evaluator is unavailable, manual resolution is explicit and provenance marks the loss of automated completion.

A database-reported abort and an ambiguous commit response are different outcomes. An ambiguous result MUST be resolved through the durable operation/checkpoint identity before re-execution. Retry of a known uncommitted attempt reruns the entire transactional read/validation set; it does not replace the caller's expected versions, mint another command identity, or replay already committed checkpoints. Transient contention is an operational interruption, not `BUDGET_EXCEEDED` or an invented game-rule failure. Automatic retry limits are specified in §18.

Operational admission/attempt records may survive a failed transaction so work remains bounded; they do not spend resources, disclose randomness, advance mechanical state, or establish a game outcome. An uncommitted draw never shown to a client is not a committed roll. Once a draw is durably bound to a committed checkpoint, every recovery and replay uses it. Implementations that reserve random input before mechanical commit must bind the reservation to the same checkpoint and prevent unauthorized reading, replacement, or a second committed outcome. No preparatory record permits publishing before the complete checkpoint commits.

On-hit child activities belong to the parent action tree, identify the committed hit they modify, and consume their own declared cost checkpoint. A flame charge is not consumed merely because an attack was proposed. A child cannot manufacture a new attack result or retry its parent. A cancelled optional child preserves the parent's committed roll and other costs. Scope gate release occurs only after a terminal root outcome is committed.

## 10. Human decisions, reactions, deadlines, and event delivery

A PendingDecision contains action/checkpoint ID, stable question ID/version, response schema digest, context digest, prompt version, eligible responder rule, target references, creation time, deadline, semantic decision window and resolution policy. The context digest binds the resolved snapshot, lock, targets, required resources, policy version, and mechanical facts relevant to the question. User-visible text is permission-filtered and is not the decision's identity.

For a spatial decision, the bound facts include source/target presence versions, scene geometry versions, coordinate frames, and the geometry-profile digest. Changing the visible browser scene or a reference marker does not change those facts. An authorized mechanical move/transfer or geometry edit inside the current frame invalidates affected unanswered prompts. A client cannot answer against another token's display coordinates for the same occurrence.

A response carries decision ID, expected decision version, context digest, idempotency key and typed answer. The server determines the responder from authentication. A response is accepted once, only from an eligible current principal, for an open unexpired decision in the active frame. Matching retries return the same receipt. Stale responses return `DECISION_STALE`; a fresh prompt is required after relevant context changes. Changing a prerequisite answer invalidates dependent unanswered decisions; accepted postcommit outcomes are not edited retroactively.

The baseline permits one sequentially offered responder per reaction slot. Candidate ordering is: ruleset window priority descending; canonical encounter initiative order if applicable; stable actor-instance ID as final tie-breaker. Priority tie-breaking determines who is offered a decision, never chooses a creative answer. A slot states whether acceptance consumes the slot or whether remaining candidates are offered in order. Reaction nesting is depth-first and resumes the suspended parent window after the child terminates. Declared re-entrancy keys and the budgets in §18 prevent self-triggered or mutual loops.

Human response timeout is 120 seconds by default, selected visibly by campaign policy within 30–600 seconds and copied into the decision at creation. At its persisted deadline, a declared optional reaction expires as a recorded decline only where the ruleset explicitly defines that result. Expiry of a mandatory decision in an active frame makes the frame SUSPENDED and notifies authorized operators; unknown never becomes false or spends resources automatically. Precommit proposals expire as CANCELLED without cost. The 600-second maximum is a cap on a decision's waiting interval, not a grace period extending a shorter deadline. Suspension does not release the gate or invent an outcome. Operators can reassign an eligible adjudicator or finish manually; their intervention is auditable. This availability tradeoff is intentional and limited to that runtime scope.

Deadlines are evaluated at response-acceptance commit using server time, never a client timestamp. Persisted UTC deadlines and a nondecreasing scope time watermark prevent clock rollback/restart from reopening an expired decision. A forward-clock anomaly can suspend a decision for operator review; it must not invent a mandatory answer. Reissuing a prompt creates a new decision version and explicit deadline; it never makes the old response valid again. Admission is limited to 20 open precommit proposals per principal and 100 per scope; proposals expire after the configured precommit deadline.

Membership/permission revocation is never delayed by the mechanical gate. It updates the policy epoch, invalidates affected decisions/subscriptions, and can suspend the action. A revoked participant receives no new privileged details. An operator override that changes mechanical context is a checkpoint inside the current frame and invalidates dependent prompts; it does not masquerade as an unrelated concurrent write.

Internal domain events carry immutable event ID, scope sequence, action/checkpoint/causation IDs, state version, lock digest and audience policy metadata. Transport serializers project the event for each currently authorized audience. Clients deduplicate by permitted event ID and use an audience-bound delivery cursor for recovery; internal sequence gaps and private causation IDs are not exposed as the public event stream. A stale/invalid cursor triggers a permitted snapshot. A reconnect negotiates an authority epoch and supported schema version before applying deltas. Old epochs force a refresh.

The outbox retries until delivery acknowledgement or an operator-visible dead-letter condition. Delivery failure never rolls back committed game state. Consumers cannot invoke a mutating action solely because an untrusted client repeated an event; downstream rules triggers are scheduled from durable domain events under the action protocol. Any eventual jobs that mutate mechanics must reacquire normal scope authority.

## 11. Time, duration, cadence, and event causality

Mechanical clocks are ruleset-declared logical domains. The platform provides ordered event/tick identities, not hardcoded D&D rest semantics. D&D-specific short rest, long rest, dawn, turn and round are namespaced events and counters in its ruleset. Wall-clock deadlines govern UI waiting and operational leases only; they do not advance game-world time.

An encounter has a stable encounter ID and a monotonically increasing turn-occurrence ID. Reordering initiative changes future order but never renumbers committed turn occurrences. Round identity is a separate counter advanced by a committed ruleset event. Each start/end boundary is a durable event with a unique identity. Repeated transport delivery cannot expire an effect or restore a resource twice.

Duration is either explicit logical ticks with a clock/anchor and start/end boundary, an event matcher with an occurrence count, or permanent. The duration begins at its declared application checkpoint. To avoid off-by-one interpretation, the first counted expiry boundary is strictly after the application event in scope order. A ruleset needing same-boundary expiry declares an explicit window-local duration instead. An expired source or removed target produces the declared terminal policy; it does not leave a timer attached to a reused ID.

Cadence consists of bucket selector, limit and consumption window. Bucket selectors include each-turn-occurrence, source-turn-interval, round-occurrence, encounter, next-matching-action and next-matching-roll. Source-turn-interval begins at one source turn start and ends before its next start; each-turn-occurrence permits a distinct bucket on each actor's turn. The text “once per turn” alone is invalid executable content. Outside a matching encounter/clock, a cadence must specify a supported fallback or resolve manually.

Usage identity is `(application or shared-feature key, optional target InstanceRef, bucket ID)` within the owning RuntimeScope. `perTarget=true` requires the full target InstanceRef; `perTarget=false` uses one shared non-target bucket. A token, definition, display name, or scene ID MUST NOT substitute for the target occurrence. All activities sharing that feature key consume the same ledger. Consumption and its affected roll/effect commit in one checkpoint. Rejecting or retrying a command cannot increment the ledger twice. A miss consumes cadence only if the ruleset assigns consumption to an attempted action rather than a successful application. Moving between scenes, changing a view, or unplacing an occurrence does not reset its bucket or logical turn identity.

Recovery is a resource command caused by one named logical event and deduplicated by resource, rule and event ID. Advancing world time across several dawns emits the declared number of recovery occurrences or an explicitly specified coalesced recovery event. Pausing a session never infers a rest. Combat rewind is an administrative branch/compensation; it does not decrement event IDs or erase usage history.

## 12. Execution locks, updates, retention, and reproducibility

An ExecutionLock records exact package versions and hashes; every transitive definition revision; ruleset ID/version/digest; schema registry bundle; formula/effect evaluator version; deterministic configuration and unit tables; extension runtime identity if any; and immutable referenced assets needed for the declared execution profile. Compatible version ranges are resolved only when creating a new lock. Execution never resolves a floating range on demand.

The v1.2 lock also records the contract version and an exact geometry-profile artifact or an explicit null when spatial automation is unavailable. The evaluator/configuration closure includes canonical provenance ordering and logical fuel semantics. Every placed automated presence must use the geometry profile in its scope's active lock. Scene geometry is versioned runtime input; it is not a floating package dependency. Updating a geometry profile requires the same quiescent migration and affected-presence reconciliation as other mechanical updates.

The registry rejects missing dependencies, ambiguous identity, digest mismatch, incompatible engines and forbidden dependency cycles before a lock becomes usable. Cyclic semantic world links can be valid; package-install dependency cycles and evaluator cycles are distinct checks. Content can extend another package only through declared typed extension points; no implicit path replacement or monkey patching is permitted.

Reproduction guarantees are separate: **mechanical replay** reproduces state/provenance from a supported snapshot and recorded outcomes under the exact lock; **semantic rendering** reproduces declared values and structure under a specified renderer; **byte-identical publication** requires retention of the rendered artifact itself and its digest. A renderer compatible range guarantees neither identical pagination nor identical bytes. Published artifacts pin exact renderer/theme/font/asset versions, locale and input projection digest; the exported artifact is retained when exact reproduction is promised.

Update workflow is preview -> impact analysis -> explicit campaign approval -> quiescent migration -> postcondition verification -> activation. The preview contains old/new locks, semantic diffs, affected instances, overridden paths, changed choices, current resource reconciliation, active effects, and unsupported migrations. Campaign channels may notify automatically, but mechanical updates never activate silently or during an active action. Text-only updates remain new revisions and cannot bypass visibility/rights checks.

Instance changes use a three-way comparison: old source revision, current instance overlay, new source revision. Overlapping incompatible changes are conflicts. Non-conflicting presentation changes may merge under declared policy. Renamed paths require explicit migration maps. Lossy migrations require an exact loss report and explicit selection; automatic semantic-version bumps are advisory metadata, not permission to migrate.

For current=2 and new max=1, an unspecified resource conversion blocks activation. A named, approved clamp records delta=-1 and its reason; a preserve-spent policy computes from the documented old maximum. Neither is silently inferred. Removing active effects or grants likewise requires explicit migration semantics.

Published bytes and lock components are retained while supported live instances or replay promises depend on them. An author withdrawing a listing removes discovery, not silently the referenced bytes. Security quarantine or rights restrictions may make continued execution unavailable: affected scopes fail closed for that content, receive an impact report, and can migrate or use explicitly authorized manual play. The platform does not promise perpetual execution of prohibited content. A restricted evaluator is never run solely to satisfy a pin.

Rollback after intervening runtime mutations requires a reverse migration over current state, not restoration of stale state. A successful update journal records prior lock, migration version, before/after digests, policy decision, resource conversions and acceptance results. Backup/restore must include deduplication tombstones, random outcomes, pending decisions, locks, outbox and policy epochs at a consistent checkpoint. Replaying an outbox after restore is safe because event IDs remain stable.

## 13. Choices, progression, grant multiplicity, and undo

A ChoiceSlot specifies trigger, min/max cardinality, distinctness key, allowed reference kinds/packages, filters, prerequisites, replacement policy and visibility. Options are evaluated against the campaign's lock, entitlements and current selections. Prerequisite recursion must be acyclic; a circular eligibility chain is an invalid definition. Failure to find enough eligible distinct options blocks completion with a specific diagnostic, not a random fallback.

Grant records have a unique grant ID and source occurrence: class-track/level/advancement, selected option, item application, or operator command. They reference the granted capability and its merge identity. Multiple sources of one proficiency produce one effective proficiency with multiple live contributions. Revoking one source removes only its grant record. Stackable items instead create separate occurrence IDs. Rulesets must declare which behavior a grant has; identical display names do not establish identity.

Character projection evaluates retained base decisions, live grants, permitted overrides, equipment state and runtime effects. It never creates, revokes, or transfers persistent grant/item records merely because a sheet or cache was rebuilt. Grant lifecycle changes are explicit semantic commands/checkpoint effects. Each class/progression track has an independent identity. Level simulation runs in an isolated ephemeral scope with copied choices and deterministic fixture inputs; it cannot spend or grant into the live character. Future-level planning stores provisional choices separately and revalidates them when the real level is attained.

Removing a level is a semantic command with an impact preview. It revokes that level's contributions, invalidates dependent selections, recomputes maxima and reports conflicts. A feat granted independently survives. A granted item that was transferred, consumed, transformed or used in later state cannot be blindly deleted or recreated. The operation must present a ruleset-supported compensation or require operator adjudication. No such unresolved conflict is auto-approved.

Draft undo restores prior draft state through a new versioned command and preserves the decision log. It does not decrement versions or erase audit history. Runtime undo distinguishes reversible local changes from compensating actions. A reversal requires proof that affected values and dependencies have not changed since the checkpoint; otherwise it returns `UNDO_CONFLICT` with an authorized impact report. Published roll information cannot be made unknown again, and a reversal cannot grant a fresh random draw for the same action.

Retcons create a named branch of history or explicit compensation in the current branch. They preserve the original event chain. Transfer ownership, action cost, condition expiration and resource recovery remain sourced events so the operator can understand what a compensation changes. The UI must not label “restore this number” as “undo the entire action.”

## 14. Authorization, information flow, and View As

Security policy is a versioned mutable overlay separate from immutable content. Retaining a revision for replay does not freeze a person's access forever. Every response and cached delivery uses current account status, membership, entitlement and policy. Content carries visibility intentions and required capabilities, but importing those declarations cannot create actual grants or ownership.

Policies grant named operations to explicit principal/role selectors and may restrict child fields, components, relationships, effects, decisions and representations. Default is deny. Container and child policy restrictions are intersected; a child may narrow access but cannot widen a parent's audience without an explicit authorized publication/reveal operation. Explicit denies prevail over grants. Owner-private data requires the owner's grant; GM/admin viewing capability does not automatically bypass it. Platform emergency access, if introduced, requires a separately specified audited policy and is excluded from ordinary View As.

| Operation | Minimum required authority; additional object policy still applies |
| --- | --- |
| Read projection / explanation / search | Usable account or explicit public publication; allowed scope and field read |
| Edit private draft | Owner or delegated draft-editor grant |
| Publish package | Publisher grant plus content rights and validation gate |
| Deploy/update campaign content | Campaign operator and deploy capability; player authorship alone is insufficient |
| Invoke actor activity | Current control of that occurrence, activity invoke permission and action requirements |
| Resolve human predicate | Current responder eligibility for that exact PendingDecision |
| Change a resource manually | Explicit control/adjust permission; shared or other-player resources are not implied |
| Place / unplace occurrence | Explicit campaign operator presence capability plus occurrence and scene policy |
| Move occurrence | Current occurrence control plus the registered movement rule's permission, costs and bounds |
| Transfer occurrence between scenes | Explicit operator transfer capability or a declared authorized transition activity; both scenes remain in one scope |
| Edit reference-marker layout | Presentation edit permission only; never grants spatial mutation or perception |
| Transfer ownership / reveal secret / compensate action | Explicit corresponding permission; auditable reason |
| Export | Read plus export/redistribution permission for every included object and dependency |
| Execute formula over restricted fields | Server-only engine-compute grant within the declared action; never arbitrary client access |

A server evaluator may read restricted mechanical inputs only where their owner/policy authorizes that use. Derived outputs inherit the intersection of source audiences. A ruleset may declare a reviewed declassification rule for a particular outcome, such as exposing resolved damage while hiding a trap's identity. That rule must name permitted output fields, input categories and audience; an ordinary package author cannot declassify data by marking an output public. Publishing an exact final number can reveal information about its hidden inputs; that is a deliberate gameplay disclosure under the rule, not a guarantee of mathematical non-inference.

Explanations and provenance undergo the same policy projection. They may reveal permitted calculation contributions but never hidden names, source IDs, decision text, URLs or exact counts of omitted sources. The public explanation may state generically that some calculation detail is unavailable when that disclosure is permitted. It must not claim a complete proof while withholding inputs. Without an allowed declassification rule, the derived value itself is withheld or the action requires authorized manual adjudication.

The output boundary covers reads, command receipts, validation errors, conflict diffs, autocomplete, search/ranking, counts, graph layouts, WebSocket events, snapshots, notifications, PDFs, embeds, imports/exports, simulation traces, audit views and operational telemetry. Unknown and inaccessible object references produce the same public not-found representation. Internal diagnostics retain a protected reason code. Search authorization precedes candidate ranking and aggregation; inaccessible candidates never affect returned totals or suggestions under the baseline.

The baseline intentionally discloses scope-level state-version changes and busy/suspended status to authorized mechanical participants so they can coordinate actions. It does not promise to hide whether any campaign mutation occurred. This narrow operational-metadata disclosure does not authorize source names, hidden object counts, private event IDs or exact omitted-contribution counts. A campaign requiring concealment even of mutation activity needs a separately reviewed transport/concurrency profile; it cannot claim that stronger guarantee under this baseline.

Cache identity includes principal/audience-equivalence class, scope, policy epoch, entitlement epoch, input state/version, ExecutionLock and representation version. Shared-cache optimization requires proof of equivalent permissions. On revocation, subscriptions are invalidated and subsequent messages re-authorized; cached responses under old epochs are not reused. The contract cannot revoke screenshots, downloaded files or information already disclosed. Public immutable publications therefore require deliberate authorization before release; future removal disables hosting/discovery, not retroactive recall.

View As is a read-only projection computed as the intersection of the initiating operator's permitted view and the selected member's permitted view, with owner-private exceptions applied. It never grants either person's additional private rights to the other. Commands, exports with greater authority, tokens and cookies cannot be impersonated through this mode. The session identifies the operator and viewed member separately, expires after 15 minutes by default, and logs entry/exit. Any actual delegated mutation is a distinct normal command, not a View As side effect.

The legacy full `character_data` serializer cannot serve migrated field-policy data. The compatibility endpoint must call the same projection policy as new endpoints before exposing new components. Restricted metadata cannot be hidden only in the frontend. Existing role-scoped socket rooms remain a delivery mechanism; they do not substitute for field projection.

Presence, destination scene, travel history, region membership, and hidden targets are policy-governed facts. A permission to read a world-map marker does not reveal the occurrence's current scene/coordinates. Reference views cannot grant player line of sight or fog discovery. Live vision calculations use authoritative presence and current scene/read/control policy under the supported geometry profile. Player and operator previews have different permissions and cache identities. Marker deletion, display hiding, alias changes, and selected-browser-scene changes cannot grant mechanical stealth or alter another audience's rights.

## 15. Guided compiler and authoring decisions

Guided mode is a deterministic schema-and-constraint interview. Structured mode organizes the same editable concepts non-linearly. Advanced mode exposes typed canonical values, references, validation, diffs and provenance. None can bypass server invariants. A registered schema's authoring metadata includes stable question IDs/version, accepted answer schema, display/help localization, required/visible conditions, dependency links, priority, adapter identity and invalidation rules. Answer adapters are registered pure transformations with versioned conformance fixtures, not content-supplied executable code.

Before natural-language import is implemented, the Guided entry point offers domain intents such as create equipment, create actor, add activity, change a value, add choice, and describe a place. Those selections are explicit user decisions. Free text can always be retained as prose; unrecognized text does not automatically populate mechanical fields. Controlled aliases may map an exact normalized term to one concept only when registered as semantically equivalent for that locale and ruleset. Mechanical ambiguities always remain proposals requiring selection.

Question selection is deterministic: compute the current constraint graph; suppress irrelevant nodes; identify unresolved required decisions for the user's selected completion profile; choose the highest registered priority, then schema order, then stable question ID. No answer is guessed merely to make progress. Constraints must not depend cyclically on unanswered decisions without an explicit discriminating question that breaks the cycle. A compiler cycle or lack of a valid next question returns `GUIDE_DEAD_END` with an authorized diagnostic and Structured-mode recovery, not an endless interview.

Every user answer is an atomic draft command carrying expected draft version. It records question/version, typed answer, author, resulting canonical mutations and invalidated descendants. Changing an earlier answer preserves superseded history but marks dependent answers as stale; their effects are removed from the active draft or surfaced as explicit conflicts, never silently retained. Switching modes preserves the graph and recomputes unresolved constraints. Stable answers are reapplied across schema upgrades only through a reviewed migration; migration cannot invent an answer.

An author can stop at any time. Drafts preserve incomplete values and unresolved questions. Preview marks unresolved values without converting them to zero. The user can skip optional questions. A required creative value—damage, duration, target count, range, rarity, recharge, scaling, cost, or equivalent—has no implicit default. Explicitly choosing a preset imports its stated values as user-approved source decisions and displays them before commit. System-generated IDs or technical sorting choices may default because they do not change intended game behavior.

For “a sword that bursts into flames three times per day,” the first mechanical question is what the flames do: visual/light only, additional damage, separate burst, transformation, or another supported/manual behavior. Damage amount is asked only if damage was selected. The author separately chooses timing, duration, cost and what “day” means. Cosmetic behavior does not acquire a damage primitive. An unsupported concept can remain prose/manual or require a registered extension; it cannot become an opaque executable escape hatch.

AI/prose import is an optional proposal producer with confidence and source-span annotations. It MUST show proposed changes and unresolved ambiguity before committing them. Accepting one proposal does not authorize unrelated generated mechanics. Creative Assist is separately enabled for the specific session/task and its proposals are marked as generated. The same command validators and no-hidden-default tests apply after proposal acceptance.

Publication and automation quality are independent axes:

| Mechanical quality | Meaning |
| --- | --- |
| Lore-only | Identity and allowed world/presentation fields are valid; no executable mechanics promised |
| Sheet-ready | Manual mechanics render honestly; required references and fields for those views are valid |
| Runtime-ready | Each enabled activity has valid lifecycle, costs, windows and authorized resolvers; human decisions may remain |
| Automation-complete | Every enabled mechanical branch can resolve without ad hoc adjudication for the declared capability/workload envelope; no unsupported executable prose |

Publication requires rights/source metadata, policy, references, renderer safety, declared mechanical quality and packaging validation. A lore-only package can be published. An automatically executable package can be private. A human-resolved predicate is compatible with Runtime-ready, but not with Automation-complete if human adjudication is necessary. A normal user choice between valid actions is not unresolved rule interpretation.

## 16. World graph, NPCs, settlements and spatial behavior

World entities begin with a title and paragraph. Optional typed components can add creature mechanics, population, government, organization, shop, faction, timeline or spatial metadata. Adding/removing a component preserves identity but validates every dependent relationship, view and mechanic. Component removal cannot silently orphan live actions, choice references or secrets; it returns an impact preview and either a supported migration or a conflict.

Relationships have their own IDs, scope, typed endpoints, attributes, validity interval, policy and version. A relationship's existence is visible only when its own policy and endpoint-disclosure rules permit it. Inaccessible endpoints are omitted by default; anonymous placeholders require an explicit allowed-existence disclosure. Inverse views are computed from one canonical edge, not separately edited duplicate edges. Cardinality constraints are transactional across competing edits.

Mentions store stable typed references plus optional author-authored display alias. Renaming the referenced entity changes its normal displayed name without altering identity; an explicit alias remains the alias. Unresolved mentions remain draft tokens until linked or created through an authorized command. Autocomplete searches accessible entities only. Creating an inline placeholder creates a scoped WorldEntity, not a globally shared publisher definition.

Transclusion is permission-checked at render time, bounded by depth and expansion limits, and cycle-detected. A public page cannot reveal a private paragraph by embedding it. Exported static pages include only the export principal's explicitly publishable projection; future permission changes do not retroactively alter already downloaded artifacts.

Settlement structure links districts, sites, factions, residents, routes, shops and encounters. “Small port town” may select a supported section to discuss but MUST NOT fabricate population, government or economy. Relationship maps, family trees, organization charts and settlement views derive from authorized canonical data. Layout caches are scoped by audience; hidden nodes must not affect visible labels or counts. Any intentionally revealed unknown relationship is a separate disclosed fact.

### 16.1 Authoritative presence and representations

Within a RuntimeScope, an EntityInstance MUST have at most one authoritative spatial presence. The occurrence owns a persistent SpatialPresence record with a monotonically increasing version and a placement tagged `unplaced` or `placed`. A placed value identifies one RuntimeScene, coordinate frame, exact 2D position, occupied footprint, and locked geometry-profile digest. An unplaced value has no mechanical coordinates. Presence versions do not reset when unplaced, re-placed, restored, or displayed through another token.

A RuntimeScene belongs to exactly one RuntimeScope. Its registered coordinate frame declares units, exact scale, and any supported transforms. Its mechanical geometry and access policy are versioned inputs to commands. Two scenes are not assumed to share coordinates because their map images overlap or have the same filename. Cross-scene distance, sight, auras, and attacks are unsupported in the baseline; a later capability must define the connection explicitly.

A representation is either a **live view**, whose mechanical scene/position/footprint is projected from the occurrence's presence, or a **reference view**, whose display layout is independent and nonmechanical. Multiple live views of the same presence may exist, but each shows the same authoritative location in a compatible coordinate frame and contributes no additional physical body. A representation at another scene or conflicting position is a reference view. Changing a display's requested view mode cannot relocate or place an occurrence; the server validates its binding and derives any live coordinates from the existing presence. An unplaced occurrence has no live spatial view until an authorized placement commits. The UI identifies reference views to authorized users and routes attempts at mechanical manipulation to the real presence or an explicit placement/transfer workflow.

A sheet, disguise, world-map marker, prepared encounter token, hidden layer, or second browser cannot acquire authority merely by being selected, opened, moved visually, or rendered last. Reference views MUST NOT establish spatial target eligibility, occupied area, range, aura sources, region entry/exit, cadence consumption, collision, or mechanical vision. They also MUST NOT provide an alternate route to map information that the current scene/presence/policy would otherwise withhold. Operator map-preview permissions are separate read capabilities; they do not create a presence or grant player vision.

Hiding a live view is presentation behavior and does not make the creature mechanically invisible. Invisibility, footprint changes, and other mechanical state changes require the relevant rules commands. Deleting a live view removes that view only; the occurrence and presence remain. The operator can recover an authorized view of an otherwise undisplayed presence. No remaining marker is silently promoted. If the intent is to remove the creature from spatial play, use explicit unplacement or the appropriate lifecycle command.

### 16.2 Presence commands and authority

The selected wire schema includes the following commands in addition to InvokeActivity, ResolveDecision, and AdjustResource. Each uses the shared command envelope, expected scope version, authority epoch, lock digest, and idempotency identity. Each also carries a full InstanceRef and `expectedPresenceVersion`; matching a reference's scope to the envelope remains a semantic obligation.

| Command | Required payload and state | Observable semantics |
| --- | --- | --- |
| PlacePresence | Unplaced occurrence; destination SceneRef/frame/position; registered placementRuleId; reason | Derive the footprint from authorized current mechanics, validate destination and entry semantics, and place once |
| MovePresence | Placed occurrence; current SceneRef/frame; mode continuous or teleport; bounded path; registered movementRuleId | Validate path start against current presence, movement/teleport authority and costs, then execute the declared windows |
| TransferPresence | Placed occurrence; destination in another scene of the same scope; registered transitionRuleId; reason | Commit departure/arrival location and membership changes together at the relocation checkpoint |
| UnplacePresence | Placed occurrence; registered transitionRuleId; reason | Explicitly remove spatial occupancy under declared exit semantics, preserving occurrence state and history |

Placement and unplacement require explicit campaign operator capabilities in the baseline. A controller's movement permission permits only supported movements under the named locked rule; it does not authorize arbitrary teleportation. A transfer requires an operator transfer capability or an actor activity that expressly authorizes that scene transition. Internal child movement uses the current action frame's validated authority. An unrelated wire command cannot enter an active frame by omitting its frame binding; it receives SCOPE_BUSY. Registered operator interventions identify the current frame and invalidate affected prompts through the normal decision protocol.

The client does not supply authoritative footprint, geometry-profile identity, state versions to install, conditions to clear, or vision grants. The server derives these from the snapshot and lock. All scene, frame, profile, presence, and movement prerequisites are checked again at commit. Invalid/inaccessible destinations follow §14's disclosure rules; known accessible conflicts use PRESENCE_VERSION_CONFLICT, PRESENCE_STATE_CONFLICT, or SPATIAL_CONTEXT_REQUIRED as appropriate. UI selection is never an authorization input.

Continuous movement has a path of 2–256 exact 2D points in the current frame; the first equals the committed starting position. Teleport has exactly two points, start and destination, and never traverses intermediate regions. Scene transfer uses a destination coordinate in its destination frame and no fictitious path between unrelated frames. Footprint changes through a transformation use the same occupancy-reconciliation boundary and increment presence version; changing icon scale alone does not change occupied geometry.

### 16.3 Checkpoints, transitions, and geometry

All mechanical presence changes use the scope gate and checkpoint protocol. A scene transfer atomically replaces the occurrence's one placed location; no committed state places it in both scenes or briefly drops its state into a fresh occurrence. Its relocation checkpoint commits the new presence version, old/new region memberships, immediate declared spatial changes, receipt, events, audit linkage, and outbox together. A failed precommit transfer leaves the old presence intact. A committed transfer recovered after response loss is not repeated.

Registered spatial rules declare pre-departure and post-arrival windows, costs, region eligibility, and any exit/entry behavior. If a mandatory decision is required before relocation, the frame waits while the old location remains authoritative. Subsequent reactions can suspend the frame after relocation; the committed location is not rolled back merely because later work waits or fails. A continuous path whose mechanics can halt movement must declare supported intermediate movement checkpoints and their ordering; the remaining path is not committed ahead of the interruption. An unsupported movement/interrupt combination fails closed or is resolved manually with recorded authority.

The baseline geometry profile supports 2D circles and simple polygons, exact rational coordinates, and at most 64 vertices per polygon footprint. Polygon closure is implicit; vertices do not repeat the first point. Polygons must have nonzero area and no self-intersections; circle radii are strictly positive. Footprints use local offsets from the presence position in its frame units. Touching counts as intersection. Exact predicates avoid floating-point epsilon choices. Intersection ordering need not persist an intersection point as a presence position. If a rule requires stopping at a point not representable in the declared coordinate type, a separately specified exact placement or explicit rounding policy is required; the engine must not introduce an implicit approximation. Elevated/3D visibility, falling physics, and other height-dependent automation require a separately versioned geometry capability; the 2D profile does not invent those semantics.

A placed footprint intersects a region when their geometry intersects. Committed continuous movement emits crossed boundaries in increasing path parameter, with equal-parameter ties ordered by region ID. Teleport emits exits for old-only memberships and entries for new-only memberships. Scene transfer emits departures in stable old-region order, then arrivals in stable new-region order; unplacement has departures only and placement has arrivals only. Events identify the occurrence and transition/checkpoint, not a display token. Multiple views cannot multiply event emission. Any profile-specific pre-window effect that changes the movement plan requires revalidation before the affected checkpoint.

Area selectors deduplicate matching live views by full InstanceRef before costs, effects, or per-target cadence are computed. Independent occurrences of one definition remain separate targets. Spatial application identity includes source application, target InstanceRef, and the declared membership/cadence identity. Auras originate only from an authoritative placed presence. Leaving an aura removes its occupancy-derived contribution according to the rule; independent timed conditions such as poison remain until their own removal/expiry event. A reference marker on the old scene cannot keep an aura active or clear a condition.

### 16.4 Unplaced play, history, and presentation

An unplaced occurrence may still be edited, use supported nonspatial mechanics, and participate in authorized manual play. A required spatial fact while unplaced is unresolved, not zero distance, an empty target set, or permission to act from any marker. Spatial automation requiring it returns SPATIAL_CONTEXT_REQUIRED or follows an explicit human adjudication contract. Unplacement is not a player shortcut out of hazards, costs, or a pending decision; it requires its stated authority and transition rule and remains subject to the scope gate.

HP, resources, grants, timed effects, action identities, and turn/cadence buckets remain with the occurrence through placement changes. A scene transfer does not end an encounter or reset a turn by itself. Any legitimate encounter transition is an explicit locked ruleset event. Presence and scene versions used by pending decisions are recorded; an authorized intervention invalidates affected unanswered decisions. Backup/replay retains presence history, movement classification, geometry-profile identity, and causal events. Animation, interpolation, camera state, and a viewer's selected scene never generate authoritative movement events.

A separate actual creature uses a separate EntityInstance even if its definition, appearance, or name is identical. A future multi-body capability must explicitly define shared/independent resources, conditions, perception, action economy, target identity, and cadence. The baseline rejects attempts to create a second authoritative presence for one occurrence. It may still render an authored multi-body concept at manual quality without pretending to automate it.

## 17. APIs, packages, imports and public extension boundaries

Read APIs expose definitions/revisions, permitted instances/projections, schema metadata, package manifests and explanations. Command APIs expose draft changes, publishing, instantiation, activity invocation, decision responses, manual adjustments, migration and compensation. Collection ordering is deterministic by declared sort key plus stable ID; pagination cursors bind the query, audience/policy epoch and snapshot. An expired cursor causes a restart rather than mixing private results from another policy snapshot.

The companion schema defines v1.2 command envelopes for InvokeActivity, ResolveDecision, AdjustResource, PlacePresence, MovePresence, TransferPresence, and UnplacePresence; selected effect/timing/reference/lock contracts; and SpatialPresence records. Feature registries add versioned payload schemas for other commands, including explicitly frame-bound operator interventions. An unknown type/version is rejected; an object-shaped `payload` is never treated as a license to accept arbitrary JSON. REST and WebSocket transports use the same semantic handlers, validation and receipts. Compatibility clients negotiate supported schemas and cannot request removal of safety fields. The schema is a selected contract set, not the entire feature registry.

The canonical request digest covers `contractVersion`, operation, scopeId, payload, expectedScopeVersion, authorityEpoch, and executionLockDigest. The authenticated principal and idempotency key identify its deduplication namespace; commandId and transport-only metadata are excluded from the request digest. Equivalent deliveries with different transport command IDs recover the original command receipt. An altered expected version, target, movement rule, or path changes the digest and cannot reuse that idempotency identity. Compatibility translation occurs before digesting and must retain one semantic identity across transports.

| Response condition | Stable code and HTTP interpretation |
| --- | --- |
| Committed checkpoint | 200/201 receipt with outcome, state version and authorized projection |
| Admitted asynchronous or pending action | 202 with operation/action ID and authorized status |
| Invalid wire syntax | 400 `SCHEMA_INVALID` |
| Inaccessible/missing target | 404 `NOT_FOUND` with no hidden identifier detail |
| Known accessible operation without permission | 403 `OPERATION_FORBIDDEN` |
| Version, authority, decision or semantic conflict | 409 with specific code and authorized diff/refresh guidance |
| Accessible occurrence in the wrong placement state or stale presence version | 409 `PRESENCE_STATE_CONFLICT` or `PRESENCE_VERSION_CONFLICT` |
| Required spatial facts unavailable | 409 `SPATIAL_CONTEXT_REQUIRED` with authorized placement/manual guidance |
| Valid syntax but invalid executable definition | 422 `SEMANTIC_INVALID` |
| Capacity exceeded before execution | 413/422 structural limit or 429 admission limit as appropriate |
| Operational evaluation interruption | 503 plus stable operation/checkpoint status; no false success |
| Automatic transactional attempts exhausted | 503 `OPERATION_RETRY_EXHAUSTED`; preserve operation identity and committed checkpoints |

Package manifests identify immutable versions, ruleset/engine compatibility ranges, declared definition revisions, exact included file hashes, source/rights metadata, declared capabilities and extension points. Dependency solving happens during preview and produces an exact lock. Integrity hashes identify bytes; publisher signatures additionally authenticate origin under a separate trusted-key policy. Neither confers authorization to run privileged code. Signing-key revocation affects future trust decisions and triggers an impact report for installed content.

Canonical export is lossless only for the selected authorized export scope and its declared closure. It includes schema version, exact references, required assets, provenance permitted for export, and an explicit manifest of exclusions. If rights prohibit a required dependency, the user chooses an explicitly external-reference export or the operation fails; the platform cannot label a redacted/incomplete bundle self-contained or lossless. Secrets require explicit export/publication authority, not mere view access.

Import has upload -> parse -> validate -> resolve rights/identity -> preview -> explicit commit. Uploaded data is quarantined and inert. Preview is bound to file digest, parser/adapter version, target scope, policy epoch and mapping decisions. Changed bytes or scope require another preview. Imported owner IDs, policy grants, event sequences, invocation receipts or runtime outcomes are not authoritative. Ordinary imports create/remap local IDs and ownership under the importer’s permissions. Exact identity-preserving restore requires a separate authenticated recovery operation and consistent backup manifest.

Adapter exports identify their adapter version, target platform/schema version, supported semantics and losses by source path. A partial adapter may never silently omit a cost, predicate, duration, visibility restriction or resource link while marking an object automated. The user must explicitly accept the loss report or select a safe manual rendering. Round-trip guarantees are limited to declared fixture coverage. Future executable modules remain unavailable until an independent extension profile specifies host isolation, capability enforcement, no ambient secrets, resource budgets, lock/replay semantics and emergency revocation.

## 18. Resource budgets, availability, and operational targets

`core-safe-1` has deterministic work limits, enforced cumulatively across one root action including all child/reaction frames. Admission rejects definitions whose declared upper bounds exceed the profile. Runtime limits still apply where branching or queries affect actual work. Exceeding a deterministic limit is `BUDGET_EXCEEDED`; it cannot produce partial writes within the current checkpoint. Earlier checkpoints follow the suspension rules in §9.

| Limit | Baseline value |
| --- | --- |
| Formula AST depth / node count per expression | 64 / 4,096 |
| Intermediate rational numerator/denominator | 256 bits each; final wire values within §6 range |
| Derived nodes / active effect applications per instance | 10,000 / 2,000 |
| Formula primitive operations per checkpoint / root action | 100,000 / 1,000,000 |
| Targets per activity / distinct affected instances per root | 64 / 128 |
| Child frames / nesting depth per root | 256 / 16 |
| Trigger firings / generated domain events per root | 1,024 / 4,096 |
| World traversal visited nodes / transclusion depth | 10,000 / 8 |
| Expanded rendered text per interactive document | 1 MiB UTF-8 |
| Upload compressed / expanded package size | 25 MiB / 100 MiB |
| Archive members / maximum expansion ratio | 5,000 / 20:1; both size limits also apply |
| Migration/preview affected instances per interactive request | 128; larger operations use explicit bounded jobs |
| Continuous movement path points / footprint polygon vertices | 256 / 64; teleport has exactly two path points |

Each AST literal, read, arithmetic/boolean operation and conditional evaluation charges one logical operation when evaluated by the pinned reference evaluator; registered compound functions charge their internal primitive and input-iteration work. Query visits, trigger firings and event creation have explicit counters and cannot hide work inside one function call. A registered function without a bounded cost contract is unavailable. The reference evaluator fixes dependency traversal, branch evaluation, memoization within one checkpoint, and contributor ordering. Failed work within an evaluation and internal function retries are charged; branches that the reference semantics do not evaluate are not charged merely because another implementation speculates on them.

**Semantic fuel and operational attempts are separate budgets.** The root frame retains the cumulative fuel charges of its committed checkpoints and children. A successful checkpoint atomically records its charge with its outcome; duplicate delivery or receipt lookup charges it no second time. An uncommitted evaluation checks its work against both checkpoint limits and the root's remaining committed allowance. A deterministic exceedance aborts that checkpoint as BUDGET_EXCEEDED and follows §9. A worker restart or new child cannot reset committed root counters. A checkpoint resumed under the same supported inputs and lock must have the same logical charge as a fresh reference evaluation.

Incremental evaluation and result caching may reduce actual CPU work, but MUST NOT change logical fuel admission or acceptance. A cache hit carries or reconstructs the reference charge and deterministic provenance for the same inputs. Implementations separately measure actual CPU, memory, and query work and enforce operational limits. A warmed cache cannot make an otherwise over-budget rules action valid; a cold cache cannot make a logically valid action fail as BUDGET_EXCEEDED. Operational resource exhaustion may still interrupt work and return the operational status without inventing a rules result.

The proposed automatic database retry policy permits at most five execution attempts per checkpoint recovery episode, counting the first attempt. Durable attempt claims bind operation/checkpoint, episode, attempt ordinal, and worker fence before expensive work begins. They survive rollback and worker replacement and are distinct from game-state mutation. A confirmed database abort may consume another attempt; an ambiguous commit must first resolve the durable outcome. Each attempt has configured finite time/memory limits and admission controls. Client resubmission, transport switching, or worker restart does not create a new episode or refill its budget.

Exhaustion returns OPERATION_RETRY_EXHAUSTED with the existing operation status. Before activation the pending operation has no committed game effect or acquired active gate; after activation the frame is suspended and retains its gate. An authorized operator can start another bounded recovery episode for that same operation after operational recovery; the action retains its lock, committed outcomes, semantic fuel, and audit history. Mechanical expected-version conflicts are reported as conflicts, not repeatedly retried with silently refreshed inputs. The deployment handoff records concrete operational time/memory/admission settings and verifies that automated recovery cannot repeat indefinitely through an external job supervisor.

Imports reject path traversal, absolute paths, symlink/device entries, duplicate paths, malformed encodings, zip bombs and references outside the allowed package closure. Baseline render/import workers have no outbound network access. Remote URLs are retained as inert links or ingested through a separate authenticated asset service with scheme/host controls, request/response size limits and no private-network fetches. HTML/CSS is never executed as server code. Operational worker isolation and memory ceilings must contain a cancelled or pathological job to that job.

The following are **acceptance targets, not measured results**. A reproducible benchmark manifest must state hardware, worker count, database, network conditions and fixture digests. Reference workload: 10 concurrent campaigns, 8 connected users each, 32 active actors per campaign, up to 1,000 derived nodes and 100 effects per actor, 10,000 world entities and 50,000 relationships per campaign. Target p95 server-side simple edit/projection latency <=200 ms; p95 no-human single-target action checkpoint <=300 ms; permitted search first page <=300 ms. Client end-to-end latency and p99/max must also be reported, not hidden by the p95 target.

At the profile's structural maxima, correctness, bounded work and explicit admission/backpressure are required; the interactive SLO above is not silently extended to every maximum-size combination. Simulations/large exports use cancellable jobs with progress and fixed input snapshots. Jobs have per-scope concurrency limits and separate worker capacity so they cannot starve live actions. Operational timeouts may abort/retry an uncommitted checkpoint but cannot change its mathematical result or regenerate a committed roll.

Recovery acceptance: worker restart must recover committed receipts and pending frames with no duplicated spend; an acknowledged checkpoint must survive the configured durable-write boundary. Disaster recovery has a declared recovery-point objective and must disclose any restored-data loss. Exactly zero disaster data loss is not claimed without an infrastructure guarantee. Restore drills verify locks, policy, scope and presence versions, scene geometry, deduplication, pending decisions, semantic-fuel ledgers, operational attempt episodes and outbox as one consistency set.

## 19. Rendering, publication, accessibility and diagnostics

Renderers consume permission-projected canonical data and a semantic presentation tree. They never establish mechanical values. Bindings reference registered value paths and typed formatting functions; they cannot execute arbitrary template expressions or access unprojected objects. Missing values render an explicit unresolved marker in drafts; published Runtime-ready views cannot silently replace them with zero or omit a mandatory cost.

The semantic tree covers headings, paragraphs, lists, tables, statblocks, activity controls, formula/value references, source links, images with alternative text, and permissioned blocks. VTT sheets, cards, tooltips, PDFs, public pages, Discord embeds and accessible JSON/text are projections of that tree. Semantic source and author-written flavor are retained separately so generated mechanical wording does not overwrite authorship.

Default themes are a validated declarative style subset. Raw script, event-handler attributes, executable URLs, unsafe embedded objects, and external resource fetches are prohibited. Rendering occurs against an already authorized projection; sanitization is additional protection, not a substitute for secrecy. PDF/public export jobs use the same projection and asset constraints as interactive rendering. Trusted publisher styling cannot mutate game state and does not bypass policy.

Published artifacts record exact renderer/theme/font/asset identities, locale, projection digest and output digest. Mechanically equivalent text in another language is a new presentation artifact. Regeneration with another renderer is explicit. Old artifacts are not silently overwritten when a theme updates.

Diagnostics report severity, affected path, cause, suggested choices and expected effect. Balance/CR/damage-per-round feedback is advisory, names its formula and assumptions, and never changes content automatically. Missing rights, unresolved execution semantics, unsafe permissions and invalid references are publication/runtime gates appropriate to the claimed quality. Accessibility acceptance includes keyboard-complete authoring, labelled controls, focus preservation during questions, text alternatives for graph views, and non-color-only error/status signals.

## 20. Audit, provenance, telemetry and privacy of operations

Domain events describe committed game facts; security audit records describe sensitive operations and authority; creative decisions explain content authorship. These are linked but distinct streams. Each checkpoint stores the IDs linking them transactionally. An immutable revision's provenance references its source revision, component, activity/advancement, user/compiler decision and mutation. Derived explanations are computed from that graph and permission-projected.

Operational logs record trace ID, operation ID, stable error code, duration, budget usage and versions. They do not include free text, secret names, prompt answers, authorization tokens or full package bodies by default. Any temporary diagnostic capture requires scoped access, explicit retention and redaction. Security audit access is a separate capability and does not automatically grant content export access.

Audit entries are append-only under application permissions; an administrative repair is another entry. “Append-only” does not claim immunity to a database administrator. Integrity verification and backup protections must match the declared operational threat model. Retention and deletion policy must identify which payloads can be redacted while preserving outcome/deduplication integrity, and when such deletion invalidates historical replay guarantees.

Required metrics include command conflict and deduplication rates, suspended-action age, prompt timeout, unauthorized access attempts, recomputation cost, deterministic budget failures, queue/outbox lag, migration discrepancies, compiler abandonment and adapter losses. Metric labels cannot contain user-generated secret content or unbounded IDs. Alerts distinguish one malformed package from scope-wide or fleet-wide service degradation.

## 21. Adversarial acceptance catalogue

These are normative future acceptance scenarios, not executed Creation Engine tests. The companion JSON records each as `specified_not_executed`. T01–T46 retain their existing identifiers; T47–T56 incorporate research proposals RA01–RA10, and T57–T64 add spatial/architecture cases. Research Q1–Q3 now have concrete expected behavior in this body; no unresolved placeholder is an acceptance result. Tests use isolated fixtures, fixed content digests, controlled clocks/randomness and explicit role identities. A happy-path demo does not waive applicable negative cases.

| ID | Setup / adversarial action | Required observable result |
| --- | --- | --- |
| T01 | Migrate legacy AC with unknown contributions | Preserve labelled legacy baseline/override; no invented provenance or double application |
| T02 | Old client writes calculated field after cutover | Translate to allowed command or reject; no second authoritative write |
| T03 | Two representations and two independent campaign occurrences | Shared resources and at most one authoritative presence within an occurrence; separate state across campaigns |
| T04 | Two commands spend last shared charge | One succeeds; current never negative |
| T05 | Crash before checkpoint commit, then retry | No partial change or exposed uncommitted roll; one eventual outcome |
| T06 | Crash after commit before response; retry on another worker | Same receipt, roll and debit; no extra effect |
| T07 | Reuse idempotency key with altered target/amount | IDEMPOTENCY_KEY_REUSE; no second execution |
| T08 | Duplicate outbox delivery and lost socket delta | Apply event once; recover permitted consistent snapshot |
| T09 | Revoke responder access while prompt is open | Reject old answer; no secret result; suspend/reassign as specified |
| T10 | Operator changes relevant mechanical context | Invalidate prompt; stale digest cannot authorize effects |
| T11 | Optional versus mandatory decision times out | Declared optional decline or mandatory suspension; no invented answer |
| T12 | Cancel after committed roll and retry | Preserve roll; no precommit cancellation or free reroll |
| T13 | Reaction chain exceeds depth or cycles | Bounded checkpoint failure; retain earlier commits and suspend |
| T14 | Permute base 10, ADD 2, MULTIPLY 2 serialization | Result 24 and equivalent provenance under core-safe-1 |
| T15 | Different SET values at equal highest priority | EFFECT_CONFLICT; arrival order cannot select winner |
| T16 | Compare incremental with full evaluation across generated fixtures | Equal values, unresolved markers and source contributions |
| T17 | Reorder initiative; duplicate turn/recovery events | Stable occurrence IDs; no repeated cadence/recovery |
| T18 | Source-turn versus each-turn cadence | Distinct explicit clock buckets; per-target identity uses InstanceRef; no reset from scene/view changes |
| T19 | Restore pinned campaign after package/evaluator release | Replay exact lock and recorded outcomes or explicit unavailable state |
| T20 | Max charges decreases from 3 to 1; current is 2 | Block until explicit conversion; record approved exact delta |
| T21 | Roll back package update after new gameplay | Evaluate current state; no stale snapshot overwrite |
| T22 | Player explains/exports value influenced by hidden curse | Only approved declassified result; private metadata absent |
| T23 | GM warms cache; player/other campaign requests same IDs | No audience/policy/scope cache crossover |
| T24 | View As requests owner-private field and mutation | No extra private rights; refuse mutation |
| T25 | Revoke membership mid-subscription; retry old receipt | Use current policy; no stale privileged payload |
| T26 | Huge valid graph, trigger loop, archive bomb or external asset | Enforce declared budgets/isolation; no partial current checkpoint |
| T27 | Same NPC installed in two campaigns; one changes allegiance | Independent state; definition/other campaign unchanged |
| T28 | Two sources grant proficiency; revoke one | Surviving source preserves proficiency |
| T29 | Remove level after granted item was transferred/consumed | Conflict or accepted compensation; no blind deletion/recreation |
| T30 | Undo after later action changes affected resource | UNDO_CONFLICT or declared compensation; preserve later work |
| T31 | Harmless flames; change an earlier interview answer | No damage invented; invalidate dependent answers/effects visibly |
| T32 | Guided -> Advanced -> Guided, locale/schema change | Retain valid decisions; ask new ambiguities instead of defaulting |
| T33 | Contradictory/cyclic interview constraints | Finite GUIDE_DEAD_END and recovery; no infinite loop |
| T34 | Progress-clock/success-pool ruleset fixture | Use declared contracts without core rest/turn hardcoding |
| T35 | Publish lore-only content; falsely claim automation with human-only predicate | Allow valid lore publication; reject false automation claim |
| T36 | Import forged owner, existing instance ID and grants | Inert preview and authorized remap; no authority takeover |
| T37 | Required export dependency is not redistributable | Explicit external-reference report or failure; no false self-contained export |
| T38 | Adapter loses resource cost or visibility | Disclose loss and accept or block; no preserved automation claim |
| T39 | Transclusion cycle, private endpoint, teleport through region | Bounded authorized rendering; specified endpoint transitions only |
| T40 | Concurrent edges exceed relationship cardinality | One consistent accepted state; reject conflicting edit |
| T41 | Reference workload with simulations/exports | Report p95/p99/errors; no live starvation; correct limits |
| T42 | Restore pending prompt, dedupe records and outbox | Consistent fenced authority; no repeated roll/spend or unauthorized delivery |
| T43 | Rounding plus unknown/divide-by-zero input | Explicit rounding; fail invalid checkpoint without NaN/partial writes |
| T44 | Regenerate publication under newer renderer/theme | New artifact ID; old promised artifact retained/verifiable |
| T45 | Novices author item, conditional effect, choice and lore | Report completion/errors/abandonment; no hidden creative defaults |
| T46 | Reference deleted entity or withdrawn package | Tombstone/retained lock or explicit unavailable result; never substitute by name |

Concurrency tests require competing transactions and process restart/failure injection, not mocks that always serialize. Permission tests cover every transport and error shape. Property tests cover operand ordering, grant multiplicity and incremental/full equivalence. Golden fixtures pin expected outputs and locks. The evaluator must ship its applicable conformance fixtures so later versions demonstrate compatibility.

| T47 | One activity has ammunition and charge costs; retry through another transport; also two legitimate costs against one pool | Each declared logical cost applies once; distinct cost IDs remain distinct; aggregate availability is checked and the original receipt is recovered |
| T48 | Fault after a legacy adapter prepares a resource change but before the full receipt/outbox unit commits | No partial checkpoint persists; helpers cannot commit independently; postcommit retry recovers the full prior outcome |
| T49 | One occurrence has a live dungeon view and conflicting reference views on other scenes; compare independent copies | Only the canonical presence establishes geometry/events/vision; references do not toggle conditions; independent occurrences retain independent state |
| T50 | Transform, equip, and rebuild repeatedly; permute unordered contributors and compare full/incremental results | No derived value is reapplied as a base; values, unknowns, conflicts and canonical provenance match without persistent projection side effects |
| T51 | Edit a nested draft answer, commit and reload in a new session; repeat with precommit failure | Answer and descendant invalidation persist together on success; neither persists on failure |
| T52 | Similar content names under distinct rules editions/evaluators; restore with an exact required artifact missing | Use the selected exact closure or report unavailable; no edition/name/latest fallback; migration reconciliation remains explicit |
| T53 | Request a private contribution through every output surface, warm another audience cache, then revoke access | Only declared declassification is exposed; old receipts/delayed jobs use current policy; no private names, IDs, links, or omitted counts escape |
| T54 | Compound function and child actions approach root fuel limits; force aborts, worker restart, and five automatic attempts | Internal work and committed root charges persist correctly; operational retries do not refill episodes or change logical fuel; exhaustion has no partial game effect |
| T55 | Canonicalize Unicode-key and numeric-boundary vectors across runtimes; parse duplicate-key source bytes | Identical valid canonical bytes/hashes; reject duplicate keys before collapse and invalid mechanical values; zero/false/missing/unknown stay distinct |
| T56 | Restart a pending spatial decision; expire worker lease; accept one valid answer then deliver late/stale/revoked responses | Same action and committed rolls; only one eligible current-context answer; stale worker fence and old presence contexts cannot commit |
| T57 | Concurrent placement, move or transfer commands use the same scope and presence version | At most one conflicting new transition commits; no second presence or lost update; duplicates return their receipt |
| T58 | Move, hide, delete or select a reference/live display; open another browser scene | No unintended relocation, invisibility, aura, vision or cadence change; deleting a view preserves its occurrence and presence |
| T59 | Transfer between scenes across regions with a pre-departure decision, post-arrival reaction, and lost response | Old presence remains until relocation commit; departure/arrival reconcile once; later suspension preserves destination and prior state; active unrelated transfer is busy |
| T60 | Unplace and re-place a poisoned occurrence with spent resource and cadence; attempt spatial action while unplaced | Explicit authority and exit/entry rules; poison/spend/cadence persist; required geometry is unresolved and returns spatial guidance or authorized manual resolution |
| T61 | Two live views of one occurrence and two independent occurrences of one definition overlap the same region | Deduplicate views by InstanceRef; independent targets retain distinct per-target cadence; scene transfer never resets logical buckets |
| T62 | Introduce a framework/ORM/network import or ambient randomness/commit into the domain boundary | Automated architecture/purity checks reject the violation; pure domain fixtures run without application or database startup |
| T63 | Equivalent authorized semantic commands arrive via REST, sockets and legacy adapter with transport differences | Same semantic handler, digest identity, costs and current-policy outcome; transport-specific payload cannot bypass the command boundary |
| T64 | Evaluate the same snapshot with cold cache, warm cache and incremental optimization at logical fuel boundaries | Same reference charge and acceptance/result/provenance; actual CPU may differ; operational interruption is not misreported as deterministic budget exhaustion |

## 22. Delivery sequence and evidence gates

The full target remains. A small complete proof precedes broad kernel expansion. G0 remains a prerequisite; accepting one design direction is not completion of the independent audit. Each package has an accountable role; the team assigns people and effort estimates before scheduling. Dates cannot be inferred from theoretical design.

| Gate | Deliverable / accountable role | Exit evidence |
| --- | --- | --- |
| G0 | Spec audit / architecture lead and security reviewer | Independent review of F01–F13 and v1.2 presence/fuel/architecture contracts; no unresolved high-risk contradiction in proposed slice |
| G1 | Existing-character adapter; magic item; three authoring modes; resource/effect / VTT integration lead | Applicable T01–T16, T22–T26, T31–T32, T47–T51, T53–T64; three-mode semantics, presence/view agreement, bounded retry and adapter proof; no live cutover |
| G2 | Time, choices, grants, reactions, contrasting ruleset / rules lead | T13–T18, T28–T34, T43; non-D&D boundary and full/incremental equivalence |
| G3 | Locks, imports, updates/rollback, canonical export / content platform lead | T19–T21, T36–T38, T42, T46 |
| G4 | Complete advertised first-ruleset mechanics; progression/NPCs / rules and product leads | Every advertised mechanic classified automatic, human or manual; choice/grant/undo matrix |
| G5 | World, relationships, mentions and spatial mechanics / world/VTT lead | T27, T39–T40, T49, T57–T61; secrecy across graph/render/vision surfaces; declared spatial capability boundary |
| G6 | Publishing and wider adapters / publishing lead | T35, T37–T38, T44; accessibility and rights evidence |
| G7 | Load, isolation, recovery and observability / operations lead | T04–T13, T25–T26, T41–T42, T54, T56–T57, T64 on the selected database and deployment-like topology |
| G8 | Optional intelligence/executable extensions / feature lead and security reviewer | Separate profile review; unchanged command/trust/replay boundaries |

The first internal G1 proving sequence connects an existing-character snapshot, a reusable resource-spending activity, a human decision, one restricted contribution, and a live/reference view pair. Demonstrating that sequence does not waive G1's three authoring modes or applicable negative cases.

G1 uses bounded real primitives, which may evolve through versioned contracts when evidence reveals defects. “Final-system primitive” is not an acceptance criterion. The slice includes an existing-character conflict and hidden-effect fixture, not only a new empty character. It proves its own coverage, not the full progression/world graph.

G1/G4 product evaluation uses at least eight target users across novice and experienced authors, each attempting the four T45 tasks without an instructor choosing their mechanics. Report completion, time, mistaken interpretations, unnecessary questions and abandonment. Proposed gate: at least 80% successful task completions, zero unnoticed creative defaults in inspected outcomes, and an explicit resolution for recurrent confusion. This is formative evidence, not a market-size or population-level proof.

Before implementation authorization, provide the chosen phase's concrete schema/migration/API diff, dependency choices, executable fixture plan, rollback boundary and acceptance owner. New architecture decisions found during implementation return to a versioned design revision. This document does not authorize production cutover, new paid services or third-party scripting.

## 23. Requirements, finding closure and proof obligations

| Requirement | Authoritative contract | Acceptance IDs |
| --- | --- | --- |
| CE-IDENTITY-01 | Scoped typed identities; §4 | T03, T27, T40, T46 |
| CE-MIGRATE-01 | Sole authority and fenced migration; §5 | T01–T03, T21, T42 |
| CE-TYPE-01 | Canonical types and bounded AST; §6 | T14–T16, T26, T43 |
| CE-EFFECT-01 | Fixed stages, explicit stacking; §7 | T14–T16, T28 |
| CE-COMMAND-01 | Authentication/durable idempotency; §8 | T04–T07, T25 |
| CE-ACTION-01 | Atomic checkpoints, explicit cost identity and random records; §§7–9 | T04–T06, T12–T13, T47–T48, T59 |
| CE-DECISION-01 | Bound authorized decisions; §10 | T09–T12, T32 |
| CE-EVENT-01 | Durable order/outbox/recovery; §§8–10 | T06, T08, T42 |
| CE-TIME-01 | Logical clocks/cadence; §11 | T17–T18 |
| CE-VERSION-01 | Exact closure, geometry and migration; §12 | T19–T21, T42, T44, T46, T52, T55 |
| CE-GRANT-01 | Sourced multiplicity/compensation; §13 | T28–T30 |
| CE-POLICY-01 | Policy on all commands/outputs and spatial perception; §14 | T09, T22–T25, T36–T37, T53, T58 |
| CE-GUIDE-01 | Bounded interview/no creative defaults; §15 | T31–T35, T45, T51 |
| CE-WORLD-01 | Scoped graph/geometry; §16 | T27, T39–T40 |
| CE-INTEROP-01 | Authorized import/honest export; §17 | T07, T36–T38 |
| CE-BUDGET-01 | Logical/operational bounds and measured workload; §18 | T13, T26, T41, T54, T64 |
| CE-RENDER-01 | Safe presentation/artifact identities; §19 | T22–T24, T39, T44 |
| CE-AUDIT-01 | Linked provenance/restricted telemetry; §20 | T06, T22, T25, T42 |
| CE-PRESENCE-01 | Occurrence-owned single presence and explicit transitions; §§4–5, 14, 16 | T03, T49, T56–T61 |
| CE-PROVENANCE-01 | Deterministic contribution identity/order and pure projection; §§6–7, 13 | T14–T16, T28, T50, T55, T64 |
| CE-RETRY-01 | Separate semantic fuel and bounded operational recovery; §§8–9, 18 | T05–T08, T42, T54, T56, T64 |
| CE-ARCH-01 | Domain dependencies, types and side-effect boundaries; §26 | T48, T50–T51, T62–T63 |
| CE-PERSIST-01 | Whole-checkpoint ownership and selected-backend proof; §§5, 8–9, 26 | T04–T06, T40, T48, T51, T57 |
| CE-TEST-01 | Independent, backend, adapter and policy acceptance evidence; §§21–22, 26 | T16, T22–T26, T41–T42, T47–T64 |

| Finding | Response | Status |
| --- | --- | --- |
| F01 | §5 field authority, ruleset target, migration and rollback | Contract addressed; migration proof pending |
| F02 | §§8–10 receipts, checkpoints, randomness and outbox | Contract addressed; crash/concurrency proof pending |
| F03 | §§9–10 action states, bound decisions and reactions | Contract addressed; interleaving proof pending |
| F04 | §§6–7, 11 algebra, types, clocks and cadence | Contract addressed; evaluator proof pending |
| F05 | §12 exact execution closure and reproduction levels | Contract addressed; restore/update proof pending |
| F06 | §14 all-surface current policy and explicit declassification | Contract addressed; information-flow proof pending |
| F07 | §18 deterministic work/import budgets and safe profiles | Contract addressed; isolation/load proof pending |
| F08 | §§4, 16 templates, occurrences, facts and representations | Contract addressed; cross-campaign fixtures pending |
| F09 | §13 grants and conflict-aware compensation | Contract addressed; progression/undo proof pending |
| F10 | §15 bounded language, interview and quality axes | Contract addressed; language/UX evidence pending |
| F11 | Profiles and namespaced logical clocks | Contract addressed; contrasting ruleset fixture pending |
| F12 | §22 earlier integration/usability evidence gates | Plan addressed; staffing/benchmark evidence pending |
| F13 | §§1, 3, 23, 25 authority, traceability and confidence | Document addressed; independent consistency review pending |

The next auditor should attack these invariants, including the new presence and clean-code contracts in §§16 and 26: committed work cannot execute twice; each scope has one authoritative state; a roll cannot be cancelled into another draw; one grant's removal preserves independent grants; secrets cross only declared disclosure boundaries; pins resolve exact behavior or fail explicitly; unsupported work cannot use an untyped bypass; and the compiler never implicitly chooses mechanical meaning for the author.

Tradeoffs remain visible: one active root mechanical action per scope; operator resolution for suspended mandatory decisions; no unrestricted deterministic prose promise; later profiles for fixed-point formulas and third-party code; no recall of already disclosed information; replay contingent on retaining permitted artifacts; unmeasured performance targets; and a required fresh inventory of the existing VTT before implementation. These bound the promise without claiming universal coverage.

## 24. Worked conformance traces

**Shared charge.** R has current=1 at scope version 40. A and B both expect version 40 and spend one charge on activation. A commits version 41, R=0 and the action gate. B changes nothing and receives a conflict/busy result. A's same-key retry returns its existing operation. B must refresh and submit a new command after A finishes; it then fails for insufficient resource if R is still zero.

**Post-hit flame.** The attack's hit/roll checkpoint is committed. The optional flame child references that hit and asks its authorized controller whether to spend a charge. Acceptance rechecks context and atomically debits one charge, records 2d6 outcomes and applies its declared damage. Repeated answers return that receipt. Declining preserves the attack and spends no flame charge. Later failure cannot erase either already committed checkpoint.

**Private curse.** A restricted effect contributes -1 defense. A reviewed rule permits the final value to be public, while source ID/name, private decision and source link remain absent from API, cache, export and socket projection. Without that declassification rule the final value is withheld. View As does not override owner-private restrictions.

**Two grant sources.** Species G1 and class G2 grant the same proficiency key. It is effective with two contributions. Revoking G2 preserves G1 and proficiency; removing the last source removes it only if no override/other contribution remains. No destructive proficiency-array removal is generated.

**Harmless flames.** The author chooses equipment then visual/light behavior, maximum three uses and an explicit recovery event. No damage component exists. Switching to damage invalidates relevant decisions and asks required amount/timing/targets. Equivalent Structured decisions yield equivalent executable meaning.

**Pinned upgrade.** Preview compares exact A/Evaluator1 against B/Evaluator2, reports changed semantics and excess charges, and requests a named reconciliation. Activation waits for quiescence and commits a new exact lock. Historical actions retain their original lock/outcomes; current state uses the approved replacement.

**Mira on three maps.** Mira's occurrence is placed in the dungeon at presence version 7. The world-map pin and tomorrow's prepared encounter token are reference views. Moving the pin or opening the prepared scene creates no movement event, vision, aura or target. A second live dungeon view resolves to the same presence and never causes a second region application. Two separately instantiated goblins from one definition remain separate targets.

**Transfer with a delayed answer.** Mira is awaiting a spatial decision bound to presence version 7. An unrelated transfer receives SCOPE_BUSY. An authorized frame-bound intervention can transfer her, committing version 8 and old/new memberships in one relocation checkpoint and invalidating the unanswered spatial decision. An answer for version 7 is stale. A lost transfer response followed by retry returns the original receipt; it does not re-enter the destination region. HP, poison duration and used cadence remain attached to Mira.

**Display deletion.** Deleting Mira's only dungeon token leaves her occurrence and presence intact. It does not cure poison, stop an aura, or remove her from initiative. An authorized user can recover a live view. Removing her from spatial play is an explicit UnplacePresence command with the required transition semantics; reference markers cannot silently become the new location.

**Logical fuel versus retries.** A deterministic checkpoint's reference charge is 80 operations. A warm cache and a cold evaluation both charge 80 if the checkpoint commits. Two confirmed database aborts followed by success consume three operational attempts and add 80 once to committed root fuel. A fifth unsuccessful attempt exhausts that recovery episode; resending the command or restarting a worker cannot create a sixth automatic attempt. No aborted attempt publishes a roll or spends the resource.

## 25. Source register and provenance

R01, R05, R06, R09, R14, R15, R21 and R26 were checked against primary sources during the preceding audit on 23 September 2026. R30–R31 were checked for v1.1. Other R entries are inherited from v1.0 and are not claimed as independently revalidated here. C entries remain community friction evidence. The normative contracts in this document are Roll Drauf design decisions, not requirements imposed by competitors. S entries below record the implementation-focused research checked on 24 September 2026; this rewrite reuses that evidence and does not claim a fresh audit of every inherited reference.

- R01 — [Foundry activities](https://github.com/foundryvtt/dnd5e/wiki/Activities)
- R02 — [Foundry effects](https://github.com/foundryvtt/dnd5e/wiki/Active-Effects)
- R03 — [Foundry effect guide](https://github.com/foundryvtt/dnd5e/wiki/Active-Effect-Guide)
- R04 — [Foundry advancement](https://github.com/foundryvtt/dnd5e/wiki/Advancement)
- R05 — [Foundry area behavior](https://github.com/foundryvtt/dnd5e/wiki/Activity-Behaviors)
- R06 — [DMV architecture/source](https://github.com/Orcpub/orcpub)
- R07 — [DiceCloud community slot guide](https://github.com/NappingPiglet/dicecloud-v2-guide/blob/master/creating-your-first-character/character-creation-101.md)
- R08 — [DiceCloud community action guide](https://github.com/NappingPiglet/dicecloud-v2-guide/blob/master/creating-your-first-character/the-stats-tab.md)
- R09 — [Roll20 homebrew builder](https://blog.roll20.net/posts/dd-homebrew-character-builder-is-here/)
- R10 — [Roll20 homebrew features](https://blog.roll20.net/posts/dd-homebrew-features-you-need-to-try-on-roll20/)
- R11 — [Roll20 updates](https://blog.roll20.net/posts/what-youve-missed-in-dd/)
- R12 — [Roll20 species/features](https://blog.roll20.net/posts/create-homebrew-dd-species-features/)
- R13 — [D&D Beyond roadmap](https://www.dndbeyond.com/posts/2132-d-d-beyonds-2026-development-roadmap)
- R14 — [D&D Beyond mid-year update](https://www.dndbeyond.com/posts/2223-mid-year-update-d-d-beyonds-2026-development)
- R15 — [Fantasy Grounds effects](https://fantasygroundsunity.atlassian.net/wiki/spaces/FGCP/pages/996642031/5E%2BEffects%2Bfor%2BAdvanced%2BAutomation)
- R16 — [World Anvil templates](https://www.worldanvil.com/learn/article-templates)
- R17 — [World Anvil template use](https://www.worldanvil.com/learn/article-guides/article-templates)
- R18 — [World Anvil settlements](https://www.worldanvil.com/learn/article-templates/settlement)
- R19 — [World Anvil characters](https://www.worldanvil.com/learn/article-templates/character)
- R20 — [Kanka mentions](https://docs.kanka.io/en/latest/features/mentions.html)
- R21 — [Kanka permissions](https://docs.kanka.io/en/latest/guides/testing-permissions.html)
- R22 — [Kanka property kits](https://docs.kanka.io/en/latest/entries/attribute-templates.html)
- R23 — [Kanka plugin library](https://docs.kanka.io/en/latest/plugins/plugins.html)
- R24 — [LegendKeeper](https://www.legendkeeper.com/features/)
- R25 — [Homebrewery changelog](https://github.com/naturalcrit/homebrewery/blob/master/changelog.md)
- R26 — [Homebrewery releases](https://github.com/naturalcrit/homebrewery/releases)
- R27 — [Monsterbrew announcements](https://www.monsterbrew.app/announcements)
- R28 — [Tetra-Cube statblocks](https://tetra-cube.com/dnd/dnd-statblock.html)
- R29 — [Roll20 attunement](https://blog.roll20.net/posts/dd-attunement-is-automatic-on-roll20/)
- R30 — [JSON Canonicalization Scheme](https://www.rfc-editor.org/info/rfc8785/)
- R31 — [JSON Schema 2020-12 core](https://json-schema.org/draft/2020-12/json-schema-core)
- C01 — [Foundry experience](https://www.reddit.com/r/FoundryVTT/comments/1dwzijd/)
- C02 — [Foundry accessibility](https://www.reddit.com/r/FoundryVTT/comments/1q0et78/homebrew_easeaccessability/)
- C03 — [Foundry automation](https://www.reddit.com/r/FoundryVTT/comments/1jdkfe1/)
- C04 — [Roll20 class help](https://www.reddit.com/r/Roll20/comments/1tlgf28/custom_class_builder_help/)
- C05 — [Roll20 reusable content](https://www.reddit.com/r/Roll20/comments/1ocekn0/dd_2024_character_builder_now_available_custom/)
- C06 — [D&D Beyond usability](https://www.reddit.com/r/onednd/comments/1otn3tv/)
Original: Roll Drauf Creation Engine v1.0, 22 September 2026, 41 pages; SHA-256 `7f6c275ee19933f869672b05a0a3588a83b8556e02a62638e161f9eddac537e3`. Source: https://discord.com/channels/1328724663257268264/1551867598876971048/1551975805146374146

### 25.1 Implementation-focused primary source register

Sources were checked on 24 September 2026. Issue reports are labelled separately from confirmed maintainer fixes. All source claims are limited to the observations in §3 and the research manifest.

- S01 — [Foundry D&D5e Activities](https://github.com/foundryvtt/dnd5e/wiki/Activities). Evidence: technical primary.
- S02 — [Foundry D&D5e Advancement](https://github.com/foundryvtt/dnd5e/wiki/Advancement). Evidence: technical primary.
- S03 — [PF2e rule elements](https://github.com/foundryvtt/pf2e/wiki/Quickstart-guide-for-rule-elements). Evidence: technical primary.
- S04 — [Dungeon Master’s Vault architecture](https://github.com/Orcpub/orcpub). Evidence: technical primary.
- S05 — [DiceCloud project README](https://github.com/ThaumRystra/DiceCloud). Evidence: product primary.
- S06 — [Kanka permission testing](https://docs.kanka.io/en/latest/guides/testing-permissions.html). Evidence: product primary.
- S07 — [Homebrewery renderer changelog](https://github.com/naturalcrit/homebrewery/blob/master/changelog.md). Evidence: technical primary.
- S08 — [Temporal safe deployments](https://docs.temporal.io/develop/safe-deployments). Evidence: technical primary.
- S09 — [CEL overview](https://cel.dev/). Evidence: technical primary.
- S10 — [CEL language and cost semantics](https://github.com/cel-expr/cel-spec/blob/master/doc/langdef.md). Evidence: technical primary.
- S11 — [Foundry issue 1239: consumption report](https://github.com/foundryvtt/dnd5e/issues/1239). Evidence: issue report.
- S12 — [Socket.IO delivery guarantees](https://socket.io/docs/v4/delivery-guarantees/). Evidence: technical primary.
- S13 — [AWS transactional outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html). Evidence: technical primary.
- S14 — [SQLAlchemy session basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html). Evidence: technical primary.
- S15 — [Foundry issue 7470: linked-token falling](https://github.com/foundryvtt/dnd5e/issues/7470). Evidence: issue report.
- S16 — [Foundry issue 7483: region cadence report](https://github.com/foundryvtt/dnd5e/issues/7483). Evidence: issue report.
- S17 — [Foundry D&D5e release 5.1.0](https://github.com/foundryvtt/dnd5e/releases/tag/release-5.1.0). Evidence: technical primary.
- S18 — [OWASP authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html). Evidence: technical primary.
- S19 — [SQLAlchemy JSON type behavior](https://docs.sqlalchemy.org/en/20/core/type_basics.html). Evidence: technical primary.
- S20 — [RFC 8785 canonical JSON](https://www.rfc-editor.org/info/rfc8785/). Evidence: technical primary.
- S21 — [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html). Evidence: technical primary.
- S22 — [OWASP XSS prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html). Evidence: technical primary.
- S23 — [Robert C. Martin: Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html). Evidence: technical primary.
- S24 — [Alistair Cockburn: Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture). Evidence: technical primary.
- S25 — [Hypothesis stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html). Evidence: technical primary.
- S26 — [Import Linter dependency contracts](https://import-linter.readthedocs.io/en/stable/). Evidence: technical primary.
- S27 — [Foundry token documentation](https://foundryvtt.com/article/tokens/). Evidence: technical primary.

The original research companion contains the detailed qualitative failure analysis. This specification integrates its relevant contracts and retains those source IDs for traceability.

## 26. Implementation architecture and clean coding contract

### 26.1 Domain boundaries and dependency direction

The implementation MUST separate deterministic domain semantics from framework and external side effects. The initial design proposal is an isolated Creation Engine package inside the existing application, with explicit persistence, transport, and legacy adapters. This preserves the current integration boundary while making the core independently testable. It is not a selected deployment topology: extraction to another process requires a versioned decision showing how checkpoint atomicity, latency, operations, and authorization remain satisfied. Neither Temporal nor CEL is selected by analogy alone.

| Responsibility | Owns | Prohibited dependency or behavior |
| --- | --- | --- |
| Domain values and evaluation | Typed identities, exact quantities, AST interpretation, effect algebra, sourced grant projection, transition validation | Flask/request globals, SQLAlchemy entities, sockets, network/filesystem access, ambient clock/randomness, transaction control |
| Application command coordination | Authenticated command context, admission, frame/decision lifecycle, complete checkpoint plans, unit-of-work and retry orchestration | Delegating partial commits to helpers; accepting a frontend-calculated outcome as authority |
| Policy and authorized projections | Current audience and entitlement inputs, field restrictions, declassification, safe receipt/explanation/view data | Treating an old cached audience or imported ownership declaration as current authority |
| Authoring/compiler | Question graph, typed answers, invalidation, pure registered adapters, semantic draft commands | An alternate mechanical evaluator, hidden creative defaults, or persistent game-state effects |
| Persistence and external adapters | Scoped consistency, locks/fences, receipts/outbox, ORM mapping, HTTP/socket translation, legacy routing | Introducing new game rules or returning unfiltered ORM objects through transports |
| Packages and publication | Inert parsing/preview, exact lock resolution, adapter loss reports, authorized semantic rendering | Activation during parsing; rules execution in templates; renderer-created game values |

Source dependencies point toward domain/application contracts. Domain functions receive immutable typed snapshots and explicit deterministic inputs and return values, conflicts, unresolved results, or proposed transitions. They do not obtain a Session, Request, global service locator, or arbitrary callback capable of mutation. Adapter interfaces expose the narrow capabilities required by the use case. Read-only previews and renderers MUST NOT receive a write-capable unit of work. An import-boundary check enforces these restrictions for the engine package.

The server evaluator is canonical. A client preview may share pure code or use a separately conformed implementation, but must identify its input/lock and satisfy the same semantic fixtures. A template, legacy form, or GUI convenience calculation cannot become a second authoritative rules implementation. Differences in persistence layout, UI toolkit, or language do not justify different mechanics.

### 26.2 Cohesion, types, and explicit effects

Single responsibility is enforced around reasons for change: a reducer calculates, a coordinator commits, a projection filters, and a renderer presents. Helpers used within a checkpoint MUST NOT commit, emit success, allocate independent grant records, or draw ambient randomness. Before entering the pure evaluator, the application materializes the authorized computation snapshot under its consistency boundary; lazy ORM reads cannot escape into pure evaluation or rendering.

Use distinct domain types for Definition/Revision/Instance/Scene/Representation references, Quantity/unit, draft version, scope version, presence version, and worker fence. Wire syntax validation is followed by relational and state-transition validation. Reusing a generic dictionary or integer type at an external boundary does not remove the obligation to discriminate these values before domain execution. Constructors/parsers do not silently coerce strings to numbers, zero to missing, or unknown to false.

Published revision values and evaluator inputs are immutable. Mutable persistence entities are mapped at the adapter boundary; returned projections are detached values that cannot write back to storage. In particular, a cached total is never a base input, and a view read is never a lifecycle command. Persistence tests reload committed JSON and related records in a fresh session/connection instead of trusting the in-memory object that was just mutated.

Prefer composition through registered components and functions over a hierarchy that hardcodes D&D creature categories in the core. Extensions are versioned registry entries with schema, purity, cost, policy, and conformance contracts. Runtime discovery or monkey-patching of ordinary content as privileged code is prohibited. Interfaces should be small enough that a read-only consumer cannot accidentally acquire unrelated write capabilities.

Do not turn stylistic similarity into a shared abstraction when semantics differ: a draft edit, published revision, and runtime adjustment have different authority and lifecycle. Share actual mechanical semantics and explicit value types. Arbitrary function-length targets, class counts, and universal repositories are not conformance criteria. Domain names such as resolve_decision, revoke_grant_source, project_for_audience, and commit_checkpoint are preferred to vague mode-driven helpers that conceal authority in boolean flags. Exceptions or result objects must distinguish domain conflict, unresolved input, policy denial, and operational interruption; public diagnostics are separately projected.

### 26.3 Checkpoint and adapter acceptance

The coordinator's unit of work MUST be visible in code review. A reviewer must be able to identify its read set, policy/fence validation, all planned costs/changes, logical fuel, random-outcome handling, receipt identity, event/outbox writes, and actual commit point. No notification is a committed success until that unit commits. A serialization failure retries the whole attempt within §18, while ambiguous results recover the existing receipt. Every external side effect has an explicit owner and retry contract.

REST, sockets, legacy commands, and registered background jobs translate to the same semantic application handlers. Transport authentication remains at the boundary; domain logic receives the server-established principal and explicit capabilities, never a principal claimed by the payload. An adapter may preserve a legacy response shape only by transforming the permitted projection. It cannot bypass current policy, resource checks, presence authority, or the lock to remain compatible.

The persistence handoff MUST state the chosen backend/version, isolation or equivalent locking argument, uniqueness/fencing constraints, lock order, policy-race strategy, session lifecycle, migration fence, and ambiguous-commit recovery. The scope-wide serial-order argument includes account/policy changes that affect commands, even when those records live outside the mechanical scope table. A transaction around writes alone is insufficient. Tests on an in-memory substitute do not establish this argument for another database.

### 26.4 Verification and review gates

Each changed invariant has targeted executable evidence when implementation begins. Pure examples test exact algebra, unknowns, grant multiplicity and deterministic provenance. Generated cases compare full and incremental evaluation and cold/warm cache logical fuel. Stateful sequences exercise grant/revoke, equip/transform, spend/recover, placement/transfer, retry, and conflicting undo against a simpler reference model. Expected results come from the specification or an independent model, not a copy of the implementation under test.

Transaction tests use the selected database, independent connections/workers, and explicit barriers to force races and crash windows. They test policy revocation, competing receipt claims, presence uniqueness, shared resources, lease fencing, outbox replay, operational retry exhaustion, and restore. Compatibility tests compare semantic outcomes across transports. Projection tests cover each authorized role and output surface, including old receipts and delayed rendering after revocation. A registered renderer/adapter has fixtures for its claimed capability and losses.

The engine boundary MUST have automated dependency, static-type or equivalent contract, formatter/linter, schema, and applicable acceptance checks in CI. Tool choice is an implementation decision. Adoption should scope checks to the new boundary and touched integration paths; unrelated repository-wide cleanup is not required. Coverage percentages, snapshots alone, or linters cannot substitute for the critical negative cases. Hypothesis and Import Linter are candidate tools; implementing equivalent checks with existing tooling is acceptable.

Every implementation review identifies the affected requirement and acceptance IDs, transaction owner, authority inputs, expected retry/crash behavior, public projection, lock/schema compatibility, and remaining test gaps. Refactors preserve observable semantics and fixture results; changes to mechanics, provenance ordering, logical fuel, or geometry require a new compatible/versioned lock and explicit migration behavior.

## 27. Decision record and implementation handoff

| Decision | Status in this revision | Remaining evidence |
| --- | --- | --- |
| One authoritative presence per occurrence per RuntimeScope | Accepted design direction; normative in §§4, 16 | Concurrency, transfer, visibility, and migration fixtures |
| Occurrence-owned presence; extra views have no independent spatial authority | Detailed design for review | UI/legacy mapping; footprint and scene-transition implementation |
| Canonical provenance ordering | Defined in §§6–7; closes research Q2 at contract level | Cross-runtime and full/incremental byte/semantic comparisons |
| Separate logical fuel from durable bounded operational attempts | Defined in §§9, 18; closes research Q3 at contract level | Cold/warm cache, crash, and retry-exhaustion fixtures |
| One application coordinator owns each unit of work | Defined in §§8–9, 26; addresses research Q4 at contract level | Selected backend/isolation, complete writer inventory, schema and fencing implementation |
| Constrained typed AST with exact rationals, units, staged reads and provenance | Existing core retained; library selection remains open under research Q5 | Candidate evaluator conformance matrix; no implicit CEL adoption |
| Initial isolated engine package with adapters inside current app | Proposed implementation shape | Architecture decision before implementation; no new service/vendor selected |

The full product target, single active mechanical root per scope, manual play, and staged delivery remain. Deliberate limitations include one physical presence per occurrence; no cross-scene spatial effects or baseline 3D falling simulation; operator handling for suspended mandatory decisions; no arbitrary executable prose or scripts; and replay contingent on retaining permitted artifacts. These limitations must be visible in capability claims.

Before implementation, produce a concrete design for the chosen gate: complete writer and field-authority inventory; selected persistence/worker configuration; schema/API/migration diff; policy/fencing transaction argument; operational limits; required fixture matrix; current dependency inventory; rollout/rollback boundary; and named acceptance owner. Resolve applicable medium/high implementation-design risks in that handoff. The document authorizes no production change and does not claim that these implementation choices are already settled.

This revision is ready for independent adversarial specification review. The review should attempt to create two presences, change conditions by editing a marker, obtain vision through a prepared token, reset cadence through a scene transfer, duplicate a cost across transports, exploit an ORM helper's commit, change fuel admission through cache warmth, accept a stale spatial decision, or expose a private contribution through an old receipt. Only subsequent implementation and executed acceptance can establish conformance.
