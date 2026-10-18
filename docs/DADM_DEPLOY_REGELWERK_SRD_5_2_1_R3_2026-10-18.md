# DAD-M Deploy: German SRD 5.2.1 Regelwerk — R3 Corpus Transcription (pages 33-412)

status: complete — transcription and source-fidelity review finished for every required page
date: 2026-10-18
profile: standard
phase: Deploy
milestone: R3 — Classes, character origins, and feats; executed as one continuous transcription run
  covering the content scope of R3-R6 (classes, origins, feats, equipment, spells, glossary,
  gameplay toolbox, magic items, monsters, animals)
discover-input: `docs/DADM_DISCOVER_REGELWERK_SRD_5_2_1_R3_2026-10-16.md`
program: `docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md`

## Execution note

The program sequences R3-R6 as separate milestones. The human product owner directed the run to
continue through the remaining corpus without per-milestone pauses, using a fixed cadence instead:
transcribe a range, validate and digest it, update the manifest, regenerate artifacts, update the
live-package snapshot test, send the rendered source pages to the reviewer by Discord DM, wait for
"Lgtm", extend `reviewedPageRanges`, send a status DM. The milestone content partitions were
therefore closed by reviewer sign-off per page range rather than by one Monitor pass each. This
record is the consolidated Deploy evidence; the matching Monitor record closes the run.

## Delivered

| Section | Pages | Documents |
| --- | --- | --- |
| classes, character-origins, feats | 33-100 | class, origin and feat documents |
| equipment, spells | 101-~235 | equipment documents; spell documents (A-Z letter groups) |
| rules-glossary | glossary pages | glossary letter-group documents |
| gameplay-toolbox | toolbox pages | toolbox chapters |
| magic-items | 236-294 | magic-item rules and A-Z item documents |
| monsters | 295-391 | `monsters.stat-block-overview`, `monsters.stat-block-elements`, 9 letter-group documents (A-B ... W-Z), 235 stat blocks |
| animals | 392-412 | 5 letter-group documents (A-E, F-K, L-Q, R, S-Z), 95 stat blocks |

Package totals: 101 documents; pages 5-412 represented and reviewed; `missingSections: []`;
package status remains `preview`.

## Transcription method and controls

- Verbatim transcription into `regelwerk.document.v1` from the pinned source PDF, generated from the
  page text stream with per-document character-multiset comparison against the source (no missing
  characters; only declared editorial additions in the output).
- Closed block vocabulary; stat blocks use the `stat-block` block with `entries` and `sections`.
- Ability values are rendered as `N (MOD ±x, RW ±y)`; the type line is an entry labelled `Typ`.
- Line-break hyphenation removed; real compound hyphens ("oder"-suspended hyphens such as
  "Rückzug- oder") kept.
- Letter-group documents carry an editorial level-2 heading (e.g. "Monster von A-Z (A-B)").
- Every document digest and the manifest were regenerated; `tools/build_regelwerk.py --check` is
  clean; the schema validator accepts all 101 documents.
- Per range, rendered 150 dpi page images were sent to the reviewer, who answered "Lgtm" before the
  range was added to `reviewedPageRanges`.

## Legal-cleanliness review (CC BY 4.0, attribution in `attribution.txt`)

The product text uses "5E" wording. The SRD's own prose is kept verbatim, including these
licensed-source terms, each reported to the reviewer in the review DM and accepted:

- "D&D" in `core.game-loop-and-abilities` (page 5) and page 18 prose
- "Monsterhandbuch" (page 261 footnote)
- "Tiamat" (page 286, magic items)
- "Yuan-ti" (page 237, magic items)
- "Minotaurus von Baphomet" (page 351), "Tarraske" (page 378), "Rakshasa" (page 361),
  "Sahuagin-Krieger" (page 364), plane names "Neun Höllen" and "Abyss"

No WotC or D&D references were added by Roll Drauf; no content outside the SRD was reconstructed.

## Source anomaly preserved verbatim

- Page 385, Junger weißer Drache: "Int 6 −2 2" — the source omits the minus sign in
  the saving-throw value. Transcribed as printed ("6 (MOD –2, RW 2)").

## Layout normalisations (not content changes)

- Page 408: the Stä/Int modifier cells of the Riesentausendfüßler are separate lines in the PDF
  text stream and were merged into their ability lines.
- Experience-point and proficiency-bonus tables on page 298 keep the source's four-column layout.

## Verification

- `tools/validate_regelwerk.py`: `documentCount: 101`, `representedPageRanges: [{5,412}]`,
  `missingPageRanges: []`, `missingSections: []`, `unexpectedPageRanges: []`, status `preview`.
- `tests/test_regelwerk_package.py` and `tests/test_regelwerk_routes.py`: 39 passed.
- Live-package snapshot test updated to the complete state (101 documents, covered pages 5-412, no
  missing pages or sections, `coverage.complete` true). `test_incomplete_package_cannot_be_published`
  now builds its incomplete case by trimming the copied manifest's reviewed range, because the live
  package is no longer incomplete.

## Open items carried to R7

- The package is not yet `published`; publication needs the named acceptance owner and the final
  legal/fidelity audit (R7).
- Browser-level acceptance checks (keyboard, reduced motion, narrow screen, print) remain
  unautomated, carried from R1. Stat-block rendering on narrow screens and in print is part of the
  R6 acceptance criteria and still needs that check.
- Search alias coverage for monster and animal names has not been exercised beyond the generated
  index.
- The work was committed locally as `7bfe069` (Regelwerk files only; not pushed) and deployed as preview, see the R7 deploy record.
