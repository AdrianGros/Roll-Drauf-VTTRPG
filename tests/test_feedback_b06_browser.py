"""Real export, brush and draft journeys for the B06 feedback contract."""
import io
import json
import zipfile
from pathlib import Path

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
