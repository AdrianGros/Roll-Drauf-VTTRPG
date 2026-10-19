"""Current authorization in an already-open editor, including delayed responses."""

from dataclasses import replace
from datetime import datetime, timezone
import os
from pathlib import Path
from urllib.parse import quote

import pytest
from flask_jwt_extended import create_access_token, decode_token
from sqlalchemy.orm import Session

from vtt.creation_engine.content import new_id
from vtt.creation_engine.policy import Grant
from vtt.creation_engine.store.models import CeDefinition, CeRevision
from vtt.models import User

from test_ce_authoring_transports import (
    author, authoring_engine, browser, migration_engine, postgres_engine,
    read, transport, wait_version,
)
from test_ce_editor_states import form, press, switch

expect = pytest.importorskip('playwright.sync_api').expect
pytestmark = pytest.mark.postgres


def suspend(context, value=True):
    with Session(context['gateway'].store.engine) as session, session.begin():
        session.get(User, context['principal']).is_suspended = value


def check_access(page):
    # Exercise the normal return-to-window listener, without reaching into app state.
    page.evaluate("window.dispatchEvent(new Event('focus'))")


def assert_cleared(page, *private_values):
    expect(page.locator('#access-notice')).to_be_visible()
    expect(page.locator('#access-heading')).to_be_focused()
    assert page.locator('#editor').is_hidden() and page.locator('#conflict').is_hidden()
    assert page.locator('#retry').is_hidden() and page.locator('#discard').is_hidden()
    assert page.locator('#new').is_disabled()
    assert page.locator('#questions').inner_html() == ''
    assert page.locator('#drafts option, #sb-item option, #sb-target option, #sb-select option, #sb-revisions input').count() == 0
    assert page.locator('#content, #history, #revision, #preset-values, #conflict-local, #conflict-current, #sb-decisions').all_text_contents() == [''] * 7
    dom_and_values = page.evaluate("document.documentElement.outerHTML + [...document.querySelectorAll('input, textarea, select')].map(n => n.value).join('|')")
    for value in private_values:
        assert value not in dom_and_values
    assert page.locator('[data-ce-nav][aria-disabled]').count() == 0


def hold_response(page, path, method='GET'):
    # Hold a response AFTER fetch resolves, so AbortController alone cannot pass
    # the stale-response test. The app must also reject its old authorization epoch.
    page.evaluate("""({path, method}) => {
      const original = window.fetch;
      window.heldResponses = [];
      window.fetch = async (url, options = {}) => {
        const response = await original(url, options);
        if (String(url).includes(path) && (options.method || 'GET') === method) {
          return await new Promise(resolve => window.heldResponses.push(() => resolve(response)));
        }
        return response;
      };
    }""", {'path': path, 'method': method})


def release_responses(page):
    page.evaluate("window.heldResponses.splice(0).forEach(release => release())")


@pytest.mark.parametrize('transport', ['damage-native'], indirect=True)
@pytest.mark.parametrize('denial', ['suspended', 'signed_out', 'flag_off', 'view_as'])
def test_browser_access_loss_clears_all_protected_surfaces_and_can_reopen(browser, transport, denial, tmp_path):
    page, context = browser
    switch(page, 'locale', {'suspended': 'de', 'signed_out': 'en', 'flag_off': 'fr', 'view_as': 'en'}[denial])
    switch(page, 'mode', 'structured')
    switch(page, 'sb-select', context['scope'])
    expect(page.locator('#sb-item option')).to_have_count(2)
    press(page, '#damage-preset')
    expect(page.locator('#preset')).to_be_visible()
    form(page, 'item.name').locator('textarea').fill('PRIVATE UNSAVED NAME')
    cookies = page.context.cookies()
    before = read(context)['draftVersion']
    if denial == 'suspended': suspend(context)
    elif denial == 'signed_out': page.context.clear_cookies()
    elif denial == 'flag_off': transport[0].config['CE_AUTHORING'] = False
    else: page.context.set_extra_http_headers({'X-CE-View-As': 'view:test'})
    check_access(page)
    assert_cleared(page, 'PRIVATE UNSAVED NAME', context['draft'], context['scope'], context['item'], context['target'])
    artifact = Path(os.environ.get('CE_TEST_ARTIFACT_DIR', tmp_path)); artifact.mkdir(parents=True, exist_ok=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(artifact / f'access-{denial}-phone.png'), full_page=True)
    if denial == 'suspended': suspend(context, False)
    elif denial == 'signed_out': page.context.add_cookies(cookies)
    elif denial == 'flag_off': transport[0].config['CE_AUTHORING'] = True
    else: page.context.set_extra_http_headers({})
    # Focus starts on the unavailable heading; normal Tab reaches the recovery action.
    page.keyboard.press('Tab'); expect(page.locator('#check-access')).to_be_focused()
    page.keyboard.press('Enter'); wait_version(page, before)
    expect(page.locator('#access-notice')).to_be_hidden()
    assert read(context)['draftVersion'] == before
    assert form(page, 'item.name').locator('textarea').input_value() != 'PRIVATE UNSAVED NAME'
    assert page.locator('#preset').is_hidden() and page.locator('#sb-scope').is_hidden()


def test_browser_periodic_check_detects_suspension_without_a_user_action(browser):
    page, context = browser
    page.clock.install()
    page.reload(); wait_version(page, 1)
    suspend(context)
    page.clock.fast_forward(15000)
    assert_cleared(page, context['draft'])


def test_browser_delayed_preset_cannot_restore_content_after_denial_or_recovery(browser):
    page, context = browser
    hold_response(page, '/presets/')
    press(page, '#damage-preset')
    page.wait_for_function('window.heldResponses.length === 1')
    suspend(context); check_access(page)
    assert_cleared(page, context['draft'])
    suspend(context, False)
    press(page, '#check-access'); wait_version(page, 1)
    release_responses(page)
    expect(page.locator('#preset')).to_be_hidden()
    assert page.locator('#preset-values').inner_html() == ''
    assert read(context)['draftVersion'] == 1 and page.locator('#mode').is_enabled()


def test_browser_delayed_committed_save_is_not_replayed_after_access_recovery(browser):
    page, context = browser
    switch(page, 'mode', 'structured')
    commands = []
    page.on('request', lambda request: commands.append(request.post_data_json) if request.url.endswith('/api/ce/commands') else None)
    form(page, 'item.name').locator('textarea').fill('Committed before access loss')
    hold_response(page, '/api/ce/commands', 'POST')
    press(page, 'form[data-question="item.name"] button[type="submit"]')
    page.wait_for_function('window.heldResponses.length === 1')
    assert read(context)['draftVersion'] == 2
    suspend(context); check_access(page)
    assert_cleared(page, 'Committed before access loss', context['draft'])
    expect(page.locator('#access-outcome')).to_be_visible()
    suspend(context, False)
    press(page, '#check-access'); wait_version(page, 2)
    release_responses(page)
    assert len(commands) == 1 and read(context)['draftVersion'] == 2
    assert 'Committed before access loss' in page.locator('#draft-info').inner_text()
    assert page.locator('#retry').is_hidden()


def test_browser_connection_check_failure_retains_dirty_input_and_keyboard_recovery(browser):
    page, context = browser
    switch(page, 'mode', 'structured')
    field = form(page, 'item.name').locator('textarea')
    field.fill('Retain on network failure')
    page.route('**/authoring/workspace', lambda route: route.abort('failed'))
    check_access(page)
    expect(page.locator('#access-explanation')).to_contain_text('pausiert')
    assert field.input_value() == 'Retain on network failure' and field.is_disabled()
    assert page.locator('#editor').is_visible() and read(context)['draftVersion'] == 1
    page.get_by_role('link', name='Anmelden', exact=True).focus(); page.keyboard.press('Enter')
    assert page.url.endswith('/api/ce/authoring') and field.input_value() == 'Retain on network failure'
    page.unroute('**/authoring/workspace')
    press(page, '#check-access')
    expect(field).to_be_focused()
    assert field.input_value() == 'Retain on network failure' and field.is_enabled()
    press(page, 'form[data-question="item.name"] button[type="submit"]'); wait_version(page, 2)
    assert read(context)['content']['name'] == 'Retain on network failure'


def test_browser_connection_check_does_not_replace_an_unknown_command(browser):
    page, context = browser
    switch(page, 'mode', 'structured')
    form(page, 'item.name').locator('textarea').fill('One saved command')
    commands = []
    def lose_reply(route):
        commands.append(route.request.post_data_json)
        if len(commands) == 1:
            route.fetch(); route.abort('failed')
        else: route.continue_()
    page.route('**/api/ce/commands', lose_reply)
    press(page, 'form[data-question="item.name"] button[type="submit"]')
    expect(page.locator('#retry')).to_be_enabled()
    page.route('**/authoring/workspace', lambda route: route.abort('failed'))
    check_access(page)
    expect(page.locator('#access-notice')).to_be_visible()
    expect(page.locator('#retry')).to_be_disabled()
    page.unroute('**/authoring/workspace')
    press(page, '#check-access'); expect(page.locator('#retry')).to_be_focused()
    assert len(commands) == 1
    press(page, '#retry'); wait_version(page, 2)
    assert commands[0] == commands[1] and read(context)['draftVersion'] == 2


def revoke_read(context, instance):
    gateway = context['gateway']
    with gateway.store.transaction(context['scope']) as tx:
        policy = gateway.policy.policies(tx).policies[instance]
        gateway.policy.replace(tx, gateway.kernel, context['principal'],
            replace(policy, denies=(Grant('read', principals=(context['principal'],)),)),
            expected_version=tx.scope.policy_version, reason='Isolated browser revocation fixture')


@pytest.mark.parametrize('transport', ['damage-native'], indirect=True)
def test_browser_new_projection_removes_revoked_copy_and_ignores_older_response(browser):
    page, context = browser
    switch(page, 'sb-select', context['scope'])
    switch(page, 'sb-item', context['item'])
    hold_response(page, '/sandboxes/' + quote(context['scope'], safe=''))
    press(page, '#sb-refresh')
    page.wait_for_function('window.heldResponses.length === 1')
    # The wrapper holds both responses. Release the newer projection first.
    revoke_read(context, context['item']); check_access(page)
    page.wait_for_function('window.heldResponses.length === 2')
    page.evaluate('window.heldResponses.pop()()')
    expect(page.locator(f'[data-instance="{context["item"]}"]')).to_have_count(0)
    release_responses(page)
    expect(page.locator('#sb-refresh')).to_be_enabled()
    assert context['item'] not in page.locator('#sandbox').inner_html()
    assert page.locator('#sb-item').input_value() == '' and page.locator('#sb-hit').is_disabled()
    assert page.locator('#access-notice').is_hidden()


@pytest.mark.parametrize('transport', ['damage-native'], indirect=True)
def test_browser_revoked_decision_disappears_and_focus_returns_to_sandbox_status(browser):
    page, context = browser
    switch(page, 'sb-select', context['scope'])
    switch(page, 'sb-item', context['item']); switch(page, 'sb-target', context['target'])
    press(page, '#sb-hit')
    expect(page.locator('#sb-decisions button').first).to_be_focused()
    revoke_read(context, context['target']); check_access(page)
    expect(page.locator('#sb-decisions button')).to_have_count(0)
    expect(page.locator('#sb-state')).to_be_focused()
    assert context['target'] not in page.locator('#sandbox').inner_html()
    assert page.locator('#sb-target').input_value() == ''
    assert context['gateway'].kernel.random.draws == 0


def test_browser_changed_signed_in_identity_needs_explicit_fresh_reads(browser, transport):
    page, context = browser
    switch(page, 'mode', 'structured')
    form(page, 'item.name').locator('textarea').fill('Previous account input')
    app = transport[0]
    with Session(context['gateway'].store.engine) as session, session.begin():
        user = User(username=new_id('author'), email=new_id('mail') + '@example.test', password_hash='x', role_id=1,
                    is_active=True, is_suspended=False, account_state='active')
        session.add(user); session.flush(); user_id = user.id
    with app.app_context():
        token = create_access_token(identity=str(user_id)); csrf = decode_token(token)['csrf']
    origin = page.url.split('/api/')[0]
    page.context.add_cookies([{'name': 'access_token_cookie', 'value': token, 'url': origin, 'httpOnly': True},
                             {'name': 'csrf_access_token', 'value': csrf, 'url': origin}])
    check_access(page)
    assert_cleared(page, 'Previous account input', context['draft'])
    press(page, '#check-access')
    expect(page.locator('#new')).to_be_enabled()
    assert page.locator('#drafts option').count() == 0 and page.locator('#editor').is_hidden()
    assert context['service'].workspace(user_id)['drafts'] == []


@pytest.mark.parametrize('transport', ['damage-native'], indirect=True)
def test_browser_checks_refresh_runtime_availability_and_revision_choices(browser, transport):
    page, context = browser
    switch(page, 'sb-select', context['scope'])
    switch(page, 'sb-item', context['item']); switch(page, 'sb-target', context['target'])
    actor_id, item_id = context['actorRevision']['id'], context['revision']['id']
    actor_choice = page.locator(f'#sb-revisions input[value="{actor_id}"]')
    actor_choice.check()
    assert page.locator('#sb-hit').is_enabled()
    version = read(context)['draftVersion']
    transport[0].config['CE_RUNTIME'] = False
    check_access(page)
    expect(page.locator('#sb-disabled')).to_be_visible()
    expect(page.locator('#sb-hit')).to_be_disabled()
    assert actor_choice.is_checked() and actor_choice.is_disabled()
    assert page.locator('#new').is_enabled() and page.locator('#access-notice').is_hidden()
    expect(page.locator('#check-access')).to_be_enabled()
    with Session(context['gateway'].store.engine) as session, session.begin():
        revision = session.get(CeRevision, item_id)
        session.get(CeDefinition, revision.definition_id).tombstoned_at = datetime.now(timezone.utc)
    transport[0].config['CE_RUNTIME'] = True
    check_access(page)
    expect(page.locator(f'#sb-revisions input[value="{item_id}"]')).to_have_count(0)
    expect(actor_choice).to_be_enabled()
    assert actor_choice.is_checked() and read(context)['draftVersion'] == version


@pytest.mark.parametrize('transport', ['damage-native'], indirect=True)
def test_browser_deselecting_scope_removes_its_cached_projection(browser):
    page, context = browser
    switch(page, 'sb-select', context['scope'])
    expect(page.locator('#sb-instances li')).to_have_count(3)
    page.locator('#sb-reason').fill('Private reason for this scope')
    page.locator('#sb-select').focus(); page.keyboard.press('Home')
    expect(page.locator('#sb-select')).to_have_value('')
    expect(page.locator('#sb-select')).to_be_enabled()
    assert page.locator('#sb-scope').is_hidden()
    assert page.locator('#sb-instances li, #sb-item option, #sb-target option, #sb-revision option').count() == 0
    assert page.locator('#sb-reason').input_value() == ''
    assert context['item'] not in page.locator('#sb-scope').inner_html()
    expect(page.locator('#sb-select')).to_be_focused()
