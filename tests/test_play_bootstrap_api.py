"""M10 tests: play bootstrap API."""

pytest_plugins = ["tests.play_shared"]

from tests.play_shared import add_map, add_member, create_campaign, create_session


class TestPlayBootstrapApi:
    def test_bootstrap_returns_runtime_payload(self, play_dm_user, play_player_user, play_player_client):
        campaign = create_campaign(play_dm_user, "Bootstrap Campaign")
        add_member(campaign, play_player_user, "Player")
        campaign_map = add_map(campaign, play_dm_user, "Bootstrap Map")
        session = create_session(campaign, "Bootstrap Session", status="scheduled", map_id=campaign_map.id)

        response = play_player_client.get(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap")
        assert response.status_code == 200
        body = response.get_json()
        assert body["campaign"]["id"] == campaign.id
        assert body["session"]["id"] == session.id
        assert body["mode"] == "waiting"
        assert body["read_only"] is True
        assert isinstance(body["action_catalog"], list)
        assert "state_payload" in body

    def test_bootstrap_requires_active_membership(self, play_dm_user, play_outsider_client):
        campaign = create_campaign(play_dm_user, "Protected Campaign")
        campaign_map = add_map(campaign, play_dm_user, "Protected Map")
        session = create_session(campaign, "Protected Session", status="scheduled", map_id=campaign_map.id)

        response = play_outsider_client.get(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap")
        assert response.status_code == 403
