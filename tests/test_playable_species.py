"""Playable Eagle Species (Duckfolk milestone): check, publish, choose, pin, derive, level, transfer and act."""

import copy
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from vtt.characters import species_catalog
from vtt.creation_engine import species as conversion
from vtt.creation_engine.models import CeSpeciesRevision
from vtt.extensions import db
from vtt.models import Campaign, CampaignMap, CampaignMember, Character, ChatMessage, GameSession
from vtt.rules_content import species_profiles
from vtt.rules_content.creator_rules import evaluate, load_creator_data

from tests.test_srd_creator_api import BASE, _client, app, data, finalized, wizard_state  # noqa: F401

CE = "/api/ce/authoring"
DUCKFOLK = {
    "name": "Duckfolk", "type": "race", "img": "icons/svg/mystery-man.svg",
    "system": {
        "description": {"value": "<p>Kleines Entenvolk mit <em>lautem</em> Quaken.</p>", "chat": ""},
        "source": {"rules": "2024", "book": "Homebrew"},
        "identifier": "duckfolk",
        "type": {"value": "humanoid", "subtype": "", "custom": ""},
        "movement": {"walk": "30", "swim": 30, "fly": None, "climb": None, "burrow": None, "units": "ft"},
        "senses": {"ranges": {"darkvision": 0, "blindsight": None, "tremorsense": None, "truesight": None}, "units": "ft", "special": ""},
        "advancement": [{"_id": "sizeAdv1", "type": "Size", "configuration": {"sizes": ["sm"]}, "value": {}, "title": "", "hint": ""}],
    },
    "effects": [],
    "flags": {"eagle-homebrew": {"pair": {"pack": "world.eagle-species-2024"}}},
}
SUPPLEMENT = {
    "schema": "roll-drauf.species-supplement.v1",
    "skillChoices": [{"id": "duck-skill", "label": "Entenfertigkeit", "options": ["athletik", "wahrnehmung"]}],
    "actions": [{
        "id": "telekinetic-quack", "name": "Telekinetisches Quaken", "kind": "object-telekinesis", "activation": "action",
        "uses": "at-will", "rangeFeet": 30, "maxWeightLb": 10, "maxMoveFeet": 30,
        "description": "Ein Quaken bewegt einen unbeaufsichtigten Gegenstand.",
    }],
    "traits": [],
}
DECLARATION = {"object": "der Schlüssel auf dem Tisch", "weightLb": 1, "distanceFeet": 20, "moveFeet": 15, "unattended": True}


def test_duckfolk_starter_is_the_playable_test_fixture():
    asset = Path(__file__).resolve().parents[1] / "vtt/static/examples/duckfolk-2024.json"
    starter = json.loads(asset.read_text())
    assert starter == {"source": DUCKFOLK, "supplement": SUPPLEMENT}


def skills():
    return {skill["id"]: skill["name"] for skill in load_creator_data()["skills"]}


def _member(campaign_id, owner_id, user_id, role):
    db.session.add(CampaignMember(
        campaign_id=campaign_id, user_id=user_id, campaign_role=role, status="active",
        joined_at=datetime.utcnow(), invited_at=datetime.utcnow(), accepted_at=datetime.utcnow(), invited_by=owner_id))


@pytest.fixture
def pond(app):
    """A campaign led by `gm` with `player`; `stranger` is in no campaign. Both feature flags on."""
    app.config.update(CE_AUTHORING=True, CE_PLAYABLE_SPECIES=True)
    gm, player, stranger = (_client(app, name) for name in ("duck_gm", "duck_player", "duck_stranger"))
    campaign = Campaign(name="Teichkampagne", description="", owner_id=gm.user_id, status="active", max_players=6)
    db.session.add(campaign)
    db.session.flush()
    _member(campaign.id, gm.user_id, gm.user_id, "DM")
    _member(campaign.id, gm.user_id, player.user_id, "Player")
    db.session.commit()
    return SimpleNamespace(app=app, gm=gm, player=player, stranger=stranger, campaign=campaign.id, world=f"campaign:{campaign.id}")


def create_species(client, world, doc=DUCKFOLK, doc_id="Duck01"):
    resp = client.post(f"{CE}/request", json={"world": world, "type": "document.create",
                                              "payload": {"target": {"world": "Item"}, "id": doc_id, "data": copy.deepcopy(doc)}})
    assert resp.get_json()["ok"] is True, resp.get_json()
    return f"Item.{doc_id}"


def check(client, world, uuid, supplement=SUPPLEMENT):
    return client.post(f"{CE}/species/check", json={"world": world, "uuid": uuid, "supplement": supplement})


def publish(client, world, uuid, supplement=SUPPLEMENT, scope=None):
    checked = check(client, world, uuid, supplement)
    assert checked.status_code == 200, checked.get_json()
    body = {"world": world, "uuid": uuid, "supplement": supplement, "expectedDigest": checked.get_json()["source"]["digest"]}
    if scope:
        body["scope"] = scope
    return client.post(f"{CE}/species/publish", json=body)


def duck_state(data, species_id, skill="athletik", name="Quaki"):
    wizard = next(c for c in data["classes"] if c["classKey"] == "wizard")
    row = wizard["spellcasting"]["levels"][0]
    cantrips = [s for s in data["spellLists"]["wizard"] if data["spells"][s]["level"] == 0][:row["cantrips"]]
    book = [s for s in data["spellLists"]["wizard"] if data["spells"][s]["level"] == 1][:wizard["spellcasting"]["spellbook"]["startingSpells"]]
    return {
        "abilityMethod": "manual",
        "abilityBase": {"str": 8, "dex": 12, "con": 13, "int": 15, "wis": 14, "cha": 10},
        "levels": [{"classKey": "wizard"}],
        "background": {"id": "character-origins.backgrounds.sage", "abilityBonus": {"int": 2, "con": 1}},
        "species": {"id": species_id, "choices": {"duck-skill": skill}},
        "skills": {"class": ["heilkunde", "nachforschungen"]},
        "spells": {"wizard": {"cantrips": cantrips, "spellbook": book, "prepared": book[:row["prepared"]]}},
        "identity": {"name": name},
    }


def published_duck(pond):
    uuid = create_species(pond.gm, pond.world)
    resp = publish(pond.gm, pond.world, uuid)
    assert resp.status_code == 201, resp.get_json()
    return uuid, resp.get_json()["revision"]


def duck_character(pond, data, skill="athletik"):
    _, revision = published_duck(pond)
    sid = species_profiles.species_id(revision["id"])
    draft = pond.player.post(f"{BASE}/drafts", json={"state": duck_state(data, sid, skill)})
    assert draft.status_code == 201, draft.get_json()
    resp = pond.player.post(f"{BASE}/drafts/{draft.get_json()['draft']['id']}/finalize", json={"version": 1, "campaign_id": pond.campaign})
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["character"], revision


def live_session(pond):
    campaign_map = CampaignMap(campaign_id=pond.campaign, name="Teich", width=20, height=20, created_by=pond.gm.user_id)
    db.session.add(campaign_map)
    db.session.flush()
    session = GameSession(campaign_id=pond.campaign, map_id=campaign_map.id, name="Abend am Teich", status="in_progress")
    db.session.add(session)
    db.session.commit()
    return session.id


# ------------------------------------------------------------------ conversion (pure)

def test_duckfolk_converts_to_a_2024_profile():
    result = conversion.inspect(copy.deepcopy(DUCKFOLK), copy.deepcopy(SUPPLEMENT), skills=skills())
    assert result["playable"] is True and result["edition"] == "2024"
    profile = result["profile"]
    assert profile["name"] == "Duckfolk" and profile["creatureType"]["label"] == "Humanoide"
    assert profile["sizes"] == [{"key": "sm", "label": "Klein"}]
    assert [(m["mode"], m["feet"], m["meters"]) for m in profile["movement"]] == [("walk", 30, 9.0), ("swim", 30, 9.0)]
    assert profile["senses"] == [] and profile["description"] == "Kleines Entenvolk mit lautem Quaken."
    assert profile["skillChoices"] == [{"id": "duck-skill", "label": "Entenfertigkeit", "options": ["athletik", "wahrnehmung"]}]
    action = profile["actions"][0]
    assert (action["kind"], action["uses"], action["rangeFeet"], action["maxWeightLb"], action["maxMoveFeet"]) == ("object-telekinesis", "at-will", 30, 10, 30)
    assert "no-damage" in action["restrictions"] and "no-creature" in action["restrictions"]
    assert {e["code"] for e in result["entries"]} >= {"size", "movement", "no-darkvision", "skill-choice", "action"}
    entry = species_profiles.species_entry(profile, "homebrew.species.7")
    assert (entry["sizes"], entry["speedMeters"], entry["darkvisionMeters"]) == (["Klein"], 9.0, None)


def _changed(path, value):
    doc = copy.deepcopy(DUCKFOLK)
    node = doc
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return doc


@pytest.mark.parametrize("doc, supplement, code", [
    (_changed(("system", "source", "rules"), "2014"), SUPPLEMENT, "edition-2014"),
    (_changed(("system", "advancement"), [*DUCKFOLK["system"]["advancement"], {"_id": "t1", "type": "Trait", "configuration": {"grants": ["skills:ath"]}}]), SUPPLEMENT, "advancement-unsupported"),
    (_changed(("system", "advancement"), [*DUCKFOLK["system"]["advancement"], {"_id": "g1", "type": "ItemGrant", "configuration": {"items": [{"uuid": "Compendium.world.eagle-feats-2024.Item.X1"}]}}]), SUPPLEMENT, "advancement-unsupported"),
    (_changed(("system", "advancement"), []), SUPPLEMENT, "size-missing"),
    (_changed(("system", "description", "value"), "<p>Siehe @UUID[Item.abc]{Quaken}</p>"), SUPPLEMENT, "description-reference"),
    (_changed(("effects",), [{"name": "Bonus", "changes": [{"key": "system.attributes.ac.bonus", "value": "1"}]}]), SUPPLEMENT, "effects-unsupported"),
    (_changed(("system", "movement", "walk"), "@scale.duck.speed"), SUPPLEMENT, "formula"),
    (_changed(("system", "type", "value"), ""), SUPPLEMENT, "creature-type-missing"),
    (_changed(("name",), ""), SUPPLEMENT, "name-invalid"),
    (_changed(("system", "description", "chat"), "Hidden rule"), SUPPLEMENT, "description-unsupported"),
    (_changed(("system", "senses", "ranges"), {"darkvision": 0, "echolocation": 60}), SUPPLEMENT, "sense-unsupported"),
    (_changed(("system", "activities"), {"a1": {"type": "attack"}}), SUPPLEMENT, "field-unsupported"),
    (DUCKFOLK, {**SUPPLEMENT, "actions": [{**SUPPLEMENT["actions"][0], "uses": "1/long-rest"}]}, "action-uses"),
    (DUCKFOLK, {**SUPPLEMENT, "actions": [{**SUPPLEMENT["actions"][0], "kind": "fireball"}]}, "action-kind"),
    (DUCKFOLK, {**SUPPLEMENT, "skillChoices": [{"id": "x", "label": "X", "options": ["athletik", "gibt-es-nicht"]}]}, "skill-options"),
    (DUCKFOLK, {**SUPPLEMENT, "resistances": ["fire"]}, "supplement-invalid"),
])
def test_unsupported_or_2014_content_blocks_publication_with_a_diagnostic(doc, supplement, code):
    result = conversion.inspect(copy.deepcopy(doc), copy.deepcopy(supplement), skills=skills())
    assert result["playable"] is False and result["profile"] is None
    blocked = [e for e in result["entries"] if e["status"] == "blocked"]
    assert code in {e["code"] for e in blocked}, blocked
    assert all(e["path"] and e["message"] for e in blocked)


def test_homebrew_skill_choice_is_a_generic_grant_and_srd_paths_are_unchanged(data):
    profile = conversion.inspect(copy.deepcopy(DUCKFOLK), copy.deepcopy(SUPPLEMENT), skills=skills())["profile"]
    sid = "homebrew.species.41"
    rules = species_profiles.with_species(data, species_profiles.species_entry(profile, sid))
    assert len(data["species"]) == len(rules["species"]) - 1, "the cached creator data is not modified"
    seeing = evaluate(rules, duck_state(data, sid, "wahrnehmung"))
    assert seeing["complete"], seeing["findings"]
    assert seeing["skills"]["wahrnehmung"]["proficiency"] == "proficient" and seeing["passivePerception"] == 14
    assert seeing["skills"]["athletik"]["proficiency"] == "none" and seeing["speedMeters"] == 9.0
    wrong = evaluate(rules, {**duck_state(data, sid), "species": {"id": sid, "choices": {"duck-skill": "heimlichkeit"}}})
    assert "species-choice-invalid" in {f["code"] for f in wrong["findings"]}
    assert wrong["skills"]["heimlichkeit"]["proficiency"] == "none"
    srd = wizard_state(data)
    assert species_profiles.rules_data_for_block({"state": srd}) is load_creator_data()
    assert evaluate(species_profiles.rules_data_for_block({"state": srd}), srd) == evaluate(data, srd)


# ------------------------------------------------------------------ author: check and publish

def test_author_checks_and_publishes_an_immutable_campaign_revision(pond):
    uuid = create_species(pond.gm, pond.world)
    checked = check(pond.gm, pond.world, uuid).get_json()
    assert checked["report"]["playable"] is True and checked["profile"]["name"] == "Duckfolk"
    assert checked["source"]["digest"].startswith("sha256:") and checked["publications"] == []
    body = {"world": pond.world, "uuid": uuid, "supplement": SUPPLEMENT}
    assert pond.gm.post(f"{CE}/species/publish", json=body).status_code == 409, "no publication without the checked digest"
    first = publish(pond.gm, pond.world, uuid)
    assert first.status_code == 201
    revision = first.get_json()["revision"]
    assert revision["revision"] == 1 and revision["scope"] == {"kind": "campaign", "id": pond.campaign}
    again = publish(pond.gm, pond.world, uuid)
    assert again.status_code == 200 and again.get_json()["created"] is False
    stale = pond.gm.post(f"{CE}/species/publish", json={**body, "expectedDigest": checked["source"]["digest"]})
    assert stale.status_code == 200, "same digest, same profile: idempotent"
    pond.gm.post(f"{CE}/request", json={"world": pond.world, "type": "document.update", "payload": {"uuid": uuid, "changes": {"name": "Duckfolk II"}}})
    changed = pond.gm.post(f"{CE}/species/publish", json={**body, "expectedDigest": checked["source"]["digest"]})
    assert changed.status_code == 409 and changed.get_json()["error"] == "source-changed"
    assert CeSpeciesRevision.query.count() == 1
    listing = pond.gm.get(f"{CE}/species/publications").get_json()["publications"]
    assert [row["id"] for row in listing] == [revision["id"]] and listing[0]["supplement"] == SUPPLEMENT
    for name in ("player", "stranger"):
        client = getattr(pond, name)
        assert check(client, pond.world, uuid).status_code == 403
        assert client.post(f"{CE}/species/publish", json={**body, "expectedDigest": "x"}).status_code == 403


def test_2014_species_is_refused_with_an_actionable_report(pond):
    uuid = create_species(pond.gm, pond.world, _changed(("system", "source", "rules"), "2014"), "Duck14")
    report = check(pond.gm, pond.world, uuid).get_json()["report"]
    assert report["playable"] is False and report["edition"] == "2014"
    entry = next(e for e in report["entries"] if e["code"] == "edition-2014")
    assert entry["path"] == "system.source.rules" and "2024" in entry["message"]
    resp = publish(pond.gm, pond.world, uuid)
    assert resp.status_code == 422 and resp.get_json()["error"] == "not-playable"
    assert CeSpeciesRevision.query.count() == 0


def test_source_only_change_gets_a_new_provenance_revision(pond):
    uuid = create_species(pond.gm, pond.world)
    first = publish(pond.gm, pond.world, uuid).get_json()["revision"]
    changed = pond.gm.post(f"{CE}/request", json={"world": pond.world, "type": "document.update",
                                            "payload": {"uuid": uuid, "changes": {"img": "icons/svg/duck.svg"}}})
    assert changed.get_json()["ok"] is True
    second = publish(pond.gm, pond.world, uuid).get_json()["revision"]
    assert second["revision"] == 2 and second["profileDigest"] == first["profileDigest"]
    assert second["sourceDigest"] != first["sourceDigest"]


def test_flag_off_hides_publishing_and_the_catalog(pond):
    published_duck(pond)
    pond.app.config["CE_PLAYABLE_SPECIES"] = False
    assert check(pond.gm, pond.world, "Item.Duck01").status_code == 404
    assert pond.player.get(f"{BASE}/species-catalog").get_json() == {"enabled": False, "species": []}


# ------------------------------------------------------------------ player: catalog, choice, finalize, sheet

def test_catalog_respects_personal_and_campaign_scope(pond, data):
    _, revision = published_duck(pond)
    names = lambda client: [(s["name"], s["origin"]["scope"]["kind"]) for s in client.get(f"{BASE}/species-catalog").get_json()["species"]]  # noqa: E731
    assert names(pond.player) == [("Duckfolk", "campaign")] and names(pond.gm) == [("Duckfolk", "campaign")]
    assert names(pond.stranger) == []
    own = create_species(pond.stranger, "personal", doc_id="Goose1")
    assert publish(pond.stranger, "personal", own).status_code == 201
    assert names(pond.stranger) == [("Duckfolk", "personal")] and names(pond.player) == [("Duckfolk", "campaign")]
    # A client-supplied revision id does not bypass the scope check.
    sid = species_profiles.species_id(revision["id"])
    resp = pond.stranger.post(f"{BASE}/drafts", json={"state": duck_state(data, sid)})
    assert resp.status_code == 422 and resp.get_json()["problems"][0]["path"] == "species.id"
    assert pond.stranger.post(f"{BASE}/evaluate", json={"state": duck_state(data, sid)}).status_code == 422
    assert pond.stranger.post(f"{BASE}/drafts", json={"state": duck_state(data, "homebrew.species.99999")}).status_code == 422
    entry = pond.player.get(f"{BASE}/species-catalog").get_json()["species"][0]
    assert entry["id"] == sid and entry["homebrew"] is True and entry["origin"]["actions"][0]["summary"]


def test_player_builds_a_duckfolk_and_the_server_derives_the_chosen_skill(pond, data):
    _, revision = published_duck(pond)
    sid = species_profiles.species_id(revision["id"])
    draft = pond.player.post(f"{BASE}/drafts", json={"state": duck_state(data, sid)}).get_json()
    assert draft["blockers"] == [] and draft["evaluation"]["skills"]["athletik"]["proficiency"] == "proficient"
    url = f"{BASE}/drafts/{draft['draft']['id']}/finalize"
    outside = pond.player.post(url, json={"version": 1})
    assert outside.status_code == 422 and outside.get_json()["error"] == "species_campaign_required"
    assert Character.query.count() == 0
    resp = pond.player.post(url, json={"version": 1, "campaign_id": pond.campaign})
    assert resp.status_code == 201, resp.get_json()
    char = resp.get_json()["character"]
    assert char["species"] == "Duckfolk"
    row = db.session.get(Character, char["id"])
    pin = row.character_data["srd"]["speciesPin"]
    assert pin["revisionId"] == revision["id"] and pin["digest"] == revision["profileDigest"] and pin["profile"]["name"] == "Duckfolk"
    sheet = pond.player.get(f"{BASE}/characters/{char['id']}").get_json()
    skills_view = sheet["evaluation"]["skills"]
    assert skills_view["athletik"] == {**skills_view["athletik"], "proficiency": "proficient", "bonus": 1}
    assert skills_view["wahrnehmung"]["proficiency"] == "none" and sheet["evaluation"]["speedMeters"] == 9.0
    assert sheet["evaluation"] == row.character_data["srd"]["derived"]
    origin = sheet["speciesOrigin"]
    assert origin["revision"] == 1 and origin["senses"] == [] and [m["mode"] for m in origin["movement"]] == ["walk", "swim"]
    assert origin["actions"][0]["id"] == "telekinetic-quack" and origin["canAct"] is True
    rolled = pond.player.post(f"{BASE}/characters/{char['id']}/roll", json={"kind": "skill", "key": "athletik"}).get_json()
    assert rolled["dice"] == "1d20+1"
    party = pond.gm.get(f"{BASE}/campaigns/{pond.campaign}/party")
    assert party.status_code == 200 and party.get_json()["isDm"] is True
    duck = next(r for r in party.get_json()["characters"] if r["id"] == char["id"])
    assert duck["species"] == "Duckfolk" and duck["speedMeters"] == 9.0
    assert duck["origin"]["name"] == "Duckfolk" and duck["origin"]["senses"] == []
    assert [m["mode"] for m in duck["origin"]["movement"]] == ["walk", "swim"]
    assert duck["origin"]["actions"][0]["name"] == "Telekinetisches Quaken" and "Spielleitung" in duck["origin"]["actions"][0]["summary"]


def test_pinned_character_survives_edit_republish_and_delete_of_the_source(pond, data):
    char, revision = duck_character(pond, data)
    uuid = "Item.Duck01"
    pond.gm.post(f"{CE}/request", json={"world": pond.world, "type": "document.update", "payload": {
        "uuid": uuid, "changes": {"name": "Duckfolk Deluxe", "system.movement": {"walk": 40, "swim": 30, "units": "ft"}}}})
    second = publish(pond.gm, pond.world, uuid)
    assert second.status_code == 201 and second.get_json()["revision"]["revision"] == 2
    assert pond.gm.delete(f"{CE}/document", query_string={"world": pond.world, "uuid": uuid}).status_code == 200
    sheet = pond.player.get(f"{BASE}/characters/{char['id']}").get_json()
    assert sheet["speciesOrigin"]["name"] == "Duckfolk" and sheet["speciesOrigin"]["revisionId"] == revision["id"]
    assert sheet["evaluation"]["speedMeters"] == 9.0 and db.session.get(Character, char["id"]).race == "Duckfolk"
    catalog = pond.player.get(f"{BASE}/species-catalog").get_json()["species"]
    assert [(s["name"], s["origin"]["revision"]) for s in catalog] == [("Duckfolk Deluxe", 2)]


def test_level_up_and_down_recompute_from_the_pin_without_duplicate_grants(pond, data):
    char, _ = duck_character(pond, data)
    cid = char["id"]
    assert pond.gm.put(f"{BASE}/characters/{cid}/progression", json={"addXp": 300}).status_code == 200
    wizard = next(c for c in data["classes"] if c["classKey"] == "wizard")
    casting = wizard["spellcasting"]
    row2 = next(r for r in casting["levels"] if r["level"] == 2)
    level1 = [s for s in data["spellLists"]["wizard"] if data["spells"][s]["level"] == 1]
    book = level1[:casting["spellbook"]["startingSpells"] + casting["spellbook"]["perLevel"]]
    cantrips = [s for s in data["spellLists"]["wizard"] if data["spells"][s]["level"] == 0][:row2["cantrips"]]
    payload = {"classKey": "wizard", "expectedLevel": 1, "hp": "fixed",
               "spells": {"cantrips": cantrips, "spellbook": book, "prepared": book[:row2["prepared"]]}}
    expertise = sum(c.get("count", 0) for c in wizard["featureChoices"] if c["kind"] == "expertise" and c["level"] <= 2)
    if expertise:
        payload["expertise"] = ["arkane-kunde"][:expertise]
    preview = pond.player.post(f"{BASE}/characters/{cid}/level-up/preview", json=payload).get_json()
    assert preview.get("blockers") == [], preview
    up = pond.player.post(f"{BASE}/characters/{cid}/level-up", json=payload)
    assert up.status_code == 200, up.get_json()
    evaluation = up.get_json()["evaluation"]
    assert evaluation["level"] == 2 and evaluation["skills"]["athletik"]["proficiency"] == "proficient"
    assert not [f for f in evaluation["findings"] if f["code"].startswith("species")]
    row = db.session.get(Character, cid)
    assert row.character_data["srd"]["speciesPin"]["revisionId"] and row.race == "Duckfolk"
    down = pond.player.post(f"{BASE}/characters/{cid}/level-down", json={"expectedLevel": 2})
    assert down.status_code == 200, down.get_json()
    assert down.get_json()["evaluation"]["skills"]["athletik"]["proficiency"] == "proficient"


# ------------------------------------------------------------------ transfer: duplicate, rebuild, export/import, campaigns

def test_duplicate_rebuild_export_and_import_keep_or_refuse_the_pin(pond, data):
    char, revision = duck_character(pond, data)
    cid = char["id"]
    copy_resp = pond.player.post(f"{BASE}/characters/{cid}/duplicate")
    assert copy_resp.status_code == 201
    copy_id = copy_resp.get_json()["character"]["id"]
    assert db.session.get(Character, copy_id).character_data["srd"]["speciesPin"]["revisionId"] == revision["id"]
    other = Campaign(name="Fremder Teich", description="", owner_id=pond.player.user_id, status="active", max_players=6)
    db.session.add(other)
    db.session.commit()
    moved = pond.player.put(f"/api/characters/{copy_id}/campaign", json={"campaign_id": other.id})
    assert moved.status_code == 409 and moved.get_json()["code"] == "species_campaign_only"
    assert pond.player.put(f"/api/characters/{copy_id}/campaign", json={"campaign_id": pond.campaign}).status_code == 200
    rebuilt = pond.player.post(f"{BASE}/characters/{cid}/to-draft")
    assert rebuilt.status_code == 201
    exported = pond.player.get(f"{BASE}/characters/{cid}/export").get_json()
    assert exported["speciesPin"] == {"revisionId": revision["id"], "digest": revision["profileDigest"], "name": "Duckfolk"}
    count = Character.query.count()
    imported = pond.player.post(f"{BASE}/characters/import", json=exported)
    assert imported.status_code == 201, imported.get_json()
    new = db.session.get(Character, imported.get_json()["character"]["id"])
    assert new.character_data["srd"]["speciesPin"]["profile"] == db.session.get(Character, cid).character_data["srd"]["speciesPin"]["profile"]
    refused = pond.stranger.post(f"{BASE}/characters/import", json=exported)
    assert refused.status_code == 422 and "Duckfolk" in refused.get_json()["message"]
    forged = copy.deepcopy(exported)
    forged["speciesPin"]["digest"] = "sha256:forged"
    assert pond.player.post(f"{BASE}/characters/import", json=forged).status_code == 422
    assert Character.query.count() == count + 1
    # Leaving the campaign takes away the right to build new characters with its Species; the pinned one stays.
    CampaignMember.query.filter_by(campaign_id=pond.campaign, user_id=pond.player.user_id).update({"status": "removed"})
    db.session.commit()
    gone = pond.player.post(f"{BASE}/characters/{cid}/to-draft")
    assert gone.status_code == 409 and gone.get_json()["error"] == "species_unavailable"
    assert pond.player.get(f"{BASE}/species-catalog").get_json()["species"] == []
    assert db.session.get(Character, cid).character_data["srd"]["speciesPin"]["profile"]["name"] == "Duckfolk"


# ------------------------------------------------------------------ table: telekinesis

def test_telekinesis_is_declared_once_per_key_by_owner_or_dm(pond, data):
    char, _ = duck_character(pond, data)
    url = f"{BASE}/characters/{char['id']}/species-actions/telekinetic-quack"
    assert pond.player.post(url, json={**DECLARATION, "idempotencyKey": "quack-0001"}).status_code == 409, "needs a live session"
    session_id = live_session(pond)
    first = pond.player.post(url, json={**DECLARATION, "idempotencyKey": "quack-0001"})
    assert first.status_code == 201, first.get_json()
    receipt = first.get_json()
    message = db.session.get(ChatMessage, receipt["messageId"])
    assert message.game_session_id == session_id and message.content_type == "species_action"
    assert message.author_user_id == pond.player.user_id and message.visibility == "public"
    assert "Telekinetisches Quaken" in message.content and "der Schlüssel auf dem Tisch" in message.content
    retry = pond.player.post(url, json={**DECLARATION, "idempotencyKey": "quack-0001"})
    assert retry.status_code == 200 and retry.get_json() == {**receipt, "duplicate": True}
    changed_retry = pond.player.post(url, json={**DECLARATION, "object": "ein anderes Buch", "idempotencyKey": "quack-0001"})
    assert changed_retry.status_code == 409 and changed_retry.get_json()["error"] == "idempotency_conflict"
    assert ChatMessage.query.filter_by(content_type="species_action").count() == 1
    assert pond.gm.post(url, json={**DECLARATION, "idempotencyKey": "dm-quack-01"}).status_code == 201
    assert pond.stranger.post(url, json={**DECLARATION, "idempotencyKey": "evil-quack-1"}).status_code == 403
    for bad in ({"weightLb": 11}, {"distanceFeet": 31}, {"moveFeet": 0}, {"unattended": False}, {"object": "x"}, {"targetCreature": "Goblin"}):
        resp = pond.player.post(url, json={**DECLARATION, **bad, "idempotencyKey": "bad-quack-01"})
        assert resp.status_code == 422 and resp.get_json()["problems"], bad
    assert pond.player.post(url, json=DECLARATION).status_code == 400
    assert pond.player.post(f"{BASE}/characters/{char['id']}/species-actions/fireball", json={**DECLARATION, "idempotencyKey": "quack-0002"}).status_code == 404
    assert ChatMessage.query.filter_by(content_type="species_action").count() == 2


def test_srd_characters_have_no_species_actions_or_origin(pond, data):
    srd = finalized(pond.player, data)
    sheet = pond.player.get(f"{BASE}/characters/{srd['id']}").get_json()
    assert sheet["speciesOrigin"] is None and "speciesPin" not in sheet["srd"]
    resp = pond.player.post(f"{BASE}/characters/{srd['id']}/species-actions/telekinetic-quack", json={**DECLARATION, "idempotencyKey": "quack-0003"})
    assert resp.status_code == 404
    assert "speciesPin" not in pond.player.get(f"{BASE}/characters/{srd['id']}/export").get_json()
    assert species_catalog.campaign_problem(None, 5) is None
