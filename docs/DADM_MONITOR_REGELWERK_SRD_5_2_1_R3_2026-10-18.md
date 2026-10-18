# DAD-M Monitor: German SRD 5.2.1 Regelwerk — R3 Corpus Transcription

status: complete — transcription run closed; R7 (activation) is the next gate
date: 2026-10-18
profile: standard
phase: Monitor
milestone: R3 (executed as the continuous R3-R6 corpus run)
deploy-input: `docs/DADM_DEPLOY_REGELWERK_SRD_5_2_1_R3_2026-10-18.md`
program: `docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md`

## Observed results

- `tools/build_regelwerk.py --check` clean; `tools/validate_regelwerk.py`: 101 documents, pages
  5-412 represented, no missing or unexpected pages, no missing sections; status `preview`.
- Block inventory across the package: 1875 headings, 4108 paragraphs, 232 tables, 406 definition
  lists, 336 stat blocks (235 monsters and 95 animals in the final two sections), 25 rule-callouts,
  58 unordered and 5 ordered lists, 4 page-notes.
- Regelwerk package and route tests: 39 passed.
- Human source-fidelity sign-off: the reviewer answered "Lgtm" on every range, the last two being
  Monster pp.295-391 and Tiere pp.392-412 on 2026-10-17/18. `reviewedPageRanges` is `[{5,412}]`.
- Legal-cleanliness terms were listed to the reviewer for every range (see Deploy record) and
  accepted.

## Acceptance validation

- [x] Every required page 5-412 is represented and reviewed.
- [x] Every top-level section expected by the manifest is covered.
- [x] No document, digest, or inventory drift.
- [x] Source anomalies preserved and reported (page 385 "−2 2").
- [ ] Browser-level acceptance checks (keyboard, reduced motion, narrow screen, print) — open since
  R1; required before publication, especially for stat-block layout.
- [ ] Package `published` — intentionally not done; belongs to R7.

## Residual risks

- **Medium — open:** nothing from R0 through this run is committed; a large amount of reviewed work
  exists only in the working tree among unrelated changes.
- **Low — accepted:** milestone separation R3-R6 was collapsed by owner direction; the per-range
  reviewer sign-off served as the milestone gate.
- **Low — open:** the product owner / final acceptance owner is not yet named for R7.

## Recommended next action

Close this run and start R7 Discover (canonical activation, preview removal, representative VTT
references, rollback rehearsal). Commit the Regelwerk package, tests, tools, and DAD-M records
as one reviewable change set separate from the unrelated working-tree changes.
