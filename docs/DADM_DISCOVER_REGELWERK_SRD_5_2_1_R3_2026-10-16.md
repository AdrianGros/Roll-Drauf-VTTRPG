# DAD-M Discover: German SRD 5.2.1 Regelwerk — R3 Classes, Character Origins, and Feats

date: 2026-10-16
status: complete — boundary established for R3 Apply
phase: Discover
milestone: R3 — Classes, character origins, and feats
program: `docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md`
predecessor: `docs/DADM_MONITOR_REGELWERK_SRD_5_2_1_R2_2026-10-16.md`

## Input summary

The approved program scopes R3 as all twelve included classes with their included subclasses,
class tables (and per-class spell lists, not full spell descriptions — those are R4), backgrounds,
species, and feats: pages 33-100, 68 pages. This is read-only research, confirmed against the
manifest's existing `expectedTopLevelSections` pins (`classes` 33-92, `character-origins` 93-97,
`feats` 98-100) and against rendered page images at every section boundary.

## Confirmed structure

### Classes (pages 33-92, 60 pages)

Twelve classes in alphabetical order, each confirmed by its "Hauptmerkmale des X" quick-reference
table heading:

| Class | Start page | Approx. end | Approx. pages |
| --- | --- | --- | --- |
| Barbar | 33 | 35 | 3 |
| Barde | 36 | 40 | 5 |
| Druide | 41 | 47 | 7 |
| Hexenmeister | 48 | 54 | 7 |
| Kämpfer | 55 | 57 | 3 |
| Kleriker | 58 | 62 | 5 |
| Magier | 63 | 69 | 7 |
| Mönch | 70 | 72 | 3 |
| Paladin | 73 | 77 | 5 |
| Schurke | 78 | 81 | 4 |
| Waldläufer | 82 | 85 | 4 |
| Zauberer | 86 | 92 | 7 |

Every class chapter follows the same internal pattern, confirmed by visually reading the Barbar
chapter (pages 33-34) in full:

1. A quick-reference table ("Hauptmerkmale des X": Hauptattribut, Trefferpunktewürfel,
   Rettungswürfe, Fertigkeiten, Übung im Umgang mit Waffen, Rüstungsvertrautheit,
   Anfangsausrüstung).
2. "Ein X werden ..." — two short bullet lists: what a 1st-level character of this class gets, and
   what a character gains when multiclassing into it (a bounded subset of the Program's own
   Klassenkombinationen rules from R2, confirmed cross-referencing correctly).
3. A full 1-20 level progression table ("Xmerkmale": Stufe, Übungsbonus, Klassenmerkmale, plus
   class-specific tracked resources as extra columns — e.g. the Barbarian table adds
   Kampfrausch-Anzahl, Kampfrausch-Schaden, and Waffenbeherrschung columns).
4. Full prose description of every named feature at every level it's gained — this is the bulk of
   each chapter's length and its highest fidelity risk (exact wording of class mechanics).
5. Exactly one subclass per class (confirmed: Barbarian gets "Pfad des Berserkers"), granted at a
   fixed level (3rd for the Barbarian) with its own leveled feature set layered into the same
   chapter.

### Character origins (pages 93-97, 5 pages)

Confirmed by direct page render. Two sub-sections, both far more compressed than R2's treatment
suggested:

- **Charakterhintergründe** (backgrounds) — an "Elemente eines Hintergrunds" explainer, then full
  descriptions of four backgrounds: Akolyth, Krimineller, Soldat, Weiser. Each entry lists
  Attributswerte, Talent, Fertigkeiten, Übung im Umgang mit Werkzeug, and an equipment choice (A/B).
  R2 only ever showed one example-reference table naming "Soldat" and "Akolyth"; the actual
  background rules are entirely unwritten until R3.
- **Charakterspezies** (species) — nine species: Drachenblütiger, Elf, Gnom, Goliath, Halbling,
  Mensch, Ork, Tiefling, Zwerg. Confirmed only the section intro so far; per-species detail depth
  needs visual confirmation during Apply/transcription (5 pages for 9 species implies compact
  entries, roughly half a page each).

### Feats (pages 98-100, 3 pages)

Confirmed by direct page render. An "Elemente eines Talents" explainer, then feats grouped by the
four categories the intro itself names: Herkunft (origin), Allgemein (general), Kampfstil (fighting
style), and Epische Gabe (epic boon). Confirmed present: Begabt, Eingeweihter der Magie, Wachsam,
Wilder Angreifer (origin); Attributswerterhöhung, Ringer (general) — fighting-style and epic-boon
feats not yet visually confirmed, likely later on page 99-100 given only 3 pages total.

## Scale relative to R2

R3 is roughly **2.5x R2's page count** (68 vs. 27) and structurally denser: every class chapter is
itself comparable in length and complexity to one of R2's own documents (R2's `core.combat-turns` /
`core.combat-attacks` / `core.damage-and-healing` split, for scale), and R3 has twelve of them plus
a subclass each, plus backgrounds, species, and feats on top. A naïve one-document-per-class split
(matching R1/R2's one-document-per-topic granularity) would produce roughly **12 class-feature
documents + 12 subclass documents + a handful for backgrounds/species/feats ≈ 28-30 documents**,
each carrying real rules-fidelity risk (progression tables, exact resource math, feature text that
player builds depend on).

## Risks and assumptions

| Severity | Finding | Evidence / treatment before Deploy |
| --- | --- | --- |
| medium — resolved for transition | Raw-text class-start page mapping needed a tooling fix mid-Discover (per-page text extraction silently concatenated page markers without a newline separator, corrupting the first page-mapping attempt) | Fixed the extraction script before trusting any page number in this record; every page number above is sourced from the corrected extraction or a direct visual render, not the broken first pass |
| medium — open | Volume (68 pages, ~30 likely documents) is large enough that a single uninterrupted Apply+transcription pass risks the same kind of fidelity-review backlog R2 already stretched (25 pages reviewed in one sitting) | Recommend explicit pacing: transcribe and request review in smaller batches (e.g. per class, or in small class groups) rather than all twelve classes before any review, unlike R2 which batched all 13 documents before requesting sign-off |
| low | Each class's subclass is granted at a different level (3rd for Barbarian; not yet confirmed for the other eleven) | Apply must confirm the grant level per class during transcription, not assume uniformity |
| low | Species section is very compressed (5 pages for 9 entries) | Visual, not text-extraction, comparison is required per entry — same discipline as every milestone so far |
| low | Feat categories (Kampfstil, Epische Gabe) not yet visually confirmed | Apply/transcription will confirm when those pages are read directly |

No critical or high-severity finding. No human-decision trigger fires for Discover itself — but
given the scale, this Discover record recommends the pacing question go to the product owner before
Apply commits to a specific document plan and batch size.

## Assumptions carried into Apply

- One document per class's core features, one per its subclass — mirroring R1/R2's granularity —
  unless Apply finds a shorter class (e.g. Barbar or Kämpfer at 3 pages) fits better as a single
  combined document with its subclass.
- Backgrounds (4) and species (9) each likely warrant their own one or two documents rather than
  one per entry, given their compressed per-entry length — to be confirmed once Apply reads the
  full section visually.
- Feats likely split by category (origin/general/fighting-style/epic boon) into one or two
  documents, not one per feat, consistent with keeping document count proportional to topic
  coherence rather than exploding it.

## Open questions for R3 Apply

1. Exact document list and count — the ~28-30 estimate above is provisional until the full page
   range is read visually, not just text-extracted.
2. Batch size and review cadence: transcribe-then-review per class, in small groups, or still as one
   large batch like R2? This affects both Apply's sequencing plan and how many review round-trips
   the product owner takes on.
3. Per-class subclass grant level (confirmed only for Barbarian so far).
4. Species entry structure and length — needs direct visual confirmation.

## Artifacts

| Artifact | Retention | Purpose |
| --- | --- | --- |
| This Discover record | permanent | Immutable R3 current-state and risk boundary after transition |
| R0-R2 package/schemas/validator/tests/reader | permanent | Approved predecessor contract; not reinterpreted by R3 |
| Corrected per-page text extraction (`r3-pages.txt`, scratch) | transient evidence summarized here | Orientation only; not a transcription source |

## Next step

Before starting R3 Apply (document planning) or any transcription, flag the batch-size/pacing
question to the product owner given R3's size relative to R2. This is a process/pacing decision,
not a new program-scope change, so it needs no formal approval record — but it is large enough that
proceeding without checking in would repeat, at roughly 2.5x scale, the same "review everything at
once" pattern R2 used.
