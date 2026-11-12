"""C02 in a real browser: owner editing and lock, reader safety, image upload/replace/remove,
independent copies, fixed section links and the creator's correction path.

Image/lock/section labels come from tools/i18n/tasks/c02.json, so the English checks need the
coordinator's regenerated bundle; the German ones do not."""

import re
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import pytest
from flask_jwt_extended import create_access_token

from tests.test_srd_creator_api import data  # noqa: F401
from tests.test_srd_inventory_browser import _character
from tests.test_srd_sheet import QuietHandler, site  # noqa: F401
from vtt.extensions import db
from vtt.models import Campaign, CampaignMember, Character, Role, User

PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8ffff3f0005fe02fe5fcc519a0000000049454e44ae426082")


def _context(p, origin, token, width, language=None):
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
    context.add_cookies([{"name": "access_token_cookie", "value": token, "url": origin, "httpOnly": True}])
    page = context.new_page()
    page.set_default_timeout(15000)
    errors, writes = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda r: writes.append((r.method, r.url)) if r.method not in ("GET", "HEAD", "OPTIONS") and "/api/" in r.url else None)
    if language:
        from playwright.sync_api import expect

        page.goto(f"{origin}/characters")
        page.locator("#vttDisplayOpen").click()
        page.locator("#vttDisplay-language").select_option(language)
        page.locator(".vtt-display-actions button").last.click()
        expect(page.locator("html")).to_have_attribute("lang", language)
    return browser, page, errors, writes


def _query(page):
    return {k: v[0] for k, v in parse_qs(urlparse(page.url).query).items()}


def _reader(app, info, char_id):
    """A second user who only sees the character through a shared campaign."""
    with app.app_context():
        role = Role.query.filter_by(name="Player").first()
        reader = User(username="table-reader", email="reader@example.test", role_id=role.id, is_active=True)
        reader.set_password("Srd-Pass-123!")
        db.session.add(reader)
        db.session.flush()
        campaign = Campaign(name="Rolltisch", description="", owner_id=info["user_id"], status="active", max_players=6)
        db.session.add(campaign)
        db.session.flush()
        for user_id, role_name in ((info["user_id"], "DM"), (reader.id, "Player")):
            db.session.add(CampaignMember(
                campaign_id=campaign.id, user_id=user_id, campaign_role=role_name, status="active",
                joined_at=datetime.utcnow(), invited_at=datetime.utcnow(), accepted_at=datetime.utcnow(), invited_by=info["user_id"]))
        db.session.get(Character, char_id).campaign_id = campaign.id
        db.session.commit()
        return create_access_token(identity=str(reader.id)), campaign.id


@pytest.mark.parametrize("width", [1440, 390])
def test_owner_edits_by_default_computed_fields_stay_locked_and_context_survives(site, data, width):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    char_id = _character(app, info, data)
    with sync_playwright() as p:
        browser, page, errors, _ = _context(p, origin, info["token"], width)
        page.goto(f"{origin}/character-sheet?id={char_id}&campaign_id=7&session_id=99&table=north")
        expect(page.locator("body")).to_have_attribute("data-sheet-mode", "edit")
        expect(page.locator("#charName")).to_be_enabled()
        # Computed SRD values stay disabled even in the default edit mode.
        for computed in ("#charStr", "#charLevel", "#charAc", "#charHpMax", "#charXp"):
            expect(page.locator(computed)).to_be_disabled()
        page.locator("#charName").fill("Mira Neu")
        page.locator("#saveCoreBtn").click()
        expect(page.locator("#messageBox")).to_contain_text("gespeichert")
        with app.app_context():
            assert db.session.get(Character, char_id).name == "Mira Neu"

        # Local lock: clearly labelled, nothing is saved, state returns on unlock.
        lock = page.locator("#sheetLockBtn")
        expect(lock).to_have_text("Bogen sperren")
        lock.click()
        expect(lock).to_have_text("Bogen entsperren")
        expect(page.locator("#charName")).to_be_disabled()
        expect(page.locator("#saveCoreBtn")).to_be_hidden()
        expect(page.locator("#modeLabel")).to_contain_text("gesperrt")
        lock.click()
        expect(page.locator("#charName")).to_be_enabled()

        # Switching mode keeps every table/campaign parameter, not just the session.
        page.locator("#sheetModeActionBtn").click()
        page.wait_for_url(re.compile(r"mode=view"))
        assert {"id": str(char_id), "campaign_id": "7", "session_id": "99", "table": "north", "mode": "view"}.items() <= _query(page).items()
        expect(page.locator("body")).to_have_attribute("data-sheet-mode", "view")
        expect(page.locator("#charName")).to_be_disabled()
        expect(page.locator("#sheetLockBtn")).to_be_hidden()
        page.locator("#sheetModeActionBtn").click()
        page.wait_for_url(re.compile(r"mode=edit"))
        assert {"id": str(char_id), "campaign_id": "7", "session_id": "99", "table": "north", "mode": "edit"}.items() <= _query(page).items()
        expect(page.locator("#charName")).to_be_enabled()
        assert page.evaluate("document.documentElement.scrollWidth") <= width + 1
        assert not errors, errors
        browser.close()


def test_explicit_view_entry_is_read_only_including_images(site, data):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    char_id = _character(app, info, data)
    with sync_playwright() as p:
        browser, page, errors, writes = _context(p, origin, info["token"], 1440)
        page.goto(f"{origin}/character-sheet?id={char_id}&mode=view")
        expect(page.locator("body")).to_have_attribute("data-sheet-mode", "view")
        expect(page.locator("#charName")).to_be_disabled()
        expect(page.locator("#saveCoreBtn")).to_be_hidden()
        page.get_by_role("tab", name="Verwaltung", exact=True).click()
        expect(page.locator("#sheetIdentityGrid")).to_be_visible()
        expect(page.locator("#sheetIdentityGrid button")).to_have_count(0)
        expect(page.locator("#sfManageImages")).to_be_hidden()
        # The read-only entry still offers the way back to editing.
        expect(page.locator("#sheetModeActionBtn")).to_have_text("Bogen bearbeiten")
        assert not [w for w in writes if "/api/characters/" in w[1]], writes
        assert not errors, errors
        browser.close()


@pytest.mark.parametrize("mode_query", ["", "&mode=edit"])
def test_shared_reader_gets_no_mutating_controls_or_requests(site, data, mode_query):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    char_id = _character(app, info, data)
    token, campaign_id = _reader(app, info, char_id)
    with sync_playwright() as p:
        browser, page, errors, writes = _context(p, origin, token, 1440)
        page.goto(f"{origin}/character-sheet?id={char_id}{mode_query}")
        expect(page.locator("#srdSheetBody")).to_contain_text("Magier 5")
        expect(page.locator("body")).to_have_attribute("data-sheet-mode", "view")
        expect(page.locator("body")).to_have_attribute("data-sheet-owner", "false")
        expect(page.locator("#charName")).to_be_disabled()
        expect(page.locator("#saveCoreBtn")).to_be_hidden()
        expect(page.locator("#sheetModeActionBtn")).to_be_hidden()
        expect(page.locator("#sheetLockBtn")).to_be_hidden()
        expect(page.locator("#sfManageImages")).to_have_count(0)
        page.get_by_role("tab", name="Verwaltung", exact=True).click()
        expect(page.locator("#sheetIdentityGrid")).to_be_visible()
        expect(page.locator("#sheetIdentityGrid button")).to_have_count(0)
        expect(page.locator("#srdManageDuplicate")).to_have_count(0)
        # Even a hand-called handler (as from the console) must not issue a write.
        page.evaluate("saveCore(); openIdentityPicker('avatar'); removeIdentity('avatar'); addSpell()")
        page.wait_for_timeout(300)
        assert not [w for w in writes if "/api/characters/" in w[1]], writes
        with app.app_context():
            assert db.session.get(Character, char_id).name == "Mira Eulenfeder"
        assert not errors, errors
        browser.close()


@pytest.mark.parametrize("width,language", [(1440, None), (390, None), (1440, "en"), (390, "en")])
def test_owner_uploads_replaces_and_removes_images_in_the_book(site, data, tmp_path, width, language):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    app.config["LOCAL_STORAGE_PATH"] = str(tmp_path / "storage")
    char_id = _character(app, info, data)
    image = tmp_path / "bild.png"
    image.write_bytes(PNG)
    text = {
        None: {"upload": "Avatar hochladen", "replace": "Avatar ersetzen", "remove": "Avatar entfernen", "saved": "gespeichert", "manage": "Bilder verwalten"},
        "en": {"upload": "Upload Avatar", "replace": "Replace Avatar", "remove": "Remove Avatar", "saved": "saved", "manage": "Manage images"},
    }[language]
    with sync_playwright() as p:
        browser, page, errors, _ = _context(p, origin, info["token"], width, language)
        page.on("dialog", lambda dialog: dialog.accept())
        page.goto(f"{origin}/character-sheet?id={char_id}")
        # The visible image action leads to the actual controls; no hidden DOM-only upload.
        page.locator("#sfManageImages").click()
        expect(page.locator("#sfManageImages")).to_have_text(text["manage"])
        upload = page.locator("#sheetIdentityUpload-avatar")
        expect(upload).to_be_visible()
        expect(upload).to_have_text(text["upload"])
        with page.expect_file_chooser() as chooser:
            upload.click()
        chooser.value.set_files(str(image))
        expect(page.locator("#messageBox")).to_contain_text(text["saved"])
        expect(page.locator("#sheetIdentityGrid img")).to_have_count(1)
        page.wait_for_function("() => document.querySelector('#sheetIdentityGrid img')?.naturalWidth === 1")
        expect(page.locator("#sheetIdentityUpload-avatar")).to_have_text(text["replace"])
        with app.app_context():
            assert db.session.get(Character, char_id).avatar_url == f"/api/characters/{char_id}/identity/avatar"

        with page.expect_file_chooser() as chooser:
            page.locator("#sheetIdentityUpload-avatar").click()
        chooser.value.set_files(str(image))
        expect(page.locator("#messageBox")).to_contain_text(text["saved"])
        expect(page.locator("#sheetIdentityGrid img")).to_have_count(1)
        page.wait_for_function("() => document.querySelector('#sheetIdentityGrid img')?.naturalWidth === 1")

        page.locator("#sheetIdentityRemove-avatar").click()
        expect(page.locator("#sheetIdentityGrid img")).to_have_count(0)
        expect(page.locator("#sheetIdentityUpload-avatar")).to_have_text(text["upload"])
        with app.app_context():
            assert db.session.get(Character, char_id).avatar_url is None
        # Locking the sheet takes the image controls away again without touching the file.
        page.locator("#sheetLockBtn").click()
        expect(page.locator("#sheetIdentityGrid button")).to_have_count(0)
        assert page.evaluate("document.documentElement.scrollWidth") <= width + 1
        assert not errors, errors
        browser.close()


def test_copy_from_the_sheet_is_independent_and_original_stays_unchanged(site, data, tmp_path):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    app.config["LOCAL_STORAGE_PATH"] = str(tmp_path / "storage")
    char_id = _character(app, info, data)
    with sync_playwright() as p:
        browser, page, errors, _ = _context(p, origin, info["token"], 1440)
        page.goto(f"{origin}/character-sheet?id={char_id}")
        page.get_by_role("tab", name="Verwaltung", exact=True).click()
        for _ in range(2):  # a second copy: no slot limit appears
            page.locator("#srdManageDuplicate").click()
            page.locator("#srdManageConfirm").click()
            page.wait_for_url(re.compile(r"/character-sheet\?id=(?!%d$)\d+" % char_id))
            copy_id = int(_query(page)["id"])
            expect(page.locator("#charName")).to_have_value("Mira Eulenfeder (Kopie)")
            page.goto(f"{origin}/character-sheet?id={char_id}")
            page.get_by_role("tab", name="Verwaltung", exact=True).click()
        page.goto(f"{origin}/character-sheet?id={copy_id}")
        expect(page.locator("#charName")).to_be_enabled()
        page.locator("#charName").fill("Nur die Kopie")
        page.locator("#saveCoreBtn").click()
        expect(page.locator("#messageBox")).to_contain_text("gespeichert")
        with app.app_context():
            assert db.session.get(Character, char_id).name == "Mira Eulenfeder"
            assert db.session.get(Character, copy_id).name == "Nur die Kopie"
            assert Character.query.filter_by(user_id=info["user_id"]).count() == 3
        page.goto(f"{origin}/character-sheet?id={char_id}")
        expect(page.locator("#charName")).to_have_value("Mira Eulenfeder")
        assert not errors, errors
        browser.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_fixed_section_links_open_the_known_area_without_writing(site, data, width):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    char_id = _character(app, info, data)
    with sync_playwright() as p:
        browser, page, errors, writes = _context(p, origin, info["token"], width)
        page.goto(f"{origin}/character-sheet?id={char_id}&section=identity&campaign_id=7")
        expect(page.locator("#sfTab-manage")).to_have_attribute("aria-selected", "true")
        expect(page.locator("#sheetIdentityGrid")).to_be_visible()
        page.wait_for_function("() => document.getElementById('sheetIdentityGrid').contains(document.activeElement)")

        page.goto(f"{origin}/character-sheet?id={char_id}&section=progression")
        expect(page.locator("#sfTab-manage")).to_have_attribute("aria-selected", "true")
        expect(page.locator("#srdProgression")).to_be_visible()
        expect(page.locator("#srdProgression")).to_contain_text("Stufe 5")

        # Unknown values are ignored: neither a tab jump nor a selector or script runs.
        page.goto(f"{origin}/character-sheet?id={char_id}&section=%22%5D%3Cimg%20src%3Dx%20onerror%3Dwindow.__pwned%3D1%3E")
        expect(page.locator("#sfTab-play")).to_have_attribute("aria-selected", "true")
        page.goto(f"{origin}/character-sheet?id={char_id}&section=manage")
        expect(page.locator("#sfTab-play")).to_have_attribute("aria-selected", "true")
        assert page.evaluate("window.__pwned === undefined")
        assert not [w for w in writes if "/api/characters/" in w[1]], writes
        with app.app_context():
            assert db.session.get(Character, char_id).name == "Mira Eulenfeder"

        # A section link grants nothing: with an explicit view the controls stay absent.
        page.goto(f"{origin}/character-sheet?id={char_id}&section=identity&mode=view")
        expect(page.locator("#sheetIdentityGrid")).to_be_visible()
        expect(page.locator("#sheetIdentityGrid button")).to_have_count(0)
        assert not errors, errors
        browser.close()


# ---------------------------------------------------------------- creator correction path


def _guided_fighter(page, origin, level):
    from playwright.sync_api import expect

    page.goto(f"{origin}/srd-creator")
    page.locator("#scNewGuided").click()
    expect(page.locator("#scBuilder")).to_be_visible()
    page.get_by_role("button", name="Kämpfer", exact=False).first.click()
    page.locator("#scLevel").fill(str(level))
    page.locator("#scLevel").dispatch_event("change")
    expect(page.locator("#scSave")).to_have_text("Gespeichert")


def _step(page, label):
    page.locator("#scSteps").get_by_role("button", name=re.compile(rf"^{label}")).click()


def test_creator_finding_leads_to_the_missing_weapon_mastery_choice(site):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    with sync_playwright() as p:
        browser, page, errors, _ = _context(p, origin, info["token"], 1440)
        _guided_fighter(page, origin, 1)
        _step(page, "Prüfung")
        finding = page.locator(".sc-finding", has_text="weapon-mastery").first
        expect(finding).to_be_visible()
        # The server message stays visible next to the action.
        expect(finding).to_contain_text("Wähle")
        finding.get_by_role("button", name=re.compile("^Zur Korrektur")).click()
        assert page.evaluate("window.SrdCreator.app.step") == "wahlen"
        focused = page.evaluate("document.activeElement.closest('[data-focus-path]')?.getAttribute('data-focus-path')")
        assert focused == "featureChoices.fighter.weapon-mastery"
        # No automatic write: nothing was chosen on the user's behalf.
        assert page.evaluate("window.SrdCreator.app.draft.state.featureChoices?.fighter?.['weapon-mastery'] ?? []") == []

        # Unknown or hostile paths only land on the step content; they never become selectors.
        _step(page, "Klasse")
        assert page.evaluate("window.SrdCreator.correctFinding({path: 'featureChoices.x\"]<img onerror=1>', message: 'x'})") is False
        assert page.evaluate("window.SrdCreator.app.step") == "wahlen"  # known step family, no matching control
        assert page.evaluate("window.SrdCreator.correctFinding({path: 'unbekannt.feld', message: 'x'})") is False
        assert page.evaluate("window.SrdCreator.app.step") == "pruefung"
        assert not errors, errors
        browser.close()


def test_creator_offers_no_second_nonrepeatable_feat_and_explains_a_saved_repeat(site):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    with sync_playwright() as p:
        browser, page, errors, _ = _context(p, origin, info["token"], 1440)
        _guided_fighter(page, origin, 6)
        feat = page.evaluate(
            "window.SrdCreator.app.data.feats.find((f) => f.category === 'Allgemeines Talent' && !f.repeatable"
            " && f.id !== 'feats.descriptions.ability-score-improvement' && !f.abilityIncrease)?.id"
            " ?? window.SrdCreator.app.data.feats.find((f) => f.category === 'Allgemeines Talent' && !f.repeatable"
            " && f.id !== 'feats.descriptions.ability-score-improvement').id")
        _step(page, "Wahlen")
        slot4 = page.locator(".sc-detail", has_text="Stufe 4")
        slot4.get_by_role("button", name="Talent", exact=True).click()
        page.locator("#scAdv-fighter-4-f").select_option(feat)
        slot6 = page.locator(".sc-detail", has_text="Stufe 6")
        slot6.get_by_role("button", name="Talent", exact=True).click()
        option = page.locator(f"#scAdv-fighter-6-f option[value='{feat}']")
        expect(option).to_have_count(1)
        assert page.evaluate("(id) => document.querySelector(`#scAdv-fighter-6-f option[value='${id}']`).disabled", feat) is True
        assert "bereits gewählt" in option.text_content()
        # The first slot still shows its own choice as a normal option.
        assert page.evaluate("(id) => document.querySelector(`#scAdv-fighter-4-f option[value='${id}']`).disabled", feat) is False
        assert page.evaluate("document.querySelector('#scAdv-fighter-4-f').value") == feat

        # A repeat that is already saved (older draft) is kept, explained and still refused by the server.
        page.evaluate(
            "(id) => window.SrdCreator.mutate((state) => { state.advancements.find((a) => a.classLevel === 6).featId = id; })", feat)
        expect(page.locator("[data-feat-repeat]")).to_have_count(1)
        assert page.evaluate("document.querySelector('#scAdv-fighter-6-f').value") == feat
        assert page.evaluate("window.SrdCreator.app.draft.state.advancements.length") == 2
        _step(page, "Prüfung")
        finding = page.locator(".sc-finding", has_text="kann nicht mehrfach gewählt werden").first
        expect(finding).to_be_visible()
        expect(page.locator("#scFinalize-btn")).to_be_disabled()
        finding.get_by_role("button", name=re.compile("^Zur Korrektur")).click()
        assert page.evaluate("window.SrdCreator.app.step") == "wahlen"
        assert page.evaluate("document.activeElement.id") == "scAdv-fighter-6-f"
        # Correcting the choice by hand clears the finding; the other slot is untouched.
        other = page.evaluate(
            "(id) => window.SrdCreator.app.data.feats.find((f) => f.category === 'Allgemeines Talent' && f.id !== id"
            " && f.id !== 'feats.descriptions.ability-score-improvement' && !f.abilityIncrease && !f.prerequisite?.raw)?.id", feat)
        if other:
            page.locator("#scAdv-fighter-6-f").select_option(other)
            expect(page.locator("[data-feat-repeat]")).to_have_count(0)
            assert page.evaluate("window.SrdCreator.app.draft.state.advancements.find((a) => a.classLevel === 4).featId") == feat
        assert not errors, errors
        browser.close()


def test_missing_sheet_permission_projection_keeps_edit_entry_read_only(site, data):
    from playwright.sync_api import expect, sync_playwright
    app, origin, info = site
    char_id = _character(app, info, data)
    with sync_playwright() as p:
        browser, page, errors, writes = _context(p, origin, info['token'], 1440)
        def without_projection(route):
            response = route.fetch()
            payload = response.json()
            payload['character'].pop('permissions', None)
            route.fulfill(response=response, json=payload)
        page.route(f'**/api/characters/{char_id}/sheet', without_projection)
        page.goto(f'{origin}/character-sheet?id={char_id}&mode=edit')
        expect(page.locator('#srdSheetBody')).to_be_visible()
        expect(page.locator('#charName')).to_be_disabled()
        expect(page.locator('#sheetModeActionBtn')).to_be_hidden()
        expect(page.locator('#sfManageImages')).to_have_count(0)
        assert not [w for w in writes if '/api/characters/' in w[1]], writes
        assert not errors, errors
        browser.close()


def test_local_lock_and_explicit_view_remove_srd_manage_mutations(site, data):
    from playwright.sync_api import expect, sync_playwright
    app, origin, info = site
    char_id = _character(app, info, data)
    with sync_playwright() as p:
        browser, page, errors, writes = _context(p, origin, info['token'], 1440)
        page.goto(f'{origin}/character-sheet?id={char_id}')
        page.get_by_role('tab', name='Verwaltung', exact=True).click()
        add = page.get_by_role('button', name='Begleiter hinzufügen', exact=True)
        expect(add).to_be_visible()
        before = len(writes)
        page.locator('#sheetLockBtn').click()
        expect(add).not_to_be_visible()
        expect(page.locator('#srdManageDuplicate')).not_to_be_visible()
        assert len(writes) == before
        page.locator('#sheetLockBtn').click()
        expect(add).to_be_visible()
        page.goto(f'{origin}/character-sheet?id={char_id}&mode=view')
        page.get_by_role('tab', name='Verwaltung', exact=True).click()
        expect(add).not_to_be_visible()
        expect(page.locator('#srdManageDuplicate')).not_to_be_visible()
        assert not errors, errors
        browser.close()
