"""Authorized table UI journeys, local shape geometry and real vision controls."""
import math
import json
from pathlib import Path
import pytest
from playwright.sync_api import expect, sync_playwright
from tests.test_personal_actions_browser import action_site  # noqa:F401
from tests.test_presentation_browser import preferences, contrast
from vtt.extensions import db
from vtt.models import CampaignMap, TokenState
from vtt.models.campaign_map_scale import CampaignMapScale

PROBE = """window.__dmViewportBindings=[];
const add=EventTarget.prototype.addEventListener;
EventTarget.prototype.addEventListener=function(type,fn,...rest){
 if(this.id==='mapViewport' && /_placeLight|_placeWall/.test(String(fn))) window.__dmViewportBindings.push(type);
 return add.call(this,type,fn,...rest);
};"""


def click_world(page, x, y):
    box=page.locator('#mapWorld').bounding_box()
    width=float(page.locator('#mapWorld').get_attribute('data-map-width'))
    height=float(page.locator('#mapWorld').get_attribute('data-map-height'))
    client_x,client_y=box['x']+x*box['width']/width,box['y']+y*box['height']/height
    diagnostic=page.evaluate('([x,y])=>{const n=document.elementFromPoint(x,y);return {x,y,target:n?.outerHTML.slice(0,200),token:!!n?.closest(".token-marker"),floating:!!n?.closest(".floating")}}',[client_x,client_y])
    page.mouse.click(client_x,client_y)
    diagnostic.update(page.evaluate('()=>({activeTool:document.querySelector(".tool-btn.active[data-tool]")?.dataset.tool,sheetOpen:!document.getElementById("tableSheet").hidden,announced:document.getElementById("measureAnnounce").textContent})'))
    return diagnostic


@pytest.mark.parametrize('role,width,engine', [('dm',1440,'chromium'),('player',390,'firefox')])
def test_measure_shapes_real_controls_and_independent_player_surface(action_site, role, width, engine):
    app,origin,info=action_site
    with app.app_context():
        map_=CampaignMap.query.filter_by(campaign_id=info['campaign']).one()
        map_.width=1200;map_.height=900;map_.grid_size=50
        db.session.add(CampaignMapScale(map_id=map_.id,meters_per_square=1.5,updated_by=map_.created_by));db.session.commit()
    with sync_playwright() as p:
        browser=getattr(p,engine).launch(headless=True,args=['--no-sandbox'] if engine=='chromium' else [])
        ctx=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce');ctx.add_init_script(PROBE)
        preferences(ctx,language='en' if role=='player' else 'de',theme='night' if role=='player' else 'paper')
        ctx.add_cookies([{'name':'access_token_cookie','value':info[role+'_auth'],'url':origin,'httpOnly':True}])
        page=ctx.new_page();page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat={role}")
        expect(page.locator('#mapWorld')).to_have_attribute('data-has-map','true',timeout=30000)
        page.locator('[data-tool=measure]').click();expect(page.locator('#measureOptions')).to_be_visible()
        contrast(page, '#measureOptions label,#measureOptions select')
        for shape in ['square','circle','cone']:
            page.locator('#measureShape').select_option(shape);first=click_world(page,100,150);second=click_world(page,200,200)
            marker=page.locator(f'#measureLayer [data-shape={shape}]')
            if marker.count()!=1:
                diagnostic={'first':first,'second':second,'overlay':page.locator('#measureLayer').inner_html(),'errors':errors}
                Path('/tmp/feedback-b07-browser-failure.json').write_text(json.dumps(diagnostic,indent=2))
                page.screenshot(path='/tmp/feedback-b07-browser-failure.png')
                raise AssertionError(json.dumps(diagnostic))
            expect(page.locator('#measureLayer .measure-label')).to_contain_text('m')
            expect(page.locator('#tableSheet')).to_be_hidden()
            if shape=='square':assert float(marker.locator('rect').get_attribute('width'))==100 and float(marker.locator('rect').get_attribute('height'))==100
            elif shape=='circle':assert abs(float(marker.locator('circle').get_attribute('r'))-math.hypot(100,50))<1
            else:
                points=[tuple(map(float,row.split(','))) for row in marker.locator('polygon').get_attribute('points').split()]
                assert len(points)==3 and abs(math.dist(points[1],points[2])-math.hypot(100,50))<1
            page.keyboard.press('Escape');page.keyboard.press('Escape');expect(page.locator('#measureLayer')).to_be_empty()
        page.locator('#measureShape').select_option('circle')
        token=page.locator('.token-marker').first;before=token.get_attribute('style');token.click();expect(page.locator('#tableSheet')).to_be_hidden();assert token.get_attribute('style')==before
        page.keyboard.press('Escape');page.keyboard.press('Escape')
        page.locator('#measureShape').select_option('line');click_world(page,100,150);click_world(page,200,200)
        expect(page.locator('#measureLayer line')).to_have_count(1)
        page.locator('[data-tool=select]').click();expect(page.locator('#measureOptions')).to_be_hidden();expect(page.locator('#measureLayer')).to_be_empty()
        if role=='player':
            expect(page.locator('#toolWall,#toolLight,#wallEditPopover,#lightEditPopover')).to_have_count(0)
            assert page.evaluate('window.__dmViewportBindings')==[]
            assert not page.evaluate('!!window.PlayDMSurface')
        else:assert len(page.evaluate('window.__dmViewportBindings'))==2
        assert page.evaluate('document.documentElement.scrollWidth')<=width+1
        assert not errors,errors
        ctx.close();browser.close()


def test_dm_light_wall_edit_reload_and_delete_through_ui(action_site):
    app,origin,info=action_site
    with app.app_context():
        map_=CampaignMap.query.filter_by(campaign_id=info['campaign']).one();map_.width=1200;map_.height=900;db.session.commit()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        ctx.add_cookies([{'name':'access_token_cookie','value':info['dm_auth'],'url':origin,'httpOnly':True}]);page=ctx.new_page();page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('dialog', lambda dialog: dialog.accept())
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat=dm")
        expect(page.locator('#toolLight')).to_be_visible(timeout=30000)
        page.locator('#toolLight').click();click_world(page,450,350);expect(page.locator('.vision-light-marker')).to_have_count(1)
        page.locator('.vision-light-dot').click();expect(page.locator('#lightEditPopover')).to_be_visible()
        page.locator('#lightEditBright').fill('150');page.locator('#lightEditBright').press('Tab');expect(page.locator('.vision-light-bright')).to_have_attribute('r','150')
        page.locator('#btnLightEditClose').click();page.locator('#toolWall').click();click_world(page,150,150);click_world(page,300,150);expect(page.locator('.vision-wall-line')).to_have_count(1)
        click_world(page,225,150);page.locator('#wallEditSight').select_option('none');expect(page.locator('.vision-wall-line.sight-none')).to_have_count(1)
        page.locator('#btnWallEditClose').click();page.reload();expect(page.locator('.vision-wall-line.sight-none')).to_have_count(1);expect(page.locator('.vision-light-bright')).to_have_attribute('r','150')
        click_world(page,225,150);page.locator('#btnWallDelete').click();expect(page.locator('.vision-wall-line')).to_have_count(0)
        page.locator('.vision-light-dot').click();page.locator('#btnLightDelete').click();expect(page.locator('.vision-light-marker')).to_have_count(0)
        assert not errors,errors
        ctx.close();browser.close()


def test_two_clients_with_fog_receive_successive_edits_and_reload(action_site):
    app,origin,info=action_site
    with app.app_context():
        map_=CampaignMap.query.filter_by(campaign_id=info['campaign']).one()
        map_.width=1200;map_.height=900;map_.grid_size=50;map_.fog_enabled=True
        token=db.session.get(TokenState,info['token']);token.x=200;token.y=200;token.sight_range=100;token.metadata_json={'position_mode':'pixels'};db.session.commit()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        contexts=[];pages={};errors=[]
        for role in ['dm','player']:
            ctx=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');contexts.append(ctx)
            ctx.add_cookies([{'name':'access_token_cookie','value':info[role+'_auth'],'url':origin,'httpOnly':True}])
            page=ctx.new_page();page.set_default_timeout(30000);page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat={role}")
            expect(page.locator('#tableDockTabs')).to_be_visible(timeout=30000);pages[role]=page
        dm,player=pages['dm'],pages['player']
        expect(player.locator('.fog-cell')).to_have_count(432)
        dm.locator('#toolLight').click();click_world(dm,400,300);expect(dm.locator('.vision-light-marker')).to_have_count(1)
        player.wait_for_function('() => document.querySelectorAll(".fog-cell").length<432')
        dm.locator('.vision-light-dot').click()
        dm.locator('#lightEditDim').fill('350');dm.locator('#lightEditDim').press('Tab');expect(dm.locator('.vision-light-dim')).to_have_attribute('r','350')
        dm.locator('#lightEditBright').fill('300');dm.locator('#lightEditBright').press('Tab');expect(dm.locator('.vision-light-bright')).to_have_attribute('r','300')
        dm.locator('#btnLightEditClose').click()
        before=player.locator('.fog-cell').count()
        dm.locator('#toolWall').click();click_world(dm,300,100);click_world(dm,300,800);expect(dm.locator('.vision-wall-line')).to_have_count(1)
        player.wait_for_function('(before) => document.querySelectorAll(".fog-cell").length>before',arg=before)
        after=player.locator('.fog-cell').count();player.reload();expect(player.locator('.fog-cell')).to_have_count(after,timeout=30000)
        expect(player.locator('.vision-light-marker,.vision-wall-line,#toolLight,#toolWall')).to_have_count(0)
        assert 'sequence_gap' not in dm.locator('#activityLog').inner_text()
        assert 'sequence_gap' not in player.locator('#activityLog').inner_text()
        assert not errors,errors
        for ctx in contexts:ctx.close()
        browser.close()
