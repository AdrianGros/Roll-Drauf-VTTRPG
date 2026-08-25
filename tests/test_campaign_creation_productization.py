"""M17.4 tests: campaign creation productization."""

import pytest

from vtt import create_app


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_campaigns_route_exposes_real_book_creation_surface(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "+ Kampagne anlegen" in html
    assert "Neue Kampagne im Buch anlegen" in html
    assert 'id="campaignCreateForm"' in html
    assert 'id="campaignCreateName"' in html
    assert 'id="campaignCreateDescription"' in html
    assert 'id="campaignCreateMaxPlayers"' in html
    assert "submitCampaignCreationForm(event)" in html
    assert "Kampagnen-Hub öffnen" in html


def test_campaign_creation_no_longer_uses_prompt_chain_as_primary_path(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'window.prompt("Name der Kampagne:")' not in html
    assert 'window.prompt("Kurze Beschreibung (optional):", "")' not in html
    assert 'window.prompt("Maximale Spielerzahl (2-20):", "6")' not in html
    assert "openCampaignCreationPanel()" in html
    assert "async function submitCampaignCreationForm(event)" in html
    assert "consumeCampaignIntent(\"create\")" in html


def test_campaign_creation_success_copy_points_into_hub_and_session_prep(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Danach öffnet sich direkt der Kampagnen-Hub." in html
    assert "Als Nächstes: Hub öffnen, Spieler einladen oder die erste Session vorbereiten." in html
    assert "Session-Prep folgt im Hub" not in html
    assert "Session-Prep" in html
    assert "viewCampaign(created.id)" in html
