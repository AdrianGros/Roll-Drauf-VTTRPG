"""The Regelwerk table of contents groups the A-Z catalogues instead of repeating long titles."""

import os

import pytest

from tests.test_srd_manage_browser import _page
from tests.test_srd_sheet import QuietHandler, site  # noqa: F401


@pytest.mark.parametrize("width", [1440, 390])
def test_toc_groups_catalogues_and_marks_the_current_page(site, width):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    with sync_playwright() as p:
        browser, page, errors = _page(p, origin, info, width)
        page.goto(f"{origin}/regelwerk/5.2.1/de/magische-gegenstaende-k-m")
        toc = page.locator(".regelwerk-toc")
        expect(toc.locator("summary", has_text="Magische Gegenstände A–Z")).to_be_visible()
        expect(toc.locator("summary", has_text="Regeln für magische Gegenstände")).to_be_visible()
        current = toc.locator("a[aria-current=page]")
        expect(current).to_have_text("K–M")
        assert current.evaluate("el => el.closest('details').open") is True
        assert toc.locator("details", has_text="Zauber A–Z").evaluate("el => el.open") is False
        assert toc.locator("a", has_text="Magische Gegenstände A–B").count() == 0
        assert toc.locator("details", has_text="Magische Gegenstände A–Z").locator("a").all_inner_texts()[:2] == ["Hinweise zum Katalog", "A–B"]
        expect(toc.locator("a", has_text="Überblick")).to_have_count(1)
        toc.locator("details", has_text="Zauber A–Z").locator("summary").click()
        toc.locator("details", has_text="Zauber A–Z").locator("a", has_text="C–E").click()
        expect(page.locator(".regelwerk-article h2").first).to_contain_text("C")
        expect(toc.locator("a[aria-current=page]")).to_have_text("C–E")
        expect(page.locator(".regelwerk-breadcrumbs")).to_have_text("Zauber › Zauber A–Z › C–E")
        expect(page.locator(".regelwerk-document-meta")).to_contain_text("Seiten 129–138")
        if os.environ.get("VTT_PROOF_DIR"):
            toc.locator("summary", has_text="Zauber A–Z").scroll_into_view_if_needed()
            page.screenshot(path=os.path.join(os.environ["VTT_PROOF_DIR"], f"regelwerk-toc-{width}.png"))
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert overflow <= 1, overflow
        assert not errors, errors
        browser.close()
