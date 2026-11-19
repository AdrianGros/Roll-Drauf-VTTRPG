"""W03 behavioral contracts; isolated testing DB, never production."""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token, get_csrf_token
from sqlalchemy.exc import IntegrityError

from vtt import create_app
from vtt import calendar_notes as notes
from vtt.campaigns import session_calendar as calendar
from vtt.extensions import db
from vtt.models import Campaign, CampaignMember, GameSession, Role, User
from vtt.models.calendar_note import CalendarNote, CalendarOneShot

NOW = datetime(2026, 11, 18, 12)


@pytest.fixture
def world(monkeypatch):
    from vtt.config import TestingConfig
    monkeypatch.setattr(TestingConfig, 'SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:')
    # The API fixture creates its schema explicitly; content seeding is unrelated here.
    monkeypatch.setattr(TestingConfig, 'AUTO_CREATE_SCHEMA', False)
    monkeypatch.setattr(notes, 'utcnow', lambda: NOW)
    monkeypatch.setattr(calendar, 'utcnow', lambda: NOW)
    app = create_app('testing')
    if 'calendar_notes' not in app.blueprints:
        app.register_blueprint(notes.calendar_notes_bp)
    with app.app_context():
        db.create_all()
        role = Role(name='calendar-review-player'); db.session.add(role); db.session.flush()
        users = [User(username=f'calendar-review-{i}', email=f'calendar-{i}@example.test', password_hash='x',
                      role_id=role.id, profile_tier='dm' if i < 2 else 'player', active_campaigns_quota=3,
                      account_state='active', is_active=True) for i in range(3)]
        db.session.add_all(users); db.session.flush()
        campaign = Campaign(name='Calendar group', owner_id=users[0].id, status='active')
        db.session.add(campaign); db.session.flush()
        db.session.add(CampaignMember(campaign_id=campaign.id, user_id=users[2].id, campaign_role='PLAYER', status='active'))
        db.session.commit()
        ids = [user.id for user in users]; cid = campaign.id
        tokens = [create_access_token(identity=str(uid)) for uid in ids]
        client = app.test_client()

        def call(who, method, path, payload=None, headers=None):
            client.set_cookie('access_token_cookie', tokens[who])
            return client.open('/api/calendar/' + path, method=method, json=payload, headers=headers or {})

        yield app, call, ids, cid, client, tokens
        db.session.remove(); db.drop_all()


def payload(**changes):
    result = dict(request_key=str(uuid4()), date='2026-11-19', title='Prepare dice', body='Private words',
                  color='purple', timezone='Europe/Berlin', reminder_local='')
    result.update(changes)
    return result


def one_shot(**changes):
    result = dict(request_key=str(uuid4()), name='A single adventure', first_local='2026-12-01T19:00',
                  timezone='Europe/Berlin', duration_minutes=180, max_players=5)
    result.update(changes)
    return result


def test_private_notes_no_other_user_or_id_write(world):
    _, call, _, _, _, _ = world
    made = call(0, 'POST', 'notes', payload())
    assert made.status_code == 201
    nid = made.json['id']
    assert call(1, 'GET', 'notes?start=2026-11-01&end=2026-12-01').json['notes'] == []
    assert len(call(0, 'GET', 'notes?start=2026-11-01&end=2026-12-01').json['notes']) == 1
    assert call(1, 'PUT', f'notes/{nid}', payload(revision=1)).status_code == 404
    assert call(1, 'DELETE', f'notes/{nid}', {'revision': 1}).status_code == 404
    assert call(1, 'POST', f'notes/{nid}/dismiss', {'revision': 1}).status_code == 404
    data = payload(); data['user_id'] = 2
    assert call(0, 'POST', 'notes', data).status_code == 400


def test_note_retry_stale_update_and_delete_tombstone(world):
    _, call, _, _, _, _ = world
    original = payload(); made = call(0, 'POST', 'notes', original)
    assert call(0, 'POST', 'notes', original).json['id'] == made.json['id']
    changed = {**original, 'title': 'Different'}
    assert call(0, 'POST', 'notes', changed).status_code == 409
    nid = made.json['id']
    edit = {**payload(), 'revision': 1, 'title': 'Better title'}
    result = call(0, 'PUT', f'notes/{nid}', edit)
    assert result.status_code == 200 and result.json['revision'] == 2
    assert call(0, 'PUT', f'notes/{nid}', edit).json['revision'] == 2
    assert call(0, 'PUT', f'notes/{nid}', {**edit, 'title': 'Retry changed'}).status_code == 409
    assert call(0, 'PUT', f'notes/{nid}', {**edit, 'request_key': str(uuid4())}).status_code == 409
    assert call(0, 'DELETE', f'notes/{nid}', {'revision': 1}).status_code == 409
    assert call(0, 'DELETE', f'notes/{nid}', {'revision': 2}).status_code == 200
    assert call(0, 'DELETE', f'notes/{nid}', {'revision': 2}).status_code == 200
    assert call(0, 'POST', 'notes', original).status_code == 409
    assert call(0, 'GET', 'notes?start=2026-11-01&end=2026-12-01').json['notes'] == []


@pytest.mark.parametrize('change', [dict(title=''), dict(title='x' * 81), dict(body='x' * 2001),
    dict(color='notacolor'), dict(date='2026-99-99'), dict(timezone='Unknown/Nope'), dict(request_key='nope'),
    dict(reminder_local='2026-11-01T10:00'), dict(reminder_local='2028-11-01T10:00'),
    dict(reminder_local='2027-03-28T02:30'), dict(reminder_local='2027-10-31T02:30'),
    dict(reminder_local='2027-10-31T02:30', fold=True), dict(reminder_local=[]),
    dict(reminder_local='2026-11-19 10:00')])
def test_note_validation(world, change):
    _, call, _, _, _, _ = world
    assert call(0, 'POST', 'notes', {**payload(), **change}).status_code == 400


def test_dst_explicit_fold_and_date_identity(world):
    _, call, _, _, _, _ = world
    for fold, expected in [(0, '2027-10-31T00:30:00Z'), (1, '2027-10-31T01:30:00Z')]:
        result = call(0, 'POST', 'notes', {**payload(), 'date': '2027-10-31', 'reminder_local': '2027-10-31T02:30', 'fold': fold})
        assert result.status_code == 201
        assert result.json['reminder_at'] == expected and result.json['date'] == '2027-10-31'


def test_reminder_worker_cancel_rearm_and_dismiss(world):
    _, call, _, _, _, _ = world
    first = call(0, 'POST', 'notes', {**payload(), 'reminder_local': '2026-11-19T10:00'}).json
    second = call(0, 'POST', 'notes', {**payload(), 'reminder_local': '2026-11-19T11:00'}).json
    assert call(0, 'DELETE', f"notes/{second['id']}", {'revision': 1}).status_code == 200
    assert notes.process_due(now=datetime(2026, 11, 19, 10)) == 1
    assert notes.process_due(now=datetime(2026, 11, 19, 10)) == 0
    ready = call(0, 'GET', 'reminders').json['notes']
    assert [n['id'] for n in ready] == [first['id']] and ready[0]['revision'] == 2
    assert call(1, 'GET', 'reminders').json['notes'] == []
    assert call(0, 'PUT', f"notes/{first['id']}", {**payload(), 'revision': 1}).status_code == 409
    assert call(0, 'POST', f"notes/{first['id']}/dismiss", {'revision': 1}).status_code == 409
    assert call(0, 'POST', f"notes/{first['id']}/dismiss", {'revision': 2}).json['reminder_state'] == 'dismissed'
    assert call(0, 'GET', 'reminders').json['notes'] == []
    rearm = call(0, 'PUT', f"notes/{first['id']}", {**payload(), 'revision': 3, 'reminder_local': '2026-11-20T10:00'})
    assert rearm.status_code == 200 and rearm.json['reminder_state'] == 'pending'
    assert notes.process_due(now=datetime(2026, 11, 19, 11)) == 0
    assert notes.process_due(now=datetime(2026, 11, 20, 11)) == 1


def test_bounded_query_limits_and_day_cap(world):
    _, call, _, _, _, _ = world
    assert call(0, 'GET', 'notes?start=2026-11-01&end=2027-02-01').status_code == 400
    assert call(0, 'GET', 'notes?start=2026-11-01&end=2026-12-01&cursor=' + '9' * 50).status_code == 400
    for i in range(20):
        assert call(0, 'POST', 'notes', payload()).status_code == 201
    assert call(0, 'POST', 'notes', payload()).status_code == 409


def test_read_pagination_is_complete_and_does_not_process_due(world):
    _, call, ids, _, _, _ = world
    for i in range(205):
        db.session.add(CalendarNote(user_id=ids[0], request_key=str(uuid4()), input_digest='x' * 64,
             local_date=NOW.date(), title=f'Note {i}', body='', color='red', timezone='UTC',
             reminder_at=NOW - timedelta(seconds=1), reminder_state='pending'))
    db.session.commit()
    first = call(0, 'GET', 'notes?start=2026-11-01&end=2026-12-01').json
    assert len(first['notes']) == 200 and not first['complete']
    second = call(0, 'GET', f"notes?start=2026-11-01&end=2026-12-01&cursor={first['next_cursor']}").json
    assert len(second['notes']) == 5 and second['complete']
    assert call(0, 'GET', 'reminders').json['notes'] == []
    assert notes.process_due(limit=100) == 100
    assert notes.process_due(limit=100) == 100
    assert notes.process_due(limit=100) == 5
    assert notes.process_due(limit=100) == 0


def test_total_note_cap_across_days_can_be_reclaimed_after_delete(world):
    _, call, ids, _, _, _ = world
    db.session.add_all([CalendarNote(user_id=ids[0], request_key=str(uuid4()), input_digest='x' * 64,
        local_date=NOW.date() - timedelta(days=i // 20), title=f'Seed {i}', color='green') for i in range(2000)])
    db.session.commit()
    assert call(0, 'POST', 'notes', payload()).status_code == 409
    first = CalendarNote.query.filter_by(user_id=ids[0], deleted_at=None).first()
    assert call(0, 'DELETE', f'notes/{first.id}', {'revision': 1}).status_code == 200
    assert call(0, 'POST', 'notes', payload()).status_code == 201


def test_one_shot_creates_real_round_and_exact_retry(world):
    _, call, ids, _, _, _ = world
    data = one_shot(); first = call(0, 'POST', 'oneshots', data)
    assert first.status_code == 201
    second = call(0, 'POST', 'oneshots', data)
    assert second.status_code == 200 and second.json['id'] == first.json['id']
    assert call(0, 'POST', 'oneshots', {**data, 'name': 'Changed retry'}).status_code == 409
    assert CalendarOneShot.query.count() == 1
    assert GameSession.query.filter_by(campaign_id=first.json['campaign_id']).count() == 1
    campaign = db.session.get(Campaign, first.json['campaign_id'])
    assert campaign.owner_id == ids[0] and campaign.is_discoverable is False
    owner_member = CampaignMember.query.filter_by(campaign_id=campaign.id, user_id=ids[0]).one()
    assert owner_member.status == 'active' and owner_member.campaign_role == 'DM'
    assert call(1, 'GET', 'oneshots').json['oneshots'] == []
    db.session.add(CampaignMember(campaign_id=campaign.id, user_id=ids[2], campaign_role='PLAYER', status='active')); db.session.commit()
    assert len(call(2, 'GET', 'oneshots').json['oneshots']) == 1
    assert call(2, 'GET', 'oneshots').json['oneshots'][0]['can_manage'] is False


def test_one_shot_quota_tier_and_atomic_failure(world):
    _, call, ids, _, _, _ = world
    assert call(2, 'POST', 'oneshots', one_shot()).status_code == 403
    assert call(0, 'POST', 'oneshots', one_shot()).status_code == 201
    assert call(0, 'POST', 'oneshots', one_shot()).status_code == 201
    before = Campaign.query.count()
    assert call(0, 'POST', 'oneshots', one_shot()).status_code == 403
    assert Campaign.query.count() == before and CalendarOneShot.query.count() == 2
    user = db.session.get(User, ids[1]); user.active_campaigns_quota = 0; db.session.commit()
    assert call(1, 'POST', 'oneshots', one_shot()).status_code == 403


def test_one_shot_late_database_failure_rolls_back_round_and_membership(world, monkeypatch):
    _, call, _, _, _, _ = world
    before = (Campaign.query.count(), CampaignMember.query.count(), GameSession.query.count())
    def fail_commit():
        raise IntegrityError('injected commit failure', {}, RuntimeError('isolated test failure'))
    with monkeypatch.context() as patch:
        patch.setattr(db.session, 'commit', fail_commit)
        assert call(1, 'POST', 'oneshots', one_shot()).status_code == 409
    assert (Campaign.query.count(), CampaignMember.query.count(), GameSession.query.count()) == before
    assert CalendarOneShot.query.count() == 0


def test_session_planning_uses_existing_series_and_retries(world):
    _, call, _, cid, _, _ = world
    data = {**one_shot(), 'campaign_id': cid}; data.pop('max_players')
    assert call(2, 'POST', 'sessions', data).status_code == 403
    created = call(0, 'POST', 'sessions', data)
    assert created.status_code == 201
    retry = call(0, 'POST', 'sessions', data)
    assert retry.status_code == 200 and retry.json['session_id'] == created.json['session_id']
    assert GameSession.query.filter_by(campaign_id=cid).count() == 1


def test_carried_player_cannot_create_privileged_scopes(world):
    _, call, _, cid, client, tokens = world
    session = GameSession(campaign_id=cid, name='Context session', status='in_progress')
    db.session.add(session); db.session.commit()
    client.set_cookie('access_token_cookie', tokens[0])
    tab = 'calendar-review-player-tab-123456'
    entered = client.post(f'/api/play/campaigns/{cid}/sessions/{session.id}/contexts', json={'mode': 'player', 'tab': tab})
    assert entered.status_code == 201, entered.json
    headers = {'X-VTT-Context': entered.json['token'], 'X-VTT-Tab': tab}
    assert call(0, 'POST', 'oneshots', one_shot(), headers).status_code == 403
    assert call(0, 'GET', 'oneshots', headers=headers).json['can_create'] is False
    assert call(0, 'POST', 'sessions', {**one_shot(), 'campaign_id': cid}, headers).status_code == 403
    assert call(0, 'POST', 'notes', payload(), headers).status_code == 201
    forged = {**headers, 'X-VTT-Context': 'x' * 43}
    assert call(0, 'POST', 'notes', payload(), forged).status_code == 403


def test_note_writes_keep_cookie_csrf_enforcement(world):
    app, call, ids, _, client, tokens = world
    app.config['JWT_COOKIE_CSRF_PROTECT'] = True
    tokens[0] = create_access_token(identity=str(ids[0]))
    assert call(0, 'POST', 'notes', payload()).status_code == 401
    csrf = get_csrf_token(tokens[0])
    client.set_cookie('csrf_access_token', csrf)
    assert call(0, 'POST', 'notes', payload(), {'X-CSRF-TOKEN': csrf}).status_code == 201
