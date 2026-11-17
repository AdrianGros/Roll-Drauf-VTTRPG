"""The shared frame respects feature availability and keeps document state intact."""

from tests.test_ui_book_feedback_browser import book_site, _browser_context  # noqa: F401
from tests.test_personal_actions_browser import action_site  # noqa: F401


def test_disabled_authoring_is_skipped_by_pager_and_refresh_keeps_content(book_site):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = book_site
    app.config['CE_AUTHORING'] = False
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = _browser_context(browser, origin, info, 390)
        page = context.new_page(); page.goto(origin + '/atlas')
        expect(page.locator('[data-creation-engine-nav]')).to_have_attribute('aria-disabled', 'true')
        expect(page.locator('[data-book-pager="next"]')).to_have_attribute('href', '/regelwerk')
        page.evaluate('''() => {
            const input=document.createElement('input'); input.id='lifecycleProbe'; input.value='Unsubmitted note';
            document.querySelector('#atlasRoot').append(input); window.originalProbe=input;
            VTTBookFrame.mount(document.querySelector('.dbf-book'));
            VTTBookFrame.mount(document.querySelector('.dbf-book'));
            document.title='A different document · Atlas · Roll Drauf';
            VTTDisplay.update({theme:'paper'});
        }''')
        expect(page.locator('.dbf-running-current')).to_have_text('A different document')
        assert page.evaluate("document.querySelector('#lifecycleProbe') === window.originalProbe")
        assert page.locator('#lifecycleProbe').input_value() == 'Unsubmitted note'
        assert page.locator('.dbf-spine').count() == 1
        assert page.locator('.dbf-pager').count() == 1
        assert page.locator('[data-book-pager="next"]').get_attribute('href') == '/regelwerk'
        context.close(); browser.close()


def test_direct_rule_language_is_retained_by_chapter_pager(book_site):
    from playwright.sync_api import expect, sync_playwright

    _, origin, info = book_site
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = _browser_context(browser, origin, info, 390, language='de')
        page = context.new_page(); page.goto(origin + '/regelwerk/en')
        expect(page.locator('[data-book-pager="next"]')).to_have_attribute('href', '/regelwerk/compendium?locale=en')
        page.goto(origin + '/regelwerk/compendium?locale=en')
        expect(page.locator('[data-book-pager="previous"]')).to_have_attribute('href', '/regelwerk/5.2.1/en')
        context.close()
        context = _browser_context(browser, origin, info, 390, language='en')
        page = context.new_page(); page.goto(origin + '/regelwerk/5.2.1/de/w20-pruefungen')
        expect(page.locator('[data-book-pager="next"]')).to_have_attribute('href', '/regelwerk/compendium?locale=de')
        page.goto(origin + '/regelwerk/compendium?locale=de')
        expect(page.locator('[data-book-pager="previous"]')).to_have_attribute('href', '/regelwerk?locale=de')
        context.close(); browser.close()
