"""P7: inventory of SRD characters: starting equipment, worn armor, coins, weight and weapon rolls."""

import pytest

from vtt.extensions import db
from vtt.models import Character, ChatMessage, InventoryItem

from tests.test_srd_creator_api import BASE, _client, app, client, data, finalized, other  # noqa: F401
from tests.test_srd_rolls import _tokens, roll, table  # noqa: F401

ARMOR = "equipment.armor.armor-light.lederruestung"
CHAIN = "equipment.armor.armor-heavy.kettenpanzer"
SHIELD = "equipment.armor.armor-shield-table.schild"
DAGGER = "equipment.coins-and-weapons.weapons-simple-melee.dolch"
STAFF = "equipment.coins-and-weapons.weapons-simple-melee.kampfstab"
LONGSWORD = "equipment.coins-and-weapons.weapons-martial-melee.langschwert"
PACK = "equipment.adventuring-gear.gear-table.entdeckerausruestung"


def inv(client, char_id):
    return f"{BASE}/characters/{char_id}/inventory"


def add(client, char_id, item_id, quantity=1, **extra):
    resp = client.post(inv(client, char_id), json={"itemId": item_id, "quantity": quantity, **extra})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()


def row(body, item_id):
    return next(i for i in body["items"] if i["itemId"] == item_id)


def test_starting_equipment_is_moved_into_the_inventory_once(client, data):
    char = finalized(client, data)
    empty = client.get(inv(client, char["id"])).get_json()
    assert empty["items"] == [] and empty["seeded"] is False and empty["worn"]["armor"] is None
    assert client.post(f"{inv(client, char['id'])}/starting-equipment", json={}).get_json()["error"] == "package_missing"

    resp = client.post(f"{inv(client, char['id'])}/starting-equipment", json={"classPackage": "A", "backgroundPackage": "A"})
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    names = {i["name"]: i["quantity"] for i in body["items"]}
    assert names["Dolch"] == 2 and names["Robe"] == 2
    assert names["Buch"] == 1 and names["Kampfstab"] == 1 and names["Pergament"] == 18
    assert "Zauberbuch" in names
    assert body["coins"]["GM"] == 5 + 8 + 500  # class + background + level 5-10 base gold
    assert body["seeded"] and any("500 GM" in note for note in body["notes"])
    assert [p["category"] for p in body["pending"]] == ["arcane-focus"]
    assert all(p["options"] for p in body["pending"])
    assert body["packages"] == {"class": "A", "background": "A"}

    again = client.post(f"{inv(client, char['id'])}/starting-equipment", json={})
    assert again.status_code == 409 and again.get_json()["error"] == "already_seeded"


def test_gold_packages_only_give_coins(client, data):
    char = finalized(client, data)
    body = client.post(f"{inv(client, char['id'])}/starting-equipment", json={"classPackage": "B", "backgroundPackage": "B"}).get_json()
    assert body["items"] == [] and body["pending"] == [] and body["coins"]["GM"] == 55 + 50 + 500
    bad = client.post(f"{inv(client, char['id'])}/starting-equipment", json={"classPackage": "Z"})
    assert bad.status_code in (409, 422)


def fighter(client, data):
    from tests.test_srd_creator_api import make_draft, wizard_state

    state = wizard_state(data, "Brunhild")
    state.update({
        "levels": [{"classKey": "fighter"}], "spells": {}, "subclasses": {}, "advancements": [],
        "skills": {"class": ["athletik", "wahrnehmung"]},
        "abilityBase": {"str": 15, "dex": 12, "con": 14, "int": 8, "wis": 10, "cha": 13},
        "background": {"id": "character-origins.backgrounds.soldier", "abilityBonus": {"str": 2, "con": 1}},
        "species": {"id": "character-origins.species.halfling", "choices": {}},
        "featureChoices": {"fighter": {
            "fighting-style": "feats.descriptions.archery",
            "weapon-mastery": [LONGSWORD, DAGGER, STAFF]}},
    })
    draft = make_draft(client, state)["draft"]
    created = client.post(f"{BASE}/drafts/{draft['id']}/finalize", json={"version": 1})
    assert created.status_code == 201, created.get_json()
    return created.get_json()["character"]


def test_seeding_equips_starting_armor_and_updates_the_armor_class(client, data):
    char = fighter(client, data)
    before = client.get(f"{BASE}/characters/{char['id']}").get_json()["evaluation"]["armorClass"]["value"]
    body = client.post(f"{inv(client, char['id'])}/starting-equipment", json={"classPackage": "A", "backgroundPackage": "B"}).get_json()
    chain = row(body, CHAIN)
    assert chain["equipped"] and body["worn"]["armor"] == "Kettenpanzer"
    assert body["armorClass"]["value"] == 16 > before
    assert db.session.get(Character, char["id"]).ac == 16
    assert client.get(f"{BASE}/characters/{char['id']}").get_json()["evaluation"]["armorClass"]["value"] == 16
    assert [f["code"] for f in body["findings"]] == ["armor-stealth"]


def test_weapon_mastery_and_proficiency_for_a_fighter(client, data):
    char = fighter(client, data)
    client.post(f"{inv(client, char['id'])}/starting-equipment", json={"classPackage": "A", "backgroundPackage": "B"})
    body = add(client, char["id"], LONGSWORD)
    sword = next(a for a in body["attacks"] if a["name"] == "Langschwert")
    # STR 15 + 2 from the background = 17 (+3), proficiency +2
    assert sword["proficient"] and sword["attackBonus"] == 5 and sword["damage"] == "1d8+3" and sword["versatile"] == "1d10+3"
    assert sword["mastery"] and sword["masteryActive"] is True


def test_wearing_armor_and_shield_drives_the_armor_class(client, data):
    char = finalized(client, data)
    base = client.get(inv(client, char["id"])).get_json()["armorClass"]["value"]
    assert base == 11
    leather = row(add(client, char["id"], ARMOR), ARMOR)
    shield = row(add(client, char["id"], SHIELD), SHIELD)
    worn = client.patch(f"{inv(client, char['id'])}/{leather['id']}", json={"equipped": True}).get_json()
    assert worn["armorClass"]["value"] == 12 and worn["worn"]["armor"] == "Lederrüstung"
    worn = client.patch(f"{inv(client, char['id'])}/{shield['id']}", json={"equipped": True}).get_json()
    assert worn["armorClass"]["value"] == 14 and worn["worn"]["shield"] is True
    assert any(f["code"] == "shield-untrained" for f in worn["findings"])
    assert db.session.get(Character, char["id"]).ac == 14
    stored = client.get(f"{BASE}/characters/{char['id']}").get_json()
    assert stored["evaluation"]["armorClass"]["value"] == 14 and stored["srd"]["derived"]["armorClass"]["value"] == 14

    chain = row(add(client, char["id"], CHAIN), CHAIN)
    swapped = client.patch(f"{inv(client, char['id'])}/{chain['id']}", json={"equipped": True}).get_json()
    assert swapped["worn"]["armor"] == "Kettenpanzer" and not row(swapped, ARMOR)["equipped"]
    assert any(f["code"] == "armor-untrained" for f in swapped["findings"])

    off = client.patch(f"{inv(client, char['id'])}/{chain['id']}", json={"equipped": False}).get_json()
    assert off["worn"]["armor"] is None and off["armorClass"]["value"] == 13  # shield only

    on = client.patch(f"{inv(client, char['id'])}/{leather['id']}", json={"equipped": True}).get_json()
    assert on["armorClass"]["value"] == 14
    gone = client.delete(f"{inv(client, char['id'])}/{leather['id']}").get_json()
    assert gone["worn"]["armor"] is None and gone["armorClass"]["value"] == 13
    assert client.delete(f"{inv(client, char['id'])}/{leather['id']}").status_code == 404


def test_gear_cannot_be_worn_and_unknown_items_are_rejected(client, data):
    char = finalized(client, data)
    rope = add(client, char["id"], PACK)["items"][0]
    assert client.patch(f"{inv(client, char['id'])}/{rope['id']}", json={"equipped": True}).get_json()["error"] == "not_wearable"
    assert client.post(inv(client, char["id"]), json={"itemId": "equipment.nix"}).get_json()["error"] == "unknown_item"
    assert client.post(inv(client, char["id"]), json={}).status_code == 422
    assert client.post(inv(client, char["id"]), json={"itemId": ARMOR, "quantity": 0}).status_code == 422
    assert client.post(inv(client, char["id"]), json={"itemId": ARMOR, "quantity": 10 ** 6}).status_code == 422
    assert client.patch(f"{inv(client, char['id'])}/{rope['id']}", json={"equipped": "ja"}).status_code == 422


def test_packs_unfold_and_stacks_merge(client, data):
    char = finalized(client, data)
    body = add(client, char["id"], PACK)
    assert len(body["items"]) > 3 and not any(i["itemId"] == PACK for i in body["items"])
    first = add(client, char["id"], DAGGER, 2)
    second = add(client, char["id"], DAGGER, 3)
    assert row(second, DAGGER)["quantity"] == 5 and len(second["items"]) == len(first["items"])
    changed = client.patch(f"{inv(client, char['id'])}/{row(second, DAGGER)['id']}", json={"quantity": 1}).get_json()
    assert row(changed, DAGGER)["quantity"] == 1


def test_custom_items_and_legacy_loot_rows(client, other, data):
    char = finalized(client, data)
    made = client.post(inv(client, char["id"]), json={"custom": {"name": "Eulenfeder", "weightKg": 0.1, "description": "Glücksbringer"}}).get_json()
    feather = made["items"][0]
    assert feather["custom"] and feather["weightKg"] == 0.1
    edited = client.patch(f"{inv(client, char['id'])}/{feather['id']}", json={"name": "Weiße Eulenfeder", "weightKg": 0.2, "quantity": 3}).get_json()
    assert edited["items"][0]["name"] == "Weiße Eulenfeder" and edited["items"][0]["totalKg"] == 0.6
    assert client.post(inv(client, char["id"]), json={"custom": {"name": " "}}).status_code == 422
    assert client.post(inv(client, char["id"]), json={"custom": {"name": "x", "weightKg": -1}}).status_code == 422

    legacy = client.post(f"/api/characters/{char['id']}/inventory", json={"name": "Beute", "quantity": 2, "weight_per_unit": 1.5})
    assert legacy.status_code == 201
    body = client.get(inv(client, char["id"])).get_json()
    loot = next(i for i in body["items"] if i["name"] == "Beute")
    assert loot["custom"] and loot["kind"] == "custom" and loot["totalKg"] == 3.0
    # catalog entries cannot be renamed
    dagger = row(add(client, char["id"], DAGGER), DAGGER)
    client.patch(f"{inv(client, char['id'])}/{dagger['id']}", json={"name": "Hacke", "weightKg": 0})
    assert row(client.get(inv(client, char["id"])).get_json(), DAGGER)["name"] == "Dolch"


def test_coins_change_by_delta_or_absolute_value(client, data):
    char = finalized(client, data)
    url = f"{inv(client, char['id'])}/coins"
    body = client.put(url, json={"coins": {"GM": 12, "SM": 7}}).get_json()
    assert body["coins"] == {"PM": 0, "GM": 12, "EM": 0, "SM": 7, "KM": 0}
    assert client.put(url, json={"delta": {"GM": -5, "KM": 3}}).get_json()["coins"]["GM"] == 7
    low = client.put(url, json={"delta": {"GM": -8}})
    assert low.status_code == 422 and low.get_json()["error"] == "not_enough_coins"
    assert client.get(inv(client, char["id"])).get_json()["coins"]["GM"] == 7
    for payload in ({}, {"coins": {"XX": 1}}, {"coins": {"GM": "1"}}, {"coins": {"GM": -1}}, {"coins": {"GM": 1}, "delta": {"GM": 1}}, {"delta": {"GM": 10 ** 9}}):
        assert client.put(url, json=payload).status_code == 422, payload


def test_weight_is_compared_with_the_carrying_capacity(client, data):
    char = finalized(client, data)
    start = client.get(inv(client, char["id"])).get_json()["weight"]
    # halfling (Klein), strength 8: 8 x 7.5 kg
    assert start["size"] == "Klein" and start["capacityKg"] == 60 and start["liftKg"] == 120 and not start["over"]
    client.put(f"{inv(client, char['id'])}/coins", json={"coins": {"GM": 100}})
    body = add(client, char["id"], CHAIN)  # 27.5 kg in the SRD data
    weight = body["weight"]
    assert weight["coinsKg"] == 1.0 and weight["itemsKg"] > 20 and weight["carriedKg"] == round(weight["itemsKg"] + 1.0, 2)
    heavy = client.post(inv(client, char["id"]), json={"custom": {"name": "Amboss", "weightKg": 90}}).get_json()["weight"]
    assert heavy["over"] is True


def test_weapon_values_follow_ability_proficiency_and_properties(client, data):
    char = finalized(client, data)
    body = add(client, char["id"], DAGGER)
    add(client, char["id"], STAFF)
    body = add(client, char["id"], LONGSWORD)
    attacks = {a["name"]: a for a in body["attacks"]}
    # Mira: STR 8 (-1), DEX 12 (+1), proficiency +3, simple weapons only
    assert attacks["Dolch"]["ability"] == "dex" and attacks["Dolch"]["attackBonus"] == 4 and attacks["Dolch"]["damage"] == "1d4+1"
    assert attacks["Kampfstab"]["ability"] == "str" and attacks["Kampfstab"]["attackBonus"] == 2 and attacks["Kampfstab"]["damage"] == "1d6-1"
    assert attacks["Kampfstab"]["versatile"] == "1d8-1"
    assert attacks["Langschwert"]["proficient"] is False and attacks["Langschwert"]["attackBonus"] == -1
    assert attacks["Waffenloser Schlag"]["attackBonus"] == 2 and attacks["Waffenloser Schlag"]["damage"] == "0"
    assert attacks["Dolch"]["masteryActive"] is False and attacks["Dolch"]["damageType"] == "Stich"


def test_weapon_rolls_use_the_sheet_values(client, other, data):
    char = finalized(client, data)
    body = add(client, char["id"], DAGGER)
    dagger = row(body, DAGGER)["id"]
    staff = row(add(client, char["id"], STAFF), STAFF)["id"]
    attack = roll(client, char["id"], kind="weapon_attack", key=str(dagger)).get_json()
    assert attack["dice"] == "1d20+4" and attack["label"] == "Angriff: Dolch"
    damage = roll(client, char["id"], kind="weapon_damage", key=str(dagger)).get_json()
    assert damage["dice"] == "1d4+1" and 2 <= damage["result"]["total"] <= 5 and "Stich" in damage["label"]
    crit = roll(client, char["id"], kind="weapon_damage", key=str(dagger), critical=True).get_json()
    assert crit["dice"] == "2d4+1" and len(crit["result"]["rolls"]) == 2 and "Kritisch" in crit["label"]
    two = roll(client, char["id"], kind="weapon_damage", key=str(staff), twoHanded=True).get_json()
    assert two["dice"] == "1d8-1" and "zweihändig" in two["label"]
    assert roll(client, char["id"], kind="weapon_damage", key=str(dagger), twoHanded=True).status_code == 422
    unarmed = roll(client, char["id"], kind="weapon_damage", key="unarmed").get_json()
    assert unarmed["dice"] == "0" and unarmed["result"]["total"] == 0
    for _ in range(20):
        total = roll(client, char["id"], kind="weapon_damage", key=str(staff)).get_json()["result"]["total"]
        assert 0 <= total <= 5
    assert roll(client, char["id"], kind="weapon_attack", key="9999").status_code == 422
    assert roll(client, char["id"], kind="weapon_attack").status_code == 422
    assert roll(client, char["id"], kind="weapon_attack", key="unarmed").get_json()["dice"] == "1d20+2"


def test_weapon_rolls_land_in_the_table_log(app, client, other, data):
    t = table(app, client, other, data)
    from tests.play_shared import enter_table
    from vtt.models import Campaign,GameSession
    enter_table(client,db.session.get(Campaign,t['campaign']),db.session.get(GameSession,t['session']))
    dagger = row(add(client, t["char"]["id"], DAGGER), DAGGER)["id"]
    body = roll(client, t["char"]["id"], kind="weapon_damage", key=str(dagger), critical=True).get_json()
    assert body["logged"]
    content = db.session.get(ChatMessage, body["messageId"]).content
    assert content.startswith("Mira Eulenfeder · Schaden: Dolch (Stich) (Kritisch): würfelt 2d4+1: ")
    assert content.endswith(f"= {body['result']['total']}")
    attack = roll(client, t["char"]["id"], kind="weapon_attack", key=str(dagger), mode="advantage").get_json()
    assert db.session.get(ChatMessage, attack["messageId"]).content.startswith("Mira Eulenfeder · Angriff: Dolch (Vorteil): würfelt 1d20+4: ")


def test_wearing_armor_updates_the_linked_table_token(app, client, other, data):
    t = table(app, client, other, data)
    from tests.play_shared import enter_table
    from vtt.models import Campaign,GameSession
    enter_table(client,db.session.get(Campaign,t['campaign']),db.session.get(GameSession,t['session']))
    token = client.post(_tokens(t), json={"name": "Mira", "x": 1, "y": 1, "character_id": t["char"]["id"]}).get_json()["token"]
    assert token["metadata_json"]["sheet"]["ac"] == 11
    leather = row(add(client, t["char"]["id"], ARMOR), ARMOR)["id"]
    client.patch(f"{inv(client, t['char']['id'])}/{leather}", json={"equipped": True})
    from vtt.models import TokenState
    db.session.expire_all()
    assert db.session.get(TokenState, token["id"]).metadata_json["sheet"]["ac"] == 12


def test_only_the_owner_writes_and_only_srd_characters_have_this_inventory(client, other, data):
    char = finalized(client, data)
    add(client, char["id"], DAGGER)
    assert other.get(inv(other, char["id"])).status_code == 403
    assert other.post(inv(other, char["id"]), json={"itemId": DAGGER}).status_code == 403
    assert other.put(f"{inv(other, char['id'])}/coins", json={"coins": {"GM": 1}}).status_code == 403
    assert other.post(f"{inv(other, char['id'])}/starting-equipment", json={}).status_code == 403
    assert client.get(inv(client, 99999)).status_code == 404
    plain = client.post("/api/characters", json={"name": "Alt"}).get_json()
    assert client.get(inv(client, plain["id"])).status_code == 422
    assert client.post(inv(client, plain["id"]), json={"itemId": DAGGER}).status_code == 422
    assert InventoryItem.query.filter_by(character_id=plain["id"]).count() == 0
    anonymous = client.application.test_client()
    assert anonymous.get(inv(anonymous, char["id"])).status_code == 401


def test_the_dm_of_the_campaign_may_read_but_not_change_the_inventory(app, client, other, data):
    t = table(app, client, other, data)
    add(client, t["char"]["id"], DAGGER)
    assert t["dm"].get(inv(t["dm"], t["char"]["id"])).status_code == 200
    assert t["dm"].post(inv(t["dm"], t["char"]["id"]), json={"itemId": DAGGER}).status_code == 403


def test_pending_choices_are_resolved_by_picking_an_item(client, data):
    char = finalized(client, data)
    body = client.post(f"{inv(client, char['id'])}/starting-equipment", json={"classPackage": "A", "backgroundPackage": "A"}).get_json()
    arcane = body["pending"][0]
    pick = arcane["options"][0]["itemId"]
    done = add(client, char["id"], pick, resolve=arcane["id"])
    assert done["pending"] == [] and row(done, pick)["quantity"] == 1


def test_pending_choices_can_be_dismissed(client, data):
    char = finalized(client, data)
    body = client.post(f"{inv(client, char['id'])}/starting-equipment", json={"classPackage": "A", "backgroundPackage": "A"}).get_json()
    pending = body["pending"][0]
    assert client.delete(f"{inv(client, char['id'])}/pending/{pending['id']}").get_json()["pending"] == []
