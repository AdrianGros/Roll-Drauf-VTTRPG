"""Charakter-Makroleiste: personal hotbar slots over the sheet's own rolls."""

from vtt.extensions import db
from vtt.models import ChatMessage, TableMacroBar

from tests.test_srd_creator_api import BASE, _client, app, client, data, finalized, other  # noqa: F401
from tests.test_srd_rolls import table


def _macros(client, char_id):
    return client.get(f"{BASE}/characters/{char_id}/macros")


def _save(client, char_id, slots):
    return client.put(f"{BASE}/characters/{char_id}/macros", json={"slots": slots})


def test_options_list_every_sheet_roll(client, data):
    char = finalized(client, data)

    body = _macros(client, char["id"]).get_json()

    assert body["slots"] == [] and body["limit"] == 10 and body["reason"] is None
    labels = {(option["kind"], option["key"]): option["label"] for option in body["options"]}
    assert labels[("initiative", None)] == "Initiative"
    assert labels[("skill", "arkane-kunde")] == "Arkane Kunde"
    assert labels[("save", "int")] == "Intelligenz-Rettungswurf"
    assert labels[("ability", "str")] == "Stärke-Probe"
    assert labels[("spell_attack", "wizard")].startswith("Zauberangriff")
    assert labels[("weapon_attack", "unarmed")] == "Angriff: Waffenloser Schlag"
    assert ("weapon_damage", "unarmed") in labels
    assert {option["group"] for option in body["options"]} == {"Kampf", "Proben", "Rettungswürfe", "Fertigkeiten"}


def test_slots_are_saved_in_order_without_duplicates_and_reloaded(client, data):
    char = finalized(client, data)
    slots = [{"kind": "skill", "key": "arkane-kunde"}, {"kind": "initiative", "key": None},
             {"kind": "skill", "key": "arkane-kunde"}]

    saved = _save(client, char["id"], slots)

    assert saved.status_code == 200, saved.get_json()
    assert [slot["label"] for slot in saved.get_json()["slots"]] == ["Arkane Kunde", "Initiative"]
    assert [slot["label"] for slot in _macros(client, char["id"]).get_json()["slots"]] == ["Arkane Kunde", "Initiative"]
    assert TableMacroBar.query.count() == 1


def test_invalid_slots_are_refused(client, data):
    char = finalized(client, data)

    assert _save(client, char["id"], [{"kind": "skill", "key": "gibt-es-nicht"}]).status_code == 422
    assert _save(client, char["id"], [{"kind": "blitz", "key": None}]).status_code == 422
    assert _save(client, char["id"], "initiative").status_code == 400
    eleven = [{"kind": "ability", "key": key} for key in ("str", "dex", "con", "int", "wis", "cha")] + \
             [{"kind": "save", "key": key} for key in ("str", "dex", "con", "int", "wis")]
    assert _save(client, char["id"], eleven).status_code == 400
    assert TableMacroBar.query.count() == 0


def test_only_who_may_roll_for_the_character_sees_its_macros(client, other, data):
    char = finalized(client, data)

    assert _macros(other, char["id"]).status_code == 403
    assert _save(other, char["id"], []).status_code == 403
    assert _macros(client, 99999).status_code == 404


def test_each_person_has_their_own_bar(app, client, other, data):
    t = table(app, client, other, data)
    _save(client, t["char"]["id"], [{"kind": "initiative", "key": None}])

    assert _macros(t["dm"], t["char"]["id"]).get_json()["slots"] == []
    _save(t["dm"], t["char"]["id"], [{"kind": "save", "key": "dex"}])
    assert [slot["kind"] for slot in _macros(client, t["char"]["id"]).get_json()["slots"]] == ["initiative"]


def test_a_plain_character_has_no_sheet_rolls(client):
    plain = client.post("/api/characters", json={"name": "Alt"}).get_json()

    body = _macros(client, plain["id"]).get_json()

    assert body["reason"] == "not_srd" and body["options"] == []
    assert _save(client, plain["id"], []).status_code == 422


def test_a_macro_roll_lands_at_the_table(app, client, other, data):
    t = table(app, client, other, data)
    slot = _save(client, t["char"]["id"], [{"kind": "skill", "key": "arkane-kunde"}]).get_json()["slots"][0]

    body = client.post(f"{BASE}/characters/{t['char']['id']}/roll",
                       json={"kind": slot["kind"], "key": slot["key"], "sessionId": t["session"]}).get_json()

    message = db.session.get(ChatMessage, body["messageId"])
    assert message.game_session_id == t["session"]
    assert message.content.startswith("Mira Eulenfeder · Arkane Kunde: würfelt 1d20+10: ")
