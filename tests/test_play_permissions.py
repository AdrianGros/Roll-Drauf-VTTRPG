"""M10 tests: runtime role and read-only permissions."""

pytest_plugins = ["tests.play_shared"]

from tests.play_shared import add_map, add_member, create_campaign, create_session


class TestPlayPermissions:
    def test_waiting_room_is_read_only_for_player(self, play_dm_user, play_player_user, play_player_client):
        campaign = create_campaign(play_dm_user, "Waiting Campaign")
        add_member(campaign, play_player_user, "Player")
        campaign_map = add_map(campaign, play_dm_user, "Waiting Map")
        session = create_session(campaign, "Waiting Session", status="scheduled", map_id=campaign_map.id)

        response = play_player_client.get(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap")
        assert response.status_code == 200
        body = response.get_json()
        assert body["mode"] == "waiting"
        assert body["read_only"] is True

    def test_live_mode_is_not_read_only_for_player(self, play_dm_user, play_player_user, play_player_client):
        campaign = create_campaign(play_dm_user, "Live Campaign")
        add_member(campaign, play_player_user, "Player")
        campaign_map = add_map(campaign, play_dm_user, "Live Map")
        session = create_session(campaign, "Live Session", status="in_progress", map_id=campaign_map.id)

        response = play_player_client.get(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap")
        assert response.status_code == 200
        body = response.get_json()
        assert body["mode"] == "live"
        assert body["read_only"] is False

    def test_observer_stays_read_only_even_live(self, play_dm_user, play_observer_user, play_observer_client):
        campaign = create_campaign(play_dm_user, "Observer Campaign")
        add_member(campaign, play_observer_user, "Observer")
        campaign_map = add_map(campaign, play_dm_user, "Observer Map")
        session = create_session(campaign, "Observer Session", status="in_progress", map_id=campaign_map.id)

        response = play_observer_client.get(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap")
        assert response.status_code == 200
        body = response.get_json()
        assert body["mode"] == "live"
        assert body["read_only"] is True

    def test_player_cannot_change_session_state(self, play_dm_user, play_player_user, play_player_client):
        campaign = create_campaign(play_dm_user, "Player Forbidden Campaign")
        add_member(campaign, play_player_user, "Player")
        campaign_map = add_map(campaign, play_dm_user, "Forbidden Map")
        session = create_session(campaign, "Forbidden Session", status="scheduled", map_id=campaign_map.id)

        response = play_player_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/transition",
            json={"target_state": "ready"},
        )
        assert response.status_code == 403
