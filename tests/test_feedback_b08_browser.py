import io
import json
from pathlib import Path
import pytest
from PIL import Image
from playwright.sync_api import sync_playwright,expect
from tests.test_personal_actions_browser import action_site  # noqa:F401
from tests.test_presentation_browser import preferences,contrast
from tests.test_mapmaker_library import document
from flask_jwt_extended import create_access_token,decode_token
from vtt.extensions import db
from vtt.models import Campaign,Asset,CampaignMap,User


def setup_storage(app,info,tmp_path):
    app.config.update(STORAGE_PROVIDER='local',LOCAL_STORAGE_PATH=str(tmp_path/'storage'))
    with app.app_context():
        campaign=db.session.get(Campaign,info['campaign']);owner=db.session.get(User,campaign.owner_id);owner.storage_quota_gb=1;db.session.commit();return owner.id


def open_table(ctx,origin,info,role,errors):
    page=ctx.new_page();page.set_default_timeout(60000);page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat={role}")
    expect(page.locator('#journalFilesPanel')).to_be_attached(timeout=60000)
    page.locator('#btnSidebarToggle').click();expect(page.locator('#journalFilesPanel')).to_be_visible();return page


def test_journal_real_upload_sharing_media_and_independent_player(action_site,tmp_path):
    app,origin,info=action_site;setup_storage(app,info,tmp_path)
    out=io.BytesIO();Image.new('RGB',(64,64),(160,90,40)).save(out,format='PNG');content=out.getvalue()
    with sync_playwright() as p:
        chrome=p.chromium.launch(headless=True,args=['--no-sandbox']);firefox=p.firefox.launch(headless=True)
        dc=chrome.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        pc=firefox.new_context(viewport={'width':390,'height':1000},reduced_motion='reduce',accept_downloads=True)
        oc=chrome.new_context(viewport={'width':390,'height':1000},reduced_motion='reduce')
        preferences(pc,language='en',theme='night');errors=[]
        for ctx,role in [(dc,'dm'),(pc,'player'),(oc,'dm')]:ctx.add_cookies([{'name':'access_token_cookie','value':info[role+'_auth'],'url':origin,'httpOnly':True}])
        player_requests=[];media=[]
        pc.on('request',lambda request:player_requests.append(request.url))
        pc.on('request',lambda request:media.append((request.url,bool(request.headers.get('x-vtt-context')),bool(request.headers.get('x-vtt-tab')))) if '/api/assets/' in request.url else None)
        dm=open_table(dc,origin,info,'dm',errors);player=open_table(pc,origin,info,'player',errors);owner_player=open_table(oc,origin,info,'player',errors)
        expect(player.locator('#journalManageFiles,#journalUpload')).to_have_count(0);expect(owner_player.locator('#journalUpload')).to_have_count(0)
        dm.locator('#journalManageFiles summary').click();dm.locator('#journalUploadFile').set_input_files({'name':'secret.png','mimeType':'image/png','buffer':content});dm.locator('#journalUpload').click()
        expect(dm.locator('.journal-asset')).to_have_count(1,timeout=60000)
        row=dm.locator('.journal-asset');aid=int(row.get_attribute('data-asset-id'))
        with app.app_context():assert db.session.get(Asset,aid).session_id==info['session']
        player.locator('#journalAssetsRefresh').click();expect(player.locator('.journal-asset')).to_have_count(0)
        row.locator('summary').click();row.locator('[data-journal-rename]').fill('Speichern – Übersicht.png');row.locator('[data-journal-save]').click();expect(dm.locator('.journal-asset strong')).to_have_text('Speichern – Übersicht.png')
        row=dm.locator('.journal-asset');row.locator('summary').click();row.locator('[data-journal-reveal]').click()
        player.locator('#journalAssetsRefresh').click();expect(player.locator('.journal-asset strong')).to_have_text('Speichern – Übersicht.png',timeout=30000)
        expect(player.locator('.journal-asset-thumb')).to_be_visible();contrast(player,'#journalFilesPanel button,#journalFilesPanel strong')
        player.get_by_role('button',name='Preview',exact=True).click();expect(player.locator('#journalAssetPreview img')).to_be_visible()
        assert player.locator('#journalAssetPreview img').evaluate('img=>img.complete && img.naturalWidth')==64
        player.locator('#journalAssetPreview').press('Escape')
        with player.expect_download() as downloaded:player.get_by_role('button',name='Download',exact=True).click()
        download=downloaded.value;assert download.suggested_filename=='Speichern – Übersicht.png';assert Path(download.path()).read_bytes()==content
        forbidden=owner_player.evaluate('''async id=>{const r=await fetch('/api/assets/'+id+'/metadata',{method:'PATCH',credentials:'include',headers:Auth.buildHeaders('PATCH',true),body:JSON.stringify({filename:'No.png'})});return r.status}''',aid)
        assert forbidden==403
        row=dm.locator('.journal-asset');row.locator('summary').click();row.locator('[data-journal-reveal]').click()
        player.locator('#journalAssetsRefresh').click();expect(player.locator('.journal-asset')).to_have_count(0)
        status=owner_player.evaluate('''async id=>(await fetch('/api/assets/'+id+'/preview',{headers:Auth.buildHeaders('GET',false),credentials:'include'})).status''',aid);assert status==403
        dm.on('dialog',lambda dialog:dialog.accept());row=dm.locator('.journal-asset');row.locator('summary').click();row.locator('[data-journal-delete]').click();expect(dm.locator('.journal-asset')).to_have_count(0)
        player.locator('#journalTokens').click();expect(player.locator('#tokenWidget')).to_be_visible()
        assert not [url for url in player_requests if 'play-journal-dm.js' in url or 'play-dm.js' in url]
        actual=[r for r in media if any('/'+str(aid)+'/'+endpoint in r[0] for endpoint in ['preview','thumbnail','download'])]
        assert len(actual)>=3 and all(ctx and tab for _,ctx,tab in actual),actual
        assert player.evaluate('document.documentElement.scrollWidth')<=391
        assert not errors,errors
        for ctx in [dc,pc,oc]:ctx.close()
        chrome.close();firefox.close()


def test_journal_read_racing_a_context_renewal_recovers_without_error(action_site,tmp_path):
    app,origin,info=action_site;setup_storage(app,info,tmp_path)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        ctx.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}]);errors=[]
        page=open_table(ctx,origin,info,'player',errors);statuses=[]
        page.on('response',lambda r:statuses.append(r.status) if '/library?' in r.url else None)
        page.wait_for_function('()=>!/Dateien werden geladen/.test(document.getElementById("journalAssetsStatus").textContent)')
        # A list request leaves with the seat's old context just as the socket renews it.
        page.evaluate('''async([c,s])=>{const stale=window.VTTTableContext;const fresh=await Auth.resumeTableContext(c,s);
            window.VTTTableContext=stale;document.getElementById('journalAssetsRefresh').click();
            setTimeout(()=>{window.VTTTableContext=fresh;},400);}''',[info['campaign'],info['session']])
        page.wait_for_function('()=>!/Dateien werden geladen/.test(document.getElementById("journalAssetsStatus").textContent)')
        page.wait_for_timeout(500)
        assert 403 in statuses and statuses[-1]==200,statuses
        assert not page.locator('#journalAssetsStatus.error').count(),page.locator('#journalAssetsStatus').text_content()
        assert not errors,errors
        ctx.close();browser.close()


def test_hub_thumbnail_import_unknown_map_response_and_editor_cards(action_site,tmp_path):
    app,origin,info=action_site;owner_id=setup_storage(app,info,tmp_path)
    client=app.test_client();client.set_cookie('access_token_cookie',info['dm_auth'])
    projects=[]
    for title in ['Küstenwelt','Bergwelt']:
        doc=document(title);doc['size']={'w':1024,'h':768};doc['layers']=[l for l in doc['layers'] if l['kind']!='raster']
        response=client.post('/api/assets/mapmaker/projects',json={'document':doc},headers={'X-Mapmaker-Account':str(owner_id)})
        assert response.status_code==201,response.json;projects.append(response.json['project'])
    source=client.get('/api/assets/mapmaker/projects/'+projects[0]['id']).json
    with sync_playwright() as p:
        # As in production, a cookie login carries a CSRF token; the editor library only lists projects with it.
        app.config['JWT_COOKIE_CSRF_PROTECT']=True
        with app.app_context():token=create_access_token(identity=str(owner_id));csrf=decode_token(token)['csrf']
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');ctx.add_cookies([{'name':'access_token_cookie','value':token,'url':origin,'httpOnly':True},{'name':'csrf_access_token','value':csrf,'url':origin}])
        page=ctx.new_page();page.set_default_timeout(60000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));posts=[]
        page.on('request',lambda r:posts.append(r.url) if r.method=='POST' and ('/maps' in r.url or '/upload' in r.url) else None)
        page.goto(f"{origin}/campaigns?campaign_id={info['campaign']}")
        try:page.locator('[data-campaign-map-library]').click(timeout=12000)
        except Exception:
            Path('/app/docs/proofs/feedback-b08-hub-diagnostic.json').write_text(json.dumps({'url':page.url,'text':page.locator('body').inner_text(),'errors':errors},indent=2))
            page.screenshot(path='/app/docs/proofs/feedback-b08-hub-diagnostic.png');raise
        expect(page.locator('#mapLibraryList li')).to_have_count(2)
        page.wait_for_function('() => [...document.querySelectorAll("#mapLibraryList img")].every(img=>img.complete && img.naturalWidth===256)')
        images=page.locator('#mapLibraryList img').evaluate_all('imgs=>imgs.map(img=>img.src)');assert images[0]!=images[1]
        page.locator(f'#mapLibraryList [data-project-id="{projects[0]["id"]}"]').click();expect(page.locator('#mapLibraryPreview')).to_be_visible()
        page.wait_for_function('()=>document.querySelector("#mapLibraryPreview").naturalWidth===1024')
        page.locator('#mapLibraryName').fill('Hubkarte');expect(page.locator('#mapLibraryConfirm')).to_be_disabled();page.locator('#mapLibraryConsent').check()
        route_url=f'**/api/campaigns/{info["campaign"]}/maps'
        def unknown_map_response(route):
            if route.request.method=='POST':route.fetch();route.abort()
            else:route.continue_()
        page.route(route_url,unknown_map_response);page.locator('#mapLibraryConfirm').click()
        expect(page.locator('#mapLibraryConfirm')).to_be_enabled();expect(page.locator('#mapLibraryDialog')).to_be_visible()
        with app.app_context():assert CampaignMap.query.filter_by(campaign_id=info['campaign'],name='Hubkarte').count()==1
        page.unroute(route_url);page.locator('#mapLibraryConfirm').click();expect(page.locator('#mapLibraryDialog')).to_be_hidden()
        expect(page.locator('#campaignHubMaps')).to_contain_text('Hubkarte')
        assert len([url for url in posts if url.endswith('/upload')])==1 and len([url for url in posts if url.endswith('/maps')])==1,posts
        assert client.get('/api/assets/mapmaker/projects/'+projects[0]['id']).json==source
        page.goto(origin+'/mapmaker');page.wait_for_selector('#app[data-state=ready]')
        expect(page.locator('#libraryList .project-thumbnail img')).to_have_count(2)
        page.wait_for_function('()=>[...document.querySelectorAll("#libraryList .project-thumbnail img")].every(img=>img.complete&&img.naturalWidth===256)')
        expect(page.locator('#libraryList')).to_contain_text('Küstenwelt');expect(page.locator('#libraryList')).to_contain_text('Bergwelt')
        assert not errors,errors
        ctx.close();browser.close()
