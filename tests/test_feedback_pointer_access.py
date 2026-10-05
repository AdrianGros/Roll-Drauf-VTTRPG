"""Use real pointer interactions to catch book layers covering working controls."""
from threading import Thread

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.serving import make_server, WSGIRequestHandler

from vtt import create_app
from vtt.config import TestingConfig
from vtt.extensions import db
from vtt.models import Role, User


class QuietHandler(WSGIRequestHandler):
    def log(self, *args):
        pass


@pytest.fixture
def pointer_site(tmp_path, monkeypatch):
    # Separate SQLite connections avoid concurrent browser requests sharing an
    # in-memory connection. No production DB, credentials or account writes.
    monkeypatch.setattr(TestingConfig, 'SQLALCHEMY_DATABASE_URI', f'sqlite:///{tmp_path}/test.db')
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        role = Role(name='Player')
        db.session.add(role); db.session.flush()
        user = User(username='pointer-test', email='pointer@example.test',
                    password_hash='test', role_id=role.id, is_active=True,
                    is_suspended=False, account_state='active')
        db.session.add(user); db.session.commit()
        token = create_access_token(identity=str(user.id))
    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', token
    finally:
        server.shutdown(); thread.join(timeout=5); server.server_close()
        with app.app_context():
            db.session.remove(); db.engine.dispose()


@pytest.fixture(params=[(1440, 'reduce'), (1440, 'no-preference'),
                        (390, 'reduce'), (390, 'no-preference')])
def pointer_browser(request):
    from playwright.sync_api import sync_playwright
    width, motion = request.param
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': width, 'height': 1000 if width == 1440 else 844},
                                      reduced_motion=motion, has_touch=width == 390)
        page = context.new_page(); page.set_default_timeout(8000)
        yield page, width
        browser.close()


def press(locator, width):
    if width == 390:
        locator.tap()
    else:
        locator.click()


def test_character_creation_and_cancel_receive_pointer_input(pointer_site, pointer_browser):
    from playwright.sync_api import expect
    origin, token = pointer_site
    page, width = pointer_browser
    page.context.add_cookies([{'name': 'access_token_cookie', 'value': token, 'url': origin, 'httpOnly': True}])
    page.goto(origin + '/characters')
    press(page.get_by_role('button', name='Held anlegen', exact=True), width)
    expect(page.locator('#charModal')).to_be_visible()
    press(page.get_by_role('button', name='Held anlegen schließen'), width)
    expect(page.locator('#charModal')).to_be_hidden()
    press(page.get_by_role('button', name='Held anlegen', exact=True), width)
    page.locator('#charName').fill('Pointer hero')
    for selector in ['#charRace', '#charFaction', '#charClass', '#charBackground']:
        page.locator(selector).select_option(index=1)
    press(page.locator('#nextBtn'), width)
    expect(page.locator('#step2')).to_be_visible()
    press(page.locator('#nextBtn'), width)
    expect(page.locator('#step3')).to_be_visible()
    with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/characters')) as created:
        press(page.locator('#submitBtn'), width)
    assert created.value.status == 201
    expect(page.locator('#charModal')).to_be_hidden()
    expect(page.get_by_text('Pointer hero', exact=True).and_(page.locator(':visible')).first).to_be_visible()


def test_discord_community_links_receive_pointer_input(pointer_site, pointer_browser):
    from playwright.sync_api import expect
    origin, _ = pointer_site
    page, width = pointer_browser
    # Prove navigation without joining a server or relying on an external page.
    page.context.route('https://discord.gg/**', lambda route: route.fulfill(body='Discord invitation destination'))
    page.goto(origin + '/login.html')
    press(page.locator('.book-cover'), width)
    expect(page.locator('#loginUsername')).to_be_visible()
    with page.expect_popup() as popup:
        press(page.locator('.login-discord-join'), width)
    popup.value.wait_for_load_state()
    assert popup.value.url == 'https://discord.gg/rolldrauf'
    expect(popup.value.locator('body')).to_have_text('Discord invitation destination')
    assert page.locator('#loginUsername').is_editable()
