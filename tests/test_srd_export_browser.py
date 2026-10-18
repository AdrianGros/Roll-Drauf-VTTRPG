"""P12: PDF, JSON backup, import and colour theme work in a real browser."""

import re

import pytest

from tests.test_srd_creator_api import data  # noqa: F401
from tests.test_srd_inventory_browser import _character
from tests.test_srd_manage_browser import _page
from tests.test_srd_sheet import QuietHandler, site  # noqa: F401


@pytest.mark.parametrize("width", [1440, 390])
def test_pdf_backup_import_and_theme(site, data, tmp_path, width):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    char_id = _character(app, info, data)
    with sync_playwright() as p:
        browser, page, errors = _page(p, origin, info, width)
        page.set_viewport_size({"width": width, "height": 1000})
        page.goto(f"{origin}/character-sheet?id={char_id}&mode=edit")
        expect(page.locator("#srdManagePdf")).to_be_visible()

        with page.expect_download() as download:
            page.locator("#srdManagePdf").click()
        pdf = tmp_path / "bogen.pdf"
        download.value.save_as(pdf)
        assert pdf.read_bytes().startswith(b"%PDF") and download.value.suggested_filename.endswith(".pdf")
        expect(page.locator("#srdManageStatus")).to_contain_text("PDF erstellt")

        with page.expect_download() as download:
            page.locator("#srdManageExport").click()
        backup = tmp_path / download.value.suggested_filename
        download.value.save_as(backup)
        assert backup.name.endswith(".rollcharakter.json") and b'"roll-drauf-srd-character"' in backup.read_bytes()

        page.locator("[data-theme=meerblau]").click()
        expect(page.locator("[data-theme=meerblau]")).to_have_attribute("aria-pressed", "true")
        expect(page.locator("body")).to_have_attribute("data-srd-theme", "meerblau")
        page.reload()
        expect(page.locator("[data-theme=meerblau]")).to_have_attribute("aria-pressed", "true")
        expect(page.locator("body")).to_have_attribute("data-srd-theme", "meerblau")
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert overflow <= 1, overflow

        page.goto(f"{origin}/srd-creator")
        page.locator("#scImportGo").click()
        expect(page.locator("#scImportMessage")).to_contain_text("wähle zuerst")
        broken = tmp_path / "kaputt.json"
        broken.write_text("{nicht json")
        page.locator("#scImportFile").set_input_files(broken)
        page.locator("#scImportGo").click()
        expect(page.locator("#scImportMessage")).to_contain_text("keine gültige")
        page.locator("#scImportFile").set_input_files(backup)
        page.locator("#scImportGo").click()
        page.wait_for_url(re.compile(r"/character-sheet\?id=(?!%d$)\d+" % char_id))
        expect(page.locator("#charName")).to_have_value("Mira Eulenfeder")
        expect(page.locator("body")).to_have_attribute("data-srd-theme", "violett")
        assert not errors, errors
        browser.close()
