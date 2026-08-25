"""Desktop audit 2026-08-25 (docs/DESKTOP_AUDIT_BROWSER_JOURNEY_2026-08-25.md +
FIX_RESEARCH_DESKTOP_AUDIT_2026-08-25.md), rule §10 (Ticket→Szenario vor Fix):
these scenarios reproduce the audit findings BEFORE the fixes land.

D01/D03/D06 — a player holding an invite could not join through any visible
book UI, and the DM had to hand the code over via window.prompt. Fix A1 adds
an invite deep link: GET /api/invites/<token> (info) + GET /invite/<token>
(landing page) so the DM shares a URL instead of a code.

D05 — lobby.html was reachable through the template catch-all but linked
nowhere; it is deleted once the deep link exists (decision #3, fix research §4).
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import Campaign, CampaignMember, InviteToken, Role, User


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        for role_name in ["Player", "DM", "Admin"]:
            db.session.add(Role(name=role_name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def _make_user(username, email):
    user = User(username=username, email=email)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.flush()
    return user


def _login(client, username, password="Password123!"):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response


def _campaign_with_invite(dm, invited):
    campaign = Campaign(
        name="Tiefenwacht",
        description="deep-link scenario campaign",
        owner_id=dm.id,
        status="active",
        max_players=6,
    )
    db.session.add(campaign)
    db.session.flush()
    db.session.add(
        CampaignMember(
            campaign_id=campaign.id,
            user_id=dm.id,
            campaign_role="DM",
            status="active",
            joined_at=datetime.utcnow(),
        )
    )
    db.session.add(
        CampaignMember(
            campaign_id=campaign.id,
            user_id=invited.id,
            campaign_role="Player",
            status="invited",
            invited_by=dm.id,
            invited_at=datetime.utcnow(),
        )
    )
    token = InviteToken(
        campaign_id=campaign.id,
        token=InviteToken.generate_token(),
        invited_user_email=invited.email,
        created_by=dm.id,
    )
    db.session.add(token)
    db.session.commit()
    return campaign, token


class TestInviteInfoEndpoint:
    """GET /api/invites/<token> — resolves a bare token to its campaign so the
    landing page (and nothing else) can render; the token is the capability."""

    def test_valid_token_resolves_campaign(self, client, app):
        with app.app_context():
            dm = _make_user("regie", "regie@example.com")
            hero = _make_user("held", "held@example.com")
            campaign, token = _campaign_with_invite(dm, hero)
            token_value, campaign_id = token.token, campaign.id

        response = client.get(f"/api/invites/{token_value}")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "valid"
        assert payload["campaign_id"] == campaign_id
        assert payload["campaign_name"] == "Tiefenwacht"
        assert payload["dm_username"] == "regie"
        # The token itself must never be echoed back in the payload body.
        assert token_value not in response.get_data(as_text=True)

    def test_used_and_expired_tokens_report_their_state(self, client, app):
        with app.app_context():
            dm = _make_user("regie2", "regie2@example.com")
            hero = _make_user("held2", "held2@example.com")
            _, token = _campaign_with_invite(dm, hero)
            token.used_at = datetime.utcnow()
            db.session.commit()
            used_value = token.token

            dm3 = _make_user("regie3", "regie3@example.com")
            hero3 = _make_user("held3", "held3@example.com")
            _, expired = _campaign_with_invite(dm3, hero3)
            expired.expires_at = datetime.utcnow() - timedelta(hours=1)
            db.session.commit()
            expired_value = expired.token

        assert client.get(f"/api/invites/{used_value}").get_json()["status"] == "used"
        assert client.get(f"/api/invites/{expired_value}").get_json()["status"] == "expired"

    def test_unknown_token_is_404_without_detail(self, client):
        response = client.get("/api/invites/definitely-not-a-token")
        assert response.status_code == 404


class TestInviteLandingPage:
    """GET /invite/<token> — the landing page must be its own template, not the
    catch-all's login.html fallback (that fallback is exactly why the audit
    found no reachable join surface)."""

    def test_landing_page_is_served_not_login_fallback(self, client, app):
        with app.app_context():
            dm = _make_user("regie4", "regie4@example.com")
            hero = _make_user("held4", "held4@example.com")
            _, token = _campaign_with_invite(dm, hero)
            token_value = token.token

        response = client.get(f"/invite/{token_value}")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'id="inviteScene"' in html
        # Not the login fallback:
        assert 'id="loginForm"' not in html

    def test_landing_page_serves_even_for_bogus_token(self, client):
        # State rendering happens client-side via the info endpoint; the page
        # itself must load so it can show the German error state.
        response = client.get("/invite/bogus")
        assert response.status_code == 200
        assert 'id="inviteScene"' in response.get_data(as_text=True)


class TestDeepLinkAcceptFlow:
    """End to end over the APIs the landing page uses: info → accept."""

    def test_invited_player_joins_via_token_only(self, client, app):
        with app.app_context():
            dm = _make_user("regie5", "regie5@example.com")
            hero = _make_user("held5", "held5@example.com")
            campaign, token = _campaign_with_invite(dm, hero)
            token_value, campaign_id, hero_id = token.token, campaign.id, hero.id

        _login(client, "held5")
        info = client.get(f"/api/invites/{token_value}").get_json()
        assert info["status"] == "valid"

        csrf = None
        for cookie in client._cookies.values():  # noqa: SLF001 - test-only peek
            if cookie.key == "csrf_access_token":
                csrf = cookie.value
        accept = client.post(
            f"/api/campaigns/{info['campaign_id']}/accept-invite",
            json={"token": token_value},
            headers={"X-CSRF-TOKEN": csrf} if csrf else {},
        )
        assert accept.status_code == 200, accept.get_data(as_text=True)

        with app.app_context():
            member = CampaignMember.query.filter_by(
                campaign_id=campaign_id, user_id=hero_id
            ).one()
            assert member.status == "active"


class TestLobbyRemoval:
    """D05: lobby.html is deleted; the catch-all must no longer serve it as a
    page of its own (it falls back to login.html, which is fine — nothing
    links there)."""

    def test_lobby_template_is_gone(self):
        assert not (
            Path(__file__).resolve().parents[1] / "vtt" / "templates" / "lobby.html"
        ).exists()
