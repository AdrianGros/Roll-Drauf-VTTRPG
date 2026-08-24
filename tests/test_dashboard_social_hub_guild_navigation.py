"""M20 tests: dashboard social hub and guild navigation."""

from pathlib import Path

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import Campaign, Character, GameSession, Guild, GuildMembership, Role, User
from vtt.utils.time import utcnow


REPO_ROOT = Path(__file__).resolve().parents[1]
BOOK_SCENE_JS = REPO_ROOT / "vtt" / "static" / "js" / "book-scene.js"
BOOK_SCENE_CSS = REPO_ROOT / "vtt" / "static" / "css" / "book-scene.css"
DASHBOARD_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "dashboard.html"
DASHBOARD_HOME_ENDPOINT = REPO_ROOT / "vtt" / "endpoints" / "dashboard_home.py"
COMMUNITY_ROUTES = REPO_ROOT / "vtt" / "community" / "routes.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.fixture
def app():
    app = create_app(config_name="testing")

    with app.app_context():
        db.create_all()
        for role_name in ["Player", "DM", "Admin"]:
            if not Role.query.filter_by(name=role_name).first():
                db.session.add(Role(name=role_name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _create_user(username: str = "home_user", email: str = "home@example.com") -> User:
    role = Role.query.filter_by(name="Player").first()
    user = User(
        username=username,
        email=email,
        role_id=role.id,
        profile_tier="player",
        storage_quota_gb=5,
        active_campaigns_quota=3,
    )
    user.set_password("SecurePass123!")
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, username: str = "home_user", password: str = "SecurePass123!"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response


def test_dashboard_home_snapshot_adds_guild_layer_and_feed_first_home_state(client, app):
    with app.app_context():
        user = _create_user()
        user_id = user.id
        campaign = Campaign(name="Die Bernsteinfahrt", description="Vorbereitung für Kapitel I.", owner_id=user.id)
        db.session.add(campaign)
        db.session.flush()

        db.session.add(
            Character(
                user_id=user.id,
                campaign_id=campaign.id,
                name="Ela Sternspur",
                class_name="Bard",
                level=3,
            )
        )
        db.session.add(
            GameSession(
                campaign_id=campaign.id,
                name="Session 1",
                status="scheduled",
                session_state="preparing",
                scheduled_at=utcnow(),
            )
        )
        db.session.commit()

    _login(client)
    response = client.get("/api/dashboard/home")

    assert response.status_code == 200
    data = response.get_json()

    assert data["home_state"]["prep_blocker_count"] >= 1
    assert data["primary_action"]["label"] == "Session-Prep fortsetzen"
    assert data["secondary_action"]["label"] == "Charakterarchiv öffnen"
    assert data["social_scope"]["kind"] == "dashboard_home"
    assert data["social_scope"]["read_only"] is True
    assert "Session-Chat getrennt" in data["social_scope"]["note"]
    assert len(data["guilds"]) == 4
    assert data["primary_guild"]["is_primary"] is True
    assert {link["label"] for link in data["quick_links"]} == {
        "Social",
        "Guilds",
        "Kampagnen",
        "Charaktere",
        "Session Prep",
        "Play-Pfad",
    }
    assert any(item["section"] == "social" and item["title"] == "Gemeinschaftssaal" for item in data["feed_preview"])
    assert any(item["section"] == "guilds" for item in data["feed_preview"])
    assert any(item["section"] == "session-prep" for item in data["feed_preview"])

    with app.app_context():
        assert Guild.query.count() == 4
        membership = GuildMembership.query.filter_by(user_id=user_id).first()
        assert membership is not None


def test_dashboard_home_can_switch_primary_guild_without_touching_permissions(client, app):
    with app.app_context():
        user = _create_user(username="guildswitch", email="guildswitch@example.com")
        user_id = user.id

    _login(client, username="guildswitch")
    initial = client.get("/api/dashboard/home").get_json()
    initial_guild_id = initial["primary_guild"]["id"]
    target_guild = next(guild for guild in initial["guilds"] if guild["id"] != initial_guild_id)

    response = client.post("/api/dashboard/guilds/primary", json={"guild_id": target_guild["id"]})

    assert response.status_code == 200
    data = response.get_json()
    assert data["primary_guild"]["id"] == target_guild["id"]
    assert data["primary_guild"]["is_primary"] is True
    assert "Primaere Gilde gewechselt" in data["guild_notice"]

    with app.app_context():
        membership = GuildMembership.query.filter_by(user_id=user_id).first()
        assert membership is not None
        assert membership.guild_id == target_guild["id"]
        resolved_user = db.session.get(User, user_id)
        assert resolved_user.role.name == "Player"


def test_dashboard_assets_expose_home_ia_and_keep_social_separate_from_session_chat():
    js = _read(BOOK_SCENE_JS)
    css = _read(BOOK_SCENE_CSS)
    dashboard_template = _read(DASHBOARD_TEMPLATE)
    dashboard_home = _read(DASHBOARD_HOME_ENDPOINT)
    community_routes = _read(COMMUNITY_ROUTES)

    # B2: die Startseite ist jetzt Lesebändchen + Inhaltsverzeichnis
    # statt Hero-Prosa (Designbrief §5).
    assert "Weiterlesen" in js
    assert "book-toc" in js
    assert "Lesebändchen" in js
    assert "Übersicht / Social" in js
    assert "Gemeinschaftssaal" in dashboard_home
    assert "Dashboard-Social bleibt vom Session-Chat getrennt" in js
    assert "Guilds bleiben reine Meta-Identität." in js
    assert "data-dashboard-guild-switch" in js
    assert ".book-home-rail {" in css
    assert ".book-home-feed {" in css
    assert ".book-home-guild-panel," in css
    assert ".book-home-context-grid {" in css
    assert "Opening Home Page..." in dashboard_template
    assert ">Übersicht</button>" in dashboard_template
    assert "Dashboard-Social bleibt vom Session-Chat getrennt" in dashboard_home
    assert "/api/dashboard/chat" not in dashboard_home
    assert "/campaigns/<int:campaign_id>/sessions/<int:session_id>/chat/messages" in community_routes
