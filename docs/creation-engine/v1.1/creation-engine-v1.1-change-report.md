# Creation Engine v1.1 — revision report

23 September 2026 · Audit Candidate 1 · Theoretical specification work

**Ready for a second adversarial audit.** The revised specification addresses all thirteen findings through explicit proposed contracts, includes 46 acceptance scenarios, and maps eighteen requirements to those scenarios. No Creation Engine implementation, live migration, or production security test was performed. The contracts are ready to challenge; implementation correctness has not been established.

The deliverable is a complete revised specification, not only an addendum. It preserves the full target: homebrew creation, character progression, runtime mechanics, worldbuilding, publishing, packages and interoperability. Its research section distinguishes checked primary sources from inherited references and community evidence.

## What changed

| Finding | Resolution in v1.1 | Next audit should challenge |
| --- | --- | --- |
| F01: migration/authority | Field ownership table, legacy adapter, authority epochs, parity gate, explicit rollback limits; §5 | Hidden legacy writers, unknown historical values, cross-campaign resources |
| F02: atomicity/retry | Durable scoped receipts, request binding, atomic checkpoints, recorded randomness and transactional outbox; §§8–10 | Crash windows, duplicate commands, multi-worker races and restoration |
| F03: human resolution | Durable action/decision state machine, context digests, responder eligibility, deadlines and reaction ordering; §§9–10 | Revocation, stale answers, reaction chains and suspended actions |
| F04: deterministic semantics | Exact rational arithmetic, fixed effect stages, explicit conflicts and logical clock/cadence identities; §§6–7, 11 | Type errors, ordering, duplicate source effects, off-by-one expiry |
| F05: pinned compatibility | Complete execution locks, retained artifacts, three-way updates, explicit resource conversion and replay levels; §12 | Missing transitive dependencies and updates after gameplay |
| F06: secrecy | Default-deny policy across reads, writes, caches, events, exports, explanations and View As; §14 | Derived inference, revocation races and new compatibility endpoints |
| F07: data-only safety | Deterministic fuel, graph/target/import limits, no ambient network, explicit failure behavior; §18 | Work hidden inside registered functions and later-checkpoint failure |
| F08: identity | Separate definitions, revisions, world entities, runtime occurrences and representations; §§4, 16 | Same NPC in two campaigns and multiple tokens for one occurrence |
| F09: reversal | Sourced grant ledger, explicit multiplicity, dependent-choice conflicts and compensation; §13 | Consumed/transferred grants and changes after the action being reversed |
| F10: compiler | Bounded intent input, deterministic question order, answer invalidation, proposal confirmation and orthogonal quality axes; §15 | Dead-end interviews, hidden creative choices and mode switching |
| F11: generic rules | Core clocks/events are namespaced; safe and future profiles are explicit; §§2, 11 | A progress-clock/success-pool fixture without D&D assumptions |
| F12: delivery | Existing-character proof moves before kernel expansion; measurable workload and user trials; §§18, 22 | Whether the first slice actually falsifies the risky assumptions |
| F13: evidence/requirements | Normative precedence, eighteen requirement mappings and qualified source register; §§1, 3, 23, 25 | Contradictions between prose, schemas, examples and tests |

## Deliberate decisions to review

An activity may pause for a person, so atomicity is defined per committed checkpoint. Earlier visible rolls and paid costs are durable; a later cancellation cannot make them disappear or produce a fresh roll. This is a precise behavior choice, not a claim that a multi-person action can fit inside one long database transaction.

The baseline admits one active root mechanical action per campaign runtime scope. Reactions and authorized interventions run within that frame. It favors correctness and understandable ordering over simultaneous mechanical editing. Mandatory unresolved decisions suspend the frame and require an operator to resume or resolve it explicitly. Reads, chat and draft authoring continue.

Effect order is fixed: base, SET, ADD, MULTIPLY, clamp, explicit final rounding. Equal-priority contradictory SET values fail rather than use arrival order. A ruleset that needs different algebra must declare typed intermediates or another separately conformed profile.

Existing Roll Drauf Light characters are the first integration target; a full D&D reference ruleset is distinct and edition-qualified. A small test ruleset can prove the integration slice without silently reinterpreting existing characters as another game system.

The first deterministic authoring experience is an explicit intent interview. Unrestricted prose parsing and creative assistance remain proposal-producing capabilities; unsupported text cannot silently become automation. Fixed-point evaluators and third-party scripts require later, independently reviewed profiles.

Restricted inputs can contribute to public game outcomes only through a reviewed declassification rule. The spec does not pretend that revealing an exact number prevents every inference about its hidden inputs. It specifies which outcomes may be revealed and keeps private source metadata out of every output surface.

Exact mechanical replay requires the complete retained execution lock and recorded outcomes. Exact publication bytes require the retained artifact. Compatibility ranges alone establish neither. Security/rights restrictions can make old execution unavailable, in which case the system reports that state rather than silently substituting content.

## Included review artifacts

- `creation-engine-v1.1.pdf` and `.md`: full revised specification.
- `creation-engine-v1.1-change-report.pdf` and `.md`: this report and finding map.
- `creation-engine-v1.0-audit-team.pdf` and `.md`: historical audit, with portable repository references.
- `creation-engine-v1.1-contracts.schema.json`: JSON Schema 2020-12 contracts for selected core wire types and three runtime commands; it is not the complete future feature registry.
- `creation-engine-v1.1-acceptance.json`: 46 scenarios, each explicitly marked specified but not executed.
- `creation-engine-v1.1-wire-examples.json`: synthetic command examples; placeholder zero hashes do not identify runnable content.
- `creation-engine-v1.1-verification.json`: packaging/schema checks and their limits.
- `review-package-manifest.json`: file hashes for the delivered package.

## Verification and remaining evidence

The JSON Schema is checked against Draft 2020-12. Synthetic valid commands and malformed command shapes are checked locally. This verifies schema consistency for those examples; it does not prove authorization, transaction isolation, state transitions, mathematical evaluation, or engine behavior. All 46 future acceptance scenarios remain unexecuted.

The second audit should begin with §§8–14 and try to break retries, prompt/context binding, checkpoint boundaries, reaction ordering, grant/undo behavior and information flow. Then challenge the companion schemas against the prose and worked traces. Performance numbers are proposed release criteria, not benchmark measurements. Named team owners, effort estimates and implementation evidence belong to subsequent planning.

The original audit is retained as historical evidence. Its high-severity findings are addressed in the proposed specification and still require independent acceptance and eventual implementation proof. No claim of a watertight or production-ready implementation is made.
