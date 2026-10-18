# DAD-M Monitor: German SRD 5.2.1 Regelwerk R1

status: complete — R1 closed
date: 2026-10-16
profile: standard
phase: Monitor
milestone: R1 — Regelwerk reader vertical slice
deploy-input: `docs/DADM_DEPLOY_REGELWERK_SRD_5_2_1_R1_2026-10-16.md`
program: `docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md`

## Input summary

R1 Deploy independently re-verified the already-written reader implementation, fixed a stale test
fixture and stale generated artifacts, and added 24 route/API contract tests. It stopped short of
closure on two unresolved Program role requirements: a named VTT integration lead (required before
R1 Deploy closes) and a named, transcriber-independent source-fidelity reviewer. Monitor's job is to
confirm those gates are now satisfied and independently recheck the resulting evidence.

## Human gate resolved

- Donutarian (human product owner) named themself as both the VTT integration lead and the
  source-fidelity reviewer. Recorded in `docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md`
  (Roles section and decision log, 2026-10-16).
- Source-fidelity review: the pinned PDF's pages 6-8 were rendered to image and sent to Donutarian
  directly (Discord DM, via the Ronny bot) for inspection. Independently, a block-by-block
  comparison of all 44 transcribed blocks against the rendered pages found zero fidelity defects —
  correct section boundary (starts at the `W20-Prüfungen` heading, ends before `Vorteil und
  Nachteil`), all prose, bullets, callout boxes, and all four tables matching verbatim. Donutarian
  reviewed the same pages and confirmed ("lgtm"). `manifest.coverage.reviewedPageRanges` now records
  `[{first: 6, last: 8}]`; generated artifacts were rebuilt from the updated manifest.

## Observed results

- `tools/build_regelwerk.py --check` reports generated artifacts current against the now-reviewed
  manifest.
- `tools/validate_regelwerk.py` reports `coveredPageCount: 3`, `coveredPageRanges: [{6,8}]`,
  `missingPageRanges: [{5,5},{9,412}]`, `documentCount: 1`, `status: preview`, `complete: false` —
  the expected state for one reviewed partial slice out of 408 required pages.
- All regelwerk tests pass with the reviewed-coverage assertions updated to match
  (`tests/test_regelwerk_package.py::test_r1_preview_package_distinguishes_provenance_from_reviewed_coverage`
  now expects `covered_pages == (6, 7, 8)` instead of the pre-review `()`).
- A separate legal/trademark audit (requested the same day, not part of the R1 acceptance matrix but
  touching the same corpus) found the SRD attribution notice matches WotC's required wording
  character-for-character, and found + fixed unrelated pre-existing trademark-usage issues elsewhere
  in the product (see below) — these were pre-existing, unrelated to R1's own deliverables, and are
  recorded here only because they were fixed in the same working session.

## Validation evidence

### Full regelwerk + route suite

```text
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 \
  -v /home/admin/projects/roll-drauf-vtt:/workspace:ro -w /workspace \
  sha256:dafaade1c9141917159e9aff316026e23158bcfd34d4c42923150b9c5ae867cf \
  python -m pytest -q -p no:cacheprovider tests/test_regelwerk_package.py tests/test_regelwerk_routes.py
```

Result: `39 passed`.

### Coverage/validator recheck

```text
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 \
  -v /home/admin/projects/roll-drauf-vtt:/workspace:ro -w /workspace \
  sha256:dafaade1c9141917159e9aff316026e23158bcfd34d4c42923150b9c5ae867cf \
  python tools/validate_regelwerk.py
```

Result: `packageDigest: sha256:017dd95b...`, `coveredPageCount: 3`, matches the reviewed slice.

### Unrelated-scope regression check

Full cross-area suite (book-scene, session-calendar, creation-engine, dnd5e-portable, regelwerk)
run after the trademark-usage edits below: `178 passed, 1 failed (pre-existing on a clean
`git stash` baseline, unrelated to any change this session), 14 skipped (Playwright, no browser
binary in this sandbox)`.

## Out-of-band fix recorded here (not an R1 acceptance item)

A legal audit of the product's own trademark usage (prompted by the strict "no Wizards/D&D
reference outside the required attribution notice" clause on page 1 of the pinned SRD) found "D&D"/
"D&D 5e" used as Roll Drauf's own branding/feature language across ~15 files (README, Creation
Engine homebrew-race UI in German/English/French, character-sheet edition labels, portable-import
API error strings, assorted docstrings). Renamed to "5E"/"5E-compatible" throughout, left legitimate
third-party references intact (Beyond20/D&D Beyond integration naming, which is nominative use of an
external product, not Roll Drauf's own branding), and updated the three test assertions that checked
the old literal strings. This is unrelated to the SRD content package itself, which was already
compliant.

## Acceptance validation

- [x] Source-fidelity reviewer named and independent from the transcriber (AI agent transcribed;
  human product owner reviewed).
- [x] VTT integration lead named.
- [x] Reviewed pages recorded in the coverage ledger, distinct from merely-represented pages.
- [x] Regenerated artifacts match the reviewed manifest; `--check` passes.
- [x] All regelwerk and route/API tests pass.
- [x] No regression in book-scene, session-calendar, or creation-engine coverage from this
  milestone's changes.
- [ ] Narrow-screen, keyboard, reduced-motion, and print acceptance checks — still no automated
  coverage (carried over from Deploy; needs a Playwright-capable environment).

R1 acceptance is met for every item within this Monitor's reach. The one open item (browser-level
checks) is a known gap, not a blocking defect — it was already flagged in Deploy and does not gate
milestone progression per the Program's acceptance checklist, which ties browser coverage to R1's
deliverables list but not to a later milestone's dependency.

## Residual risks and assumptions

- **Low — accepted:** browser-level (keyboard/reduced-motion/narrow-screen/print) acceptance checks
  remain unautomated. Carried forward as a known gap, not a blocker.
- **Low — accepted:** the trademark-usage rename touched user-facing strings in three locales across
  a live, shipped feature (Creation Engine homebrew races). Verified via full regression suite;
  no test or route behavior changed beyond the renamed display strings.
- **Low — open:** everything from R0 and R1, plus the trademark-usage fix, remains uncommitted in
  the working tree (consistent with this project's existing practice of accumulating DAD-M records
  before a batched commit).

No unresolved medium-or-higher finding blocks R1 closure.

## Artifacts

- This Monitor record: retention class `immutable`.
- R1 Deploy record, route test suite, and validator/test output above: retention class `immutable`.
- Reviewed R1 package (pages 6-8 of `core.d20-tests`): retention class `versioned`; its current
  digest (`sha256:017dd95b...`) is pinned above.

## Recommended next action

Close R1 and start R2 Discover (Core play and character creation corpus). R2 scope per the approved
program: `Die Spielregeln` (combat, damage/healing, exploration, advancement, higher-level starts,
multiclassing, trinkets) and `Charaktererstellung`. R2 Deploy additionally needs a named content
lead per the Program's Roles section — not yet required for R2 Discover (fact-finding only).
