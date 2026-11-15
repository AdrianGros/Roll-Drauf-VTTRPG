"""Token ownership never grants a Player context control of the DM layer."""
import secrets

import pytest

from tests.play_shared import create_token
from tests.test_table_contexts import table, enter, join  # noqa: F401
from vtt.extensions import db, socketio
from vtt.play.service import ensure_session_state

pytest_plugins = ['tests.play_shared']


@pytest.mark.parametrize('actor', ['owner_as_player', 'player'])
@pytest.mark.parametrize('transport', ['http', 'socket'])
def test_hidden_ownership_cannot_create_reveal_delete_or_leak_conflicts(
        table, play_app, play_dm_user, play_player_user, play_dm_client, play_player_client, actor, transport):
    campaign, session, _ = table
    user = play_dm_user if actor == 'owner_as_player' else play_player_user
    client = play_dm_client if actor == 'owner_as_player' else play_player_client
    state = ensure_session_state(campaign, session)
    hidden = create_token(campaign, session, state, user.id, name='Private-layer-sentinel')
    hidden.visibility = 'dm_only'
    public = create_token(campaign, session, state, user.id, name='Public owned hero')
    db.session.commit()
    hidden_id, public_id = hidden.id, public.id
    player_headers = enter(client, campaign, session, 'player')
    dm_headers = enter(play_dm_client, campaign, session, 'dm')
    base = f'/api/campaigns/{campaign.id}/sessions/{session.id}/tokens'
    peer = socketio.test_client(play_app, flask_test_client=play_dm_client)
    sock = None
    try:
        join(peer, campaign, session, dm_headers)
        if transport == 'socket':
            sock = socketio.test_client(play_app, flask_test_client=client)
            assert 'Private-layer-sentinel' not in str(join(sock, campaign, session, player_headers))
        operations = [
            ('create', None, {'name': 'Hidden new', 'token_type': 'player', 'x': 140, 'y': 140, 'visibility': 'dm_only'}),
            ('update', hidden_id, {'base_version': 1, 'patch': {'visibility': 'public'}}),
            ('update', hidden_id, {'base_version': 0, 'patch': {'x': 150}}),
            ('delete', hidden_id, {'base_version': 1}),
            ('delete', hidden_id, {'base_version': 0}),
            ('update', public_id, {'base_version': 1, 'patch': {'visibility': 'dm_only'}}),
        ]
        for operation, token_id, body in operations:
            peer.get_received()
            if transport == 'http':
                url = base + (f'/{token_id}' if token_id is not None else '')
                response = client.open(url, method={'create': 'POST', 'update': 'PUT', 'delete': 'DELETE'}[operation],
                                       headers=player_headers, json=body)
                assert response.status_code == 403, (operation, response.get_json())
                assert 'Private-layer-sentinel' not in response.get_data(as_text=True)
            else:
                packet = {'campaign_id': campaign.id, 'session_id': session.id, 'client_event_id': secrets.token_hex(16)}
                if operation == 'create':
                    packet['token'] = body
                else:
                    packet.update(token_id=token_id, **body)
                sock.emit('token:' + operation, packet)
                events = sock.get_received()
                assert 'forbidden' in str(events), events
                assert 'Private-layer-sentinel' not in str(events)
            assert not any(e['name'].startswith('token:') for e in peer.get_received())
            db.session.expire_all()
            assert db.session.get(type(hidden), hidden_id).visibility == 'dm_only'
            assert db.session.get(type(hidden), hidden_id).version == 1
            assert db.session.get(type(hidden), hidden_id).deleted_at is None

        # The same Player authority can still perform its permitted public movement.
        if transport == 'http':
            assert client.put(base + f'/{public_id}', headers=player_headers,
                              json={'base_version': 1, 'patch': {'x': 150}}).status_code == 200
        else:
            sock.emit('token:update', {'campaign_id': campaign.id, 'session_id': session.id, 'token_id': public_id,
                      'base_version': 1, 'patch': {'x': 150}, 'client_event_id': secrets.token_hex(16)})
            assert any(e['name'] == 'token:updated' for e in sock.get_received())
        db.session.expire_all()
        assert db.session.get(type(public), public_id).x == 150
        # Only an explicitly authorized DM context may transfer the hidden token.
        response = play_dm_client.put(base + f'/{hidden_id}', headers=dm_headers,
                                      json={'base_version': 1, 'patch': {'visibility': 'public'}})
        assert response.status_code == 200, response.get_json()
    finally:
        for connection in (sock, peer):
            if connection and connection.is_connected():
                connection.disconnect()
