"""M19 tests: Discord-only login and guild access gate."""

from datetime import timedelta
from urllib.parse import unquote, urlparse

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import DiscordIdentityLink, RegistrationKey, Role, User
from vtt.utils.time import utcnow


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


def test_login_page_exposes_standard_auth_and_optional_discord(client):
    response = client.get("/login.html")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'aria-label="Mit Discord anmelden"' in html
    assert '<img src="/static/images/discord-symbol.svg" alt="" class="login-discord-button-icon">' in html
    assert "<span>Mit Discord anmelden</span>" in html
    assert "Optional mit Discord anmelden" not in html
    assert "Roll drauf im Discord" in html
    assert 'href="https://discord.gg/rolldrauf"' in html
    assert 'href="https://disboard.org/de/server/1244342177539166238"' in html
    assert "Dein Zugang, deine Wahl" not in html
    assert "Die Registrierung legt einen normalen Player-Account" not in html
    assert "/static/images/discord-symbol.svg" in html
    assert "/static/assets/sternenstaub/banners/banner-roll-drauf.png" in html
    assert 'class="login-book-banner-image"' in html
    assert "spellbook-logo.svg" not in html
    assert "banner-starry-sky.jpg" not in html
    assert "Discord ist ein optionaler Schnellzugang." not in html
    assert "Discord access requirements" not in html
    assert 'class="book-discord-step"' not in html
    assert 'class="book-discord-hint"' not in html
    assert html.index('id="passwordLoginForm"') < html.index('id="loginDiscordGate"')
    assert html.count('href="/forgot-password.html"') == 1
    assert 'id="passwordLoginContinueBtn"' not in html
    assert "Übersicht öffnen" not in html
    assert "E-Mail oder Benutzername" in html
    assert '<form id="passwordLoginForm" class="book-form book-auth-form" hidden' not in html
    assert "/signup.html" in html


@pytest.mark.parametrize("path", ["/signup.html", "/register.html", "/signup", "/register"])
def test_signup_and_register_routes_remain_reachable_with_discord_enabled(path, client):
    response = client.get(path, follow_redirects=False)

    assert response.status_code == 200


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


def test_discord_callback_allows_login_when_original_key_expired_after_consumption(client, monkeypatch, app):
    """A key that already granted access shouldn't retroactively lock the
    user out once its own expiry window passes — expiry only gates whether
    an unclaimed key can still be claimed, not already-granted access."""
    with app.app_context():
        player_role = Role.query.filter_by(name="Player").first()
        user = User(username="long_time_member", email="longtime@example.com", role_id=player_role.id, profile_tier="player")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.flush()

        _add_assignment(
            "523456789012345678",
            tier="player",
            uses_remaining=0,
            used_by_id=user.id,
            expires_at=utcnow() - timedelta(days=90),
        )
        db.session.add(
            DiscordIdentityLink(
                user_id=user.id,
                discord_user_id="523456789012345678",
                discord_guild_id="1328724663257268264",
                discord_username_snapshot="Long Time Member",
                link_status="linked",
            )
        )
        db.session.commit()

    _set_discord_state(client)

    monkeypatch.setattr("vtt.auth.routes.exchange_discord_code", lambda code, redirect_uri: {"access_token": "discord-token"})
    monkeypatch.setattr(
        "vtt.auth.routes.fetch_discord_profile",
        lambda token: {"id": "523456789012345678", "username": "Long Time Member", "email": "longtime@example.com"},
    )
    monkeypatch.setattr(
        "vtt.auth.routes.verify_discord_with_bot",
        lambda payload: {"allowed": True, "player": True, "role": "player", "guild_id": payload["guild_id"], "reason": None},
    )

    response = client.get("/api/auth/discord/callback?code=test-code&state=state-123", follow_redirects=False)

    assert response.status_code == 302
    location = unquote(_read_location(response))
    assert "access_expired" not in location
    assert urlparse(response.headers["Location"]).path == "/dashboard"


def test_discord_callback_still_denies_login_when_consumed_key_is_revoked(client, monkeypatch, app):
    """Revocation must still block access even for an already-consumed key —
    only expiry is exempted for consumed keys, not revocation."""
    with app.app_context():
        player_role = Role.query.filter_by(name="Player").first()
        user = User(username="revoked_member", email="revoked@example.com", role_id=player_role.id, profile_tier="player")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.flush()

        _add_assignment(
            "623456789012345678",
            tier="player",
            uses_remaining=0,
            used_by_id=user.id,
            revoked=True,
        )
        db.session.commit()

    _set_discord_state(client)

    monkeypatch.setattr("vtt.auth.routes.exchange_discord_code", lambda code, redirect_uri: {"access_token": "discord-token"})
    monkeypatch.setattr(
        "vtt.auth.routes.fetch_discord_profile",
        lambda token: {"id": "623456789012345678", "username": "Revoked Member", "email": "revoked@example.com"},
    )
    monkeypatch.setattr(
        "vtt.auth.routes.verify_discord_with_bot",
        lambda payload: {"allowed": True, "player": True, "role": "player", "guild_id": payload["guild_id"], "reason": None},
    )

    response = client.get("/api/auth/discord/callback?code=test-code&state=state-123", follow_redirects=False)

    assert response.status_code == 302
    location = unquote(_read_location(response))
    assert "/login.html?discord_error=" in location
    assert "widerrufen" in location
