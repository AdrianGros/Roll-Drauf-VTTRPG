# DAD-M Discover: German SRD 5.2.1 Regelwerk — R2 Core Play and Character Creation Corpus

date: 2026-10-16
status: complete — boundary established for R2 Apply
phase: Discover
milestone: R2 — Core play and character creation corpus
program: `docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md`
predecessor: `docs/DADM_MONITOR_REGELWERK_SRD_5_2_1_R1_2026-10-16.md`

## Input summary

The approved program scopes R2 as the complete German SRD sections `Die Spielregeln` (pages 5-21)
and `Charaktererstellung` (pages 22-32) — 27 pages, excluding the 3 already reviewed and published
in R1 (`W20-Prüfungen`, pages 6-8). This is read-only research: it inventories the source material's
structure and risk surface. It does not transcribe content, select final document boundaries, or
implement anything.

## Current-state summary

- R1 is closed and Monitored. The reader shell, routes, generator, and validator proved the
  end-to-end pipeline on one short, single-table-light section.
- R2 is roughly **9x the page volume** of R1 (27 pages vs. 3) and structurally different: R1 was one
  self-contained topic with four tables; R2's `Die Spielregeln` remainder covers combat (turn
  structure, movement, actions, attacks), damage and healing (a dense, numerically exacting
  sub-chapter — damage types, resistance/vulnerability/immunity, application order, death saves,
  stabilizing), exploration (travel, environment hazards), and more, before `Charaktererstellung`
  starts an entirely different topic (ability score assignment, species/background/class choice at
  a high level — actual class/species/feat content is explicitly out of R2 scope per the program;
  that is R3).
- A raw `pdftotext -layout` pass across pages 9-32 located the following headings reliably, used
  only as rough orientation (page numbers approximate; the two-column layout reflows unpredictably
  in plain-text extraction, same limitation R1 Discover already flagged):
  - `Erkundung` (Exploration) heading near source page 12, `Reisen` (Travel) subsection nearby.
  - `Kampf` (Combat) heading near source page 14.
  - `Stufenaufstiege` (Leveling up) subsection near source page 26, inside `Charaktererstellung`.
  - Extensive `Schaden und Heilung` (Damage and Healing) content with many sub-rules (Schadenswürfe,
    Schadensarten, Resistenz/Anfälligkeit/Immunität, Anwendungsreihenfolge, Halber Schaden,
    Rettungswürfe und Schaden, Schaden bei mehreren Zielen, Todesrettungswürfe, Einen Charakter
    stabilisieren) appears interleaved with or following the Kampf section, roughly pages 15-20.
  - `Charaktererstellung` itself begins around source page 21-22, matching the manifest's existing
    `firstPage: 22` pin for that top-level section (pages 5-21 for `core` already matches observed
    structure: attributes intro on p5, W20-Prüfungen on 6-8, remaining core-rules content 9-21).
- This text-only pass is explicitly **not sufficient to fix final document/page boundaries**. R1's
  own validated lesson applies here at larger scale: hyphenation, column reflow, and control
  characters make raw extraction unreliable for anything beyond orientation; final boundaries and
  verbatim content require the same visual page-by-page comparison method R1 used, reviewed by the
  named source-fidelity reviewer.

## Relevant inventory

| Artifact | Current responsibility | R2 relevance |
| --- | --- | --- |
| `vtt/rules_content/srd-5.2.1-de/manifest.json` `expectedTopLevelSections` | Already pins `core` (5-21) and `character-creation` (22-32) boundaries | R2 must stay within these; no boundary change needed |
| `vtt/rules_content/validator.py` | Schema, digest, coverage, and reference checks | Unchanged; must keep passing as documents are added |
| `vtt/rules_content/generator.py` / `tools/build_regelwerk.py` | Deterministic navigation/search/coverage generation | Unchanged; must be rerun after every document addition (R1 Deploy caught a stale-artifact defect from skipping this) |
| `tests/test_regelwerk_package.py`, `tests/test_regelwerk_routes.py` | 39 passing contract tests | Must stay green; likely need new fixtures/cases for multi-document navigation and search once R2 adds documents |
| `docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md` Roles section | Names Donutarian as VTT integration lead and source-fidelity reviewer (R1) | **Content lead is required before R2 Deploy** and is not yet named |

## Structural difference from R1 that Apply must resolve

R1 shipped exactly one document (`core.d20-tests`) for one short, self-contained topic. R2's source
material does not fit that pattern:

1. **Volume.** 27 pages of dense rules text, several with multi-row numeric tables (damage,
   leveling, death saves), is not one defensible "vertical slice" — it is the bulk of a chapter.
2. **Natural seams.** The content has clear internal topic boundaries (Erkundung / Kampf / Schaden
   und Heilung / Charaktererstellung, each with further subsections) that map naturally to separate
   documents, consistent with R0/R1's existing `documentId` granularity (one document per coherent
   rule topic, not one document per chapter).
3. **Incremental reviewability.** A human source-fidelity reviewer comparing content against the
   pinned PDF scales with page count. Asking for one 27-page review pass is a much larger ask than
   R1's 3-page pass; splitting into smaller reviewable documents (as R1 already does per-document)
   lets review happen incrementally rather than as one large batch at the end.

## Risks and assumptions

| Severity | Finding | Evidence / treatment before Deploy |
| --- | --- | --- |
| medium — resolved for transition | Raw-text heading/page mapping is approximate only | Apply/transcription must use the same visual PDF comparison method R1 used (page renders, not text extraction) before any document is marked verbatim |
| medium — resolved for transition | Volume makes a single end-to-end review pass impractical | Apply must define a document-by-document transcription and review sequence, not one monolithic batch |
| medium — open | **Content lead is required before R2 Deploy** (Program Roles section) and has no name on record | Apply and transcription drafting may proceed (Discover/Apply do not require this role per the R1 precedent — only Deploy does); R2 Deploy cannot close until a content lead is named |
| low | Damage/healing and death-save rules are numerically exacting (resistance math, death-save counting, massive damage threshold) | Full field-by-field comparison required per R1's existing validator discipline (table column counts, rule-ID resolution); no new tooling gap identified |
| low | `Charaktererstellung` at R2 is explicitly high-level only (no classes/species/feats — that is R3) | Apply must bound R2 documents to avoid silently drafting R3-scope content (e.g., do not transcribe class tables while covering "how character creation works") |
| low | The source PDF's own body text uses "D&D" directly (e.g., "Die drei Säulen bei D&D sind...") | This is licensed, quoted SRD content and is correctly preserved verbatim — it is not an added Roll Drauf reference and is unaffected by the trademark-usage fix made elsewhere in the product today. Apply should note this explicitly so nobody "corrects" licensed source text during transcription. |

No critical or high-severity finding was found. The content-lead gate is the same shape as R1's two
role gates and is expected to resolve the same way (a human name), not a scope or design blocker.

## Assumptions carried into Apply

- R2's natural document split follows the observed topic seams (Erkundung, Kampf, Schaden und
  Heilung, and a bounded Charaktererstellung overview), each as its own `documentId`, mirroring R1's
  one-document-per-topic granularity rather than one document per whole page range.
- Exact page boundaries per document are provisional until visually confirmed against the pinned PDF
  during transcription, exactly as R1 required.
- R2 Deploy and Monitor need the named content lead before they can close, matching the Program's
  Roles section. Apply and the transcription/document-drafting work itself does not require it.
- Generated artifacts (`navigation.json`, `search-index.json`, `coverage.json`) must be rebuilt after
  every document addition and checked with `tools/build_regelwerk.py --check` before any Deploy
  evidence is recorded — this is now standing practice after the R1 Deploy fix.

## Open questions for R2 Apply

1. Exact document list and `documentId` naming for the Erkundung / Kampf / Schaden-und-Heilung /
   Charaktererstellung-overview split.
2. Exact page boundaries per document (requires visual PDF comparison, not raw-text extraction).
3. Whether R2 ships as one Apply/Deploy/Monitor pass covering all documents, or whether Apply should
   recommend further splitting R2 into smaller internal batches for incremental review — this is an
   implementation sequencing choice within the existing R2 milestone, not a program-scope change.
4. How the navigation/search generator and reader JS handle multiple documents within one
   `expectedTopLevelSections` section (`core`) for the first time (R1 only ever had one).

These are bounded design questions with clear evaluation criteria; none requires product-owner
intervention before Apply.

## Artifacts

| Artifact | Retention | Purpose |
| --- | --- | --- |
| This Discover record | permanent | Immutable R2 current-state and risk boundary after transition |
| R1 package/schemas/validator/tests/reader | permanent | Approved predecessor contract; not reinterpreted by R2 |
| Raw-text heading scan (`r2-pages.txt`, scratch) | transient evidence summarized here | Orientation only; not a transcription source |

## Next step

Enter R2 Apply. Define the exact document list and provisional page boundaries for `Erkundung`,
`Kampf`, `Schaden und Heilung`, and the bounded `Charaktererstellung` overview; specify the
visual-comparison and incremental-review sequence; then begin transcription document-by-document,
re-running the generator and the full regelwerk test suite after each addition. R2 Deploy and
Monitor cannot close until a human content lead is named, per the Program's Roles section — flag
this to the product owner once Apply's document plan is ready for review.
