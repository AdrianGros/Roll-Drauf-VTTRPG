"""Admin/platform auth foundation repair tests for M06."""

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import AppThemeSettings, RegistrationKey, Role, User


def _login(client, username, password="Password123!"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response


def _create_user(username, role_id, *, platform_role="supporter", email=None):
    user = User(
        username=username,
        email=email or f"{username}@test.com",
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
def admin_user(app):
    user = _create_user("admin_user", 3, platform_role="admin")
    db.session.commit()
    return user


@pytest.fixture
def moderator_user(app):
    user = _create_user("moderator_user", 2, platform_role="moderator")
    db.session.commit()
    return user


@pytest.fixture
def owner_user(app):
    user = _create_user("owner_user", 3, platform_role="owner")
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = _create_user("player_user", 1, platform_role="supporter")
    db.session.commit()
    return user


@pytest.fixture
def admin_client(app, admin_user):
    client = app.test_client()
    _login(client, admin_user.username)
    return client


@pytest.fixture
def moderator_client(app, moderator_user):
    client = app.test_client()
    _login(client, moderator_user.username)
    return client


@pytest.fixture
def owner_client(app, owner_user):
    client = app.test_client()
    _login(client, owner_user.username)
    return client


@pytest.fixture
def player_client(app, player_user):
    client = app.test_client()
    _login(client, player_user.username)
    return client


@pytest.fixture
def anon_client(app):
    return app.test_client()


@pytest.fixture
def active_theme(app):
    theme = AppThemeSettings.get_default_theme()
    db.session.commit()
    return theme


@pytest.fixture
def registration_key(app):
    key = RegistrationKey(
        key_code="SPELL-TEST-KEY1-0001",
        key_name="Test Key",
        key_batch_id="batch-test",
        tier="player",
        max_uses=1,
        uses_remaining=1,
    )
    db.session.add(key)
    db.session.commit()
    return key


class TestAdminDashboardProtection:
    def test_admin_dashboard_allows_moderator(self, moderator_client):
        response = moderator_client.get("/api/admin/dashboard/metrics")
        assert response.status_code == 200
        assert "metrics" in response.get_json()

    def test_admin_dashboard_denies_non_platform_user(self, player_client):
        response = player_client.get("/api/admin/dashboard/metrics")
        assert response.status_code == 403

    def test_admin_dashboard_denies_unauthenticated(self, anon_client):
        response = anon_client.get("/api/admin/dashboard/metrics")
        assert response.status_code == 401


class TestThemeAdminProtection:
    def test_theme_admin_allows_admin(self, admin_client, active_theme):
        response = admin_client.post("/api/theme/admin/update", json={"primary_color": "#123456"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["theme"]["primary_color"] == "#123456"

    def test_theme_admin_denies_moderator(self, moderator_client, active_theme):
        response = moderator_client.post("/api/theme/admin/update", json={"primary_color": "#654321"})
        assert response.status_code == 403

    def test_theme_admin_denies_unauthenticated(self, anon_client, active_theme):
        response = anon_client.post("/api/theme/admin/update", json={"primary_color": "#654321"})
        assert response.status_code == 401


class TestRegistrationKeyAdminProtection:
    def test_registration_keys_allow_owner(self, owner_client, registration_key):
        response = owner_client.get("/api/admin/keys")
        assert response.status_code == 200
        data = response.get_json()
        assert data["pagination"]["total"] >= 1

    def test_registration_keys_deny_non_platform_user(self, player_client, registration_key):
        response = player_client.get("/api/admin/keys")
        assert response.status_code == 403

    def test_registration_keys_deny_unauthenticated(self, anon_client, registration_key):
        response = anon_client.get("/api/admin/keys")
        assert response.status_code == 401


class TestAdminProfileLifecycleProtection:
    def test_admin_profile_allows_moderator(self, moderator_client):
        response = moderator_client.get("/api/admin/users")
        assert response.status_code == 200
        data = response.get_json()
        assert "users" in data

    def test_admin_profile_denies_non_platform_user(self, player_client):
        response = player_client.get("/api/admin/users")
        assert response.status_code == 403

    def test_admin_profile_denies_unauthenticated(self, anon_client):
        response = anon_client.get("/api/admin/users")
        assert response.status_code == 401
