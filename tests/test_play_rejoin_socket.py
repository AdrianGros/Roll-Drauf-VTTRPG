"""M10 tests: play mode socket/rejoin guarantees."""

pytest_plugins = ["tests.play_shared"]

from vtt_app.extensions import socketio
from tests.play_shared import add_map, add_member, create_campaign, create_session


class TestPlayRejoinSocket:
    def test_session_join_emits_play_mode(self, play_app, play_dm_user, play_player_user, play_player_client):
        campaign = create_campaign(play_dm_user, "Socket Join Campaign")
        add_member(campaign, play_player_user, "Player")
        campaign_map = add_map(campaign, play_dm_user, "Socket Join Map")
        session = create_session(campaign, "Socket Join Session", status="scheduled", map_id=campaign_map.id)

        player_socket = socketio.test_client(play_app, flask_test_client=play_player_client)
        assert player_socket.is_connected()

        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        events = player_socket.get_received()
        mode_events = [event for event in events if event["name"] == "play:mode"]
        assert mode_events
        mode_payload = mode_events[-1]["args"][0]
        assert isinstance(mode_payload.get("event_seq"), int)
        snapshot_events = [event for event in events if event["name"] == "state:snapshot"]
        assert snapshot_events
        snapshot_payload = snapshot_events[-1]["args"][0]
        assert isinstance(snapshot_payload.get("event_seq"), int)
        player_socket.disconnect()

    def test_rejoin_gets_latest_mode_after_transition(self, play_app, play_dm_user, play_player_user, play_dm_client, play_player_client):
        campaign = create_campaign(play_dm_user, "Rejoin Campaign")
        add_member(campaign, play_player_user, "Player")
        campaign_map = add_map(campaign, play_dm_user, "Rejoin Map")
        session = create_session(campaign, "Rejoin Session", status="scheduled", map_id=campaign_map.id)

        init_response = play_dm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/scene-stack/init",
            json={},
        )
        assert init_response.status_code == 201
        play_dm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/transition",
            json={"target_state": "ready"},
        )
        play_dm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/transition",
            json={"target_state": "in_progress", "ignore_warnings": True},
        )

        player_socket = socketio.test_client(play_app, flask_test_client=play_player_client)
        assert player_socket.is_connected()
        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})

        events = player_socket.get_received()
        mode_events = [event for event in events if event["name"] == "play:mode"]
        assert mode_events
        latest_mode = mode_events[-1]["args"][0]
        assert latest_mode["mode"] == "live"
        assert latest_mode["status"] == "in_progress"
        assert isinstance(latest_mode.get("event_seq"), int)
        player_socket.disconnect()
