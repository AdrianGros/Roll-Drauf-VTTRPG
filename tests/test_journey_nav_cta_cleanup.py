"""Targeted journey/nav/CTA checks for M16."""

import pytest

from vtt import create_app


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.mark.parametrize(
    ("path", "active_label"),
    [
        ("/dashboard", "Übersicht"),
        ("/campaigns", "Kampagnen"),
        ("/characters", "Charaktere"),
        ("/character-sheet?id=42&mode=edit", "Charaktere"),
    ],
)
def test_non_play_routes_share_primary_spellbook_nav(path, active_label, client):
    response = client.get(path)

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'book-dashboard-topbar' in html
    assert 'book-dashboard-ribbon' in html
    assert 'aria-label="Buchnavigation"' in html
    assert '>Übersicht<' in html
    assert '>Kampagnen<' in html
    assert '>Charaktere<' in html
    assert 'aria-current="page"' in html or 'book-dashboard-ribbon-btn is-active' in html
    assert f'>{active_label}<' in html


def test_campaigns_route_surfaces_clearer_play_path_language(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Hub öffnen" in html
    assert "Session fortsetzen" in html
    assert "Session betreten" in html
    assert "Zu Play" in html
    assert "Hauptweg: Home -> Kampagnen-Hub -> Session-Prep -> Session starten oder fortsetzen -> Play." in html
    assert "Launch Game" not in html
    assert ">Reingehen<" not in html


def test_campaigns_play_entry_still_uses_bookscene_seam(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "function openPlay(campaignId, sessionId)" in html
    assert "BookScene.enterPlay({" in html
    assert "sourceRoute: 'campaigns'" in html
    assert "window.location.href = `/play" not in html
