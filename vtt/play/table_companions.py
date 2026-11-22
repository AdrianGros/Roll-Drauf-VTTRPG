"""Place an existing companion through a durable session/token binding."""
from uuid import UUID

from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from vtt.characters import srd_manage
from vtt.characters.srd_progression import ProgressionError
from vtt.extensions import db, limiter
from vtt.models import CampaignMap, Character, GameSession, SessionState, TokenState
from vtt.models.character_hotbar import TableRequestReceipt
from vtt.models.table_companion import TableCompanionBinding
from vtt.play.personal_actions import _character
from vtt.play.receipts import claim
from vtt.play.routes import _get_context
from vtt.play.service import is_operator_role, is_read_only_mode, is_token_visible_to, refresh_state_snapshot
from vtt.play.vision import map_world_size, token_world_xy

table_companions_bp = Blueprint('table_companions', __name__, url_prefix='/api/play')
PATH = '/campaigns/<int:campaign_id>/sessions/<int:session_id>/characters/<int:char_id>/companions'


class CompanionError(Exception):
    def __init__(self, error='companion_not_available', status=404):
        self.payload = error if isinstance(error, dict) else {'error': error}
        self.status = status


@table_companions_bp.after_request
def private(response):
    response.headers['Cache-Control'] = 'private, no-store'
    return response


@table_companions_bp.errorhandler(CompanionError)
def denied(error):
    db.session.rollback()
    identity = g.get('companion_receipt_id')
    if identity:
        receipt = db.session.get(TableRequestReceipt, identity)
        if receipt and receipt.status_code is None:
            receipt.response, receipt.status_code = error.payload, error.status
            db.session.commit()
    return jsonify(error.payload), error.status


def positive(value):
    if type(value) is not int or not 0 < value < 2**31:
        raise CompanionError('invalid_request', 400)
    return value


def scope(campaign_id, session_id, char_id, parent_id, *, lock=False):
    user, campaign, session, role = _get_context(campaign_id, session_id)
    if isinstance(role, tuple):
        response, status = role
        raise CompanionError(response.get_json(), status)
    if role != 'PLAYER' and not is_operator_role(role):
        raise CompanionError('forbidden', 403)
    if is_read_only_mode(session.status, role):
        raise CompanionError('read_only', 403)
    state_query = select(SessionState).where(SessionState.game_session_id == session.id,
                                              SessionState.campaign_id == campaign.id)
    if lock:
        state_query = state_query.with_for_update().execution_options(populate_existing=True)
    state = db.session.execute(state_query).scalar_one_or_none()
    if not state or not state.active_map_id:
        raise CompanionError()
    if lock:
        db.session.refresh(session, with_for_update=True)
        if is_read_only_mode(session.status, role):
            raise CompanionError('read_only', 403)
    db.session.get(Character, char_id, with_for_update=lock, populate_existing=True)
    char = _character(campaign.id, session.id, char_id)
    if not char:
        raise CompanionError()
    parent = db.session.get(TokenState, positive(parent_id), with_for_update=lock, populate_existing=True)
    map_ = db.session.get(CampaignMap, state.active_map_id, populate_existing=True)
    if (not map_ or map_.campaign_id != campaign.id or map_.archived_at is not None or
            not parent or parent.deleted_at is not None or parent.character_id != char.id or
            parent.owner_user_id != user.id or parent.visibility != 'public' or
            parent.campaign_id != campaign.id or parent.game_session_id != session.id or
            parent.session_state_id != state.id or parent.map_id != map_.id):
        raise CompanionError()
    return user, campaign, session, role, state, char, parent, map_


def sources(char):
    raw = (char.character_data or {}).get('srdCompanions', [])
    if not isinstance(raw, list) or len(raw) > srd_manage.MAX_COMPANIONS:
        raise CompanionError('invalid_companion_source', 422)
    try:
        for index, row in enumerate(raw):
            cleaned = srd_manage._companion(row, index)
            if not cleaned['id']:
                raise CompanionError('invalid_companion_source', 422)
        rows = srd_manage.companions(char)
    except ProgressionError:
        raise CompanionError('invalid_companion_source', 422)
    if len({row['id'] for row in rows}) != len(rows):
        raise CompanionError('invalid_companion_source', 422)
    return rows


def bound_token(binding, user, char, role, campaign_id, session_id, *, lock=False):
    if not binding:
        return None
    token = db.session.get(TokenState, binding.token_id, with_for_update=lock, populate_existing=True)
    if (not token or token.campaign_id != campaign_id or token.game_session_id != session_id or
            token.character_id is not None or token.owner_user_id != char.user_id or
            not is_token_visible_to(token, role, user.id)):
        raise CompanionError()
    return token


def adjacent(parent, map_):
    """Resolve legacy cells, then emit explicit pixel coordinates within the map."""
    grid = max(16, map_.grid_size or 32)
    width, height = map_world_size(map_)
    x, y = token_world_xy(parent, grid)
    step = grid * max(1, min(6, parent.size or 1))
    for candidate_x, candidate_y in ((x + step, y), (x - grid, y), (x, y + step), (x, y - grid)):
        if 0 <= candidate_x <= width - grid and 0 <= candidate_y <= height - grid:
            return round(candidate_x), round(candidate_y)
    raise CompanionError('no_adjacent_space', 409)


@table_companions_bp.get(PATH)
@jwt_required()
def list_companions(campaign_id, session_id, char_id):
    try:
        parent_id = positive(int(request.args.get('parent_token_id', '')))
    except (TypeError, ValueError):
        raise CompanionError('invalid_request', 400)
    user, campaign, session, role, state, char, parent, map_ = scope(campaign_id, session_id, char_id, parent_id)
    rows = sources(char)
    bindings = TableCompanionBinding.query.filter_by(game_session_id=session.id, character_id=char.id).all()
    existing = {binding.companion_id: db.session.get(TokenState, binding.token_id) for binding in bindings}
    values = []
    for row in rows:
        token = existing.get(row['id'])
        if token and (token.character_id is not None or token.owner_user_id != char.user_id or
                      not is_token_visible_to(token, role, user.id)):
            continue
        damage = max(0, token.hp_max - token.hp_current) if token and type(token.hp_max) is int and type(token.hp_current) is int else None
        values.append(dict(id=row['id'], name=row['name'], hpMax=row['hpMax'],
                           hpCurrent=max(0, row['hpMax'] - damage) if damage is not None else row['hpCurrent']))
    return jsonify(character_id=char.id, parent_token_id=parent.id, parent_version=parent.version, companions=values)


@table_companions_bp.post(PATH + '/<string:companion_id>/place')
@jwt_required()
@limiter.limit('120 per minute')
def place_companion(campaign_id, session_id, char_id, companion_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {'parent_token_id', 'parent_version', 'request_id'}:
        raise CompanionError('invalid_request', 400)
    positive(data['parent_token_id']); positive(data['parent_version'])
    try:
        data['request_id'] = str(UUID(data['request_id']))
    except (TypeError, ValueError, AttributeError):
        raise CompanionError('invalid_request', 400)
    current = scope(campaign_id, session_id, char_id, data['parent_token_id'])
    if not any(row['id'] == companion_id for row in sources(current[5])):
        raise CompanionError()
    prior = TableCompanionBinding.query.filter_by(game_session_id=session_id, character_id=char_id,
                                                 companion_id=companion_id).first()
    bound_token(prior, current[0], current[5], current[3], campaign_id, session_id)
    # Authority and source are checked before even a confirmed receipt is read.
    receipt, replay = claim(g.table_context, data['request_id'], request.path, data)
    if replay:
        payload, status = replay
        fresh = scope(campaign_id, session_id, char_id, data['parent_token_id'])
        if not any(row['id'] == companion_id for row in sources(fresh[5])):
            raise CompanionError()
        bound_token(prior, fresh[0], fresh[5], fresh[3], campaign_id, session_id)
        response = jsonify(payload); response.headers['X-Request-Replayed'] = 'true'
        return response, status
    g.companion_receipt_id = receipt.id
    user, campaign, session, role, state, char, parent, map_ = scope(campaign_id, session_id, char_id, data['parent_token_id'], lock=True)
    source = next((row for row in sources(char) if row['id'] == companion_id), None)
    if source is None:
        raise CompanionError()
    if parent.version != data['parent_version']:
        raise CompanionError('parent_version_conflict', 409)
    x, y = adjacent(parent, map_)
    binding = TableCompanionBinding.query.filter_by(game_session_id=session.id, character_id=char.id,
                                                   companion_id=companion_id).first()
    token = bound_token(binding, user, char, role, campaign.id, session.id, lock=True)
    created = not token or token.deleted_at is not None
    old_visibility = token.visibility if token else 'public'
    old_owner = token.owner_user_id if token else char.user_id
    if token:
        if type(token.hp_max) is not int or type(token.hp_current) is not int:
            raise CompanionError('companion_resources_unavailable', 409)
        damage = max(0, token.hp_max - token.hp_current)
        token.hp_current = max(0, source['hpMax'] - damage)
        token.hp_max = source['hpMax']
        token.version += 1
    else:
        token = TokenState(session_state_id=state.id, campaign_id=campaign.id, game_session_id=session.id,
                           owner_user_id=char.user_id, hp_max=source['hpMax'], hp_current=source['hpCurrent'], version=1)
        db.session.add(token)
    token.character_id = None
    token.name, token.map_id, token.x, token.y = source['name'], map_.id, x, y
    token.token_type, token.visibility, token.size = 'player', 'public', 1
    token.sight_range, token.rotation, token.deleted_at = 0, 0, None
    token.updated_by = user.id
    token.metadata_json = {'position_mode': 'pixel', 'companion': {'character_id': char.id, 'id': companion_id}}
    db.session.flush()
    if not binding:
        db.session.add(TableCompanionBinding(game_session_id=session.id, character_id=char.id,
                                             companion_id=companion_id, token_id=token.id))
    state.bump_version(); refresh_state_snapshot(state)
    payload = dict(token=token.serialize(), version=token.version, state_version=state.version,
                   companion_id=companion_id, client_event_id=data['request_id'])
    receipt.response, receipt.status_code = payload, 200
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise CompanionError('placement_conflict', 409)
    from vtt.socket_handlers import _emit_token_event
    _emit_token_event('created' if created else 'updated', campaign.id, session.id, payload,
                      visibility=token.visibility, owner_user_id=token.owner_user_id,
                      old_visibility=old_visibility, old_owner_user_id=old_owner)
    return jsonify(payload)
