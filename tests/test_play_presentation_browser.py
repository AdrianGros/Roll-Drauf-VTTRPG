"""Play table chrome stays readable in paper and night for the real DM and Player compositions.

Contrast is measured in a real browser with the alpha-composition helper shared with the C01
navigation tests: every text color is composited over the actually painted ancestor backgrounds
(including translucent layers and gradient stops). Canvas, grid and SVG pixels are not measured.
"""
import re
import pytest
from tests.test_personal_actions_browser import action_site  # noqa:F401
from tests.test_presentation_browser import contrast, preferences

PANEL_TEXT = '.tab-panel.active :is(h1,h2,h3,h4,label,legend,summary,p,small,.muted,dt,dd,th,td)'
PANEL_BUTTONS = '.tab-panel.active button'
TOOLBAR = '.left-toolbar .tool-btn, .left-toolbar .tool-btn .tool-label'


def visible(page, selector):
    return page.locator(selector).evaluate_all('nodes=>nodes.filter(n=>n.getClientRects().length&&!n.disabled).length')


def check_if_present(page, selector):
    if visible(page, selector):
        contrast(page, selector)


def open_sidebar(page):
    from playwright.sync_api import expect
    sidebar = page.locator('.right-sidebar')
    if 'is-open' not in (sidebar.get_attribute('class') or ''):
        page.locator('#btnSidebarToggle').click()
    expect(sidebar).to_have_class(re.compile(r'is-open'))


def check_every_sidebar_tab(page):
    """Each reachable tab's actual panels, labels and controls; returns how many tabs were measured."""
    tabs = page.locator('.sidebar-tab[data-tab]').evaluate_all(
        'nodes=>nodes.filter(n=>n.getClientRects().length).map(n=>n.dataset.tab)')
    assert tabs
    for tab in tabs:
        page.locator(f'.sidebar-tab[data-tab="{tab}"]').click()
        check_if_present(page, PANEL_TEXT)
        check_if_present(page, PANEL_BUTTONS)
        # The tab strip itself: selected tab (plum) and the unselected ones.
        contrast(page, '.sidebar-tab')
    return len(tabs)


@pytest.mark.parametrize('role,theme,language', [
    ('dm', 'paper', 'de'), ('dm', 'night', 'en'),
    ('player', 'paper', 'de'), ('player', 'night', 'en')])
def test_play_chrome_text_contrasts_with_its_painted_surface(action_site, role, theme, language):
    from playwright.sync_api import sync_playwright, expect
    app, origin, info = action_site
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        preferences(context, theme=theme, language=language)
        context.add_cookies([{'name': 'access_token_cookie', 'value': info[f'{role}_auth'], 'url': origin, 'httpOnly': True}])
        page = context.new_page()
        page.set_default_timeout(30000)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat={role}")
        expect(page.locator('html')).to_have_attribute('data-vtt-theme', theme)
        expect(page.locator('#presenceRoster')).to_be_visible()

        # Toolbar at rest.
        contrast(page, TOOLBAR)
        # Selected tool: this is the plum surface that used to carry dark text in night.
        for tool in ('measure', 'pan'):
            button = page.locator(f'.left-toolbar [data-tool="{tool}"]')
            button.click()
            expect(button).to_have_class(re.compile(r'active'))
            contrast(page, f'.left-toolbar [data-tool="{tool}"], .left-toolbar [data-tool="{tool}"] .tool-label')
            # Hover/focus keep a readable plum surface as well.
            button.hover()
            contrast(page, f'.left-toolbar [data-tool="{tool}"]')
        page.mouse.move(700, 500)

        open_sidebar(page)
        assert check_every_sidebar_tab(page) >= 1

        if role == 'dm':
            # Actual map-scale labels (paper default used dark brown on navy).
            page.locator('.sidebar-tab[data-tab="session"]').click()
            expect(page.locator('#mapScaleMeters')).to_be_visible()
            # Exercise the actual displayed value (typed only, no save and no API call).
            page.locator('#mapScaleMeters').fill('1.5')
            expect(page.locator('#mapScaleMeters')).to_have_value('1.5')
            contrast(page, '#mapScalePanel h2, #mapScalePanel p, #mapScalePanel label, #mapScalePanel label span, '
                           '#mapScalePanel button, #mapScalePanel input')
            # Existing inline declarations (and the book skin's !important .muted rule) must not win.
            page.evaluate('''()=>{const panel=document.querySelector('#mapScalePanel');
              const probe=document.createElement('p');probe.id='contrastProbe';probe.className='muted';
              probe.setAttribute('style','color:#342b25');probe.textContent='probe';panel.appendChild(probe);}''')
            contrast(page, '#contrastProbe')
        else:
            expect(page.locator('#mapScalePanel')).to_have_count(0)

        # Primary controls inside the sidebar (token and other plum buttons) at rest and hovered.
        page.locator('.sidebar-tab[data-tab]').first.click()
        buttons = page.locator('.tab-panel.active button:visible:not([disabled])')
        if buttons.count():
            buttons.first.hover()
            contrast(page, '.tab-panel.active button')
        assert not errors, errors
        browser.close()


def test_play_chrome_does_not_recolor_canvas_or_map_layers(action_site):
    """The fix is chrome-only: the map surface keeps the colors its own document paints."""
    from playwright.sync_api import sync_playwright, expect
    app, origin, info = action_site
    colors = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        for theme in ('paper', 'night'):
            context = browser.new_context(viewport={'width': 1440, 'height': 1000})
            preferences(context, theme=theme)
            context.add_cookies([{'name': 'access_token_cookie', 'value': info['player_auth'], 'url': origin, 'httpOnly': True}])
            page = context.new_page()
            page.set_default_timeout(30000)
            page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat=player")
            expect(page.locator('#mapWorld')).to_be_visible()
            colors[theme] = page.evaluate('''()=>{const s=n=>n?getComputedStyle(n):null;
              const pick=n=>n?{bg:s(n).backgroundColor,image:s(n).backgroundImage}:null;
              return {world:pick(document.querySelector('#mapWorld')),viewport:pick(document.querySelector('.map-viewport'))};}''')
            context.close()
        browser.close()
    # The map world and viewport must be theme independent (only chrome tokens are re-bound).
    assert colors['paper'] == colors['night'], colors
