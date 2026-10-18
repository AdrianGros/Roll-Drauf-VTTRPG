# Regelwerk R1 Source Review — W20-Prüfungen

date: 2026-10-15
status: preview transcription reviewed; independent publication review pending
document: `core.d20-tests`
source: `Systemreferenzdokument 5.2.1` (German)
source URL: `https://media.dndbeyond.com/compendium-images/srd/5.2/DE_SRD_CC_v5.2.1.pdf`
source SHA-256: `f06989dcdf98c8e93b52ba5ea9db52d5e1b054d6d87a148ff295138bafe8a65b`
printed pages: 6–8
transcriber/reviewer: Codex, visual comparison at 2.2× raster resolution

## Boundary

Included:

- `W20-Prüfungen`, beginning on printed page 6;
- all three procedure steps and their modifier list;
- `Attributswürfe`, including both tables and all subsections;
- `Rettungswürfe`, including its table and all subsections;
- `Angriffswürfe`, including its table, armor-class rules, and natural 20/1 rules;
- final included sentence: a natural 1 misses regardless of modifiers and target AC.

Explicitly excluded:

- `Attributsmodifikatoren` and earlier material above the selected heading on printed page 6;
- `Vorteil und Nachteil` and `Heldische Inspiration` beginning beside the selected material on
  printed page 8.

Because the selected section shares its first and final printed pages with excluded material, pages
6–8 are provenance only. No page is entered in `reviewedPageRanges` and no complete-page coverage
is claimed.

## Visual comparison checklist

- [x] Source download SHA-256 matches the external source lock.
- [x] Heading order compared across both columns of printed pages 6, 7, and 8.
- [x] Three W20 procedure steps and all three modifier bullets compared.
- [x] Every number and abbreviation compared: 1W20, W20, SG 5/10/15/20/25/30, RK, 10 +
      Geschicklichkeitsmodifikator, natural 20, natural 1.
- [x] `Beispiele für Attributswürfe`: 2 columns × 6 body rows compared.
- [x] `Typische Schwierigkeitsgrade`: 4 columns × 3 body rows compared.
- [x] `Beispiele für Rettungswürfe`: 2 columns × 6 body rows compared.
- [x] `Angriffswurf-Attribute`: 2 columns × 3 body rows compared.
- [x] Quotation marks, en dashes, umlauts, compound words, and cross-reference wording compared.
- [x] The start and end boundaries were checked against adjacent source headings.
- [x] Semantic JSON contains no source-controlled HTML.

## Extraction discrepancies resolved visually

The extracted PDF text was not used without review. The visual pages resolved these extraction
artifacts:

- line-wrap/soft-hyphen splits such as `Anhalts­punkte`, `Konstitutions­rettungswurf`,
  `Geschick­lichkeit`, `Ausrüs‑tung`, and `entspre‑chenden` were restored as normal German words;
- the two-column extraction order on printed pages 6–8 was reordered to match the visual reading
  flow;
- nonbreaking spaces introduced by extraction were normalized to ordinary semantic spaces;
- the multi-line basis-AC formula was retained as separated text inside its rule callout rather
  than flattened into an invented sentence;
- typographic minus/plus characters and table values were checked directly where present in the
  selected source.

## Semantic-format notes

- The numbered procedure is represented as numbered level-3 headings plus paragraphs, with the
  nested modifiers retained as an unordered list. Wording is not paraphrased.
- Source bold labels `RK berechnen:` and `Nur eine Basis-RK:` are represented as callout titles;
  their prose remains source text.
- Source line and column breaks are presentation, not authored newlines. Paragraph boundaries,
  list boundaries, table cells, and rule headings remain explicit semantic blocks.
- References to chapters not yet present in the preview remain source prose. No unresolved typed
  `ruleRefs` were fabricated.

## Review counts

| Item | Count |
| --- | ---: |
| Source pages represented | 3 |
| Source pages claimed complete | 0 |
| Semantic blocks | 41 |
| Tables | 4 |
| Table body rows | 18 |
| Typed cross-document rule references | 0 |

## Publication gate

This record is sufficient for the R1 engineering preview. It is not independent human fidelity
sign-off. Before the package can become `published`, a named reviewer other than the transcriber
must repeat the source comparison and record acceptance under the program's R7 gate.
