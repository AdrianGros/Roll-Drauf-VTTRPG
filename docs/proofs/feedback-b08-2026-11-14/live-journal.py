"""B08 live, part 2: table Own Library cards and the Journal as file access, per role."""
import io,json
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright,expect
from tests.test_mapmaker_browser import CSP_PROBE
from tests.test_presentation_browser import preferences
expect.set_options(timeout=60000)
ROOT=Path('/delivery');ORIGIN='https://vtt.roll-drauf.de';f=json.loads((ROOT/'live-credentials.json').read_text())
proof={'status':'running','journeys':[],'checks':{},'errors':[]};NAME='Lagekarte – geheim.png'
out=io.BytesIO();Image.new('RGB',(64,64),(160,90,40)).save(out,format='PNG');CONTENT=out.getvalue()
def table(ctx,kind,action):
    ctx.add_init_script(CSP_PROBE)
    page=ctx.new_page();page.set_default_timeout(60000);page.on('pageerror',lambda e:proof['errors'].append(str(e)))
    page.goto(ORIGIN+'/login.html');page.locator('#loginUsername').fill(f['users'][kind]['username']);page.locator('#loginPassword').fill(f['users'][kind]['password'])
    page.locator('#passwordLoginSubmitBtn').click();page.wait_for_url(lambda u:'/login' not in u)
    page.goto(f"{ORIGIN}/campaigns?campaign_id={f['campaign_id']}")
    page.locator(f'[data-hub-action="{action}"][data-hub-session-id="{f["session_id"]}"]').click();page.wait_for_url(lambda u:'/play' in u)
    expect(page.locator('#journalFilesPanel')).to_be_attached();page.locator('#btnSidebarToggle').click();expect(page.locator('#journalFilesPanel')).to_be_visible()
    # Context renewal right after entry must not leave a stale-context error in the Journal.
    page.wait_for_function('()=>!/Dateien werden geladen|Loading files/.test(document.getElementById("journalAssetsStatus").textContent)')
    page.wait_for_timeout(1500)
    assert not page.locator('#journalAssetsStatus.error').count(),(kind,action,page.locator('#journalAssetsStatus').text_content())
    proof['checks'].setdefault('journal_first_open_status',{})[kind+':'+action]=page.locator('#journalAssetsStatus').text_content()
    return page
def handout(page):return page.locator('.journal-asset').filter(has_text=NAME)
def status(page,path,method='GET',body=None):
    return page.evaluate('''async([p,m,b])=>(await fetch(p,{method:m,credentials:'include',headers:Auth.buildHeaders(m,!!b),...(b?{body:JSON.stringify(b)}:{})})).status''',[path,method,body])
with sync_playwright() as p:
    chrome=p.chromium.launch(headless=True,args=['--no-sandbox']);firefox=p.firefox.launch(headless=True)
    try:
        dc=chrome.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        pc=firefox.new_context(viewport={'width':390,'height':1000},reduced_motion='reduce',accept_downloads=True);preferences(pc,language='en',theme='night')
        oc=chrome.new_context(viewport={'width':390,'height':1000},reduced_motion='reduce')
        player_requests=[];pc.on('request',lambda r:player_requests.append(r.url))
        dm=table(dc,'dm','open-session-dm')
        # Own Library in the table composition: same visual cards as the hub.
        dm.locator('#dock-layersWidget').click();expect(dm.locator('#layersWidget')).to_be_visible();expect(dm.locator('#layerAddBtn')).to_be_visible()
        for _ in range(40):
            if dm.locator('#mapLibraryDialog').count() and dm.locator('#mapLibraryDialog').is_visible():break
            if not dm.locator('#layerAddLibrary').is_visible():dm.locator('#layerAddBtn').click()
            if dm.locator('#layerAddLibrary').is_visible():dm.locator('#layerAddLibrary').click()
            dm.wait_for_timeout(250)
        expect(dm.locator('#mapLibraryDialog')).to_be_visible();expect(dm.locator('#mapLibraryList li')).to_have_count(2)
        dm.wait_for_function('()=>{const i=[...document.querySelectorAll("#mapLibraryList img")];return i.length===2&&i.every(x=>x.complete&&x.naturalWidth===256)}')
        dm.screenshot(path=str(ROOT/'table-library.png'));dm.locator('#mapLibraryDialog').press('Escape');expect(dm.locator('#mapLibraryDialog')).to_be_hidden()
        proof['journeys'].append('DM am Tisch: Eigene Bibliothek zeigt dieselben 256-px-Vorschauen; Schließen ohne Import')
        player=table(pc,'player','open-session');owner_player=table(oc,'dm','open-session-player')
        expect(player.locator('#journalManageFiles,#journalUpload')).to_have_count(0);expect(owner_player.locator('#journalUpload')).to_have_count(0)
        dm.locator('#journalManageFiles summary').click();dm.locator('#journalUploadFile').set_input_files({'name':'b08-handout.png','mimeType':'image/png','buffer':CONTENT})
        dm.locator('#journalUpload').click();row=dm.locator('.journal-asset').filter(has_text='b08-handout.png');expect(row).to_have_count(1)
        aid=int(row.get_attribute('data-asset-id'));proof['checks']['asset_id']=aid
        row.locator('summary').click();row.locator('[data-journal-rename]').fill(NAME);row.locator('[data-journal-save]').click();expect(handout(dm)).to_have_count(1)
        player.locator('#journalAssetsRefresh').click();expect(handout(player)).to_have_count(0)
        proof['checks']['player_preview_hidden']=status(player,f'/api/assets/{aid}/preview');proof['checks']['owner_as_player_preview_hidden']=status(owner_player,f'/api/assets/{aid}/preview')
        assert proof['checks']['player_preview_hidden']==403 and proof['checks']['owner_as_player_preview_hidden']==403,proof['checks']
        row=handout(dm);row.locator('summary').click();row.locator('[data-journal-reveal]').click()
        player.locator('#journalAssetsRefresh').click();expect(handout(player)).to_have_count(1);expect(handout(player).locator('.journal-asset-thumb')).to_be_visible()
        handout(player).get_by_role('button',name='Preview',exact=True).click();expect(player.locator('#journalAssetPreview img')).to_be_visible()
        assert player.locator('#journalAssetPreview img').evaluate('img=>img.complete&&img.naturalWidth')==64
        player.screenshot(path=str(ROOT/'journal-player-mobile.png'));player.locator('#journalAssetPreview').press('Escape')
        with player.expect_download() as downloaded:handout(player).get_by_role('button',name='Download',exact=True).click()
        assert downloaded.value.suggested_filename==NAME and Path(downloaded.value.path()).read_bytes()==CONTENT
        proof['checks']['player_rename_denied']=status(player,f'/api/assets/{aid}/metadata','PATCH',{'filename':'No.png'})
        proof['checks']['owner_as_player_rename_denied']=status(owner_player,f'/api/assets/{aid}/metadata','PATCH',{'filename':'No.png'})
        assert proof['checks']['player_rename_denied']==403 and proof['checks']['owner_as_player_rename_denied']==403,proof['checks']
        dm.screenshot(path=str(ROOT/'journal-dm.png'))
        row=handout(dm);row.locator('summary').click();row.locator('[data-journal-reveal]').click()
        player.locator('#journalAssetsRefresh').click();expect(handout(player)).to_have_count(0)
        dm.on('dialog',lambda d:d.accept());row=handout(dm);row.locator('summary').click();row.locator('[data-journal-delete]').click();expect(handout(dm)).to_have_count(0)
        player.locator('#journalTokens').click();expect(player.locator('#tokenWidget')).to_be_visible()
        assert not [u for u in player_requests if 'play-journal-dm.js' in u or 'play-dm.js' in u]
        assert player.evaluate('document.documentElement.scrollWidth')<=391
        for page in (dm,player,owner_player):assert not page.evaluate('window.__csp'),page.evaluate('window.__csp')
        proof['journeys'].append('DM (Desktop): Journal → Datei für diese Sitzung hochladen → umbenennen → freigeben → wieder verbergen → löschen')
        proof['journeys'].append('Player (Firefox mobil, Englisch/Nacht): verborgenes Handout unsichtbar und 403 → nach Freigabe Vorschaubild, Vorschau, Download → Tokens-Schaltfläche; kein DM-Modul geladen')
        proof['journeys'].append('Owner im Player-Modus: keine Verwaltung, verborgene Datei 403, Umbenennen 403')
        assert not proof['errors'],proof['errors'];proof['status']='pass'
    except BaseException as error:proof.update(status='fail',failure=str(error));raise
    finally:
        (ROOT/'live-journal-result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');chrome.close();firefox.close()
