# DAD-M Deploy: Regelwerk Compendium C2 (creator data and detail view)

date: 2026-10-18
status: see the commit that carries this file; deployed on the live test environment as an overlay image `roll-drauf-vtt-app:regelwerk-<commit>`
goal: step 2 toward creator parity: data the character creator needs, derived only from the published SRD 5.2.1 DE package (1.0.0, unchanged).

## Scope

New entity types in `generated/compendium.json` (built by `vtt/rules_content/compendium_creator.py`, verified by `tools/build_regelwerk.py --check`):

| type | count | notable fields |
| --- | --- | --- |
| class | 12 | hit die, primary ability, saving throws, skill choices, weapon/armor/tool training, starting equipment options A/B, 20-level progression table, spell list per grade |
| subclass | 12 | class, motto, feature ids |
| class-feature | 232 | class, level, subclass |
| class-option | 38 | Metamagie, Schauerliche Anrufung (kind, prerequisite) |
| species | 9 | creature type, sizes, speed, darkvision, trait names |
| background | 4 | ability scores, origin feat (+ choice), skills, tool, equipment options |
| gear | 108 | adventuring gear, foci, holy symbols, ammunition, tack; kit descriptions linked |
| tool | 25 | ability, cost, weight, use, craft |
| mount / vehicle | 8 / 7 | capacity, cost / speed, crew, AC, HP |
| service | 34 | lifestyle, food and lodging, hirelings, spellcasting services |
| glossary | 155 | rules terms incl. conditions (category Zustand) |

- Row entities (weapons, armor, gear rows, mounts, vehicles, services) link to their table anchor and carry `tableId`/`rowIndex`.
- API: new facets per type (class-feature level 1-20, className, subclass, spellcaster, hitDie, ...); new
  `GET /api/rulesets/srd-5.2.1-de/compendium/entry/<id>` returns the entity plus the verbatim package blocks (class: overview plus progression table; row entities: the single table row plus the detail section).
- UI: 18 categories, inline detail view (`?type=...&entry=<id>`, browser back works), link to the rule text.
- `compendium.json` is cached in memory by file mtime.
- Tests: `tests/test_regelwerk_compendium_creator.py` (9) and the extended `tests/test_regelwerk_compendium.py`; 67 pass. The UI was exercised with jsdom against API fixtures (all 18 types render, detail open/back works); no real browser exists on the server.

## Findings in the source (package unchanged, flagged for the content lead)

1. Spell name differences: four spells carry different names in class lists and descriptions (`Licht`/`Leicht`, `Fliegen`/`Flug`, `Springen`/`Sprung`, `Verwünschen`/`Verwünschung`). Package text stays verbatim; a small alias map links them.
2. Printed class spell tables are incomplete or misplace rows in the source layout: Druid level 2 lacks 17 spells and holds 12 level-4 spells, level 3 holds 4 level-6 spells; Bard and Wizard each miss `Macht der Vorstellungskraft`, Sorcerer misses `Gedankendorn` and `Macht der Vorstellungskraft`. The compendium therefore builds class spell lists from each spell's own class line and grade (complete and consistent); a test pins the exact deviations so any change is noticed. Fixing the package tables would need a new package version (owner decision).
3. Two names in the source use decomposed umlauts (Gelehrtenausrüstung, Unterhaltungskünstler-Ausrüstung); matching normalizes them, the text stays verbatim.

## Source discipline

Only the digest-pinned, CC BY 4.0 package content is used; no external data or non-SRD content.

## Rollback

Set the compose image back to `roll-drauf-vtt-app:regelwerk-d2e3cde` (C1) and run `docker compose -p migration-production -f /srv/migration/2026-10-07/setup/production.compose.json up -d --no-deps app`.

## Open

- Owner check of `/regelwerk/compendium` in a real browser (phone), including the detail view.
- Next: DAD-M Discover for the character creator on this data.
