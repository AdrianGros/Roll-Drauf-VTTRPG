"""FV15: campaign-quota request and owner/admin review in the normal own-profile entry."""

import json
from threading import Thread

import pytest
from flask_jwt_extended import create_access_token
from playwright.sync_api import expect
from werkzeug.serving import make_server

from tests.test_srd_creator_browser import QuietHandler
from vtt import create_app
from vtt.config import TestingConfig
from vtt.extensions import db
from vtt.models import AuditLog, Role, User
from vtt.models.campaign_quota_request import CampaignQuotaRequest
from vtt.models.role import init_default_roles
from vtt.utils.time import utcnow

LITERAL = '<img src=x onerror="window.cqInjected=1"> {total} & Zeile'


@pytest.fixture
def quota_site(tmp_path, monkeypatch):
    monkeypatch.setattr(TestingConfig, 'SQLALCHEMY_DATABASE_URI', f'sqlite:///{tmp_path}/quota.db')
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        init_default_roles(db.session)
        role = Role.query.filter_by(name='Player').first()
        people = {
            'dm': dict(profile_tier='dm', active_campaigns_quota=2),
            'owner': dict(profile_tier='player', platform_role='owner'),
            'player': dict(profile_tier='player'),
        }
        ids = {}
        for name, fields in people.items():
            user = User(username=f'cq-{name}', email=f'cq-{name}@example.test', role_id=role.id,
                        is_active=True, account_state='active', **fields)
            user.set_password('Quota-Pass-123!')
            db.session.add(user); db.session.flush(); ids[name] = user.id
        db.session.commit()
        tokens = {name: create_access_token(identity=str(i)) for name, i in ids.items()}
    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield app, f'http://127.0.0.1:{server.server_port}', ids, tokens
    finally:
        server.shutdown(); thread.join(timeout=5); server.server_close()
        with app.app_context():
            db.session.remove(); db.engine.dispose()


@pytest.fixture
def browser_page(quota_site):
    from playwright.sync_api import sync_playwright

    app, origin, ids, tokens = quota_site
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        page = context.new_page()
        page.set_default_timeout(8000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))

        def login(name):
            context.clear_cookies()
            context.add_cookies([{'name': 'access_token_cookie', 'value': tokens[name], 'url': origin, 'httpOnly': True}])
        yield page, origin, app, ids, login
        browser.close()
        assert errors == [], errors


def _open_profile(page, origin):
    page.goto(origin + '/dashboard')
    page.locator('.vtt-account-profile').first.click()
    expect(page.locator('#reviewOwnProfile dl')).to_contain_text('Charaktere')


def _seed_pending(app, requester_id, desired=4, reason=LITERAL):
    with app.app_context():
        row = CampaignQuotaRequest(requester_id=requester_id, current_quota=2, desired_total=desired,
                                   reason=reason, status='pending', pending_key=requester_id, created_at=utcnow())
        db.session.add(row); db.session.commit()
        request_id = row.id
        db.session.remove()
    return request_id


def _quota(app, user_id):
    with app.app_context():
        value = db.session.get(User, user_id).active_campaigns_quota
        db.session.remove()
    return value


def test_dm_requests_and_cancels_without_quota_change(browser_page):
    page, origin, app, ids, login = browser_page
    login('dm')
    _open_profile(page, origin)
    panel = page.locator('#reviewOwnProfile .cq-panel')
    expect(panel).to_contain_text('Aktuelles Limit')
    expect(panel.locator('.cq-fact').first).to_contain_text('2')
    expect(panel).to_contain_text('Eine Anfrage ändert dein Limit nicht')
    panel.get_by_label('Gewünschtes Gesamtlimit').fill('2')
    panel.get_by_label('Begründung').fill('zu niedrig')
    panel.get_by_role('button', name='Anfrage senden').click()
    expect(panel.locator('.cq-status')).to_contain_text('ganze Zahl über deinem aktuellen Limit')
    panel.get_by_label('Gewünschtes Gesamtlimit').fill('4')
    panel.get_by_label('Begründung').fill(LITERAL)
    panel.get_by_role('button', name='Anfrage senden').click()
    expect(panel.locator('.cq-status')).to_contain_text('Dein Limit bleibt unverändert')
    expect(panel.locator('.cq-history .cq-literal').first).to_have_text(LITERAL)
    assert panel.locator('img').count() == 0
    assert page.evaluate('window.cqInjected') is None
    expect(panel.get_by_role('button', name='Anfrage senden')).to_have_count(0)
    assert _quota(app, ids['dm']) == 2
    panel.get_by_role('button', name='Anfrage zurückziehen').click()
    expect(panel.locator('.cq-status')).to_contain_text('Anfrage zurückgezogen')
    expect(panel.locator('.cq-history')).to_contain_text('Anfrage zurückgezogen')
    assert _quota(app, ids['dm']) == 2


def test_ineligible_profile_shows_values_without_extra_controls(browser_page):
    page, origin, _, _, login = browser_page
    login('player')
    _open_profile(page, origin)
    panel = page.locator('#reviewOwnProfile .cq-panel')
    expect(panel).to_contain_text('nicht zugewiesen')
    expect(panel).to_contain_text('nur für Konten möglich')
    # The existing profile contract keeps a single (close) button for such accounts.
    expect(page.locator('#reviewOwnProfile button')).to_have_count(1)
    expect(page.locator('#reviewOwnProfile dl')).to_have_count(1)


def test_owner_reviews_with_manual_total_exactly_once(browser_page):
    page, origin, app, ids, login = browser_page
    request_id = _seed_pending(app, ids['dm'])
    decisions = []
    page.on('request', lambda r: decisions.append(r) if r.url.endswith('/decision') else None)
    login('owner')
    _open_profile(page, origin)
    panel = page.locator('#reviewOwnProfile .cq-panel')
    panel.get_by_role('button', name='Anfragen prüfen').click()
    entry = panel.locator('.cq-review .cq-item').first
    expect(entry).to_contain_text('cq-dm')
    expect(entry).to_contain_text('Aktuelles Limit: 2')
    expect(entry.locator('.cq-literal').first).to_have_text(LITERAL)
    total = entry.get_by_label('Neues Gesamtlimit (manuell festlegen)')
    expect(total).to_have_value('')
    expect(entry.locator('.cq-confirm')).to_be_hidden()
    entry.get_by_role('button', name='Genehmigen …').click()
    expect(panel.locator('.cq-review .cq-status')).to_contain_text('ganzzahliges neues Gesamtlimit')
    assert decisions == []
    total.fill('5')
    entry.get_by_role('button', name='Genehmigen …').click()
    expect(entry.locator('.cq-confirm-text')).to_have_text('Limit von cq-dm von 2 auf 5 setzen?')
    expect(entry.locator('.cq-actions').first).to_be_hidden()
    assert decisions == []
    entry.get_by_role('button', name='Gesamtlimit bestätigen').click()
    expect(panel.locator('.cq-review .cq-status')).to_contain_text('Gesamtlimit von 5')
    assert len(decisions) == 1
    assert json.loads(decisions[0].post_data) == dict(decision='approve', expected_current_quota=2, approved_total=5)
    assert decisions[0].headers['x-quota-account'] == str(ids['owner'])
    assert _quota(app, ids['dm']) == 5
    with app.app_context():
        assert db.session.get(CampaignQuotaRequest, request_id).status == 'approved'
        assert AuditLog.query.filter_by(action='campaign_quota_request_approved').count() == 1
        db.session.remove()
    expect(panel).to_contain_text('Keine offenen Anfragen.')


def test_stale_review_reports_conflict_and_never_replays(browser_page):
    page, origin, app, ids, login = browser_page
    _seed_pending(app, ids['dm'])
    decisions = []
    page.on('request', lambda r: decisions.append(r) if r.url.endswith('/decision') else None)
    login('owner')
    _open_profile(page, origin)
    panel = page.locator('#reviewOwnProfile .cq-panel')
    panel.get_by_role('button', name='Anfragen prüfen').click()
    entry = panel.locator('.cq-review .cq-item').first
    expect(entry).to_contain_text('cq-dm')
    with app.app_context():
        db.session.get(User, ids['dm']).active_campaigns_quota = 3
        db.session.commit(); db.session.remove()
    entry.get_by_label('Neues Gesamtlimit (manuell festlegen)').fill('6')
    entry.get_by_role('button', name='Genehmigen …').click()
    entry.get_by_role('button', name='Gesamtlimit bestätigen').click()
    expect(entry).to_contain_text('Es wurde nichts gespeichert')
    page.wait_for_timeout(500)
    assert len(decisions) == 1
    assert _quota(app, ids['dm']) == 3
    entry.get_by_role('button', name='Liste neu laden').click()
    expect(panel.locator('.cq-review .cq-item').first).to_contain_text('Aktuelles Limit: 3')


def test_reject_keeps_quota_and_shows_literal_note_to_requester(browser_page):
    page, origin, app, ids, login = browser_page
    _seed_pending(app, ids['dm'])
    login('owner')
    _open_profile(page, origin)
    panel = page.locator('#reviewOwnProfile .cq-panel')
    panel.get_by_role('button', name='Anfragen prüfen').click()
    entry = panel.locator('.cq-review .cq-item').first
    entry.get_by_label('Notiz (optional, für die anfragende Person sichtbar)').fill('<b>später</b>')
    entry.get_by_role('button', name='Ablehnen').click()
    expect(panel.locator('.cq-review .cq-status')).to_contain_text('bleibt unverändert')
    assert _quota(app, ids['dm']) == 2
    login('dm')
    _open_profile(page, origin)
    history = page.locator('#reviewOwnProfile .cq-history')
    expect(history).to_contain_text('Anfrage abgelehnt')
    expect(history.locator('.cq-note .cq-literal')).to_have_text('<b>später</b>')
    assert history.locator('b').count() == 0


def test_mismatched_account_response_is_never_rendered(browser_page):
    page, origin, _, ids, login = browser_page
    login('dm')

    def foreign(route):
        route.fulfill(status=200, content_type='application/json', body=json.dumps(dict(
            accountId=ids['owner'], quota=dict(current=99, assigned=True, active_count=0),
            eligible=True, ineligible_reason=None, can_review=True,
            limits=dict(max_total=2147483647, text_max=500, per_24h=5, used_24h=0), requests=[])))
    page.route('**/api/campaign-quota/requests', foreign)
    _open_profile(page, origin)
    panel = page.locator('#reviewOwnProfile .cq-panel')
    expect(panel).to_contain_text('Das angemeldete Konto hat sich geändert')
    expect(panel).not_to_contain_text('99')
    expect(panel.locator('button, form')).to_have_count(0)


def test_late_quota_response_after_close_does_not_mount(browser_page):
    page, origin, _, _, login = browser_page
    login('dm')
    held = []
    page.route('**/api/campaign-quota/requests', lambda route: held.append(route))
    _open_profile(page, origin)
    for _ in range(40):
        if held:
            break
        page.wait_for_timeout(50)
    assert held, 'quota request should be in flight'
    page.locator('#reviewOwnProfile > button').click()
    expect(page.locator('#reviewOwnProfile')).to_have_count(0)
    held[0].continue_()
    page.wait_for_timeout(500)
    expect(page.locator('.cq-panel')).to_have_count(0)


def test_failed_quota_panel_keeps_profile_counts(browser_page):
    page, origin, _, _, login = browser_page
    login('dm')
    page.route('**/api/campaign-quota/requests', lambda route: route.fulfill(
        status=500, content_type='application/json', body='{"error":"boom"}'))
    _open_profile(page, origin)
    page.wait_for_timeout(500)
    expect(page.locator('#reviewOwnProfile .cq-panel')).to_have_count(0)
    expect(page.locator('#reviewOwnProfile dl')).to_contain_text('Eigene Kampagnen')


@pytest.mark.parametrize('width', [390, 1440])
def test_review_layout_fits_viewport(browser_page, width):
    page, origin, app, ids, login = browser_page
    _seed_pending(app, ids['dm'], reason='x' * 400)
    login('owner')
    page.set_viewport_size({'width': width, 'height': 900})
    _open_profile(page, origin)
    page.locator('#reviewOwnProfile .cq-panel').get_by_role('button', name='Anfragen prüfen').click()
    expect(page.locator('#reviewOwnProfile .cq-review .cq-item')).to_have_count(1)
    dialog_overflow = page.evaluate(
        "() => {const d=document.getElementById('reviewOwnProfile');return d.scrollWidth>d.clientWidth+1}")
    page_overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
    assert not dialog_overflow and not page_overflow
