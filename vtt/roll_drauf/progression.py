"""
Roll Drauf Light — progression engine.

Provides:
  build_progression_scaffold(class_entry, current_level)
    -> dict: progression block for roll_drauf_light payload

  apply_level1_package(rdl_payload, species_entry, faction_entry, class_entry, background_entry)
    -> rdl_payload enriched with `content` and `progression` blocks

Design constraints (M24):
  - No stat side-effects applied here — stat baselines stay in routes/LEVEL_ONE_BASELINES.
  - Content blocks are descriptive and serialization-safe.
  - Choices at levels 3/4/5 are scaffolded but empty (chosen: {}) until level-up.
  - This module has no Flask or DB imports — pure data transformation.
"""


def build_progression_scaffold(class_entry: dict, current_level: int = 1) -> dict:
    """
    Build the full 1–5 progression structure for a character.

    Each level entry contains:
      status         'complete' | 'locked'
      auto_features  list of {slug, name} stubs (full descriptions in catalog)
      choices_available  list of choice descriptors from catalog
      choices        dict of player-made decisions (empty until level-up)
    """
    levels = {}
    prog = class_entry['progression']

    for lvl in range(1, 6):
        level_data = prog[lvl]
        status = 'complete' if lvl <= current_level else 'locked'

        levels[str(lvl)] = {
            'status': status,
            'auto_features': [
                {'slug': f['slug'], 'name': f['name']}
                for f in level_data['auto_features']
            ],
            'choices_available': level_data['choices_available'],
            'choices': {},
        }

    return {
        'current_level': current_level,
        'level_cap': 5,
        'levels': levels,
    }


def _species_trait_snapshot(species_entry: dict) -> dict:
    """Return a slim content snapshot of the species trait."""
    trait = species_entry.get('trait', {})
    return {
        'slug': trait.get('slug', ''),
        'name': trait.get('name', ''),
        'description': trait.get('description', ''),
    }


def _faction_tags_snapshot(faction_entry: dict) -> list:
    """Return faction tags list."""
    return list(faction_entry.get('tags', []))


def _background_perk_snapshot(background_entry: dict) -> dict:
    """Return a slim content snapshot of the background perk."""
    perk = background_entry.get('perk', {})
    return {
        'slug': perk.get('slug', ''),
        'name': perk.get('name', ''),
        'description': perk.get('description', ''),
    }


def _class_level1_features(class_entry: dict) -> list:
    """Return level-1 auto_features with full descriptions."""
    return [
        {
            'slug': f['slug'],
            'name': f['name'],
            'description': f['description'],
            'source': f.get('source', 'class'),
        }
        for f in class_entry['progression'][1]['auto_features']
    ]


def apply_level_up(
    rdl: dict,
    class_entry: dict,
    target_level: int,
    choices: dict,
) -> dict:
    """
    Apply a level-up to target_level (must equal current_level + 1).

    Mutates rdl in-place:
      - content.class_features: auto_features appended (idempotent by slug);
        signature-chosen feature appended.
      - progression.levels[target_level].status → 'complete'
      - progression.levels[target_level].choices → saved choices dict
      - progression.current_level → target_level
      - content.training_bonus → 3 at level 5 (all classes)

    Returns a metadata dict:
      {'chosen_attribute': str | None}
    so the route can apply stat changes to the Character ORM model.

    Pure data transformation — no Flask/DB imports.
    """
    cat_level = class_entry['progression'][target_level]
    stored_level = rdl['progression']['levels'][str(target_level)]

    # Apply auto_features idempotently (guard by slug)
    existing_slugs = {f['slug'] for f in rdl['content']['class_features']}
    for feat in cat_level['auto_features']:
        if feat['slug'] not in existing_slugs:
            rdl['content']['class_features'].append({
                'slug': feat['slug'],
                'name': feat['name'],
                'description': feat['description'],
                'source': feat.get('source', 'class'),
            })
            existing_slugs.add(feat['slug'])

    chosen_attribute = None

    # Process each choice_def at this level
    for choice_def in cat_level['choices_available']:
        slug = choice_def['slug']
        chosen = choices.get(slug)
        choice_type = choice_def['choice_type']

        if choice_type == 'signature' and chosen:
            option = next(
                (o for o in choice_def['options'] if o['slug'] == chosen),
                None,
            )
            if option and option['slug'] not in existing_slugs:
                rdl['content']['class_features'].append({
                    'slug': option['slug'],
                    'name': option['name'],
                    'description': option['description'],
                    'source': option.get('source', 'class'),
                })
                existing_slugs.add(option['slug'])

        elif choice_type == 'attribute' and chosen:
            chosen_attribute = chosen

    # Persist what the player chose
    stored_level['choices'] = dict(choices) if choices else {}

    # Level-5 milestone: training_bonus rises to 3 for all classes
    if target_level == 5:
        rdl['content']['training_bonus'] = 3

    # Advance progression state
    rdl['progression']['current_level'] = target_level
    stored_level['status'] = 'complete'

    return {'chosen_attribute': chosen_attribute}


def apply_level1_package(
    rdl_payload: dict,
    species_entry: dict,
    faction_entry: dict,
    class_entry: dict,
    background_entry: dict,
) -> dict:
    """
    Enrich an rdl_payload dict (in-place) with Level-1 content packages
    and the full 1–5 progression scaffold.

    Called from routes._build_roll_drauf_light_payload() after the catalog
    lookups confirm all four choices are valid.

    Returns the mutated rdl_payload.
    """
    rdl_payload['content'] = {
        'species_trait': _species_trait_snapshot(species_entry),
        'faction_tags': _faction_tags_snapshot(faction_entry),
        'background_perk': _background_perk_snapshot(background_entry),
        'class_features': _class_level1_features(class_entry),
        'training_bonus': class_entry.get('training_bonus', 2),
    }

    rdl_payload['progression'] = build_progression_scaffold(class_entry, current_level=1)

    return rdl_payload
