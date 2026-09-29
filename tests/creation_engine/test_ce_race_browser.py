"""Real browser journeys from named race traits to new and imported D&D sheets."""

import os
from pathlib import Path

import pytest
from flask import jsonify, render_template
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vtt.auth import auth_bp
from vtt.campaigns import campaigns_bp
from vtt.characters import characters_bp
from vtt.endpoints.dashboard_home import dashboard_home_bp
from vtt.extensions import db
from vtt.models import Character
from vtt.creation_engine.store.sheet_models import CeCharacterOrigin, CeSheetCommand

from test_ce_authoring import author, authoring_engine, read
from test_ce_authoring_transports import browser, transport, wait_version
from test_ce_content_store import postgres_engine
from test_ce_migration import migration_engine
from test_ce_race_compiler import ANSWERS, TRAITS
from test_ce_race_sheets import CORE, imported, saved_race

expect = pytest.importorskip('playwright.sync_api').expect
pytestmark = pytest.mark.postgres
M79 = Path(__file__).resolve().parents[2] / 'migrations/migration_m79_creation_engine_sheets.sql'


@pytest.fixture(scope='module', autouse=True)
def race_sheet_schema(authoring_engine):
    with authoring_engine.begin() as connection:
        with connection.connection.cursor() as cursor:
            cursor.execute(M79.read_text())


@pytest.fixture(autouse=True)
def sheet_browser_routes(transport, race_sheet_schema):
    app, _, _, _, _, context = transport
    app.config['SQLALCHEMY_DATABASE_URI'] = context['gateway'].store.engine.url.render_as_string(hide_password=False)
    db.init_app(app)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(characters_bp, url_prefix='/api')
    app.register_blueprint(campaigns_bp, url_prefix='/api')
    app.register_blueprint(dashboard_home_bp)
    app.add_url_rule('/character-sheet', 'sheet_page', lambda: render_template('character-sheet.html'))
    app.add_url_rule('/dashboard', 'dashboard_page', lambda: render_template('dashboard.html'))
    app.add_url_rule('/characters', 'characters_page', lambda: render_template('characters.html'))
    app.add_url_rule('/api/page-content/<path:key>', 'page_content', lambda key: jsonify({}))
    yield
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def capture_journey(page, name, locator=None):
    directory = os.getenv('CE_BROWSER_ARTIFACT_DIR')
    if not directory:
        return
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    if locator is None:
        page.screenshot(path=str(path / (name + '.png')), full_page=True)
    else:
        locator.screenshot(path=str(path / (name + '.png')))


def question(page, key):
    return page.locator(f'form[data-question="{key}"]')


def save_answer(page, context, key, value):
    form = question(page, key)
    before = read(context)['draftVersion']
    if form.locator('select').count():
        form.locator('select').select_option(value)
    else:
        form.locator('textarea, input').fill(str(value))
    form.locator('button[type="submit"]').click()
    wait_version(page, before + 1)


def create_race_in_browser(page, context):
    page.locator('#locale').select_option('en')
    expect(page.locator('#new-type')).to_be_enabled()
    page.locator('#new-type').select_option('dnd5e.authored-race')
    page.locator('#new').click()
    expect(question(page, 'content.name')).to_be_visible()
    wait_version(page, 1)
    context = {**context, 'draft': page.locator('#drafts').input_value()}
    page.locator('#mode').select_option('structured')
    expect(question(page, 'race.edition')).to_be_visible()
    for key, value in ANSWERS.items():
        if key != 'race.traits':
            save_answer(page, context, key, value)
            continue
        form = question(page, key)
        before = read(context)['draftVersion']
        for index, trait in enumerate(TRAITS):
            form.get_by_role('button', name='Add a feature or trait', exact=True).click()
            row = form.locator('[data-trait]').nth(index)
            for field, value in trait.items():
                control = row.locator(f'[data-trait-field="{field}"]')
                if field == 'kind': control.select_option(value)
                else: control.fill(value)
        form.locator('button[type="submit"]').click()
        wait_version(page, before + 1)
    assert read(context)['content']['race']['traits'] == TRAITS
    page.locator('#claim').select_option('sheet_ready')
    expect(page.locator('#commit')).to_be_enabled()
    page.locator('#commit').click()
    expect(page.locator('#sheet-form')).to_be_visible()
    expect(page.locator('#commit')).to_be_enabled()
    return context


def open_seeded_race(page, context, *, character_id=None):
    race = saved_race(context)
    origin = page.url.split('/api/')[0]
    page.goto(origin + '/api/ce/authoring' + (f'?character_id={character_id}' if character_id else ''))
    expect(page.locator('#drafts')).to_be_enabled()
    page.locator('#drafts').select_option(race['draft'])
    expect(page.locator('#sheet-form')).to_be_visible()
    page.locator('#locale').select_option('en')
    expect(page.locator('#sheet-destination')).to_be_enabled()
    return race


def fill_new_character(page):
    page.locator('#sheet-destination').select_option('new')
    for field, value in CORE.items():
        page.locator('#sheet-new-' + field).fill(str(value))
    page.locator('#sheet-confirm').check()


def applied_character(page):
    expect(page.locator('#sheet-open')).to_be_visible()
    href = page.locator('#sheet-open').get_attribute('href')
    return int(href.split('id=')[1]), href


@pytest.mark.parametrize('width', [1280, 390])
def test_create_homebrew_race_reload_and_create_real_character_sheet(browser, width):
    page, context = browser
    page.set_viewport_size({'width': width, 'height': 960})
    race = create_race_in_browser(page, context)
    draft_id = race['draft']
    capture_journey(page, f'race-editor-{width}')
    capture_journey(page, f'race-traits-{width}', question(page, 'race.traits'))
    page.reload()
    expect(page.locator('#drafts')).to_be_enabled()
    page.locator('#drafts').select_option(draft_id)
    expect(page.locator('#sheet-form')).to_be_visible()
    assert read(race)['content']['race']['traits'] == TRAITS
    expect(page.locator('#sheet-review')).to_contain_text('Stone memory')
    fill_new_character(page)
    if width == 390:
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.locator('#sheet-apply').click()
    character_id, href = applied_character(page)
    with Session(race['gateway'].store.engine) as session:
        character = session.get(Character, character_id)
        assert character.name == CORE['name'] and character.hp_current == CORE['hp_max']
        assert character.str_score == CORE['str'] and character.race == ANSWERS['content.name']
    response = page.request.get(page.url.split('/api/')[0] + f'/api/characters/{character_id}/sheet')
    assert response.ok and response.json()['character']['homebrew_origin']['traits'] == TRAITS
    page.locator('#sheet-open').click()
    expect(page).to_have_url(page.url.split('/character-sheet')[0] + href)
    expect(page.locator('#homebrewOriginProfile')).to_contain_text(ANSWERS['content.name'])
    expect(page.locator('#homebrewOriginTraits')).to_contain_text('Stone memory')
    expect(page.locator('#homebrewOriginTraits')).to_contain_text('Echo step')
    expect(page.locator('#homebrewOriginTraits')).to_contain_text(TRAITS[1]['usage'])
    expect(page.locator('#homebrewOriginTraits')).to_contain_text(TRAITS[1]['choices'])
    capture_journey(page, f'character-sheet-{width}')


def test_imported_character_context_and_lost_response_retry_preserve_existing_values(browser):
    page, context = browser
    character_id = imported(context)
    race = open_seeded_race(page, context, character_id=character_id)
    expect(page.locator('#return-character')).to_have_attribute('href', f'/character-sheet?id={character_id}')
    expect(page.locator('#sheet-character')).to_have_value(str(character_id))
    expect(page.locator('#sheet-review')).to_contain_text('Old race')
    page.locator('#sheet-confirm').check()
    writes = []

    def lose_first_reply(route):
        if route.request.method != 'POST':
            route.continue_(); return
        writes.append(route.request.post_data_json)
        if len(writes) == 1:
            response = route.fetch()
            assert response.ok
            route.abort('failed')
        else: route.continue_()

    page.route('**/authoring/workspaces/*/sheets', lose_first_reply)
    page.locator('#sheet-apply').click()
    expect(page.locator('#retry')).to_be_visible()
    expect(page.locator('#retry')).to_be_enabled()
    page.get_by_role('link', name='Overview', exact=True).click(force=True)
    assert '/api/ce/authoring' in page.url and len(writes) == 1
    page.locator('#retry').click()
    result_id, _ = applied_character(page)
    assert result_id == character_id and writes[0] == writes[1] and len(writes) == 2
    with Session(race['gateway'].store.engine) as session:
        character = session.get(Character, character_id)
        assert character.str_score == 19 and character.hp_current == 7
        assert character.hp_max == 41 and character.ac == 18 and character.xp == 3450
        assert character.character_data['imported'] == {'notes': 'keep me', 'skills': ['Arcana']}
        assert character.equipment[0].name == 'Imported staff'
        assert session.get(CeCharacterOrigin, character_id).version == 1
        assert session.scalar(select(func.count()).select_from(CeSheetCommand)
                              .where(CeSheetCommand.principal_id == context['principal'])) == 1


def test_dirty_traits_and_character_values_block_navigation_until_discarded(browser):
    page, context = browser
    race = open_seeded_race(page, context)
    page.locator('#mode').select_option('structured')
    form = question(page, 'race.traits')
    expect(form.locator('[data-trait]')).to_have_count(2)
    form.locator('[data-trait-field="description"]').first.fill('Unsaved trait text')
    overview = page.get_by_role('link', name='Overview', exact=True)
    overview.click(force=True)
    assert page.url.endswith('/api/ce/authoring')
    expect(form.locator('[data-trait-field="description"]').first).to_have_value('Unsaved trait text')
    assert read(race)['content']['race']['traits'] == TRAITS
    page.locator('#discard').click()
    expect(form.locator('[data-trait-field="description"]').first).to_have_value(TRAITS[0]['description'])
    fill_new_character(page)
    overview.click(force=True)
    assert page.url.endswith('/api/ce/authoring')
    expect(page.locator('#sheet-new-name')).to_have_value(CORE['name'])
    page.locator('#discard').click()
    expect(page.locator('#sheet-confirm')).not_to_be_checked()
    origin = page.url.split('/api/')[0]
    overview.click()
    expect(page).to_have_url(origin + '/dashboard')


def test_confirmed_sheet_creation_survives_failed_followup_catalog(browser):
    page, context = browser
    race = open_seeded_race(page, context)
    fill_new_character(page)
    writes = []

    def fail_only_catalog_after_success(route):
        if route.request.method == 'POST':
            writes.append(route.request.post_data_json)
            route.fulfill(response=route.fetch())
        elif writes: route.abort('failed')
        else: route.continue_()

    page.route('**/authoring/workspaces/*/sheets', fail_only_catalog_after_success)
    page.locator('#sheet-apply').click()
    character_id, href = applied_character(page)
    expect(page.locator('#retry')).to_be_hidden()
    assert len(writes) == 1
    expect(page.locator('#sheet-confirm')).not_to_be_checked()
    with Session(race['gateway'].store.engine) as session:
        assert session.get(Character, character_id).name == CORE['name']
        assert session.scalar(select(func.count()).select_from(Character)
                              .where(Character.user_id == context['principal'])) == 1
    page.locator('#sheet-open').click()
    expect(page).to_have_url(page.url.split('/character-sheet')[0] + href)
    expect(page.locator('#homebrewOriginTraits')).to_contain_text('Echo step')


def test_edit_named_traits_save_second_revision_and_explicitly_replace_sheet_origin(browser):
    page, context = browser
    character_id = imported(context)
    race = open_seeded_race(page, context, character_id=character_id)
    first_revision = page.locator('#sheet-revision').input_value()
    page.locator('#sheet-confirm').check()
    page.locator('#sheet-apply').click()
    applied_character(page)
    expect(page.locator('#sheet-open')).not_to_have_attribute('aria-disabled', 'true')
    page.locator('#mode').select_option('structured')
    form = question(page, 'race.traits')
    before = read(race)['draftVersion']
    form.locator('[data-trait-field="description"]').first.fill('Remember a mountain touched during the last year.')
    form.locator('[data-trait]').last.get_by_role('button', name='Remove this entry', exact=True).click()
    expect(form.locator('[data-trait]')).to_have_count(1)
    form.locator('button[type="submit"]').click()
    wait_version(page, before + 1)
    page.locator('#claim').select_option('sheet_ready')
    page.locator('#commit').click()
    expect(page.locator('#sheet-revision option')).to_have_count(3)
    with Session(race['gateway'].store.engine) as session:
        character = session.get(Character, character_id)
        assert race['sheets'].projection(character)['traits'] == TRAITS
    latest = page.locator('#sheet-revision option').last.get_attribute('value')
    assert latest != first_revision
    page.locator('#sheet-revision').select_option(latest)
    page.locator('#sheet-character').select_option(str(character_id))
    page.locator('#sheet-confirm').check()
    page.locator('#sheet-apply').click()
    expect(page.locator('#sheet-confirm')).not_to_be_checked()
    expect(page.locator('#sheet-open')).not_to_have_attribute('aria-disabled', 'true')
    with Session(race['gateway'].store.engine) as session:
        character = session.get(Character, character_id)
        assert session.get(CeCharacterOrigin, character_id).version == 2
        assert race['sheets'].projection(character)['traits'] == [
            {**TRAITS[0], 'description': 'Remember a mountain touched during the last year.'}]
        assert character.hp_current == 7 and character.str_score == 19


def test_download_export_import_through_visible_archive_and_apply_race(browser):
    import json

    page, context = browser
    original_id = imported(context, class_name='Wizard', background='Sage')
    race = open_seeded_race(page, context, character_id=original_id)
    page.locator('#sheet-confirm').check()
    page.locator('#sheet-apply').click()
    applied_character(page)
    expect(page.locator('#sheet-open')).not_to_have_attribute('aria-disabled', 'true')
    page.locator('#sheet-open').click()
    expect(page.locator('#homebrewOriginTraits')).to_contain_text('Stone memory')
    with page.expect_download() as downloaded:
        page.locator('#dndExportSection').get_by_role('button').click()
    payload = json.loads(Path(downloaded.value.path()).read_text())
    assert payload['export_kind'] == 'dnd5e_character'
    assert payload['homebrew_origin']['traits'] == TRAITS
    assert payload['equipment'][0]['name'] == 'Imported staff'
    payload['name'] = 'Imported journey copy'
    origin = page.url.split('/character-sheet')[0]
    # Enter Characters via an in-document page turn, so the import entry must
    # work even while the browser still owns dashboard.html's JavaScript.
    page.goto(origin + '/dashboard')
    page.locator('.book-dashboard-ribbon [data-dashboard-route="/characters"]').click()
    page.get_by_role('button', name='Charakter importieren', exact=True).click()
    expect(page.get_by_role('dialog', name='Charakter importieren')).to_be_visible()
    page.locator('#importPayload').fill(json.dumps(payload))
    with page.expect_response(lambda response: response.url.endswith('/api/characters/import')
                              and response.request.method == 'POST') as imported_response:
        page.locator('#importSubmitBtn').click()
    assert imported_response.value.ok
    new_id = imported_response.value.json()['character']['id']
    assert new_id != original_id
    expect(page.locator('#importModal')).to_be_hidden()
    expect(page.locator('[data-character-import-status]')).to_contain_text('Imported journey copy')
    expect(page.locator('#book-dashboard-scene')).to_contain_text('Imported journey copy')
    page.locator(f'[data-dashboard-href="/character-sheet?id={new_id}"]').click()
    expect(page.locator('#homebrewOriginTraits')).to_contain_text('Stone memory')
    engine = page.locator('.book-dashboard-ribbon [data-creation-engine-nav]:visible')
    expect(engine).to_have_attribute('href', f'/api/ce/authoring?character_id={new_id}')
    engine.click()
    expect(page.locator('#drafts')).to_be_enabled()
    page.locator('#drafts').select_option(race['draft'])
    expect(page.locator('#sheet-character')).to_have_value(str(new_id))
    page.locator('#sheet-confirm').check()
    page.locator('#sheet-apply').click()
    expect(page.locator('#sheet-confirm')).not_to_be_checked()
    expect(page.locator('#sheet-open')).not_to_have_attribute('aria-disabled', 'true')
    with Session(race['gateway'].store.engine) as session:
        character = session.get(Character, new_id)
        assert character.name == 'Imported journey copy'
        assert character.str_score == 19 and character.hp_current == 7
        assert character.equipment[0].name == 'Imported staff'
        assert race['sheets'].projection(character)['traits'] == TRAITS
        assert session.get(Character, original_id).name == 'Imported hero'


@pytest.mark.parametrize('width', [1280, 390])
def test_sheet_navigation_stays_visible_beside_long_account_badge(browser, width):
    page, context = browser
    character_id = imported(context, class_name='Wizard', background='Sage')
    page.set_viewport_size({'width': width, 'height': 960})
    origin = page.url.split('/api/')[0]
    page.goto(f'{origin}/character-sheet?id={character_id}')
    entry = page.locator('.book-dashboard-ribbon [data-creation-engine-nav]:visible')
    expect(entry).to_have_attribute('href', f'/api/ce/authoring?character_id={character_id}')
    page.evaluate('window.scrollTo(0, 0)')
    geometry = page.evaluate('''() => {
        const ribbon = document.querySelector('#book-dashboard-scene .book-dashboard-ribbon');
        const badge = document.getElementById('sheetReaderBadge').getBoundingClientRect();
        const rect = box => ({left: box.left, right: box.right, top: box.top, bottom: box.bottom});
        return [...ribbon.children].map(node => {
            const box = node.getBoundingClientRect();
            const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
            return {text: node.textContent, ...rect(box), viewport: innerWidth,
                badge: rect(badge), reachable: node === hit || node.contains(hit),
                overlapsBadge: box.left < badge.right && box.right > badge.left && box.top < badge.bottom && box.bottom > badge.top};
        });
    }''')
    assert all(row['reachable'] and not row['overlapsBadge'] and row['left'] >= 0
               and row['right'] <= row['viewport'] for row in geometry), geometry
