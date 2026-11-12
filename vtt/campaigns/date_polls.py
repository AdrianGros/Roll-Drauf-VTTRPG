"""Session date polls: managers propose, active participants answer, a manager decides.

Every writer takes the shared campaign writer lock (``lock_campaign``) first and then
re-validates, inside that lock, the actor's current campaign rights and the whole
poll -> option -> session -> campaign chain. Nothing here trusts a client-supplied user
id: the voter is always the authenticated user. Reads never write.

``revision`` changes only when the poll's state changes (close / cancel), not on votes,
so a manager's expected revision stays valid while members keep answering.
"""
import hashlib
import json
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select

from vtt.campaigns.session_calendar import (HORIZON_DAYS, NO_ACCESS, CalendarError, ensure_manager, is_managed,
                                            local_to_utc, lock_campaign, session_is_schedulable, utc_iso, zone)
from vtt.extensions import db
from vtt.models import (Campaign, CampaignMember, GameSession, SessionDateOption, SessionDatePoll,
                        SessionDateVote, User)
from vtt.models.session_date_poll import VOTE_VALUES
from vtt.utils.time import utcnow

MAX_OPTIONS = 20
LIST_LIMIT = 50


def _int(value):
    return value if type(value) is int and 0 < value < 2**31 else None


def parse_poll(data, *, now=None):
    now = now or utcnow()
    if not isinstance(data, dict):
        raise CalendarError('Ungültige Abstimmungsdaten.')
    session_id = _int(data.get('session_id'))
    if session_id is None:
        raise CalendarError('Bitte eine Session wählen.')
    title = data.get('title')
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 100:
        raise CalendarError('Bitte einen Titel mit höchstens 100 Zeichen eingeben.')
    tz = zone(data.get('timezone', 'Europe/Berlin'))
    try:
        key = str(uuid.UUID(data['request_key']))
    except (ValueError, TypeError, KeyError, AttributeError):
        raise CalendarError('Ungültige Anfragekennung.') from None
    raw = data.get('options')
    if not isinstance(raw, list) or not raw:
        raise CalendarError('Bitte mindestens eine Terminoption angeben.')
    if len(raw) > MAX_OPTIONS:
        raise CalendarError('Höchstens 20 verschiedene Terminoptionen.')
    parsed = {}
    for item in raw:
        if not isinstance(item, dict):
            raise CalendarError('Ungültige Terminoption.')
        try:
            local = datetime.fromisoformat(item['local'])
            if local.tzinfo is not None or local.second or local.microsecond:
                raise ValueError()
            at = local_to_utc(local, tz, strict=True)
        except CalendarError:
            raise
        except (ValueError, TypeError, KeyError, OverflowError):
            raise CalendarError('Bitte für jede Option Datum und Uhrzeit angeben.') from None
        duration = item.get('duration_minutes')
        if duration is not None and (type(duration) is not int or not 1 <= duration <= 1440):
            raise CalendarError('Die Dauer muss zwischen 1 und 1440 Minuten liegen.')
        if at <= now or at > now + timedelta(days=HORIZON_DAYS):
            raise CalendarError('Jede Option muss in der Zukunft und innerhalb der nächsten zwölf Monate liegen.')
        if at in parsed:
            raise CalendarError('Terminoptionen müssen verschieden sein.')
        parsed[at] = duration
    options = sorted(parsed.items())
    digest = hashlib.sha256(json.dumps(
        dict(session_id=session_id, title=title.strip(), options=[[at.isoformat(), d] for at, d in options]),
        sort_keys=True).encode()).hexdigest()
    return dict(session_id=session_id, title=title.strip(), options=options), key, digest


def participant_ids(campaign):
    ids = {campaign.owner_id}
    ids.update(db.session.execute(select(CampaignMember.user_id).where(
        CampaignMember.campaign_id == campaign.id, CampaignMember.status == 'active')).scalars().all())
    return ids


def _scoped_poll(campaign_id, poll_id, *, lock=False):
    query = select(SessionDatePoll).where(SessionDatePoll.id == poll_id, SessionDatePoll.campaign_id == campaign_id)
    poll = db.session.execute(query.with_for_update() if lock else query).scalar_one_or_none()
    if poll is None:
        raise CalendarError('Abstimmung nicht gefunden.', 404)
    return poll


def _scoped_option(poll, option_id):
    option = SessionDateOption.query.filter_by(id=option_id, poll_id=poll.id).first() if _int(option_id) else None
    if option is None:
        raise CalendarError('Diese Option gehört nicht zu dieser Abstimmung.', 404)
    return option


def _locked_session(campaign_id, session_id):
    session = db.session.execute(select(GameSession).where(
        GameSession.id == session_id, GameSession.campaign_id == campaign_id).with_for_update()).scalar_one_or_none()
    if session is None:
        raise CalendarError('Diese Session gehört nicht zu dieser Kampagne.', 404)
    return session


def _unscheduled(session):
    return session.scheduled_at is None and session_is_schedulable(session)


# ---------------------------------------------------------------- writers

def create_poll(campaign_id, actor_id, data):
    values, key, digest = parse_poll(data)
    campaign = lock_campaign(campaign_id)
    ensure_manager(campaign, actor_id)
    existing = SessionDatePoll.query.filter_by(campaign_id=campaign_id, created_by=actor_id, request_key=key).first()
    if existing:
        if existing.input_digest != digest:
            raise CalendarError('Diese Anfrage wurde bereits mit anderen Abstimmungsdaten gespeichert.', 409)
        return existing, False
    if campaign.status != 'active':
        raise CalendarError('Abstimmungen gibt es nur in aktiven Kampagnen.', 409)
    session = _locked_session(campaign_id, values['session_id'])
    if not _unscheduled(session):
        raise CalendarError('Die Session hat bereits einen Termin oder wurde gestartet.', 409)
    if SessionDatePoll.query.filter_by(session_id=session.id, status='open').first():
        raise CalendarError('Für diese Session läuft bereits eine Terminabstimmung.', 409)
    poll = SessionDatePoll(campaign_id=campaign_id, session_id=session.id, created_by=actor_id, request_key=key,
                           input_digest=digest, title=values['title'], status='open', revision=1)
    poll.options = [SessionDateOption(starts_at=at, duration_minutes=duration) for at, duration in values['options']]
    db.session.add(poll)
    db.session.flush()
    return poll, True


def set_vote(campaign_id, poll_id, option_id, user_id, value):
    if value not in VOTE_VALUES:
        raise CalendarError('Bitte Ja, Vielleicht oder Nein wählen.')
    campaign = lock_campaign(campaign_id)
    if user_id not in participant_ids(campaign):
        raise CalendarError(NO_ACCESS, 403)
    poll = _scoped_poll(campaign_id, poll_id, lock=True)
    option = _scoped_option(poll, option_id)
    if poll.status != 'open' or campaign.status != 'active':
        raise CalendarError('Diese Abstimmung ist nicht mehr offen.', 409)
    if not _unscheduled(_locked_session(campaign_id, poll.session_id)):
        raise CalendarError('Die Session hat bereits einen Termin oder wurde gestartet.', 409)
    vote = SessionDateVote.query.filter_by(option_id=option.id, user_id=user_id).first()
    if vote is None:
        db.session.add(SessionDateVote(option_id=option.id, user_id=user_id, value=value))
    elif vote.value != value:
        vote.value, vote.updated_at = value, utcnow()
    db.session.flush()
    db.session.expire(option, ['votes'])    # the serialized poll must show this write
    return poll


def finalize_poll(campaign_id, poll_id, actor_id, expected_revision, option_id):
    """CAS: set the session's schedule and close the poll in one transaction.

    Returns (poll, session, changed). The identical retry of an already successful close
    returns the same session with changed=False; any other choice is a 409.
    """
    if _int(expected_revision) is None or _int(option_id) is None:
        raise CalendarError('Bitte Abstimmungsstand und Terminoption angeben.')
    campaign = lock_campaign(campaign_id)
    ensure_manager(campaign, actor_id)
    poll = _scoped_poll(campaign_id, poll_id, lock=True)
    option = _scoped_option(poll, option_id)
    session = _locked_session(campaign_id, poll.session_id)
    if poll.status == 'closed':
        if poll.selected_option_id == option.id and expected_revision == poll.revision - 1:
            return poll, session, False
        raise CalendarError('Diese Abstimmung wurde bereits mit einer anderen Auswahl abgeschlossen.', 409)
    if poll.status != 'open':
        raise CalendarError('Diese Abstimmung wurde abgebrochen.', 409)
    if expected_revision != poll.revision:
        raise CalendarError('Die Abstimmung wurde inzwischen geändert. Bitte neu laden.', 409)
    if campaign.status != 'active':
        raise CalendarError('Abstimmungen gibt es nur in aktiven Kampagnen.', 409)
    if not _unscheduled(session):
        raise CalendarError('Die Session hat inzwischen einen Termin oder wurde gestartet.', 409)
    now = utcnow()
    if option.starts_at <= now:
        raise CalendarError('Dieser Termin liegt bereits in der Vergangenheit.', 409)
    session.scheduled_at = option.starts_at
    if option.duration_minutes is not None:
        session.duration_minutes = option.duration_minutes
    poll.status, poll.selected_option_id = 'closed', option.id
    poll.revision, poll.updated_at, poll.closed_at = poll.revision + 1, now, now
    return poll, session, True


def cancel_poll(campaign_id, poll_id, actor_id, expected_revision=None):
    campaign = lock_campaign(campaign_id)
    ensure_manager(campaign, actor_id)
    poll = _scoped_poll(campaign_id, poll_id, lock=True)
    if poll.status == 'cancelled':
        return poll
    if poll.status == 'closed':
        raise CalendarError('Eine abgeschlossene Abstimmung kann nicht abgebrochen werden.', 409)
    if expected_revision is not None and expected_revision != poll.revision:
        raise CalendarError('Die Abstimmung wurde inzwischen geändert. Bitte neu laden.', 409)
    now = utcnow()
    poll.status, poll.revision, poll.updated_at, poll.closed_at = 'cancelled', poll.revision + 1, now, now
    return poll


# ---------------------------------------------------------------- pure reads

def get_poll(campaign_id, poll_id):
    return _scoped_poll(campaign_id, poll_id)


def list_polls(campaign_id, *, session_id=None, status=None):
    query = select(SessionDatePoll).where(SessionDatePoll.campaign_id == campaign_id)
    if session_id is not None:
        query = query.where(SessionDatePoll.session_id == session_id)
    if status is not None:
        query = query.where(SessionDatePoll.status == status)
    rows = db.session.execute(query.order_by(SessionDatePoll.id.desc()).limit(LIST_LIMIT + 1)).scalars().all()
    return rows[:LIST_LIMIT], len(rows) > LIST_LIMIT


def serialize_poll(poll, viewer_id):
    """Options, totals and the viewer's own answers; named answers only for managers."""
    campaign = db.session.get(Campaign, poll.campaign_id)
    role = db.session.execute(select(CampaignMember.campaign_role).where(
        CampaignMember.campaign_id == poll.campaign_id, CampaignMember.user_id == viewer_id,
        CampaignMember.status == 'active')).scalar_one_or_none()
    manager = is_managed(campaign.id, campaign.owner_id, role, viewer_id)
    eligible = participant_ids(campaign)
    session = db.session.get(GameSession, poll.session_id)
    options, answered = [], 0
    for option in poll.options:
        counts = dict.fromkeys(VOTE_VALUES, 0)
        mine = None
        for vote in option.votes:
            if vote.user_id not in eligible:
                continue            # answers of members who left no longer count
            counts[vote.value] += 1
            if vote.user_id == viewer_id:
                mine = vote.value
        answered += mine is not None
        options.append(dict(id=option.id, starts_at=utc_iso(option.starts_at), duration_minutes=option.duration_minutes,
                            mine=mine, **counts))
    payload = dict(id=poll.id, campaign_id=poll.campaign_id, session_id=poll.session_id,
                   session_name=session.name if session else None, title=poll.title, status=poll.status,
                   revision=poll.revision, selected_option_id=poll.selected_option_id, options=options,
                   participant_count=len(eligible), answered=answered, total=len(options),
                   my_complete=answered == len(options), can_manage=manager,
                   created_at=utc_iso(poll.created_at), closed_at=utc_iso(poll.closed_at) if poll.closed_at else None)
    if manager:
        names = dict(db.session.execute(select(User.id, User.username).where(User.id.in_(eligible))).all())
        by_user = {uid: {} for uid in eligible}
        for option in poll.options:
            for vote in option.votes:
                if vote.user_id in by_user:
                    by_user[vote.user_id][option.id] = vote.value
        payload['participants'] = sorted(
            (dict(user_id=uid, username=names.get(uid), answers=answers, answered=len(answers))
             for uid, answers in by_user.items()), key=lambda row: (str(row['username']).lower(), row['user_id']))
    return payload
