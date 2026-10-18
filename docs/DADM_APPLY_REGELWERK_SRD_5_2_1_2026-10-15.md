# DAD-M Apply: German SRD 5.2.1 Regelwerk

version: 1
status: complete — approved 2026-10-15; R0 Deploy authorized
date: 2026-10-15
profile: standard
phase: Apply
basis: completed SRD/licensing Discover pass; official German SRD 5.2.1; Creation Engine v1.2; current VTT Book Scene

## 1. Input summary

The requested product outcome is a Roll Drauf-native main ruleset based on the complete German
System Reference Document 5.2.1. The VTT website must expose it through a first-class
**Regelwerk** tab, and that surface must become the canonical in-product destination for rules
references.

Discover established these constraints:

- the German SRD 5.2.1 is available under CC BY 4.0 and may be reproduced and adapted with the
  required attribution and change notices;
- the licensed source is the SRD itself, not D&D Beyond's Basic Rules or purchased rulebooks;
- the German PDF has 412 pages and includes the player rules, character options, spells,
  equipment, glossary, game-master tools, magic items, monsters, and animals;
- the repository has original Roll Drauf Light content and provenance-capable Creation Engine
  revisions, but no complete 5E corpus or repository-level SRD attribution package;
- the current Book Scene navigation has no Regelwerk destination; and
- the Creation Engine specification already requires 2014 and 2024-compatible rulesets to stay
  explicitly separated.

The official upstream artifact selected for this project is:

- title: `Systemreferenzdokument 5.2.1`;
- locale: `de-DE`;
- publication date shown by the official SRD page: 2025-12-08;
- URL: `https://media.dndbeyond.com/compendium-images/srd/5.2/DE_SRD_CC_v5.2.1.pdf`;
- SHA-256 verified on 2026-10-15:
  `f06989dcdf98c8e93b52ba5ea9db52d5e1b054d6d87a148ff295138bafe8a65b`.

## 2. Design summary

Build one versioned German rules corpus and expose it through one canonical reader.

Authority is deliberately separated into three layers:

1. **Legal upstream:** the digest-pinned official German SRD PDF is the authority for what may be
   reproduced and for source fidelity.
2. **Repository source of truth:** a versioned semantic content package is the only editable Roll
   Drauf representation of that source. Every document carries provenance, licensing, change
   status, and stable rule IDs.
3. **Canonical published target:** `/regelwerk` renders the active package. Character sheets,
   compendium entries, Creation Engine definitions, help text, and VTT actions link to its stable
   rule IDs instead of keeping copies of rule prose.

The initial package identity is `srd-5.2.1-de`. It represents the 2024/5.5e-compatible SRD and
must never silently include SRD 5.1/2014 mechanics. A later 2014 package receives a separate ID,
manifest, routes, and compatibility profile.

The complete ruleset is the project target. Delivery is incremental, but `/regelwerk` remains a
labelled preview until the completeness, fidelity, licensing, and navigation gates have passed.

## 3. Explicit design decisions

### D1 — Licensed wording is preferred

Use the official German SRD wording verbatim where practical. Formatting-only normalization is
recorded separately from substantive adaptation. Rewriting licensed rules merely to appear more
original would reduce mechanical fidelity and increase editorial error without improving the
license position.

### D2 — Original Roll Drauf material stays visibly separate

Turtonia lore, Roll Drauf examples, custom species, optional rules, and explanatory notes are
separate original documents or explicitly labelled callouts. They never appear as if they were
part of the SRD. The first custom-content acceptance fixture will be the telekinetic duck species,
but its design is not part of the SRD transcription milestones.

### D3 — Semantic JSON is the canonical repository format

The corpus uses JSON documents with a small, versioned set of safe block types. It does not store
arbitrary executable HTML and does not require a new runtime Markdown dependency. The renderer
escapes text and owns all markup.

### D4 — Stable rule IDs outlive presentation changes

Every addressable rule receives an edition- and locale-scoped ID. Titles, navigation placement,
and layout may change without changing the ID. A changed rule body creates a new package version;
published package versions are immutable.

### D5 — The reader is public and read-only

Versioned Regelwerk pages and content endpoints contain no account, campaign, or character data
and require no authentication. The Regelwerk tab is also present inside the authenticated Book
Scene. Public access supplies stable citations and avoids coupling CC-licensed content to account
entitlements.

### D6 — One main version, stable historical URLs

`/regelwerk` resolves to the configured main package. Versioned URLs remain stable so saved links
do not change when a future ruleset becomes primary.

### D7 — Generated artifacts are never authoritative

Search indexes, navigation trees, rendered HTML, and caches are derived from the package and can
be rebuilt. They may not be edited directly.

## 4. Solution boundary

### In scope

- The complete German SRD 5.2.1 corpus.
- Exact CC BY attribution, source provenance, source digest, and change marking.
- A versioned content manifest and validated semantic document format.
- A responsive, accessible `/regelwerk` reader matching the VTT's Book Scene presentation.
- Chapter navigation, table of contents, breadcrumbs, previous/next navigation, search, stable
  deep links, copy-link behavior, and print-friendly rendering.
- A global **Regelwerk** tab in authenticated VTT navigation, character sheet, Creation Engine,
  and play workspace.
- A small public read API for the manifest, documents, and search results.
- Stable rule references that later executable mechanics and character resources can use.
- Automated structural, licensing, link, coverage, security, and route tests.
- A staged rollout with preview, completeness gate, activation, and rollback.

### Out of scope

- Importing or scraping characters from D&D Beyond.
- Copying D&D Beyond pages, UI, character-sheet presentation, or Basic Rules content.
- Reproducing non-SRD books, artwork, logos, settings, protected trade dress, or omitted branded
  material.
- Implementing every rule as executable VTT automation during this program.
- Designing the complete custom-content balance system; only the reference boundary and a later
  acceptance fixture are reserved here.
- Mixing SRD 5.1/2014 content into `srd-5.2.1-de`.
- A general-purpose WYSIWYG publishing system.
- Replacing the existing Creation Engine architecture.

## 5. Canonical content package

The planned package boundary is:

```text
vtt/rules_content/srd-5.2.1-de/
  manifest.json
  attribution.txt
  documents/
    <document-id>.json
  generated/
    navigation.json
    search-index.json
    coverage.json
```

`manifest.json`, `attribution.txt`, and `documents/*.json` are canonical inputs. `generated/` is
reproducible output.

### 5.1 Manifest contract

The manifest contains at minimum:

| Field | Contract |
| --- | --- |
| `schemaVersion` | `regelwerk.package.v1` |
| `rulesetId` | `srd-5.2.1-de` |
| `rulesetVersion` | immutable package version |
| `edition` | `2024` |
| `locale` | `de-DE` |
| `status` | `draft`, `review`, `preview`, `published`, or `retired` |
| `title` | user-facing German title |
| `source` | official URL, title, publication date, retrieval date, and SHA-256 |
| `license` | `CC-BY-4.0`, license URL, attribution-file reference |
| `documents` | ordered document IDs, slugs, titles, and digests |
| `coverage` | expected and present source sections/pages |
| `publishedAt` | required only for a published package |

The package digest is computed from canonical manifest and document bytes. Publishing freezes
those bytes. Corrections create a new package version and retain the prior version.

### 5.2 Document contract

Each document contains:

| Field | Contract |
| --- | --- |
| `schemaVersion` | `regelwerk.document.v1` |
| `rulesetId` | must match the manifest |
| `documentId` | stable opaque identity |
| `slug` | stable URL segment; aliases preserve renamed slugs |
| `title` | official German heading where SRD-derived |
| `navigationPath` | ordered German table-of-contents path |
| `order` | deterministic order within its parent |
| `sourcePages` | one or more one-based PDF pages |
| `contentStatus` | `verbatim`, `format-only`, `adapted`, or `original` |
| `blocks` | ordered safe semantic blocks |
| `ruleRefs` | links to other stable rule IDs |
| `digest` | canonical content digest |

Supported v1 blocks are deliberately small:

- `heading`;
- `paragraph`;
- `ordered-list` and `unordered-list`;
- `definition-list`;
- `table`;
- `rule-callout`;
- `stat-block`;
- `page-note`; and
- `original-note`, which must visibly identify non-SRD Roll Drauf material.

Every addressable block has a stable `ruleId`. Text values are plain text; links are typed
internal or approved external references. No scripts, event attributes, iframes, or arbitrary
HTML are permitted in content documents.

### 5.3 Rule reference contract

A reference stored elsewhere in the VTT has this minimum shape:

```json
{
  "rulesetId": "srd-5.2.1-de",
  "ruleId": "core.d20-tests.ability-checks",
  "label": "Attributswürfe"
}
```

The label is display fallback only. Resolution is always by `rulesetId + ruleId`. A missing or
retired reference renders a clear unavailable state and never falls through to another edition.

## 6. Regelwerk website experience

### 6.1 Routes

| Route | Purpose |
| --- | --- |
| `/regelwerk` | canonical entry for the configured main ruleset |
| `/regelwerk/5.2.1/de/<slug>` | stable versioned document URL |
| `/regelwerk/5.2.1/de/<slug>#<rule-id>` | stable rule-level citation |
| `/regelwerk/lizenz` | attribution, license, source, modification policy |

The unversioned route may redirect or resolve internally, but the browser exposes the versioned
canonical URL once a document is selected.

### 6.2 Layout

The Regelwerk is a Book Scene chapter, not a disconnected admin tool. Its desktop layout has:

- global VTT ribbon with **Regelwerk** active;
- ruleset/version badge `SRD 5.2.1 · Deutsch`;
- collapsible table of contents;
- central reading column;
- local search and result count;
- breadcrumbs and previous/next document controls;
- persistent copy-link control for the current rule;
- visible source and modification status; and
- attribution/license footer.

On narrow screens, the table of contents becomes a drawer, reading order remains linear, and no
horizontal scrolling is required except inside explicitly labelled wide tables.

### 6.3 Navigation placement

The shared authenticated order becomes:

`Übersicht → Kampagnen → Charaktere → Regelwerk → Creation Engine → Spieltisch`

Regelwerk is also available from the character-sheet focus page and the play workspace. Opening a
rule during play must support a new tab without changing session state.

### 6.4 Search behavior

Search is German-first and searches normalized titles, headings, body text, aliases, and indexed
terms. Results return title, breadcrumb, short excerpt, and stable rule URL. The first version does
not require fuzzy ranking or a database-backed search service. The checked-in generated index is
rebuilt from published documents and verified against their digests.

### 6.5 Accessibility and presentation

- Semantic heading order and landmarks are mandatory.
- All reader operations work by keyboard.
- Search results and document loading announce status without stealing focus.
- Color is not the sole indicator for source/modification status.
- Tables expose captions and headers.
- Print output includes title, version, canonical URL, and attribution.
- Content remains readable when animation is disabled.

## 7. Public read interfaces

The planned API namespace is `/api/rulesets`.

### `GET /api/rulesets/main`

Returns the active public package identity and canonical Regelwerk URL. It contains no user state.

### `GET /api/rulesets/srd-5.2.1-de/manifest`

Returns the published public manifest, its package digest, navigation URL, coverage summary, and
license URL.

### `GET /api/rulesets/srd-5.2.1-de/documents/<document-id>`

Returns one published document by stable ID. Unknown IDs return `404`; drafts are never exposed by
this interface.

### `GET /api/rulesets/srd-5.2.1-de/search?q=<query>`

Returns bounded search results from the generated index. Empty or oversized queries are rejected
consistently. Results contain stable rule IDs and canonical URLs.

Versioned published resources use ETags derived from their digests and public cache headers. The
unversioned `main` response uses short revalidation so activation can change without breaking
historical content.

## 8. Editorial and publishing workflow

Each corpus milestone follows this controlled flow:

1. **Select:** register exact PDF page ranges and expected table-of-contents entries.
2. **Transcribe:** extract or enter text only from the digest-pinned official German PDF.
3. **Normalize:** represent headings, lists, tables, and stat blocks without substantive edits.
4. **Identify:** assign stable document and rule IDs.
5. **Record:** attach source pages and `contentStatus` to every document.
6. **Review source fidelity:** compare text, numbers, tables, names, and exceptions to the PDF.
7. **Review presentation:** validate rendering, accessibility, deep links, and responsive behavior.
8. **Build:** regenerate navigation, search, coverage, and package digests.
9. **Preview:** publish behind the Regelwerk preview flag with a visible coverage statement.
10. **Approve:** a human reviewer signs off the milestone's source ranges and acceptance report.
11. **Publish:** freeze the package version. Corrections create a successor version.

OCR or PDF text extraction is an aid, never an authority. No extracted document may reach preview
without source-page review, because line breaks, ligatures, tables, and special characters can be
corrupted silently.

## 9. Content topology

The corpus follows the official German SRD table of contents:

1. Die Spielregeln.
2. Charaktererstellung.
3. Klassen and their included subclasses.
4. Charakterherkunft: backgrounds and species.
5. Talente.
6. Ausrüstung.
7. Zauberwirken and Zauber.
8. Regelglossar.
9. Werkzeugkasten fürs Spiel.
10. Magische Gegenstände.
11. Monster.
12. Tiere.

These are editorial partitions, not separate rulesets. Cross-references always retain the same
`srd-5.2.1-de` identity.

## 10. Rules-engine and character integration boundary

The Regelwerk corpus is the canonical human-readable authority. Executable Creation Engine
definitions remain separately versioned machine contracts. They link to rule IDs and source
pages, but neither representation silently overwrites the other.

For each later executable definition:

- `rulesetId` and `ruleId` identify the displayed rule;
- the definition revision and execution lock identify the mechanics actually executed;
- a conformance fixture proves that the executable result matches the published prose; and
- any unsupported mechanic is labelled manual rather than approximated invisibly.

Character-sheet spells, features, species traits, equipment, conditions, and actions should
eventually use rule references. This program only requires the link contract and representative
links; comprehensive gameplay automation remains a separate program.

## 11. Licensing and provenance controls

- The required German SRD 5.2.1 attribution from PDF page 1 is stored once in
  `attribution.txt` and rendered on `/regelwerk/lizenz` and in print output.
- The CC BY 4.0 legal-code URL and official SRD URL remain clickable.
- Modified documents state that changes were made and preserve prior modification indications.
- The product may say `5E-kompatibel`; it does not use D&D or D&D Beyond as Roll Drauf branding.
- No official logos, artwork, page design, or D&D Beyond UI are imported.
- Only the digest-pinned German SRD is an approved Wizards content source for this package.
- Original Roll Drauf material records Roll Drauf authorship and is not falsely attributed to the
  SRD.
- Product terms must not claim exclusive rights over the CC-licensed SRD material or prohibit uses
  that CC BY permits.

## 12. Program and milestone plan

The milestone program is defined in:

`docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md`

Every milestone performs its own Discover → Apply → Deploy → Monitor cycle. The current document
defines the program contract; it does not authorize all milestones as one unreviewed deployment.

## 13. Global acceptance criteria

The project is complete only when all of the following are true:

- `/regelwerk` is a first-class tab across the VTT's principal navigation surfaces.
- The active package identifies itself as German SRD 5.2.1 and exposes stable versioned URLs.
- Every official table-of-contents entry and source page is accounted for in the coverage report.
- Every published document passes schema validation and digest verification.
- Every SRD-derived document has source pages and modification status.
- The exact required attribution and license links are visible on the website and in print output.
- No non-SRD Wizards content, official artwork, logos, or D&D Beyond UI is present.
- Search finds representative rules from every top-level corpus partition.
- Direct links to documents and rule IDs survive reload, anonymous access, and navigation from the
  character sheet and play workspace.
- Rule text renders safely without arbitrary content HTML or script execution.
- Keyboard, narrow-screen, reduced-motion, heading-order, table, and print checks pass.
- A source-fidelity review samples every document and fully checks high-risk numeric tables, class
  progressions, spell data, item data, and stat blocks.
- A representative character-sheet feature, spell, equipment entry, condition, and action resolve
  to the correct Regelwerk rule ID.
- The preview label is removed only after full corpus, legal, fidelity, and regression approval.
- The previous published package can be reactivated without deleting content or changing its
  versioned URLs.

## 14. Verification strategy

Planned evidence includes:

- JSON schema and canonical-digest tests;
- manifest/document/reference integrity tests;
- source-page and table-of-contents coverage reports;
- duplicate and unstable rule-ID checks;
- forbidden arbitrary-markup tests;
- attribution and modification-notice tests;
- route, ETag, cache, anonymous-access, and 404 tests;
- search-index determinism and representative query fixtures;
- Book Scene navigation contract tests;
- browser tests for deep links, keyboard navigation, responsive layout, and print view;
- source-fidelity review checklists signed per page range; and
- final authenticated and anonymous user walkthroughs.

Automated tests prove structure and rendering. They do not replace human comparison against the
official PDF.

## 15. Rollout and rollback

1. Add the content package and reader behind `REGELWERK_PREVIEW`.
2. Expose the tab only to approved preview users while the corpus is incomplete.
3. Keep every preview page visibly labelled with package status and coverage.
4. Complete and monitor each content milestone independently.
5. When the global criteria pass, publish an immutable package version and configure it as
   `main`.
6. Enable Regelwerk for all users and anonymous deep links.
7. If a defect is found, reactivate the previous published package or disable the reader flag;
   never mutate or delete the defective published version.

Rollout never changes active character mechanics. The first release is authoritative reference
content and navigation, not an automatic rules-engine cutover.

## 16. Risks, assumptions, and tradeoffs

| ID | Severity | Status | Finding and treatment |
| --- | --- | --- | --- |
| R1 | high | accepted and mitigated | Non-SRD contamination would create the largest legal risk. The source allowlist contains only the digest-pinned German SRD; source pages and human review are mandatory. This implements the product owner's stated SRD-first risk acceptance. |
| R2 | medium | resolved in design | A 412-page corpus is too large for one deployment. The milestone program partitions it by official sections and requires independent phase gates. |
| R3 | medium | resolved in design | OCR can alter numbers, symbols, tables, and German characters. Extraction is never authoritative; source-page review and high-risk full checks are mandatory. |
| R4 | medium | resolved in design | Rule prose and executable mechanics could diverge. Stable references, separate revision identities, and conformance fixtures make that mismatch explicit. |
| R5 | medium | resolved in design | A Markdown/HTML pipeline would introduce parser and injection choices. Semantic JSON and renderer-owned markup avoid a new runtime dependency and arbitrary HTML. |
| R6 | medium | resolved in design | Edition mixing would be hard to detect. Package identity and reference resolution are edition-scoped and never fall back across editions. |
| R7 | low | open | The named human acceptance owner and source-fidelity reviewers must be recorded before the first corpus publication. This does not block the initial Deploy foundation, but it blocks `published` status. |
| A1 | low | accepted | German is the canonical initial locale. English or other localized packages are separate future work. |
| A2 | low | accepted | The official German SRD's terminology is retained even when existing Roll Drauf Light uses different vocabulary. Roll Drauf content must map explicitly. |
| A3 | low | accepted | Public read-only access is appropriate because the corpus contains no private data and is intentionally CC-licensed. |

No unresolved medium-or-higher finding remains in the Apply design.

## 17. Deploy handoff

After human approval of plan version 1, Deploy begins only with milestone R0 from the program:

- create the source/rights lock and content schemas;
- add the exact attribution artifact from the official PDF;
- add validation and coverage tooling/tests;
- do not yet publish the full reader or transcribe later sections; and
- preserve all unrelated dirty-tree work.

R1 may begin only after R0 Monitor confirms the source digest, attribution rendering contract,
schema validation, and package immutability rules.

## 18. Artifacts

- This Apply design: retention class `versioned`; approval freezes version 1.
- `docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md`: retention class
  `versioned`; approval freezes version 1.
- Official German SRD 5.2.1 PDF identified above: external normative source, digest-pinned.

## 19. Next step

Human review and approval of plan version 1. On approval, create an append-only decision/approval
record and enter R0 Deploy. No production implementation is authorized by this Apply artifact
alone.
