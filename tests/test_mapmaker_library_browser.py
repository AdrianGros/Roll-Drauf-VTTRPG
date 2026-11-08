"""Real browser journeys against the project API and persisted editable maps."""
import threading
import time
from pathlib import Path
import pytest
from flask_jwt_extended import create_access_token, decode_token
from playwright.sync_api import expect
from werkzeug.serving import make_server
from vtt import create_app
from vtt.extensions import db
from vtt.models import Role, User
from vtt.models.mapmaker_project import MapmakerProject
from test_mapmaker_browser import browser, CSP_PROBE
from test_mapmaker_library import API, document


@pytest.fixture
def site(tmp_path):
    app = create_app('testing')
    app.config.update(LOCAL_STORAGE_PATH=str(tmp_path / 'storage'), STORAGE_PROVIDER='local', JWT_COOKIE_CSRF_PROTECT=True)
    with app.app_context():
        db.create_all()
        role = Role(name='Player')
        db.session.add(role)
        db.session.flush()
        users = []
        for name, tier in [('library_browser_dm', 'dm'), ('library_browser_player', 'player')]:
            user = User(username=name, email=name+'@test.invalid', password_hash='unused', role_id=role.id,
                        profile_tier=tier, storage_quota_gb=5)
            db.session.add(user)
            users.append(user)
        db.session.commit()
        ids = [u.id for u in users]
        tokens = [create_access_token(identity=str(i)) for i in ids]
        csrf = [decode_token(t)['csrf'] for t in tokens]
    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    contexts = []
    def cookie_values(index):
        return [{'name': 'access_token_cookie', 'value': tokens[index], 'url': origin, 'httpOnly': True},
                {'name': 'csrf_access_token', 'value': csrf[index], 'url': origin}]
    def open_page(browser, index=0, width=1440):
        context = browser.new_context(viewport={'width': width, 'height': 900 if width > 600 else 844}, accept_downloads=True)
        contexts.append(context)
        context.add_cookies(cookie_values(index))
        context.add_init_script(CSP_PROBE)
        page = context.new_page()
        page.set_default_timeout(25000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(origin + '/static/mapmaker/index.html')
        page.wait_for_selector('#app[data-state=ready]')
        expect(page.locator('#newDialog')).to_be_visible()
        return page, errors
    yield app, ids, origin, open_page, cookie_values
    for context in contexts: context.close()
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()
    with app.app_context():
        db.session.remove()
        db.drop_all()


def summary(page):
    return page.evaluate('() => window.rdMapmaker.summary()')


def save(page):
    page.locator('#cloudSave').click()
    expect(page.locator('#cloudStatus')).to_have_text('In Bibliothek gespeichert', timeout=20000)


def clean(page, errors):
    assert errors == []
    assert page.evaluate('window.__csp') == []


@pytest.mark.parametrize('width', [320, 390, 1440])
def test_start_choices_and_responsive_library(site, browser, width):
    page, errors = site[3](browser, width=width)
    for selector in ['#newLibrary', '#newEmpty', '#newStarter']:
        expect(page.locator(selector)).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#newDialog')).to_be_visible()
    expect(page.locator('#libraryQuota')).to_contain_text('5 GiB')
    page.locator('#newEmpty').click()
    assert summary(page)['stamps'] == 0
    page.locator('#mapTitle').fill('Meine leere Karte')
    if width == 1440:
        page.keyboard.press('Control+s')
        expect(page.locator('#cloudStatus')).to_have_text('In Bibliothek gespeichert', timeout=20000)
    else:
        save(page)
    page.locator('#libraryBtn').click()
    expect(page.locator('#libraryList')).to_contain_text('Meine leere Karte')
    for selector in ['html', '#newDialog']:
        assert page.locator(selector).evaluate('(e) => e.scrollWidth <= e.clientWidth + 1')
    if width == 390:
        page.screenshot(path='/tmp/mapmaker-library-mobile.png')
    clean(page, errors)


def test_editable_map_roundtrip_other_device_copy_and_delete(site, browser):
    page, errors = site[3](browser)
    page.locator('#newStarter').click()
    page.locator('#mapTitle').fill('Küstenkarte <Archiv>')
    # Real raster gesture, retained across server persistence and another browser.
    position = page.evaluate('window.rdMapmaker.docToClient(1500, 290)')
    page.mouse.move(position['x'], position['y'])
    page.mouse.down()
    page.mouse.move(position['x'] + 20, position['y'] + 5, steps=5)
    page.mouse.up()
    save(page)
    original = summary(page)
    pixel = page.evaluate('window.rdMapmaker.sampleRegion(1500, 290, 20, 20)')
    other, other_errors = site[3](browser)
    expect(other.locator('#libraryList')).to_contain_text('Küstenkarte <Archiv>')
    other.locator('#libraryList .mm-btn-primary').click()
    expect(other.locator('#mapTitle')).to_have_value('Küstenkarte <Archiv>')
    restored = summary(other)
    # Import validation makes optional, absent place symbols explicitly null.
    normalized = [{**item, **({'symbol': None} if 'text' in item and 'symbol' not in item else {})}
                  for item in original['items']]
    assert restored['items'] == normalized
    assert restored['layers'] == original['layers']
    assert other.evaluate('window.rdMapmaker.sampleRegion(1500, 290, 20, 20)') == pixel
    other.locator('#mapTitle').fill('Küstenkarte überarbeitet')
    save(other)
    with site[0].app_context():
        project = MapmakerProject.query.one()
        assert project.revision == 2
    other.locator('#fileMenuBtn').click()
    other.locator('#saveCopyBtn').click()
    expect(other.locator('#cloudStatus')).to_have_text('In Bibliothek gespeichert')
    with site[0].app_context(): assert MapmakerProject.query.count() == 2
    other.locator('#libraryBtn').click()
    other.locator('#libraryList li').first.get_by_role('button', name='löschen', exact=False).click()
    other.locator('#deleteMapConfirm').click()
    expect(other.locator('#libraryList li')).to_have_count(1)
    unrelated, unrelated_errors = site[3](browser, index=1)
    expect(unrelated.locator('#libraryList li')).to_have_count(0)
    clean(page, errors)
    clean(other, other_errors)
    clean(unrelated, unrelated_errors)


def test_stale_tab_conflict_then_save_as_copy(site, browser):
    first, first_errors = site[3](browser)
    first.locator('#newEmpty').click()
    first.locator('#mapTitle').fill('Gemeinsamer Ausgangsstand')
    save(first)
    second, second_errors = site[3](browser)
    second.locator('#libraryList .mm-btn-primary').click()
    expect(second.locator('#mapTitle')).to_have_value('Gemeinsamer Ausgangsstand')
    second.locator('#mapTitle').fill('Aktueller Serverstand')
    save(second)
    first.locator('#mapTitle').fill('Eigene spätere Änderungen')
    first.locator('#cloudSave').click()
    expect(first.locator('#errorDialog')).to_be_visible()
    expect(first.locator('#errorText')).to_contain_text('inzwischen geändert')
    assert summary(first)['title'] == 'Eigene spätere Änderungen'
    first.locator('#errorClose').click()
    first.locator('#fileMenuBtn').click()
    first.locator('#saveCopyBtn').click()
    expect(first.locator('#cloudStatus')).to_have_text('In Bibliothek gespeichert')
    with site[0].app_context():
        assert {p.title for p in MapmakerProject.query.all()} == {'Aktueller Serverstand', 'Eigene spätere Änderungen'}
    clean(first, first_errors)
    clean(second, second_errors)


def test_account_change_blocks_save_and_scopes_drafts(site, browser):
    page, errors = site[3](browser)
    page.locator('#newEmpty').click()
    page.locator('#mapTitle').fill('Privater Entwurf Konto A')
    save(page)
    expect(page.locator('#saveStatus')).to_have_attribute('data-state', 'saved', timeout=20000)
    page.context.add_cookies(site[4](1))
    page.locator('#mapTitle').fill('Darf nicht in Konto B landen')
    page.locator('#cloudSave').click()
    expect(page.locator('#errorText')).to_contain_text('Konto hat sich geändert')
    with site[0].app_context():
        assert MapmakerProject.query.filter_by(owner_id=site[1][1]).count() == 0
        assert MapmakerProject.query.filter_by(owner_id=site[1][0]).one().title == 'Privater Entwurf Konto A'
    page.reload()
    page.wait_for_selector('#app[data-state=ready]')
    expect(page.locator('#newDialog')).to_be_visible()
    expect(page.locator('#restoreDialog')).not_to_be_visible()
    expect(page.locator('#libraryList li')).to_have_count(0)
    clean(page, errors)


def test_quota_error_and_local_file_backup(site, browser, tmp_path):
    page, errors = site[3](browser, index=1)
    page.locator('#newStarter').click()
    page.locator('#mapTitle').fill('Bei vollem Speicher behalten')
    with site[0].app_context():
        user = db.session.get(User, site[1][1])
        user.storage_quota_gb = 0
        db.session.commit()
    page.locator('#cloudSave').click()
    expect(page.locator('#errorText')).to_contain_text('Speicherplatz reicht nicht')
    page.locator('#errorClose').click()
    assert summary(page)['title'] == 'Bei vollem Speicher behalten'
    with page.expect_download() as download:
        page.locator('#fileMenuBtn').click()
        page.locator('#saveBtn').click()
    download.value.save_as(tmp_path / 'backup.rdmap.json')
    assert (tmp_path / 'backup.rdmap.json').stat().st_size > 1000
    with site[0].app_context(): assert MapmakerProject.query.count() == 0
    clean(page, errors)


def test_edits_during_save_remain_unsaved(site, browser):
    from test_mapmaker_browser import HOLD_TO_BLOB, _wait_until
    page, errors = site[3](browser)
    page.locator('#newEmpty').click()
    page.locator('#mapTitle').fill('Stand beim Speichern')
    page.evaluate(HOLD_TO_BLOB)
    page.locator('#cloudSave').click()
    deadline = time.monotonic() + 15
    while not page.evaluate('window.__held.length'):
        assert time.monotonic() < deadline
        page.wait_for_timeout(50)
    page.locator('#mapTitle').fill('Änderung während des Speicherns')
    page.evaluate('window.__release()')
    expect(page.locator('#cloudStatus')).to_have_text('Bibliothek: Änderungen offen', timeout=20000)
    with site[0].app_context():
        assert MapmakerProject.query.one().title == 'Stand beim Speichern'
    assert summary(page)['title'] == 'Änderung während des Speicherns'
    save(page)
    with site[0].app_context():
        assert MapmakerProject.query.one().title == 'Änderung während des Speicherns'
    clean(page, errors)
