"""Real browser authoring and execution against authenticated PostgreSQL APIs."""
import json
import os
from pathlib import Path

import pytest
from playwright.sync_api import expect

from homebrew_examples import build, examples
from test_ce_content_store import postgres_engine
from test_ce_migration import migration_engine
from test_ce_authoring import authoring_engine, author
from test_ce_authoring_transports import transport, browser
from test_ce_homebrew_backend import homebrew_tables, world, command
from test_ce_advanced import payload
from vtt.creation_engine.store.advanced import AdvancedService

pytestmark = pytest.mark.postgres


def studio(page):
    page.locator('nav a[href="/api/ce/authoring/advanced"]').click()
    expect(page.locator('#source')).to_be_enabled()
    return page


def version(page, number):
    expect(page.locator('#document-version')).to_have_text('Version ' + str(number))
    expect(page.locator('#source')).to_be_enabled()


def create(page, kind):
    page.locator('#new-type').select_option(kind.type_id)
    page.locator('#create').click()
    version(page, 1)
    expect(page.locator('#source')).to_have_value('{}')


def fill(page, document):
    page.locator('#source').fill(json.dumps(document, indent=2))


def state(page):
    return json.loads(page.locator('#test-state').text_content())


def action(page, document, number):
    page.locator('#action-source').fill(json.dumps(document, indent=2))
    page.locator('#execute').click()
    expect(page.locator('#scope-version')).to_contain_text('Version ' + str(number) + ' ·')
    expect(page.locator('#operation')).to_be_enabled()
    return json.loads(page.locator('#outcome').text_content())


def artifact(page, tmp_path, name):
    folder = Path(os.environ.get('CE_TEST_ARTIFACT_DIR', tmp_path))
    folder.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(folder / name), full_page=True)


def test_browser_authors_revisions_builds_casts_and_reopens(browser, tmp_path):
    page, _ = browser
    studio(page)
    documents = examples()
    for kind, document in documents:
        create(page, kind)
        fill(page, document)
        page.keyboard.press('Control+Enter')
        expect(page.locator('#issues')).to_contain_text('Document is valid')
        page.keyboard.press('Control+s')
        version(page, 2)
        page.locator('#commit').click()
        version(page, 3)
        expect(page.locator('#revision-result')).to_contain_text('rev:')
    artifact(page, tmp_path, 'advanced-author-desktop.png')
    page.locator('#test-tab').click()
    expect(page.locator('#edition')).to_be_enabled()
    page.locator('#edition').select_option('dnd5e_2024')
    expect(page.locator('#revision-list input')).to_have_count(5)
    for checkbox in page.locator('#revision-list input').all():
        checkbox.check()
    page.locator('#create-sandbox').click()
    expect(page.locator('#test-controls')).to_be_visible()
    expect(page.locator('#prepare')).to_be_enabled()
    page.locator('#build-class').select_option(index=1)
    page.locator('#build-race').select_option(index=1)
    page.locator('#prepare').click()
    expect(page.locator('#action-source')).to_be_enabled()
    prepared = json.loads(page.locator('#action-source').input_value())
    assert prepared['baseHp'] is None
    hero = build(prepared['classRevision'], prepared['raceRevision'])
    caster = action(page, hero, 2)['outcome']['characterId']
    target = action(page, {**hero, 'name': 'Target'}, 3)['outcome']['characterId']
    page.locator('#operation').select_option('CastSpell')
    page.locator('#actor').select_option(caster)
    page.locator('#target').select_option(target)
    page.locator('#spell').select_option('ember')
    page.locator('#prepare').click()
    expect(page.locator('#action-source')).to_be_enabled()
    casting = json.loads(page.locator('#action-source').input_value())
    assert casting['distanceFeet'] is None and casting['adjudication']['timingSatisfied'] is False
    casting.update(distanceFeet=20, adjudication={'timingSatisfied': True, 'componentsSatisfied': True})
    action(page, casting, 4)
    after = state(page)
    assert after['characters'][caster]['resources']['mana']['current'] == 8
    assert after['characters'][target]['hp'] < after['characters'][target]['stats']['hpMax']
    expect(page.locator('#test-history > li')).to_have_count(4)
    artifact(page, tmp_path, 'advanced-test-desktop.png')
    sandbox_id = page.locator('#sandboxes').input_value()
    page.reload()
    expect(page.locator('#source')).to_be_enabled()
    page.locator('#test-tab').click()
    expect(page.locator('#sandboxes')).to_be_enabled()
    page.locator('#sandboxes').select_option(sandbox_id)
    expect(page.locator('#scope-version')).to_contain_text('Version 4 ·')
    expect(page.locator('#operation')).to_be_enabled()
    assert state(page) == after
    # The same bench exposes progression, recovery, duration and concentration.
    def perform(operation, values, number, actor=caster):
        page.locator('#operation').select_option(operation)
        if operation not in ('AdvanceRounds', 'BuildCharacter'):
            page.locator('#actor').select_option(actor)
        page.locator('#prepare').click()
        expect(page.locator('#action-source')).to_be_enabled()
        prepared = json.loads(page.locator('#action-source').input_value())
        return action(page, {**prepared, **values}, number)
    perform('RebuildCharacter', {'build': {**hero, 'name': 'Target', 'level': 2}}, 5, actor=target)
    assert state(page)['characters'][target]['level'] == 2
    perform('RecoverResources', {'event': 'long_rest', 'reason': 'A completed test rest'}, 6)
    assert state(page)['characters'][caster]['resources']['mana']['current'] == 10
    ward = {'casterId': caster, 'targetId': caster, 'spellKey': 'ward', 'castLevel': 1,
            'distanceFeet': 0, 'adjudication': {'timingSatisfied': True, 'componentsSatisfied': True}}
    perform('CastSpell', ward, 7)
    assert 'AC 15' in page.locator('#actors').inner_text()
    perform('AdvanceRounds', {'rounds': 2}, 8)
    assert not any(effect['casterId'] == caster for effect in state(page)['effects'])
    perform('CastSpell', ward, 9)
    perform('CastSpell', {**casting, 'casterId': target, 'targetId': caster}, 10, actor=target)
    expect(page.locator('#concentration')).to_be_visible()
    perform('ResolveConcentration', {'maintained': False, 'reason': 'Failed concentration check'}, 11)
    expect(page.locator('#concentration')).to_be_hidden()
    perform('CastSpell', ward, 12)
    perform('EndConcentration', {'reason': 'Voluntarily ended the ward'}, 13)
    assert not any(effect['casterId'] == caster for effect in state(page)['effects'])
    artifact(page, tmp_path, 'advanced-test-desktop.png')
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert page.locator('#author-tab').bounding_box()['width'] > 100
    artifact(page, tmp_path, 'advanced-test-mobile.png')


def test_browser_validation_import_download_diff_and_dirty_guards(browser, tmp_path):
    page, _ = browser
    studio(page)
    kind, document = examples()[2]
    create(page, kind)
    page.locator('#source').fill('{"name":"first","name":"second"}')
    page.locator('#validate').click()
    expect(page.locator('#status')).to_contain_text('Duplicate property')
    page.locator('#source').fill('{')
    page.locator('#validate').click()
    expect(page.locator('#status')).to_contain_text('Invalid JSON')
    invalid = {**document, 'spell': {**document['spell'], 'level': 12}}
    fill(page, invalid)
    page.locator('#validate').click()
    expect(page.locator('#issues')).to_contain_text('/spell/level')
    page.locator('#issues button').first.click()
    assert page.locator('#source').evaluate('(n)=>n.selectionStart') > 0
    expect(page.locator('#new-type')).to_be_disabled()
    page.locator('a[data-nav][href="/api/ce/authoring"]').click(force=True)
    expect(page.locator('#status')).to_have_text('Save or discard your edits first.')
    assert page.url.endswith('/advanced')
    file = tmp_path / 'spell.json'
    file.write_text(json.dumps(document))
    page.locator('#file').set_input_files(file)
    expect(page.locator('#status')).to_contain_text('Imported into the editor')
    page.locator('#format').click()
    expect(page.locator('#source')).to_have_value(json.dumps(document, indent=2))
    page.locator('#diff-panel summary').click()
    expect(page.locator('#diff')).to_contain_text('Ember thread')
    page.locator('#field-filter').fill('spell.level')
    expect(page.locator('#fields details')).to_have_count(1)
    page.locator('#fields summary').click()
    page.locator('#fields button').click()
    assert page.locator('#source').evaluate('(n)=>n.selectionStart') > 0
    with page.expect_download() as download:
        page.locator('#download').click()
    assert json.loads(Path(download.value.path()).read_text()) == document
    page.locator('#save').click()
    version(page, 2)
    for locale, title in [('de','Erweiterte Werkstatt'), ('fr','Atelier avancé'), ('en','Advanced studio')]:
        page.locator('#language').select_option(locale)
        expect(page.locator('h1')).to_have_text(title)
        expect(page.locator('#language')).to_be_enabled()
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    artifact(page, tmp_path, 'advanced-author-mobile.png')


def test_browser_conflict_preserves_local_and_explicitly_rebases(browser):
    page, a = browser
    studio(page)
    kind, document = examples()[2]
    create(page, kind)
    a = {**a, 'draft': page.locator('#drafts').input_value()}
    fill(page, {**document, 'name': 'Local draft'})
    service = AdvancedService(a['service'])
    a['advanced'] = service
    service.save(a['principal'], a['workspace'], a['draft'], payload(a, {**document, 'name': 'Other tab'}))
    page.locator('#save').click()
    expect(page.locator('#conflict')).to_be_visible()
    assert json.loads(page.locator('#source').input_value())['name'] == 'Local draft'
    page.locator('#compare').click()
    expect(page.locator('#remote-content')).to_contain_text('Other tab')
    page.locator('#accept-base').click()
    version(page, 2)
    assert json.loads(page.locator('#source').input_value())['name'] == 'Local draft'
    page.locator('#save').click()
    version(page, 3)
    assert service.read(a['principal'], a['workspace'], a['draft'])['content']['name'] == 'Local draft'


def test_browser_lost_save_retries_exact_request_once(browser):
    page, a = browser
    studio(page)
    kind, document = examples()[2]
    create(page, kind)
    a = {**a, 'draft': page.locator('#drafts').input_value()}
    requests = []
    def lose(route):
        if route.request.method != 'POST':
            return route.continue_()
        requests.append(route.request.post_data_json)
        if len(requests) == 1:
            route.fetch()
            route.abort('failed')
        else:
            route.continue_()
    page.route('**/drafts/*/document', lose)
    document['name'] = '<img src=x onerror=alert(1)> Test'
    fill(page, document)
    page.locator('#save').click()
    expect(page.locator('#retry')).to_be_visible()
    expect(page.locator('#source')).to_be_disabled()
    page.locator('#retry').click()
    version(page, 2)
    assert len(requests) == 2 and requests[0] == requests[1]
    assert AdvancedService(a['service']).read(a['principal'], a['workspace'], a['draft'])['draftVersion'] == 2
    expect(page.locator('#document-title img')).to_have_count(0)
    expect(page.locator('#document-title')).to_have_text(document['name'])


def test_browser_access_loss_clears_content_and_offline_preserves_input(browser):
    page, _ = browser
    studio(page)
    fill(page, {'name': 'Unsent private work'})
    page.route('**/advanced/workspace', lambda route: route.abort('failed'))
    page.evaluate("window.dispatchEvent(new Event('focus'))")
    expect(page.locator('#access')).to_be_visible()
    expect(page.locator('#source')).to_be_disabled()
    assert 'Unsent private work' in page.locator('#source').input_value()
    page.unroute('**/advanced/workspace')
    page.locator('#recheck').click()
    expect(page.locator('#source')).to_be_enabled()
    page.route('**/advanced/workspace', lambda route: route.fulfill(status=401, json={'error': {'code':'UNAUTHORIZED'}}))
    page.evaluate("window.dispatchEvent(new Event('focus'))")
    expect(page.locator('#source')).to_have_value('')
    expect(page.locator('#access-message')).to_contain_text('Protected content has been cleared')
    expect(page.locator('#schema')).to_have_text('')
    expect(page.locator('#drafts option')).to_have_count(0)


def test_browser_test_scope_conflict_and_lost_action_response(browser, world):
    page, _ = browser
    studio(page)
    page.locator('#test-tab').click()
    expect(page.locator('#sandboxes')).to_be_enabled()
    page.locator('#sandboxes').select_option(world['sandbox']['sandboxId'])
    expect(page.locator('#operation')).to_be_enabled()
    page.locator('#operation').select_option('CastSpell')
    page.locator('#actor').select_option(world['caster'])
    page.locator('#target').select_option(world['target'])
    page.locator('#spell').select_option('ember')
    page.locator('#prepare').click()
    expect(page.locator('#action-source')).to_be_enabled()
    casting = json.loads(page.locator('#action-source').input_value())
    casting.update(distanceFeet=20, adjudication={'timingSatisfied': True, 'componentsSatisfied': True})
    local = json.dumps(casting, indent=2)
    page.locator('#action-source').fill(local)
    world['send'](command('AdvanceRounds', {'rounds': 1}, world['sandbox']))
    page.locator('#execute').click()
    expect(page.locator('#status')).to_contain_text('The test changed')
    expect(page.locator('#execute')).to_be_disabled()
    expect(page.locator('#action-source')).to_have_value(local)
    page.locator('#refresh-test').click()
    expect(page.locator('#scope-version')).to_contain_text('Version 4 ·')
    expect(page.locator('#execute')).to_be_enabled()
    expect(page.locator('#action-source')).to_have_value(local)
    assert state(page)['characters'][world['caster']]['resources']['mana']['current'] == 10
    action(page, casting, 5)
    assert state(page)['characters'][world['caster']]['resources']['mana']['current'] == 8
    page.locator('#operation').select_option('AdvanceRounds')
    page.locator('#prepare').click()
    expect(page.locator('#action-source')).to_be_enabled()
    page.locator('#action-source').fill('{"rounds":1}')
    requests = []
    def lost(route):
        requests.append(route.request.post_data_json)
        if len(requests) == 1:
            route.fetch()
            route.abort('failed')
        else:
            route.continue_()
    page.route('**/homebrew/commands', lost)
    page.locator('#execute').click()
    expect(page.locator('#retry')).to_be_visible()
    page.locator('#retry').click()
    expect(page.locator('#scope-version')).to_contain_text('Version 6 ·')
    expect(page.locator('#operation')).to_be_enabled()
    assert len(requests) == 2 and requests[0] == requests[1]
    assert state(page)['round'] == 2
