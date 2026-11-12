"""Real worker preview -> one normal layer -> undo/redo and persisted exports."""
import json,time,zipfile,io
import pytest
from PIL import Image
from playwright.sync_api import expect
from tests.test_mapmaker_library_browser import site,summary,save,clean  # noqa:F401
from tests.test_mapmaker_browser import browser  # noqa:F401

@pytest.mark.parametrize('width,theme,language',[(1440,'paper','de'),(390,'night','en')])
def test_preview_is_local_adoption_is_one_undo_and_exports_roundtrip(site,browser,tmp_path,width,theme,language):
    page,errors=site[3](browser,width=width,preferences={'theme':theme,'language':language})
    page.locator('#newEmpty').click()
    before=summary(page);pixels=page.evaluate('window.rdMapmaker.sampleRegion(1180,780,40,40)')
    page.locator('#landmassBtn').click();dialog=page.locator('#landmassDialog')
    dialog.locator('[name=resolution]').select_option('512')
    page.evaluate("""()=>{const button=document.getElementById('landmassAdopt');document.getElementById('landmassPreview').addEventListener('click',()=>window.__previewStart=performance.now(),true);new MutationObserver(()=>{if(!button.disabled)window.__previewElapsed=(performance.now()-window.__previewStart)/1000}).observe(button,{attributes:true,attributeFilter:['disabled']})}""")
    page.locator('#landmassPreview').click()
    expect(page.locator('#landmassAdopt')).to_be_enabled(timeout=10000)
    elapsed=page.evaluate('window.__previewElapsed')
    assert elapsed<(2 if width==1440 else 5),elapsed
    status=page.locator('#landmassStatus').inner_text();assert 'landmass-v1' in status and '1337' in status
    assert summary(page)['generation']==before['generation'] and summary(page)['historySteps']==before['historySteps']
    assert page.evaluate('window.rdMapmaker.sampleRegion(1180,780,40,40)')==pixels
    # Parameter changes invalidate the result immediately; closing stays mutation-free.
    dialog.locator('[name=seed]').fill('42');expect(page.locator('#landmassAdopt')).to_be_disabled()
    page.locator('#landmassCancel').click();assert summary(page)['generation']==before['generation']
    page.locator('#landmassBtn').click();page.locator('#landmassPreview').click();expect(page.locator('#landmassAdopt')).to_be_enabled(timeout=10000)
    page.locator('#landmassAdopt').click();expect(dialog).not_to_be_visible()
    after=summary(page);assert len(after['layers'])==len(before['layers'])+1
    assert after['historySteps']==before['historySteps']+1
    assert after['layers'][:-1]==before['layers'] and after['layers'][-1]['name'].startswith('landmass-v1 42 ')
    painted=page.evaluate('window.rdMapmaker.sampleRegion(1180,780,40,40)');assert painted!=pixels
    page.locator('#undoBtn').click();assert summary(page)['layers']==before['layers']
    assert page.evaluate('window.rdMapmaker.sampleRegion(1180,780,40,40)')==pixels
    page.locator('#redoBtn').click();assert summary(page)['layers']==after['layers']
    assert page.evaluate('window.rdMapmaker.sampleRegion(1180,780,40,40)')==painted
    save(page)
    page.locator('#fileMenuBtn').click()
    with page.expect_download() as download:page.locator('#saveBtn').click()
    target=tmp_path/'landmass.rdmap.json';download.value.save_as(target)
    original=json.loads(target.read_text());assert original['layers'][-1]['effects']['coast'] is True
    page.locator('#exportActionBtn').click()
    with page.expect_download(timeout=60000) as download:page.locator('#exportBundle').click()
    bundle=tmp_path/'landmass.zip';download.value.save_as(bundle)
    with zipfile.ZipFile(bundle) as z:
        raw=json.loads(z.read(next(n for n in z.namelist() if n.endswith('.json'))))
        assert raw['layers'][-1]['png']==original['layers'][-1]['png']
        png=Image.open(io.BytesIO(z.read(next(n for n in z.namelist() if n.endswith('.png')))))
        assert png.size==(2400,1600) and 'CREDITS.txt' in z.namelist()
    expect(page.locator('#exportDialog')).not_to_be_visible()
    page.reload();expect(page.locator('#restoreDialog')).to_be_visible(timeout=30000);page.locator('#restoreYes').click()
    page.wait_for_selector('#app[data-state=ready]');assert summary(page)['layers']==after['layers']
    page.locator('#fileInput').set_input_files(str(target));expect(page.locator('#toast')).to_contain_text('geladen' if language=='de' else 'loaded',timeout=30000)
    assert summary(page)['layers']==after['layers']
    assert page.evaluate('document.documentElement.scrollWidth')<=width+1
    (tmp_path/'preview-performance.json').write_text(json.dumps({'width':width,'resolution':512,'seconds':elapsed}))
    clean(page,errors)

from tests.test_mapmaker_browser import preview_origin  # noqa:F401

@pytest.mark.parametrize('boundary',['history','layers','raster-count','raster-area','project-change'])
def test_adoption_preflight_preserves_document_history_and_allocates_no_full_raster(browser,preview_origin,boundary):
    page=browser.new_page(viewport={'width':390,'height':900});page.set_default_timeout(15000)
    page.goto(preview_origin+'/mapmaker/credits.html')
    page.evaluate('''async boundary=>{
        const {LandmassDialog}=await import('./js/landmass-dialog.js');
        const {History}=await import('./js/history.js');
        const button=document.createElement('button');button.id='landmassBtn';document.body.append(button);
        const size=boundary==='history'?{w:4096,h:4096}:boundary==='raster-area'?{w:2500,h:2000}:{w:256,h:256};
        const count=boundary==='layers'?32:boundary==='raster-count'?8:boundary==='raster-area'?6:1;
        const doc={size,layers:Array.from({length:count},(_,id)=>({id:String(id),kind:boundary.startsWith('raster')?'raster':'paths'}))};
        const history=new History();history.push({bytes:256,undo(){},redo(){}});
        const ed={doc,generation:0,history,canAddRaster(){const n=this.doc.layers.filter(l=>l.kind==='raster').length+1;return n<=8&&n*size.w*size.h<=32000000}};
        window.testLandmass={ed,controller:new LandmassDialog(ed)};
    }''',boundary)
    page.locator('#landmassBtn').click();page.locator('#landmassPreview').click();expect(page.locator('#landmassAdopt')).to_be_enabled(timeout=15000)
    page.evaluate('''boundary=>{
        if(boundary==='project-change')window.testLandmass.ed.generation++;
        window.__allocations=0;const original=document.createElement;
        document.createElement=function(tag,...args){if(tag==='canvas')window.__allocations++;return original.call(this,tag,...args)};
    }''',boundary)
    page.locator('#landmassAdopt').click()
    data=page.evaluate('''()=>({allocations:window.__allocations,steps:window.testLandmass.ed.history.undoStack.length,
        count:window.testLandmass.ed.doc.layers.length,status:document.getElementById('landmassStatus').textContent})''')
    assert data['allocations']==0 and data['steps']==1
    assert data['count']==({'layers':32,'raster-count':8,'raster-area':6}.get(boundary,1))
    if boundary!='project-change':assert 'Budget' in data['status']
    page.close()
