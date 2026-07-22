"""M19 tests: Discord-only login and guild access gate."""

from urllib.parse import unquote, urlparse

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import DiscordIdentityLink, RegistrationKey, Role, User


def _read_location(response) -> str:
    return response.headers.get("Location", "")


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    app.config.update(
        DISCORD_LOGIN_ENABLED=True,
        DISCORD_CLIENT_ID="discord-client",
        DISCORD_CLIENT_SECRET="discord-secret",
        DISCORD_REDIRECT_URI="http://localhost/api/auth/discord/callback",
        DISCORD_GUILD_ID="1328724663257268264",
        DISCORD_BOT_VERIFICATION_URL="http://bot.local/vtt/discord/verify",
        DISCORD_BOT_SHARED_SECRET="shared-secret",
    )

    with app.app_context():
        db.create_all()
        for role_name in ["Player", "DM", "Admin"]:
            db.session.add(Role(name=role_name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _set_discord_state(client, *, state="state-123", next_path="/dashboard"):
    with client.session_transaction() as session:
        session["discord_oauth_state"] = state
        session["discord_oauth_next"] = next_path
        session["discord_oauth_redirect_uri"] = "http://localhost/api/auth/discord/callback"


def _add_assignment(discord_user_id: str, *, tier="player", uses_remaining=1, used_by_id=None, revoked=False, expires_at=None):
    key = RegistrationKey(
        key_code=f"SPELL-{discord_user_id[-4:]}-ABCD-EFGH",
        key_name=f"Discord assignment for {discord_user_id}",
        key_batch_id=f"discord-assign-{discord_user_id}",
        tier=tier,
        max_uses=1,
        uses_remaining=uses_remaining,
        used_by_id=used_by_id,
        is_revoked=revoked,
        expires_at=expires_at,
    )
    db.session.add(key)
    db.session.commit()
    return key


def test_login_page_is_discord_only_from_user_perspective(client):
    response = client.get("/login.html")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Mit Discord anmelden" in html
    assert "Server + Bot Access Required" in html
    assert "Es gibt keine separate Website-Registrierung." in html
    assert "Benutzername" not in html
    assert "Passwort" not in html
    assert "/signup.html" not in html
    assert "/register.html" not in html


@pytest.mark.parametrize("path", ["/signup.html", "/register.html", "/signup", "/register"])
def test_signup_and_register_routes_redirect_back_to_discord_login(path, client):
    response = client.get(path, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login.html?auth_notice=discord_only")


def test_discord_callback_denies_user_not_in_guild(client, monkeypatch):
    _set_discord_state(client)

    monkeypatch.setattr("vtt.auth.routes.exchange_discord_code", lambda code, redirect_uri: {"access_token": "discord-token"})
    monkeypatch.setattr(
        "vtt.auth.routes.fetch_discord_profile",
        lambda token: {"id": "123456789012345678", "username": "GateBlocked", "email": "blocked@example.com"},
    )
    monkeypatch.setattr(
        "vtt.auth.routes.verify_discord_with_bot",
        lambda payload: {"allowed": False, "player": False, "role": None, "guild_id": payload["guild_id"], "reason": "not_member"},
    )

    response = client.get("/api/auth/discord/callback?code=test-code&state=state-123", follow_redirects=False)

    assert response.status_code == 302
    location = unquote(_read_location(response))
    assert "/login.html?discord_error=" in location
    assert "nicht Teil des erlaubten Servers" in location


def test_discord_callback_denies_user_without_valid_discord_assignment(client, monkeypatch):
    _set_discord_state(client)

    monkeypatch.setattr("vtt.auth.routes.exchange_discord_code", lambda code, redirect_uri: {"access_token": "discord-token"})
    monkeypatch.setattr(
        "vtt.auth.routes.fetch_discord_profile",
        lambda token: {"id": "223456789012345678", "username": "NoKeyUser", "email": "nokey@example.com"},
    )
    monkeypatch.setattr(
        "vtt.auth.routes.verify_discord_with_bot",
        lambda payload: {"allowed": True, "player": True, "role": "player", "guild_id": payload["guild_id"], "reason": None},
    )

    response = client.get("/api/auth/discord/callback?code=test-code&state=state-123", follow_redirects=False)

    assert response.status_code == 302
    location = unquote(_read_location(response))
    assert "/login.html?discord_error=" in location
    assert "noch kein VTT-Zugang" in location


def test_discord_callback_auto_provisions_user_after_guild_and_key_validation(client, monkeypatch, app):
    with app.app_context():
        _add_assignment("323456789012345678", tier="dm")

    _set_discord_state(client)

    monkeypatch.setattr("vtt.auth.routes.exchange_discord_code", lambda code, redirect_uri: {"access_token": "discord-token"})
    monkeypatch.setattr(
        "vtt.auth.routes.fetch_discord_profile",
        lambda token: {
            "id": "323456789012345678",
            "username": "GuildRunner",
            "global_name": "Guild Runner",
            "email": "guild.runner@example.com",
        },
    )
    monkeypatch.setattr(
        "vtt.auth.routes.verify_discord_with_bot",
        lambda payload: {"allowed": True, "player": True, "role": "player", "guild_id": payload["guild_id"], "reason": None},
    )

    response = client.get("/api/auth/discord/callback?code=test-code&state=state-123", follow_redirects=False)

    assert response.status_code == 302
    assert urlparse(response.headers["Location"]).path == "/dashboard"
    set_cookie_values = response.headers.getlist("Set-Cookie")
    assert any("access_token_cookie=" in cookie for cookie in set_cookie_values)
    assert any("refresh_token_cookie=" in cookie for cookie in set_cookie_values)

    with app.app_context():
        user = User.query.filter_by(email="guild.runner@example.com").first()
        assert user is not None
        assert user.profile_tier == "dm"
        assert user.storage_quota_gb == 20
        assert user.active_campaigns_quota == 10

        link = DiscordIdentityLink.query.filter_by(discord_user_id="323456789012345678").first()
        assert link is not None
        assert link.user_id == user.id
        assert link.link_status == "linked"

        assignment = RegistrationKey.query.filter_by(key_batch_id="discord-assign-323456789012345678").first()
        assert assignment is not None
        assert assignment.used_by_id == user.id
        assert assignment.uses_remaining == 0


def test_discord_callback_reuses_existing_linked_user_with_consumed_assignment(client, monkeypatch, app):
    with app.app_context():
        player_role = Role.query.filter_by(name="Player").first()
        user = User(username="discord_existing", email="existing@example.com", role_id=player_role.id, profile_tier="player")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.flush()

        _add_assignment("423456789012345678", tier="player", uses_remaining=0, used_by_id=user.id)
        db.session.add(
            DiscordIdentityLink(
                user_id=user.id,
                discord_user_id="423456789012345678",
                discord_guild_id="1328724663257268264",
                discord_username_snapshot="Existing User",
                link_status="linked",
            )
        )
        db.session.commit()

    _set_discord_state(client)

    monkeypatch.setattr("vtt.auth.routes.exchange_discord_code", lambda code, redirect_uri: {"access_token": "discord-token"})
    monkeypatch.setattr(
        "vtt.auth.routes.fetch_discord_profile",
        lambda token: {"id": "423456789012345678", "username": "Existing User", "email": "existing@example.com"},
    )
    monkeypatch.setattr(
        "vtt.auth.routes.verify_discord_with_bot",
        lambda payload: {"allowed": True, "player": True, "role": "player", "guild_id": payload["guild_id"], "reason": None},
    )

    response = client.get("/api/auth/discord/callback?code=test-code&state=state-123", follow_redirects=False)

    assert response.status_code == 302
    assert urlparse(response.headers["Location"]).path == "/dashboard"
