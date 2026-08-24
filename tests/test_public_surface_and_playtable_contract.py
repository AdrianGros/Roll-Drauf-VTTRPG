"""Emergency public-surface and Playtable empty-state contracts."""

from pathlib import Path

import pytest

from vtt import create_app


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAY_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "play.html"
PLAY_UI = REPO_ROOT / "vtt" / "static" / "js" / "play-ui.js"


@pytest.fixture
def app():
    return create_app(config_name="testing")


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.mark.parametrize("path", ["/", "/showcase", "/showcase.html"])
def test_public_review_paths_are_reviewable_landing_pages(client, path):
    response = client.get(path, follow_redirects=False)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Roll-Drauf VTT" in html
    assert "Beyond20-Integration ansehen" in html
    assert 'href="/login.html"' in html
    assert 'href="/beyond20.html"' in html
    assert 'href="#"' not in html
    assert "placeholder" not in html.lower()
    assert "coming soon" not in html.lower()
    assert "disabled" not in html.lower()


def test_beyond20_review_page_is_public_and_names_the_supported_contract(client):
    response = client.get("/beyond20.html")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    for event_name in (
        "Beyond20_RenderedRoll",
        "Beyond20_UpdateHP",
        "Beyond20_UpdateConditions",
        "Beyond20_UpdateCombat",
    ):
        assert event_name in html
    assert "Sessiondaten geschützt" in html


def test_playtable_explains_disabled_existing_map_action():
    template = PLAY_TEMPLATE.read_text(encoding="utf-8")
    script = PLAY_UI.read_text(encoding="utf-8")

    assert 'id="layerAddStatus"' in template
    assert 'role="status"' in template
    assert "Noch keine Kampagnenkarte vorhanden" in script
    assert "Alle vorhandenen Kampagnenkarten sind bereits Seiten" in script
    assert "select.onchange = syncButton" in script
