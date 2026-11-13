"""Real export, brush and draft journeys for the B06 feedback contract."""
import io
import json
import zipfile
from pathlib import Path
import pytest

from PIL import Image
from playwright.sync_api import expect
from tests.test_mapmaker_browser import browser, preview_origin, open_editor, STATIC  # noqa:F401


def test_raster_sources_survive_file_roundtrip_and_png_bundle(open_editor, tmp_path):
    ed = open_editor(choose_template=False)
    ed.page.locator('#newEmpty').click()
    ed.drag([(500, 500), (700, 550)])
    assert ed.summary()['stamps'] == 0
    with ed.page.expect_download() as pending:
        ed.menu('Als Datei speichern')
    saved = tmp_path / 'raster.rdmap.json'
    pending.value.save_as(saved)
    ed.page.locator('#fileInput').set_input_files(saved)
    expect(ed.page.locator('#toast')).to_contain_text('geladen')
    ed.menu('Als PNG exportieren')
    with ed.page.expect_download(timeout=60000) as pending:
        ed.page.locator('#exportBundle').click()
    bundle = tmp_path / 'raster.zip'
    pending.value.save_as(bundle)
    with zipfile.ZipFile(bundle) as archive:
        credits = archive.read('CREDITS.txt').decode()
        assert 'Rasterquellensammlung' in credits
        assets = STATIC / 'mapmaker/assets'
        for pack in json.loads((assets / 'packs.json').read_text())['packs']:
            manifest = json.loads((assets / pack['manifest']).read_text())
            if manifest.get('exportCredit'):
                assert manifest['exportCredit'] in credits, pack['id']
        png = archive.read(next(name for name in archive.namelist() if name.endswith('.png')))
        with Image.open(io.BytesIO(png)) as image:
            image.load()  # PNG credits follow the pixel data, before IEND.
            assert image.info['Credits'] == credits
    # Vector-only documents keep the existing precise pack projection.
    result = ed.page.evaluate("""async () => {
        const {creditsForDocument} = await import('/mapmaker/js/credits.js');
        return creditsForDocument({meta:{title:'Vector'},layers:[]},
            {stamps:new Map(),packs:[{id:'unused',credit:'UNUSED-ARTIST'}]});
    }""")
    assert 'UNUSED-ARTIST' not in result and 'Rasterquellensammlung' not in result
    ed.assert_clean()


def test_brush_shapes_image_color_opacity_and_frozen_gesture(open_editor):
    ed = open_editor(choose_template=False)
    ed.page.locator('#newEmpty').click()
    result = ed.page.evaluate("""async () => {
        const {StrokeEngine,imageBrush,brushMaterial} = await import('/mapmaker/js/brush.js');
        const {createCanvas} = await import('/mapmaker/js/document.js');
        const sample = (canvas,x,y) => [...canvas.getContext('2d').getImageData(x,y,1,1).data];
        const paint = (shape, image=null) => {
            const layer={canvas:createCanvas(128,128),rev:0},engine=new StrokeEngine(128,128);
            const settings={size:40,opacity:.5,softness:0,pressureEnabled:false,material:'forest',shape,image,colorEnabled:true,color:'#ff0000',texture:0};
            engine.begin(layer,settings);settings.opacity=1;settings.size=100;
            engine.addPoint(64,64,null);engine.flush();engine.addPoint(64,64,null);engine.end();
            return [sample(layer.canvas,64,64),sample(layer.canvas,79,79),sample(layer.canvas,79,64)];
        };
        const source=createCanvas(8,8);source.getContext('2d').fillStyle='#00ff00';source.getContext('2d').fillRect(0,0,8,8);
        const image=imageBrush(source,null,'Synthetic green'), square=paint('square'), diamond=paint('diamond'),round=paint('round'),picture=paint('image',image);
        const layer={canvas:createCanvas(128,128),rev:0}, engine=new StrokeEngine(128,128);
        engine.begin(layer,{size:40,opacity:1,softness:0,material:'forest',shape:'image',image});engine.addPoint(64,64,null);engine.flush();engine.cancel();
        return {square,diamond,round,picture,cancel:sample(layer.canvas,64,64),bounded:[image.canvas.width,image.canvas.height]};
    }""")
    assert result['square'][0] == [255, 0, 0, 128]
    assert result['square'][1][3] == 128
    assert result['diamond'][1][3] == result['round'][1][3] == 0
    assert result['diamond'][2][3] == 128
    assert result['picture'][0] == [0, 255, 0, 128]
    assert result['cancel'] == [0, 0, 0, 0]
    assert max(result['bounded']) <= 256
    ed.assert_clean()


@pytest.mark.parametrize('width', [1440, 390])
def test_independent_eraser_image_brush_coast_and_file_undo(open_editor, tmp_path, width):
    ed = open_editor(width=width, choose_template=False)
    ed.page.locator('#newEmpty').click()
    if width < 600:
        ed.tab('Werkzeug')
    ed.page.locator('#brushShape').select_option('square')
    ed.set_range('#brushOpacity', 35)
    ed.set_range('#brushSoftness', 65)
    ed.page.locator('#brushColorEnabled').check()
    ed.page.locator('#brushColor').fill('#cc3333')
    ed.set_range('#brushTexture', 0)
    ed.page.locator('#brushCoast').check()
    ed.page.locator('#brushCoastColor').fill('#112233')
    ed.page.locator('#brushCoastColor').dispatch_event('change')
    ed.set_range('#brushCoastWidth', 8)
    ed.tool('eraser')
    assert ed.page.locator('#brushOpacity').input_value() == '100'
    assert ed.page.locator('#brushSoftness').input_value() == '0'
    ed.set_range('#brushSize', 100)
    ed.tool('brush')
    assert ed.page.locator('#brushOpacity').input_value() == '35'
    assert ed.page.locator('#brushSoftness').input_value() == '65'
    assert ed.page.locator('#brushShape').input_value() == 'square'
    ed.tool('stamp')
    ed.page.locator('.mm-stamp').first.click()
    ed.page.locator('#stampAsBrush').click()
    expect(ed.page.locator('#brushShape')).to_have_value('image')
    expect(ed.page.locator('#brushColor')).to_be_disabled()
    if width < 600:
        ed.tab('Werkzeug')
    before = ed.region(480, 480, 150, 100)
    ed.drag([(500, 500), (600, 520)])
    after = ed.region(480, 480, 150, 100)
    assert after != before
    ed.page.keyboard.press('Control+z')
    assert ed.region(480, 480, 150, 100) == before
    ed.page.keyboard.press('Control+Shift+z')
    assert ed.region(480, 480, 150, 100) == after
    with ed.page.expect_download() as pending:
        ed.menu('Als Datei speichern')
    saved = tmp_path / 'brush.rdmap.json'
    pending.value.save_as(saved)
    from vtt.mapmaker_document import normalize_document
    normalized, _ = normalize_document(json.loads(saved.read_text()))
    effects = next(l['effects'] for l in normalized['layers'] if l['id'] == 'terrain')
    assert effects == {'coast': True, 'coastColor': '#112233', 'coastWidth': 8}
    ed.page.locator('#fileInput').set_input_files(saved)
    expect(ed.page.locator('#toast')).to_contain_text('geladen')
    assert ed.region(480, 480, 150, 100) == after
    ed.assert_clean()


def test_leave_guard_tracks_confirmed_local_generation_and_visibility_cancel(open_editor):
    ed = open_editor(choose_template=False)
    ed.page.locator('#newEmpty').click()
    ed.page.locator('#mapTitle').fill('Confirmed baseline')
    ed.page.wait_for_function('() => window.rdMapmaker.summary().autosave === "saved"')
    ed.page.evaluate("""async () => {
        const {DraftStore}=await import('/mapmaker/js/storage.js');const save=DraftStore.prototype.save;
        DraftStore.prototype.save=function(record){
            if (!window.__heldSave) return new Promise((resolve,reject)=>{
                window.__heldSave=()=>save.call(this,record).then(resolve,reject);
            });
            return save.call(this,record);
        };
    }""")
    ed.page.locator('#mapTitle').fill('First edit')
    assert ed.summary()['leaveWarning']
    ed.page.wait_for_function('() => !!window.__heldSave')
    ed.page.locator('#mapTitle').fill('Newer edit')
    ed.page.evaluate('window.__heldSave()')
    assert ed.summary()['leaveWarning']
    ed.page.wait_for_function('() => !window.rdMapmaker.summary().leaveWarning')
    before = ed.region(480, 480, 150, 100)
    history = ed.summary()['historySteps']
    start, end = ed.client(500, 500), ed.client(600, 520)
    ed.page.mouse.move(*start)
    ed.page.mouse.down()
    ed.page.mouse.move(*end, steps=4)
    assert ed.summary()['leaveWarning']
    downloads = []
    ed.page.on('download', lambda download: downloads.append(download))
    ed.page.keyboard.press('Control+s')
    expect(ed.page.locator('#toast')).to_contain_text('Zeichenbewegung zuerst beenden')
    assert not downloads
    ed.page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))")
    ed.page.mouse.up()
    assert ed.summary()['historySteps'] == history
    assert ed.region(480, 480, 150, 100) == before
    ed.page.wait_for_function('() => !window.rdMapmaker.summary().leaveWarning')
    ed.assert_clean()


from tests.test_mapmaker_library_browser import site  # noqa:E402,F401


@pytest.mark.parametrize('status', [401, 403])
def test_expired_library_auth_preserves_editor_and_permission_errors_stay_distinct(site, browser, status):
    page, errors = site[3](browser)
    page.locator('#newEmpty').click()
    page.locator('#mapTitle').fill('Keep this draft')
    page.route('**/api/assets/mapmaker/projects**', lambda route: route.fulfill(
        status=status, content_type='application/json', body=json.dumps({'error': 'Sign-in expired' if status == 401 else 'Permission denied'})))
    page.locator('#cloudSave').click()
    expect(page.locator('#libraryLogin')).to_be_visible() if status == 401 else expect(page.locator('#libraryLogin')).to_be_hidden()
    expect(page.locator('#mapTitle')).to_have_value('Keep this draft')
    assert '/static/mapmaker/' in page.url
    page.wait_for_function('() => window.rdMapmaker.summary().autosave === "saved"')
    assert not errors
