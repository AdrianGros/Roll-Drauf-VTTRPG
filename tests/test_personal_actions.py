"""Persistent character references and durable command/roll receipts."""

import secrets

import pytest

from tests.play_shared import add_map, add_member, create_campaign, create_session, create_token, enter_table
from tests.test_srd_creator_api import data, wizard_state  # noqa: F401
from vtt.extensions import db, socketio
from vtt.models import Character, ChatMessage
from vtt.models.character_hotbar import TableRequestReceipt
from vtt.play.service import ensure_session_state
from vtt.rules_content.creator_drafts import character_values
from vtt.rules_content.creator_rules import evaluate

pytest_plugins = ["tests.play_shared"]


@pytest.fixture
def personal(data, play_dm_user, play_player_user, play_player_client):
    campaign = create_campaign(play_dm_user, "Personal actions")
    add_member(campaign, play_player_user)
    map_ = add_map(campaign, play_dm_user)
    session = create_session(campaign, status="in_progress", map_id=map_.id)
    state = wizard_state(data, "Hotbar caster")
    char = Character(user_id=play_player_user.id, **character_values(data, state, evaluate(data, state),
                     draft_id=1, finalized_at="2026-11-11T08:00:00Z"))
    char.campaign_id = campaign.id
    db.session.add(char)
    db.session.commit()
    token = create_token(campaign, session, ensure_session_state(campaign, session), play_player_user.id)
    token.character_id = char.id
    db.session.commit()
    auth = enter_table(play_player_client, campaign, session)
    base = f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/characters/{char.id}"
    return campaign, session, char, token, base, auth


def test_catalog_and_personal_layout_persist(personal, play_player_client):
    *_, base, auth = personal
    response = play_player_client.get(base + "/hotbar")
    assert response.status_code == 200, response.json
    payload = response.json
    ids = {action['id'] for action in payload['catalog']['actions']}
    assert {'ability:str', 'weapon_attack:unarmed', 'initiative:'} <= ids
    assert any(action.startswith('spell_declare:') for action in ids)
    slots = ['ability:str', None, 'weapon_attack:unarmed']
    saved = play_player_client.put(base + '/hotbar', json={'revision': 0, 'slots': slots})
    assert saved.status_code == 200
    assert play_player_client.get(base + '/hotbar').json['slots'] == slots
    assert play_player_client.put(base + '/hotbar', json={'revision': 0, 'slots': slots}).status_code == 409


@pytest.mark.parametrize('slots', [['not-an-action'], ['ability:str'] * 11, [42], {'script': 'evil()'}])
def test_layout_rejects_unavailable_or_executable_references(personal, play_player_client, slots):
    *_, base, auth = personal
    response = play_player_client.put(base + '/hotbar', json={'revision': 0, 'slots': slots})
    assert response.status_code in {400, 422}
    assert play_player_client.get(base + '/hotbar').json['revision'] == 0


def test_personal_roll_receipt_returns_same_result_once(personal, play_player_client):
    campaign, session, char, token, base, auth = personal
    catalog = play_player_client.get(base + '/hotbar').json['catalog']
    body = {'request_id': secrets.token_urlsafe(20), 'catalog_revision': catalog['revision'], 'action_id': 'ability:str'}
    first = play_player_client.post(base + '/actions/execute', json=body)
    assert first.status_code == 200, first.json
    second = play_player_client.post(base + '/actions/execute', json=body)
    assert second.status_code == 200 and second.json == first.json
    assert second.headers['X-Request-Replayed'] == 'true'
    assert ChatMessage.query.filter_by(game_session_id=session.id).count() == 1
    changed = play_player_client.post(base + '/actions/execute', json={**body, 'action_id': 'ability:dex'})
    assert changed.status_code == 409 and changed.json['error'] == 'request_id_reused'
    assert ChatMessage.query.filter_by(game_session_id=session.id).count() == 1


def test_catalog_version_and_foreign_character_never_execute(personal, play_player_client, play_outsider_client):
    campaign, session, char, token, base, auth = personal
    catalog = play_player_client.get(base + '/hotbar').json['catalog']
    body = {'request_id': secrets.token_urlsafe(20), 'catalog_revision': 'old', 'action_id': 'ability:str'}
    response = play_player_client.post(base + '/actions/execute', json=body)
    assert response.status_code == 409 and response.json['error'] == 'action_catalog_changed'
    assert play_outsider_client.get(base + '/hotbar', headers={'X-VTT-Context': auth['token'], 'X-VTT-Tab': auth['tab']}).status_code == 403
    assert ChatMessage.query.filter_by(game_session_id=session.id).count() == 0


def test_spell_announcement_is_explicit_and_idempotent(personal, play_player_client):
    campaign, session, char, token, base, auth = personal
    catalog = play_player_client.get(base + '/hotbar').json['catalog']
    action = next(a for a in catalog['actions'] if a['kind'] == 'spell_declare')
    body = {'request_id': secrets.token_urlsafe(20), 'catalog_revision': catalog['revision'], 'action_id': action['id']}
    first = play_player_client.post(base + '/actions/execute', json=body)
    assert first.status_code == 200 and first.json['resources'] == 'manual'
    assert play_player_client.post(base + '/actions/execute', json=body).json == first.json
    assert ChatMessage.query.filter_by(game_session_id=session.id).count() == 1


def test_pending_receipt_cannot_execute_again(personal, play_player_client):
    campaign, session, char, token, base, auth = personal
    catalog = play_player_client.get(base + '/hotbar').json['catalog']
    body = {'request_id': secrets.token_urlsafe(20), 'catalog_revision': catalog['revision'], 'action_id': 'ability:str'}
    first = play_player_client.post(base + '/actions/execute', json=body)
    receipt = TableRequestReceipt.query.first()
    receipt.response = None
    receipt.status_code = None
    db.session.commit()
    replay = play_player_client.post(base + '/actions/execute', json=body)
    assert replay.status_code == 409 and replay.json['error'] == 'request_in_progress'
    assert ChatMessage.query.filter_by(game_session_id=session.id).count() == 1


def test_socket_roll_request_id_survives_repeat_without_broadcast(personal, play_player_client, play_app):
    campaign, session, char, token, base, auth = personal
    socket = socketio.test_client(play_app, flask_test_client=play_player_client)
    try:
        socket.emit('session:join', {'campaign_id': campaign.id, 'session_id': session.id,
                                   'context_token': auth['token'], 'tab_id': auth['tab']})
        socket.get_received()
        body = {'campaign_id': campaign.id, 'session_id': session.id, 'dice': '1d20', 'client_event_id': secrets.token_urlsafe(20)}
        first = socket.emit('roll_dice', body, callback=True)
        assert first.get('message_id'), first
        assert any(e['name'] == 'dice_rolled' for e in socket.get_received())
        second = socket.emit('roll_dice', body, callback=True)
        assert second == first
        assert not any(e['name'] == 'dice_rolled' for e in socket.get_received())
        assert ChatMessage.query.filter_by(game_session_id=session.id).count() == 1
    finally:
        socket.disconnect()


def test_second_character_and_other_member_have_independent_layouts(personal, data, play_player_client,
                                                                  play_player_user, play_codm_user, play_codm_client):
    campaign, session, char, token, base, auth = personal
    first = play_player_client.put(base + '/hotbar', json={'revision': 0, 'slots': ['ability:str']})
    assert first.status_code == 200
    state = wizard_state(data, 'Second character')
    other = Character(user_id=play_player_user.id, **character_values(data, state, evaluate(data,state),
                      draft_id=2, finalized_at='2026-11-11T08:00:00Z'))
    other.campaign_id = campaign.id
    db.session.add(other);db.session.commit()
    second_token = create_token(campaign, session, ensure_session_state(campaign,session), play_player_user.id)
    second_token.character_id = other.id;db.session.commit()
    second_base = f'/api/play/campaigns/{campaign.id}/sessions/{session.id}/characters/{other.id}'
    assert play_player_client.get(second_base + '/hotbar').json['slots'] == []
    assert play_player_client.put(second_base + '/hotbar',json={'revision':0,'slots':['ability:dex']}).status_code == 200
    assert play_player_client.get(base + '/hotbar').json['slots'] == ['ability:str']
    add_member(campaign,play_codm_user,'Player')
    enter_table(play_codm_client,campaign,session)
    assert play_codm_client.get(base + '/hotbar').status_code == 403
    assert play_codm_client.put(base + '/hotbar',json={'revision':1,'slots':[]}).status_code == 403


def test_receipt_replays_after_transport_capability_rotation(personal,play_player_client):
    campaign,session,char,token,base,auth=personal
    catalog=play_player_client.get(base+'/hotbar').json['catalog']
    body={'request_id':secrets.token_urlsafe(20),'catalog_revision':catalog['revision'],'action_id':'ability:str'}
    first=play_player_client.post(base+'/actions/execute',json=body)
    assert first.status_code==200
    response=play_player_client.post(f'/api/play/campaigns/{campaign.id}/sessions/{session.id}/contexts',
        json={'resume':True,'tab':secrets.token_urlsafe(24)})
    assert response.status_code==201
    headers={'X-VTT-Context':response.json['token'],'X-VTT-Tab':response.json['tab']}
    second=play_player_client.post(base+'/actions/execute',json=body,headers=headers)
    assert second.status_code==200 and second.json==first.json
    assert second.headers['X-Request-Replayed']=='true'
    assert ChatMessage.query.filter_by(game_session_id=session.id).count()==1
