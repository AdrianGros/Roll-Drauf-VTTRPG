"""Contention contracts against an explicitly disposable, network-isolated PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import os
from threading import Barrier
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import create_engine, select, text

from vtt import create_app
from vtt import calendar_notes as notes
from vtt.config import TestingConfig
from vtt.extensions import db
from vtt.models import Campaign, GameSession, Role, User
from vtt.models.calendar_note import CalendarNote, CalendarOneShot

pytestmark = pytest.mark.postgres


@pytest.fixture
def pg_calendar(monkeypatch):
    url = os.getenv('CALENDAR_REVIEW_TEST_DB')
    if not url:
        pytest.skip('Disposable CALENDAR_REVIEW_TEST_DB required')
    parsed = urlparse(url)
    assert (parsed.hostname, parsed.port, parsed.path, parsed.username) == (
        '127.0.0.1', 5432, '/calendar_review_test', 'calendar_review_test')
    schema = 'calendar_review_' + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA {schema}'))
    monkeypatch.setattr(TestingConfig, 'SQLALCHEMY_DATABASE_URI', url)
    monkeypatch.setattr(TestingConfig, 'AUTO_CREATE_SCHEMA', False)
    monkeypatch.setattr(TestingConfig, 'SQLALCHEMY_ENGINE_OPTIONS', {
        'connect_args': {'options': f'-csearch_path={schema}'}, 'pool_size': 8, 'max_overflow': 0}, raising=False)
    app = None
    try:
        app = create_app('testing')
        if 'calendar_notes' not in app.blueprints:
            app.register_blueprint(notes.calendar_notes_bp)
        with app.app_context():
            db.create_all()
            role = Role(name='Calendar PostgreSQL test'); db.session.add(role); db.session.flush()
            user = User(username='calendar-postgres', email='calendar-pg@example.test', password_hash='test',
                        role_id=role.id, profile_tier='dm', active_campaigns_quota=2,
                        account_state='active', is_active=True)
            db.session.add(user); db.session.commit(); uid = user.id
            token = create_access_token(identity=str(uid))
        def api(path, method='GET', data=None):
            with app.test_client() as client:
                client.set_cookie('access_token_cookie', token)
                return client.open('/api/calendar/' + path, method=method, json=data)
        yield app, api, uid
    finally:
        if app:
            with app.app_context():
                db.session.remove(); db.engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        admin.dispose()


def contend(payloads, operation):
    barrier = Barrier(len(payloads))
    def run(payload):
        barrier.wait(timeout=20)
        return operation(payload)
    with ThreadPoolExecutor(max_workers=len(payloads)) as pool:
        return list(pool.map(run, payloads))


def test_note_cas_quota_and_one_shot_retries_under_contention(pg_calendar):
    app, api, uid = pg_calendar
    day = datetime.now().date().isoformat()
    original = dict(request_key=str(uuid4()), date=day, title='Concurrent private note', body='', color='blue', timezone='UTC')
    made = contend([original] * 4, lambda data: api('notes', 'POST', data))
    assert sorted(response.status_code for response in made) == [200, 200, 200, 201]
    assert len({response.json['id'] for response in made}) == 1
    nid = made[0].json['id']
    edits = [{**original, 'request_key': str(uuid4()), 'revision': 1, 'title': f'Winner {i}'} for i in range(2)]
    changed = contend(edits, lambda data: api(f'notes/{nid}', 'PUT', data))
    assert sorted(response.status_code for response in changed) == [200, 409]
    with app.app_context():
        assert db.session.get(CalendarNote, nid).revision == 2
        for i in range(18):
            db.session.add(CalendarNote(user_id=uid, request_key=str(uuid4()), input_digest='x' * 64,
                                       local_date=datetime.now().date(), title=f'Seed {i}', color='red'))
        db.session.commit()
    capped = contend([{**original, 'request_key': str(uuid4())} for _ in range(2)], lambda data: api('notes', 'POST', data))
    assert sorted(response.status_code for response in capped) == [201, 409]

    shot = dict(request_key=str(uuid4()), name='Concurrent One-Shot', timezone='UTC',
                first_local=(datetime.now() + timedelta(days=2)).isoformat(timespec='minutes'), max_players=6, duration_minutes=120)
    made = contend([shot] * 4, lambda data: api('oneshots', 'POST', data))
    assert sorted(response.status_code for response in made) == [200, 200, 200, 201]
    assert len({response.json['campaign_id'] for response in made}) == 1
    final_slot = contend([{**shot, 'request_key': str(uuid4())} for _ in range(2)], lambda data: api('oneshots', 'POST', data))
    assert sorted(response.status_code for response in final_slot) == [201, 403]
    with app.app_context():
        assert Campaign.query.filter_by(owner_id=uid, deleted_at=None).count() == 2
        assert CalendarOneShot.query.filter_by(user_id=uid).count() == 2
        assert GameSession.query.count() == 2


def test_skip_locked_workers_and_cancelled_claim_do_not_duplicate(pg_calendar):
    app, _, uid = pg_calendar
    due = datetime.now() - timedelta(minutes=5)
    with app.app_context():
        for i in range(40):
            db.session.add(CalendarNote(user_id=uid, request_key=str(uuid4()), input_digest='x' * 64,
                local_date=due.date(), title=f'Due {i}', reminder_at=due, reminder_state='pending'))
        db.session.commit()
    def worker(_):
        with app.app_context():
            return notes.process_due(limit=20)
    assert sum(contend(range(4), worker)) == 40
    with app.app_context():
        assert CalendarNote.query.filter_by(reminder_state='ready', revision=2).count() == 40
        assert notes.process_due() == 0
        pending = CalendarNote(user_id=uid, request_key=str(uuid4()), input_digest='x' * 64,
            local_date=due.date(), title='Cancelled while held', reminder_at=due, reminder_state='pending')
        db.session.add(pending); db.session.commit(); nid = pending.id
        # The editor owns this row lock; SKIP LOCKED must leave it untouched.
        row = db.session.execute(select(CalendarNote).where(CalendarNote.id == nid).with_for_update()).scalar_one()
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert pool.submit(worker, None).result(timeout=20) == 0
        row.reminder_at = None; row.reminder_state = 'none'; row.revision += 1
        db.session.commit()
        assert notes.process_due() == 0
        assert db.session.get(CalendarNote, nid).reminder_state == 'none'
