# D&D 5e portable character JSON

The VTT supports its own portable D&D 5e JSON format through the character archive's **Charakter importieren** action and the character sheet's **Charakter exportieren** action. Both 2014 and 2024 editions are explicit. This format is not a D&D Beyond or Roll20 file importer; those exports need conversion to the fields below.

Import creates a new character owned by the signed-in user. It preserves the supplied current and maximum HP, other statistics, class, background, race, notes, spells, equipment and inventory. It does not transfer account ownership, campaign membership, character IDs, avatar/token media or Creation Engine identifiers. Unknown fields are rejected instead of silently ignored.

## Format version 1

Required top-level fields:

| Field | Value |
| --- | --- |
| `export_kind` | `"dnd5e_character"` |
| `export_version` | Integer `1` |
| `system_id` | `"dnd5e_2014"` or `"dnd5e_2024"` |
| `name` | Nonempty character name, at most 100 characters |
| `race` | Nonempty race name, at most 50 characters |
| `class` | Nonempty class description, at most 50 characters |
| `background` | Nonempty background, at most 100 characters |
| `stats` | The explicit statistics object described below |

Optional top-level fields are `character_data` (an object), `spells`, `equipment`, `inventory` (arrays), and `homebrew_origin` (the full race profile). An omitted resource array means no resources of that type. Export includes these arrays and ordinary metadata even when empty.

`stats` requires integer `str`, `dex`, `con`, `int`, `wis`, `cha` (1–30), `level` (1–20), `xp` (0–1,000,000,000), `ac` (0–100), `hp_current` (0–10,000), `hp_max` (1–10,000), and `proficiency_bonus` (0–100). Optional `mana_current` and `mana_max` are 0–10,000 and default to 0. Current HP and mana cannot exceed their maximum values. Boolean and fractional values are rejected for integer fields.

A minimal valid file is:

```json
{
  "export_kind": "dnd5e_character",
  "export_version": 1,
  "system_id": "dnd5e_2024",
  "name": "Mara",
  "race": "Human",
  "class": "Wizard",
  "background": "Sage",
  "stats": {
    "str": 8,
    "dex": 14,
    "con": 12,
    "int": 18,
    "wis": 13,
    "cha": 10,
    "level": 5,
    "xp": 7000,
    "ac": 14,
    "hp_current": 7,
    "hp_max": 31,
    "proficiency_bonus": 3
  },
  "character_data": {
    "notes": "A student of the northern observatory.",
    "skills": {"Arcana": 7}
  },
  "spells": [],
  "equipment": [],
  "inventory": []
}
```

## Resources and metadata

Every resource requires a nonempty `name` of at most 100 characters. The other supported fields are optional; standard model defaults apply when omitted. Export writes every supported field so a roundtrip preserves its value.

| Array | Supported fields besides `name` |
| --- | --- |
| `spells` | `level`, `school`, `casting_time`, `range`, `duration`, `is_prepared`, `is_ritual`, `description`, `damage_dice`, `damage_type`, `custom_data` |
| `equipment` | `type`, `rarity`, `ac_bonus`, `damage_dice`, `damage_type`, `is_equipped`, `is_cursed`, `weight`, `cost`, `description`, `special_properties` |
| `inventory` | `type`, `quantity`, `weight_per_unit`, `cost`, `is_consumable`, `is_cursed`, `description`, `effects` |

Spell levels are integers 0–9, equipment AC bonuses are −100–100, inventory quantities are 0–1,000,000, and weights are finite numbers 0–1,000,000 or `null`. Flags are booleans. Optional text accepts `null`; descriptions are at most 8,192 characters, duration at most 100, damage dice at most 20, and other resource text at most 50. Structured metadata fields (`custom_data`, `special_properties`, `effects`) are objects. Resource IDs, `character_id`, timestamps and derived fields such as `total_weight` are not part of the portable format.

`character_data` and resource metadata remain inert JSON. They do not execute scripts, apply bonuses or grant engine authority. Metadata allows at most 8 nested levels, 100 keys per object, 200 entries per array, 8,192 characters per string, and finite numeric magnitudes up to 1,000,000,000. The complete file is limited to 512 KiB; each resource array is limited to 200 entries.

Reserved metadata includes `system_id`, `roll_drauf_light`, `homebrew_origin`, `creation_engine`, `provenance`, keys beginning with `ce_`, and private engine reference fields (`workspaceId`, `draftId`, `revisionId`, `definitionId`, `scopeId`, `executionLockDigest`). Tagged engine references are also rejected. The canonical edition is carried at the file's top level and restored in the character's internal system marker. Existing data outside these portable bounds produces an explicit export/import error; it is not truncated.

## Homebrew race rules

To retain an attached homebrew race, include `homebrew_origin`. Its `name` must equal the character's `race`, and its `edition` must equal `system_id`. A complete example is:

```json
{
  "name": "Echo folk",
  "edition": "dnd5e_2024",
  "creatureType": "Humanoid",
  "size": "medium",
  "speed": 30,
  "languages": "Common and one chosen language",
  "abilityScoreRules": "No automatic attribute changes.",
  "prose": "People of the echoing hills.",
  "traits": [
    {
      "name": "Stone memory",
      "kind": "trait",
      "description": "Remember a path through stone.",
      "usage": "Passive"
    },
    {
      "name": "Echo step",
      "kind": "feature",
      "description": "Follow an echo to a visible space.",
      "usage": "Once per long rest",
      "choices": "Choose a visible space.",
      "prerequisites": "Level 3"
    }
  ]
}
```

Required profile fields are `name`, `edition`, `creatureType`, `size`, `speed`, `languages` and `traits`. `abilityScoreRules` and `prose` are optional. Size is one of `tiny`, `small`, `medium`, `large`, `huge`, `gargantuan`, or `small_or_medium`. Walking speed is an integer from 0 to 300 feet. Provide 1–20 traits with distinct names; each requires `name`, `kind` (`trait` or `feature`), `description` and `usage`. `choices` and `prerequisites` are optional. Trait names are at most 200 characters, creature type at most 100, prose at most 8,192, and other rule text at most 2,048.

The Creation Engine must be available to import a file containing homebrew rules. The importer rebuilds and validates the race answers, checks `sheet_ready` quality, and creates an independent race revision owned by the importing user. Character, resources, revision and association are saved in one transaction. The file never carries the original workspace, draft, revision, history or ownership identifiers. Race traits remain manually resolved rule text; importing them does not change the supplied statistics.

Previously attached race text remains visible and exportable when the editor is disabled. Importing that file with its homebrew rules requires the editor capability again. Files without `homebrew_origin` can be imported without the Creation Engine and can receive an authored race through the engine afterward.

## HTTP entry points

- `GET /api/characters/<id>/export` returns the portable JSON to an authorized character reader.
- `POST /api/characters/import` accepts the JSON and returns `201` with `{ "message": "…", "character": { … } }`.

Authentication and the normal CSRF policy apply. D&D import requires an active account and rejects View As. Unsupported fields or inconsistent rules return an explicit validation error; unavailable homebrew authoring returns `409`. A failed persistence transaction returns `503` and leaves no partial character or race source. Existing Roll-Drauf-Light import/export retains its existing separate format.
