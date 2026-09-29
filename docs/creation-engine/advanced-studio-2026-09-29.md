# Advanced creation studio

Status: implemented in the working tree, with automated Monitor evidence below.
Authorized by the user's request to layer Advanced creation on the executable
backend before expanding Guided. Production deployment is not part of this step.

## Discovery and boundary

The active tree includes prior race/navigation work and the verified class,
executable race and spell backend. Preserve all of it. The existing Advanced
editor edits individual typed answers and has no full-document transaction or
interface to the new private homebrew sandbox. The backend is usable through JSON
APIs, but that alone is insufficient for a power-user workflow.

## Design and Deploy handoff

- Add a dedicated Advanced studio at `/api/ce/authoring/advanced`, reachable from
  the current editor. Use the existing book styles and local assets, with no new
  dependency. Keep the existing Guided/Structured editor intact.
- Offer explicit content-type selection, named drafts, whole-document JSON,
  formatting, local JSON import/download, searchable field/schema help,
  path-specific validation, local-versus-saved changes, revision quality and
  history. Missing fields stay explicit; no generated creative defaults.
- Provide a narrow `advanced-document:1` adapter for validate/save on existing
  drafts. Reuse registry validation, interview dependencies, version guards,
  workspace ownership and the existing snapshot/answer/receipt tables. One
  document save advances one version in one PostgreSQL transaction. Preserve
  invalidated answers and old snapshots. Do not send a sequence of partially
  committed answer requests or amend the frozen A1 vocabulary.
- Revision commits and reverts continue through A1. The inspector obtains
  authoritative schema, readiness and errors from the server. Unknown properties,
  duplicate JSON keys and imprecise numbers are rejected without silent coercion.
- Add a private test bench: select exact saved revisions/edition, create or open
  scopes, build/rebuild characters, select known spells/targets, explicitly enter
  distances and adjudications, advance rounds, recover resources, resolve
  concentration, and inspect actual state/roll/history. Uses the existing
  homebrew API; no additional mechanics or live campaign integration.
- Protect dirty input and exact pending requests; preserve local content on
  conflicts and require explicit review against refreshed server content. Account
  loss clears protected content, rejects late responses and pauses on uncertain
  connectivity. Never replay a write during rechecks or refresh.
- Support keyboard access, narrow layouts and de/en/fr interface text. Retain
  screenshots and actual Chromium browser evidence; do not claim assistive-tech
  or other-browser coverage that was not run.

## Risk treatment and acceptance

Medium atomicity: schema/dependency validation occurs before the single write;
test competing edits, rollback and lost-response retry. Medium privacy: reuse
JWT/CSRF/current account checks and test denial/late responses. Medium data loss:
test navigation locks, conflict comparison and exact retry across server success
with a lost response. Medium scope: backend power-user flows only; Guided
redesign and production activation are later work.

Prove actual browser creation/import/edit/validation/save/reopen/revision and
class + race + spell → character → cast → persisted result. Verify mobile layout,
keyboard save/validate, unknown fields, malicious display text, ownership,
conflicts and retained existing editor/backend behavior. The task workspace
`advanced-evidence/` retains the starting hashes and verification artifacts.

## Using the studio

On an isolated host with M73–M80 applied and `CE_AUTHORING=true`, open
`/api/ce/authoring`, then **Advanced studio** (or visit
`/api/ce/authoring/advanced` directly). No additional migration or library is
introduced by this UI. The studio supports class, executable race and spell
profiles, plus the existing item/manual/lore drafts.

1. Choose a definition type and create a draft. Write or import the complete
   JSON document. Field reference entries show the server's field schemas;
   validation links jump to the offending value. Import remains unsaved until
   explicitly saved. Download exports the current editor contents.
2. Validate, inspect changes and save the draft. Ctrl/Cmd+Enter validates;
   Ctrl/Cmd+S saves. A save produces one version, including dependent changes.
   Partial valid documents can be saved; missing mechanical answers prevent an
   Executable revision. History can restore a previous snapshot as a new version.
3. Save an **Executable** revision of a class, race and every granted spell.
   In **Test bench**, choose their edition and exact revisions and create a
   private test. Existing tests retain their original revision pins.
4. Select class/race revisions and **Prepare action**. Fill the explicit build
   values and choices in the action JSON. Base values exclude class/race bonuses.
   Run it, select caster/target/known spell, prepare the cast, and explicitly set
   range and timing/component attestations. Inspect characters, resources,
   outcomes, complete state and recorded dice/actions.
5. The other actions expose rebuild/level changes, recovery, rounds and
   concentration decisions. A pending concentration decision must be resolved
   before continuing. All changes persist in the private test scope.

This is a JSON document workbench for power users, with schema and reference
assistance. Guided composition is the next UX task. The underlying private
runtime remains bounded to the mechanics described in
[the backend API](homebrew-backend-api.md); it does not apply these characters to
live campaigns or implement complete 5e automation.

## Whole-document HTTP adapter

Authenticated, private/no-store routes use the same JWT cookie, CSRF and ViewAs
restrictions as existing authoring. The document path prefix is
`/api/ce/authoring/workspaces/{workspace}/drafts/{draft}`.

- `GET /api/ce/authoring/advanced/workspace`: existing workspace metadata with
  draft names and definition IDs.
- `GET {prefix}/document?locale=en`: existing Advanced presentation plus
  `contentSchema` and `documentContract`.
- `POST {prefix}/document/validate`: read-only candidate validation.
- `POST {prefix}/document`: atomic candidate save.

Both POST bodies contain `contractVersion: "advanced-document:1"`,
`expectedDraftVersion`, `promptLocale` (`de`, `en` or `fr`) and `content`.
Save additionally requires `idempotencyKey`. Bodies are bounded to 256 KiB.
Validation returns `valid`, `draftVersion`, `qualityGates` and proposed `changes`.
Save returns `operation`, `draftId`, new `draftVersion`, `qualityGates` and `changes`.
Invalid fields return HTTP 422 `DOCUMENT_INVALID` with bounded
`issues: [{path, code, message}]`; paths use JSON Pointer. A changed draft returns
409 `DRAFT_VERSION_CONFLICT`. Retries with an identical key/body return the
original saved result after current ownership checks. Reusing a key for different
content fails. The existing core/A1 contract and command registry are unchanged.

The browser preserves uncertain requests in memory for exact retry, locks
navigation while input is dirty, and compares concurrent server edits before
explicitly rebasing retained local content. Closing the tab loses unsaved input
and pending client requests after the browser's unload warning; there is no
durable local autosave. Confirmed access loss clears protected content; network
uncertainty pauses editing and retains it. The visible-page access interval is
15 seconds with checks on return, rather than push revocation.

## Reproduce verification

```sh
CE_TEST_ARTIFACT_DIR=/tmp/ce-advanced-evidence venv/bin/python tools/ce_homebrew_check.py --advanced
```

Requires Docker, the existing test dependencies and installed Playwright Chromium.
The runner owns and removes its own PostgreSQL container on a random loopback
port. It never uses the configured application database. Browser examples are
explicit test fixtures, not product defaults. Screenshots cover 1280px desktop
and 390px mobile layouts. This establishes Chromium automation evidence only;
human acceptance, assistive technology and other browsers are not claimed.

## Automated Monitor evidence — 29 September 2026

- The final isolated runner passed **50 tests**: 34 retained homebrew backend
  checks, 10 atomic-document/API cases and 6 real Chromium studio journeys.
- A final compatibility addition passed **5 more cases**, round-tripping item,
  manual race, conditional, choice and lore documents through the same atomic
  adapter. The runner now includes these cases as well (55 focused checks total).
- The selected existing authoring, transport, editor/access, design, race browser,
  manual-authoring, boundary and browser-icon regression passed **137 tests with
  1 skipped** (the opt-in WebKit case; `CE_TEST_WEBKIT` was not enabled).
  Across the focused and regression runs, **192 tests passed**.
- Browser execution covers class/race/three-spell authoring and revision commits,
  pinned test creation, two character builds, damage/costs and persisted reload,
  level changes, recovery, duration expiry and concentration decisions. It also
  covers JSON/import/download/field jumps, dirty navigation, de/en/fr interface
  selection, draft and sandbox conflicts, exact retries after lost responses,
  hostile display text and account/network access handling.
- Desktop and mobile screenshots were inspected. The checks caught and corrected
  canonical-byte draft-name decoding and narrow-screen tab sizing. No production
  configuration or database was modified.
- `node --check`, Python compilation, tracked diff whitespace and new-file
  whitespace checks passed. Logs, screenshots and source hashes are retained in
  the task workspace's `advanced-evidence/` directory. Existing SQLAlchemy model
  relationship warnings remain visible in the logs.
- All containers created for this task's verification were removed after the
  checks. Pre-existing containers and databases were preserved.
