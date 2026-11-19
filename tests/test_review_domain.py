"""Real HTTP coverage of parent authority, retries, CAS and derived companion HP."""
from copy import deepcopy
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from tests.test_c06_calendar import world  # noqa: F401
from tests.test_srd_creator_api import wizard_state
from vtt.extensions import db
from vtt.models import CampaignMember, Character, ModerationAction, User
from vtt.models.review_domain import AtlasCampaignLink, ReviewThread, ReviewThreadMessage
from vtt.review_domain import review_domain_bp
from vtt.rules_content.creator_drafts import character_values
from vtt.rules_content.creator_rules import evaluate, load_creator_data

BASE = '/api/review-domain'


def register(app):
    # Integration deliberately belongs to the parent task, not this worker.
    if review_domain_bp.name not in app.blueprints:
        app.register_blueprint(review_domain_bp)


@pytest.fixture
def domain(world, tmp_path):
    app, _, session, campaigns, users = world
    register(app)
    app.config.update(LOCAL_STORAGE_PATH=str(tmp_path / 'storage'), STORAGE_PROVIDER='local')
    for identity in users.values():
        db.session.get(User, identity).storage_quota_gb = 1
    db.session.commit()
    client = app.test_client()
    tokens = {key: create_access_token(identity=str(value)) for key, value in users.items()}

    def call(who, method, path, data=None, headers=None):
        client.set_cookie('access_token_cookie', tokens[who])
        return client.open(path if path.startswith('/api/') else BASE + path,
                           method=method, json=data, headers=headers or {})

    def thread(who=2, kind='private', parent=None, title='Secret thread', key=None):
        if parent is None:
            response = call(who, 'POST', '/api/private-conversations',
                            dict(campaign_id=campaigns['A'], recipient_user_id=users[3]))
            assert response.status_code in (200, 201), response.json
            parent = response.json['conversation']['id']
        data = dict(kind=kind, parent_id=parent, title=title, request_id=key or str(uuid4()))
        response = call(who, 'POST', '/threads', data)
        assert response.status_code in (200, 201), response.json
        return response.json['thread'], data

    return app, call, thread, campaigns, users, session


def test_private_thread_pair_is_the_only_audience_and_replay_uses_original_title(domain):
    _, call, create, campaigns, users, _ = domain
    thread, body = create()
    tid = thread['id']
    payload = dict(content='<b>PRIVATE THREAD</b>', request_id=str(uuid4()))
    first = call(2, 'POST', f'/threads/{tid}/messages', payload)
    assert first.status_code == 201
    for outsider in (1, 4, 5, 6, 7, 8, 9, 10):
        for path in (f'/threads/{tid}', f'/threads?kind=private&parent_id={body["parent_id"]}'):
            response = call(outsider, 'GET', path)
            assert response.status_code == 404, outsider
            assert 'PRIVATE THREAD' not in response.text
            assert response.headers['Cache-Control'] == 'private, no-store'
        assert call(outsider, 'POST', f'/threads/{tid}/messages', payload).status_code == 404
    assert call(3, 'GET', f'/threads/{tid}').json['messages'][0]['content'] == payload['content']
    assert call(3, 'PUT', f'/threads/{tid}', dict(revision=1, title='Hijack', closed=False)).status_code == 404
    changed = call(2, 'PUT', f'/threads/{tid}', dict(revision=1, title='Renamed', closed=True))
    assert changed.status_code == 200 and changed.json['thread']['revision'] == 2
    # The original create retry remains idempotent after a later rename.
    replay = call(2, 'POST', '/threads', body)
    assert replay.status_code == 200 and replay.json['thread']['title'] == 'Renamed'
    assert call(2, 'POST', '/threads', {**body, 'title': 'Renamed'}).status_code == 409
    assert call(2, 'PUT', f'/threads/{tid}', dict(revision=1, title='Lost update', closed=False)).status_code == 409
    assert call(2, 'POST', f'/threads/{tid}/messages', payload).json['replayed'] is True
    assert call(2, 'POST', f'/threads/{tid}/messages', {**payload, 'request_id': str(uuid4())}).status_code == 409
    assert ReviewThread.query.count() == ReviewThreadMessage.query.count() == 1


def test_private_parent_revocation_precedes_history_and_acknowledged_retry(domain):
    _, call, create, campaigns, users, _ = domain
    thread, body = create()
    payload = dict(content='confirmed', request_id=str(uuid4()))
    assert call(2, 'POST', f'/threads/{thread["id"]}/messages', payload).status_code == 201
    CampaignMember.query.filter_by(campaign_id=campaigns['A'], user_id=users[3]).one().status = 'left'
    db.session.commit()
    assert call(3, 'GET', f'/threads/{thread["id"]}').status_code == 404
    retained = call(2, 'GET', f'/threads/{thread["id"]}')
    assert retained.status_code == 200 and retained.json['thread']['can_send'] is False
    assert call(2, 'POST', '/threads', body).status_code == 409
    assert call(2, 'POST', f'/threads/{thread["id"]}/messages', payload).status_code == 409
    db.session.get(User, users[2]).is_active = False
    db.session.commit()
    assert call(2, 'GET', f'/threads/{thread["id"]}').status_code == 404


def test_campaign_thread_crossaccess_mutes_bans_and_current_context(domain):
    _, call, create, campaigns, users, session = domain
    thread, _ = create(kind='campaign', parent=campaigns['A'])
    tid = thread['id']
    for who in (1, 2, 3, 5):
        assert call(who, 'GET', f'/threads/{tid}').status_code == 200
    for who in (4, 6, 7, 8, 9, 10):
        assert call(who, 'GET', f'/threads/{tid}').status_code == 404
    payload = dict(content='campaign reply', request_id=str(uuid4()))
    assert call(3, 'POST', f'/threads/{tid}/messages', payload).status_code == 201
    sanction = ModerationAction(campaign_id=campaigns['A'], actor_user_id=users[1],
                                subject_user_id=users[3], action_type='mute')
    db.session.add(sanction); db.session.commit()
    assert call(3, 'GET', f'/threads/{tid}').json['thread']['can_send'] is False
    assert call(3, 'POST', f'/threads/{tid}/messages', payload).status_code == 403
    sanction.action_type = 'ban'; db.session.commit()
    assert call(3, 'GET', f'/threads/{tid}').status_code == 403
    sid = session('A', status='in_progress')
    def context(who, campaign, mode='player'):
        response = call(who, 'POST', f'/api/play/campaigns/{campaign}/sessions/{sid}/contexts',
                        dict(mode=mode, tab=uuid4().hex))
        assert response.status_code == 201, response.json
        return {'X-VTT-Context': response.json['token'], 'X-VTT-Tab': response.json['tab']}
    observer = context(5, campaigns['A'])
    assert call(5, 'GET', f'/threads/{tid}', headers=observer).json['thread']['can_send'] is False
    assert call(5, 'POST', f'/threads/{tid}/messages', payload, observer).status_code == 403
    owner_player = context(1, campaigns['A'])
    # Player mode permits ordinary campaign text but never DM link authority.
    assert call(1, 'POST', f'/threads/{tid}/messages', payload, owner_player).status_code == 201
    other = session('B', status='in_progress')
    response = call(2, 'POST', f'/api/play/campaigns/{campaigns["B"]}/sessions/{other}/contexts',
                    dict(mode='player', tab=uuid4().hex))
    headers = {'X-VTT-Context': response.json['token'], 'X-VTT-Tab': response.json['tab']}
    assert call(2, 'GET', f'/threads/{tid}', headers=headers).status_code == 404


def test_thread_history_bounded_cursors_and_payloads(domain):
    _, call, create, campaigns, users, _ = domain
    thread, body = create()
    for index in range(105):
        db.session.add(ReviewThreadMessage(thread_id=thread['id'], author_id=users[2],
                       request_id=str(uuid4()), content=str(index)))
    for index in range(52):
        db.session.add(ReviewThread(private_conversation_id=body['parent_id'], created_by=users[2],
                       request_id=str(uuid4()), request_title=str(index), title=str(index)))
    db.session.commit()
    path = f'/threads/{thread["id"]}'
    latest = call(2, 'GET', path).json
    assert len(latest['messages']) == 50 and latest['messages'][0]['content'] == '55' and latest['more']
    older = call(2, 'GET', path + '?before=' + str(latest['oldest_id'])).json
    assert [message['content'] for message in older['messages']] == [str(i) for i in range(5, 55)]
    first = call(2, 'GET', path + '?after=0').json
    assert first == latest
    listed = call(2, 'GET', f'/threads?kind=private&parent_id={body["parent_id"]}').json
    assert len(listed['threads']) == 50 and listed['next_after']
    assert len(call(2, 'GET', f'/threads?kind=private&parent_id={body["parent_id"]}&after={listed["next_after"]}').json['threads']) == 3
    for query in ('?before=-1', '?after=bad', '?after=1&before=2', '?after=2147483648'):
        assert call(2, 'GET', path + query).status_code == 400
    for content in ('', ' ', 'x' * 2001, '\x00', {'html': 'wrong'}):
        assert call(2, 'POST', path + '/messages', dict(content=content, request_id=str(uuid4()))).status_code == 400
    assert call(2, 'POST', '/threads', {**body, 'attachment': 'forbidden'}).status_code == 400


def test_world_links_require_both_resources_never_grant_and_guard_revision(domain):
    _, call, _, campaigns, users, session = domain
    response = call(1, 'POST', '/api/atlas/worlds', dict(title='Private world'))
    assert response.status_code == 201, response.json
    world = response.json
    path = f'/worlds/{world["id"]}/campaigns'
    payload = dict(campaign_id=campaigns['A'], world_revision=world['revision'], request_id=str(uuid4()))
    assert call(2, 'POST', path, payload).status_code == 404
    assert call(1, 'POST', path, {**payload, 'campaign_id': campaigns['B']}).status_code == 404
    sid = session('A', status='in_progress')
    ctx = call(1, 'POST', f'/api/play/campaigns/{campaigns["A"]}/sessions/{sid}/contexts', dict(mode='player', tab=uuid4().hex)).json
    headers = {'X-VTT-Context': ctx['token'], 'X-VTT-Tab': ctx['tab']}
    assert call(1, 'GET', '/managed-campaigns', headers=headers).json['campaigns'] == []
    assert call(1, 'POST', path, payload, headers).status_code == 404
    created = call(1, 'POST', path, payload)
    assert created.status_code == 201 and created.json['world_revision'] == world['revision'] + 1
    assert call(1, 'POST', path, payload).json['replayed'] is True
    assert call(1, 'POST', path, {**payload, 'request_id': str(uuid4())}).status_code == 409
    # Campaign membership creates no world membership and no private world discovery.
    assert call(2, 'GET', path).status_code == 404
    assert call(2, 'GET', '/api/atlas/worlds').json['worlds'] == []
    world = call(1, 'GET', '/api/atlas/worlds/' + world['id']).json
    response = call(1, 'PUT', '/api/atlas/worlds/' + world['id'] + '/members',
                    dict(revision=world['revision'], username=db.session.get(User, users[2]).username, role='editor'))
    assert response.status_code == 200
    assert call(2, 'GET', path).json['campaigns'][0]['name'] == 'Alpha'
    assert call(2, 'POST', path, payload).status_code == 404  # editor is not world owner
    CampaignMember.query.filter_by(campaign_id=campaigns['A'], user_id=users[2]).one().status = 'left'
    db.session.commit()
    assert call(2, 'GET', path).json['campaigns'] == []
    revision = call(1, 'GET', path).json['world_revision']
    delete = f'{path}/{campaigns["A"]}'
    assert call(1, 'DELETE', delete, dict(world_revision=revision - 1, revision=1)).status_code == 409
    assert call(1, 'DELETE', delete, dict(world_revision=revision, revision=2)).status_code == 409
    assert call(1, 'DELETE', delete, dict(world_revision=revision, revision=1)).status_code == 200
    assert AtlasCampaignLink.query.count() == 0


def test_world_reader_publication_boundary_and_codm_revocation_on_retry(domain):
    _, call, _, campaigns, users, _ = domain
    response = call(3, 'POST', '/api/atlas/worlds', dict(title='CoDM owned world'))
    assert response.status_code == 201, response.json
    world = response.json; atlas = '/api/atlas/worlds/' + world['id']
    path = f'/worlds/{world["id"]}/campaigns'
    payload = dict(campaign_id=campaigns['A'], world_revision=world['revision'], request_id=str(uuid4()))
    assert call(3, 'POST', path, payload).status_code == 201
    revision = call(3, 'GET', path).json['world_revision']
    granted = call(3, 'PUT', atlas + '/members', dict(revision=revision,
                   username=db.session.get(User, users[2]).username, role='reader'))
    assert granted.status_code == 200, granted.json
    assert call(2, 'GET', path).status_code == 404  # unpublished world
    published = call(3, 'POST', atlas + '/publish', dict(revision=granted.json['revision'], confirm_visible_pixels=True))
    assert published.status_code == 201, published.json
    assert call(2, 'GET', path).json['campaigns'][0]['campaign_id'] == campaigns['A']
    role = CampaignMember.query.filter_by(campaign_id=campaigns['A'], user_id=users[3]).one()
    role.campaign_role = 'PLAYER'; db.session.commit()
    assert call(3, 'POST', path, payload).status_code == 404
    assert call(3, 'DELETE', path + '/' + str(campaigns['A']), dict(world_revision=granted.json['revision'], revision=1)).status_code == 404
    current = call(3, 'GET', atlas).json
    assert call(3, 'PUT', atlas + '/members', dict(revision=current['revision'],
                username=db.session.get(User, users[2]).username, role=None)).status_code == 200
    assert call(2, 'GET', path).status_code == 404


@pytest.fixture
def companion(domain):
    _, call, _, _, users, _ = domain
    data = load_creator_data(); state = wizard_state(data)
    char = Character(user_id=users[2], **character_values(data, state, evaluate(data, state),
                     draft_id=1, finalized_at='2026-11-18T08:00:00Z'))
    char.character_data['srdCompanions'] = [dict(id='c12345678', name='Wolf', hpMax=20, hpCurrent=13, ac=13, speed='12 m')]
    db.session.add(char); db.session.commit()
    return call, char


def test_companion_scaling_cas_owner_bounds_damage_and_manual_defaults(companion):
    call, char = companion
    path = f'/characters/{char.id}/companion-scaling'
    original = deepcopy(char.character_data)
    initial = call(2, 'GET', path)
    assert initial.status_code == 200 and initial.json['companions'][0]['hpMax'] == 20
    assert char.character_data == original  # GET never materializes derived HP
    config = dict(enabled=True, base=10, perLevel=5, perProficiency=2, label='My custom rule')
    payload = dict(revision=initial.json['revision'], companion_id='c12345678', scaling=config)
    assert call(3, 'PUT', path, payload).status_code in (403, 404)
    saved = call(2, 'PUT', path, payload)
    assert saved.status_code == 200, saved.json
    row = saved.json['companions'][0]
    assert (row['id'], row['name'], row['hpMax'], row['hpCurrent']) == ('c12345678', 'Wolf', 41, 34)
    assert call(2, 'PUT', path, payload).status_code == 409
    fresh = {**payload, 'revision': saved.json['revision']}
    for invalid in ({**config, 'perLevel': 101}, {**config, 'base': True},
                    {**config, 'label': 'x' * 81}, {**config, 'label': '\ud800'}, {**config, 'formula': 'eval()'}):
        assert call(2, 'PUT', path, {**fresh, 'scaling': invalid}).status_code == 422
    assert call(2, 'PUT', path, {**fresh, 'companion_id': 'missing'}).status_code == 404
    # Derived HP follows actual SRD evaluation and retains seven damage without a GET write.
    from sqlalchemy.orm.attributes import flag_modified
    values = deepcopy(char.character_data)
    values['srd']['state']['levels'].append({'classKey': 'wizard'})
    char.character_data = values; flag_modified(char, 'character_data'); db.session.commit()
    stored = deepcopy(char.character_data)
    current = call(2, 'GET', path).json
    assert current['level'] == 6 and current['companions'][0]['hpMax'] == 46
    assert current['companions'][0]['hpCurrent'] == 39 and char.character_data == stored
    # An older ordinary editor may edit text/HP but cannot remove the separate rule.
    manual = call(2, 'PUT', f'/api/srd-creator/characters/{char.id}/companions',
                  dict(companions=[dict(id='c12345678', name='Wolf renamed', hpMax=41, hpCurrent=34, ac=13)]))
    assert manual.status_code == 200, manual.json
    assert manual.json['companions'][0]['scaling'] == config
    assert (manual.json['companions'][0]['hpMax'], manual.json['companions'][0]['hpCurrent']) == (46, 39)
    current = call(2, 'GET', path).json
    disabled = call(2, 'PUT', path, dict(revision=current['revision'], companion_id='c12345678', scaling={**config, 'enabled': False}))
    assert disabled.status_code == 200
    assert disabled.json['companions'][0]['hpCurrent'] == 39
    capped = call(2, 'PUT', path, dict(revision=disabled.json['revision'], companion_id='c12345678', scaling={**config, 'base': 9999, 'perLevel': 100}))
    assert capped.status_code == 200 and capped.json['companions'][0]['hpMax'] == 9999
