"""Campaign-scoped calendar endpoints; authorization is checked on every action."""
from flask import jsonify, request
from flask_jwt_extended import jwt_required

from vtt.campaigns import campaigns_bp
from vtt.campaigns import session_calendar as calendar
from vtt.campaigns.routes import _get_campaign_or_404, _get_current_user, _is_active_member, _is_dm
from vtt.extensions import db, limiter


def access(campaign_id, *, write=False):
    user, error = _get_current_user()
    if error:
        return None, error
    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return None, error
    if not (_is_dm(campaign, user.id) if write else _is_active_member(campaign, user.id)):
        return None, (jsonify(error='Kein Zugriff auf diese Kampagne.'), 403)
    return user, None


@campaigns_bp.get('/campaigns/<int:campaign_id>/session-calendar')
@jwt_required()
def session_calendar(campaign_id):
    user, error = access(campaign_id)
    if error:
        return error
    try:
        data = calendar.load_calendar(campaign_id, request.args.get('scope', 'month'),
                                      request.args.get('anchor'), request.args.get('timezone', 'Europe/Berlin'))
        db.session.commit()
        return jsonify(data)
    except ValueError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 400


@campaigns_bp.post('/campaigns/<int:campaign_id>/session-series')
@limiter.limit('40 per hour')
@jwt_required()
def create_session_series(campaign_id):
    user, error = access(campaign_id, write=True)
    if error:
        return error
    try:
        series, created = calendar.create_series(campaign_id, user.id, request.get_json(silent=True))
        db.session.commit()
        return jsonify(series=series.serialize(), created=created), 201 if created else 200
    except ValueError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 400


@campaigns_bp.post('/campaigns/<int:campaign_id>/session-series/<int:series_id>/stop')
@jwt_required()
def stop_session_series(campaign_id, series_id):
    user, error = access(campaign_id, write=True)
    if error:
        return error
    try:
        series, count = calendar.stop_series(campaign_id, series_id)
        db.session.commit()
        return jsonify(series=series.serialize(), cancelled=count)
    except ValueError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 409


@campaigns_bp.post('/campaigns/<int:campaign_id>/sessions/<int:session_id>/cancel-appointment')
@jwt_required()
def cancel_session_appointment(campaign_id, session_id):
    user, error = access(campaign_id, write=True)
    if error:
        return error
    try:
        session = calendar.cancel_appointment(campaign_id, session_id)
        db.session.commit()
        return jsonify(id=session.id, status=session.status)
    except ValueError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 409
