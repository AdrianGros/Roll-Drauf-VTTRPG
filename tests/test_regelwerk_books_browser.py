"""Real browser: switching between the SRD and Oglans Book of Chaos in the Regelwerk reader."""

import os

import pytest

from tests.test_srd_manage_browser import _page
from tests.test_srd_sheet import QuietHandler, site  # noqa: F401


@pytest.mark.parametrize("width", [1440, 390])
def test_reader_switches_between_the_srd_and_the_own_book(site, width):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    with sync_playwright() as p:
        browser, page, errors = _page(p, origin, info, width)
        page.goto(f"{origin}/regelwerk/oglan")
        expect(page.locator("#regelwerkTitle")).to_have_text("Oglans Book of Chaos")
        books = page.locator("#regelwerkBooks a")
        expect(books).to_have_count(2)
        expect(page.locator("#regelwerkBooks a[aria-current=page]")).to_contain_text("Oglans Book of Chaos")
        expect(page.locator("#regelwerkPreviewBadge")).to_be_visible()
        expect(page.locator(".regelwerk-document-meta")).to_contain_text("eigenes Werk von Roll Drauf")
        toc = page.locator(".regelwerk-toc")
        for section in ("Vorwort", "Unterklassen", "Zauber"):
            expect(toc.locator(".regelwerk-toc-section", has_text=section)).to_be_visible()
        expect(page.locator("#regelwerkFooterSource")).to_contain_text("eigenes Werk von Roll Drauf")
        if os.environ.get("VTT_PROOF_DIR"):
            page.screenshot(path=os.path.join(os.environ["VTT_PROOF_DIR"], f"oglan-home-{width}.png"), full_page=True)

        toc.locator("a", has_text="Druide").click()
        expect(page).to_have_url(f"{origin}/regelwerk/oglan/de/unterklassen-druide")
        expect(page.locator(".regelwerk-article h2").first).to_be_visible()
        if os.environ.get("VTT_PROOF_DIR"):
            page.screenshot(path=os.path.join(os.environ["VTT_PROOF_DIR"], f"oglan-subclass-{width}.png"), full_page=True)

        page.locator("#regelwerkSearchInput").fill("Oglans")
        page.locator("#regelwerkSearch button").click()
        first = page.locator(".regelwerk-search-result").first
        expect(first).to_be_visible()
        assert first.get_attribute("href").startswith("/regelwerk/oglan/de/")

        page.locator("#regelwerkLicenseLink").click()
        expect(page).to_have_url(f"{origin}/regelwerk/oglan/lizenz")
        expect(page.locator(".regelwerk-article")).to_contain_text("© 2026 Roll Drauf")
        expect(page.locator(".regelwerk-article")).to_contain_text("Creative Commons")

        books.filter(has_text="SRD").click()
        expect(page).to_have_url(f"{origin}/regelwerk")
        expect(page.locator("#regelwerkTitle")).to_have_text("Regelwerk")
        expect(page.locator("#regelwerkBooks a[aria-current=page]")).to_contain_text("SRD")
        expect(page.locator(".regelwerk-document-meta")).to_contain_text("SRD 5.2.1")

        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert overflow <= 1, overflow
        assert not errors, errors
        browser.close()
