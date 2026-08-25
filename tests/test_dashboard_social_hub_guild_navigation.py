"""Dashboard overview keeps the personal VTT path separate from Discord."""

from pathlib import Path

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import Campaign, Character, GameSession, Role, User
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


def test_dashboard_home_snapshot_is_a_personal_vtt_start_point(client, app):
    with app.app_context():
        user = _create_user()
        user_id = user.id
        campaign = Campaign(name="Die Bernsteinfahrt", description="Vorbereitung für Kapitel I.", owner_id=user.id)
        db.session.add(campaign)
        db.session.flush()
        db.session.add(Campaign(name="Archivierte Runde", status="paused", owner_id=user.id))

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
    assert data["overview_scope"]["kind"] == "personal_vtt_home"
    assert data["overview_scope"]["read_only"] is True
    assert "Kampagnen" in data["overview_scope"]["note"]
    assert "guilds" not in data
    assert "primary_guild" not in data
    assert "priorities" not in data
    assert "quick_links" not in data
    assert all(item["section"] not in {"social", "guilds"} for item in data["feed_preview"])
    assert {item["section"] for item in data["feed_preview"]} == {"campaigns"}
    assert {item["title"] for item in data["feed_preview"]} == {"Die Bernsteinfahrt"}

    with app.app_context():
        resolved_user = db.session.get(User, user_id)
        assert resolved_user is not None


def test_standard_player_gets_distinct_first_actions_without_discord(client, app):
    with app.app_context():
        _create_user(username="emptyplayer", email="emptyplayer@example.com")

    _login(client, username="emptyplayer")
    data = client.get("/api/dashboard/home").get_json()

    assert data["primary_action"]["label"] == "Charakter anlegen"
    assert data["secondary_action"]["label"] == "Kampagnen öffnen"
    assert data["primary_action"]["href"] != data["secondary_action"]["href"]


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
    assert "book-toc" in js
    assert "showRunningHead: false" in js
    assert "showRightHeader: false" in js
    assert "book-page-folio--left" in js
    assert "book-page-folio--right" in js
    assert "book-folio" not in js
    assert "book-folio" not in css
    assert "Live-Pfad" not in dashboard_home
    assert "Spieltisch vorbereiten" not in dashboard_home
    assert "Gemeinschaftssaal" not in dashboard_home
    assert "home.overview_scope_default" in js
    assert "buildDashboardGuildPanel" not in js
    assert "data-dashboard-guild-switch" not in js
    assert "/api/dashboard/guilds/primary" not in dashboard_home
    assert ".book-home-rail {" in css
    assert ".book-home-feed {" in css
    assert "book-home-guild-panel" not in css
    assert "book-home-context-grid" not in css
    assert "Übersicht wird vorbereitet" in dashboard_template
    assert ">Übersicht</button>" in dashboard_template
    assert "Neuigkeiten und Hinweise" not in dashboard_home
    assert "/api/dashboard/chat" not in dashboard_home
    assert "/campaigns/<int:campaign_id>/sessions/<int:session_id>/chat/messages" in community_routes
