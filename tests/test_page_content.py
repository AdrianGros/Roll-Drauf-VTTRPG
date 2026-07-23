"""M65 tests: PageContent model + /api/content endpoints.

Covers the seed-if-missing idempotency (editors' changes must survive
every deploy), the public read endpoint pages actually fetch from, and
the admin-only read/write endpoints the content editor uses.
"""

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import PageContent, Role, User


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
        # create_app() already auto-seeded the real PAGE_CONTENT_DEFAULTS
        # (AUTO_CREATE_SCHEMA is on for the testing config too) - clear that
        # out so these tests exercise ensure_defaults() against a known,
        # controlled set rather than the real ~75-row baseline.
        PageContent.query.delete()
        for role_name in ["Player", "DM", "Admin"]:
            db.session.add(Role(name=role_name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def admin_client(app):
    user = _create_user("content_admin", 3, platform_role="admin")
    db.session.commit()
    client = app.test_client()
    _login(client, user.username)
    return client


@pytest.fixture
def player_client(app):
    user = _create_user("content_player", 1, platform_role="supporter")
    db.session.commit()
    client = app.test_client()
    _login(client, user.username)
    return client


@pytest.fixture
def anon_client(app):
    return app.test_client()


@pytest.fixture
def seeded_entries(app):
    with app.app_context():
        PageContent.ensure_defaults([
            {"page_key": "shared", "content_key": "ribbon.play_button", "text": "▶ Play", "description": "Play button"},
            {"page_key": "dashboard", "content_key": "home.hero_title", "text": "Dein Heimathafen vor dem Tisch", "description": "Hero heading"},
        ])
        db.session.commit()


# ── model: ensure_defaults idempotency ─────────────────────────────────────

def test_ensure_defaults_inserts_missing_rows(app):
    with app.app_context():
        PageContent.ensure_defaults([
            {"page_key": "shared", "content_key": "a", "text": "A"},
            {"page_key": "shared", "content_key": "b", "text": "B"},
        ])
        assert PageContent.query.count() == 2


def test_ensure_defaults_never_overwrites_existing_edit(app):
    with app.app_context():
        PageContent.ensure_defaults([{"page_key": "shared", "content_key": "a", "text": "Original"}])
        entry = PageContent.query.filter_by(page_key="shared", content_key="a").first()
        entry.text = "Edited by staff"
        db.session.commit()

        # Simulates a redeploy re-running the seed with the same default text
        PageContent.ensure_defaults([{"page_key": "shared", "content_key": "a", "text": "Original"}])

        assert PageContent.query.count() == 1
        assert PageContent.query.filter_by(page_key="shared", content_key="a").first().text == "Edited by staff"


def test_ensure_defaults_adds_new_keys_without_touching_others(app):
    with app.app_context():
        PageContent.ensure_defaults([{"page_key": "shared", "content_key": "a", "text": "Original"}])
        PageContent.query.filter_by(content_key="a").first().text = "Edited"
        db.session.commit()

        # A later code change adds a brand-new key
        PageContent.ensure_defaults([
            {"page_key": "shared", "content_key": "a", "text": "Original"},
            {"page_key": "shared", "content_key": "b", "text": "New key"},
        ])

        assert PageContent.query.count() == 2
        assert PageContent.query.filter_by(content_key="a").first().text == "Edited"
        assert PageContent.query.filter_by(content_key="b").first().text == "New key"


def test_get_content_map_returns_flat_key_value_dict(app, seeded_entries):
    with app.app_context():
        content_map = PageContent.get_content_map("dashboard")
        assert content_map == {"home.hero_title": "Dein Heimathafen vor dem Tisch"}


# ── GET /api/content/<page_key> — public ────────────────────────────────────

def test_public_content_endpoint_works_unauthenticated(anon_client, seeded_entries):
    response = anon_client.get("/api/content/shared")
    assert response.status_code == 200
    assert response.get_json() == {"ribbon.play_button": "▶ Play"}


def test_public_content_endpoint_empty_page_returns_empty_map(anon_client, seeded_entries):
    response = anon_client.get("/api/content/nonexistent-page")
    assert response.status_code == 200
    assert response.get_json() == {}


# ── admin endpoints — auth boundary ─────────────────────────────────────────

def test_admin_pages_list_denies_player(player_client, seeded_entries):
    response = player_client.get("/api/content/admin/pages")
    assert response.status_code == 403


def test_admin_pages_list_denies_anonymous(anon_client, seeded_entries):
    response = anon_client.get("/api/content/admin/pages")
    assert response.status_code == 401


def test_admin_pages_list_allows_admin(admin_client, seeded_entries):
    response = admin_client.get("/api/content/admin/pages")
    assert response.status_code == 200
    assert sorted(response.get_json()["pages"]) == ["dashboard", "shared"]


def test_admin_entries_list_allows_admin(admin_client, seeded_entries):
    response = admin_client.get("/api/content/admin/dashboard")
    assert response.status_code == 200
    entries = response.get_json()["entries"]
    assert len(entries) == 1
    assert entries[0]["content_key"] == "home.hero_title"
    assert entries[0]["description"] == "Hero heading"


def test_update_denies_player(player_client, seeded_entries):
    response = player_client.put(
        "/api/content/admin/dashboard/home.hero_title",
        json={"text": "Hacked"},
    )
    assert response.status_code == 403


# ── PUT /api/content/admin/<page_key>/<content_key> ─────────────────────────

def test_update_persists_new_text(admin_client, seeded_entries):
    response = admin_client.put(
        "/api/content/admin/dashboard/home.hero_title",
        json={"text": "Neue Ueberschrift"},
    )
    assert response.status_code == 200
    assert response.get_json()["entry"]["text"] == "Neue Ueberschrift"

    # Reflects immediately on the public endpoint - no redeploy needed.
    public = admin_client.get("/api/content/dashboard")
    assert public.get_json() == {"home.hero_title": "Neue Ueberschrift"}


def test_update_rejects_empty_text(admin_client, seeded_entries):
    response = admin_client.put(
        "/api/content/admin/dashboard/home.hero_title",
        json={"text": "   "},
    )
    assert response.status_code == 400


def test_update_rejects_unknown_key(admin_client, seeded_entries):
    response = admin_client.put(
        "/api/content/admin/dashboard/nonexistent.key",
        json={"text": "Doesn't matter"},
    )
    assert response.status_code == 404


def test_update_stamps_updated_by(admin_client, seeded_entries):
    response = admin_client.put(
        "/api/content/admin/dashboard/home.hero_title",
        json={"text": "Updated"},
    )
    assert response.get_json()["entry"]["updated_by"] == "content_admin"
