"""Real browser: separate player and DM table surfaces, seat switch and target picker.

Owner decision 2026-11-01: the player surface does not mount DM controls,
not even hidden or disabled. A DM can sit at the table as a player and
switch back explicitly; other open tabs of that person follow.
"""
import re
from threading import Thread

import pytest
from flask_jwt_extended import create_access_token
from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import WSGIRequestHandler, make_server

from vtt import create_app
from vtt.config import TestingConfig
from vtt.extensions import db, socketio
from vtt.models import Campaign, CampaignMap, CampaignMember, GameSession, Role, TokenState, User
from vtt.play.service import ensure_session_state

DM_ONLY_IDS = [
    "toolWall", "toolLight", "btnVisionToggle", "wallEditPopover", "lightEditPopover",
    "tokenCreateVisibility", "mapUploadFile", "layerAddRow", "layerAddChoice", "initiativeControls",
    "btnStartCombat", "visionControls", "btnFogReset", "tokenUploadRow", "tokenLootSourceRow",
    "tokenVisibleRow", "visibleTokensPopover", "lootAddRow", "btnInitStack", "btnStart", "btnEnd",
    "readyCheckOutput",
]


class QuietHandler(WSGIRequestHandler):
    def log(self, *args):
        pass


def _user(username, role):
    user = User(username=username, email=f"{username}@example.test", password_hash="test", role_id=role.id,
                is_active=True, is_suspended=False, account_state="active", profile_tier="headmaster")
    db.session.add(user)
    db.session.flush()
    return user


@pytest.fixture
def table(tmp_path, monkeypatch):
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{tmp_path}/seat.db")
    monkeypatch.setitem(socketio.server_options, "async_mode", "threading")
    from vtt import socket_handlers
    socket_handlers._room_presence.clear()
    socket_handlers._connected_rooms.clear()
    socket_handlers._connected_users.clear()
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        role = Role(name="DM")
        db.session.add(role)
        db.session.flush()
        dm = _user("Seat DM", role)
        player = _user("Seat Player", role)
        campaign = Campaign(name="Tischplatz", owner_id=dm.id)
        db.session.add(campaign)
        db.session.flush()
        db.session.add(CampaignMember(campaign_id=campaign.id, user_id=player.id, campaign_role="Player",
                                      status="active"))
        map_ = CampaignMap(campaign_id=campaign.id, name="Karte", width=1000, height=1000, grid_size=50,
                           created_by=dm.id)
        db.session.add(map_)
        db.session.flush()
        session = GameSession(campaign_id=campaign.id, map_id=map_.id, name="Abend", status="in_progress")
        db.session.add(session)
        db.session.commit()
        state = ensure_session_state(campaign, session)
        state.active_map_id = map_.id
        tokens = {}
        for key, name, owner, kind, x in (("hero", "Heldin", player.id, "player", 100),
                                          ("goblin", "Goblin", None, "npc", 300)):
            token = TokenState(session_state_id=state.id, campaign_id=campaign.id, game_session_id=session.id,
                               map_id=map_.id, owner_user_id=owner, name=name, token_type=kind, x=x, y=100,
                               size=1, rotation=0, visibility="public", metadata_json={"position_mode": "pixel"},
                               version=1)
            db.session.add(token)
            db.session.flush()
            tokens[key] = token.id
        db.session.commit()
        cookies = {"dm": create_access_token(identity=str(dm.id)),
                   "player": create_access_token(identity=str(player.id))}
        route = f"/play?campaign_id={campaign.id}&session_id={session.id}"
    server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    monkeypatch.setattr(socketio.server.eio, "cors_allowed_origins", [origin])
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

            def open_as(who, path=route):
                context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
                context.add_cookies([{"name": "access_token_cookie", "value": cookies[who], "url": origin,
                                      "httpOnly": True}])
                page = context.new_page()
                page.set_default_timeout(10000)
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(origin + path)
                _ready(page)
                return page

            yield {"open_as": open_as, "route": route, "tokens": tokens}
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
    assert errors == [], errors


def _ready(page):
    # The surface is composed once the server answered; #btnRoll alone is
    # enabled in the static markup already.
    expect(page.locator("body[data-table-seat]")).to_have_count(1)
    expect(page.locator("#roleBadge")).not_to_have_text("-")


def _seat(page):
    return page.locator("body").get_attribute("data-table-seat")


def _assert_player_surface(page):
    assert _seat(page) == "player"
    assert page.locator("template[data-dm-layer]").count() == 0
    for element_id in DM_ONLY_IDS:
        assert page.locator(f"#{element_id}").count() == 0, element_id
    values = page.locator("#rollVisibility option").evaluate_all("nodes => nodes.map(node => node.value)")
    assert values == ["public", "gm_only"]


def _open_menu_and_switch(page, expected_label):
    page.locator("#btnBack").click()
    item = page.locator("#appMenuSeat")
    expect(item).to_have_text(expected_label)
    with page.expect_navigation():
        item.click()
    _ready(page)


def test_player_surface_mounts_no_dm_controls(table):
    page = table["open_as"]("player")

    _assert_player_surface(page)
    assert page.locator("#appMenuSeat").count() == 0
    expect(page.locator("#roleBadge")).to_have_text("PLAYER")


def test_dm_surface_has_its_tools_and_hidden_tools_stay_hidden(table):
    page = table["open_as"]("dm")

    assert _seat(page) == "dm"
    expect(page.locator("#toolWall")).to_be_visible()
    expect(page.locator("#toolLight")).to_be_visible()
    assert page.locator("#btnStart").count() == 1
    # Raster only shows with the measure tool (the [hidden] CSS fix).
    expect(page.locator("#btnMeasureSnap")).to_be_hidden()
    page.locator('.tool-btn[data-tool="measure"]').click()
    expect(page.locator("#btnMeasureSnap")).to_be_visible()


def test_dm_sits_as_player_and_takes_the_dm_seat_back(table):
    page = table["open_as"]("dm")

    _open_menu_and_switch(page, "Als Spieler am Tisch sitzen")
    _assert_player_surface(page)
    expect(page.locator("#roleBadge")).to_contain_text("Spielleitung sitzt als Spieler")

    page.reload()
    _ready(page)
    _assert_player_surface(page)

    _open_menu_and_switch(page, "Als Spielleitung übernehmen")
    assert _seat(page) == "dm"
    expect(page.locator("#toolWall")).to_be_visible()


def test_other_tab_follows_the_seat_switch(table):
    first = table["open_as"]("dm")
    second = table["open_as"]("dm")
    expect(first.locator("#presenceRoster")).to_contain_text("Seat DM")

    with first.expect_navigation():
        _open_menu_and_switch(second, "Als Spieler am Tisch sitzen")
    _ready(first)
    _assert_player_surface(first)


def test_hub_entry_as_player_drops_the_parameter(table):
    page = table["open_as"]("dm", table["route"] + "&seat=player")

    _assert_player_surface(page)
    assert "seat=" not in page.url


def test_attack_slot_asks_for_a_target(table):
    page = table["open_as"]("player")
    hero, goblin = table["tokens"]["hero"], table["tokens"]["goblin"]

    page.locator(f'.token-marker[data-token-id="{hero}"]').click()
    attack = page.locator('.hotbar-slot[data-action-code="attack_basic"]')
    expect(attack).to_be_enabled()

    picking = re.compile(r"\bis-picking-target\b")
    attack.click()
    expect(page.locator("body")).to_have_class(picking)
    page.keyboard.press("Escape")
    expect(page.locator("body")).not_to_have_class(picking)

    attack.click()
    page.locator(f'.token-marker[data-token-id="{goblin}"]').click()
    expect(page.locator("#chatLog")).to_contain_text("Heldin setzt Attack gegen Goblin ein.")
    expect(page.locator("body")).not_to_have_class(picking)
