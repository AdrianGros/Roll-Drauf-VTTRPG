# DAD-M Deploy: German SRD 5.2.1 Regelwerk R1

status: complete — pending role assignment (see Risks)
date: 2026-10-16
profile: standard
phase: Deploy
milestone: R1 — Regelwerk reader vertical slice
apply-input: `docs/DADM_APPLY_REGELWERK_SRD_5_2_1_R1_2026-10-15.md`
discover-input: `docs/DADM_DISCOVER_REGELWERK_SRD_5_2_1_R1_2026-10-15.md`
program: `docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md`

## Input summary

R1 Apply designed a public preview reader at `/regelwerk`, backed by one verbatim-transcribed
section (`W20-Prüfungen`, printed pages 6–8), a read-only Flask blueprint, deterministic generated
navigation/search/coverage artifacts, and a shared availability probe hydrating the Regelwerk entry
across every main navigation surface. This Deploy pass independently re-verified the already-written
implementation against that design, found and fixed two defects, and captured verification evidence.
It did not design or implement new scope.

## Verification summary

- Confirmed `vtt/rules.py` registers a self-contained, read-only blueprint (`rules_bp`) gated by
  `REGELWERK_PREVIEW` (default off); no route mutates state, and all API responses are
  `public`/304-conditional with short `max-age`.
- Confirmed the reader shell and JS renderer (`regelwerk-reader.js`, `regelwerk-navigation.js`)
  write every piece of source-controlled text through `textContent`/`createTextNode`; grep found
  zero `innerHTML` usage in either file, so content cannot be interpreted as markup.
- Confirmed the navigation probe (`regelwerk-navigation.js`) degrades safely: every
  `[data-regelwerk-nav]` anchor ships `hidden aria-disabled="true"` in the template source and is
  only unhidden after `/api/rulesets/main` reports `available: true`, so a disabled preview never
  exposes a live-looking link.
- Confirmed all nine navigation surfaces named in Discover (dashboard, campaigns, characters,
  character sheet, Creation Engine, advanced authoring, login, register, signup, play) carry the
  navigation script; the three Book Scene–ribbon surfaces (dashboard, campaigns, characters) get
  their entry from `book-scene.js::buildRibbon`/table-of-contents rather than static markup.
- Confirmed the pre-existing uncommitted session-calendar work in `vtt/static/js/book-scene.js`
  (`data-session-calendar` mount, `mountSessionCalendar` import) is untouched by and
  non-overlapping with the new Regelwerk ribbon/TOC entries and the
  `window.RegelwerkNavigation?.hydrate(root)` call added for dynamically re-rendered panels.
- Confirmed generated artifacts are reproducible: `tools/build_regelwerk.py --check` now reports
  current (see Defect 2).

## Defects found and fixed

### Defect 1 — test fixture leaked real corpus content

`tests/test_regelwerk_package.py::_minimal_complete_package` copies the live `srd-5.2.1-de` package
into a tmp dir and adds its own synthetic document on top, but never removed the real
`core.d20-tests.json` that R1 had since added to that live package. Nine of the fourteen R0 tests
built on that helper failed with `manifest/document inventory mismatch: ... unlisted=['core.d20-tests']`.

Fix: `_minimal_complete_package` now deletes every pre-existing `documents/*.json` file from the
copied fixture before writing its own (`tests/test_regelwerk_package.py:30`). No test assertions
changed.

### Defect 2 — generated artifacts were stale relative to source

File timestamps showed `manifest.json` and `documents/core.d20-tests.json` were last written at
11:16:40 on 2026-10-15, six minutes after `generated/navigation.json`, `generated/search-index.json`,
and `generated/coverage.json` were last built (11:10:25). `tools/build_regelwerk.py --check`
confirmed: `Regelwerk generated artifacts are stale: navigation.json, search-index.json,
coverage.json`. The checked-in generated files did not reflect the actual manifest/document
content a reader or the public API would serve.

Fix: regenerated all three files with `python tools/build_regelwerk.py`. `--check` now reports
"Regelwerk generated artifacts are current." Package content (manifest, documents) was not
changed by this fix.

## New verification coverage added

`tests/test_regelwerk_routes.py` (new, 24 tests) — Flask-test-client-level route/API contracts for
the acceptance criteria that do not require a browser:

- every reader page and ruleset API returns 404/`unavailable` when `REGELWERK_PREVIEW` is off;
- `/regelwerk`, `/regelwerk/lizenz`, and the one known deep link serve anonymously (no auth) when on;
- wrong source version, wrong locale, and unknown slugs all 404;
- `/api/rulesets/main`, the manifest, document, search, and license APIs return the expected
  shapes, and the manifest's own navigation URL round-trips to a reachable route;
- search resolves a known term, rejects a >100-character query, and returns an empty (not error)
  result for a too-short query;
- the license API always carries non-empty attribution text and the correct license id.

Not covered by this Deploy (needs a browser, out of scope for a Flask test client): keyboard
operability, reduced-motion behavior, narrow-viewport layout, and print styling. These remain open
per Program R1's acceptance criteria.

## Proofs

Sandbox: read-only repository mount, networking disabled, pinned application image (same as R0):

```text
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 \
  -v /home/admin/projects/roll-drauf-vtt:/workspace:ro -w /workspace \
  sha256:dafaade1c9141917159e9aff316026e23158bcfd34d4c42923150b9c5ae867cf \
  python -m pytest -q -p no:cacheprovider \
  tests/test_regelwerk_package.py tests/test_regelwerk_routes.py \
  tests/test_book_scene_layout_contract.py tests/test_core_book_runtime_routes.py \
  tests/test_session_calendar.py tests/creation_engine/test_ce_content.py
```

Observed: `109 passed` (40 package/content, 24 new route/API, 45 pre-existing book-scene/session-
calendar/creation-engine regression). Zero failures, zero skips.

```text
python tools/build_regelwerk.py --check
```

Observed: `Regelwerk generated artifacts are current.`

```text
python tools/validate_regelwerk.py
```

Observed: `status: preview`, `documentCount: 1`, `representedPageCount: 3`, `requiredPageCount: 408`,
`missingSections: 12` — the single-slice preview state Apply specified, confirmed unchanged by
either fix.

## Files changed

- `tests/test_regelwerk_package.py` (fixture fix, Defect 1)
- `tests/test_regelwerk_routes.py` (new, route/API contract tests)
- `vtt/rules_content/srd-5.2.1-de/generated/navigation.json` (regenerated, Defect 2)
- `vtt/rules_content/srd-5.2.1-de/generated/search-index.json` (regenerated, Defect 2)
- `vtt/rules_content/srd-5.2.1-de/generated/coverage.json` (regenerated, Defect 2)
- `docs/DADM_DEPLOY_REGELWERK_SRD_5_2_1_R1_2026-10-16.md` (this record)

No route, template, JS, database, dependency, or production container change was made by this
Deploy pass — `vtt/rules.py`, the templates, and the JS files were already present from Apply and
are verified, not modified, here.

## Acceptance checklist (testable-without-browser subset)

- [x] Anonymous reads work for the reader shell, license view, and the one known document.
- [x] Preview-off state 404s every reader page and ruleset API, and reports `available: false`.
- [x] A stable rule link (the navigation-reported URL) resolves.
- [x] Search resolves the fixture rule and rejects an oversized query.
- [x] Unsafe content cannot be interpreted as HTML (textContent-only rendering, verified by grep
  and by the absence of any markup field surviving the closed document schema).
- [x] Attribution is present and non-empty from the license API.
- [x] The navigation entry is hidden/disabled when preview is off everywhere it appears.
- [ ] Narrow-screen, keyboard, reduced-motion, and print checks — not run (no browser harness
  exercised in this Deploy pass).
- [ ] Human source-fidelity sign-off that the transcribed pages 6–8 match the pinned PDF
  (`manifest.coverage.reviewedPageRanges` is still empty; content is `contentStatus: verbatim`
  but not yet marked reviewed).

## Risks and assumptions

- **Medium — open, blocks R1 closure:** the Program's Roles section requires a named **VTT
  integration lead assigned before R1 Deploy**. No name has been recorded in any governance
  document this Deploy pass could find. This Deploy pass proceeded with independent verification
  only (no new design decisions) because the Apply record states Deploy was already authorized by
  the approved program; it does not itself satisfy the role requirement.
- **Medium — open:** no independent source-fidelity reviewer has signed off that the verbatim
  `W20-Prüfungen` transcription matches the pinned PDF pages 6–8. `reviewedPageRanges` stays empty
  until that happens, which is correct behavior, not a defect — but it means R1's content is not
  yet certified, only mechanically validated.
- **Low — open:** browser-level acceptance criteria (keyboard, reduced-motion, narrow-screen,
  print) have no automated coverage yet.
- **Low — accepted:** this fix touched only test fixtures and regenerated derived artifacts;
  no change to the pinned source, attribution, or manifest coverage contract.

## Next step

Do not write R1 Monitor closure yet. Two human inputs are needed first: (1) name the VTT
integration lead the Program requires before R1 Deploy closes, and (2) name an independent
source-fidelity reviewer to compare the transcribed `W20-Prüfungen` pages against the pinned PDF
and record the result in `manifest.coverage.reviewedPageRanges`. Once named, Monitor can
independently recheck this evidence and recommend closing R1 / starting R2 Discover.
