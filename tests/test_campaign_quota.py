"""FV15: campaign-quota requests and explicit owner/admin review."""

import os
import threading
from datetime import timedelta

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError

from vtt import create_app
from vtt.campaign_quota import INT_MAX
from vtt.config import TestingConfig
from vtt.extensions import db
from vtt.models import AuditLog, Campaign, Role, User
from vtt.models.campaign_quota_request import CampaignQuotaRequest
from vtt.utils.time import utcnow

# name: (profile_tier, platform_role, active_campaigns_quota)
ACCOUNTS = {
    'dm': ('dm', None, 3),
    'dm2': ('dm', None, 2),
    'owner': ('player', 'owner', None),
    'admin': ('player', 'admin', 1),
    'player': ('player', None, 3),
    'headmaster': ('headmaster', None, None),
    'moderator': ('player', 'moderator', 3),
    'zero': ('dm', None, 0),
}


def _seed():
    role = Role.query.filter_by(name='Player').first() or Role(name='Player')
    db.session.add(role); db.session.flush()
    users = {}
    for name, (tier, platform, quota) in ACCOUNTS.items():
        user = User(username=f'cq-{name}', email=f'cq-{name}@example.test', password_hash='x',
                    role_id=role.id, is_active=True, account_state='active',
                    profile_tier=tier, platform_role=platform, active_campaigns_quota=quota)
        db.session.add(user); users[name] = user
    db.session.flush()
    # dm2 has exhausted its capacity: requests must still be possible.
    db.session.add_all([Campaign(name=f'Full {i}', owner_id=users['dm2'].id, status='active') for i in range(2)])
    db.session.commit()
    return {name: user.id for name, user in users.items()}


def _caller(app, ids):
    client = app.test_client()
    tokens = {name: create_access_token(identity=str(i)) for name, i in ids.items()}

    def call(who, path, method='GET', body=None, account='self', raw=None):
        if who is None:
            client.delete_cookie('access_token_cookie')
        else:
            client.set_cookie('access_token_cookie', tokens[who])
        headers = {}
        if account == 'self' and who is not None:
            headers['X-Quota-Account'] = str(ids[who])
        elif account not in ('self', None):
            headers['X-Quota-Account'] = str(account)
        url = path if path.startswith('/') else '/api/campaign-quota/' + path
        if raw is not None:
            return client.open(url, method=method, data=raw, content_type='application/json', headers=headers)
        return client.open(url, method=method, json=body, headers=headers)
    return call


@pytest.fixture
def site():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        ids = _seed()
        yield _caller(app, ids), ids
        db.session.remove(); db.drop_all()


def quota(user_id):
    db.session.expire_all()
    return db.session.get(User, user_id).active_campaigns_quota


def submit(call, who='dm', desired=5, reason='Neue Runde am Donnerstag'):
    return call(who, 'requests', 'POST', dict(desired_total=desired, reason=reason))


def decide(call, request_id, who='owner', **body):
    return call(who, f'review-requests/{request_id}/decision', 'POST', body)


# ----- own state and authentication -----

def test_own_state_is_truthful_private_and_account_bound(site):
    call, ids = site
    response = call('dm2', 'requests')
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'private, no-store'
    data = response.json
    assert data['accountId'] == ids['dm2']
    assert data['quota'] == dict(current=2, assigned=True, active_count=2)
    assert data['eligible'] is True and data['can_review'] is False
    assert data['limits']['per_24h'] == 5 and data['limits']['max_total'] == INT_MAX
    headmaster = call('headmaster', 'requests').json
    # NULL keeps its existing meaning: unassigned, not unlimited, and not requestable.
    assert headmaster['quota'] == dict(current=None, assigned=False, active_count=0)
    assert headmaster['eligible'] is False and headmaster['ineligible_reason'] == 'quota_unassigned'
    assert call('owner', 'requests').json['can_review'] is True
    assert call('admin', 'requests').json['can_review'] is True
    assert call('moderator', 'requests').json['can_review'] is False


def test_own_history_never_contains_other_accounts(site):
    call, ids = site
    assert submit(call, 'dm', reason='geheim-dm').status_code == 201
    assert submit(call, 'dm2', desired=4, reason='geheim-dm2').status_code == 201
    body = call('dm', 'requests').get_data(as_text=True)
    assert 'geheim-dm' in body and 'geheim-dm2' not in body
    assert 'example.test' not in body


@pytest.mark.parametrize('path,method', [
    ('requests', 'GET'), ('requests', 'POST'), ('requests/1/cancel', 'POST'),
    ('review-requests', 'GET'), ('review-requests/1/decision', 'POST'),
])
def test_anonymous_is_rejected(site, path, method):
    call, _ = site
    response = call(None, path, method, {} if method == 'POST' else None)
    assert response.status_code == 401
    assert CampaignQuotaRequest.query.count() == 0


@pytest.mark.parametrize('change', [
    dict(is_suspended=True), dict(account_state='deactivated'), dict(is_active=False),
    dict(account_state='marked_for_deletion'),
])
def test_unusable_accounts_cannot_read_or_mutate(site, change):
    call, ids = site
    for who in ('dm', 'owner'):
        user = db.session.get(User, ids[who])
        for key, value in change.items():
            setattr(user, key, value)
    db.session.commit()
    assert call('dm', 'requests').status_code == 401
    assert submit(call).status_code == 401
    assert call('owner', 'review-requests').status_code == 401
    assert CampaignQuotaRequest.query.count() == 0


def test_own_profile_exposes_only_own_user_id(site):
    call, ids = site
    client_profile = call('dm', '/api/review-web/profile')
    assert client_profile.status_code == 200
    assert client_profile.json['user_id'] == ids['dm']


# ----- submission -----

@pytest.mark.parametrize('who,code', [
    ('player', 'creator_role_required'), ('moderator', 'creator_role_required'),
    ('headmaster', 'quota_unassigned'), ('zero', 'quota_not_positive'),
])
def test_ineligible_accounts_cannot_request(site, who, code):
    call, ids = site
    response = submit(call, who, desired=10)
    assert response.status_code == 403 and response.json['error'] == code
    assert CampaignQuotaRequest.query.count() == 0
    assert quota(ids[who]) == ACCOUNTS[who][2]


@pytest.mark.parametrize('who,desired', [('dm', 4), ('dm2', 3), ('admin', 2)])
def test_eligible_request_including_exhausted_capacity_never_changes_quota(site, who, desired):
    call, ids = site
    before = quota(ids[who])
    response = submit(call, who, desired=desired)
    assert response.status_code == 201
    assert response.json['quota_changed'] is False
    assert response.json['request']['status'] == 'pending'
    assert response.json['request']['submitted_quota'] == before
    assert quota(ids[who]) == before
    row = CampaignQuotaRequest.query.one()
    assert row.pending_key == ids[who] and row.requester_id == ids[who]
    audit = AuditLog.query.filter_by(action='campaign_quota_requested').one()
    assert audit.user_id == ids[who] and audit.performed_by_id == ids[who]
    assert audit.details['old_quota'] == audit.details['new_quota'] == before
    assert 'email' not in str(audit.details)


@pytest.mark.parametrize('body', [
    dict(desired_total=True, reason='x'), dict(desired_total='5', reason='x'),
    dict(desired_total=5.0, reason='x'), dict(desired_total=0, reason='x'),
    dict(desired_total=-4, reason='x'), dict(desired_total=INT_MAX + 1, reason='x'),
    dict(desired_total=None, reason='x'), dict(desired_total=5),
    dict(desired_total=5, reason=''), dict(desired_total=5, reason='   '),
    dict(desired_total=5, reason='x' * 501), dict(desired_total=5, reason=7),
    dict(desired_total=5, reason='bad\x00byte'), dict(desired_total=5, reason='bell\x07'),
    dict(desired_total=5, reason='x', user_id=2), dict(desired_total=5, reason='x', status='approved'),
    dict(desired_total=3, reason='equal to current'), dict(desired_total=2, reason='below current'),
])
def test_submission_payload_is_strict(site, body):
    call, ids = site
    response = call('dm', 'requests', 'POST', body)
    assert response.status_code == 400
    assert CampaignQuotaRequest.query.count() == 0 and quota(ids['dm']) == 3


@pytest.mark.parametrize('raw', ['[]', '"x"', '5', 'not json', ''])
def test_submission_rejects_non_object_bodies(site, raw):
    call, _ = site
    assert call('dm', 'requests', 'POST', raw=raw).status_code == 400
    assert CampaignQuotaRequest.query.count() == 0


def test_maximum_integer_total_is_accepted(site):
    call, _ = site
    assert submit(call, desired=INT_MAX).status_code == 201


def test_authored_reason_stays_literal(site):
    call, _ = site
    text = '<img src=x onerror=alert(1)> {total} &amp; "Zitat"\nZeile 2'
    assert submit(call, reason=text).status_code == 201
    assert call('dm', 'requests').json['requests'][0]['reason'] == text


@pytest.mark.parametrize('account', [None, 'other', '', '0', '01', 'abc'])
def test_mutation_requires_matching_account_header(site, account):
    call, ids = site
    header = ids['dm2'] if account == 'other' else account
    response = call('dm', 'requests', 'POST', dict(desired_total=5, reason='x'), account=header)
    assert response.status_code == 403 and response.json['error'] == 'account_mismatch'
    assert CampaignQuotaRequest.query.count() == 0


def test_one_pending_request_per_account(site):
    call, ids = site
    first = submit(call)
    assert first.status_code == 201
    duplicate = submit(call, desired=6)
    assert duplicate.status_code == 409 and duplicate.json['error'] == 'pending_request_exists'
    assert duplicate.json['request_id'] == first.json['request']['id']
    assert CampaignQuotaRequest.query.count() == 1


def test_database_enforces_single_pending_and_key_relationship(site):
    _, ids = site
    now = utcnow()
    db.session.add(CampaignQuotaRequest(requester_id=ids['dm'], current_quota=3, desired_total=4,
                                        reason='a', status='pending', pending_key=ids['dm'], created_at=now))
    db.session.commit()
    db.session.add(CampaignQuotaRequest(requester_id=ids['dm'], current_quota=3, desired_total=5,
                                        reason='b', status='pending', pending_key=ids['dm'], created_at=now))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    for bad in (dict(status='pending', pending_key=None), dict(status='pending', pending_key=ids['dm']),
                dict(status='cancelled', pending_key=ids['dm2']), dict(status='done', pending_key=None),
                dict(status='rejected', pending_key=None, approved_total=9)):
        db.session.add(CampaignQuotaRequest(requester_id=ids['dm2'], current_quota=2, desired_total=4,
                                            reason='c', created_at=now, **bad))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_rolling_daily_limit_counts_cancelled_history(site):
    call, ids = site
    for _ in range(5):
        created = submit(call)
        assert created.status_code == 201
        assert call('dm', f"requests/{created.json['request']['id']}/cancel", 'POST', {}).status_code == 200
    limited = submit(call)
    assert limited.status_code == 429 and limited.json['error'] == 'request_rate_limited'
    assert CampaignQuotaRequest.query.count() == 5
    oldest = CampaignQuotaRequest.query.order_by(CampaignQuotaRequest.id).first()
    oldest.created_at = utcnow() - timedelta(hours=24, minutes=1)
    db.session.commit()
    assert submit(call).status_code == 201
    assert quota(ids['dm']) == 3


# ----- cancellation -----

def test_cancel_is_own_only_and_never_changes_quota(site):
    call, ids = site
    request_id = submit(call).json['request']['id']
    other = call('dm2', f'requests/{request_id}/cancel', 'POST', {})
    unknown = call('dm2', 'requests/999999/cancel', 'POST', {})
    assert other.status_code == unknown.status_code == 404
    assert other.json == unknown.json
    response = call('dm', f'requests/{request_id}/cancel', 'POST', {})
    assert response.status_code == 200 and response.json['request']['status'] == 'cancelled'
    assert response.json['quota_changed'] is False
    repeat = call('dm', f'requests/{request_id}/cancel', 'POST', {})
    assert repeat.status_code == 409 and repeat.json['quota_changed'] is False
    row = db.session.get(CampaignQuotaRequest, request_id)
    db.session.refresh(row)
    assert row.status == 'cancelled' and row.pending_key is None
    assert quota(ids['dm']) == 3
    assert AuditLog.query.filter_by(action='campaign_quota_request_cancelled').count() == 1
    # A new request is possible once nothing is pending.
    assert submit(call).status_code == 201


def test_cancel_requires_header_and_empty_body(site):
    call, _ = site
    request_id = submit(call).json['request']['id']
    assert call('dm', f'requests/{request_id}/cancel', 'POST', {}, account=None).status_code == 403
    assert call('dm', f'requests/{request_id}/cancel', 'POST', {'status': 'approved'}).status_code == 400
    assert db.session.get(CampaignQuotaRequest, request_id).status == 'pending'


# ----- review list -----

@pytest.mark.parametrize('who', ['dm', 'player', 'moderator', 'headmaster'])
def test_review_list_is_exact_owner_admin_only(site, who):
    call, _ = site
    submit(call)
    assert call(who, 'review-requests').status_code == 403


def test_review_list_is_minimal_and_live(site):
    call, ids = site
    submit(call, 'dm2', desired=6, reason='Volle Kampagnen')
    for who in ('owner', 'admin'):
        response = call(who, 'review-requests')
        assert response.status_code == 200
        assert response.headers['Cache-Control'] == 'private, no-store'
        assert response.json['accountId'] == ids[who] and response.json['view'] == 'pending'
        entry = response.json['entries'][0]
        assert entry['requester'] == dict(id=ids['dm2'], username='cq-dm2')
        assert entry['live'] == dict(current=2, assigned=True, active_count=2)
        assert entry['desired_total'] == 6 and entry['submitted_quota'] == 2
        assert 'example.test' not in response.get_data(as_text=True)
        assert 'Full 0' not in response.get_data(as_text=True)
    assert call('owner', 'review-requests?view=closed').json['entries'] == []
    assert call('owner', 'review-requests?view=all').status_code == 400
    assert call('owner', 'review-requests?user_id=1').status_code == 400


def test_review_list_is_bounded(site):
    call, ids = site
    now = utcnow()
    db.session.add_all([CampaignQuotaRequest(
        requester_id=ids['dm'], current_quota=3, desired_total=4, reason=f'r{i}', status='rejected',
        created_at=now - timedelta(days=2), decided_at=now - timedelta(minutes=i),
    ) for i in range(55)])
    db.session.commit()
    closed = call('owner', 'review-requests?view=closed').json
    assert len(closed['entries']) == 50 and closed['complete'] is False
    assert closed['entries'][0]['reason'] == 'r0'


# ----- review decisions -----

def test_approval_raises_quota_once_with_audit(site):
    call, ids = site
    request_id = submit(call, desired=6).json['request']['id']
    response = decide(call, request_id, decision='approve', expected_current_quota=3,
                      approved_total=5, reviewer_note='<b>nur 5</b>')
    assert response.status_code == 200
    assert response.json['status'] == 'approved' and response.json['approved_total'] == 5
    assert response.json['quota_changed'] is True and response.json['live']['current'] == 5
    assert quota(ids['dm']) == 5
    row = db.session.get(CampaignQuotaRequest, request_id)
    db.session.refresh(row)
    assert row.pending_key is None and row.reviewer_id == ids['owner']
    assert row.reviewer_note == '<b>nur 5</b>' and row.decided_at is not None
    audit = AuditLog.query.filter_by(action='campaign_quota_request_approved').one()
    assert audit.user_id == ids['dm'] and audit.performed_by_id == ids['owner']
    assert audit.details == dict(request_id=request_id, old_quota=3, new_quota=5, desired_total=6)
    # Role, tier and storage are untouched.
    user = db.session.get(User, ids['dm'])
    assert (user.profile_tier, user.platform_role, user.storage_quota_gb) == ('dm', None, None)
    # Double review: the second attempt conflicts and changes nothing.
    again = decide(call, request_id, 'admin', decision='approve', expected_current_quota=3, approved_total=9)
    assert again.status_code == 409 and again.json['error'] == 'request_not_pending'
    assert again.json['mutated'] is False
    assert quota(ids['dm']) == 5
    assert AuditLog.query.filter_by(action='campaign_quota_request_approved').count() == 1
    assert call('dm', 'requests').json['requests'][0]['reviewer_note'] == '<b>nur 5</b>'


def test_rejection_never_changes_quota(site):
    call, ids = site
    request_id = submit(call).json['request']['id']
    response = decide(call, request_id, 'admin', decision='reject', expected_current_quota=3)
    assert response.status_code == 200 and response.json['status'] == 'rejected'
    assert response.json['quota_changed'] is False and response.json['approved_total'] is None
    assert quota(ids['dm']) == 3
    assert decide(call, request_id, decision='reject', expected_current_quota=3).status_code == 409


def test_stale_expected_quota_is_conflict_without_mutation(site):
    call, ids = site
    request_id = submit(call).json['request']['id']
    db.session.get(User, ids['dm']).active_campaigns_quota = 4
    db.session.commit()
    response = decide(call, request_id, decision='approve', expected_current_quota=3, approved_total=6)
    assert response.status_code == 409 and response.json['error'] == 'quota_changed'
    assert response.json['live']['current'] == 4
    assert quota(ids['dm']) == 4
    assert db.session.get(CampaignQuotaRequest, request_id).status == 'pending'
    assert decide(call, request_id, decision='reject', expected_current_quota=3).status_code == 409
    assert decide(call, request_id, decision='approve', expected_current_quota=4, approved_total=6).status_code == 200
    assert quota(ids['dm']) == 6


def test_quota_removed_after_request_cannot_be_approved(site):
    call, ids = site
    request_id = submit(call).json['request']['id']
    db.session.get(User, ids['dm']).active_campaigns_quota = None
    db.session.commit()
    response = decide(call, request_id, decision='approve', expected_current_quota=None, approved_total=6)
    assert response.status_code == 409 and response.json['error'] == 'quota_not_finite'
    assert quota(ids['dm']) is None
    assert decide(call, request_id, decision='reject', expected_current_quota=None).status_code == 200
    assert quota(ids['dm']) is None


@pytest.mark.parametrize('body,code', [
    (dict(decision='approve', expected_current_quota=2), 'invalid_approved_total'),
    (dict(decision='approve', expected_current_quota=2, approved_total=True), 'invalid_approved_total'),
    (dict(decision='approve', expected_current_quota=2, approved_total='4'), 'invalid_approved_total'),
    (dict(decision='approve', expected_current_quota=2, approved_total=4.0), 'invalid_approved_total'),
    (dict(decision='approve', expected_current_quota=2, approved_total=INT_MAX + 1), 'invalid_approved_total'),
    (dict(decision='approve', expected_current_quota=2, approved_total=2), 'approved_total_not_above_current'),
    (dict(decision='approve', expected_current_quota='2', approved_total=4), 'invalid_expected_quota'),
    (dict(decision='approve', expected_current_quota=False, approved_total=4), 'invalid_expected_quota'),
    (dict(decision='approve', approved_total=4), 'invalid_review_decision'),
    (dict(decision='accept', expected_current_quota=2), 'invalid_review_decision'),
    (dict(decision='reject', expected_current_quota=2, approved_total=4), 'invalid_approved_total'),
    (dict(decision='reject', expected_current_quota=2, reviewer_note='x' * 501), 'invalid_reviewer_note'),
    (dict(decision='reject', expected_current_quota=2, reviewer_note=5), 'invalid_reviewer_note'),
    (dict(decision='reject', expected_current_quota=2, requester_id=1), 'invalid_review_decision'),
])
def test_decision_payload_is_strict(site, body, code):
    call, ids = site
    request_id = submit(call, 'dm2', desired=5).json['request']['id']
    response = decide(call, request_id, **body)
    assert response.status_code == 400 and response.json['error'] == code
    assert quota(ids['dm2']) == 2
    assert db.session.get(CampaignQuotaRequest, request_id).status == 'pending'


def test_approved_total_cannot_be_below_active_count(site):
    call, ids = site
    request_id = submit(call, 'dm2', desired=5).json['request']['id']
    for i in range(2):
        db.session.add(Campaign(name=f'Extra {i}', owner_id=ids['dm2'], status='active'))
    db.session.commit()
    response = decide(call, request_id, decision='approve', expected_current_quota=2, approved_total=3)
    assert response.status_code == 400 and response.json['error'] == 'approved_total_below_active'
    assert decide(call, request_id, decision='approve', expected_current_quota=2, approved_total=4).status_code == 200
    assert quota(ids['dm2']) == 4


@pytest.mark.parametrize('who', ['dm', 'dm2', 'moderator', 'player'])
def test_non_reviewers_cannot_decide(site, who):
    call, ids = site
    request_id = submit(call).json['request']['id']
    response = decide(call, request_id, who, decision='approve', expected_current_quota=3, approved_total=9)
    assert response.status_code == 403
    assert quota(ids['dm']) == 3


def test_decision_requires_reviewer_account_header_and_known_request(site):
    call, ids = site
    request_id = submit(call).json['request']['id']
    body = dict(decision='approve', expected_current_quota=3, approved_total=9)
    assert call('owner', f'review-requests/{request_id}/decision', 'POST', body, account=ids['dm']).status_code == 403
    assert call('owner', f'review-requests/{request_id}/decision', 'POST', body, account=None).status_code == 403
    assert decide(call, 999999, **body).status_code == 404
    assert quota(ids['dm']) == 3


def test_cancelled_request_cannot_be_approved(site):
    call, ids = site
    request_id = submit(call).json['request']['id']
    call('dm', f'requests/{request_id}/cancel', 'POST', {})
    response = decide(call, request_id, decision='approve', expected_current_quota=3, approved_total=9)
    assert response.status_code == 409 and quota(ids['dm']) == 3


# ----- isolated PostgreSQL concurrency (Codex: own throwaway DB/port, never a lane/live URL) -----

PG_URL = os.environ.get('VTT_FV15_PG_URL')


@pytest.fixture
def pg_site(monkeypatch):
    # This fixture drops schema: refuse arbitrary or lane/live URLs even when accidentally exported.
    from sqlalchemy.engine import make_url
    parsed=make_url(PG_URL)
    assert os.environ.get('VTT_FV15_PG_TEST_CONFIRM')=='isolated-fv15-only'
    assert parsed.drivername=='postgresql+psycopg2' and not parsed.query and parsed.host=='127.0.0.1'
    assert parsed.port==55495 and parsed.database.startswith('fv15_test_')
    monkeypatch.setattr(TestingConfig, 'SQLALCHEMY_DATABASE_URI', PG_URL)
    app = create_app('testing')
    def reset_schema():
        # The repository has an unnamed moderation FK cycle; drop_all cannot sort it on PG.
        # This schema belongs solely to the guarded, disposable database above.
        from sqlalchemy import text
        db.session.remove()
        with db.engine.begin() as connection:
            connection.execute(text('DROP SCHEMA public CASCADE'))
            connection.execute(text('CREATE SCHEMA public'))
    with app.app_context():
        reset_schema(); db.create_all()
        ids = _seed()
        db.session.remove()
    try:
        yield app, ids
    finally:
        with app.app_context():
            reset_schema(); db.engine.dispose()


def _race(app, ids, count, action):
    barrier = threading.Barrier(count)
    results = []

    def worker():
        with app.app_context():
            call = _caller(app, ids)
            barrier.wait()
            results.append(action(call).status_code)
            db.session.remove()
    threads = [threading.Thread(target=worker) for _ in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return sorted(results)


@pytest.mark.skipif(not PG_URL, reason='set VTT_FV15_PG_URL to an isolated throwaway PostgreSQL database')
def test_postgres_concurrent_submissions_create_one_pending(pg_site):
    app, ids = pg_site
    results = _race(app, ids, 8, lambda call: submit(call, desired=7))
    assert results.count(201) == 1 and results.count(409) == 7
    with app.app_context():
        assert CampaignQuotaRequest.query.filter_by(requester_id=ids['dm']).count() == 1
        assert db.session.get(User, ids['dm']).active_campaigns_quota == 3


@pytest.mark.skipif(not PG_URL, reason='set VTT_FV15_PG_URL to an isolated throwaway PostgreSQL database')
def test_postgres_concurrent_reviews_apply_exactly_once(pg_site):
    app, ids = pg_site
    with app.app_context():
        request_id = submit(_caller(app, ids), desired=7).json['request']['id']
        db.session.remove()
    results = _race(app, ids, 6, lambda call: decide(
        call, request_id, decision='approve', expected_current_quota=3, approved_total=7))
    assert results.count(200) == 1 and results.count(409) == 5
    with app.app_context():
        assert db.session.get(User, ids['dm']).active_campaigns_quota == 7
        assert AuditLog.query.filter_by(action='campaign_quota_request_approved').count() == 1


@pytest.mark.skipif(not PG_URL, reason='set VTT_FV15_PG_URL to an isolated throwaway PostgreSQL database')
def test_postgres_cancel_and_approve_race_has_one_terminal_state(pg_site):
    app, ids = pg_site
    with app.app_context():
        request_id = submit(_caller(app, ids), desired=7).json['request']['id']
        db.session.remove()
    actions = iter([
        lambda call: call('dm', f'requests/{request_id}/cancel', 'POST', {}),
        lambda call: decide(call, request_id, decision='approve', expected_current_quota=3, approved_total=7),
    ])
    lock = threading.Lock()

    def next_action(call):
        with lock:
            action = next(actions)
        return action(call)
    results = _race(app, ids, 2, next_action)
    assert results == [200, 409]
    with app.app_context():
        row = db.session.get(CampaignQuotaRequest, request_id)
        user_quota = db.session.get(User, ids['dm']).active_campaigns_quota
        assert (row.status, user_quota) in {('cancelled', 3), ('approved', 7)}


@pytest.mark.skipif(not PG_URL, reason='requires guarded isolated PostgreSQL')
def test_postgres_rate_cap_survives_submission_cancel_churn(pg_site):
    app, ids = pg_site
    with app.app_context():
        call=_caller(app,ids)
        for _ in range(4):
            request_id=submit(call).json['request']['id']
            assert call('dm',f'requests/{request_id}/cancel','POST',{}).status_code==200
        db.session.remove()
    def submit_and_cancel(call):
        response=submit(call)
        if response.status_code==201:
            assert call('dm',f"requests/{response.json['request']['id']}/cancel",'POST',{}).status_code==200
        return response
    results=_race(app,ids,8,submit_and_cancel)
    assert results.count(201)==1 and all(code in (201,409,429) for code in results)
    with app.app_context():
        assert CampaignQuotaRequest.query.filter_by(requester_id=ids['dm']).count()==5
        assert db.session.get(User,ids['dm']).active_campaigns_quota==3
