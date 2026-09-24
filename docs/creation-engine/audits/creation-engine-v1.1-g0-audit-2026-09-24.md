# Roll Drauf Creation Engine — G0 audit of v1.1 (Audit Candidate 1)

24 September 2026 · Second adversarial audit (spec §22 gate G0) · Read-only review

**Verdict: G0 is not passed yet — conditional pass.**

- Three **high** findings sit inside the proposed G1 slice: G0-01 (privacy), G0-02 (migration
  authority) and G0-03 (wire identity).
- G0's exit criterion is "no unresolved high-risk contradiction in proposed slice", so these must
  close first.
- Each has a small, text-level closure proposed below. None needs a redesign.
- G0 passes when the architecture lead adopts G0-01…G0-03 into a versioned revision (v1.1.1), and
  when the medium findings that touch G1 are resolved or explicitly accepted (DAD-M transition rule:
  no open medium-or-higher finding may remain unresolved or unaccepted).

The v1.1 revision is a large improvement over v1.0. Its checkpoint model, receipts, effect algebra,
execution locks and quality axes are concrete enough to implement and test. The findings are
mostly about precision at boundaries: what a client may see, who is authoritative during
migration, and exactly what a wire message identifies.

## Scope, independence and evidence

- **Reviewed.** The full `creation-engine-v1.1.md` (§§1–25). Per the #reporte brief, §§8–14 got
  first focus: crash/retry, post-roll choices, stale prompts, reaction ordering, undo/grants, secret
  propagation. Then the companion schema, wire examples and acceptance catalogue against the prose.
  Then an independent closure review of F01–F13 (G0 exit criterion).
- **Package integrity.** All ten file hashes match `review-package-manifest.json`. Copy in `docs/creation-engine/v1.1/`.
- **Independence.** The reviewer did not author v1.0 or v1.1. The reviewer did author the G1 plan
  (`dadm/artifacts/programs/milestone_program_creation_engine_g1.md`), so this audit does not
  review that plan. The accountable acceptance of this audit stays with the architecture lead
  (spec §22 names "architecture lead and security reviewer").
- **Nothing was changed.** No application code, database, deployment or Discord message was
  changed. The checks below are document and schema checks, not engine tests.

Severity scale (same as the v1.0 audit):

- **High:** could corrupt state, expose restricted information, or force substantial redesign in the affected release.
- **Medium:** materially weakens implementability, portability or acceptance.
- **Low:** clarity or traceability.

### Mechanical checks performed

| Check | Result |
| --- | --- |
| Companion schema is valid JSON Schema Draft 2020-12 (independent re-run, `jsonschema` 4.26) | Pass |
| `wire-examples.json` valid command validates | Pass |
| All 46 acceptance cases in JSON match the §21 table text exactly | Pass (46/46) |
| Every T-ID is assigned to at least one gate (§22) and one requirement (§23) | Pass |
| Probe: InvokeActivity naming the item occurrence it activates | Rejected by schema (see G0-03) |
| Probe: retry with same idempotency key and a new `commandId` | Schema-valid; semantics undefined (see G0-05) |
| Probe: unkeyed SHA-256 context digest over one hidden fact | Hidden target HP (37) recovered in 38 guesses (see G0-01) |

## Findings

| ID | Severity | Class | Finding | Affects G1 |
| --- | --- | --- | --- | --- |
| G0-01 | **High** | privacy | Client-visible digests over restricted facts are unkeyed and can be brute-forced | T09–T12, T22, T25 |
| G0-02 | **High** | correctness | Migration authority is per character in one sentence and per scope in the next; mixed scopes are undefined | T01–T03 |
| G0-03 | **High** | correctness | `InvokeActivity` cannot name the occurrence whose activity/charges are used | Magic item, T04, T06 |
| G0-04 | Medium | correctness | Two different suspension clocks for mandatory decisions | T11 |
| G0-05 | Medium | correctness | Relationship of `commandId` and `idempotencyKey` is undefined | T06, T07 |
| G0-06 | Medium | availability | `expectedScopeVersion` semantics per operation are undefined | T04, T09–T12 |
| G0-07 | Medium | correctness | Authority epoch vs worker fencing epoch vs restore are not distinguished | T05, T06 |
| G0-08 | Medium | security | "Control" of an occurrence and "campaign operator" are used but never defined | T09, T24 |
| G0-09 | Medium | correctness | `AdjustResource` behavior at resource bounds is unspecified | T02, T04 |
| G0-10 | Medium | contract drift | Formula schema lacks the boolean/arithmetic nodes the prose names | T14, T15 |
| G0-11 | Medium | contract gap | No wire contract for authoring, override, migration, operator or instantiation commands | T02, T31, T32 |
| G0-12 | Medium | contract conflict | Inert legacy metadata must round-trip, but schema-unknown fields are rejected on commit | T01 |
| G0-13 | Medium | product | Gate blocks all token movement, although movement is representation state | T03 |
| G0-14 | Medium | traceability | §2 manual-play MUSTs have no requirement ID or acceptance scenario | — |
| G0-15 | Medium | correctness | Reaction candidate order vs initiative reorder mid-slot is unspecified | G2 only |
| G0-16 | Low | contract | `PROPOSED` has no path to `CANCELLED`, yet precommit proposals "expire as CANCELLED" | T12 |
| G0-17 | Low | contract | HTTP mapping of a runtime `BUDGET_EXCEEDED` (after admission) and 413 vs 422 are ambiguous | T13, T26 |
| G0-18 | Low | ops | "Forward-clock anomaly" detection is undefined | T11 |
| G0-19 | Low | traceability | No requirement ID for ruleset independence (F11); T34 is reachable only via CE-GUIDE-01 | — |
| G0-20 | Low | contract drift | Naming drift (prose "prompt version", "resolution policy"); `Timestamp` not constrained to UTC | T11 |

---

### G0-01 (High, privacy) — Unkeyed digests disclose restricted facts

**Evidence.**

- §10: "The context digest binds the resolved snapshot, lock, targets, required resources, policy
  version, and mechanical facts relevant to the question."
- The responder must echo that digest, so it is delivered to the client.
- §6 prescribes plain "RFC 8785 … then SHA-256" hashing, and the schema's `Digest` type is the
  unkeyed `sha256:` form.
- The `Receipt` requires `outcomeDigest`, and its schema says only that a public projection "may
  omit restricted identifiers".
- §14 requires that outputs never reveal hidden names, source IDs "or exact counts of omitted
  sources", and it lists receipts among the covered outputs.

**Counterexample.**

- A player is asked whether to spend a flame charge against a hidden target.
- Every other input in the context is visible to mechanical participants: state version (§14
  discloses it), lock digest, own charges, policy version.
- Enumerating the hidden HP and re-hashing found the value in 38 guesses (probe above).
- The same works for low-entropy outcomes behind `outcomeDigest`.
- A public `eventIds` list reveals how many events a checkpoint produced about hidden targets.

**Required closure (proposed v1.1.1 text).**

- "Digests exposed to a principal are either content digests over content that principal may read,
  or opaque tokens."
- `contextDigest` becomes a context token: HMAC-SHA-256 under a per-scope server secret, rotated with
  the policy epoch, or an opaque server nonce bound to the stored context hash.
- `outcomeDigest` is internal. A public receipt MUST omit it or present a context token.
- Public `eventIds` MUST contain only events the recipient may read.
- The schema's "may omit" becomes "MUST omit".

**Pass condition.** A player receives a decision and receipt concerning a hidden target. Offline
enumeration over candidate values never matches the delivered token. The public receipt reveals
no count of omitted events.

### G0-02 (High, correctness) — Migration authority is per character and per scope at once

**Evidence.**

- §5 says "No character enters ENGINE until its declared parity checks pass … approved by its
  authorized controller and campaign operator". That makes state per character.
- The next sentence says "Cutover fences all writers for the affected runtime scope … commits the
  migration ledger and authority switch atomically". That makes it per scope.
- §8/§9 promise "serializable observable outcomes within a scope" and a scope gate. Legacy writers
  are neither gated nor versioned.

**Counterexample.**

- In one campaign, character A is ENGINE and character B is LEGACY.
- A's engine attack reads B's AC as a legacy column.
- During A's pending decision, B's owner changes AC through legacy `PUT /characters/<id>`.
- The checkpoint's revalidation reads a value that no gate serialized.
- If A's attack damages B, the engine must write a resource it does not own.
- Separately: if one player refuses parity approval, it is unclear whether the whole campaign blocks.

**Required closure (proposed v1.1.1 text).**

- "Migration state is a property of the RuntimeScope. Per-character parity approvals are
  preconditions of the scope's cutover. A scope's instances change authority together."
- "Until cutover, engine evaluation in a LEGACY/SHADOW scope is preview-only."
- "A character without a campaign is migrated within its owner's personal sandbox scope. Joining a
  campaign after cutover uses the transfer protocol or is rejected with a specific code."

**Pass condition.** A fixture scope with two characters cuts over both atomically. An attempt to
cut over one alone is rejected. No engine action ever reads a legacy-authoritative value.

### G0-03 (High, correctness) — Invocation cannot identify its source occurrence

**Evidence.**

- `InvokeActivityPayload` = `actorInstanceId`, `activityRevisionRef`, `activityId`, `targets`, with `additionalProperties: false`.
- §13: "Stackable items instead create separate occurrence IDs."
- §4: an independent duplicate "receives a new occurrence".
- §7: costs spend resources owned by an owner scope.

**Counterexample.**

- A character holds two flame swords, i.e. two occurrences of one revision, with 3 and 1 charges.
- `InvokeActivity` can only name the revision, so the server cannot tell which sword's charge to debit.
- Two conforming implementations can debit different pools.
- Adding the missing field is rejected by the schema (probe above).
- Also, `actorInstanceId` and `AdjustResourcePayload.instanceId` are bare IDs, although §4 makes
  `InstanceRef` a distinct tagged wire type.

**Required closure (proposed v1.1.1 schema change).**

- Add a required `sourceInstance: InstanceRef` (equal to the actor for innate activities).
- Change `actorInstanceId`/`instanceId` to `InstanceRef`, with `scopeId` equal to the envelope `scopeId`.

**Pass condition.** With two swords, invoking sword 2 debits only sword 2. An ambiguous invocation
cannot be expressed.

### G0-04 (Medium) — Two suspension clocks for mandatory decisions

- §10 sets the response timeout at 120 s by default (policy range 30–600 s).
- It says "A mandatory unknown answer suspends resolution", and also "An active frame awaiting
  mandatory input for 600 seconds becomes SUSPENDED".
- T11 and `timeoutPolicy: suspend_mandatory` imply suspension at the deadline.
- Between a 120 s deadline and 600 s, the decision is expired (unanswerable) and the operator is not
  yet notified. Who may reissue a prompt is unstated.
- **Closure:** at a mandatory decision's deadline the action enters SUSPENDED and operators are
  notified immediately. 600 s is the policy maximum. Reissue is an explicit operator command that
  creates a new decision version.

### G0-05 (Medium) — `commandId` vs `idempotencyKey`

- Both are required. The request digest "excludes transport-only metadata", but whether
  `commandId` is transport-only is not stated.
- If it is digested, every retry with a fresh `commandId` returns `IDEMPOTENCY_KEY_REUSE` and breaks T06.
- **Closure:** `commandId` is a client correlation ID, excluded from the digest. Retries MUST reuse
  `idempotencyKey`. Receipts return the original `commandId`.

### G0-06 (Medium) — `expectedScopeVersion` per operation

- The §24 shared-charge trace implies exact-match semantics.
- Applied to `ResolveDecision` inside an active frame, exact match rejects valid answers whenever
  an unrelated child checkpoint committed first. That produces refresh churn during reaction chains.
- **Closure:** exact match for `InvokeActivity`/`AdjustResource`. For `ResolveDecision`, admission
  binds on `decisionVersion` and the context token (G0-01), and `expectedScopeVersion` must be at
  least the decision's creation version.

### G0-07 (Medium) — Epochs are not distinguished

- §5 uses a client-facing authority epoch. §9 uses durable writer fencing epochs. §§10/14 add policy and entitlement epochs.
- If worker failover bumps the client epoch, every failover forces all clients to refresh.
- Restore is not required to fence pre-restore retries. A retried command could then redraw a roll
  the client had already seen.
- **Closure:** the authority epoch changes only on authority transfer (cutover, rollback review,
  restore), and restore MUST bump it. Worker fencing epochs are internal and never on the wire.

### G0-08 (Medium, security) — "Control" and "operator" are undefined

- §14 grants "Invoke actor activity" to "current control of that occurrence".
- §5 requires approval by an "authorized controller and campaign operator". §10 refers to "authorized operators".
- None of these relations is defined or mapped to the VTT's campaign roles. Default-deny keeps
  this fail-closed, but implementations will diverge.
- **Closure:** define `controls(principal, occurrence)` and `operates(principal, scope)` as
  policy-granted relations, with the adapter's default mapping:
  - the character owner controls its occurrence;
  - campaign `DM`/`CO_DM` hold the operator capability;
  - token ownership grants presentation control of that representation only;
  - delegation is explicit and audited.

### G0-09 (Medium) — `AdjustResource` at bounds

- §7 makes `0 ≤ current ≤ max` invariant but defines behavior only for maximum decreases.
- A delta that would cross a bound may clamp (legacy `adjust_hp` does) or be rejected.
- **Closure:** each Resource declares `adjustBoundPolicy` (`reject` | `clamp_report_delta`), and
  receipts report the applied delta.

### G0-10 (Medium) — Formula schema vs prose

- §6 names "boolean operators, bounded arithmetic and registered pure functions".
- The schema `Formula` has `literal`, `read`, `call`, and `if` (with a predicate binding) only.
- **Closure:** state that arithmetic is expressed through registered core functions with declared
  fuel (list them), and that boolean logic lives in Predicate definitions (publish that schema).
  Alternatively, add the nodes.

### G0-11 (Medium) — Missing wire contracts for G1 commands

- The schema covers three runtime commands.
- G1 also needs:
  - authoring commands (§15 "Every user answer is an atomic draft command");
  - override and base-edit commands (§5 legacy-write translation);
  - migration commands;
  - operator resolution (§10);
  - instantiation into a scope.
- §17 says feature registries add versioned payload schemas.
- **Closure:** a reviewed registry addendum before G1 Deploy. Drafted as
  `docs/creation-engine/addenda/creation-engine-v1.1-registry-addendum-g1.md`; it requires review by
  someone other than its author.

### G0-12 (Medium) — Inert legacy metadata vs strict schemas

- §5: unrecognized data "remains inert metadata … round-trips".
- §6: "schema-unknown fields are rejected on commit".
- No container is declared.
- **Closure:** an adapter-schema component `legacyMetadata`: opaque JSON, never addressable by
  formulas or selectors, policy-projected, and round-tripped byte-identically.

### G0-13 (Medium, product) — Gate and token movement

- §9's gate "spans … token movement".
- §§4–5 classify movement as representation (presentation) state.
- In a scope without spatial mechanics, a pending or suspended action therefore freezes all token
  movement, potentially until an operator intervenes. That is a sharp regression against current
  VTT behavior.
- **Closure (product owner decision):** movement is a gated mechanical command only where the
  scope's lock declares a geometry profile that observes that map. Otherwise it is ungated
  representation state. G1 has no spatial mechanics.

### G0-14 (Medium) — Manual play is untested

- §2's MUSTs say manual outcomes are recorded, distinguished in the UI, and never grant
  unavailable mutation privileges.
- They have no requirement ID and no T-case.
- **Closure:** add `CE-MANUAL-01` and a scenario, e.g. "manual adjudication records adjudicator and
  reason; UI labels it; a player cannot use manual mode to adjust another player's resource".

### G0-15 (Medium, G2) — Reaction candidate order

- The candidate order depends on initiative.
- The spec does not say whether the ordered candidate list is fixed at slot creation (and part of
  the context), or what happens when an operator reorders initiative mid-slot. Re-offering to a
  candidate who already declined is possible.
- **Closure:** snapshot the candidate list into the slot and its context. An operator reorder
  invalidates and restarts the slot, excluding recorded decliners.

### Low findings

- **G0-16:** add `PROPOSED → CANCELLED`, or state that `PROPOSED` is transient and never persisted.
- **G0-17:** map a post-admission `BUDGET_EXCEEDED` explicitly (proposal: 422 with suspended
  checkpoint status). Define 413 as the transport-size limit only.
- **G0-18:** define "forward-clock anomaly" (proposal: server time exceeds the scope watermark plus a
  configured bound).
- **G0-19:** add a requirement for ruleset independence (F11) mapping T34.
- **G0-20:** align names: prose "prompt version" = `decisionVersion`; "resolution policy" =
  `timeoutPolicy` plus slot rules. Constrain `Timestamp` to UTC (`Z`).

## F01–F13 closure review (G0 exit criterion)

| Finding | v1.1 response | G0 assessment |
| --- | --- | --- |
| F01 migration/authority | §5 field authority, epochs, parity gate, rollback limits | **Not closed:** G0-02 (high); G0-12 medium |
| F02 atomicity/retry | Receipts, checkpoints, recorded randomness, outbox | Closed at design level, subject to G0-05, G0-06, G0-07 |
| F03 human resolution | State machine, bound decisions, deadlines | Closed at design level, subject to G0-04, G0-16; G0-15 for G2 |
| F04 deterministic semantics | Rationals, fixed stages, conflicts, clocks | Closed; G0-09, G0-10 need wording |
| F05 pinned compatibility | Execution lock, three-way updates, replay levels | Closed. Lock schema matches prose |
| F06 secrecy | Default-deny, all outputs, declassification | **Not closed:** G0-01 (high); G0-08 medium |
| F07 data-only safety | Deterministic fuel and import limits | Closed; G0-17 low |
| F08 identity | Definitions/revisions/occurrences/representations | **Not closed at the wire level:** G0-03 (high) |
| F09 reversal | Grant ledger, compensation | Closed at design level (exercised in G2) |
| F10 compiler | Bounded interview, invalidation, quality axes | Closed in prose; wire contract missing (G0-11) |
| F11 generic rules | Namespaced clocks, profiles | Closed; G0-19 traceability |
| F12 delivery | Earlier integration/usability gates | Closed |
| F13 evidence/requirements | Precedence, catalogue, source register | Closed; G0-14, G0-20 |

## Limitations

- **Sources not re-checked.** The competitor/source register (§25) was not re-verified in this
  audit. Only the identities of RFC 8785 and JSON Schema 2020-12 were relied upon. Those sources
  shape research context, not G1 contracts.
- **No behavior tested.** Probe results demonstrate schema properties and a hashing consequence.
  They do not test an engine.
- **Other gates only screened.** Findings are complete for the G1 slice. Later-gate sections
  (§§16, 19 and the G3–G8 parts of §§12, 17) were screened for contradictions only.

## Integration notes for later gates (not findings against the spec)

- The VTT accepts client-provided rolls via the `external:roll` socket event (Beyond20). Under
  ENGINE authority these must become the §9 "separately labelled, permissioned manual-roll command".
  This is not needed for G1.
- The legacy sheet serializer returns all of `character_data` to campaign members
  (`vtt/characters/routes.py:241`). §14's last paragraph already requires the compatibility endpoint
  to use projection policy.

## Next step

1. The architecture lead accepts or modifies closures for G0-01…G0-03 and publishes v1.1.1 (errata).
2. The product owner decides G0-13. Medium findings touching G1 are resolved or explicitly accepted.
3. The registry addendum (G0-11) gets review by someone other than its author. Then G0 is recorded
   as passed, and G1 Deploy can be authorized per the G1 plan.
