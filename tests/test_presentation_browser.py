"""Preferences across real entry paths; authorized calibration and live ruler refresh."""
import json
from pathlib import Path
import pytest
from tests.test_personal_actions_browser import action_site  # noqa:F401
from vtt.extensions import db
from vtt.models import Character,CampaignMap
from vtt.models.campaign_map_scale import CampaignMapScale

PREFS='vtt.display.v1'

def preferences(context,**values):
    context.add_init_script('if (!localStorage.getItem('+json.dumps(PREFS)+')) localStorage.setItem('+json.dumps(PREFS)+','+json.dumps(json.dumps({'schema':1,'theme':'paper','language':'de','unit':'m','accent':'default','stickyPortrait':False,**values}))+')')


def contrast(page, selector):
    rows=page.locator(selector).evaluate_all('''nodes=>nodes.filter(n=>n.getClientRects().length && !n.disabled).map(n=>{
      const rgba=c=>{const v=c.match(/[\\d.]+/g).map(Number);return [...v.slice(0,3),v.length>3?v[3]:1]};
      const over=(c,b)=>c.slice(0,3).map((v,i)=>v*c[3]+b[i]*(1-c[3]));
      const hex=c=>'#'+c.slice(0,3).map(x=>Math.round(x).toString(16).padStart(2,'0')).join('');
      const chain=[];for(let p=n;p;p=p.parentElement)chain.unshift(p);
      let backs=[[255,255,255]];
      for(const p of chain){
        const s=getComputedStyle(p),color=rgba(s.backgroundColor);
        const stops=/gradient\\(/.test(s.backgroundImage)?s.backgroundImage.match(/rgba?\\([^)]+\\)/g)||[]:[];
        backs=backs.flatMap(b=>{const base=over(color,b);return stops.length?stops.map(c=>over(rgba(c),base)):[base]});
        backs=[...new Map(backs.map(c=>[hex(c),c])).values()];
      }
      const fg=rgba(getComputedStyle(n).color);
      const samples=backs.map(b=>({bg:hex(b),ratio:VTTDisplay.contrast(hex(over(fg,b)),hex(b))}));
      const worst=samples.reduce((a,b)=>a.ratio<b.ratio?a:b);
      return {text:n.textContent.trim().slice(0,60),...worst,fg:hex(fg)};
    })''')
    assert rows
    assert not [r for r in rows if r['ratio']<4.5], rows


@pytest.mark.parametrize('engine,width,language,theme',[
    ('chromium',1440,'de','paper'),('firefox',1440,'en','night'),
    ('chromium',320,'en','paper'),('firefox',390,'de','night')])
def test_preferences_main_paths_and_user_text(action_site,engine,width,language,theme):
    from playwright.sync_api import sync_playwright,expect
    app,origin,info=action_site
    app.config.update(CE_AUTHORING=True,CE_PLAYABLE_ORIGINS=True)
    with app.app_context():
        char=db.session.get(Character,info['character']);char.name='Speichern';db.session.commit()
        canonical=json.dumps(char.serialize(),sort_keys=True,default=str)
    with sync_playwright() as p:
        browser=getattr(p,engine).launch(headless=True,args=['--no-sandbox'] if engine=='chromium' else [])
        context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(origin+'/characters');page.locator('#vttDisplayOpen').click()
        page.locator('#vttDisplay-theme').select_option(theme);page.locator('#vttDisplay-language').select_option(language)
        page.locator('#vttDisplay-unit').select_option('ft');page.locator('#vttDisplay-accent').select_option('teal');page.locator('#vttDisplay-stickyPortrait').check()
        contrast(page,'#vttDisplayDialog button, #vttDisplayDialog select, #vttDisplayDialog h2')
        page.locator('.vtt-display-actions button').last.click()
        expect(page.locator('html')).to_have_attribute('lang',language)
        expect(page.locator('html')).to_have_attribute('data-vtt-theme',theme)
        expect(page.locator('#vttDisplayOpen')).to_have_text('Appearance and language' if language=='en' else 'Ansicht und Sprache')
        page.goto(f"{origin}/character-sheet?id={info['character']}")
        expect(page.locator('#srdSheetSection')).to_be_visible();expect(page.locator('#charName')).to_have_value('Speichern')
        expect(page.locator('#sfUnits')).to_have_value('ft')
        if language=='en':
            expect(page.locator('#srdSheetBody')).to_contain_text('Armor Class')
            expect(page.locator('#srdSheetBody')).to_contain_text('ft')
        expect(page.locator('.sf-sticky-portrait')).to_be_visible() if width>=960 else expect(page.locator('.sf-sticky-portrait')).not_to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth')<=width+1
        contrast(page,'.sf-tab, #sfTheme, #sfUnits')
        # Normal navigation keeps preferences across separate page compositions.
        for path in ('/srd-creator','/mapmaker','/regelwerk/compendium','/api/ce/authoring'):
            page.goto(origin+path)
            expect(page.locator('#vttDisplayOpen')).to_have_text('Appearance and language' if language=='en' else 'Ansicht und Sprache')
            expect(page.locator('html')).to_have_attribute('data-vtt-theme',theme)
            assert page.evaluate('document.documentElement.scrollWidth')<=width+1,(path,width)
        expect(page.locator('#ce-origins')).to_be_visible()
        page.locator('#ce-create').click();expect(page.locator('.eh-window')).to_be_visible()
        expect(page.locator('.eh-window')).to_contain_text('What do you want to create?' if language=='en' else 'Was möchtest du erstellen?')
        contrast(page,'.eh-window button, .ce-help, #ce-create')
        page.locator('.eh-window [data-action="close"]').click()
        assert not errors,errors
        browser.close()
    with app.app_context():
        db.session.expire_all();assert json.dumps(db.session.get(Character,info['character']).serialize(),sort_keys=True,default=str)==canonical


def test_dm_calibration_updates_player_ruler_without_granting_controls(action_site):
    from playwright.sync_api import sync_playwright,expect
    app,origin,info=action_site
    with app.app_context():
        map_=CampaignMap.query.first();map_id=map_.id;pixels=map_.grid_size
    with sync_playwright() as p:
        chrome=p.chromium.launch(headless=True,args=['--no-sandbox']);firefox=p.firefox.launch(headless=True)
        dmctx=chrome.new_context(viewport={'width':1440,'height':1000});plctx=firefox.new_context(viewport={'width':1440,'height':1000})
        preferences(plctx,language='en',theme='night',unit='ft')
        for ctx,auth in ((dmctx,info['dm_auth']),(plctx,info['player_auth'])):ctx.add_cookies([{'name':'access_token_cookie','value':auth,'url':origin,'httpOnly':True}])
        dm=dmctx.new_page();player=plctx.new_page();errors=[]
        for page in (dm,player):page.set_default_timeout(30000);page.on('pageerror',lambda e:errors.append(str(e)))
        route=f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}"
        dm.goto(route+'&seat=dm');player.goto(route+'&seat=player')
        expect(player.locator('#presenceRoster')).to_contain_text('action-dm')
        expect(player.locator('#mapScalePanel')).to_have_count(0)
        assert not player.evaluate('!!window.PlayDMSurface')
        player.locator('[data-tool="measure"]').click()
        world=player.locator('#mapWorld');box=world.bounding_box()
        # Two actual pointer waypoints on the map. Snap yields a one-square segment.
        player.mouse.click(box['x']+pixels*3,box['y']+pixels*3)
        player.mouse.click(box['x']+pixels*4,box['y']+pixels*3)
        player.mouse.move(10,10)
        expect(player.locator('#measureLayer')).to_contain_text('1 squares')
        dm.locator('#btnSidebarToggle').click();dm.locator('.sidebar-tab[data-tab="session"]').click()
        expect(dm.locator('#mapScaleMeters')).to_be_visible();dm.locator('#mapScaleMeters').fill('1.5');dm.locator('#mapScaleSave').click()
        expect(player.locator('#measureLayer')).to_contain_text('5 ft')
        # Current unit changes redraw the same geometry without another save.
        player.locator('#btnBack').click();player.locator('#appMenuDisplay').click();player.locator('#vttDisplay-unit').select_option('m');player.locator('.vtt-display-actions button').last.click()
        expect(player.locator('#measureLayer')).to_contain_text('1.5 m')
        dm.locator('#mapScaleClear').click();expect(player.locator('#measureLayer')).to_contain_text('1 squares')
        with app.app_context():
            db.session.expire_all();assert db.session.get(CampaignMap,map_id).grid_size==pixels
            assert db.session.get(CampaignMapScale,map_id).meters_per_square is None
        assert not errors,errors
        chrome.close();firefox.close()
