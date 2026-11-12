"""Calendar arithmetic, projections and persistence.

Reads (``load_calendar``, ``load_my_calendar``, ``load_alerts``) are pure data
projections: they never lock, never materialize and never write. Only the explicit
writers (create/materialize/cancel/stop) take the campaign writer lock, re-check the
actor's *current* campaign rights inside that lock and are committed by their route.
"""
import base64
import binascii
import calendar
import hashlib
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, func, or_, select

from vtt.extensions import db
from vtt.models import (Campaign, CampaignMember, GameSession, SessionDateOption, SessionDatePoll,
                        SessionDateVote, SessionOccurrence, SessionSeries)
from vtt.utils.time import utcnow

FREQUENCIES = {'once', 'weekly', 'biweekly', 'monthly'}
DM_ROLES = {'DM', 'CO_DM', 'CODM'}
HORIZON_DAYS = 366            # "twelve months" for first dates, poll options and materialization
PAGE_LIMIT = 200              # entries per calendar page; a cursor continues, never a silent cut
MAX_FILTER_IDS = 50
MAX_MATERIALIZE_CAMPAIGNS = 25
ALERT_LIMIT = 25
CAMPAIGN_ENTRY_LIMIT = 500
NO_ACCESS = 'Kein Zugriff auf diese Kampagne.'


class CalendarError(ValueError):
    """A user-facing validation/conflict/authorization failure with its HTTP status."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def zone(name):
    if not isinstance(name, str) or not name or len(name) > 64:
        raise CalendarError('Bitte eine gültige Zeitzone wählen.')
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        raise CalendarError('Bitte eine gültige Zeitzone wählen.') from None


def local_to_utc(local, tz, *, strict=False):
    """Keep wall time; first autumn occurrence, spring gap shifted by its delta."""
    aware = local.replace(tzinfo=tz, fold=0)
    utc = aware.astimezone(timezone.utc)
    if strict and utc.astimezone(tz).replace(tzinfo=None) != local:
        raise CalendarError('Diese Startzeit existiert wegen der Zeitumstellung nicht.')
    return utc.replace(tzinfo=None)


def utc_iso(value):
    return value.replace(microsecond=0).isoformat() + 'Z'


def add_months(day, months):
    index = day.year * 12 + day.month - 1 + months
    year, month = divmod(index, 12)
    month += 1
    return day.replace(year=year, month=month, day=min(day.day, calendar.monthrange(year, month)[1]))


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
        raise CalendarError('Ungültige Termindaten.')
    name = data.get('name')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
        raise CalendarError('Bitte einen Session-Namen mit höchstens 100 Zeichen eingeben.')
    frequency = data.get('frequency', 'once')
    if not isinstance(frequency, str) or frequency not in FREQUENCIES:
        raise CalendarError('Bitte einmalig, wöchentlich, alle zwei Wochen oder monatlich wählen.')
    tz_name = data.get('timezone', 'Europe/Berlin')
    tz = zone(tz_name)
    try:
        first = datetime.fromisoformat(data['first_local'])
        if first.tzinfo is not None or first.second or first.microsecond:
            raise ValueError()
        until = date.fromisoformat(data['until']) if data.get('until') else None
        key = str(uuid.UUID(data['request_key']))
    except (ValueError, TypeError, KeyError, AttributeError):
        raise CalendarError('Bitte Startdatum, Uhrzeit und ein gültiges Enddatum angeben.') from None
    try:
        at = local_to_utc(first, tz, strict=True)
    except OverflowError:
        raise CalendarError('Ungültiges Startdatum.') from None
    if at > now + timedelta(days=HORIZON_DAYS):
        raise CalendarError('Der erste Termin muss innerhalb der nächsten zwölf Monate liegen.')
    if until and (until < first.date() or until.year > first.year + 10):
        raise CalendarError('Das Ende muss nach dem Start und innerhalb von zehn Jahren liegen.')
    duration = data.get('duration_minutes')
    if duration is not None and (type(duration) is not int or not 1 <= duration <= 1440):
        raise CalendarError('Die Dauer muss zwischen 1 und 1440 Minuten liegen.')
    values = dict(name=name.strip(), first_local=first, timezone=tz_name,
                  frequency=frequency, until_date=until, duration_minutes=duration)
    digest = hashlib.sha256(json.dumps(values, default=str, sort_keys=True).encode()).hexdigest()
    return values, key, digest, at


# ---------------------------------------------------------------- writer lock / rights

def lock_campaign(campaign_id):
    """Serializes series, poll and schedule writers (and retries) across workers."""
    campaign = db.session.execute(
        select(Campaign).where(Campaign.id == campaign_id).with_for_update()).scalar_one_or_none()
    if campaign is None or not campaign.is_public():
        raise CalendarError('Kampagne nicht gefunden.', 404)
    return campaign


def ensure_manager(campaign, actor_id):
    """Current DM/Co-DM rights inside the lock; a carried Player context never writes."""
    from vtt.campaigns.routes import _is_dm
    if not _is_dm(campaign, actor_id):
        raise CalendarError(NO_ACCESS, 403)


def is_managed(campaign_id, owner_id, role, user_id):
    """Manager decision from preloaded membership, honouring a carried Player context."""
    from vtt.play.contexts import restrict_campaign_role
    if restrict_campaign_role(campaign_id, user_id):
        return False
    return owner_id == user_id or str(role or '').strip().upper() in DM_ROLES


def session_is_schedulable(session):
    """An unstarted, not cancelled/ended session (the only kind a poll may schedule)."""
    return (session.started_at is None and (session.status in (None, 'scheduled', 'ready'))
            and (session.session_state in (None, 'preparing')) and not session.is_archived)


def schedulable_clause():
    return and_(GameSession.started_at.is_(None),
                or_(GameSession.status.is_(None), GameSession.status.in_(['scheduled', 'ready'])),
                or_(GameSession.session_state.is_(None), GameSession.session_state == 'preparing'),
                or_(GameSession.is_archived.is_(None), GameSession.is_archived.is_(False)))


# ---------------------------------------------------------------- series writers

def materialize(series, through, *, now=None):
    """Create real sessions up to ``through``; returns how many were created."""
    now = now or utcnow()
    if series.status != 'active':
        return 0
    tz = zone(series.timezone)
    created = 0
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
        created += 1
    return created


def create_series(campaign_id, actor_id, data):
    values, key, digest, at = parse_series(data)
    campaign = lock_campaign(campaign_id)
    ensure_manager(campaign, actor_id)
    existing = SessionSeries.query.filter_by(campaign_id=campaign_id, created_by=actor_id, request_key=key).first()
    if existing:
        if existing.input_digest != digest:
            raise CalendarError('Diese Anfrage wurde bereits mit anderen Termindaten gespeichert.')
        return existing, False
    if campaign.status != 'active':
        raise CalendarError('Termine können nur für aktive Kampagnen angelegt werden.')
    if at <= utcnow():
        raise CalendarError('Bitte einen Starttermin in der Zukunft wählen.')
    if values['frequency'] != 'once' and SessionSeries.query.filter(
        SessionSeries.campaign_id == campaign_id, SessionSeries.status == 'active',
        SessionSeries.frequency != 'once',
    ).count() >= 20:
        raise CalendarError('Diese Kampagne hat bereits 20 Serien. Bitte zuerst eine Serie beenden.')
    series = SessionSeries(campaign_id=campaign_id, created_by=actor_id, request_key=key,
                           input_digest=digest, status='active', next_index=0, **values)
    db.session.add(series)
    db.session.flush()
    materialize(series, max(utcnow() + timedelta(days=HORIZON_DAYS), at + timedelta(days=1)))
    return series, True


def materialize_horizon(campaign_id, actor_id):
    """Explicit, bounded top-up of one campaign's active series to twelve months."""
    campaign = lock_campaign(campaign_id)
    ensure_manager(campaign, actor_id)
    if campaign.status != 'active':
        return 0
    through = utcnow() + timedelta(days=HORIZON_DAYS)
    series = SessionSeries.query.filter_by(campaign_id=campaign_id, status='active') \
        .order_by(SessionSeries.id).limit(100).all()
    return sum(materialize(item, through) for item in series)


def materialize_managed(user_id, campaign_ids=None):
    """DM/Co-DM top-up over the caller's managed campaigns; never reachable for Players.

    Each campaign is processed in its own locked transaction (ascending id order), so
    a long list never holds several locks at once. At most MAX_MATERIALIZE_CAMPAIGNS
    campaigns are handled per call; ``remaining`` tells the caller to call again.
    """
    own = own_campaigns(user_id, campaign_ids)
    managed = {c.id: c for c, role in own if is_managed(c.id, c.owner_id, role, user_id)}
    if campaign_ids is not None and set(campaign_ids) - set(managed):
        raise CalendarError(NO_ACCESS, 403)
    if not managed:
        raise CalendarError(NO_ACCESS, 403)
    candidates = sorted(db.session.execute(
        select(SessionSeries.campaign_id).where(
            SessionSeries.campaign_id.in_(list(managed)), SessionSeries.status == 'active',
            SessionSeries.frequency != 'once').distinct()).scalars().all())
    batch, remaining = candidates[:MAX_MATERIALIZE_CAMPAIGNS], candidates[MAX_MATERIALIZE_CAMPAIGNS:]
    results = []
    for campaign_id in batch:
        try:
            created = materialize_horizon(campaign_id, user_id)
            db.session.commit()            # releases the campaign lock before the next one
        except CalendarError as exc:
            db.session.rollback()
            results.append(dict(campaign_id=campaign_id, created=0, error=str(exc)))
            continue
        results.append(dict(campaign_id=campaign_id, created=created))
    return dict(campaigns=results, remaining=len(remaining),
                horizon=utc_iso(utcnow() + timedelta(days=HORIZON_DAYS)))


def cancel_appointment(campaign_id, session_id, actor_id):
    campaign = lock_campaign(campaign_id)
    ensure_manager(campaign, actor_id)
    session = db.session.execute(select(GameSession).where(
        GameSession.id == session_id, GameSession.campaign_id == campaign_id,
    ).with_for_update()).scalar_one_or_none()
    if session is None:
        raise CalendarError('Dieser Termin gehört nicht zu dieser Kampagne.', 409)
    if session.status == 'cancelled':
        return session
    if session.status not in {'scheduled', 'ready'} or session.started_at is not None:
        raise CalendarError('Laufende und abgeschlossene Sessions können nicht abgesagt werden.', 409)
    session.status, session.session_state = 'cancelled', 'ended'
    # A poll for a cancelled session can no longer produce a date.
    for poll in SessionDatePoll.query.filter_by(session_id=session.id, status='open').all():
        poll.status, poll.revision, poll.updated_at, poll.closed_at = 'cancelled', poll.revision + 1, utcnow(), utcnow()
    return session


def stop_series(campaign_id, series_id, actor_id):
    campaign = lock_campaign(campaign_id)
    ensure_manager(campaign, actor_id)
    series = SessionSeries.query.filter_by(id=series_id, campaign_id=campaign_id).first()
    if series is None:
        raise CalendarError('Diese Serie gehört nicht zu dieser Kampagne.', 409)
    series.status = 'stopped'
    upcoming = db.session.execute(select(GameSession).join(
        SessionOccurrence, SessionOccurrence.session_id == GameSession.id,
    ).where(SessionOccurrence.series_id == series.id, GameSession.campaign_id == campaign_id,
            GameSession.scheduled_at > utcnow(), GameSession.started_at.is_(None),
            GameSession.status.in_(['scheduled', 'ready'])).with_for_update()).scalars().all()
    for session in upcoming:
        session.status, session.session_state = 'cancelled', 'ended'
    return series, len(upcoming)


# ---------------------------------------------------------------- pure projections

def entry_payload(session, tz, *, series_id=None, campaign_name=None, can_manage=False):
    local = session.scheduled_at.replace(tzinfo=timezone.utc).astimezone(tz)
    status = session.status or 'scheduled'          # the original status, never runtime_status
    entry = dict(session_id=session.id, id=session.id, name=session.name, session_name=session.name,
                 campaign_id=session.campaign_id, series_id=series_id, status=status,
                 cancelled=status == 'cancelled',
                 scheduled_at=utc_iso(session.scheduled_at), date=local.date().isoformat(),
                 local_date=local.date().isoformat(), local_time=local.strftime('%H:%M'),
                 local_iso=local.isoformat(timespec='minutes'), duration_minutes=session.duration_minutes,
                 cancellable=status in {'scheduled', 'ready'} and session.started_at is None,
                 hub_href=f'/campaigns?campaign_id={session.campaign_id}')
    if campaign_name is not None:
        entry.update(campaign_name=campaign_name, can_manage=can_manage)
    return entry


def period(scope, anchor, tz_name):
    """Per-campaign week/month/year window (legacy campaign calendar)."""
    tz = zone(tz_name)
    today = utcnow().replace(tzinfo=timezone.utc).astimezone(tz).date()
    try:
        day = date.fromisoformat(anchor) if anchor else today
    except (ValueError, TypeError):
        raise CalendarError('Ungültiges Kalenderdatum.') from None
    if not today.year - 10 <= day.year <= today.year + 5:
        raise CalendarError('Bitte einen Zeitraum innerhalb von zehn vergangenen oder fünf kommenden Jahren wählen.')
    if scope == 'week':
        start = day - timedelta(days=day.weekday())
        end = start + timedelta(days=7)
    elif scope == 'month':
        start = day.replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1)
    elif scope == 'year':
        start, end = date(day.year, 1, 1), date(day.year + 1, 1, 1)
    else:
        raise CalendarError('Bitte Woche, Monat oder Jahr wählen.')
    return start, end, local_midnight_utc(start, tz), local_midnight_utc(end, tz), tz


def local_midnight_utc(day, tz):
    return local_to_utc(datetime.combine(day, datetime.min.time()), tz)


def load_calendar(campaign_id, scope, anchor, tz_name):
    """One campaign's window. Pure read: series are only listed, never materialized."""
    start, end, utc_start, utc_end, tz = period(scope, anchor, tz_name)
    series = SessionSeries.query.filter_by(campaign_id=campaign_id).order_by(SessionSeries.id).limit(100).all()
    rows = db.session.execute(select(GameSession, SessionOccurrence.series_id).outerjoin(
        SessionOccurrence, SessionOccurrence.session_id == GameSession.id,
    ).where(GameSession.campaign_id == campaign_id, GameSession.scheduled_at >= utc_start,
            GameSession.scheduled_at < utc_end).order_by(GameSession.scheduled_at, GameSession.id)
        .limit(CAMPAIGN_ENTRY_LIMIT + 1)).all()
    truncated = len(rows) > CAMPAIGN_ENTRY_LIMIT
    entries = [entry_payload(session, tz, series_id=series_id) for session, series_id in rows[:CAMPAIGN_ENTRY_LIMIT]]
    return dict(scope=scope, start=start.isoformat(), end=end.isoformat(), timezone=tz_name,
                entries=entries, complete=not truncated, series=[s.serialize() for s in series])


def own_campaigns(user_id, campaign_ids=None):
    """[(Campaign, active_role)] for owner or *active* member of non-deleted campaigns.

    Invited/pending/left/kicked members and merely discoverable campaigns are not
    included. An explicit id list must be entirely inside this set: anything else
    (foreign, deleted, unknown) is rejected without saying which.
    """
    query = (select(Campaign, CampaignMember.campaign_role)
             .outerjoin(CampaignMember, and_(CampaignMember.campaign_id == Campaign.id,
                                             CampaignMember.user_id == user_id,
                                             CampaignMember.status == 'active'))
             .where(Campaign.deleted_at.is_(None),
                    or_(Campaign.owner_id == user_id, CampaignMember.id.is_not(None))))
    if campaign_ids is not None:
        query = query.where(Campaign.id.in_(campaign_ids))
    rows = db.session.execute(query.order_by(Campaign.name, Campaign.id)).all()
    if campaign_ids is not None and {c.id for c, _ in rows} != set(campaign_ids):
        raise CalendarError(NO_ACCESS, 403)
    return [(campaign, role) for campaign, role in rows]


def parse_campaign_ids(args):
    raw = [part for value in args.getlist('campaign_ids') + args.getlist('campaign_id')
           for part in value.split(',') if part.strip()]
    if not raw:
        return None
    if len(raw) > MAX_FILTER_IDS:
        raise CalendarError('Bitte höchstens 50 Kampagnen filtern.')
    try:
        ids = sorted({int(part) for part in raw})
    except ValueError:
        raise CalendarError('Ungültige Kampagnenauswahl.') from None
    if any(i < 1 or i > 2**31 - 1 for i in ids):
        raise CalendarError('Ungültige Kampagnenauswahl.')
    return ids


def my_period(scope, anchor, tz_name):
    tz = zone(tz_name)
    today = utcnow().replace(tzinfo=timezone.utc).astimezone(tz).date()
    try:
        day = date.fromisoformat(anchor) if anchor else today
    except (ValueError, TypeError):
        raise CalendarError('Ungültiges Kalenderdatum.') from None
    if not add_months(today, -120) <= day <= add_months(today, 12):
        raise CalendarError('Bitte einen Zeitraum innerhalb von zehn vergangenen Jahren und zwölf kommenden Monaten wählen.')
    if scope == 'month':
        start = day.replace(day=1)
        end = add_months(start, 1)
    elif scope == 'rolling30':
        start, end = day, day + timedelta(days=30)
    else:
        raise CalendarError('Bitte 30 Tage oder Monat wählen.')
    # DST-safe: local midnights are converted individually, never "+24 hours".
    return start, end, local_midnight_utc(start, tz), local_midnight_utc(end, tz), tz


def encode_cursor(at, session_id):
    return base64.urlsafe_b64encode(f'{at.isoformat()}|{session_id}'.encode()).decode().rstrip('=')


def decode_cursor(value):
    try:
        text = base64.urlsafe_b64decode(value + '=' * (-len(value) % 4)).decode()
        stamp, ident = text.split('|')
        at, session_id = datetime.fromisoformat(stamp), int(ident)
        if at.tzinfo is not None or session_id < 1:
            raise ValueError()
        return at, session_id
    except (ValueError, TypeError, UnicodeDecodeError, binascii.Error):
        raise CalendarError('Ungültiger Seitenmarker.') from None


def parse_limit(raw):
    if raw in (None, ''):
        return PAGE_LIMIT
    try:
        limit = int(raw)
    except ValueError:
        raise CalendarError('Ungültige Seitengröße.') from None
    if not 1 <= limit <= PAGE_LIMIT:
        raise CalendarError('Ungültige Seitengröße.')
    return limit


def load_my_calendar(user_id, *, scope='rolling30', anchor=None, tz_name='Europe/Berlin',
                     campaign_ids=None, cursor=None, limit=PAGE_LIMIT):
    """Own sessions across all campaigns. Pure read; membership is re-evaluated per page."""
    start, end, utc_start, utc_end, tz = my_period(scope, anchor, tz_name)
    own = own_campaigns(user_id, campaign_ids)
    after = decode_cursor(cursor) if cursor else None
    query = (select(GameSession, Campaign.name, Campaign.owner_id, CampaignMember.campaign_role,
                    SessionOccurrence.series_id)
             .join(Campaign, Campaign.id == GameSession.campaign_id)
             .outerjoin(CampaignMember, and_(CampaignMember.campaign_id == Campaign.id,
                                             CampaignMember.user_id == user_id,
                                             CampaignMember.status == 'active'))
             .outerjoin(SessionOccurrence, SessionOccurrence.session_id == GameSession.id)
             .where(Campaign.deleted_at.is_(None),
                    or_(Campaign.owner_id == user_id, CampaignMember.id.is_not(None)),
                    GameSession.scheduled_at >= utc_start, GameSession.scheduled_at < utc_end))
    if campaign_ids is not None:
        query = query.where(Campaign.id.in_(campaign_ids))
    if after:
        at, session_id = after
        query = query.where(or_(GameSession.scheduled_at > at,
                                and_(GameSession.scheduled_at == at, GameSession.id > session_id)))
    rows = db.session.execute(query.order_by(GameSession.scheduled_at, GameSession.id).limit(limit + 1)).all()
    page = rows[:limit]
    entries = [entry_payload(session, tz, series_id=series_id, campaign_name=name,
                             can_manage=is_managed(session.campaign_id, owner_id, role, user_id))
               for session, name, owner_id, role, series_id in page]
    next_cursor = encode_cursor(page[-1][0].scheduled_at, page[-1][0].id) if len(rows) > limit else None
    campaigns = [dict(id=c.id, name=c.name, can_manage=is_managed(c.id, c.owner_id, role, user_id))
                 for c, role in own]
    return dict(scope=scope, anchor=(anchor or start.isoformat()), timezone=tz_name,
                start=start.isoformat(), end=end.isoformat(), utc_start=utc_iso(utc_start), utc_end=utc_iso(utc_end),
                limit=limit, entries=entries, next_cursor=next_cursor, complete=next_cursor is None,
                campaigns=campaigns, can_manage_any=any(c['can_manage'] for c in campaigns),
                filter_campaign_ids=campaign_ids or [])


def load_alerts(user_id, campaign_ids=None):
    """Own managed sessions without a date + own open polls with incomplete answers."""
    own = own_campaigns(user_id, campaign_ids)
    names = {c.id: c.name for c, _ in own}
    managed = [c.id for c, role in own if c.status == 'active' and is_managed(c.id, c.owner_id, role, user_id)]
    active = [c.id for c, _ in own if c.status == 'active']
    missing = []
    if managed:
        missing = db.session.execute(
            select(GameSession).where(GameSession.campaign_id.in_(managed), GameSession.scheduled_at.is_(None),
                                      schedulable_clause())
            .order_by(GameSession.campaign_id, GameSession.created_at, GameSession.id)
            .limit(ALERT_LIMIT + 1)).scalars().all()
    votes = []
    if active:
        options = (select(func.count(SessionDateOption.id))
                   .where(SessionDateOption.poll_id == SessionDatePoll.id).correlate(SessionDatePoll)
                   .scalar_subquery())
        mine = (select(func.count(SessionDateVote.id))
                .join(SessionDateOption, SessionDateOption.id == SessionDateVote.option_id)
                .where(SessionDateOption.poll_id == SessionDatePoll.id, SessionDateVote.user_id == user_id)
                .correlate(SessionDatePoll).scalar_subquery())
        votes = db.session.execute(
            select(SessionDatePoll, GameSession, options.label('total'), mine.label('answered'))
            .join(GameSession, and_(GameSession.id == SessionDatePoll.session_id,
                                    GameSession.campaign_id == SessionDatePoll.campaign_id))
            .where(SessionDatePoll.status == 'open', SessionDatePoll.campaign_id.in_(active),
                   GameSession.scheduled_at.is_(None), schedulable_clause(), mine < options)
            .order_by(SessionDatePoll.created_at, SessionDatePoll.id).limit(ALERT_LIMIT + 1)).all()
    href = lambda cid: f'/campaigns?campaign_id={cid}'
    return dict(
        missing_dates=[dict(campaign_id=s.campaign_id, campaign_name=names.get(s.campaign_id), session_id=s.id,
                            session_name=s.name, hub_href=href(s.campaign_id)) for s in missing[:ALERT_LIMIT]],
        missing_dates_more=len(missing) > ALERT_LIMIT,
        open_votes=[dict(poll_id=p.id, title=p.title, campaign_id=p.campaign_id, campaign_name=names.get(p.campaign_id),
                         session_id=s.id, session_name=s.name, answered=answered, total=total,
                         hub_href=href(p.campaign_id)) for p, s, total, answered in votes[:ALERT_LIMIT]],
        open_votes_more=len(votes) > ALERT_LIMIT)
