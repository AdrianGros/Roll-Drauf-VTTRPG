"""End-to-end UI journeys for authorized DM and separate Player surfaces."""
from tests.test_personal_actions_browser import action_site
from vtt.extensions import db
from vtt.models import SceneWall,SceneLight

def test_grid_hierarchy_library_measure_and_candidate_journeys(action_site):
    from playwright.sync_api import sync_playwright,expect
    app,origin,info=action_site
    with app.app_context():
        from vtt.models import GameSession,FogOfWarState
        session=db.session.get(GameSession,info['session'])
        db.session.add(FogOfWarState(user_id=info['player_id'],campaign_map_id=session.map_id,explored_cells=[[0,0]],visible_cells=[[0,0]],version=1))
        db.session.commit()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        dm_context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        player_context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        dm_context.add_cookies([{'name':'access_token_cookie','value':info['dm_auth'],'url':origin}]);player_context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin}])
        dm=dm_context.new_page();player=player_context.new_page();errors=[]
        for page in (dm,player):page.set_default_timeout(25000);page.on('pageerror',lambda error:errors.append(str(error)))
        route=f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}"
        dm.goto(route+'&seat=dm');player.goto(route+'&seat=player')
        confirmations=[]
        dm.on('dialog',lambda dialog:(confirmations.append(dialog.message),dialog.accept()))
        expect(dm.locator('#btnMapPresentation')).to_be_visible();expect(player.locator('#btnMapPresentation')).to_have_count(0)
        assert player.evaluate("typeof window.PlayFeedbackDM")=='undefined'
        dm.locator('#btnMapPresentation').click();dm.locator('#presentationGridSize').fill('80');dm.locator('#presentationGridVisible').uncheck();dm.locator('#savePresentationSettings').click()
        expect(dm.locator('#window-mapPresentation')).to_contain_text('gespeichert')
        assert len(confirmations)==1 and 'Aufklärung' in confirmations[0]
        expect(player.locator('#mapGridLayer')).to_be_hidden()
        dm.locator('#window-mapPresentation .play-window-head button').click()
        # First native sheet initiative is accepted; another roll appears in DM decisions.
        player.locator(f".token-marker[data-token-id='{info['token']}']").click()
        expect(player.locator('#btnSelectedInitiative')).to_be_visible()
        player.locator('#btnSelectedInitiative').click()
        player.locator('#btnSelectedInitiative').click()
        dm.locator('#dock-turnOrderWidget').click()
        expect(dm.locator('#initiativeCandidates li')).to_have_count(1)
        dm.locator('#initiativeCandidates button').click()
        expect(dm.locator('#initiativeCandidates li')).to_have_count(0)
        # Library first, then a chosen template creates directly on a map click.
        player.locator('#btnSaveTokenTemplate').click();expect(player.locator('#tokenLibraryList li')).to_have_count(1)
        player.locator('#tokenLibraryList button').filter(has_text='Platzieren').click()
        expect(player.locator('#window-tokenWidget')).to_be_hidden()
        # Cancelled placement must clear the chosen template.
        player.locator('[data-tool="select"]').click();player.locator('#dock-tokenWidget').click()
        expect(player.locator('#window-tokenWidget')).to_be_visible()
        player.locator('#btnPlaceNewToken').click()
        viewport=player.locator('#mapViewport');box=viewport.bounding_box();player.mouse.click(box['x']+300,box['y']+220)
        expect(player.locator('#tokenCreatePanel')).to_be_visible()
        player.locator('#btnTokenCreateCancel').click()
        player.locator('[data-tool="measure"]').click()
        expect(player.locator('#btnMeasureSnap')).to_have_attribute('aria-pressed','false')
        player.mouse.click(box['x']+200,box['y']+200);player.mouse.move(box['x']+310,box['y']+240)
        expect(player.locator('#measureLayer text')).not_to_have_count(0)
        player.locator('#btnMeasureSnap').click();expect(player.locator('#btnMeasureSnap')).to_have_attribute('aria-pressed','true')
        assert not errors,errors
        browser.close()


def test_visible_lighting_preview_and_campaign_page_hierarchy(action_site):
    from playwright.sync_api import sync_playwright,expect
    from tests.play_shared import add_map
    from vtt.models import Campaign,GameSession,User,TokenState,ChatMessage
    from vtt.play.service import init_scene_stack
    app,origin,info=action_site
    with app.app_context():
        campaign=db.session.get(Campaign,info['campaign']);session=db.session.get(GameSession,info['session']);owner=db.session.get(User,campaign.owner_id)
        child=add_map(campaign,owner,'Harbour');init_scene_stack(campaign,session,owner,[session.map_id,child.id])
        hero=db.session.get(TokenState,info['token']);hero.x=80;hero.y=80;hero.metadata_json={'position_mode':'pixel'}
        db.session.add(SceneWall(campaign_map_id=session.map_id,x0=250,y0=0,x1=250,y1=900,sight='normal',light='normal',created_by=owner.id))
        db.session.add(SceneLight(campaign_map_id=session.map_id,x=80,y=80,bright_radius=100,dim_radius=300,created_by=owner.id))
        db.session.add(ChatMessage(campaign_id=campaign.id,game_session_id=session.id,author_user_id=owner.id,content='Historical public journey',visibility='public',moderation_state='visible'))
        db.session.commit()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        context.add_cookies([{'name':'access_token_cookie','value':info['dm_auth'],'url':origin}]);page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        route=f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat=dm"
        page.goto(route);page.locator('#btnMapPresentation').click()
        expect(page.locator('#geometryManager li')).to_have_count(2)
        page.locator('#previewPerspectiveToken').select_option(str(info['token']))
        expect(page.locator('#lightingProjection')).to_be_visible();expect(page.locator('#previewPerspectiveStatus')).to_contain_text('Vorschau')
        page.locator('#previewPerspectiveToken').select_option('');expect(page.locator('#lightingProjection')).to_be_hidden()
        page.locator('#window-mapPresentation .play-window-head button').click();page.locator('#dock-layersWidget').click()
        rows=page.locator('#layerList .layer-row');expect(rows).to_have_count(2)
        parent=rows.first.get_attribute('data-layer-id');rows.nth(1).locator('select').select_option(parent)
        expect(rows.nth(1)).to_have_attribute('data-depth','1')
        page.reload();page.locator('#dock-layersWidget').click();expect(page.locator('#layerList .layer-row').nth(1)).to_have_attribute('data-depth','1')
        page.goto(origin+f"/conversations?campaign_id={info['campaign']}")
        # Normal campaign room link/query selects the room, then history is opened deliberately.
        expect(page.locator('#previousSessions')).to_be_visible();page.locator('#previousSessions summary').click()
        expect(page.locator('#previousSessions')).to_contain_text('Historical public journey')
        assert not errors,errors
        browser.close()


def test_lighting_error_retains_full_legacy_map_cover(action_site):
    from playwright.sync_api import sync_playwright,expect
    from vtt.models import GameSession,TokenState
    app,origin,info=action_site
    with app.app_context():
        session=db.session.get(GameSession,info['session']);hero=db.session.get(TokenState,info['token'])
        hero.x=80;hero.y=80;hero.metadata_json={'position_mode':'pixel'}
        db.session.add(SceneLight(campaign_map_id=session.map_id,x=80,y=80,bright_radius=50,dim_radius=150,created_by=hero.owner_user_id))
        db.session.commit()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1200,'height':900})
        ctx.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin}]);page=ctx.new_page()
        page.route('**/vision/illumination*',lambda route:route.abort())
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat=player")
        expect(page.locator('#lightingProjection')).to_be_visible()
        expect(page.locator('#msg')).to_contain_text('Sicht konnte nicht aktualisiert',timeout=10000)
        size=page.evaluate("""()=>{const mask=document.getElementById('lightingProjection').getBoundingClientRect(),world=document.getElementById('mapWorld').getBoundingClientRect();return {mask:[mask.width,mask.height],world:[world.width,world.height],source:document.getElementById('lightingProjection').src};}""")
        assert all(abs(a-b)<1 for a,b in zip(size['mask'],size['world'])) and size['source'].startswith('data:image/svg+xml,'),size
        page.unroute('**/vision/illumination*');page.reload()
        expect(page.locator('#lightingProjection')).to_have_attribute('src',__import__('re').compile(r'^data:image/png;'),timeout=15000)
        assert page.locator('#lightingProjection').is_visible()
        browser.close()
