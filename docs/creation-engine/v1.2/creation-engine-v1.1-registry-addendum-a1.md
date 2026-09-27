# Creation Engine v1.1 — Registry Addendum A1 (G1 command set)

**Status:** approved on 24 September 2026 by Matt (product owner; non-author review), relayed by
Adrian. This closes audit finding G0-11. Companion wire contract of spec v1.1.4.

**Date:** 24 September 2026.

**Extends:** `urn:rolldrauf:creation-engine:contracts:1.1.3` through the registry mechanism of spec
§17 ("Feature registries add versioned payload schemas for other commands").

**Built on:** v1.1.3 (errata E1 + E2 + E3, adopted 2026-09-24): opaque context tokens (G0-01), tagged
`InstanceRef` for every occurrence (G0-03), and the `controls`/`operates` relations (G0-08). Envelopes carry `contractVersion` "1.1.3".

**Artifacts:**

- `creation-engine-v1.1-registry-a1.schema.json`: JSON Schema 2020-12, 24 operations.
- `creation-engine-v1.1-registry-a1-verification.json`: examples and shape checks.

This addendum adds wire contracts only. It does not change any semantic rule of v1.1. If anything
here conflicts with the specification, the specification wins and the conflict blocks the affected
feature (§1).

## 1. Why the addendum exists

The companion schema defines three runtime commands (`InvokeActivity`, `ResolveDecision`,
`AdjustResource`). G1 also needs:

- **Authoring:** §15, "Every user answer is an atomic draft command carrying expected draft
  version"; §13, draft undo; §15, quality axes.
- **Legacy-write translation:** §5. Calculated values translate "to an authorized override
  command", ability scores to "base edit or explicit override", and equipment changes to commands.
- **Operator intervention:** §10, "Operators can reassign an eligible adjudicator or finish
  manually"; G0-04 adds reissue.
- **Migration:** §5, states and cutover. In G1, cutover happens in fixture scopes only.
- **Personal sandbox and instantiation:** §8 "personal sandbox"; §14 "Deploy/update campaign content".

## 2. Contract rules

1. **Operation names are immutable identifiers.** A payload schema never changes after
   publication. A breaking change gets a new name (`RecordDraftDecisionV2`). This keeps the core
   envelope untouched (it is closed with `additionalProperties: false`), and still rejects an
   "unknown type/version" (§17).
2. **Runtime registry schemas travel in the execution lock's `schemaBundle`** (§12). A draft records
   the authoring registry bundle and schema type version it was created with.
3. **The envelope family follows the mutation scope.** Spec §8: commands carry "expected
   scope/draft version, authority epoch, lock digest where mechanical". Idempotency identity is
   always `(authenticated principal, mutation scope, idempotency key)`.

| Family | Mutation scope | Version field | Lock digest | Operations |
| --- | --- | --- | --- | --- |
| `WorkspaceEnvelope` | the principal's personal workspace | — (creates a new scope) | no | CreateDraft, CreateSandboxScope, OpenLegacyCampaignScope |
| `DraftEnvelope` | one draft | `expectedDraftVersion` | no | RecordDraftDecision, SkipDraftQuestion, RetractDraftDecision, ApplyDraftPreset, RevertDraft, CommitDraftRevision |
| `MechanicalEnvelope` (same fields as the core envelope) | a RuntimeScope; passes the scope gate (§9) | `expectedScopeVersion` | yes | InstantiateRevision, SetItemEquipped, SetValueOverride, ClearValueOverride, SetBaseValue, ReissueDecision, ReassignDecisionResponder, ResumeSuspendedAction, ResolveActionManually |
| `ScopeEnvelope` | a RuntimeScope; administrative, not mechanical | `expectedScopeVersion` | no | MapLegacyCharacter, BeginScopeShadow, ApproveParityDifference, FreezeScopeForCutover, CommitScopeCutover, AbortScopeCutover |

**No principal on the wire.** No envelope carries a principal. The server derives it from
authentication (§8). The verification file shows a spoofed principal field being rejected for
every operation.

## 3. Operation catalogue

The capability column names the §14 matrix row. "Controller" and "operator" use the G0-08
definitions: the character owner controls its occurrence; campaign `DM`/`CO_DM` are operators;
the sandbox owner is the operator of their sandbox.

| Operation | Capability (§14) | Spec | Serves |
| --- | --- | --- | --- |
| CreateDraft | Edit private draft (workspace owner) | §4, §15 | T31, T32, T45 |
| CreateSandboxScope | Workspace owner. Lock resolved server-side from exact revisions (§12) | §8, §12 | Magic item |
| OpenLegacyCampaignScope | Operator of that legacy campaign | §5, §8 | T01–T03 |
| RecordDraftDecision | Edit private draft | §15 | T31, T32, T45 |
| SkipDraftQuestion | Edit private draft. Optional questions only | §15 | T31, T45 |
| RetractDraftDecision | Edit private draft | §15 | T31 |
| ApplyDraftPreset | Edit private draft | §15 "explicitly choosing a preset" | T45 |
| RevertDraft | Edit private draft | §13 draft undo | T32 |
| CommitDraftRevision | Edit private draft | §4, §15 quality axes | T31, T35 (quality-claim rule) |
| InstantiateRevision | Sandbox: owner. Campaign: operator plus deploy capability | §4, §14 | Magic item, T03 |
| SetItemEquipped | Control of the holder occurrence | §9 (equipment is gated), §5 | T02, T22 |
| SetValueOverride / ClearValueOverride | Explicit adjust permission. Binding declared overrideable | §4, §5 | T01, T02 |
| SetBaseValue | Control plus base-edit permission | §5 | T02 |
| ReissueDecision | Operator | §10, G0-04 | T11 |
| ReassignDecisionResponder | Operator | §10 | T09 |
| ResumeSuspendedAction | Operator | §9 | T13 |
| ResolveActionManually | Operator. Recorded as manual outcome (§2) | §2, §9, §10 | T11, T13 |
| MapLegacyCharacter | Operator | §5 | T01 |
| BeginScopeShadow | Operator | §5 | T01 |
| ApproveParityDifference | Controller or operator; both are required per discrepancy | §5 | T01 |
| FreezeScopeForCutover / CommitScopeCutover / AbortScopeCutover | Operator. G1: fixture scopes only | §5, G0-02 | T02, T03 |

## 4. Semantic rules

### 4.1 Authoring: one command vocabulary for all three modes

§2: "All authoring surfaces MUST emit the same authorized semantic commands."

- **One owning question per path.** Every author-editable canonical path in a registered schema
  type is owned by exactly one registered question (stable ID and version, §15).
- **Guided mode** asks the next question by the deterministic §15 ordering.
- **Structured mode** shows the same questions grouped non-linearly.
- **Advanced mode** edits a typed canonical value, which the registry maps to its owning question.
- **All three emit `RecordDraftDecision`.** Switching modes is a view change, never a command.
  Equivalent answers therefore produce equivalent canonical results by construction (T31).

The rules the draft commands follow:

- **`RecordDraftDecision`** is one atomic draft command (§15).
  - It records question ID/version, the typed answer, author, `promptLocale`, the resulting
    canonical mutations, and invalidated descendants.
  - Descendants of a changed answer become visibly stale. They are never silently kept (§15, T31).
  - `answer` is a core `DecisionAnswer`, or `structured` for typed values (for example a
    `Duration`). It must match the question's registered answer schema exactly, with no coercion
    and no defaulting.
- **`SkipDraftQuestion`** applies to optional questions only. On a required creative value it is
  rejected: `QUESTION_REQUIRED`, §15 "no implicit default".
- **`ApplyDraftPreset`** carries the `previewDigest` of the preset preview the author was shown.
  - This digest covers content the author may read, so it is a permitted content digest under G0-01.
  - A changed preset returns `PRESET_PREVIEW_STALE`.
  - Applied values become user-approved source decisions (§15).
- **`RevertDraft`** restores an earlier draft state as a new version. The decision log is kept (§13).
- **`CommitDraftRevision`** creates an immutable revision (§4) with the declared mechanical quality.
  - The server verifies the claim against §15's quality table.
  - A false claim returns `QUALITY_CLAIM_UNMET`, listing the unmet gates (compare T35).
  - The revision records the registry bundle, question versions and compiler version (F10 closure).

### 4.2 Runtime commands (mechanical family)

- **Standard admission.** Each command passes the full §8 admission order and the §9 scope gate.
  Each commits as one checkpoint with a receipt, events and outbox records.
- **`InstantiateRevision`** requires the revision to be in the scope's execution lock
  (`REVISION_NOT_IN_LOCK` otherwise). It creates a new occurrence (§4). Adding content to a
  campaign lock is the G3 update workflow; in G1, campaign locks exist only in fixture scopes.
- **`SetValueOverride`** is allowed only on bindings the pinned schema declares overrideable
  (`BINDING_NOT_OVERRIDEABLE`). It is a versioned command with reason and provenance (§4).
  Arbitrary patches do not exist.
- **Operator commands** are checkpoints inside the current frame. They invalidate dependent prompts
  (§10). `ResolveActionManually` yields the operator-finalized `COMPLETED` outcome (§9), and its
  result is labelled manual (§2).

### 4.3 Migration (scope family), following G0-02

- **Scope-level state.** Migration state belongs to the RuntimeScope:
  `LEGACY → SHADOW → FROZEN_FOR_CUTOVER → ENGINE`, with `ROLLBACK_REVIEW` per §5.
- **Mapping.** `MapLegacyCharacter` writes the bijective ledger entry
  `(vtt.character, id, migrationVersion) → opaque ID` (§5).
- **Shadow.** `BeginScopeShadow` creates the scope's first lock for the "Roll Drauf Light G1 subset"
  ruleset (decision D3). Shadow evaluation is read-only.
- **Approvals.** A discrepancy counts as approved only when both a controller approval and an
  operator approval are recorded (§5). The approving capacity comes from authentication, never
  from the payload.
- **Commit.** `CommitScopeCutover` binds the parity report the operator reviewed
  (`parityReportDigest`). It fails with `PARITY_UNRESOLVED` or `SCOPE_NOT_QUIESCENT`.
- **G1 restriction.** Cutover is rejected with `CUTOVER_FIXTURE_ONLY` unless the scope is flagged
  as a fixture (G1: "no live cutover").

## 5. Error codes (in addition to the §17 core codes)

| Code | HTTP | Meaning |
| --- | --- | --- |
| DRAFT_VERSION_CONFLICT | 409 | `expectedDraftVersion` is not the current draft version. The response carries the authorized diff |
| QUESTION_VERSION_STALE | 409 | The question version is no longer current for this draft's schema type |
| QUESTION_NOT_APPLICABLE | 422 | The question is suppressed in the current constraint graph |
| ANSWER_TYPE_MISMATCH | 422 | The answer does not match the registered answer schema; no coercion |
| QUESTION_REQUIRED | 422 | Skip attempted on a required question |
| PRESET_PREVIEW_STALE | 409 | The preset changed since preview |
| QUALITY_CLAIM_UNMET | 422 | Declared mechanical quality not met |
| REVISION_NOT_IN_LOCK | 422 | Instantiation of content outside the scope lock |
| BINDING_NOT_OVERRIDEABLE | 422 | Override on a path the schema does not declare overrideable |
| ACTION_VERSION_CONFLICT | 409 | `expectedActionVersion` is stale |
| MIGRATION_STATE_CONFLICT | 409 | Transition not allowed from the current migration state |
| PARITY_UNRESOLVED | 409 | Cutover with unapproved discrepancies |
| SCOPE_NOT_QUIESCENT | 409 | Cutover with pending actions (§5) |
| CUTOVER_FIXTURE_ONLY | 403 | G1: cutover of a non-fixture scope |
| LEGACY_FIELD_READ_ONLY | 409 | Spec §5 code; HTTP mapping proposed here |

## 6. Legacy-write translation for ENGINE-state scopes (T02)

The writers come from the G1 plan's Discover inventory. In LEGACY/SHADOW scopes none of them
changes behavior.

| Legacy writer | Engine behavior |
| --- | --- |
| `PUT /characters/<id>`: `ac`, `hp_max`, `mana_max` | `SetValueOverride` on the declared binding, or `LEGACY_FIELD_READ_ONLY` if not overrideable |
| `PUT`: `hp_current`, `mana_current` | `AdjustResource` with delta = requested − current, reason "legacy sheet edit" |
| `PUT`: `str` … `cha` | `SetBaseValue` |
| `PUT`: `level`, `xp`, `character_data` content/progression | `LEGACY_FIELD_READ_ONLY` (progression is G2). Unknown metadata stays inert and round-trips (G0-12) |
| `POST /characters/<id>/level-up` | `LEGACY_FIELD_READ_ONLY` (G2) |
| `token:update` `hp_current`/`hp_max` | `AdjustResource` / `SetValueOverride` on the occurrence. `x`/`y` stay representation state (G0-13) |
| `token:create` HP fields | Ignored. The token becomes a representation of the occurrence (§5) |
| `adjust_hp` (combat) | `AdjustResource` |
| Trap damage (`combat/traps.py`) | Rejected for ENGINE occurrences until traps are engine activities; manual resolution meanwhile |
| Equipment `is_equipped` toggle | `SetItemEquipped` |
| Equipment/inventory create/delete, loot transfer | `LEGACY_FIELD_READ_ONLY` in G1 (item transfer semantics are §13/G2+) |
| Sheet read, export | Engine projection policy, never raw `character_data` (§14) |

All of these pass through one function, `legacy_write_guard`, so the rule lives in one place (see §7.5).

## 7. Code structure in `vtt/`

Terms follow the codebase-design vocabulary: module, interface, seam, adapter, depth, leverage, locality.

### 7.1 The deep module: `CommandKernel`

```python
# vtt/creation_engine/kernel/__init__.py
@dataclass(frozen=True)
class Principal:
    user_id: int                      # from the verified JWT, never from the payload (§8)

class CommandKernel:
    def submit(self, principal: Principal, envelope: Mapping[str, object]) -> Receipt: ...
    def receipt(self, principal: Principal, scope: MutationScope, idempotency_key: str) -> Receipt | None: ...
```

- **Two entry points.** Everything else sits behind them: envelope/payload schema validation, the
  §8 admission order, idempotency with request digests, version and epoch checks, the scope gate,
  the checkpoint transaction, recorded randomness, receipts, domain events and outbox rows.
- **Interface invariants:**
  - `submit` is idempotent per `(principal, mutation scope, key)`.
  - Domain outcomes, rejections included, come back as a `Receipt`. Only programmer errors raise.
  - One call commits at most one checkpoint.
  - No network I/O happens inside the transaction. Delivery runs from the outbox after commit (§9).
- **Leverage:** 27 operations (24 here plus 3 core) share one admission path.
- **Locality:** an idempotency or authorization bug is fixed once.
- **Deletion test.** Without the kernel, every route would re-implement what
  `play_transfer_loot` does today (`vtt/play/routes.py:645-760`): a global key, no request
  binding, lookup-then-insert. That is the pattern §8 rules out.

### 7.2 The per-operation extension point: a registry entry

```python
# vtt/creation_engine/registry.py
@dataclass(frozen=True)
class Operation(Generic[P]):
    name: str                          # "RecordDraftDecision" — immutable (rule 2.1)
    family: Family                     # WORKSPACE | DRAFT | MECHANICAL | SCOPE
    payload: type[P]                   # frozen dataclass, parsed after schema validation
    capability: Capability             # §14 row
    decide: Callable[[Snapshot, P, Context], Decision]   # pure

OPERATIONS: Mapping[str, Operation] = index(drafts.OPERATIONS + content.OPERATIONS
                                            + overrides.OPERATIONS + operator.OPERATIONS
                                            + migration.OPERATIONS + runtime.OPERATIONS)
```

- **`decide` is pure** (functional core). It takes an immutable snapshot, the typed payload, and a
  context (principal, clock, randomness ports). It returns `Accepted(mutations, events, result)` or
  `Rejected(code, detail)`.
- **The kernel is the imperative shell.** It loads the snapshot inside the transaction, calls
  `decide`, and persists everything atomically.
- **Explicit tuples per family, not decorator magic.** The registry is greppable and import order
  cannot change it.

### 7.3 Admission reads like §8

```python
ADMISSION = (validate_envelope, authenticate, require_usable_account, require_scope_membership,
             require_capability, require_resource_relationship, validate_payload_schema,
             parse_payload, validate_semantics, check_expected_versions, check_execution_profile)
```

- Each step is a small function returning `None` or a `Rejected`. Transactional revalidation
  repeats the relevant checks under the scope row lock.
- `validate_envelope` runs first only because membership needs the scope ID. The payload schema is
  checked after authorization, so unauthorized callers learn nothing about payload shape.
- **Parse, don't validate.** After `parse_payload`, domain code never touches raw dicts.

### 7.4 Transports are thin adapters

```python
# vtt/creation_engine/transports/http.py
@ce_bp.route("/api/ce/commands", methods=["POST"])
@jwt_required()
def post_command():
    principal = principal_from_jwt()
    receipt = kernel.submit(principal, strict_json(request))
    return jsonify(project_receipt(receipt, principal)), status_for(receipt)
```

- The Socket.IO adapter (`transports/socket.py`, event `ce:command`) calls the same `submit` (§17:
  "REST and WebSocket transports use the same command IDs, validation and receipts").
- `status_for` is the §17 table plus §5 of this addendum.
- `project_receipt` applies G0-01: no internal digests, filtered event IDs.
- `strict_json` rejects duplicate keys and non-finite numbers (§6). Flask's default parser keeps
  the last duplicate key.

### 7.5 Dependency categories and seams

| Dependency | Category (DEEPENING) | Seam decision |
| --- | --- | --- |
| Evaluator, compiler, policy, `decide` functions | In-process | No adapter. Tested directly, including property tests (§21) |
| PostgreSQL | Local-substitutable (disposable PG 16 in tests) | Internal seam, no port. T04–T06 need the real engine's locking (§21) |
| Clock, randomness | Needs controlled test variants (§21 "controlled clocks/randomness") | Port with two adapters (system / fixed-recorded): a real seam |
| Event delivery | Outbox dispatcher | Port with two adapters (Socket.IO rooms / in-memory recorder): a real seam |
| Legacy writers | Existing routes | One guard function, `legacy_write_guard(character) -> Translation or Rejection`, called by each writer in §6. Not a port |

### 7.6 File layout

```text
vtt/creation_engine/
  contracts/        core 1.1 schema, registry A1 schema, loader (referencing.Registry, compiled once)
  kernel/           submit, admission, receipts, gate, checkpoints, outbox, ports (clock, rng, delivery)
  registry.py       OPERATIONS (single source of truth)
  operations/       drafts.py, content.py, overrides.py, operator.py, migration.py, runtime.py
  evaluator/  compiler/  policy/  adapter/(legacy RDL mapping, legacy_write_guard)
  store/            SQLAlchemy models (ce_* tables) and queries
  transports/       http.py, socket.py
tests/creation_engine/   pure/ (no DB), pg/ (PostgreSQL, multi-process), acceptance/ (T-IDs)
```

### 7.7 Rules enforced by tests

This is the approach goblin_delve_bot takes with ADR-0002, "facade enforced by test":

1. **Import guard.** `operations/`, `evaluator/`, `compiler/` and `policy/` import nothing from
   `flask`, `flask_socketio`, `sqlalchemy`, `vtt.models` or `vtt.extensions`.
2. **Registry/schema drift guard.**
   - Every `Operation` has exactly one `<Name>Command` in the registry schema, and the reverse holds.
   - Each payload dataclass's fields equal its schema's properties.
   - Every author-editable path has exactly one owning question (§4.1).
3. **Acceptance mapping.** Every operation names at least one T-ID it serves, and the acceptance
   suite covers them.
4. **Legacy writer coverage.** Each writer in the §6 table calls `legacy_write_guard`. The list comes
   from the Discover inventory.
5. **Locale completeness.** Every G1 question has `de`, `en` and `fr` text (see §8).

**Naming:**

- Commands are imperative (`RecordDraftDecision`).
- Events are past tense (`DraftDecisionRecorded`).
- Error codes are stable `UPPER_SNAKE`.
- Domain vocabulary follows the spec §4 table (Definition, Revision, Draft, EntityInstance → "occurrence", Representation, ExecutionLock).
- `CONTEXT.md` gains these terms when G1 starts.

### 7.8 Alternatives considered

| Shape | Verdict |
| --- | --- |
| **A. One kernel `submit`, plus registry entries with pure `decide`** (chosen) | Deep. Small interface, most behavior hidden, one test surface for T04–T08 |
| B. One service function per command called by routes (today's VTT style) | Shallow. The interface grows with every command, and admission/idempotency repeat N times, as in the loot route |
| C. Generic `apply_patch(entity, patch)` | Violates §4 ("arbitrary patches are forbidden") and §15's decision log |

## 8. Localization (decision D8)

- **Locales.** `Locale` is `de | en | fr`. German is canonical.
- **Per-question text.** Every registered question carries display and help text for all three
  (§15 "display/help localization").
- **No fallback.** A missing translation is a registry conformance failure, never a silent fallback
  at runtime.
- **Identity.** `promptLocale` is recorded with each answer. The answer's identity is the question
  ID/version, never the text (compare §10).
- **T32.** Run it across de → en → fr with Guided → Advanced → Guided mode changes.
- **Artifacts.** A mechanically equivalent text in another language is a new presentation artifact (§19).

## 9. Verification performed

- The registry schema is valid Draft 2020-12 and resolves all `$ref`s into the core 1.1.3 schema.
- 24/24 example commands validate.
- For every operation, four variants are rejected: an unknown payload field, a spoofed principal
  field, a missing authority epoch, and the superseded contract version "1.1.2".
- Also rejected: a draft operation in a mechanical envelope, an unsupported locale (`es`), a string
  where a boolean answer is required, and a bare ID where an occurrence reference is required.
- Details: `creation-engine-v1.1-registry-a1-verification.json`.
- These are shape checks only. Semantic, authorization and transaction rules still need engine tests.

## 10. Review notes

1. **Content, not wire.** The question registry for the G1 magic item (question IDs, order,
   constraints, de/en/fr text) is content. It ships with the ruleset package, not with this addendum.
2. **Token movement (G0-13), resolved by E4.** Movement is ungated representation state except on
   maps whose geometry profile declares spatial mechanics (G5). G1 therefore needs no
   `MoveRepresentation` command.
3. **Manual rolls.** A manual-roll command (§9) and a transfer protocol (§4) are deliberately absent.
   They are not needed for G1.

## Pattern sources

- J. Ousterhout, *A Philosophy of Software Design*: deep modules.
- M. Feathers, *Working Effectively with Legacy Code*: seams.
- G. Bernhardt, "Functional Core, Imperative Shell": https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell
- A. King, "Parse, don't validate": https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/
- B. Leach, "Implementing Stripe-like Idempotency Keys in Postgres": https://brandur.org/idempotency-keys
- Transactional outbox: https://microservices.io/patterns/data/transactional-outbox.html
- python-jsonschema referencing: https://python-jsonschema.readthedocs.io/en/stable/referencing/
