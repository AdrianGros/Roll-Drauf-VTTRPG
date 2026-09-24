# Creation Engine v1.1.2 — errata E1 + E2, and the low-findings map (proposed E3)

24 September 2026. Decision record: `dadm/artifacts/approvals/approval_creation_engine_g1_2026-09-24.md`.

- **v1.1.2** = v1.1 (Audit Candidate 1) + E1 (G0 high findings) + E2 (accepted G0 medium findings).
  Every other normative sentence of v1.1 is unchanged.
- **Older packages.** `../v1.1/` (historical audit candidate) and `../v1.1.1/` (superseded) stay
  unchanged, with their original hashes.
- **Contract version** is `1.1.2` (`urn:rolldrauf:creation-engine:contracts:1.1.2`). Registry addendum A1 is retargeted to it.

## E1 — high findings (approved by Adrian, 2026-09-24)

| Finding | Spec change | Wire change | Evidence |
| --- | --- | --- | --- |
| G0-01 unkeyed digests disclose restricted facts | §6 context tokens; §8 public receipts; §10 context token; §14 output boundary | `ContextToken`, `contextToken` fields, `PublicReceipt` | T47 |
| G0-02 migration authority per character vs per scope | §5 scope-level migration state and cutover preconditions, `SCOPE_TRANSFER_UNSUPPORTED` | — | T48 |
| G0-03 invocation cannot name its source occurrence | §§4, 8 `InstanceRef` for occurrences, `sourceInstance` | `actorInstance`, `sourceInstance`, `AdjustResourcePayload.instance` | T49 |

## E2 — accepted medium findings (approved by Adrian, 2026-09-24)

| Finding | Spec change | Wire change | Evidence |
| --- | --- | --- | --- |
| G0-04 two suspension clocks | §10: SUSPENDED at the mandatory deadline, in the same commit. 600 s is the policy maximum, not a second clock. Reissue is an operator command | — | T11 |
| G0-05 `commandId` vs `idempotencyKey` | §8: the command ID is a correlation ID outside the request digest. Retries reuse the key. Receipts return the first command ID | — | T06, T07 |
| G0-06 `expectedScopeVersion` semantics | §8: exact match for mechanical commands. `ResolveDecision` is bound by decision version and context token, with scope version ≥ decision creation | — | T04, T09–T12 |
| G0-07 epochs | §9: fencing epochs are internal, and the authority epoch changes only on authority transfer. §12: restore increments the authority epoch | — | T05, T06, T42 |
| G0-08 "control" and "operator" undefined | §14: `controls` / `operates` are default-deny policy relations. §5: VTT default grants (owner controls, DM/CO_DM operate, token = presentation only, sandbox owner) | — | T09, T24 |
| G0-09 `AdjustResource` at bounds | §7: mandatory adjustment bound policy `reject` (`RESOURCE_BOUND_EXCEEDED`) or `clamp_report_delta`, with no default | — | T02, T04 |
| G0-10 formula schema vs prose | §6: numeric formulas use the core function set (11 functions, 1 operation each); boolean logic lives in Predicates | `Predicate` schema; `Formula` description | T14, T15, T43 |
| G0-12 inert legacy metadata vs strict schemas | §5: `legacyMetadata` is the only container for unrecognized legacy data, is never addressable, and round-trips unchanged | `LegacyMetadata` | T01 |
| G0-14 manual play untested | §23: requirement CE-MANUAL-01 | — | T50 (G1) |
| G0-15 reaction candidate order | §10: candidate list fixed per slot and bound into the context token; an operator reorder restarts the slot without re-offering decliners | — | T51 (G2) |

## Still open with the product owner

| Finding | Owner | Status |
| --- | --- | --- |
| G0-11 wire contracts for G1 commands | Matt (non-author review) | Addendum A1 drafted and retargeted to 1.1.2 |
| G0-13 token movement and the scope gate | Matt (product decision) | Open. §9 still gates all token movement |

## Low findings map (proposed E3, not applied)

Each low finding has a location, a proposed closure, its wire impact, the evidence that would
prove it, the gate or work package it touches, and an owner. On approval, E3 becomes v1.1.3.

| Finding | Where | Proposed closure | Wire impact | Evidence | Gate / WP | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| **G0-16** `PROPOSED` has no path to `CANCELLED`, although "precommit proposals expire as CANCELLED" | §9 state machine; §10 | Add `PROPOSED → CANCELLED` for withdrawal by the invoker or precommit-deadline expiry. No cost and no checkpoint. The admission count is released | none (enum unchanged) | New **T52**: withdraw one PROPOSED action and let another expire; both end CANCELLED without cost, and the open-proposal count drops | G1 / WP4 | Adrian |
| **G0-17** runtime `BUDGET_EXCEEDED` has no HTTP mapping; 413 vs 422 ambiguous | §17 response table; §18 | Split the "capacity" row into four: **413 `PAYLOAD_TOO_LARGE`** (transport body limit only); **422 `BUDGET_EXCEEDED`** (declared structural bound at admission, nothing written); **429 `ADMISSION_LIMIT`** (open proposals, rate); **422 `BUDGET_EXCEEDED`** during a later checkpoint (the response carries action status SUSPENDED, or FAILED_PRECOMMIT for an activation checkpoint, plus the last committed checkpoint ID). 503 stays reserved for operational interruption | error codes only | New **T53**: oversized body, over-bound definition, and budget exceeded in a later checkpoint produce exactly those responses, and earlier checkpoints stay intact | G1 / WP2, WP4 | Adrian |
| **G0-18** "forward-clock anomaly" undefined | §10 deadlines | All workers read deadline time from one shared time authority, once per commit. While a scope has open decisions, the lease holder commits a watermark heartbeat every 30 s. A **forward anomaly** is authority time exceeding the last heartbeat by more than the interval plus a tolerance (default 30 s, campaign-visible). Deadlines that passed inside such a gap do not expire the decision: it becomes SUSPENDED for operator review. An outage looks the same as a clock step and gets the same safe treatment. A backward step is evaluated against the watermark, so it never reopens an expired decision | none | New **T54**: a clock step or outage passes an open deadline; the decision is SUSPENDED for review, not expired or answered; a backward step never reopens | G1 / WP5 | Adrian |
| **G0-19** no requirement for ruleset independence (F11) | §23 requirement table | Add **CE-RULESET-01**, "Ruleset-namespaced clocks/events and the contrasting-ruleset boundary; §§2, 11", mapped to T34. Remove T34 from CE-GUIDE-01, where it was mis-filed | none | Existing **T34** | G2 | Adrian |
| **G0-20** naming drift; `Timestamp` not UTC | §10 wording; schema `Timestamp` | The prose uses schema names: "decision version" (was "prompt version") and "timeout policy" (was "resolution policy"). Slot consumption is named as a reaction-slot property. `Timestamp` gets a pattern that requires UTC `Z` | `Timestamp` pattern tightened (contract 1.1.3) | Schema negative check: a `+02:00` offset is rejected | G1 / WP1 | Adrian |

Effect on the G1 plan once approved:

- G1 acceptance grows by T52–T54, and G2 keeps T34 under its new requirement.
- WP1 validates UTC timestamps. WP2/WP4 implement the error-code split. WP4 adds the CANCELLED path.
  WP5 adds the heartbeat watermark.
- None of this changes G1 scope boundaries.
