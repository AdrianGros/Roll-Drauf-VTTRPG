"""Calendar arithmetic and persistence. Every public route checks campaign access."""
import calendar
import hashlib
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select

from vtt.extensions import db
from vtt.models import Campaign, GameSession, SessionOccurrence, SessionSeries
from vtt.utils.time import utcnow

FREQUENCIES = {'once', 'weekly', 'biweekly', 'monthly'}


def zone(name):
    if not isinstance(name, str) or len(name) > 64:
        raise ValueError('Bitte eine gültige Zeitzone wählen.')
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError('Bitte eine gültige Zeitzone wählen.') from None


def local_to_utc(local, tz, *, strict=False):
    """Keep wall time; first autumn occurrence, spring gap shifted by its delta."""
    aware = local.replace(tzinfo=tz, fold=0)
    utc = aware.astimezone(timezone.utc)
    if strict and utc.astimezone(tz).replace(tzinfo=None) != local:
        raise ValueError('Diese Startzeit existiert wegen der Zeitumstellung nicht.')
    return utc.replace(tzinfo=None)


def occurrence_local(anchor, frequency, index):
    if frequency == 'monthly':
        month = anchor.year * 12 + anchor.month - 1 + index
        year, month = divmod(month, 12)
        month += 1
        day = min(anchor.day, calendar.monthrange(year, month)[1])
        return anchor.replace(year=year, month=month, day=day)
    if frequency in {'weekly', 'biweekly'}:
        return anchor + timedelta(weeks=index * (2 if frequency == 'biweekly' else 1))
    if frequency == 'once' and index == 0:
        return anchor
    return None


def parse_series(data, *, now=None):
    now = now or utcnow()
    if not isinstance(data, dict):
        raise ValueError('Ungültige Termindaten.')
    name = data.get('name')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
        raise ValueError('Bitte einen Session-Namen mit höchstens 100 Zeichen eingeben.')
    frequency = data.get('frequency', 'once')
    if not isinstance(frequency, str) or frequency not in FREQUENCIES:
        raise ValueError('Bitte einmalig, wöchentlich, alle zwei Wochen oder monatlich wählen.')
    tz_name = data.get('timezone', 'Europe/Berlin')
    tz = zone(tz_name)
    try:
        first = datetime.fromisoformat(data['first_local'])
        if first.tzinfo is not None or first.second or first.microsecond:
            raise ValueError()
        until = date.fromisoformat(data['until']) if data.get('until') else None
        key = str(uuid.UUID(data['request_key']))
    except (ValueError, TypeError, KeyError, AttributeError):
        raise ValueError('Bitte Startdatum, Uhrzeit und ein gültiges Enddatum angeben.') from None
    try:
        at = local_to_utc(first, tz, strict=True)
    except OverflowError:
        raise ValueError('Ungültiges Startdatum.') from None
    if at > now + timedelta(days=366):
        raise ValueError('Der erste Termin muss innerhalb der nächsten zwölf Monate liegen.')
    if until and (until < first.date() or until.year > first.year + 10):
        raise ValueError('Das Ende muss nach dem Start und innerhalb von zehn Jahren liegen.')
    duration = data.get('duration_minutes')
    if duration is not None and (type(duration) is not int or not 1 <= duration <= 1440):
        raise ValueError('Die Dauer muss zwischen 1 und 1440 Minuten liegen.')
    values = dict(name=name.strip(), first_local=first, timezone=tz_name,
                  frequency=frequency, until_date=until, duration_minutes=duration)
    digest = hashlib.sha256(json.dumps(values, default=str, sort_keys=True).encode()).hexdigest()
    return values, key, digest, at


def lock_campaign(campaign_id):
    # Serializes materialization, cancellation, and retries across workers.
    return db.session.execute(select(Campaign).where(Campaign.id == campaign_id).with_for_update()).scalar_one()


def materialize(series, through, *, now=None):
    now = now or utcnow()
    if series.status != 'active':
        return
    tz = zone(series.timezone)
    # Every index is calculated from the original anchor: Feb 28 never changes
    # a Jan 31 monthly series into a series that always plays on the 28th.
    for _ in range(600):
        local = occurrence_local(series.first_local, series.frequency, series.next_index)
        if local is None or (series.until_date and local.date() > series.until_date):
            break
        at = local_to_utc(local, tz)
        if at >= through:
            break
        index = series.next_index
        series.next_index += 1
        # Downtime does not manufacture past game nights or replay notices.
        if at < now and index > 0:
            continue
        session = GameSession(campaign_id=series.campaign_id, name=series.name,
                              scheduled_at=at, duration_minutes=series.duration_minutes, status='scheduled')
        db.session.add(session)
        db.session.flush()
        db.session.add(SessionOccurrence(series_id=series.id, ordinal=index, session_id=session.id))


def create_series(campaign_id, actor_id, data):
    values, key, digest, at = parse_series(data)
    campaign = lock_campaign(campaign_id)
    existing = SessionSeries.query.filter_by(campaign_id=campaign_id, created_by=actor_id, request_key=key).first()
    if existing:
        if existing.input_digest != digest:
            raise ValueError('Diese Anfrage wurde bereits mit anderen Termindaten gespeichert.')
        return existing, False
    if campaign.status != 'active':
        raise ValueError('Termine können nur für aktive Kampagnen angelegt werden.')
    if at <= utcnow():
        raise ValueError('Bitte einen Starttermin in der Zukunft wählen.')
    if values['frequency'] != 'once' and SessionSeries.query.filter(
        SessionSeries.campaign_id == campaign_id, SessionSeries.status == 'active',
        SessionSeries.frequency != 'once',
    ).count() >= 20:
        raise ValueError('Diese Kampagne hat bereits 20 Serien. Bitte zuerst eine Serie beenden.')
    series = SessionSeries(campaign_id=campaign_id, created_by=actor_id, request_key=key,
                           input_digest=digest, status='active', next_index=0, **values)
    db.session.add(series)
    db.session.flush()
    materialize(series, max(utcnow() + timedelta(days=366), at + timedelta(days=1)))
    return series, True


def period(scope, anchor, tz_name):
    tz = zone(tz_name)
    try:
        day = date.fromisoformat(anchor) if anchor else datetime.now(tz).date()
    except (ValueError, TypeError):
        raise ValueError('Ungültiges Kalenderdatum.') from None
    if not datetime.now(tz).year - 10 <= day.year <= datetime.now(tz).year + 5:
        raise ValueError('Bitte einen Zeitraum innerhalb von zehn vergangenen oder fünf kommenden Jahren wählen.')
    if scope == 'week':
        start = day - timedelta(days=day.weekday())
        end = start + timedelta(days=7)
    elif scope == 'month':
        start = day.replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1)
    elif scope == 'year':
        start, end = date(day.year, 1, 1), date(day.year + 1, 1, 1)
    else:
        raise ValueError('Bitte Woche, Monat oder Jahr wählen.')
    as_utc = lambda d: local_to_utc(datetime.combine(d, datetime.min.time()), tz)
    return start, end, as_utc(start), as_utc(end), tz


def load_calendar(campaign_id, scope, anchor, tz_name):
    start, end, utc_start, utc_end, tz = period(scope, anchor, tz_name)
    campaign = lock_campaign(campaign_id)
    series = SessionSeries.query.filter_by(campaign_id=campaign_id).order_by(SessionSeries.id).all()
    if campaign.status == 'active':
        for item in series:
            materialize(item, max(utc_end, utcnow() + timedelta(days=366)))
    db.session.flush()
    rows = db.session.execute(select(GameSession, SessionOccurrence.series_id).outerjoin(
        SessionOccurrence, SessionOccurrence.session_id == GameSession.id,
    ).where(GameSession.campaign_id == campaign_id, GameSession.scheduled_at >= utc_start,
            GameSession.scheduled_at < utc_end).order_by(GameSession.scheduled_at, GameSession.id)).all()
    entries = []
    for session, series_id in rows:
        local = session.scheduled_at.replace(tzinfo=timezone.utc).astimezone(tz)
        entries.append(dict(id=session.id, name=session.name, series_id=series_id,
                            status=session.status, date=local.date().isoformat(),
                            local_time=local.strftime('%H:%M'), scheduled_at=local.isoformat(),
                            duration_minutes=session.duration_minutes,
                            cancellable=session.status in {'scheduled', 'ready'} and session.started_at is None))
    return dict(scope=scope, start=start.isoformat(), end=end.isoformat(), timezone=tz_name,
                entries=entries, series=[s.serialize() for s in series])


def cancel_appointment(campaign_id, session_id):
    lock_campaign(campaign_id)
    session = db.session.execute(select(GameSession).where(
        GameSession.id == session_id, GameSession.campaign_id == campaign_id,
    ).with_for_update()).scalar_one_or_none()
    if session is None:
        raise ValueError('Dieser Termin gehört nicht zu dieser Kampagne.')
    if session.status == 'cancelled':
        return session
    if session.status not in {'scheduled', 'ready'} or session.started_at is not None:
        raise ValueError('Laufende und abgeschlossene Sessions können nicht abgesagt werden.')
    session.status, session.session_state = 'cancelled', 'ended'
    return session


def stop_series(campaign_id, series_id):
    lock_campaign(campaign_id)
    series = SessionSeries.query.filter_by(id=series_id, campaign_id=campaign_id).first()
    if series is None:
        raise ValueError('Diese Serie gehört nicht zu dieser Kampagne.')
    series.status = 'stopped'
    upcoming = db.session.execute(select(GameSession).join(
        SessionOccurrence, SessionOccurrence.session_id == GameSession.id,
    ).where(SessionOccurrence.series_id == series.id, GameSession.campaign_id == campaign_id,
            GameSession.scheduled_at > utcnow(), GameSession.started_at.is_(None),
            GameSession.status.in_(['scheduled', 'ready'])).with_for_update()).scalars().all()
    for session in upcoming:
        session.status, session.session_state = 'cancelled', 'ended'
    return series, len(upcoming)
