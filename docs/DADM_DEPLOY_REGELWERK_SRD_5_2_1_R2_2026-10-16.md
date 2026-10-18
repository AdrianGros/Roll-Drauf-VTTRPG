# DAD-M Deploy: German SRD 5.2.1 Regelwerk R2

status: complete
date: 2026-10-16
profile: standard
phase: Deploy
milestone: R2 — Core play and character creation corpus
apply-input: `docs/DADM_APPLY_REGELWERK_SRD_5_2_1_R2_2026-10-16.md`
program: `docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md`

## Input summary

R2 Apply defined a ten-document transcription plan covering the remainder of `Die Spielregeln`
(pages 5, 9-21; pages 6-8 were already published in R1) and all of `Charaktererstellung`
(pages 22-32), sequenced smallest/lowest-risk first. This Deploy pass executed that plan: thirteen
new documents were transcribed, schema-validated, and digest-pinned one at a time, with the
generator and full test suite rerun after every addition.

## Implementation summary

- Transcribed and validated, in sequence: `core.game-loop-and-abilities`, `core.advantage-and-
  inspiration`, `core.proficiency`, `core.actions`, `core.social-interaction`, `core.exploration`,
  `core.combat-turns`, `core.combat-attacks`, `core.damage-and-healing`,
  `character-creation.overview-and-steps`, `character-creation.abilities-alignment-and-details`,
  `character-creation.advancement-and-multiclassing`, `character-creation.trinkets`.
- Apply's provisional document plan diverged from the final split as transcription proceeded against
  the actual pages (e.g. "Übung im Umgang mit Ausrüstung" and "Aktionen" turned out to be a
  distinct document not named in Apply's list; `Kampf` needed two documents, not one). This is the
  expected refinement Apply itself flagged, not a defect.
- Caught and fixed one schema issue during transcription: the "Seltene Sprachen" table has nine
  entries in what prints as a two-column layout, which would have produced an empty table cell
  (schema-invalid). Flattened to a single-column table; no content was lost.
- Package `status` stays `preview`. No class, species, feat, spell, or monster content was
  transcribed even where the character-creation overview names them (e.g. the `Klassenüberblick`
  table lists class names/summary stats only) — that remains R3+ scope per the Program.
- `tools/build_regelwerk.py` was rerun after every single document addition and `--check` confirmed
  current before moving to the next, per the standing practice established after R1's stale-artifact
  defect. No staleness occurred this pass.

## Human review

Donutarian (content lead, VTT integration lead, and source-fidelity reviewer) was sent rendered
images of all pages pending review — page 5 and pages 9-32, 25 pages in three Discord DM batches —
and confirmed fidelity ("lgtm") for the full set. `manifest.coverage.reviewedPageRanges` now records
`[{first: 5, last: 32}]`, extending from R1's `{6, 8}`.

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

Result: `documentCount: 14`, `coveredPageRanges: [{5,32}]`, `coveredSections: [core,
character-creation]`, `missingSections: 10` (classes, character-origins, feats, equipment, spells,
rules-glossary, gameplay-toolbox, magic-items, monsters, animals — all correctly still missing, R3+
scope), `complete: false` (correct — 10 of 12 sections remain).

### Cross-area regression

```text
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 \
  -v /home/admin/projects/roll-drauf-vtt:/workspace:ro -w /workspace \
  sha256:dafaade1c9141917159e9aff316026e23158bcfd34d4c42923150b9c5ae867cf \
  python -m pytest -q -p no:cacheprovider tests/test_regelwerk_package.py tests/test_regelwerk_routes.py \
  tests/test_book_scene_layout_contract.py tests/test_core_book_runtime_routes.py \
  tests/test_session_calendar.py tests/creation_engine/test_ce_content.py
```

Result: `109 passed`. Zero regressions from this milestone's changes.

## Files changed

- 13 new documents under `vtt/rules_content/srd-5.2.1-de/documents/`.
- `vtt/rules_content/srd-5.2.1-de/manifest.json` — 13 new `documents` entries; `reviewedPageRanges`
  extended to `[{5, 32}]`.
- `vtt/rules_content/srd-5.2.1-de/generated/{navigation,search-index,coverage}.json` — regenerated.
- `tests/test_regelwerk_package.py` — the live-package snapshot test's expectations updated to match
  (document count, represented/covered pages, covered sections).
- `docs/DADM_DEPLOY_REGELWERK_SRD_5_2_1_R2_2026-10-16.md` (this record).

No route, template, JS, database, dependency, or production container change was made.

## Acceptance checklist

- [x] All thirteen new documents schema-valid and digest-pinned.
- [x] Package/document inventory, rule-ID uniqueness, and cross-document rule references all
  resolve (e.g. `core.game-loop-and-abilities` references `core.d20-tests`; `core.social-interaction`
  references `core.actions` and `core.proficiency`).
- [x] Generated artifacts current after every addition; no stale-artifact recurrence.
- [x] `core` and `character-creation` top-level sections fully reviewed and covered.
- [x] Human source-fidelity sign-off received on all 25 newly represented pages.
- [x] Full regelwerk, route, and cross-area regression suites green.
- [x] No class/species/feat/spell/monster content transcribed ahead of its authorized milestone.
- [ ] Narrow-screen, keyboard, reduced-motion, and print acceptance checks — still no automated
  coverage (carried over from R1 Deploy; same known gap, not a new one).

## Risks and assumptions

- **Low — accepted:** the browser-level acceptance gap from R1 remains open and unautomated.
- **Low — accepted:** document boundaries diverged from the Apply plan as actual page content was
  read; this is normal refinement, not scope creep — no new page ranges or sections were touched
  beyond what Apply and the Program authorized.
- **Low — accepted:** everything from R0 through R2, plus the earlier trademark-usage fix, remains
  uncommitted in the working tree, consistent with this project's existing practice of accumulating
  DAD-M records before a batched commit.

No unresolved medium-or-higher risk blocks R2 closure.

## Artifacts

- This Deploy record: retention class `immutable`.
- The 13 new documents and updated manifest: retention class `versioned` until R2 Monitor closes.
- Test and validator output above: retention class `immutable` phase evidence.

## Next step

Run R2 Monitor to independently confirm this evidence and recommend closing R2 / starting R3
Discover (Classes, character origins, and feats — pages 33-97, a substantially larger corpus than
R2).
