"""Review feedback through the existing creator, navigation and rule reader."""
import json
from pathlib import Path
from playwright.sync_api import expect

from tests.test_srd_creator_browser import site, wiz  # noqa: F401
from vtt.extensions import db
from vtt.models.review_web import ReviewPrintRequest


def test_creator_rebuild_preserves_working_field_and_open_details(wiz):
    page, origin, _, _ = wiz
    page.goto(origin + '/srd-creator')
    page.locator('#scNewRandom').click()
    expect(page.locator('#scBuilder')).to_be_visible()
    page.locator('#scModeQuick').click()
    expect(page.locator('#scId-name')).to_be_attached()
    # An actual rule-choice disclosure must survive a rebuild further down the page.
    detail = page.locator('#scStepBody details').first
    detail.locator('summary').click()
    field = page.locator('#scId-name')
    field.fill('Brunhild Silberhand')
    field.evaluate('(node) => {node.focus();node.setSelectionRange(3,8)}')
    before = field.bounding_box()['y']
    page.evaluate('SrdCreator.renderAll()')
    expect(field).to_be_focused()
    assert abs(field.bounding_box()['y'] - before) <= 2
    assert field.evaluate('node => [node.selectionStart,node.selectionEnd]') == [3, 8]
    assert detail.evaluate('node => node.open')
    expect(page.locator('#scSave')).to_have_text('Gespeichert')
    page.evaluate('SrdCreator.renderAll()')
    expect(field).to_be_focused()
    assert abs(field.bounding_box()['y'] - before) <= 2
    assert detail.evaluate('node => node.open')


def test_profile_group_navigation_and_reset_preserve_drafts(wiz):
    page, origin, _, _ = wiz
    page.goto(origin + '/dashboard')
    group = page.locator('.vtt-nav-play').first
    expect(group.locator('a[href="/characters"]')).to_be_hidden()
    group.locator('summary').click()
    expect(group.locator('a[href="/characters"]')).to_be_visible()
    group.locator('summary').press('Escape')
    expect(group.locator('a[href="/characters"]')).to_be_hidden()
    page.locator('.vtt-account-profile').first.click()
    expect(page.locator('#reviewOwnProfile')).to_contain_text('srd-wizard')
    expect(page.locator('#reviewOwnProfile dl')).to_contain_text('Charaktere')
    page.locator('#reviewOwnProfile button').click()
    page.evaluate("localStorage.setItem('review-draft-sentinel','keep');VTTDisplay.update({theme:'night',accent:'teal',unit:'ft',stickyPortrait:true})")
    page.set_viewport_size({'width': 320, 'height': 800})
    page.locator('#vttDisplayOpen').click()
    expect(page.locator('#vttDisplayDialog')).to_be_visible()
    overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
    if overflow:
        Path('/app/docs/proofs/review-web-2026-11-18/layout-debug.json').write_text(json.dumps(page.evaluate("({width:innerWidth,doc:document.documentElement.scrollWidth,body:document.body.scrollWidth,nodes:Array.from(document.querySelectorAll('body *')).filter(n=>n.getBoundingClientRect().right>innerWidth+1).map(n=>({tag:n.tagName,id:n.id,cls:n.className,right:n.getBoundingClientRect().right,width:n.getBoundingClientRect().width,overflow:getComputedStyle(n).overflowX,position:getComputedStyle(n).position})).slice(0,30)})"), indent=2))
    assert not overflow
    page.locator('#vttDisplayReset').click()
    expect(page.locator('html')).to_have_attribute('data-vtt-theme', 'paper')
    assert page.evaluate('VTTDisplay.get().accent') == 'default'
    assert page.evaluate('VTTDisplay.get().unit') == 'm'
    assert page.evaluate("localStorage.getItem('review-draft-sentinel')") == 'keep'
    page.reload()
    expect(page.locator('.vtt-account-name').first).to_have_text('srd-wizard')


def test_navigation_and_profile_are_available_before_book_data(wiz):
    page, origin, _, _ = wiz
    requests = []
    page.route('**/api/dashboard/home', lambda route: requests.append(route))
    page.goto(origin + '/dashboard', wait_until='domcontentloaded')
    expect(page.locator('.book-dashboard-ribbon').first).to_be_visible()
    page.locator('.vtt-account-profile').first.click()
    expect(page.locator('#reviewOwnProfile')).to_contain_text('srd-wizard')
    page.locator('#reviewOwnProfile button').click()
    for route in requests:
        route.continue_()
    page.unroute('**/api/dashboard/home')
    expect(page.locator('.book-dashboard-page')).to_be_visible(timeout=20000)


def test_print_requires_two_confirmations_and_records_one_ui_request(wiz):
    page, origin, app, _ = wiz
    page.goto(origin + '/regelwerk')
    expect(page.locator('#regelwerkArticle')).to_have_attribute('aria-busy', 'false')
    page.evaluate('() => {window.reviewPrintCalls=0;window.print=()=>window.reviewPrintCalls++}')
    page.locator('#regelwerkPrint').click()
    expect(page.locator('#reviewPrintDialog')).to_contain_text('aktuell angezeigte Regeltext')
    assert page.evaluate('window.reviewPrintCalls') == 0
    page.locator('#reviewPrintNext').click()
    assert page.evaluate('window.reviewPrintCalls') == 0
    page.locator('#reviewPrintConfirm').click()
    expect(page.locator('#reviewPrintDialog')).to_have_count(0)
    assert page.evaluate('window.reviewPrintCalls') == 1
    with app.app_context():
        request = ReviewPrintRequest.query.one()
        assert request.ruleset == 'srd-5.2.1-de'
        assert request.document_id != 'current-view'
        assert request.user_id > 0
        db.session.remove()
    # Cancellation has no analytics side effect.
    page.locator('#regelwerkPrint').click()
    page.locator('#reviewPrintDialog').get_by_role('button', name='Abbrechen').click()
    assert page.evaluate('window.reviewPrintCalls') == 1


def test_rule_content_language_is_independent_of_ui(wiz):
    page, origin, _, _ = wiz
    page.goto(origin + '/regelwerk/compendium?locale=de')
    expect(page.locator('#cpContentLanguage')).to_have_value('de')
    page.locator('#cpContentLanguage').select_option('en')
    expect(page).to_have_url(origin + '/regelwerk/compendium?locale=en&type=spell')
    expect(page.locator('html')).to_have_attribute('lang', 'de')
    expect(page.locator('#cpRulebookLink')).to_have_attribute('href', '/regelwerk?locale=en')
    page.locator('#cpRulebookLink').click()
    expect(page.locator('#regelwerkArticle')).to_have_attribute('lang', 'en')
    expect(page.locator('#regelwerkArticle')).to_have_attribute('aria-busy', 'false')
