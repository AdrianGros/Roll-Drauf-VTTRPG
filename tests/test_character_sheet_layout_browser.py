"""Character sheet layout regression checks for phone and desktop readers."""

from playwright.sync_api import expect, sync_playwright

from tests.test_srd_creator_api import data  # noqa: F401
from tests.test_sheet_to_table_browser import live_table  # noqa: F401


def test_character_sheet_pages_fit_their_content(live_table):
    _, origin, ids = live_table
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        for width, height in ((390, 844), (1280, 900)):
            context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce")
            context.add_cookies([{
                "name": "access_token_cookie", "value": ids["token"],
                "url": origin, "httpOnly": True,
            }])
            page = context.new_page()
            page.set_default_timeout(15000)
            page.goto(f"{origin}/character-sheet?id={ids['char']}")
            expect(page.locator("#srdRollDestination")).to_be_visible()
            geometry = page.evaluate("""() => {
                const rect = selector => {
                    const element = document.querySelector(selector);
                    const box = element.getBoundingClientRect();
                    return { y: Math.round(box.y), height: Math.round(box.height),
                             scrollHeight: element.scrollHeight, clientHeight: element.clientHeight,
                             display: getComputedStyle(element).display,
                             minHeight: getComputedStyle(element).minHeight };
                };
                return { viewport: innerWidth, documentWidth: document.documentElement.scrollWidth,
                         documentHeight: document.documentElement.scrollHeight,
                         spread: rect('#sheetSpread'), index: rect('.sheet-focus-page .book-page--index'),
                         content: rect('.sheet-focus-page .book-page--content'),
                         title: rect('#sheetTitle'), roll: rect('[data-roll-kind="initiative"]'),
                         identity: rect('.sheet-identity-preview') };
            }""")
            assert geometry["documentWidth"] == width, geometry
            assert geometry["title"]["y"] < height // 2, geometry
            assert geometry["roll"]["y"] + geometry["roll"]["height"] < height, geometry
            assert geometry["index"]["scrollHeight"] <= geometry["index"]["clientHeight"] + 2, geometry
            assert geometry["documentHeight"] - geometry["index"]["y"] - geometry["index"]["height"] < 100, geometry
            assert geometry["index"]["minHeight"] == "0px", geometry
            assert geometry["content"]["display"] == "none", geometry
            assert geometry["identity"]["height"] <= 100, geometry
            expect(page.locator("#sheetTitle")).to_have_text("Mira Eulenfeder")

            page.goto(f"{origin}/character-sheet?id={ids['char']}&mode=edit")
            expect(page.locator("#srdRollDestination")).to_be_visible()
            expect(page.locator("#sheetForm")).to_be_visible()
            expect(page.locator("#charName")).to_have_value("Mira Eulenfeder")
            context.close()
        browser.close()
