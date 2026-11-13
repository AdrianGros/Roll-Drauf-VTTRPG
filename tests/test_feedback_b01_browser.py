"""Real selection controls and normal Back→Maps navigation, no copied JS methods."""
import pytest

from tests.test_feedback_invocation_prerequisites import PREFIX, warlock
from tests.test_personal_actions_browser import action_site  # noqa: F401
from tests.test_srd_creator_api import data  # noqa: F401
from tests.test_srd_creator_browser import site, wiz, _saved  # noqa: F401


def test_creator_disables_missing_pact_and_rechecks_after_selection(wiz, data):
    from playwright.sync_api import expect
    page, origin, app, info = wiz
    page.goto(origin + '/srd-creator')
    page.locator('#scNewQuick').click()
    expect(page.locator('#scBuilder')).to_be_visible()
    state = warlock(data)
    state['featureChoices']['warlock']['eldritch-invocations'] = [PREFIX + 'eldritch-mind']
    page.evaluate('(state)=>window.SrdCreator.mutate(s=>{Object.keys(s).forEach(k=>delete s[k]);Object.assign(s,state);})', state)
    _saved(page)
    smite = page.get_by_role('checkbox', name=__import__('re').compile('^Schauerliches Niederstrecken'))
    pact = page.get_by_role('checkbox', name=__import__('re').compile('^Pakt der Klinge'))
    expect(smite).to_be_disabled()
    expect(smite.locator('xpath=../..')).to_contain_text('Erfordert die gültige Anrufung')
    pact.check()
    _saved(page)
    expect(smite).to_be_enabled()
    smite.check()
    _saved(page)
    pact.uncheck()
    _saved(page)
    expect(smite).to_be_checked()
    expect(smite).to_be_enabled()  # explicit correction remains possible
    smite.uncheck()
    _saved(page)
    expect(smite).to_be_disabled()


def test_progression_rechecks_pacts_without_losing_selected_options(wiz, data):
    from playwright.sync_api import expect
    from vtt.extensions import db
    from vtt.models import Character
    from vtt.rules_content.creator_drafts import character_values
    from vtt.rules_content.creator_rules import evaluate
    page, origin, app, info = wiz
    state = warlock(data, 4)
    state['featureChoices']['warlock']['eldritch-invocations'] = [PREFIX + x for x in
        ['eldritch-mind', 'devils-sight', 'fiendish-vigor']]
    with app.app_context():
        char = Character(user_id=info['user_id'], **character_values(data, state, evaluate(data, state), draft_id=1, finalized_at='2026-11-13T09:00:00Z'))
        char.xp = 6500
        db.session.add(char)
        db.session.commit()
        cid = char.id
    page.goto(f'{origin}/character-sheet?id={cid}&mode=edit')
    page.get_by_role('tab', name='Verwaltung', exact=True).click()
    page.get_by_role('button', name='Stufe 5 aufsteigen').click()
    smite = page.locator(f'#srdWizard input[value="{PREFIX}eldritch-smite"]')
    pact = page.locator(f'#srdWizard input[value="{PREFIX}pact-of-the-blade"]')
    expect(smite).to_be_disabled()
    expect(smite.locator('xpath=..')).to_contain_text('Erfordert die gültige Anrufung')
    pact.check()
    expect(smite).to_be_enabled()
    smite.check()
    expect(smite).to_be_checked()
    pact.uncheck()
    expect(smite.locator('xpath=..')).to_contain_text('Erfordert die gültige Anrufung')
    expect(smite).to_be_enabled()
    smite.uncheck()
    expect(smite).to_be_disabled()


@pytest.mark.parametrize('role', ['dm', 'player'])
def test_back_maps_is_reachable_without_role_elevation(action_site, role):
    from playwright.sync_api import sync_playwright, expect
    app, origin, info = action_site
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(reduced_motion='reduce')
        context.add_cookies([{'name': 'access_token_cookie', 'value': info[f'{role}_auth'], 'url': origin, 'httpOnly': True}])
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat={role}")
        page.wait_for_function('() => !!window.RollDraufTable')
        if role == 'player':
            assert not page.evaluate('() => !!window.PlayDMSurface')
        page.locator('#btnBack').click()
        page.locator('#appMenu [data-book-return-target="/mapmaker"]').click()
        # /mapmaker is the established UI entry; its existing template redirects
        # to the static editor document, where relative asset paths resolve.
        page.wait_for_url(origin + '/static/mapmaker/index.html')
        expect(page.locator('#cloudSave')).to_be_visible()
        assert not errors, errors
        context.close()
        browser.close()
