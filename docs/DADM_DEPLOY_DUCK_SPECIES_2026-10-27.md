# Deploy: playable Duckfolk Species (Eagle Species → 2024 origin)

Date: 2026-10-27. Phase: Deploy. Worktree: `feat/eagle-homebrew` (base `776778e`).
Inputs: [Discover](DADM_DISCOVER_EAGLE_PLAYABLE_SPECIES_2026-10-26.md),
[Apply](DADM_APPLY_EAGLE_PLAYABLE_SPECIES_2026-10-26.md), [Duck addendum](DADM_APPLY_DUCK_SPECIES_2026-10-27.md).
Deployed to the live VTT as an overlay on the previous map/navigation image. No production user content was
created or changed; the additive publication table was created. `vendor/eagle-homebrew` and `archive/` untouched.

## Implementation summary

A reusable adapter turns a saved Eagle Species (`Item` of type `race`) plus a typed VTT supplement into an
immutable, versioned 2024 Species profile. Nothing is keyed on a Species id; Duckfolk is only test data.

1. **Check** (`POST /api/ce/authoring/species/check`): reads the world or Library document under the author's
   current rights and reports every field as `converted`, `narrative` or `blocked` with path and German hint.
   Converted: name, `system.source.rules` (2024), `system.type`, `system.movement.*` (fixed numbers, ft/m),
   `system.senses.ranges.*`, one `Size` advancement, description as text. Blocked: 2014/unknown edition,
   any other advancement (Trait, ItemGrant, ItemChoice, ScaleValue, ASI, unknown), Active Effects, Activities or any
   unknown non-empty `system` field, formulas, `@UUID[…]`/`[[…]]` enrichers, malformed supplement.
2. **Supplement** (`roll-drauf.species-supplement.v1`): `skillChoices` (≤2; one SRD skill proficiency picked by the
   player), `actions` (≤4; only kind `object-telekinesis`, activation `action`/`bonus-action`, uses `at-will`,
   integer `rangeFeet` 5–120, `maxWeightLb` 1–500, `maxMoveFeet` 5–120; fixed restrictions no attack, no damage,
   no creature, nothing worn/carried; DM adjudicates), `traits` (narrative only).
3. **Publish** (`POST …/species/publish`): requires the digest returned by the check (`409 source-changed`
   otherwise), re-runs the check, refuses non-playable (`422 not-playable` + report), inserts one immutable
   `ce_species_revisions` row (source copy + digest, supplement, profile + digest, report, author, scope). Same source,
   supplement and profile again → `200 created:false`. Scope `personal` or a campaign the author leads (`resolve_world`).
4. **Catalog / selection** (`GET /api/srd-creator/species-catalog`): latest revision per source for the user's own
   personal scope and the campaigns they own or are an active member of. Draft create/update, `/evaluate`,
   draft view, finalize, rebuild and import all re-check access via `species_catalog.resolve`; a client-supplied
   `homebrew.species.<id>` is never trusted.
5. **Rules**: `species_profiles.species_entry` maps the profile into the creator-data Species shape;
   `creator_rules.evaluate` gained one generic rule — a Species choice with `grants: "proficiency"` grants the chosen
   skill (warning on duplicates). SRD Species and characters take the unchanged path.
6. **Pin**: finalize stores `srd.speciesPin` (revision id/number, profile digest, source uuid/digest, scope, author,
   full profile copy). Campaign-scoped Species must finalize into that campaign. `sheet_link.srd_evaluation` and
   `sheet_link.rules_data` (used by sheet, rolls, inventory recompute, progression, level-up/down, party, tokens,
   shared view/PDF) evaluate from the pin only.
7. **Lifecycle**: duplicate copies the pin; rebuild draft keeps the same revision id and is refused
   (`409 species_unavailable`) if the user lost access; export adds `speciesPin {revisionId, digest, name}`; import
   re-pins from this server's revision only if the importer may choose exactly that revision and digest, else
   `422` before any write; moving a character with a campaign Species into another campaign → `409 species_campaign_only`.
8. **Telekinetic Quack** (`POST /api/srd-creator/characters/<id>/species-actions/<action>`): owner or campaign
   DM; validates object text (3–160), weight ≤ max, distance ≤ range, move 0<…≤ max, `unattended: true`, rejects
   creature/damage/attack fields; requires a live (`in_progress`) session and a non-read-only role; writes one public
   `ChatMessage` (`content_type="species_action"`, `client_event_id="sa:<char>:<action>:<idempotencyKey>"`) and
   broadcasts `chat:message_sent`. The existing unique (author, session, client_event_id) constraint makes retries
   return the first receipt (`200 duplicate:true`).
9. **UI**: Creation Engine companion panel “Spezies spielbar machen” (typed skill choice + telekinesis form, check
   report, publish); SRD creator lists catalog Species with scope/revision/author, movement, senses, action text;
   character sheet shows a pinned-origin block (type, size, walk/swim, “Keine Dunkelsicht”, provenance, traits) and a
   declaration form with a per-declaration idempotency key; DM party card shows origin, movement, senses, action.
   The play table opens the same sheet, so the action is launched from the play context too.
10. **Starter**: “Duckfolk-Beispiel anlegen” creates an ordinary Eagle document in the selected world from
    `vtt/static/examples/duckfolk-2024.json`, restores its typed supplement after reload, and leaves check/publish
    to the GM. The evaluator has no Duckfolk special case. A previously published supplement keeps its choice/action
    IDs when reopened; switching only the publication campaign no longer invalidates a completed check.

The declaration endpoint now rejects reuse of an idempotency key with a different validated declaration (`409`).
An edit to the Eagle source that leaves the playable profile identical still creates a new provenance revision.
Empty names, overlong text, nested unknown sense/type fields, and unused chat description text block publication
instead of being silently dropped.

Feature flag `CE_PLAYABLE_SPECIES` (default off) gates publish, catalog and new selections; pinned characters keep
evaluating when it is off. Migration `migrations/migration_m83_playable_species.sql` is additive (one table).
Rollback: set the flag off; do not drop the table while characters reference revision ids.

## Files changed

New: `vtt/creation_engine/species.py`, `vtt/creation_engine/species_routes.py`,
`vtt/rules_content/species_profiles.py`, `vtt/characters/species_catalog.py`, `vtt/characters/species_actions.py`,
`vtt/static/js/ce-species-publish.js`, `vtt/static/examples/duckfolk-2024.json`,
`migrations/migration_m83_playable_species.sql` (`*.sql` is gitignored and must be force-added),
`tests/test_playable_species.py`, this document.
Modified: `vtt/config.py` (flag), `vtt/creation_engine/models.py` (`CeSpeciesRevision`), `vtt/creation_engine/routes.py`
(registers species routes), `vtt/creation_engine/__init__.py` (docstring), `vtt/rules_content/creator_rules.py`
(generic proficiency grant), `vtt/characters/sheet_link.py`, `vtt/characters/srd_creator.py`,
`vtt/characters/srd_inventory.py`, `vtt/characters/srd_party.py`, `vtt/characters/srd_export.py`,
`vtt/static/js/srd-creator.js`, `vtt/static/js/srd-creator-steps.js`, `vtt/static/js/srd-party-ui.js`,
`vtt/static/css/creation-engine.css`, `vtt/static/css/srd-party.css`, `vtt/templates/character-sheet.html`, `vtt/templates/creation-engine.html`,
`tests/test_creation_engine_eagle_browser.py`.

## Verification

Claude Code Opus 5.5 made the initial implementation with file tools; the supervising agent ran and refined it.
Results: focused Species suite **30 passed**; Eagle/SRD regressions **180 passed**, with four browser cases failing
only because Chromium's `libatk-1.0.so.0` was absent from the default loader path. Rerunning those sheet cases with
the test browser library path gave **10 passed**. The full Eagle Chromium suite, including the Duckfolk journey,
gave **4 passed**. The Duckfolk journey also passed against the disposable PostgreSQL database (**1 passed**) and
was rerun after adding the GM party view (**1 passed**).
Python `compileall` and `git diff --check` passed. No host `node` binary was available for `node --check`; Chromium
loaded and exercised the modified scripts. The M83 SQL was applied twice in a temporary PostgreSQL schema; all 17
columns and 3 indexes were present, then the schema was removed. Baseline before changes: 51 Eagle/SRD API tests.

`tests/test_playable_species.py` covers: Duckfolk conversion; 16 blocking diagnostics (2014, Trait, ItemGrant
reference, missing Size, `@UUID`, Active Effects, formula, creature type, Activities, limited uses, unknown action
kind, unknown skill, unknown supplement field); generic grant and unchanged SRD evaluation; author check/publish,
digest gate, idempotent republish, stale source, player/stranger refusal; 2014 refusal via API; flag off;
personal/campaign catalog scoping and forged revision ids; player draft → campaign-required finalize → pin →
server-derived skill bonus, sheet origin, skill roll `1d20+1`, DM party origin; edit/republish/delete of the source
leaves the character on revision 1; XP → level-up → level-down keep the proficiency once; duplicate, campaign move
refusal, rebuild, export/import (owner ok, stranger and forged digest refused, no partial write), access loss;
telekinesis without session, owner/DM declaration, exact-once retry, stranger 403, six invalid declarations, missing
key, unknown action; SRD characters have no origin/action/export pin.

## Acceptance checklist (Duck addendum)

1. Author checks and publishes Duckfolk to a campaign — implemented; API-tested.
2. Campaign player sees it, picks Athletics/Perception, finishes, reloads; server-derived bonus without duplicates —
   implemented; API-tested.
3. Sheet and DM party view show Duckfolk, walk/swim, no darkvision, telekinesis rule; linked token uses existing
   character stats — implemented; party/sheet payload API-tested and rendered in Chromium. The visual pass found
   the full action rule cramped the DM card, so the card now has an expandable rule detail.
4. Owner or DM declares telekinesis in a live session; visible, attributable, once on retry; unauthorized refused —
   implemented; API-tested (socket broadcast not asserted).
5. Level-up, duplicate/rebuild, export preserve or refuse before writing; source edits do not change the character —
   implemented; API-tested.
6. Chromium journey on a disposable account/database — passed on SQLite and PostgreSQL-backed browser servers.

## Residual risks and follow-ups

- The browser journey covers starter → check/publish → player skill choice/finalize → sheet/action → GM party;
  level-up, source edit and transfer/rebuild are covered by the focused API suite.
- The telekinesis rule is the provisional interpretation; combat push/pull would be a new action kind or field in
  the supplement schema, not code keyed to Duckfolk.
- No resources/rest counters, resistances, spells, Trait/ItemGrant conversion or Active Effects; they block
  publication by design.
- A campaign Species character that leaves the campaign keeps its pin (owner already holds the content); it cannot
  join another campaign. Shared-link view and PDF show only the Species name and derived numbers.
- `ce_species_revisions` has no withdraw/retire action; the catalog shows the latest revision per source.
- Live rollout built `roll-drauf-vtt-app:duck-species-20261027-v2` FROM the exact prior image
  `roll-drauf-vtt-app:mapmaker-nav-20261026-v2`. The two changed templates were patched over their live versions,
  preserving `vtt-main-nav` and `creation-engine-nav`. The Compose override at
  `/srv/migration/2026-10-07/setup/production.duck-species.override.yml` selects the image and enables
  `CE_PLAYABLE_SPECIES`; the original Compose JSON remains unchanged. `AUTO_CREATE_SCHEMA=true` created the table.
  Container smoke verified schema, starter asset and authoring route. Live smoke verified the running image, flag,
  table, unauthenticated catalog 401, and public health and starter asset 200. Rollback uses the original Compose
  JSON without this override. Leave the additive table in place so existing character pins keep evaluating.
- No Duckfolk was published into a live campaign because none was designated. A GM can use the starter button to
  create a normal editable Eagle Species and publish it for the intended campaign.
