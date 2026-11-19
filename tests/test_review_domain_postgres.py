"""Actual row-lock contention in the existing disposable-schema test fixture."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from tests.test_session_calendar_postgres import pg_calendar  # noqa: F401
from tests.test_review_domain import register
from vtt.extensions import db
from vtt.models import Campaign, User
from vtt.models.review_domain import AtlasCampaignLink, ReviewThread, ReviewThreadMessage

pytestmark = pytest.mark.postgres


@pytest.fixture
def pg_domain(pg_calendar, tmp_path):
    app, _ = pg_calendar
    register(app)
    app.config.update(LOCAL_STORAGE_PATH=str(tmp_path / 'storage'), STORAGE_PROVIDER='local')
    with app.app_context():
        campaign = Campaign.query.one(); cid = campaign.id
        user = db.session.get(User, campaign.owner_id); user.storage_quota_gb = 1
        db.session.commit(); auth = create_access_token(identity=str(user.id))

    def api(path, method='GET', data=None):
        with app.test_client() as client:
            client.set_cookie('access_token_cookie', auth)
            return client.open('/api/review-domain' + path if not path.startswith('/api/') else path,
                               method=method, json=data)
    return app, api, cid


def together(count, operation):
    gate = Barrier(count)
    def run(index):
        gate.wait(timeout=20)
        response = operation(index)
        return response.status_code, response.json
    with ThreadPoolExecutor(max_workers=count) as pool:
        return list(pool.map(run, range(count)))


def test_concurrent_thread_create_messages_and_revision_cas(pg_domain):
    app, api, cid = pg_domain
    payload = dict(kind='campaign', parent_id=cid, title='One thread', request_id=str(uuid4()))
    results = together(4, lambda _: api('/threads', 'POST', payload))
    assert sorted(status for status, _ in results) == [200, 200, 200, 201], results
    ids = {data['thread']['id'] for _, data in results}; assert len(ids) == 1
    tid = ids.pop()
    message = dict(content='One message', request_id=str(uuid4()))
    results = together(4, lambda _: api(f'/threads/{tid}/messages', 'POST', message))
    assert sorted(status for status, _ in results) == [200, 200, 200, 201], results
    assert len({data['message']['id'] for _, data in results}) == 1
    results = together(2, lambda index: api(f'/threads/{tid}', 'PUT',
                       dict(revision=1, title=f'Concurrent title {index}', closed=False)))
    assert sorted(status for status, _ in results) == [200, 409], results
    with app.app_context():
        assert ReviewThread.query.count() == ReviewThreadMessage.query.count() == 1


def test_concurrent_world_link_retries_and_competing_unlink(pg_domain):
    app, api, cid = pg_domain
    response = api('/api/atlas/worlds', 'POST', dict(title='Concurrent world'))
    assert response.status_code == 201, response.json
    world = response.json; path = f'/worlds/{world["id"]}/campaigns'
    payload = dict(campaign_id=cid, world_revision=world['revision'], request_id=str(uuid4()))
    results = together(4, lambda _: api(path, 'POST', payload))
    assert sorted(status for status, _ in results) == [200, 200, 200, 201], results
    assert len({data['world_revision'] for _, data in results}) == 1
    revision = results[0][1]['world_revision']
    results = together(2, lambda _: api(path + '/' + str(cid), 'DELETE', dict(world_revision=revision, revision=1)))
    assert sorted(status for status, _ in results) == [200, 404], results
    with app.app_context():
        assert AtlasCampaignLink.query.count() == 0
