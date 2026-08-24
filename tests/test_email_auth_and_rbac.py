"""Standard email authentication and layered RBAC contracts."""

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import Role, User


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    with app.app_context():
        db.create_all()
        for role_name in ("Player", "DM", "Admin"):
            db.session.add(Role(name=role_name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_standard_registration_needs_no_discord_or_invitation_key(client, app):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "email_player",
            "email": "player@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["user"]["email"] == "player@example.com"
    assert payload["user"]["role"] == "Player"
    assert payload["user"]["profile_tier"] == "player"
    assert payload["user"]["platform_role"] is None

    with app.app_context():
        user = User.query.filter_by(email="player@example.com").one()
        assert user.role.name == "Player"
        assert user.platform_role is None


def test_login_accepts_email_as_the_primary_identifier(client):
    client.post(
        "/api/auth/register",
        json={
            "username": "email_login",
            "email": "login@example.com",
            "password": "SecurePass123!",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "LOGIN@example.com", "password": "SecurePass123!"},
    )

    assert response.status_code == 200
    assert response.get_json()["user"]["email"] == "login@example.com"
    assert any("access_token_cookie=" in value for value in response.headers.getlist("Set-Cookie"))


def test_discord_configuration_does_not_remove_standard_auth_routes(client, app):
    app.config.update(
        DISCORD_LOGIN_ENABLED=True,
        DISCORD_CLIENT_ID="client",
        DISCORD_CLIENT_SECRET="secret",
        DISCORD_GUILD_ID="guild",
        DISCORD_BOT_VERIFICATION_URL="http://bot.local/verify",
        DISCORD_BOT_SHARED_SECRET="shared",
    )

    login_page = client.get("/login.html")
    signup_page = client.get("/signup.html", follow_redirects=False)
    register_page = client.get("/register.html", follow_redirects=False)

    assert login_page.status_code == 200
    assert '<form id="passwordLoginForm" class="book-form book-auth-form" hidden' not in login_page.get_data(as_text=True)
    assert "E-Mail oder Benutzername" in login_page.get_data(as_text=True)
    assert "/forgot-password.html" in login_page.get_data(as_text=True)
    assert signup_page.status_code == 200
    assert register_page.status_code == 200


def test_standard_user_cannot_enter_platform_admin_surface(client):
    client.post(
        "/api/auth/register",
        json={
            "username": "plain_player",
            "email": "plain@example.com",
            "password": "SecurePass123!",
        },
    )

    response = client.get("/api/admin/dashboard/metrics")

    assert response.status_code == 403
