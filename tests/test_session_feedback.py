"""Authority, replay and persistence for the first-session feedback slice."""
import secrets
from uuid import uuid4
import pytest
from tests.play_shared import add_map, add_member, create_campaign, create_session, create_token
from tests.test_table_contexts import enter
from tests.test_personal_actions import personal, data
from vtt.extensions import db, socketio
from vtt.models import ChatMessage
from vtt.play.service import ensure_session_state

pytest_plugins = ["tests.play_shared"]


@pytest.fixture
def table(play_dm_user, play_player_user):
    campaign = create_campaign(play_dm_user, "Session feedback")
    member = add_member(campaign, play_player_user)
    map_ = add_map(campaign, play_dm_user)
    session = create_session(campaign, status="in_progress", map_id=map_.id)
    state = ensure_session_state(campaign, session)
    hero = create_token(campaign, session, state, play_player_user.id, "Hero")
    secret = create_token(campaign, session, state, play_dm_user.id, "Secret", token_type="npc")
    secret.visibility = "dm_only"
    secret.metadata_json = {"secret": "must not enter a template", "conditions": ["poisoned"]}
    secret.initiative = 13
    secret.hp_current, secret.hp_max = 1, 25
    db.session.commit()
    return campaign, session, member, hero, secret


def base(table):
    campaign, session, *_ = table
    return f"/api/play/campaigns/{campaign.id}/sessions/{session.id}"


def test_library_is_personal_mode_scoped_and_contains_no_runtime_state(table, play_dm_client, play_player_client):
    campaign, session, member, hero, secret = table
    dm = enter(play_dm_client, campaign, session, "dm")
    player = enter(play_player_client, campaign, session)
    endpoint = base(table) + "/token-library"
    result = play_dm_client.post(endpoint, headers=dm, json={"token_id": secret.id})
    assert result.status_code == 201, result.json
    saved = result.json["template"]
    assert saved["values"]["hp_max"] == 25
    assert saved["values"]["metadata_json"] == {}
    assert not {"hp_current", "initiative", "x", "visibility"} & saved["values"].keys()
    assert play_player_client.get(endpoint, headers=player).json["templates"] == []
    assert play_player_client.post(endpoint, headers=player, json={"token_id": secret.id}).status_code == 404
    owner_player = enter(play_dm_client, campaign, session)
    assert play_dm_client.get(endpoint, headers=owner_player).json["templates"] == []
    assert play_dm_client.patch(endpoint + f"/{saved['id']}", headers=owner_player,
                                json={"revision": 1, "name": "stolen"}).status_code == 404


def test_library_survives_map_switch_and_edit_delete_do_not_change_instance(table, play_player_client, play_dm_user):
    campaign, session, member, hero, secret = table
    auth = enter(play_player_client, campaign, session)
    endpoint = base(table) + "/token-library"
    saved = play_player_client.post(endpoint, headers=auth, json={"token_id": hero.id}).json["template"]
    assert play_player_client.patch(endpoint + f"/{saved['id']}", headers=auth,
                                   json={"revision": 1, "name": "Reusable Hero", "size": 2}).status_code == 200
    hero.session_state.active_map_id = add_map(campaign, play_dm_user, "Next map").id
    db.session.commit()
    assert play_player_client.get(endpoint, headers=auth).json["templates"][0]["name"] == "Reusable Hero"
    assert hero.name == "Hero" and hero.size == 1
    assert play_player_client.delete(endpoint + f"/{saved['id']}", headers=auth, json={"revision": 2}).status_code == 200
    assert hero.deleted_at is None


def test_initiative_accepts_own_token_and_receipt_prevents_second_roll(table, play_player_client):
    campaign, session, member, hero, secret = table
    auth = enter(play_player_client, campaign, session)
    endpoint = base(table) + f"/tokens/{hero.id}/initiative-roll"
    body = {"request_id": secrets.token_urlsafe(24)}
    first = play_player_client.post(endpoint, headers=auth, json=body)
    assert first.status_code == 200, first.json
    second = play_player_client.post(endpoint, headers=auth, json=body)
    assert second.json == first.json
    assert hero.initiative == first.json["total"]
    assert ChatMessage.query.filter_by(game_session_id=session.id).count() == 1
    assert play_player_client.post(base(table) + f"/tokens/{secret.id}/initiative-roll", headers=auth, json={}).status_code == 403
    assert secret.initiative == 13


def test_player_roll_updates_combat_without_rerolling_other_participants(table, play_player_client, play_dm_client):
    campaign, session, member, hero, secret = table
    player = enter(play_player_client, campaign, session)
    dm = enter(play_dm_client, campaign, session, "dm")
    hero.initiative = 19
    db.session.commit()
    combat_base = f"/api/campaigns/{campaign.id}/sessions/{session.id}/combat"
    started = play_dm_client.post(combat_base + "/start", headers=dm, json={"mode": "players"})
    assert started.status_code == 201, started.json
    assert hero.initiative == 19 and secret.initiative == 13
    current = started.json["encounter"]["active_token_id"]
    result = play_player_client.post(base(table) + f"/tokens/{hero.id}/initiative-roll", headers=player, json={})
    assert result.status_code == 200
    state = play_player_client.get(combat_base + "/state", headers=player)
    assert state.status_code == 200
    assert "Secret" not in state.get_data(as_text=True)
    from vtt.combat.service import get_active_encounter
    assert get_active_encounter(session.id).active_token_id == current
    assert secret.initiative == 13


def test_external_initiative_has_authorized_actor_and_is_applied_once(table, play_player_client, play_app):
    campaign, session, member, hero, secret = table
    auth = enter(play_player_client, campaign, session)
    client = socketio.test_client(play_app, flask_test_client=play_player_client)
    client.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id,
                "context_token": auth["X-VTT-Context"], "tab_id": auth["X-VTT-Tab"]})
    payload = {"campaign_id": campaign.id, "session_id": session.id, "client_event_id": str(uuid4()),
               "roll": {"source": "beyond20", "roll_type": "initiative", "title": "Initiative", "total": 18, "token_id": hero.id}}
    client.emit("external:roll", payload)
    client.emit("external:roll", payload)
    db.session.refresh(hero)
    assert hero.initiative == 18
    assert ChatMessage.query.filter_by(game_session_id=session.id).count() == 1
    payload["client_event_id"] = str(uuid4())
    payload["roll"]["token_id"] = secret.id
    client.emit("external:roll", payload)
    assert secret.initiative == 13
    assert ChatMessage.query.filter_by(game_session_id=session.id).count() == 1
    client.disconnect()


def test_campaign_room_is_shared_but_excludes_private_and_session_dice(table, play_dm_client, play_player_client):
    campaign, session, member, hero, secret = table
    endpoint = f"/api/campaign-rooms/{campaign.id}"
    body = {"content": "Across sessions", "client_event_id": str(uuid4())}
    first = play_player_client.post(endpoint, json=body)
    assert first.status_code == 201, first.json
    assert play_player_client.post(endpoint, json=body).json == first.json
    result = play_dm_client.get(endpoint)
    assert [m["content"] for m in result.json["messages"]] == ["Across sessions"]
    assert ChatMessage.query.count() == 0
    member.status = "removed"
    db.session.commit()
    assert play_player_client.get(endpoint).status_code == 404
    assert play_player_client.post(endpoint, json={**body, "client_event_id": str(uuid4())}).status_code == 404
    assert play_player_client.get("/api/campaign-rooms").json["rooms"] == []


def test_campaign_room_rejects_reused_id_with_different_content_and_bad_cursors(table, play_player_client):
    campaign, *_ = table
    endpoint = f"/api/campaign-rooms/{campaign.id}"
    body = {"content": "Hello", "client_event_id": str(uuid4())}
    assert play_player_client.post(endpoint, json=body).status_code == 201
    assert play_player_client.post(endpoint, json={**body, "content": "Changed"}).status_code == 409
    assert play_player_client.get(endpoint + "?after=oops").status_code == 400


def test_personal_sheet_initiative_updates_linked_token_once(personal, play_player_client):
    campaign, session, char, token, endpoint, auth = personal
    catalog = play_player_client.get(endpoint + "/hotbar").json["catalog"]
    body = {"request_id": secrets.token_urlsafe(24), "catalog_revision": catalog["revision"], "action_id": "initiative:"}
    first = play_player_client.post(endpoint + "/actions/execute", json=body)
    assert first.status_code == 200, first.json
    assert token.initiative == first.json["result"]["total"]
    second = play_player_client.post(endpoint + "/actions/execute", json=body)
    assert second.json == first.json
    assert ChatMessage.query.filter_by(game_session_id=session.id).count() == 1


@pytest.mark.parametrize("payload", [[1], "invalid", 4])
def test_feedback_http_endpoints_reject_non_object_bodies(table, play_player_client, payload):
    campaign, session, *_ = table
    auth = enter(play_player_client, campaign, session)
    assert play_player_client.post(base(table) + "/token-library", headers=auth, json=payload).status_code == 400
    assert play_player_client.post(f"/api/campaign-rooms/{campaign.id}", headers=auth, json=payload).status_code == 400


def test_saved_character_binding_reuses_figure_on_another_map_but_not_twice_on_one_map(personal, play_player_client, play_dm_user):
    campaign, session, char, original, endpoint, auth = personal
    library = f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/token-library"
    saved = play_player_client.post(library, json={"token_id": original.id})
    assert saved.status_code == 201 and saved.json["template"]["values"]["character_id"] == char.id
    second = add_map(campaign, play_dm_user, "Second map")
    original.session_state.active_map_id = second.id
    db.session.commit()
    from vtt.characters import sheet_link
    assert any(c["id"] == char.id for c in sheet_link.linkable_characters(campaign, original.owner, False, session.id))
    url = f"/api/campaigns/{campaign.id}/sessions/{session.id}/tokens"
    body = {"name": "Linked on new map", "token_type": "player", "x": 140, "y": 140, "character_id": char.id}
    result = play_player_client.post(url, json=body)
    assert result.status_code == 201, result.json
    assert result.json["token"]["character_id"] == char.id and result.json["token"]["map_id"] == second.id
    assert original.map_id != second.id and original.character_id == char.id
    assert play_player_client.post(url, json=body).status_code == 400
