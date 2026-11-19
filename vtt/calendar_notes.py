"""Private day notes, durable in-app reminders, and ordinary campaign-backed One-Shots."""
import hashlib
import json
import uuid
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from vtt.campaigns import session_calendar as calendar
from vtt.campaigns.routes import _get_current_user, _is_dm
from vtt.extensions import db, limiter
from vtt.models import Campaign, CampaignMember, GameSession, SessionOccurrence, User
from vtt.models.calendar_note import CalendarNote, CalendarOneShot
from vtt.permissions import can_create_campaign
from vtt.utils.time import utcnow

calendar_notes_bp = Blueprint('calendar_notes', __name__, url_prefix='/api/calendar')
COLORS = ('red', 'orange', 'yellow', 'green', 'teal', 'blue', 'purple')
MAX_DAY_NOTES = 20
MAX_USER_NOTES = 2000
PAGE_SIZE = 200


def error(message, status=400):
    db.session.rollback()
    return jsonify(error=message, message=message), status


def body():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise calendar.CalendarError('Bitte gültige Formulardaten eingeben.')
    return value


def request_key(value):
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise calendar.CalendarError('Ungültige Anfragekennung.') from None


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str).encode()).hexdigest()


def local_instant(value, tz_name, fold=None):
    """Strict round-trip conversion; ambiguous wall times need the user's explicit fold."""
    tz = calendar.zone(tz_name)
    try:
        local = datetime.fromisoformat(value)
        if len(value) != 16 or local.tzinfo or local.isoformat(timespec='minutes') != value:
            raise ValueError()
    except (TypeError, ValueError, OverflowError):
        raise calendar.CalendarError('Bitte Datum und Uhrzeit vollständig eingeben.') from None
    candidates = []
    for occurrence in (0, 1):
        aware = local.replace(tzinfo=tz, fold=occurrence)
        instant = aware.astimezone(timezone.utc)
        if instant.astimezone(tz).replace(tzinfo=None) == local:
            candidates.append((occurrence, instant.replace(tzinfo=None)))
    if not candidates:
        raise calendar.CalendarError('Diese Uhrzeit existiert wegen der Zeitumstellung nicht.')
    ambiguous = len({at for _, at in candidates}) > 1
    if fold is not None and (type(fold) is not int or fold not in (0, 1)):
        raise calendar.CalendarError('Bitte die erste oder zweite Uhrzeit wählen.')
    if ambiguous and fold is None:
        raise calendar.CalendarError('Diese Uhrzeit kommt zweimal vor. Bitte erste oder zweite Uhrzeit wählen.')
    return next((at for occurrence, at in candidates if occurrence == (fold or 0)), candidates[0][1])


def note_values(data):
    if set(data) - {'request_key', 'revision', 'date', 'title', 'body', 'color', 'reminder_local', 'timezone', 'fold'}:
        raise calendar.CalendarError('Unbekanntes Notizfeld.')
    try:
        day = date.fromisoformat(data['date'])
        if abs((day - utcnow().date()).days) > 3660:
            raise ValueError()
    except (KeyError, ValueError, TypeError):
        raise calendar.CalendarError('Bitte ein gültiges Notizdatum wählen.') from None
    title, text = data.get('title'), data.get('body', '')
    color = data.get('color', 'red')
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 80:
        raise calendar.CalendarError('Bitte einen Titel mit höchstens 80 Zeichen eingeben.')
    if not isinstance(text, str) or len(text) > 2000 or not isinstance(color, str) or color not in COLORS:
        raise calendar.CalendarError('Notiztext oder Farbe ist ungültig.')
    tz_name = data.get('timezone', 'Europe/Berlin')
    calendar.zone(tz_name)
    raw = data.get('reminder_local')
    if raw is not None and not isinstance(raw, str):
        raise calendar.CalendarError('Bitte Datum und Uhrzeit vollständig eingeben.')
    raw = raw or None
    at = local_instant(raw, tz_name, data.get('fold')) if raw else None
    return dict(local_date=day, title=title.strip(), body=text, color=color, timezone=tz_name,
                reminder_local=raw, reminder_at=at, fold=data.get('fold') if raw else None)


def serialize(note):
    return dict(id=note.id, date=note.local_date.isoformat(), title=note.title, body=note.body,
                color=note.color, revision=note.revision, reminder_at=calendar.utc_iso(note.reminder_at) if note.reminder_at else None,
                reminder_local=note.reminder_local, timezone=note.timezone, fold=note.fold,
                reminder_state=note.reminder_state)


def owned(note_id, user_id, include_deleted=False):
    stmt = select(CalendarNote).where(CalendarNote.id == note_id, CalendarNote.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(CalendarNote.deleted_at.is_(None))
    row = db.session.execute(stmt).scalar_one_or_none()
    if row is None:
        raise calendar.CalendarError('Notiz nicht gefunden.', 404)
    return row


def lock_actor(user_id):
    return db.session.execute(select(User).where(User.id == user_id).with_for_update()
                              .execution_options(populate_existing=True)).scalar_one()


def note_limits(user_id, day, exclude=None):
    query = CalendarNote.query.filter_by(user_id=user_id, deleted_at=None)
    if exclude is not None:
        query = query.filter(CalendarNote.id != exclude)
    if query.count() >= MAX_USER_NOTES or query.filter_by(local_date=day).count() >= MAX_DAY_NOTES:
        raise calendar.CalendarError('Notizlimit erreicht: höchstens 20 pro Tag und 2000 insgesamt.', 409)


def reminder_bounds(values):
    at = values['reminder_at']
    if at and not utcnow() < at <= utcnow() + timedelta(days=366):
        raise calendar.CalendarError('Eine neue Erinnerung muss in den nächsten zwölf Monaten liegen.')


def paginate(query):
    try:
        cursor = int(request.args.get('cursor', '0'))
        if not 0 <= cursor <= 9223372036854775807:
            raise ValueError()
    except ValueError:
        raise calendar.CalendarError('Ungültige Kalenderseite.') from None
    rows = query.filter(CalendarNote.id > cursor).order_by(CalendarNote.id).limit(PAGE_SIZE + 1).all()
    more = len(rows) > PAGE_SIZE
    rows = rows[:PAGE_SIZE]
    return dict(notes=[serialize(row) for row in rows], next_cursor=rows[-1].id if more else None, complete=not more)


@calendar_notes_bp.get('/notes')
@limiter.limit('600 per hour')
@jwt_required()
def list_notes():
    user, failure = _get_current_user()
    if failure:
        return failure
    try:
        start, end = date.fromisoformat(request.args['start']), date.fromisoformat(request.args['end'])
        if not 1 <= (end - start).days <= 62:
            raise ValueError()
        return jsonify(paginate(CalendarNote.query.filter(CalendarNote.user_id == user.id, CalendarNote.deleted_at.is_(None),
                                                            CalendarNote.local_date >= start, CalendarNote.local_date < end)))
    except (KeyError, TypeError, ValueError) as exc:
        return error(str(exc) if isinstance(exc, calendar.CalendarError) else 'Bitte einen Zeitraum von höchstens 62 Tagen wählen.',
                     getattr(exc, 'status', 400))


@calendar_notes_bp.post('/notes')
@limiter.limit('120 per hour')
@jwt_required()
def create_note():
    user, failure = _get_current_user()
    if failure:
        return failure
    try:
        data = body(); key = request_key(data.get('request_key')); values = note_values(data); fingerprint = digest(values)
        lock_actor(user.id)
        old = CalendarNote.query.filter_by(user_id=user.id, request_key=key).first()
        if old:
            if old.input_digest != fingerprint or old.deleted_at:
                raise calendar.CalendarError('Diese Anfrage wurde bereits für eine andere oder gelöschte Notiz verwendet.', 409)
            return jsonify(serialize(old)), 200
        reminder_bounds(values); note_limits(user.id, values['local_date'])
        row = CalendarNote(user_id=user.id, request_key=key, input_digest=fingerprint,
                           reminder_state='pending' if values['reminder_at'] else 'none', **values)
        db.session.add(row); db.session.commit()
        return jsonify(serialize(row)), 201
    except calendar.CalendarError as exc:
        return error(str(exc), exc.status)
    except IntegrityError:
        return error('Die Anfrage kollidiert mit einer parallelen Änderung. Bitte erneut versuchen.', 409)


@calendar_notes_bp.put('/notes/<int:note_id>')
@limiter.limit('240 per hour')
@jwt_required()
def update_note(note_id):
    user, failure = _get_current_user()
    if failure:
        return failure
    try:
        data = body(); key = request_key(data.get('request_key')); values = note_values(data)
        fingerprint = digest(values); revision = data.get('revision')
        lock_actor(user.id); row = owned(note_id, user.id)
        if row.mutation_key == key:
            if row.mutation_digest != fingerprint:
                raise calendar.CalendarError('Diese Anfragekennung wurde schon anders verwendet.', 409)
            return jsonify(serialize(row))
        if type(revision) is not int or revision != row.revision:
            raise calendar.CalendarError('Die Notiz wurde inzwischen geändert. Bitte neu laden.', 409)
        if values['reminder_at'] != row.reminder_at:
            reminder_bounds(values)
        note_limits(user.id, values['local_date'], note_id)
        state = row.reminder_state if values['reminder_at'] == row.reminder_at else 'pending' if values['reminder_at'] else 'none'
        changed = db.session.execute(update(CalendarNote).where(CalendarNote.id == note_id, CalendarNote.user_id == user.id,
                CalendarNote.deleted_at.is_(None), CalendarNote.revision == revision).values(**values,
                reminder_state=state, revision=revision + 1, mutation_key=key, mutation_digest=fingerprint, updated_at=utcnow()))
        if changed.rowcount != 1:
            raise calendar.CalendarError('Die Notiz wurde inzwischen geändert. Bitte neu laden.', 409)
        db.session.commit(); db.session.refresh(row)
        return jsonify(serialize(row))
    except calendar.CalendarError as exc:
        return error(str(exc), exc.status)


@calendar_notes_bp.delete('/notes/<int:note_id>')
@limiter.limit('120 per hour')
@jwt_required()
def delete_note(note_id):
    user, failure = _get_current_user()
    if failure:
        return failure
    try:
        lock_actor(user.id); row = owned(note_id, user.id, include_deleted=True)
        if row.deleted_at:
            return jsonify(deleted=True)
        revision = body().get('revision')
        if type(revision) is not int or revision != row.revision:
            raise calendar.CalendarError('Die Notiz wurde inzwischen geändert. Bitte neu laden.', 409)
        changed = db.session.execute(update(CalendarNote).where(CalendarNote.id == row.id, CalendarNote.user_id == user.id,
             CalendarNote.deleted_at.is_(None), CalendarNote.revision == revision).values(
             deleted_at=utcnow(), reminder_state='none', revision=revision + 1, updated_at=utcnow()))
        if changed.rowcount != 1:
            raise calendar.CalendarError('Die Notiz wurde inzwischen geändert. Bitte neu laden.', 409)
        db.session.commit(); return jsonify(deleted=True)
    except calendar.CalendarError as exc:
        return error(str(exc), exc.status)


@calendar_notes_bp.get('/reminders')
@limiter.limit('600 per hour')
@jwt_required()
def reminders():
    user, failure = _get_current_user()
    if failure:
        return failure
    try:
        return jsonify(paginate(CalendarNote.query.filter_by(user_id=user.id, deleted_at=None, reminder_state='ready')))
    except calendar.CalendarError as exc:
        return error(str(exc), exc.status)


@calendar_notes_bp.post('/notes/<int:note_id>/dismiss')
@limiter.limit('120 per hour')
@jwt_required()
def dismiss(note_id):
    user, failure = _get_current_user()
    if failure:
        return failure
    try:
        lock_actor(user.id); row = owned(note_id, user.id)
        revision = body().get('revision')
        if row.reminder_state == 'dismissed':
            return jsonify(serialize(row))
        if row.reminder_state != 'ready' or type(revision) is not int or revision != row.revision:
            raise calendar.CalendarError('Die Erinnerung wurde inzwischen geändert. Bitte neu laden.', 409)
        changed = db.session.execute(update(CalendarNote).where(CalendarNote.id == row.id, CalendarNote.user_id == user.id,
                CalendarNote.deleted_at.is_(None), CalendarNote.revision == revision, CalendarNote.reminder_state == 'ready')
                .values(reminder_state='dismissed', revision=revision + 1, updated_at=utcnow()))
        if changed.rowcount != 1:
            raise calendar.CalendarError('Die Erinnerung wurde inzwischen geändert. Bitte neu laden.', 409)
        db.session.commit(); db.session.refresh(row); return jsonify(serialize(row))
    except calendar.CalendarError as exc:
        return error(str(exc), exc.status)


def process_due(limit=200, now=None):
    """A durable DB transition only. Multiple workers cannot create duplicate messages."""
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError('limit must be between 1 and 500')
    now = now or utcnow()
    rows = db.session.execute(select(CalendarNote).where(CalendarNote.deleted_at.is_(None),
            CalendarNote.reminder_state == 'pending', CalendarNote.reminder_at <= now)
            .order_by(CalendarNote.reminder_at, CalendarNote.id).limit(limit).with_for_update(skip_locked=True)).scalars().all()
    count = 0
    for row in rows:
        result = db.session.execute(update(CalendarNote).where(CalendarNote.id == row.id,
             CalendarNote.deleted_at.is_(None), CalendarNote.reminder_state == 'pending', CalendarNote.reminder_at <= now,
             CalendarNote.revision == row.revision).values(reminder_state='ready', revision=row.revision + 1, updated_at=now))
        count += result.rowcount
    db.session.commit()
    return count


def one_shot_view(marker, user_id):
    campaign = db.session.get(Campaign, marker.campaign_id)
    session = db.session.get(GameSession, marker.session_id)
    return dict(id=marker.id, campaign_id=campaign.id, session_id=session.id, name=campaign.name,
                scheduled_at=calendar.utc_iso(session.scheduled_at) if session.scheduled_at else None,
                status=session.status, can_manage=_is_dm(campaign, user_id), hub_href=f'/campaigns?campaign_id={campaign.id}')


@calendar_notes_bp.get('/oneshots')
@limiter.limit('600 per hour')
@jwt_required()
def list_one_shots():
    user, failure = _get_current_user()
    if failure:
        return failure
    context = getattr(g, 'table_context', None)
    rows = db.session.execute(select(CalendarOneShot).join(Campaign, CalendarOneShot.campaign_id == Campaign.id)
            .where(Campaign.deleted_at.is_(None), or_(Campaign.owner_id == user.id,
                Campaign.id.in_(select(CampaignMember.campaign_id).where(CampaignMember.user_id == user.id, CampaignMember.status == 'active'))))
            .order_by(CalendarOneShot.id.desc()).limit(201)).scalars().all()
    return jsonify(oneshots=[one_shot_view(row, user.id) for row in rows[:200]], complete=len(rows) <= 200,
                   can_create=bool(can_create_campaign(user) and not (context and context.mode == 'player')),
                   quota=user.active_campaigns_quota, used=user.get_active_campaigns_count())


@calendar_notes_bp.post('/oneshots')
@limiter.limit('20 per hour')
@jwt_required()
def create_one_shot():
    user, failure = _get_current_user()
    if failure:
        return failure
    try:
        data = body(); key = request_key(data.get('request_key'))
        name = data.get('name'); size = data.get('max_players', 6); duration = data.get('duration_minutes', 240)
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100 or type(size) is not int or not 2 <= size <= 20:
            raise calendar.CalendarError('Bitte einen Namen und 2 bis 20 Plätze wählen.')
        if type(duration) is not int or not 1 <= duration <= 1440:
            raise calendar.CalendarError('Die Dauer muss zwischen 1 und 1440 Minuten liegen.')
        at = local_instant(data.get('first_local'), data.get('timezone', 'Europe/Berlin'), data.get('fold'))
        fingerprint = digest(dict(name=name.strip(), max_players=size, duration_minutes=duration, at=at,
                                   timezone=data.get('timezone', 'Europe/Berlin')))
        actor = lock_actor(user.id)
        context = getattr(g, 'table_context', None)
        if context and context.mode == 'player':
            raise calendar.CalendarError('Bitte verlasse den Spieler-Modus, um eine Runde zu planen.', 403)
        old = CalendarOneShot.query.filter_by(user_id=user.id, request_key=key).first()
        if old:
            if old.input_digest != fingerprint:
                raise calendar.CalendarError('Diese Anfrage wurde bereits anders verwendet.', 409)
            campaign = db.session.get(Campaign, old.campaign_id)
            if not campaign or campaign.deleted_at or not _is_dm(campaign, actor.id):
                raise calendar.CalendarError('One-Shot nicht verfügbar.', 404)
            return jsonify(one_shot_view(old, actor.id))
        if not can_create_campaign(actor):
            raise calendar.CalendarError('Für einen One-Shot brauchst du einen freien Kampagnenplatz und DM-Zugang.', 403)
        if not utcnow() < at <= utcnow() + timedelta(days=366):
            raise calendar.CalendarError('Bitte einen Termin in den nächsten zwölf Monaten wählen.')
        campaign = Campaign(name=name.strip(), owner_id=actor.id, status='active', max_players=size, is_discoverable=False)
        db.session.add(campaign); db.session.flush()
        now = utcnow()
        db.session.add(CampaignMember(campaign_id=campaign.id, user_id=actor.id, campaign_role='DM', status='active',
              invited_by=actor.id, invited_at=now, accepted_at=now, joined_at=now))
        session = GameSession(campaign_id=campaign.id, name=name.strip(), scheduled_at=at, duration_minutes=duration, status='scheduled')
        db.session.add(session); db.session.flush()
        marker = CalendarOneShot(campaign_id=campaign.id, session_id=session.id, user_id=actor.id, request_key=key, input_digest=fingerprint)
        db.session.add(marker); db.session.commit(); return jsonify(one_shot_view(marker, actor.id)), 201
    except calendar.CalendarError as exc:
        return error(str(exc), exc.status)
    except IntegrityError:
        return error('Die Anfrage kollidiert mit einer parallelen Änderung. Bitte erneut versuchen.', 409)


@calendar_notes_bp.post('/sessions')
@limiter.limit('40 per hour')
@jwt_required()
def create_day_session():
    user, failure = _get_current_user()
    if failure:
        return failure
    try:
        data = body(); campaign_id = data.get('campaign_id')
        if type(campaign_id) is not int or campaign_id < 1:
            raise calendar.CalendarError('Bitte eine Kampagne wählen.')
        # Enforce the same strict DST semantics as reminders before handing off to existing service.
        at = local_instant(data.get('first_local'), data.get('timezone', 'Europe/Berlin'), data.get('fold'))
        payload = {key: data[key] for key in ('name', 'request_key', 'first_local', 'timezone', 'duration_minutes') if key in data}
        payload['frequency'] = 'once'
        # Existing series convention uses fold=0; an explicitly selected second autumn occurrence
        # cannot be represented in that contract, so reject rather than silently choosing another instant.
        if data.get('fold') == 1:
            tz = calendar.zone(data.get('timezone', 'Europe/Berlin'))
            if calendar.local_to_utc(datetime.fromisoformat(data['first_local']), tz) != at:
                raise calendar.CalendarError('Für Sessions bitte die erste Uhrzeit wählen; die zweite wird noch nicht unterstützt.')
        series, created = calendar.create_series(campaign_id, user.id, payload)
        occurrence = SessionOccurrence.query.filter_by(series_id=series.id, ordinal=0).first()
        db.session.commit()
        return jsonify(series_id=series.id, session_id=occurrence.session_id,
                       campaign_id=campaign_id, hub_href=f'/campaigns?campaign_id={campaign_id}'), 201 if created else 200
    except calendar.CalendarError as exc:
        return error(str(exc), exc.status)
    except IntegrityError:
        return error('Die Anfrage kollidiert mit einer parallelen Änderung. Bitte erneut versuchen.', 409)
