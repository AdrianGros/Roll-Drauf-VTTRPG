# Classes, races and spells: backend expansion

Status: backend implemented and selected verification passed. Implementation was
authorized by the user's 29 September instruction to build the backend for
end-to-end testing. Changes remain in the working tree; no production activation.

## Discover

The active checkout at `ece5f29` includes uncommitted race-to-sheet, portable D&D
import and navigation work. Preserve that work. The earlier release snapshot
omitted it. The existing race profile stores manual traits; class and spell
authoring and executable D&D character composition are absent. The shared draft
service already supplies typed answers, invalidation, immutable revisions,
ownership, PostgreSQL transactions and idempotency. Its three editing views can
serve additional profiles without a new draft protocol.

User scope: classes, races and spells must be usable before inviting testers.
Backend-first implementation is now authorized. This is an explicit extension of
the G1 implementation boundary; it does not declare G1 or later gates passed.

## Apply and implementation boundary

- Add independent, versioned executable class, race and spell profiles for the
  explicitly selected D&D 2014/2024 edition. Retain the existing manual race v1
  and its sheet adapter unchanged. No implicit conversion of old revisions.
- Reuse A1 authoring commands and their existing registry/provenance mechanism.
  Structured mechanical grants are required; prose remains descriptive.
- Class progression explicitly authors level-by-level HP contributions,
  features, choices and resources. Race features supply typed bonuses,
  proficiencies, resistances, resources and spell grants. All base character
  values are explicit, before these contributions; never double-count imported
  totals by silently treating them as base values.
- Add a versioned private sandbox adapter using the existing ContentStore and
  AuthoringService transaction boundary. It pins exact revisions, registry and
  runtime identity. It owns separate disposable character state, not campaign
  or legacy character rows. Its commands never enter the frozen core/A1 command
  registry or impersonate an RDL native scope.
- A persisted sandbox supports character creation/rebuild/progression, exact
  choices and source-labelled grants, authored spell casting, bounded damage,
  healing and temporary AC/speed modifiers, explicit round advancement, resource
  recovery and concentration ending. Spell grants must resolve to exact pinned
  revisions of the same edition. Unimplemented effect kinds fail validation.
- Casts validate learned spell, level, costs, targets, range and explicit timing/
  component adjudication. Server-generated dice, costs, HP/effects, immutable
  events and receipts commit together. Attack/save formulas and runtime policy
  are versioned. Concentration checks and reaction/component eligibility require
  explicit human adjudication; do not claim complete D&D rules automation.
- Add M80 tables for sandbox state and immutable command events. Serialize writes
  under the existing workspace advisory lock plus sandbox row lock, reject stale
  versions, check current ownership/account before returning retries, and record
  exact outcomes so retries cannot reroll or spend twice. No new dependency.
- Expose owner-only JSON APIs under the authoring workspace, with existing JWT,
  CSRF, View As refusal, payload bounds, feature flags and private response policy.
  Backend schema discovery describes operations and supported limits. New editor
  controls and production activation are follow-up integration, not claimed here.

## Risks addressed by design

- Medium, compatibility: separate registry/runtime identities preserve old pins.
- Medium, state integrity: scope versions, atomic events/receipts, server RNG and
  competing-request/fault tests cover retries, rollback and resource changes.
- Medium, gameplay breadth: the supported primitives are explicit. No universal
  5e automation, spatial map engine, multiclass or automatic reaction scheduling
  is promised by this backend. Unsupported authored mechanics cannot qualify as
  executable merely by adding prose.
- Medium, isolation: test scopes contain no live campaign actors. Applying these
  executable builds to production sheets needs a separate reviewed adapter.

## Acceptance / verification handoff

Author class, executable race and spell through authenticated A1 commands; save
and reload each; read through all three modes; pin revisions in a sandbox; build
a character; resolve choices and level progression; cast an authored spell;
verify resources, target HP, temporary effects, expiry and persisted history.
Prove edition/pin checks, ownership/CSRF, invalid/missing choices, resource bounds,
duplicate grant contributions, stale/competing commands, exact retry across a
fresh service instance, precommit rollback and immutable audit rows. Run retained
authoring/race/native regressions against an isolated PostgreSQL database.

Task evidence and the pre-existing working-tree snapshot are retained in
`/root/Documents/Codex/2026-09-29-okay-how-far-along-are-we/backend-evidence/`.
## Executed verification

- New mechanics and persisted/authenticated API checks: **34 passed**, 7 existing
  ORM/schema warnings, in **51.30 seconds**, exit 0, using the delivered
  `venv/bin/python tools/ce_homebrew_check.py`. The runner created a distinct
  PostgreSQL 16 container on a random loopback port and removed it afterward.
- Selected regression: **190 passed**, 66 existing ORM/schema/UTC warnings, in
  **190.93 seconds**, exit 0. This includes the new tests plus retained draft,
  authoring transport/browser, race compiler/sheet, manual compiler, native item
  and framework/approved-contract boundary coverage. This count overlaps the
  34-test runner; it is not 224 distinct cases and is not a full repository run.
- The first database development run was intentionally interrupted after one
  pass to eliminate repeated compilation of nested immutable registries. The
  corrected implementation caches the three new registrations/interviews; old
  registry identities are unchanged. The subsequent initial backend/mechanics
  run passed 31 cases before three final edge cases were added.
- Exact retries after a lost committed response survive a fresh service instance
  without reroll/spend. Real competing PostgreSQL transactions produce either one
  committed result plus a version conflict, or the same receipt for an identical
  request. Injected precommit failure leaves state and event unchanged.
- M80 matches the SQLAlchemy model columns, is repeatable, rejects event mutation
  and protects scope ownership/execution-lock bytes. No M80 migration was applied
  to production. The pre-existing test database container was preserved.

Regression command (against this task's disposable database):

```sh
venv/bin/python -m pytest -q \
  tests/creation_engine/test_ce_homebrew_runtime.py \
  tests/creation_engine/test_ce_homebrew_backend.py \
  tests/creation_engine/test_ce_authoring.py \
  tests/creation_engine/test_ce_authoring_transports.py \
  tests/creation_engine/test_ce_race_compiler.py \
  tests/creation_engine/test_ce_race_sheets.py \
  tests/creation_engine/test_ce_manual_compiler.py \
  tests/creation_engine/test_ce_native.py \
  tests/creation_engine/test_ce_boundaries.py
```

## Acceptance and retained limits

- [x] Class, executable race and spell draft/revision profiles with explicit
  edition, typed mechanics, quality validation and all three backend views.
- [x] Immutable revision pins; private persisted character builds, feature-choice
  resolution, source-labelled grants, class progression and independent resources.
- [x] Authored spell damage/healing/temporary AC/speed effects, recorded server
  rolls, costs, attack/save outcomes, resistance, expiry and concentration gating.
- [x] Authenticated author → save → build → cast → reload/history HTTP journey,
  current ownership/account/CSRF/flag enforcement, rollback and retry checks.
- [x] One-command isolated verification runner and machine-readable examples/API
  contract, preserving existing uncommitted race/navigation/import work.
- [x] Follow-up: [Advanced studio creation controls and private test bench](advanced-studio-2026-09-29.md).
- [ ] Production/campaign sheet adapter for executable builds and activation.
- [ ] Broader rules coverage listed in the API guide and human acceptance.

The backend uses separate private test scopes, not live VTT character records.
It implements the documented single-class, grant/resource and spell primitives;
it does not establish full D&D automation or readiness to invite human testers.
