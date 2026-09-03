"""Adversarial audit fix (2026-09-03): /api/admin/assets/* had a
literal no-op admin_required decorator -- every route was reachable by
anyone, unauthenticated. Pins the fix: unauthenticated and non-admin
callers are rejected, admin/owner callers pass through, and the
path-containment/identifier-sanitization defense-in-depth added to
asset_organizer.py/asset_downloader.py actually rejects escape attempts.
"""

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import Role, User
from vtt.services.asset_downloader import AssetDownloader
from vtt.services.asset_organizer import AssetOrganizer, _require_within


def _login(client, username, password="Password123!"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response


def _create_user(username, role_id, *, platform_role="supporter"):
    user = User(
        username=username,
        email=f"{username}@test.com",
        role_id=role_id,
        platform_role=platform_role,
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.flush()
    return user


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
def admin_client(app):
    _create_user("aa_admin", 3, platform_role="admin")
    db.session.commit()
    client = app.test_client()
    _login(client, "aa_admin")
    return client


@pytest.fixture
def player_client(app):
    _create_user("aa_player", 1, platform_role="supporter")
    db.session.commit()
    client = app.test_client()
    _login(client, "aa_player")
    return client


@pytest.fixture
def anon_client(app):
    return app.test_client()


class TestAdminAssetsRequiresRealAuth:
    """Every mutating/listing route in admin_assets_bp used to be wide
    open. Spot-check a representative route from each category plus the
    previously-unprotected job-status endpoint."""

    ROUTES = [
        ("POST", "/api/admin/assets/download/game-icons", {"icons": [{"name": "book", "category": "campaign"}]}),
        ("POST", "/api/admin/assets/organize/files", {"source_dir": "/tmp/whatever"}),
        ("POST", "/api/admin/assets/batch/colorize", {"directory": "vtt/static/icons"}),
        ("POST", "/api/admin/assets/batch/compress", {"directory": "vtt/static/images/textures"}),
        ("GET", "/api/admin/assets/list?path=icons", None),
        ("POST", "/api/admin/assets/verify", {"directory": "vtt/static/icons"}),
        ("GET", "/api/admin/assets/status/deadbeef", None),
    ]

    def test_anonymous_caller_is_rejected(self, anon_client):
        for method, url, body in self.ROUTES:
            response = anon_client.open(url, method=method, json=body)
            assert response.status_code in (401, 403), f"{method} {url} returned {response.status_code} for an anonymous caller"

    def test_regular_player_is_rejected(self, player_client):
        for method, url, body in self.ROUTES:
            response = player_client.open(url, method=method, json=body)
            assert response.status_code == 403, f"{method} {url} returned {response.status_code} for a non-admin player"

    def test_admin_can_reach_a_safe_route(self, admin_client):
        response = admin_client.get("/api/admin/assets/list?path=icons")
        assert response.status_code == 200


class TestPathContainmentDefenseInDepth:
    """Even with real auth now gating the surface, the underlying
    path-escape bugs were real -- pin the sanitizers directly."""

    def test_require_within_rejects_absolute_escape(self):
        with pytest.raises(ValueError):
            _require_within("vtt/static", "/etc/cron.d", "target_dir")

    def test_require_within_rejects_relative_traversal(self):
        with pytest.raises(ValueError):
            _require_within("vtt/static", "vtt/static/../../etc", "target_dir")

    def test_require_within_accepts_a_real_subdirectory(self, tmp_path):
        base = tmp_path / "static"
        sub = base / "icons"
        sub.mkdir(parents=True)
        # Must not raise.
        _require_within(str(base), str(sub), "target_dir")

    def test_batch_colorize_rejects_a_directory_outside_static(self):
        organizer = AssetOrganizer()
        results = organizer.batch_colorize_svgs("/etc", "#FFFFFF", "#000000")
        assert results["colorized"] == 0
        assert any("must stay within" in err for err in results["errors"])

    def test_organize_files_rejects_a_target_dir_escape(self, tmp_path):
        organizer = AssetOrganizer()
        results = organizer.organize_files(str(tmp_path), "../../../../etc")
        assert results["copied"] == 0
        assert any("must stay within" in err for err in results["errors"])


class TestIdentifierSanitizationDefenseInDepth:
    def test_download_game_icons_rejects_a_path_traversal_category(self):
        downloader = AssetDownloader()
        results = downloader.download_game_icons(["book"], category="../../../../etc/cron.d")
        assert results == {"book": False}

    def test_download_game_icons_rejects_a_path_traversal_icon_name(self):
        downloader = AssetDownloader()
        results = downloader.download_game_icons(["../../../../etc/passwd"], category="campaign")
        assert results == {"../../../../etc/passwd": False}
