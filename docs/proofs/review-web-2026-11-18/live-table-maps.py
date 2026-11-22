"""Normal editor/library and DM/Player journeys for custom images and artwork floors."""
import base64,hashlib,io,json,os
from pathlib import Path
from PIL import Image
from playwright.sync_api import expect,sync_playwright

root=Path(os.environ['PROOF_ROOT']);fixture=json.loads((root/'private-live-credentials.json').read_text())
origin='https://vtt.roll-drauf.de';proof={'status':'running','journeys':[]};current=None
def save(): (root/'table-maps-live.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
def passed(name,**details): proof['journeys'].append({'name':name,'status':'pass',**details});save()
def png(color):
    data=io.BytesIO();Image.new('RGBA',(1200,900),color).save(data,format='PNG');return data.getvalue()
def close_windows(page):
    for _ in range(20):
        rows=page.locator('.play-window:visible')
        if not rows.count():return
        ident=rows.evaluate_all('rows=>rows.sort((a,b)=>Number(b.style.zIndex)-Number(a.style.zIndex))[0].id')
        page.locator('#'+ident+' .play-window-head button').click()
def bootstrap(page):
    return page.evaluate('async f=>Auth.makeAuthRequest(`/api/play/campaigns/${f.c}/sessions/${f.s}/bootstrap`)',{'c':fixture['campaign_id'],'s':fixture['session_id']})

with sync_playwright() as p:
    browsers=[]
    def new_page(kind,engine,width):
        browser=getattr(p,engine).launch(headless=True,args=['--no-sandbox'] if engine=='chromium' else []);browsers.append(browser)
        context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        context.add_init_script("localStorage.setItem('vtt.display.v1',JSON.stringify({schema:1,theme:'night',language:'de',unit:'m',accent:'default'}))")
        u=fixture['users'][kind]
        context.add_cookies([{'name':'access_token_cookie','value':u['token'],'url':origin,'httpOnly':True,'secure':True},
                            {'name':'csrf_access_token','value':u['csrf'],'url':origin,'secure':True}])
        page=context.new_page();page.set_default_timeout(30000);page.on('dialog',lambda dialog:dialog.accept())
        return page
    def enter(page,role):
        page.goto(origin+f"/campaigns?campaign_id={fixture['campaign_id']}")
        page.locator('[data-hub-action="'+('open-session-dm' if role=='dm' else 'open-session')+'"]').first.click()
        expect(page.locator('body')).to_have_attribute('data-table-seat',role)
        assert page.locator('body').get_attribute('data-table-seat')==role
    try:
        dm=current=new_page('dm','chromium',1440)
        dm.goto(origin+'/mapmaker');dm.wait_for_selector('#app[data-state=ready]',timeout=45000)
        dm.locator('#newEmpty').click();dm.locator('#mapTitle').fill('QA Portable Review')
        dm.locator('[data-tool=stamp]').click();dm.locator('#ownPixelBtn').click()
        dm.locator('#pixelSize').select_option('16');dm.locator('#pixelNew').click();dm.locator('#pixelColor').fill('#ff3344')
        box=dm.locator('#pixelCanvas').bounding_box();x=box['x']+box['width']*.25;y=box['y']+box['height']*.25
        dm.mouse.move(x,y);dm.mouse.down();dm.mouse.move(x+box['width']*.5,y+box['height']*.5,steps=12);dm.mouse.up()
        dm.locator('#pixelLabel').fill('QA Own Stamp');dm.locator('#pixelSave').click()
        point=dm.evaluate('() => rdMapmaker.docToClient(128,128)');dm.mouse.click(point['x'],point['y'])
        assert dm.evaluate('rdMapmaker.summary().stamps')==1
        dm.locator('#cloudSave').click();expect(dm.locator('#cloudStatus')).to_have_text('In Bibliothek gespeichert',timeout=45000)
        with dm.expect_download() as download:
            dm.locator('#fileMenuBtn').click();dm.locator('#saveBtn').click()
        path=root/'qa-project.rdmap.json';download.value.save_as(path);doc=json.loads(path.read_text())
        assert len(doc['assets'])==1
        own=doc['assets'][0];raw=base64.b64decode(own['png'].split(',',1)[1])
        assert own['id']=='custom:'+hashlib.sha256(raw).hexdigest()
        assert any(item.get('asset')==own['id'] for layer in doc['layers'] for item in layer.get('items',[]))
        expect(dm.locator('#saveStatus')).to_have_attribute('data-state','saved',timeout=20000)
        dm.reload();dm.locator('#restoreYes').click();dm.wait_for_selector('#app[data-state=ready]',timeout=45000)
        assert dm.evaluate('rdMapmaker.summary().assets[0].id')==own['id']
        dm.screenshot(path=str(root/'custom-map-editor-night.png'))
        passed('Pixel image is placed, saved in personal library, exported with byte-derived identity and restored after reload',asset_id=own['id'])

        dm.goto(origin+f"/campaigns?campaign_id={fixture['campaign_id']}")
        dm.locator('[data-hub-action=map-library]').click();expect(dm.locator('#mapLibraryDialog')).to_be_visible()
        dm.locator('#mapLibraryList .project-choice').first.click();expect(dm.locator('#mapLibraryPreview')).to_be_visible(timeout=45000)
        dm.locator('#mapLibraryConsent').check();dm.locator('#mapLibraryConfirm').click()
        expect(dm.locator('#mapLibraryDialog')).not_to_be_visible(timeout=45000)
        passed('Normal campaign map-library preview imports the custom-image project as a real map')

        enter(dm,'dm');dm.locator('#btnMapPresentation').click();dm.locator('#btnMapFloors').click()
        expect(dm.locator('#floorLimitation')).to_contain_text('gemeinsamen 2D-Karte')
        for index,(name,color) in enumerate([('QA Ground','red'),('QA Balcony','lime')],1):
            dm.locator('#newFloorName').fill(name)
            dm.locator('#newFloorFile').set_input_files({'name':name+'.png','mimeType':'image/png','buffer':png(color)})
            dm.locator('#uploadFloor').click();expect(dm.locator('#floorList .floor-card')).to_have_count(index)
        card=dm.locator('#floorList .floor-card').nth(1);upper=card.get_attribute('data-floor-id')
        card.locator('input[type=checkbox]').check();card.get_by_role('button',name='Rechteckige Öffnung hinzufügen').click()
        for key,value in [('x','80'),('y','80'),('width','180'),('height','180')]:card.locator('[data-rect-key='+key+']').fill(value)
        card.get_by_role('button',name='Etage speichern',exact=True).click();expect(dm.locator('#floorEditorStatus')).to_contain_text('gespeichert')
        dm.locator('#floorEnabled').check();dm.locator('#activeFloor').select_option(upper);dm.locator('#applyFloorDeck').click()
        expect(dm.locator('#floorViewStatus')).to_have_text('QA Balcony',timeout=20000)
        dm.screenshot(path=str(root/'floor-dm-night.png'));close_windows(dm)
        player=current=new_page('player','firefox',390);enter(player,'player')
        expect(player.locator('#floorViewStatus')).to_have_text('QA Balcony',timeout=25000)
        assert not player.evaluate('Boolean(window.PlayFloorDM || window.PlayDMSurface)')
        assert player.locator('#btnMapFloors').count()==0
        pixels=player.evaluate("""async()=>{const image=document.getElementById('mapImage');await image.decode();const c=document.createElement('canvas');c.width=image.naturalWidth;c.height=image.naturalHeight;const x=c.getContext('2d');x.drawImage(image,0,0);return [[140,140],[300,140],[900,140]].map(([a,b])=>Array.from(x.getImageData(a,b,1,1).data));}""")
        assert pixels[0][0]>0 and pixels[0][1]==0,pixels
        assert pixels[1][1]>0 and pixels[1][0]==0,pixels
        assert pixels[2]==[0,0,0,255],pixels
        denied=player.evaluate("""async f=>{const r=await fetch(`/api/play/campaigns/${f.c}/sessions/${f.s}/maps/${f.m}/floors`,{headers:Auth.buildHeaders('GET',false)});return r.status;}""",{'c':fixture['campaign_id'],'s':fixture['session_id'],'m':fixture['map_id']})
        assert denied==403
        player.screenshot(path=str(root/'floor-player-mobile-night.png'))
        passed('Real DM floor editor and Firefox Player receive opaque balcony pixels through existing wall/vision rules; private source configuration is denied',pixels=pixels)

        def summon():
            close_windows(player);player.locator('.token-marker[data-token-id="'+str(fixture['token_id'])+'"]').click()
            player.locator('[data-pa-companions]').click();expect(player.locator('#paCompanionSelect')).to_contain_text('QA Companion')
            player.locator('#paCompanionPlace').click();expect(player.locator('#personalCompanionDialog')).to_have_count(0)
        summon();child=next(t for t in bootstrap(player)['state_payload']['tokens'] if t['name']=='QA Companion')
        close_windows(player);player.locator('.token-marker[data-token-id="'+str(child['id'])+'"]').click()
        player.locator('#tokenHpCurrent').fill('7');player.locator('#btnTokenHpSet').click()
        player.wait_for_function("() => document.getElementById('tokenHpCurrent').value==='7'")
        player.locator('#btnTokenDelete').click();summon()
        child_after=next(t for t in bootstrap(player)['state_payload']['tokens'] if t['name']=='QA Companion')
        assert child_after['id']==child['id'] and child_after['hp_current']==7,child_after
        passed('Personal companion placement reuses the same soft-deleted token and preserves table damage',token_id=child['id'],hp_current=7)
        assert player.locator('#mapImage').evaluate('e=>getComputedStyle(e).display')=='block'
        proof['status']='pass';save()
    except Exception as error:
        proof['status']='failed';proof['error']=str(error)
        if current:current.screenshot(path=str(root/'table-maps-failure.png'))
        save();raise
    finally:
        for browser in browsers:browser.close()
