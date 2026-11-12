"""C02: the sheet's additive owner-only permissions projection and the existing copy/identity endpoints.

The projection is a UI hint only; every write route keeps its own owner check, so each test
also tries the mutation as the non-owner instead of trusting the projected flags."""

from base64 import b64decode
from datetime import datetime
from io import BytesIO

import pytest

from tests.test_srd_creator_api import BASE, _client, app, client, data, finalized, other  # noqa: F401
from vtt.extensions import db
from vtt.models import Campaign, CampaignMember, Character

PNG_BYTES = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlH0uoAAAAASUVORK5CYII="
)
NONE = {"editCore": False, "editIdentity": False, "copy": False}
OWNER = {"editCore": True, "editIdentity": True, "copy": True}


@pytest.fixture(autouse=True)
def _isolated_storage(app, tmp_path):
    app.config["LOCAL_STORAGE_PATH"] = str(tmp_path / "c02-storage")


def _campaign(app, dm_id, member_ids, character_id):
    with app.app_context():
        campaign = Campaign(name="Rolltisch", description="", owner_id=dm_id, status="active", max_players=6)
        db.session.add(campaign)
        db.session.flush()
        for user_id, role in [(dm_id, "DM")] + [(m, "Player") for m in member_ids]:
            db.session.add(CampaignMember(
                campaign_id=campaign.id, user_id=user_id, campaign_role=role, status="active",
                joined_at=datetime.utcnow(), invited_at=datetime.utcnow(), accepted_at=datetime.utcnow(), invited_by=dm_id))
        db.session.get(Character, character_id).campaign_id = campaign.id
        db.session.commit()
        return campaign.id


def _projection(client, char_id):
    response = client.get(f"/api/characters/{char_id}/sheet")
    assert response.status_code == 200, response.get_json()
    return response.get_json()["character"].get("permissions")


def test_owner_gets_the_projection_on_srd_and_plain_sheets(client, data):
    srd = finalized(client, data)
    plain = client.post("/api/characters", json={"name": "Alt"}).get_json()
    assert _projection(client, srd["id"]) == OWNER
    assert _projection(client, plain["id"]) == OWNER


def test_shared_reader_and_campaign_dm_get_no_owner_actions(app, client, other, data):
    char = finalized(client, data)
    dm = _client(app, "srd_dm")
    _campaign(app, dm.user_id, [other.user_id], char["id"])

    assert _projection(other, char["id"]) == NONE
    # No global DM / campaign-owner fallback: the DM reads the sheet but owns none of the actions.
    assert _projection(dm, char["id"]) == NONE

    for who in (other, dm):
        assert who.put(f"/api/characters/{char['id']}", json={"name": "Fremd"}).status_code == 403
        assert who.post(f"/api/characters/{char['id']}/identity/avatar",
                        data={"file": (BytesIO(PNG_BYTES), "a.png")}, content_type="multipart/form-data").status_code == 403
        assert who.delete(f"/api/characters/{char['id']}/identity/avatar").status_code == 403
        assert who.post(f"{BASE}/characters/{char['id']}/duplicate").status_code == 403
    with app.app_context():
        assert db.session.get(Character, char["id"]).name == "Mira Eulenfeder"
        assert Character.query.count() == 1


def test_unrelated_user_is_refused_and_sees_no_projection(client, other, data):
    char = finalized(client, data)
    response = other.get(f"/api/characters/{char['id']}/sheet")
    assert response.status_code == 403
    assert "permissions" not in (response.get_json() or {})


def test_projection_is_not_stored_and_cannot_be_forged(app, client, other, data):
    plain = client.post("/api/characters", json={"name": "Alt"}).get_json()
    assert "permissions" not in client.get(f"/api/characters/{plain['id']}").get_json()
    # A forged flag inside the stored document does not change what the server projects for others.
    client.put(f"/api/characters/{plain['id']}", json={"character_data": {"permissions": OWNER}})
    assert "permissions" not in Character.__table__.columns
    assert other.get(f"/api/characters/{plain['id']}/sheet").status_code == 403
    assert _projection(client, plain["id"]) == OWNER


def test_default_editing_does_not_open_computed_srd_fields(client, data):
    char = finalized(client, data)
    assert _projection(client, char["id"])["editCore"] is True
    # editCore only covers the fields the generic API already allowed.
    assert client.put(f"/api/characters/{char['id']}", json={"name": "Neu", "hp_current": 3}).status_code == 200
    for field in ({"xp": 10}, {"level": 9}, {"ac": 30}, {"str": 20}, {"character_data": {}}):
        assert client.put(f"/api/characters/{char['id']}", json=field).status_code == 409, field


def test_owner_identity_upload_replace_remove_roundtrip(app, client, data):
    char = finalized(client, data)
    url = f"/api/characters/{char['id']}/identity/avatar"
    assert client.post(url, data={"file": (BytesIO(PNG_BYTES), "one.png")}, content_type="multipart/form-data").status_code == 200
    assert client.post(url, data={"file": (BytesIO(PNG_BYTES), "two.png")}, content_type="multipart/form-data").status_code == 200
    sheet = client.get(f"/api/characters/{char['id']}/sheet").get_json()["character"]
    assert sheet["avatar_url"] == url and sheet["permissions"] == OWNER
    assert client.delete(url).status_code == 200
    assert client.get(f"/api/characters/{char['id']}/sheet").get_json()["character"]["avatar_url"] in (None, "")


def test_copy_is_independent_and_not_capped(app, client, data):
    char = finalized(client, data)
    url = f"{BASE}/characters/{char['id']}/duplicate"
    client.post(f"/api/characters/{char['id']}/identity/avatar",
                data={"file": (BytesIO(PNG_BYTES), "a.png")}, content_type="multipart/form-data")
    copies = []
    for _ in range(6):  # more than any slot count the creator or archive might suggest
        response = client.post(url)
        assert response.status_code == 201, response.get_json()
        copies.append(response.get_json()["character"])
    ids = {c["id"] for c in copies}
    assert len(ids) == 6 and char["id"] not in ids
    assert all(c["name"] == "Mira Eulenfeder (Kopie)" for c in copies)
    assert all(not c.get("avatar_url") and c.get("campaign_id") is None for c in copies)

    before = client.get(f"/api/characters/{char['id']}/sheet").get_json()["character"]
    first = copies[0]["id"]
    assert client.put(f"/api/characters/{first}", json={"name": "Nur die Kopie", "hp_current": 1}).status_code == 200
    original = client.get(f"/api/characters/{char['id']}/sheet").get_json()["character"]
    assert original["name"] == "Mira Eulenfeder" and original["hp_current"] == before["hp_current"]
    assert original["avatar_url"] == before["avatar_url"] and before["avatar_url"]
    other_copy = client.get(f"/api/characters/{copies[1]['id']}/sheet").get_json()["character"]
    assert other_copy["name"] == "Mira Eulenfeder (Kopie)"
    # Each copy carries its own owner projection, not inherited state from the original.
    assert _projection(client, first) == OWNER
