"""Real table API authority and persistent companion resources across placement."""
from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy.orm.attributes import flag_modified

from tests.test_review_domain import domain, world  # noqa: F401
from tests.test_srd_creator_api import wizard_state
from tests.play_shared import add_map, create_token
from vtt.extensions import db
from vtt.models import Campaign, CampaignMember, Character, GameSession, SessionState, TokenState
from vtt.models.table_companion import TableCompanionBinding
from vtt.play.table_companions import table_companions_bp
from vtt.play.service import ensure_session_state
from vtt.rules_content.creator_drafts import character_values
from vtt.rules_content.creator_rules import evaluate, load_creator_data
from vtt.utils.time import utcnow


def register(app):
    if table_companions_bp.name not in app.blueprints:
        app.register_blueprint(table_companions_bp)


@pytest.fixture
def companions(domain):
    app, call, _, campaigns, users, session = domain
    register(app)
    campaign = db.session.get(Campaign, campaigns['A'])
    from vtt.models import User
    map_ = add_map(campaign, db.session.get(User, users[1]))
    sid = session('A', status='in_progress', map_id=map_.id)
    game = db.session.get(GameSession, sid); state = ensure_session_state(campaign, game)
    data = load_creator_data(); source = wizard_state(data)
    char = Character(user_id=users[2], campaign_id=campaign.id,
                     **character_values(data, source, evaluate(data, source), draft_id=1, finalized_at='2026-11-19T08:00:00Z'))
    char.character_data['srdCompanions'] = [dict(id='c12345678', name='Wolf', hpMax=20, hpCurrent=13, ac=13,
        scaling=dict(enabled=True, base=10, perLevel=5, perProficiency=2, label='Own rule'))]
    db.session.add(char); db.session.commit()
    parent = create_token(campaign, game, state, users[2], x=1, y=2)
    parent.character_id = char.id; db.session.commit()
    base = f'/api/play/campaigns/{campaign.id}/sessions/{sid}/characters/{char.id}/companions'
    def context(who=2, mode='player'):
        response = call(who, 'POST', f'/api/play/campaigns/{campaign.id}/sessions/{sid}/contexts', dict(mode=mode, tab=uuid4().hex))
        assert response.status_code == 201, response.json
        return {'X-VTT-Context': response.json['token'], 'X-VTT-Tab': response.json['tab']}
    headers = context()
    def api(method='GET', body=None, who=2, auth=None, companion_id='c12345678'):
        path = base + (f'/{companion_id}/place' if method == 'POST' else '?parent_token_id=' + str(parent.id))
        return call(who, method, path, body, headers if auth is None else auth)
    def payload(**extra):
        return dict(parent_token_id=parent.id, parent_version=parent.version, request_id=str(uuid4())) | extra
    return app, api, payload, char, parent, game, state, map_, context, users


def test_stable_token_damage_softdelete_max_change_and_map_replacement(companions):
    _, api, payload, char, parent, game, state, map_, _, users = companions
    original_character_hp = char.hp_current
    listed = api(); assert listed.status_code == 200, listed.json
    assert listed.json['companions'][0]['hpCurrent'] == 34
    body = payload(); placed = api('POST', body)
    assert placed.status_code == 200, placed.json
    token = db.session.get(TokenState, placed.json['token']['id'])
    assert token.character_id is None and token.owner_user_id == char.user_id
    assert (token.hp_max, token.hp_current, token.x, token.y) == (41, 34, 64, 64)
    assert token.metadata_json['position_mode'] == 'pixel' and token.sight_range == 0
    assert token.visibility == 'public' and token.token_type == 'player'
    token.hp_current = 20; token.version += 1; db.session.commit()
    replay = api('POST', body)
    assert replay.status_code == 200 and replay.headers['X-Request-Replayed'] == 'true'
    db.session.refresh(token); assert token.hp_current == 20
    assert api('POST', payload()).json['token']['id'] == token.id
    assert token.hp_current == 20 and TableCompanionBinding.query.count() == 1
    token.deleted_at = utcnow(); token.version += 1; db.session.commit()
    assert api('POST', payload()).json['token']['id'] == token.id
    assert token.deleted_at is None and token.hp_current == 20
    values = deepcopy(char.character_data); values['srd']['state']['levels'].append({'classKey': 'wizard'})
    char.character_data = values; flag_modified(char, 'character_data'); db.session.commit()
    assert api('POST', payload()).status_code == 200
    assert (token.hp_max, token.hp_current) == (46, 25)  # still 21 damage
    from vtt.models import User
    second = add_map(db.session.get(Campaign, game.campaign_id), db.session.get(User, users[1]))
    second.width, second.height, second.light_rules = 640, 480, {'dimensions_mode': 'pixel'}
    old_version = parent.version
    state.active_map_id = second.id; parent.map_id = second.id; parent.x, parent.y = 120, 160
    parent.metadata_json = {'position_mode': 'pixel'}; parent.version += 1; db.session.commit()
    assert api('POST', payload(parent_version=old_version)).status_code == 409
    replacement = api('POST', payload())
    assert replacement.status_code == 200, replacement.json
    assert (token.id, token.map_id, token.x, token.y, token.hp_current) == (placed.json['token']['id'], second.id, 152, 160, 25)
    assert char.hp_current == original_character_hp
    assert TokenState.query.filter_by(game_session_id=game.id, character_id=None).count() == 1


def test_current_source_parent_visibility_and_membership_precede_replay(companions):
    _, api, payload, char, parent, game, state, map_, context, users = companions
    body = payload(); assert api('POST', body).status_code == 200
    token = db.session.get(TokenState, TableCompanionBinding.query.one().token_id)
    for target in (parent, token):
        target.visibility = 'dm_only'; db.session.commit()
        assert api('POST', body).status_code == 404
        target.visibility = 'public'; db.session.commit()
    original = deepcopy(char.character_data)
    values = deepcopy(original); values['srdCompanions'] = []
    char.character_data = values; flag_modified(char, 'character_data'); db.session.commit()
    assert api('POST', body).status_code == 404
    char.character_data = original; flag_modified(char, 'character_data'); db.session.commit()
    member = CampaignMember.query.filter_by(campaign_id=game.campaign_id, user_id=users[2]).one()
    member.status = 'left'; db.session.commit()
    assert api('POST', body).status_code == 403
    assert token.hp_current == 34


def test_only_effective_actor_own_public_parent_in_active_map(companions):
    _, api, payload, char, parent, game, state, map_, context, users = companions
    for who, mode in ((1, 'player'), (1, 'dm'), (3, 'dm')):
        headers = context(who, mode)
        assert api('POST', payload(), who, headers).status_code == 404
    observer = context(5)
    assert api('POST', payload(), 5, observer).status_code == 403
    for field, invalid in [('visibility', 'owner_only'), ('visibility', 'dm_only'), ('owner_user_id', users[3]),
                           ('deleted_at', utcnow()), ('map_id', 99999), ('character_id', None)]:
        previous = getattr(parent, field); setattr(parent, field, invalid); db.session.commit()
        assert api().status_code == 404, field
        assert api('POST', payload()).status_code == 404, field
        setattr(parent, field, previous); db.session.commit()
    game.status = 'ended'; db.session.commit()
    assert api('POST', payload()).status_code == 403
    assert TableCompanionBinding.query.count() == 0


def test_exact_payload_and_cas_are_checked_without_client_resource_or_vision_values(companions):
    _, api, payload, char, parent, game, state, map_, _, _ = companions
    for extra in ({'hp_current': 9999}, {'x': 123}, {'sight_range': 9999}, {'metadata_json': {}}, {'visibility': 'dm_only'}):
        assert api('POST', payload(**extra)).status_code == 400
    for extra in ({'parent_token_id': True}, {'parent_version': False}, {'request_id': 'bad'}):
        assert api('POST', payload(**extra)).status_code == 400
    assert api('POST', payload(parent_version=parent.version + 1)).status_code == 409
    assert api('POST', payload(), companion_id='missing').status_code == 404
    assert TableCompanionBinding.query.count() == 0
    # A valid current source is required; arbitrary imported JSON never becomes
    # executable rules, invalid resources or an unbounded token generator.
    values = deepcopy(char.character_data); values['srdCompanions'][0]['hpMax'] = 999999
    char.character_data = values; flag_modified(char, 'character_data'); db.session.commit()
    assert api('POST', payload()).status_code == 422
