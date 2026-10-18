"""P4: the SRD character creator wizard in a real browser."""

import os
from pathlib import Path
from threading import Thread

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.serving import WSGIRequestHandler, make_server

from vtt import create_app
from vtt.config import TestingConfig
from vtt.extensions import db
from vtt.models import Character, Role, User
from vtt.models.role import init_default_roles
from vtt.models.srd_creator_draft import SrdCreatorDraft


class QuietHandler(WSGIRequestHandler):
    def log(self, *args):
        pass


@pytest.fixture
def site(tmp_path, monkeypatch):
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{tmp_path}/test.db")
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        init_default_roles(db.session)
        role = Role.query.filter_by(name="Player").first()
        user = User(username="srd-wizard", email="wizard@example.test", role_id=role.id, is_active=True)
        user.set_password("Srd-Pass-123!")
        db.session.add(user)
        db.session.commit()
        info = {"user_id": user.id, "token": create_access_token(identity=str(user.id))}
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


@pytest.fixture
def wiz(site):
    from playwright.sync_api import sync_playwright

    app, origin, info = site
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
        context.add_cookies([{"name": "access_token_cookie", "value": info["token"], "url": origin, "httpOnly": True}])
        page = context.new_page()
        page.set_default_timeout(8000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error) + " | " + str(getattr(error, "stack", ""))))
        yield page, origin, app, info
        browser.close()
        assert errors == [], errors


def _proof(page, name):
    if os.environ.get("VTT_PROOF_DIR"):
        out = Path(os.environ["VTT_PROOF_DIR"])
        out.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out / f"{name}-chromium-{page.viewport_size['width']}.png"), full_page=True)


def _saved(page):
    from playwright.sync_api import expect

    expect(page.locator("#scSave")).to_have_text("Gespeichert")


def _next(page):
    page.get_by_role("button", name="Weiter", exact=True).click()


def test_guided_flow_builds_a_valid_fighter(wiz):
    from playwright.sync_api import expect

    page, origin, app, info = wiz
    page.goto(f"{origin}/srd-creator")
    page.locator("#scNewGuided").click()
    expect(page.locator("#scBuilder")).to_be_visible()

    # klasse
    page.get_by_role("button", name="Kämpfer", exact=False).first.click()
    expect(page.locator(".sc-detail h3", has_text="Kämpfer")).to_be_visible()
    page.get_by_role("button", name="Klassentext lesen").click()
    expect(page.locator("#scDialog")).to_be_visible()
    expect(page.locator("#scDialogBody")).to_contain_text("Kämpfer")
    page.locator("#scDialogClose").click()
    _next(page)

    # herkunft
    page.get_by_role("button", name="Zwerg", exact=False).first.click()
    page.get_by_role("button", name="Soldat", exact=False).first.click()
    page.locator("#scBgPlus2").select_option("str")
    page.locator("#scBgPlus1").select_option("con")
    _next(page)

    # attribute
    page.get_by_role("button", name="Standardsatz", exact=True).click()
    page.locator("#scRecommend").click()
    expect(page.locator("#scBase-str")).to_have_value("15")
    _next(page)

    # wahlen
    skills = page.get_by_role("group", name="Klassenfertigkeiten")
    skills.get_by_label("Akrobatik").check()
    skills.get_by_label("Wahrnehmung").check()
    expect(page.get_by_text("2 von 2 gewählt").first).to_be_visible()
    page.locator("#scFc-fighter-fighting-style").select_option(index=1)
    mastery = page.get_by_role("group", name="Waffenbeherrschung")
    boxes = mastery.get_by_role("checkbox")
    for i in range(3):
        boxes.nth(i).check()
    _next(page)

    # ausruestung
    page.get_by_role("button", name="Paket A").first.click()
    page.locator("#scArmor").select_option(index=1)
    _next(page)

    # zauber: fighters cast nothing
    expect(page.get_by_text("keine Zauber")).to_be_visible()
    _next(page)

    # beschreibung
    page.locator("#scId-name").fill("Brunhild Eisenfaust")
    _next(page)

    # prüfung
    expect(page.locator("#scFinalize-btn")).to_be_enabled()
    _saved(page)
    _proof(page, "creator-review")
    page.locator("#scFinalize-btn").click()
    expect(page.get_by_text("wurde erstellt")).to_be_visible()
    expect(page.get_by_role("link", name="Zum Charakterbogen")).to_be_visible()
    with app.app_context():
        character = Character.query.filter_by(user_id=info["user_id"]).one()
        assert character.name == "Brunhild Eisenfaust"
        assert character.class_name == "Kämpfer"
        assert character.level == 1
        assert character.hp_max >= 10
        assert SrdCreatorDraft.query.one().status == "finalized"


def test_random_character_finalizes_from_home(wiz):
    from playwright.sync_api import expect

    page, origin, app, info = wiz
    page.goto(f"{origin}/srd-creator")
    page.locator("#scNewRandom").click()
    expect(page.locator("#scBuilder")).to_be_visible()
    page.get_by_role("button", name="Prüfung", exact=False).first.click()
    expect(page.locator("#scFinalize-btn")).to_be_enabled()
    page.locator("#scFinalize-btn").click()
    expect(page.get_by_text("wurde erstellt")).to_be_visible()
    with app.app_context():
        assert Character.query.filter_by(user_id=info["user_id"]).count() == 1


def test_generated_characters_are_always_rule_valid(wiz):
    from playwright.sync_api import expect

    page, origin, app, info = wiz
    page.goto(f"{origin}/srd-creator")
    page.locator("#scNewGuided").click()
    expect(page.locator("#scBuilder")).to_be_visible()
    problems = page.evaluate(
        """async () => {
            const SC = window.SrdCreator;
            const bad = [];
            for (const level of [1, 2, 3, 5, 9, 12, 17, 20]) {
                for (let i = 0; i < 12; i++) {
                    SC.randomize(level);
                    const res = await SC.api('/evaluate', 'POST', { state: SC.app.draft.state });
                    if (!res.ok) { bad.push({ level, http: res.status, data: res.data }); continue; }
                    const blockers = res.data.blockers;
                    if (blockers.length) bad.push({ level, classes: res.data.evaluation.classes, blockers: blockers.map((b) => b.message) });
                }
            }
            return bad.slice(0, 5);
        }"""
    )
    assert problems == []


def test_two_tabs_conflict_banner_and_reload(wiz):
    from playwright.sync_api import expect

    page, origin, app, info = wiz
    page.goto(f"{origin}/srd-creator")
    page.locator("#scNewGuided").click()
    page.get_by_role("button", name="Barde", exact=False).first.click()
    _saved(page)
    draft_id = page.evaluate("window.SrdCreator.app.draft.id")
    # another tab overwrites the draft
    other = page.evaluate(
        """async (id) => {
            const SC = window.SrdCreator;
            const cur = await SC.api('/drafts/' + id);
            const state = cur.data.draft.state;
            state.identity = { name: 'Aus dem zweiten Tab' };
            return (await SC.api('/drafts/' + id, 'PUT', { version: cur.data.draft.version, state })).status;
        }""",
        draft_id,
    )
    assert other == 200
    page.get_by_role("button", name="Zwerg", exact=False).count()
    page.get_by_role("button", name="Magier", exact=False).first.click()
    expect(page.locator("#scConflict")).to_be_visible()
    page.get_by_role("button", name="Neueste Version laden", exact=False).click()
    expect(page.locator("#scConflict")).to_be_hidden()
    assert page.evaluate("window.SrdCreator.app.draft.state.identity.name") == "Aus dem zweiten Tab"
    assert page.evaluate("window.SrdCreator.app.draft.state.levels[0].classKey") == "bard"


def test_draft_list_resume_duplicate_discard(wiz):
    from playwright.sync_api import expect

    page, origin, app, info = wiz
    page.goto(f"{origin}/srd-creator")
    page.locator("#scNewGuided").click()
    page.get_by_role("button", name="Schurke", exact=False).first.click()
    page.locator("#scBackHome").click()
    expect(page.locator(".sc-draft")).to_have_count(1)
    page.get_by_role("button", name="Duplizieren").click()
    expect(page.locator(".sc-draft")).to_have_count(2)
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Verwerfen").first.click()
    expect(page.locator(".sc-draft")).to_have_count(1)
    page.get_by_role("button", name="Fortsetzen").click()
    expect(page.locator("#scBuilder")).to_be_visible()
    assert page.evaluate("window.SrdCreator.app.draft.state.levels[0].classKey") == "rogue"
    page.reload()
    expect(page.locator("#scBuilder")).to_be_visible()


def test_quick_mode_and_mobile_layout(wiz):
    from playwright.sync_api import expect

    page, origin, app, info = wiz
    page.goto(f"{origin}/srd-creator")
    page.locator("#scNewQuick").click()
    expect(page.locator("#scBuilder")).to_be_visible()
    for heading in ["Klasse", "Herkunft", "Attribute", "Wahlen", "Ausrüstung", "Zauber", "Beschreibung", "Prüfung"]:
        expect(page.locator(".sc-section h2", has_text=heading).first).to_be_visible() if heading == "Klasse" else expect(page.locator(".sc-section h2", has_text=heading).first).to_be_attached()
    page.set_viewport_size({"width": 390, "height": 844})
    page.get_by_role("button", name="Paladin", exact=False).first.click()
    _saved(page)
    assert page.evaluate("document.documentElement.scrollWidth") <= 391
    _proof(page, "creator-quick")
    page.get_by_role("button", name="Geführt", exact=True).click()
    expect(page.locator(".sc-section")).to_have_count(1)
    assert page.evaluate("document.documentElement.scrollWidth") <= 391


def test_ability_methods_and_multiclass_levels(wiz):
    from playwright.sync_api import expect

    page, origin, app, info = wiz
    page.goto(f"{origin}/srd-creator")
    page.locator("#scNewGuided").click()
    page.get_by_role("button", name="Kleriker", exact=False).first.click()
    page.locator("#scLevel").fill("3")
    page.locator("#scLevel").dispatch_event("change")
    page.locator("#scLvlClass2").select_option("fighter")
    _saved(page)
    state = page.evaluate("window.SrdCreator.app.draft.state.levels.map((l) => l.classKey)")
    assert state == ["cleric", "cleric", "fighter"]
    page.get_by_role("button", name="Attribute", exact=False).first.click()
    page.get_by_role("button", name="Punktekauf", exact=True).click()
    _saved(page)
    assert page.evaluate("window.SrdCreator.app.draft.state.abilityMethod") == "point-buy"
    page.get_by_role("button", name="Manuell", exact=True).click()
    _saved(page)
    assert page.evaluate("window.SrdCreator.app.draft.state.abilityMethod") == "manual"
    page.get_by_role("button", name="Würfeln", exact=False).click()
    page.locator("#scRollAll").click()
    _saved(page)
    assert page.evaluate("window.SrdCreator.app.draft.state.abilityMethod") == "roll"
    assert len(page.evaluate("window.SrdCreator.app.draft.state.abilityRolls")) == 6
    assert page.evaluate("document.documentElement.scrollWidth") <= 1441
