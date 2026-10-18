"""SRD 5.2.1 character creator API: server-side drafts, evaluation and finalizing.

The client only displays; every number that lands on a character is recomputed here
from the stored draft state by `creator_rules.evaluate`.
"""

import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from vtt.characters import sheet_link
from vtt.characters.routes import (
    _can_read_character,
    _get_character_or_404,
    _get_current_user,
    _validate_character_campaign,
)
from vtt.extensions import db, limiter
from vtt.models import Character
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
    spec = sheet_link.roll_spec(evaluation, kind, key if isinstance(key, str) else None)
    if spec is None:
        return _bad('invalid_roll', 'Dieser Wurf existiert auf dem Bogen nicht.', 422)
    result = sheet_link.roll_d20(spec['modifier'], body.get('mode') if isinstance(body.get('mode'), str) else 'normal')
    visibility = body.get('visibility') if isinstance(body.get('visibility'), str) else 'public'
    message_id = sheet_link.log_roll(user, char, spec, result, visibility)
    return jsonify({
        'label': spec['label'],
        'dice': sheet_link.dice_text(spec['modifier']),
        'result': result,
        'logged': message_id is not None,
        'messageId': message_id,
    })
