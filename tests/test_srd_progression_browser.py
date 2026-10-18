"""P8: XP award and level-up wizard of the SRD sheet work in a real browser."""

import pytest

from tests.test_srd_creator_api import data  # noqa: F401
from tests.test_srd_inventory_browser import _character
from tests.test_srd_sheet import QuietHandler, site  # noqa: F401


def _fill_open_steps(page):
    for _ in range(12):
        steps = page.locator("#srdWizard .srd-prog-step:has(.srd-prog-counter)")
        progressed = False
        for index in range(steps.count()):
            step = steps.nth(index)
            for counter_index in range(step.locator(".srd-prog-counter").count()):
                counter = step.locator(".srd-prog-counter").nth(counter_index)
                if "is-done" in (counter.get_attribute("class") or ""):
                    continue
                box = step.locator("input[type=checkbox]:not(:checked):not(:disabled)").first
                if box.count():
                    box.click()
                    progressed = True
                    page.wait_for_timeout(250)
                    break
            if progressed:
                break
        if not progressed:
            return


@pytest.mark.parametrize("width", [1440, 390])
def test_xp_award_and_level_up_wizard(site, data, width):
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
        progression = page.locator("#srdProgression")
        expect(progression).to_contain_text("Stufe 5")
        expect(page.locator("#charXp")).to_be_disabled()
        expect(page.get_by_role("button", name="Stufe 6 aufsteigen")).to_have_count(0)

        page.fill("#srdProgXpAmount", "7500")
        page.fill("#srdProgXpNote", "Drachenhort")
        page.get_by_role("button", name="EP vergeben").click()
        expect(progression).to_contain_text("Bereit für Stufe 6")
        expect(page.locator("#charXp")).to_have_value("14000")

        page.get_by_role("button", name="Stufe 6 aufsteigen").click()
        wizard = page.locator("#srdWizard")
        expect(wizard).to_contain_text("Stufe 6: Magier 6")
        expect(page.locator("#srdWizConfirm")).to_be_disabled()
        _fill_open_steps(page)
        expect(page.locator("#srdWizConfirm")).to_be_enabled()
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert overflow <= 1, overflow
        wizard.scroll_into_view_if_needed()
        page.screenshot(path=f"/proof/p8-wizard-{width}.png") if __import__("os").environ.get("VTT_PROOF_DIR") else None
        page.locator("#srdWizConfirm").click()
        expect(page.locator("#charLevel")).to_have_value("6")
        expect(page.locator("#srdProgression")).to_contain_text("Stufe 6")
        expect(page.locator("#srdWizard")).to_have_count(0)
        assert not errors, errors
        browser.close()
