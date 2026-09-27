# Task-readiness implementation — 27 September 2026

**Status:** implemented and verified within the selected scope; uncommitted.
**Phase:** G1 Deploy. **Input:** user's instruction to resolve the remaining task gaps and
technical checks; [bounded design and contracts](authoring-task-readiness-v0.1.md).
**Retention:** repository report; logs, screenshots and exact source evidence in task-workspace
`authoring-task-readiness-2026-09-27/`.

## Implementation and authority

The editor now offers explicit creation of a magic item, manual conditional effect, manual
choice, or standalone lore. The same Guided, Structured and Advanced modes save typed
answers through existing A1 commands. Conditional cards collect affected value, condition,
change and end/removal. Choice cards collect a prompt, two to six distinctly named alternatives,
their consequences and an explicit selection count. Lore has only title and prose.

Required creative answers start empty. Changing a condition invalidates its dependent change
and removal instructions; changing choice prompt/count invalidates dependent alternatives and
selection count. History retains the old answers. A changed alternative label invalidates its
consequence. Sheet-ready cards require complete, consistent answers; lore requires actual prose.
Manual profiles reject Runtime-ready/Automation-complete even with the native host enabled,
and cannot be admitted to an executable sandbox by supplying a revision directly. The editor
labels these limits in de/en/fr and hides inapplicable flame presets; the server also rejects
cross-profile preset application atomically.

New profiles use separate immutable registry artifacts. The original flame registry remains
byte-identical (`sha256:8030551e4be578f08eba12fb3f03855530b957bb6a8241d3f33c2e5223d51e2a`).
The store resolves each draft's exact type and checks its pinned registry; no existing draft,
revision or runtime lock is migrated. The approved specification 1.1.4, wire 1.1.3 and A1
command schemas remain unchanged. There is no database migration, new dependency, G2
ChoiceSlot/grant execution, world graph, publication or production activation.

## Files and review boundary

- `compiler/manual.py`: bounded question metadata, content schemas and honest quality gates.
- `compiler/catalog.py`: per-type registration/dispatch while preserving the flame artifact.
- `store/authoring.py`: per-type pinned registry for create/read/commit, quality dispatch and
  preset compatibility checks within existing owner/version/receipt transactions.
- Editor template/JavaScript: explicit creation selector and localized profile notices;
  existing input/conflict/access-loss/focus behavior is reused.
- New compiler/persistence/browser tests, new lifecycle tests, and a small browser fixture
  parameter for the optional WebKit case.
- Task cards, reset protocol, candidate-source identity, unfilled session manifest and updated
  backlog/status references. Earlier WP5–WP8 and UI slices remain intact and uncommitted.

The profile extension changes neither runtime mechanics nor command authorization. Production
flags remain default-off. Roll back creation availability through the UI while retaining the
new registered readers for any new saved drafts. Removing those registrations would strand
new content and is not a data-preserving rollback. Before snapshots retain the prior UI/store.

## Verification

Initial focused run: **73 passed, 10 warnings in 77.84s**. Five lifecycle cases then passed
in **37.05s**, with seven existing warnings. They use real server transactions and Chromium:
hard tab closure with unsaved input; hard closure after a committed-but-lost save response;
held-copy unequip/equip, decline/accept and resource recovery; optional worker timeout;
and clock-anomaly suspension followed by explicit manual completion without resource changes.

The follow-up runtime admission check passed for all three new profile types. WebKit was
attempted but could not launch: this Arch host lacks Playwright's required libicu74, libxml2
and libflite1 dependencies. That is recorded as unavailable, not a product test pass. The
dedicated test can run with `CE_TEST_WEBKIT=1` on a compatible host; the standard run reports
it skipped. Firefox is not installed. No system-package changes were made for this check.

**Combined regression:** **198 passed, one failed, one skipped, 128 warnings in 372.88s**.
The single failure was the existing keyboard test expecting Tab to skip the new content-type
selector. Its sequence now traverses and operates that selector without creating a draft.
The focused editor-state rerun passed **11 tests, seven warnings in 45.13s (exit 0)**.
Together these establish **199 distinct passing selected tests, including 33 new cases**;
the optional WebKit case remains unverified. The application sources did not change during
or after the combined regression; only that test changed for the follow-up. This is not a
full repository run. Existing ORM/table-cycle/UTC warnings remain.

`regression-command.json` contains the exact combined pytest arguments; `verified-source.json`
and `final-source.json` distinguish the original and corrected test. `environment.json`
records Python 3.14.7, Playwright 1.62.0 and Chromium 151.0.7922.34. Tests use only
the disposable PostgreSQL 16 database `ce-task-readiness-20260927` on localhost:55441.
It was stopped and removed after verification; all preexisting containers were preserved.
JavaScript syntax, whitespace, 110 local documentation links, 299 candidate source/contract
hashes and the active-authority reconciliation checks pass; the human-result CSV is empty.

## Acceptance and limits

- [x] Four explicit authoring intents exist; the three new ones have persisted, private,
  immutable output and no inferred creative answers.
- [x] Invalid/incomplete quality claims, count/label conflicts, forbidden presets, provenance,
  dependency invalidation, retry, revert and original flame compatibility have focused proof.
- [x] Tab loss and the tested held-copy/timeout/suspension journeys have real browser evidence.
- [x] Combined regression and focused keyboard follow-up recorded with exact source identities.
- [x] All three new profiles complete browser creation/edit/revision journeys in de/en/fr,
  cycling through Guided/Structured/Advanced; nine 390×844 profile/locale captures and
  no-overflow checks recorded. French lore and English conditional/choice captures inspected.
  The prior 18 width/locale/reduced-motion cells also reran. These are technical checks only.
- [ ] Acceptance owner confirms whether the manual conditional/choice task depth satisfies T45.
- [ ] Real back/forward-cache restoration, full uninterrupted keyboard/screen-reader coverage,
  actual 200% zoom, Firefox/WebKit, physical devices and the remaining result/failure UI matrix.
- [ ] Confirm Tuesday's time/roster/devices, provision the isolated session environment/accounts,
  verify its installed build, conduct ≥8-person/four-task sessions and complete WP9/G1 evidence.

The [task cards](study-task-cards-2026-09-29.md) and [session manifest](study-run-manifest-2026-09-29.json)
make those preparation fields explicit. The [candidate identity](study-candidate-build-2026-09-27.json)
identifies source bytes; it does not claim deployment or selection of Tuesday's installed build.
No participant outcomes are recorded. Human testing remains deferred until **29 September 2026**.
