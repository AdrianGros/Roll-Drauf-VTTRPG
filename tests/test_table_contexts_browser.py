"""Real browser composition, parallel tabs and safe reload."""

import pytest

from tests.test_srd_sheet import site  # noqa: F401
from tests.play_shared import add_map, create_campaign, create_session, create_token
from vtt.extensions import db
from vtt.models import User
from vtt.play.service import ensure_session_state


@pytest.mark.parametrize("engine", ["firefox", "chromium"])
def test_owner_parallel_context_compositions_and_reload(site, engine):
    from playwright.sync_api import sync_playwright, expect
    app, origin, info = site
    with app.app_context():
        user = db.session.get(User, info['user_id'])
        campaign = create_campaign(user, 'Browser contexts')
        map_ = add_map(campaign, user)
        session = create_session(campaign, status='in_progress', map_id=map_.id)
        state = ensure_session_state(campaign, session)
        hidden = create_token(campaign, session, state, user.id, name='Private sentinel')
        hidden.visibility = 'dm_only'
        db.session.commit()
        campaign_id, session_id = campaign.id, session.id
    with sync_playwright() as p:
        browser = getattr(p, engine).launch(headless=True, args=['--no-sandbox'] if engine == 'chromium' else [])
        context = browser.new_context(viewport={'width':1440,'height':1000})
        context.add_cookies([{'name':'access_token_cookie','value':info['token'],'url':origin,'httpOnly':True}])
        errors = []
        player, dm = context.new_page(), context.new_page()
        for page in (player, dm):
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.set_default_timeout(30000)
        base = f'{origin}/play?campaign_id={campaign_id}&session_id={session_id}'
        player.goto(base + '&seat=player')
        expect(player.locator('body')).to_have_attribute('data-table-seat', 'player')
        expect(player.locator('#btnInitStack')).to_have_count(0)
        assert not player.locator('script[src="/static/js/play-dm.js"]').count()
        dm.goto(base + '&seat=dm')
        expect(dm.locator('body')).to_have_attribute('data-table-seat', 'dm')
        expect(dm.locator('#btnInitStack')).to_have_count(1)
        expect(dm.locator('script[src="/static/js/play-dm.js"]')).to_have_count(1)
        player.reload()
        expect(player.locator('body')).to_have_attribute('data-table-seat', 'player')
        expect(player.locator('#btnInitStack')).to_have_count(0)
        result = player.evaluate('''async ({c,s}) => {
            const payload = await Auth.makeAuthRequest(`/api/play/campaigns/${c}/sessions/${s}/bootstrap`);
            return {role:payload.session_role, serialized:JSON.stringify(payload)};
        }''', {'c':campaign_id,'s':session_id})
        assert result['role'] == 'PLAYER'
        assert 'Private sentinel' not in result['serialized']
        assert not errors, errors
        browser.close()
