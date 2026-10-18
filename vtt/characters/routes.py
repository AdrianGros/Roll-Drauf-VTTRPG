"""Character and character-sheet endpoints."""

from io import BytesIO

from flask import current_app, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from sqlalchemy import or_

from vtt.characters import characters_bp
from vtt.extensions import db, limiter
from vtt.models import (
    Campaign,
    CampaignMember,
    Character,
    Equipment,
    InventoryItem,
    SessionCharacterAssignment,
    TokenState,
    Spell,
    User,
)
from vtt.storage import get_storage_adapter
from vtt.upload_security import UploadError, validate_upload
from vtt.utils.time import utcnow
from vtt.rules_content.creator_drafts import is_srd_character_data


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

# Derived by the SRD creator; the generic character API must not overwrite them.
SRD_MANAGED_FIELDS = (
    'race', 'class', 'background', 'level', 'xp', 'ac', 'hp_max', 'mana_max',
    'str', 'dex', 'con', 'int', 'wis', 'cha', 'character_data',
)


def _srd_write_guard(data, existing=None):
    if existing is not None and is_srd_character_data(existing.character_data):
        locked = [field for field in SRD_MANAGED_FIELDS if field in data]
        if locked:
            return jsonify({
                'error': 'srd_character_managed',
                'message': 'Dieser SRD-Charakter wird über den Regelwerk-Ersteller geändert.',
                'fields': locked,
            }), 409
    elif is_srd_character_data(data.get('character_data')):
        return jsonify({
            'error': 'srd_character_forbidden',
            'message': 'SRD-Charaktere entstehen nur über den Regelwerk-Ersteller.',
        }), 400
    return None


def _get_current_user():
    user_id = get_jwt_identity()
    if not user_id:
        return None, (jsonify({'error': 'Authentication required'}), 401)

    user = db.session.get(User, int(user_id))
    if not user or not user.is_usable():
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
    if not campaign or campaign.deleted_at:
        return False
    if campaign.owner_id == user_id:
        return True
    member = CampaignMember.query.filter_by(
        user_id=user_id,
        campaign_id=campaign_id,
        status='active',
    ).first()
    return member is not None


def _validate_character_campaign(user_id, campaign_id):
    if campaign_id is None:
        return None
    if type(campaign_id) is not int or campaign_id <= 0:
        return jsonify({'error': 'campaign_id must be a positive integer or null'}), 400
    campaign = db.session.get(Campaign, campaign_id)
    if not campaign or campaign.deleted_at:
        return jsonify({'error': 'Campaign not found'}), 404
    if not _is_active_campaign_member(user_id, campaign_id):
        return jsonify({'error': 'Active campaign membership required'}), 403
    return None


def _can_read_character(user_id, char):
    if char.user_id == user_id:
        return True
    if char.campaign_id and _is_active_campaign_member(user_id, char.campaign_id):
        return True
    return False


def _serialize_character_sheet(char):
    from vtt.ce_compat import character_projection
    projected = character_projection(char)
    if projected is not None:
        return {"character": projected, "items": projected["items"]}
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

    error = _srd_write_guard(data)
    if error:
        return error

    # Optional: attach to campaign if campaign_id provided
    campaign_id = data.get('campaign_id')
    error = _validate_character_campaign(user_id, campaign_id)
    if error:
        return error

    is_discoverable = bool(data.get('is_discoverable', False))

    char = Character(
        user_id=user_id,
        campaign_id=campaign_id,
        name=data.get('name'),
        is_discoverable=is_discoverable,
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


@characters_bp.route('/characters/shared', methods=['GET'])
@limiter.limit('600 per hour')
@jwt_required()
def list_shared_characters():
    """Characters explicitly assigned to the caller's active campaigns."""
    user, error = _get_current_user()
    if error:
        return error
    memberships = db.session.query(CampaignMember.campaign_id).filter_by(
        user_id=user.id, status='active')
    rows = (db.session.query(Character, Campaign).join(
        Campaign, Character.campaign_id == Campaign.id).filter(
        Character.deleted_at.is_(None), Character.user_id != user.id,
        Campaign.deleted_at.is_(None),
        or_(Campaign.owner_id == user.id, Campaign.id.in_(memberships)),
    ).order_by(Campaign.name, Character.name).all())
    return jsonify([
        {**char.serialize(), 'campaign_name': campaign.name,
         'owner_username': char.user.username}
        for char, campaign in rows
    ]), 200


@characters_bp.route('/characters/<int:char_id>/campaign', methods=['PUT'])
@limiter.limit('60 per hour')
@jwt_required()
def assign_character_campaign(char_id):
    """Let the owner share a character with one of their campaign groups."""
    user, error = _get_current_user()
    if error:
        return error
    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if char.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json() or {}
    if 'campaign_id' not in data:
        return jsonify({'error': 'campaign_id required'}), 400
    campaign_id = data['campaign_id']
    error = _validate_character_campaign(user.id, campaign_id)
    if error:
        return error
    if char.campaign_id != campaign_id:
        if char.is_party_stash:
            return jsonify({'error': 'Der gemeinsame Vorrat bleibt seiner Kampagne zugeordnet.'}), 409
        assigned = SessionCharacterAssignment.query.filter_by(character_id=char.id).first()
        token = TokenState.query.filter_by(character_id=char.id, deleted_at=None).first()
        if assigned or token:
            return jsonify({'error': 'Entferne zuerst die Sitzungszuweisungen und Tokens dieses Charakters in der bisherigen Kampagne.'}), 409
        char.campaign_id = campaign_id
        db.session.commit()
    return jsonify(char.serialize()), 200


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
    error = _srd_write_guard(data, existing=char)
    if error:
        return error

    # Update allowed fields
    if 'name' in data:
        char.name = data['name']
    if 'race' in data:
        char.race = data['race']
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
    try:
        from vtt.characters import sheet_link
        sheet_link.push_character_to_tokens(char)
    except Exception:
        db.session.rollback()
        current_app.logger.exception('token push after sheet update failed')
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


@characters_bp.route('/characters/<int:char_id>/export', methods=['GET'])
@jwt_required()
def export_character(char_id):
    """Export an explicitly versioned D&D character as portable JSON."""
    user, error = _get_current_user()
    if error:
        return error

    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if not _can_read_character(user.id, char):
        return jsonify({'error': 'Unauthorized'}), 403

    from vtt.characters.dnd5e_portable import PortableError, export_payload
    try:
        return jsonify(export_payload(char)), 200
    except PortableError as exc:
        return jsonify({'error': str(exc)}), exc.status


@characters_bp.route('/characters/import', methods=['POST'])
@limiter.limit('20 per hour')
@jwt_required()
def import_character():
    """Create an owned character from a supported D&D portable export."""
    user, error = _get_current_user()
    if error:
        return error

    raw = request.get_json() or {}
    if isinstance(raw, dict) and raw.get('export_kind') == 'dnd5e_character':
        from vtt.characters.dnd5e_portable import PortableError, import_payload
        try:
            char = import_payload(raw, user)
        except PortableError as exc:
            return jsonify({'error': str(exc)}), exc.status
        return jsonify({
            'message': f'Charakter "{char.name}" erfolgreich importiert.',
            'character': char.serialize(include_details=True),
        }), 201
    return jsonify({
        'error': 'Unbekanntes Exportformat. Neue Charaktere entstehen im Regelwerk-Ersteller (/srd-creator).',
    }), 400


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
