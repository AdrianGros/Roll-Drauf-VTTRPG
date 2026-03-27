"""M10 tests: scene stack initialization and layer switching."""

pytest_plugins = ["tests.play_shared"]

from tests.play_shared import add_map, add_member, create_campaign, create_session


class TestSceneStackApi:
    def test_init_scene_stack_creates_layers(self, play_dm_user, play_dm_client):
        campaign = create_campaign(play_dm_user, "Stack Campaign")
        map_one = add_map(campaign, play_dm_user, "Floor 1")
        map_two = add_map(campaign, play_dm_user, "Floor 2")
        session = create_session(campaign, "Stack Session", status="scheduled", map_id=map_one.id)

        response = play_dm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/scene-stack/init",
            json={"map_ids": [map_one.id, map_two.id]},
        )
        assert response.status_code == 201
        body = response.get_json()
        assert body["scene_stack"]["game_session_id"] == session.id
        assert len(body["scene_stack"]["layers"]) == 2

    def test_activate_layer_updates_active_map(self, play_dm_user, play_dm_client):
        campaign = create_campaign(play_dm_user, "Activate Campaign")
        map_one = add_map(campaign, play_dm_user, "Ground")
        map_two = add_map(campaign, play_dm_user, "Tower")
        session = create_session(campaign, "Activate Session", status="scheduled", map_id=map_one.id)

        init_response = play_dm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/scene-stack/init",
            json={"map_ids": [map_one.id, map_two.id]},
        )
        assert init_response.status_code == 201
        layers = init_response.get_json()["scene_stack"]["layers"]
        second_layer_id = layers[1]["id"]

        activate_response = play_dm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/scene-stack/layers/{second_layer_id}/activate",
            json={},
        )
        assert activate_response.status_code == 200
        body = activate_response.get_json()
        assert body["active_layer"]["campaign_map_id"] == map_two.id
        assert body["state"]["active_map_id"] == map_two.id

    def test_player_cannot_initialize_scene_stack(self, play_dm_user, play_player_user, play_player_client):
        campaign = create_campaign(play_dm_user, "Forbidden Stack Campaign")
        add_member(campaign, play_player_user, "Player")
        campaign_map = add_map(campaign, play_dm_user, "Forbidden Map")
        session = create_session(campaign, "Forbidden Session", status="scheduled", map_id=campaign_map.id)

        response = play_player_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/scene-stack/init",
            json={},
        )
        assert response.status_code == 403
