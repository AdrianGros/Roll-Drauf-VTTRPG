"""Bug report 2026-09-23: (a) a headmaster account (storage_quota_gb
NULL = unlimited) got 400 "No storage quota" on every upload; (b)
re-uploading the same file into the same campaign hit the
assets.storage_key UNIQUE constraint -> 500 and leaked quota."""

import io

from vtt.extensions import db
from vtt.models import Asset

from tests.test_asset_library import (  # noqa: F401 -- fixtures
    _add_member,
    _create_campaign,
    _make_png_bytes,
    app,
    dm_client,
    dm_user,
    player_client,
    player_user,
)


def _upload_token(client, campaign, png_bytes, filename="Brogdan Token.png"):
    return client.post(
        f"/api/assets/campaigns/{campaign.id}/upload",
        data={"file": (io.BytesIO(png_bytes), filename), "asset_type": "token"},
        content_type="multipart/form-data",
    )


def test_headmaster_with_null_quota_can_upload(app, dm_user, player_user, player_client, tmp_path):
    app.config["LOCAL_STORAGE_PATH"] = str(tmp_path / "asset-storage")
    campaign = _create_campaign(dm_user)
    _add_member(campaign, player_user, "Player")
    player_user.profile_tier = "headmaster"
    player_user.storage_quota_gb = None
    db.session.commit()

    response = _upload_token(player_client, campaign, _make_png_bytes())
    assert response.status_code == 201
    db.session.refresh(player_user)
    assert player_user.storage_used_gb > 0


def test_null_quota_on_a_normal_tier_is_still_rejected(app, dm_user, player_user, player_client, tmp_path):
    app.config["LOCAL_STORAGE_PATH"] = str(tmp_path / "asset-storage")
    campaign = _create_campaign(dm_user)
    _add_member(campaign, player_user, "Player")
    player_user.profile_tier = "player"
    player_user.storage_quota_gb = None
    db.session.commit()

    response = _upload_token(player_client, campaign, _make_png_bytes())
    assert response.status_code == 400


def test_same_file_uploaded_repeatedly_by_two_users_all_succeed(
    app, dm_user, player_user, dm_client, player_client, tmp_path
):
    app.config["LOCAL_STORAGE_PATH"] = str(tmp_path / "asset-storage")
    campaign = _create_campaign(dm_user)
    _add_member(campaign, player_user, "Player")
    dm_user.storage_quota_gb = 1
    player_user.storage_quota_gb = 1
    db.session.commit()
    png_bytes = _make_png_bytes()

    responses = [
        _upload_token(dm_client, campaign, png_bytes),
        _upload_token(player_client, campaign, png_bytes),
        _upload_token(player_client, campaign, png_bytes),
    ]
    assert [r.status_code for r in responses] == [201, 201, 201]
    keys = {Asset.query.get(r.get_json()["asset_id"]).storage_key for r in responses}
    assert len(keys) == 3


def test_jpeg_saved_as_png_uploads_and_is_stored_as_jpeg(app, dm_user, player_user, player_client, tmp_path):
    """Follow-up the same day: with the quota fixed, legendaryrock's
    upload still got 400 "File content does not match claimed type" --
    real image bytes under the wrong image extension."""
    from PIL import Image

    app.config["LOCAL_STORAGE_PATH"] = str(tmp_path / "asset-storage")
    campaign = _create_campaign(dm_user)
    _add_member(campaign, player_user, "Player")
    player_user.storage_quota_gb = 1
    db.session.commit()
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), (10, 20, 30)).save(buffer, format="JPEG")

    response = player_client.post(
        f"/api/assets/campaigns/{campaign.id}/upload",
        data={"file": (io.BytesIO(buffer.getvalue()), "token.png", "image/png"), "asset_type": "token"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    assert Asset.query.get(response.get_json()["asset_id"]).mime_type == "image/jpeg"
