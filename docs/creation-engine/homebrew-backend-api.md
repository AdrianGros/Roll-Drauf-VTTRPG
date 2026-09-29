# Private class, race and spell backend

The `homebrew-sandbox:1` adapter provides persisted end-to-end tests of authored
mechanics. Its characters are isolated copies. They are not campaign character
rows, and its sandbox IDs are not RDL native scope IDs.

## Run the end-to-end checks

From the repository, with Docker and the existing virtual environment available:

```sh
venv/bin/python tools/ce_homebrew_check.py
# Include the Advanced studio's document API and actual Chromium journeys:
venv/bin/python tools/ce_homebrew_check.py --advanced
```

This creates and removes its own PostgreSQL 16 container on a random loopback
port. It applies test migrations, creates temporary accounts, authors real
revisions and exercises authenticated Flask HTTP routes and database transactions.
It does not use the application's configured database. The fixtures explicitly
choose example content; they are never authoring defaults.

The full API journey is in
`tests/creation_engine/test_ce_homebrew_backend.py::test_http_author_create_reload_build_cast_progress_history_and_access`.
Machine-readable sample content and request schemas are in
[`examples/homebrew-backend.json`](examples/homebrew-backend.json).

## Installation for an existing isolated test host

Use the existing Creation Engine host integration, migrations M73 through M80,
and `CE_AUTHORING=true`. The private adapter does not require `CE_RUNTIME` or
campaign cutover. M80 must be applied explicitly: `create_all` does not install
the immutable-event/execution-lock triggers. Use a disposable database for the
test runner above; its fixtures reset the `ce_test` database.

The [Advanced studio](advanced-studio-2026-09-29.md) at
`/api/ce/authoring/advanced` exposes these profiles and the private sandbox.
It is linked from the existing authoring page. Existing manual race authoring
and race-to-sheet remain separate. Production activation and human acceptance
are still open.

## Authoring

`GET /api/ce/authoring/workspace` returns the caller's workspace and registered
schema types. New types, all version 1:

- `dnd5e.authored-class`
- `dnd5e.runtime-race` (separate from the existing manual `dnd5e.authored-race`)
- `dnd5e.authored-spell`

Use existing core 1.1.3/A1 commands at `POST /api/ce/commands`: `CreateDraft`,
`RecordDraftDecision`, `CommitDraftRevision`. Read the draft with
`GET /api/ce/authoring/workspaces/{workspace}/drafts/{draft}?mode=guided&locale=en`.
`structured` and `advanced` return the same content and typed question schemas.
Answer envelopes for these profiles have `kind: structured`, the question's
`answerType` as `schemaType`, and the authored `value`.

Resolve each command's created references through the existing workspace/draft
command-result endpoint. Commit with `declaredQuality: runtime_ready`; complete
mechanical answers and semantic checks are required. `automation_complete` is
rejected because spatial/timing/component and concentration adjudication remain
explicit. Edition changes invalidate dependent mechanics.

Class levels must be consecutive from 1, up to 20. Each authors `hpGain` and its
features explicitly; hit dice do not silently choose HP gains. Feature grants
contain typed modifiers, proficiency keys, resistance types, resources and spell
keys. Choices require an explicit count of distinct options. Resource IDs may
have multiple contribution sources only with consistent recovery semantics.
`save.con`, for example, grants proficiency in Constitution saves. Other keys
remain inspectable proficiencies; arbitrary skill/action execution is not implied.

## Sandbox endpoints

All paths below begin with `/api/ce/authoring/workspaces/{workspace}/homebrew`.
Existing JWT authentication, CSRF on POST, active-account/ownership checks and
View As refusal apply. Responses are private and not cached.

| Method / path | Result |
| --- | --- |
| `GET /` (omit trailing slash) | Runtime identity, complete command schemas, owned executable revisions and sandbox IDs. |
| `POST /commands` | Execute one versioned command; return durable outcome, draws, state digest and new version. |
| `GET /sandboxes/{id}` | Pinned execution lock and current characters, effective stats, resources, effects and pending concentration decision. |
| `GET /sandboxes/{id}/history?after=0` | At most 100 ordered immutable command/outcome records. Continue after the last returned version. |

Example envelope after creating a sandbox:

```json
{
  "contractVersion": "homebrew-sandbox:1",
  "idempotencyKey": "mytest:cast-1",
  "operation": "CastSpell",
  "sandboxId": "COPY_THE_RETURNED_ID",
  "expectedVersion": 3,
  "payload": {
    "casterId": "COPY_THE_CASTER_ID",
    "targetId": "COPY_THE_TARGET_ID",
    "spellKey": "ember",
    "castLevel": 1,
    "distanceFeet": 20,
    "adjudication": {"timingSatisfied": true, "componentsSatisfied": true}
  }
}
```

Copy actual IDs and the current version. For a lost response, retry the exact
envelope/key; a retry returns the original result even if the scope has since
advanced. Changing that request with the same key is rejected. A new command
against a stale version is rejected before spending or rolling.

## Operations and behavior

1. **CreateSandbox:** explicit edition plus exact class, executable-race and spell
   revision references. All must be owned executable revisions of that edition.
   Spell keys must be unique. The runtime and registry digests and exact content
   are pinned. Editing a draft later cannot change the scope.
2. **BuildCharacter:** class/race revision IDs from that lock; name, level,
   `baseScores`, `baseAc`, `baseHp` and `choices`. Bases are values **before** class
   and race contributions. Do not pass imported totals as bases. Choice keys use
   `race/{featureId}/{choiceId}` or `class/{featureId}/{choiceId}`. Missing, extra,
   duplicate and unknown selections fail. The result includes source-labelled
   grants, derived stats, learned spells and independent resources.
3. **RebuildCharacter:** character ID and a complete reviewed build. Recomputes
   from bases; retains current HP/resources capped by new maxima. New resource
   pools start empty on rebuild and require explicit recovery. Independent grant
   sources survive removing another source. It never rewinds past spell damage.
4. **CastSpell:** validates the known spell, authored level/cost/range/target and
   attestations. Rolls are server-generated and recorded. Supported effects are
   damage, healing, and temporary additive AC/speed modifiers. Damage supports
   automatic, spell-attack or saving-throw resolution, authored upcast scaling,
   critical dice and resistance. Healing caps at maximum HP. Misses spend costs.
5. **AdvanceRounds:** explicit positive round count; expires duration-bound effects.
   No wall-clock, initiative, calendar or map movement is inferred.
6. **RecoverResources:** declared `short_rest`, `long_rest` or `manual` event plus
   a reason. Restores matching authored resources; a long rest also restores
   short-rest pools. It does not infer HP recovery.
7. **EndConcentration:** character and reason; removes that caster's concentration
   effects. A new concentration spell also ends prior concentration. Incapacitating
   damage ends it automatically.
8. **ResolveConcentration:** after non-incapacitating damage to a concentrating
   caster, the result records the required DC and the sandbox pauses mutations.
   Explicitly adjudicate `maintained` with the matching character and a reason.
   Failure removes concentration effects; success retains them. Both preserve
   already committed damage and costs. Retries cannot reopen the decision.

Repeated casts from the same caster replace that spell's prior modifier. Multiple
casters of the same pinned spell do not multiply the same modifier; remaining
applications can survive another caster ending concentration. Different spell
keys can contribute independently.

## Deliberate boundaries

This profile supports a single class track per character, explicitly selected
race, HP, authored resources and the primitives above. It is not complete D&D
automation: multiclass/subclass rules, area targets, conditions, summons,
automatic action/reaction scheduling, component inventory, immunity/vulnerability,
death saves and live VTT character application are not implemented here. Distances
and timing/component eligibility are explicit author adjudications in a private
test; they are not spatial proofs or campaign authority.

Scope writes serialize under a workspace advisory lock and sandbox row lock.
State, RNG outcomes and the immutable receipt/event commit together. The API
bounds request size (256 KiB), revision count (64), actors (32), draws per action
(202), and persisted lock/state (2 MiB each). It executes no user-supplied code.
Human-study readiness still requires the new editor integration and agreed
content coverage; passing backend tests alone is not an invitation to testers.
