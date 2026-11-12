"""C06: own all-campaign calendar, alerts, explicit materialization and date polls.

Runs against the testing app with seeded users; nothing here talks to production.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError

from vtt import create_app
from vtt.campaigns import session_calendar as service
from vtt.extensions import db
from vtt.models import (Campaign, CampaignMember, GameSession, Role, SessionDateOption, SessionDatePoll,
                        SessionDateVote, SessionOccurrence, SessionSeries, User)
from vtt.utils.time import utcnow

NOW = datetime(2026, 11, 12, 12, 0)


@pytest.fixture
def world():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        role = Role(name='Player'); db.session.add(role); db.session.flush()
        users = {i: User(username=f'c06-{i}', email=f'c06-{i}@example.test', password_hash='x', role_id=role.id,
                         account_state='active', is_active=True) for i in range(1, 11)}
        db.session.add_all(users.values()); db.session.flush()
        camp = {'A': Campaign(name='Alpha', owner_id=users[1].id),
                'B': Campaign(name='Bravo', owner_id=users[4].id),
                'C': Campaign(name='Public Charlie', owner_id=users[4].id, is_discoverable=True),
                'D': Campaign(name='Deleted Delta', owner_id=users[1].id, deleted_at=NOW)}
        db.session.add_all(camp.values()); db.session.flush()
        def member(cid, uid, role_name, state):
            db.session.add(CampaignMember(campaign_id=camp[cid].id, user_id=users[uid].id, campaign_role=role_name, status=state))
        for uid, role_name, state in [(2, 'PLAYER', 'active'), (3, 'CO_DM', 'active'), (5, 'OBSERVER', 'active'),
                                      (6, 'PLAYER', 'invited'), (7, 'PLAYER', 'left'), (8, 'PLAYER', 'pending'),
                                      (9, 'PLAYER', 'kicked')]:
            member('A', uid, role_name, state)
        member('B', 2, 'PLAYER', 'active')
        db.session.commit()
        ids = {k: v.id for k, v in camp.items()}
        uid = {k: v.id for k, v in users.items()}
        tokens = {k: create_access_token(identity=str(v)) for k, v in uid.items()}
        client = app.test_client()

        def call(actor, method, path, data=None):
            client.set_cookie('access_token_cookie', tokens[actor])
            return client.open('/api/campaigns/' + path, method=method, json=data)

        def session(cid, at=None, **fields):
            row = GameSession(campaign_id=ids[cid], name=fields.pop('name', f'S-{cid}-{uuid4().hex[:6]}'),
                              scheduled_at=at, **fields)
            db.session.add(row); db.session.commit()
            return row.id
        yield app, call, session, ids, uid
        db.session.remove(); db.drop_all()


@pytest.fixture
def frozen(monkeypatch):
    monkeypatch.setattr(service, 'utcnow', lambda: NOW)


def names(response):
    return sorted(e['session_name'] for e in response.json['entries'])


# ------------------------------------------------------------------ own calendar

def test_calendar_membership_matrix_and_no_private_fields(world, frozen):
    _, call, session, ids, uid = world
    at = NOW + timedelta(days=3)
    for cid in 'ABCD':
        session(cid, at, name=f'only-{cid}', session_log='SECRET LOG', session_password='hunter2')
    expected = {1: ['only-A'], 2: ['only-A', 'only-B'], 3: ['only-A'], 4: ['only-B', 'only-C'], 5: ['only-A'],
                6: [], 7: [], 8: [], 9: [], 10: []}
    for actor, sessions in expected.items():
        response = call(actor, 'GET', 'my-session-calendar?anchor=2026-11-12')
        assert response.status_code == 200, actor
        assert names(response) == sessions, actor      # public/discoverable, invited, pending, left, kicked: nothing
        assert response.json['complete'] is True
    body = call(2, 'GET', 'my-session-calendar?anchor=2026-11-12').get_data(as_text=True)
    assert 'SECRET LOG' not in body and 'hunter2' not in body and 'session_log' not in body
    entry = call(1, 'GET', 'my-session-calendar?anchor=2026-11-12').json['entries'][0]
    assert entry['campaign_name'] == 'Alpha' and entry['scheduled_at'].endswith('Z')
    assert entry['hub_href'] == f"/campaigns?campaign_id={ids['A']}" and entry['status'] == 'scheduled'
    assert call(1, 'GET', 'my-session-calendar?anchor=2026-11-12').json['campaigns'] == [
        dict(id=ids['A'], name='Alpha', can_manage=True)]
    assert call(2, 'GET', 'my-session-calendar?anchor=2026-11-12').json['can_manage_any'] is False
    assert call(3, 'GET', 'my-session-calendar?anchor=2026-11-12').json['can_manage_any'] is True


def test_calendar_filter_accepts_only_own_ids_and_rejects_foreign(world, frozen):
    _, call, session, ids, _ = world
    for cid in 'ABC':
        session(cid, NOW + timedelta(days=2), name=f'f-{cid}')
    ok = call(2, 'GET', f"my-session-calendar?anchor=2026-11-12&campaign_ids={ids['B']}")
    assert names(ok) == ['f-B'] and ok.json['filter_campaign_ids'] == [ids['B']]
    assert names(call(2, 'GET', f"my-session-calendar?campaign_id={ids['A']}&campaign_id={ids['B']}")) == ['f-A', 'f-B']
    for foreign in (ids['C'], ids['D'], 999999):     # public-only, deleted, unknown are all rejected alike
        assert call(2, 'GET', f"my-session-calendar?campaign_ids={ids['A']},{foreign}").status_code == 403
    assert call(6, 'GET', f"my-session-calendar?campaign_ids={ids['A']}").status_code == 403  # invited only
    for bad in ('x', '0', '-1', '99999999999'):
        assert call(2, 'GET', f'my-session-calendar?campaign_ids={bad}').status_code == 400
    many = ','.join(str(i) for i in range(1, 52))
    assert call(2, 'GET', f'my-session-calendar?campaign_ids={many}').status_code == 400


@pytest.mark.parametrize('query', ['scope=week', 'scope=year', 'anchor=junk', 'anchor=2015-01-01', 'anchor=2027-12-01',
                                   'anchor=0001-01-01', 'timezone=Mars/Base', 'cursor=!!', 'limit=0', 'limit=201', 'limit=x'])
def test_calendar_inputs_are_bounded(world, frozen, query):
    _, call, _, _, _ = world
    assert call(1, 'GET', 'my-session-calendar?' + query).status_code == 400


def test_anchor_window_edges_are_inclusive(world, frozen):
    _, call, _, _, _ = world
    assert call(1, 'GET', 'my-session-calendar?anchor=2027-11-12').status_code == 200   # 12 months ahead
    assert call(1, 'GET', 'my-session-calendar?anchor=2016-11-12').status_code == 200   # 10 years back
    assert call(1, 'GET', 'my-session-calendar?anchor=2027-11-13').status_code == 400
    assert call(1, 'GET', 'my-session-calendar?anchor=2016-11-11').status_code == 400


def test_month_year_wrap_uses_real_local_month_and_utc_dates(world, frozen):
    _, call, session, _, _ = world
    december = datetime(2026, 12, 31, 23, 30)           # 2027-01-01 00:30 in Berlin, still Dec 31 in UTC
    session('A', december, name='new-years-eve')
    session('A', datetime(2026, 11, 30, 23, 30), name='dec-first-berlin')
    berlin_dec = call(1, 'GET', 'my-session-calendar?scope=month&anchor=2026-12-20&timezone=Europe/Berlin')
    assert (berlin_dec.json['start'], berlin_dec.json['end']) == ('2026-12-01', '2027-01-01')
    assert names(berlin_dec) == ['dec-first-berlin']
    utc_dec = call(1, 'GET', 'my-session-calendar?scope=month&anchor=2026-12-20&timezone=UTC')
    assert names(utc_dec) == ['new-years-eve'] and utc_dec.json['entries'][0]['local_date'] == '2026-12-31'
    jan = call(1, 'GET', 'my-session-calendar?scope=month&anchor=2027-01-05&timezone=Europe/Berlin').json
    assert [(e['session_name'], e['local_date'], e['local_time']) for e in jan['entries']] == [('new-years-eve', '2027-01-01', '00:30')]
    assert call(1, 'GET', 'my-session-calendar?scope=month&anchor=2026-12-20&timezone=America/Los_Angeles').json['utc_start'] == '2026-12-01T08:00:00Z'


def test_rolling30_crosses_dst_with_local_midnights_not_24h_days(world, frozen):
    _, call, session, _, _ = world
    first = call(1, 'GET', 'my-session-calendar?scope=rolling30&anchor=2027-03-15&timezone=Europe/Berlin').json
    assert (first['start'], first['end']) == ('2027-03-15', '2027-04-14')
    assert (first['utc_start'], first['utc_end']) == ('2027-03-14T23:00:00Z', '2027-04-13T22:00:00Z')   # CET -> CEST
    session('A', datetime(2027, 4, 13, 21, 59), name='last-minute-in')
    session('A', datetime(2027, 4, 13, 22, 0), name='first-minute-out')
    session('A', datetime(2027, 3, 14, 23, 0), name='first-minute-in')
    session('A', datetime(2027, 3, 14, 22, 59), name='last-minute-out')
    result = call(1, 'GET', 'my-session-calendar?scope=rolling30&anchor=2027-03-15&timezone=Europe/Berlin')
    assert names(result) == ['first-minute-in', 'last-minute-in']
    utc = call(1, 'GET', 'my-session-calendar?scope=rolling30&anchor=2027-03-15&timezone=UTC').json
    assert (utc['utc_start'], utc['utc_end']) == ('2027-03-15T00:00:00Z', '2027-04-14T00:00:00Z')
    assert call(1, 'GET', 'my-session-calendar?scope=month&anchor=2027-03-31&timezone=Europe/Berlin').json['utc_end'] == '2027-03-31T22:00:00Z'


def test_cancelled_status_is_the_original_and_not_runtime_paused(world, frozen):
    _, call, session, _, _ = world
    cancelled = session('A', NOW + timedelta(days=2), name='off', status='cancelled', session_state='ended')
    paused = session('A', NOW + timedelta(days=3), name='paused', status='paused', session_state='paused')
    rows = {e['session_name']: e for e in call(2, 'GET', 'my-session-calendar?anchor=2026-11-12').json['entries']}
    assert rows['off']['status'] == 'cancelled' and rows['off']['cancelled'] and not rows['off']['cancellable']
    assert rows['paused']['status'] == 'paused' and not rows['paused']['cancelled']
    assert db.session.get(GameSession, cancelled).get_runtime_status() == 'paused'     # legacy projection unchanged


def test_pagination_is_stable_complete_and_membership_is_checked_per_page(world, frozen):
    _, call, session, ids, _ = world
    same = NOW + timedelta(days=5)
    db.session.add_all([GameSession(campaign_id=ids['A'], name=f'p{i:03d}', scheduled_at=same if i < 120 else same + timedelta(minutes=i))
                        for i in range(205)])
    db.session.commit()
    first = call(2, 'GET', 'my-session-calendar?anchor=2026-11-12').json
    assert len(first['entries']) == 200 and first['complete'] is False and first['next_cursor']
    second = call(2, 'GET', 'my-session-calendar?anchor=2026-11-12&cursor=' + first['next_cursor']).json
    assert len(second['entries']) == 5 and second['complete'] is True and second['next_cursor'] is None
    ids_seen = [e['session_id'] for e in first['entries'] + second['entries']]
    assert len(set(ids_seen)) == 205
    order = [(e['scheduled_at'], e['session_id']) for e in first['entries'] + second['entries']]
    assert order == sorted(order)
    pages, cursor = [], None
    while True:
        page = call(2, 'GET', 'my-session-calendar?anchor=2026-11-12&limit=50' + (f'&cursor={cursor}' if cursor else '')).json
        pages.append(len(page['entries'])); cursor = page['next_cursor']
        if not cursor: break
    assert pages == [50, 50, 50, 50, 5]
    CampaignMember.query.filter_by(campaign_id=ids['A'], user_id=2).update({'status': 'left'}); db.session.commit()
    revoked = call(2, 'GET', 'my-session-calendar?anchor=2026-11-12&cursor=' + first['next_cursor'])
    assert revoked.status_code == 200 and revoked.json['entries'] == [] and revoked.json['complete'] is True


# ------------------------------------------------------------------ alerts + materialize

def test_alerts_show_only_own_managed_missing_dates_and_own_incomplete_votes(world):
    _, call, session, ids, uid = world
    undated = session('A', None, name='needs-date')
    session('A', utcnow() + timedelta(days=4), name='dated')
    session('A', None, name='cancelled-undated', status='cancelled')
    other = session('B', None, name='b-needs-date')
    owner_alerts = call(1, 'GET', 'my-session-alerts').json
    assert [a['session_name'] for a in owner_alerts['missing_dates']] == ['needs-date']
    assert owner_alerts['missing_dates'][0]['hub_href'] == f"/campaigns?campaign_id={ids['A']}"
    assert [a['session_name'] for a in call(3, 'GET', 'my-session-alerts').json['missing_dates']] == ['needs-date']
    for actor in (2, 5, 6, 7, 8, 10):                  # Player, Observer and everybody without active management
        assert call(actor, 'GET', 'my-session-alerts').json['missing_dates'] == [], actor
    assert [a['session_name'] for a in call(4, 'GET', 'my-session-alerts').json['missing_dates']] == ['b-needs-date']
    start = (utcnow() + timedelta(days=3)).replace(hour=17, minute=0, second=0, microsecond=0)
    options = [{'local': (start + timedelta(days=i)).isoformat(timespec='minutes')} for i in range(2)]
    created = call(1, 'POST', f"{ids['A']}/date-polls", dict(session_id=undated, title='When?', timezone='UTC', options=options, request_key=str(uuid4())))
    assert created.status_code == 201
    poll = created.json['poll']
    assert [a['poll_id'] for a in call(2, 'GET', 'my-session-alerts').json['open_votes']] == [poll['id']]
    assert call(2, 'GET', 'my-session-alerts').json['open_votes'][0]['answered'] == 0
    for actor in (6, 7, 8, 9, 10, 4):
        assert call(actor, 'GET', 'my-session-alerts').json['open_votes'] == [], actor
    assert call(1, 'GET', 'my-session-alerts').json['open_votes'][0]['total'] == 2     # the owner votes too
    first, second = poll['options'][0]['id'], poll['options'][1]['id']
    assert call(2, 'PUT', f"{ids['A']}/date-polls/{poll['id']}/options/{first}/vote", {'value': 'yes'}).status_code == 200
    assert call(2, 'GET', 'my-session-alerts').json['open_votes'][0]['answered'] == 1
    assert call(2, 'PUT', f"{ids['A']}/date-polls/{poll['id']}/options/{second}/vote", {'value': 'no'}).status_code == 200
    assert call(2, 'GET', 'my-session-alerts').json['open_votes'] == []              # answered everything
    assert call(2, 'GET', f"my-session-alerts?campaign_ids={ids['A']}").status_code == 200
    assert call(2, 'GET', f"my-session-alerts?campaign_ids={ids['C']}").status_code == 403
    assert other  # keeps the foreign-campaign session in play for the matrix above


def test_explicit_materialize_is_dm_only_bounded_and_never_a_get(world):
    _, call, _, ids, _ = world
    first = (utcnow() + timedelta(days=2)).replace(hour=19, minute=30, second=0, microsecond=0)
    body = dict(name='Weekly', first_local=first.isoformat(timespec='minutes'), timezone='UTC', frequency='weekly', request_key=str(uuid4()))
    assert call(1, 'POST', f"{ids['A']}/session-series", body).status_code == 201
    SessionSeries.query.update({'next_index': 1}); SessionOccurrence.query.delete(); GameSession.query.delete(); db.session.commit()
    for actor in (1, 2, 5):
        call(actor, 'GET', 'my-session-calendar?anchor=' + first.date().isoformat())
    assert GameSession.query.count() == 0                                         # GET never materializes
    for actor in (2, 5, 6, 10):
        assert call(actor, 'POST', 'my-session-calendar/materialize', {}).status_code == 403, actor
    assert call(1, 'POST', 'my-session-calendar/materialize', {'campaign_ids': [ids['B']]}).status_code == 403   # not own
    assert call(3, 'POST', 'my-session-calendar/materialize', {'campaign_ids': [ids['A'], ids['B']]}).status_code == 403
    assert call(1, 'POST', 'my-session-calendar/materialize', {'campaign_ids': ['1']}).status_code == 400
    assert GameSession.query.count() == 0
    result = call(3, 'POST', 'my-session-calendar/materialize', {})
    assert result.status_code == 200 and result.json['remaining'] == 0
    assert [c['campaign_id'] for c in result.json['campaigns']] == [ids['A']] and result.json['campaigns'][0]['created'] > 40
    count = GameSession.query.count()
    assert call(1, 'POST', 'my-session-calendar/materialize', {}).json['campaigns'][0]['created'] == 0
    assert GameSession.query.count() == count and SessionOccurrence.query.count() == count


def test_carried_player_context_reads_but_never_writes(world, monkeypatch):
    _, call, session, ids, uid = world
    import vtt.play.contexts as contexts
    undated = session('A', None, name='ctx')
    monkeypatch.setattr(contexts, 'restrict_campaign_role', lambda campaign_id, user_id: user_id == uid[1])
    assert call(1, 'GET', 'my-session-calendar').status_code == 200
    assert call(1, 'GET', 'my-session-calendar').json['can_manage_any'] is False
    assert call(1, 'GET', 'my-session-alerts').json['missing_dates'] == []
    assert call(1, 'GET', f"{ids['A']}/date-polls").status_code == 200
    first = (utcnow() + timedelta(days=2)).replace(hour=19, minute=30, second=0, microsecond=0)
    series = dict(name='x', first_local=first.isoformat(timespec='minutes'), timezone='UTC', frequency='once', request_key=str(uuid4()))
    assert call(1, 'POST', f"{ids['A']}/session-series", series).status_code == 403
    assert call(1, 'POST', f"{ids['A']}/session-series/materialize", {}).status_code == 403
    assert call(1, 'POST', 'my-session-calendar/materialize', {}).status_code == 403
    poll = dict(session_id=undated, title='t', timezone='UTC', request_key=str(uuid4()),
                options=[{'local': (utcnow() + timedelta(days=5)).replace(microsecond=0, second=0).isoformat(timespec='minutes')}])
    assert call(1, 'POST', f"{ids['A']}/date-polls", poll).status_code == 403
    assert SessionSeries.query.count() == SessionDatePoll.query.count() == 0


# ------------------------------------------------------------------ date polls

def future(days, hour=19):
    return (utcnow() + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)


def poll_body(session_id, options=None, **changes):
    options = options or [{'local': future(3 + i).isoformat(timespec='minutes'), 'duration_minutes': 180 if i == 0 else None} for i in range(3)]
    body = dict(session_id=session_id, title='Termin?', timezone='UTC', options=options, request_key=str(uuid4()))
    body.update(changes)
    return body


def make_poll(call, ids, session_id, cid='A', actor=1, **changes):
    response = call(actor, 'POST', f'{ids[cid]}/date-polls', poll_body(session_id, **changes))
    assert response.status_code == 201, response.json
    return response.json['poll']


def vote(call, ids, poll, index, value, actor=2, cid='A'):
    return call(actor, 'PUT', f"{ids[cid]}/date-polls/{poll['id']}/options/{poll['options'][index]['id']}/vote", {'value': value})


def test_poll_create_idempotent_authorized_and_bounded(world):
    _, call, session, ids, uid = world
    sid = session('A', None)
    body = poll_body(sid)
    created = call(1, 'POST', f"{ids['A']}/date-polls", body)
    assert created.status_code == 201 and created.json['created'] is True
    retry = call(1, 'POST', f"{ids['A']}/date-polls", body)
    assert retry.status_code == 200 and retry.json['poll']['id'] == created.json['poll']['id'] and retry.json['created'] is False
    assert call(1, 'POST', f"{ids['A']}/date-polls", {**body, 'title': 'Anders'}).status_code == 409
    assert SessionDatePoll.query.count() == 1 and SessionDateOption.query.count() == 3
    assert call(3, 'POST', f"{ids['A']}/date-polls", poll_body(sid)).status_code == 409          # one open poll per session
    for actor in (2, 5, 6, 7, 8, 9, 10, 4):
        assert call(actor, 'POST', f"{ids['A']}/date-polls", poll_body(sid)).status_code == 403, actor
    foreign = session('B', None)
    assert call(1, 'POST', f"{ids['A']}/date-polls", poll_body(foreign)).status_code == 404
    dated = session('A', future(9))
    assert call(1, 'POST', f"{ids['A']}/date-polls", poll_body(dated)).status_code == 409
    started = session('A', None, status='in_progress', session_state='active', started_at=utcnow())
    assert call(1, 'POST', f"{ids['A']}/date-polls", poll_body(started)).status_code == 409
    assert SessionDatePoll.query.count() == 1


@pytest.mark.parametrize('mutate', [
    lambda b: b.update(title=''), lambda b: b.update(title='x' * 101), lambda b: b.update(session_id=True),
    lambda b: b.update(session_id='1'), lambda b: b.update(request_key='nope'), lambda b: b.update(timezone='Nowhere'),
    lambda b: b.update(options=[]), lambda b: b.update(options='x'), lambda b: b.update(options=[{'local': 'junk'}]),
    lambda b: b.update(options=[{'local': '2020-01-01T10:00'}]),
    lambda b: b.update(options=[{'local': future(400).isoformat(timespec='minutes')}]),
    lambda b: b.update(options=[{'local': future(3).isoformat(timespec='minutes') + '+02:00'}]),
    lambda b: b.update(options=[{'local': future(3).isoformat(timespec='minutes'), 'duration_minutes': 0}]),
    lambda b: b.update(options=[{'local': future(3).isoformat(timespec='minutes'), 'duration_minutes': 1441}]),
    lambda b: b.update(options=[{'local': future(3).isoformat(timespec='minutes'), 'duration_minutes': True}]),
    lambda b: b.update(options=[{'local': future(3).isoformat(timespec='minutes')}] * 2),
    lambda b: b.update(options=[{'local': (future(2) + timedelta(hours=i)).isoformat(timespec='minutes')} for i in range(21)]),
])
def test_poll_rejects_malformed_or_unbounded_payloads_without_writes(world, mutate):
    _, call, session, ids, _ = world
    body = poll_body(session('A', None)); mutate(body)
    assert call(1, 'POST', f"{ids['A']}/date-polls", body).status_code == 400
    assert SessionDatePoll.query.count() == SessionDateOption.query.count() == 0


def test_poll_accepts_exactly_twenty_distinct_options_and_normalizes_dst(world):
    _, call, session, ids, _ = world
    twenty = [{'local': (future(2) + timedelta(hours=i)).isoformat(timespec='minutes')} for i in range(20)]
    assert call(1, 'POST', f"{ids['A']}/date-polls", poll_body(session('A', None), options=twenty)).status_code == 201
    # 2027-03-28 02:30 does not exist in Europe/Berlin; it is refused before any date-range rule applies.
    gap = call(1, 'POST', f"{ids['A']}/date-polls", poll_body(session('A', None), options=[{'local': '2027-03-28T02:30'}], timezone='Europe/Berlin'))
    assert gap.status_code == 400 and 'Zeitumstellung' in gap.json['error']
    ok = call(1, 'POST', f"{ids['A']}/date-polls", poll_body(session('A', None), options=[{'local': future(10, 19).strftime('%Y-%m-%dT19:00')}],
                                                               timezone='America/New_York'))
    assert ok.status_code == 201
    stored = SessionDateOption.query.order_by(SessionDateOption.id.desc()).first().starts_at
    assert stored.hour in (23, 0)                      # 19:00 in New York is 23:00 (EDT) or 00:00 UTC (EST)


def test_poll_read_scopes_and_named_participants_only_for_managers(world):
    _, call, session, ids, uid = world
    poll = make_poll(call, ids, session('A', None))
    other = make_poll(call, ids, session('B', None), cid='B', actor=4)
    assert vote(call, ids, poll, 0, 'yes', actor=2).status_code == 200
    assert vote(call, ids, poll, 0, 'maybe', actor=5).status_code == 200
    base = f"{ids['A']}/date-polls/{poll['id']}"
    manager = call(3, 'GET', base).json['poll']
    assert manager['can_manage'] and sorted(p['username'] for p in manager['participants']) == ['c06-1', 'c06-2', 'c06-3', 'c06-5']
    by_name = {p['username']: p for p in manager['participants']}
    assert by_name['c06-2']['answers'] == {str(poll['options'][0]['id']): 'yes'} or by_name['c06-2']['answers'] == {poll['options'][0]['id']: 'yes'}
    player = call(2, 'GET', base).get_json()['poll']
    assert 'participants' not in player and not player['can_manage']
    assert (player['options'][0]['yes'], player['options'][0]['maybe'], player['options'][0]['mine']) == (1, 1, 'yes')
    assert player['options'][1]['mine'] is None and player['answered'] == 1 and player['my_complete'] is False
    assert 'c06-5' not in call(2, 'GET', base).get_data(as_text=True)                 # others' identities stay hidden
    for actor in (6, 7, 8, 9, 10, 4):
        assert call(actor, 'GET', base).status_code == 403, actor
        assert call(actor, 'GET', f"{ids['A']}/date-polls").status_code == 403
    assert call(2, 'GET', f"{ids['B']}/date-polls/{poll['id']}").status_code == 404   # poll of another campaign via own campaign
    assert call(4, 'GET', f"{ids['B']}/date-polls/{other['id']}").status_code == 200
    assert call(2, 'GET', f"{ids['A']}/date-polls?status=open").json['polls'][0]['id'] == poll['id']
    assert call(2, 'GET', f"{ids['A']}/date-polls?status=weird").status_code == 400


def test_votes_are_self_only_upserted_scoped_and_survive_reload(world):
    _, call, session, ids, uid = world
    poll = make_poll(call, ids, session('A', None))
    sibling = make_poll(call, ids, session('A', None))
    foreign = make_poll(call, ids, session('B', None), cid='B', actor=4)
    result = call(2, 'PUT', f"{ids['A']}/date-polls/{poll['id']}/options/{poll['options'][0]['id']}/vote", {'value': 'yes', 'user_id': uid[5]})
    assert result.status_code == 200
    assert [(v.user_id, v.value) for v in SessionDateVote.query.all()] == [(uid[2], 'yes')]     # voter is never client supplied
    assert vote(call, ids, poll, 0, 'no').status_code == 200
    db.session.remove()
    assert SessionDateVote.query.count() == 1 and SessionDateVote.query.one().value == 'no'
    assert call(2, 'GET', f"{ids['A']}/date-polls/{poll['id']}").json['poll']['options'][0]['mine'] == 'no'   # reload keeps it
    for value in ('YES', 'true', '', None, 1, ['yes']):
        assert call(2, 'PUT', f"{ids['A']}/date-polls/{poll['id']}/options/{poll['options'][0]['id']}/vote", {'value': value}).status_code == 400
    sibling_option = sibling['options'][0]['id']
    assert call(2, 'PUT', f"{ids['A']}/date-polls/{poll['id']}/options/{sibling_option}/vote", {'value': 'yes'}).status_code == 404
    foreign_option = foreign['options'][0]['id']
    assert call(2, 'PUT', f"{ids['A']}/date-polls/{poll['id']}/options/{foreign_option}/vote", {'value': 'yes'}).status_code == 404
    assert call(2, 'PUT', f"{ids['A']}/date-polls/{foreign['id']}/options/{foreign_option}/vote", {'value': 'yes'}).status_code == 404
    assert call(2, 'PUT', f"{ids['B']}/date-polls/{foreign['id']}/options/{foreign_option}/vote", {'value': 'yes'}).status_code == 200  # own B membership
    assert vote(call, ids, poll, 1, 'maybe', actor=5).status_code == 200                      # observers are active members
    for actor in (6, 7, 8, 9, 10):
        assert vote(call, ids, poll, 0, 'yes', actor=actor).status_code == 403, actor
    CampaignMember.query.filter_by(campaign_id=ids['A'], user_id=uid[2]).update({'status': 'left'}); db.session.commit()
    assert vote(call, ids, poll, 0, 'yes', actor=2).status_code == 403
    assert call(1, 'GET', f"{ids['A']}/date-polls/{poll['id']}").json['poll']['options'][0]['no'] == 0   # left members no longer count
    assert SessionDateVote.query.filter_by(user_id=uid[10]).count() == 0


def test_finalize_cas_sets_schedule_once_and_is_idempotent(world):
    _, call, session, ids, uid = world
    sid = session('A', None, name='Finale')
    poll = make_poll(call, ids, sid)
    chosen, other = poll['options'][0], poll['options'][1]
    url = f"{ids['A']}/date-polls/{poll['id']}/finalize"
    assert call(2, 'POST', url, {'expected_revision': 1, 'option_id': chosen['id']}).status_code == 403
    assert call(5, 'POST', url, {'expected_revision': 1, 'option_id': chosen['id']}).status_code == 403
    assert call(1, 'POST', url, {'expected_revision': 2, 'option_id': chosen['id']}).status_code == 409     # stale revision
    assert call(1, 'POST', url, {'expected_revision': 1, 'option_id': 999999}).status_code == 404
    assert call(1, 'POST', url, {'expected_revision': 1}).status_code == 400
    assert call(1, 'POST', url, {'expected_revision': True, 'option_id': chosen['id']}).status_code == 400
    foreign = make_poll(call, ids, session('B', None), cid='B', actor=4)
    assert call(1, 'POST', url, {'expected_revision': 1, 'option_id': foreign['options'][0]['id']}).status_code == 404
    db.session.remove()
    assert db.session.get(GameSession, sid).scheduled_at is None and SessionDatePoll.query.filter_by(status='open').count() == 2
    done = call(1, 'POST', url, {'expected_revision': 1, 'option_id': chosen['id']})
    assert done.status_code == 200 and done.json['changed'] is True
    assert done.json['poll']['status'] == 'closed' and done.json['poll']['revision'] == 2
    assert done.json['poll']['selected_option_id'] == chosen['id'] and done.json['session']['session_id'] == sid
    db.session.remove()
    row = db.session.get(GameSession, sid)
    assert row.scheduled_at.isoformat(timespec='minutes') == chosen['starts_at'][:16] and row.duration_minutes == 180
    count = GameSession.query.count()
    again = call(1, 'POST', url, {'expected_revision': 1, 'option_id': chosen['id']})          # same retry
    assert again.status_code == 200 and again.json['changed'] is False and again.json['session']['session_id'] == sid
    assert call(3, 'POST', url, {'expected_revision': 1, 'option_id': other['id']}).status_code == 409   # other choice
    assert call(1, 'POST', url, {'expected_revision': 2, 'option_id': chosen['id']}).status_code == 409   # wrong revision
    assert GameSession.query.count() == count
    assert vote(call, ids, poll, 0, 'yes').status_code == 409
    assert call(1, 'POST', f"{ids['A']}/date-polls/{poll['id']}/cancel", {}).status_code == 409
    shown = call(2, 'GET', 'my-session-calendar?scope=rolling30&timezone=UTC').json['entries'] \
        + call(1, 'GET', f"my-session-calendar?scope=month&anchor={chosen['starts_at'][:10]}&timezone=UTC").json['entries']
    assert [e['session_id'] for e in shown if e['session_name'] == 'Finale'] and {e['session_id'] for e in shown if e['session_name'] == 'Finale'} == {sid}
    assert call(1, 'GET', 'my-session-alerts').json['missing_dates'] == []
    # A later poll for the (now dated) session is refused rather than overwriting its schedule.
    assert call(1, 'POST', f"{ids['A']}/date-polls", poll_body(sid)).status_code == 409


def test_finalize_refuses_when_session_changed_underneath(world):
    _, call, session, ids, _ = world
    for change in ({'scheduled_at': future(20)}, {'status': 'in_progress', 'session_state': 'active', 'started_at': utcnow()},
                   {'status': 'cancelled', 'session_state': 'ended'}):
        sid = session('A', None)
        poll = make_poll(call, ids, sid)
        GameSession.query.filter_by(id=sid).update(change); db.session.commit()
        before = db.session.get(GameSession, sid).scheduled_at
        response = call(1, 'POST', f"{ids['A']}/date-polls/{poll['id']}/finalize", {'expected_revision': 1, 'option_id': poll['options'][0]['id']})
        assert response.status_code == 409, change
        db.session.remove()
        assert db.session.get(GameSession, sid).scheduled_at == before
        assert db.session.get(SessionDatePoll, poll['id']).status == 'open'
        assert vote(call, ids, poll, 0, 'yes').status_code == 409


def test_cancel_poll_is_explicit_and_frees_the_session(world):
    _, call, session, ids, _ = world
    sid = session('A', None)
    poll = make_poll(call, ids, sid)
    url = f"{ids['A']}/date-polls/{poll['id']}/cancel"
    assert call(2, 'POST', url, {}).status_code == 403
    assert call(1, 'POST', url, {'expected_revision': 5}).status_code == 409
    assert call(1, 'POST', url, {'expected_revision': 'x'}).status_code == 400
    cancelled = call(1, 'POST', url, {'expected_revision': 1})
    assert cancelled.status_code == 200 and cancelled.json['poll']['status'] == 'cancelled' and cancelled.json['poll']['revision'] == 2
    assert call(3, 'POST', url, {}).status_code == 200                                    # idempotent
    assert call(1, 'POST', f"{ids['A']}/date-polls/{poll['id']}/finalize", {'expected_revision': 2, 'option_id': poll['options'][0]['id']}).status_code == 409
    assert vote(call, ids, poll, 0, 'yes').status_code == 409
    assert call(1, 'POST', f"{ids['A']}/date-polls", poll_body(sid)).status_code == 201   # a new poll needs a new, deliberate request
    assert call(2, 'GET', 'my-session-alerts').json['open_votes'][0]['poll_id'] != poll['id']
    assert db.session.get(GameSession, sid).scheduled_at is None


def test_cancelling_the_appointment_cancels_its_open_poll(world):
    _, call, session, ids, _ = world
    sid = session('A', None)
    poll = make_poll(call, ids, sid)
    assert call(1, 'POST', f"{ids['A']}/session-appointments/{sid}/cancel", {}).status_code == 200
    db.session.remove()
    assert db.session.get(SessionDatePoll, poll['id']).status == 'cancelled'
    assert call(2, 'GET', 'my-session-alerts').json['open_votes'] == []
    assert call(2, 'POST', f"{ids['A']}/session-appointments/{sid}/cancel", {}).status_code == 403


def test_database_allows_only_one_open_poll_per_session(world):
    _, _, session, ids, uid = world
    sid = session('A', None)
    def row(key, status):
        return SessionDatePoll(campaign_id=ids['A'], session_id=sid, created_by=uid[1], request_key=key, input_digest='d',
                               title='t', status=status)
    db.session.add_all([row(str(uuid4()), 'cancelled'), row(str(uuid4()), 'closed'), row(str(uuid4()), 'open')]); db.session.commit()
    db.session.add(row(str(uuid4()), 'open'))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    db.session.add(SessionDatePoll(campaign_id=ids['A'], session_id=sid, created_by=uid[1], request_key=str(uuid4()),
                                   input_digest='d', title='t', status='bogus'))
    with pytest.raises(IntegrityError):
        db.session.commit()
