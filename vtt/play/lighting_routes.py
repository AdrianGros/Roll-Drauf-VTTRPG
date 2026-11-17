"""Role-authorized image projections; preview never mutates player exploration."""
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from vtt.extensions import db, limiter
from vtt.models import SceneWall, SceneLight, TokenState, FogOfWarState
from vtt.play import play_bp
from vtt.play.routes import _get_context, _get_active_map_or_404
from vtt.play.service import is_operator_role, is_token_visible_to
from vtt.play.scene_settings import view_settings
from vtt.play.illumination import render_overlay
from vtt.play.vision import visible_token_ids, token_world_xy, map_world_size


@play_bp.get('/campaigns/<int:campaign_id>/sessions/<int:session_id>/vision/illumination')
@jwt_required()
@limiter.limit('120 per minute', key_func=lambda: str(get_jwt_identity()))
def illumination_projection(campaign_id,session_id):
    user,campaign,session,role=_get_context(campaign_id,session_id)
    if isinstance(role,tuple):return role
    state,map_,error=_get_active_map_or_404(campaign,session)
    if error:return error
    options=view_settings(map_.id)
    response=dict(map_id=map_.id,presentation=options,preview=False,overlay=None)
    preview=request.args.get('token_id')
    if preview is not None and not is_operator_role(role):return jsonify(error='forbidden'),403
    tokens=TokenState.query.filter_by(campaign_id=campaign_id,game_session_id=session_id,map_id=map_.id,deleted_at=None).all()
    if preview is not None:
        try:chosen=int(preview)
        except (ValueError,TypeError):return jsonify(error='invalid_token'),400
        tokens=[t for t in tokens if t.id==chosen]
        if not tokens:return jsonify(error='not_found'),404
        response.update(preview=True,preview_name=tokens[0].name)
    elif is_operator_role(role):
        return jsonify(response)
    else:
        tokens=[t for t in tokens if t.owner_user_id==user.id and is_token_visible_to(t,role,user.id)]
    walls=SceneWall.query.filter_by(campaign_map_id=map_.id).all()
    lights=SceneLight.query.filter_by(campaign_map_id=map_.id).all()
    if preview is not None:
        origin=tokens[0]
        others=TokenState.query.filter_by(campaign_id=campaign_id,game_session_id=session_id,map_id=map_.id,deleted_at=None).all()
        visible=set(visible_token_ids(*token_world_xy(origin,map_.grid_size),origin.sight_range,walls,lights,others,map_.grid_size))
        response['visible_token_ids']=[t.id for t in others if t.id in visible and is_token_visible_to(t,'PLAYER',origin.owner_user_id)]
    if not options['dynamic_lighting'] or not lights and not map_.fog_enabled:
        return jsonify(response)
    fog=None if preview else FogOfWarState.query.filter_by(user_id=user.id,campaign_map_id=map_.id).first()
    response['overlay']=render_overlay(*map_world_size(map_),walls,lights,tokens,ambient=options['ambient'],
        explored=fog.explored_cells if fog else (),grid_size=map_.grid_size,fog_enabled=map_.fog_enabled)
    return jsonify(response)
