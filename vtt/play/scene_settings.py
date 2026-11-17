"""Authorized map presentation and campaign-persistent map-page hierarchy."""
from flask import g, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError
from vtt.extensions import db
from vtt.models import Campaign, CampaignMap, SceneLayer, FogOfWarState, TokenState
from vtt.models.ui_playtable import MapViewSettings, PageHierarchyState, MapPageParent
from vtt.play import play_bp
from vtt.play.routes import _get_context
from vtt.play.service import is_operator_role, recalculate_fog_for_all_owners


def view_settings(map_id):
    row = db.session.get(MapViewSettings, map_id)
    return dict(revision=row.revision if row else 0, grid_visible=row.grid_visible if row else True,
                dynamic_lighting=row.dynamic_lighting if row else True, ambient=row.ambient if row else 25)


def _notify(campaign_id, session_id, kind):
    from vtt.extensions import socketio
    from vtt.utils.realtime import session_room, build_event_envelope
    from vtt.models import GameSession
    for target in GameSession.query.filter_by(campaign_id=campaign_id).all():
        socketio.emit('scene:scale_updated', build_event_envelope(campaign_id, target.id,
            {'change': kind}), room=session_room(campaign_id, target.id))


@play_bp.route('/campaigns/<int:campaign_id>/sessions/<int:session_id>/maps/<int:map_id>/presentation', methods=['GET', 'PUT'])
@jwt_required()
def map_presentation(campaign_id, session_id, map_id):
    user, campaign, session, role = _get_context(campaign_id, session_id)
    if isinstance(role, tuple):
        return role
    row = CampaignMap.query.filter_by(id=map_id, campaign_id=campaign_id, archived_at=None).with_for_update().first()
    if not row:
        return jsonify(error='not_found'), 404
    if request.method == 'GET':
        return jsonify(presentation=view_settings(row.id), grid_size=row.grid_size, fog_enabled=row.fog_enabled)
    if not is_operator_role(role):
        return jsonify(error='forbidden'), 403
    body = request.get_json(silent=True)
    allowed = {'revision','grid_size','grid_visible','dynamic_lighting','ambient','fog_enabled','confirm_fog_reset'}
    if not isinstance(body, dict) or set(body)-allowed or type(body.get('revision')) is not int:
        return jsonify(error='invalid_settings'), 400
    current = view_settings(row.id)
    if body['revision'] != current['revision']:
        return jsonify(error='version_conflict'), 409
    size = body.get('grid_size', row.grid_size)
    ambient = body.get('ambient', current['ambient'])
    if type(size) is not int or not 16 <= size <= 300 or type(ambient) is not int or not 0 <= ambient <= 100:
        return jsonify(error='invalid_settings'), 422
    for key in ['grid_visible','dynamic_lighting','fog_enabled']:
        if key in body and type(body[key]) is not bool:
            return jsonify(error='invalid_settings'), 400
    fog_rows = FogOfWarState.query.filter_by(campaign_map_id=row.id).all()
    if size != row.grid_size and any(f.explored_cells for f in fog_rows) and body.get('confirm_fog_reset') is not True:
        return jsonify(error='fog_reset_confirmation_required', message='Die neue Rastergröße setzt die bisherige Aufklärung dieser Karte zurück. Bitte ausdrücklich bestätigen.'), 409
    if size != row.grid_size:
        # Legacy tokens use grid coordinates in the renderer. Freeze their world
        # position before the grid changes so existing tokens do not jump.
        from vtt.play.vision import token_world_xy, map_world_size
        row.width,row.height=map_world_size(row)
        row.light_rules={**(row.light_rules or {}),'dimensions_mode':'pixel'}
        for token in TokenState.query.filter_by(map_id=row.id,deleted_at=None).order_by(TokenState.id).with_for_update().all():
            x,y=token_world_xy(token,row.grid_size)
            token.x,token.y=x,y
            token.metadata_json={**(token.metadata_json or {}),'position_mode':'pixel'}
            token.version+=1;token.updated_by=user.id
        for fog in fog_rows:
            fog.explored_cells = []; fog.visible_cells = []; fog.version += 1
    row.grid_size = size
    row.fog_enabled = body.get('fog_enabled', row.fog_enabled)
    setting = db.session.get(MapViewSettings, row.id)
    if not setting:
        setting = MapViewSettings(map_id=row.id, revision=0)
        db.session.add(setting)
    setting.revision = current['revision'] + 1
    setting.grid_visible = body.get('grid_visible', current['grid_visible'])
    setting.dynamic_lighting = body.get('dynamic_lighting', current['dynamic_lighting'])
    setting.ambient = ambient
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback(); return jsonify(error='version_conflict'), 409
    from vtt.play.service import ensure_session_state
    from vtt.play.fog_delivery import emit_private_fog
    state = ensure_session_state(campaign, session)
    for owner_id, fog in recalculate_fog_for_all_owners(row, state).items():
        emit_private_fog(campaign_id, session_id, owner_id, fog)
    _notify(campaign_id, session_id, 'presentation')
    return jsonify(presentation=view_settings(row.id), grid_size=row.grid_size, fog_enabled=row.fog_enabled)


def hierarchy_projection(layers, campaign_id):
    """Return only parent layer IDs present in the caller's permitted projection."""
    by_map = {layer.campaign_map_id: layer.id for layer in layers}
    rows = {r.map_id:r for r in MapPageParent.query.filter_by(campaign_id=campaign_id).all()}
    result = {}
    for layer in layers:
        row = rows.get(layer.campaign_map_id)
        parent = row.parent_map_id if row else None
        visited = set()
        while parent is not None and parent not in by_map:
            if parent in visited:
                parent = None; break
            visited.add(parent)
            parent = rows[parent].parent_map_id if parent in rows else None
        result[layer.id] = dict(parent_layer_id=by_map.get(parent))
    state = db.session.get(PageHierarchyState, campaign_id)
    return result, state.revision if state else 0


@play_bp.route('/campaigns/<int:campaign_id>/sessions/<int:session_id>/scene-stack/layers/<int:layer_id>/parent', methods=['PUT'])
@jwt_required()
def set_page_parent(campaign_id, session_id, layer_id):
    user, campaign, session, role = _get_context(campaign_id, session_id)
    if isinstance(role, tuple):
        return role
    if not is_operator_role(role):
        return jsonify(error='forbidden'), 403
    from vtt.play.service import get_scene_stack
    stack = get_scene_stack(session_id)
    if not stack:
        return jsonify(error='not_found'), 404
    layers = SceneLayer.query.filter_by(scene_stack_id=stack.id).all()
    by_id = {row.id:row for row in layers}
    layer = by_id.get(layer_id)
    body = request.get_json(silent=True)
    if not layer or not isinstance(body, dict) or set(body) != {'parent_layer_id','revision'}:
        return jsonify(error='invalid_parent'), 400
    parent_id = body['parent_layer_id']
    if type(body['revision']) is not int or parent_id is not None and type(parent_id) is not int:
        return jsonify(error='invalid_parent'), 400
    parent = by_id.get(parent_id) if parent_id is not None else None
    if parent_id is not None and not parent:
        return jsonify(error='not_found'), 404
    # One stable campaign lock serializes both the first hierarchy edit and later edits.
    db.session.query(Campaign).filter_by(id=campaign_id).with_for_update().one()
    state = db.session.get(PageHierarchyState, campaign_id, populate_existing=True)
    if body['revision'] != (state.revision if state else 0):
        return jsonify(error='version_conflict'), 409
    rows = {r.map_id:r for r in MapPageParent.query.filter_by(campaign_id=campaign_id).all()}
    ancestor = parent.campaign_map_id if parent else None
    visited = set()
    while ancestor is not None:
        if ancestor == layer.campaign_map_id or ancestor in visited or len(visited) >= 100:
            return jsonify(error='hierarchy_cycle'), 422
        visited.add(ancestor)
        ancestor = rows[ancestor].parent_map_id if ancestor in rows else None
    row = rows.get(layer.campaign_map_id)
    if not row:
        row = MapPageParent(map_id=layer.campaign_map_id, campaign_id=campaign_id)
        db.session.add(row)
    row.parent_map_id = parent.campaign_map_id if parent else None
    if not state:
        state = PageHierarchyState(campaign_id=campaign_id, revision=0); db.session.add(state)
    state.revision += 1
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback(); return jsonify(error='version_conflict'), 409
    _notify(campaign_id, session_id, 'hierarchy')
    return jsonify(revision=state.revision, layer_id=layer_id, parent_layer_id=parent_id)
