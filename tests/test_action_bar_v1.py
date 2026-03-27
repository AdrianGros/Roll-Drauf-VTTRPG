"""M10 tests: action bar execution contracts."""

pytest_plugins = ["tests.play_shared"]

from tests.play_shared import add_map, add_member, create_campaign, create_session


class TestActionBarV1:
    def test_player_can_execute_action_on_owned_token_in_live_mode(self, play_dm_user, play_player_user, play_dm_client, play_player_client):
        campaign = create_campaign(play_dm_user, "Action Campaign")
        add_member(campaign, play_player_user, "Player")
        campaign_map = add_map(campaign, play_dm_user, "Action Map")
        session = create_session(campaign, "Action Session", status="in_progress", map_id=campaign_map.id)

        create_token = play_player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/tokens",
            json={"name": "Player Token", "x": 1, "y": 1, "token_type": "player"},
        )
        assert create_token.status_code == 201
        token_id = create_token.get_json()["token"]["id"]

        response = play_player_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/actions/execute",
            json={
                "token_id": token_id,
                "action_code": "dash_move",
                "payload": {"distance": 6},
            },
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body["result"]["action_code"] == "dash_move"
        assert body["result"]["token_id"] == token_id

    def test_player_cannot_execute_action_on_foreign_token(self, play_dm_user, play_player_user, play_dm_client, play_player_client):
        campaign = create_campaign(play_dm_user, "Foreign Action Campaign")
        add_member(campaign, play_player_user, "Player")
        campaign_map = add_map(campaign, play_dm_user, "Foreign Action Map")
        session = create_session(campaign, "Foreign Action Session", status="in_progress", map_id=campaign_map.id)

        create_token = play_dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/tokens",
            json={"name": "DM Token", "x": 3, "y": 3, "token_type": "npc"},
        )
        assert create_token.status_code == 201
        token_id = create_token.get_json()["token"]["id"]

        response = play_player_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/actions/execute",
            json={
                "token_id": token_id,
                "action_code": "dash_move",
            },
        )
        assert response.status_code == 403

    def test_attack_action_requires_target(self, play_dm_user, play_player_user, play_player_client):
        campaign = create_campaign(play_dm_user, "Target Action Campaign")
        add_member(campaign, play_player_user, "Player")
        campaign_map = add_map(campaign, play_dm_user, "Target Action Map")
        session = create_session(campaign, "Target Action Session", status="in_progress", map_id=campaign_map.id)

        create_token = play_player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/tokens",
            json={"name": "Attacker", "x": 1, "y": 1, "token_type": "player"},
        )
        assert create_token.status_code == 201
        token_id = create_token.get_json()["token"]["id"]

        response = play_player_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/actions/execute",
            json={
                "token_id": token_id,
                "action_code": "attack_basic",
            },
        )
        assert response.status_code == 400
