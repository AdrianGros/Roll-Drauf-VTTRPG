"""Visible real-browser journeys for scoped text threads and world/campaign links."""
from uuid import uuid4

import pytest
from playwright.sync_api import expect, sync_playwright

from tests.test_personal_actions_browser import action_site  # noqa: F401
from tests.test_presentation_browser import preferences
from tests.test_review_domain import register
from vtt.extensions import db
from vtt.models import CampaignMember, User
from vtt.models.review_domain import AtlasCampaignLink, ReviewThreadMessage


@pytest.fixture
def domain_site(action_site):
    app, origin, info = action_site
    register(app)
    with app.app_context():
        User.query.filter_by(username='action-dm').one().storage_quota_gb = 1
        db.session.commit()
    return app, origin, info


@pytest.mark.parametrize('engine,width,language', [('chromium', 1440, 'de'), ('firefox', 390, 'en')])
def test_private_thread_visible_plain_text_retry_reload_and_revocation(domain_site, engine, width, language):
    app, origin, info = domain_site
    with sync_playwright() as p:
        browser = getattr(p, engine).launch(headless=True, args=['--no-sandbox'] if engine == 'chromium' else [])
        context = browser.new_context(viewport={'width': width, 'height': 1000}, reduced_motion='reduce')
        preferences(context, language=language)
        context.add_cookies([{'name': 'access_token_cookie', 'value': info['dm_auth'], 'url': origin, 'httpOnly': True}])
        pair = context.request.post(origin + '/api/private-conversations', data={
            'campaign_id': info['campaign'], 'recipient_user_id': info['player_id']})
        assert pair.status == 201, pair.text()
        cid = pair.json()['conversation']['id']
        page = context.new_page(); page.set_default_timeout(30000)
        errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(f'{origin}/conversations?id={cid}')
        page.locator('#conversationThreads summary').click()
        page.locator('#threadTitle').fill('<b>Secret side thread</b>')
        page.locator('#threadCreate button').click()
        expect(page.locator('#threadHeading')).to_have_text('<b>Secret side thread</b>')
        expect(page.locator('#threadHeading b')).to_have_count(0)
        tid = int(page.locator('#threadList button').get_attribute('data-thread-id'))
        attempts = []
        def lose_ack(route):
            attempts.append(route.request.post_data_json)
            if len(attempts) == 1:
                response = route.fetch(); assert response.status == 201
                route.abort()
            else:
                route.continue_()
        page.route(f'**/api/review-domain/threads/{tid}/messages', lose_ack)
        page.locator('#threadMessage').fill('<script>Only text</script>')
        page.locator('#threadMessage').locator('..').locator('..').locator('button').click()
        expect(page.locator('#threadMessage')).to_have_attribute('readonly', '')
        expect(page.locator('#conversationThreads [role=status]')).not_to_be_empty()
        with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith(f'/{tid}/messages')) as replay:
            page.locator('#threadMessage').locator('..').locator('..').locator('button').click()
        assert replay.value.status == 200 and replay.value.json()['replayed'] is True
        assert len(attempts) == 2 and attempts[0] == attempts[1]
        expect(page.locator('#threadHistory p')).to_have_text(['<script>Only text</script>'])
        expect(page.locator('#threadHistory script')).to_have_count(0)
        page.reload(); page.locator('#conversationThreads summary').click()
        page.locator(f'[data-thread-id="{tid}"]').click()
        expect(page.locator('#threadHistory p')).to_have_text(['<script>Only text</script>'])
        page.locator('#threadClose').click()
        expect(page.locator('#threadMessage')).to_be_hidden()
        expect(page.locator('#threadClose')).to_have_text('Reopen thread' if language == 'en' else 'Thread wieder öffnen')
        page.locator('#threadClose').click()
        expect(page.locator('#threadMessage')).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth') <= width + 1
        with app.app_context():
            assert ReviewThreadMessage.query.filter_by(thread_id=tid).count() == 1
            # Remaining private participant keeps history but loses all write controls.
            CampaignMember.query.filter_by(campaign_id=info['campaign'], user_id=info['player_id']).one().status = 'left'
            db.session.commit()
        expect(page.locator('#threadMessage')).to_be_hidden(timeout=20000)
        expect(page.locator('#threadCreate')).to_be_hidden()
        expect(page.locator('#threadHistory p')).to_have_count(1)
        context.clear_cookies()
        context.add_cookies([{'name': 'access_token_cookie', 'value': info['player_auth'], 'url': origin, 'httpOnly': True}])
        page.reload()
        expect(page.locator('#conversationHistory li')).to_have_count(0)
        expect(page.locator('#threadHistory li')).to_have_count(0)
        assert not errors, errors
        browser.close()


def test_companion_rule_visible_save_damage_and_explicit_view_lock(domain_site):
    _, origin, info = domain_site
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 390, 'height': 1000}, reduced_motion='reduce')
        preferences(context, language='en')
        context.add_cookies([{'name': 'access_token_cookie', 'value': info['player_auth'], 'url': origin, 'httpOnly': True}])
        response = context.request.put(origin + f'/api/srd-creator/characters/{info["character"]}/companions',
                   data={'companions': [{'name': 'Wolf', 'hpMax': 20, 'hpCurrent': 13, 'ac': 13}]})
        assert response.status == 200, response.text()
        page = context.new_page(); page.set_default_timeout(30000)
        errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(origin + f'/character-sheet?id={info["character"]}&mode=edit')
        page.get_by_role('tab', name='Management', exact=True).click()
        # The parent owns the actual template mount. Exercise this worker's ES
        # module through the same real URL, without editing a shared template.
        page.add_script_tag(type='module', url=origin + '/static/js/review-domain.js')
        page.locator('#companionScaling summary').click()
        card = page.locator('[data-scaling-companion]')
        expect(card).to_contain_text('HP 13/20')
        card.locator('input[type=checkbox]').check()
        numbers = card.locator('input[type=number]')
        numbers.nth(0).fill('10'); numbers.nth(1).fill('5'); numbers.nth(2).fill('2')
        card.locator('button').click()
        expect(card).to_contain_text('HP 34/41')
        page.goto(origin + f'/character-sheet?id={info["character"]}&mode=view')
        page.get_by_role('tab', name='Management', exact=True).click()
        page.add_script_tag(type='module', url=origin + '/static/js/review-domain.js')
        page.locator('#companionScaling summary').click()
        expect(page.locator('[data-scaling-companion] button')).to_be_disabled()
        assert page.evaluate('document.documentElement.scrollWidth') <= 391
        assert not errors, errors
        browser.close()


def test_atlas_optional_campaign_dirty_guard_stale_revision_and_no_implicit_grant(domain_site, tmp_path):
    app, origin, info = domain_site
    app.config.update(LOCAL_STORAGE_PATH=str(tmp_path / 'storage'), STORAGE_PROVIDER='local')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 390, 'height': 1000}, reduced_motion='reduce')
        context.add_cookies([{'name': 'access_token_cookie', 'value': info['dm_auth'], 'url': origin, 'httpOnly': True}])
        page = context.new_page(); page.set_default_timeout(30000)
        errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(origin + '/atlas')
        page.locator('#atlasNewTitle').fill('Campaign world')
        page.locator('#atlasNewCampaign').select_option(str(info['campaign']))
        page.locator('#atlasCreate').click()
        expect(page.locator('#atlasTitle')).to_have_value('Campaign world')
        world = page.url.split('world=')[-1]
        expect(page.locator('#atlasCampaignLinks a')).to_have_text('Hotbar browser')
        page.locator('#atlasSummary').fill('Keep my unsaved draft')
        page.locator('[data-unlink-campaign]').click()
        expect(page.locator('#atlasCampaignLinks [role=status]')).to_contain_text('zuerst')
        expect(page.locator('#atlasSummary')).to_have_value('Keep my unsaved draft')
        expect(page.locator('#atlasCampaignLinks a')).to_have_count(1)
        page.locator('#atlasSave').click()
        expect(page.locator('#atlasAuthorStatus')).to_have_text('Gespeichert.')
        page.locator('[data-unlink-campaign]').click()
        expect(page.locator('#atlasCampaignLinks a')).to_have_count(0)
        page.locator('#atlasLinkCampaign').select_option(str(info['campaign']))
        # Another author action advances world revision while the page has old link state.
        current = context.request.get(origin + f'/api/atlas/worlds/{world}').json()
        current['graph']['summary'] = 'Concurrent server change'
        changed = context.request.put(origin + f'/api/atlas/worlds/{world}', data={
            'revision': current['revision'], 'graph': current['graph']})
        assert changed.status == 200, changed.text()
        page.locator('#atlasCampaignLinks form button').click()
        expect(page.locator('#atlasCampaignLinks [role=status]')).to_contain_text('geändert')
        expect(page.locator('#atlasSummary')).to_have_value('Keep my unsaved draft')
        page.locator('#atlasReload').click()
        expect(page.locator('#atlasSummary')).to_have_value('Concurrent server change')
        page.locator('#atlasLinkCampaign').select_option(str(info['campaign']))
        page.locator('#atlasCampaignLinks form button').click()
        expect(page.locator('#atlasCampaignLinks a')).to_have_count(1)
        assert page.evaluate('document.documentElement.scrollWidth') <= 391
        with app.app_context():
            assert AtlasCampaignLink.query.count() == 1
        player = browser.new_context()
        player.add_cookies([{'name': 'access_token_cookie', 'value': info['player_auth'], 'url': origin, 'httpOnly': True}])
        assert player.request.get(origin + f'/api/review-domain/worlds/{world}/campaigns').status == 404
        assert player.request.get(origin + '/api/atlas/worlds').json()['worlds'] == []
        assert not errors, errors
        browser.close()
