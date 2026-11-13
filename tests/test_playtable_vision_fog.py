"""S10 (vision/walls/lights/Fog of War) server-side tests.

Covers the REST/socket-adjacent contract on top of the pure-geometry unit
tests in test_vision_engine.py: permission boundaries (DM-only geometry
mutation, per-user fog isolation), the destructive fog-reset flow, and
that a real token move through the socket handler actually recomputes
and persists fog -- not just that the underlying math is correct.
"""

from datetime import datetime

import pytest

from tests.play_shared import enter_table
from vtt import create_app
from vtt.extensions import db, socketio
from vtt.models import (
    Campaign,
    CampaignMap,
    CampaignMember,
    FogOfWarState,
    GameSession,
    Role,
    SceneLight,
    SceneWall,
    TokenState,
    User,
)


def _login(client, username, password="Password123!"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response


def _create_campaign(owner_user, name):
    campaign = Campaign(name=name, description="vision tests", owner_id=owner_user.id,
                        status="active", max_players=6)
    db.session.add(campaign)
    db.session.flush()
    db.session.add(CampaignMember(
        campaign_id=campaign.id, user_id=owner_user.id, campaign_role="DM",
        status="active", joined_at=datetime.utcnow(), invited_at=datetime.utcnow(),
        accepted_at=datetime.utcnow(), invited_by=owner_user.id))
    db.session.commit()
    return campaign


def _add_member(campaign, user, campaign_role="Player"):
    db.session.add(CampaignMember(
        campaign_id=campaign.id, user_id=user.id, campaign_role=campaign_role,
        status="active", joined_at=datetime.utcnow(), invited_at=datetime.utcnow(),
        accepted_at=datetime.utcnow(), invited_by=campaign.owner_id))
    db.session.commit()


def _add_map_and_live_session(campaign, creator_user, grid_size=50, fog_enabled=True):
    campaign_map = CampaignMap(campaign_id=campaign.id, name="Vision Map", width=2000, height=2000,
                               grid_size=grid_size, fog_enabled=fog_enabled, created_by=creator_user.id)
    db.session.add(campaign_map)
    db.session.flush()
    session = GameSession(campaign_id=campaign.id, map_id=campaign_map.id, name="Vision Session",
                          status="in_progress")
    db.session.add(session)
    db.session.commit()
    return campaign_map, session


def _init_active_map(client, campaign_id, session_id, map_ids):
    enter_table(client, db.session.get(Campaign,campaign_id), db.session.get(GameSession,session_id), "dm")
    response = client.post(
        f"/api/play/campaigns/{campaign_id}/sessions/{session_id}/scene-stack/init",
        json={"map_ids": map_ids})
    assert response.status_code == 201, response.get_json()


def _add_token(state_id, campaign, session, campaign_map, name, x, y, owner_user_id=None, sight_range=None):
    token = TokenState(
        session_state_id=state_id, campaign_id=campaign.id, game_session_id=session.id,
        map_id=campaign_map.id, name=name, token_type="npc", x=x, y=y,
        owner_user_id=owner_user_id, sight_range=sight_range,
    )
    db.session.add(token)
    db.session.commit()
    return token


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    with app.app_context():
        db.create_all()
        for role_name in ["Player", "DM", "Admin"]:
            db.session.add(Role(name=role_name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def dm_user(app):
    user = User(username="vision_dm", email="vision_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="vision_player", email="vision_player@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def dm_client(app, dm_user):
    client = app.test_client()
    _login(client, dm_user.username)
    return client


@pytest.fixture
def player_client(app, player_user):
    client = app.test_client()
    _login(client, player_user.username)
    return client


def _vision_url(campaign, session, suffix):
    return f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/vision/{suffix}"


class TestWallPermissions:
    def test_player_cannot_create_a_wall(self, app, dm_user, player_user, dm_client, player_client):
        campaign = _create_campaign(dm_user, "Wand-Kampagne")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_live_session(campaign, dm_user)
        _init_active_map(dm_client, campaign.id, session.id, [campaign_map.id])
        enter_table(player_client, campaign, session, "player")

        response = player_client.post(_vision_url(campaign, session, "walls"),
                                      json={"x0": 0, "y0": 0, "x1": 100, "y1": 0})
        assert response.status_code == 403
        assert SceneWall.query.count() == 0

    def test_dm_creates_a_wall_and_the_dm_can_read_it(self, app, dm_user, player_user, dm_client, player_client):
        campaign = _create_campaign(dm_user, "Wand-Kampagne 2")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_live_session(campaign, dm_user)
        _init_active_map(dm_client, campaign.id, session.id, [campaign_map.id])
        enter_table(player_client, campaign, session, "player")

        create = dm_client.post(_vision_url(campaign, session, "walls"),
                                json={"x0": 0, "y0": 0, "x1": 100, "y1": 0, "sight": "normal"})
        assert create.status_code == 201, create.get_json()

        listing = dm_client.get(_vision_url(campaign, session, "walls"))
        assert listing.status_code == 200
        assert len(listing.get_json()["walls"]) == 1

    def test_player_cannot_read_wall_geometry(self, app, dm_user, player_user, dm_client, player_client):
        """Fixed 2026-09-02: full wall geometry reveals room/corridor
        shapes and secret-door locations -- exactly what fog-of-war
        exists to hide. Player reads must be blocked the same as
        Player writes already were."""
        campaign = _create_campaign(dm_user, "Wand-Kampagne 3")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_live_session(campaign, dm_user)
        _init_active_map(dm_client, campaign.id, session.id, [campaign_map.id])
        enter_table(player_client, campaign, session, "player")

        create = dm_client.post(_vision_url(campaign, session, "walls"),
                                json={"x0": 0, "y0": 0, "x1": 100, "y1": 0, "sight": "normal"})
        assert create.status_code == 201, create.get_json()

        listing = player_client.get(_vision_url(campaign, session, "walls"))
        assert listing.status_code == 403

    def test_zero_length_wall_is_rejected(self, app, dm_user, dm_client):
        campaign = _create_campaign(dm_user, "Nullwand-Kampagne")
        campaign_map, session = _add_map_and_live_session(campaign, dm_user)
        _init_active_map(dm_client, campaign.id, session.id, [campaign_map.id])

        response = dm_client.post(_vision_url(campaign, session, "walls"),
                                  json={"x0": 50, "y0": 50, "x1": 50, "y1": 50})
        assert response.status_code == 400
        assert "non-zero length" in response.get_json()["error"]


class TestLightPermissions:
    def test_player_cannot_create_a_light(self, app, dm_user, player_user, dm_client, player_client):
        campaign = _create_campaign(dm_user, "Licht-Kampagne")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_live_session(campaign, dm_user)
        _init_active_map(dm_client, campaign.id, session.id, [campaign_map.id])
        enter_table(player_client, campaign, session, "player")

        response = player_client.post(_vision_url(campaign, session, "lights"),
                                      json={"x": 10, "y": 10, "bright_radius": 50, "dim_radius": 100})
        assert response.status_code == 403
        assert SceneLight.query.count() == 0

    def test_dm_can_create_and_patch_a_light(self, app, dm_user, dm_client):
        campaign = _create_campaign(dm_user, "Licht-Kampagne 2")
        campaign_map, session = _add_map_and_live_session(campaign, dm_user)
        _init_active_map(dm_client, campaign.id, session.id, [campaign_map.id])

        create = dm_client.post(_vision_url(campaign, session, "lights"),
                                json={"x": 10, "y": 10, "bright_radius": 50, "dim_radius": 100})
        assert create.status_code == 201, create.get_json()
        light_id = create.get_json()["light"]["id"]

        patch = dm_client.patch(_vision_url(campaign, session, f"lights/{light_id}"),
                                json={"light_type": "darkness"})
        assert patch.status_code == 200
        assert patch.get_json()["light"]["light_type"] == "darkness"

    def test_player_cannot_read_light_geometry(self, app, dm_user, player_user, dm_client, player_client):
        """Fixed 2026-09-02 -- same reasoning as
        test_player_cannot_read_wall_geometry above."""
        campaign = _create_campaign(dm_user, "Licht-Kampagne 3")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_live_session(campaign, dm_user)
        _init_active_map(dm_client, campaign.id, session.id, [campaign_map.id])
        enter_table(player_client, campaign, session, "player")

        create = dm_client.post(_vision_url(campaign, session, "lights"),
                                json={"x": 10, "y": 10, "bright_radius": 50, "dim_radius": 100})
        assert create.status_code == 201, create.get_json()

        listing = player_client.get(_vision_url(campaign, session, "lights"))
        assert listing.status_code == 403


class TestFogPersistenceAndIsolation:
    def test_token_move_over_socket_persists_fog_for_its_owner_only(
        self, app, dm_user, player_user, dm_client, player_client
    ):
        campaign = _create_campaign(dm_user, "Sichtfeld-Kampagne")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_live_session(campaign, dm_user, grid_size=50)
        _init_active_map(dm_client, campaign.id, session.id, [campaign_map.id])
        enter_table(player_client, campaign, session, "player")

        from vtt.play.service import ensure_session_state
        state = ensure_session_state(campaign, session)
        token = _add_token(state.id, campaign, session, campaign_map, "Held", x=100, y=100,
                           owner_user_id=player_user.id, sight_range=200)

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        player_socket = socketio.test_client(app, flask_test_client=player_client)
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id, "context_token":dm_client.environ_base["HTTP_X_VTT_CONTEXT"], "tab_id":dm_client.environ_base["HTTP_X_VTT_TAB"]})
        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id, "context_token":player_client.environ_base["HTTP_X_VTT_CONTEXT"], "tab_id":player_client.environ_base["HTTP_X_VTT_TAB"]})
        dm_socket.get_received()
        player_socket.get_received()

        player_socket.emit("token:update", {
            "context_token":player_client.environ_base["HTTP_X_VTT_CONTEXT"], "tab_id":player_client.environ_base["HTTP_X_VTT_TAB"],
            "campaign_id": campaign.id, "session_id": session.id, "token_id": token.id,
            "base_version": token.version, "client_event_id": "vision-move-1",
            "patch": {"x": 150, "y": 150},
        })

        fog = FogOfWarState.query.filter_by(user_id=player_user.id, campaign_map_id=campaign_map.id).first()
        assert fog is not None, "moving an owned token must create/persist that owner's fog row"
        assert fog.visible_cells, "a token with sight_range should see something around itself"

        # Only the owning player receives the fog:updated broadcast --
        # never the DM's own socket, and never another player's.
        player_fog_events = [e for e in player_socket.get_received() if e["name"] == "fog:updated"]
        assert len(player_fog_events) == 1
        dm_fog_events = [e for e in dm_socket.get_received() if e["name"] == "fog:updated"]
        assert not dm_fog_events, "fog updates are per-owner, the DM room must not receive them"

    def test_fog_disabled_map_never_creates_a_fog_row(self, app, dm_user, player_user, dm_client, player_client):
        campaign = _create_campaign(dm_user, "Kein-Nebel-Kampagne")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_live_session(campaign, dm_user, fog_enabled=False)
        _init_active_map(dm_client, campaign.id, session.id, [campaign_map.id])
        enter_table(player_client, campaign, session, "player")
        from vtt.play.service import ensure_session_state
        state = ensure_session_state(campaign, session)
        token = _add_token(state.id, campaign, session, campaign_map, "Held", x=100, y=100,
                           owner_user_id=player_user.id)

        player_socket = socketio.test_client(app, flask_test_client=player_client)
        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id, "context_token":player_client.environ_base["HTTP_X_VTT_CONTEXT"], "tab_id":player_client.environ_base["HTTP_X_VTT_TAB"]})
        player_socket.get_received()
        player_socket.emit("token:update", {
            "context_token":player_client.environ_base["HTTP_X_VTT_CONTEXT"], "tab_id":player_client.environ_base["HTTP_X_VTT_TAB"],
            "campaign_id": campaign.id, "session_id": session.id, "token_id": token.id,
            "base_version": token.version, "client_event_id": "no-fog-move-1",
            "patch": {"x": 150, "y": 150},
        })

        assert FogOfWarState.query.count() == 0

    def test_player_can_only_read_their_own_fog(self, app, dm_user, player_user, dm_client, player_client):
        campaign = _create_campaign(dm_user, "Eigener-Nebel-Kampagne")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_live_session(campaign, dm_user)
        _init_active_map(dm_client, campaign.id, session.id, [campaign_map.id])
        enter_table(player_client, campaign, session, "player")

        db.session.add(FogOfWarState(user_id=dm_user.id, campaign_map_id=campaign_map.id,
                                     explored_cells=[[1, 1]], visible_cells=[[1, 1]]))
        db.session.commit()

        response = player_client.get(_vision_url(campaign, session, "fog"))
        assert response.status_code == 200
        assert response.get_json()["fog"] is None, "a player must never see another user's fog row"


class TestFogReset:
    def test_player_cannot_reset_fog(self, app, dm_user, player_user, dm_client, player_client):
        campaign = _create_campaign(dm_user, "Reset-Kampagne")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_live_session(campaign, dm_user)
        _init_active_map(dm_client, campaign.id, session.id, [campaign_map.id])
        enter_table(player_client, campaign, session, "player")

        response = player_client.post(_vision_url(campaign, session, "fog/reset"), json={"confirm": True})
        assert response.status_code == 403

    def test_reset_requires_explicit_confirm(self, app, dm_user, dm_client):
        campaign = _create_campaign(dm_user, "Reset-Kampagne 2")
        campaign_map, session = _add_map_and_live_session(campaign, dm_user)
        _init_active_map(dm_client, campaign.id, session.id, [campaign_map.id])

        response = dm_client.post(_vision_url(campaign, session, "fog/reset"), json={})
        assert response.status_code == 400

    def test_reset_clears_explored_history_for_every_user_and_logs_to_chat(
        self, app, dm_user, player_user, dm_client, player_client
    ):
        campaign = _create_campaign(dm_user, "Reset-Kampagne 3")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_live_session(campaign, dm_user)
        _init_active_map(dm_client, campaign.id, session.id, [campaign_map.id])
        enter_table(player_client, campaign, session, "player")

        db.session.add(FogOfWarState(user_id=player_user.id, campaign_map_id=campaign_map.id,
                                     explored_cells=[[1, 1], [2, 2]], visible_cells=[[1, 1]]))
        db.session.commit()

        response = dm_client.post(_vision_url(campaign, session, "fog/reset"), json={"confirm": True})
        assert response.status_code == 200
        body = response.get_json()
        assert player_user.id in body["affected_user_ids"]

        fog = FogOfWarState.query.filter_by(user_id=player_user.id, campaign_map_id=campaign_map.id).first()
        assert fog.explored_cells == []

        from vtt.models import ChatMessage
        audit = ChatMessage.query.filter_by(game_session_id=session.id, content_type="fog_reset").first()
        assert audit is not None, "a reset must leave an audit trail in session chat"


class TestVisibleTokensDebugEndpoint:
    def test_dm_only_can_query_visible_tokens_from_a_tokens_perspective(
        self, app, dm_user, player_user, dm_client, player_client
    ):
        campaign = _create_campaign(dm_user, "Sichtliste-Kampagne")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_live_session(campaign, dm_user, grid_size=50)
        _init_active_map(dm_client, campaign.id, session.id, [campaign_map.id])
        enter_table(player_client, campaign, session, "player")
        from vtt.play.service import ensure_session_state
        state = ensure_session_state(campaign, session)

        origin = _add_token(state.id, campaign, session, campaign_map, "Beobachter", x=0, y=0, sight_range=200)
        near = _add_token(state.id, campaign, session, campaign_map, "Nah", x=50, y=0)
        far = _add_token(state.id, campaign, session, campaign_map, "Fern", x=2000, y=0)

        forbidden = player_client.get(_vision_url(campaign, session, f"tokens/{origin.id}/visible"))
        assert forbidden.status_code == 403

        response = dm_client.get(_vision_url(campaign, session, f"tokens/{origin.id}/visible"))
        assert response.status_code == 200
        visible_ids = {row["id"] for row in response.get_json()["visible_tokens"]}
        assert near.id in visible_ids
        assert far.id not in visible_ids


def test_private_fog_has_contiguous_ticks_without_leaking_contents(app, dm_user, player_user, dm_client, player_client):
    from vtt.play.service import ensure_session_state
    campaign = _create_campaign(dm_user, 'Fog sequence')
    _add_member(campaign, player_user)
    campaign_map, session = _add_map_and_live_session(campaign, dm_user)
    _init_active_map(dm_client, campaign.id, session.id, [campaign_map.id])
    enter_table(player_client, campaign, session, 'player')
    state = ensure_session_state(campaign, session)
    _add_token(state.id, campaign, session, campaign_map, 'Owner', x=200, y=200,
               owner_user_id=player_user.id, sight_range=100)
    sockets = []
    for client in [dm_client, player_client]:
        socket = socketio.test_client(app, flask_test_client=client)
        socket.emit('session:join', {'campaign_id':campaign.id,'session_id':session.id,
                    'context_token':client.environ_base['HTTP_X_VTT_CONTEXT'],'tab_id':client.environ_base['HTTP_X_VTT_TAB']})
        sockets.append(socket)
    for socket in sockets:socket.get_received()
    assert dm_client.post(_vision_url(campaign, session, 'lights'), json={'x':200,'y':200,'bright_radius':300,'dim_radius':350}).status_code == 201
    light = SceneLight.query.one()
    assert dm_client.patch(_vision_url(campaign,session,f'lights/{light.id}'),json={'bright_radius':250}).status_code == 200
    deliveries = [socket.get_received() for socket in sockets]
    for events in deliveries:
        sequence = sorted({e['args'][0]['event_seq'] for e in events if e['name'] in {'vision:geometry_changed','fog:updated','state:tick'}})
        assert len(sequence) == 4 and sequence == list(range(sequence[0],sequence[0]+4))
    assert not [e for e in deliveries[0] if e['name']=='fog:updated']
    assert len([e for e in deliveries[1] if e['name']=='fog:updated']) == 2
    assert all('fog' not in e['args'][0] for e in deliveries[0] if e['name']=='state:tick')
