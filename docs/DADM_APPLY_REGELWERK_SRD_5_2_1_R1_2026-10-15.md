# DAD-M Apply: German SRD 5.2.1 Regelwerk — R1 Reader Vertical Slice

date: 2026-10-15
status: complete — implementation-ready; R1 Deploy authorized by the approved program
phase: Apply
milestone: R1 — Regelwerk reader vertical slice
program: `docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md`
input: `docs/DADM_DISCOVER_REGELWERK_SRD_5_2_1_R1_2026-10-15.md`

## Design summary

R1 will publish an explicitly labelled public preview reader at `/regelwerk`, backed only by the
validated checked-in German SRD package. The vertical slice is the official `W20-Prüfungen`
section from printed source pages 6–8. It is transcribed verbatim into the existing semantic JSON
vocabulary, visually reviewed against the pinned PDF, generated into deterministic navigation,
search, and coverage artifacts, and served through a small read-only Flask blueprint.

The reader is a public Book Scene-styled chapter, not a protected `BookScene` route. It renders
semantic blocks with DOM text nodes, exposes stable rule anchors and reloadable URLs, includes a
license view and print mode, and displays a persistent `Vorschau` state. A shared availability
probe hydrates Regelwerk entries across logged-out, protected-book, character-sheet, Creation
Engine, and play navigation without coupling public reads to authentication.

The design also corrects R0's coverage ambiguity: document `sourcePages` records provenance
(`representedPages`), while a new manifest `reviewedPageRanges` ledger alone records pages whose
entire relevant source content has been reviewed (`coveredPages`). The partial-page R1 slice
represents pages 6–8 but claims no complete-page coverage.

## Solution boundary

### In scope

- one `W20-Prüfungen` semantic document, including its headings, process, modifiers, tables,
  checks, saving throws, attack rolls, and natural 20/1 rules present before the next section;
- R0 coverage-contract hardening for partial-page provenance;
- deterministic checked-in `navigation.json`, `search-index.json`, and `coverage.json`;
- public preview flag and public read-only routes/APIs;
- `/regelwerk`, stable versioned document URLs, license view, search, TOC, anchors, print styles;
- Regelwerk navigation entry on the established main surfaces;
- source review, unit/route/browser/accessibility/security/regression evidence.

### Out of scope

- any other SRD chapter or completion claim for pages 5–21;
- executable dice, character, class, species, spell, equipment, or automation rules;
- D&D Beyond import/export or browser-extension behavior;
- a database model, CMS, authoring UI, full-text-search service, fuzzy search, or new dependency;
- activation as the published main package; package status remains `preview`;
- independent human source sign-off, which is required before final publication but not before
  this explicitly labelled engineering preview.

## Selected content slice and fidelity contract

### Boundary

- Document ID: `core.d20-tests`
- Slug: `w20-pruefungen`
- Title: `W20-Prüfungen`
- Navigation: `Die Spielregeln` → `W20-Prüfungen`
- Printed source pages: 6, 7, 8
- Content status: `verbatim`
- Stable URL: `/regelwerk/5.2.1/de/w20-pruefungen`
- First included heading: `W20-Prüfungen`
- Last included rule: the natural-20/natural-1 rule for attack rolls immediately before
  `Vorteil und Nachteil`
- Excluded adjacent content: ability-score material before the heading and `Vorteil und Nachteil`
  onward

This boundary deliberately exercises headings, paragraphs, ordered/unordered lists, definition-like
material, tables, and rule callouts without borrowing incomplete neighboring sections.

### Fidelity procedure

1. Use text extraction only as a transcription aid.
2. Compare every block visually against printed pages 6–8 in the digest-pinned PDF.
3. Resolve soft hyphens, line-wrap hyphens, ligatures, column order, and control characters from the
   visual page, never by guessing from extracted bytes.
4. Compare every number, die notation, operator, table cell, bold-label boundary, exception, and
   cross-reference phrase.
5. Record included/excluded boundaries, block IDs, table dimensions, discrepancies corrected, and
   reviewer status in `docs/reviews/REGELWERK_R1_W20_SOURCE_REVIEW_2026-10-15.md`.
6. Do not mark any page fully reviewed in the coverage ledger because this document includes only
   part of pages 6 and 8 and does not establish complete adjacent-page accounting.

## Authored and generated data contracts

### Coverage correction

The package schema gains required `coverage.reviewedPageRanges`, using the existing page-range
shape. For the R1 package it is `[]`.

- `document.sourcePages`: sorted provenance pages on which any included text appears.
- `representedPages`: union of all `document.sourcePages`; informational only.
- `coveredPages`: expansion of `manifest.coverage.reviewedPageRanges`; publication completeness
  input.
- `reviewedPageRanges` must be inside required pages and every reviewed page must also be
  represented by at least one document.
- `missingPages`: required pages minus `coveredPages`.
- top-level section completion continues to require every page in its range to be in
  `coveredPages`.
- `published` and `retired` packages still fail unless `coveredPages` is complete.

The wire coverage report keeps `coveredPages` for compatibility but changes its implementation to
the explicit review ledger and adds `representedPages`. R0 tests are updated to pin the distinction,
including a partial-page false-completeness regression.

### Authored document

`vtt/rules_content/srd-5.2.1-de/documents/core.d20-tests.json` follows
`regelwerk.document.v1`. Rule IDs are rooted under `core.d20-tests`; each rendered block receives
one stable ID. Content carries no HTML. References to not-yet-authored rules remain plain source
text and are not added as unresolved `ruleRefs`.

The manifest changes to:

- package version `0.1.0-r1`;
- status `preview`;
- one document inventory entry with matching digest;
- empty `reviewedPageRanges`.

### Generated artifacts

`tools/build_regelwerk.py` owns deterministic generation and supports:

```text
python tools/build_regelwerk.py
python tools/build_regelwerk.py --check
```

Default mode writes canonical UTF-8 JSON with sorted keys and a trailing newline. `--check` makes
no writes and fails if any checked-in artifact differs. Generation first calls package validation
and writes:

- `generated/navigation.json`: schema marker, ruleset/package identity, status, title, ordered
  section/document nodes, document URLs, and license URL;
- `generated/search-index.json`: schema marker, package digest, deterministic normalized entries
  keyed by document/rule ID with title, heading path, searchable text, and stable URL;
- `generated/coverage.json`: the validator's exact coverage wire report, including represented,
  covered, and missing pages/sections.

Search normalization is locale-independent lowercase/casefold-style Unicode text plus collapsed
whitespace. The checked-in index contains source text needed for matching and snippets, but never
HTML. Document order, block order, and stable IDs break score ties deterministically.

## Runtime interfaces

### Preview configuration

`REGELWERK_PREVIEW` is an environment-backed boolean:

- base/production default: `false`;
- development default: inherited base unless set in the environment;
- testing default: `false`, with tests enabling it explicitly.

When disabled, content page/API routes return explicit 404 responses and every hydrated Regelwerk
navigation placeholder stays hidden. The availability endpoint remains callable so shared
navigation can determine that state without authentication.

### Public endpoints

All endpoints are GET/HEAD only and require no cookie or JWT.

| Route | Enabled response | Disabled / unknown response | Cache contract |
| --- | --- | --- | --- |
| `/api/rulesets/main` | `200` availability/identity summary | always `200`, `{available:false}` when off | `public, max-age=60`; ETag; `Vary` absent |
| `/api/rulesets/srd-5.2.1-de/manifest` | `200` generated public manifest/navigation summary | JSON `404` | `public, max-age=60`; package ETag |
| `/api/rulesets/srd-5.2.1-de/documents/<document_id>` | `200` semantic document | JSON `404` | `public, max-age=60`; document ETag |
| `/api/rulesets/srd-5.2.1-de/search?q=<text>` | `200` deterministic result list | JSON `404` if disabled/ruleset unknown; `400` if over 100 chars | `public, max-age=60`; query-specific ETag |
| `/api/rulesets/srd-5.2.1-de/license` | `200` license metadata and exact attribution text | JSON `404` | `public, max-age=60`; attribution ETag |

`/api/rulesets/main` enabled payload:

```json
{
  "available": true,
  "rulesetId": "srd-5.2.1-de",
  "rulesetVersion": "0.1.0-r1",
  "sourceVersion": "5.2.1",
  "locale": "de-DE",
  "status": "preview",
  "title": "Roll Drauf Regelwerk — SRD 5.2.1 (Deutsch)",
  "readerUrl": "/regelwerk"
}
```

Search response:

```json
{
  "query": "Angriffswurf",
  "results": [
    {
      "documentId": "core.d20-tests",
      "ruleId": "core.d20-tests.attack-rolls",
      "title": "W20-Prüfungen",
      "heading": "Angriffswürfe",
      "snippet": "…",
      "url": "/regelwerk/5.2.1/de/w20-pruefungen#core.d20-tests.attack-rolls"
    }
  ]
}
```

Search accepts empty/one-character queries and returns an empty result list. It returns at most 20
results. Error bodies use `{"error":"not found"}` or a concise validation message. Conditional
requests with a matching `If-None-Match` return `304`.

### Public page routes

| Route | Behavior |
| --- | --- |
| `/regelwerk` | Reader shell; loads the first navigation document and labels it Vorschau |
| `/regelwerk/5.2.1/de/w20-pruefungen` | Same shell with the stable document selected |
| `/regelwerk/lizenz` | Same shell in license mode with attribution visible |

When disabled, or when a version/locale/slug is unknown, these explicit routes return a real HTTP
404 and never fall through to `login.html`. `/regelwerk` stays the canonical product destination;
the versioned path is the canonical citation/deep-link destination for the slice.

## Reader behavior and safety

- Static shell: `vtt/templates/regelwerk.html`.
- Runtime: `vtt/static/js/regelwerk-reader.js`.
- Styles: `vtt/static/css/regelwerk.css`, layered on the shared Book Scene/page component CSS.
- The shell contains a skip link, site ribbon, preview banner, search form/status, TOC nav, article,
  source/license footer, and print control.
- The JS determines route mode from `location.pathname`, fetches public APIs, renders blocks with
  `createElement` and `textContent`, and never assigns authored content to `innerHTML`.
- Every block receives `id=<ruleId>` and `tabindex="-1"`; on load/hash change the target is focused
  without animation and scrolled into view.
- Search submission renders keyboard-focusable results; selecting one navigates to its stable URL.
- Back/forward navigation restores route and hash state without authentication.
- Tables use captions, header cells, a horizontally scrollable wrapper on narrow screens, and
  remain readable in print.
- `prefers-reduced-motion: reduce` disables nonessential transitions. The page does not depend on
  Book Scene page-turn animation.
- Print CSS removes navigation/search controls, expands content/tables, preserves the title,
  preview/source note, and attribution/link.
- Errors and empty states are text, announced through an `aria-live` status node, and never reveal
  filesystem paths.

## Shared navigation contract

`vtt/static/js/regelwerk-navigation.js` exposes one idempotent
`RegelwerkNavigation.hydrate(root=document)` function. It makes one memoized anonymous request to
`/api/rulesets/main` and handles elements marked `data-regelwerk-nav`:

- unavailable/network failure: leave the placeholder hidden and non-navigable;
- available: set `href="/regelwerk"`, remove `hidden`, set `aria-disabled="false"`, and use label
  `Regelwerk · Vorschau`;
- current reader page: static shell marks its own entry active with `aria-current="page"`.

Placeholders and the shared script are added to:

- generated Book Scene ribbon and dashboard table of contents;
- login, signup, and registration ribbons;
- character-sheet ribbon;
- Creation Engine and advanced-authoring navigation;
- Play desktop ribbon and app menu.

Book Scene adds only placeholder markup and calls the hydrator after scene rendering. It does not
add Regelwerk to `routeMeta`, `routeOrder`, or `pageTurn`; navigation is a normal public anchor.
The Deploy diff must leave the existing session-calendar hunks intact. All template placeholders
start `hidden` so disabled/no-JS deployments do not expose a dead link.

## File ownership and planned changes

### New

- `vtt/rules_content/generator.py`
- `tools/build_regelwerk.py`
- `vtt/rules_content/srd-5.2.1-de/documents/core.d20-tests.json`
- `vtt/rules_content/srd-5.2.1-de/generated/{navigation,search-index,coverage}.json`
- `vtt/rules.py`
- `vtt/templates/regelwerk.html`
- `vtt/static/js/regelwerk-reader.js`
- `vtt/static/js/regelwerk-navigation.js`
- `vtt/static/css/regelwerk.css`
- `tests/test_regelwerk_reader.py`
- `tests/test_regelwerk_browser.py`
- `docs/reviews/REGELWERK_R1_W20_SOURCE_REVIEW_2026-10-15.md`
- R1 Deploy and Monitor records

### Modified

- R0 package manifest/schema/validator/export and package tests for honest coverage;
- `vtt/config.py` for the preview flag;
- `vtt/__init__.py` to register the public rules blueprint before the catch-all;
- `vtt/static/js/book-scene.js` only at the ribbon, contents, and hydration seams;
- navigation-bearing templates listed above only for hidden placeholders/script loading;
- program decision log/status after phase closure.

No model, migration, database, dependency lock, character calculation, play protocol, or Creation
Engine rule contract changes.

## Implementation sequence

1. Correct and test provenance-versus-reviewed coverage semantics.
2. Transcribe/review the selected document and register its digest in the preview manifest.
3. Build the deterministic generator, write artifacts, and prove `--check` reproducibility.
4. Add the flag, read-only blueprint, explicit page/API errors, ETags, and route tests.
5. Add the safe reader shell/runtime/styles and direct-link/search/license behavior.
6. Add shared hidden navigation placeholders and hydrator, preserving the dirty Book Scene hunks.
7. Run focused Python, source-contract, Playwright, generation, whitespace, and diff-overlap checks.
8. Record Deploy evidence; then enter Monitor for acceptance/regression review.

## Acceptance criteria

### Content and integrity

- [ ] The package validates as `preview`, with exactly one registered document and matching
      manifest/document digest.
- [ ] Source pages 6–8 are `representedPages` but not `coveredPages`; all required pages remain
      missing and no section is falsely complete.
- [ ] The source-review record accounts for every included heading/block/table and notes the exact
      adjacent exclusions.
- [ ] `build_regelwerk.py --check` passes after a clean generation and detects modified output.
- [ ] Existing arbitrary-HTML, edition, provenance, reference, and immutability tests remain green.

### Public API and routes

- [ ] Anonymous and authenticated clients receive identical enabled reader/document content.
- [ ] Disabled content routes are real 404s; availability returns `available:false`; nav stays
      hidden.
- [ ] Manifest/document/search/license responses have correct public cache headers and ETags;
      matching conditional requests return 304.
- [ ] Unknown version, locale, slug, document, and ruleset return real page/JSON 404s rather than
      the login soft fallback.
- [ ] Search for at least `W20` and `Angriffswurf` resolves the intended stable rule.

### Reader and navigation

- [ ] `/regelwerk`, the stable document URL, and the license route work anonymously.
- [ ] A rule hash survives full reload and leaves focus on the matching semantic block.
- [ ] Authored `<script>`/HTML-like text cannot become an element or execute.
- [ ] Desktop and 390px layouts expose usable TOC, content, tables, search, source, and license.
- [ ] Keyboard-only search/result/deep-link flow works and has visible focus.
- [ ] Reduced-motion mode performs no page-turn/scroll animation.
- [ ] Print mode omits interactive chrome and retains title, content, preview/source notice, and
      attribution.
- [ ] Enabled Regelwerk entries appear and navigate correctly on every enumerated navigation
      surface; disabled entries are hidden.

### Regression and worktree safety

- [ ] R0 package tests, Book Scene route/layout tests, Creation Engine navigation tests, and public
      surface contracts remain green.
- [ ] The pre-existing session-calendar hunks in `book-scene.js` remain present and no unrelated
      dirty file is changed by R1.
- [ ] No database schema, dependency, executable character mechanic, or play event changes.

## Risks and tradeoffs

| Severity | Decision / tradeoff | Resolution |
| --- | --- | --- |
| medium → low | Correcting R0 coverage semantics changes the meaning of `coveredPages` | Preserve the wire field, add `representedPages`, require the explicit reviewed ledger, and pin both meanings in regression tests |
| medium → low | One public availability probe adds a request on navigation surfaces | Cache for 60 seconds and memoize per page; it avoids leaking auth state or hard-coding server configuration into every static template |
| medium → low | Exact prose can be corrupted by PDF extraction | Visual block/table review is an acceptance gate; extraction never becomes canonical automatically |
| medium → low | Dirty Book Scene file is shared with session-calendar work | Limit edits to three named seams and compare the resulting diff against the inventoried pre-R1 hunks |
| low | Preview package routes are versioned but may still change before publication | Short cache lifetime and ETags; any later reviewed content change updates document/package digests and package version |
| low | Search is intentionally simple | Deterministic substring/token matching satisfies the slice and provides a stable contract for later corpus milestones |

No medium-or-higher risk remains unresolved. No dependency or cross-milestone scope change is
required, and no human-decision trigger fires.

## Artifacts

| Artifact | Retention | Purpose |
| --- | --- | --- |
| This Apply record | permanent | Immutable R1 implementation contract after Deploy begins |
| R1 Discover record | permanent | Evidence and constraints feeding this design |
| Generated artifact schemas described here | permanent contract, derived files replaceable | Defines public reader data without making generated output canonical |
| Source-review checklist | permanent | Fidelity evidence for the selected official pages |

## Explicit Deploy handoff

R1 Deploy is authorized under the product owner's approved program and completed R0 Monitor. Deploy
must implement only this boundary, in the sequence above. If exact source inspection reveals an
ambiguous rule/table value, if a new dependency becomes necessary, if explicit public routing
cannot coexist with the catch-all, or if preserving the session-calendar changes requires a
broader Book Scene rewrite, stop and return to Apply or a human decision rather than improvising.
