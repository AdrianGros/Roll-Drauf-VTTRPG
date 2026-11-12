"""Shared calendar -> actual poll creation -> Firefox vote -> reload -> schedule."""
from datetime import datetime, timedelta
import pytest
from tests.test_personal_actions_browser import action_site  # noqa:F401
from vtt.extensions import db
from vtt.models import GameSession

@pytest.mark.parametrize('width,language,theme', [(1440, 'de', 'paper'), (390, 'en', 'night')])
def test_own_calendar_and_manager_poll_roundtrip_with_firefox_player(action_site, width, language, theme):
    from playwright.sync_api import sync_playwright, expect
    from tests.test_presentation_browser import preferences
    app, origin, info = action_site
    with app.app_context():
        session=GameSession(campaign_id=info['campaign'],name='Gemeinsam planen',status='scheduled')
        db.session.add(session);db.session.commit();sid=session.id
    with sync_playwright() as p:
        chrome=p.chromium.launch(headless=True,args=['--no-sandbox']);ff=p.firefox.launch(headless=True)
        dc=chrome.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        pc=ff.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        for context,kind in ((dc,'dm'),(pc,'player')):
            preferences(context,theme=theme,language=language)
            context.add_cookies([{'name':'access_token_cookie','value':info[kind+'_auth'],'url':origin,'httpOnly':True}])
        dm=dc.new_page();player=pc.new_page();errors=[]
        for page in (dm,player):
            page.set_default_timeout(30000);page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('dialog',lambda d:d.accept())
        dm.goto(origin+'/campaigns')
        own=dm.locator('[data-own-calendar]')
        expect(own.locator('[data-calendar-content]')).to_have_attribute('aria-busy','false',timeout=30000)
        expect(own.locator(f'[data-alert-session="{sid}"]')).to_be_visible()
        own.locator(f'[data-alert-session="{sid}"] a').click()
        planner=dm.locator('[data-campaign-planner]')
        expect(planner.locator('[data-polls]')).to_have_attribute('aria-busy','false',timeout=30000)
        planner.locator('[data-tool="poll"] summary').click()
        planner.locator('[data-poll-session]').select_option(str(sid))
        planner.locator('[data-poll-title]').fill('Unser Spielabend')
        first=(datetime.now()+timedelta(days=2)).replace(hour=19,minute=0,second=0,microsecond=0)
        for i,field in enumerate(planner.locator('[data-option-local]').all()):
            field.fill((first+timedelta(days=i)).isoformat(timespec='minutes'))
        planner.locator('[data-poll-form] [type=submit]').click()
        expect(planner.locator('[data-poll]')).to_have_count(1,timeout=30000)
        player.goto(f"{origin}/campaigns?campaign_id={info['campaign']}")
        poll=player.locator('[data-campaign-planner] [data-poll]')
        expect(poll).to_be_visible(timeout=30000)
        expect(poll.locator('[data-finalize]')).to_have_count(0)
        expect(poll.locator('[data-participant]')).to_have_count(0)
        for option in poll.locator('[data-option-id].sc-option').all():
            option.locator('[data-vote=yes]').click()
            expect(option.locator('[data-vote=yes]')).to_have_attribute('aria-pressed','true')
        player.reload()
        expect(poll.locator('[data-vote=yes][aria-pressed=true]')).to_have_count(2,timeout=30000)
        dm.reload()
        planner=dm.locator('[data-campaign-planner]')
        expect(planner.locator('[data-participant]')).not_to_have_count(0,timeout=30000)
        planner.locator('[data-finalize]').first.click()
        expect(planner.locator('[data-poll]')).to_have_count(0,timeout=30000)
        for page in (dm,player):
            page.goto(origin+'/campaigns')
            event=page.locator(f'[data-own-calendar] [data-session-id="{sid}"]')
            expect(event).to_contain_text('Gemeinsam planen',timeout=30000)
            assert page.evaluate('document.documentElement.scrollWidth')<=width+1
        with app.app_context():
            assert db.session.get(GameSession,sid).scheduled_at is not None
            assert GameSession.query.filter_by(name='Gemeinsam planen').count()==1
        assert not errors,errors
        chrome.close();ff.close()
