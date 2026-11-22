"""A companion is placed from the personal bar and keeps its table damage."""
import pytest
from playwright.sync_api import sync_playwright, expect
from sqlalchemy.orm.attributes import flag_modified
from tests.test_personal_actions_browser import action_site  # noqa: F401
from vtt.extensions import db
from vtt.models import Character, TokenState
from vtt.models.table_companion import TableCompanionBinding


@pytest.mark.parametrize('engine,width', [('chromium',1440),('firefox',390)])
def test_personal_bar_companion_keeps_identity_and_damage_after_reload(action_site,engine,width):
    app,origin,info=action_site
    with app.app_context():
        char=db.session.get(Character,info['character'])
        char.character_data['srdCompanions']=[dict(id='c12345678',name='Browser Wolf',kind='Wolf',speed='12 m',hpMax=20,hpCurrent=13,ac=13,attacks='',notes='')]
        flag_modified(char,'character_data');db.session.commit()
    with sync_playwright() as p:
        browser=getattr(p,engine).launch(headless=True,args=['--no-sandbox'] if engine=='chromium' else [])
        context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        context.add_init_script("localStorage.setItem('vtt.display.v1',JSON.stringify({schema:1,theme:'night',language:'en',accent:'default',unit:'m'}))")
        context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(20000)
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        route=f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat=player"
        def place():
            page.locator(f".token-marker[data-token-id='{info['token']}']").click()
            page.locator('[data-pa-companions]').click()
            expect(page.locator('#personalCompanionDialog')).to_be_visible()
            expect(page.locator('#paCompanionSelect')).to_contain_text('Browser Wolf')
            expect(page.locator('#paCompanionPlace')).to_be_enabled()
            page.locator('#paCompanionPlace').click()
            expect(page.locator('#personalCompanionDialog')).to_have_count(0)
        page.goto(route);expect(page.locator('#floorViewStatus')).to_be_attached();place()
        with app.app_context():
            binding=TableCompanionBinding.query.one();token_id=binding.token_id
            token=db.session.get(TokenState,token_id)
            assert (token.hp_max,token.hp_current,token.character_id,token.sight_range)==(20,13,None,0)
            token.hp_current=7;token.version+=1;db.session.commit()
        page.reload();place()
        with app.app_context():
            assert TableCompanionBinding.query.one().token_id==token_id
            assert db.session.get(TokenState,token_id).hp_current==7
        assert not page.evaluate('Boolean(window.PlayDMSurface)')
        assert not errors,errors
        browser.close()
