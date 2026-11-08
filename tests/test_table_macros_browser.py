"""Real browser: fill the Charakter-Makroleiste from the sheet and roll at the table."""
import os
from pathlib import Path
from threading import Thread

import pytest
from flask_jwt_extended import create_access_token
from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import WSGIRequestHandler, make_server

from vtt import create_app
from vtt.config import TestingConfig
from vtt.extensions import db, socketio
from vtt.models import Campaign, CampaignMap, CampaignMember, Character, GameSession, TokenState
from vtt.models.role import init_default_roles
from vtt.play.service import ensure_session_state
from vtt.rules_content.creator_rules import load_creator_data

from tests.test_srd_creator_api import _client, finalized


class QuietHandler(WSGIRequestHandler):
    def log(self, *args):
        pass


@pytest.fixture
def table(tmp_path, monkeypatch):
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{tmp_path}/macros.db")
    monkeypatch.setitem(socketio.server_options, "async_mode", "threading")
    from vtt import socket_handlers
    socket_handlers._room_presence.clear()
    socket_handlers._connected_rooms.clear()
    socket_handlers._connected_users.clear()
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        init_default_roles(db.session)
        dm = _client(app, "macro_dm")
        player = _client(app, "macro_player")
        char = finalized(player, load_creator_data())
        campaign = Campaign(name="Makros", owner_id=dm.user_id, status="active", max_players=6)
        db.session.add(campaign)
        db.session.flush()
        db.session.add(CampaignMember(campaign_id=campaign.id, user_id=player.user_id, campaign_role="Player",
                                      status="active"))
        map_ = CampaignMap(campaign_id=campaign.id, name="Karte", width=1000, height=1000, grid_size=50,
                           created_by=dm.user_id)
        db.session.add(map_)
        db.session.flush()
        session = GameSession(campaign_id=campaign.id, map_id=map_.id, name="Abend", status="in_progress")
        db.session.add(session)
        db.session.get(Character, char["id"]).campaign_id = campaign.id
        db.session.commit()
        state = ensure_session_state(campaign, session)
        state.active_map_id = map_.id
        token = TokenState(session_state_id=state.id, campaign_id=campaign.id, game_session_id=session.id,
                           map_id=map_.id, owner_user_id=player.user_id, character_id=char["id"], name="Mira",
                           token_type="player", x=100, y=100, size=1, rotation=0, visibility="public",
                           metadata_json={"position_mode": "pixel"}, version=1)
        db.session.add(token)
        db.session.commit()
        token_id = token.id
        cookie = create_access_token(identity=str(player.user_id))
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
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
            context.add_cookies([{"name": "access_token_cookie", "value": cookie, "url": origin, "httpOnly": True}])
            page = context.new_page()
            page.set_default_timeout(10000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + route)
            expect(page.locator("body[data-table-seat]")).to_have_count(1)
            yield page, token_id
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
    assert errors == [], errors


def _proof(page, name):
    if os.environ.get("VTT_PROOF_DIR"):
        out = Path(os.environ["VTT_PROOF_DIR"])
        out.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out / name))


def test_fill_the_macro_bar_and_roll_at_the_table(table):
    page, token_id = table
    page.locator(f'.token-marker[data-token-id="{token_id}"]').click()
    edit = page.locator("[data-macro-edit]")
    expect(edit).to_be_visible()

    edit.click()
    editor = page.locator("#macroEditor")
    expect(editor).to_be_visible()
    expect(page.locator("#macroEditorTitle")).to_have_text("Makros · Mira")
    editor.locator('[data-macro-add="initiative:"]').click()
    editor.locator('[data-macro-add="skill:arkane-kunde"]').click()
    expect(editor.locator(".macro-editor-slot")).to_have_count(2)
    editor.locator(".macro-editor-slot").nth(1).locator('[data-macro-move="-1"]').click()
    expect(editor.locator(".macro-editor-slot").first).to_contain_text("Arkane Kunde")
    _proof(page, "macro-editor.png")
    page.locator("#btnMacroEditorSave").click()
    expect(editor).to_be_hidden()

    macros = page.locator(".hotbar-macro[data-macro-index]")
    expect(macros).to_have_count(2)
    expect(macros.first).to_have_attribute("data-hotkey", "4")
    _proof(page, "macro-hotbar.png")
    macros.first.click()
    expect(page.locator("#chatLog")).to_contain_text("Mira Eulenfeder · Arkane Kunde · 1d20+10:")

    page.locator("#mapViewport").click(position={"x": 600, "y": 600})
    page.locator(f'.token-marker[data-token-id="{token_id}"]').click()
    page.keyboard.press("5")
    expect(page.locator("#chatLog")).to_contain_text("Mira Eulenfeder · Initiative · 1d20+1:")

    page.reload()
    expect(page.locator("body[data-table-seat]")).to_have_count(1)
    page.locator(f'.token-marker[data-token-id="{token_id}"]').click()
    expect(page.locator(".hotbar-macro[data-macro-index]")).to_have_count(2)
