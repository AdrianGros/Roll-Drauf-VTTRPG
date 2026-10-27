"""Sheet to table: a roll clicked on the character sheet in its own tab shows up live at the open table."""
from datetime import datetime
from threading import Thread

import pytest
from flask_jwt_extended import create_access_token
from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import WSGIRequestHandler, make_server

from tests.test_srd_creator_api import data, wizard_state  # noqa: F401
from vtt import create_app
from vtt.config import TestingConfig
from vtt.extensions import db, socketio
from vtt.models import Campaign, CampaignMap, CampaignMember, Character, ChatMessage, GameSession, Role, User
from vtt.models.role import init_default_roles
from vtt.rules_content.creator_drafts import character_values
from vtt.rules_content.creator_rules import evaluate

DAGGER = "equipment.coins-and-weapons.weapons-simple-melee.dolch"


class QuietHandler(WSGIRequestHandler):
    def log(self, *args):
        pass


@pytest.fixture
def live_table(tmp_path, monkeypatch, data):
    """A DM's campaign with two running sessions; the player owns Mira and plays at "Abend"."""
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{tmp_path}/sheet-table.db")
    # This fixture serves Flask through threaded Werkzeug, not eventlet.
    monkeypatch.setitem(socketio.server_options, "async_mode", "threading")
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        init_default_roles(db.session)
        role = Role.query.filter_by(name="Player").first()
        dm = User(username="Tisch DM", email="dm@example.test", role_id=role.id, is_active=True)
        player = User(username="Mira Spielerin", email="mira@example.test", role_id=role.id, is_active=True)
        for user in (dm, player):
            user.set_password("Srd-Pass-123!")
            db.session.add(user)
        db.session.flush()
        campaign = Campaign(name="Rolltisch", description="", owner_id=dm.id, status="active", max_players=6)
        db.session.add(campaign)
        db.session.flush()
        now = datetime.utcnow()
        db.session.add(CampaignMember(
            campaign_id=campaign.id, user_id=player.id, campaign_role="Player", status="active",
            joined_at=now, invited_at=now, accepted_at=now, invited_by=dm.id))
        campaign_map = CampaignMap(campaign_id=campaign.id, name="Karte", width=1000, height=1000,
                                   grid_size=50, created_by=dm.id)
        db.session.add(campaign_map)
        db.session.flush()
        table = GameSession(campaign_id=campaign.id, map_id=campaign_map.id, name="Abend", status="in_progress")
        elsewhere = GameSession(campaign_id=campaign.id, map_id=campaign_map.id, name="Zweiter Tisch", status="in_progress")
        db.session.add_all([table, elsewhere])
        state = wizard_state(data, "Mira Eulenfeder")
        values = character_values(data, state, evaluate(data, state), draft_id=1, finalized_at="2026-10-27T10:00:00Z")
        character = Character(user_id=player.id, campaign_id=campaign.id, **values)
        db.session.add(character)
        db.session.commit()
        ids = {"campaign": campaign.id, "session": table.id, "elsewhere": elsewhere.id, "char": character.id,
               "token": create_access_token(identity=str(player.id))}
    server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    monkeypatch.setattr(socketio.server.eio, "cors_allowed_origins", [origin])
    try:
        yield app, origin, ids
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        with app.app_context():
            db.session.remove()
            db.engine.dispose()


def _open_table_chat(page):
    page.locator("#btnSidebarToggle").click()
    page.locator('[data-tab="chat"]').click()
    return page.locator("#chatLog")


def test_a_sheet_roll_in_a_second_tab_appears_live_at_the_table_and_stays(live_table):
    app, origin, ids = live_table
    char, session = ids["char"], ids["session"]
    bound = f"/character-sheet?id={char}&session_id={session}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
        context.add_cookies([{"name": "access_token_cookie", "value": ids["token"], "url": origin, "httpOnly": True}])
        token = context.request.post(f"{origin}/api/campaigns/{ids['campaign']}/sessions/{session}/tokens",
                                     data={"name": "Mira", "x": 1, "y": 1, "character_id": char})
        assert token.status == 201, token.text()
        token_id = token.json()["token"]["id"]
        added = context.request.post(f"{origin}/api/srd-creator/characters/{char}/inventory",
                                     data={"itemId": DAGGER, "quantity": 1})
        assert added.ok, added.text()
        dagger = next(item["id"] for item in added.json()["items"] if item["itemId"] == DAGGER)

        errors = []
        table = context.new_page()
        table.set_default_timeout(15000)
        table.on("pageerror", lambda error: errors.append(f"table: {error}"))
        table.goto(f"{origin}/play?campaign_id={ids['campaign']}&session_id={session}")
        expect(table.locator("#btnRoll")).to_be_enabled()

        # The table hands its own session to the sheet, in the drawer and in a tab of its own.
        toggle = table.locator('[data-widget="tokenWidget"]')
        if toggle.get_attribute("aria-expanded") != "true":
            toggle.click()
        table.locator(f'#tokenList [data-token-id="{token_id}"]').click()
        expect(table.locator("#btnOpenSheetTab")).to_have_attribute("href", bound)
        table.locator("#btnOpenSheet").click()
        expect(table.locator("#sheetFrame")).to_have_attribute("src", bound)
        expect(table.locator("#sheetDrawerTabLink")).to_have_attribute("href", bound)
        drawer_destination = table.frame_locator("#sheetFrame").locator("#srdRollDestination")
        expect(drawer_destination).to_have_attribute("data-state", "live")
        expect(drawer_destination).to_contain_text("Abend")
        table.locator("#btnCloseSheet").click()
        expect(table.locator("#sheetDrawer")).to_be_hidden()
        table.evaluate("window.__sameTableDocument = true")

        with context.expect_page() as opened:
            table.locator("#btnOpenSheetTab").click()
        sheet = opened.value
        sheet.set_default_timeout(15000)
        sheet.on("pageerror", lambda error: errors.append(f"sheet: {error}"))
        destination = sheet.locator("#srdRollDestination")
        expect(destination).to_have_attribute("data-state", "live")
        expect(destination).to_contain_text("Abend")

        # Switching to edit mode keeps the table binding.
        sheet.locator("#sheetModeActionBtn").click()
        expect(sheet).to_have_url(f"{origin}/character-sheet?id={char}&mode=edit&session_id={session}")
        expect(destination).to_have_attribute("data-state", "live")

        sheet.locator('[data-roll-kind="skill"][data-roll-key="arkane-kunde"]').click()
        expect(sheet.locator("#srdRollResult")).to_contain_text("Arkane Kunde:")
        expect(sheet.locator("#srdRollResult")).to_contain_text("live am Tisch „Abend“")
        expect(table.locator("#diceLog")).to_contain_text("Mira Eulenfeder · Arkane Kunde · 1d20+10:")

        sheet.locator(f'[data-roll-kind="weapon_attack"][data-roll-key="{dagger}"]').click()
        expect(sheet.locator("#srdRollResult")).to_contain_text("Angriff: Dolch:")
        chat = _open_table_chat(table)
        expect(chat.locator(".chat-roll-summary").first).to_contain_text("Mira Eulenfeder · Angriff: Dolch · 1d20+4:")
        expect(chat).to_contain_text("Mira Eulenfeder · Arkane Kunde · 1d20+10:")
        assert table.evaluate("window.__sameTableDocument === true"), "the table reloaded instead of receiving the roll live"

        table.reload()
        expect(table.locator("#btnRoll")).to_be_enabled()
        chat = _open_table_chat(table)
        expect(chat).to_contain_text("Mira Eulenfeder · Arkane Kunde: würfelt 1d20+10:")
        expect(chat).to_contain_text("Mira Eulenfeder · Angriff: Dolch: würfelt 1d20+4:")

        # A standalone sheet with two running tables says so and rolls nowhere until the player picks one.
        loose = context.new_page()
        loose.set_default_timeout(15000)
        loose.on("pageerror", lambda error: errors.append(f"standalone sheet: {error}"))
        loose.goto(f"{origin}/character-sheet?id={char}")
        loose_destination = loose.locator("#srdRollDestination")
        expect(loose_destination).to_have_attribute("data-state", "choose")
        loose.locator('[data-roll-kind="initiative"]').click()
        expect(loose.locator("#srdRollResult")).to_contain_text("Wähle zuerst")
        loose.locator("#srdRollSession").select_option(str(ids["elsewhere"]))
        expect(loose_destination).to_have_attribute("data-state", "live")
        expect(loose_destination).to_contain_text("Zweiter Tisch")
        expect(loose).to_have_url(f"{origin}/character-sheet?id={char}&session_id={ids['elsewhere']}")
        loose.locator('[data-roll-kind="initiative"]').click()
        expect(loose.locator("#srdRollResult")).to_contain_text("live am Tisch „Zweiter Tisch“")
        browser.close()
        assert errors == [], errors

    with app.app_context():
        rolls = ChatMessage.query.filter_by(content_type="dice_roll").all()
        assert sorted((row.game_session_id, row.content.split(":")[0]) for row in rolls) == sorted([
            (session, "Mira Eulenfeder · Arkane Kunde"),
            (session, "Mira Eulenfeder · Angriff"),
            (ids["elsewhere"], "Mira Eulenfeder · Initiative"),
        ])
