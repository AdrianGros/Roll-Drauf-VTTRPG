"""VD slice 1: real dashboard entry, book material and guarded navigation."""

import json
import os
from pathlib import Path

import pytest
from flask import render_template
from flask_jwt_extended import create_access_token, decode_token
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vtt.auth import auth_bp
from vtt.endpoints.dashboard_home import dashboard_home_bp
from vtt.extensions import db
from vtt.models import User
from vtt.creation_engine.store.models import CeDraft, CeWorkspace
from vtt.creation_engine.content import new_id

from test_ce_authoring_transports import (
    author, authoring_engine, browser, migration_engine, postgres_engine,
    read, transport, wait_version,
)

pytestmark = pytest.mark.postgres


@pytest.fixture(autouse=True)
def dashboard_routes(transport):
    """Real home/auth endpoints and page, sharing the isolated CE database."""
    app, _, _, _, _, context = transport
    app.config['SQLALCHEMY_DATABASE_URI'] = context['gateway'].store.engine.url.render_as_string(hide_password=False)
    db.init_app(app)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(dashboard_home_bp)
    app.add_url_rule('/dashboard', 'dashboard', lambda: render_template('dashboard.html'))
    yield
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.mark.parametrize('state', ['enabled', 'flag_off', 'no_host', 'no_authoring', 'suspended', 'inactive', 'pending_account', 'view_as'])
def test_dashboard_authoring_capability_is_private_and_does_not_create_content(transport, state):
    app, _, client, _, _, context = transport
    engine = context['gateway'].store.engine
    if state == 'flag_off':
        app.config['CE_AUTHORING'] = False
    elif state == 'no_host':
        app.extensions.pop('ce_gateway')
    elif state == 'no_authoring':
        app.extensions['ce_gateway'] = object()
    elif state in {'suspended', 'inactive', 'pending_account'}:
        with Session(engine) as session, session.begin():
            user = session.get(User, context['principal'])
            if state == 'suspended': user.is_suspended = True
            elif state == 'inactive': user.is_active = False
            else: user.account_state = 'pending'
    headers = {'X-CE-View-As': 'view:test'} if state == 'view_as' else {}
    with Session(engine) as session:
        before = [session.scalar(select(func.count()).select_from(model)) for model in (CeWorkspace, CeDraft)]
    response = client.get('/api/dashboard/home', headers=headers)
    if state == 'inactive':
        assert response.status_code == 404
    else:
        assert response.status_code == 200
        assert response.json['home_state']['authoring_available'] is (state == 'enabled')
        assert response.headers['Cache-Control'] == 'private, no-store'
        assert 'X-CE-View-As' in response.headers['Vary']
        assert response.json['primary_action']['href'] != '/api/ce/authoring'
    with Session(engine) as session:
        assert before == [session.scalar(select(func.count()).select_from(model)) for model in (CeWorkspace, CeDraft)]
    assert app.test_client().get('/api/dashboard/home').status_code == 401
    if state in {'flag_off', 'suspended', 'inactive', 'pending_account', 'view_as'}:
        assert client.get('/api/ce/authoring', headers=headers).status_code in {403, 404}


def test_browser_dashboard_entry_and_keyboard_return_preserve_unsaved_input(browser, transport):
    page, context = browser
    page.goto(page.url.split('/api/')[0] + '/dashboard')
    entry = page.get_by_test_id('authoring-entry')
    entry.wait_for(state='visible')
    assert entry.count() == 1
    assert read(context)['draftVersion'] == 1
    entry.focus(); page.keyboard.press('Enter')
    page.wait_for_url('**/api/ce/authoring')
    page.locator('#draft-info').get_by_text('Version 1').wait_for()
    assert page.get_by_role('navigation', name='Buchnavigation').count() == 1
    assert page.locator('[aria-current="page"]').count() == 1
    page.locator('#mode').select_option('structured')
    field = page.locator('form[data-question="item.name"] textarea')
    field.fill('Mein eigener Gegenstand')
    home = page.get_by_role('link', name='Übersicht', exact=True)
    home.focus(); page.keyboard.press('Enter')
    assert page.url.endswith('/api/ce/authoring')
    assert field.input_value() == 'Mein eigener Gegenstand'
    assert page.locator('#status').inner_text().startswith('Speichere oder verwerfe')
    page.locator('form[data-question="item.name"] button[type="submit"]').click()
    wait_version(page, 2)
    assert 'Mein eigener Gegenstand' in page.locator('#draft-info').inner_text()
    home.focus(); page.keyboard.press('Enter')
    page.wait_for_url('**/dashboard')
    page.get_by_test_id('authoring-entry').wait_for(state='visible')
    assert read(context)['content']['name'] == 'Mein eigener Gegenstand'
    transport[0].config['CE_AUTHORING'] = False
    page.reload()
    page.locator('#dashboardSceneStatus').wait_for(state='hidden')
    assert page.get_by_test_id('authoring-entry').count() == 0


def test_browser_pending_retry_blocks_navigation_without_a_second_command(browser):
    page, context = browser
    page.locator('#mode').select_option('structured')
    page.locator('form[data-question="item.name"] textarea').fill('Uncertain response')
    commands = []

    def lose_reply(route):
        commands.append(route.request.post_data_json)
        if len(commands) == 1:
            route.fetch()
            route.abort('failed')
        else:
            route.continue_()

    page.route('**/api/ce/commands', lose_reply)
    page.locator('form[data-question="item.name"] button[type="submit"]').click()
    page.locator('#retry').wait_for(state='visible')
    page.wait_for_function("!document.getElementById('retry').disabled")
    page.get_by_role('link', name='Übersicht', exact=True).click(force=True)
    assert page.url.endswith('/api/ce/authoring')
    assert len(commands) == 1
    page.locator('#retry').click(); wait_version(page, 2)
    assert len(commands) == 2 and commands[0] == commands[1]
    assert read(context)['draftVersion'] == 2
    assert page.get_by_role('link', name='Übersicht', exact=True).get_attribute('aria-disabled') is None


def test_browser_empty_workspace_needs_explicit_draft_creation(browser, transport):
    page, context = browser
    app = transport[0]
    with Session(context['gateway'].store.engine) as session, session.begin():
        user = User(username=new_id('author'), email=new_id('mail') + '@example.test', password_hash='x', role_id=1,
                    is_active=True, is_suspended=False, account_state='active')
        session.add(user); session.flush(); user_id = user.id
    with app.app_context():
        token = create_access_token(identity=str(user_id))
        csrf = decode_token(token)['csrf']
    origin = page.url.split('/api/')[0]
    page.context.add_cookies([{'name': 'access_token_cookie', 'value': token, 'url': origin, 'httpOnly': True},
                             {'name': 'csrf_access_token', 'value': csrf, 'url': origin}])
    page.goto(origin + '/api/ce/authoring')
    page.get_by_text('Erstelle einen Gegenstand oder öffne einen Entwurf.', exact=True).wait_for()
    assert page.locator('#editor').is_hidden()
    workspace = app.extensions['ce_gateway'].authoring.workspace(user_id)
    assert workspace['drafts'] == []
    page.reload()
    page.get_by_text('Erstelle einen Gegenstand oder öffne einen Entwurf.', exact=True).wait_for()
    assert app.extensions['ce_gateway'].authoring.workspace(user_id)['drafts'] == []
    page.locator('#new').click(); wait_version(page, 1)
    assert len(app.extensions['ce_gateway'].authoring.workspace(user_id)['drafts']) == 1


def test_browser_book_layout_locales_and_reduced_motion(browser, tmp_path):
    page, _ = browser
    artifact = Path(os.environ.get('CE_TEST_ARTIFACT_DIR', tmp_path))
    artifact.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(artifact / 'editor-guided-desktop.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path=str(artifact / 'editor-guided-phone.png'), full_page=True)
    page.locator('#damage-preset').click(); page.locator('#apply-preset').click(); wait_version(page, 2)
    page.locator('#mode').select_option('structured')
    page.emulate_media(reduced_motion='reduce')
    measurements = []
    for locale in ['de', 'en', 'fr']:
        page.locator('#locale').select_option(locale)
        page.wait_for_function("!document.getElementById('locale').disabled")
        for width in [320, 390, 1199, 1200, 1201, 1280]:
            page.set_viewport_size({'width': width, 'height': 960})
            result = page.evaluate("""() => {
              const style = n => getComputedStyle(n), body = style(document.body);
              const q = document.querySelector('#questions').getBoundingClientRect();
              const preview = document.querySelector('aside').getBoundingClientRect();
              const hiddenControls = [...document.querySelectorAll('button, input, select, textarea')]
                .filter(n => n.getClientRects().length && !n.closest('details:not([open])'))
                .filter(n => {const b = n.getBoundingClientRect(); return b.left < -1 || b.right > innerWidth + 1;})
                .map(n => n.id || n.tagName);
              return {width: innerWidth, scroll: document.documentElement.scrollWidth,
                columns: style(document.querySelector('.columns')).gridTemplateColumns.split(' ').length,
                hiddenControls, background: body.backgroundColor, color: body.color,
                font: body.fontFamily, inputFont: style(document.querySelector('textarea')).fontFamily,
                transition: style(document.querySelector('[data-ce-nav]')).transitionDuration,
                previewBelow: preview.top >= q.bottom,
                lang: document.documentElement.lang};
            }""")
            measurements.append(result)
            assert result['scroll'] <= width + 1, result
            assert result['hiddenControls'] == [], result
            assert result['columns'] == (2 if width >= 1200 else 1), result
            assert result['previewBelow'] is (width < 1200), result
            assert result['background'] == 'rgb(248, 243, 233)' and result['color'] == 'rgb(58, 50, 44)'
            assert 'Segoe UI' in result['inputFont']
            assert result['transition'] == '0s' and result['lang'] == locale
    page.locator('#locale').select_option('de')
    page.wait_for_function("!document.getElementById('locale').disabled")
    page.screenshot(path=str(artifact / 'editor-book-desktop.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path=str(artifact / 'editor-book-phone.png'), full_page=True)
    (artifact / 'layout-measurements.json').write_text(json.dumps(measurements, indent=2) + '\n')
    page.locator('#claim').select_option('runtime_ready')
    contrast = page.evaluate("""() => {
      const rgb = value => value.match(/[\\d.]+/g).slice(0, 3).map(Number);
      const light = value => rgb(value).map(x => {x /= 255; return x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4;})
        .reduce((sum, x, i) => sum + x * [.2126, .7152, .0722][i], 0);
      return ['.help', '[data-ce-nav]', 'button[type="submit"]', '#commit:disabled', '.ready', 'textarea'].map(selector => {
        const node = document.querySelector(selector); let ancestor = node, background;
        while (ancestor) {
          background = getComputedStyle(ancestor).backgroundColor;
          if (background !== 'rgba(0, 0, 0, 0)' && background !== 'transparent') break;
          ancestor = ancestor.parentElement;
        }
        const foreground = getComputedStyle(node).color, a = light(foreground), b = light(background);
        return {selector, foreground, background, ratio: (Math.max(a, b) + .05) / (Math.min(a, b) + .05)};
      });
    }""")
    assert all(item['ratio'] >= 4.5 for item in contrast), contrast
    (artifact / 'text-contrast.json').write_text(json.dumps(contrast, indent=2) + '\n')
