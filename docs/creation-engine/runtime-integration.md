# Creation Engine runtime integration — G1 WP6–WP8

This guide describes the implemented policy and transport boundary under specification
v1.1.4, core wire 1.1.3 and registry A1. The active authority is
[README.md](README.md). It does not activate the engine or authorize production cutover.

## Installation boundary

Apply migrations M73, M74, M75, M76 and M77 in order; authoring additionally requires M78; the race-to-sheet adapter also requires M79. Creating ORM tables alone does not install
the append-only history triggers. The default flags remain off: CE_RUNTIME, CE_AUTHORING
and CE_SHADOW. An enabled surface without a configured gateway returns ENGINE_UNAVAILABLE.

The host installs a PublicGateway in app.extensions["ce_gateway"]. The WP7 RDL host supplies
legacy occurrence mapping and document builders; WP8 supplies authoring and native flame registrations.
The gateway requires a Kernel, PolicyStore, labelled document/snapshot/event builders and
the exact configuration used by the ExecutionLock. An optional outcome builder supplies
projected action outcomes. Builders are trusted, versioned server code. Ordinary content
cannot supply callbacks or grants.

A worker must handle only the ruleset, schema bundle and configuration it has installed.
The gateway checks these identities before projecting. The periodic worker also skips
decision scopes requiring different registrations.

## Policy and information flow

PolicyStore.bootstrap installs the approved defaults into an unconfigured owned scope:
campaign DM/CO_DM roles operate the scope, character controllers control their occurrences,
and the personal sandbox owner controls its occurrences. Platform roles and token ownership
supply no extra rights. Subsequent grants are explicit, audited policy changes.

Policies form a bounded tree rooted in the runtime scope. Every ancestor must grant the
requested operation; explicit denies win. Read is also required for explain/export.
Owner-private policies additionally require the owner's own access or an explicit owner grant.
An operator cannot manufacture another owner's private grant. An owner can update grants on
their existing private policy without becoming a campaign operator.

Entitlements are current, scope/principal-specific grants with a version and optional UTC
expiry. They participate in policy checks and cache/subscription identity. Server computation
uses a separate explicit engine-compute grant; it does not grant any client read rights.

Document, Field and Source are internal builder types, not client-supplied payloads:

- Give every object and field a policy ID. Split mixed-audience nested content into separately
  labelled fields/documents; a field's label covers its entire nested value.
- Include every input dependency in a derived field's Source labels, including conditions,
  prior stages, effects and mechanical facts that influenced the value.
- Register reviewed Declassification rules in the pinned configuration's declassifications
  list using each rule's wire() form. A rule names output fields, input categories and
  allowed audience/operations. Content cannot add or choose a new rule.
- Mark content hashes with Field.content_digest. A hash over unreadable source content is
  withheld even when the final numeric outcome can be declassified.
- Keep raw evaluator traces, internal snapshots, receipts and policy records behind this
  boundary. Projection returns neither omitted-source counts nor hidden placeholders.
- Set Document.manual for manual source documents. The gateway additionally derives the
  manual label from the retained checkpoint for event and action-outcome projections.

Read, explanation, export, search, snapshots and event delivery use this projector. Search
filters before matching, ranking and counting. Public receipts use the exact approved
PublicReceipt schema: no outcomeDigest and only currently permitted event IDs/checkpoint IDs.
Only the originating client's received envelopes are eligible for public receipt lookup.

The projection cache includes principal and View As audience, roles, entitlement grants/epoch,
scope, policy epoch, state version, execution lock, representation version, object and operation.
Each request rechecks current account/membership/policy before a cache hit. Cache hashes are
internal; HTTP responses use private, no-store and publish no content ETag.

## Coordinated policy writes and worker maintenance

Policy writers must use the runtime scope lock and the same transaction as the membership,
grant or entitlement change. Call PolicyStore.changed(tx, kernel, authenticated_actor,
reason=...) inside that transaction. It updates the policy/state versions, invalidates open
decisions, revokes subscriptions and closes View As sessions while retaining the mechanical
gate. PolicyStore.replace applies the same behavior to a checked policy revision.

For entitlement changes, pass entitlement_principal and the explicit entitlements list;
valid_until is optional. An epoch-only invalidation can omit the list. The authenticated
policy issuer remains a trusted host integration, not a public content command.

Acquire scope locks before changing membership/account rows. Writers affecting several scopes
must lock them in stable ID order. The installed WP7 host connects existing ORM writers to
this protocol. Delivery also rereads current membership and account
status, so an uncoordinated legacy revocation cannot return a cached privileged payload; that
fallback does not replace atomic prompt/epoch invalidation by the writer.

Run store.maintenance.run(gateway, stop_event) in the configured engine worker, or schedule
tick(gateway) every 30 seconds. It renews the current lease holder's decision heartbeat and
performs View As/subscription/cursor expiry housekeeping. A worker cannot take an unexpired
lease from another worker or process a scope with different pinned registrations.

The public gateway preserves observed authority time on rejected reads and closes expired
View As sessions, so clock rollback cannot revive a session it has already rejected. Failed
reads do not commit the failed operation's writes.

## REST and Socket.IO

All REST routes are under /api/ce and use the app's cookie JWT authentication and CSRF checks.
The local account identity comes from authentication. Request principal/role fields are
rejected. The existing core command envelope remains unchanged.

| Surface | Contract |
| --- | --- |
| POST /commands | Raw command JSON; PublicReceipt result |
| GET /scopes/<scope>/objects/<object> | Projected object; operation=read, explain or export |
| GET /scopes/<scope>/search?q=... | Authorized matches and authorized total |
| GET /scopes/<scope>/receipts/<idempotency-key> | Originating principal's receipt, reauthorized now |
| GET /scopes/<scope>/decisions/<decision> | Eligible responder's question and opaque nonce |
| GET /scopes/<scope>/actions/<action>/outcome | Projected outcome, including manual labels |
| POST /scopes/<scope>/view-as | memberId; read-only session with 15-minute expiry |
| DELETE /scopes/<scope>/view-as/<session> | Close and audit the session |

X-CE-View-As selects the read-only intersection of operator and member permissions. It grants
no mutation, receipt impersonation or response tokens. Unknown and inaccessible references
share the same public NOT_FOUND representation; diagnostics never include internal exception
messages, source values or object paths.

The dedicated Socket.IO namespace is /creation-engine. The connection authenticates its
cookie JWT and requires auth.csrf matching that JWT's CSRF claim. Every event checks the
token again, including expiry/revocation.

- ce:command takes {"command": "<raw JSON envelope text>"}. Text preserves duplicate keys and
  invalid numbers for the same strict parser used by REST. It returns the same PublicReceipt.
- ce:subscribe takes scopeId, contractVersion and authorityEpoch. It returns subscriptionId,
  an opaque cursor and a permitted snapshot. An old authority epoch requests a refresh.
- ce:poll takes scopeId, subscriptionId and cursor. It emits ce:events to that connection only
  and acknowledges the projected page. Clients deduplicate by permitted event ID.
- ce:unsubscribe takes scopeId and revokes that connection's subscriptions.

Subscriptions/cursors are persisted and bound to scope, principal, connection, policy,
entitlement state and authority epoch. No internal sequence or private event ID is exposed.
An invalid/stale cursor gives a new permitted snapshot; a revoked subscription must be
re-established under current authority. Reconnects subscribe with their new connection ID.
Stream consumption is requested through ce:poll; it does not reuse legacy room broadcasts.

Mechanical transactions commit before public projection. At delivery the gateway rechecks
current authority and enqueues the already-filtered page while the scope/account/membership
locks are held. Delivery sinks must enqueue promptly, not wait for remote acknowledgments.
A lost acknowledgment can repeat the same permitted event IDs; it cannot repeat a game-state
mutation. The public receipt's authorization record is committed atomically with the kernel
receipt, so lookup also survives a crash before the first response.

## Verification and remaining integration

The fixtures exercise F-CURSE using the real evaluator and PostgreSQL; two actual processes
race delivery and revocation. REST and Socket.IO tests use authenticated clients, CSRF,
revoked tokens, stale cursors and the same kernel/database path.

See the [G1 program](../../dadm/artifacts/programs/milestone_program_creation_engine_g1.md)
for executed counts and retained logs. WP7 supplies legacy mappings, compatibility
projections, writer translation and host installation as described below. WP8 supplies the authoring editor and native sandbox bindings described below.
The G1 human acceptance study and later-gate deployment/load evidence remain outstanding.

## RDL legacy host (WP7)

After installing M73–M77, enable an engine surface and CE_LEGACY_ADAPTER to install the RDL
host in the Flask factory. All four flags default off. CE_SHADOW permits opening a legacy
campaign scope, mapping characters, starting SHADOW and recording parity approvals. Mechanical
commands and cutover operations also require CE_RUNTIME. The public API cannot mark a scope
as a fixture. Tests use the trusted MigrationService.provision(..., fixture=True) entry point;
every legacy cutover, including a personal scope, checks that flag.

The host factory is transports/legacy_host.py; pure mapping remains in adapter/mapping.py.
PostgreSQL integration is in store/legacy/. Their separation is enforced by the existing import
guard. The host pins the separately versioned RDL G1 ruleset, schema bundle and configuration.
A worker with different registrations cannot change migration state or regenerate reports.

OpenLegacyCampaignScope uses the authenticated account's personal workspace and shares its
idempotency namespace with CreateDraft and CreateSandboxScope. Its receipt identifies the resulting runtime scope; retrying the
workspace command recovers that receipt. Its key does not occupy the runtime command namespace.
Personal legacy scopes can be provisioned through the trusted host entry point. Creation of
new authored sandboxes and item instantiation use WP8's authoring flow below.

MapLegacyCharacter reserves a bijective source/version mapping. BeginScopeShadow requires every
active character in the campaign (or personal sandbox) to be mapped. SHADOW snapshots all
mapped columns, item rows and token representations under the scope lock. It records labelled
legacy totals, exact inert metadata, supported signature selections and manual capabilities.
Selections and descriptive item bonuses do not add themselves to imported totals.

Parity reports list mapped fields, discrepancies and unsupported behavior. The full legacy
snapshot and its digest stay internal; the operator's report digest covers the reviewable
report. An owner can read their character's preview without receiving the whole-scope digest.
Resource bound violations and conflicting token HP copies require both current controller and
operator approval. A token discrepancy cannot be resolved by keeping a second independent HP
value. Source changes replace the report and make earlier approvals inapplicable.

FreezeScopeForCutover captures the exact snapshot and requires quiescence. All ORM writers
acquire the same scope lock before flushing and are refused while frozen. CommitScopeCutover
checks the reviewed digest, source snapshot, approvals, fixture restriction and quiescence,
then installs the pinned revisions, occurrences, grants, resource ledgers and representation
links atomically with the authority-epoch change. AbortScopeCutover returns a frozen scope to
SHADOW. No legacy columns are rewritten during preview or cutover.

Interactive migration is bounded to 128 occurrences and the configured request byte limit.
Larger migrations require an explicit bounded job; that job interface is not implemented here.
Rollback after ENGINE mutations and campaign transfer remain outside this G1 adapter. Attempts
to transfer an ENGINE character return SCOPE_TRANSFER_UNSUPPORTED.

## Legacy compatibility and writers

For ENGINE characters, sheet/read/export routes return the current policy projection. Unknown
metadata is owner-private by default and round-trips as legacyMetadata; even tagged-looking
JSON inside it cannot create revision dependencies or executable behavior. Item occurrences
remain explicitly manual until authored. Their original quantity, descriptions and unsupported
mechanics remain in the inert snapshot.

The compatibility writer accepts one supported field per request. Mixed-field edits are
rejected as a whole, so an unsupported field cannot leave a partial mechanical change.

| Legacy input | Registered engine command |
| --- | --- |
| hp_current / mana_current | AdjustResource, converting an absolute edit to a delta |
| ac / proficiency_bonus / hp_max / mana_max | SetValueOverride |
| str / dex / con / int / wis / cha | SetBaseValue |
| Equipment is_equipped | SetItemEquipped, requiring control of the holder |
| Combat HP delta | AdjustResource with the existing route authorization plus current resource grants |

Maximum edits cannot silently discard current resources. Adjust the resource explicitly
before reducing its maximum below its current amount. Overrides replace the declared numeric
input; separately registered engine effects still pass through the evaluator's stages.

Legacy REST writes carry Idempotency-Key, X-CE-Authority-Epoch and X-CE-Scope-Version alongside
the normal JWT/CSRF authentication. A missing/stale epoch gives AUTHORITY_EPOCH_MISMATCH and an
instruction to reload the authorized projection. Absolute-resource retries reconstruct the
original delta from the retained checkpoint, preserving receipt identity after the value changes.

Legacy token:update uses patch with one supported HP field and a ce object containing
idempotencyKey, authorityEpoch, expectedScopeVersion and the JWT's csrf claim. Engine writes
recheck token validity/revocation and CSRF and return ce:receipt to that connection. They do
not use the legacy process-local deduplication cache. Direct engine commands continue to use
the dedicated /creation-engine namespace and raw JSON envelopes.

New tokens linked to an ENGINE occurrence ignore incoming HP and become another representation
of its ledger. Token positions remain presentation state. Legacy room broadcasts contain an
engine reference and no engine HP; GET /api/ce/migration/tokens/<id>/projection provides current
values after checking both token visibility and the engine policy, including View As.

Progression, level-up, unsupported content edits, item creation/deletion/transfer and trap
damage are refused for ENGINE occurrences. Traps are refused before drawing damage dice.
All ORM mutation paths, including model helpers and bulk ORM updates, pass the same
legacy_write_guard. LEGACY/SHADOW writes keep their existing authority; unrelated scopes remain
writable. Raw SQL outside these installed application paths is a trusted administrative action,
not a supported gameplay write API.

Membership/account/campaign policy writers acquire affected scope locks in ID order and
invalidate prompts, subscriptions and View As in the same transaction. The authenticated JWT
supplies the audit actor for requests. Trusted background writers must explicitly set
session.info["ce_authenticated_actor"] before such writes. Rolling back a writer also discards
queued invalidations. Entitlement issuers continue to use PolicyStore.changed directly.

The installed host registers flask ce-maintain for the 30-second heartbeat/expiry loop. Run it
as the configured worker process; installation does not start a background thread. Each host
instance receives a distinct worker identity. This package neither applies production migrations
nor enables any engine flag.

## Authoring editor and persistence (WP8)

With M78 installed and CE_AUTHORING plus CE_LEGACY_ADAPTER enabled, the authenticated editor
is served at `/api/ce/authoring`. CE_RUNTIME is additionally required to instantiate or execute
items. Flags still default off. A host explicitly supplied without native registrations can
save description/sheet revisions, but returns RUNTIME_REGISTRATION_PENDING for runtime claims.

Guided, Structured and Advanced views all emit RecordDraftDecision with the registered question
identity, typed answer and prompt locale. Advanced edits the owned canonical field, not arbitrary
document paths. German, English and French presentations retain the same decisions. Free prose
is inert. There are no implicit mechanical answers; optional questions may be explicitly skipped.
Changes retract dependent active values, retain their stale answers and append the decision log.
The editor shows invalidations and prevents an unsaved input from being lost in a view switch.
Dependency dead ends have a Structured inspection/recovery view; changing compiler/schema
versions still requires an explicit reviewed migration.

The authoring registry digest covers question metadata, schemas, localized prompts, compiler
version and preset previews. Presets are opt-in and require the exact previewDigest shown to
the author, including the displayed language; A1 PresetRef uses `version`. Applying a translated
preview records that actual prompt locale while preserving the draft's original authoring locale.
Quality claims are checked on the server. An immutable
revision retains registry/compiler/question versions, declared quality and its source draft.
RevertDraft creates a new version and preserves history. Future edits cannot change a revision.

M78 adds append-only compilation snapshots, draft command receipts and workspace results. It
allows a workspace command to have no runtime scope (CreateDraft), while preserving M77's shared
workspace command key. Content versions, answers, snapshots, receipts and revisions commit in
one transaction. Current usable-account/owner checks precede retry lookup; optimistic draft
versions prevent competing tabs from overwriting one another. Receipt bodies retain the exact
closed PublicReceipt schema. Owner-only command-result reads carry draft/revision references.
REST and Socket.IO use the same command gateway and idempotency namespace. CSRF remains required.

## Native flame runtime and sandbox (WP8)

`build_gateway(..., native_authoring=True)` installs RDL G1 ruleset **1.1.0**, the separate
`g1.native-runtime-schemas@1` registry and `g1.flames:1` activity configuration. The Flask installer
selects this profile when CE_AUTHORING is enabled. The existing legacy-only **1.0.0** artifacts
are unchanged. A worker serves only its exact profile; enabling authoring is not a migration of
an existing 1.0.0 execution lock. Existing scopes need their original worker or a later approved
lock migration. G1 does not silently update campaign content or production scopes.

CreateSandboxScope resolves exact, owner-readable revisions and their dependency closure into
an immutable execution lock. InstantiateRevision copies only a revision in that lock. Each item
copy gets its own explicitly authored initial/maximum charges; held items begin unequipped.
Equip changes use SetItemEquipped. Imported character revisions can supply existing actor/target
statistics; the editor does not generate a character or fill in missing statistics. A malformed
imported resource baseline is refused. Sandbox mutation is owner-only. Campaign instantiation
requires a fixture scope, an operator and a separate explicit `deploy` policy grant; no default
campaign deploy grant or public live-cutover path is introduced.

The bounded registered activities are:

| Activity | Behavior |
| --- | --- |
| `g1.flame.activate` | Spend the chosen charge cost and record harmless flames for this activation window; no damage roll |
| `g1.flame.confirmed-hit` | Record a manually attested hit on one existing target, then ask the actor controller whether to use flames |
| `g1.flame.damage-child` | Server-only declared child of that committed hit; spend charges, draw the authored fire dice and apply their sum to the same target's HP in one checkpoint |
| `g1.flame.recover.<event>` | Explicitly attest the authored recovery event and restore that copy's charges to its maximum |

The native slice does not claim automatic attack adjudication, resistance handling or calendar
simulation. Only activation/hit window durations execute here; other duration choices remain
manual. Recovery attestations and confirmed hits are labelled manual. They prevent an
automation_complete claim. Harmless-flame behavior never receives a damage primitive.

RollAdjustment is an internal typed mutation over a declared recorded roll, not a new wire
command, random source or executable content callback. Cost, roll, applied HP delta and discarded
overflow share a checkpoint. A declined or timely expired optional choice spends nothing and
retains the hit. An interrupted child leaves committed parent history intact. Retries recover
the exact child request and cannot repeat a committed cost or roll. Native continuation is
driven after commands and by the existing fenced maintenance worker, including after restart.
Failed children suspend for explicit operator recovery; the editor can record a manual completion
without inventing further resource changes.

Native projections require all involved objects' current read grants before exposing an event.
Private outcomes retain source labels and explicit engine-compute grants. Revoking a compute
grant prevents the activity before any cost or draw. Owner-only sandbox reads supply projected
instances and currently eligible decision tokens; raw internal checkpoint hashes are not public.

The browser supports revision selection, sandbox creation, separate copies, equip state, charge
use/recovery, explicit hit/optional-flame choices and manual completion. Network failures retain
the exact command for retry. The editor and its sandbox controls were exercised against real
PostgreSQL and Chromium; the required ≥8-person formative study remains WP9 work.


## Manual authoring profiles and lore (27 September follow-up)

The owner-only workspace now lists four schema types. `g1.authored-magic-item@1` retains
its original registry and runtime behavior. `g1.authored-manual-conditional@1` and
`g1.authored-manual-choice@1` save complete manual instruction cards as Sheet-ready;
`g1.authored-lore@1` saves title/prose as Lore-only. Each new type pins a separate
authoring registry. The existing A1 commands and M73–M78 storage are reused without a
wire change, migration or new dependency.

Manual conditions, alternatives, consequences and selection counts are author decisions.
They are never interpreted as scripts, runtime predicates, grants or automatic value changes.
All new profiles reject executable quality claims and executable sandbox admission;
non-flame drafts also reject flame presets. Reads/commits resolve the exact type and check
its pinned registry bytes, preserving existing flame drafts and native locks.

See the [design contracts](../vtt-design/authoring-task-readiness-v0.1.md) and
[implementation evidence](../vtt-design/deploy-task-readiness-2026-09-27.md). The T45
acceptance owner still needs to assess the manual task depth; this addition does not
claim the G2 choice/grant runtime, world graph or completed human acceptance.


## D&D race-to-sheet adapter (28 September follow-up)

`dnd5e.authored-race@1` is a fifth, separately pinned authoring profile. It records
an explicit 2014/2024 edition, creature type, size, walking speed in feet, language
rules and up to 20 named features/traits. Optional ability rules, choices and
prerequisites remain manual instructions. Existing profile registry hashes stay
unchanged. The race profile cannot claim executable quality or join the native
flame runtime catalogue.

Apply M79 after M73–M78 before enabling this UI. It adds only
`ce_character_origins` and append-only `ce_sheet_commands`; no legacy character
column or campaign scope is migrated. With the installed host and CE_AUTHORING,
GET/POST `/api/ce/authoring/workspaces/<workspace_id>/sheets` implement the separate
`race-sheet:1` sheet adapter contract. The POST carries a pinned revision and an
idempotency key plus either explicitly supplied new character values or a reviewed
existing character ID/state digest. CSRF, current active account, workspace/source
ownership, target ownership and edition compatibility are enforced server-side.
ENGINE-authoritative targets are refused even for an otherwise idempotent race
replacement. The adapter does not extend the frozen A1 command vocabulary.

A saved race is explicitly shared with the selected character's existing sheet
readers. Only its public rules appear in `homebrew_origin`; draft IDs, revision IDs,
workspace identity and authoring history remain private. The separate association
pins an immutable revision. Existing stats, equipment and unrelated import metadata
are retained, and repeat application cannot stack racial bonuses. Bonuses and
choices are shown for manual resolution. New character values are explicit input;
the D&D proficiency bonus follows the selected level.

All book/table navigation shows Creation Engine availability. Disabled live flags
keep entries visibly unavailable; adding links alone does not activate the editor.
See the [journey and acceptance record](race-to-sheet-2026-09-28.md) and
[portable D&D format](dnd5e-import-format.md).
