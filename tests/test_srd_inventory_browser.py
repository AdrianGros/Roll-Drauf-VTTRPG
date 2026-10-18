"""P7: the inventory block of the SRD sheet works in a real browser."""

import os
from pathlib import Path

import pytest

from tests.test_srd_creator_api import data  # noqa: F401
from tests.test_srd_sheet import QuietHandler, site  # noqa: F401
from vtt.extensions import db


def _character(app, info, data, name="Mira Eulenfeder"):
    from tests.test_srd_creator_api import wizard_state
    from vtt.models import Character
    from vtt.rules_content.creator_drafts import character_values
    from vtt.rules_content.creator_rules import evaluate

    state = wizard_state(data, name)
    with app.app_context():
        values = character_values(data, state, evaluate(data, state), draft_id=1, finalized_at="2026-10-18T10:00:00Z")
        character = Character(user_id=info["user_id"], **values)
        db.session.add(character)
        db.session.commit()
        return character.id


@pytest.mark.parametrize("width", [1440, 390])
def test_inventory_is_built_and_used_from_the_sheet(site, data, width):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    char_id = _character(app, info, data)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
        context.add_cookies([{"name": "access_token_cookie", "value": info["token"], "url": origin, "httpOnly": True}])
        page = context.new_page()
        page.set_default_timeout(15000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(f"{origin}/character-sheet?id={char_id}&mode=edit")
        inventory = page.locator("#srdInventory")
        expect(inventory).to_contain_text("noch nicht im Inventar")
        expect(page.locator("#legacyInventoryPane")).to_be_hidden()
        expect(page.locator("#legacyEquipmentPane")).to_be_hidden()

        page.locator("#srdInventory select").nth(0).select_option("A")
        page.locator("#srdInventory select").nth(1).select_option("A")
        page.get_by_role("button", name="Ausgangsausrüstung übernehmen").click()
        expect(inventory).to_contain_text("Gegenstände (14)")
        expect(inventory).to_contain_text("Dolch")
        expect(inventory).to_contain_text("Noch zu wählen: Arkaner Fokus")
        expect(page.locator("#srdCoinGM")).to_have_value("513")
        expect(inventory).to_contain_text("Tragelast")

        page.get_by_role("button", name="Nehmen").click()
        expect(inventory).not_to_contain_text("Noch zu wählen")

        page.fill("#srdInvSearch", "Lederrüstung")
        page.locator("#srdInvResults").select_option(index=0)
        page.get_by_role("button", name="Hinzufügen", exact=True).click()
        row = page.locator(".srd-inv-item", has_text="Lederrüstung").first
        expect(row).to_be_visible()
        expect(page.locator("#srdAcCell")).to_contain_text("11")
        row.get_by_role("button", name="Anlegen").click()
        expect(page.locator("#srdAcCell")).to_contain_text("12")
        expect(page.locator(".srd-inv-item.is-equipped", has_text="Lederrüstung")).to_be_visible()
        row = page.locator(".srd-inv-item", has_text="Lederrüstung").first
        row.get_by_role("button", name="Ablegen").click()
        expect(page.locator("#srdAcCell")).to_contain_text("11")

        dagger = page.locator(".srd-inv-attack", has_text="Dolch").first
        dagger.get_by_role("button", name="Angriff +4").click()
        expect(page.locator("#srdRollResult")).to_contain_text("Angriff: Dolch")
        expect(page.locator("#srdRollResult")).to_contain_text("+ 4 =")
        dagger.get_by_role("button", name="Kritisch").click()
        expect(page.locator("#srdRollResult")).to_contain_text("Schaden: Dolch (Stich) (Kritisch)")
        page.locator('.srd-inv-attack[data-attack-key="unarmed"]').get_by_role("button", name="Schaden").click()
        expect(page.locator("#srdRollResult")).to_contain_text("Schaden: Waffenloser Schlag (Wucht): 0 = 0")
        staff = page.locator(".srd-inv-attack", has_text="Kampfstab").first
        staff.get_by_role("button", name="Zweihändig").click()
        expect(page.locator("#srdRollResult")).to_contain_text("zweihändig")

        page.fill("#srdCoinGM", "7")
        page.get_by_role("button", name="Münzen speichern").click()
        expect(page.locator("#srdInvStatus")).to_contain_text("Münzen gespeichert")
        page.fill("#srdCoinGM", "-3")
        page.get_by_role("button", name="Münzen speichern").click()
        expect(page.locator("#srdInvStatus")).to_contain_text("Ungültige Münzmenge")

        page.fill("#srdInvCustomName", "Amboss")
        page.fill("#srdInvCustomWeight", "90")
        page.get_by_role("button", name="Eigenen anlegen").click()
        expect(inventory).to_contain_text("Über der Tragkraft")
        page.locator(".srd-inv-item", has_text="Amboss").get_by_role("button", name="Entfernen").click()
        expect(inventory).not_to_contain_text("Über der Tragkraft")

        assert page.evaluate("document.documentElement.scrollWidth") <= width + 1
        if os.environ.get("VTT_PROOF_DIR"):
            out = Path(os.environ["VTT_PROOF_DIR"])
            out.mkdir(parents=True, exist_ok=True)
            inventory.scroll_into_view_if_needed()
            page.screenshot(path=str(out / f"srd-inventory-{width}.png"), full_page=True)
        browser.close()
        assert errors == [], errors

    # the stored result survives a reload and the view mode has no controls
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
        context.add_cookies([{"name": "access_token_cookie", "value": info["token"], "url": origin, "httpOnly": True}])
        page = context.new_page()
        page.set_default_timeout(15000)
        page.goto(f"{origin}/character-sheet?id={char_id}")
        expect(page.locator("#srdInventory")).to_contain_text("Dolch")
        expect(page.locator("#srdInventory")).to_contain_text("Tragelast")
        assert page.get_by_role("button", name="Entfernen").count() == 0
        assert page.locator("#srdInvSearch").count() == 0
        assert page.locator("#srdCoinGM").is_disabled()
        browser.close()
