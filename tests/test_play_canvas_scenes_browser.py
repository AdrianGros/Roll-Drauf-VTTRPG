"""Free camera coordinates and readable scene management through real input."""
import os
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright,expect
from tests.test_personal_actions_browser import action_site  # noqa:F401
from tests.play_shared import add_map
from tests.play_canvas_shared import exercise_camera
from vtt.extensions import db
from vtt.models import Campaign,CampaignMap,GameSession,User,TokenState,SceneLayer
from vtt.play.service import init_scene_stack


@pytest.mark.parametrize('engine,role,width,language,theme',[
 ('chromium','dm',1440,'de','paper'),('firefox','dm',390,'de','paper'),
 ('chromium','player',320,'en','night'),('firefox','owner_player',1024,'en','night')])
def test_free_camera_and_readable_scene_cards(action_site,engine,role,width,language,theme):
    app,origin,info=action_site
    with app.app_context():
        campaign=db.session.get(Campaign,info['campaign']);session=db.session.get(GameSession,info['session']);owner=db.session.get(User,campaign.owner_id)
        map_=db.session.get(CampaignMap,session.map_id);map_.width,map_.height=12000,9000;map_.light_rules={'dimensions_mode':'pixel'}
        child=add_map(campaign,owner,'Porta · eine zweite Szene mit langem Kartennamen')
        stack=init_scene_stack(campaign,session,owner,[map_.id,child.id]);db.session.flush()
        layers=SceneLayer.query.filter_by(scene_stack_id=stack.id).order_by(SceneLayer.order_index).all()
        layers[0].label='Turtonia · der Wald hinter dem nördlichen Stadttor';layers[1].label='Porta · die verborgene Unterseite';
        for layer in layers:layer.is_player_visible=True
        db.session.commit()
        token=db.session.get(TokenState,info['token']);before=(token.x,token.y,token.version)
    seat='player' if role=='owner_player' else role
    with sync_playwright() as p:
        browser=getattr(p,engine).launch(headless=True,args=['--no-sandbox'] if engine=='chromium' else [])
        ctx=browser.new_context(viewport={'width':width,'height':900},reduced_motion='reduce',has_touch=width<600)
        ctx.add_init_script("localStorage.setItem('vtt.display.v1',JSON.stringify({schema:1,theme:'"+theme+"',language:'"+language+"',accent:'default',unit:'m'}))")
        ctx.add_cookies([{'name':'access_token_cookie','value':info[('dm' if role=='owner_player' else role)+'_auth'],'url':origin,'httpOnly':True}])
        page=ctx.new_page();page.set_default_timeout(25000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat={seat}")
        expect(page.locator('body')).to_have_class(__import__('re').compile('play-tool-groups'))
        expect(page.locator('#presenceRoster')).to_contain_text('action-dm' if role in ('dm','owner_player') else 'action-player')
        touch=ctx.new_cdp_session(page) if engine=='chromium' and width<600 else None
        exercise_camera(page,touch)
        with app.app_context():
            db.session.expire_all();token=db.session.get(TokenState,info['token']);assert (token.x,token.y,token.version)==before
        page.locator('#dock-layersWidget').click();rows=page.locator('#layerList .layer-row');expect(rows).to_have_count(2)
        for row in rows.all():
            assert row.evaluate('e=>e.scrollWidth<=e.clientWidth+1')
            assert row.locator('.layer-title').bounding_box()['width']>=70
        if seat=='dm':
            second=rows.nth(1);second.locator('summary').press('Enter')
            expect(second.locator('details')).to_have_attribute('open','')
            expect(second).to_have_attribute('aria-current','false')
            assert second.locator('input').bounding_box()['width']>150
            assert second.locator('select').bounding_box()['width']>150
            second.locator('input').fill('Porta · umbenannt');second.locator('input').press('Tab')
            expect(second.locator('.layer-title')).to_have_text('Porta · umbenannt')
            expect(second.locator('details')).to_have_attribute('open','')
            second.locator('select').select_option(rows.first.get_attribute('data-layer-id'))
            expect(second).to_have_attribute('data-depth','1')
            expect(second.locator('details')).to_have_attribute('open','')
            for button in second.locator('.scene-action').all():
                assert button.evaluate('e=>e.scrollWidth<=e.clientWidth+1')
            second.locator('summary').click()
        else:
            expect(page.locator('.scene-options,[data-act=rename],[data-act=activate]')).to_have_count(0)
            assert not page.evaluate('Boolean(window.PlayFeedbackDM)')
        assert page.evaluate('document.documentElement.scrollWidth')<=width+1
        if os.environ.get('CANVAS_PROOF_DIR'):
            root=Path(os.environ['CANVAS_PROOF_DIR']);root.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(root/f'scenes-{engine}-{role}-{width}.png'))
        assert errors==[],errors
        browser.close()


def test_copy_paste_uses_world_coordinates_after_camera_movement(action_site):
    from tests.play_shared import create_token
    from vtt.play.service import ensure_session_state
    from tests.test_playtable_token_clipboard_browser import client_point,world_point
    from tests.play_canvas_shared import pan_by
    app,origin,info=action_site
    with app.app_context():
        campaign=db.session.get(Campaign,info['campaign']);session=db.session.get(GameSession,info['session'])
        map_=db.session.get(CampaignMap,session.map_id);map_.width,map_.height=1200,900;map_.light_rules={'dimensions_mode':'pixel'}
        token=create_token(campaign,session,ensure_session_state(campaign,session),campaign.owner_id,name='Camera Goblin',token_type='monster',x=350,y=350)
        token.metadata_json={'position_mode':'pixel'};db.session.commit()
        ids={row.id for row in TokenState.query.filter_by(game_session_id=session.id)}
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1440,'height':900},reduced_motion='reduce')
        ctx.add_cookies([{'name':'access_token_cookie','value':info['dm_auth'],'url':origin,'httpOnly':True}])
        page=ctx.new_page();page.set_default_timeout(25000)
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat=dm")
        expect(page.locator('body')).to_have_class(__import__('re').compile('play-tool-groups'),timeout=30000)
        expect(page.locator('#presenceRoster')).to_contain_text('action-dm',timeout=30000)
        page.locator('[data-tool=pan]').click();pan_by(page,40,30)
        page.locator('#btnZoomIn').click();page.locator('[data-tool=select]').click()
        page.locator('.token-marker',has_text='Camera Goblin').click();page.keyboard.press('Control+c')
        target=client_point(page,900,650);expected=world_point(page,*target)
        page.mouse.move(*target);page.keyboard.press('Control+v')
        expect(page.locator('.token-marker')).to_have_count(3)
        with app.app_context():
            db.session.expire_all();new=[t for t in TokenState.query.filter_by(game_session_id=info['session']) if t.id not in ids]
            assert len(new)==1 and abs(new[0].x-expected[0])<=70 and abs(new[0].y-expected[1])<=70
        browser.close()
