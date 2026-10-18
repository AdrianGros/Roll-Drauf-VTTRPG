"""P11 endpoints on the SRD creator blueprint: party view, campaign rules, XP awards, share links, item handouts."""

from flask import jsonify, make_response
from flask_jwt_extended import jwt_required

from vtt.characters import sheet_link, srd_inventory, srd_party
from vtt.characters.routes import _get_character_or_404, _get_current_user, _is_active_campaign_member
from vtt.characters.srd_creator import _apply_inventory_change, _bad, _body, srd_creator_bp
from vtt.characters.srd_progression import ProgressionError
from vtt.extensions import db, limiter
from vtt.models import Campaign, InventoryItem
from vtt.socket_handlers import _is_dm


def _campaign_member(campaign_id, *, dm):
    """(user, campaign, is_dm, error); `dm=True` additionally demands the DM role."""
    user, error = _get_current_user()
    if error:
        return None, None, False, error
    campaign = db.session.get(Campaign, campaign_id)
    if campaign is None or campaign.deleted_at or not _is_active_campaign_member(user.id, campaign_id):
        return None, None, False, _bad('not_found', 'Kampagne nicht gefunden.', 404)
    is_dm = bool(_is_dm(campaign_id, user.id))
    if dm and not is_dm:
        return None, None, False, _bad('forbidden', 'Das darf nur die Spielleitung.', 403)
    return user, campaign, is_dm, None


def _failure(exc):
    db.session.rollback()
    return _bad(exc.code, exc.message, exc.status, **getattr(exc, 'extra', {}))


def _owner_character(char_id):
    user, error = _get_current_user()
    if error:
        return None, None, error
    char, error = _get_character_or_404(char_id)
    if error:
        return None, None, error
    if char.user_id != user.id:
        return None, None, _bad('forbidden', 'Nur die Besitzerin oder der Besitzer verwaltet die Freigabe.', 403)
    if sheet_link.srd_evaluation(char) is None:
        return None, None, _bad('not_srd', 'Kein SRD-Charakter.', 422)
    return user, char, None


def _dm_character(char_id):
    user, error = _get_current_user()
    if error:
        return None, None, error
    char, error = _get_character_or_404(char_id)
    if error:
        return None, None, error
    if not char.campaign_id or not _is_dm(char.campaign_id, user.id):
        return None, None, _bad('forbidden', 'Das darf nur die Spielleitung der Kampagne des Charakters.', 403)
    if sheet_link.srd_evaluation(char) is None:
        return None, None, _bad('not_srd', 'Kein SRD-Charakter.', 422)
    return user, char, None


# ------------------------------------------------------------------ party and campaign rules

@srd_creator_bp.get('/campaigns/<int:campaign_id>/party')
@limiter.limit('600 per hour')
@jwt_required()
def get_party(campaign_id):
    user, campaign, is_dm, error = _campaign_member(campaign_id, dm=False)
    if error:
        return error
    return jsonify({
        'campaign': {'id': campaign.id, 'name': campaign.name},
        'isDm': is_dm,
        'rules': srd_party.campaign_rules(campaign.id),
        'characters': srd_party.party(campaign, viewer_is_dm=is_dm),
    })


@srd_creator_bp.get('/campaigns/<int:campaign_id>/rules')
@jwt_required()
def get_campaign_rules(campaign_id):
    _, campaign, is_dm, error = _campaign_member(campaign_id, dm=False)
    if error:
        return error
    return jsonify({**srd_party.campaign_rules(campaign.id), 'canEdit': is_dm})


@srd_creator_bp.put('/campaigns/<int:campaign_id>/rules')
@limiter.limit('60 per hour')
@jwt_required()
def put_campaign_rules(campaign_id):
    user, campaign, _, error = _campaign_member(campaign_id, dm=True)
    if error:
        return error
    try:
        srd_party.set_campaign_rules(campaign.id, _body(), user_id=user.id)
        db.session.commit()
    except ProgressionError as exc:
        return _failure(exc)
    return jsonify({**srd_party.campaign_rules(campaign.id), 'canEdit': True})


@srd_creator_bp.post('/campaigns/<int:campaign_id>/award')
@limiter.limit('60 per hour')
@jwt_required()
def post_award(campaign_id):
    user, campaign, _, error = _campaign_member(campaign_id, dm=True)
    if error:
        return error
    try:
        changed = srd_party.award(campaign, _body(), user_id=user.id)
        db.session.commit()
    except ProgressionError as exc:
        return _failure(exc)
    return jsonify({'changed': changed, 'characters': srd_party.party(campaign, viewer_is_dm=True)})


# ------------------------------------------------------------------ share link

def _sharing_payload(char):
    return srd_party.sharing_info(char)


@srd_creator_bp.get('/characters/<int:char_id>/sharing')
@jwt_required()
def get_sharing(char_id):
    _, char, error = _owner_character(char_id)
    if error:
        return error
    return jsonify(_sharing_payload(char))


@srd_creator_bp.put('/characters/<int:char_id>/sharing')
@limiter.limit('60 per hour')
@jwt_required()
def put_sharing(char_id):
    _, char, error = _owner_character(char_id)
    if error:
        return error
    body = _body() or {}
    try:
        srd_party.set_sharing(char, body.get('enabled'), regenerate=body.get('regenerate', False))
        db.session.commit()
    except ProgressionError as exc:
        return _failure(exc)
    return jsonify(_sharing_payload(char))


@srd_creator_bp.get('/shared/<token>')
@limiter.limit('120 per hour')
def get_shared(token):
    char = srd_party.find_shared(token)
    if char is None:
        return _bad('not_found', 'Dieser Link ist nicht (mehr) gültig.', 404)
    response = make_response(jsonify(srd_party.shared_view(char)))
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


# ------------------------------------------------------------------ DM handouts

@srd_creator_bp.get('/handout/items')
@limiter.limit('600 per hour')
@jwt_required()
def search_handout_items():
    from flask import request

    _, error = _get_current_user()
    if error:
        return error
    try:
        items = srd_party.search_items(request.args.get('kind', 'gear'), request.args.get('q'))
    except srd_inventory.InventoryError as exc:
        return _bad(exc.code, exc.message, exc.status)
    return jsonify({'items': items})


@srd_creator_bp.post('/characters/<int:char_id>/handout')
@limiter.limit('300 per hour')
@jwt_required()
def post_handout(char_id):
    user, char, error = _dm_character(char_id)
    if error:
        return error
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    return _apply_inventory_change(char, lambda: {'handedOut': [row.name for row in srd_party.hand_out(char, body, user_id=user.id)]})


@srd_creator_bp.delete('/characters/<int:char_id>/handout/<int:item_id>')
@limiter.limit('300 per hour')
@jwt_required()
def delete_handout(char_id, item_id):
    user, char, error = _dm_character(char_id)
    if error:
        return error
    row = db.session.get(InventoryItem, item_id)
    if row is None or row.character_id != char.id:
        return _bad('not_found', 'Gegenstand nicht gefunden.', 404)
    return _apply_inventory_change(char, lambda: srd_party.take_back(char, row, user_id=user.id))
