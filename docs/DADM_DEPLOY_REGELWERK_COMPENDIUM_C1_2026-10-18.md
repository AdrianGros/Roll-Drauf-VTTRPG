# DAD-M Deploy: Regelwerk Compendium C1 (queryable SRD data)

date: 2026-10-18
status: deployed on the live test environment (image `roll-drauf-vtt-app:regelwerk-d2e3cde`, commit `d2e3cde`)
goal: step 1 toward feature parity with compendium tools (D&D Beyond / 5e.tools style), built independently on the published SRD 5.2.1 DE package.

## Scope

- Derived artifact `generated/compendium.json` (built by `tools/build_regelwerk.py`, `--check` verifies currency; no package version change).
- Entities: 339 spells, 330 creatures (235 monsters + 95 animals), 258 magic items, 17 feats, 38 weapons, 13 armor entries.
- API `GET /api/rulesets/srd-5.2.1-de/compendium` with `type`, `q` (name/summary, umlaut-folded), per-type facets
  (spell: level, school, class, concentration, ritual, component; creature: type, size, origin, cr_min/cr_max, legendary;
  magic item: category, rarity, attunement; feat: category; weapon: class, kind, mastery; armor: category), `sort`, `limit` (<=200), `offset`;
  invalid input returns 400. `/compendium/summary` returns counts.
- UI `/regelwerk/compendium` (filters, sorting, paging, URL state, links to the rule text anchors); linked from the Regelwerk sidebar.
- Tests: `tests/test_regelwerk_compendium.py` (18) plus existing Regelwerk tests, 58 pass.

## Source discipline

Only SRD 5.2.1 content from the digest-pinned, CC BY 4.0 package is used; entities are parsed from the reviewed documents, no external data.

## Not yet covered / open

- Classes, species, backgrounds, adventuring gear, tools, conditions/glossary terms as compendium entities.
- Inline detail view (currently links to the rule text); browser-level checks of the new page (no browser on the server).
- Rollback: set the compose image back to `regelwerk-72e3177`.
