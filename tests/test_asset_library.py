"""M64 tests: asset library listing and preview endpoints."""

import io
from datetime import datetime

import pytest
from PIL import Image

from vtt import create_app
from vtt.extensions import db
from vtt.models import Asset, Campaign, CampaignMember, Role, User


def _login(client, username, password="Password123!"):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response


def _create_campaign(owner_user, name="Library Campaign"):
    campaign = Campaign(
        name=name,
        description="campaign for library tests",
        owner_id=owner_user.id,
        status="active",
        max_players=6,
    )
    db.session.add(campaign)
    db.session.flush()

    dm_member = CampaignMember(
        campaign_id=campaign.id,
        user_id=owner_user.id,
        campaign_role="DM",
        status="active",
        joined_at=datetime.utcnow(),
        invited_at=datetime.utcnow(),
        accepted_at=datetime.utcnow(),
        invited_by=owner_user.id,
    )
    db.session.add(dm_member)
    db.session.commit()
    return campaign


def _add_member(campaign, user, campaign_role="Player"):
    member = CampaignMember(
        campaign_id=campaign.id,
        user_id=user.id,
        campaign_role=campaign_role,
        status="active",
        joined_at=datetime.utcnow(),
        invited_at=datetime.utcnow(),
        accepted_at=datetime.utcnow(),
        invited_by=campaign.owner_id,
    )
    db.session.add(member)
    db.session.commit()
    return member


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    with app.app_context():
        db.create_all()
        for role_name in ["Player", "DM", "Admin"]:
            db.session.add(Role(name=role_name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def dm_user(app):
    user = User(username="lib_dm", email="lib_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="lib_player", email="lib_player@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def outsider_user(app):
    user = User(username="lib_out", email="lib_out@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def dm_client(app, dm_user):
    client = app.test_client()
    _login(client, "lib_dm")
    return client


@pytest.fixture
def player_client(app, player_user):
    client = app.test_client()
    _login(client, "lib_player")
    return client


@pytest.fixture
def outsider_client(app, outsider_user):
    client = app.test_client()
    _login(client, "lib_out")
    return client


class TestAssetLibrary:
    def test_member_can_list_library_assets(self, dm_user, player_user, player_client):
        campaign = _create_campaign(dm_user)
        _add_member(campaign, player_user, "Player")

        asset = Asset(
            campaign_id=campaign.id,
            uploaded_by=dm_user.id,
            filename="forest-map.png",
            mime_type="image/png",
            size_bytes=1024,
            checksum_md5="abc123abc123abc123abc123abc123ab",
            storage_key="campaigns/1/assets/forest-map.png",
            storage_provider="local",
            asset_type="map",
            scope="campaign",
        )
        db.session.add(asset)
        db.session.commit()

        response = player_client.get(f"/api/assets/campaigns/{campaign.id}/library?scope=campaign")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["assets"][0]["filename"] == "forest-map.png"
        assert data["assets"][0]["previewable"] is True

    def test_library_filters_by_search(self, dm_user, dm_client):
        campaign = _create_campaign(dm_user)
        asset_a = Asset(
            campaign_id=campaign.id,
            uploaded_by=dm_user.id,
            filename="forest-map.png",
            mime_type="image/png",
            size_bytes=1024,
            checksum_md5="abc123abc123abc123abc123abc123ab",
            storage_key="campaigns/1/assets/forest-map.png",
            storage_provider="local",
            asset_type="map",
            scope="campaign",
        )
        asset_b = Asset(
            campaign_id=campaign.id,
            uploaded_by=dm_user.id,
            filename="orc-token.png",
            mime_type="image/png",
            size_bytes=1024,
            checksum_md5="def456def456def456def456def456de",
            storage_key="campaigns/1/assets/orc-token.png",
            storage_provider="local",
            asset_type="token",
            scope="campaign",
        )
        db.session.add_all([asset_a, asset_b])
        db.session.commit()

        response = dm_client.get(f"/api/assets/campaigns/{campaign.id}/library?query=orc")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["assets"][0]["filename"] == "orc-token.png"

    def test_non_member_cannot_view_library(self, dm_user, outsider_client):
        campaign = _create_campaign(dm_user)
        response = outsider_client.get(f"/api/assets/campaigns/{campaign.id}/library")
        assert response.status_code == 403

    def test_preview_asset_returns_inline_content(self, dm_user, dm_client, monkeypatch):
        campaign = _create_campaign(dm_user)
        asset = Asset(
            campaign_id=campaign.id,
            uploaded_by=dm_user.id,
            filename="preview-map.png",
            mime_type="image/png",
            size_bytes=2048,
            checksum_md5="feedfacefeedfacefeedfacefeedface",
            storage_key="campaigns/1/assets/preview-map.png",
            storage_provider="local",
            asset_type="map",
            scope="campaign",
        )
        db.session.add(asset)
        db.session.commit()

        class _Storage:
            @staticmethod
            def download(_key):
                return b"PNGDATA"

        monkeypatch.setattr("vtt.endpoints.assets.get_storage_adapter", lambda: _Storage())

        response = dm_client.get(f"/api/assets/{asset.id}/preview")
        assert response.status_code == 200
        assert response.headers["Content-Disposition"].startswith("inline")
        assert response.data == b"PNGDATA"


def _make_png_bytes(size=(64, 48), color=(200, 50, 50)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


class TestAssetThumbnails:
    """M4: thumbnail generation on upload + thumbnail serving endpoint."""

    def _grant_quota(self, user, gb=1):
        user.storage_quota_gb = gb
        db.session.commit()

    def test_image_upload_generates_thumbnail(self, app, dm_user, dm_client, tmp_path):
        app.config["LOCAL_STORAGE_PATH"] = str(tmp_path / "asset-storage")
        self._grant_quota(dm_user)
        campaign = _create_campaign(dm_user)

        png_bytes = _make_png_bytes()
        response = dm_client.post(
            f"/api/assets/campaigns/{campaign.id}/upload",
            data={
                "file": (io.BytesIO(png_bytes), "battle-map.png"),
                "asset_type": "map",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 201
        asset_id = response.get_json()["asset_id"]

        asset = Asset.query.get(asset_id)
        assert asset.thumbnail_key is not None
        assert asset.serialize()["thumbnail_url"] == f"/api/assets/{asset_id}/thumbnail"

        thumb_response = dm_client.get(f"/api/assets/{asset_id}/thumbnail")
        assert thumb_response.status_code == 200
        assert thumb_response.data
        # Should be a valid, smaller JPEG.
        thumb_image = Image.open(io.BytesIO(thumb_response.data))
        assert thumb_image.format == "JPEG"
        assert max(thumb_image.size) <= 320

    def test_non_image_upload_does_not_set_thumbnail(self, app, dm_user, dm_client, tmp_path):
        app.config["LOCAL_STORAGE_PATH"] = str(tmp_path / "asset-storage")
        self._grant_quota(dm_user)
        campaign = _create_campaign(dm_user)

        response = dm_client.post(
            f"/api/assets/campaigns/{campaign.id}/upload",
            data={
                "file": (io.BytesIO(b"just some plain text notes"), "notes.txt"),
                "asset_type": "handout",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 201
        asset_id = response.get_json()["asset_id"]

        asset = Asset.query.get(asset_id)
        assert asset.thumbnail_key is None
        assert asset.serialize()["thumbnail_url"] is None

    def test_thumbnail_endpoint_falls_back_to_preview_when_missing(self, dm_user, dm_client, monkeypatch):
        campaign = _create_campaign(dm_user)
        asset = Asset(
            campaign_id=campaign.id,
            uploaded_by=dm_user.id,
            filename="legacy-map.png",
            mime_type="image/png",
            size_bytes=2048,
            checksum_md5="0123456789abcdef0123456789abcdef",
            storage_key="campaigns/1/assets/legacy-map.png",
            storage_provider="local",
            asset_type="map",
            scope="campaign",
            thumbnail_key=None,
        )
        db.session.add(asset)
        db.session.commit()

        class _Storage:
            @staticmethod
            def download(_key):
                return b"FULLPREVIEWDATA"

        monkeypatch.setattr("vtt.endpoints.assets.get_storage_adapter", lambda: _Storage())

        response = dm_client.get(f"/api/assets/{asset.id}/thumbnail")
        assert response.status_code == 200
        assert response.data == b"FULLPREVIEWDATA"


class TestAssetUploadPermissions:
    """F4 Gap A: a Player who owns a token could see the play table's
    "Bild setzen..." control but the server always 403'd the upload,
    because @require_campaign_access(can_edit_campaign) blocked every
    Player regardless of what they were uploading or why. Fixed by
    relaxing the route to membership-only and pushing the DM/CO_DM-only
    check down to just the non-token asset types (map, handout, generic
    image) -- those must stay exactly as restricted as before.
    """

    def _grant_quota(self, user, gb=1):
        user.storage_quota_gb = gb
        db.session.commit()

    def test_player_can_upload_token_asset_for_their_own_token(
        self, app, dm_user, player_user, player_client, tmp_path
    ):
        app.config["LOCAL_STORAGE_PATH"] = str(tmp_path / "asset-storage")
        campaign = _create_campaign(dm_user)
        _add_member(campaign, player_user, "Player")
        self._grant_quota(player_user)

        response = player_client.post(
            f"/api/assets/campaigns/{campaign.id}/upload",
            data={
                "file": (io.BytesIO(_make_png_bytes()), "my-token-face.png"),
                "asset_type": "token",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["asset_type"] == "token"

        asset = Asset.query.get(data["asset_id"])
        assert asset.uploaded_by == player_user.id
        assert asset.campaign_id == campaign.id

    def test_player_cannot_upload_map_asset(self, app, dm_user, player_user, player_client, tmp_path):
        app.config["LOCAL_STORAGE_PATH"] = str(tmp_path / "asset-storage")
        campaign = _create_campaign(dm_user)
        _add_member(campaign, player_user, "Player")
        self._grant_quota(player_user)

        response = player_client.post(
            f"/api/assets/campaigns/{campaign.id}/upload",
            data={
                "file": (io.BytesIO(_make_png_bytes()), "battle-map.png"),
                "asset_type": "map",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 403

    def test_player_cannot_upload_handout_asset(self, app, dm_user, player_user, player_client, tmp_path):
        app.config["LOCAL_STORAGE_PATH"] = str(tmp_path / "asset-storage")
        campaign = _create_campaign(dm_user)
        _add_member(campaign, player_user, "Player")
        self._grant_quota(player_user)

        response = player_client.post(
            f"/api/assets/campaigns/{campaign.id}/upload",
            data={
                "file": (io.BytesIO(b"handout notes"), "handout.txt"),
                "asset_type": "handout",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 403

    def test_non_member_cannot_upload_token_asset(self, app, dm_user, outsider_client, tmp_path):
        """The route is membership-only now, not public: someone who was
        never added to the campaign still gets 403, even for asset_type
        'token'."""
        app.config["LOCAL_STORAGE_PATH"] = str(tmp_path / "asset-storage")
        campaign = _create_campaign(dm_user)

        response = outsider_client.post(
            f"/api/assets/campaigns/{campaign.id}/upload",
            data={
                "file": (io.BytesIO(_make_png_bytes()), "not-my-campaign.png"),
                "asset_type": "token",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 403

    def test_dm_can_still_upload_map_asset(self, app, dm_user, dm_client, tmp_path):
        """Unchanged behaviour: the campaign's DM keeps full upload rights
        for every asset type, not just token."""
        app.config["LOCAL_STORAGE_PATH"] = str(tmp_path / "asset-storage")
        campaign = _create_campaign(dm_user)
        self._grant_quota(dm_user)

        response = dm_client.post(
            f"/api/assets/campaigns/{campaign.id}/upload",
            data={
                "file": (io.BytesIO(_make_png_bytes()), "battle-map.png"),
                "asset_type": "map",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 201
