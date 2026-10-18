"""P12: JSON export/import, printable PDF and colour themes of SRD characters."""

import copy
import json

from reportlab import rl_config

from vtt.characters import srd_export, srd_pdf
from vtt.extensions import db
from vtt.models import Character

from tests.test_srd_creator_api import BASE, _client, app, client, data, make_draft, other, wizard_state  # noqa: F401
from tests.test_srd_inventory import STAFF, add, inv
from tests.test_srd_rolls import table  # noqa: F401

IMPORT = f"{BASE}/characters/import"


def built(client, data):
    state = wizard_state(data)
    state["identity"] = {"name": "Mira Eulenfeder", "backstory": "Fand eine Eule im Archiv.", "pronouns": "sie/ihr"}
    draft = make_draft(client, state)["draft"]
    char = client.post(f"{BASE}/drafts/{draft['id']}/finalize", json={"version": 1}).get_json()["character"]
    cid = char["id"]
    add(client, cid, STAFF)
    client.put(f"{BASE}/characters/{cid}/inventory/coins", json={"coins": {"GM": 42, "SM": 7}})
    client.post(inv(client, cid), json={"custom": {"name": "Eulenfeder", "weightKg": 0.1, "quantity": 3, "description": "Weich."}})
    client.put(f"{BASE}/characters/{cid}/companions", json={"companions": [{"name": "Rabe", "hpMax": 1, "hpCurrent": 1, "ac": 12}]})
    return cid


def export(client, cid):
    resp = client.get(f"{BASE}/characters/{cid}/export")
    assert resp.status_code == 200, resp.get_json()
    return resp, json.loads(resp.data)


# ------------------------------------------------------------------ export and import

def test_export_is_owner_only_and_carries_no_account_data(app, client, other, data):
    cid = built(client, data)
    resp, doc = export(client, cid)
    assert resp.headers["Content-Disposition"].startswith('attachment; filename="mira-eulenfeder.rollcharakter')
    assert resp.headers["Cache-Control"] == "private, no-store"
    assert doc["format"] == "roll-drauf-srd-character" and doc["version"] == 1 and doc["ruleset"] == "srd-5.2.1-de"
    assert doc["state"]["identity"]["backstory"] == "Fand eine Eule im Archiv."
    assert doc["inventory"]["coins"]["GM"] == 42 and {i["name"] for i in doc["inventory"]["items"]} == {"Kampfstab", "Eulenfeder"}
    assert [c["name"] for c in doc["companions"]] == ["Rabe"] and all("id" not in c for c in doc["companions"])
    text = resp.get_data(as_text=True)
    for secret in ("srd_owner", "campaign", "sharing", "history", "user_id", "handedOutBy"):
        assert secret not in text, secret
    assert other.get(f"{BASE}/characters/{cid}/export").status_code == 403
    assert client.get(f"{BASE}/characters/99999/export").status_code == 404
    plain = client.post("/api/characters", json={"name": "Plain", "level": 1}).get_json()["id"]
    assert client.get(f"{BASE}/characters/{plain}/export").status_code == 422


def test_import_roundtrip_creates_an_independent_equal_character(app, client, other, data):
    cid = built(client, data)
    client.put(f"{BASE}/characters/{cid}/appearance", json={"theme": "glutrot"})
    _, doc = export(client, cid)
    doc["character"]["hpCurrent"] = 10
    resp = other.post(IMPORT, json=doc)
    assert resp.status_code == 201, resp.get_json()
    new = resp.get_json()["character"]
    assert new["id"] != cid and new["name"] == "Mira Eulenfeder" and new["hp"].startswith("10/") and new["campaign_id"] is None
    original = client.get(f"{BASE}/characters/{cid}").get_json()
    copy_ = other.get(f"{BASE}/characters/{new['id']}").get_json()
    assert copy_["evaluation"] == original["evaluation"]
    assert copy_["srd"]["state"] == original["srd"]["state"] and copy_["srd"]["draftId"] is None
    assert copy_["srd"]["history"][-1]["type"] == "import" and len(copy_["srd"]["history"]) == 1
    body = other.get(inv(other, new["id"])).get_json()
    assert {i["name"]: i["quantity"] for i in body["items"]} == {"Kampfstab": 1, "Eulenfeder": 3} and body["coins"]["GM"] == 42
    assert other.get(f"{BASE}/characters/{new['id']}/companions").get_json()["companions"][0]["name"] == "Rabe"
    assert other.get(f"{BASE}/characters/{new['id']}/appearance").get_json()["theme"] == "glutrot"
    assert client.get(f"{BASE}/characters/{new['id']}").status_code == 403
    with app.app_context():
        assert db.session.get(Character, new["id"]).user_id != db.session.get(Character, cid).user_id
    again = export(other, new["id"])[1]
    assert again["state"] == doc["state"] and again["inventory"]["coins"] == doc["inventory"]["coins"]


def test_import_rejects_foreign_tampered_and_oversized_files(app, client, other, data):
    cid = built(client, data)
    _, doc = export(client, cid)

    def code(body):
        resp = client.post(IMPORT, json=body)
        assert resp.status_code in (400, 413, 422), resp.get_json()
        return resp.get_json()["error"]

    assert code({"format": "other"}) == "import_invalid"
    assert code({**doc, "version": 2}) == "import_invalid"
    assert code({**doc, "ruleset": "srd-9"}) == "import_invalid"
    assert code({**doc, "state": {"levels": []}}) == "import_invalid"
    assert code({**doc, "state": {**doc["state"], "derived": {"hp": 999}}}) == "import_invalid"
    unfinished = copy.deepcopy(doc)
    unfinished["state"]["skills"] = []
    unfinished["state"]["levels"] = unfinished["state"]["levels"][:1] + [{"classKey": "unbekannt"}]
    assert code(unfinished) == "import_invalid"
    broken = copy.deepcopy(doc)
    broken["inventory"]["items"].append({"name": "x", "quantity": 0})
    assert code(broken) == "import_invalid"
    broken = copy.deepcopy(doc)
    broken["inventory"]["coins"]["GM"] = -1
    assert code(broken) == "import_invalid"
    broken = copy.deepcopy(doc)
    broken["progression"] = {"mode": "lauwarm"}
    assert code(broken) == "import_invalid"
    broken = copy.deepcopy(doc)
    broken["companions"] = [{"name": ""}]
    assert code(broken) == "import_invalid"
    assert client.post(IMPORT, data="kein json", content_type="application/json").status_code == 400
    assert client.post(IMPORT, json=[1]).status_code == 400
    assert client.post(IMPORT, data=b"x" * (srd_export.MAX_BYTES + 10), content_type="application/json").status_code == 413
    assert client.post(f"{BASE}/characters/import", json=doc).status_code == 201
    with app.app_context():
        assert Character.query.filter_by(name="Mira Eulenfeder").count() == 2


def test_import_keeps_a_failed_file_from_leaving_a_character_behind(app, client, data):
    cid = built(client, data)
    _, doc = export(client, cid)
    doc["companions"] = [{"name": "A"}, {"name": "B", "ac": 99}]
    with app.app_context():
        before = Character.query.count()
    assert client.post(IMPORT, json=doc).status_code == 422
    with app.app_context():
        assert Character.query.count() == before


# ------------------------------------------------------------------ PDF

def test_pdf_is_a_violet_a4_sheet_and_private_text_stays_with_the_owner(app, client, other, data, monkeypatch):
    cid = built(client, data)
    resp = client.get(f"{BASE}/characters/{cid}/pdf")
    assert resp.status_code == 200 and resp.mimetype == "application/pdf" and resp.data.startswith(b"%PDF")
    assert resp.headers["Content-Disposition"].endswith('.pdf"') and resp.headers["Cache-Control"] == "private, no-store"
    monkeypatch.setattr(rl_config, "useA85", 0)
    with app.app_context():
        char = db.session.get(Character, cid)
        mine = srd_pdf.render_pdf(char, private=True, compress=False).decode("latin-1")
        public = srd_pdf.render_pdf(char, private=False, compress=False).decode("latin-1")
    for text in (mine, public):
        assert ".294118 .137255 .352941 rg" in text  # #4b235a fills
        assert "Mira Eulenfeder" in text and "Kampfstab" in text and "Eulenfeder" in text and "Rabe" in text
        assert "Zauber-SG" in text and "Rettungswurf" in text
    assert "Fand eine Eule" in mine and "Fand eine Eule" not in public
    assert other.get(f"{BASE}/characters/{cid}/pdf").status_code == 403
    plain = client.post("/api/characters", json={"name": "Plain", "level": 1}).get_json()["id"]
    assert client.get(f"{BASE}/characters/{plain}/pdf").status_code == 422


def test_campaign_members_get_the_pdf_without_private_text(app, client, other, data, monkeypatch):
    t = table(app, client, other, data)
    pdf = other.get(f"{BASE}/characters/{t['char']['id']}/pdf")
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF")
    assert t["dm"].get(f"{BASE}/characters/{t['char']['id']}/pdf").status_code == 200
    assert _client(app, "srd_stranger").get(f"{BASE}/characters/{t['char']['id']}/pdf").status_code == 403


def test_pdf_survives_awkward_text(app, client, data):
    state = wizard_state(data)
    state["identity"] = {"name": "Ærin <b>Ü</b> & „Zoë“ → 日本", "notes": "Zeile 1\nZeile 2 </para>"}
    draft = make_draft(client, state)["draft"]
    cid = client.post(f"{BASE}/drafts/{draft['id']}/finalize", json={"version": 1}).get_json()["character"]["id"]
    resp = client.get(f"{BASE}/characters/{cid}/pdf")
    assert resp.status_code == 200 and resp.data.startswith(b"%PDF")


# ------------------------------------------------------------------ themes

def test_theme_is_chosen_by_the_owner_and_shown_to_readers(app, client, other, data):
    t = table(app, client, other, data)
    cid = t["char"]["id"]
    url = f"{BASE}/characters/{cid}/appearance"
    body = client.get(url).get_json()
    assert body["theme"] == "violett" and body["canEdit"] is True and len(body["themes"]) == 6
    assert body["themes"][0]["accent"] == "#4b235a"
    assert other.get(url).get_json()["canEdit"] is False
    assert other.put(url, json={"theme": "meerblau"}).status_code == 403
    assert client.put(url, json={"theme": "pink"}).get_json()["error"] == "invalid_theme"
    assert client.put(url, json={}).status_code == 422
    assert client.put(url, json={"theme": "meerblau"}).get_json()["theme"] == "meerblau"
    mira = next(r for r in client.get(f"{BASE}/campaigns/{t['campaign']}/party").get_json()["characters"] if r["id"] == cid)
    assert mira["accent"] == "#1d4e7a"
    shared = client.put(f"{BASE}/characters/{cid}/sharing", json={"enabled": True}).get_json()
    view = _client(app, "srd_stranger").get(f"{BASE}/shared/{shared['token']}").get_json()
    assert view["accent"] == "#1d4e7a"
