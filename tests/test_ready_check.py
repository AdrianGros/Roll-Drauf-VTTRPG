"""M10 tests: ready-check behavior."""

pytest_plugins = ["tests.play_shared"]

from tests.play_shared import add_map, add_member, create_campaign, create_session


class TestReadyCheck:
    def test_ready_check_blocks_without_scene_stack(self, play_dm_user, play_dm_client):
        campaign = create_campaign(play_dm_user, "Ready Block Campaign")
        campaign_map = add_map(campaign, play_dm_user, "Ready Block Map")
        session = create_session(campaign, "Ready Block Session", status="ready", map_id=campaign_map.id)

        response = play_dm_client.get(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/ready-check")
        assert response.status_code == 200
        body = response.get_json()
        assert body["can_start"] is False
        assert any("scene stack" in issue for issue in body["blocking_issues"])

    def test_ready_check_returns_warnings_not_blockers(self, play_dm_user, play_player_user, play_dm_client):
        campaign = create_campaign(play_dm_user, "Ready Warn Campaign")
        add_member(campaign, play_player_user, "Player")
        campaign_map = add_map(campaign, play_dm_user, "Ready Warn Map")
        session = create_session(campaign, "Ready Warn Session", status="ready", map_id=campaign_map.id)

        init_response = play_dm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/scene-stack/init",
            json={},
        )
        assert init_response.status_code == 201

        response = play_dm_client.get(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/ready-check")
        assert response.status_code == 200
        body = response.get_json()
        assert body["can_start"] is True
        assert body["blocking_issues"] == []
        assert isinstance(body["warnings"], list)
