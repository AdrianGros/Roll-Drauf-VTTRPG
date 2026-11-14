"""B08 live, part 1: campaign-hub import from the own library and editor-library cards."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from tests.test_mapmaker_browser import CSP_PROBE
expect.set_options(timeout=60000)
ROOT=Path('/delivery');ORIGIN='https://vtt.roll-drauf.de';f=json.loads((ROOT/'live-credentials.json').read_text())
proof={'status':'running','journeys':[],'errors':[]};MAP='Hubkarte B08'
def login(ctx,kind):
    ctx.add_init_script(CSP_PROBE)
    page=ctx.new_page();page.set_default_timeout(60000);page.on('pageerror',lambda e:proof['errors'].append(str(e)))
    page.goto(ORIGIN+'/login.html');page.locator('#loginUsername').fill(f['users'][kind]['username']);page.locator('#loginPassword').fill(f['users'][kind]['password'])
    page.locator('#passwordLoginSubmitBtn').click();page.wait_for_url(lambda u:'/login' not in u);return page
def loaded(page,selector,width):
    page.wait_for_function('([s,w])=>{const i=[...document.querySelectorAll(s)];return i.length&&i.every(img=>img.complete&&img.naturalWidth===w)}',arg=[selector,width])
with sync_playwright() as p:
    chrome=p.chromium.launch(headless=True,args=['--no-sandbox'])
    try:
        ctx=chrome.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');dm=login(ctx,'dm')
        dm.goto(f"{ORIGIN}/campaigns?campaign_id={f['campaign_id']}");dm.locator('[data-campaign-map-library]').click()
        expect(dm.locator('#mapLibraryList li')).to_have_count(2);loaded(dm,'#mapLibraryList img',256)
        sources=dm.locator('#mapLibraryList img').evaluate_all('imgs=>imgs.map(img=>img.src)');assert len(set(sources))==2
        dm.screenshot(path=str(ROOT/'hub-library.png'))
        dm.locator(f"#mapLibraryList [data-project-id=\"{f['projects'][0]['id']}\"]").click();expect(dm.locator('#mapLibraryPreview')).to_be_visible()
        dm.wait_for_function('()=>document.querySelector("#mapLibraryPreview").naturalWidth===1024')
        dm.locator('#mapLibraryName').fill(MAP);expect(dm.locator('#mapLibraryConfirm')).to_be_disabled();dm.locator('#mapLibraryConsent').check()
        dm.locator('#mapLibraryConfirm').click();expect(dm.locator('#mapLibraryDialog')).to_be_hidden();expect(dm.locator('#campaignHubMaps')).to_contain_text(MAP)
        dm.screenshot(path=str(ROOT/'hub-imported.png'))
        proof['journeys'].append('DM: Kampagnenhub → Karten → Eigene Bibliothek → 2 echte 256-px-Vorschauen → Auswahl/Vollvorschau 1024 px → Name + Zustimmung → Karte im Hub, ohne Tisch zu betreten')
        dm.goto(ORIGIN+'/characters');dm.locator('.book-dashboard-ribbon a[href="/mapmaker"]').click();dm.wait_for_selector('#app[data-state=ready]')
        rows=dm.locator('#libraryList li').filter(has_text='B08');expect(rows).to_have_count(2);loaded(dm,'#libraryList .project-thumbnail img',256)
        dm.screenshot(path=str(ROOT/'editor-library.png'))
        proof['journeys'].append('DM: normale Karten-Navigation → Editor-Bibliothek zeigt beide Projekte mit Vorschaubild')
        assert not dm.evaluate('window.__csp'),dm.evaluate('window.__csp');assert not proof['errors'],proof['errors'];proof['status']='pass'
    except BaseException as error:proof.update(status='fail',failure=str(error));raise
    finally:
        (ROOT/'live-hub-result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');chrome.close()
