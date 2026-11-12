"""C01: rulebook browser controls follow the UI language; rule/entity text never does."""
import re

import pytest

from tests.test_personal_actions_browser import action_site  # noqa:F401
from tests.test_presentation_browser import preferences

SRD = '/api/rulesets/srd-5.2.1-de'

SPELL_HEADERS = {
    'en': ['Name', 'Level', 'School', 'Casting time', 'Range', 'Comp.', 'Duration', 'Classes'],
    'de': ['Name', 'Grad', 'Schule', 'Zeitaufwand', 'Reichweite', 'Komp.', 'Dauer', 'Klassen'],
}


def open_page(playwright, origin, info, path, language, width=1000):
    browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width': width, 'height': 1000}, reduced_motion='reduce')
    preferences(context, language=language)
    context.add_cookies([{'name': 'access_token_cookie', 'value': info['player_auth'],
                          'url': origin, 'httpOnly': True}])
    page = context.new_page()
    page.set_default_timeout(30000)
    return browser, context, page


def api_json(page, path):
    return page.evaluate(
        '''async (path) => (await fetch(path, {credentials: 'same-origin'})).json()''', path)


@pytest.mark.parametrize('language', ['en', 'de'])
def test_compendium_headings_and_filters_follow_language_but_entity_text_does_not(action_site, language):
    from playwright.sync_api import expect, sync_playwright
    _app, origin, info = action_site
    with sync_playwright() as playwright:
        browser, _context, page = open_page(playwright, origin, info, '', language)
        page.goto(origin + '/regelwerk/compendium?type=spell')
        expect(page.locator('#cpTable')).to_be_visible()
        expect(page.locator('#cpHead th')).to_have_text(SPELL_HEADERS[language])
        labels = page.locator('#cpFilters label').all_text_contents()
        assert ('School' if language == 'en' else 'Schule') in labels
        assert ('Cantrip' if language == 'en' else 'Zaubertrick') in page.locator('#cpf-level option').all_text_contents()
        expect(page.locator('#cpf-school option').first).to_have_text('All' if language == 'en' else 'Alle')
        expect(page.locator('#cpStatus')).to_have_text(
            re.compile(r'^Showing \d+ of \d+ ' if language == 'en' else r'^\d+ von \d+ '))

        # Entity names come from the German SRD API and must be untouched in both languages.
        data = api_json(page, f'{SRD}/compendium?type=spell&limit=3')
        names = [item['name'] for item in data['items']]
        assert names
        expect(page.locator('#cpBody tr td:first-child a').first).to_have_text(names[0])
        first_rows = page.locator('#cpBody tr td:first-child a').all_text_contents()[:len(names)]
        assert first_rows == names

        page.locator('#cpBody tr td:first-child a').first.click()
        expect(page.locator('#cpDetail')).to_be_visible()
        entry = api_json(page, f"{SRD}/compendium/entry/{data['items'][0]['id']}")
        expect(page.locator('#cpDetailTitle')).to_have_text(entry['entity']['name'])
        meta_link = page.locator('#cpDetailMeta a')
        expect(meta_link).to_have_text('Read in the rulebook' if language == 'en' else 'Im Regelwerk lesen')
        paragraph = next((b['text'] for b in entry['blocks'] if b.get('type') == 'paragraph' and b.get('text')), None)
        if paragraph:
            assert paragraph.strip()[:40] in page.locator('#cpDetailBody').text_content()
        browser.close()


def test_english_creature_filters_translate_labels_but_keep_facet_values(action_site):
    from playwright.sync_api import expect, sync_playwright
    _app, origin, info = action_site
    with sync_playwright() as playwright:
        browser, _context, page = open_page(playwright, origin, info, '', 'en')
        page.goto(origin + '/regelwerk/compendium?type=creature')
        expect(page.locator('#cpTable')).to_be_visible()
        headers = page.locator('#cpHead th').all_text_contents()
        assert headers[:2] == ['Name', 'CR'] and 'AC' in headers and 'HP' in headers
        assert 'Legendary' in page.locator('#cpFilters label').all_text_contents()
        origin_options = page.locator('#cpf-origin option').all_text_contents()
        assert 'Animals' in origin_options and 'Monster' in origin_options
        facets = api_json(page, f'{SRD}/compendium?type=creature&limit=1')['facets']
        type_options = page.locator('#cpf-creatureType option').all_text_contents()
        assert type_options[0] == 'All'
        assert type_options[1:] == [str(v) for v in facets['creatureType']]
        page.locator('#cpf-legendary').select_option('true')
        expect(page.locator('#cpf-legendary option:checked')).to_have_text('Yes')
        browser.close()


@pytest.mark.parametrize('language,expected', [
    ('en', 'The compendium is not available.'), ('de', 'Compendium nicht verfügbar.'),
])
def test_compendium_failure_message_is_localized(action_site, language, expected):
    from playwright.sync_api import expect, sync_playwright
    _app, origin, info = action_site
    with sync_playwright() as playwright:
        browser, context, page = open_page(playwright, origin, info, '', language)
        context.route('**/api/rulesets/*/compendium*', lambda route: route.fulfill(
            status=500, content_type='application/json', body='{"error":"Interner Fehler"}'))
        page.goto(origin + '/regelwerk/compendium?type=spell')
        expect(page.locator('#cpStatus')).to_have_text(expected)
        browser.close()


def test_english_reader_controls_status_and_license_keep_rule_text(action_site):
    from playwright.sync_api import expect, sync_playwright
    _app, origin, info = action_site
    with sync_playwright() as playwright:
        browser, _context, page = open_page(playwright, origin, info, '', 'en')
        page.goto(origin + '/regelwerk')
        expect(page.locator('#regelwerkArticle')).to_have_attribute('aria-busy', 'false')
        expect(page.locator('#regelwerkToc .regelwerk-toc-heading')).not_to_have_text('Inhaltsverzeichnis')
        expect(page.locator('#regelwerkToc a').last).to_have_text('Source & license')
        expect(page.locator('.regelwerk-document-meta').first).to_have_text(
            re.compile(r'^SRD 5\.2\.1 · Pages? '))

        # German rule text from the API appears unchanged in the reader.
        manifest = api_json(page, f'{SRD}/manifest')
        document = manifest['sections'][0]['documents'][0]
        doc = api_json(page, f"{SRD}/documents/{document['documentId']}")
        body = page.locator('#regelwerkArticle').text_content()
        texts = [b['text'] for b in doc['blocks'] if b.get('type') in ('heading', 'paragraph') and b.get('text')]
        assert texts and all(t.strip()[:40] in body for t in texts[:3])

        page.locator('#regelwerkSearchInput').fill('Z')
        page.locator('#regelwerkSearch button[type=submit]').click()
        expect(page.locator('#regelwerkSearchStatus')).to_have_text('Please enter at least two characters.')
        page.locator('#regelwerkSearchInput').fill('Zauber')
        page.locator('#regelwerkSearch button[type=submit]').click()
        expect(page.locator('#regelwerkSearchStatus')).to_have_text(
            re.compile(r'^(\d+ results found\.|No results found\.)$'))
        found = api_json(page, f'{SRD}/search?q=Zauber')['results']
        headings = page.locator('#regelwerkSearchResults a strong').all_text_contents()
        assert headings == [r['heading'] for r in found]

        page.goto(origin + '/regelwerk/lizenz')
        expect(page.locator('#regelwerkArticle h2')).to_have_text('Source & license')
        expect(page.locator('#regelwerkArticle a').first).to_have_text('Open the official German SRD 5.2.1')
        license_data = api_json(page, f'{SRD}/license')
        shown = page.locator('.regelwerk-license-text').text_content().strip()
        assert shown == license_data['attribution'].strip()
        browser.close()


@pytest.mark.parametrize('language,heading,message', [
    ('en', 'Rulebook not available', 'The content could not be loaded.'),
    ('de', 'Regelwerk nicht verfügbar', 'Inhalt konnte nicht geladen werden.'),
])
def test_reader_load_failure_is_localized(action_site, language, heading, message):
    from playwright.sync_api import expect, sync_playwright
    _app, origin, info = action_site
    with sync_playwright() as playwright:
        browser, context, page = open_page(playwright, origin, info, '', language)
        context.route('**/api/rulesets/*/manifest', lambda route: route.fulfill(
            status=500, content_type='application/json', body='{"error":"x"}'))
        page.goto(origin + '/regelwerk')
        expect(page.locator('#regelwerkArticle h2')).to_have_text(heading)
        expect(page.locator('#regelwerkArticle .regelwerk-status')).to_have_text(message)
        browser.close()
