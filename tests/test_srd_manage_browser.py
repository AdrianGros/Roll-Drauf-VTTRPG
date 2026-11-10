"""P10: level-down, companions, duplicate, archive and drafts work in a real browser."""

import re

import pytest

from tests.test_srd_creator_api import data  # noqa: F401
from tests.test_srd_inventory_browser import _character
from tests.test_srd_sheet import QuietHandler, site  # noqa: F401


def _page(p, origin, info, width):
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
    context.add_cookies([{"name": "access_token_cookie", "value": info["token"], "url": origin, "httpOnly": True}])
    page = context.new_page()
    page.set_default_timeout(15000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    return browser, page, errors


@pytest.mark.parametrize("width", [1440, 390])
def test_level_down_and_companions_on_the_sheet(site, data, width):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    char_id = _character(app, info, data)
    with sync_playwright() as p:
        browser, page, errors = _page(p, origin, info, width)
        page.goto(f"{origin}/character-sheet?id={char_id}&mode=edit")
        page.get_by_role("tab", name="Verwaltung", exact=True).click()
        progression = page.locator("#srdProgression")
        expect(progression).to_contain_text("Stufe 5")

        page.locator("#srdProgDown").click()
        expect(progression).to_contain_text("wird zurückgenommen")
        page.get_by_role("button", name="Abbrechen").first.click()
        expect(page.locator("#srdProgDownConfirm")).to_have_count(0)
        page.locator("#srdProgDown").click()
        page.locator("#srdProgDownConfirm").click()
        expect(page.locator("#charLevel")).to_have_value("4")
        expect(progression).to_contain_text("Stufe 4")
        expect(progression).to_contain_text("Verlauf")

        page.locator("#srdManageAddCompanion").click()
        card = page.locator(".srd-man-card").first
        card.locator("[data-field=name]").fill("Wolf")
        card.locator("[data-field=hpMax]").fill("11")
        card.locator("[data-field=hpCurrent]").fill("7")
        card.locator("[data-field=attacks]").fill("Biss +4")
        page.locator("#srdManageSaveCompanions").click()
        expect(page.locator("#srdManageStatus")).to_contain_text("gespeichert")
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert overflow <= 1, overflow

        page.reload()
        page.get_by_role("tab", name="Verwaltung", exact=True).click()
        expect(page.locator(".srd-man-card [data-field=name]").first).to_have_value("Wolf")
        expect(page.locator(".srd-man-card [data-field=hpCurrent]").first).to_have_value("7")
        page.get_by_role("button", name="Begleiter entfernen").click()
        page.locator("#srdManageSaveCompanions").click()
        expect(page.locator("#srdManage")).to_contain_text("Keine Begleiter")
        assert not errors, errors
        browser.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_duplicate_rebuild_and_archive_flow(site, data, width):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    char_id = _character(app, info, data)
    with sync_playwright() as p:
        browser, page, errors = _page(p, origin, info, width)
        page.goto(f"{origin}/character-sheet?id={char_id}&mode=edit")
        page.get_by_role("tab", name="Verwaltung", exact=True).click()
        page.locator("#srdManageDuplicate").click()
        page.locator("#srdManageConfirm").click()
        page.wait_for_url(re.compile(r"/character-sheet\?id=(?!%d$)\d+" % char_id))
        expect(page.locator("#charName")).to_have_value("Mira Eulenfeder (Kopie)")
        page.get_by_role("tab", name="Verwaltung", exact=True).click()
        expect(page.locator("#srdManage")).to_be_visible()

        page.goto(f"{origin}/character-sheet?id={char_id}&mode=edit")
        page.get_by_role("tab", name="Verwaltung", exact=True).click()
        page.locator("#srdManageRebuild").click()
        page.locator("#srdManageConfirm").click()
        page.wait_for_url(re.compile(r"/srd-creator\?draft=\d+"))

        page.goto(f"{origin}/character-sheet?id={char_id}&mode=edit")
        page.get_by_role("tab", name="Verwaltung", exact=True).click()
        page.locator("#srdManageArchive").click()
        page.locator("#srdManageConfirm").click()
        page.wait_for_url(re.compile(r"/characters"))
        archive = page.locator("[data-archived-characters]")
        expect(archive).to_contain_text("Archiv (1)")
        drafts = page.locator("[data-open-drafts]")
        expect(drafts).to_contain_text("Offene Entwürfe (1)")
        expect(drafts.locator("[data-draft-continue]")).to_have_attribute("href", re.compile(r"/srd-creator\?draft=\d+"))
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert overflow <= 1, overflow

        archive.locator("summary").click()
        archive.get_by_role("button", name="Wiederherstellen").click()
        expect(page.locator("[data-archived-characters]")).to_have_count(0)
        expect(page.get_by_role("button", name="Archivieren")).to_have_count(2)

        page.get_by_role("button", name="Archivieren").first.click()
        expect(page.locator("[data-archived-characters]")).to_contain_text("Archiv (1)")
        page.on("dialog", lambda dialog: dialog.accept())
        page.locator("[data-archived-characters] summary").click()
        page.get_by_role("button", name="Endgültig löschen").click()
        expect(page.locator("[data-archived-characters]")).to_have_count(0)
        assert not errors, errors
        browser.close()
