"""Seiten-Hinzufügen-Flow (Adrian, 2026-08-25): „Hinzufügen" ist DER Weg,
eine neue Seite anzulegen — und er darf nie in der Sackgasse „alle Karten
sind bereits Seiten" enden.  Eine bereits verwendete Karte wird auf Wunsch
kopiert (neue CampaignMap, gleiche Grafik, eigene Tokens), statt mit 409
abzublocken.  Szenario vor Fix (§10)."""

from datetime import datetime

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import Campaign, CampaignMap, CampaignMember, GameSession, Role, User


def _login(client, username, password="Password123!"):
    response = client.post("/api/auth/login",
                           json={"username": username, "password": password})
    assert response.status_code == 200


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    with app.app_context():
        db.create_all()
        for role_name in ["Player", "DM", "Admin"]:
            db.session.add(Role(name=role_name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def dm_client(app):
    user = User(username="seiten_dm", email="seiten_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()

    campaign = Campaign(name="Seiten-Kampagne", description="",
                        owner_id=user.id, status="active", max_players=6)
    db.session.add(campaign)
    db.session.flush()
    db.session.add(CampaignMember(
        campaign_id=campaign.id, user_id=user.id, campaign_role="DM",
        status="active", joined_at=datetime.utcnow(),
        invited_at=datetime.utcnow(), accepted_at=datetime.utcnow(),
        invited_by=user.id))

    world = CampaignMap(campaign_id=campaign.id, name="Welt", width=20,
                        height=20, grid_size=70,
                        background_url="/api/assets/abc123/preview",
                        created_by=user.id)
    spare = CampaignMap(campaign_id=campaign.id, name="Hafen", width=10,
                        height=10, created_by=user.id)
    db.session.add_all([world, spare])
    db.session.flush()
    session = GameSession(campaign_id=campaign.id, map_id=world.id,
                          name="Seiten-Session", status="in_progress")
    db.session.add(session)
    db.session.commit()

    client = app.test_client()
    _login(client, "seiten_dm")
    client.ctx = {"campaign": campaign, "session": session,
                  "world": world, "spare": spare}
    return client


def _layers_url(client):
    ctx = client.ctx
    return (f"/api/play/campaigns/{ctx['campaign'].id}"
            f"/sessions/{ctx['session'].id}/scene-stack")


class TestLayerAddFlow:
    def _init_stack(self, client):
        response = client.post(f"{_layers_url(client)}/init",
                               json={"map_ids": [client.ctx["world"].id]})
        assert response.status_code == 201, response.get_json()

    def test_attach_unused_map_with_label(self, app, dm_client):
        self._init_stack(dm_client)
        response = dm_client.post(
            f"{_layers_url(dm_client)}/layers",
            json={"campaign_map_id": dm_client.ctx["spare"].id,
                  "label": "Hafenseite"})
        assert response.status_code == 201
        assert response.get_json()["layer"]["label"] == "Hafenseite"

    def test_used_map_without_copy_flag_keeps_409(self, app, dm_client):
        self._init_stack(dm_client)
        response = dm_client.post(
            f"{_layers_url(dm_client)}/layers",
            json={"campaign_map_id": dm_client.ctx["world"].id})
        assert response.status_code == 409

    def test_used_map_with_copy_flag_creates_page_copy(self, app, dm_client):
        self._init_stack(dm_client)
        world = dm_client.ctx["world"]
        maps_before = CampaignMap.query.filter_by(
            campaign_id=dm_client.ctx["campaign"].id).count()

        response = dm_client.post(
            f"{_layers_url(dm_client)}/layers",
            json={"campaign_map_id": world.id, "label": "Welt B",
                  "allow_copy": True})
        assert response.status_code == 201, response.get_json()
        layer = response.get_json()["layer"]
        assert layer["label"] == "Welt B"
        assert layer["campaign_map_id"] != world.id

        copied = db.session.get(CampaignMap, layer["campaign_map_id"])
        assert copied is not None
        assert copied.name == "Welt B"
        assert copied.background_url == world.background_url
        assert (copied.width, copied.height, copied.grid_size) == (
            world.width, world.height, world.grid_size)
        assert CampaignMap.query.filter_by(
            campaign_id=dm_client.ctx["campaign"].id).count() == maps_before + 1
