"""Character and character-sheet endpoints."""

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from vtt_app.characters import characters_bp
from vtt_app.extensions import db, limiter
from vtt_app.models import (
    Campaign,
    CampaignMember,
    Character,
    Equipment,
    InventoryItem,
    Spell,
    User,
)
from vtt_app.utils.time import utcnow


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
        str_score=data.get('str', 10),
        dex_score=data.get('dex', 10),
        con_score=data.get('con', 10),
        int_score=data.get('int', 10),
        wis_score=data.get('wis', 10),
        cha_score=data.get('cha', 10),
        token_url=data.get('token_url')
    )
    db.session.add(char)
    db.session.commit()

    return jsonify(char.serialize(include_details=True)), 201


@characters_bp.route('/characters/mine', methods=['GET'])
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
    if 'token_url' in data:
        char.token_url = data['token_url']

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
