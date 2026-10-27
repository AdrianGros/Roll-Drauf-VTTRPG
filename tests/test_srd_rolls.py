"""P6: rolls from the SRD sheet land in the table log; characters stay linked to their tokens."""

from datetime import datetime

from vtt.extensions import db, socketio
from vtt.models import Campaign, CampaignMap, CampaignMember, Character, ChatMessage, GameSession, TokenState

from tests.test_srd_creator_api import BASE, _client, app, client, data, finalized, other  # noqa: F401


def _member(campaign, user_id, role):
    db.session.add(CampaignMember(
        campaign_id=campaign.id, user_id=user_id, campaign_role=role, status="active",
        joined_at=datetime.utcnow(), invited_at=datetime.utcnow(), accepted_at=datetime.utcnow(),
        invited_by=campaign.owner_id))


def table(app, client, other, data, status="in_progress"):
    """A campaign (DM = `dm`, player = `client`, second player = `other`) with a running session and Mira in it."""
    dm = _client(app, "srd_dm")
    char = finalized(client, data)
    campaign = Campaign(name="Rolltisch", description="", owner_id=dm.user_id, status="active", max_players=6)
    db.session.add(campaign)
    db.session.flush()
    _member(campaign, dm.user_id, "DM")
    _member(campaign, client.user_id, "Player")
    _member(campaign, other.user_id, "Player")
    campaign_map = CampaignMap(campaign_id=campaign.id, name="Karte", width=20, height=20, created_by=dm.user_id)
    db.session.add(campaign_map)
    db.session.flush()
    session = GameSession(campaign_id=campaign.id, map_id=campaign_map.id, name="Abend", status=status)
    db.session.add(session)
    db.session.get(Character, char["id"]).campaign_id = campaign.id
    db.session.commit()
    return {"dm": dm, "char": char, "campaign": campaign.id, "session": session.id}


def roll(client, char_id, **body):
    return client.post(f"{BASE}/characters/{char_id}/roll", json=body)


def test_modifiers_come_from_the_evaluated_sheet(client, data):
    char = finalized(client, data)
    arkane = roll(client, char["id"], kind="skill", key="arkane-kunde").get_json()
    assert arkane["label"] == "Arkane Kunde" and arkane["dice"] == "1d20+10"
    assert arkane["result"]["total"] == arkane["result"]["rolls"][0] + 10
    assert roll(client, char["id"], kind="ability", key="int").get_json()["dice"] == "1d20+4"
    assert roll(client, char["id"], kind="save", key="int").get_json()["dice"] == "1d20+7"
    assert roll(client, char["id"], kind="initiative").get_json()["dice"] == "1d20+1"
    assert roll(client, char["id"], kind="death_save").get_json()["dice"] == "1d20"
    spell = roll(client, char["id"], kind="spell_attack", key="wizard").get_json()
    assert spell["dice"] == "1d20+7" and spell["label"].startswith("Zauberangriff")
    assert not spell["logged"]


def test_advantage_and_disadvantage_keep_the_right_die(client, data):
    char = finalized(client, data)
    for _ in range(25):
        high = roll(client, char["id"], kind="ability", key="str", mode="advantage").get_json()["result"]
        low = roll(client, char["id"], kind="ability", key="str", mode="disadvantage").get_json()["result"]
        assert high["rolls"][0] >= high["discarded_rolls"][0]
        assert low["rolls"][0] <= low["discarded_rolls"][0]
        assert 1 <= high["natural"] <= 20 and high["total"] == high["natural"] - 1
    assert "discarded_rolls" not in roll(client, char["id"], kind="ability", key="str").get_json()["result"]


def test_invalid_and_forbidden_rolls(client, other, data):
    char = finalized(client, data)
    assert roll(client, char["id"], kind="skill", key="gibt-es-nicht").status_code == 422
    assert roll(client, char["id"], kind="blitz").status_code == 422
    assert roll(client, char["id"], kind="spell_attack", key="cleric").status_code == 422
    assert roll(other, char["id"], kind="initiative").status_code == 403
    assert roll(client, 99999, kind="initiative").status_code == 404
    plain = client.post("/api/characters", json={"name": "Alt"}).get_json()
    assert roll(client, plain["id"], kind="initiative").status_code == 422


def test_rolls_are_logged_to_the_running_session(app, client, other, data):
    t = table(app, client, other, data)
    body = roll(client, t["char"]["id"], kind="skill", key="arkane-kunde", mode="advantage").get_json()
    assert body["logged"] and body["messageId"]
    message = db.session.get(ChatMessage, body["messageId"])
    assert message.game_session_id == t["session"] and message.content_type == "dice_roll"
    assert message.content.startswith("Mira Eulenfeder · Arkane Kunde (Vorteil): würfelt 1d20+10: ")
    assert message.content.endswith(f"= {body['result']['total']}")
    assert message.visibility == "public"
    assert db.session.get(ChatMessage, roll(t["dm"], t["char"]["id"], kind="initiative").get_json()["messageId"])
    # players cannot make blind rolls
    secret = roll(client, t["char"]["id"], kind="initiative", visibility="blind").get_json()
    assert db.session.get(ChatMessage, secret["messageId"]).visibility == "public"


def test_rolls_are_not_logged_without_a_running_session(app, client, other, data):
    t = table(app, client, other, data, status="scheduled")
    body = roll(client, t["char"]["id"], kind="initiative").get_json()
    assert body["logged"] is False and body["messageId"] is None
    assert ChatMessage.query.count() == 0


def _session(campaign_id, name, status="in_progress"):
    session = GameSession(campaign_id=campaign_id, name=name, status=status)
    db.session.add(session)
    db.session.commit()
    return session.id


def _context(client, char_id, session_id=None):
    query = "" if session_id is None else f"?session_id={session_id}"
    return client.get(f"{BASE}/characters/{char_id}/roll-context{query}")


def test_an_explicit_table_gets_the_roll_while_several_run(app, client, other, data):
    t = table(app, client, other, data)
    second = _session(t["campaign"], "Zweiter Tisch")
    first = roll(client, t["char"]["id"], kind="skill", key="arkane-kunde", sessionId=t["session"]).get_json()
    assert first["logged"] and first["session"] == {"id": t["session"], "name": "Abend"}
    assert db.session.get(ChatMessage, first["messageId"]).game_session_id == t["session"]
    # the sheet sends the id it read from its URL, as text
    there = roll(client, t["char"]["id"], kind="initiative", sessionId=str(second)).get_json()
    assert db.session.get(ChatMessage, there["messageId"]).game_session_id == second
    assert ChatMessage.query.count() == 2


def test_several_running_tables_need_a_choice_before_anything_is_rolled(app, client, other, data):
    t = table(app, client, other, data)
    second = _session(t["campaign"], "Zweiter Tisch")
    refused = roll(client, t["char"]["id"], kind="initiative")
    assert refused.status_code == 409
    body = refused.get_json()
    assert body["error"] == "session_required" and "nicht gewürfelt" in body["message"] and "result" not in body
    assert {s["id"] for s in body["sessions"]} == {t["session"], second}
    context = _context(client, t["char"]["id"]).get_json()
    assert context["live"] is False and context["reason"] == "choose_session" and context["session"] is None
    assert [s["id"] for s in context["sessions"]] == [second, t["session"]]
    assert ChatMessage.query.count() == 0


def test_wrong_or_finished_tables_refuse_the_roll_and_never_redirect_it(app, client, other, data):
    t = table(app, client, other, data)  # "Abend" keeps running: a fallback the server must not use
    ended = _session(t["campaign"], "Gestern", status="ended")
    paused = _session(t["campaign"], "Pause", status="paused")
    stranger = Campaign(name="Fremd", description="", owner_id=other.user_id, status="active", max_players=6)
    db.session.add(stranger)
    db.session.flush()
    foreign = _session(stranger.id, "Fremder Tisch")
    for session_id, status, code in (
        (ended, 409, "session_not_live"),
        (paused, 409, "session_not_live"),
        (foreign, 409, "session_mismatch"),
        (99999, 409, "session_mismatch"),
        ("abc", 400, "invalid_session"),
        (0, 400, "invalid_session"),
        (-3, 400, "invalid_session"),
        (True, 400, "invalid_session"),
        (1.5, 400, "invalid_session"),
    ):
        resp = roll(client, t["char"]["id"], kind="initiative", sessionId=session_id)
        assert resp.status_code == status, (session_id, resp.get_json())
        assert resp.get_json()["error"] == code and "result" not in resp.get_json()
    assert "beendet" in roll(client, t["char"]["id"], kind="initiative", sessionId=ended).get_json()["message"]
    assert ChatMessage.query.count() == 0
    # the sheet's destination check gives the same answers
    assert _context(client, t["char"]["id"], ended).get_json()["error"] == "session_not_live"
    assert _context(client, t["char"]["id"], foreign).get_json()["error"] == "session_mismatch"
    assert _context(client, t["char"]["id"], "x").status_code == 400
    # a character without a campaign cannot name a table either
    loose = finalized(client, data, name="Ohne Kampagne")
    assert roll(client, loose["id"], kind="initiative", sessionId=t["session"]).get_json()["error"] == "session_mismatch"
    alone = _context(client, loose["id"]).get_json()
    assert alone["live"] is False and alone["reason"] == "no_campaign" and alone["sessions"] == []
    assert ChatMessage.query.count() == 0


def test_only_the_owner_or_dm_roll_and_only_at_tables_they_play_at(app, client, other, data):
    t = table(app, client, other, data)
    stolen = roll(other, t["char"]["id"], kind="initiative", sessionId=t["session"])
    assert stolen.status_code == 403
    assert _context(other, t["char"]["id"], t["session"]).status_code == 403
    by_dm = roll(t["dm"], t["char"]["id"], kind="initiative", sessionId=t["session"]).get_json()
    assert db.session.get(ChatMessage, by_dm["messageId"]).game_session_id == t["session"]

    member = CampaignMember.query.filter_by(campaign_id=t["campaign"], user_id=client.user_id).first()
    member.campaign_role = "Observer"
    db.session.commit()
    watching = roll(client, t["char"]["id"], kind="initiative", sessionId=t["session"])
    assert watching.status_code == 403 and watching.get_json()["error"] == "session_forbidden"
    local = roll(client, t["char"]["id"], kind="initiative").get_json()
    assert local["logged"] is False and local["reason"] == "no_session" and local["session"] is None

    member.campaign_role, member.status = "Player", "removed"
    db.session.commit()
    gone = roll(client, t["char"]["id"], kind="initiative", sessionId=t["session"])
    assert gone.status_code == 403 and gone.get_json()["error"] == "session_forbidden"
    assert ChatMessage.query.count() == 1


def test_roll_context_names_the_destination_before_the_roll(app, client, other, data):
    t = table(app, client, other, data)
    implicit = _context(client, t["char"]["id"])
    assert implicit.status_code == 200 and "no-store" in implicit.headers["Cache-Control"]
    body = implicit.get_json()
    assert body["live"] is True and body["explicit"] is False and body["reason"] is None
    assert body["session"] == {"id": t["session"], "name": "Abend"} and body["campaignId"] == t["campaign"]
    bound = _context(client, t["char"]["id"], t["session"]).get_json()
    assert bound["live"] and bound["explicit"] and bound["sessions"] == [{"id": t["session"], "name": "Abend"}]
    db.session.get(GameSession, t["session"]).status = "completed"
    db.session.commit()
    assert _context(client, t["char"]["id"]).get_json()["reason"] == "no_session"
    assert _context(client, t["char"]["id"], t["session"]).status_code == 409
    assert ChatMessage.query.count() == 0


def _tokens(t):
    return f"/api/campaigns/{t['campaign']}/sessions/{t['session']}/tokens"


def test_linking_a_token_copies_hit_points_and_sheet_values(app, client, other, data):
    t = table(app, client, other, data)
    created = client.post(_tokens(t), json={"name": "Mira", "x": 1, "y": 1, "character_id": t["char"]["id"]})
    assert created.status_code == 201, created.get_json()
    token = created.get_json()["token"]
    assert token["hp_current"] == token["hp_max"] == 32
    sheet = token["metadata_json"]["sheet"]
    assert sheet["ac"] == 11 and sheet["level"] == 5 and sheet["initiative"] == 1
    assert sheet["proficiencyBonus"] == 3 and sheet["passivePerception"] >= 10
    again = client.post(_tokens(t), json={"name": "Zwilling", "x": 2, "y": 2, "character_id": t["char"]["id"]})
    assert again.status_code == 400 and "bereits" in again.get_json()["error"]


def test_only_owner_or_dm_may_link_and_the_campaign_must_match(app, client, other, data):
    t = table(app, client, other, data)
    stolen = other.post(_tokens(t), json={"name": "Dieb", "x": 0, "y": 0, "character_id": t["char"]["id"]})
    assert stolen.status_code == 400
    assert t["dm"].post(_tokens(t), json={"name": "SL", "x": 0, "y": 0, "token_type": "npc", "character_id": t["char"]["id"]}).status_code == 201
    stray = other.post("/api/characters", json={"name": "Streuner"}).get_json()
    assert t["dm"].post(_tokens(t), json={"name": "Fremd", "x": 0, "y": 0, "token_type": "npc", "character_id": stray["id"]}).status_code == 400
    assert t["dm"].post(_tokens(t), json={"name": "Nix", "x": 0, "y": 0, "token_type": "npc", "character_id": 99999}).status_code == 400


def test_hit_points_flow_both_ways(app, client, other, data):
    t = table(app, client, other, data)
    token = client.post(_tokens(t), json={"name": "Mira", "x": 1, "y": 1, "character_id": t["char"]["id"]}).get_json()["token"]
    hurt = client.put(f"{_tokens(t)}/{token['id']}", json={"base_version": token["version"], "patch": {"hp_current": 12, "hp_max": 999}})
    assert hurt.status_code == 200, hurt.get_json()
    updated = hurt.get_json()["token"]
    assert updated["hp_current"] == 12 and updated["hp_max"] == 32
    assert db.session.get(Character, t["char"]["id"]).hp_current == 12
    over = client.put(f"{_tokens(t)}/{token['id']}", json={"base_version": updated["version"], "patch": {"hp_current": 500}})
    assert over.get_json()["token"]["hp_current"] == 32
    assert db.session.get(Character, t["char"]["id"]).hp_current == 32

    assert client.put(f"/api/characters/{t['char']['id']}", json={"hp_current": 5}).status_code == 200
    db.session.expire_all()
    live = db.session.get(TokenState, token["id"])
    assert live.hp_current == 5 and live.version == over.get_json()["token"]["version"] + 1


def test_character_changes_do_not_touch_closed_sessions(app, client, other, data):
    t = table(app, client, other, data)
    token = client.post(_tokens(t), json={"name": "Mira", "x": 1, "y": 1, "character_id": t["char"]["id"]}).get_json()["token"]
    db.session.get(GameSession, t["session"]).status = "completed"
    db.session.commit()
    assert client.put(f"/api/characters/{t['char']['id']}", json={"hp_current": 7}).status_code == 200
    db.session.expire_all()
    assert db.session.get(TokenState, token["id"]).hp_current == 32


def test_socket_create_and_update_link_the_same_way(app, client, other, data):
    t = table(app, client, other, data)
    sock = socketio.test_client(app, flask_test_client=client)
    assert sock.is_connected()
    sock.emit("session:join", {"campaign_id": t["campaign"], "session_id": t["session"]})
    sock.get_received()
    sock.emit("token:create", {"campaign_id": t["campaign"], "session_id": t["session"], "client_event_id": "c1",
                               "token": {"name": "Mira", "x": 1, "y": 1, "character_id": t["char"]["id"]}})
    created = [e for e in sock.get_received() if e["name"] == "token:created"]
    assert created, "token was not created"
    token = created[0]["args"][0]["token"]
    assert token["character_id"] == t["char"]["id"] and token["hp_max"] == 32
    assert token["metadata_json"]["sheet"]["level"] == 5

    sock.emit("token:create", {"campaign_id": t["campaign"], "session_id": t["session"], "client_event_id": "c2",
                               "token": {"name": "Doppelt", "x": 2, "y": 1, "character_id": t["char"]["id"]}})
    events = sock.get_received()
    assert any(e["name"] == "state:error" for e in events) and not any(e["name"] == "token:created" for e in events)

    sock.emit("token:update", {"campaign_id": t["campaign"], "session_id": t["session"], "token_id": token["id"],
                               "client_event_id": "u1", "base_version": token["version"], "patch": {"hp_current": 9}})
    assert any(e["name"] == "token:updated" for e in sock.get_received())
    assert db.session.get(Character, t["char"]["id"]).hp_current == 9
    sock.disconnect()
