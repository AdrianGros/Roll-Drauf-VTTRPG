"""Recurrence arithmetic, authenticated persistence, and cancellation boundaries."""
from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import inspect

from vtt import create_app
from vtt.campaigns.session_calendar import local_to_utc, occurrence_local, parse_series, zone
from vtt.extensions import db
from vtt.models import Campaign, CampaignMember, GameSession, Role, SessionOccurrence, SessionSeries, User
from vtt.utils.time import utcnow


@pytest.fixture
def calendar_app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        role = Role(name='Player'); db.session.add(role); db.session.flush()
        users = [User(username=f'calendar-{i}', email=f'calendar-{i}@example.test', password_hash='test',
                      role_id=role.id, account_state='active', is_active=True) for i in range(1, 5)]
        db.session.add_all(users); db.session.flush()
        campaigns = [Campaign(name='Private campaign', owner_id=users[0].id),
                     Campaign(name='Other campaign', owner_id=users[3].id)]
        db.session.add_all(campaigns); db.session.flush()
        db.session.add_all([CampaignMember(campaign_id=campaigns[0].id, user_id=users[1].id, campaign_role='PLAYER', status='active'),
                            CampaignMember(campaign_id=campaigns[0].id, user_id=users[2].id, campaign_role='CO_DM', status='active')])
        db.session.commit()
        tokens = {str(i+1):create_access_token(identity=str(u.id)) for i, u in enumerate(users)}
        campaign_id = campaigns[0].id
        client = app.test_client()
        def api(path, *, actor='1', method='GET', data=None):
            client.set_cookie('access_token_cookie', tokens[actor])
            return client.open(f'/api/campaigns/{campaign_id}/'+path, method=method, json=data)
        yield app, api, campaigns, users
        db.session.remove(); db.drop_all()


def payload(**changes):
    first = (utcnow() + timedelta(days=2)).replace(hour=19, minute=30, second=0, microsecond=0)
    return dict(name='Friday adventures', first_local=first.isoformat(timespec='minutes'), timezone='Europe/Berlin',
                frequency='weekly', request_key=str(uuid4()), **changes)


@pytest.mark.parametrize('year,last', [(2027,28),(2028,29)])
def test_monthly_clamps_without_drifting_from_original_day(year, last):
    anchor = datetime(year, 1, 31, 19, 30)
    assert occurrence_local(anchor, 'monthly', 1) == datetime(year, 2, last, 19, 30)
    assert occurrence_local(anchor, 'monthly', 2) == datetime(year, 3, 31, 19, 30)
    assert occurrence_local(anchor, 'monthly', 12) == datetime(year+1, 1, 31, 19, 30)


@pytest.mark.parametrize('frequency,days', [('weekly',7),('biweekly',14)])
def test_weekly_preserves_berlin_clock_across_dst(frequency, days):
    anchor = datetime(2027, 3, 21, 19, 30)
    next_local = occurrence_local(anchor, frequency, 1)
    assert (next_local-anchor).days == days
    assert local_to_utc(anchor, zone('Europe/Berlin')).hour == 18
    assert local_to_utc(next_local, zone('Europe/Berlin')).hour == 17


def test_dst_gap_and_fold_are_explicit_and_deterministic():
    tz = zone('Europe/Berlin')
    with pytest.raises(ValueError, match='existiert'):
        local_to_utc(datetime(2027,3,28,2,30), tz, strict=True)
    assert local_to_utc(datetime(2027,3,28,2,30), tz) == datetime(2027,3,28,1,30)
    assert local_to_utc(datetime(2026,10,25,2,30), tz) == datetime(2026,10,25,0,30)


@pytest.mark.parametrize('field,value', [('name',''),('name','a'*101),('timezone','Mars'),('timezone',[]),
    ('frequency','daily'),('frequency',[]),('first_local','broken'),('first_local','2027-01-01T19:00+01:00'),
    ('first_local','0001-01-01T00:00'),('until','broken'),('duration_minutes',True),('duration_minutes',0),('duration_minutes',1441),('request_key','broken')])
def test_malformed_series_rejected_without_writes(calendar_app, field, value):
    _, api, _, _ = calendar_app
    body=payload(); body[field]=value
    assert api('session-series',method='POST',data=body).status_code == 400
    assert SessionSeries.query.count() == GameSession.query.count() == 0


def test_series_creates_real_sessions_once_and_survives_retry(calendar_app):
    _, api, campaigns, _ = calendar_app
    body=payload(); first=api('session-series',method='POST',data=body)
    assert first.status_code==201
    sid=first.json['series']['id']; count=GameSession.query.count()
    campaign_id=campaigns[0].id
    assert 50 <= count <= 53
    assert SessionOccurrence.query.count()==count
    assert api('session-series',method='POST',data=body).status_code==200
    db.session.remove()
    assert SessionSeries.query.count()==1 and GameSession.query.count()==count
    calendar=api('session-calendar?scope=year&anchor='+body['first_local'][:4]+'-01-01')
    assert calendar.status_code==200
    assert all(e['series_id']==sid for e in calendar.json['entries'])
    assert all(e['local_time']=='19:30' for e in calendar.json['entries'])
    assert all(s.campaign_id==campaign_id for s in GameSession.query.all())
    changed={**body,'name':'Different title'}
    assert api('session-series',method='POST',data=changed).status_code==400
    assert SessionSeries.query.count()==1


@pytest.mark.parametrize('frequency,step', [('weekly',7),('biweekly',14)])
def test_end_date_is_inclusive(calendar_app, frequency, step):
    _,api,_,_=calendar_app
    body=payload();body['frequency']=frequency
    end=date.fromisoformat(body['first_local'][:10])+timedelta(days=step*2)
    body['until']=end.isoformat()
    assert api('session-series',method='POST',data=body).status_code==201
    assert GameSession.query.count()==3
    for _ in range(2): assert api('session-calendar').status_code==200
    assert GameSession.query.count()==3


def test_once_and_legacy_one_off_both_appear(calendar_app):
    _,api,_,_=calendar_app
    body=payload();body['frequency']='once'
    assert api('session-series',method='POST',data=body).status_code==201
    at=GameSession.query.one().scheduled_at
    assert api('sessions',method='POST',data={'name':'Legacy one-off','scheduled_at':at.isoformat()+'Z'}).status_code==201
    result=api('session-calendar?scope=week&anchor='+body['first_local'][:10])
    assert len(result.json['entries'])==2
    assert {e['name'] for e in result.json['entries']}=={body['name'],'Legacy one-off'}


def test_cancel_occurrence_stays_cancelled_and_cannot_start(calendar_app):
    _,api,_,_=calendar_app
    assert api('session-series',method='POST',data=payload()).status_code==201
    session=GameSession.query.order_by(GameSession.scheduled_at).first();sid=session.id;total=GameSession.query.count()
    for _ in range(2):assert api(f'session-appointments/{sid}/cancel',method='POST',data={}).status_code==200
    assert api('session-calendar?scope=year').status_code==200
    assert GameSession.query.count()==total
    db.session.refresh(session)
    assert session.status=='cancelled'
    # The legacy runtime projection is unchanged (cancelled -> paused); the calendar
    # reports the original status instead of deriving "abgesagt" from it.
    assert session.get_runtime_status()=='paused'
    entries=api('session-calendar?scope=year').json['entries']
    assert [e['status'] for e in entries if e['id']==sid]==['cancelled']
    with pytest.raises(ValueError): session.start()
    assert SessionOccurrence.query.filter_by(session_id=sid).count()==1


def test_stopping_series_preserves_past_and_running_sessions(calendar_app):
    _,api,_,_=calendar_app
    result=api('session-series',method='POST',data=payload());sid=result.json['series']['id']
    sessions=GameSession.query.order_by(GameSession.id).all()
    sessions[0].scheduled_at=utcnow()-timedelta(days=1);sessions[0].status='completed';sessions[0].session_state='ended'
    sessions[1].status='in_progress';sessions[1].started_at=utcnow();sessions[1].session_state='active'
    db.session.commit()
    result=api(f'session-series/{sid}/stop',method='POST',data={})
    assert result.status_code==200 and result.json['cancelled']==len(sessions)-2
    assert api(f'session-series/{sid}/stop',method='POST',data={}).json['cancelled']==0
    assert api('session-calendar?scope=year').status_code==200
    assert GameSession.query.count()==len(sessions)
    assert GameSession.query.filter_by(status='completed').count()==1
    assert GameSession.query.filter_by(status='in_progress').count()==1
    assert api(f'session-appointments/{sessions[1].id}/cancel',method='POST',data={}).status_code==409


def test_member_reads_but_only_campaign_dm_and_codm_write(calendar_app):
    _,api,_,_=calendar_app
    assert api('session-calendar',actor='2').status_code==200
    assert api('session-calendar',actor='4').status_code==403
    assert api('session-series',actor='2',method='POST',data=payload()).status_code==403
    assert api('session-series',actor='4',method='POST',data=payload()).status_code==403
    assert api('session-series',actor='3',method='POST',data=payload()).status_code==201
    sid=SessionSeries.query.one().id
    assert api(f'session-series/{sid}/stop',actor='2',method='POST',data={}).status_code==403
    session=GameSession.query.first()
    assert api(f'session-appointments/{session.id}/cancel',actor='2',method='POST',data={}).status_code==403


def test_cross_campaign_ids_and_revoked_access_are_rejected(calendar_app):
    _,api,campaigns,users=calendar_app
    assert api('session-series',actor='3',method='POST',data=payload()).status_code==201
    other=GameSession(campaign_id=campaigns[1].id,name='Other secret',scheduled_at=utcnow()+timedelta(days=1))
    db.session.add(other);db.session.commit()
    assert api(f'session-appointments/{other.id}/cancel',method='POST',data={}).status_code==409
    member=CampaignMember.query.filter_by(user_id=users[2].id).one();member.status='left';db.session.commit()
    assert api('session-calendar',actor='3').status_code==403
    assert api(f'session-series/{SessionSeries.query.one().id}/stop',actor='3',method='POST',data={}).status_code==403
    assert other.status=='scheduled'


@pytest.mark.parametrize('query', ['scope=decade','anchor=garbage','anchor=9999-01-01','timezone=Bad'])
def test_calendar_queries_are_bounded(calendar_app,query):
    _,api,_,_=calendar_app
    assert api('session-calendar?'+query).status_code==400


def test_calendar_get_is_pure_and_explicit_post_rolls_forward(calendar_app, monkeypatch):
    from vtt.campaigns import session_calendar as service
    _,api,_,_=calendar_app
    body=payload();assert api('session-series',method='POST',data=body).status_code==201
    first_count=GameSession.query.count()
    series=SessionSeries.query.one();next_index=series.next_index
    first=GameSession.query.order_by(GameSession.id).first()
    assert api(f'session-appointments/{first.id}/cancel',method='POST',data={}).status_code==200
    monkeypatch.setattr(service,'utcnow',lambda:utcnow()+timedelta(days=90))
    for _ in range(2):assert api('session-calendar?scope=year').status_code==200
    db.session.remove()
    # Reads never materialize, advance next_index, lock or commit.
    assert GameSession.query.count()==first_count
    assert SessionSeries.query.one().next_index==next_index
    # Only the explicit DM/Co-DM POST tops up the twelve-month horizon.
    assert api('session-series/materialize',actor='2',method='POST',data={}).status_code==403
    top_up=api('session-series/materialize',method='POST',data={})
    assert top_up.status_code==200 and top_up.json['created']>0
    db.session.remove()
    assert GameSession.query.count()==first_count+top_up.json['created']
    assert api('session-series/materialize',method='POST',data={}).json['created']==0
    assert GameSession.query.filter_by(status='cancelled').count()==1
    assert SessionOccurrence.query.count()==GameSession.query.count()


def test_additive_migration_is_repeatable(calendar_app):
    from tools.migrate_session_calendar import NEW_TABLES, upgrade
    from vtt.models import SessionDateOption, SessionDatePoll, SessionDateVote
    for model in (SessionDateVote,SessionDateOption,SessionDatePoll,SessionOccurrence,SessionSeries):
        model.__table__.drop(db.engine)
    tables=set(inspect(db.engine).get_table_names())
    with db.engine.begin() as conn:upgrade(conn)
    with db.engine.begin() as conn:upgrade(conn)
    assert set(inspect(db.engine).get_table_names())-tables==set(NEW_TABLES)
    assert set(NEW_TABLES)=={'session_series','session_occurrences','session_date_polls','session_date_options','session_date_votes'}
