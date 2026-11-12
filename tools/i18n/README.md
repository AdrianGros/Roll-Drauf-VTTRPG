# Explicit UI catalogs

`python3 tools/i18n/build_catalog.py` builds the browser bundle and DE/EN JSON.
`--check` verifies generated files, complete English coverage and placeholder parity.
Only marked repository UI is translated. User names, chat, Homebrew descriptions,
rule catalogs, credits and assets keep their source content. API diagnostics are
adapted only at their explicit error/report display seams; codes remain unchanged.

The source-position inventory and numbered translation chunks preserve the reviewed
initial migration. `scan-ui.cjs` and `mark-ui.py` document that migration; do not
rerun the marker over already marked sources. Acorn is available through the Node
runtime bundled in the existing Playwright test image, without adding dependencies.
Add later source labels to `extra-messages.json`, use `VTTUi(source, parameters)`
for text, `VTTUiHTML(source)` only for static HTML labels, or explicit `data-ui-key`
attributes. Never translate arbitrary DOM text or pass user HTML to the static helper.
API diagnostic adapters in display-preferences.js use code/path contracts and keep
user content separate. Future locales can move these bounded diagnostic messages
into additional catalogs. UI DE/EN does not translate rulebooks (open input I04).

`extra-messages.json` is parsed with a duplicate-key check: the same source twice fails the
build instead of letting the later entry win silently. English uses "DM" consistently.
An extra message may deliberately override an inventory entry with the same source;
`build_catalog.py` then prints a `NOTE extra-messages override differs …` line to stderr
(a different source hashing to the same key still fails). Name-bearing text uses
placeholders (`VTTUi('Die Session "{name}" …', { name })`), never string concatenation.
The rulebook scripts translate only their authored controls/status/headings; rule blocks,
entity/document names, facet values and search excerpts stay source text.

Eagle's 410 existing UI keys are pinned to upstream commit 518b2f9c… in
`eagle-sources.json`; original EN plus our DE translation is compiled alongside
VTT labels. `installEagle()` adapts the existing shim i18n API, not arbitrary DOM.
`eagle-host-patches.json` records the exact changes to the VTT-owned host entry
in the existing compiled bundle so a rebuild can preserve them. Imported dnd5e
catalog names and document content remain source-language data.

Independent workers add new authored labels only in their assigned
`tools/i18n/tasks/<task>.json` (the same source → `{de,en}` format). The compiler
loads these files in filename order. Identical existing translations are accepted;
conflicting translations are rejected, including conflicts with the inventory or
main extras. Duplicate keys, missing/empty locales and placeholder mismatches keep
the same strict checks. Reuse existing labels rather than overriding another task.
Generated bundles and the compiler remain coordinator-owned.
