"""Creation Engine in a real browser against the real server: Matt's Eagle Homebrew creates, edits and deletes.

Needs the built bundle (frontend/eagle-homebrew-host: `npm run build`, or the Docker image) and Chromium.
"""

import os
import re
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from werkzeug.serving import make_server

from vtt import create_app
from vtt.config import TestingConfig
from vtt.extensions import db
from vtt.models import Campaign, CampaignMember, User
from vtt.models.role import init_default_roles

BUNDLE = Path(__file__).resolve().parents[1] / "vtt/static/eagle-homebrew/creation-engine.js"
PASSWORD = "EaglePass123!"
SHOTS = os.environ.get("CE_E2E_SCREENSHOTS")

pytestmark = pytest.mark.skipif(not BUNDLE.exists(), reason="Creation Engine bundle not built (frontend/eagle-homebrew-host: npm run build)")


@pytest.fixture
def server(monkeypatch):
    # With CE_TEST_DATABASE_URL (tools/ce_test_postgres.py) the server runs threaded against PostgreSQL, as in
    # production, so the editor's parallel requests really run in parallel. The default in-memory SQLite shares
    # one connection between threads, so without PostgreSQL requests are served one after another.
    url = os.getenv("CE_TEST_DATABASE_URL")
    schema = admin = None
    if url:
        parsed = urlparse(url)
        assert (parsed.hostname, parsed.port, parsed.path) == ("127.0.0.1", 55432, "/ce_test")
        schema = "ce_eagle_" + uuid4().hex
        admin = create_engine(url)
        with admin.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA {schema}"))
        monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", url)
        monkeypatch.setattr(TestingConfig, "SQLALCHEMY_ENGINE_OPTIONS",
                            {"connect_args": {"options": f"-csearch_path={schema}"}}, raising=False)
    app = create_app("testing")
    app.config.update(CE_AUTHORING=True, CE_PLAYABLE_SPECIES=True)
    with app.app_context():
        db.create_all()
        init_default_roles(db.session)
        users = {}
        for name in ("eagle_gm", "eagle_player"):
            users[name] = User(username=name, email=f"{name}@example.test", role_id=1,
                               is_active=True, is_suspended=False, account_state="active")
            users[name].set_password(PASSWORD)
            db.session.add(users[name])
        db.session.flush()
        campaign = Campaign(name="Adlerhorst", owner_id=users["eagle_gm"].id)
        db.session.add(campaign)
        db.session.flush()
        db.session.add(CampaignMember(campaign_id=campaign.id, user_id=users["eagle_player"].id,
                                      campaign_role="PLAYER", status="active"))
        db.session.commit()
        world = f"campaign:{campaign.id}"
    http = make_server("127.0.0.1", 0, app, threaded=bool(url))
    thread = Thread(target=http.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{http.server_port}", world
    finally:
        http.shutdown()
        thread.join(timeout=5)
        http.server_close()
        with app.app_context():
            db.session.remove()
            if schema:
                db.engine.dispose()
            else:
                db.drop_all()
        if schema:
            with admin.begin() as connection:
                connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))


@pytest.fixture
def browser():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        instance = p.chromium.launch(headless=True, args=["--no-sandbox"])
        yield instance
        instance.close()


def open_engine(browser, origin, username):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    response = page.request.post(origin + "/api/auth/login", data={"username": username, "password": PASSWORD})
    assert response.ok, response.text()
    page.goto(origin + "/api/ce/authoring")
    page.locator("#ce-world option").first.wait_for(state="attached")
    return page, errors


def shot(page, name):
    if SHOTS:
        page.screenshot(path=os.path.join(SHOTS, f"{name}.png"), full_page=True)


def api(page, origin, path, **params):
    response = page.request.get(origin + path, params=params)
    assert response.ok, response.text()
    return response.json()


def test_create_edit_retrofit_and_delete_through_the_creation_engine(server, browser):
    from playwright.sync_api import expect
    origin, world = server
    page, errors = open_engine(browser, origin, "eagle_gm")
    expect(page.locator("#ce-world option")).to_have_text(["Persönliche Werkstatt", "Adlerhorst"])
    page.select_option("#ce-world", world)
    expect(page.locator("#ce-world-documents")).to_contain_text("noch keine Homebrew-Inhalte")
    shot(page, "01-page")

    # Create: the Flight Control hub's "open" is the page's "Neu erstellen".
    page.click("#ce-create")
    window = page.locator("#eagle-homebrew-window")
    expect(window).to_be_visible()
    window.locator("[data-action=selectArt][data-art=Item]").click()
    window.locator("[data-action=selectKind][data-key=weapons]").click()
    window.locator("input[name=name]").fill("Flammenklinge")
    window.locator("select[name='type.value']").select_option("martialM")
    window.locator("[data-action=addAction]").click()
    window.locator("[data-action=pickActivityType][data-type=attack]").click()
    window.locator("[data-action=confirmActivity]").click()
    shot(page, "02-weapon")
    window.locator("[data-action=create]").click()
    expect(page.locator("#ce-world-documents")).to_contain_text("Flammenklinge")
    expect(page.locator("#ce-library-documents")).to_contain_text("Flammenklinge")
    listing = api(page, origin, "/api/ce/authoring/documents", world=world)
    world_uuid = listing["world"][0]["uuid"]
    library_uuid = listing["library"][0]["uuid"]
    assert re.fullmatch(r"Item\.[A-Za-z0-9]{16}", world_uuid)
    assert library_uuid == "Compendium.world.eagle-weapons-2024." + world_uuid
    source = api(page, origin, "/api/ce/authoring/document", world=world, uuid=world_uuid)["document"]["source"]
    assert source["type"] == "weapon" and source["system"]["type"]["value"] == "martialM"
    assert source["system"]["source"]["rules"] == "2024"
    assert [activity["type"] for activity in source["system"]["activities"].values()] == ["attack"]
    assert source["flags"]["eagle-homebrew"]["pair"] == {"pack": "world.eagle-weapons-2024"}

    # Edit: the sidebar's "Edit with Eagle Homebrew" is the directory button; saves go Library first, then world.
    page.locator(f"#ce-world-documents [data-uuid='{world_uuid}'] button", has_text="Edit with Eagle Homebrew").click()
    expect(window.locator("input[name=name]")).to_have_value("Flammenklinge")
    window.locator("input[name=name]").fill("Frostklinge")
    window.locator("[data-action=create]").click()
    expect(page.locator("#ce-world-documents")).to_contain_text("Frostklinge")
    for uuid in (world_uuid, library_uuid):
        saved = api(page, origin, "/api/ce/authoring/document", world=world, uuid=uuid)["document"]["source"]
        assert saved["name"] == "Frostklinge"
        assert [activity["type"] for activity in saved["system"]["activities"].values()] == ["attack"]
    shot(page, "03-edited")

    # Retrofit: a world document without Library counterpart gets one under its own id (compendium.import).
    created = page.request.post(origin + "/api/ce/authoring/request", data={
        "world": world, "type": "document.create",
        "payload": {"target": {"world": "Item"}, "id": "OldSpell00000001",
                    "data": {"name": "Altzauber", "type": "spell", "system": {"level": 1}, "flags": {"legacy": {"keep": 1}}}}})
    assert created.json()["ok"] is True
    page.reload()
    page.locator("#ce-world-documents [data-uuid='Item.OldSpell00000001'] button", has_text="Edit with Eagle Homebrew").click()
    page.wait_for_selector("#eagle-homebrew-window input[name=name], .eh-notification.error")
    assert page.locator(".eh-notification.error").count() == 0, page.locator(".eh-notification.error").all_inner_texts()
    expect(window.locator("input[name=name]")).to_have_value("Altzauber")
    library = api(page, origin, "/api/ce/authoring/document", world=world,
                  uuid="Compendium.world.eagle-spells-2024.Item.OldSpell00000001")["document"]
    assert library is not None and library["source"]["flags"]["legacy"] == {"keep": 1}
    assert library["source"]["flags"]["eagle-homebrew"]["pair"] == {"world": "Item"}
    world_spell = api(page, origin, "/api/ce/authoring/document", world=world, uuid="Item.OldSpell00000001")["document"]
    assert world_spell["source"]["flags"]["eagle-homebrew"]["pair"] == {"pack": "world.eagle-spells-2024"}
    window.locator("[data-action=close]").click()

    # Delete asks first and removes only the world side.
    row = page.locator(f"#ce-world-documents [data-uuid='{world_uuid}']")
    row.get_by_role("button", name="Löschen", exact=True).click()
    row.locator("button.ce-danger").click()
    expect(page.locator(f"#ce-world-documents [data-uuid='{world_uuid}']")).to_have_count(0)
    expect(page.locator("#ce-library-documents")).to_contain_text("Frostklinge")
    assert errors == []


def test_players_only_reach_their_personal_workshop(server, browser):
    from playwright.sync_api import expect
    origin, world = server
    page, errors = open_engine(browser, origin, "eagle_player")
    expect(page.locator("#ce-world option")).to_have_text(["Persönliche Werkstatt"])
    denied = page.request.get(origin + "/api/ce/authoring/documents", params={"world": world})
    assert denied.status == 403
    assert errors == []


def test_editor_fits_a_phone_screen(server, browser):
    from playwright.sync_api import expect
    origin, _ = server
    page, errors = open_engine(browser, origin, "eagle_gm")
    page.set_viewport_size({"width": 390, "height": 844})
    page.click("#ce-create")
    window = page.locator("#eagle-homebrew-window")
    expect(window).to_be_visible()
    box = window.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 390
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
    shot(page, "04-phone")
    assert errors == []


def test_duckfolk_publish_creator_sheet_and_live_action(server, browser):
    """Chromium follows the author → player → live table path against a disposable server."""
    from playwright.sync_api import expect

    from tests.test_playable_species import duck_state

    origin, world = server
    campaign_id = int(world.split(":", 1)[1])
    gm, gm_errors = open_engine(browser, origin, "eagle_gm")
    gm.select_option("#ce-world", world)
    expect(gm.locator("#ce-species")).to_be_visible()
    gm.locator("#ce-species-example").click()
    expect(gm.locator("#ce-species-report")).to_contain_text("Duckfolk ist als normaler Eagle-Entwurf angelegt")
    expect(gm.locator("#ce-species-source")).to_have_value(re.compile(r"Item\.D[0-9a-f]{15}"))
    expect(gm.locator("#ce-species-action-name")).to_have_value("Telekinetisches Quaken")
    gm.locator("#ce-species-check").click()
    expect(gm.locator("#ce-species-report")).to_contain_text("Spielbar")
    expect(gm.locator("#ce-species-publish")).to_be_enabled()
    gm.select_option("#ce-species-scope", world)
    gm.locator("#ce-species-publish").click()
    expect(gm.locator("#ce-species-report")).to_contain_text("Veröffentlicht als Fassung 1")
    shot(gm, "05-duckfolk-published")

    player, player_errors = open_engine(browser, origin, "eagle_player")
    catalog = api(player, origin, "/api/srd-creator/species-catalog")["species"]
    duck = next(row for row in catalog if row["name"] == "Duckfolk")
    data = api(player, origin, "/api/srd-creator/creator-data")
    state = duck_state(data, duck["id"], skill="wahrnehmung", name="Quaki Browser")
    state["species"]["choices"] = {}
    draft_response = player.request.post(origin + "/api/srd-creator/drafts", data={"state": state})
    assert draft_response.status == 201, draft_response.text()
    draft = draft_response.json()["draft"]
    player.goto(f"{origin}/srd-creator?draft={draft['id']}&schritt=herkunft")
    expect(player.locator("#scStepBody")).to_contain_text("Duckfolk")
    expect(player.locator("#scStepBody")).to_contain_text("Telekinetisches Quaken")
    player.select_option("#scSpc-duck-skill", "wahrnehmung")
    expect(player.locator("#scSave")).to_contain_text("Gespeichert")
    shot(player, "06-duckfolk-creator")
    draft = api(player, origin, f"/api/srd-creator/drafts/{draft['id']}")["draft"]
    finished = player.request.post(origin + f"/api/srd-creator/drafts/{draft['id']}/finalize",
                                   data={"version": draft["version"], "campaign_id": campaign_id})
    assert finished.status == 201, finished.text()
    char_id = finished.json()["character"]["id"]

    campaign_map = gm.request.post(origin + f"/api/campaigns/{campaign_id}/maps",
                                   data={"name": "Ententeich", "width": 20, "height": 20})
    assert campaign_map.status == 201, campaign_map.text()
    game_session = gm.request.post(origin + f"/api/campaigns/{campaign_id}/sessions",
                                   data={"name": "Entenabend", "map_id": campaign_map.json()["id"]})
    assert game_session.status == 201, game_session.text()
    started = gm.request.post(origin + f"/api/campaigns/{campaign_id}/sessions/{game_session.json()['id']}/start")
    assert started.status == 200, started.text()

    player.goto(f"{origin}/character-sheet?id={char_id}")
    expect(player.locator("#srdSpeciesOrigin")).to_contain_text("Duckfolk")
    expect(player.locator("#srdSpeciesOrigin")).to_contain_text("Schwimmen 30 ft")
    expect(player.locator("#srdSpeciesOrigin")).to_contain_text("Keine Dunkelsicht")
    action = player.locator(".srd-origin-action[data-action-id=telekinetic-quack]")
    expect(action).to_be_visible()
    action.locator("input[name=object]").fill("der Schlüssel auf dem Tisch")
    action.locator("input[name=weightLb]").fill("1")
    action.locator("input[name=distanceFeet]").fill("20")
    action.locator("input[name=moveFeet]").fill("15")
    action.locator("input[name=unattended]").check()
    action.get_by_role("button", name="Am Tisch erklären").click()
    expect(player.locator("#srdSpeciesOrigin")).to_contain_text("Telekinetisches Quaken")
    expect(player.locator("#messageBox")).to_contain_text("Telekinetisches Quaken erklärt")
    shot(player, "07-duckfolk-sheet")
    if SHOTS:
        player.locator("#srdSpeciesOrigin").screenshot(path=os.path.join(SHOTS, "08-duckfolk-origin.png"))
    gm.goto(f"{origin}/party?campaign={campaign_id}")
    dm_origin = gm.locator(f".sp-card[data-character-id='{char_id}'] .sp-origin")
    expect(dm_origin).to_contain_text("Duckfolk")
    expect(dm_origin).to_contain_text("Schwimmen 30 ft")
    expect(dm_origin).to_contain_text("Telekinetisches Quaken")
    dm_origin.locator("summary").click()
    expect(dm_origin).to_contain_text("Kein Angriff")
    shot(gm, "09-duckfolk-dm-party")
    assert gm_errors == [] and player_errors == []
