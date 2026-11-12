"""Context authority is independent of campaign ownership and client role flags."""

from datetime import timedelta
import secrets

import pytest

from vtt.extensions import db, socketio
from vtt.models import TableContext, ChatMessage
from vtt.play.service import ensure_session_state
from vtt.utils.realtime import dm_room, build_event_envelope
from vtt.utils.time import utcnow
from tests.play_shared import add_map, add_member, create_campaign, create_session, create_token

pytest_plugins = ["tests.play_shared"]


def enter(client, campaign, session, mode="player"):
    tab = secrets.token_urlsafe(24)
    response = client.post(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/contexts",
                           json={"mode": mode, "tab": tab})
    assert response.status_code == 201, response.get_json()
    return {"X-VTT-Context": response.json["token"], "X-VTT-Tab": tab}


@pytest.fixture
def table(play_dm_user, play_player_user):
    campaign = create_campaign(play_dm_user, "Contexts")
    member = add_member(campaign, play_player_user, "Player")
    map_ = add_map(campaign, play_dm_user)
    session = create_session(campaign, status="in_progress", map_id=map_.id)
    return campaign, session, member


def test_owner_player_bootstrap_and_dm_surface_are_separate(table, play_dm_client, play_dm_user):
    campaign, session, _ = table
    state = ensure_session_state(campaign, session)
    hidden = create_token(campaign, session, state, play_dm_user.id, name="DM secret")
    hidden.visibility = "dm_only"
    db.session.commit()
    player = enter(play_dm_client, campaign, session)
    dm = enter(play_dm_client, campaign, session, "dm")
    base = f"/api/play/campaigns/{campaign.id}/sessions/{session.id}"
    result = play_dm_client.get(base + "/bootstrap", headers=player)
    assert result.status_code == 200
    assert result.json["session_role"] == "PLAYER"
    assert "DM secret" not in result.get_data(as_text=True)
    assert play_dm_client.get(base + "/surface", headers=player).status_code == 403
    assert play_dm_client.post(base + "/scene-stack/init", headers=player, json={}).status_code == 403
    assert play_dm_client.get(base + "/bootstrap", headers=dm).json["session_role"] == "DM"
    assert "DM secret" in play_dm_client.get(base + "/bootstrap", headers=dm).get_data(as_text=True)
    assert play_dm_client.get(base + "/surface", headers=dm).json["fragments"]["session-controls"]
    # Entering another context did not upgrade the existing Player context.
    assert play_dm_client.get(base + "/bootstrap", headers=player).json["session_role"] == "PLAYER"


def test_player_cannot_issue_dm_context(table, play_player_client):
    campaign, session, _ = table
    response = play_player_client.post(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/contexts",
                                      json={"mode": "dm", "tab": "a" * 32})
    assert response.status_code == 403


@pytest.mark.parametrize("failure", ["missing", "forged", "tab", "foreign_user", "expired", "revoked", "foreign_session"])
def test_invalid_context_never_falls_back_to_owner(table, play_dm_client, play_player_client, failure):
    campaign, session, _ = table
    headers = enter(play_dm_client, campaign, session, "dm")
    target = session.id
    client = play_dm_client
    if failure == "missing":
        headers = {}
    elif failure == "forged":
        headers["X-VTT-Context"] = "x" * 43
    elif failure == "tab":
        headers["X-VTT-Tab"] = "x" * 32
    elif failure == "foreign_user":
        client = play_player_client
    elif failure == "foreign_session":
        target = create_session(campaign, "Other", status="in_progress").id
    else:
        context = TableContext.query.order_by(TableContext.id.desc()).first()
        if failure == "expired":
            context.expires_at = utcnow() - timedelta(seconds=1)
        else:
            context.revoked_at = utcnow()
        db.session.commit()
    response = client.get(f"/api/play/campaigns/{campaign.id}/sessions/{target}/bootstrap", headers=headers)
    assert response.status_code == 403
    assert response.json["error"] == "table_context_required"


def test_all_session_http_routes_have_missing_context_guard(table, play_dm_client, play_app):
    campaign, session, _ = table
    checked = 0
    for rule in play_app.url_map.iter_rules():
        if not ("/campaigns/<int:campaign_id>/sessions/<int:session_id>" in rule.rule or
                rule.rule.startswith("/api/sessions/<int:session_id>")) or rule.rule.endswith("/contexts"):
            continue
        args = {name: 1 for name in rule.arguments}
        args.update(campaign_id=campaign.id, session_id=session.id)
        # Build this exact rule: url_for(endpoint) may select a non-table alias
        # (calendar appointment cancellation shares its endpoint with one).
        import re
        path = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", lambda match: str(args[match[1]]), rule.rule)
        method = next(m for m in rule.methods if m not in {"HEAD", "OPTIONS"})
        response = play_dm_client.open(path, method=method, json={} if method != "GET" else None)
        assert response.status_code == 403, (method, path, response.status_code)
        checked += 1
    assert checked >= 45


def join(socket, campaign, session, headers):
    socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id,
                                "context_token": headers["X-VTT-Context"], "tab_id": headers["X-VTT-Tab"]})
    return socket.get_received()


def test_socket_owner_player_parallel_dm_and_duplicate_binding(table, play_dm_client, play_dm_user, play_app):
    campaign, session, _ = table
    state = ensure_session_state(campaign, session)
    hidden = create_token(campaign, session, state, play_dm_user.id, name="secret socket token")
    hidden.visibility = "dm_only"
    db.session.commit()
    player_headers = enter(play_dm_client, campaign, session)
    dm_headers = enter(play_dm_client, campaign, session, "dm")
    player = socketio.test_client(play_app, flask_test_client=play_dm_client)
    dm = socketio.test_client(play_app, flask_test_client=play_dm_client)
    copy = socketio.test_client(play_app, flask_test_client=play_dm_client)
    try:
        events = join(player, campaign, session, player_headers)
        assert any(e["name"] == "state:snapshot" for e in events)
        assert "secret socket token" not in str(events)
        assert "secret socket token" in str(join(dm, campaign, session, dm_headers))
        assert any(e["name"] == "table:context_revoked" for e in join(copy, campaign, session, player_headers))
        player.get_received()
        socketio.emit("test:private", build_event_envelope(campaign.id, session.id, {"secret": "DM only"}),
                      room=dm_room(campaign.id, session.id))
        assert not any(e["name"] == "test:private" for e in player.get_received())
        assert any(e["name"] == "test:private" for e in dm.get_received())
        # Reconnect uses the Player authority again, not the parallel DM authority.
        player.disconnect()
        player = socketio.test_client(play_app, flask_test_client=play_dm_client)
        assert "secret socket token" not in str(join(player, campaign, session, player_headers))
    finally:
        for socket in (player, dm, copy):
            if socket.is_connected():
                socket.disconnect()


def test_membership_revocation_removes_receiver_before_broadcast(table, play_player_client, play_app):
    campaign, session, member = table
    headers = enter(play_player_client, campaign, session)
    socket = socketio.test_client(play_app, flask_test_client=play_player_client)
    try:
        join(socket, campaign, session, headers)
        member.status = "removed"
        db.session.commit()
        socketio.emit("test:private", {"secret": "must not arrive"},
                      room=f"campaign:{campaign.id}:session:{session.id}:players")
        events = socket.get_received()
        assert not any(e["name"] == "test:private" for e in events)
        assert any(e["name"] == "table:context_revoked" for e in events)
    finally:
        socket.disconnect()


def test_public_player_composition_has_no_dm_markup(play_dm_client):
    html = play_dm_client.get("/play").get_data(as_text=True)
    assert 'data-dm-layer=' not in html
    assert 'id="btnInitStack"' not in html
    assert 'src="/static/js/play-dm.js"' not in html
    assert 'src="/static/js/play-player.js"' in html


def test_dm_revocation_blocks_existing_http_and_socket_context(table, play_codm_user, play_codm_client, play_app):
    campaign, session, _ = table
    member = add_member(campaign, play_codm_user, "CO_DM")
    headers = enter(play_codm_client, campaign, session, "dm")
    socket = socketio.test_client(play_app, flask_test_client=play_codm_client)
    try:
        join(socket, campaign, session, headers)
        member.campaign_role = "Player"
        db.session.commit()
        assert play_codm_client.get(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap", headers=headers).status_code == 403
        socketio.emit("test:private", {"secret": "revoked DM"}, room=dm_room(campaign.id, session.id))
        assert not any(e["name"] == "test:private" for e in socket.get_received())
    finally:
        socket.disconnect()


@pytest.mark.parametrize("path", ["state", "combat/start", "maps/activate"])
def test_owner_player_legacy_paths_cannot_gain_dm(table, play_dm_client, path):
    campaign, session, _ = table
    headers = enter(play_dm_client, campaign, session)
    url = f"/api/campaigns/{campaign.id}/sessions/{session.id}/{path}"
    response = play_dm_client.open(url, method="GET" if path == "state" else "POST", headers=headers,
                                  json={"mode": "dm", "role": "DM"} if path != "state" else None)
    if path == "state":
        assert response.status_code == 200
    else:
        assert response.status_code == 403
    assert play_dm_client.get(f"/api/sessions/{session.id}/initiative", headers=headers).status_code == 403


def test_owner_player_cannot_moderate_another_members_message(table, play_dm_client, play_player_user):
    campaign, session, _ = table
    row = ChatMessage(campaign_id=campaign.id, game_session_id=session.id,
                      author_user_id=play_player_user.id, content="Player's words", content_type="text")
    db.session.add(row)
    db.session.commit()
    headers = enter(play_dm_client, campaign, session)
    response = play_dm_client.patch(f"/api/campaigns/{campaign.id}/sessions/{session.id}/chat/messages/{row.id}",
                                    headers=headers, json={"content": "Owner privilege must not apply"})
    assert response.status_code == 403
    db.session.refresh(row)
    assert row.content == "Player's words"


def test_attack_cannot_target_another_session(table, play_player_client, play_player_user):
    campaign, session, _ = table
    other = create_session(campaign, "Other combat", status="in_progress")
    own = create_token(campaign, session, ensure_session_state(campaign, session), play_player_user.id)
    foreign = create_token(campaign, other, ensure_session_state(campaign, other), play_player_user.id)
    response = play_player_client.post(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/actions/execute",
                                      headers=enter(play_player_client, campaign, session),
                                      json={"token_id": own.id, "action_code": "attack_basic", "target_token_id": foreign.id})
    assert response.status_code == 403


def test_moderation_delivery_revalidates_dm_context(table, play_codm_user, play_codm_client, play_app):
    campaign, session, _ = table
    member = add_member(campaign, play_codm_user, "CO_DM")
    headers = enter(play_codm_client, campaign, session, "dm")
    socket = socketio.test_client(play_app, flask_test_client=play_codm_client)
    try:
        join(socket, campaign, session, headers)
        socket.emit("mod:join", {"campaign_id": campaign.id})
        assert any(e['name'] == 'mod:joined' for e in socket.get_received())
        member.campaign_role = "Player"
        db.session.commit()
        socketio.emit("mod:secret", {"private": "must not arrive"}, room=f"campaign:{campaign.id}:mods")
        assert not any(e['name'] == 'mod:secret' for e in socket.get_received())
    finally:
        socket.disconnect()


def test_observer_context_cannot_write_a_dice_roll(table, play_observer_user, play_observer_client, play_app):
    campaign, session, _ = table
    add_member(campaign, play_observer_user, "OBSERVER")
    headers = enter(play_observer_client, campaign, session)
    socket = socketio.test_client(play_app, flask_test_client=play_observer_client)
    try:
        join(socket, campaign, session, headers)
        result = socket.emit("roll_dice", {"campaign_id": campaign.id, "session_id": session.id, "dice": "1d20"}, callback=True)
        assert result['error'] == 'read_only'
        assert ChatMessage.query.filter_by(game_session_id=session.id).count() == 0
    finally:
        socket.disconnect()


def test_logout_revokes_outstanding_table_delegations(table, play_dm_client, play_app):
    campaign, session, _ = table
    headers = enter(play_dm_client, campaign, session, "dm")
    socket = socketio.test_client(play_app, flask_test_client=play_dm_client)
    try:
        join(socket, campaign, session, headers)
        assert play_dm_client.post('/api/auth/logout').status_code == 200
        socketio.emit('test:private', {'secret': 'after logout'}, room=dm_room(campaign.id, session.id))
        assert not any(e['name'] == 'test:private' for e in socket.get_received())
        assert TableContext.query.filter(TableContext.revoked_at.is_(None)).count() == 0
    finally:
        socket.disconnect()


def test_auth_refresh_keeps_its_own_contract_with_table_headers(table, play_dm_client):
    campaign, session, _ = table
    headers = enter(play_dm_client, campaign, session, "dm")
    response = play_dm_client.post('/api/auth/refresh', headers=headers)
    assert response.status_code == 200
    assert play_dm_client.get(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap", headers=headers).json['session_role'] == 'DM'


def test_resume_rotates_capability_keeps_mode_and_context_identity(table,play_dm_client,play_app):
    campaign,session,_=table
    headers=enter(play_dm_client,campaign,session,'player')
    old=TableContext.query.filter_by(token_hash=__import__('hashlib').sha256(headers['X-VTT-Context'].encode()).hexdigest()).one()
    cid=old.id
    socket=socketio.test_client(play_app,flask_test_client=play_dm_client)
    join(socket,campaign,session,headers)
    response=play_dm_client.post(f'/api/play/campaigns/{campaign.id}/sessions/{session.id}/contexts',
        headers=headers,json={'resume':True,'mode':'dm','tab':secrets.token_urlsafe(24)})
    assert response.status_code==201 and response.json['mode']=='player'
    assert not socket.is_connected()
    db.session.expire_all()
    assert db.session.get(TableContext,cid).token_hash==__import__('hashlib').sha256(response.json['token'].encode()).hexdigest()
    endpoint=f'/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap'
    assert play_dm_client.get(endpoint,headers=headers).status_code==403
    new={'X-VTT-Context':response.json['token'],'X-VTT-Tab':response.json['tab']}
    assert play_dm_client.get(endpoint,headers=new).json['session_role']=='PLAYER'
    assert play_dm_client.post(f'/api/play/campaigns/{campaign.id}/sessions/{session.id}/contexts',
        json={'resume':True,'mode':'dm','tab':secrets.token_urlsafe(24)}).status_code==403
