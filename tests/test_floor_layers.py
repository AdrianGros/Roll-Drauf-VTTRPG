"""Private sources, real balcony pixels, existing vision and bounded CAS writes."""
import base64
from io import BytesIO
import secrets

from PIL import Image
import pytest

from vtt.extensions import db
from vtt.models import CampaignMap, SceneWall, SceneLight, FogOfWarState, Asset
from vtt.models.map_floor import MapFloorDeck, MapFloorImage
from vtt.models.ui_playtable import MapViewSettings
from vtt.play.floor_layers import floor_layers_bp
from vtt.play.service import ensure_session_state
from vtt.storage import get_storage_adapter
from tests.play_shared import create_campaign, add_member, add_map, create_session, create_token
from tests.test_table_contexts import enter

pytest_plugins = ["tests.play_shared"]


@pytest.fixture(autouse=True)
def floor_registration(play_app, tmp_path):
    if "floor_layers" not in play_app.blueprints:
        play_app.register_blueprint(floor_layers_bp, url_prefix="/api/play")
    play_app.config.update(LOCAL_STORAGE_PATH=str(tmp_path), STORAGE_PROVIDER="local")


@pytest.fixture
def floor_table(play_dm_user, play_player_user):
    campaign = create_campaign(play_dm_user, "Private floors")
    add_member(campaign, play_player_user)
    map_ = add_map(campaign, play_dm_user)
    map_.width, map_.height, map_.grid_size = 128, 96, 16
    map_.light_rules = {"dimensions_mode": "pixel"}
    map_.fog_enabled = False
    map_.background_url = "/legacy-map.png"
    play_dm_user.storage_quota_gb = 1
    session = create_session(campaign, status="in_progress", map_id=map_.id)
    state = ensure_session_state(campaign, session)
    token = create_token(campaign, session, state, play_player_user.id, x=32, y=48)
    token.metadata_json = {"position_mode": "pixel"}
    token.sight_range = 200
    db.session.add(MapViewSettings(map_id=map_.id, ambient=100, dynamic_lighting=True))
    db.session.commit()
    return campaign, session, map_, token


def prefix(table):
    campaign, session, _, _ = table
    return f"/api/play/campaigns/{campaign.id}/sessions/{session.id}"


def floor_path(table):
    return prefix(table) + f"/maps/{table[2].id}/floors"


def png(color, size=(128, 96)):
    stream = BytesIO()
    Image.new("RGBA", size, color).save(stream, format="PNG")
    return stream.getvalue()


def upload(client, table, headers, revision=0, color="red", name="Ground", **options):
    raw = options.pop("raw", None)
    data = dict(revision=str(revision), name=name, request_id=secrets.token_hex(16),
                file=(BytesIO(png(color) if raw is None else raw), "floor.png"))
    data.update(options)
    return client.post(floor_path(table), data=data, headers=headers)


def enable(client, table, headers, revision, active):
    response = client.put(floor_path(table), headers=headers, json=dict(
        revision=revision, enabled=True, active_floor_id=active))
    assert response.status_code == 200, response.json
    return response.json


def view(client, table, headers, query=""):
    return client.get(prefix(table) + "/floors/view" + query, headers=headers)


def image(response):
    assert response.status_code == 200, response.json
    return Image.open(BytesIO(base64.b64decode(response.json["image"].split(",")[1])))


def test_existing_map_is_unchanged_without_an_enabled_deck(floor_table, play_player_client):
    campaign, session, map_, _ = floor_table
    headers = enter(play_player_client, campaign, session)
    assert view(play_player_client, floor_table, headers).json == {"enabled": False, "map_id": map_.id}
    assert MapFloorDeck.query.count() == MapFloorImage.query.count() == 0
    assert map_.background_url == "/legacy-map.png"
    assert play_player_client.get(prefix(floor_table) + "/vision/illumination", headers=headers).json["overlay"] is None


def test_actual_member_and_owner_player_cannot_access_sources_or_mutate(floor_table, play_dm_client, play_player_client):
    campaign, session, map_, _ = floor_table
    dm = enter(play_dm_client, campaign, session, "dm")
    result = upload(play_dm_client, floor_table, dm)
    assert result.status_code == 201, result.json
    floor = result.json["floors"][0]
    assert not result.json["enabled"]
    enable(play_dm_client, floor_table, dm, 1, floor["id"])
    source = floor_path(floor_table) + f"/{floor['id']}/image"
    assert play_dm_client.get(source, headers=dm).mimetype == "image/png"
    assert "storage_key" not in str(result.json) and "storage_provider" not in str(result.json)
    player = enter(play_player_client, campaign, session)
    owner_player = enter(play_dm_client, campaign, session, "player")
    for client, headers in [(play_player_client, player), (play_dm_client, owner_player)]:
        assert client.get(floor_path(floor_table), headers=headers).status_code == 403
        assert client.get(source, headers=headers).status_code == 403
        assert client.put(floor_path(floor_table), headers=headers, json={"revision": 2}).status_code == 403
        assert client.delete(floor_path(floor_table) + f"/{floor['id']}", headers=headers, json={"revision": 2}).status_code == 403
        assert upload(client, floor_table, headers, revision=2).status_code == 403
        response = view(client, floor_table, headers)
        assert set(response.json) == {"enabled", "map_id", "view_key", "masked", "name", "image"}
        assert response.json["masked"] is True
        for forbidden in ["storage_key", "openings", "floor_ids", "active_floor_id", "floors"]:
            assert forbidden not in response.json
        assert response.headers["Cache-Control"] == "private, no-store"
        assert view(client, floor_table, headers, "?token_id=1").status_code == 403
    assert Asset.query.count() == 0


def test_balcony_is_real_composited_lower_art_never_higher(floor_table, play_dm_client, play_player_client):
    campaign, session, _, _ = floor_table
    dm = enter(play_dm_client, campaign, session, "dm")
    data = upload(play_dm_client, floor_table, dm).json
    lower = data["floors"][0]["id"]
    data = upload(play_dm_client, floor_table, dm, 1, "lime", "Balcony").json
    upper = data["floors"][1]["id"]
    upload(play_dm_client, floor_table, dm, 2, "blue", "Private attic")
    data = play_dm_client.put(floor_path(floor_table) + f"/{upper}", headers=dm, json=dict(
        revision=3, reveal_below=True, openings=[dict(x=10, y=12, width=20, height=25)])).json
    enable(play_dm_client, floor_table, dm, data["revision"], upper)
    player = enter(play_player_client, campaign, session)
    result = view(play_player_client, floor_table, player)
    raster = image(result)
    assert raster.mode == "RGB"
    assert raster.getpixel((10, 12)) == raster.getpixel((29, 36)) == (255, 0, 0)
    assert raster.getpixel((30, 37)) == raster.getpixel((70, 60)) == (0, 255, 0)
    assert (0, 0, 255) not in set(raster.getdata())
    assert "Private attic" not in str(result.json)
    assert play_dm_client.put(floor_path(floor_table) + f"/{upper}", headers=dm,
                              json=dict(revision=5, reveal_below=False)).status_code == 200
    raster = image(view(play_player_client, floor_table, player))
    assert raster.getpixel((15, 15)) == (0, 0, 0)
    # Switching to the ground floor shows no upper artwork at all.
    enable(play_dm_client, floor_table, dm, 6, lower)
    assert image(view(play_player_client, floor_table, player)).getpixel((70, 60)) == (255, 0, 0)


def test_existing_walls_lights_and_fog_mask_actual_output_pixels(floor_table, play_dm_client, play_player_client):
    campaign, session, map_, token = floor_table
    dm = enter(play_dm_client, campaign, session, "dm")
    data = upload(play_dm_client, floor_table, dm, color="white").json
    enable(play_dm_client, floor_table, dm, 1, data["floors"][0]["id"])
    map_.fog_enabled = True
    db.session.add(SceneWall(campaign_map_id=map_.id, x0=64, y0=0, x1=64, y1=96,
                             sight="normal", light="normal", created_by=campaign.owner_id))
    db.session.commit()
    player = enter(play_player_client, campaign, session)
    raster = image(view(play_player_client, floor_table, player))
    assert raster.getpixel((32, 48)) == (255, 255, 255)
    assert raster.getpixel((110, 48)) == (0, 0, 0)
    assert image(view(play_dm_client, floor_table, dm)).getpixel((110, 48)) == (255, 255, 255)
    preview = image(view(play_dm_client, floor_table, dm, f"?token_id={token.id}"))
    assert preview.getpixel((110, 48)) == (0, 0, 0)
    assert FogOfWarState.query.count() == 0  # Preview/projection never writes exploration.
    SceneWall.query.delete()
    token.sight_range = 20
    db.session.add(SceneLight(campaign_map_id=map_.id, x=32, y=48, bright_radius=10,
                              dim_radius=10, light_type="darkness", created_by=campaign.owner_id))
    db.session.commit()
    raster = image(view(play_player_client, floor_table, player))
    assert raster.getpixel((32, 48)) == raster.getpixel((110, 48)) == (0, 0, 0)


def test_view_keys_change_with_vision_and_are_audience_bound(floor_table, play_dm_client, play_player_client):
    campaign, session, map_, token = floor_table
    dm = enter(play_dm_client, campaign, session, "dm")
    data = upload(play_dm_client, floor_table, dm).json
    enable(play_dm_client, floor_table, dm, 1, data["floors"][0]["id"])
    map_.fog_enabled = True
    token.sight_range = 20
    db.session.commit()
    player = enter(play_player_client, campaign, session)
    key = view(play_player_client, floor_table, player).json["view_key"]
    assert "image" in view(play_player_client, floor_table, player, "?view_key=%C3%A4").json
    unchanged = view(play_player_client, floor_table, player, "?view_key=" + key).json
    assert unchanged["unchanged"] and "image" not in unchanged
    owner_player = enter(play_dm_client, campaign, session)
    assert view(play_dm_client, floor_table, owner_player).json["view_key"] != key
    token.x += 20
    db.session.commit()
    assert view(play_player_client, floor_table, player).json["view_key"] != key


def test_upload_replay_cas_quota_release_and_deleted_request_tombstone(floor_table, play_dm_client, play_dm_user):
    campaign, session, _, _ = floor_table
    dm = enter(play_dm_client, campaign, session, "dm")
    rid = secrets.token_hex(16)
    first = upload(play_dm_client, floor_table, dm, request_id=rid)
    used = play_dm_user.storage_used_gb
    assert used > 0
    replay = upload(play_dm_client, floor_table, dm, request_id=rid)
    assert replay.status_code == 200 and replay.json["revision"] == 1
    assert play_dm_user.storage_used_gb == used and MapFloorImage.query.count() == 1
    assert upload(play_dm_client, floor_table, dm, request_id=rid, color="blue").status_code == 409
    assert upload(play_dm_client, floor_table, dm).status_code == 409
    floor = MapFloorImage.query.one()
    storage, key = get_storage_adapter(), floor.storage_key
    assert storage.exists(key)
    assert play_dm_client.delete(floor_path(floor_table) + f"/{floor.id}", headers=dm,
                                 json={"revision": 0}).status_code == 409
    result = play_dm_client.delete(floor_path(floor_table) + f"/{floor.id}", headers=dm, json={"revision": 1})
    assert result.status_code == 200 and result.json["floors"] == [] and not result.json["enabled"]
    assert not storage.exists(key) and play_dm_user.storage_used_gb == pytest.approx(0)
    assert upload(play_dm_client, floor_table, dm, 2, request_id=rid).status_code == 409


def test_quota_failure_does_not_create_source_or_revision(floor_table, play_dm_client, play_dm_user):
    campaign, session, _, _ = floor_table
    dm = enter(play_dm_client, campaign, session, "dm")
    play_dm_user.storage_quota_gb = 0
    db.session.commit()
    result = upload(play_dm_client, floor_table, dm)
    assert result.status_code == 507 and result.json["code"] == "storage_quota_exceeded"
    assert MapFloorImage.query.count() == MapFloorDeck.query.count() == 0
    assert play_dm_user.storage_used_gb == 0


@pytest.mark.parametrize("raw,status", [(b"<svg/>", 415), (b"\x89PNG\r\n\x1a\ninvalid", 415),
                                          (png("red", (10, 10)), 422), (b"x" * (4 * 1024**2 + 1), 413),
                                          (png("red", (2049, 10)), 413)])
def test_invalid_or_unbounded_images_are_rejected(floor_table, play_dm_client, raw, status):
    dm = enter(play_dm_client, floor_table[0], floor_table[1], "dm")
    assert upload(play_dm_client, floor_table, dm, raw=raw).status_code == status
    assert MapFloorImage.query.count() == 0


def test_rectangles_and_order_are_validated_atomically(floor_table, play_dm_client):
    dm = enter(play_dm_client, floor_table[0], floor_table[1], "dm")
    data = upload(play_dm_client, floor_table, dm).json
    floor = data["floors"][0]["id"]
    for rect in [dict(x=-1, y=0, width=10, height=10), dict(x=127, y=0, width=2, height=10),
                 dict(x=0, y=True, width=10, height=10), dict(x=0, y=0, width=0, height=10)]:
        response = play_dm_client.put(floor_path(floor_table) + f"/{floor}", headers=dm,
                                      json=dict(revision=1, name="Should roll back", openings=[rect]))
        assert response.status_code == 422
    assert MapFloorImage.query.one().name == "Ground"
    for ids in [[floor, floor], [99999], [True]]:
        assert play_dm_client.put(floor_path(floor_table), headers=dm,
                                  json=dict(revision=1, floor_ids=ids)).status_code == 422
    assert play_dm_client.put(floor_path(floor_table), headers=dm,
                              json=dict(revision=1, active_floor_id=99999)).status_code == 422
    assert db.session.get(MapFloorDeck, floor_table[2].id).revision == 1


def test_floor_count_and_total_pixels_are_bounded(floor_table, play_dm_client):
    dm = enter(play_dm_client, floor_table[0], floor_table[1], "dm")
    for revision in range(8):
        assert upload(play_dm_client, floor_table, dm, revision).status_code == 201
    assert upload(play_dm_client, floor_table, dm, 8).json["code"] == "floor_budget_exceeded"
    assert MapFloorImage.query.count() == 8


def test_real_total_pixel_budget_and_canonical_storage_budget(floor_table, play_dm_client, monkeypatch):
    import vtt.play.floor_layers as module
    dm = enter(play_dm_client, floor_table[0], floor_table[1], "dm")
    map_ = floor_table[2]
    map_.width = map_.height = 2048
    db.session.commit()
    raw = png("red", (2048, 2048))
    for revision in range(3):
        assert upload(play_dm_client, floor_table, dm, revision, raw=raw).status_code == 201
    # Four individually legal images exceed the real aggregate 16M pixels.
    assert upload(play_dm_client, floor_table, dm, 3, raw=raw).json["code"] == "floor_budget_exceeded"
    map_.width, map_.height = 128, 96
    db.session.commit()
    # Narrow the byte cap to the exact bytes already occupied; the next valid
    # image must fail before quota/storage changes, independently of pixel cap.
    monkeypatch.setattr(module, "MAX_BYTES", sum(row.size_bytes for row in module.rows(map_.id)))
    before = MapFloorImage.query.count()
    assert upload(play_dm_client, floor_table, dm, 3).json["code"] == "floor_budget_exceeded"
    assert MapFloorImage.query.count() == before


def test_storage_failure_rolls_back_quota_and_cleans_partial_object(floor_table, play_dm_client, play_dm_user, monkeypatch):
    from vtt.storage import LocalStorageAdapter
    dm = enter(play_dm_client, floor_table[0], floor_table[1], "dm")
    original = LocalStorageAdapter.upload
    def broken(self, key, raw):
        original(self, key, raw)
        raise OSError("isolated partial upload failure")
    monkeypatch.setattr(LocalStorageAdapter, "upload", broken)
    assert upload(play_dm_client, floor_table, dm).status_code == 503
    assert MapFloorImage.query.count() == MapFloorDeck.query.count() == 0
    assert play_dm_user.storage_used_gb == 0
    from pathlib import Path
    from flask import current_app
    assert not list(Path(current_app.config["LOCAL_STORAGE_PATH"]).rglob("*.png"))


def test_alpha_openings_reorder_and_delete_active_neighbor(floor_table, play_dm_client):
    dm = enter(play_dm_client, floor_table[0], floor_table[1], "dm")
    lower = upload(play_dm_client, floor_table, dm).json["floors"][0]["id"]
    translucent = png((0, 255, 0, 128))
    upper = upload(play_dm_client, floor_table, dm, 1, raw=translucent,
                   reveal_below="true").json["floors"][1]["id"]
    enable(play_dm_client, floor_table, dm, 2, upper)
    assert image(view(play_dm_client, floor_table, dm)).getpixel((20, 20)) == (127, 128, 0)
    reordered = play_dm_client.put(floor_path(floor_table), headers=dm,
                                   json=dict(revision=3, floor_ids=[upper, lower]))
    assert reordered.status_code == 200
    # Active floor is now the bottom: no red source under its alpha.
    assert image(view(play_dm_client, floor_table, dm)).getpixel((20, 20)) == (0, 128, 0)
    deleted = play_dm_client.delete(floor_path(floor_table) + f"/{upper}", headers=dm,
                                    json=dict(revision=4))
    assert deleted.json["active_floor_id"] == lower and deleted.json["enabled"]


def test_missing_or_changed_source_fails_closed_and_is_not_an_asset(floor_table, play_dm_client, play_player_client):
    dm = enter(play_dm_client, floor_table[0], floor_table[1], "dm")
    data = upload(play_dm_client, floor_table, dm).json
    enable(play_dm_client, floor_table, dm, 1, data["floors"][0]["id"])
    floor = MapFloorImage.query.one()
    get_storage_adapter().upload(floor.storage_key, png("blue"))
    player = enter(play_player_client, floor_table[0], floor_table[1])
    result = view(play_player_client, floor_table, player)
    assert result.status_code == 503 and "image" not in result.json
    assert Asset.query.count() == 0
    assert not any("map-floors" in str(row) for row in play_player_client.get(
        prefix(floor_table) + "/bootstrap", headers=player).json.values())


def test_other_maps_and_context_revocation_are_enforced(floor_table, play_dm_client):
    dm = enter(play_dm_client, floor_table[0], floor_table[1], "dm")
    data = upload(play_dm_client, floor_table, dm).json
    image_id = data["floors"][0]["id"]
    wrong = floor_path(floor_table).replace(f"/maps/{floor_table[2].id}/", "/maps/99999/")
    assert play_dm_client.get(wrong + f"/{image_id}/image", headers=dm).status_code == 404
    assert play_dm_client.get(floor_path(floor_table)).status_code == 403
    from vtt.models import TableContext
    from vtt.play.contexts import digest
    from vtt.utils.time import utcnow
    context = TableContext.query.filter_by(token_hash=digest(dm["X-VTT-Context"])).one()
    context.revoked_at = utcnow()
    db.session.commit()
    assert play_dm_client.get(floor_path(floor_table), headers=dm).status_code == 403
