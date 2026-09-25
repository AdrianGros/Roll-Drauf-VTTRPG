# DAD-M Program: Creation Engine — G1 pre-authorization plan

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

Nothing here was implemented or executed. No acceptance scenario has run.

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
