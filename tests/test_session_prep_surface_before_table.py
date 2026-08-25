"""M17.6 tests: dedicated session-prep surface before table."""

import pytest

from vtt import create_app


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_campaigns_route_exposes_dedicated_session_prep_surface(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Vorbereitungsbereich" in html
    assert 'id="campaignSessionPrepSurface"' in html
    assert "Vor dem Spielabend" in html
    assert 'id="sessionPrepSelect"' in html
    assert "Session-Prep" in html
    assert "Prep öffnen" in html


def test_session_prep_surface_makes_state_and_next_steps_clearer(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "letzte Buchstopp vor dem Tisch" in html
    assert "Welche Session ist das?" in html
    assert "Nächster Schritt" in html
    assert "Readiness:" in html
    assert "Sessionliste" in html
    assert "Zurück zum Kampagnen-Hub" in html


def test_session_prep_surface_connects_existing_prep_pillars_honestly(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Participants / Invite Context" in html
    assert "Character Context" in html
    assert "Map Context" in html
    assert "Asset Context" in html
    assert 'id="sessionPrepCharacterCard"' in html
    assert "Zugewiesen" in html
    assert "Verfügbar für diese Session" in html
    assert "Map Workspace folgt" not in html
    assert "Import / Export folgt" not in html
    assert "Assets, Uploads und Vorschau sind verfügbar." in html


def test_session_prep_surface_keeps_play_entry_seam_owned(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "function openPlay(campaignId, sessionId)" in html
    assert "BookScene.enterPlay({" in html
    assert "sourceRoute: 'campaigns'" in html
    assert "window.location.href = `/play" not in html
