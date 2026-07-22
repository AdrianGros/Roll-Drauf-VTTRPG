"""Character and character-sheet endpoints."""

import copy
from io import BytesIO

from flask import jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from sqlalchemy.orm.attributes import flag_modified

from vtt.characters import characters_bp
from vtt.extensions import db, limiter
from vtt.models import (
    Campaign,
    CampaignMember,
    Character,
    Equipment,
    InventoryItem,
    Spell,
    User,
)
from vtt.storage import get_storage_adapter
from vtt.upload_security import UploadError, validate_upload
from vtt.utils.time import utcnow
from vtt.roll_drauf.catalog import (
    SPECIES as ROLL_DRAUF_LIGHT_SPECIES,
    CLASSES as ROLL_DRAUF_LIGHT_CLASSES,
    BACKGROUNDS as ROLL_DRAUF_LIGHT_BACKGROUNDS,
    LEVEL_ONE_BASELINES as ROLL_DRAUF_LIGHT_LEVEL_ONE_BASELINES,
)
from vtt.roll_drauf.progression import apply_level1_package, apply_level_up


ROLL_DRAUF_LIGHT_VERSION = 1


IDENTITY_FIELD_MAP = {
    'avatar': {
        'url': 'avatar_url',
        'storage_key': 'avatar_storage_key',
        'mime_type': 'avatar_mime_type',
    },
    'token': {
        'url': 'token_url',
        'storage_key': 'token_storage_key',
        'mime_type': 'token_mime_type',
    },
}

# Maps Roll-Drauf attribute choice values to Character ORM field names
_ATTRIBUTE_STAT_MAP = {
    'str': 'str_score',
    'dex': 'dex_score',
    'con': 'con_score',
    'int': 'int_score',
    'wis': 'wis_score',
    'cha': 'cha_score',
}


def _catalog_lookup(entries, raw_value):
    if raw_value is None:
        return None

    normalized = str(raw_value).strip()
    if not normalized:
        return None

    needle = normalized.casefold()
    for entry in entries.values():
        for candidate in (entry.get('id'), entry.get('slug'), entry.get('name')):
            if candidate and str(candidate).casefold() == needle:
                return entry
    return None


def _extract_roll_drauf_light(character_data):
    if not isinstance(character_data, dict):
        return {}
    payload = character_data.get('roll_drauf_light')
    return payload if isinstance(payload, dict) else {}


def _validate_level_up_choices(cat_level, choices):
    """
    Validate a choices dict against the catalog level definition.

    Returns (validated_choices_dict, None) on success.
    Returns (None, (jsonify_response, status_code)) on failure.

    Only the choices_available defined in the catalog are validated;
    extra keys in `choices` are silently ignored.
    """
    choices = choices or {}
    validated = {}

    for choice_def in cat_level.get('choices_available', []):
        slug = choice_def['slug']
        chosen = choices.get(slug)
        choice_type = choice_def['choice_type']

        if choice_type == 'signature':
            if not chosen:
                return None, (jsonify({'error': 'This level requires a signature choice'}), 400)
            valid_slugs = [o['slug'] for o in choice_def.get('options', [])]
            if chosen not in valid_slugs:
                return None, (jsonify({'error': f'Invalid signature choice: {chosen}'}), 400)
            validated[slug] = chosen

        elif choice_type == 'attribute':
            if not chosen:
                return None, (jsonify({'error': 'This level requires an attribute choice'}), 400)
            if chosen not in _ATTRIBUTE_STAT_MAP:
                return None, (jsonify({'error': f'Invalid attribute choice: {chosen}'}), 400)
            validated[slug] = chosen

    return validated, None


def _build_roll_drauf_light_payload(data):
    species_entry = _catalog_lookup(ROLL_DRAUF_LIGHT_SPECIES, data.get('species'))
    if not species_entry:
        return None, None

    faction_entry = _catalog_lookup(species_entry['factions'], data.get('faction'))
    if not faction_entry:
        return None, (jsonify({'error': 'Faction must match the selected species'}), 400)

    class_entry = _catalog_lookup(ROLL_DRAUF_LIGHT_CLASSES, data.get('class'))
    if not class_entry:
        return None, (jsonify({'error': 'Class must be selected from the Roll Drauf Light list'}), 400)

    background_entry = _catalog_lookup(ROLL_DRAUF_LIGHT_BACKGROUNDS, data.get('background'))
    if not background_entry:
        return None, (jsonify({'error': 'Background must be selected from the Roll Drauf Light list'}), 400)

    rdl = {
        'system_id': 'roll_drauf_light',
        'system_version': ROLL_DRAUF_LIGHT_VERSION,
        'creator_contract_version': 1,
        'species': {
            'id': species_entry['id'],
            'slug': species_entry['slug'],
            'name': species_entry['name'],
        },
        'faction': {
            'id': faction_entry['id'],
            'slug': faction_entry['slug'],
            'name': faction_entry['name'],
        },
        'class': {
            'id': class_entry['id'],
            'slug': class_entry['slug'],
            'name': class_entry['name'],
        },
        'background': {
            'id': background_entry['id'],
            'slug': background_entry['slug'],
            'name': background_entry['name'],
        },
        'attribute_mode': str(data.get('attribute_mode') or 'point_buy'),
        'level_cap': 5,
    }
    # M24: apply level-1 content packages + progression scaffold
    apply_level1_package(rdl, species_entry, faction_entry, class_entry, background_entry)
    return rdl, None


def _normalize_character_payload(data, *, existing_character=None):
    payload = dict(data or {})
    roll_drauf_light, error = _build_roll_drauf_light_payload(payload)
    if error:
        return None, error

    if roll_drauf_light:
        class_slug = roll_drauf_light['class']['slug']
        baseline = ROLL_DRAUF_LIGHT_LEVEL_ONE_BASELINES[class_slug]
        legacy_data = dict(existing_character.character_data or {}) if existing_character else {}
        legacy_data['roll_drauf_light'] = roll_drauf_light

        payload['race'] = roll_drauf_light['species']['name']
        payload['class'] = roll_drauf_light['class']['name']
        payload['background'] = roll_drauf_light['background']['name']
        payload['character_data'] = legacy_data
        payload.setdefault('level', 1)
        payload.setdefault('ac', baseline['ac'])
        payload.setdefault('hp_max', baseline['hp_max'])
        payload.setdefault('mana_max', baseline['mana_max'])

    return payload, None


def _get_current_user():
    user_id = get_jwt_identity()
    if not user_id:
        return None, (jsonify({'error': 'Authentication required'}), 401)

    user = db.session.get(User, int(user_id))
    if not user:
        return None, (jsonify({'error': 'User not found'}), 404)
    return user, None


def _coerce_int(raw_value, field_name):
    try:
        return int(raw_value), None
    except (TypeError, ValueError):
        return None, (jsonify({'error': f'{field_name} must be a number'}), 400)


def _get_character_or_404(char_id):
    char = db.session.get(Character, char_id)
    if not char or char.deleted_at:
        return None, (jsonify({'error': 'Character not found'}), 404)
    return char, None


def _is_active_campaign_member(user_id, campaign_id):
    if not campaign_id:
        return False
    campaign = db.session.get(Campaign, campaign_id)
    if campaign and campaign.owner_id == user_id:
        return True
    member = CampaignMember.query.filter_by(
        user_id=user_id,
        campaign_id=campaign_id,
        status='active',
    ).first()
    return member is not None


def _can_read_character(user_id, char):
    if char.user_id == user_id:
        return True
    if char.campaign_id and _is_active_campaign_member(user_id, char.campaign_id):
        return True
    return False


def _serialize_character_sheet(char):
    character_payload = char.serialize(include_details=True)
    character_payload.update(
        {
            'campaign_id': char.campaign_id,
            'hp_current': char.hp_current,
            'hp_max': char.hp_max,
            'mana_current': char.mana_current,
            'mana_max': char.mana_max,
            'proficiency_bonus': char.proficiency_bonus,
            'character_data': char.character_data or {},
        }
    )
    return {
        'character': character_payload,
        'spells': [spell.serialize() for spell in char.spells],
        'equipment': [item.serialize() for item in char.equipment],
        'inventory': [item.serialize() for item in char.inventory],
    }


def _identity_fields(identity_kind):
    fields = IDENTITY_FIELD_MAP.get(identity_kind)
    if not fields:
        return None, (jsonify({'error': 'Unsupported identity type'}), 404)
    return fields, None


def _identity_url(char_id, identity_kind):
    return f'/api/characters/{char_id}/identity/{identity_kind}'


def _identity_storage_key(char, identity_kind, validation):
    filename = secure_filename(validation['filename']) or f'{identity_kind}.bin'
    checksum_prefix = validation['checksum_md5'][:8]
    return (
        f'uploads/users/{char.user_id}/characters/{char.id}/'
        f'{identity_kind}/originals/{checksum_prefix}-{filename}'
    )


def _clear_identity(char, identity_kind):
    fields = IDENTITY_FIELD_MAP[identity_kind]
    setattr(char, fields['url'], None)
    setattr(char, fields['storage_key'], None)
    setattr(char, fields['mime_type'], None)


@characters_bp.route('/characters', methods=['POST'])
@limiter.limit('10 per hour')
@jwt_required()
def create_character():
    """Create a new character."""
    user, error = _get_current_user()
    if error:
        return error
    user_id = user.id

    data = request.get_json() or {}
    if not data.get('name'):
        return jsonify({'error': 'Character name required'}), 400

    data, error = _normalize_character_payload(data)
    if error:
        return error

    # Optional: attach to campaign if campaign_id provided
    campaign_id = data.get('campaign_id')
    if campaign_id:
        campaign = db.session.get(Campaign, campaign_id)
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        # Check if user is member of campaign
        member = CampaignMember.query.filter_by(
            user_id=user_id, campaign_id=campaign_id
        ).first()
        if not member:
            return jsonify({'error': 'Not a member of this campaign'}), 403

    char = Character(
        user_id=user_id,
        campaign_id=campaign_id,
        name=data.get('name'),
        race=data.get('race', ''),
        class_name=data.get('class', ''),
        background=data.get('background', ''),
        level=data.get('level', 1),
        ac=data.get('ac', 10),
        hp_max=data.get('hp_max', 10),
        hp_current=data.get('hp_max', 10),
        mana_max=data.get('mana_max', 0),
        mana_current=data.get('mana_max', 0),
        str_score=data.get('str', 10),
        dex_score=data.get('dex', 10),
        con_score=data.get('con', 10),
        int_score=data.get('int', 10),
        wis_score=data.get('wis', 10),
        cha_score=data.get('cha', 10),
        character_data=data.get('character_data', {}),
    )
    db.session.add(char)
    db.session.commit()

    return jsonify(char.serialize(include_details=True)), 201


@characters_bp.route('/characters/mine', methods=['GET'])
@limiter.limit('600 per hour')
@jwt_required()
def list_my_characters():
    """List authenticated user's characters."""
    user, error = _get_current_user()
    if error:
        return error

    chars = Character.query.filter_by(user_id=user.id, deleted_at=None).all()
    return jsonify([c.serialize() for c in chars]), 200


@characters_bp.route('/characters/<int:char_id>', methods=['GET'])
@jwt_required()
def get_character(char_id):
    """Get character details."""
    user, error = _get_current_user()
    if error:
        return error

    char, error = _get_character_or_404(char_id)
    if error:
        return error

    if not _can_read_character(user.id, char):
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify(char.serialize(include_details=True)), 200


@characters_bp.route('/characters/<int:char_id>/sheet', methods=['GET'])
@jwt_required()
def get_character_sheet(char_id):
    """Get full character sheet with spells, equipment, and inventory."""
    user, error = _get_current_user()
    if error:
        return error

    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if not _can_read_character(user.id, char):
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify(_serialize_character_sheet(char)), 200


@characters_bp.route('/characters/<int:char_id>', methods=['PUT'])
@limiter.limit('20 per hour')
@jwt_required()
def update_character(char_id):
    """Update character."""
    user, error = _get_current_user()
    if error:
        return error

    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if char.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    data, error = _normalize_character_payload(data, existing_character=char)
    if error:
        return error

    # Update allowed fields
    if 'name' in data:
        char.name = data['name']
    if 'race' in data:
        char.race = data['race']
    if 'faction' in data and not data.get('species'):
        existing = _extract_roll_drauf_light(char.character_data or {})
        if not existing:
            return jsonify({'error': 'Faction requires canonical species data'}), 400
    if 'class' in data:
        char.class_name = data['class']
    if 'background' in data:
        char.background = data['background']
    if 'level' in data:
        char.level = data['level']
    if 'xp' in data:
        char.xp = data['xp']
    if 'ac' in data:
        char.ac = data['ac']
    if 'hp_max' in data:
        char.hp_max = data['hp_max']
    if 'hp_current' in data:
        char.hp_current = min(data['hp_current'], char.hp_max)
    if 'str' in data:
        char.str_score = data['str']
    if 'dex' in data:
        char.dex_score = data['dex']
    if 'con' in data:
        char.con_score = data['con']
    if 'int' in data:
        char.int_score = data['int']
    if 'wis' in data:
        char.wis_score = data['wis']
    if 'cha' in data:
        char.cha_score = data['cha']
    if 'mana_max' in data:
        char.mana_max = data['mana_max']
    if 'mana_current' in data:
        char.mana_current = min(data['mana_current'], char.mana_max)
    if 'character_data' in data:
        char.character_data = data['character_data']

    db.session.commit()
    return jsonify(char.serialize(include_details=True)), 200


@characters_bp.route('/characters/<int:char_id>', methods=['DELETE'])
@limiter.limit('10 per hour')
@jwt_required()
def delete_character(char_id):
    """Soft delete character."""
    user, error = _get_current_user()
    if error:
        return error

    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if char.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    char.deleted_at = utcnow()
    db.session.commit()

    return jsonify({'message': 'Character deleted'}), 200


@characters_bp.route('/characters/<int:char_id>/level-up', methods=['POST'])
@limiter.limit('20 per hour')
@jwt_required()
def level_up_character(char_id):
    """Advance a canonical Roll-Drauf-Light character by exactly one level."""
    user, error = _get_current_user()
    if error:
        return error

    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if char.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    # --- Canonical-character guard ---
    rdl = _extract_roll_drauf_light(char.character_data)
    if not rdl or rdl.get('system_id') != 'roll_drauf_light':
        return jsonify({'error': 'Not a canonical Roll-Drauf-Light character'}), 422

    progression = rdl.get('progression')
    if not progression:
        return jsonify({'error': 'Character has no progression data'}), 422

    current_level = progression.get('current_level', 1)
    level_cap = progression.get('level_cap', 5)

    # --- Level-cap guard ---
    if current_level >= level_cap:
        return jsonify({'error': 'Max level reached'}), 422

    target_level = current_level + 1

    # --- One-level-per-request guard: scaffold must exist ---
    if str(target_level) not in progression.get('levels', {}):
        return jsonify({'error': f'No progression scaffold for level {target_level}'}), 422

    # --- Class lookup ---
    class_slug = rdl.get('class', {}).get('slug')
    class_entry = _catalog_lookup(ROLL_DRAUF_LIGHT_CLASSES, class_slug)
    if not class_entry:
        return jsonify({'error': 'Cannot resolve class from catalog'}), 422

    cat_level = class_entry['progression'][target_level]

    # --- Choice validation ---
    data = request.get_json() or {}
    raw_choices = data.get('choices', {})
    validated_choices, error = _validate_level_up_choices(cat_level, raw_choices)
    if error:
        return error

    # --- Apply level-up (pure data mutation on a copy) ---
    char_data = copy.deepcopy(char.character_data or {})
    rdl_mut = char_data['roll_drauf_light']
    meta = apply_level_up(rdl_mut, class_entry, target_level, validated_choices)

    # --- Apply stat change for attribute choice ---
    chosen_attr = meta.get('chosen_attribute')
    if chosen_attr:
        stat_field = _ATTRIBUTE_STAT_MAP.get(chosen_attr)
        if stat_field:
            setattr(char, stat_field, getattr(char, stat_field, 10) + 1)

    # --- Persist ---
    char.level = target_level
    char.character_data = char_data
    flag_modified(char, 'character_data')
    db.session.commit()

    return jsonify({
        'message': f'Level up! {char.name} ist jetzt Level {target_level}.',
        'level': target_level,
        'character': char.serialize(include_details=True),
    }), 200


def _build_export_payload(char):
    """Build a versioned, portable export dict for a canonical RDL character."""
    char_data = char.character_data or {}
    rdl = char_data.get('roll_drauf_light', {})
    avatar_url = char.avatar_url or (
        f'/api/characters/{char.id}/identity/avatar' if char.avatar_storage_key else None
    )
    token_url = char.token_url or (
        f'/api/characters/{char.id}/identity/token' if char.token_storage_key else None
    )
    return {
        'export_kind': 'character',
        'system_id': 'roll_drauf_light',
        'system_version': ROLL_DRAUF_LIGHT_VERSION,
        'export_version': 1,
        'name': char.name,
        'stats': {
            'str': char.str_score,
            'dex': char.dex_score,
            'con': char.con_score,
            'int': char.int_score,
            'wis': char.wis_score,
            'cha': char.cha_score,
            'level': char.level,
            'xp': char.xp,
            'ac': char.ac,
            'hp_max': char.hp_max,
            'mana_max': char.mana_max,
        },
        'roll_drauf_light': rdl,
        'identity_refs': {
            'avatar_url': avatar_url,
            'token_url': token_url,
        },
    }


def _validate_import_payload(payload):
    """
    Validate a character import payload against the export contract.

    Returns (validated_dict, None) on success where validated_dict has keys:
      name, rdl, stats
    Returns (None, (jsonify_response, status_code)) on failure.
    """
    if not isinstance(payload, dict):
        return None, (jsonify({'error': 'Import payload must be a JSON object'}), 400)

    if payload.get('export_kind') != 'character':
        return None, (jsonify({'error': 'export_kind must be "character"'}), 400)

    if payload.get('system_id') != 'roll_drauf_light':
        return None, (jsonify({'error': 'system_id must be "roll_drauf_light"'}), 400)

    if payload.get('system_version') != ROLL_DRAUF_LIGHT_VERSION:
        return None, (jsonify({
            'error': f'Unsupported system_version; expected {ROLL_DRAUF_LIGHT_VERSION}',
        }), 422)

    name = payload.get('name')
    if not name or not str(name).strip():
        return None, (jsonify({'error': 'Character name required'}), 400)

    rdl = payload.get('roll_drauf_light')
    if not isinstance(rdl, dict):
        return None, (jsonify({'error': 'roll_drauf_light payload required'}), 400)

    # --- Catalog checks ---
    species_slug = (rdl.get('species') or {}).get('slug')
    species_entry = _catalog_lookup(ROLL_DRAUF_LIGHT_SPECIES, species_slug)
    if not species_entry:
        return None, (jsonify({'error': f'Unknown species: {species_slug}'}), 422)

    faction_slug = (rdl.get('faction') or {}).get('slug')
    faction_entry = _catalog_lookup(species_entry['factions'], faction_slug)
    if not faction_entry:
        return None, (jsonify({'error': f'Unknown faction: {faction_slug}'}), 422)

    class_slug = (rdl.get('class') or {}).get('slug')
    class_entry = _catalog_lookup(ROLL_DRAUF_LIGHT_CLASSES, class_slug)
    if not class_entry:
        return None, (jsonify({'error': f'Unknown class: {class_slug}'}), 422)

    background_slug = (rdl.get('background') or {}).get('slug')
    background_entry = _catalog_lookup(ROLL_DRAUF_LIGHT_BACKGROUNDS, background_slug)
    if not background_entry:
        return None, (jsonify({'error': f'Unknown background: {background_slug}'}), 422)

    # --- Progression consistency ---
    progression = rdl.get('progression')
    if not isinstance(progression, dict):
        return None, (jsonify({'error': 'roll_drauf_light.progression required'}), 422)

    current_level = progression.get('current_level')
    level_cap = progression.get('level_cap')

    if not isinstance(current_level, int) or current_level < 1:
        return None, (jsonify({'error': 'progression.current_level must be a positive integer'}), 422)

    if not isinstance(level_cap, int) or level_cap < current_level:
        return None, (jsonify({'error': 'progression.level_cap must be >= current_level'}), 422)

    levels = progression.get('levels', {})
    for lvl in range(1, current_level + 1):
        if str(lvl) not in levels:
            return None, (jsonify({'error': f'progression.levels is missing level {lvl}'}), 422)

    stats = payload.get('stats') or {}

    return {'name': str(name).strip(), 'rdl': rdl, 'stats': stats}, None


@characters_bp.route('/characters/<int:char_id>/export', methods=['GET'])
@jwt_required()
def export_character(char_id):
    """Export a canonical Roll-Drauf-Light character as a portable JSON payload."""
    user, error = _get_current_user()
    if error:
        return error

    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if not _can_read_character(user.id, char):
        return jsonify({'error': 'Unauthorized'}), 403

    rdl = _extract_roll_drauf_light(char.character_data)
    if not rdl or rdl.get('system_id') != 'roll_drauf_light':
        return jsonify({'error': 'Not a canonical Roll-Drauf-Light character'}), 422

    payload = _build_export_payload(char)
    return jsonify(payload), 200


@characters_bp.route('/characters/import', methods=['POST'])
@limiter.limit('20 per hour')
@jwt_required()
def import_character():
    """Create a new character from a portable Roll-Drauf-Light export payload."""
    user, error = _get_current_user()
    if error:
        return error

    raw = request.get_json() or {}
    validated, error = _validate_import_payload(raw)
    if error:
        return error

    rdl = validated['rdl']
    stats = validated['stats']

    char = Character(
        user_id=user.id,
        campaign_id=None,
        name=validated['name'],
        race=rdl['species']['name'],
        class_name=rdl['class']['name'],
        background=rdl['background']['name'],
        level=stats.get('level', rdl.get('progression', {}).get('current_level', 1)),
        xp=stats.get('xp', 0),
        ac=stats.get('ac', 10),
        hp_max=stats.get('hp_max', 10),
        hp_current=stats.get('hp_max', 10),
        mana_max=stats.get('mana_max', 0),
        mana_current=stats.get('mana_max', 0),
        str_score=stats.get('str', 10),
        dex_score=stats.get('dex', 10),
        con_score=stats.get('con', 10),
        int_score=stats.get('int', 10),
        wis_score=stats.get('wis', 10),
        cha_score=stats.get('cha', 10),
        character_data={'roll_drauf_light': rdl},
    )
    db.session.add(char)
    db.session.commit()

    return jsonify({
        'message': f'Charakter "{char.name}" erfolgreich importiert.',
        'character': char.serialize(include_details=True),
    }), 201


@characters_bp.route('/characters/<int:char_id>/identity/<identity_kind>', methods=['GET'])
@jwt_required()
def get_character_identity(char_id, identity_kind):
    """Serve stored character identity media for authorized readers."""
    user, error = _get_current_user()
    if error:
        return error

    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if not _can_read_character(user.id, char):
        return jsonify({'error': 'Unauthorized'}), 403

    fields, error = _identity_fields(identity_kind)
    if error:
        return error

    storage_key = getattr(char, fields['storage_key'])
    mime_type = getattr(char, fields['mime_type']) or 'application/octet-stream'
    if not storage_key:
        return jsonify({'error': f'{identity_kind.title()} not found'}), 404

    storage = get_storage_adapter()
    try:
        content = storage.download(storage_key)
    except FileNotFoundError:
        return jsonify({'error': f'{identity_kind.title()} not found'}), 404

    response = send_file(
        BytesIO(content),
        mimetype=mime_type,
        download_name=f'{identity_kind}-{char.id}',
    )
    response.headers['Cache-Control'] = 'private, no-store, max-age=0'
    return response


@characters_bp.route('/characters/<int:char_id>/identity/<identity_kind>', methods=['POST'])
@limiter.limit('20 per hour')
@jwt_required()
def upload_character_identity(char_id, identity_kind):
    """Upload or replace character avatar/token media."""
    user, error = _get_current_user()
    if error:
        return error

    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if char.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    fields, error = _identity_fields(identity_kind)
    if error:
        return error

    file_obj = request.files.get('file')
    if not file_obj or not file_obj.filename:
        return jsonify({'error': 'No file selected'}), 400

    try:
        validation = validate_upload(file_obj, user, check_quota=False)
    except UploadError as err:
        return jsonify({'error': str(err)}), 400

    if not validation['mime_type'].startswith('image/'):
        return jsonify({'error': 'Identity uploads must be image files'}), 400

    storage = get_storage_adapter()
    previous_key = getattr(char, fields['storage_key'])
    new_key = _identity_storage_key(char, identity_kind, validation)

    try:
        storage.upload(new_key, validation['content'])
        setattr(char, fields['url'], _identity_url(char.id, identity_kind))
        setattr(char, fields['storage_key'], new_key)
        setattr(char, fields['mime_type'], validation['mime_type'])
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': f'Failed to upload {identity_kind}'}), 500

    if previous_key and previous_key != new_key:
        try:
            storage.delete(previous_key)
        except Exception:
            pass

    return jsonify({
        'message': f'{identity_kind.title()} uploaded',
        'identity_kind': identity_kind,
        'character': char.serialize(include_details=True),
    }), 200


@characters_bp.route('/characters/<int:char_id>/identity/<identity_kind>', methods=['DELETE'])
@limiter.limit('30 per hour')
@jwt_required()
def delete_character_identity(char_id, identity_kind):
    """Remove stored character avatar/token media."""
    user, error = _get_current_user()
    if error:
        return error

    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if char.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    fields, error = _identity_fields(identity_kind)
    if error:
        return error

    storage_key = getattr(char, fields['storage_key'])
    if not storage_key:
        return jsonify({'error': f'{identity_kind.title()} not found'}), 404

    storage = get_storage_adapter()
    try:
        storage.delete(storage_key)
    except Exception:
        pass

    _clear_identity(char, identity_kind)
    db.session.commit()

    return jsonify({
        'message': f'{identity_kind.title()} removed',
        'identity_kind': identity_kind,
        'character': char.serialize(include_details=True),
    }), 200


@characters_bp.route('/characters/<int:char_id>/spells', methods=['GET'])
@jwt_required()
def list_character_spells(char_id):
    user, error = _get_current_user()
    if error:
        return error
    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if not _can_read_character(user.id, char):
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify({'spells': [spell.serialize() for spell in char.spells]}), 200


@characters_bp.route('/characters/<int:char_id>/spells', methods=['POST'])
@limiter.limit('60 per hour')
@jwt_required()
def create_character_spell(char_id):
    user, error = _get_current_user()
    if error:
        return error
    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if char.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    name = str(data.get('name', '')).strip()
    if not name:
        return jsonify({'error': 'Spell name required'}), 400

    level = data.get('level', 0)
    level, error = _coerce_int(level, 'level')
    if error:
        return error

    spell = Spell(
        character_id=char.id,
        name=name,
        level=level,
        school=data.get('school'),
        casting_time=data.get('casting_time'),
        duration=data.get('duration'),
        range_distance=data.get('range'),
        is_prepared=bool(data.get('is_prepared', True)),
        is_ritual=bool(data.get('is_ritual', False)),
        description=data.get('description'),
        damage_dice=data.get('damage_dice'),
        damage_type=data.get('damage_type'),
        custom_data=data.get('custom_data') or {},
    )
    db.session.add(spell)
    db.session.commit()
    return jsonify(spell.serialize()), 201


@characters_bp.route('/characters/<int:char_id>/spells/<int:spell_id>', methods=['PUT'])
@limiter.limit('120 per hour')
@jwt_required()
def update_character_spell(char_id, spell_id):
    user, error = _get_current_user()
    if error:
        return error
    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if char.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    spell = Spell.query.filter_by(id=spell_id, character_id=char.id).first()
    if not spell:
        return jsonify({'error': 'Spell not found'}), 404

    data = request.get_json() or {}
    if 'name' in data:
        name = str(data.get('name', '')).strip()
        if not name:
            return jsonify({'error': 'Spell name required'}), 400
        spell.name = name
    if 'level' in data:
        level, error = _coerce_int(data.get('level'), 'level')
        if error:
            return error
        spell.level = level
    if 'school' in data:
        spell.school = data.get('school')
    if 'casting_time' in data:
        spell.casting_time = data.get('casting_time')
    if 'duration' in data:
        spell.duration = data.get('duration')
    if 'range' in data:
        spell.range_distance = data.get('range')
    if 'is_prepared' in data:
        spell.is_prepared = bool(data.get('is_prepared'))
    if 'is_ritual' in data:
        spell.is_ritual = bool(data.get('is_ritual'))
    if 'description' in data:
        spell.description = data.get('description')
    if 'damage_dice' in data:
        spell.damage_dice = data.get('damage_dice')
    if 'damage_type' in data:
        spell.damage_type = data.get('damage_type')
    if 'custom_data' in data:
        spell.custom_data = data.get('custom_data') or {}

    db.session.commit()
    return jsonify(spell.serialize()), 200


@characters_bp.route('/characters/<int:char_id>/spells/<int:spell_id>', methods=['DELETE'])
@limiter.limit('60 per hour')
@jwt_required()
def delete_character_spell(char_id, spell_id):
    user, error = _get_current_user()
    if error:
        return error
    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if char.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    spell = Spell.query.filter_by(id=spell_id, character_id=char.id).first()
    if not spell:
        return jsonify({'error': 'Spell not found'}), 404

    db.session.delete(spell)
    db.session.commit()
    return jsonify({'message': 'Spell deleted'}), 200


@characters_bp.route('/characters/<int:char_id>/equipment', methods=['GET'])
@jwt_required()
def list_character_equipment(char_id):
    user, error = _get_current_user()
    if error:
        return error
    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if not _can_read_character(user.id, char):
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify({'equipment': [item.serialize() for item in char.equipment]}), 200


@characters_bp.route('/characters/<int:char_id>/equipment', methods=['POST'])
@limiter.limit('60 per hour')
@jwt_required()
def create_character_equipment(char_id):
    user, error = _get_current_user()
    if error:
        return error
    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if char.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    name = str(data.get('name', '')).strip()
    if not name:
        return jsonify({'error': 'Equipment name required'}), 400

    ac_bonus = data.get('ac_bonus', 0)
    ac_bonus, error = _coerce_int(ac_bonus, 'ac_bonus')
    if error:
        return error

    item = Equipment(
        character_id=char.id,
        name=name,
        equipment_type=data.get('type'),
        rarity=data.get('rarity'),
        ac_bonus=ac_bonus,
        damage_dice=data.get('damage_dice'),
        damage_type=data.get('damage_type'),
        is_equipped=bool(data.get('is_equipped', False)),
        is_cursed=bool(data.get('is_cursed', False)),
        weight=data.get('weight'),
        cost=data.get('cost'),
        description=data.get('description'),
        special_properties=data.get('special_properties') or {},
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.serialize()), 201


@characters_bp.route('/characters/<int:char_id>/equipment/<int:item_id>', methods=['PUT'])
@limiter.limit('120 per hour')
@jwt_required()
def update_character_equipment(char_id, item_id):
    user, error = _get_current_user()
    if error:
        return error
    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if char.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    item = Equipment.query.filter_by(id=item_id, character_id=char.id).first()
    if not item:
        return jsonify({'error': 'Equipment not found'}), 404

    data = request.get_json() or {}
    if 'name' in data:
        name = str(data.get('name', '')).strip()
        if not name:
            return jsonify({'error': 'Equipment name required'}), 400
        item.name = name
    if 'type' in data:
        item.equipment_type = data.get('type')
    if 'rarity' in data:
        item.rarity = data.get('rarity')
    if 'ac_bonus' in data:
        ac_bonus, error = _coerce_int(data.get('ac_bonus'), 'ac_bonus')
        if error:
            return error
        item.ac_bonus = ac_bonus
    if 'damage_dice' in data:
        item.damage_dice = data.get('damage_dice')
    if 'damage_type' in data:
        item.damage_type = data.get('damage_type')
    if 'is_equipped' in data:
        item.is_equipped = bool(data.get('is_equipped'))
    if 'is_cursed' in data:
        item.is_cursed = bool(data.get('is_cursed'))
    if 'weight' in data:
        item.weight = data.get('weight')
    if 'cost' in data:
        item.cost = data.get('cost')
    if 'description' in data:
        item.description = data.get('description')
    if 'special_properties' in data:
        item.special_properties = data.get('special_properties') or {}

    db.session.commit()
    return jsonify(item.serialize()), 200


@characters_bp.route('/characters/<int:char_id>/equipment/<int:item_id>', methods=['DELETE'])
@limiter.limit('60 per hour')
@jwt_required()
def delete_character_equipment(char_id, item_id):
    user, error = _get_current_user()
    if error:
        return error
    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if char.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    item = Equipment.query.filter_by(id=item_id, character_id=char.id).first()
    if not item:
        return jsonify({'error': 'Equipment not found'}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Equipment deleted'}), 200


@characters_bp.route('/characters/<int:char_id>/inventory', methods=['GET'])
@jwt_required()
def list_character_inventory(char_id):
    user, error = _get_current_user()
    if error:
        return error
    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if not _can_read_character(user.id, char):
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify({'inventory': [item.serialize() for item in char.inventory]}), 200


@characters_bp.route('/characters/<int:char_id>/inventory', methods=['POST'])
@limiter.limit('60 per hour')
@jwt_required()
def create_character_inventory_item(char_id):
    user, error = _get_current_user()
    if error:
        return error
    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if char.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    name = str(data.get('name', '')).strip()
    if not name:
        return jsonify({'error': 'Inventory item name required'}), 400

    quantity = data.get('quantity', 1)
    quantity, error = _coerce_int(quantity, 'quantity')
    if error:
        return error
    if quantity <= 0:
        return jsonify({'error': 'quantity must be positive'}), 400

    item = InventoryItem(
        character_id=char.id,
        name=name,
        item_type=data.get('type'),
        quantity=quantity,
        weight_per_unit=data.get('weight_per_unit'),
        cost=data.get('cost'),
        is_consumable=bool(data.get('is_consumable', False)),
        is_cursed=bool(data.get('is_cursed', False)),
        description=data.get('description'),
        effects=data.get('effects') or {},
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.serialize()), 201


@characters_bp.route('/characters/<int:char_id>/inventory/<int:item_id>', methods=['PUT'])
@limiter.limit('120 per hour')
@jwt_required()
def update_character_inventory_item(char_id, item_id):
    user, error = _get_current_user()
    if error:
        return error
    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if char.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    item = InventoryItem.query.filter_by(id=item_id, character_id=char.id).first()
    if not item:
        return jsonify({'error': 'Inventory item not found'}), 404

    data = request.get_json() or {}
    if 'name' in data:
        name = str(data.get('name', '')).strip()
        if not name:
            return jsonify({'error': 'Inventory item name required'}), 400
        item.name = name
    if 'type' in data:
        item.item_type = data.get('type')
    if 'quantity' in data:
        quantity, error = _coerce_int(data.get('quantity'), 'quantity')
        if error:
            return error
        if quantity <= 0:
            return jsonify({'error': 'quantity must be positive'}), 400
        item.quantity = quantity
    if 'weight_per_unit' in data:
        item.weight_per_unit = data.get('weight_per_unit')
    if 'cost' in data:
        item.cost = data.get('cost')
    if 'is_consumable' in data:
        item.is_consumable = bool(data.get('is_consumable'))
    if 'is_cursed' in data:
        item.is_cursed = bool(data.get('is_cursed'))
    if 'description' in data:
        item.description = data.get('description')
    if 'effects' in data:
        item.effects = data.get('effects') or {}

    db.session.commit()
    return jsonify(item.serialize()), 200


@characters_bp.route('/characters/<int:char_id>/inventory/<int:item_id>', methods=['DELETE'])
@limiter.limit('60 per hour')
@jwt_required()
def delete_character_inventory_item(char_id, item_id):
    user, error = _get_current_user()
    if error:
        return error
    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if char.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    item = InventoryItem.query.filter_by(id=item_id, character_id=char.id).first()
    if not item:
        return jsonify({'error': 'Inventory item not found'}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Inventory item deleted'}), 200
