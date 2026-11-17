"""Shared book materials preserve the real document surfaces and editor lifecycle."""

import json
import os
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from flask import render_template

from tests.test_personal_actions_browser import action_site  # noqa: F401


@pytest.fixture
def book_site(action_site):
    app, origin, info = action_site
    # The authoring gateway needs PostgreSQL; exercise its actual template and Eagle
    # browser module here, with transport fixtures for its world/directory reads.
    app.config['CE_AUTHORING'] = True
    app.extensions['ce_gateway'] = SimpleNamespace(authoring=object())
    if not any(rule.rule == '/api/ce/authoring' for rule in app.url_map.iter_rules()):
        app.add_url_rule('/api/ce/authoring', 'book_authoring_template',
                         lambda: render_template('creation-engine.html'))
    return app, origin, info


def _browser_context(browser, origin, info, width, language='de', theme='night'):
    context = browser.new_context(viewport={'width': width, 'height': 1000}, reduced_motion='reduce')
    context.add_cookies([{'name': 'access_token_cookie', 'value': info['dm_auth'],
                         'url': origin, 'httpOnly': True}])
    prefs = json.dumps({'schema': 1, 'theme': theme, 'language': language, 'accent': 'default'})
    context.add_init_script(f"localStorage.setItem('vtt.display.v1', JSON.stringify({prefs}));")

    def authoring_read(route):
        path = urlsplit(route.request.url).path
        if path.endswith('/worlds'):
            body = {'worlds': [{'id': 'personal', 'label': 'Personal'}], 'rulesVersion': 'modern'}
        elif path.endswith('/documents'):
            body = {'world': [], 'library': []}
        else:
            body = {'index': []}
        route.fulfill(json=body)

    context.route('**/api/ce/authoring/**', authoring_read)
    return context


@pytest.mark.parametrize('width', [1440, 390, 320])
def test_six_book_surfaces_share_frame_without_mobile_overflow(book_site, width, tmp_path):
    from playwright.sync_api import expect, sync_playwright

    _, origin, info = book_site
    pages = [('/conversations', 'conversations', '#privateConversations'),
             ('/mapmaker', 'maps', '#mapCanvas'), ('/atlas', 'atlas', '#atlasRoot'),
             ('/api/ce/authoring', 'creation', '#ce-create'),
             ('/regelwerk/5.2.1/de/w20-pruefungen', 'rules', '#regelwerkArticle h2'),
             ('/regelwerk/compendium', 'compendium', '#cpBody tr')]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        for language, theme in (('de', 'night'), ('en', 'night'), ('de', 'paper')):
            context = _browser_context(browser, origin, info, width, language, theme)
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.set_default_timeout(20000)
            for path, chapter, ready in pages:
                page.goto(origin + path)
                root = page.locator(f'.dbf-book[data-book-chapter="{chapter}"]')
                expect(root).to_have_attribute('data-book-ready', 'true')
                expect(root.locator(':scope > .dbf-spine')).to_be_visible()
                expect(root.locator('[data-book-running-head] .dbf-pager')).to_be_visible()
                expect(page.locator(ready).first).to_be_visible()
                if chapter == 'maps':
                    expect(page.locator('#app')).to_have_attribute('data-state', 'ready', timeout=60000)
                    page.locator('#newEmpty').click()
                assert page.evaluate('document.documentElement.scrollWidth') <= width + 1, (path, language)
                assert page.locator('.dbf-running-head').evaluate('(el)=>el.scrollWidth <= el.clientWidth + 1'), (path, language)
                assert page.locator('html').get_attribute('lang') == language
                assert not errors, (path, errors)
                if chapter != 'maps':
                    assert root.locator(':scope > .dbf-page').evaluate(
                        '(el)=>getComputedStyle(el).boxShadow !== "none"')
                if chapter == 'creation':
                    # This opens the real bundled Eagle editor; only world reads are fixtures.
                    page.locator('#ce-create').click()
                    editor = page.locator('#ce-eagle-mount .eh-window')
                    expect(editor).to_be_visible()
                    assert not editor.evaluate('(el)=>Boolean(el.closest(".dbf-book"))')
                    box = editor.bounding_box()
                    assert box['x'] >= 0 and box['x'] + box['width'] <= width + 1
                    assert box['y'] >= 0 and box['y'] < 1000
                    editor.locator('[data-action="close"]').click()
                    expect(editor).to_have_count(0)
                proof = os.environ.get('VTT_PROOF_DIR')
                if proof and width == 390 and language == 'de':
                    page.screenshot(path=os.path.join(proof, f'book-{chapter}-{theme}-{width}.png'), full_page=True)
            context.close()
        browser.close()


def test_frame_pager_keyboard_preserves_document_navigation(book_site):
    from playwright.sync_api import expect, sync_playwright

    _, origin, info = book_site
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = _browser_context(browser, origin, info, 1440)
        page = context.new_page()
        page.goto(origin + '/conversations')
        page.locator('[data-book-pager="next"]').focus()
        page.keyboard.press('Enter')
        expect(page.locator('.dbf-book')).to_have_attribute('data-book-chapter', 'maps')
        expect(page.locator('#app')).to_have_attribute('data-state', 'ready', timeout=60000)
        page.locator('#newEmpty').click()
        page.locator('[data-book-pager="next"]').click()
        expect(page).to_have_url(origin + '/atlas')
        expect(page.locator('[data-book-pager="next"]')).to_have_attribute('href', '/api/ce/authoring')
        page.locator('[data-book-pager="next"]').click()
        expect(page.locator('#ce-create')).to_be_visible()
        page.locator('[data-book-pager="next"]').click()
        expect(page.locator('#regelwerkArticle h2').first).to_be_visible()
        page.locator('[data-book-pager="next"]').click()
        expect(page.locator('#cpBody tr').first).to_be_visible()
        page.locator('#cpQ').fill('Feuerball')
        page.locator('#cpBody').get_by_role('link', name='Feuerball', exact=True).click()
        expect(page.locator('#cpDetailTitle')).to_have_text('Feuerball')
        context.close(); browser.close()


def test_relocated_play_chrome_and_chat_use_measured_night_pairs(book_site):
    from playwright.sync_api import expect, sync_playwright

    _, origin, info = book_site
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = _browser_context(browser, origin, info, 390)
        page = context.new_page()
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat=dm")
        expect(page.locator('#presenceRoster')).to_contain_text('action-dm')
        expect(page.locator('body > .left-toolbar')).to_be_visible()
        page.locator('#btnChatToggle').click()
        expect(page.locator('body > #window-panel-chat')).to_be_visible()
        page.locator('#chatInput').fill('Readable night chat')
        page.locator('#btnSendChat').click()
        expect(page.locator('#campaignRoomLog')).to_contain_text('Readable night chat')
        page.locator('#btnDiceWindow').click()
        page.locator('#diceInput').fill('1d20+7')
        page.locator('#btnRoll').click()
        expect(page.locator('#chatLog .chat-entry')).to_have_count(1)
        pairs = page.evaluate('''() => {
            const hex=s=>{const c=s.match(/[\\d.]+/g);return '#'+c.slice(0,3).map(v=>Math.round(+v).toString(16).padStart(2,'0')).join('')};
            const pair=(fg,bg)=>{
                const a=getComputedStyle(document.querySelector(fg)),b=getComputedStyle(document.querySelector(bg));
                return {color:hex(a.color),background:hex(b.backgroundColor),ratio:VTTDisplay.contrast(hex(a.color),hex(b.backgroundColor))};
            };
            return {chat:pair('#campaignRoomLog .chat-entry','#campaignRoomLog'),meta:pair('#chatLog .chat-meta','#chatLog'),
                    selected:pair('body > .left-toolbar .tool-btn.active','body > .left-toolbar .tool-btn.active')};
        }''')
        assert pairs['chat']['color'] == '#f8f4e9' and pairs['chat']['ratio'] >= 7, pairs
        assert pairs['meta']['ratio'] >= 4.5, pairs
        assert pairs['selected']['background'] == '#5e4a8c' and pairs['selected']['ratio'] >= 4.5, pairs
        context.close(); browser.close()


def test_night_palette_and_editor_canvas_remain_independent(book_site):
    from playwright.sync_api import expect, sync_playwright

    _, origin, info = book_site
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = _browser_context(browser, origin, info, 1440, theme='paper')
        page = context.new_page(); page.goto(origin + '/mapmaker')
        expect(page.locator('#app')).to_have_attribute('data-state', 'ready', timeout=60000)
        page.locator('#newEmpty').click()
        before = page.locator('#mapCanvas').evaluate('''el => ({
            width:el.width,height:el.height,rect:JSON.stringify(el.getBoundingClientRect().toJSON()),
            sample:Array.from(el.getContext('2d').getImageData(0,0,1,1).data)
        })''')
        page.evaluate("VTTDisplay.update({theme:'night'})")
        after = page.locator('#mapCanvas').evaluate('''el => ({
            width:el.width,height:el.height,rect:JSON.stringify(el.getBoundingClientRect().toJSON()),
            sample:Array.from(el.getContext('2d').getImageData(0,0,1,1).data)
        })''')
        assert before == after
        colors = page.evaluate('''() => {
            const s=getComputedStyle(document.documentElement);
            return Object.fromEntries(['--ui-paper','--ui-ink','--ui-action-bg','--ui-action-text','--ui-accent']
                .map(k=>[k,s.getPropertyValue(k).trim()]));
        }''')
        assert colors == {'--ui-paper': '#1c1c1c', '--ui-ink': '#f8f4e9',
                          '--ui-action-bg': '#5e4a8c', '--ui-action-text': '#f8f4e9', '--ui-accent': '#ab9fbb'}
        context.close(); browser.close()
