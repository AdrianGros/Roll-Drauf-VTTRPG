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


class TestSceneLayerManagementApi:
    def _base_url(self, campaign_id, session_id):
        return f"/api/play/campaigns/{campaign_id}/sessions/{session_id}/scene-stack"

    def _init_stack(self, client, campaign, session, map_ids):
        response = client.post(
            f"{self._base_url(campaign.id, session.id)}/init",
            json={"map_ids": map_ids},
        )
        assert response.status_code == 201
        return response.get_json()["scene_stack"]

    def test_dm_can_add_layer_from_existing_map(self, play_dm_user, play_dm_client):
        campaign = create_campaign(play_dm_user, "Add Layer Campaign")
        map_one = add_map(campaign, play_dm_user, "Ground")
        map_two = add_map(campaign, play_dm_user, "Attic")
        session = create_session(campaign, "Add Layer Session", status="scheduled", map_id=map_one.id)
        self._init_stack(play_dm_client, campaign, session, [map_one.id])

        response = play_dm_client.post(
            f"{self._base_url(campaign.id, session.id)}/layers",
            json={"campaign_map_id": map_two.id, "label": "Attic Floor"},
        )
        assert response.status_code == 201
        body = response.get_json()
        assert body["layer"]["campaign_map_id"] == map_two.id
        assert body["layer"]["label"] == "Attic Floor"
        assert len(body["scene_stack"]["layers"]) == 2

    def test_add_layer_defaults_label_to_map_name(self, play_dm_user, play_dm_client):
        campaign = create_campaign(play_dm_user, "Default Label Campaign")
        map_one = add_map(campaign, play_dm_user, "Ground")
        map_two = add_map(campaign, play_dm_user, "Basement")
        session = create_session(campaign, "Default Label Session", status="scheduled", map_id=map_one.id)
        self._init_stack(play_dm_client, campaign, session, [map_one.id])

        response = play_dm_client.post(
            f"{self._base_url(campaign.id, session.id)}/layers",
            json={"campaign_map_id": map_two.id},
        )
        assert response.status_code == 201
        assert response.get_json()["layer"]["label"] == "Basement"

    def test_adding_same_map_twice_returns_409(self, play_dm_user, play_dm_client):
        campaign = create_campaign(play_dm_user, "Duplicate Map Campaign")
        map_one = add_map(campaign, play_dm_user, "Ground")
        session = create_session(campaign, "Duplicate Map Session", status="scheduled", map_id=map_one.id)
        self._init_stack(play_dm_client, campaign, session, [map_one.id])

        response = play_dm_client.post(
            f"{self._base_url(campaign.id, session.id)}/layers",
            json={"campaign_map_id": map_one.id},
        )
        assert response.status_code == 409
        assert "error" in response.get_json()

    def test_dm_can_rename_and_toggle_visibility(self, play_dm_user, play_dm_client):
        campaign = create_campaign(play_dm_user, "Rename Campaign")
        map_one = add_map(campaign, play_dm_user, "Ground")
        session = create_session(campaign, "Rename Session", status="scheduled", map_id=map_one.id)
        stack = self._init_stack(play_dm_client, campaign, session, [map_one.id])
        layer_id = stack["layers"][0]["id"]

        response = play_dm_client.put(
            f"{self._base_url(campaign.id, session.id)}/layers/{layer_id}",
            json={"label": "Renamed Floor", "is_player_visible": False},
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body["layer"]["label"] == "Renamed Floor"
        assert body["layer"]["is_player_visible"] is False

    def test_dm_can_reorder_layers(self, play_dm_user, play_dm_client):
        campaign = create_campaign(play_dm_user, "Reorder Campaign")
        map_one = add_map(campaign, play_dm_user, "Ground")
        map_two = add_map(campaign, play_dm_user, "Roof")
        session = create_session(campaign, "Reorder Session", status="scheduled", map_id=map_one.id)
        stack = self._init_stack(play_dm_client, campaign, session, [map_one.id, map_two.id])
        first_id = stack["layers"][0]["id"]
        second_id = stack["layers"][1]["id"]

        response = play_dm_client.put(
            f"{self._base_url(campaign.id, session.id)}/layers/reorder",
            json={"order": [{"layer_id": first_id, "order_index": 1}, {"layer_id": second_id, "order_index": 0}]},
        )
        assert response.status_code == 200
        reordered = response.get_json()["scene_stack"]["layers"]
        assert reordered[0]["id"] == second_id
        assert reordered[1]["id"] == first_id

        bootstrap = play_dm_client.get(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap")
        assert bootstrap.status_code == 200
        fetched_layers = bootstrap.get_json()["scene_stack"]["layers"]
        assert fetched_layers[0]["id"] == second_id
        assert fetched_layers[1]["id"] == first_id

    def test_reorder_rejects_layer_id_from_other_stack(self, play_dm_user, play_dm_client):
        campaign = create_campaign(play_dm_user, "Reorder Reject Campaign")
        map_one = add_map(campaign, play_dm_user, "Ground")
        map_two = add_map(campaign, play_dm_user, "Roof")
        session = create_session(campaign, "Reorder Reject Session", status="scheduled", map_id=map_one.id)
        stack = self._init_stack(play_dm_client, campaign, session, [map_one.id, map_two.id])
        first_id = stack["layers"][0]["id"]
        bogus_id = first_id + 99999

        response = play_dm_client.put(
            f"{self._base_url(campaign.id, session.id)}/layers/reorder",
            json={"order": [{"layer_id": first_id, "order_index": 5}, {"layer_id": bogus_id, "order_index": 0}]},
        )
        assert response.status_code in (400, 404)

        bootstrap = play_dm_client.get(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap")
        fetched_layers = bootstrap.get_json()["scene_stack"]["layers"]
        first_layer = next(layer for layer in fetched_layers if layer["id"] == first_id)
        assert first_layer["order_index"] != 5

    def test_dm_can_delete_non_active_layer(self, play_dm_user, play_dm_client):
        campaign = create_campaign(play_dm_user, "Delete Non-Active Campaign")
        map_one = add_map(campaign, play_dm_user, "Ground")
        map_two = add_map(campaign, play_dm_user, "Roof")
        session = create_session(campaign, "Delete Non-Active Session", status="scheduled", map_id=map_one.id)
        stack = self._init_stack(play_dm_client, campaign, session, [map_one.id, map_two.id])
        active_layer_id = stack["active_layer_id"]
        other_layer_id = next(layer["id"] for layer in stack["layers"] if layer["id"] != active_layer_id)

        response = play_dm_client.delete(
            f"{self._base_url(campaign.id, session.id)}/layers/{other_layer_id}",
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body["scene_stack"]["active_layer_id"] == active_layer_id
        assert len(body["scene_stack"]["layers"]) == 1

    def test_dm_deleting_active_layer_promotes_another(self, play_dm_user, play_dm_client):
        campaign = create_campaign(play_dm_user, "Delete Active Campaign")
        map_one = add_map(campaign, play_dm_user, "Ground")
        map_two = add_map(campaign, play_dm_user, "Roof")
        session = create_session(campaign, "Delete Active Session", status="scheduled", map_id=map_one.id)
        stack = self._init_stack(play_dm_client, campaign, session, [map_one.id, map_two.id])
        active_layer_id = stack["active_layer_id"]
        remaining_layer_id = next(layer["id"] for layer in stack["layers"] if layer["id"] != active_layer_id)

        response = play_dm_client.delete(
            f"{self._base_url(campaign.id, session.id)}/layers/{active_layer_id}",
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body["scene_stack"]["active_layer_id"] == remaining_layer_id
        assert len(body["scene_stack"]["layers"]) == 1

    def test_dm_deleting_last_layer_clears_active_layer(self, play_dm_user, play_dm_client):
        campaign = create_campaign(play_dm_user, "Delete Last Campaign")
        map_one = add_map(campaign, play_dm_user, "Ground")
        session = create_session(campaign, "Delete Last Session", status="scheduled", map_id=map_one.id)
        stack = self._init_stack(play_dm_client, campaign, session, [map_one.id])
        active_layer_id = stack["active_layer_id"]

        response = play_dm_client.delete(
            f"{self._base_url(campaign.id, session.id)}/layers/{active_layer_id}",
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body["scene_stack"]["active_layer_id"] is None
        assert body["scene_stack"]["layers"] == []

        bootstrap = play_dm_client.get(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap")
        assert bootstrap.get_json()["state_payload"]["state"]["active_map_id"] is None

    def test_player_forbidden_on_all_layer_management_endpoints(
        self, play_dm_user, play_player_user, play_player_client, play_dm_client
    ):
        campaign = create_campaign(play_dm_user, "Player Forbidden Campaign")
        add_member(campaign, play_player_user, "Player")
        map_one = add_map(campaign, play_dm_user, "Ground")
        map_two = add_map(campaign, play_dm_user, "Roof")
        session = create_session(campaign, "Player Forbidden Session", status="scheduled", map_id=map_one.id)
        stack = self._init_stack(play_dm_client, campaign, session, [map_one.id])
        layer_id = stack["layers"][0]["id"]
        base = self._base_url(campaign.id, session.id)

        add_response = play_player_client.post(f"{base}/layers", json={"campaign_map_id": map_two.id})
        assert add_response.status_code == 403

        update_response = play_player_client.put(f"{base}/layers/{layer_id}", json={"label": "Hacked"})
        assert update_response.status_code == 403

        reorder_response = play_player_client.put(
            f"{base}/layers/reorder", json={"order": [{"layer_id": layer_id, "order_index": 0}]}
        )
        assert reorder_response.status_code == 403

        delete_response = play_player_client.delete(f"{base}/layers/{layer_id}")
        assert delete_response.status_code == 403
