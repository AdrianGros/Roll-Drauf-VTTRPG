"""P5: the character sheet and archive speak the SRD system; the old light creator is gone."""

import os
from pathlib import Path
from threading import Thread

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.serving import WSGIRequestHandler, make_server

from tests.test_srd_creator_api import BASE, app, client, data, finalized  # noqa: F401
from vtt import create_app
from vtt.config import TestingConfig
from vtt.extensions import db
from vtt.models import Role, User
from vtt.models.role import init_default_roles

ROOT = Path(__file__).resolve().parents[1]
REMOVED_MARKERS = ("charModal", "rollDraufSpeciesCatalog", "submitCharacter", "Roll Drauf Light", "charFaction")
SHEET_REMOVED = ("rdlProfileSection", "rdlProgressionSection", "rdlFeaturesSection", "submitLevelUp", "charFaction")


def test_characters_page_has_no_light_creator_and_points_to_srd(client):
    html = client.get("/characters").get_data(as_text=True)
    for marker in REMOVED_MARKERS:
        assert marker not in html, marker
    assert "/srd-creator" in html


def test_sheet_page_has_no_light_panes_but_an_srd_pane(client):
    html = client.get("/character-sheet").get_data(as_text=True)
    for marker in SHEET_REMOVED:
        assert marker not in html, marker
    assert 'id="srdSheetSection"' in html and "/api/srd-creator/characters/" in html


def test_create_entry_points_lead_to_the_srd_creator():
    book_scene = (ROOT / "vtt/static/js/book-scene.js").read_text(encoding="utf-8")
    assert "{ label: 'Held anlegen', href: '/srd-creator', primary: true }" in book_scene
    assert "/characters?intent=create" not in (ROOT / "vtt/endpoints/dashboard_home.py").read_text(encoding="utf-8")
    assert "window.location.replace('/srd-creator')" in (ROOT / "vtt/templates/characters.html").read_text(encoding="utf-8")


def test_light_backend_is_removed():
    assert not list((ROOT / "vtt/roll_drauf").glob("*.py"))
    for relative in ("vtt/characters/routes.py", "vtt/models/character.py"):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "roll_drauf_light" not in source and "vtt.roll_drauf" not in source, relative


def test_sheet_payload_for_srd_and_plain_characters(client, data):
    srd = finalized(client, data)
    payload = client.get(f"/api/characters/{srd['id']}/sheet").get_json()["character"]
    assert payload["system_id"] == "srd_5_2_1_de" and payload["level"] == 5
    assert payload["hp_max"] == payload["hp_current"] and payload["ac"] == 11
    plain = client.post("/api/characters", json={"name": "Alt", "race": "Mensch", "class": "Kämpfer", "level": 3}).get_json()
    legacy = client.get(f"/api/characters/{plain['id']}/sheet").get_json()["character"]
    assert legacy["system_id"] is None and legacy["race"] == "Mensch" and legacy["level"] == 3
    assert "progression" not in legacy and "faction" not in legacy
    assert client.put(f"/api/characters/{srd['id']}", json={"name": "Neu", "hp_current": 3}).status_code == 200
    assert client.put(f"/api/characters/{srd['id']}", json={"xp": 10}).status_code == 409
    assert client.put(f"/api/characters/{srd['id']}", json={"level": 9}).status_code == 409


def test_export_and_import_of_light_format_are_gone(client, data):
    srd = finalized(client, data)
    plain = client.post("/api/characters", json={"name": "Alt"}).get_json()
    assert client.post("/api/characters/import", json={"format": "roll_drauf_light", "character": {}}).status_code == 400
    assert client.get(f"/api/characters/{plain['id']}/export").status_code in (200, 400, 422)
    assert client.get(f"/api/characters/{srd['id']}/export").status_code in (200, 400, 422)
    assert client.post(f"/api/characters/{plain['id']}/level-up", json={}).status_code in (404, 405)


class QuietHandler(WSGIRequestHandler):
    def log(self, *args):
        pass


@pytest.fixture
def site(tmp_path, monkeypatch):
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{tmp_path}/sheet.db")
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        init_default_roles(db.session)
        role = Role.query.filter_by(name="Player").first()
        user = User(username="sheet-reader", email="sheet@example.test", role_id=role.id, is_active=True)
        user.set_password("Srd-Pass-123!")
        db.session.add(user)
        db.session.commit()
        info = {"token": create_access_token(identity=str(user.id)), "user_id": user.id}
    server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield app, f"http://127.0.0.1:{server.server_port}", info
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        with app.app_context():
            db.session.remove()
            db.engine.dispose()


@pytest.mark.parametrize("width", [1440, 390])
def test_srd_character_sheet_renders_rule_values_in_a_browser(site, data, width):
    from playwright.sync_api import expect, sync_playwright
    from tests.test_srd_creator_api import wizard_state
    from vtt.rules_content.creator_drafts import character_values
    from vtt.rules_content.creator_rules import evaluate
    from vtt.models import Character

    app, origin, info = site
    state = wizard_state(data, "Mira <b>Eulenfeder</b>")
    evaluation = evaluate(data, state)
    with app.app_context():
        values = character_values(data, state, evaluation, draft_id=1, finalized_at="2026-10-18T10:00:00Z")
        character = Character(user_id=info["user_id"], **values)
        db.session.add(character)
        db.session.commit()
        char_id = character.id
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
        context.add_cookies([{"name": "access_token_cookie", "value": info["token"], "url": origin, "httpOnly": True}])
        page = context.new_page()
        page.set_default_timeout(15000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(f"{origin}/character-sheet?id={char_id}")
        body = page.locator("#srdSheetBody")
        expect(page.locator("#srdSheetSection")).to_be_visible()
        expect(body).to_contain_text("Magier 5")
        expect(body).to_contain_text("Rüstungsklasse")
        expect(body).to_contain_text("Intelligenz")
        expect(body).to_contain_text("19 (+4)")
        expect(body).to_contain_text("Arkane Kunde")
        expect(body).to_contain_text("(Expertise)")
        expect(body).to_contain_text("Zauberwirken")
        expect(body).to_contain_text("SG 15")
        expect(body).to_contain_text("Grad 3: 2")
        expect(body).to_contain_text("Zum Regelwerk-Ersteller")
        assert page.locator("#srdSheetBody b").count() == 0
        for field in ("charRace", "charClass", "charLevel", "charAc", "charHpMax", "charStr"):
            assert page.locator(f"#{field}").is_disabled(), field
        assert page.locator("#charFaction").count() == 0
        for section in ("#rdlProfileSection", "#rdlProgressionSection", "#rdlFeaturesSection"):
            assert page.locator(section).count() == 0
        assert page.evaluate("document.documentElement.scrollWidth") <= width + 1
        if os.environ.get("VTT_PROOF_DIR"):
            out = Path(os.environ["VTT_PROOF_DIR"])
            out.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out / f"srd-sheet-chromium-{width}.png"), full_page=True)
        browser.close()
        assert errors == [], errors


@pytest.mark.parametrize("width", [1440, 390])
def test_srd_sheet_rolls_from_values_and_shows_the_result(site, data, width):
    from playwright.sync_api import expect, sync_playwright
    from tests.test_srd_creator_api import wizard_state
    from vtt.rules_content.creator_drafts import character_values
    from vtt.rules_content.creator_rules import evaluate
    from vtt.models import Character

    app, origin, info = site
    state = wizard_state(data, "Mira Eulenfeder")
    with app.app_context():
        values = character_values(data, state, evaluate(data, state), draft_id=1, finalized_at="2026-10-18T10:00:00Z")
        character = Character(user_id=info["user_id"], **values)
        db.session.add(character)
        db.session.commit()
        char_id = character.id
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
        context.add_cookies([{"name": "access_token_cookie", "value": info["token"], "url": origin, "httpOnly": True}])
        page = context.new_page()
        page.set_default_timeout(15000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(f"{origin}/character-sheet?id={char_id}")
        result = page.locator("#srdRollResult")
        expect(result).to_contain_text("Klicke auf einen Wert")
        assert page.locator(".srd-roll-btn").count() >= 6 * 2 + 18 + 3
        page.locator('[data-roll-kind="skill"][data-roll-key="arkane-kunde"]').click()
        expect(result).to_contain_text("Arkane Kunde:")
        expect(result).to_contain_text("+ 10 =")
        expect(result).to_contain_text("nur hier")
        page.select_option("#srdRollMode", "advantage")
        page.locator('[data-roll-kind="save"][data-roll-key="int"]').click()
        expect(result).to_contain_text("Intelligenz-Rettungswurf (Vorteil):")
        expect(result).to_contain_text("+ 7 =")
        expect(page.locator("#srdRollHistory li")).to_have_count(1)
        page.locator('[data-roll-kind="spell_attack"]').first.click()
        expect(result).to_contain_text("Zauberangriff (Magier)")
        assert page.evaluate("document.documentElement.scrollWidth") <= width + 1
        if os.environ.get("VTT_PROOF_DIR"):
            out = Path(os.environ["VTT_PROOF_DIR"])
            out.mkdir(parents=True, exist_ok=True)
            page.locator("#srdRollBar").scroll_into_view_if_needed()
            page.screenshot(path=str(out / f"srd-sheet-rolls-{width}.png"), full_page=True)
        browser.close()
        assert errors == [], errors
