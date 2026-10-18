# DAD-M Discover: German SRD 5.2.1 Regelwerk — R1 Reader Vertical Slice

date: 2026-10-15
status: complete — safe boundary established for R1 Apply
phase: Discover
milestone: R1 — Regelwerk reader vertical slice
program: `docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md`
predecessor: `docs/DADM_MONITOR_REGELWERK_SRD_5_2_1_R0_2026-10-15.md`

## Input summary

The approved program asks R1 to prove one reviewed German SRD 5.2.1 section end to end: checked-in
semantic source, generated navigation/search/coverage artifacts, public reader and API routes,
stable rule deep links, visible attribution, a Regelwerk entry on the VTT's main navigation
surfaces, and accessible screen/print behavior. The rules corpus must remain preview and must not
change executable character mechanics.

This pass is read-only research. It inventories the existing Flask route ownership, Book Scene
navigation, configuration and test conventions, the R0 content contract, the dirty-worktree
overlap, and representative source material. It does not select an implementation architecture or
modify the reader/navigation runtime.

## Current-state summary

- R0 is complete and monitored. The source-lock, attribution, package/document schemas, semantic
  block vocabulary, deterministic digests, coverage model, validator, and negative tests exist.
- There is no Regelwerk page, route blueprint, preview flag, generated reader artifact, or
  Regelwerk navigation entry today.
- Flask's final catch-all serves extensionless top-level templates, so a future `regelwerk.html`
  would make `/regelwerk` reachable. Nested stable document paths do not map to a template and
  currently fall through to `login.html`; they require explicit ownership before the catch-all.
- Existing Book Scene pages are protected-route experiences. The approved Regelwerk reader has a
  different contract: both anonymous and authenticated reads must work.
- Navigation is not centralized in one template. Book Scene generates the main ribbon and table of
  contents in JavaScript, while Play, character sheet, Creation Engine, and advanced authoring have
  additional hard-coded navigation surfaces.
- `vtt/static/js/book-scene.js` already contains unrelated, uncommitted session-calendar work. The
  R1 navigation area itself is unchanged, but the same file is dirty and therefore requires a
  surgical additive edit plus diff-specific verification in Deploy.
- The official PDF's extractable text contains column-order, line-break, soft-hyphen, and control
  character artifacts. Raw PDF extraction is not reliable enough to become canonical content
  without visual comparison.
- R0 currently derives `covered_pages` directly from every document's `sourcePages`. A document
  that covers one section spanning only parts of shared pages would therefore overstate those
  pages as complete. R1 needs to separate provenance (pages touched) from reviewed whole-page
  completeness before adding the vertical slice.

## Relevant inventory

### R0 source and content boundary

| Artifact | Current responsibility | R1 relevance |
| --- | --- | --- |
| `vtt/rules_content/source-locks.json` | External trust anchor for source and attribution digests | R1 must not alter the pinned official source identity |
| `vtt/rules_content/srd-5.2.1-de/manifest.json` | Draft package metadata, page inventory, document list | R1 adds only the reviewed slice and keeps package status `draft` |
| `vtt/rules_content/srd-5.2.1-de/attribution.txt` | Exact German attribution notice | Must be visible from the reader/license surface |
| `vtt/rules_content/schemas/regelwerk-package-v1.schema.json` | Closed package contract | R1 document registration must continue to validate |
| `vtt/rules_content/schemas/regelwerk-document-v1.schema.json` | Closed semantic document/block contract | Reader must render data, not content-controlled HTML |
| `vtt/rules_content/validator.py` | Schema, provenance, digest, rule-ID, reference, markup, and coverage checks | R1 generation must preserve all R0 checks |
| `tools/validate_regelwerk.py` | Direct/module CLI validation entry point | Natural verification entry point for generated R1 artifacts |
| `tests/test_regelwerk_package.py` | Fourteen R0 contract/security tests | Must stay green and gain slice/generation coverage |

The pinned official source remains `DE_SRD_CC_v5.2.1.pdf`, SHA-256
`f06989dcdf98c8e93b52ba5ea9db52d5e1b054d6d87a148ff295138bafe8a65b`. Required page coverage
is printed pages 5–412; pages 1–4 are represented by the legal artifact and generated navigation.

### Flask and public-route ownership

| Location | Fact |
| --- | --- |
| `vtt/__init__.py` app factory | Registers feature blueprints before the final catch-all and is the existing composition root |
| `vtt/__init__.py` `/<path:path>` | Serves `/static/*`, returns JSON 404 for unmatched `/api/*`, serves existing `.html` templates and top-level extensionless templates, otherwise returns `login.html` as a soft 404 |
| `vtt/config.py` | Uses environment-backed booleans for opt-in features; no `REGELWERK_PREVIEW` setting exists |
| Existing endpoints | Protected APIs normally use private/no-store behavior; no immutable public content API convention was found |
| `tests/conftest.py` and route suites | `create_app(config_name="testing")` plus Flask client is the established route-test seam |

Consequences for Apply: `/regelwerk` cannot rely solely on the catch-all if disabled/preview behavior
must be explicit, and `/regelwerk/<version>/<locale>/<slug>` needs a registered route. Public JSON
responses need their cache/error contract stated rather than copied from protected APIs.

### Navigation and Book Scene ownership

| Surface | Current owner | Current entries relevant to R1 |
| --- | --- | --- |
| Dashboard/campaigns/characters Book Scene ribbon | `vtt/static/js/book-scene.js::buildRibbon` | Übersicht, Kampagnen, Charaktere, Creation Engine, Spieltisch, Abmelden |
| Dashboard contents page | `vtt/static/js/book-scene.js::buildHomeOverview` | Übersicht, Kampagnen, Charaktere, Spieltisch, Creation Engine |
| Book route metadata/order | `vtt/static/js/book-scene.js` | Login, signup/register, dashboard, campaigns, characters, character sheet; no public rules route |
| Character sheet ribbon | `vtt/templates/character-sheet.html` | Separate hard-coded Book Scene-style navigation |
| Play ribbon and app menu | `vtt/templates/play.html` | Separate hard-coded ribbon and mobile/app-menu entry set |
| Creation Engine | `vtt/templates/creation-engine.html` | Separate hard-coded ribbon |
| Advanced authoring | `vtt/templates/creation-advanced.html` | Minimal separate navigation |

`BookScene.bootstrapProtectedRoute()` owns authentication and protected-page initialization; a
public reader cannot inherit that bootstrap requirement. `BookScene.pageTurn()` handles existing
protected route transitions. A plain stable Regelwerk link can coexist with this system, but its
exact shared-navigation behavior belongs in Apply.

The uncommitted `book-scene.js` delta is limited to session selection, session-calendar mounting,
root-scoped event binding, and a cancelled-session state. It does not currently edit `routeMeta`,
`routeOrder`, `buildRibbon`, or the table-of-contents entries. This makes conflict avoidance
possible, but R1 Deploy must preserve those hunks byte-for-byte outside its explicit additions.

### Presentation and verification seams

- Shared visual foundations already exist in `vtt/static/css/components.css`,
  `vtt/static/css/book-page.css`, and `vtt/static/css/book-scene.css`.
- Existing pages load Book Scene through route-specific templates rather than a server-rendered
  layout engine.
- `tests/test_core_book_runtime_routes.py` pins Book Scene route ownership.
- `tests/test_book_scene_layout_contract.py` pins source-level layout/runtime invariants.
- `tests/test_creation_engine_navigation.py` demonstrates Flask-server + Playwright testing for
  desktop/mobile, keyboard entry, disabled capability state, page-turn navigation, and return
  boundaries.
- `tests/test_public_surface_and_playtable_contract.py` demonstrates anonymous page contracts.
- The test environment already supports pytest and optional Playwright Chromium; R1 does not need
  a new runtime dependency for its required route/browser tests.

### Representative official-source material

The early `Die Spielregeln` chapter provides candidate material that exercises more than plain
paragraph rendering. Printed pages 6–8 contain the `W20-Prüfungen` section, including a process
sequence, modifier lists, multiple tables, explanatory prose, exception-like notes, and stable
subheadings. It starts after the ability-score material and ends before the following
`Vorteil und Nachteil` section. This is evidence that one compact slice can exercise the R0 block
vocabulary, table rendering, search, and deep links; Apply must formally select and bound the R1
slice.

Automated extraction from these pages is visibly unsuitable as final source: hyphenation and
multi-column order are inconsistent and at least one word boundary is represented by a control
character. R1 transcription therefore needs a visual page-by-page comparison, not only text
extraction.

## Dependencies and external constraints

- Program dependency: R0 Monitor is complete; R1 may proceed.
- Source dependency: the digest-pinned official German SRD 5.2.1 PDF under CC BY 4.0.
- Runtime dependency: existing Flask/static JavaScript stack and existing `jsonschema`/
  canonical-JSON support; no dependency change is required by the discovered boundary.
- Accessibility dependency: semantic renderer output, keyboard-operable search/TOC, reduced-motion
  compatibility with Book Scene styling, narrow viewport behavior, and print CSS.
- Licensing constraint: attribution must be visible and linked from the reader; package status
  stays draft/preview.
- Product constraint: this milestone displays reference rules only and does not activate or alter
  character-sheet calculations, species, classes, or roll automation.

## Risks and assumptions

| Severity | Finding | Evidence / treatment before Deploy |
| --- | --- | --- |
| medium — resolved for transition | Dirty shared navigation file could overwrite unrelated session-calendar work | The exact existing diff is inventoried; Apply must define additive edit locations and Deploy must verify the unrelated hunks remain present |
| medium — resolved for transition | Public reader contract differs from protected Book Scene bootstrap | Apply must assign explicit public route/API ownership and must not call `bootstrapProtectedRoute()` for reader access |
| medium — resolved for transition | Preview flag can create visible links to disabled routes or expose unfinished content unintentionally | Apply must define page, API, and all navigation states together, including testing defaults and anonymous behavior |
| medium — resolved for transition | PDF text extraction can corrupt canonical prose and tables | Apply/Deploy must require visual source comparison and recorded page-level fidelity evidence for the selected slice |
| medium — resolved for transition | `sourcePages` currently conflates provenance with complete-page coverage | Apply must separate represented pages from explicitly reviewed complete pages; partial-page R1 content must not reduce the missing-page inventory |
| medium — resolved for transition | Nested stable URLs currently soft-fall through to login | Apply must give versioned rules paths explicit route ownership and test unknown document/version behavior |
| low | Navigation is duplicated across several surfaces and can drift | R1 acceptance must enumerate every main navigation surface and test each entry |
| low | A one-document preview has limited search data | Search still needs a deterministic interface and fixture result so later corpus growth does not replace its contract |
| low | Content rendering could regress into unsafe HTML interpolation | R0's closed schema/markup rejection remains mandatory; browser tests must prove text is escaped |
| low | Generated navigation/search/coverage files can drift from source JSON | Apply must specify one deterministic generator/verification command and checked-in output ownership |

No critical finding, high security/privacy finding, dependency change, or cross-milestone expansion
was found. Each medium item has a bounded design requirement, so no human-decision trigger fires.

## Assumptions carried into Apply

- R1's program acceptance criterion that anonymous reads work is authoritative for the vertical
  slice. The preview flag gates whether the deployment exposes the slice; when enabled, the
  reader itself is public rather than user-allowlisted.
- The checked-in semantic JSON remains the canonical authored source. Generated indexes and
  rendered HTML are derived and replaceable.
- One visually reviewed core-rules section is sufficient for R1; complete `Die Spielregeln`
  coverage remains R2.
- Rule references to documents that do not yet exist will not be fabricated merely to make the
  preview appear complete.

## Open questions for R1 Apply

1. Which exact printed-page and heading boundary should be the single R1 slice?
2. What are the precise public page/API URLs, response/cache contracts, and disabled/unknown
   behavior?
3. How will one preview-availability state drive both public routes and every duplicated navigation
   surface without a broken or misleading tab?
4. Which generated files are checked in, what fields do they contain, and which command proves
   reproducibility?
5. How will stable rule anchors, browser history, search selection, print mode, and license access
   behave in the public shell?
6. What exact source-fidelity checklist and evidence are required for the selected pages?
7. How will the coverage contract distinguish source pages touched by a document from pages whose
   entire relevant source content has been reviewed?

These are bounded design questions with clear evaluation criteria; none requires product-owner
intervention before Apply.

## Artifacts

| Artifact | Retention | Purpose |
| --- | --- | --- |
| This Discover record | permanent | Immutable R1 current-state and risk boundary after transition |
| R0 package/schemas/validator/tests | permanent | Approved predecessor contract; not reinterpreted by R1 |
| Existing dirty-worktree inventory | transient evidence summarized here | Conflict-avoidance input for R1 Apply/Deploy |
| PDF extraction observations | transient evidence summarized here | Establishes visual-review requirement; extraction is not canonical content |

## Next step

Enter R1 Apply. Select and bound the representative section; define the public route/API and
preview-state contracts, deterministic generated artifacts, safe renderer, Book Scene/tab
integration, source-review protocol, file boundary, and acceptance matrix. Do not implement until
that Apply output is complete and has no unresolved medium-or-higher finding.
