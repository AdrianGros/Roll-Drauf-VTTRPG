"""DM-authored physical map scale, delivered to both authorized surfaces."""
from decimal import Decimal
import math
from flask import g,jsonify,request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError
from vtt.extensions import db,limiter,socketio
from vtt.models import CampaignMap
from vtt.models.campaign_map_scale import CampaignMapScale,scale_for
from vtt.play import play_bp
from vtt.play.contexts import current_role
from vtt.play.service import is_operator_role
from vtt.utils.realtime import build_event_envelope,session_room
from vtt.utils.time import utcnow


def resource(campaign_id,map_id):
    row=db.session.get(CampaignMap,map_id)
    return row if row and row.campaign_id==campaign_id and row.archived_at is None else None


@play_bp.route('/campaigns/<int:campaign_id>/sessions/<int:session_id>/maps/<int:map_id>/scale',methods=['GET','PUT'])
@jwt_required()
@limiter.limit('300 per hour')
def map_scale(campaign_id,session_id,map_id):
    context=g.table_context
    if not resource(campaign_id,map_id):return jsonify(error='not_found',message='Karte nicht gefunden.'),404
    if request.method=='GET':return jsonify(scale=scale_for(map_id))
    if not is_operator_role(current_role(campaign_id,context.user_id,session_id)):
        return jsonify(error='forbidden',message='Den Kartenmaßstab kann nur die Spielleitung im DM-Kontext ändern.'),403
    body=request.get_json(silent=True)
    if not isinstance(body,dict) or set(body)!={'revision','meters_per_square'} or type(body.get('revision')) is not int:
        return jsonify(error='invalid_scale',message='Version und Meter pro Rasterfeld angeben.'),400
    value=body['meters_per_square']
    if value is not None:
        if type(value) not in (int,float) or not math.isfinite(value) or not .01<=value<=1000000:
            return jsonify(error='invalid_scale',message='Maßstab: 0,01 bis 1.000.000 Meter pro Feld oder unkalibriert.'),422
        value=Decimal(str(value))
        if value!=value.quantize(Decimal('.0001')):
            return jsonify(error='invalid_scale',message='Höchstens vier Nachkommastellen verwenden.'),422
    row=db.session.get(CampaignMapScale,map_id)
    if body['revision']!=(row.revision if row else 0):return jsonify(error='version_conflict',message='Maßstab inzwischen geändert. Bitte neu laden.'),409
    if row:
        updated=CampaignMapScale.query.filter_by(map_id=map_id,revision=row.revision).update(
            {'meters_per_square':value,'revision':row.revision+1,'updated_by':context.user_id,'updated_at':utcnow()},synchronize_session=False)
        if updated!=1:
            db.session.rollback();return jsonify(error='version_conflict',message='Maßstab inzwischen geändert.'),409
    else:db.session.add(CampaignMapScale(map_id=map_id,meters_per_square=value,revision=1,updated_by=context.user_id))
    try:db.session.commit()
    except IntegrityError:
        db.session.rollback();return jsonify(error='version_conflict',message='Maßstab inzwischen geändert.'),409
    result=scale_for(map_id)
    socketio.emit('scene:scale_updated',build_event_envelope(campaign_id,session_id,{'map_id':map_id,'scale':result}),room=session_room(campaign_id,session_id))
    return jsonify(scale=result)
