"""W02 browser journeys in the real Kartenwerkstatt (headless Chromium, production CSP).

Own images (pixel editor, upload with crop/colour key) through file, ZIP, draft and
table/Atlas snapshot; canonical object order; brush clip; named and explicitly
connected paths; label families; generator presets/outputs; tool-context layers.
"""
import base64
import hashlib
import io
import json
import zipfile

import pytest
from PIL import Image
from playwright.sync_api import expect

from tests.test_mapmaker_browser import browser, open_editor, preview_origin  # noqa: F401
from vtt.mapmaker_document import normalize_document


def new_empty(ed):
    ed.page.locator('#newEmpty').click()
    expect(ed.page.locator('#newDialog')).to_be_hidden()


def draw_pixels(page, start=(0.1, 0.1), end=(0.9, 0.9)):
    box = page.locator('#pixelCanvas').bounding_box()
    page.mouse.move(box['x'] + box['width'] * start[0], box['y'] + box['height'] * start[1])
    page.mouse.down()
    page.mouse.move(box['x'] + box['width'] * end[0], box['y'] + box['height'] * end[1], steps=12)
    page.mouse.up()


def pixel_alpha(page):
    return page.evaluate("""() => { const c = document.getElementById('pixelCanvas');
        return Array.from(c.getContext('2d').getImageData(0, 0, c.width, c.height).data).filter((v, i) => i % 4 === 3).reduce((a, b) => a + b, 0); }""")


def make_pixel_asset(page, label, color, start=(0.1, 0.1), end=(0.9, 0.9)):
    page.locator('#ownPixelBtn').click()
    expect(page.locator('#pixelDialog')).to_be_visible()
    page.locator('#pixelSize').select_option('16')
    page.locator('#pixelNew').click()
    page.locator('#pixelColor').fill(color)
    draw_pixels(page, start, end)
    page.locator('#pixelLabel').fill(label)
    page.locator('#pixelSave').click()
    expect(page.locator('#pixelDialog')).to_be_hidden()


def save_file(ed, path):
    with ed.page.expect_download() as pending:
        ed.menu('Als Datei speichern')
    pending.value.save_as(path)
    return json.loads(path.read_text())


def item_ids(ed):
    return [item['id'] for item in ed.summary()['items']]


def test_sha256_matches_hashlib_and_webcrypto(open_editor):
    ed = open_editor(choose_template=False)
    lengths = [0, 1, 55, 56, 63, 64, 65, 119, 120, 1000, 65537]
    result = ed.page.evaluate("""async (lengths) => {
        const {sha256Hex} = await import('/mapmaker/js/sha256.js');
        const out = [];
        for (const n of lengths) {
            const bytes = new Uint8Array(n);
            for (let i = 0; i < n; i++) bytes[i] = (i * 31 + 7) & 255;
            const web = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(b => b.toString(16).padStart(2, '0')).join('');
            out.push([sha256Hex(bytes), web]);
        }
        return out;
    }""", lengths)
    for n, (ours, web) in zip(lengths, result):
        assert ours == web == hashlib.sha256(bytes((i * 31 + 7) & 255 for i in range(n))).hexdigest(), n
    ed.assert_clean()


def test_pixel_editor_image_survives_file_bundle_draft_and_filters(open_editor, tmp_path):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('stamp')
    page.locator('#ownPixelBtn').click()
    page.locator('#pixelSize').select_option('16')
    page.locator('#pixelNew').click()
    draw_pixels(page)
    stroke = pixel_alpha(page)
    assert stroke > 0
    page.locator('#pixelUndo').click()
    assert pixel_alpha(page) == 0
    page.locator('#pixelRedo').click()
    assert pixel_alpha(page) == stroke
    page.locator('#pixelZoom').select_option('8')
    style = page.locator('#pixelCanvas').evaluate("c => [c.getBoundingClientRect().width, getComputedStyle(c).imageRendering]")
    assert style == [128, 'pixelated']  # zoom never smooths the bitmap
    page.locator('#pixelLabel').fill('Wachturm')
    page.locator('#pixelLicense').fill('CC0 1.0')
    steps = ed.summary()['historySteps']
    page.locator('#pixelSave').click()
    expect(page.locator('#pixelDialog')).to_be_hidden()
    summary = ed.summary()
    (own,) = summary['assets']
    assert own['id'].startswith('custom:') and (own['width'], own['height'], own['style']) == (16, 16, 'pixel')
    assert summary['stampAsset'] == own['id'] and summary['historySteps'] == steps + 1
    expect(page.locator(f'.mm-stamp[data-asset="{own["id"]}"]')).to_be_visible()
    before = ed.region(560, 560, 80, 80)
    ed.click_doc(600, 600)
    assert any(item.get('asset') == own['id'] for item in ed.summary()['items'])
    placed = ed.region(560, 560, 80, 80)
    assert placed != before
    make_pixel_asset(page, 'Unbenutzt', '#1133cc', (0.2, 0.8), (0.8, 0.2))
    assert [a['label'] for a in ed.summary()['assets']] == ['Wachturm', 'Unbenutzt']
    # Style/perspective filters: own images carry both, the pack filter isolates them.
    page.locator('#stampPack').select_option('custom')
    expect(page.locator('.mm-stamp')).to_have_count(2)
    page.locator('#stampPerspective').select_option('side')
    expect(page.locator('.mm-stamp')).to_have_count(0)
    page.locator('#stampPerspective').select_option('top')
    page.locator('#stampStyle').select_option('pixel')
    expect(page.locator('.mm-stamp')).to_have_count(2)
    page.locator('#stampPerspective').select_option('')
    page.locator('#stampStyle').select_option('')
    page.locator('#stampPack').select_option('')

    raw = save_file(ed, tmp_path / 'own.rdmap.json')
    assert [a['label'] for a in raw['assets']] == ['Wachturm', 'Unbenutzt']
    for entry in raw['assets']:
        data = base64.b64decode(entry['png'].split(',', 1)[1])
        assert entry['id'] == 'custom:' + hashlib.sha256(data).hexdigest()
        with Image.open(io.BytesIO(data)) as image:
            assert image.format == 'PNG' and image.size == (16, 16)
    normalized, _ = normalize_document(raw)
    assert [a['id'] for a in normalized['assets']] == [a['id'] for a in raw['assets']]

    page.locator('#exportActionBtn').click()
    with page.expect_download(timeout=60000) as pending:
        page.locator('#exportBundle').click()
    bundle = tmp_path / 'own.zip'
    pending.value.save_as(bundle)
    with zipfile.ZipFile(bundle) as archive:
        project = json.loads(archive.read(next(n for n in archive.namelist() if n.endswith('.json'))))
        credits = archive.read('CREDITS.txt').decode()
    assert [a['label'] for a in project['assets']] == ['Wachturm']  # portable: only the referenced image
    assert 'Wachturm' in credits and 'CC0 1.0' in credits and 'Unbenutzt' not in credits
    normalize_document(project)

    page.locator('#fileInput').set_input_files(str(tmp_path / 'own.rdmap.json'))
    expect(page.locator('#toast')).to_contain_text('geladen')
    assert [a['id'] for a in ed.summary()['assets']] == [a['id'] for a in raw['assets']]
    assert ed.region(560, 560, 80, 80) == placed

    used_id, unused_id = raw['assets'][0]['id'], raw['assets'][1]['id']
    page.locator('#ownAssetManage summary').click()
    expect(page.locator(f'#ownAssetList [data-asset="{used_id}"] button', has_text='Entfernen')).to_be_disabled()
    page.locator(f'#ownAssetList [data-asset="{unused_id}"] button', has_text='Entfernen').click()
    assert [a['id'] for a in ed.summary()['assets']] == [used_id]
    page.keyboard.press('Control+z')
    assert [a['id'] for a in ed.summary()['assets']] == [used_id, unused_id]

    page.wait_for_function('() => window.rdMapmaker.summary().autosave === "saved"')
    page.reload()
    expect(page.locator('#restoreDialog')).to_be_visible(timeout=30000)
    page.locator('#restoreYes').click()
    page.wait_for_selector('#app[data-state=ready]')
    assert [a['id'] for a in ed.summary()['assets']] == [used_id, unused_id]
    assert ed.region(560, 560, 80, 80) == placed
    ed.assert_clean()


def test_upload_crop_colour_key_and_rejections(open_editor, tmp_path):
    image = Image.new('RGBA', (64, 32), (255, 255, 255, 255))
    for x in range(8, 28):
        for y in range(6, 26):
            image.putpixel((x, y), (220, 20, 20, 255))
    for x in range(40, 60):
        for y in range(6, 26):
            image.putpixel((x, y), (20, 20, 220, 255))
    source = tmp_path / 'zwei-tuerme.png'
    image.save(source)
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('stamp')
    page.locator('#ownUploadBtn').click()
    page.locator('#ownUploadFile').set_input_files(str(source))
    expect(page.locator('#ownUploadSave')).to_be_enabled()
    expect(page.locator('#ownUploadLabel')).to_have_value('zwei tuerme')
    for key, value in (('X', 0), ('Y', 0), ('W', 32), ('H', 32)):
        page.locator(f'#ownCrop{key}').fill(str(value))
    page.locator('#ownKeyOn').check()
    page.locator('#ownKeyColor').fill('#ffffff')
    page.locator('#ownUploadSave').click()
    expect(page.locator('#ownUploadError')).to_contain_text('bestätigen')
    assert ed.summary()['assets'] == []
    page.locator('#ownUploadRights').check()
    page.locator('#ownUploadLicense').fill('Eigenes Foto')
    page.locator('#ownUploadSave').click()
    expect(page.locator('#ownUploadDialog')).to_be_hidden()
    (own,) = ed.summary()['assets']
    assert (own['width'], own['height'], own['license'], own['style']) == (32, 32, 'Eigenes Foto', 'painted')
    ed.click_doc(800, 800)
    raw = save_file(ed, tmp_path / 'upload.rdmap.json')
    data = base64.b64decode(raw['assets'][0]['png'].split(',', 1)[1])
    with Image.open(io.BytesIO(data)) as png:
        png = png.convert('RGBA')
        assert png.getpixel((0, 0))[3] == 0                    # white background keyed out
        assert png.getpixel((15, 15)) == (220, 20, 20, 255)    # red tower kept exactly
        assert all(png.getpixel((x, 15))[2] < 100 for x in range(32))  # blue tower cropped away
    svg = tmp_path / 'angriff.svg'
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>')
    page.locator('#ownUploadBtn').click()
    page.locator('#ownUploadFile').set_input_files(str(svg))
    expect(page.locator('#ownUploadError')).to_contain_text('SVG')
    expect(page.locator('#ownUploadSave')).to_be_disabled()
    page.locator('#ownUploadCancel').click()
    assert len(ed.summary()['assets']) == 1
    ed.assert_clean()


def test_client_validator_matches_server_bounds_and_isolation(open_editor):
    ed = open_editor(choose_template=False)
    result = ed.page.evaluate("""async () => {
        const {validateDocument, customAssetId, LIMITS} = await import('/mapmaker/js/document.js');
        const png = async (w, h, color) => { const c = document.createElement('canvas'); c.width = w; c.height = h;
            const x = c.getContext('2d'); x.fillStyle = color; x.fillRect(0, 0, w, h);
            return new Uint8Array(await (await new Promise(r => c.toBlob(r, 'image/png'))).arrayBuffer()); };
        const b64 = (bytes) => { let s = ''; for (const b of bytes) s += String.fromCharCode(b); return btoa(s); };
        const entry = (bytes, w, h, extra = {}) => ({id: customAssetId(bytes), label: 'T', png: 'data:image/png;base64,' + b64(bytes), width: w, height: h, ...extra});
        const doc = (assets, asset) => ({format: 'rd-mapmaker', version: 1, size: {w: 256, h: 256}, meta: {}, sea: {},
            layers: [{id: 's', kind: 'stamps', name: 'S', items: asset ? [{id: 'a', asset, x: 10, y: 10, size: 20}] : []}], ...(assets ? {assets} : {})});
        const check = (raw, known = new Map()) => { try { validateDocument(raw, {knownAssets: known}); return 'ok'; } catch (e) { return e.constructor.name; } };
        const red = await png(16, 16, '#c00'), id = customAssetId(red);
        const many = [];
        for (let i = 0; i < 33; i++) many.push(entry(await png(4, 4, `rgb(${i},0,0)`), 4, 4));
        return {
            ok: check(doc([entry(red, 16, 16)], id)),
            old: check(doc(null, null)),
            foreign: check(doc(null, id), new Map([[id, {w: 16, h: 16}]])),
            wrongId: check(doc([{...entry(red, 16, 16), id: 'custom:' + '0'.repeat(64)}])),
            wrongSize: check(doc([entry(red, 15, 16)])),
            url: check(doc([{...entry(red, 16, 16), png: 'https://example.invalid/x.png'}])),
            style: check(doc([entry(red, 16, 16, {style: 'gif'})])),
            tooMany: check(doc(many)),
            limits: [LIMITS.customAssets, LIMITS.customAssetBytes, LIMITS.customAssetTotalBytes, LIMITS.customAssetSide, LIMITS.customAssetPixels],
        };
    }""")
    assert result['ok'] == result['old'] == 'ok'
    for key in ('foreign', 'wrongId', 'wrongSize', 'url', 'style', 'tooMany'):
        assert result[key] == 'ValidationError', key
    from vtt import mapmaker_document as server
    assert result['limits'] == [server.MAX_CUSTOM_ASSETS, server.MAX_CUSTOM_ASSET_BYTES, server.MAX_CUSTOM_TOTAL_BYTES,
                                server.MAX_CUSTOM_SIDE, server.MAX_CUSTOM_PIXELS]
    ed.assert_clean()


def test_table_and_atlas_snapshot_render_and_credit_embedded_images(open_editor):
    ed = open_editor(choose_template=False)
    result = ed.page.evaluate("""async () => {
        const {loadSnapshotPalette, snapshotFromProject} = await import('/mapmaker/js/snapshot.js');
        const {creditsForDocument} = await import('/mapmaker/js/credits.js');
        const {customAssetId} = await import('/mapmaker/js/document.js');
        const c = document.createElement('canvas'); c.width = c.height = 32;
        const x = c.getContext('2d'); x.fillStyle = '#e01010'; x.fillRect(0, 0, 32, 32);
        const bytes = new Uint8Array(await (await new Promise(r => c.toBlob(r, 'image/png'))).arrayBuffer());
        let s = ''; for (const b of bytes) s += String.fromCharCode(b);
        const asset = {id: customAssetId(bytes), label: 'Roter Turm', png: 'data:image/png;base64,' + btoa(s), width: 32, height: 32,
            style: 'painted', perspective: 'top', source: 'Test', license: 'CC0 1.0'};
        const doc = (items) => ({format: 'rd-mapmaker', version: 1, size: {w: 256, h: 256}, meta: {title: 'Snap'},
            sea: {top: '#2f5d6e', bottom: '#2f5d6e'}, layers: [{id: 's', kind: 'stamps', name: 'S', items}], assets: [asset]});
        const palette = await loadSnapshotPalette();
        const sample = async (snapshot) => { const bitmap = await createImageBitmap(snapshot.blob); const k = document.createElement('canvas');
            k.width = bitmap.width; k.height = bitmap.height; const kx = k.getContext('2d'); kx.drawImage(bitmap, 0, 0);
            return [...kx.getImageData(128, 128, 1, 1).data]; };
        const stamped = doc([{id: 'a', asset: asset.id, x: 128, y: 128, size: 64}]);
        const withStamp = await snapshotFromProject({project: {id: 'p', revision: 1}, document: stamped, palette});
        const without = await snapshotFromProject({project: {id: 'p', revision: 1}, document: doc([]), palette});
        return {stamp: await sample(withStamp), sea: await sample(without), size: [withStamp.width, withStamp.height],
            credits: creditsForDocument(stamped, palette), unused: creditsForDocument(doc([]), palette)};
    }""")
    assert result['size'] == [256, 256]
    assert result['stamp'] != result['sea']
    assert result['stamp'][0] > result['stamp'][1] + 60 and result['stamp'][0] > result['stamp'][2] + 60
    assert 'Roter Turm – Quelle: Test – Lizenz: CC0 1.0' in result['credits']
    assert 'Roter Turm' not in result['unused']
    ed.assert_clean()


def test_object_order_buttons_keys_and_alt_wheel_are_one_step_each(open_editor, tmp_path):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('stamp')
    ed.click_doc(600, 600)
    ed.click_doc(600, 600)
    first, second = item_ids(ed)
    ed.tool('select')
    ed.click_doc(600, 600)
    assert ed.summary()['selection'] == second  # the later list entry is on top
    steps = ed.summary()['historySteps']
    page.locator('#inspector [data-order=back]').click()
    assert item_ids(ed) == [second, first] and ed.summary()['historySteps'] == steps + 1
    ed.click_doc(600, 600)
    assert ed.summary()['selection'] == first  # hit test follows the canonical list
    page.keyboard.press('Control+z')
    assert item_ids(ed) == [first, second]
    steps = ed.summary()['historySteps']
    page.locator('#mapCanvas').focus()
    page.keyboard.press('PageUp')
    assert item_ids(ed) == [second, first] and ed.summary()['historySteps'] == steps + 1
    zoom, steps = ed.summary()['zoom'], ed.summary()['historySteps']
    page.mouse.move(*ed.client(600, 600))
    page.keyboard.down('Alt')
    for _ in range(3):
        page.mouse.wheel(0, 120)
    page.keyboard.up('Alt')
    page.wait_for_function(f'() => window.rdMapmaker.summary().historySteps === {steps + 1} && !window.rdMapmaker.summary().mutating')
    assert item_ids(ed) == [first, second] and ed.summary()['zoom'] == zoom
    page.mouse.wheel(0, -240)
    page.wait_for_function(f'() => window.rdMapmaker.summary().zoom !== {zoom}')  # the plain wheel still zooms
    assert ed.summary()['historySteps'] == steps + 1
    raw = save_file(ed, tmp_path / 'order.rdmap.json')
    assert [item['id'] for item in next(l for l in raw['layers'] if l['id'] == 'symbols')['items']] == item_ids(ed)
    ed.assert_clean()


def test_brush_clip_paints_only_on_reference_and_keeps_old_pixels(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('brush')
    page.locator('.mm-swatch[data-material=land]').click()
    assert ed.summary()['activeLayer'] == 'land'
    ed.drag([(400, 400), (700, 400)])
    page.locator('.mm-swatch[data-material=forest]').click()
    assert ed.summary()['activeLayer'] == 'terrain'
    ed.drag([(1300, 900), (1400, 900)])  # earlier terrain outside the land
    old, sea = ed.region(1320, 880, 60, 40), ed.region(1000, 380, 60, 40)
    page.locator('#brushClip').select_option('land')
    assert ed.summary()['clip'] == 'land'
    page.locator('.mm-swatch[data-material=desert]').click()
    land_before = ed.region(520, 380, 60, 40)
    steps = ed.summary()['historySteps']
    ed.drag([(450, 400), (1000, 400), (1350, 900)])
    assert ed.region(520, 380, 60, 40) != land_before
    assert ed.region(1000, 380, 60, 40) == sea and ed.region(1320, 880, 60, 40) == old
    assert ed.summary()['historySteps'] == steps + 1
    page.keyboard.press('Control+z')
    assert ed.region(520, 380, 60, 40) == land_before
    ed.tab('Ebenen')
    page.locator('.mm-layer[data-layer=land] .mm-danger-icon').click()
    summary = ed.summary()
    assert summary['clip'] is None and 'gelöscht' in summary['clipNotice']
    assert 'gelöscht' in page.locator('#brushClipHint').text_content()
    page.keyboard.press('Control+z')
    assert ed.summary()['clip'] is None  # stays off after the reference returns; the user chooses again
    ed.assert_clean()


def test_named_paths_connect_only_by_explicit_action(open_editor, tmp_path):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('path')
    ed.drag([(400, 600), (550, 600), (700, 600)])
    ed.drag([(715, 610), (850, 615), (1000, 620)])
    ed.drag([(550, 450), (550, 600), (550, 750)])  # crosses the first path
    paths = [item for item in ed.summary()['items'] if 'points' in item]
    assert len(paths) == 3
    first = paths[0]
    ed.tool('select')
    ed.click_doc(450, 600)
    assert ed.summary()['selection'] == first['id']
    page.locator('#selPathName').fill('Königsweg')
    page.locator('#selPathName').press('Enter')
    steps = ed.summary()['historySteps']
    page.locator('#selPathConnect').click()
    after = [item for item in ed.summary()['items'] if 'points' in item]
    merged = next(item for item in after if item['id'] == first['id'])
    assert len(after) == 2 and paths[2]['id'] in [item['id'] for item in after]
    assert merged['name'] == 'Königsweg' and len(merged['points']) == len(first['points']) + len(paths[1]['points']) - 1
    assert ed.summary()['historySteps'] == steps + 1
    page.keyboard.press('Control+z')
    restored = [item for item in ed.summary()['items'] if 'points' in item]
    assert len(restored) == 3 and next(i for i in restored if i['id'] == first['id'])['name'] == 'Königsweg'
    page.keyboard.press('Control+Shift+z')
    raw = save_file(ed, tmp_path / 'paths.rdmap.json')
    saved = normalize_document(raw)[0]
    names = [item.get('name') for layer in saved['layers'] if layer['kind'] == 'paths' for item in layer['items']]
    assert names.count('Königsweg') == 1 and len(names) == 2
    ed.click_doc(550, 460)
    assert ed.summary()['selection'] == paths[2]['id']
    page.locator('#selPathConnect').click()
    expect(page.locator('#toast')).to_contain_text('Kein passender Endpunkt')
    assert len([item for item in ed.summary()['items'] if 'points' in item]) == 2
    ed.assert_clean()


def test_label_family_is_separate_from_style_and_roundtrips(open_editor, tmp_path):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('label')
    page.locator('#labelStyle').select_option('city')
    page.locator('#labelFont').select_option('cinzel')
    ed.click_doc(900, 700)
    label = lambda: next(item for item in ed.summary()['items'] if 'text' in item)  # noqa: E731
    assert (label()['font'], label()['style']) == ('cinzel', 'city')
    expect(page.locator('#selFont')).to_have_value('cinzel')
    cinzel = ed.region(820, 600, 160, 80)
    page.locator('#selFont').select_option('literata')
    assert (label()['font'], label()['style']) == ('literata', 'city')
    assert ed.region(820, 600, 160, 80) != cinzel
    page.locator('#selFont').select_option('')
    assert not label().get('font')
    page.locator('#selFont').select_option('badscript')
    saved = normalize_document(save_file(ed, tmp_path / 'fonts.rdmap.json'))[0]
    (item,) = [i for layer in saved['layers'] if layer['kind'] == 'labels' for i in layer['items']]
    assert (item['font'], item['style']) == ('badscript', 'city')
    ed.assert_clean()


def test_generator_presets_tile_output_and_seeded_decoration_are_one_undo(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    before = ed.summary()
    dialog = page.locator('#landmassDialog')

    def generate(preset=True):
        page.locator('#landmassBtn').click()
        if preset:
            page.locator('#landmassPreset').select_option('builtin:continent')
            expect(dialog.locator('[name=seed]')).to_have_value('4242')
            dialog.locator('[name=output]').select_option('tile')
            dialog.locator('[name=mountains]').check()
            dialog.locator('[name=forest]').check()
        page.locator('#landmassPreview').click()
        expect(page.locator('#landmassAdopt')).to_be_enabled(timeout=15000)
        status = page.locator('#landmassStatus').inner_text()
        assert '4242' in status and 'Symbole' in status
        assert ed.summary()['generation'] == before['generation'] or not preset
        page.locator('#landmassAdopt').click()
        expect(dialog).to_be_hidden()
        summary = ed.summary()
        added = summary['layers'][len(before['layers']):]
        return summary, added, [(i['asset'], i['x'], i['y']) for i in summary['items'] if i['layer'] == added[-1]['id']]

    after, added, decoration = generate()
    assert after['historySteps'] == before['historySteps'] + 1
    assert [layer['kind'] for layer in added] == ['tiles', 'stamps'] and added[0]['name'].startswith('landmass-v1 4242 C')
    assert added[0]['tiles'] and decoration and {asset for asset, _, _ in decoration} <= {'kenney:mountains', 'kenney:forest'}
    page.locator('#undoBtn').click()
    assert ed.summary()['layers'] == before['layers']
    _, again, repeated = generate(preset=False)  # same fields: same land, same separate decoration stream
    assert repeated == decoration and again[0]['tiles'] == added[0]['tiles']
    page.locator('#landmassBtn').click()
    page.locator('#landmassPresetName').fill('Meine Küste')
    page.locator('#landmassPresetSave').click()
    expect(page.locator('#landmassPreset option', has_text='Meine Küste')).to_have_count(1)
    stored = page.evaluate("JSON.parse(localStorage.getItem('rd-mapmaker-landmass-presets'))")
    assert stored[0]['version'] == 'landmass-v1' and stored[0]['parameters']['seed'] == 4242 and stored[0]['output'] == 'tile'
    page.locator('#landmassCancel').click()
    ed.assert_clean()


def test_area_fill_is_one_step_and_refuses_over_budget_before_placing(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('stamp')
    page.locator('#stampScatter').check()
    page.locator('#stampArea').check()
    expect(page.locator('#stampScatter')).not_to_be_checked()
    steps = ed.summary()['historySteps']
    ed.drag([(400, 400), (700, 600)])
    summary = ed.summary()
    assert summary['stamps'] > 1 and summary['historySteps'] == steps + 1
    assert all(399 <= i['x'] <= 701 and 399 <= i['y'] <= 601 for i in summary['items'])
    page.keyboard.press('Control+z')
    assert ed.summary()['stamps'] == 0
    ed.set_range('#stampSize', 16)
    ed.drag([(100, 100), (2300, 1500)])
    expect(page.locator('#toast')).to_contain_text('Budget')
    summary = ed.summary()
    assert summary['stamps'] == 0 and summary['historySteps'] == steps and summary['canRedo']
    ed.assert_clean()


@pytest.mark.parametrize('width', [1440, 390])
def test_layer_choice_lives_in_the_tool_context_with_keyboard(open_editor, width):
    ed = open_editor(width=width, choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('brush')
    if width < 600:
        ed.tab('Werkzeug')
    select = page.locator('#toolLayer')
    expect(select).to_be_visible()
    assert select.locator('option').all_inner_texts() == ['Flüsse & Wege', 'Gelände', 'Land']
    select.select_option('land')
    assert ed.summary()['activeLayer'] == 'land'
    page.locator('#mapCanvas').focus()
    page.keyboard.press('Alt+ArrowUp')
    assert ed.summary()['activeLayer'] == 'terrain'
    ed.tool('stamp')
    expect(select).to_be_visible()
    assert select.locator('option').all_inner_texts() == ['Symbole']
    box = select.bounding_box()
    assert box['x'] >= 0 and box['x'] + box['width'] <= width + 1
    assert page.evaluate('document.documentElement.scrollWidth') <= width + 1
    ed.assert_clean()


def test_crop_comparison_detects_cut_content_and_fits_a_clean_crop(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    failed_urls = []
    page.on('response', lambda response: failed_urls.append(response.url) if response.status >= 400 else None)
    result = page.evaluate("""async () => {
        const {cropCutSides, fitCropToContent} = await import('/mapmaker/js/ui.js');
        const w = 40, h = 30, alpha = new Uint8Array(w * h);
        for (let y = 5; y < 20; y++) for (let x = 10; x < 30; x++) alpha[y * w + x] = 1;
        const sheet = {w, h, alpha}, cut = {x: 10, y: 5, w: 12, h: 15};
        return {cut: cropCutSides(cut, sheet), clean: cropCutSides({x: 10, y: 5, w: 20, h: 15}, sheet),
            fit: fitCropToContent(cut, sheet), trimmed: fitCropToContent({x: 0, y: 0, w: 40, h: 30}, sheet),
            empty: fitCropToContent({x: 0, y: 25, w: 5, h: 5}, sheet)};
    }""")
    assert result['cut'] == ['right'] and result['clean'] == []
    assert result['fit'] == result['trimmed'] == {'x': 10, 'y': 5, 'w': 20, 'h': 15}
    assert result['empty'] is None
    ed.tool('stamp')
    page.locator('#stampCrop').click()
    expect(page.locator('#sheetDialog')).to_be_visible()
    expect(page.locator('#sheetCropInfo')).to_contain_text('Quelle')
    page.locator('#sheetCancel').click()
    assert not failed_urls, failed_urls
    ed.assert_clean()
