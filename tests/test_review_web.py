"""Own inventory and deduplicated, non-public print request analytics."""

from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from vtt import create_app
from vtt.extensions import db
from vtt.models import Campaign, CampaignMember, Character, Role, User
from vtt.models.review_web import ReviewPrintRequest
from vtt.utils.time import utcnow


@pytest.fixture
def site():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        role = Role(name='Player'); db.session.add(role); db.session.flush()
        users = [User(username=f'review-user-{i}', email=f'review-{i}@example.test',
                      password_hash='x', role_id=role.id, is_active=True, account_state='active')
                 for i in range(3)]
        users[2].platform_role = 'owner'
        db.session.add_all(users); db.session.flush()
        own = Campaign(name='Own', owner_id=users[0].id)
        other = Campaign(name='Other', owner_id=users[1].id)
        db.session.add_all([own, other]); db.session.flush()
        db.session.add_all([
            CampaignMember(campaign_id=other.id, user_id=users[0].id, campaign_role='PLAYER', status='active'),
            CampaignMember(campaign_id=own.id, user_id=users[1].id, campaign_role='PLAYER', status='pending'),
            Character(user_id=users[0].id, name='My figure'),
            Character(user_id=users[0].id, name='Removed figure', deleted_at=utcnow()),
            Character(user_id=users[1].id, name='Secret figure'),
        ])
        db.session.commit()
        ids = [u.id for u in users]
        tokens = [create_access_token(identity=str(i)) for i in ids]
        client = app.test_client()

        def call(who, path, method='GET', body=None):
            if who is None:
                client.delete_cookie('access_token_cookie')
            else:
                client.set_cookie('access_token_cookie', tokens[who])
            return client.open('/api/review-web/' + path, method=method, json=body)
        yield call, ids
        db.session.remove(); db.drop_all()


def payload(**changes):
    return dict(request_id=str(uuid4()), ruleset='srd-5.2.1-de', document_id='introduction', **changes)


def test_profile_only_counts_own_objects(site):
    call, ids = site
    own = call(0, 'profile?user_id=2')
    assert own.status_code == 200
    assert own.headers['Cache-Control'] == 'private, no-store'
    assert own.json == dict(user_id=ids[0], username='review-user-0', avatar_url=None,
                            characters=1, owned_campaigns=1, memberships=1)
    assert call(1, 'profile').json['memberships'] == 0
    assert 'Secret figure' not in own.get_data(as_text=True)
    assert call(None, 'profile').status_code == 401


def test_unusable_account_cannot_read_or_write(site):
    call, ids = site
    user = db.session.get(User, ids[0]); user.is_suspended = True; db.session.commit()
    assert call(0, 'profile').status_code == 401
    assert call(0, 'print-requests', 'POST', payload()).status_code == 401


def test_print_retry_is_idempotent_and_actor_bound(site):
    call, _ = site
    data = payload()
    assert call(0, 'print-requests', 'POST', data).status_code == 201
    assert call(0, 'print-requests', 'POST', data).json == dict(recorded=True, duplicate=True)
    assert ReviewPrintRequest.query.count() == 1
    assert call(1, 'print-requests', 'POST', data).status_code == 201
    changed = dict(data, document_id='another-chapter')
    assert call(0, 'print-requests', 'POST', changed).status_code == 409
    assert ReviewPrintRequest.query.count() == 2


@pytest.mark.parametrize('change', [
    {'request_id': 'not-a-uuid'}, {'request_id': 12}, {'ruleset': '<script>'},
    {'document_id': 'a' * 161}, {'document_id': ['intro']}, {'ruleset': ''},
    {'document_id': 'intro\nextra'}, {'user_id': 999},
])
def test_print_request_rejects_invalid_or_injected_fields(site, change):
    call, _ = site
    data = payload(); data.update(change)
    assert call(0, 'print-requests', 'POST', data).status_code == 400
    assert ReviewPrintRequest.query.count() == 0


def test_summary_is_internal_aggregate_and_not_physical_prints(site):
    call, _ = site
    for actor in (0, 1):
        assert call(actor, 'print-requests', 'POST', payload()).status_code == 201
    assert call(0, 'print-requests/summary').status_code == 403
    summary = call(2, 'print-requests/summary')
    assert summary.status_code == 200 and summary.json['total'] == 2
    assert summary.json['metric'] == 'confirmed_ui_print_requests'
    assert summary.json['entries'] == [dict(ruleset='srd-5.2.1-de', document_id='introduction', count=2)]
    assert 'username' not in summary.get_data(as_text=True)
