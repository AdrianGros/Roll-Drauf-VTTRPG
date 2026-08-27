"""S09 (loot transfer) server-side tests.

CRITICAL risk per the research doc: a network retry must never duplicate a
transfer, and the server -- never the client -- must be the source of
truth for what gets moved. These tests hit the real REST endpoints
(vtt/play/routes.py: play_transfer_loot, play_get_token_loot,
play_add_token_loot_item), not just the model layer, so a permission or
idempotency regression in the route itself would be caught here.
"""

from datetime import datetime

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import (
    Campaign,
    CampaignMap,
    CampaignMember,
    Character,
    ChatMessage,
    GameSession,
    InventoryItem,
    LootTransfer,
    Role,
    TokenLoot,
    TokenState,
    User,
)
from vtt.play.service import ensure_session_state


def _login(client, username, password="Password123!"):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response


def _create_campaign(owner_user, name):
    campaign = Campaign(
        name=name,
        description="campaign for loot transfer tests",
        owner_id=owner_user.id,
        status="active",
        max_players=6,
    )
    db.session.add(campaign)
    db.session.flush()
    db.session.add(
        CampaignMember(
            campaign_id=campaign.id,
            user_id=owner_user.id,
            campaign_role="DM",
            status="active",
            joined_at=datetime.utcnow(),
            invited_at=datetime.utcnow(),
            accepted_at=datetime.utcnow(),
            invited_by=owner_user.id,
        )
    )
    db.session.commit()
    return campaign


def _add_member(campaign, user, campaign_role="Player"):
    db.session.add(
        CampaignMember(
            campaign_id=campaign.id,
            user_id=user.id,
            campaign_role=campaign_role,
            status="active",
            joined_at=datetime.utcnow(),
            invited_at=datetime.utcnow(),
            accepted_at=datetime.utcnow(),
            invited_by=campaign.owner_id,
        )
    )
    db.session.commit()


def _add_map_and_session(campaign, creator_user, session_status="in_progress"):
    campaign_map = CampaignMap(
        campaign_id=campaign.id,
        name="Loot Map",
        width=20,
        height=20,
        created_by=creator_user.id,
    )
    db.session.add(campaign_map)
    db.session.flush()
    session = GameSession(
        campaign_id=campaign.id,
        map_id=campaign_map.id,
        name="Loot Session",
        status=session_status,
    )
    db.session.add(session)
    db.session.commit()
    return campaign_map, session


def _add_loot_token(state, campaign, session, campaign_map, name="Goblin (tot)"):
    token = TokenState(
        session_state_id=state.id,
        campaign_id=campaign.id,
        game_session_id=session.id,
        map_id=campaign_map.id,
        name=name,
        token_type="npc",
        x=1,
        y=1,
        is_loot_source=True,
    )
    db.session.add(token)
    db.session.commit()
    return token


def _add_loot_item(token, name="Heiltrank", quantity=5, **kwargs):
    item = TokenLoot(token_id=token.id, name=name, quantity=quantity, **kwargs)
    db.session.add(item)
    db.session.commit()
    return item


def _add_character(user, campaign, name, is_party_stash=False):
    character = Character(
        user_id=user.id,
        campaign_id=campaign.id,
        name=name,
        is_party_stash=is_party_stash,
    )
    db.session.add(character)
    db.session.commit()
    return character


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
def dm_user(app):
    user = User(username="loot_dm", email="loot_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="loot_player", email="loot_player@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def other_player_user(app):
    user = User(username="loot_other", email="loot_other@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def dm_client(app, dm_user):
    client = app.test_client()
    _login(client, dm_user.username)
    return client


@pytest.fixture
def player_client(app, player_user):
    client = app.test_client()
    _login(client, player_user.username)
    return client


@pytest.fixture
def other_player_client(app, other_player_user):
    client = app.test_client()
    _login(client, other_player_user.username)
    return client


def _transfer_url(campaign, session):
    return f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/loot/transfer"


class TestTransferHappyPath:
    def test_transfer_moves_quantity_and_stacks_onto_existing_item(
        self, app, dm_user, player_user, dm_client, player_client
    ):
        campaign = _create_campaign(dm_user, "Beute-Kampagne")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_session(campaign, dm_user)
        state = ensure_session_state(campaign, session)
        token = _add_loot_token(state, campaign, session, campaign_map)
        item = _add_loot_item(token, name="Heiltrank", quantity=5)
        character = _add_character(player_user, campaign, "Held")
        db.session.add(InventoryItem(character_id=character.id, name="Heiltrank", quantity=2))
        db.session.commit()

        response = player_client.post(
            _transfer_url(campaign, session),
            json={
                "idempotency_key": "key-1",
                "source_token_id": token.id,
                "recipient_character_id": character.id,
                "items": [{"token_loot_id": item.id, "quantity": 3}],
            },
        )
        assert response.status_code == 201, response.get_json()
        body = response.get_json()["transfer"]
        assert body["items_transferred"] == [{"name": "Heiltrank", "quantity": 3}]

        db.session.refresh(item)
        assert item.quantity == 2, "source stack must decrement by the transferred amount"

        stacked = InventoryItem.query.filter_by(character_id=character.id, name="Heiltrank").all()
        assert len(stacked) == 1, "must stack onto the existing entry, not create a duplicate"
        assert stacked[0].quantity == 5

        assert LootTransfer.query.filter_by(idempotency_key="key-1").count() == 1
        chat = ChatMessage.query.filter_by(game_session_id=session.id, content_type="loot_transfer").first()
        assert chat is not None, "a transfer must leave an audit trail in session chat"

    def test_depleting_source_item_deletes_the_token_loot_row(
        self, app, dm_user, player_user, dm_client, player_client
    ):
        campaign = _create_campaign(dm_user, "Beute-Kampagne 2")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_session(campaign, dm_user)
        state = ensure_session_state(campaign, session)
        token = _add_loot_token(state, campaign, session, campaign_map)
        item = _add_loot_item(token, name="Pfeil", quantity=3)
        character = _add_character(player_user, campaign, "Held")

        response = player_client.post(
            _transfer_url(campaign, session),
            json={
                "idempotency_key": "key-deplete",
                "source_token_id": token.id,
                "recipient_character_id": character.id,
                "items": [{"token_loot_id": item.id, "quantity": 3}],
            },
        )
        assert response.status_code == 201, response.get_json()
        assert TokenLoot.query.filter_by(id=item.id).first() is None

    def test_dm_can_transfer_into_party_stash_character(
        self, app, dm_user, player_user, dm_client, player_client
    ):
        campaign = _create_campaign(dm_user, "Beute-Kampagne 3")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_session(campaign, dm_user)
        state = ensure_session_state(campaign, session)
        token = _add_loot_token(state, campaign, session, campaign_map)
        item = _add_loot_item(token, name="Goldmünzen", quantity=100)
        stash = _add_character(player_user, campaign, "Truhe", is_party_stash=True)

        response = dm_client.post(
            _transfer_url(campaign, session),
            json={
                "idempotency_key": "key-stash",
                "source_token_id": token.id,
                "recipient_character_id": stash.id,
                "items": [{"token_loot_id": item.id, "quantity": 100}],
            },
        )
        assert response.status_code == 201, response.get_json()


class TestIdempotency:
    def test_repeated_request_with_same_key_does_not_double_transfer(
        self, app, dm_user, player_user, dm_client, player_client
    ):
        campaign = _create_campaign(dm_user, "Idempotenz-Kampagne")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_session(campaign, dm_user)
        state = ensure_session_state(campaign, session)
        token = _add_loot_token(state, campaign, session, campaign_map)
        item = _add_loot_item(token, name="Schwert", quantity=1)
        character = _add_character(player_user, campaign, "Held")

        payload = {
            "idempotency_key": "retry-key",
            "source_token_id": token.id,
            "recipient_character_id": character.id,
            "items": [{"token_loot_id": item.id, "quantity": 1}],
        }
        first = player_client.post(_transfer_url(campaign, session), json=payload)
        assert first.status_code == 201, first.get_json()

        second = player_client.post(_transfer_url(campaign, session), json=payload)
        assert second.status_code == 200
        assert second.get_json().get("cached") is True

        assert LootTransfer.query.filter_by(idempotency_key="retry-key").count() == 1
        stacked = InventoryItem.query.filter_by(character_id=character.id, name="Schwert").first()
        assert stacked.quantity == 1, "a retried request must never re-execute the transfer"


class TestQuantityAndPermissionGuards:
    def test_requesting_more_than_available_is_rejected_and_mutates_nothing(
        self, app, dm_user, player_user, dm_client, player_client
    ):
        campaign = _create_campaign(dm_user, "Mangel-Kampagne")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_session(campaign, dm_user)
        state = ensure_session_state(campaign, session)
        token = _add_loot_token(state, campaign, session, campaign_map)
        item = _add_loot_item(token, name="Trank", quantity=2)
        character = _add_character(player_user, campaign, "Held")

        response = player_client.post(
            _transfer_url(campaign, session),
            json={
                "idempotency_key": "over-request",
                "source_token_id": token.id,
                "recipient_character_id": character.id,
                "items": [{"token_loot_id": item.id, "quantity": 10}],
            },
        )
        assert response.status_code == 409
        db.session.refresh(item)
        assert item.quantity == 2, "a rejected transfer must not partially decrement the source"
        assert LootTransfer.query.filter_by(idempotency_key="over-request").count() == 0

    def test_player_cannot_transfer_into_another_players_character(
        self, app, dm_user, player_user, other_player_user, dm_client, player_client
    ):
        campaign = _create_campaign(dm_user, "Fremde-Kampagne")
        _add_member(campaign, player_user)
        _add_member(campaign, other_player_user)
        campaign_map, session = _add_map_and_session(campaign, dm_user)
        state = ensure_session_state(campaign, session)
        token = _add_loot_token(state, campaign, session, campaign_map)
        item = _add_loot_item(token, name="Ring", quantity=1)
        foreign_character = _add_character(other_player_user, campaign, "Fremder Held")

        response = player_client.post(
            _transfer_url(campaign, session),
            json={
                "idempotency_key": "foreign-recipient",
                "source_token_id": token.id,
                "recipient_character_id": foreign_character.id,
                "items": [{"token_loot_id": item.id, "quantity": 1}],
            },
        )
        assert response.status_code == 403
        db.session.refresh(item)
        assert item.quantity == 1

    def test_cannot_transfer_from_a_token_not_flagged_as_loot_source(
        self, app, dm_user, player_user, dm_client, player_client
    ):
        campaign = _create_campaign(dm_user, "Kein-Beute-Kampagne")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_session(campaign, dm_user)
        state = ensure_session_state(campaign, session)
        token = _add_loot_token(state, campaign, session, campaign_map)
        token.is_loot_source = False
        db.session.commit()
        item = _add_loot_item(token, name="Amulett", quantity=1)
        character = _add_character(player_user, campaign, "Held")

        response = player_client.post(
            _transfer_url(campaign, session),
            json={
                "idempotency_key": "not-a-source",
                "source_token_id": token.id,
                "recipient_character_id": character.id,
                "items": [{"token_loot_id": item.id, "quantity": 1}],
            },
        )
        assert response.status_code == 400

    def test_transfer_is_blocked_outside_a_live_session(
        self, app, dm_user, player_user, dm_client, player_client
    ):
        campaign = _create_campaign(dm_user, "Wartend-Kampagne")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_session(campaign, dm_user, session_status="scheduled")
        state = ensure_session_state(campaign, session)
        token = _add_loot_token(state, campaign, session, campaign_map)
        item = _add_loot_item(token, name="Karte", quantity=1)
        character = _add_character(player_user, campaign, "Held")

        response = player_client.post(
            _transfer_url(campaign, session),
            json={
                "idempotency_key": "not-live",
                "source_token_id": token.id,
                "recipient_character_id": character.id,
                "items": [{"token_loot_id": item.id, "quantity": 1}],
            },
        )
        assert response.status_code == 409


class TestAddTokenLootItem:
    def test_dm_stocking_a_token_flags_it_as_a_loot_source(self, app, dm_user, dm_client):
        campaign = _create_campaign(dm_user, "Bestueckungs-Kampagne")
        campaign_map, session = _add_map_and_session(campaign, dm_user)
        state = ensure_session_state(campaign, session)
        token = TokenState(
            session_state_id=state.id,
            campaign_id=campaign.id,
            game_session_id=session.id,
            map_id=campaign_map.id,
            name="Truhe",
            token_type="object",
            x=1,
            y=1,
        )
        db.session.add(token)
        db.session.commit()
        assert token.is_loot_source is False

        response = dm_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/loot/{token.id}/items",
            json={"name": "Diamant", "quantity": 1},
        )
        assert response.status_code == 201, response.get_json()
        db.session.refresh(token)
        assert token.is_loot_source is True
        assert TokenLoot.query.filter_by(token_id=token.id, name="Diamant").count() == 1

    def test_player_cannot_stock_a_token(self, app, dm_user, player_user, player_client):
        campaign = _create_campaign(dm_user, "Spieler-Bestueckungs-Kampagne")
        _add_member(campaign, player_user)
        campaign_map, session = _add_map_and_session(campaign, dm_user)
        state = ensure_session_state(campaign, session)
        token = _add_loot_token(state, campaign, session, campaign_map)

        response = player_client.post(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/loot/{token.id}/items",
            json={"name": "Verbotener Gegenstand", "quantity": 1},
        )
        assert response.status_code == 403
        assert TokenLoot.query.filter_by(token_id=token.id).count() == 0


class TestGetTokenLoot:
    def test_player_only_sees_own_characters_and_party_stash_as_recipients(
        self, app, dm_user, player_user, other_player_user, player_client
    ):
        campaign = _create_campaign(dm_user, "Empfaenger-Kampagne")
        _add_member(campaign, player_user)
        _add_member(campaign, other_player_user)
        campaign_map, session = _add_map_and_session(campaign, dm_user)
        state = ensure_session_state(campaign, session)
        token = _add_loot_token(state, campaign, session, campaign_map)
        _add_loot_item(token, name="Zaubertrank", quantity=1)

        own_character = _add_character(player_user, campaign, "Eigener Held")
        stash = _add_character(dm_user, campaign, "Gemeinsame Truhe", is_party_stash=True)
        _add_character(other_player_user, campaign, "Fremder Held")

        response = player_client.get(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/loot/{token.id}"
        )
        assert response.status_code == 200
        recipient_ids = {row["id"] for row in response.get_json()["recipients"]}
        assert recipient_ids == {own_character.id, stash.id}
