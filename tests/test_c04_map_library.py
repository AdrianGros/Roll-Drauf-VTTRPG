"""C04: private library snapshot -> table map (operator-only, idempotent, bounded)."""
import io
import secrets

import pytest
from PIL import Image

from vtt.extensions import db
from vtt.models import Asset, CampaignMap, TableRequestReceipt
from tests.play_shared import add_map, add_member, create_campaign, create_session
from tests.test_mapmaker_library import document

pytest_plugins = ["tests.play_shared"]
PROJECTS = "/api/assets/mapmaker/projects"


def png(size=(256, 256), fmt="PNG"):
    buffer = io.BytesIO()
    Image.new("RGBA", size, (10, 90, 40, 255)).save(buffer, format=fmt)
    return buffer.getvalue()


def enter(client, campaign, session, mode):
    tab = secrets.token_urlsafe(24)
    response = client.post(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/contexts",
                           json={"mode": mode, "tab": tab})
    assert response.status_code == 201, response.get_json()
    return {"X-VTT-Context": response.json["token"], "X-VTT-Tab": tab}


@pytest.fixture
def table(play_app, play_dm_user, play_player_user, play_dm_client, tmp_path):
    play_app.config.update(LOCAL_STORAGE_PATH=str(tmp_path / "storage"), STORAGE_PROVIDER="local")
    play_dm_user.storage_quota_gb = 1
    campaign = create_campaign(play_dm_user, "Library")
    add_member(campaign, play_player_user, "Player")
    session = create_session(campaign, status="in_progress", map_id=add_map(campaign, play_dm_user).id)
    created = play_dm_client.post(PROJECTS, json={"document": document()},
                                  headers={"X-Mapmaker-Account": str(play_dm_user.id)})
    assert created.status_code == 201, created.get_json()
    return campaign, session, created.get_json()["project"]


def url(campaign, session):
    return f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/map-library-snapshots"


def form(project, **over):
    data = {"project_id": project["id"], "revision": str(project["revision"]), "request_id": "req-" + secrets.token_hex(8),
            "grid_size": "70", "name": "Küstenburg", "credits": "Kenney (CC0)",
            "file": (io.BytesIO(png()), "snapshot.png", "image/png")}
    data.update(over)
    return {k: v for k, v in data.items() if v is not None}


def post(client, table, headers, **over):
    campaign, session, project = table
    return client.post(url(campaign, session), data=form(project, **over), headers=headers,
                       content_type="multipart/form-data")


def test_dm_snapshot_creates_asset_map_and_receipt_atomically(table, play_dm_client):
    campaign, session, project = table
    headers = enter(play_dm_client, campaign, session, "dm")
    result = post(play_dm_client, table, headers)
    assert result.status_code == 201, result.get_json()
    body = result.get_json()
    campaign_map = db.session.get(CampaignMap, body["map_id"])
    asset = db.session.get(Asset, body["asset_id"])
    assert campaign_map.campaign_id == campaign.id and (campaign_map.width, campaign_map.height) == (256, 256)
    assert campaign_map.background_url == f"/api/assets/{asset.id}/preview"
    assert "Revision 1" in campaign_map.description and "Kenney (CC0)" in campaign_map.description
    assert asset.asset_type == "map" and asset.mime_type == "image/png" and not asset.is_public
    # The private project source is never exposed through the shared asset/map.
    assert project["id"] not in (asset.storage_key or "") and "mapmaker" not in (asset.storage_key or "")
    receipt = TableRequestReceipt.query.one()
    assert receipt.status_code == 201 and receipt.response["map_id"] == body["map_id"]


def test_identical_retry_replays_same_ids_and_changed_payload_conflicts(table, play_dm_client):
    campaign, session, project = table
    headers = enter(play_dm_client, campaign, session, "dm")
    first = post(play_dm_client, table, headers, request_id="same-request-1")
    again = post(play_dm_client, table, headers, request_id="same-request-1")
    assert again.status_code == 201 and again.headers["X-Request-Replayed"] == "true"
    assert (again.get_json()["map_id"], again.get_json()["asset_id"]) == (first.get_json()["map_id"], first.get_json()["asset_id"])
    changed = post(play_dm_client, table, headers, request_id="same-request-1", name="Anderer Name")
    assert changed.status_code == 409
    assert CampaignMap.query.filter(CampaignMap.name == "Küstenburg").count() == 1
    assert Asset.query.filter_by(asset_type="map").count() == 1


def test_owner_in_player_mode_and_real_player_cannot_snapshot(table, play_dm_client, play_player_client):
    campaign, session, _ = table
    owner_player = enter(play_dm_client, campaign, session, "player")
    assert post(play_dm_client, table, owner_player).status_code == 403
    assert post(play_player_client, table, enter(play_player_client, campaign, session, "player")).status_code == 403
    assert post(play_dm_client, table, {}).status_code == 403  # no context never falls back to DM
    assert Asset.query.filter_by(asset_type="map").count() == 0


def test_context_of_another_session_is_rejected(table, play_dm_client, play_dm_user):
    campaign, session, _ = table
    other = create_session(campaign, name="Other", status="in_progress")
    headers = enter(play_dm_client, campaign, other, "dm")
    assert post(play_dm_client, table, headers).status_code == 403


def test_foreign_project_and_stale_revision_are_refused_without_side_effects(table, play_dm_client, play_player_client):
    campaign, session, project = table
    headers = enter(play_dm_client, campaign, session, "dm")
    assert post(play_dm_client, table, headers, project_id="00000000-0000-4000-8000-000000000000").status_code == 404
    stale = post(play_dm_client, table, headers, revision="2")
    assert stale.status_code == 409 and stale.get_json()["error"] == "revision_conflict"
    assert Asset.query.filter_by(asset_type="map").count() == 0
    assert TableRequestReceipt.query.count() == 0  # nothing happened: the claim is released


@pytest.mark.parametrize("bad,status", [
    ({"file": (io.BytesIO(b"not a png"), "x.png", "image/png")}, 400),
    ({"file": (io.BytesIO(png((128, 128))), "x.png", "image/png")}, 400),
    ({"file": (io.BytesIO(png(fmt="GIF")), "x.png", "image/png")}, 400),
    ({"file": None}, 400),
    ({"grid_size": "15"}, 400), ({"grid_size": "301"}, 400), ({"name": ""}, 400), ({"request_id": "short"}, 400),
    ({"revision": "x"}, 400), ({"project_id": "not-a-uuid"}, 400),
])
def test_bad_png_dimensions_and_fields_are_rejected(table, play_dm_client, bad, status):
    campaign, session, _ = table
    result = post(play_dm_client, table, enter(play_dm_client, campaign, session, "dm"), **bad)
    assert result.status_code == status
    assert Asset.query.filter_by(asset_type="map").count() == 0


def test_quota_failure_leaves_no_asset_map_or_claim(table, play_dm_client, play_dm_user):
    campaign, session, _ = table
    headers = enter(play_dm_client, campaign, session, "dm")
    play_dm_user.storage_quota_gb = 0
    db.session.commit()
    result = post(play_dm_client, table, headers)
    assert result.status_code == 507
    assert Asset.query.filter_by(asset_type="map").count() == 0
    assert CampaignMap.query.filter(CampaignMap.name == "Küstenburg").count() == 0
    assert TableRequestReceipt.query.count() == 0


def test_storage_failure_cleans_up_and_releases_claim(table, play_dm_client, monkeypatch):
    campaign, session, _ = table
    headers = enter(play_dm_client, campaign, session, "dm")

    class Broken:
        def upload(self, *a, **k):
            raise OSError("disk full")

        def delete(self, *a, **k):
            pass
    monkeypatch.setattr("vtt.play.map_library.get_storage_adapter", lambda: Broken())
    result = post(play_dm_client, table, headers)
    assert result.status_code == 503
    assert Asset.query.filter_by(asset_type="map").count() == 0 and TableRequestReceipt.query.count() == 0


@pytest.mark.parametrize("fail_on", ["image", "thumbnail"])
def test_write_then_raise_cleans_up_the_prospective_keys(table, play_dm_client, monkeypatch, fail_on):
    """A storage write that stores bytes and THEN raises must not leave an orphan."""
    campaign, session, _ = table
    headers = enter(play_dm_client, campaign, session, "dm")
    stored, deleted = {}, []

    class WritesThenRaises:
        def upload(self, key, data):
            stored[key] = data  # the object exists now ...
            if (fail_on == "image") == (not key.endswith("-thumb.jpg")):
                raise OSError("connection dropped after the write")  # ... but the call raises

        def delete(self, key):
            deleted.append(key)
            stored.pop(key, None)
    monkeypatch.setattr("vtt.play.map_library.get_storage_adapter", lambda: WritesThenRaises())
    result = post(play_dm_client, table, headers)
    if fail_on == "image":
        assert result.status_code == 503
        assert Asset.query.filter_by(asset_type="map").count() == 0
        assert stored == {} and deleted  # the image key was registered before the upload
    else:
        # A thumbnail is best effort: the map is created, but the half-written thumbnail is removed.
        assert result.status_code == 201
        asset = db.session.get(Asset, result.get_json()["asset_id"])
        assert asset.thumbnail_key is None
        assert set(stored) == {asset.storage_key}


def test_revision_bound_matches_the_integer_range(table, play_dm_client):
    campaign, session, _ = table
    headers = enter(play_dm_client, campaign, session, "dm")
    top = post(play_dm_client, table, headers, revision=str(2**31 - 1))
    assert top.status_code == 409 and top.get_json()["error"] == "revision_conflict"  # accepted, then stale
    assert post(play_dm_client, table, headers, revision=str(2**31)).status_code == 400
    assert post(play_dm_client, table, headers, revision="-1").status_code == 400
    assert Asset.query.filter_by(asset_type="map").count() == 0
