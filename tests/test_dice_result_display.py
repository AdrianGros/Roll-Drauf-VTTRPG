"""Visible per-die results through real Tools, Socket.IO and persisted chat."""
from pathlib import Path
from threading import Thread
import os

import pytest
from flask_jwt_extended import create_access_token
from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import WSGIRequestHandler, make_server

from vtt import create_app
from vtt.config import TestingConfig
from vtt.extensions import db, socketio
from vtt.models import Campaign, CampaignMap, GameSession, Role, User


class QuietHandler(WSGIRequestHandler):
    def log(self, *args):
        pass


@pytest.fixture
def dice_table(tmp_path, monkeypatch):
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{tmp_path}/dice.db")
    # This fixture serves Flask through threaded Werkzeug, not eventlet.
    monkeypatch.setattr(TestingConfig, "SOCKETIO_ASYNC_MODE", "threading", raising=False)
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        role = Role(name="DM")
        db.session.add(role)
        db.session.flush()
        user = User(username="Dice DM", email="dice@example.test", password_hash="test",
                    role_id=role.id, is_active=True, is_suspended=False,
                    account_state="active", profile_tier="headmaster")
        db.session.add(user)
        db.session.flush()
        campaign = Campaign(name="Dice display", owner_id=user.id)
        db.session.add(campaign)
        db.session.flush()
        map_ = CampaignMap(campaign_id=campaign.id, name="Dice map", width=1000,
                           height=1000, grid_size=50, created_by=user.id)
        db.session.add(map_)
        db.session.flush()
        session = GameSession(campaign_id=campaign.id, map_id=map_.id,
                              name="Dice session", status="in_progress")
        db.session.add(session)
        db.session.commit()
        token = create_access_token(identity=str(user.id))
        route = f"/play?campaign_id={campaign.id}&session_id={session.id}"
    server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    monkeypatch.setattr(socketio.server.eio, "cors_allowed_origins", [origin])
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(viewport={"width": 1440, "height": 1000},
                                          reduced_motion="reduce")
            context.add_init_script("window.__diceTableReady=0;window.addEventListener('rolldrauf:table-ready',()=>window.__diceTableReady++);")
            context.add_cookies([{"name": "access_token_cookie", "value": token,
                                 "url": origin, "httpOnly": True}])
            page = context.new_page()
            page.set_default_timeout(10000)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + route)
            expect(page.locator("#btnRoll")).to_be_enabled()
            page.wait_for_function('() => window.__diceTableReady>=2')
            expect(page.locator('#presenceRoster')).to_contain_text('Dice DM',timeout=15000)
            page.locator("#btnSidebarToggle").click()
            page.locator('.sidebar-tab[data-tab="tools"]').click()
            expect(page.locator("#diceInput")).to_be_visible()
            yield page, context, origin + route
            browser.close()
            assert errors == [], errors
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        with app.app_context():
            db.session.remove()
            db.engine.dispose()


@pytest.mark.parametrize("formula,values,mode,total,breakdown,persisted", [
    ("3d6", [2, 5, 4], "normal", 11, "Würfel: 2 + 5 + 4", "2 + 5 + 4 = 11"),
    ("3d6+2", [2, 5, 4], "normal", 13,
     "Würfel: 2 + 5 + 4 · Modifikator: +2", "2 + 5 + 4 +2 = 13"),
    ("2d6-3", [1, 1], "normal", -1,
     "Würfel: 1 + 1 · Modifikator: -3", "1 + 1 -3 = -1"),
    ("1d20+2", [7, 18], "advantage", 20,
     "Würfel: 18 · Modifikator: +2 · verworfen: 7", "18 +2 = 20"),
    ("1d20", [7, 18], "disadvantage", 7,
     "Würfel: 7 · verworfen: 18", "7 = 7"),
])
def test_roll_results_visible_for_roller_peer_and_after_reload(
    dice_table, monkeypatch, formula, values, mode, total, breakdown, persisted,
):
    page, context, url = dice_table
    peer = context.new_page()
    peer.goto(url)
    expect(peer.locator("#btnRoll")).to_be_enabled()
    peer.wait_for_function('() => window.__diceTableReady>=2')
    peer.locator("#btnSidebarToggle").click()
    peer.locator('.sidebar-tab[data-tab="tools"]').click()
    rolls = iter(values)
    monkeypatch.setattr("random.randint", lambda _low, _high: next(rolls))
    page.locator("#diceInput").fill(formula)
    page.locator("#rollMode").select_option(mode)
    page.locator("#btnRoll").click()
    expect(page.locator("#diceResult")).to_have_text(f"{formula} → {total} · {breakdown}")
    for client in (page, peer):
        expect(client.locator("#diceLog .chat-roll-breakdown").first).to_have_text(breakdown)
        expect(client.locator("#diceLog .chat-roll-breakdown").first).to_be_visible()
        client.locator('[data-tab="chat"]').click()
        expect(client.locator("#chatLog .chat-roll-breakdown").first).to_have_text(breakdown)
        expect(client.locator("#chatLog .chat-roll-breakdown").first).to_be_visible()
        expect(client.locator("#chatLog .chat-roll-summary").first).to_contain_text(f": {total}")
    page.reload()
    page.wait_for_function('() => window.__diceTableReady>=2')
    page.locator("#btnSidebarToggle").click()
    page.locator('[data-tab="chat"]').click()
    expect(page.locator("#chatLog")).to_contain_text(persisted)


def test_many_dice_wrap_in_tools_and_chat(dice_table, monkeypatch):
    page, _, _ = dice_table
    monkeypatch.setattr("random.randint", lambda _low, _high: 6)
    page.locator("#diceInput").fill("30d6")
    page.locator("#btnRoll").click()
    breakdown = "Würfel: " + " + ".join(["6"] * 30)
    expect(page.locator("#diceResult")).to_have_text(f"30d6 → 180 · {breakdown}")
    expect(page.locator("#diceLog .chat-roll-breakdown").first).to_have_text(breakdown)
    for selector in ("#diceResult", "#diceLog"):
        assert page.locator(selector).evaluate("el => el.scrollWidth <= el.clientWidth + 1")
    if os.environ.get("VTT_PROOF_DIR"):
        out = Path(os.environ["VTT_PROOF_DIR"])
        out.mkdir(parents=True, exist_ok=True)
        page.locator("#diceLog").scroll_into_view_if_needed()
        page.screenshot(path=str(out / "dice-tools.png"))
    page.locator('[data-tab="chat"]').click()
    detail = page.locator("#chatLog .chat-roll-breakdown").first
    expect(detail).to_be_visible()
    expect(detail).to_have_text(breakdown)
    assert detail.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
    if os.environ.get("VTT_PROOF_DIR"):
        page.screenshot(path=str(out / "dice-chat.png"))
