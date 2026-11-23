"""Route state remains visible after closing the shared navigation disclosure."""

import json
import re

import pytest

from tests.test_srd_sheet import site  # noqa: F401


@pytest.mark.parametrize("engine,width,language,theme", [
    ("chromium", 390, "de", "night"),
    ("firefox", 1440, "en", "paper"),
])
def test_closed_navigation_group_and_direct_pages(site, engine, width, language, theme):
    from playwright.sync_api import expect, sync_playwright

    _, origin, info = site
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch(headless=True,
            **({"args": ["--no-sandbox"]} if engine == "chromium" else {}))
        context = browser.new_context(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
        context.add_cookies([{"name": "access_token_cookie", "value": info["token"],
                             "url": origin, "httpOnly": True}])
        prefs = {"schema": 1, "theme": theme, "language": language, "accent": "teal"}
        context.add_init_script(f"localStorage.setItem('vtt.display.v1', {json.dumps(json.dumps(prefs))});")
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append({
            "message": str(error), "stack": str(getattr(error, 'stack', '')), "url": page.url,
        }))
        page.goto(origin + "/dashboard")
        nav = page.locator('.book-dashboard-ribbon:visible')
        expect(nav).to_have_count(1)
        group = nav.locator('.vtt-nav-play')
        summary = group.locator('summary')
        summary.click()
        group.locator('a[href="/campaigns"]').click()
        expect(page).to_have_url(origin + "/campaigns", timeout=15000)
        expect(nav.locator('a[aria-current="page"]')).to_have_attribute('href', '/campaigns')
        expect(group).not_to_have_attribute('open', '')
        expect(summary).to_have_css('text-decoration-line', 'underline')
        summary.click()
        summary.press('Escape')
        expect(summary).to_be_focused()
        expect(group).not_to_have_attribute('open', '')
        expect(summary).to_have_css('text-decoration-line', 'underline')

        nav.locator('a[href="/dashboard"]').click()
        expect(page).to_have_url(origin + '/dashboard', timeout=15000)
        expect(summary).not_to_have_css('text-decoration-line', 'underline')
        for path in ['/conversations', '/atlas', '/regelwerk/compendium']:
            nav.locator(f'a[href="{path}"]').click()
            expect(page).to_have_url(re.compile(re.escape(path)), timeout=15000)
            expect(page.locator('.book-dashboard-ribbon:visible')).to_have_count(1)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
            page.go_back()
            expect(page).to_have_url(origin + '/dashboard', timeout=15000)
            expect(page.locator('.book-dashboard-ribbon:visible')).to_have_count(1)
        assert not errors, errors
        browser.close()


def test_dashboard_contents_has_consistent_numbered_destinations(site):
    from playwright.sync_api import expect, sync_playwright

    _, origin, info = site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion='reduce')
        context.add_cookies([{"name": "access_token_cookie", "value": info['token'],
                             "url": origin, "httpOnly": True}])
        page = context.new_page()
        page.goto(origin + '/dashboard')
        toc = page.locator('.book-toc')
        expect(toc).to_be_visible()
        for path in ['/campaigns', '/characters', '/conversations', '/mapmaker', '/atlas', '/regelwerk/compendium']:
            expect(toc.locator(f'a[href="{path}"]')).to_have_count(1)
        # Wait for the existing capability lookup to settle before inspecting its label structure.
        expect(toc.locator('[data-creation-engine-nav]')).not_to_contain_text('wird geprüft', timeout=15000)
        rows = toc.locator('.book-toc-row:visible')
        expected = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX'][:rows.count()]
        assert rows.locator('.book-toc-numeral').all_text_contents() == expected
        assert rows.locator('.book-toc-label').count() == rows.count()
        sizes = rows.locator('.book-toc-label').evaluate_all('(labels) => labels.map(el => getComputedStyle(el).fontSize)')
        assert len(set(sizes)) == 1
        browser.close()
