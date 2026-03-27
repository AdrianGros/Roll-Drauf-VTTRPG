"""M10 tests: session lifecycle state machine."""

pytest_plugins = ["tests.play_shared"]

from tests.play_shared import add_map, add_member, create_campaign, create_session


class TestSessionStateMachine:
    def test_valid_transition_flow_dm(self, play_dm_user, play_player_user, play_dm_client):
        campaign = create_campaign(play_dm_user, "Flow Campaign")
        add_member(campaign, play_player_user, "Player")
        campaign_map = add_map(campaign, play_dm_user, "Flow Map")
        session = create_session(campaign, "Flow Session", status="scheduled", map_id=campaign_map.id)

        init_response = play_dm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/scene-stack/init",
            json={},
        )
        assert init_response.status_code == 201

        ready_response = play_dm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/transition",
            json={"target_state": "ready"},
        )
        assert ready_response.status_code == 200
        assert ready_response.get_json()["session"]["runtime_status"] == "ready"

        start_response = play_dm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/transition",
            json={"target_state": "in_progress", "ignore_warnings": True},
        )
        assert start_response.status_code == 200
        assert start_response.get_json()["mode"] == "live"

        pause_response = play_dm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/transition",
            json={"target_state": "paused"},
        )
        assert pause_response.status_code == 200
        assert pause_response.get_json()["mode"] == "paused"

        resume_response = play_dm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/transition",
            json={"target_state": "in_progress", "ignore_warnings": True},
        )
        assert resume_response.status_code == 200
        assert resume_response.get_json()["mode"] == "live"

        end_response = play_dm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/transition",
            json={"target_state": "ended"},
        )
        assert end_response.status_code == 200
        assert end_response.get_json()["mode"] == "ended"

    def test_invalid_transition_is_rejected(self, play_dm_user, play_dm_client):
        campaign = create_campaign(play_dm_user, "Invalid Transition Campaign")
        campaign_map = add_map(campaign, play_dm_user, "Invalid Map")
        session = create_session(campaign, "Invalid Session", status="scheduled", map_id=campaign_map.id)

        response = play_dm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/transition",
            json={"target_state": "in_progress", "ignore_warnings": True},
        )
        assert response.status_code == 409

    def test_codm_can_transition_but_player_cannot(self, play_dm_user, play_codm_user, play_player_user, play_codm_client, play_player_client):
        campaign = create_campaign(play_dm_user, "Role Campaign")
        add_member(campaign, play_codm_user, "CO_DM")
        add_member(campaign, play_player_user, "Player")
        campaign_map = add_map(campaign, play_dm_user, "Role Map")
        session = create_session(campaign, "Role Session", status="scheduled", map_id=campaign_map.id)

        codm_ready = play_codm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/transition",
            json={"target_state": "ready"},
        )
        assert codm_ready.status_code == 200

        player_forbidden = play_player_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/transition",
            json={"target_state": "ready"},
        )
        assert player_forbidden.status_code == 403
