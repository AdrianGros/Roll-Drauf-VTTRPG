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

Eagle's 410 existing UI keys are pinned to upstream commit 518b2f9c… in
`eagle-sources.json`; original EN plus our DE translation is compiled alongside
VTT labels. `installEagle()` adapts the existing shim i18n API, not arbitrary DOM.
`eagle-host-patches.json` records the exact changes to the VTT-owned host entry
in the existing compiled bundle so a rebuild can preserve them. Imported dnd5e
catalog names and document content remain source-language data.
