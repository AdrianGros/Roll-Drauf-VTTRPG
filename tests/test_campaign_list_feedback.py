"""Large authorized campaign lists remain navigable without dropping entries."""
from threading import Thread

import pytest
from werkzeug.serving import make_server

from tests.test_character_campaign_feedback import feedback_app  # noqa: F401
from tests.test_balu_navigation import QuietHandler
from vtt.extensions import db
from vtt.models import Campaign


@pytest.fixture
def campaign_list_site(feedback_app):
    app, info = feedback_app
    with app.app_context():
        for index in range(48):
            db.session.add(Campaign(name=f'Runde {index:02}', description=f'Abenteuer Nummer {index:02}', owner_id=info['users']['dm']))
        db.session.commit()
    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
    thread = Thread(target=server.serve_forever,daemon=True); thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', info['tokens']['dm']
    finally:
        server.shutdown(); thread.join(timeout=5); server.server_close()


@pytest.mark.parametrize('engine',['chromium','firefox'])
def test_fifty_campaigns_search_page_and_keep_navigation(campaign_list_site, engine):
    from playwright.sync_api import sync_playwright, expect
    origin,token = campaign_list_site
    with sync_playwright() as p:
        browser = getattr(p,engine).launch(headless=True,**({'args':['--no-sandbox']} if engine=='chromium' else {}))
        context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        context.add_cookies([{'name':'access_token_cookie','value':token,'url':origin,'httpOnly':True}])
        page=context.new_page(); page.set_default_timeout(15000)
        errors=[]; page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(origin+'/campaigns')
        visible=page.locator('[data-campaign-list] [data-testid="campaign-ledger-item"]:visible')
        expect(visible).to_have_count(5)
        expect(page.locator('[data-campaign-count]')).to_have_text('1–5 von 50 Kampagnen')
        first=visible.first.text_content()
        page.locator('[data-campaign-next]').click()
        expect(page.locator('[data-campaign-count]')).to_have_text('6–10 von 50 Kampagnen')
        assert visible.first.text_content()!=first
        page.locator('[data-campaign-prev]').click()
        assert visible.first.text_content()==first
        search=page.get_by_role('searchbox',name='Kampagnen suchen')
        search.fill('Runde 47')
        expect(visible).to_have_count(1); expect(visible).to_contain_text('Runde 47')
        expect(page.locator('[data-campaign-prev]')).to_be_disabled()
        expect(page.locator('[data-campaign-next]')).to_be_disabled()
        expect(visible.get_by_role('button',name='Gruppenübersicht')).to_have_attribute('data-dashboard-href',__import__('re').compile(r'^/party\?campaign=\d+$'))
        search.fill('Kein Treffer hier'); expect(visible).to_have_count(0)
        expect(page.locator('[data-campaign-count]')).to_have_text('Keine passende Kampagne')
        search.fill(''); expect(visible).to_have_count(5)
        logout=page.get_by_role('button',name='Abmelden',exact=True)
        expect(logout).to_be_visible(); assert logout.bounding_box()['height']>=32
        assert errors==[],errors
        browser.close()
