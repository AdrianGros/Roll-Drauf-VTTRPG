"""P8: XP / milestone progression and level-up 2-20 of SRD characters."""

import copy

import pytest

from vtt.characters import srd_progression
from vtt.extensions import db
from vtt.models import Character
from vtt.rules_content.creator_drafts import finalize_blockers
from vtt.rules_content.creator_rules import _weapon_allowed, evaluate

from tests.test_srd_creator_api import BASE, _client, app, client, data, finalized, other  # noqa: F401
from tests.test_srd_rolls import table  # noqa: F401


# ------------------------------------------------------------------ generic filler (uses the server's `needs`)

def payload_from_needs(data, need, evaluation, state):
    key = need["classKey"]
    entry = next(c for c in data["classes"] if c["classKey"] == key)
    payload = {"classKey": key, "hp": "fixed"}
    if need["subclass"]:
        payload["subclass"] = need["subclass"]["options"][0]
    if need["advancement"]:
        if need["advancement"]["epicBoon"]:
            feat = next(f for f in data["feats"] if f["category"] == "Epische-Gabe-Talent")
            payload["advancement"] = {"kind": "feat", "featId": feat["id"], "increaseAbility": "str"}
        else:
            payload["advancement"] = {"kind": "asi", "increases": {"str": 1, "con": 1}}
    choices = {}
    for pending in need["featureChoices"]:
        choice = next(c for c in entry["featureChoices"] if c["id"] == pending["id"])
        if pending["kind"] == "option":
            choices[pending["id"]] = next(iter(choice["options"]))
        elif pending["kind"] == "feat-category":
            choices[pending["id"]] = next(f["id"] for f in data["feats"] if f["category"].startswith(choice["category"]))
        else:
            picks = list(pending["current"])
            taken = {p for value in (state.get("featureChoices", {}).get(key) or {}).values() if isinstance(value, list) for p in value}
            if pending["kind"] == "weapon-mastery":
                pool = [w["id"] for w in data["equipment"]["weapons"] if _weapon_allowed(entry, w)]
            elif pending["kind"] == "language":
                pool = [l["id"] for l in data["languages"] if not l.get("automatic")]
            else:
                pool = [o["id"] for o in data["classOptions"]
                        if o["classKey"] == key and o["kind"] == choice["optionKind"] and (o["minClassLevel"] or 1) <= need["newClassLevel"]]
            picks += [p for p in pool if p not in picks and p not in taken][: pending["need"] - len(picks)]
            assert len(picks) == pending["need"], (key, pending["id"])
            choices[pending["id"]] = picks
    if choices:
        payload["featureChoices"] = choices
    if need["expertise"]:
        skills = [s for s, row in evaluation["skills"].items() if row["proficiency"] == "proficient"]
        payload["expertise"] = list(need["expertise"]["current"]) + skills[: need["expertise"]["add"]]
    if need["spells"]:
        sp = need["spells"]
        pool = data["spellLists"][key]
        spells = data["spells"]
        grade = sp["maxGrade"]
        payload["spells"] = {}
        cantrips = list(sp["cantrips"]["current"])
        cantrips += [s for s in pool if spells[s]["level"] == 0 and s not in cantrips][: sp["cantrips"]["count"] - len(cantrips)]
        payload["spells"]["cantrips"] = cantrips[: sp["cantrips"]["count"]]
        leveled = [s for s in pool if 1 <= spells[s]["level"] <= grade]
        book = sp["spellbook"]
        if book:
            have = list(book["current"])
            have += [s for s in leveled if s not in have][: book["count"] - len(have)]
            payload["spells"]["spellbook"] = have
            leveled = have
        prepared = [s for s in sp["prepared"]["current"] if s in leveled][: sp["prepared"]["count"]]
        prepared += [s for s in leveled if s not in prepared][: sp["prepared"]["count"] - len(prepared)]
        payload["spells"]["prepared"] = prepared
    return payload


def level_one_state(data, key):
    entry = next(c for c in data["classes"] if c["classKey"] == key)
    background = next(b for b in data["backgrounds"] if b["id"] == "character-origins.backgrounds.sage")
    options = entry["skillChoices"]["options"] or [s["id"] for s in data["skills"]]
    class_skills = [s for s in options if s not in background["skills"]][: entry["skillChoices"]["count"]]
    state = {
        "abilityMethod": "manual",
        "abilityBase": {"str": 15, "dex": 14, "con": 14, "int": 13, "wis": 13, "cha": 13},
        "levels": [{"classKey": key}],
        "background": {"id": background["id"], "abilityBonus": {background["abilities"][0]: 2, background["abilities"][1]: 1}},
        "species": {"id": "character-origins.species.halfling", "choices": {}},
        "skills": {"class": class_skills},
        "identity": {"name": f"Test {key}"},
    }
    evaluation = evaluate(data, state)
    need = srd_progression.needs(data, {**state, "levels": []}, {**evaluation, "level": 0}, key)
    payload = payload_from_needs(data, need, evaluation, state)
    if payload.get("featureChoices"):
        state["featureChoices"] = {key: payload["featureChoices"]}
    if payload.get("expertise"):
        state["skills"]["expertise"] = payload["expertise"]
    if payload.get("spells"):
        state["spells"] = {key: payload["spells"]}
    return state


CLASS_KEYS = ["barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard"]


def make_character(client, state):
    from tests.test_srd_creator_api import make_draft

    draft = make_draft(client, state)["draft"]
    created = client.post(f"{BASE}/drafts/{draft['id']}/finalize", json={"version": 1})
    assert created.status_code == 201, created.get_json()
    return created.get_json()["character"]


def award(client, char_id, **body):
    resp = client.put(f"{BASE}/characters/{char_id}/progression", json=body)
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()


# ------------------------------------------------------------------ pure engine: every class 1 -> 20

@pytest.mark.parametrize("key", CLASS_KEYS)
def test_every_class_can_be_levelled_from_1_to_20(data, key):
    state = level_one_state(data, key)
    evaluation = evaluate(data, state)
    assert finalize_blockers(evaluation, state) == [] or [b["code"] for b in finalize_blockers(evaluation, state)] == ["name-missing"], finalize_blockers(evaluation, state)
    hp = evaluation["hitPoints"]["max"]
    for target in range(2, 21):
        need = srd_progression.needs(data, state, evaluation, key)
        assert need["newClassLevel"] == target and need["newTotalLevel"] == target
        payload = payload_from_needs(data, need, evaluation, state)
        candidate = srd_progression.build_state(data, state, payload)
        evaluation = evaluate(data, candidate)
        blockers = finalize_blockers(evaluation, candidate)
        assert blockers == [], (key, target, blockers)
        assert evaluation["level"] == target and evaluation["hitPoints"]["max"] > hp
        hp = evaluation["hitPoints"]["max"]
        state = candidate
    assert evaluation["proficiencyBonus"] == 6
    assert evaluation["classes"][0]["subclass"]
    assert len(state["levels"]) == 20


def test_needs_name_what_each_level_asks_for(data):
    state = level_one_state(data, "fighter")
    evaluation = evaluate(data, state)
    seen = {}
    for target in range(2, 21):
        need = srd_progression.needs(data, state, evaluation, "fighter")
        seen[target] = need
        state = srd_progression.build_state(data, state, payload_from_needs(data, need, evaluation, state))
        evaluation = evaluate(data, state)
    assert seen[3]["subclass"]["options"] and not seen[4]["subclass"]
    assert [t for t, n in seen.items() if n["advancement"]] == [4, 6, 8, 12, 14, 16, 19]
    assert seen[19]["advancement"]["epicBoon"] and not seen[4]["advancement"]["epicBoon"]
    assert seen[5]["proficiencyBonus"] == 3 and seen[9]["proficiencyBonus"] == 4
    assert seen[2]["features"] and seen[2]["hp"] == {"die": 10, "fixed": 6, "conModifier": 3}
    assert [c["id"] for c in seen[4]["featureChoices"]] == ["weapon-mastery"]


# ------------------------------------------------------------------ XP, milestones, permissions

def test_status_and_xp_gate_the_level_up(client, other, data):
    char = finalized(client, data)
    body = client.get(f"{BASE}/characters/{char['id']}/progression").get_json()
    assert body["status"]["level"] == 5 and body["status"]["xp"] == 6500
    assert body["status"]["nextLevelXp"] == 14000 and body["status"]["canLevelUp"] is False
    assert body["canManage"] and body["canLevelUp"] and len(body["xpTable"]) == 20
    blocked = client.post(f"{BASE}/characters/{char['id']}/level-up/preview", json={"classKey": "wizard"})
    assert blocked.status_code == 409 and blocked.get_json()["error"] == "not_ready"
    assert other.get(f"{BASE}/characters/{char['id']}/progression").status_code == 403

    body = award(client, char["id"], addXp=7500, note="Drachenhöhle")
    assert body["status"]["xp"] == 14000 and body["status"]["canLevelUp"] and body["status"]["targetLevel"] == 6
    assert body["history"][-1]["type"] == "xp" and body["history"][-1]["note"] == "Drachenhöhle"
    assert db.session.get(Character, char["id"]).xp == 14000
    assert award(client, char["id"], setXp=100)["status"]["canLevelUp"] is False
    assert award(client, char["id"], addXp=-500)["status"]["xp"] == 0
    for bad in ({"addXp": 1.5}, {"addXp": "9"}, {"setXp": -1}, {"setXp": 10 ** 9}, {"addXp": 1, "setXp": 1}, {"mode": "bogus"}, {"milestoneTarget": 21}):
        resp = client.put(f"{BASE}/characters/{char['id']}/progression", json=bad)
        assert resp.status_code == 422, bad
    assert client.put(f"{BASE}/characters/{char['id']}/progression", json=[]).status_code == 400


def test_milestone_target_replaces_the_xp_threshold(client, data):
    char = finalized(client, data)
    body = award(client, char["id"], mode="milestone", milestoneTarget=7)
    assert body["status"]["mode"] == "milestone" and body["status"]["targetLevel"] == 7 and body["status"]["canLevelUp"]
    assert award(client, char["id"], milestoneTarget=5)["status"]["canLevelUp"] is False
    assert award(client, char["id"], milestoneTarget=None)["status"]["milestoneTarget"] is None
    # XP no longer grants anything in milestone mode
    assert award(client, char["id"], setXp=355000)["status"]["canLevelUp"] is False
    assert award(client, char["id"], mode="xp")["status"]["targetLevel"] == 20
    assert client.put(f"{BASE}/characters/{char['id']}/progression", json={}).status_code == 200


def test_in_a_campaign_only_the_dm_awards_experience(app, client, other, data):
    t = table(app, client, other, data)
    path = f"{BASE}/characters/{t['char']['id']}/progression"
    mine = client.get(path).get_json()
    assert mine["canManage"] is False and mine["canLevelUp"] is True
    assert client.put(path, json={"addXp": 1000}).status_code == 403
    assert other.put(path, json={"addXp": 1000}).status_code == 403
    dm_view = t["dm"].get(path).get_json()
    assert dm_view["canManage"] is True and dm_view["canLevelUp"] is False
    resp = t["dm"].put(path, json={"addXp": 7500})
    assert resp.status_code == 200 and resp.get_json()["status"]["canLevelUp"]
    assert client.get(path).get_json()["status"]["canLevelUp"]
    # the DM cannot level the character up, the owner can
    assert t["dm"].post(f"{BASE}/characters/{t['char']['id']}/level-up", json={"classKey": "wizard", "expectedLevel": 5}).status_code == 403
    assert client.put(f"{BASE}/characters/{t['char']['id']}/progression", json={"setXp": 0}).status_code == 403


def test_xp_is_no_longer_editable_through_the_generic_character_api(client, data):
    char = finalized(client, data)
    resp = client.put(f"/api/characters/{char['id']}", json={"xp": 999999})
    assert resp.status_code == 409 and resp.get_json()["fields"] == ["xp"]
    assert db.session.get(Character, char["id"]).xp == 6500


# ------------------------------------------------------------------ level-up through the API

def test_level_up_a_wizard_to_6_through_the_api(client, data):
    char = finalized(client, data)
    cid = char["id"]
    award(client, cid, addXp=7500)
    old = db.session.get(Character, cid)
    old_hp, old_max = old.hp_current, old.hp_max
    old.hp_current = old_max - 3
    db.session.commit()

    preview = client.post(f"{BASE}/characters/{cid}/level-up/preview", json={"classKey": "wizard"}).get_json()
    need = preview["needs"]
    assert need["newClassLevel"] == 6 and need["subclass"] is None and need["advancement"] is None
    assert need["spells"]["spellbook"]["count"] == 6 + 2 * 5 and need["spells"]["prepared"]["count"] > len(need["spells"]["prepared"]["current"])
    assert {b["code"] for b in preview["blockers"]} >= {"spellbook-missing", "prepared-missing"}
    assert "state" not in preview

    state = db.session.get(Character, cid).character_data["srd"]["state"]
    evaluation = evaluate(data, state)
    payload = payload_from_needs(data, need, evaluation, state)
    incomplete = client.post(f"{BASE}/characters/{cid}/level-up", json={"classKey": "wizard", "expectedLevel": 5})
    assert incomplete.status_code == 422 and incomplete.get_json()["error"] == "level_up_incomplete"
    assert db.session.get(Character, cid).level == 5

    resp = client.post(f"{BASE}/characters/{cid}/level-up", json={**payload, "expectedLevel": 5})
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["level"] == 6 and body["hpGain"] >= 1 and body["status"]["level"] == 6
    assert body["history"][-1]["type"] == "level-up" and body["history"][-1]["toLevel"] == 6
    stored = db.session.get(Character, cid)
    assert stored.level == 6 and stored.proficiency_bonus == 3 and stored.hp_max == old_max + body["hpGain"]
    assert stored.hp_current == old_max - 3 + body["hpGain"]
    assert stored.character_data["srd"]["derived"]["level"] == 6
    assert len(stored.character_data["srd"]["state"]["levels"]) == 6
    assert stored.xp == 14000
    assert client.get(f"{BASE}/characters/{cid}").get_json()["evaluation"]["level"] == 6
    again = client.post(f"{BASE}/characters/{cid}/level-up", json={**payload, "expectedLevel": 5})
    assert again.status_code == 409 and again.get_json()["error"] in ("level_conflict", "not_ready")
    assert old_hp  # sanity: fixture had hit points


def test_rolled_hit_points_are_checked_against_the_die(client, data):
    char = finalized(client, data)
    cid = char["id"]
    award(client, cid, addXp=7500)
    state = db.session.get(Character, cid).character_data["srd"]["state"]
    need = client.post(f"{BASE}/characters/{cid}/level-up/preview", json={"classKey": "wizard"}).get_json()["needs"]
    payload = payload_from_needs(data, need, evaluate(data, state), state)
    bad = client.post(f"{BASE}/characters/{cid}/level-up", json={**payload, "hp": 7, "expectedLevel": 5})
    assert bad.status_code == 422 and "hp-roll" in {b["code"] for b in bad.get_json()["blockers"]}
    junk = client.post(f"{BASE}/characters/{cid}/level-up", json={**payload, "hp": "viel", "expectedLevel": 5})
    assert junk.status_code == 422 and junk.get_json()["error"] == "invalid_hp"
    ok = client.post(f"{BASE}/characters/{cid}/level-up", json={**payload, "hp": 6, "expectedLevel": 5})
    assert ok.status_code == 200
    con = db.session.get(Character, cid).character_data["srd"]["derived"]["abilities"]["con"]["modifier"]
    assert ok.get_json()["hpGain"] == 6 + con


def test_level_up_validation_and_locks(client, other, data):
    char = finalized(client, data)
    cid = char["id"]
    award(client, cid, setXp=355000)
    url = f"{BASE}/characters/{cid}/level-up"
    assert other.post(url, json={"classKey": "wizard", "expectedLevel": 5}).status_code == 403
    assert client.post(url, json={"classKey": "wizard"}).get_json()["error"] == "expected_level_required"
    assert client.post(url, json={"classKey": "wizard", "expectedLevel": 4}).get_json()["error"] == "level_conflict"
    assert client.post(url, json={"classKey": "artificer", "expectedLevel": 5}).get_json()["error"] == "invalid_class"
    assert client.post(url, json={"expectedLevel": 5}).get_json()["error"] == "invalid_class"
    assert client.post(url, data="x", content_type="application/json").status_code == 400
    state = db.session.get(Character, cid).character_data["srd"]["state"]
    need = client.post(f"{url}/preview", json={"classKey": "wizard"}).get_json()["needs"]
    payload = payload_from_needs(data, need, evaluate(data, state), state)
    base = {**payload, "expectedLevel": 5}
    locked = client.post(url, json={**base, "subclass": "classes.wizard.subclass-abjurer"})
    assert locked.status_code == 409 and locked.get_json()["error"] == "subclass_locked"
    shrink = copy.deepcopy(base)
    shrink["spells"]["spellbook"] = shrink["spells"]["spellbook"][4:]
    assert client.post(url, json=shrink).get_json()["error"] == "spellbook_locked"
    assert client.post(url, json={**base, "expertise": []}).get_json()["error"] == "expertise_locked"
    assert client.post(url, json={**base, "featureChoices": {"nope": ["x"]}}).get_json()["error"] == "invalid_choice"
    assert client.post(url, json={**base, "advancement": {"kind": "feat", "evil": 1}}).get_json()["error"] == "invalid_payload"
    assert client.post(url, json={**base, "spells": {"cantrips": "x"}}).get_json()["error"] == "invalid_payload"
    bad_spell = copy.deepcopy(base)
    bad_spell["spells"]["prepared"][0] = "spells.gibts.nicht"
    resp = client.post(url, json=bad_spell)
    assert resp.status_code == 422 and "spell-invalid" in {b["code"] for b in resp.get_json()["blockers"]}
    assert db.session.get(Character, cid).level == 5


def test_level_up_to_a_new_asi_level_needs_the_advancement(client, data):
    char = finalized(client, data)
    cid = char["id"]
    award(client, cid, setXp=355000)
    url = f"{BASE}/characters/{cid}/level-up"
    for target in (6, 7):
        state = db.session.get(Character, cid).character_data["srd"]["state"]
        need = client.post(f"{url}/preview", json={"classKey": "wizard"}).get_json()["needs"]
        payload = payload_from_needs(data, need, evaluate(data, state), state)
        assert client.post(url, json={**payload, "expectedLevel": target - 1}).status_code == 200
    state = db.session.get(Character, cid).character_data["srd"]["state"]
    preview = client.post(f"{url}/preview", json={"classKey": "wizard"}).get_json()
    assert preview["needs"]["advancement"] == {"classLevel": 8, "epicBoon": False}
    assert "advancement-missing" in {b["code"] for b in preview["blockers"]}
    payload = payload_from_needs(data, preview["needs"], evaluate(data, state), state)
    del payload["advancement"]
    missing = client.post(url, json={**payload, "expectedLevel": 7})
    assert missing.status_code == 422
    payload["advancement"] = {"kind": "asi", "increases": {"int": 1, "con": 1}}
    ok = client.post(url, json={**payload, "expectedLevel": 7})
    assert ok.status_code == 200, ok.get_json()
    stored = db.session.get(Character, cid)
    assert stored.level == 8 and stored.con_score == 15 and stored.int_score == 20
    wrong = client.post(url, json={**payload, "expectedLevel": 8, "advancement": {"kind": "asi", "increases": {"int": 3}}})
    assert wrong.status_code in (409, 422)


def test_level_up_refreshes_the_open_table_token(app, client, other, data):
    from vtt.models import TokenState
    from tests.test_srd_rolls import _tokens

    t = table(app, client, other, data)
    cid = t["char"]["id"]
    award(t["dm"], cid, addXp=7500)
    state = db.session.get(Character, cid).character_data["srd"]["state"]
    need = client.post(f"{BASE}/characters/{cid}/level-up/preview", json={"classKey": "wizard"}).get_json()["needs"]
    payload = payload_from_needs(data, need, evaluate(data, state), state)
    created = client.post(_tokens(t), json={"name": "Mira", "x": 1, "y": 1, "character_id": cid})
    assert created.status_code == 201, created.get_json()
    token_id = created.get_json()["token"]["id"]
    resp = client.post(f"{BASE}/characters/{cid}/level-up", json={**payload, "expectedLevel": 5})
    assert resp.status_code == 200, resp.get_json()
    db.session.expire_all()
    token = db.session.get(TokenState, token_id)
    assert token.hp_max == db.session.get(Character, cid).hp_max > 32
    assert token.metadata_json["sheet"]["level"] == 6 and token.metadata_json["sheet"]["proficiencyBonus"] == 3


def test_non_srd_characters_have_no_progression(client):
    plain = client.post("/api/characters", json={"name": "Alt", "level": 1}).get_json()
    assert client.get(f"{BASE}/characters/{plain['id']}/progression").status_code == 422
    assert client.put(f"{BASE}/characters/{plain['id']}/progression", json={"addXp": 5}).status_code == 422
    assert client.post(f"{BASE}/characters/{plain['id']}/level-up", json={"classKey": "wizard", "expectedLevel": 1}).status_code == 422


# ------------------------------------------------------------------ P9: multiclassing

def multiclass_character(client, data, key="fighter"):
    state = level_one_state(data, key)
    state["abilityBase"]["cha"] = 8
    char = make_character(client, state)
    award(client, char["id"], addXp=300)
    return char


def test_multiclass_options_name_eligible_and_blocked_classes(client, data):
    cid = multiclass_character(client, data)["id"]
    options = {o["classKey"]: o for o in client.get(f"{BASE}/characters/{cid}/progression").get_json()["multiclassOptions"]}
    assert options["fighter"]["owned"] and options["fighter"]["level"] == 1
    assert options["wizard"]["eligible"] and options["wizard"]["reason"] is None
    assert not options["bard"]["eligible"] and "Charisma" in options["bard"]["reason"]
    assert len(options) == 12


def test_multiclass_into_wizard_adds_a_level_one_wizard(client, data):
    cid = multiclass_character(client, data)["id"]
    preview = client.post(f"{BASE}/characters/{cid}/level-up/preview", json={"classKey": "wizard"}).get_json()
    need = preview["needs"]
    assert need["newClassLevel"] == 1 and need["newTotalLevel"] == 2
    assert need["multiclass"]["grants"] is not None
    assert need["spells"]["spellbook"]["count"] > 0 and need["spells"]["cantrips"]["count"] > 0
    state = db.session.get(Character, cid).character_data["srd"]["state"]
    payload = payload_from_needs(data, need, evaluate(data, state), state)
    payload["expectedLevel"] = 1
    resp = client.post(f"{BASE}/characters/{cid}/level-up", json=payload)
    assert resp.status_code == 200, resp.get_json()
    stored = db.session.get(Character, cid)
    classes = {c["classKey"]: c["level"] for c in stored.character_data["srd"]["derived"]["classes"]}
    assert classes == {"fighter": 1, "wizard": 1}
    assert stored.level == 2 and "Magier" in stored.class_name and "Kämpfer" in stored.class_name
    sheet = client.get(f"{BASE}/characters/{cid}").get_json()["evaluation"]
    assert sheet["spellcasting"] is not None


def test_multiclass_prerequisite_blocks_the_level_up(client, data):
    cid = multiclass_character(client, data)["id"]
    preview = client.post(f"{BASE}/characters/{cid}/level-up/preview", json={"classKey": "bard"}).get_json()
    assert any(b["code"] == "multiclass-prerequisite" for b in preview["blockers"])
    resp = client.post(f"{BASE}/characters/{cid}/level-up", json={"classKey": "bard", "expectedLevel": 1})
    assert resp.status_code == 422 and resp.get_json()["error"] == "level_up_incomplete"
    assert db.session.get(Character, cid).level == 1


def test_multiclass_skill_grant_is_required_and_applied(client, data):
    cid = multiclass_character(client, data)["id"]
    need = client.post(f"{BASE}/characters/{cid}/level-up/preview", json={"classKey": "rogue"}).get_json()
    grant = next(c for c in data["classes"] if c["classKey"] == "rogue")["multiclassGrants"]["skillChoices"]
    assert need["needs"]["multiclass"]["skillChoices"]["count"] == grant["count"]
    assert any(b["code"] == "multiclass-skills" for b in need["blockers"])
    state = db.session.get(Character, cid).character_data["srd"]["state"]
    evaluation = evaluate(data, state)
    payload = payload_from_needs(data, need["needs"], evaluation, state)
    owned = {s for s, row in evaluation["skills"].items() if row["proficiency"] != "none"}
    options = need["needs"]["multiclass"]["skillChoices"]["options"] or [s["id"] for s in data["skills"]]
    pick = next(s for s in options if s not in owned)
    payload["multiclassSkills"] = [pick]
    ok = client.post(f"{BASE}/characters/{cid}/level-up/preview", json=payload).get_json()
    assert not any(b["code"] == "multiclass-skills" for b in ok["blockers"])
    assert ok["evaluation"]["skills"][pick]["proficiency"] == "proficient"
    bad = client.post(f"{BASE}/characters/{cid}/level-up/preview", json={**payload, "multiclassSkills": ["nonsense"]}).get_json()
    assert any(b["code"] == "multiclass-skills" and b["severity"] == "error" for b in bad["blockers"])
    stored = client.post(f"{BASE}/characters/{cid}/level-up", json={**payload, "expectedLevel": 1})
    assert stored.status_code == 200, stored.get_json()
    assert db.session.get(Character, cid).character_data["srd"]["state"]["skills"]["multiclass"]["rogue"] == [pick]


def test_multiclass_skills_are_refused_for_classes_the_character_already_has(client, data):
    cid = multiclass_character(client, data)["id"]
    resp = client.post(f"{BASE}/characters/{cid}/level-up/preview", json={"classKey": "fighter", "multiclassSkills": ["acrobatics"]})
    assert resp.status_code == 422 and resp.get_json()["error"] == "invalid_payload"


def test_unknown_class_is_refused(client, data):
    cid = multiclass_character(client, data)["id"]
    resp = client.post(f"{BASE}/characters/{cid}/level-up/preview", json={"classKey": "artificer"})
    assert resp.status_code == 422 and resp.get_json()["error"] == "invalid_class"


def test_caster_level_slots_combine_across_classes(data):
    state = level_one_state(data, "wizard")
    state["levels"] = [{"classKey": "wizard"}, {"classKey": "wizard", "hp": "fixed"}, {"classKey": "cleric", "hp": "fixed"}, {"classKey": "cleric", "hp": "fixed"}]
    evaluation = evaluate(data, state)
    assert [c["level"] for c in evaluation["classes"]] == [2, 2]
    slots = evaluation["spellcasting"]["slots"]
    assert slots and sum(slots) >= 4
