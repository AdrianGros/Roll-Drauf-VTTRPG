# DAD-M Program: Creation Engine — approved G1 implementation program

version: 1
status: approved — G0 passed 2026-09-24 (v1.1.4, errata E1–E4); G1 in Deploy
date: 2026-09-24
phase: Deploy (authorized 2026-09-24 by Adrian with Matt's go); Discover and Apply outputs below are closed
basis: Roll Drauf Creation Engine v1.1.4 = v1.1 Audit Candidate 1 + G0 errata E1–E4 (`docs/creation-engine/v1.1.4/`); wire contract 1.1.3 plus registry addendum A1

## 0. What this document is — and is not

The v1.1.4 specification (v1.1 plus G0 errata E1–E4) is the normative input. This plan does not
reinterpret, extend, or weaken it. Where the spec leaves a choice open, this plan names it as a decision (§14 below)
instead of choosing silently (spec §1: "No implementation may silently choose the weaker
interpretation").

Two spec rules govern whether implementation may start:

- **G0 comes first.** §22: "G0 — Spec audit / architecture lead and security reviewer —
  Independent review of F01–F13; no unresolved high-risk contradiction in proposed slice."
  The #reporte post of 2026-09-23 requested exactly this second adversarial audit. It ran on
  2026-09-24: `docs/creation-engine/audits/creation-engine-v1.1-g0-audit-2026-09-24.md`.
  Its closures were adopted the same day: highs (E1), mediums (E2), lows (E3) and Matt's G0-11/G0-13
  decisions (E4, v1.1.4). **G0 passed on 2026-09-24.**
- **Pre-authorization package.** §22: "Before implementation authorization, provide the
  chosen phase's concrete schema/migration/API diff, dependency choices, executable fixture
  plan, rollback boundary and acceptance owner." Sections 7–13 below are that package for G1.

Historical planning context: sections 1–15 retain the pre-implementation design and decisions. Implementation progress and executed evidence are recorded in §16; the original planning premise is not the current project status. The 25 September document reconciliation preserves G0 approval, G1 authorization and the active v1.1.4/core 1.1.3/A1 contract. See `docs/creation-engine/README.md`; proposed research deltas do not expand this program.

## 1. Input summary

| Input | Location / identity |
| --- | --- |
| v1.1.4 specification (normative, G0 passed) | `docs/creation-engine/v1.1.4/creation-engine-v1.1.4.md`; E4 in `creation-engine-v1.1.4-errata.md`, E1–E3 in `../v1.1.3/creation-engine-v1.1.3-errata.md`; manifest pins package and companions |
| v1.1.3 package (superseded text; still holds wire contract 1.1.3) | `docs/creation-engine/v1.1.3/` |
| v1.1.2 specification (superseded, E1 + E2) | `docs/creation-engine/v1.1.2/` |
| v1.1.1 specification (superseded, E1 only) | `docs/creation-engine/v1.1.1/` |
| v1.1 specification (historical Audit Candidate 1) | `docs/creation-engine/v1.1/creation-engine-v1.1.md`, sha256 `70b7d3ce…c5ad` |
| Companion wire schemas | Core: `v1.1.3/creation-engine-v1.1.3-contracts.schema.json` (contract 1.1.3). Registry addendum A1: `addenda/creation-engine-v1.1-registry-a1.schema.json` (approved). v1.1 original: sha256 `53e6ba0c…6cfb8d35` |
| Acceptance catalogue T01–T56 | `v1.1.4/creation-engine-v1.1.4-acceptance.json` (all `specified_not_executed`; T47–T56 added by E1–E4) |
| Revision report / v1.0 audit | `creation-engine-v1.1-change-report.md`, `creation-engine-v1.0-audit-team.md` |
| Package manifest | `review-package-manifest.json` — all 10 file hashes verified on copy (2026-09-24) |
| Source post | Team server #reporte, 2026-09-23 13:17 UTC (message in channel `1504746179005513778`) |
| Original v1.0 spec | Team server #it-keller, message `1551975805146374146` (v1.1 preamble: "This revision replaces v1.0's normative specification") |
| VTT working tree | `main` @ `87ff37f` (spec inventory was taken at `94ff1b9`; 3 commits of drift, see §2.6) |

## 2. Discover — fresh VTT inventory (spec §23: "a required fresh inventory of the existing VTT before implementation")

### 2.1 Mechanical fields and their current writers (spec §5 field-authority table)

| Spec §5 row | Current storage | Current writers (evidence) |
| --- | --- | --- |
| Calculated values (AC, proficiency, max resources) | `characters.ac`, `hp_max`, `mana_max`, `proficiency_bonus` (`vtt/models/character.py:30-44`) | Owner `PUT /characters/<id>` writes all directly (`vtt/characters/routes.py:432-458`); create/import constructors (`:322`, `:713`); combat HP adjust also writes `character.hp_max` (`vtt/combat/service.py:296-298`) |
| Current resources (HP, mana) | `characters.hp_current`, `mana_current`; **and** `token_states.hp_current/hp_max` per session/map (`vtt/models/token_state.py:29-30`) | `PUT` (`routes.py:440,456`); `adjust_hp` writes token **and** character (`combat/service.py:289-298`); `token:update` lets token owners patch `hp_current`/`hp_max` on the token only (`vtt/socket_handlers.py:554-568`, `:1117-1118`); `token:create` (`socket_handlers.py:965-1005`) and REST token create (`vtt/campaigns/routes.py:1442-1473`); traps damage the token only (`vtt/combat/traps.py:75`) |
| Ability scores | `characters.str_score … cha_score` | `PUT` (`routes.py:442-452`); level-up attribute choice (`routes.py:547`) |
| Equipment / inventory | `equipment` (`ac_bonus`, `is_equipped`, `is_cursed`, `special_properties`), `inventory_items` (`quantity`, `effects`, `is_cursed`) | Equipment CRUD (`routes.py:1048,1105,1138`); inventory CRUD (`routes.py:1182,1230,1265`); loot transfer adds inventory (`vtt/play/routes.py:741-743`); spells CRUD (`routes.py:916-989`) |
| Content / progression JSON | `characters.character_data.roll_drauf_light` (species, faction, class, background, content, progression) | Create/`PUT` via `_normalize_character_payload` (`routes.py:170-192`); level-up (`routes.py:485-559`, `vtt/roll_drauf/progression.py:91`) |
| Token HP copied from character | `token_states.hp_*`, one row per session/map | See "current resources" — nothing keeps token and sheet in agreement except `adjust_hp` |
| Legacy exports | `GET /characters/<id>/export`, `POST /characters/import` (`routes.py:562-743`) | Import creates a Character directly (ORM) |

### 2.2 Unexplained legacy totals (drives T01 and the "existing-character conflict" fixture)

- Level-up adds signature features as **text only**. For example, "Defensiver Stil" says "Abwehrwert
  erhöht sich dauerhaft um 1", but `ac` is never changed (`progression.py:137-149`). Only an
  attribute choice changes a column (`routes.py:544-547`).
- Level-up never changes `hp_max`, although classes declare `hit_die` (`vtt/roll_drauf/catalog.py`, `CLASSES`).
- `equipment.ac_bonus` is stored but never applied to `characters.ac`. No reader exists outside CRUD.
- Owners can overwrite any total through `PUT` with no provenance.
- Consequence: a stored AC/HP may already include a bonus applied by hand, or may never include
  it. Spec §5: "Unknown historical calculations MUST NOT be reverse-engineered as invented author
  intent … Known effects must not be applied again on top of an imported total without an
  explicit reconciliation."

### 2.3 Identity and scope

- A character has at most one campaign (`characters.campaign_id`, nullable). A token references a
  character per session/map. Several tokens can point at one character, each holding its own HP copy (T03 hazard).
- No workspace concept exists. Principals are local accounts (JWT). Campaign roles are
  `Player | DM | CO_DM | Observer` with member status `invited | pending | active | left | kicked`
  (`vtt/models/campaign_member.py:16-17`). Platform role and profile tier are separate
  (`vtt/models/user.py:38-55`), as ADR-0001 and `CONTEXT.md` describe.

### 2.4 Realtime, deduplication, ordering (spec §§8–10)

- The socket dedupe cache is process-local with a 120 s TTL (`vtt/socket_handlers.py:49,338-352`).
- `event_seq` is a process-local counter (`vtt/utils/realtime.py:8-22`).
- Production runs **one** eventlet worker (`gunicorn.conf.py`). A Socket.IO message queue is
  already configurable (`vtt/__init__.py:190`, `SOCKETIO_MESSAGE_QUEUE`).
- Token writes use optimistic `version` per token plus a session `state.version`. There is no
  campaign-wide mechanical version, authority epoch, receipt, or outbox.
- `combat_events` has durable per-encounter `sequence_no` (`vtt/models/combat_event.py:15`), but
  it is not a command-receipt mechanism.

### 2.5 Read authorization and serialization (spec §14 last paragraph)

- `_can_read_character` allows the owner or any active campaign member (`routes.py:233-238`).
- `_serialize_character_sheet` returns the **entire** `character_data` blob (`routes.py:241-259`).
- Anything stored in `character_data` is therefore visible to every campaign member.

### 2.6 Persistence, schema management, tests, drift

- Production and development use PostgreSQL 16 (docker `roll-drauf-vtt-db-1`). Tests use
  in-memory SQLite (`vtt/config.py:228`, `TestingConfig`).
- Schema source is the models plus `db.create_all()` (`AUTO_CREATE_SCHEMA`). Column changes are
  hand-applied SQL (`migrations/migration_m72_…sql`). There are no Alembic versions
  (`infra/scripts/deploy_staging.sh:46-58`).
- New dependencies land in `requirements.txt`. `jsonschema`, an RFC 8785 canonicalizer, and
  `hypothesis` are not present.
- Drift since `94ff1b9`: `vtt/campaigns/routes.py`, `vtt/permissions.py`,
  `vtt/models/campaign_member.py`, `vtt/models/invite_token.py` and uploads changed (multi-use
  invites, pending join requests). The membership rule "only `active` counts" still holds in
  `_is_active_campaign_member`. Re-check again at G1 start.

## 3. Risks and assumptions

| ID | Severity | Class | Finding | Consequence for G1 |
| --- | --- | --- | --- | --- |
| R1 | closed | process | All G0 findings closed (E1–E4); G0 passed 2026-09-24 | Deploy authorized |
| R2 | high | privacy | Legacy sheet serializer exposes all of `character_data` to campaign members (§2.5) | Engine data MUST NOT live in `character_data`. ENGINE-state characters need a policy-projected compatibility endpoint (§14) |
| R3 | high | correctness | Multiple HP writers; token HP can diverge from the sheet (§2.1) | Blocks "sheet/token agreement" and T03 unless every HP writer goes through one resource command in ENGINE scopes |
| R4 | medium | correctness | Unexplained legacy totals (§2.2) | Expect many parity discrepancies. Each becomes a labelled legacy baseline/override or an explicit approval (§5) |
| R5 | medium | test evidence | SQLite in-memory cannot exercise competing transactions or process restarts | T04–T06, T08, T25 need a PostgreSQL + multi-process harness (§21: "not mocks that always serialize") (D4) |
| R6 | medium | ops | Single worker; process-local sequencing and dedupe | Engine must use durable scope sequence, receipts and outbox. T06 needs ≥2 worker processes in test |
| R7 | medium | scope | G1 covers T01–T16, T22–T26, T31–T32 plus an 8-user study. This is large | Team must set effort per work package (§22: "Dates cannot be inferred") (D2) |
| R8 | medium | contract gap | Companion schema covers only 3 runtime commands. Authoring/draft command payloads are unregistered | Must be written as a versioned registry addendum before Deploy (D7) |
| R9 | low | drift | 3 commits since spec inventory | Re-verify §2 at G1 start |
| R10 | medium | evidence | §22 requires ≥8 target users for the T45 study. The team's IT role has 7 members besides the two leads | Recruit at least one more participant, e.g. from the Projektteam role or the community's DMs/players |

Assumption A1: the first engine surfaces are new routes and pages in this Flask app, and
PostgreSQL remains the store. The spec leaves vendor and topology open as long as the
semantics hold (§1).

## 4. Gate sequence (unchanged from spec §22)

`G0 audit → G1 → G2 → … → G8`. This plan covers only G1:

> G1 — Existing-character adapter; magic item; three authoring modes; resource/effect / VTT
> integration lead — Applicable T01–T16, T22–T26, T31–T32, T47–T50, T52–T55; sheet/token agreement; no live cutover.
> (v1.1.4 wording. T51 belongs to G2 and T56 to G5.)

Also bound to G1 by §22:

- "The slice includes an existing-character conflict and hidden-effect fixture, not only a new empty character."
- "It proves its own coverage, not the full progression/world graph."
- "G1/G4 product evaluation uses at least eight target users … four T45 tasks … at least 80%
  successful task completions, zero unnoticed creative defaults in inspected outcomes."

## 5. G1 solution boundary

In scope (spec reference):

- Canonical types, IDs, digests, rationals, units, JCS hashing (§6)
- `core-safe-1` evaluator: typed acyclic formula AST, fixed stages, stack policies, conflicts, budgets (§7, §18)
- Definitions, revisions, drafts and execution locks, for the subset G1 needs (§4, §12 lock identity)
- Command kernel: admission, idempotent receipts, scope gate, action state machine, atomic
  checkpoints, recorded randomness, transactional outbox, fencing epochs (§§8–9)
- Pending decisions with deadlines for the flame child activity (§10)
- Policy projection on engine outputs, declassification, View As, cache identity (§14)
- Legacy adapter: migration ledger, `LEGACY → SHADOW`, parity preview; `ENGINE` only in fixture/test scopes (§5)
- One magic item authored through Guided, Structured and Advanced modes (§15)

Out of scope for G1 (owned by later gates; nothing is dropped from the target):

- Live cutover of any production character (G1 exit: "no live cutover")
- D&D 5e reference ruleset (§5)
- Full choices/grants multiplicity/undo matrix (G2: T28–T30)
- Time/cadence ledger beyond what the magic item needs (G2: T17–T18)
- Package import/export, updates and rollback (G3)
- World graph (G5), publishing (G6), load/recovery at deployment topology (G7), AI assist and extensions (G8)

## 6. Architecture placement

The core stays framework-free so it can be tested without Flask or a database. Adapters wrap it.

| Module (proposed) | Spec | Responsibility |
| --- | --- | --- |
| `vtt/creation_engine/types.py`, `canonical.py` | §6 | Opaque IDs, tagged refs, `sha256:` digests, rationals, units, RFC 8785 canonical bytes |
| `vtt/creation_engine/registry/` | §6, §15 | Trusted schema/ruleset registry: type IDs, validators, question metadata, renderer fallback |
| `vtt/creation_engine/evaluator/` | §7, §18 | Formula AST, stage pipeline, stacking, `EFFECT_CONFLICT`, fuel accounting |
| `vtt/creation_engine/kernel/` | §§8–10 | Admission, receipts, scope gate, action state machine, checkpoints, RNG records, decisions, outbox |
| `vtt/creation_engine/policy/` | §14 | Policy overlay, projection, declassification, View As, cache keys |
| `vtt/creation_engine/adapter/` | §5 | RDL mapping, migration ledger, parity preview, legacy-write translation |
| `vtt/creation_engine/compiler/` | §15 | Deterministic interview, answer log, invalidation, mode switching |
| `vtt/creation_engine/store.py`, `models.py` | §§8, 12 | PostgreSQL persistence (SQLAlchemy models, `ce_` tables) |
| `vtt/creation_engine/routes.py`, `sockets.py` | §17 | REST/WebSocket transports sharing one command path |
| `vtt/templates/creation/*`, `vtt/static/js/creation/*` | §15, §19 | Three authoring modes and projection views |

Scope consistency argument (§8: "Per-row optimistic checks without a scope-wide consistency
argument are insufficient"):

- Every mechanical mutation first takes `SELECT … FOR UPDATE` on its `ce_runtime_scopes` row.
- It then checks `expectedScopeVersion` and `authorityEpoch`.
- It commits the new `stateVersion` in the same transaction.
- Commit order per scope is therefore the lock order.
- This argument must be written into the design record and attacked in G0/G1 review.

## 7. Schema / migration diff (additive only)

All tables are new. G1 changes no legacy table or column. Content tables are defined by the WP3 models and
`migrations/migration_m73_creation_engine_content.sql`; later work packages add their own
migrations. `AUTO_CREATE_SCHEMA` alone does not install append-only triggers. The SQL migration
is required before activating the engine, following the repo convention in §2.6.

| Table | Spec | Key contents and constraints |
| --- | --- | --- |
| `ce_workspaces` | §4, §1 | Personal workspace per local account. Never derived from a Discord guild ID |
| `ce_definitions` | §4 | Opaque ID (1–128 chars, §4 grammar), namespace, owner workspace, mutable name label, tombstone. IDs never reused |
| `ce_revisions` | §4, §6 | Immutable canonical bytes, `sha256` digest, schema type/version, provenance, definition FK. Append-only (no UPDATE path) |
| `ce_drafts`, `ce_draft_answers` | §15 | Draft ID, owner workspace, monotonic draft version. Answer log: question ID/version, typed answer, author, resulting mutations, invalidated descendants, superseded marker |
| `ce_execution_locks` | §12, schema `ExecutionLock` | `lockId`, `profileId`, ruleset, schema bundle, evaluator, config/unit-table digests, packages, revisions, assets. Immutable |
| `ce_runtime_scopes` | §8 | Kind (`campaign` / `sandbox`), campaign FK nullable, `stateVersion`, `authorityEpoch`, `eventSequence`, active lock, policy version, gate (active root action ID) |
| `ce_instances`, `ce_representations` | §4 | Occurrence ID, owning scope, pinned revision, declared overlays. Representations map `token_states.id` or a sheet to one occurrence |
| `ce_resource_ledger`, `ce_resource_entries` | §7, §11 | Current amount per (instance, resource) with `0 ≤ current ≤ max` enforced. Append-only entries with checkpoint ID and reason |
| `ce_effect_applications` | §7, schema `EffectApplication` | All required schema fields. Unique `applicationId` |
| `ce_grants` | §13 (subset) | Recognized RDL selections from the adapter. Grant ID, source occurrence, merge identity |
| `ce_actions`, `ce_checkpoints` | §9 | `ActionState` enum, parent/root, window sequence, checkpoint outcome digest |
| `ce_random_records` | §9 | Checkpoint ID, algorithm identity, dice spec, raw outcomes, rules snapshot digest |
| `ce_pending_decisions` | §10, schema `PendingDecision` | All required schema fields, deadline (UTC), status |
| `ce_receipts` | §8, schema `Receipt` | Unique `(principal, scope, idempotency_key)`. Request digest. Outcome digest. Retained for the scope lifetime |
| `ce_domain_events`, `ce_outbox` | §§9–10, §20 | Immutable event ID, scope sequence, causation IDs, audience metadata. Delivery attempts and dead-letter |
| `ce_policies`, `ce_policy_epochs` | §14 | Versioned grants/denies, declassification rules, epochs |
| `ce_view_as_sessions` | §14 | Operator, viewed member, 15-minute expiry, entry/exit log |
| `ce_worker_leases` | §9 | Fencing epochs for execution leases |
| `ce_migration_ledger`, `ce_migration_states`, `ce_parity_reports` | §5 | Bijective `(source type, source ID, migration version) → opaque ID`. State `LEGACY / SHADOW / FROZEN_FOR_CUTOVER / ENGINE / ROLLBACK_REVIEW`. Per-field discrepancies |
| `ce_security_audit` | §20 | Append-only stream, linked by IDs to domain events and creative decisions. Distinct from `audit_log` |

## 8. API diff

New (behind feature flags `CE_AUTHORING`, `CE_RUNTIME`, `CE_SHADOW`, all off by default):

- `POST /api/ce/commands` takes the command envelope from the companion schema: `InvokeActivity`,
  `ResolveDecision`, `AdjustResource`, plus the registry addendum A1 commands (D7). It returns the
  `PublicReceipt` shape (v1.1.1: no outcome digest, filtered event IDs).
- Admission order follows §8. Error codes follow §17: 400 `SCHEMA_INVALID`, 404 `NOT_FOUND`,
  403 `OPERATION_FORBIDDEN`, 409 with a specific code (`IDEMPOTENCY_KEY_REUSE`, `SCOPE_BUSY`,
  `DECISION_STALE`, `AUTHORITY_EPOCH_MISMATCH`, `EFFECT_CONFLICT`, …), 422 `SEMANTIC_INVALID`,
  413/429 limits, 503 with checkpoint status.
- `GET` projections, explanations, receipts, decisions and drafts. All are policy-projected; an
  unknown ID and a forbidden ID return the same 404.
- WebSocket engine stream: an audience-bound cursor, reconnect negotiation (authority epoch plus
  schema version), and a snapshot on a stale cursor. This does **not** use `vtt/utils/realtime.py` counters.
- Migration preview: `GET /api/ce/migration/characters/<id>/preview` returns the field map, discrepancies and unsupported items (§5).
- View As: enter/exit endpoints, read-only (§14).

Changed legacy behavior, **only** for characters/scopes in `ENGINE` state (G1: fixture/test scopes only):

- `PUT /characters/<id>` mechanical fields, level-up, equipment/inventory/spell CRUD, loot
  transfer, `token:create` / `token:update` HP fields, `adjust_hp`, trap damage, import: each is
  translated to an authorized engine command or rejected with `LEGACY_FIELD_READ_ONLY` (§5, T02).
- The sheet and legacy export for ENGINE-state characters use the engine projection policy, never
  raw `character_data` (§14).

In `LEGACY` / `SHADOW` state, legacy writers keep sole authority and stay unchanged. Shadow
evaluation is read-only and cannot mutate live resources (§5).

## 9. Dependency choices (approved 2026-09-24, D4)

| Need | Proposed | Alternative |
| --- | --- | --- |
| RFC 8785 canonical JSON (§6) | `rfc8785` (pure Python) | In-house implementation plus RFC test vectors |
| Draft 2020-12 validation of wire contracts (§17) | `jsonschema` | none reasonable |
| Property tests (§21: operand ordering, grant multiplicity) | `hypothesis` (dev only) | Hand-written generators |
| Concurrency/restart tests (§21) | PostgreSQL 16 test database (docker) plus a 2-process harness | none; SQLite cannot prove T04–T06 |
| Multi-worker delivery | Existing `SOCKETIO_MESSAGE_QUEUE` (Redis already deployed) | — |
| Randomness (§9) | Server CSPRNG (`secrets.SystemRandom`), recorded per checkpoint; replay never draws | — |

## 10. Work packages (dependency order inside G1; gate order unchanged)

| WP | Deliverable | Spec | Acceptance IDs |
| --- | --- | --- | --- |
| WP1 | Canonical types, IDs, digests, rationals, units, JCS, UTC timestamps; companion schema validation | §6, §10, §17 | Schema negative cases from `verification.json`; foundation for T14–T15 |
| WP2 | `core-safe-1` evaluator (core functions, Predicates) plus deterministic budgets | §§6–7, §18 | T14, T15, T26 (budget part), T16 (see D5), T53 |
| WP3 | Definitions, revisions, drafts, execution locks (G1 subset); personal workspaces | §4, §12 | Digest/immutability unit tests |
| WP4 | Command kernel: admission, receipts, scope gate, action states, checkpoints, RNG records, outbox, fencing | §§8–9, §17 | T04, T05, T06, T07, T08, T12, T13 (see D5), T49, T52, T53 |
| WP5 | Pending decisions, deadlines, revocation handling, operator intervention, manual resolution labelling | §10, §2 | T09, T10, T11, T50, T54 |
| WP6 | Policy projection, declassification, View As, cache identity, subscription revocation, context tokens, public receipts | §6, §14 | T22, T23, T24, T25, T47 |
| WP7 | Legacy RDL adapter: migration ledger, SHADOW parity, fixture-scope ENGINE cutover, legacy-write translation, token/sheet as representations | §5, §4 | T01, T02, T03, T48; sheet/token agreement |
| WP8 | Guided compiler plus Structured and Advanced modes for the magic item | §15, §19 | T31, T32 |
| WP9 | G1 evidence: acceptance run report; ≥8-user T45 study; exit report against §22 | §21–22 | All G1 IDs; study thresholds |

## 11. Executable fixture plan

Harness (§21):

- Pure tests (WP1, WP2, WP8) run anywhere.
- Kernel/policy/adapter tests run on PostgreSQL with competing transactions, process kill and
  restart (failure injection), controlled clocks, and fixed randomness via recorded outcomes.
- Golden fixtures pin content digests and execution locks.
- Conformance fixtures ship with the evaluator.

Content fixtures:

- **F-RDL-CONFLICT:** existing RDL Kämpfer, level 3, "Defensiver Stil", in two variants. Variant a:
  `ac` still 12 (bonus never applied). Variant b: `ac` 13 set by hand. Both must yield a labelled
  legacy baseline/override or an explicit reconciliation, never a double application (T01, §2.2).
- **F-HP-TOKENS:** one character with two tokens in two sessions of one campaign plus a second
  campaign occurrence (T03, sheet/token agreement).
- **F-FLAME-HARMLESS / F-FLAME-DAMAGE:** the §24 "Harmless flames" and "Post-hit flame" traces:
  3 charges, explicit recovery event, optional child decision (T09–T12, T31).
- **F-CURSE:** the §24 "Private curse" trace. A restricted −1 defense, a reviewed
  declassification rule, and a variant without the rule (T22–T24). This is the required hidden-effect fixture.
- **F-SHARED-CHARGE:** the §24 "Shared charge" trace (T04, T06, T07).
- **F-TWO-SWORDS:** one actor holding two occurrences of the flame sword revision with different charges (T49).
- **F-MIXED-CUTOVER:** F-HP-TOKENS campaign with an attempted single-character cutover and a legacy edit during an engine action (T48).
- **F-TOKEN-PROBE:** F-CURSE variant where the responder enumerates hidden values against the context token and public receipt (T47).
- **F-MANUAL:** an operator resolves a suspended flame-charge action manually, and a player tries to adjust another player's HP (T50).

T-ID applicability (approved 2026-09-24, D5):

| IDs | Ruling |
| --- | --- |
| T01–T12, T14, T15, T22–T25, T31, T32, T47–T50, T52–T55 | Applicable in full |
| T13 | Applicable to child-frame depth/cycle budgets (on-hit flame child). Reaction-slot ordering is exercised in G2, where T13 is listed again |
| T16 | Applicable only if G1 ships incremental evaluation. Proposal: G1 evaluates by full recomputation only; T16 executes in G2 ("full/incremental equivalence") |
| T26 | Graph, trigger and formula budgets plus external-asset rendering are applicable. Archive-bomb sub-case executes with imports in G3 (T36–T38) |
| T32 | Runs across de → en → fr with Guided → Advanced → Guided (D8) |

## 12. Rollback boundary

- G1 moves no production character past `SHADOW`. Legacy writers remain the sole authority for all live data.
- All engine tables are additive. Turning the flags off returns the product to legacy behavior with no data migration.
- Engine records (receipts, tombstones, revisions) are retained, not dropped (§8, §12).
- Proof obligation: a test snapshots every legacy table before and after SHADOW evaluation of the
  fixture set and asserts no change (§5: "shadow evaluation cannot mutate live resources").
- Post-cutover rollback semantics (§5) do not arise in G1 because no live cutover happens.

## 13. Acceptance owner and roles

§22 requires named accountable roles. The team assigns people and effort; none are inferred here.

Team assignment (D2, 2026-09-24):

- Product owner: Matt (co-author).
- IT project lead: Adrian (Donut).
- Project team, mainly volunteer testers: Legendary Rock plus every holder of the team server's
  `IT` role. As of 2026-09-24 that is Balu, Janine, Karma, Maxilein, Rock, Sonic and Wale, besides
  the two leads.

Proposed mapping of the spec's roles onto that assignment (confirm or change):

| Spec role | Responsibility | Person |
| --- | --- | --- |
| Architecture lead | G0 acceptance, v1.1.1 errata, design record | Adrian |
| Security reviewer | Accepts G0-01 (privacy) and reviews WP6 | Adrian; second reviewer _TBD_ (the G0 review itself was done by Claude) |
| VTT integration lead (G1 accountable) | WP1–WP9 | Adrian |
| Product owner / acceptance owner | T-ID rulings (D5), G0-13 product decision, addendum review, G1 exit sign-off | Matt |
| Study lead | ≥8-user T45 evaluation | Matt |
| Study participants and testers | T45 tasks, acceptance runs | Project team (see R10: 7 available, ≥8 needed) |

## 14. Decisions required before Deploy

Status after 2026-09-24: all decisions D1–D8 are made (record: `dadm/artifacts/approvals/approval_creation_engine_g1_2026-09-24.md`).

| ID | Decision | Recommendation / outcome |
| --- | --- | --- |
| D1 | Who performs the G0 second adversarial audit, and when | **Done 2026-09-24 by Claude:** `docs/creation-engine/audits/creation-engine-v1.1-g0-audit-2026-09-24.md`. Verdict: not passed yet. Three high findings, each with a text-level closure for v1.1.1 |
| D2 | Assign the §13 roles and effort estimates | **Decided:** see §13. Effort estimates still open |
| D3 | What the §5 "deliberately small test ruleset" is | **Decided (recommendation accepted):** a separately versioned "Roll Drauf Light G1 subset" covering exactly the fields the adapter maps (attributes, defense, HP, Fokus/mana, training bonus, signature choices). Everything else stays inert/manual |
| D4 | Approve the §9 dependencies and the PostgreSQL + multi-process test harness | **Approved** |
| D5 | T-ID applicability rulings in §11 | **Approved** |
| D6 | G1 magic item | **Approved:** flame sword from the §24 traces, plus the private curse as the hidden-effect fixture |
| D7 | Authoring/draft command payload schemas are not in the companion schema | **Drafted:** `docs/creation-engine/addenda/creation-engine-v1.1-registry-addendum-a1.md` plus schema and verification (24 operations, code structure for `vtt/creation_engine/`). Needs review by someone other than its author (proposed: Matt) |
| D8 | Locales | **Decided:** German (canonical), English and French for all G1 question text; T32 runs across all three |

## 15. Next step

1. Done: D1–D8 decided. E1–E4 adopted as v1.1.4. G0 passed 2026-09-24.
2. Deploy WP1: pure code, touching no legacy path. Progress is recorded in §16.
3. Then WP2 (evaluator) and WP3 (content store), per §10.

## 16. Deploy log

### WP1 — canonical types, JSON canonicalization, rationals, units, UTC timestamps, contract validation (2026-09-24)

**Implementation summary.** New package `vtt/creation_engine/`. It is not imported by the running
app, and it touches no legacy path.

- **`errors.py`:** `ContractViolation` carries the stable codes `SCHEMA_INVALID`,
  `SEMANTIC_INVALID` and `BUDGET_EXCEEDED` (§17/§18). `ArithmeticFault` covers division by zero
  (§6: never NaN).
- **`types.py`:** opaque IDs, content digests, context-token shape, tagged references. A reference
  kind is never substituted (§4). UTC-only timestamps (§10, G0-20).
- **`canonical.py`:** a strict JSON parser that rejects duplicate keys, non-finite numbers, unsafe
  integers and invalid Unicode. It never normalizes Unicode. RFC 8785 canonical bytes come from
  `rfc8785`, and `sha256:` content digests are computed over them (§6).
- **`rational.py`:** exact reduced rationals and a 256-bit intermediate budget, plus the safe-integer
  wire range (both `BUDGET_EXCEEDED`, §18). Four explicit rounding operations (§6); no implicit
  mixing with Python numbers.
- **`units.py`:** a registered unit table with exact ratios. Different dimensions can never be
  combined. A canonical form feeds the `unitTableDigest` (§12).
- **`contracts/`:** byte-identical copies of core contract 1.1.3 and registry addendum A1, loaded
  once through a `referencing.Registry`. It exposes `validate_command`, `validate_definition` and
  `parse_command` (strict parse, then schema).
- **Hygiene:** `CONTEXT.md` gains the Creation Engine vocabulary. `.hypothesis/` is added to
  `.gitignore` and `.dockerignore`.

**Implementation-level choice adopted by WP3.** The unit table's canonical JSON shape
(`{"units":[{"id","dimension","toBase"}]}`, sorted by ID) is not in the wire contract. It exists so
the `unitTableDigest` is computable. WP3 adopts this shape unchanged.

**Files changed.**

- New: `vtt/creation_engine/{__init__,errors,types,canonical,rational,units}.py`,
  `vtt/creation_engine/contracts/{__init__.py,core-contracts-1.1.3.schema.json,registry-a1.schema.json}`.
- New tests: `tests/creation_engine/test_ce_{canonical,rational,types_units,contracts,boundaries}.py`.
- Edited: `CONTEXT.md`, `.gitignore`, `.dockerignore`, `requirements.txt`.
- Committed as `e17ae9c`.

**Proofs.**

- WP1 suite: `pytest tests/creation_engine`, **245 passed** in 7.1 s. That includes Hypothesis
  property tests: key-order independence of digests, canonical round trip, field laws and the
  rounding brackets.
- Covered from spec evidence:
  - every negative case from the v1.1.3 and addendum verifications, through the production code path;
  - the §7 example (10 + 2) × 2 = 24;
  - UTF-16 key ordering;
  - the import guard;
  - schema drift against the hashes pinned in the v1.1.4 manifest.
- **Regression:** the full repository suite (`pytest`, dev venv) ran **879 passed, 0 failed** in
  7 min 23 s. It included the WP1 tests as collected at that point. The 3,932 warnings are
  pre-existing deprecations (for example `datetime.utcnow`), none from WP1.

**Acceptance checklist (WP1).**

- [x] Canonical bytes and digests per RFC 8785; strict input rejects everything §6 forbids.
- [x] Exact rationals, explicit rounding, 256-bit and safe-range budgets (§6, §18).
- [x] Units: exact conversion, no cross-dimension arithmetic (§6).
- [x] Tagged references without kind substitution; bare IDs refused (§4, G0-03).
- [x] UTC-only timestamps (G0-20).
- [x] Command and definition validation against the approved 1.1.3 contract and A1, including the 15 + 96 negative variants.
- [x] Engine modules import no framework or legacy code (addendum §7.7 rule 1).
- [x] `requirements.txt` pins `jsonschema==4.26.0`, `referencing==0.37.0`, `rfc8785==0.1.4` and
  `hypothesis==6.168.1`, added after Adrian fixed file ownership. Installed in the project `venv/`,
  where the WP1 suite also passes (245).

**Residual risks.**

- **Root-owned files: resolved.** Adrian ran `chown -R admin:admin` on the repo (2026-09-24). All
  tracked files and `venv/` are now writable. The temporary dev venv was removed.
- **Flask on import.** `vtt/__init__.py` imports Flask, so importing the engine package loads Flask
  transitively. The engine's own modules stay framework-free by test.
- **Git ignore rule.** `dadm/artifacts/` matches the `artifacts/` ignore rule, so the plan and
  decision record need `git add -f` when committed.

**Next step.** WP2 (the `core-safe-1` evaluator: formula AST with core functions, Predicates,
fixed stages, stacking, budgets), then WP3.

### WP2 — `core-safe-1` evaluator (2026-09-24)

**Implementation summary.** New package `vtt/creation_engine/evaluator/`, with the interface
`evaluate(target, bindings, applications, *, units, predicates, inputs, fuel, limits)`.

- **`nodes.py`:** typed Formula nodes (literal, read, call, if) and Predicate nodes (binding, and,
  or, not, compare, is_known, human, manual_toggle).
  - The §18 admission limits (depth 64, 4,096 nodes) are checked iteratively before any recursive
    validation.
  - The value is then validated against the approved schema and parsed, with function registry and
    arity checked.
- **`functions.py`:** the 11 core functions from §6, each costing one operation, with exact unit rules.
- **`effects.py`:** `EffectApplication.from_wire`, which validates against the schema and parses
  into types. Payload digests are used for coalescing.
- **`fuel.py`:** a cumulative operation budget (checkpoint 100,000; the root-action constant is
  1,000,000).
- **`engine.py`:** a full recomputation.
  - A static dependency graph rejects unknown references and cycles, and enforces 2,000
    applications and 10,000 derived nodes per instance.
  - The fixed stages run base → SET → ADD → MULTIPLY → clamp → final rounding.
  - Four stack policies apply per stack group before reduction.
  - `EFFECT_CONFLICT` is reported per binding.
  - Unresolved values are explicit, with reasons.
  - Provenance is sorted and independent of input order.
- **`errors.py`:** gains `EFFECT_CONFLICT`. **`units.py`:** gains `base_unit()`, `is_dimensionless()`
  and the core dimension `dimension:dimensionless`.

**Interpretations confirmed (2026-09-24).** The user approved these readings and continuation
into WP3 in the prior implementation session. None changes a contract.

1. **Dimensionless dimension.** Pure numbers use the core dimension `dimension:dimensionless`. A
   unit table must register its base unit before MULTIPLY factors or ratios can be used.
2. **Core function signatures.** Fixed arities: 2 for add, subtract, multiply, divide, min and max;
   1 for negate and the four roundings. There are no compound units. multiply needs a dimensionless
   operand; divide takes a dimensionless divisor or two values of one dimension (giving a ratio).
3. **Predicates use Kleene three-valued logic.**
   - `and(unknown, false)` = false and `or(unknown, true)` = true; `not unknown` = unknown.
   - A comparison with an unknown operand is unknown.
   - `is_known` means the binding's final value is resolved; a conflict propagates as a conflict.
4. **Reads address bindings of the evaluated occurrence.** Reading other occurrences (such as the
   target's AC) is the activity layer's selector job (WP4/WP5).
5. **Stack groups form per (stackGroupId, operator) within a stage.** So a group's lower and upper
   bounds reduce separately.
   - Mixed policies in one group → `EFFECT_CONFLICT`.
   - `highest` needs identical units, per the literal "same-unit".
   - An `exclusive` choice is an input keyed by stack group.
   - Coalesced candidates take their highest priority.
6. **Any conflict among SET candidates makes SET a conflict**, whatever its priority (strict reading
   of "priority does not grant permission to ignore a stack conflict"). Unknown lower-priority SETs
   are ignored.
7. **Conflict dominates unknown** when both are present.
8. **Scope of a failure.** `EFFECT_CONFLICT` is per binding, and other bindings still evaluate.
   Budget, unit, reference and cycle errors fail the whole evaluation. A cycle reports as
   `SEMANTIC_INVALID`.
9. **Fuel.** One operation per executed formula or predicate node. Memoized reads cost 1. Stage
   reductions are bounded by the application limit instead of fuel. Derived nodes = bindings × 6
   stages + named predicates.

**Files changed.**

- New: `vtt/creation_engine/evaluator/{__init__,nodes,functions,effects,fuel,engine}.py`,
  `tests/creation_engine/test_ce_evaluator.py`, `tests/creation_engine/test_ce_evaluator_properties.py`.
- Edited: `vtt/creation_engine/{errors,units,canonical}.py`. `canonical.py` gains recursion guards:
  pathological nesting becomes `BUDGET_EXCEEDED` instead of a crash.
- Committed as `825b8ad`.

**Proofs.**

- `pytest tests/creation_engine`: **300 passed** (WP1 245 + WP2 55) in 7.2 s.
- WP2 coverage:
  - T14 over every permutation, plus a Hypothesis property test (250 random effect sets, shuffled)
    checking value, stages and provenance against the §7 algebra;
  - T15 SET conflict in every order; coalescing; priority;
  - clamp and the empty interval;
  - the four rounding operators;
  - all four stack policies, and "priority never overrides a stack conflict";
  - Kleene logic, human and toggle inputs;
  - reads, self- and cross-binding cycles, predicate cycles;
  - units and division by zero;
  - the depth, node, fuel, application and derived-node budgets, and 100,000-deep JSON.
- **Mutation check.** Three bugs planted in the engine were each caught by the suite (SET
  disagreement ignored, ADD applied twice, payload conflict skipped). The engine was restored
  byte-identical.
- **Regression:** the full repository suite (project `venv/`) ran **936 passed, 0 failed** in
  7 min 26 s (636 existing + 300 Creation Engine). The warnings are the same 3,932 pre-existing
  deprecations.

**Acceptance checklist (WP2).**

- [x] T14: base 10, ADD 2, MULTIPLY 2 = 24 in any serialization order, with equivalent provenance.
- [x] T15: equal-priority SETs that disagree give `EFFECT_CONFLICT`; arrival order cannot pick a winner.
- [x] T26 budget part: formula depth/nodes, fuel, applications, derived nodes, and deep JSON give
  `BUDGET_EXCEEDED` with no partial result.
- [x] T53 foundation: admission-time structural bounds raise `BUDGET_EXCEEDED` before anything is
  evaluated. The HTTP mapping arrives with the transports (WP4).
- [x] T16: deferred to G2 by D5. The evaluator is full recomputation only.

**Residual risks.**

- Duration and cadence are carried but not interpreted. Deciding which applications are active is
  the G2 time ledger's job; G1 callers pass only active applications.

**Next step.** WP3: definitions, revisions, drafts and execution locks (G1 subset), plus personal
workspaces. That includes the RDL G1-subset ruleset package (D3) that supplies the real bindings,
units and rounding.


### WP3 — content store, drafts, locks and RDL G1 subset (2026-09-25)

**Input / status.** Continued the approved G1 plan from WP2 commit `825b8ad` and the prior
session's unfinished WP3 files. That session stopped at its usage limit during PostgreSQL
verification; the working tree already contained the DBAPI migration-execution fix. WP3
implementation and verification are complete.

**Implementation summary / files.**

- `vtt/creation_engine/content/`: schema registry, definitions/revisions, versioned drafts,
  ruleset declarations and execution-lock resolution. The registry snapshots schema inputs;
  callers cannot mutate a validator through the schema accessor. Revisions are validated before
  publication and retain canonical bytes and provenance. Lock resolution checks the entire
  referenced revision closure, actual byte digests, identities, schema support and evaluator
  compatibility before producing a content-addressed lock.
- `vtt/creation_engine/store/`: seven additive SQLAlchemy tables and a transaction-neutral
  repository. Workspaces belong to local accounts. Definitions can be renamed/tombstoned;
  their revisions remain immutable. Drafts retain their authoring schema bundle, locale and
  type/version. Undo appends a snapshot instead of erasing history. Decision logs reference
  existing snapshots and retain typed answers and question versions.
- `migrations/migration_m73_creation_engine_content.sql`: PostgreSQL byte storage, foreign
  keys, uniqueness and append-only triggers for revisions, snapshots, answers and locks.
  Version columns are BIGINT, preserving the approved wire contract's full safe-integer range.
- `vtt/creation_engine/evaluator/identity.py`: versioned evaluator artifact covering the
  profile descriptor and implementation bytes, including arithmetic and contract dependencies.
- `content/rdl_g1.py`: **Roll Drauf Light G1 subset 1.0.0** (`rules.roll-drauf-light-g1`).
  Declares six attributes, defense, HP maximum, Fokus maximum, training bonus, HP/Fokus
  resources and the existing three class-signature selection sets. All numeric bindings
  explicitly round down; score, HP and Fokus dimensions are distinct. Resource adjustments
  use `clamp_report_delta`. This policy concerns commands, not maximum-change migrations.
  Base edits and overrides are eligible, subject to later command authorization. No base value
  or signature selection is inferred. Signature IDs have no implicit effect; imported totals
  and described bonuses still require WP7's explicit reconciliation. Other mechanics remain manual.
- `tests/creation_engine/test_ce_{content,content_store,rdl_g1}.py`,
  `tools/ce_test_postgres.py` and the `postgres` pytest marker provide pure, SQLite and actual
  PostgreSQL verification. The harness uses a disposable PostgreSQL 16 container on localhost.
  `contracts/__init__.py` exports the approved reference registry; `errors.py` adds the existing
  A1 `DRAFT_VERSION_CONFLICT` code.

**Recovered defects / proofs.**

- Regression cases exposed accepted digest claims that disagreed with stored bytes, mutable
  registered schemas, concurrent first-insert failures, and invalid draft JSON leaving partial
  heads if the caller caught the error and committed. These cases now pass.
- PostgreSQL tests exercise competing transactions for draft saves and workspace/lock creation;
  exactly one competing draft save wins, while both identical first-use requests may commit.
- All eight UPDATE/DELETE combinations on the four append-only tables are rejected by database
  triggers. Migration columns/types, primary keys and foreign keys match the models; rerunning
  the migration preserves saved content.
- Ruleset/evaluator digests are pinned in tests. An implementation-byte change alters the
  evaluator digest even when its descriptor is unchanged. The real evaluator leaves missing
  RDL bases unresolved and applies the package's declared rounding.
- Targeted verification: **378 passed**, including PostgreSQL, before the final three evaluator
  compatibility cases were added.
- Full repository verification: **1,017 passed, 0 failed, 0 skipped** in **518.88 s**
  (381 Creation Engine tests plus 636 existing tests), with PostgreSQL enabled. There were
  3,933 warnings, primarily existing deprecations and legacy SQLAlchemy relationship warnings.
  No production paths import the new engine package; the import guard also passes.

Reproduction (from the repository, with its `venv/`):

```bash
venv/bin/python tools/ce_test_postgres.py start
export CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55432/ce_test
venv/bin/python -m pytest tests/creation_engine -q
venv/bin/python -m pytest -q
venv/bin/python tools/ce_test_postgres.py stop
```

**Acceptance checklist (WP3).**

- [x] Personal workspace creation is idempotent under concurrency.
- [x] Immutable revision bytes/digests; schema validation; retained definition identity.
- [x] Draft optimistic concurrency, monotonic undo, preserved authoring bundle and answer history.
- [x] Deterministic locks pin the supported G1 closure and reject missing/ambiguous/tampered content.
- [x] Separately versioned RDL subset supplies explicit units, bindings, rounding and resource policy.
- [x] PostgreSQL enforces append-only history independently of repository methods.
- [x] Full repository regression verification complete: 1,017 passed.

**Retention / residual scope.** The handoff backup and raw verification logs are retained in the
Codex task workspace under `creation-engine/` (`full-regression.log` holds the final run);
the disposable PostgreSQL container was stopped after verification. The tests and this record are the repository
artifacts. No production migration or live cutover was performed. The runtime app does not
import these tables yet. SQLite is a fast functional fixture; PostgreSQL is required for the
immutability and concurrent-write guarantees. The repository assumes a trusted command caller;
workspace authorization, admission/idempotent receipts, transaction boundaries and transports
arrive in WP4/WP6. Semantic validator code changes require a schema-bundle version bump;
evaluator dependencies outside this package remain pinned by the deployment environment.
Package distribution, asset retention, updates and full progression remain later-gate work.

**Next step.** WP4: command admission, receipts, scope gate, action/checkpoint state, recorded
randomness, transactional outbox and fencing, using this store inside the kernel's transaction.
The G1 milestone remains in progress; WP3 completion is not G1 exit or a live rollout.


### WP4 — command/checkpoint kernel (2026-09-25)

**Input / status.** Continued from WP3 commit `d7a8fd0` under the existing G1 authorization.
The backend kernel and PostgreSQL adapter are implemented and verified. Public transport and current-audience projection remain disabled
until WP6; this entry does not claim completion of the overall G1 acceptance catalogue.

**Implementation summary / files.**

- `vtt/creation_engine/kernel/records.py`: command parsing, canonical request identity excluding
  only `commandId`, internal receipts, the specified action transitions and cumulative root budgets.
- `kernel/activity.py`: typed internal plans with explicit ordered windows, cost owners/spend
  windows, dice, work bounds and declared child activity IDs. These are trusted registry/compiler
  inputs, not a new public wire contract. Admission freezes the exact plan into the action.
- `kernel/service.py`: shared admission and execution for `InvokeActivity` and `AdjustResource`;
  deferred proposals, cancellation/expiry, worker continuation, declared child dispatch and lease
  acquisition. Later work packages register their remaining semantic commands; unknown operations
  are rejected. Every admission/continuation rechecks usable-account status and the required
  current-policy port. Duplicates also recheck access before returning their retained receipt.
- `store/runtime.py`: PostgreSQL unit of work. Every mechanical writer takes the scope row lock,
  giving a committed order across processes. Account status uses shared row locks. Authorization
  implementations must read current grants through this transaction, and policy writers must
  coordinate on the same scope row. No SQLite runtime fallback is offered.
- `store/runtime_models.py` and `migrations/migration_m74_creation_engine_kernel.sql`: twelve
  additive runtime tables for scopes, occurrences, resources, actions, checkpoints, receipts,
  resource entries, random records, effect applications, events, outbox delivery and consumer
  deduplication. M74 requires M73. PostgreSQL triggers protect checkpoint/effect/roll/event history,
  retain terminal receipts, and enforce exact rational resource bounds independently of the caller.
- `tests/creation_engine/test_ce_kernel.py`: actual competing processes, abrupt process exits,
  controlled clocks, replay, resource/effect integrity, scope isolation, limits and database guards.

**Interfaces / implementation choices within the approved design.**

- `Kernel.submit(principal, raw, defer=False)` takes an authenticated **server** principal, never
  an identity from the envelope. A duplicate with another command ID returns the first admitted
  command ID. Changed payload/version/lock under the same key is `IDEMPOTENCY_KEY_REUSE`.
- `Kernel` requires the installed ruleset, schema registry, configuration and three trusted ports:
  authorization, immutable-revision activity resolution, and bounded checkpoint preparation.
  Installed artifacts must match the lock. Native resolver/preparer registrations must themselves
  be versioned in the pinned configuration before production registration (WP7/WP8); there is no
  content-supplied executable callback and no permissive default authorization.
- Kernel preparation returns typed resource adjustments, effect applications and an internal
  result. Every cost/adjustment/effect is validated before writing. A savepoint additionally rolls
  back late validation failures. The outer transaction commits receipt, checkpoint, ledger changes,
  effects, CSPRNG outcomes, events and outbox together. No delivery occurs inside that transaction.
- Each successful checkpoint increments the scope version once. The initial invocation receipt
  retains its first committed checkpoint; subsequent checkpoints have their own immutable records.
  Later failures preserve those records and suspend the action while retaining the durable gate.
- `advance(scope, action, window_index, fence)` and `spawn_child(...)` are internal worker APIs.
  They are not extra client envelope fields. Children must be declared by a committed parent,
  retain the actor, respect depth/source re-entry limits, and charge the root's cumulative budget.
- Lease reassignment increments an internal fence, never the authority epoch. Fence/expiry and
  proposal deadline are rechecked at the transaction's commit boundary using the shared database
  clock and a nondecreasing scope watermark. Lease expiry does not release the action gate.
- `dispatch` is at least once to **trusted internal consumers**. `consume_once` commits a consumer's
  database mutation and deduplication record together. A lost ACK redelivers the same event ID;
  consumer failure rolls back both. Internal snapshots are consistent under the scope lock.
  WP6 must project these records and replace internal sequence numbers with audience-bound cursors.
- Limits: 20 open proposals per principal, 100 per scope, 64 targets, 128 affected occurrences,
  16 child levels, 256 child frames, 1,024 triggers, 4,096 generated events, 100,000 primitive
  operations/checkpoint and 1,000,000/root. The transport byte limit is explicitly configurable
  (default 1 MiB); malformed/oversized traffic is checked before persistence. Proposal timeout
  is an explicit server policy within 30–600 seconds, copied at admission.
- Effect application storage is immutable and bounded at 2,000 retained applications/occurrence
  for this G1 adapter. Selecting/removing active contributions and cadence/time expiry belongs to
  the adapter/time work; this package does not silently execute an expiry policy.

**Proofs / verification.**

- Full repository regression: **1,067 passed, 0 failed, 0 skipped** in **501.49 s**, with
  PostgreSQL enabled (3,934 warnings from legacy deprecations/relationships and table sorting).
- Final Creation Engine run after the added schema/configuration and malformed-wire guards:
  **435 passed, 0 failed, 0 skipped** in **57.88 s** (8 legacy ORM/table-sorting warnings).
  This includes the import guard and 50 kernel scenarios. The final additions were restricted to
  the kernel and its tests; the existing application code had no changes after the full run.
- T04: competing processes spend one charge once; matching simultaneous duplicates get the same
  receipt. Refreshing and trying a second new command cannot overdraw the resource.
- T05/T06: process death after a draw, after SQL writes but before commit, and after commit;
  restart on another worker produces one checkpoint, one debit, one stored roll and one effect.
- T07/T49: changed request under the same key is rejected; two occurrences of the same item
  revision do not share a charge pool; only the selected source pays.
- T08 kernel/consumer portion: lost-ACK redelivery is deduplicated with a real transactional
  consumer write, and snapshot recovery agrees with committed state. Client projection is WP6.
- T12/T13: post-roll cancellation cannot refund/reroll; depth/cycle/root-work overruns retain
  earlier checkpoints and suspend; a parent cannot advance past an unfinished child.
- T52: withdrawal and expiration cancel proposals with no checkpoint/cost; counts are released.
  An expired retry retains the first command ID; activation crossing its deadline cannot commit.
- T53 kernel portion: body/structural admission limits leave nothing persisted; runtime budget
  faults produce failed activation or suspension with the last committed checkpoint retained.
  Public HTTP/Socket.IO envelope testing remains with transport wiring.

Reproduction uses the WP3 disposable database command, then:

```bash
CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55432/ce_test venv/bin/python -m pytest tests/creation_engine -q
CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55432/ce_test venv/bin/python -m pytest -q
```

**Acceptance checklist (WP4 backend).**

- [x] Principal/scope/key deduplication with retained receipt identity and current authorization.
- [x] Durable scope gate, explicit action states, atomic checkpoints and recorded randomness.
- [x] Before/after-commit crash proof with two real worker processes.
- [x] Source occurrence isolation; resource bounds; atomic, unique effect applications.
- [x] Lease fences distinct from authority epochs; stale/expired workers cannot commit.
- [x] Persistent outbox, consumer deduplication and consistent internal snapshot recovery.
- [x] Precommit limits/cancellation and deterministic action-tree budgets.
- [x] Full regression plus final focused verification recorded: 1,067 and 435 passed, respectively.

**Retention / residual work.** Code, migration and fixtures are repository artifacts. Raw logs
are retained under the Codex task workspace's `creation-engine/wp4/` (`full-regression.log`,
`engine-final.log`). The disposable PostgreSQL container was stopped after verification. No production schema was
changed and no running app imports the new runtime adapter. Public receipt projection, permissions
on each transport, subscriptions and audience-bound recovery are WP6. Registered RDL/authoring
compilers and the remaining mutation adapters are WP7/WP8. The three host ports remain mandatory
integration contracts; the tests supply explicit fixture implementations. Live cutover remains
excluded. G1 exit still requires the later packages and human acceptance study.

**Next step.** WP5: persisted pending decisions, deadlines/clock anomalies, responder revocation,
operator intervention and manual-resolution provenance, attached to these action/checkpoint records.


### WP5 — persisted decisions and operator recovery (2026-09-26)

**Input / status.** Continued from WP4 commit `66b6fc4` and the existing WP5 working changes,
under the approved v1.1.4 specification, core wire 1.1.3 and registry A1. This is G1 Deploy;
the reconciled v1.2 reading edition supplies no additional implementation requirements.
The backend decision and recovery implementation is complete and verified in the working tree. Verification below
tracks this checkout, not a new commit or completion of the G1 milestone.

**Implementation summary / files.**

- `kernel/decisions.py` and `kernel/activity.py`: explicit question contracts attached to frozen
  activity windows, exact registered answer schemas, optional declared declines and retained
  decision versions. A waiting window cannot omit its question contract.
- `kernel/decision_service.py` and `kernel/service.py`: once-only decision responses;
  `ReissueDecision`, `ReassignDecisionResponder`, `ResumeSuspendedAction` and
  `ResolveActionManually`; operator adjustments within the held action frame. Responder,
  context-fact and operator-authority registrations fail closed when absent.
- `store/runtime.py`, `store/runtime_models.py` and
  `migrations/migration_m75_creation_engine_decisions.sql`: durable pending decisions,
  immutable closed versions, retained answers, scope timeout/heartbeat policy and commit-time
  deadline checks under the scope row lock. M75 is additive after M74 and repeatable.
- `tests/creation_engine/test_ce_decisions.py` and `test_ce_kernel.py`: PostgreSQL acceptance
  scenarios, distinct worker processes, abrupt process exits, controlled clocks and database
  history guards. The kernel fixture now applies M75 after M74.

**Behavior and integration contracts.**

- A response binds the action/checkpoint, question/schema version, opaque context nonce,
  current eligible responder and current mechanical context. Matching retries retain the
  original receipt and recheck authorization before returning it. Accepted answers feed
  subsequent checkpoints without repeating earlier resource costs or random draws.
- Human commands serialize on the scope row lock. They do not acquire the execution worker's
  lease: another request worker can accept a response or operator intervention while the
  execution worker retains its lease and fence. Worker continuation and heartbeat remain fenced.
- Timeout policy is copied into each decision (120 seconds by default, within 30–600).
  Mandatory expiry suspends the action and retains the gate; an optional expiry records only
  its explicitly declared decline. Acceptance checks the shared clock at the commit boundary.
- A heartbeat gap past a deadline invalidates the question and suspends for operator review,
  without expiring it or inventing an answer. A gap ending before the deadline leaves a valid
  question usable. The persisted time watermark prevents a backward step reopening history.
- Reissue creates a fresh version, nonce and explicit deadline. Reassignment rotates the
  version and nonce but preserves the deadline; it cannot revive an expired window.
  Accepted outcomes cannot be rewritten. Resume cannot bypass an unresolved question.
- Policy writers call `policy_changed` in the same scope-locked transaction as grant or
  membership revocation; this bypasses the mechanical gate and invalidates pending questions.
  Operator resource changes are checkpoints in the active frame and invalidate old prompts.
- Manual completion records adjudicator, reason, outcome note, execution lock and explicit
  manual provenance. Each resource adjustment still needs its own authorization. It can
  recover an action whose pinned evaluator is unavailable without executing that evaluator.
- The host must register the three trusted ports and schedule the lease holder's heartbeat
  every 30 seconds while decisions are open. Public projections, transport authorization,
  subscription revocation and visible manual labels remain WP6 integration obligations.

**Proofs / verification.**

- Decision suite: **48 passed, 0 failed, 0 skipped** in **24.59 s**, using PostgreSQL 16
  (7 existing ORM/table-sorting warnings).
- Complete Creation Engine suite: **485 passed, 0 failed, 0 skipped** in **70.25 s**
  (9 existing ORM/table-sorting warnings), including the package import guard.
- Full repository regression: **1,121 passed, 0 failed, 0 skipped** in **533.76 s** with
  PostgreSQL enabled (3,935 deprecation, ORM and table-sorting warnings). No implementation
  files changed after these successful runs.
- Active specification, core schema and A1 schema SHA-256 values still match
  `docs/creation-engine/active-contract.json`; `git diff --check` passes.
- T09 backend: revocation invalidates the prompt while the gate remains held; revoked or
  unusable accounts cannot answer or retrieve a previously accepted response receipt.
- T10: operator adjustments invalidate the question in the same transaction; an unannounced
  mechanical-context change also prevents the old token authorizing effects.
- T11/T54: mandatory and optional deadlines, commit-time acceptance, copied timeout policy,
  forward gaps, backward time and explicit reissue are covered with controlled authority time.
- T50 backend: manual provenance is durable and operator status cannot grant control of
  another principal's resource. Verification of every public projection belongs to WP6.
- Different worker processes racing with matching or distinct keys accept one outcome.
  Process death immediately before commit leaves no accepted answer; death after commit
  retains one answer, checkpoint and receipt for recovery on another worker.
- Five added regression cases failed before the worker-lease and pre-deadline clock-gap fixes,
  then passed. Two further tests exercise actual process death at the commit boundaries.

Verification commands (repository `venv/`, separate disposable `ce_test` database on 55435):

```bash
CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55435/ce_test venv/bin/python -m pytest tests/creation_engine/test_ce_decisions.py -q
CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55435/ce_test venv/bin/python -m pytest tests/creation_engine -q
CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55435/ce_test venv/bin/python -m pytest -q
```

**Acceptance checklist (WP5 backend).**

- [x] Persisted, typed, context-bound decisions and once-only authorized acceptance.
- [x] Current responder checks, policy invalidation and active-frame operator intervention.
- [x] Declared optional decline, mandatory suspension, clock-gap review and monotonic time.
- [x] Versioned reissue/reassignment and recovery without rewriting retained outcomes.
- [x] Durable manual provenance with per-resource authorization.
- [x] Competing-worker and before/after-commit process-death verification.
- [x] Complete engine and repository regression verification: 485 and 1,121 passed.

**Retention / residual scope.** Code, migration, tests and this record are repository artifacts.
Raw logs and the pre-edit backup are retained in the Codex task workspace under
`creation-engine/wp5/`; the final runs use `decisions-final.log`, `engine-final.log` and
`full-regression.log`. `gap-reproduction.log` captures the intended failing reproduction;
`decisions-after-fixes.log` is a superseded intermediate failure, not final evidence.
The tests used a separate disposable PostgreSQL container on port 55435, stopped after
verification. `verification.json` in that workspace directory records the final source and
log hashes. No production
migration or cutover is part of this package. Public access remains disabled. **Integration
assumption (medium):** WP6 must wire current policy reads, coordinated policy writes,
heartbeat scheduling and audience projection before exposing this runtime to clients.
Sequential reaction-slot ordering remains G2; this entry does not claim T51 completion.

**Next step.** WP6: policy projection, public receipts and events, transport authorization,
subscription revocation and audience-bound recovery. Continue against v1.1.4/core 1.1.3/A1;
WP7–WP9 and G1 acceptance remain open.


### WP6 — policy projection and public transport (2026-09-26)

**Input / status.** Continued from the verified WP5 working tree at HEAD `66b6fc4`, under
specification v1.1.4, core wire 1.1.3 and registry A1. This is G1 Deploy. Implementation,
focused verification and the full repository regression are complete. This entry
tracks uncommitted working changes, not a new contract, production deployment or G1 exit.

**Implementation summary / files.**

- `policy/rules.py`, `projection.py` and `public_errors.py`: pure policy checks, labelled
  field/source projection, reviewed declassification, audience-specific cache identity,
  public receipt allowlisting and stable sanitized errors.
- `store/policy.py`, `policy_models.py` and
  `migrations/migration_m76_creation_engine_policy.sql`: versioned policies, entitlement
  epochs, View As sessions, subscriptions, opaque cursors, public request records and
  append-only security history. M76 follows M75 and is repeatable.
- `store/public.py`: one gateway for current authorization, projected objects/search/outcomes,
  decisions, receipts and subscription recovery. `store/maintenance.py` supplies the periodic
  heartbeat/expiry worker for scopes whose pinned registrations match the worker.
- `kernel/service.py` and `decision_service.py`: a trusted database-only request-recording
  port, committed atomically with the receipt so public recovery survives a lost response.
- `transports/common.py`, `http.py` and `sockets.py`, with registration in `vtt/__init__.py`
  and default-off flags in `vtt/config.py`: authenticated REST and a dedicated Socket.IO
  namespace using the same gateway and strict command parser.
- `tests/creation_engine/test_ce_policy.py`, `test_ce_public.py`, `test_ce_transports.py`
  and the configuration extension to `test_ce_kernel.py`: pure policy, PostgreSQL,
  competing-process and authenticated transport verification.
- `docs/creation-engine/runtime-integration.md`: trusted builder, writer-lock, worker and
  transport contracts for the WP7 host integration.

**Behavior and integration contracts.**

- Every policy ancestor must grant access; explicit denies win. Owner-private fields require
  the owner's own access or explicit owner grants, including for campaign operators. Platform
  roles and token ownership grant no additional rights. Personal sandbox delegation is explicit.
- Derived fields require the intersection of their labelled inputs, unless a reviewed rule
  in the execution lock's configuration authorizes that exact field/category/audience.
  Private source names, content hashes, URLs and omitted counts remain hidden. Read, explain,
  export, search, snapshots and events share projection; search filters before ranking/counting.
- Cache identity binds the current audience, entitlement state, policy epoch, scope, state,
  execution lock and representation version. Access and expiry are checked again at delivery,
  including cache hits. Configuration mismatches fail closed before projection.
- View As intersects operator and member rights, expires after 15 minutes and audits entry,
  exit and expiry. It cannot mutate or obtain another member's response token. Rejected expired
  reads retain observed authority time so a backward clock step cannot reopen the session.
- Coordinated policy changes invalidate open decisions, subscriptions and View As in the same
  scope-locked transaction while retaining the mechanical gate. Every delivery also rereads
  current membership/account/entitlements; cached data cannot bypass a legacy revocation.
- Public receipts follow the approved schema and omit internal outcome digests. Retrieval and
  matching retries reauthorize the originating command. Eligible responders receive opaque
  nonces, never context digests; manual outcomes and their event/export projections are labelled.
- REST and Socket.IO use authenticated local identity and CSRF checks. Socket commands carry
  raw JSON envelope text so duplicate keys and invalid numbers reach the strict parser.
  Subscriptions bind scope, principal, connection and current authority. Cursors are random
  identifiers, not event sequences; stale cursors recover a permitted snapshot.
- Delivery is requested through `ce:poll` on `/creation-engine`, filtered and enqueued only to
  that connection under current authorization. Lost acknowledgments can replay permitted
  event IDs without repeating mutations. Delivery callbacks must enqueue without waiting for
  remote acknowledgments while the transaction's authorization locks are held.
- CE_RUNTIME, CE_AUTHORING and CE_SHADOW default off. Enabling a surface without an explicitly
  installed host gateway returns ENGINE_UNAVAILABLE. No production gateway or worker is started.

**Proofs / verification.**

- Focused policy/database/transport review: **81 passed** in **23.97 s** (112 warnings).
- Subsequent complete Creation Engine run: **572 passed, 0 failed, 0 skipped** in **98.76 s**
  (119 warnings), including the added clock-rollback and pinned-worker maintenance cases.
- Final sandbox-delegation regression: **1 passed, 33 deselected** in **4.49 s** (7 warnings).
  This final change is included in the full repository run below.
- Final full repository regression: **1,209 passed, 0 failed, 0 skipped** in **531.67 s**
  with PostgreSQL enabled (4,045 deprecation, ORM and table-sorting warnings). No implementation
  files changed after this run. The earlier engine/focused counts above precede the last added cases.
- Active specification, core schema and A1 SHA-256 values still match
  `docs/creation-engine/active-contract.json`; `git diff --check` passes.
- T22–T24: the real F-CURSE evaluator yields defense 12 from 13 minus a private 1; all public
  output modes disclose only the reviewed result. The variant without a reviewed rule withholds
  it. GM-warmed caches, other scopes, owner-private fields and View As cannot widen access.
- T25: separate processes race delivery with revocation under database locks; prompt, receipt,
  subscription and View As checks observe current authority. A failed policy transaction leaves
  the earlier prompt, epoch and subscription intact.
- T47: response nonces and public receipts do not expose context/outcome content digests;
  another member cannot retrieve them. Public receipt authorization survives a crash injected
  after the kernel commit, and neither record survives a failure before commit.
- The receipt recovery regression first reproduced the missing authorization record after
  commit (one expected failure), then passed after the atomic recording fix.
- T08 transport portion: permitted event replay, private-event omission, connection-bound
  cursors and stale-cursor snapshot recovery. T50 public portion: manual labels on outcomes,
  exports and events. Transport admission tests cover size, identity spoofing and malformed JSON.

Verification commands (repository `venv/`, disposable PostgreSQL 16 database on 55436):

```bash
CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55436/ce_test venv/bin/python -m pytest tests/creation_engine/test_ce_policy.py tests/creation_engine/test_ce_public.py tests/creation_engine/test_ce_transports.py -q
CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55436/ce_test venv/bin/python -m pytest tests/creation_engine -q
CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55436/ce_test venv/bin/python -m pytest tests/creation_engine/test_ce_public.py -q -k personal_sandbox_delegation
CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55436/ce_test venv/bin/python -m pytest -q
```

**Acceptance checklist (WP6 backend/transport).**

- [x] Field/source policy intersection, reviewed declassification and owner-private rules.
- [x] Current-audience cache identity, read-only View As, expiry and audit history.
- [x] Atomic policy invalidation, current delivery checks and competing-process revocation proof.
- [x] Public receipt filtering/recovery, opaque decision tokens and manual output labels.
- [x] Authenticated REST/Socket.IO, audience-bound cursors and permitted snapshot recovery.
- [x] Final full repository regression: 1,209 passed; retained verification manifest.

**Retention / residual scope.** Repository artifacts contain the implementation, M76, tests
and integration guide. Raw logs and pre-edit backups are retained in the Codex task workspace
under `creation-engine/wp6/`. `focused-final.log`, `engine-verified.log`, `delegation-final.log`
and `full-regression.log` retain the runs above; earlier logs are superseded. The intentional
before-fix failure is in `receipt-gap-reproduction.log`.
The workspace's `verification.json` records commands, exact results, source/log hashes and
cleanup. The disposable WP6 PostgreSQL container on port 55436 was stopped and removed after
verification; the preexisting test database on port 55432 was preserved.

**Integration obligation (medium):** WP7 must supply legacy document/control mappings and
connect membership/account/entitlement writers to the coordinated scope-lock protocol when
installing the gateway. Current-read denial does not replace atomic writer-side prompt/epoch
invalidation. WP7 must also install the matching worker's 30-second maintenance schedule.
WP8 supplies authoring registrations and UI bindings. No production schema migration, live
cutover, human acceptance study or G1 exit is claimed by this package.

**Next step.** WP7: legacy RDL mapping, migration ledger, SHADOW parity, fixture-only ENGINE
cutover and legacy-write translation, including sheet/token agreement. Continue against the
approved v1.1.4/core 1.1.3/A1 contract; WP8–WP9 and G1 acceptance remain open.


### WP7 — legacy RDL migration and compatibility (2026-09-26; evidence finalized 2026-09-27)

**Input / status.** Continued from the verified WP6 working tree at HEAD `66b6fc4`, under
specification v1.1.4, core wire 1.1.3 and registry A1. This is G1 Deploy. The implementation
and full repository verification are complete. WP5–WP7 remain
uncommitted. This package does not change the active contract or enable a production surface.

**Implementation summary / files.**

- `adapter/mapping.py`: pure RDL mapping and closed content schemas. Numeric columns become
  labelled legacy inputs; recognized signatures become explicit imported selections without
  applying their descriptive effects. Unknown content stays in inert `legacyMetadata`.
- `store/migration_models.py` and `migrations/migration_m77_creation_engine_legacy.sql`:
  bijective source/version ledger, scope links, parity reports/approvals, imported grants,
  runtime inputs, representations and workspace-command deduplication. M77 is additive and
  repeatable; source identities, reports, approvals and representation links are append-only.
- `store/legacy/migration.py` and `snapshots.py`: authenticated campaign provisioning,
  scope-wide mapping/SHADOW/freeze/cutover/abort, current dual-capacity approvals and atomic
  installation of revisions, execution lock, occurrences, resources and authority epoch.
- `store/legacy/inputs.py`: `SetBaseValue`, `SetValueOverride`, `ClearValueOverride` and
  `SetItemEquipped`, using existing checkpoints, receipts, scope gate and lease checks.
- `store/legacy/guards.py`, `compatibility.py` and `projections.py`: one authority guard for
  ORM writers, coordinated policy invalidation, legacy-write translation, labelled projection
  and shared occurrence resources across token/sheet representations.
- `transports/legacy_host.py` and `legacy_http.py`, plus existing transport adapters:
  explicit host installation, legacy route interception, migration preview, token projection,
  SHADOW-only command admission and the `flask ce-maintain` worker entry point.
- `vtt/ce_compat.py`, character/token serializers, character and campaign routes, socket
  handlers and traps: small host lookups connecting existing paths to the adapter. App/config
  wiring adds CE_LEGACY_ADAPTER, off by default alongside the existing flags.
- `content/records.py`: dependency discovery ignores the declared inert legacy container,
  including imported JSON that resembles tagged engine references. Public errors include an
  authorized-refresh instruction on authority-epoch mismatch.
- `test_ce_migration.py` and `test_ce_legacy_transports.py`: real legacy database rows,
  authenticated existing routes, scope-fence concurrency and authority/projection regressions.

**Behavior and integration contracts.**

- F-RDL-CONFLICT variants preserve AC 12 and 13 respectively. Neither “Defensiver Stil” nor
  imported armor adds another bonus to a total whose history is unknown. Original JSON,
  quantities, descriptions and unsupported mechanics remain available as inert metadata;
  imported item capabilities are labelled manual.
- SHADOW enumerates every active character in a scope and reports mapped fields, discrepancies
  and unsupported behavior. It changes no legacy table or live resource ledger. Current HP
  outside bounds and divergent token copies require explicit reconciliation by both current
  controller and operator. A stale source snapshot invalidates earlier report approvals.
- Freeze and legacy writers acquire the same runtime scope row lock. Cutover rechecks the
  exact reviewed report, all current source rows, quiescence and approvals, then installs every
  occurrence atomically. A per-character authority switch is unavailable. Every legacy cutover
  requires a trusted fixture flag; the public command cannot set it.
- ENGINE resource edits translate to the shared resource ledger. Calculated values and base
  attributes translate to the registered input commands; equipment toggles require control
  of the holder. A maximum cannot silently discard current resources. Unsupported/mixed edits
  are rejected before any partial change; progression and item transfer remain later work.
- Compatibility requests need explicit authority/version/idempotency context. Matching absolute
  resource retries recover their original delta and receipt even after the value changes.
  Workspace creation keys and runtime command keys are distinct namespaces.
- Sheet and export reads use current engine policy. Unknown imported metadata is owner-private
  by default. Token projection checks representation visibility as well as engine policy and
  View As. Legacy room broadcasts carry a reference instead of audience-specific engine HP.
- New token representations ignore incoming HP. Position changes remain presentation state.
  Traps refuse ENGINE targets before drawing damage dice. ENGINE character transfer is rejected
  with SCOPE_TRANSFER_UNSUPPORTED. No legacy column becomes a second authoritative writer.
- ORM model helpers and bulk writers acquire scope locks before mutation. Membership/account/
  campaign policy changes invalidate prompts, subscriptions and View As in the same transaction.
  Background policy writers supply an authenticated audit actor explicitly; rollback clears
  queued invalidations. Entitlement issuers use the existing PolicyStore.changed contract.
- The installed host provides a distinct worker identity and `flask ce-maintain` for the
  existing 30-second maintenance loop. Installation starts no worker thread. Native activity
  registrations and authored sandbox/item creation are the WP8 integration boundary.

**Proofs / verification.**

- Initial migration/guard/transport package run: **37 passed** in **51.21 s** (375 warnings),
  before the final combat, visibility, strict-JSON and registration cases.
- Creation Engine verification: **615 passed, 0 failed, 0 skipped** in **157.51 s**
  (528 warnings). This run includes the final source-layout and workspace-key corrections.
- Final pinned-worker regression: **1 passed, 26 deselected** in **6.33 s** (13 warnings).
  Its registration check and added case are included in the full repository run below.
- Full repository regression: **1,252 passed, 0 failed, 0 skipped** in **604.59 s**
  (4,460 warnings), including the final pinned-worker regression. The retained pytest log
  contains the completed passing summary; the original shell session expired before its
  exit status could be retrieved after resumption, so no separate process-exit claim is made.
  All 48 files in `full-run-source.json` still match their hashes from the running test session.
- T01: both existing-character conflict variants, inert tagged-looking JSON, recognized manual
  selections, shadow snapshots and explicit resource-bound reconciliation.
- T02: authenticated sheet, equipment, combat and Socket.IO translation; retries, missing epoch,
  unsupported/mixed writes, direct ORM/bulk bypass attempts and maximum-reduction refusal.
- T03: two tokens in different sessions share their character occurrence's HP; a second campaign
  remains independent. New representations cannot seed a separate HP pool.
- T48: partial campaign mapping fails; an active engine frame blocks a legacy calculated edit;
  a real separate process holds the legacy-write fence while cutover waits. Freeze then captures
  its committed value, and a subsequent worker cannot write through the frozen scope.
- Failures injected before/after the cutover commit leave either the original frozen scope with
  no installed occurrences or the entire new ENGINE scope with one increased authority epoch.
- All legacy tables are snapshotted before and after SHADOW and compared unchanged. Policy-write
  rollback preserves current subscriptions, and current membership/account revocation closes them.
- The first broad run found seven import-boundary failures in the new I/O file placement.
  These files were moved into store/transports; the existing boundary test was not relaxed.
  Its focused rerun passed all **34** checks; the final engine run above includes them.
- Specification, core schema and A1 hashes still match `active-contract.json`; `git diff --check`
  passes. The frozen v1.2 research/reconciliation artifacts were not regenerated.

Verification commands (repository `venv/`, disposable PostgreSQL 16 database on 55437):

```bash
CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55437/ce_test venv/bin/python -m pytest tests/creation_engine/test_ce_migration.py tests/creation_engine/test_ce_legacy_transports.py -q
venv/bin/python -m pytest tests/creation_engine/test_ce_boundaries.py -q
CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55437/ce_test venv/bin/python -m pytest tests/creation_engine -q
CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55437/ce_test venv/bin/python -m pytest tests/creation_engine/test_ce_migration.py -q -k wrong_migration_worker
CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55437/ce_test venv/bin/python -m pytest -q
```

**Acceptance checklist (WP7 backend/compatibility).**

- [x] Labelled legacy baselines, inert metadata and imported selections without double application.
- [x] Bijective mapping, complete scope SHADOW reports and current dual-capacity discrepancy approval.
- [x] Quiescent fixture-only cutover, authority fencing and atomic failure-boundary verification.
- [x] Shared token/sheet resources, input-command translation and no second legacy writer.
- [x] Current-policy compatibility reads, coordinated revocation and explicit host/worker installation.
- [x] Real competing-process fence test and unchanged pure-core import guard.
- [x] Final repository regression and retained verification manifest.

**Retention / residual scope.** Implementation, migration, tests and the updated runtime integration
guide are repository artifacts. The Codex task workspace retains pre-edit backups and logs under
`creation-engine/wp7/`. The recorded runs use `wp7-review.log`, `boundaries-final.log`,
`engine-final.log`, `registration-final.log` and `full-regression.log`; earlier runs are superseded.
The first `engine-review.log` records the seven corrected source-placement failures.
`verification.json` records the final counts, source and artifact hashes, and cleanup evidence.
The disposable WP7 PostgreSQL container was stopped and removed; the preexisting test database
and production containers were preserved.

**Integration boundary (medium, assigned to WP8):** authored activities, new authored sandbox/item
creation and Guided/Structured/Advanced client bindings remain to be connected. Existing legacy
capabilities are not automatically executable. Bulk migration jobs, post-mutation semantic rollback
and transfer belong to their later contracts. Raw administrative SQL is not a supported gameplay
write path. All engine/adapter flags remain off; production schema and data were not changed.
G1 exit still requires WP8–WP9 and the human acceptance study.

**Next step.** WP8: the flame-sword authoring slice across Guided, Structured and Advanced modes,
including registered activity execution and German/English/French question identity. Continue the
approved v1.1.4/core 1.1.3/A1 contract; no renewed specification phase is needed.

### WP8 — guided authoring, durable drafts and native sandbox execution (2026-09-27)

**Status.** Implemented and verified in the working tree. The active authority remains approved
v1.1.4, core wire 1.1.3 and registry A1; no specification, wire schema, approval or frozen reading
edition was changed. WP1–WP4 remain committed at HEAD `66b6fc4`; WP5–WP8 remain uncommitted.

**Implementation.** The new pure compiler supplies stable question/version/path ownership,
typed schemas, deterministic ordering, explicit dependencies/invalidation, de/en/fr prompts,
reviewed opt-in presets and mechanical quality gates. Guided, Structured and Advanced use the
same RecordDraftDecision operation. Free prose creates no mechanics. Required questions cannot
be skipped; optional questions can. Changing a decision removes active descendant values while
retaining stale answers and append-only history. A dependency dead end exposes Structured
recovery; an unreviewed registry/compiler change is refused.

M78 adds immutable compiler snapshots, draft receipts and workspace results. Its only change
to M77 is allowing a workspace creation command without a runtime scope; all workspace commands
still share the same principal/workspace/key namespace. Draft content, answers, snapshots,
immutable revisions and receipts commit together, with current owner/account checks and an
expected draft version. Revert creates a new version. Commit validates the declared quality and
records the registry, compiler and question provenance. Preset digests seal the reviewed values
and displayed language; replay cannot substitute another preview or silently reinterpret a
revision under a different compiler.

The authenticated editor at `/api/ce/authoring` provides all three modes, localized questions,
readable previews, quality gates, preset review, stale-answer notices, revision saves and history.
REST and Socket.IO share the same strict command dispatch. Views/locale changes are reads;
unsaved inputs are protected and uncertain network outcomes retain the exact retry command.
The closed PublicReceipt shape is unchanged; owner-only result reads expose created references.

The native host profile separately pins RDL G1 **1.1.0**, the native schema bundle and `g1.flames:1`
configuration. Existing 1.0.0 artifacts and scopes are not upgraded. CreateSandboxScope resolves
exact authorized revisions; InstantiateRevision requires lock membership and gives each copy
independent resource ledgers. Held items start unequipped. Harmless activation cannot draw damage.
The optional flame child follows a committed, explicitly attested hit: accepting spends charges,
records the authored dice and adjusts the same target's HP in one checkpoint; declining or a
timely timeout preserves the hit without spending or rolling. Recovery is an explicit attestation
of the author's chosen event. A failed child preserves committed parent history and suspends for
operator resolution. Exact child requests and the fenced maintenance continuation survive a lost
reply/restart without duplicating a committed cost or roll.

Native calculations require explicit engine-compute grants. Fixture campaign instantiation also
requires operator authority and a separate, default-denied deploy capability. Native event
projections require every involved object's current read grant, private outcomes retain source
labels, decision tokens are restricted to eligible responders, and summary errors use the public
allowlist. No native activity, grant or callback can be supplied by ordinary content.

**Files.** Added `compiler/{interview,flame,catalog,runtime}.py`, authoring/native store adapters and
models, the M78 migration, authoring routes, the editor template/JS/CSS, and four focused test
modules. Integrated the existing host/transport dispatch, policy projection, maintenance worker
and kernel's bounded declared-roll adjustment port. Updated the runtime integration guide and
status entry point. Pure engine modules still pass the existing framework-import guard.
No external runtime dependency was added.

**Verification.** PostgreSQL 16 used only the disposable `ce_test` database at localhost:55438;
browser cases used authenticated Flask routes and installed Chromium through Playwright.

| Run | Observed result |
| --- | --- |
| Compiler and boundary review | 64 passed |
| Authoring/store review | 86 passed |
| Engine regression before native integration | 676 passed; completed pytest summary retained |
| Native/browser/policy/boundary review | 84 passed, exit 0 |
| Explicit compute/deploy authority checks | 2 passed, 9 deselected, exit 0 |
| Full repository regression | 1,325 passed, 1 failed, 4,467 warnings in 648.39s; exit 1 |
| Existing browser-icon contract after fix | 2 passed, exit 0 |
| Final follow-up over authoring, compiler, native runtime, browser, boundaries and icon | **113 passed**, 13 warnings in 76.39s; exit 0 |
| JavaScript syntax and whitespace checks | Passed |
| Active specification/core/registry hash checks | All three unchanged |

The full run's sole failure was the new template's missing shared browser icon. The icon was
added and its existing contract tests passed. Subsequent review strengthened immutable revision
provenance, sandbox error sanitization and translated-preset audit locale. The final follow-up
exercises every changed implementation/template path; there was **no second full-suite run**.
Do not describe the initial full run itself as all green. Its source snapshot and all later
source changes are retained so these two verification stages remain distinguishable.

Exact primary commands (CE_TEST_DATABASE_URL pointed to the disposable database):

```text
CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55438/ce_test venv/bin/python -m pytest -q
CE_TEST_DATABASE_URL=postgresql://postgres:ce_test@127.0.0.1:55438/ce_test venv/bin/python -m pytest tests/creation_engine/test_ce_native.py tests/creation_engine/test_ce_authoring.py tests/creation_engine/test_ce_authoring_transports.py tests/creation_engine/test_ce_compiler.py tests/creation_engine/test_ce_boundaries.py tests/test_browser_icon_contract.py -q
node --check vtt/static/js/creation-engine.js
git diff --check
```

**Acceptance checklist (WP8).**

- [x] T31: harmless flames have no invented damage; earlier answers invalidate descendants visibly.
- [x] T32: Guided/Structured/Advanced and de/en/fr retain valid decisions; upgrades require review.
- [x] Atomic draft history, current authorization, competing saves, exact retry and rollback proof.
- [x] Immutable revision quality/provenance checks and reviewed preset application.
- [x] Exact-lock private sandbox creation, independent copies, equip state and charge use/recovery.
- [x] Optional post-hit damage child; decline/timeout and failure-boundary recovery preserve the hit.
- [x] Real browser authoring-to-execution flow; current-policy output and compute/deploy checks.
- [x] Regression failure fixed and final changed paths reverified; evidence retained.

**Retention and limits.** The task workspace retains `creation-engine/wp8/` backups, logs, exit
codes, source hashes, screenshot and `verification.json`. `full-initial-regression.log` and
`full-initial-run-source.json` identify the initial full run; `post-full-changes.json`,
`followup-source.json` and `final-followup.log` identify final verification. M78 was never applied
to production. The task's disposable PostgreSQL container is removed after verification; the
preexisting test and production containers are preserved. All engine flags remain off by default.

This bounded native profile explicitly attests hits/recovery and supports activation/hit-window
durations. It does not claim complete attack/resistance/calendar automation or manufacture missing
character statistics. Existing scopes require their original registered worker; switching a host
profile is not a lock migration. Automated browser checks are not the formative user study.

**Next step.** WP9: consolidate G1 acceptance evidence, execute the required ≥8-target-user study
and assess the milestone exit against §22. G1 remains open; no production cutover is authorized.

### WP9 — evidence preparation and scheduled WP8 product test (2026-09-27)

**Status.** Preparation documented; user-study execution is pending. The user reports that the
WP8 test is scheduled for **Tuesday, 29 September 2026**, Europe/Berlin. Its exact time and
participant roster have not been supplied. This records the user's schedule, not an agent-created
calendar event. Per the user's instruction, no participant/usability testing takes place before
that date; design, automated checks, source review and isolated fixture preparation can continue.

WP8 names the implemented authoring slice being tested; WP9 owns its acceptance evidence.
The scheduled session does not waive the existing §22 requirement of at least eight target users,
the four T45 tasks, the completion threshold, zero unnoticed creative defaults or resolution of
recurrent confusion. G1 remains in Deploy and its exit remains open. No spec, wire, registry,
approval record, production data or engine flag was changed by this documentation work.

**Design package and backlog.** The user authorized the bounded VTT design follow-up described
in the 27 September discovery. The Apply package is retained in:

- `docs/vtt-design/README.md` — entry point and distinct design/engine status;
- `docs/vtt-design/authoring-sandbox-design-v0.1.md` — source reconciliation, shared-theme and
  navigation integration, authoring/sandbox states, interfaces, tradeoffs and implementation handoff;
- `docs/vtt-design/authoring-sandbox-contracts-v0.1.md` — 16 specified observable contracts,
  `VD-C01`–`VD-C16`, without renumbering engine acceptance IDs;
- `docs/vtt-design/test-backlog-2026-09-29.md` — 16 engineering cases, seven deferred human
  scenarios, fixtures, planned coverage, priorities, responsibility roles and evidence/scoring rules;
- `docs/vtt-design/study-results-template.csv` — empty observation register; no invented results.

**Acceptance gap (medium, open).** WP8 supplies magic-item authoring and a bounded post-hit flame
path. It does not establish a general conditional-effect or authored-choice UI. An existing
yes/no runtime response is not proof of authoring a choice. Lore-only item prose is a candidate
bounded lore task whose fit must be recorded before the study. Backlog VD-T01 and VD-H02–VD-H04
keep these gaps visible. Unsupported tasks cannot be replaced by moderator-created content,
silently removed from the scoring denominator or recorded as passes. A partial Tuesday session
can yield useful WP8 feedback while leaving the complete G1 study obligation open.

**Design conformance gaps (medium, open).** The current editor uses a separate dark palette and
dashboard backlink, and its automated browser fixture is Chromium at 1280×960. Shared VTT
navigation/theme integration, distinct same-named-copy labels, responsive/zoom coverage and
complete keyboard/focus/permission-state evidence remain backlog work. The new contracts are
specified targets; this package makes no claim that they are already implemented or accepted.

**Verification and retention.** This is documentation-only work. Local references, contract/test
ID coverage, operation names against the active schemas, the empty CSV template, date and source
identity are checked. The active authority pins and the 92 source hashes retained for WP8 are
unchanged. No runtime suite or participant session was executed for this package. The task
workspace retains before-document snapshots and the document verification record under
`vtt-design-2026-09-27/`; earlier WP8 run artifacts remain historical evidence, not new design
verification. The project status entry point links the schedule and backlog.

**Next step.** Prepare the selected test build/fixtures and complete the bounded technical/design
backlog as appropriate. Record Tuesday's actual build, participants, supported task scope and
results, then consolidate WP9 evidence and unresolved findings. Do not close G1 merely because
the session date arrives or because automation passes.

### VTT design follow-up — slice 1 implementation (2026-09-27)

**Authorization/status.** The user instructed “go ahead and continue” after receiving the bounded
design/contracts/backlog package. Its first UI integration slice is implemented and verified in
the working tree. This is a design implementation follow-up to WP8, not a new engine specification
phase or G1 exit. Human testing remains deferred until Tuesday, 29 September; time and attendance
are still unrecorded here. No new architecture, dependency or engine protocol was introduced.

**Implementation.** The real BookScene dashboard renders a contextual authoring entry using
private server-provided availability metadata. The helper checks the installed authoring host,
feature flag and usable account, excludes View As, and creates no workspace/draft during a
dashboard read. Existing primary session/preparation actions retain priority. The editor uses
the shared theme/fonts/navigation styles with scoped feature CSS, localizes its orientation in
de/en/fr, and uses a single column below 1200 CSS px. Native links preserve existing VTT targets;
dirty/pending navigation is guarded and a lost response retains the exact retry command. The
current saved draft name/version is visible. Domain operations and current authorization remain
server-owned and unchanged.

**Files/evidence.** `docs/vtt-design/deploy-slice1-2026-09-27.md` records the six implementation
files, `tests/creation_engine/test_ce_design.py`, exact commands, source/evidence retention,
acceptance boundaries and rollback. The design README, test backlog and engine status entry point
are updated. Logs, before snapshots, screenshots and the verification manifest are retained under
the task workspace's `vtt-design-slice1-2026-09-27/`; historical WP8 artifacts were preserved.

**Verification.** Initial design review: 11 passed, exit 0. Final selected regression: **111 passed,
20 warnings in 56.91s, exit 0**, including the final 12 design cases plus authoring/store/browser,
dashboard/book/navigation/icon and pure-core boundary checks. JavaScript syntax and whitespace
checks pass; active specification/core/registry hashes are unchanged. Eighteen Chromium layout
cells (six widths × de/en/fr, height 960, reduced motion) show no horizontal overflow/clipped
controls and the correct column boundary. Six sampled text contrast ratios are 5.07:1–13.92:1.
Guided/Structured desktop and phone-sized screenshots were inspected. This is not a fresh full
repository regression, complete accessibility acceptance or human-study evidence.

**Limits/next step.** Shared theme and entry gaps are implemented; the backlog records partial
coverage without declaring all 16 contracts accepted. Remaining work includes draft conflict/focus
and error handling, distinct same-named-copy identification, in-page revocation races, actual zoom,
Firefox/WebKit, screen-reader/device coverage and the unresolved T45 authoring scope. The task
database container is removed after verification; preexisting containers are preserved. All flags
remain default-off, changes uncommitted, and no production migration/activation/deployment occurred.


### VTT design follow-up — slice 2 implementation (2026-09-27)

**Authorization/scope.** The user's “Ok go” accepted slice 1's next bounded conflict/focus/copy-identity work. Deploy continues against engine specification 1.1.4 / core 1.1.3 / registry A1; no G0 reopening, engine redesign or production cutover. Human testing remains deferred until Tuesday 2026-09-29, Europe/Berlin.

**Implemented.** Draft conflicts retain exact local control values, provide read-only refresh/comparison, and permit explicit restoration/resaving only for a compatible visible/ready question. Guided recovery opens Structured view; JSON remains JSON. New saves use the reviewed version and a new key, while unknown-response retries keep the original envelope. Repeated conflicts and failed refreshes retain input; rejected presets are never automatically applied. Focus is applied after controls are enabled, field errors preserve and identify input, and sandbox copies/actors have consistent distinct references in selectors and resource lists. Short-reference collisions expand to full authorized IDs.

**Files/evidence.** `docs/vtt-design/deploy-slice2-2026-09-27.md` records the three UI files, `tests/creation_engine/test_ce_editor_states.py`, commands, limits, rollback and evidence. The design index, technical backlog and engine status index are updated. Task-workspace `vtt-design-slice2-2026-09-27/` retains before snapshots, development logs, final source hashes, environment details, screenshots and verification. WP8 and slice 1 evidence are preserved.

**Verification.** Dedicated browser run: **11 passed, 7 warnings in 55.57s**, exit 0. Final selected regression: **96 passed, 24 warnings in 168.58s**, exit 0, including the final UI wording and all new cases plus the real dashboard/editor/native sandbox and existing navigation/layout/icon workflows. Development failures and their test-fixture/mid-run-edit causes are retained in the slice report; the final implementation/test hashes stayed fixed throughout the accepted regression. JavaScript syntax, whitespace, local links and authority/reconciliation checks pass. Rerun layout coverage includes 18 reduced-motion width/locale cells and six sampled text contrast ratios (5.07:1–13.92:1); conflict/copy phone-sized screenshots were inspected. This is selected automated coverage, not a fresh full repository run, complete accessibility acceptance or human evidence.

**Limits/next step.** The backlog retains open-page revocation/delayed-response races, hard-tab-loss behavior, uninterrupted full keyboard traversal, actual zoom, Firefox/WebKit, screen-reader and physical-device coverage. T45's missing general conditional-effect/choice authoring capability and ≥8-person/four-task human gate remain open. Continue with those bounded technical gaps and prepare the scheduled WP9 observations. The task database container was removed after verification and preexisting containers preserved. Work remains uncommitted and flags default-off; no production migration, activation or deployment occurred.


### VTT design follow-up — slice 3 implementation (2026-09-27)

**Authorization/scope.** The user's “Continue” accepted the next bounded open-page revocation/accessibility work. G1 remains in Deploy against specification 1.1.4 / core 1.1.3 / registry A1. No server API, policy, schema, migration, dependency or engine operation changes. Human testing remains deferred until Tuesday 2026-09-29, Europe/Berlin.

**Implemented.** Confirmed denial/unavailable responses and changed workspace identities clear protected DOM/client state, disable mutation and focus a localized unavailable/recheck surface. Request generations plus cancellation prevent late responses from restoring an old access state; sandbox/catalog read sequence checks prevent older projections from replacing newer ones. Rechecks use existing GETs, never replay a previous command, and preserve input/exact pending envelopes through transient connection failure. The page checks on visible return/focus and every 15 seconds while visible, with a 10-second timeout per probe request. Runtime availability, revision choices, objects and decisions follow the current projected responses; valid selections persist. Deselection clears hidden scope details. Keyboard recovery and removed-decision focus are covered.

**Files/evidence.** `docs/vtt-design/deploy-slice3-2026-09-27.md` records the JavaScript/template changes, `tests/creation_engine/test_ce_access_states.py`, exact commands, limits and rollback. Design/engine indexes and the technical backlog are updated. Task-workspace `vtt-design-slice3-2026-09-27/` retains the before snapshots, bounded implementation note, development/final logs and exit codes, fixed-source hashes, environment, screenshots and verification manifest. Earlier evidence is preserved.

**Verification.** Initial access run: **12 passed, 7 warnings in 50.71s**, exit 0. Development browser follow-ups recorded 29 passes/2 test-sequencing failures and 31 passes/1 programmatic-focus assumption; the report preserves their corrections. Final fixed-source selected regression: **139 passed, 126 warnings in 236.94s, exit 0**, including all **14 new access-state cases** plus previous conflict/retry/dashboard/editor/native, public-policy and HTTP/socket authorization cases. Existing ORM/table-cycle/UTC warnings remain. Syntax, whitespace, local links and authority/reconciliation checks pass. Eighteen width/locale/reduced-motion layout cells and six sampled text contrasts reran; unavailable-state English/French phone captures were inspected. This is not a full repository run or human/accessibility acceptance.

**Limits/next step.** Detection depends on an actual authorization response, lifecycle signal or completed periodic check; no instantaneous push revocation or offline authorization is promised. Real browser-cache restoration/hard-tab-loss tests, the complete keyboard/assistive-technology/browser/zoom/device matrix and remaining suspended/timeout/receipt-state UI evidence stay open. The T45 capability gaps and ≥8-person/four-task study gate remain unchanged. The task database is removed after verification and preexisting containers preserved. Changes remain uncommitted and flags default-off; no production deployment, activation or migration occurred.


### Task-readiness follow-up — manual authoring and lifecycle evidence (2026-09-27)

**Authorization/scope.** The user's “Ok let's do that” accepted resolving study-task gaps and
continuing technical checks. The bounded Apply revision is `docs/vtt-design/authoring-task-readiness-v0.1.md`.
G1 remains in Deploy; specification 1.1.4 / core 1.1.3 / A1 remain authoritative. The working
assumption is manual authoring first, keeping G2 runtime choices/grants separate. This is not
a decision that manual tasks satisfy T45; acceptance-owner review remains explicit.

**Implemented.** The existing A1 draft/revision path now supports manual conditional-effect
and choice cards plus standalone lore. New profiles have separate versioned registries;
original flame registry bytes, old drafts, native revisions and locks are unchanged. No
creative defaults, executable prose, migration or dependency was introduced. Complete manual
cards can be Sheet-ready; lore requires title/prose. Unsupported runtime/automation quality,
executable sandbox admission and cross-profile flame presets are refused. UI explains these
boundaries in de/en/fr and retains the shared mode/recovery/access handling.

**Evidence.** `docs/vtt-design/deploy-task-readiness-2026-09-27.md` records the scoped changes,
commands, compatibility proof, nine profile/locale browser journeys and five lifecycle cases.
Combined regression: **198 passed, one outdated keyboard-sequence assertion failed, one
optional WebKit test skipped; 128 warnings in 372.88s**. After correcting that test to include
the new content selector, the focused editor-state follow-up passed **11 tests, seven warnings
in 45.13s**. There are **199 distinct passing selected cases, including 33 new ones**. Application
sources were unchanged across the combined run and follow-up. WebKit was attempted but could
not launch on missing host libraries; Firefox is not installed. No full-repository or complete
accessibility result is claimed. Source hashes, before snapshots, diffs, logs and screenshots
are retained under task-workspace `authoring-task-readiness-2026-09-27/`.

**Study preparation/limits.** Task cards, reset protocol, a 299-file candidate source identity
and unfilled session manifest are in `docs/vtt-design/`. The T45 manual-depth ruling, actual
Tuesday time/roster/devices, installed isolated study environment/accounts, remaining browser/
assistive-technology/result-state checks and WP9 human evidence remain open. Human testing
is deferred until 2026-09-29. Changes remain uncommitted and production flags off; no live
deployment, migration or activation occurred.
