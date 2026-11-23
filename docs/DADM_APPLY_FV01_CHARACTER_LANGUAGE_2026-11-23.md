# Apply FV01 character module language

Status: detailed read-only Claude design received; Codex review below defines the implementation handoff and corrections. Base `44fa2da96`; no FV01 application changes yet. Retention permanent. Source: the confirmed November 23 language matrix and the full-version goal. Independent map-layer work remains separate.

## Codex integration decisions

- Preserve the canonical German mechanical model and every logic discriminator. Use ID-keyed presentation overlays and a module-scoped translator, including creator, editor/progression/inventory, details and authored validation. Do not mutate the site-wide UI locale.
- Matching fingerprints are candidate discovery only. A unique fingerprint is not proof that two rules are semantically identical. Review/pin cross-language identities against their actual entries and require validated coverage. German fallback may keep a partially delivered slice usable during development; it does not satisfy FV01's through-English acceptance without an explicit owner scope decision.
- Correct the proposed probe: use the actual German name attached to `classes.warlock.invocation-agonizing-blast` from the compendium, not the different Eldritch Blast spell name. Generated tests must obtain the reference ID/name from the real data.
- Units retain their existing independent preference. No additional owner confirmation is required for preserving it.
- Include character-specific shared read views in presentation consistency. Party/campaign lists retain their surrounding site locale. Inspect stored inventory naming first: user-renamed names and authored homebrew text stay unchanged; canonical rule references can determine unmodified display names without migrating stored characters.
- Resolve translated error templates by stable code and structured parameters, not generic string replacement on user text. Preserve quoted source evidence and numerical results. Reuse the current authenticated rule-entry endpoints and all current permissions.
- Shared display-preferences changes are coordinated by Codex; no FV03 worker owns that file now. No new dependency is proposed.
- FV01 remains open until the full creator/editor matrix, all required label collections, API errors and rule dialogs have genuine coverage and live proof. A creator-only slice is progress, not packet completion.

## Claude source design

Codex inventory follow-up: the [reproducible spell candidate scan](proofs/full-version-layers-2026-11-23/fv01-inventory.py) uses the actual eight German school labels and validates class labels against each locale's class entries. All 339 spells have facet-compatible candidates: 310 single candidates and 29 ambiguous cases. Every result remains `identity_approved: false`; this evidence sizes the mapping work and does not authorize automatic name or rule substitution.

# FV01 Apply: character module language (rules locale scoped to the creator and editor)

This plan was built from read-only inspection at `44fa2da96`. I ran no tests and changed no files. I didn't look at any mapmaker files.

## 1. Facts the design relies on

- **German is hard-wired today.**
  - `creator_rules.py:17`: `PACKAGE_DIR = …"srd-5.2.1-de"`, and `load_creator_data()` at line 27 takes no locale.
  - `srd_creator.py:113-118` serves `/creator-data` with no locale.
  - These four places all call the DE compendium directly: `srd-creator.js:7` (`COMP`), `srd-rule-preview.js:7`, `character-sheet.html:1853-1855`.
- **One translator for the whole page.** `display-preferences.js:30-47` binds `t`/`literal`/`translate` to a single `language` constant, which is the site UI locale. `apply()` at line 77 and the MutationObserver at line 219 re-translate the entire document. `contentLocale()` (line 92) already resolves `auto`, `de` or `en`.
- **Client logic matches on German display strings.** This rules out translating names inside creator-data:
  - `srd-creator-steps.js:573` matches `f.name === bg.feat`
  - `srd-creator-steps.js:81` and `srd-progression-ui.js:606` match `p.name` against `requiresProperty`
  - `srd-creator-random.js:82` matches `'Epische-Gabe-Talent'`
  - `creator_data.py:937` uses `"category": "Herkunftstalent"`; line 1137 uses `"column": "Ungerüstete Bewegung"`
- **Hard-coded German that never goes through the catalog:**
  - `srd-creator-steps.js:152`: `'Kriegswaffen'`, `'Einfache Waffen'`, `mit`
  - `srd-creator-steps.js:662`: `Heiliges Symbol`
  - `srd-creator-steps.js:719`: `RK`, `GES max.`, `ungeübt`, `'Bitte wählen'`
  - `creator_data.py:206`: `4W6`
- **Validation messages are German f-strings.** `_Findings.add(severity, code, message, path, ref)` is at `creator_rules.py:154`, with 79 call sites. Messages are rendered as-is at `srd-creator.js:342` and `srd-progression-ui.js:803`. The `code` is stable.
- **No shared key between the DE and EN compendia.** DE `sourcePages` covers the whole document (Ablenkung shows 122–129); EN covers the entry (Mislead shows 150). They can't be used as a join key, and I found no existing crosswalk anywhere in the repo.
- **What can be matched deterministically:**
  - Spells have structured facets: level, school, ritual, concentration, components, classes.
  - Class options share a stem: DE `classes.warlock.invocation-agonizing-blast` ↔ EN `classes.warlock.eldritch-invocation-options.agonizing-blast`.
  - Classes share IDs: `classes.barbarian.barbarian` exists in both.
- **Reusable pieces:**
  - `creator_data.py:86` `Source.ref(rule_id, quote)` checks that a quote appears verbatim in a rule block.
  - `english.py` `entity()` / `entry()` serve EN entries through `/api/rulesets/srd-5.2.1-en/compendium/entry/<id>` (`rules.py:482`).
  - `tools/i18n/build_catalog.py` merges `tasks/*.json` files and supports `--check`.

## 2. Design decisions

**D1. One engine, display data kept separate.** Creator-data stays canonical German and is never changed. Evaluation, IDs, `category`, `column`, `kind`, `classKey`, property names and every logic comparison keep using it. English display comes from a separate overlay keyed by canonical ID. There is no EN `creator-data.json` and no second mechanics derivation.

**D2. Validated crosswalk that maps IDs, not labels.**
- A new builder, `tools/build_creator_locale.py`, writes `vtt/rules_content/srd-5.2.1-en/generated/creator-display.json`. It supports `--check` for staleness, the same way `build_catalog.py` does.
- It proposes DE→EN pairs using deterministic rules per collection:
  - **classes:** identical `classes.<key>.<key>`
  - **subclasses:** same `classKey`, exactly one SRD subclass on each side (12/12)
  - **class options (38):** `(classKey, option stem)` plus a consistent `optionKind`
  - **spells (339):** a fingerprint of level, school, ritual, concentration, component letters (G→S) and the class set mapped through the class crosswalk. School names go through a fixed 8-entry table.
  - **species (9), backgrounds (4), feats, weapons, armor and gear:** document scope plus structured fields (sizes, speed, cost, weight, damage, properties)
  - **abilities, skills, languages, alignments, coins:** row-aligned tables with the same shape and a matching ability column
- Collisions are never guessed. They go into `tools/creator_locale/pins.json`, which holds reviewed **ID pairs only** (DE id → EN id plus a note), never label text.
- Every EN name in the overlay must equal the EN entity's `name` or pass `Source.ref` against an EN document block.
- An overlay entry contains: `{key: "<collection>:<deId>", enEntityId | enRuleId, name, abbreviation?, evidence}`, plus top-level `unresolved: [...]`, `coverage: {collection: {total, mapped, pinned, unresolved}}` and `canonicalHash`.
- Anything unresolved falls back to the German canonical name, shown with `lang="de"`. It is listed in the coverage report, never machine-translated.

**D3. Labels with no SRD entity.** These are weapon categories, armor categories, `RK`/`AC`, `GES`/`DEX`, dice notation `W`/`d`, choice-category labels, weapon property names, ability abbreviations, step names and help text.
- They go in a new catalog task, `tools/i18n/tasks/fv01-character-module.json`.
- The EN wording comes verbatim from EN SRD text wherever the term exists there. Roll Drauf-authored help text gets authored EN catalog strings, which is existing practice.
- Property names are display-mapped by their canonical German string. Logic keeps comparing `p.name`.

**D4. The module gets its own translator; the site locale stays global.**
- `display-preferences.js` adds `VTTI18n.module()`. It returns `{locale, t, literal, translate(root)}` reading `row[contentLocale()]` from the same `VTTUiMessages`.
- Global `translate()` and the MutationObserver skip any node inside `[data-rules-locale-scope]`. The module translator handles those subtrees and sets `lang` on the scope root. `documentElement.lang` keeps the UI locale.
- Scope roots:
  - `srd-creator.html`: `#scMain`, plus `#scDialog` if it sits outside `#scMain`. Check its placement during implementation.
  - `character-sheet.html`: the sheet focus page `section` at line 749, including the section nav "Bogenabschnitte" at line 838, because that nav belongs to the editor.
  - Site chrome stays global: `vtt-main-nav.js`, `regelwerk-navigation.js`, `creation-engine-nav.js` and `book-scene.js`.
- In module scripts, replace `globalThis.VTTUi(` with a file-local `ui(` bound to `VTTI18n.module()`. That covers `srd-creator*.js`, `srd-rule-preview.js`, `srd-inventory-ui.js`, `srd-progression-ui.js`, `srd-manage-ui.js` and the SRD part of the sheet's inline script.
- On `vtt:displaychange`, if the resolved content locale changed, the module reloads its overlay and re-renders from the in-memory draft. It doesn't save, reset or touch dirty state.

**D5. Localized rule detail.**
- `SC.COMP` and the rule-preview base are computed from the module locale.
- For EN, a canonical ID resolves to `enEntityId` through the overlay, and the EN compendium entry is fetched.
- Subclass previews use the EN subclass entity's own `features`.
- If there's no mapping or the fetch fails, the DE entry is shown with a module-locale notice ("Only available in German" / „Nur auf Deutsch verfügbar"). Requests are never redirected to a guessed ID.
- Homebrew entries (`srd-creator.js:156`) always render their authored text and are never overlaid.

**D6. Localized findings.**
- `_Findings.add` gets an optional `params` dict. Messages stay German, so the default output is unchanged.
- A new `vtt/rules_content/creator_messages.py` provides `localize(items, locale, overlay)`. It holds EN templates keyed by `code`, and fills entity params by ID through the overlay.
- These endpoints accept `rulesLocale=de|en`, default `de`, and return 400 for anything else: `/evaluate`, and later the progression preview and level-up blockers.
- Responses echo `rulesLocale`. `code`, `path` and `ref` never change.
- Authorization stays where it is now (`jwt_required`, `_owned_draft`, progression ownership). The locale can't affect access.

**D7. Cache, errors and stale responses.**
- New endpoint: `GET /api/srd-creator/creator-display?locale=en`.
  - Requires login, like `creator-data`.
  - Sends `Cache-Control: private, max-age=300` and an ETag.
  - The client adds `?v=<canonicalHash>` to bust caches.
  - `canonicalHash` is a hash of the served creator-data. If the hashes don't match, the client uses DE display and shows a notice.
- The client keeps an `app.localeSeq` counter. Any overlay, evaluation or entry response whose sequence number or echoed `rulesLocale` is not current is discarded.
- A failed overlay load falls back to DE display with a visible notice. It never blocks editing, saving or finalizing.
- Locale is never stored in drafts or characters, so it can't change draft identity, versions or values.

## 3. Acceptance criteria (full FV01)

1. **Language matrix.** For DE/DE, DE/EN, EN/DE, EN/EN and both automatic variants:
   - Site ribbon and navigation follow the UI locale.
   - Everything inside the creator and editor scope follows the rules locale: steps, help, validation, choices, class details, weapons, spells, invocations and rule dialogs.
   - Probe terms: Weisheit/Wisdom, Einfache Waffen/Simple Weapons, Ablenkung/Mislead, Schauerlicher Strahl/Agonizing Blast, point-buy messages.
2. **Reload and existing drafts.** After a reload or reopening an existing draft, the draft's state JSON is byte-identical across locales. Evaluation output is equal once `message` is removed. Homebrew names and descriptions are unchanged.
3. **Crosswalk.** It passes these checks:
   - bijective
   - every EN ID exists
   - every name is backed by evidence
   - no logic discriminator appears in the overlay
   - `--check` finds nothing stale
   - 100% coverage for classes, subclasses, class options, species, backgrounds, abilities and skills
   - every remaining collection either fully mapped or carrying explicitly approved unresolved entries
4. **Findings.** Every `code` literal in `creator_rules.py` has an EN template with matching parameter names, verified by an AST scan.
5. **Editor.** The sheet, inventory, progression and level-up preview meet the same criteria.
6. **Live.** Deployed to `vtt.roll-drauf.de` with evidence as required by AGENTS.md.

## 4. Tests

- **New `tests/test_creator_locale_crosswalk.py`:**
  - generated output is fresh
  - bijection and existence checks
  - names equal EN entity names
  - coverage thresholds per collection
  - known pairs: `spells.a-b.ablenkung → spells.m-o.mislead`, `classes.warlock.invocation-agonizing-blast → classes.warlock.eldritch-invocation-options.agonizing-blast`
  - no `category`/`column`/`kind`/`classKey` keys in the overlay
- **`test_regelwerk_creator_rules.py`:** findings code ↔ EN template parity (AST); default `de` output unchanged.
- **`test_srd_creator_api.py`:**
  - `creator-display` requires auth, rejects a bad locale with 400, returns the ETag and `canonicalHash`
  - `evaluate` in `en` returns the same values as in `de`
  - a draft saved while viewing in EN keeps its state identical
- **`test_srd_creator_browser.py`:**
  - the language matrix plus reload
  - switching locale mid-draft keeps state and dirty flag
  - stale response, by delaying the old-locale route
  - overlay-failure fallback
  - homebrew text preserved
  - detail dialog title in EN
- **Editor browser tests:** `test_srd_progression_browser.py`, `test_srd_inventory_browser.py`, `test_srd_manage_browser.py`.
- **Catalog:** `python tools/i18n/build_catalog.py --check`.

## 5. Unresolved inputs

- **U1.** The number of ambiguous spell, item and feat fingerprints is unknown until the builder runs. Each one needs a reviewed pin, and each counts as unresolved until then.
- **U2.** Are `srd-shared-ui.js` (the shared view) and `srd-party-ui.js` part of the "editor"? My recommendation: shared view yes, using the viewer's rules locale; party UI no (separate packet).
- **U3.** Do finalized characters or inventory items store German display names as snapshots? `srd-inventory-ui.js:64` reads `e.name` from creator data, but stored item names weren't inspected. If snapshots exist, the editor renders by ID and falls back to the stored name. No migration.
- **U4.** Do API error bodies from `_bad()` (German) and `VTTI18n.error` (`display-preferences.js:166`) get localized by code in module locale? I recommend yes, done in Slice 3.
- **U5.** Measurement units (`m`/`ft`) stay their own preference and are not tied to rules locale. Owner confirmation would be useful.
- **U6.** `display-preferences.js` is shared with FV03 (navigation/layout). The scope-skip change has to be coordinated so neither packet overwrites the other.

## 6. Implementation handoff: Slice 1 (smallest slice that still delivers)

**Goal:** on the live creator, the full matrix works end-to-end for classes, subclasses, class options/invocations, species, backgrounds, abilities, skills, spells and all creator labels and findings. Collections with unresolved entries are visibly reported, never guessed.

**Files** (none are mapmaker files):
- **New:** `tools/build_creator_locale.py`, `tools/creator_locale/pins.json`, `vtt/rules_content/srd-5.2.1-en/generated/creator-display.json`, `vtt/rules_content/creator_messages.py`, `tools/i18n/tasks/fv01-character-module.json`, `tests/test_creator_locale_crosswalk.py`
- **Edited:**
  - `vtt/static/js/display-preferences.js`: `module()` and the scope skip
  - `vtt/rules_content/creator_rules.py`: `params` only; no rule changes
  - `vtt/characters/srd_creator.py`: `creator-display` endpoint and `rulesLocale` on `/evaluate`
  - `vtt/templates/srd-creator.html`: scope attribute
  - `vtt/static/js/srd-creator.js`, `srd-creator-steps.js`, `srd-creator-random.js`: `ui()`, label helpers `SC.label(collection, id)`, localized `COMP`/`openEntry`, findings rendering, sequence guard
  - `vtt/static/js/srd-rule-preview.js`
  - regenerated `ui-catalog.js` and `ui.*.json`
  - the API and browser test files listed in section 4

**Process:** the builder runs locally and the output is committed. Then the Section 4 tests, then the release flow from AGENTS.md: commit, push, reconcile the running image, deploy the app only, live-verify the 5 combinations with a QA user, record evidence under `docs/proofs/fv01-<date>/`, clean up QA data, and keep a rollback image.

**Interim limitation to disclose:** in Slice 1 the character editor still shows German until Slice 2.

## 7. Remaining work to close FV01

- **Slice 2, editor:**
  - scope root in `character-sheet.html`
  - the sheet's inline SRD script (lines ~1100–2494): `srdCreatorData`, the subclass compendium fetch at 1855, and roll and species-action labels
  - `srd-inventory-ui.js`, `srd-progression-ui.js`, `srd-manage-ui.js`
  - `rulesLocale` on the progression and level-up preview endpoints and their blockers
  - resolve U3
- **Slice 3, closing:**
  - localize API error codes (U4), finalize and import messages, and the shared view (U2)
  - get unresolved crosswalk coverage to zero, or to an owner-approved list
  - update the FV01 status in `VTT_NEXT_FULL_VERSION_2026-11-23.{md,json}` with verification and delivery references
  - Monitor pass over the whole matrix on creator and editor, live
- **FV01 closes only when** all criteria in section 3 have live evidence. FV02 and FV14 stay blocked until then.
