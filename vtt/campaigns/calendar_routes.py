"""Calendar and date-poll endpoints. Authorization is re-evaluated on every request.

Read access = owner or *active* member (a carried Player table context may read, never
write). Write access = ``_is_dm``, which lowers DM rights under a carried Player context.
GET handlers are pure projections: they never materialize, lock or commit.
"""
from flask import jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from vtt.campaigns import campaigns_bp
from vtt.campaigns import date_polls as polls
from vtt.campaigns import session_calendar as calendar
from vtt.campaigns.routes import _get_campaign_or_404, _get_current_user, _is_active_member, _is_dm
from vtt.extensions import db, limiter

CalendarError = calendar.CalendarError


def fail(exc):
    """``message`` carries the translatable source sentence for the UI error adapter."""
    db.session.rollback()
    return jsonify(error=str(exc), message=str(exc)), getattr(exc, 'status', 400)


def access(campaign_id, *, write=False):
    user, error = _get_current_user()
    if error:
        return None, error
    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return None, error
    if not (_is_dm(campaign, user.id) if write else _is_active_member(campaign, user.id)):
        return None, fail(CalendarError(calendar.NO_ACCESS, 403))
    return user, None


def guarded(action):
    """Run ``action`` and commit. Returns (value, None) or (None, error_response)."""
    try:
        value = action()
        db.session.commit()
        return value, None
    except CalendarError as exc:
        return None, fail(exc)
    except IntegrityError:
        return None, fail(CalendarError('Die Anfrage kollidiert mit einer parallelen Änderung. Bitte neu laden.', 409))


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


# ------------------------------------------------------------ own calendar (all campaigns)

@campaigns_bp.get('/campaigns/my-session-calendar')
@limiter.limit('600 per hour')
@jwt_required()
def my_session_calendar():
    user, error = _get_current_user()
    if error:
        return error
    try:
        data = calendar.load_my_calendar(
            user.id, scope=request.args.get('scope', 'rolling30'), anchor=request.args.get('anchor'),
            tz_name=request.args.get('timezone', 'Europe/Berlin'), campaign_ids=calendar.parse_campaign_ids(request.args),
            cursor=request.args.get('cursor'), limit=calendar.parse_limit(request.args.get('limit')))
    except CalendarError as exc:
        return fail(exc)
    return jsonify(data)


@campaigns_bp.get('/campaigns/my-session-alerts')
@limiter.limit('600 per hour')
@jwt_required()
def my_session_alerts():
    user, error = _get_current_user()
    if error:
        return error
    try:
        return jsonify(calendar.load_alerts(user.id, calendar.parse_campaign_ids(request.args)))
    except CalendarError as exc:
        return fail(exc)


@campaigns_bp.post('/campaigns/my-session-calendar/materialize')
@limiter.limit('60 per hour')
@jwt_required()
def materialize_my_series():
    """Explicit, bounded DM/Co-DM POST; the hub calls it before reading, Players never."""
    user, error = _get_current_user()
    if error:
        return error
    ids = _json_body().get('campaign_ids')
    if ids is not None and (not isinstance(ids, list) or not ids or len(ids) > calendar.MAX_FILTER_IDS
                            or any(type(i) is not int or i < 1 for i in ids)):
        return fail(CalendarError('Ungültige Kampagnenauswahl.'))
    try:
        return jsonify(calendar.materialize_managed(user.id, sorted(set(ids)) if ids else None))
    except CalendarError as exc:
        return fail(exc)


# ------------------------------------------------------------ one campaign: calendar + series

@campaigns_bp.get('/campaigns/<int:campaign_id>/session-calendar')
@jwt_required()
def session_calendar(campaign_id):
    user, error = access(campaign_id)
    if error:
        return error
    try:
        return jsonify(calendar.load_calendar(campaign_id, request.args.get('scope', 'month'),
                                              request.args.get('anchor'), request.args.get('timezone', 'Europe/Berlin')))
    except CalendarError as exc:
        return fail(exc)


@campaigns_bp.post('/campaigns/<int:campaign_id>/session-series')
@limiter.limit('40 per hour')
@jwt_required()
def create_session_series(campaign_id):
    user, error = access(campaign_id, write=True)
    if error:
        return error
    result, error = guarded(lambda: _series_created(campaign_id, user.id))
    if error:
        return error
    payload, created = result
    return jsonify(series=payload, created=created), 201 if created else 200


def _series_created(campaign_id, user_id):
    series, created = calendar.create_series(campaign_id, user_id, request.get_json(silent=True))
    return series.serialize(), created


@campaigns_bp.post('/campaigns/<int:campaign_id>/session-series/materialize')
@limiter.limit('60 per hour')
@jwt_required()
def materialize_campaign_series(campaign_id):
    user, error = access(campaign_id, write=True)
    if error:
        return error
    created, error = guarded(lambda: calendar.materialize_horizon(campaign_id, user.id))
    return error or jsonify(created=created)


@campaigns_bp.post('/campaigns/<int:campaign_id>/session-series/<int:series_id>/stop')
@jwt_required()
def stop_session_series(campaign_id, series_id):
    user, error = access(campaign_id, write=True)
    if error:
        return error
    result, error = guarded(lambda: _series_stopped(campaign_id, series_id, user.id))
    if error:
        return error
    return jsonify(series=result[0], cancelled=result[1])


def _series_stopped(campaign_id, series_id, user_id):
    series, count = calendar.stop_series(campaign_id, series_id, user_id)
    return series.serialize(), count


@campaigns_bp.post('/campaigns/<int:campaign_id>/sessions/<int:session_id>/cancel-appointment')
# Same action outside ``/sessions/<id>/``: the calendar UI uses it so that cancelling an
# appointment never mints a table context (auth.js does that for session-scoped URLs).
@campaigns_bp.post('/campaigns/<int:campaign_id>/session-appointments/<int:session_id>/cancel')
@jwt_required()
def cancel_session_appointment(campaign_id, session_id):
    user, error = access(campaign_id, write=True)
    if error:
        return error
    result, error = guarded(lambda: _appointment_cancelled(campaign_id, session_id, user.id))
    return error or jsonify(id=result[0], status=result[1])


def _appointment_cancelled(campaign_id, session_id, user_id):
    session = calendar.cancel_appointment(campaign_id, session_id, user_id)
    return session.id, session.status


# ------------------------------------------------------------ date polls

@campaigns_bp.post('/campaigns/<int:campaign_id>/date-polls')
@limiter.limit('40 per hour')
@jwt_required()
def create_date_poll(campaign_id):
    user, error = access(campaign_id, write=True)
    if error:
        return error
    result, error = guarded(lambda: _poll_created(campaign_id, user.id))
    if error:
        return error
    payload, created = result
    return jsonify(poll=payload, created=created), 201 if created else 200


def _poll_created(campaign_id, user_id):
    poll, created = polls.create_poll(campaign_id, user_id, request.get_json(silent=True))
    return polls.serialize_poll(poll, user_id), created


@campaigns_bp.get('/campaigns/<int:campaign_id>/date-polls')
@jwt_required()
def list_date_polls(campaign_id):
    user, error = access(campaign_id)
    if error:
        return error
    session_id, status = request.args.get('session_id'), request.args.get('status')
    if (session_id is not None and not (session_id.isascii() and session_id.isdigit() and len(session_id) < 10)) \
            or status not in (None, 'open', 'closed', 'cancelled'):
        return fail(CalendarError('Ungültige Filter.'))
    rows, more = polls.list_polls(campaign_id, session_id=int(session_id) if session_id else None, status=status)
    return jsonify(polls=[polls.serialize_poll(p, user.id) for p in rows], more=more)


@campaigns_bp.get('/campaigns/<int:campaign_id>/date-polls/<int:poll_id>')
@jwt_required()
def get_date_poll(campaign_id, poll_id):
    user, error = access(campaign_id)
    if error:
        return error
    try:
        return jsonify(poll=polls.serialize_poll(polls.get_poll(campaign_id, poll_id), user.id))
    except CalendarError as exc:
        return fail(exc)


@campaigns_bp.put('/campaigns/<int:campaign_id>/date-polls/<int:poll_id>/options/<int:option_id>/vote')
@limiter.limit('600 per hour')
@jwt_required()
def vote_date_option(campaign_id, poll_id, option_id):
    # Reading under a carried Player context is allowed; the voter is always the authenticated user.
    user, error = access(campaign_id)
    if error:
        return error
    value = _json_body().get('value')
    payload, error = guarded(lambda: polls.serialize_poll(
        polls.set_vote(campaign_id, poll_id, option_id, user.id, value), user.id))
    return error or jsonify(poll=payload)


@campaigns_bp.post('/campaigns/<int:campaign_id>/date-polls/<int:poll_id>/finalize')
@limiter.limit('60 per hour')
@jwt_required()
def finalize_date_poll(campaign_id, poll_id):
    user, error = access(campaign_id, write=True)
    if error:
        return error
    body = _json_body()
    payload, error = guarded(lambda: _poll_finalized(campaign_id, poll_id, user.id, body))
    return error or jsonify(payload)


def _poll_finalized(campaign_id, poll_id, user_id, body):
    poll, session, changed = polls.finalize_poll(campaign_id, poll_id, user_id, body.get('expected_revision'),
                                                 body.get('option_id'))
    return dict(poll=polls.serialize_poll(poll, user_id), changed=changed,
                session=calendar.entry_payload(session, calendar.zone('UTC')))


@campaigns_bp.post('/campaigns/<int:campaign_id>/date-polls/<int:poll_id>/cancel')
@jwt_required()
def cancel_date_poll(campaign_id, poll_id):
    user, error = access(campaign_id, write=True)
    if error:
        return error
    revision = _json_body().get('expected_revision')
    if revision is not None and type(revision) is not int:
        return fail(CalendarError('Ungültiger Abstimmungsstand.'))
    payload, error = guarded(lambda: polls.serialize_poll(
        polls.cancel_poll(campaign_id, poll_id, user.id, revision), user.id))
    return error or jsonify(poll=payload)
