"""Regression coverage for the Goblin Brawl Schabernacks Trap."""

import pytest

pytest_plugins = ["tests.play_shared"]

from vtt.extensions import db, socketio
from vtt.models import TokenState
from tests.play_shared import add_map, add_member, create_campaign, create_session


def _create_token(client, campaign_id, session_id, payload):
    response = client.post(
        f"/api/campaigns/{campaign_id}/sessions/{session_id}/tokens",
        json=payload,
    )
    assert response.status_code == 201
    return response.get_json()["token"]


class TestSchabernacksTrap:
    def test_extended_range_fires_five_poison_dart_volleys_at_every_enemy_and_disappears(
        self, play_dm_user, play_player_user, play_dm_client, play_player_client, monkeypatch
    ):
        campaign = create_campaign(play_dm_user, "Goblin Brawl")
        add_member(campaign, play_player_user, "Player")
        campaign_map = add_map(campaign, play_dm_user, "Brawl Map")
        session = create_session(campaign, "Goblin Brawl Session", status="in_progress", map_id=campaign_map.id)

        trap = _create_token(
            play_dm_client,
            campaign.id,
            session.id,
            {
                "name": "Schabernacks Trap",
                "x": 100,
                "y": 100,
                "token_type": "object",
                "metadata_json": {
                    "trap": {
                        "kind": "schabernacks_trap",
                        "target_token_types": ["player"],
                    }
                },
            },
        )
        nearby_enemy = _create_token(
            play_player_client,
            campaign.id,
            session.id,
            {
                "name": "Hero in dart range",
                "x": 340,
                "y": 100,
                "token_type": "player",
                "hp_current": 100,
                "hp_max": 100,
            },
        )
        entering_enemy = _create_token(
            play_player_client,
            campaign.id,
            session.id,
            {
                "name": "Hero entering range",
                "x": 400,
                "y": 100,
                "token_type": "player",
                "hp_current": 100,
                "hp_max": 100,
            },
        )

        monkeypatch.setattr("vtt.dice.random.randint", lambda _minimum, _maximum: 2)
        response = play_player_client.put(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/tokens/{entering_enemy['id']}",
            json={"patch": {"x": 330}, "base_version": entering_enemy["version"]},
        )

        assert response.status_code == 200
        body = response.get_json()
        trap_results = body["trap_results"]
        assert len(trap_results) == 1
        trap_result = trap_results[0]
        assert trap_result["trigger_range"] == 280
        assert len(trap_result["volleys"]) == 5
        assert all(
            {target["token_id"] for target in volley["targets"]}
            == {nearby_enemy["id"], entering_enemy["id"]}
            for volley in trap_result["volleys"]
        )
        assert all(
            target["damage_type"] == "poison"
            and target["damage"] == 2
            and target["condition"] == "poisoned"
            for volley in trap_result["volleys"]
            for target in volley["targets"]
        )

        nearby_row = db.session.get(TokenState, nearby_enemy["id"])
        entering_row = db.session.get(TokenState, entering_enemy["id"])
        trap_row = db.session.get(TokenState, trap["id"])
        assert nearby_row.hp_current == 90
        assert entering_row.hp_current == 90
        assert nearby_row.metadata_json["conditions"] == ["poisoned"]
        assert entering_row.metadata_json["conditions"] == ["poisoned"]
        assert trap_row.deleted_at is not None

        retry = play_player_client.put(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/tokens/{entering_enemy['id']}",
            json={"patch": {"x": 320}, "base_version": body["token"]["version"]},
        )
        assert retry.status_code == 200
        assert retry.get_json()["trap_results"] == []
        assert db.session.get(TokenState, entering_enemy["id"]).hp_current == 90

    def test_socket_movement_uses_the_same_trap_trigger(self, play_dm_user, play_player_user, play_dm_client, play_player_client, monkeypatch):
        campaign = create_campaign(play_dm_user, "Goblin Brawl Socket")
        add_member(campaign, play_player_user, "Player")
        campaign_map = add_map(campaign, play_dm_user, "Brawl Socket Map")
        session = create_session(campaign, "Goblin Brawl Socket Session", status="in_progress", map_id=campaign_map.id)

        trap = _create_token(
            play_dm_client,
            campaign.id,
            session.id,
            {"name": "Schabernacks Trap", "x": 100, "y": 100, "token_type": "object"},
        )
        enemy = _create_token(
            play_player_client,
            campaign.id,
            session.id,
            {
                "name": "Socket Hero",
                "x": 400,
                "y": 100,
                "token_type": "player",
                "hp_current": 100,
                "hp_max": 100,
            },
        )

        monkeypatch.setattr("vtt.dice.random.randint", lambda _minimum, _maximum: 1)
        player_socket = socketio.test_client(play_player_client.application, flask_test_client=play_player_client)
        assert player_socket.is_connected()
        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        player_socket.get_received()

        player_socket.emit(
            "token:update",
            {
                "campaign_id": campaign.id,
                "session_id": session.id,
                "token_id": enemy["id"],
                "base_version": enemy["version"],
                "patch": {"x": 330},
                "client_event_id": "socket-trap-test",
            },
        )

        events = player_socket.get_received()
        trap_events = [event for event in events if event["name"] == "trap:triggered"]
        assert len(trap_events) == 1
        assert len(trap_events[0]["args"][0]["traps"][0]["volleys"]) == 5

        enemy_row = db.session.get(TokenState, enemy["id"])
        trap_row = db.session.get(TokenState, trap["id"])
        assert enemy_row.hp_current == 95
        assert enemy_row.metadata_json["conditions"] == ["poisoned"]
        assert trap_row.deleted_at is not None
        player_socket.disconnect()
