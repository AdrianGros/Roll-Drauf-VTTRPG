"""SRD 5.2.1 character creator API: server-side drafts, evaluation and finalizing.

The client only displays; every number that lands on a character is recomputed here
from the stored draft state by `creator_rules.evaluate`.
"""

import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from vtt.characters import sheet_link, srd_inventory, srd_manage, srd_party, srd_progression
from vtt.characters.routes import (
    _can_read_character,
    _get_character_or_404,
    _get_current_user,
    _validate_character_campaign,
)
from vtt.extensions import db, limiter
from vtt.models import Character, InventoryItem
from vtt.models.srd_creator_draft import SrdCreatorDraft
from vtt.rules_content.creator_drafts import (
    SYSTEM_ID,
    character_values,
    finalize_blockers,
    identity_name,
    is_srd_character_data,
    sanitize_state,
)
from vtt.rules_content.creator_rules import evaluate, load_creator_data
from vtt.rules_content.creator_sources import default_source_ids, pin_status, registered_sources
from vtt.utils.time import utcnow

srd_creator_bp = Blueprint('srd_creator', __name__)

MAX_OPEN_DRAFTS = 25
_STEP = re.compile(r'^[a-z0-9-]{1,32}$')


def _body():
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else None


def _bad(code, message, status=400, **extra):
    return jsonify({'error': code, 'message': message, **extra}), status


def _owned_draft(draft_id, user):
    draft = db.session.get(SrdCreatorDraft, draft_id)
    if draft is None or draft.user_id != user.id or draft.status == 'discarded':
        return None, _bad('not_found', 'Entwurf nicht gefunden.', 404)
    return draft, None


def _view(draft, data):
    evaluation = evaluate(data, draft.state or {})
    return {
        'draft': {**draft.summary(), 'state': draft.state or {}, 'sources': draft.sources},
        'evaluation': evaluation,
        'blockers': finalize_blockers(evaluation, draft.state or {}),
    }


def _invalid_state(problems):
    return _bad('invalid_state', 'Der Entwurfszustand ist ungültig.', 422, problems=problems)


@srd_creator_bp.get('/meta')
@jwt_required()
def meta():
    data = load_creator_data()
    return jsonify({
        'systemId': SYSTEM_ID,
        'rulesetId': data['rulesetId'],
        'rulesetVersion': data['rulesetVersion'],
        'maxLevel': data['maxLevel'],
        'maxOpenDrafts': MAX_OPEN_DRAFTS,
        'sources': registered_sources(),
        'defaultSources': default_source_ids(),
    })


@srd_creator_bp.get('/creator-data')
@jwt_required()
def creator_data():
    response = jsonify(load_creator_data())
    response.headers['Cache-Control'] = 'private, max-age=300'
    return response


@srd_creator_bp.post('/evaluate')
@limiter.limit('600 per hour')
@jwt_required()
def evaluate_state():
    _, error = _get_current_user()
    if error:
        return error
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    data = load_creator_data()
    state, problems = sanitize_state(body.get('state'), data)
    if problems:
        return _invalid_state(problems)
    evaluation = evaluate(data, state)
    return jsonify({'evaluation': evaluation, 'blockers': finalize_blockers(evaluation, state)})


@srd_creator_bp.get('/drafts')
@jwt_required()
def list_drafts():
    user, error = _get_current_user()
    if error:
        return error
    rows = (
        SrdCreatorDraft.query.filter_by(user_id=user.id, status='draft')
        .order_by(SrdCreatorDraft.updated_at.desc(), SrdCreatorDraft.id.desc())
        .limit(MAX_OPEN_DRAFTS)
        .all()
    )
    return jsonify({'drafts': [row.summary() for row in rows]})


@srd_creator_bp.post('/drafts')
@limiter.limit('30 per hour')
@jwt_required()
def create_draft():
    user, error = _get_current_user()
    if error:
        return error
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    data = load_creator_data()
    if SrdCreatorDraft.query.filter_by(user_id=user.id, status='draft').count() >= MAX_OPEN_DRAFTS:
        return _bad('draft_limit', f'Es sind höchstens {MAX_OPEN_DRAFTS} offene Entwürfe möglich.', 409)
    state, problems = sanitize_state(body.get('state'), data)
    if problems:
        return _invalid_state(problems)
    step = body.get('step')
    if step is not None and not (isinstance(step, str) and _STEP.match(step)):
        return _bad('invalid_step', 'Ungültiger Schritt.')
    draft = SrdCreatorDraft(
        user_id=user.id,
        step=step,
        name=identity_name(state)[:100] or None,
        state=state,
        sources=state.get('sources') or default_source_ids(),
    )
    db.session.add(draft)
    db.session.commit()
    return jsonify(_view(draft, data)), 201


@srd_creator_bp.get('/drafts/<int:draft_id>')
@jwt_required()
def get_draft(draft_id):
    user, error = _get_current_user()
    if error:
        return error
    draft, error = _owned_draft(draft_id, user)
    if error:
        return error
    return jsonify(_view(draft, load_creator_data()))


@srd_creator_bp.put('/drafts/<int:draft_id>')
@limiter.limit('900 per hour')
@jwt_required()
def update_draft(draft_id):
    user, error = _get_current_user()
    if error:
        return error
    draft, error = _owned_draft(draft_id, user)
    if error:
        return error
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    version = body.get('version')
    if type(version) is not int:
        return _bad('version_required', 'Die Entwurfsversion (version) ist erforderlich.')
    if draft.status != 'draft':
        return _bad('draft_not_editable', 'Dieser Entwurf ist bereits abgeschlossen.', 409)
    data = load_creator_data()
    if draft.version != version:
        return jsonify({'error': 'version_conflict', 'message': 'Der Entwurf wurde zwischenzeitlich geändert.', **_view(draft, data)}), 409
    values = {'version': draft.version + 1, 'updated_at': utcnow()}
    if 'state' in body:
        state, problems = sanitize_state(body['state'], data)
        if problems:
            return _invalid_state(problems)
        values.update(state=state, name=identity_name(state)[:100] or None, sources=state.get('sources') or default_source_ids())
    if 'step' in body:
        step = body['step']
        if step is not None and not (isinstance(step, str) and _STEP.match(step)):
            return _bad('invalid_step', 'Ungültiger Schritt.')
        values['step'] = step
    changed = SrdCreatorDraft.query.filter_by(id=draft.id, version=version, status='draft').update(values, synchronize_session=False)
    if changed != 1:
        db.session.rollback()
        fresh = db.session.get(SrdCreatorDraft, draft_id)
        return jsonify({'error': 'version_conflict', 'message': 'Der Entwurf wurde zwischenzeitlich geändert.', **_view(fresh, data)}), 409
    db.session.commit()
    db.session.refresh(draft)
    return jsonify(_view(draft, data))


@srd_creator_bp.delete('/drafts/<int:draft_id>')
@limiter.limit('60 per hour')
@jwt_required()
def discard_draft(draft_id):
    user, error = _get_current_user()
    if error:
        return error
    draft, error = _owned_draft(draft_id, user)
    if error:
        return error
    if draft.status != 'draft':
        return _bad('draft_not_editable', 'Ein abgeschlossener Entwurf kann nicht verworfen werden.', 409)
    changed = SrdCreatorDraft.query.filter_by(id=draft.id, status='draft').update(
        {'status': 'discarded', 'version': draft.version + 1, 'updated_at': utcnow()}, synchronize_session=False
    )
    db.session.commit()
    return jsonify({'discarded': bool(changed)})


@srd_creator_bp.post('/drafts/<int:draft_id>/finalize')
@limiter.limit('20 per hour')
@jwt_required()
def finalize_draft(draft_id):
    user, error = _get_current_user()
    if error:
        return error
    draft, error = _owned_draft(draft_id, user)
    if error:
        return error
    if draft.status == 'finalized' and draft.character_id:
        char = db.session.get(Character, draft.character_id)
        if char is not None:
            return jsonify({'character': char.serialize(include_details=True), 'alreadyFinalized': True})
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    if type(body.get('version')) is not int:
        return _bad('version_required', 'Die Entwurfsversion (version) ist erforderlich.')
    if draft.status != 'draft':
        return _bad('draft_not_editable', 'Dieser Entwurf ist bereits abgeschlossen.', 409)
    if draft.version != body['version']:
        return _bad('version_conflict', 'Der Entwurf wurde zwischenzeitlich geändert.', 409)
    data = load_creator_data()
    state = draft.state or {}
    evaluation = evaluate(data, state)
    blockers = finalize_blockers(evaluation, state)
    if blockers:
        return _bad('draft_incomplete', 'Der Entwurf ist noch nicht vollständig oder enthält Regelverstöße.', 422, blockers=blockers)
    campaign_id = body.get('campaign_id')
    campaign_error = _validate_character_campaign(user.id, campaign_id)
    if campaign_error:
        return campaign_error
    try:
        srd_party.check_ability_method(state, campaign_id)
    except srd_progression.ProgressionError as exc:
        return _progression_failure(exc)
    finalized_at = utcnow()
    values = character_values(data, state, evaluation, draft_id=draft.id, finalized_at=finalized_at.isoformat() + 'Z')
    char = Character(user_id=user.id, campaign_id=campaign_id, mana_max=0, mana_current=0, **values)
    db.session.add(char)
    db.session.flush()
    changed = SrdCreatorDraft.query.filter_by(id=draft.id, version=draft.version, status='draft').update(
        {'status': 'finalized', 'character_id': char.id, 'finalized_at': finalized_at, 'version': draft.version + 1, 'updated_at': finalized_at},
        synchronize_session=False,
    )
    if changed != 1:
        db.session.rollback()
        return _bad('version_conflict', 'Der Entwurf wurde zwischenzeitlich geändert.', 409)
    db.session.commit()
    return jsonify({'character': char.serialize(include_details=True), 'alreadyFinalized': False}), 201


@srd_creator_bp.get('/characters/<int:char_id>')
@jwt_required()
def get_srd_character(char_id):
    user, error = _get_current_user()
    if error:
        return error
    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if not _can_read_character(user.id, char):
        return _bad('forbidden', 'Kein Zugriff.', 403)
    block = (char.character_data or {}).get('srd') if is_srd_character_data(char.character_data) else None
    if not isinstance(block, dict):
        return _bad('not_srd', 'Kein SRD-Charakter.', 422)
    data = load_creator_data()
    return jsonify({
        'characterId': char.id,
        'srd': block,
        'evaluation': evaluate(data, block.get('state') or {}),
        'sourceStatus': pin_status(data, block.get('sources')),
    })


@srd_creator_bp.post('/characters/<int:char_id>/roll')
@limiter.limit('240 per hour')
@jwt_required()
def roll_from_sheet(char_id):
    user, error = _get_current_user()
    if error:
        return error
    char, error = _get_character_or_404(char_id)
    if error:
        return error
    if not sheet_link.can_roll_for(user, char):
        return _bad('forbidden', 'Nur die Besitzerin, der Besitzer oder die Spielleitung darf für diesen Charakter würfeln.', 403)
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    evaluation = sheet_link.srd_evaluation(char)
    if evaluation is None:
        return _bad('not_srd', 'Kein SRD-Charakter.', 422)
    kind, key = body.get('kind'), body.get('key')
    if kind not in sheet_link.ROLL_KINDS:
        return _bad('invalid_roll', 'Unbekannte Wurfart.', 422)
    key = key if isinstance(key, str) else None
    if kind in ('weapon_attack', 'weapon_damage'):
        spec = srd_inventory.weapon_roll_spec(
            char, evaluation, kind, key, critical=body.get('critical') is True, two_handed=body.get('twoHanded') is True)
    else:
        spec = sheet_link.roll_spec(evaluation, kind, key)
    if spec is None:
        return _bad('invalid_roll', 'Dieser Wurf existiert auf dem Bogen nicht.', 422)
    if spec.get('damage'):
        result = srd_inventory.roll_damage(spec['damage'])
        dice = spec['dice']
    else:
        result = sheet_link.roll_d20(spec['modifier'], body.get('mode') if isinstance(body.get('mode'), str) else 'normal')
        dice = sheet_link.dice_text(spec['modifier'])
    visibility = body.get('visibility') if isinstance(body.get('visibility'), str) else 'public'
    message_id = sheet_link.log_roll(user, char, spec, result, visibility)
    return jsonify({
        'label': spec['label'],
        'dice': dice,
        'result': result,
        'logged': message_id is not None,
        'messageId': message_id,
    })


def _inventory_character(char_id, *, write):
    """(user, char, error) for the inventory endpoints; write access is the owner's only."""
    user, error = _get_current_user()
    if error:
        return None, None, error
    char, error = _get_character_or_404(char_id)
    if error:
        return None, None, error
    if write and char.user_id != user.id:
        return None, None, _bad('forbidden', 'Nur die Besitzerin oder der Besitzer ändert das Inventar.', 403)
    if not write and not _can_read_character(user.id, char):
        return None, None, _bad('forbidden', 'Kein Zugriff.', 403)
    if sheet_link.srd_evaluation(char) is None:
        return None, None, _bad('not_srd', 'Kein SRD-Charakter.', 422)
    return user, char, None


def _inventory_response(char, status=200, **extra):
    payload = srd_inventory.inventory_payload(char, sheet_link.srd_evaluation(char))
    payload.update(extra)
    return jsonify(payload), status


def _inventory_failure(exc):
    db.session.rollback()
    return _bad(exc.code, exc.message, exc.status)


def _apply_inventory_change(char, action):
    """Run `action()` and store the result; refresh open table tokens so the new armor class shows up."""
    try:
        extra = action()
        db.session.commit()
    except srd_inventory.InventoryError as exc:
        return _inventory_failure(exc)
    try:
        sheet_link.push_character_to_tokens(char)
    except Exception:  # the sheet change itself is already stored
        db.session.rollback()
    return _inventory_response(char, **(extra or {}))


@srd_creator_bp.get('/characters/<int:char_id>/inventory')
@jwt_required()
def get_inventory(char_id):
    _, char, error = _inventory_character(char_id, write=False)
    if error:
        return error
    return _inventory_response(char)


@srd_creator_bp.post('/characters/<int:char_id>/inventory')
@limiter.limit('300 per hour')
@jwt_required()
def add_inventory_item(char_id):
    _, char, error = _inventory_character(char_id, write=True)
    if error:
        return error
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')

    def action():
        if isinstance(body.get('custom'), dict):
            srd_inventory.add_custom_item(char, body['custom'])
        elif isinstance(body.get('itemId'), str):
            srd_inventory.add_catalog_item(char, body['itemId'], body.get('quantity', 1))
        else:
            raise srd_inventory.InventoryError('invalid_item', 'Wähle einen Gegenstand aus dem Regelwerk oder lege einen eigenen an.')
        if isinstance(body.get('resolve'), str):
            srd_inventory.resolve_pending(char, body['resolve'])

    return _apply_inventory_change(char, action)


@srd_creator_bp.patch('/characters/<int:char_id>/inventory/<int:item_id>')
@limiter.limit('300 per hour')
@jwt_required()
def update_inventory_item(char_id, item_id):
    _, char, error = _inventory_character(char_id, write=True)
    if error:
        return error
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    row = InventoryItem.query.filter_by(id=item_id, character_id=char.id).first()
    if row is None:
        return _bad('not_found', 'Gegenstand nicht gefunden.', 404)

    def action():
        if 'quantity' in body:
            row.quantity = srd_inventory._clean_quantity(body['quantity'])
        if row.item_type == 'custom':
            if isinstance(body.get('name'), str) and body['name'].strip():
                row.name = body['name'].strip()[:100]
            if 'description' in body and (body['description'] is None or isinstance(body['description'], str)):
                row.description = (body['description'] or None) and body['description'][:1000]
            if 'weightKg' in body:
                weight = body['weightKg']
                if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not 0 <= weight <= 1000:
                    raise srd_inventory.InventoryError('invalid_weight', 'Das Gewicht muss zwischen 0 und 1000 kg liegen.')
                row.weight_per_unit = float(weight)
        if 'equipped' in body:
            if not isinstance(body['equipped'], bool):
                raise srd_inventory.InventoryError('invalid_body', 'equipped muss true oder false sein.')
            srd_inventory.set_equipped(char, row, body['equipped'])

    return _apply_inventory_change(char, action)


@srd_creator_bp.delete('/characters/<int:char_id>/inventory/<int:item_id>')
@limiter.limit('300 per hour')
@jwt_required()
def delete_inventory_item(char_id, item_id):
    _, char, error = _inventory_character(char_id, write=True)
    if error:
        return error
    row = InventoryItem.query.filter_by(id=item_id, character_id=char.id).first()
    if row is None:
        return _bad('not_found', 'Gegenstand nicht gefunden.', 404)
    return _apply_inventory_change(char, lambda: srd_inventory.remove_item(char, row))


@srd_creator_bp.put('/characters/<int:char_id>/inventory/coins')
@limiter.limit('300 per hour')
@jwt_required()
def change_coins(char_id):
    _, char, error = _inventory_character(char_id, write=True)
    if error:
        return error
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    return _apply_inventory_change(char, lambda: srd_inventory.change_coins(char, body))


@srd_creator_bp.delete('/characters/<int:char_id>/inventory/pending/<pending_id>')
@limiter.limit('300 per hour')
@jwt_required()
def dismiss_pending(char_id, pending_id):
    _, char, error = _inventory_character(char_id, write=True)
    if error:
        return error
    return _apply_inventory_change(char, lambda: srd_inventory.resolve_pending(char, pending_id))


@srd_creator_bp.post('/characters/<int:char_id>/inventory/starting-equipment')
@limiter.limit('60 per hour')
@jwt_required()
def seed_inventory(char_id):
    _, char, error = _inventory_character(char_id, write=True)
    if error:
        return error
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    packages = {}
    for field in ('classPackage', 'backgroundPackage'):
        value = body.get(field)
        if value is not None and not (isinstance(value, str) and re.fullmatch(r'[A-Z]', value)):
            return _bad('invalid_package', 'Ein Paket ist ein Buchstabe (A, B, …).')
        packages[field] = value

    def action():
        notes = srd_inventory.seed_starting_equipment(char, packages['classPackage'], packages['backgroundPackage'])
        return {'notes': notes}

    return _apply_inventory_change(char, action)


# ------------------------------------------------------------------ progression: XP, milestones, level-up

def _progression_character(char_id, *, write):
    """(user, char, can_manage, error); XP and milestones are managed by the campaign's DM, else by the owner."""
    user, error = _get_current_user()
    if error:
        return None, None, False, error
    char, error = _get_character_or_404(char_id)
    if error:
        return None, None, False, error
    if not _can_read_character(user.id, char):
        return None, None, False, _bad('forbidden', 'Kein Zugriff.', 403)
    if sheet_link.srd_evaluation(char) is None:
        return None, None, False, _bad('not_srd', 'Kein SRD-Charakter.', 422)
    if char.campaign_id:
        from vtt.socket_handlers import _is_dm

        can_manage = bool(_is_dm(char.campaign_id, user.id))
    else:
        can_manage = char.user_id == user.id
    if write == 'manage' and not can_manage:
        return None, None, False, _bad('forbidden', 'Erfahrung und Meilensteine vergibt die Spielleitung (ohne Kampagne die Besitzerin oder der Besitzer).', 403)
    if write == 'owner' and char.user_id != user.id:
        return None, None, False, _bad('forbidden', 'Nur die Besitzerin oder der Besitzer steigt die Stufe auf.', 403)
    return user, char, can_manage, None


def _progression_payload(char, user, can_manage):
    data = load_creator_data()
    last_level = srd_progression.last_level(char, data)
    return {
        'status': srd_progression.status(char, data),
        'history': srd_progression.history(char)[-50:],
        'canManage': can_manage,
        'canLevelUp': char.user_id == user.id,
        'xpTable': [{'level': row['level'], 'xp': row['xp']} for row in data['levels']],
        'multiclassOptions': srd_progression.multiclass_options(data, evaluate(data, ((char.character_data or {}).get('srd') or {}).get('state') or {})),
        'lastLevel': last_level,
        'canLevelDown': char.user_id == user.id and last_level is not None,
        'archived': srd_manage.is_archived(char),
    }


def _progression_failure(exc):
    db.session.rollback()
    return _bad(exc.code, exc.message, exc.status, **exc.extra)


@srd_creator_bp.get('/characters/<int:char_id>/progression')
@jwt_required()
def get_progression(char_id):
    user, char, can_manage, error = _progression_character(char_id, write=False)
    if error:
        return error
    return jsonify(_progression_payload(char, user, can_manage))


@srd_creator_bp.put('/characters/<int:char_id>/progression')
@limiter.limit('120 per hour')
@jwt_required()
def put_progression(char_id):
    user, char, can_manage, error = _progression_character(char_id, write='manage')
    if error:
        return error
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    try:
        srd_progression.set_progression(char, load_creator_data(), body, user_id=user.id)
        db.session.commit()
    except srd_progression.ProgressionError as exc:
        return _progression_failure(exc)
    return jsonify(_progression_payload(char, user, can_manage))


@srd_creator_bp.post('/characters/<int:char_id>/level-up/preview')
@limiter.limit('600 per hour')
@jwt_required()
def preview_level_up(char_id):
    _, char, _, error = _progression_character(char_id, write='owner')
    if error:
        return error
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    try:
        result = srd_progression.preview(char, load_creator_data(), body)
    except srd_progression.ProgressionError as exc:
        return _progression_failure(exc)
    result.pop('state')
    return jsonify(result)


@srd_creator_bp.post('/characters/<int:char_id>/level-up')
@limiter.limit('60 per hour')
@jwt_required()
def post_level_up(char_id):
    user, char, can_manage, error = _progression_character(char_id, write='owner')
    if error:
        return error
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    try:
        result = srd_progression.level_up(char, load_creator_data(), body, user_id=user.id)
        db.session.commit()
    except srd_progression.ProgressionError as exc:
        return _progression_failure(exc)
    try:
        sheet_link.push_character_to_tokens(char)
    except Exception:  # the level-up itself is already stored
        db.session.rollback()
    return jsonify({
        'level': char.level,
        'hpGain': result['hpGain'],
        'evaluation': result['evaluation'],
        **_progression_payload(char, user, can_manage),
    })


# ------------------------------------------------------------------ management: level-down, archive, duplicate, rebuild, companions

@srd_creator_bp.post('/characters/<int:char_id>/level-down')
@limiter.limit('30 per hour')
@jwt_required()
def post_level_down(char_id):
    user, char, can_manage, error = _progression_character(char_id, write='owner')
    if error:
        return error
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    try:
        result = srd_progression.level_down(char, load_creator_data(), body, user_id=user.id)
        db.session.commit()
    except srd_progression.ProgressionError as exc:
        return _progression_failure(exc)
    try:
        sheet_link.push_character_to_tokens(char)
    except Exception:  # the level-down itself is already stored
        db.session.rollback()
    return jsonify({
        'level': char.level,
        'removed': result['removed'],
        'evaluation': result['evaluation'],
        **_progression_payload(char, user, can_manage),
    })


@srd_creator_bp.post('/characters/<int:char_id>/archive')
@limiter.limit('120 per hour')
@jwt_required()
def post_archive(char_id):
    user, char, _, error = _progression_character(char_id, write='owner')
    if error:
        return error
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    try:
        srd_manage.set_archived(char, body.get('archived'), user_id=user.id)
        db.session.commit()
    except srd_progression.ProgressionError as exc:
        return _progression_failure(exc)
    return jsonify({'characterId': char.id, 'archived': srd_manage.is_archived(char)})


@srd_creator_bp.post('/characters/<int:char_id>/duplicate')
@limiter.limit('30 per hour')
@jwt_required()
def post_duplicate(char_id):
    user, char, _, error = _progression_character(char_id, write='owner')
    if error:
        return error
    try:
        copy_row = srd_manage.duplicate(char, user_id=user.id)
    except srd_progression.ProgressionError as exc:
        return _progression_failure(exc)
    db.session.add(copy_row)
    db.session.commit()
    return jsonify({'character': copy_row.serialize(include_details=True)}), 201


@srd_creator_bp.post('/characters/<int:char_id>/to-draft')
@limiter.limit('30 per hour')
@jwt_required()
def post_to_draft(char_id):
    user, char, _, error = _progression_character(char_id, write='owner')
    if error:
        return error
    if SrdCreatorDraft.query.filter_by(user_id=user.id, status='draft').count() >= MAX_OPEN_DRAFTS:
        return _bad('draft_limit', f'Es sind höchstens {MAX_OPEN_DRAFTS} offene Entwürfe möglich.', 409)
    data = load_creator_data()
    try:
        state, name, sources = srd_manage.draft_values(char, data)
    except srd_progression.ProgressionError as exc:
        return _progression_failure(exc)
    draft = SrdCreatorDraft(user_id=user.id, step='klasse', name=name, state=state, sources=sources)
    db.session.add(draft)
    db.session.commit()
    return jsonify({'draft': draft.summary()}), 201


@srd_creator_bp.get('/characters/<int:char_id>/companions')
@jwt_required()
def get_companions(char_id):
    user, char, _, error = _progression_character(char_id, write=False)
    if error:
        return error
    return jsonify({
        'companions': srd_manage.companions(char),
        'maxCompanions': srd_manage.MAX_COMPANIONS,
        'canEdit': char.user_id == user.id,
        'archived': srd_manage.is_archived(char),
        'inCampaign': bool(char.campaign_id),
        'campaignId': char.campaign_id,
    })


@srd_creator_bp.put('/characters/<int:char_id>/companions')
@limiter.limit('300 per hour')
@jwt_required()
def put_companions(char_id):
    user, char, _, error = _progression_character(char_id, write='owner')
    if error:
        return error
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    try:
        stored = srd_manage.set_companions(char, body, user_id=user.id)
        db.session.commit()
    except srd_progression.ProgressionError as exc:
        return _progression_failure(exc)
    return jsonify({'companions': stored, 'maxCompanions': srd_manage.MAX_COMPANIONS})


from vtt.characters import srd_party_routes  # noqa: E402,F401  (registers the campaign routes on this blueprint)
from vtt.characters import srd_export_routes  # noqa: E402,F401  (registers export, import, PDF and theme routes)
