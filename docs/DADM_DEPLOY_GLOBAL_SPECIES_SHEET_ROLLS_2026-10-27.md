# Deploy — VTT-wide playable Species and sheet-to-table rolls

## Implementation summary
The existing playable Species publication flow now accepts a `global` target. Any active author can publish a validated Eagle Species into the VTT-wide compendium, and authenticated players can select it across campaigns. Publications remain immutable and author-owned. The SRD character sheet now binds rolls to the table it was opened from, exposes that destination before a click, and carries the roll to the live VTT dice and chat log. A standalone sheet requires a choice if several tables are running. Duckfolk's telekinesis declaration follows the same table binding.

## Files changed
- Publication and catalog: `vtt/creation_engine/species_routes.py`, `vtt/creation_engine/models.py`, `vtt/characters/species_catalog.py`, `vtt/static/js/ce-species-publish.js`, `vtt/templates/creation-engine.html`.
- Sheet and table: `vtt/characters/sheet_link.py`, `vtt/characters/srd_creator.py`, `vtt/characters/species_actions.py`, `vtt/templates/character-sheet.html`, `vtt/static/js/play-ui.js`, `vtt/templates/play.html`.
- Regression coverage: `tests/test_playable_species.py`, `tests/test_srd_rolls.py`, `tests/test_sheet_to_table_browser.py`, and the Duckfolk journey in `tests/test_creation_engine_eagle_browser.py`.

## Verification run
- Focused API, sheet, inventory, dice display, and two Chromium journeys: **85 passed** on 2026-10-27. Command and final output: `/tmp/focused-20261027.log` (test environment: disposable PostgreSQL and local Chromium).
- `git diff --check` passed before committing. The release image was inspected for the new roll-context route, global Species publication code, Duckfolk session binding, and the existing main navigation assets.
- Release image `roll-drauf-vtt-app:global-sheet-20261027-v3` was staged from the prior production image, retaining the live navigation overlays in the three touched templates. No schema migration was needed. The previous Compose override was backed up as `production.duck-species.override.yml.bak-global-sheet-20261027`.

## Production evidence
On 2026-10-27, Compose service `app` was recreated with image `roll-drauf-vtt-app:global-sheet-20261027-v3`; its container is running. `https://vtt.roll-drauf.de/api/admin/assets/health`, `/character-sheet`, `/creation-engine`, `/static/js/play-ui.js`, and `/static/examples/duckfolk-2024.json` returned HTTP 200. The served sheet contains `roll-context` and the shared navigation assets; the served editor contains the VTT-Compendium copy. The new roll-context and Species catalog endpoints returned HTTP 401 without credentials, confirming their routes are mounted and protected. `CE_AUTHORING=true` and `CE_PLAYABLE_SPECIES=true` are set in the live app.

## Acceptance checklist
1. Global publication, cross-campaign selection, privacy, and immutable lineage: **passed in API and Chromium tests**.
2. Separate-tab skill and dagger rolls appeared live in the correct VTT table and persisted after reload: **passed in Chromium**.
3. Wrong or ended table IDs, multiple live tables, and unauthorized roll attempts: **passed in API tests**.
4. Live routes and container: **passed production smoke**.
5. A public Duckfolk revision exists in production: **pending**. There is no live Duckfolk Eagle source or Species publication yet; an owner account must be named before creating the first attributed revision.
