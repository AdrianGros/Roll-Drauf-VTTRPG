"""P11: campaign assignment rules, party view, group awards, share links and DM handouts of SRD characters."""

import pytest

from vtt.extensions import db
from vtt.models import Character, GameSession, TokenState

from tests.test_srd_creator_api import BASE, _client, app, client, data, finalized, make_draft, other, wizard_state  # noqa: F401
from tests.test_srd_rolls import _tokens, table  # noqa: F401


def party_url(t):
    return f"{BASE}/campaigns/{t['campaign']}/party"


def rules_url(t):
    return f"{BASE}/campaigns/{t['campaign']}/rules"


def only_mira(rows):
    return next(r for r in rows if r["name"] == "Mira Eulenfeder")


# ------------------------------------------------------------------ party view

def test_party_is_visible_to_members_only_and_shows_values(app, client, other, data):
    t = table(app, client, other, data)
    stranger = _client(app, "srd_stranger")
    assert stranger.get(party_url(t)).status_code == 404
    body = client.get(party_url(t)).get_json()
    assert body["campaign"]["name"] == "Rolltisch" and body["isDm"] is False
    mira = only_mira(body["characters"])
    assert mira["level"] == 5 and mira["hpMax"] == mira["hpCurrent"] == 32 and mira["srd"] is True
    assert mira["ac"] == 11 and mira["passivePerception"] >= 10 and mira["speedMeters"] > 0
    assert mira["abilities"]["int"] >= 15 and mira["spellSaveDc"] is not None
    assert "progress" not in mira and mira["owner"] == "srd_owner"
    assert other.get(party_url(t)).get_json()["characters"] == body["characters"]
    dm = t["dm"].get(party_url(t)).get_json()
    assert dm["isDm"] is True
    progress = only_mira(dm["characters"])["progress"]
    assert progress["mode"] and "xp" in progress and "canLevelUp" in progress
    assert client.get(f"{BASE}/campaigns/99999/party").status_code == 404


def test_party_shows_conditions_of_live_tokens_and_skips_archived(app, client, other, data):
    t = table(app, client, other, data)
    from tests.play_shared import enter_table
    from vtt.models import Campaign, GameSession
    enter_table(client, db.session.get(Campaign, t['campaign']), db.session.get(GameSession, t['session']))
    token = client.post(_tokens(t), json={"name": "Mira", "x": 1, "y": 1, "character_id": t["char"]["id"]}).get_json()["token"]
    row = db.session.get(TokenState, token["id"])
    row.metadata_json = {**(row.metadata_json or {}), "conditions": ["poisoned", "frightened", "unbekannt", 7]}
    db.session.commit()
    mira = only_mira(client.get(party_url(t)).get_json()["characters"])
    assert [c["id"] for c in mira["conditions"]] == ["poisoned", "frightened"]
    assert all(c["label"] for c in mira["conditions"])
    db.session.get(GameSession, t["session"]).status = "completed"
    db.session.commit()
    assert only_mira(client.get(party_url(t)).get_json()["characters"])["conditions"] == []
    char = db.session.get(Character, t["char"]["id"])
    char.character_data = {**char.character_data, "lifecycle": {"archivedAt": "2026-10-18T10:00:00Z"}}
    db.session.commit()
    assert client.get(party_url(t)).get_json()["characters"] == []


def test_plain_characters_appear_with_basic_values(app, client, other, data):
    t = table(app, client, other, data)
    plain = other.post("/api/characters", json={"name": "Schlicht", "level": 2}).get_json()
    assert other.put(f"/api/characters/{plain['id']}/campaign", json={"campaign_id": t["campaign"]}).status_code == 200
    rows = client.get(party_url(t)).get_json()["characters"]
    schlicht = next(r for r in rows if r["name"] == "Schlicht")
    assert schlicht["srd"] is False and "abilities" not in schlicht and "progress" not in schlicht


# ------------------------------------------------------------------ campaign rules

def test_campaign_rules_are_dm_only_and_validated(app, client, other, data):
    t = table(app, client, other, data)
    default = client.get(rules_url(t)).get_json()
    assert default["attributeMethods"] == ["standard-array", "point-buy", "roll", "manual"] and default["canEdit"] is False
    assert client.put(rules_url(t), json={"attributeMethods": ["manual"]}).status_code == 403
    assert t["dm"].put(rules_url(t), json={"attributeMethods": []}).status_code == 400
    assert t["dm"].put(rules_url(t), json={"attributeMethods": ["magie"]}).status_code == 400
    assert t["dm"].put(rules_url(t), json={"attributeMethods": "manual"}).status_code == 400
    saved = t["dm"].put(rules_url(t), json={"attributeMethods": ["point-buy", "standard-array", "point-buy"]})
    assert saved.status_code == 200 and saved.get_json()["attributeMethods"] == ["standard-array", "point-buy"]
    assert saved.get_json()["canEdit"] is True
    assert client.get(rules_url(t)).get_json()["attributeMethods"] == ["standard-array", "point-buy"]
    assert client.get(party_url(t)).get_json()["rules"]["attributeMethods"] == ["standard-array", "point-buy"]
    assert _client(app, "srd_stranger").get(rules_url(t)).status_code == 404


def test_rules_are_enforced_when_assigning_and_finalizing(app, client, other, data):
    t = table(app, client, other, data)
    assert t["dm"].put(rules_url(t), json={"attributeMethods": ["point-buy"]}).status_code == 200
    # Mira (manual) is already inside; a second manual character may not join now
    second = finalized(other, data, name="Bram Zweig")
    refused = other.put(f"/api/characters/{second['id']}/campaign", json={"campaign_id": t["campaign"]})
    assert refused.status_code == 422
    assert refused.get_json()["code"] == "ability_method_not_allowed" and "Punktekauf" in refused.get_json()["error"]
    assert db.session.get(Character, second["id"]).campaign_id is None

    draft = make_draft(other, wizard_state(data, "Cora Neu"))["draft"]
    blocked = other.post(f"{BASE}/drafts/{draft['id']}/finalize", json={"version": 1, "campaign_id": t["campaign"]})
    assert blocked.status_code == 422
    assert blocked.get_json()["error"] == "ability_method_not_allowed" and blocked.get_json()["allowed"] == ["point-buy"]
    assert t["dm"].put(rules_url(t), json={"attributeMethods": ["manual", "point-buy"]}).status_code == 200
    ok = other.post(f"{BASE}/drafts/{draft['id']}/finalize", json={"version": 1, "campaign_id": t["campaign"]})
    assert ok.status_code == 201
    assert other.put(f"/api/characters/{second['id']}/campaign", json={"campaign_id": t["campaign"]}).status_code == 200


# ------------------------------------------------------------------ group award

def test_dm_awards_experience_to_the_whole_party_or_a_selection(app, client, other, data):
    t = table(app, client, other, data)
    second = finalized(other, data, name="Bram Zweig")
    assert other.put(f"/api/characters/{second['id']}/campaign", json={"campaign_id": t["campaign"]}).status_code == 200
    url = f"{BASE}/campaigns/{t['campaign']}/award"
    assert client.post(url, json={"addXp": 100}).status_code == 403
    for bad in ({}, {"addXp": 0}, {"addXp": -5}, {"addXp": 1.5}, {"addXp": True}, {"addXp": 10**7}, {"addXp": "9"},
                {"addXp": 10, "characterIds": "all"}, {"addXp": 10, "characterIds": [1.5]}):
        assert t["dm"].post(url, json=bad).status_code == 400, bad
    before = {c.id: c.xp for c in Character.query.filter(Character.campaign_id == t["campaign"]).all()}
    chosen = t["dm"].post(url, json={"addXp": 250, "characterIds": [second["id"]], "note": "Brückenkampf"})
    assert chosen.status_code == 200, chosen.get_json()
    assert chosen.get_json()["changed"] == [second["id"]]
    db.session.expire_all()
    assert db.session.get(Character, second["id"]).xp == before[second["id"]] + 250
    assert db.session.get(Character, t["char"]["id"]).xp == before[t["char"]["id"]]
    everyone = t["dm"].post(url, json={"addXp": 100})
    assert sorted(everyone.get_json()["changed"]) == sorted([second["id"], t["char"]["id"]])
    db.session.expire_all()
    assert db.session.get(Character, t["char"]["id"]).xp == before[t["char"]["id"]] + 100
    history = db.session.get(Character, second["id"]).character_data["srd"]["history"]
    assert history[-2]["by"] == t["dm"].user_id and history[-2].get("note") == "Brückenkampf" and "note" not in history[-1]
    assert only_mira(everyone.get_json()["characters"])["progress"]["xp"] == before[t["char"]["id"]] + 100


# ------------------------------------------------------------------ share link

def sharing_url(char):
    return f"{BASE}/characters/{char['id']}/sharing"


def test_share_link_lifecycle_and_public_view(client, other, data):
    char = finalized(client, data)
    assert client.get(sharing_url(char)).get_json() == {"enabled": False, "token": None}
    assert other.get(sharing_url(char)).status_code == 403
    assert other.put(sharing_url(char), json={"enabled": True}).status_code == 403
    assert client.put(sharing_url(char), json={"enabled": "ja"}).status_code == 400
    anonymous = client.application.test_client()
    on = client.put(sharing_url(char), json={"enabled": True}).get_json()
    assert on["enabled"] and on["token"].startswith(f"{char['id']}-") and len(on["token"]) > 20
    assert client.put(sharing_url(char), json={"enabled": True}).get_json()["token"] == on["token"]
    view = anonymous.get(f"{BASE}/shared/{on['token']}")
    assert view.status_code == 200
    assert view.headers["Cache-Control"] == "no-store" and "noindex" in view.headers["X-Robots-Tag"]
    assert view.headers["Referrer-Policy"] == "no-referrer"
    body = view.get_json()
    assert body["name"] == "Mira Eulenfeder" and body["level"] == 5 and body["hitPoints"]["max"] == 32 and body["armorClass"] == 11
    assert body["abilities"]["int"]["score"] >= 15 and body["spells"] and body["classes"][0]["level"] == 5
    flat = str(body)
    for secret in ("backstory", "Fand eine Eule", "srd_owner", on["token"], "user_id", "notes"):
        assert secret not in flat
    assert "id" not in body

    again = client.put(sharing_url(char), json={"enabled": True, "regenerate": True}).get_json()
    assert again["token"] != on["token"]
    assert anonymous.get(f"{BASE}/shared/{on['token']}").status_code == 404
    assert anonymous.get(f"{BASE}/shared/{again['token']}").status_code == 200

    off = client.put(sharing_url(char), json={"enabled": False}).get_json()
    assert off == {"enabled": False, "token": None}
    assert anonymous.get(f"{BASE}/shared/{again['token']}").status_code == 404


def test_share_tokens_reject_garbage_and_hidden_characters(client, data):
    char = finalized(client, data)
    anonymous = client.application.test_client()
    token = client.put(sharing_url(char), json={"enabled": True}).get_json()["token"]
    ident = token.split("-", 1)[0]
    for bad in (f"{ident}-", f"{ident}-falsch", "x-abc", f"{ident}", "0-0", f"99999-{token.split('-', 1)[1]}", "-" * 5, ident + "-" + "a" * 200):
        assert anonymous.get(f"{BASE}/shared/{bad}").status_code == 404, bad
    client.post(f"{BASE}/characters/{char['id']}/archive", json={"archived": True})
    assert anonymous.get(f"{BASE}/shared/{token}").status_code == 404
    client.post(f"{BASE}/characters/{char['id']}/archive", json={"archived": False})
    assert anonymous.get(f"{BASE}/shared/{token}").status_code == 404
    assert client.get(sharing_url(char)).get_json()["enabled"] is False
    token = client.put(sharing_url(char), json={"enabled": True}).get_json()["token"]
    assert anonymous.get(f"{BASE}/shared/{token}").status_code == 200
    assert client.delete(f"/api/characters/{char['id']}").status_code == 200
    assert anonymous.get(f"{BASE}/shared/{token}").status_code == 404


def test_sharing_needs_an_srd_character_and_survives_a_copy_only_as_off(client, data):
    plain = client.post("/api/characters", json={"name": "Plain"}).get_json()
    assert client.put(sharing_url(plain), json={"enabled": True}).status_code == 422
    char = finalized(client, data)
    client.put(sharing_url(char), json={"enabled": True})
    copy = client.post(f"{BASE}/characters/{char['id']}/duplicate").get_json()["character"]
    assert client.get(sharing_url(copy)).get_json()["enabled"] is False


# ------------------------------------------------------------------ handouts

def handout(t, **body):
    return t["dm"].post(f"{BASE}/characters/{t['char']['id']}/handout", json=body)


def test_dm_hands_out_gear_magic_items_and_coins(app, client, other, data):
    t = table(app, client, other, data)
    gear = t["dm"].get(f"{BASE}/handout/items?kind=gear&q=seil").get_json()["items"]
    assert gear and all("seil" in item["name"].casefold() for item in gear)
    magic = t["dm"].get(f"{BASE}/handout/items?kind=magic&q=").get_json()["items"]
    assert magic and len(magic) <= 30
    assert t["dm"].get(f"{BASE}/handout/items?kind=quatsch").status_code == 422

    assert client.post(f"{BASE}/characters/{t['char']['id']}/handout", json={"kind": "gear", "itemId": gear[0]["id"]}).status_code == 403
    assert other.post(f"{BASE}/characters/{t['char']['id']}/handout", json={"kind": "gear", "itemId": gear[0]["id"]}).status_code == 403

    given = handout(t, kind="gear", itemId=gear[0]["id"], quantity=2)
    assert given.status_code == 200, given.get_json()
    rows = [i for i in given.get_json()["items"] if i["handedOut"]]
    assert rows and rows[0]["quantity"] == 2

    wanted = next(m for m in magic if m["name"])
    item = handout(t, kind="magic", itemId=wanted["id"])
    assert item.status_code == 200, item.get_json()
    magic_row = next(i for i in item.get_json()["items"] if i["handedOut"] and i["name"] == wanted["name"])
    assert magic_row["source"] == "SRD 5.2.1 (CC BY 4.0)" and magic_row["rarity"] and magic_row["description"]

    coins = handout(t, coins={"GM": 50})
    assert coins.status_code == 200 and coins.get_json()["coins"]["GM"] >= 50
    assert handout(t, coins={}).status_code == 422
    assert handout(t, kind="magic", itemId="gibt-es-nicht").status_code == 404
    assert handout(t, kind="gear", itemId="gibt-es-nicht").status_code in (404, 422)
    assert handout(t, kind="waffe", itemId="x").status_code == 422

    history = db.session.get(Character, t["char"]["id"]).character_data["srd"]["history"]
    assert [h["type"] for h in history if h["type"] == "handout"] == ["handout"] * 3
    assert history[-1]["by"] == t["dm"].user_id
    assert client.get(f"{BASE}/characters/{t['char']['id']}/inventory").get_json()["items"]


def test_dm_can_only_take_back_what_was_handed_out(app, client, other, data):
    t = table(app, client, other, data)
    base = f"{BASE}/characters/{t['char']['id']}"
    own = client.post(f"{base}/inventory", json={"itemId": t["dm"].get(f"{BASE}/handout/items?kind=gear&q=seil").get_json()["items"][0]["id"], "quantity": 1})
    assert own.status_code in (200, 201), own.get_json()
    own_id = next(i for i in own.get_json()["items"] if not i["handedOut"] and "seil" in i["name"].casefold())["id"]
    assert t["dm"].delete(f"{base}/handout/{own_id}").status_code == 409

    given = handout(t, kind="gear", itemId=t["dm"].get(f"{BASE}/handout/items?kind=gear&q=fackel").get_json()["items"][0]["id"])
    given_id = next(i for i in given.get_json()["items"] if i["handedOut"])["id"]
    assert client.delete(f"{base}/handout/{given_id}").status_code == 403
    gone = t["dm"].delete(f"{base}/handout/{given_id}")
    assert gone.status_code == 200 and all(i["id"] != given_id for i in gone.get_json()["items"])
    assert t["dm"].delete(f"{base}/handout/{given_id}").status_code == 404
    history = db.session.get(Character, t["char"]["id"]).character_data["srd"]["history"]
    assert history[-1]["type"] == "take-back"


def test_handouts_need_a_campaign_and_an_srd_character(app, client, other, data):
    char = finalized(client, data)
    assert client.post(f"{BASE}/characters/{char['id']}/handout", json={"coins": {"GM": 1}}).status_code == 403
    t = table(app, client, other, data)
    plain = other.post("/api/characters", json={"name": "Schlicht"}).get_json()
    assert other.put(f"/api/characters/{plain['id']}/campaign", json={"campaign_id": t["campaign"]}).status_code == 200
    assert t["dm"].post(f"{BASE}/characters/{plain['id']}/handout", json={"coins": {"GM": 1}}).status_code == 422
