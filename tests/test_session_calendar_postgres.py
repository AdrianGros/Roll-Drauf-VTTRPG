"""Real worker contention against an isolated schema in the disposable database."""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
from urllib.parse import urlparse

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import create_engine, text

from vtt import create_app
from vtt.config import TestingConfig
from vtt.extensions import db
from vtt.models import Campaign, Role, User, GameSession, SessionSeries, SessionOccurrence
from tests.test_session_calendar import payload

pytestmark = pytest.mark.postgres


@pytest.fixture
def pg_calendar(monkeypatch):
    url=os.getenv('CE_TEST_DATABASE_URL')
    if not url:pytest.skip('Disposable CE_TEST_DATABASE_URL required')
    parsed=urlparse(url)
    assert (parsed.hostname,parsed.port,parsed.path)==('127.0.0.1',55432,'/ce_test')
    schema='calendar_test_'+uuid4().hex
    admin=create_engine(url)
    with admin.begin() as conn:conn.execute(text(f'CREATE SCHEMA {schema}'))
    monkeypatch.setattr(TestingConfig,'SQLALCHEMY_DATABASE_URI',url)
    monkeypatch.setattr(TestingConfig,'SQLALCHEMY_ENGINE_OPTIONS',{'connect_args':{'options':f'-csearch_path={schema}'}},raising=False)
    app=None
    try:
        app=create_app('testing')
        with app.app_context():
            role=Role(name='Player');db.session.add(role);db.session.flush()
            user=User(username='calendar-dm',email='calendar@example.test',password_hash='test',role_id=role.id,
                      is_active=True,account_state='active')
            db.session.add(user);db.session.flush()
            campaign=Campaign(name='Concurrent campaign',owner_id=user.id);db.session.add(campaign);db.session.commit()
            cid=campaign.id;token=create_access_token(identity=str(user.id))
        def api(path,method='GET',data=None):
            with app.test_client() as client:
                client.set_cookie('access_token_cookie',token)
                return client.open(f'/api/campaigns/{cid}/{path}',method=method,json=data)
        yield app,api
    finally:
        if app:
            with app.app_context():db.session.remove();db.engine.dispose()
        with admin.begin() as conn:conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        admin.dispose()


def test_concurrent_create_and_calendar_reads_are_unique(pg_calendar):
    app,api=pg_calendar;body=payload();barrier=Barrier(4)
    def save(_):
        barrier.wait(timeout=10)
        result=api('session-series','POST',body)
        return result.status_code,result.json
    with ThreadPoolExecutor(max_workers=4) as workers:results=list(workers.map(save,range(4)))
    assert sorted(r[0] for r in results)==[200,200,200,201]
    assert len({r[1]['series']['id'] for r in results})==1
    anchor=str(int(body['first_local'][:4])+1)+'-12-01'
    with ThreadPoolExecutor(max_workers=4) as workers:
        responses=list(workers.map(lambda _:api('session-calendar?scope=year&anchor='+anchor),range(4)))
    assert all(r.status_code==200 for r in responses)
    assert len({tuple(e['id'] for e in r.json['entries']) for r in responses})==1
    with app.app_context():
        assert SessionSeries.query.count()==1
        assert GameSession.query.count()==SessionOccurrence.query.count()
        assert len({s.scheduled_at for s in GameSession.query.all()})==GameSession.query.count()
    series_id=results[0][1]['series']['id']
    stopped=api(f'session-series/{series_id}/stop','POST',{})
    assert stopped.status_code==200
    assert api('session-calendar?scope=year&anchor='+anchor).status_code==200
    with app.app_context():assert GameSession.query.filter_by(status='scheduled').count()==0
