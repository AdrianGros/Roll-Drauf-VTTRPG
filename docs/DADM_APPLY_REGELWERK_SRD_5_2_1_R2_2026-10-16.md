# DAD-M Apply: German SRD 5.2.1 Regelwerk — R2 Core Play and Character Creation Corpus

date: 2026-10-16
status: complete — document plan ready; transcription sequenced as follow-on execution
phase: Apply
milestone: R2 — Core play and character creation corpus
program: `docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md`
input: `docs/DADM_DISCOVER_REGELWERK_SRD_5_2_1_R2_2026-10-16.md`

## Design summary

R2 covers the rest of `Die Spielregeln` (pages 5, 9-21 — page 5 was never covered by R1; pages 6-8
are already published as `core.d20-tests`) and all of `Charaktererstellung` (pages 22-32). Discover's
text-only pass gave approximate orientation; this Apply pass visually confirmed every major
top-level (H1) heading and several document boundaries directly against the pinned PDF before
committing to a document plan, following the same visual-comparison discipline R1 required.

## Confirmed structure (visual page checks, 2026-10-16)

| Page(s) | Heading(s) observed | Notes |
| --- | --- | --- |
| 5 | Spielrhythmus; Die sechs Attribute; Attributswerte (table); Attributsmodifikatoren (table) | Not yet covered by any document — still shows in `missingPageRanges` |
| 6-8 | W20-Prüfungen | Published as `core.d20-tests` (R1) |
| 8-9 | Vorteil und Nachteil; Mit zwei W20 würfeln; Nicht stapelbar; Heldische Inspiration (callout) | Starts page 8 right column, continues page 9 |
| 9 | Übung (H1); Fertigkeiten, in denen du geübt bist; Fertigkeitenliste; Fertigkeiten bestimmen; Rettungswürfe, in denen du geübt bist | This is the section `core.d20-tests` already forward-references ("Siehe „Übung" weiter hinten...") |
| ~9-12 | Soziale Interaktion; Rollenspiel; Attributswürfe (social) | Ends before page 12's `Erkundung` heading; exact start page needs confirmation during transcription |
| 12-~14 | Erkundung; Abenteuerausrüstung; Lichtverhältnisse und Sicht (+ Verschleierte Bereiche, Licht, Spezialsinne); Sich verstecken; Mit Gegenständen interagieren (+ subsections); Gefahren; Reisen | `Erkundung` confirmed starting page 12 (right column) |
| ~14-18 | Kampf (turn structure, initiative, movement, actions, attacks); Berittener Kampf; Unterwasserkampf | Combat chapter; mounted/underwater combat confirmed on page 18 (left column, before Schaden und Heilung starts) |
| 18-21 | Schaden und Heilung; Trefferpunkte; Schadenswürfe; Schadensarten; Resistenz/Anfälligkeit/Immunität; Anwendungsreihenfolge; Rasten (callout); death-and-dying rules; Nicht stapelbar / Keine Trefferpunkte und keine Heilung (temporary HP) | Confirmed starting page 18 right column; confirmed ending page 21 (page 21 has trailing whitespace after its last subsection — last page of `core`) |
| 22-32 | Charaktererstellung (confirmed starting exactly page 22); Einen Charakterbogen wählen; Deinen Charakter erstellen (5 numbered steps); Schritt 1: Klasse auswählen (+ Klassenüberblick table, names only — no class rules); Schritt 2: Charakterherkunft; ... Stufenaufstiege (~page 26) | Klassenüberblick table lists 12 class names/summary stats only; full class rules are explicitly out of R2 scope (R3) |

A note found in the source itself, not a defect: body text at page 18 reads *"In D&D sind
Verletzungen und Tod häufige Gefahren..."* — the licensed SRD content legitimately uses "D&D"
in its own prose. This must be preserved verbatim where it appears in transcribed content; it is
licensed quoted material, not a Roll Drauf-added reference, and is unrelated to the trademark-usage
fix applied elsewhere in the product today.

## Proposed document plan

Following R1's one-document-per-coherent-topic granularity rather than one document per whole page
range, so each document stays independently reviewable:

| `documentId` | Topic | Provisional pages | Confidence |
| --- | --- | --- | --- |
| `core.game-loop-and-abilities` | Spielrhythmus, die sechs Attribute, Attributswerte/-modifikatoren tables | 5 | confirmed |
| `core.advantage-and-inspiration` | Vorteil und Nachteil, Heldische Inspiration | 8-9 | confirmed |
| `core.proficiency` | Übung, geübte Fertigkeiten/Rettungswürfe | 9 | confirmed |
| `core.social-interaction` | Soziale Interaktion, Rollenspiel | ~9-12 | provisional start page |
| `core.exploration` | Erkundung and all subsections through Reisen | 12-~14 | provisional end page |
| `core.combat` | Kampf, mounted and underwater combat | ~14-18 | provisional boundaries |
| `core.damage-and-healing` | Schaden und Heilung, Trefferpunkte, death/dying, Rasten | 18-21 | confirmed |
| `character-creation.overview-and-steps` | Charaktererstellung intro, 5-step process, Schritt 1-2 | 22-~24 | provisional |
| `character-creation.attributes-and-details` | Schritt 3-5 (Attributswerte, Gesinnung, Details) | ~24-26 | provisional |
| `character-creation.advancement` | Stufenaufstiege, höhere Startstufen, multiclassing/trinkets summary if present at this overview level | ~26-32 | provisional |

Ten documents total (nine new, one — `core.d20-tests` — already published). Provisional boundaries
will be pinned exactly during transcription, the same way R1 pinned `core.d20-tests` to pages 6-8
only after visual comparison, not from the text-extraction pass alone.

## Constraints carried from R1 and the Program

- Verbatim transcription only; no paraphrase, no silent correction of source wording (including the
  source's own "D&D" usage noted above).
- Package `status` stays `preview`; no document here moves the package toward `published`.
- `reviewedPageRanges` stays per-document and is only set after the named source-fidelity reviewer
  confirms each document against the rendered pages — matching the R1 precedent exactly (R1 shipped
  `represented` before `reviewed`; R2 should do the same so transcription isn't blocked on review
  throughput).
- No class, species, feat, spell, or monster content is transcribed here even where the character-
  creation overview names them (e.g., the `Klassenüberblick` table) — that is explicitly R3+ scope.
- Every document addition must be followed by `tools/build_regelwerk.py` (regenerate) and
  `tools/build_regelwerk.py --check` (verify) before any Deploy evidence is recorded — standing
  practice since the R1 Deploy stale-artifact defect.

## Sequencing recommendation

Nine documents of this density (several with numeric tables, and `core.combat` /
`core.damage-and-healing` carrying real rules-fidelity risk) is a substantially larger unit of work
than R1's single three-page slice. Recommend transcribing and reviewing in the table order above —
smallest/lowest-risk first (`core.game-loop-and-abilities`, `core.advantage-and-inspiration`,
`core.proficiency`) to validate the multi-document navigation/search/coverage generator path (R1
only ever exercised it with one document), then the larger sections. This is an internal execution
sequencing choice within the existing R2 milestone, not a new plan version or scope change, so it
needs no additional human approval.

## Risks and assumptions

- **Medium — open, carried to Deploy:** R2 Deploy still needs a named content lead per the Program's
  Roles section. Not required for this Apply pass or for transcription itself.
- **Low — accepted:** provisional page boundaries for `core.social-interaction`, `core.exploration`'s
  end, `core.combat`'s start/end, and both `character-creation` sub-splits will be confirmed
  page-by-page during transcription, not re-litigated here.
- **Low — accepted:** ten documents in one `core`/`character-creation` top-level section is new
  territory for the generator (R1 had one document in `core`); no code change is anticipated, but
  Deploy should explicitly verify navigation ordering and search ranking behave correctly with
  multiple documents before closing.

No critical or high-severity finding. No human-decision trigger fires for Apply itself.

## Artifacts

| Artifact | Retention | Purpose |
| --- | --- | --- |
| This Apply record | permanent | Document plan and confirmed/provisional boundaries |
| R2 Discover record | permanent | Predecessor risk boundary, not reinterpreted here |
| Page renders used for boundary confirmation (scratch, pages 5, 8-22) | transient evidence summarized here | Not transcription source; transcription still requires its own visual pass per document |

## Next step

Begin transcription in the sequencing order above, one document at a time: draft the semantic JSON,
regenerate and check artifacts, run the full regelwerk test suite, and request source-fidelity
review per document (not batched at the end). Flag the content-lead gate to the product owner before
attempting R2 Deploy's closure evidence.
