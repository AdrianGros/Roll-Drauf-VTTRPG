"""FV07 object list, label preview and rotation presets; FV08 node-by-node paths and
the explicit draw/edit switch, in the real Kartenwerkstatt (headless Chromium, production CSP).

The label preview lives on the display canvas overlay, not in the document composite,
so those checks sample #mapCanvas itself.
"""
import pytest
from playwright.sync_api import expect

from tests.test_mapmaker_browser import browser, open_editor, preview_origin  # noqa: F401
from tests.test_review_maps_browser import new_empty, save_file
from tests.test_c27_mapmaker_browser import CASTLE, choose_stamp

GRASS = 'color:kenney-tiny_33382ddbb14436e9'

SCREEN_REGION = """([x, y, w, h]) => {
    const canvas = document.getElementById('mapCanvas');
    const rect = canvas.getBoundingClientRect();
    const dpr = canvas.width / rect.width;
    const data = canvas.getContext('2d').getImageData(Math.round((x - rect.left) * dpr), Math.round((y - rect.top) * dpr),
        Math.round(w * dpr), Math.round(h * dpr)).data;
    return Array.from(data);
}"""
TWO_FRAMES = "() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))"


def paths(ed):
    return [entry for entry in ed.summary()['items'] if 'points' in entry]


def item(ed, item_id):
    return next(entry for entry in ed.summary()['items'] if entry['id'] == item_id)


def objects_tab(ed):
    ed.page.locator('#tab-objects').click()
    expect(ed.page.locator('#pane-objects')).to_be_visible()


def row(ed, key):
    return ed.page.locator(f'#objectList .mm-object[data-key="{key}"]')


def screen_region(ed, x, y, w, h):
    return ed.page.evaluate(SCREEN_REGION, [x, y, w, h])


def changed_pixels(a, b):
    return sum(1 for i in range(0, len(a), 4) if max(abs(a[i + c] - b[i + c]) for c in range(3)) > 12)


def build_scene(ed):
    """One named path, one stamp, one label and one tile group on an empty map."""
    page = ed.page
    ed.tool('path')
    ed.drag([(400, 400), (600, 450), (800, 400)])
    (path,) = paths(ed)
    page.locator('#selPathName').fill('Königsweg')
    page.locator('#selPathName').press('Enter')
    ed.tool('stamp')
    choose_stamp(page, 'kenney-cartography', CASTLE)
    ed.click_doc(1000, 1000)
    ed.tool('label')
    ed.click_doc(1400, 600)
    ed.tool('tile')
    page.locator('#tilePack').select_option('kenney-tiny')
    page.locator('#tileSearch').fill('Gras')
    page.locator(f'.mm-tile-btn[data-tile="{GRASS}"]').click()
    ed.drag([(1600, 1310), (1700, 1310)], steps=2)
    summary = ed.summary()
    stamp = next(entry for entry in summary['items'] if 'asset' in entry)
    label = next(entry for entry in summary['items'] if 'text' in entry)
    tiles = next(layer for layer in summary['layers'] if layer['kind'] == 'tiles')
    return path['id'], stamp['id'], label['id'], tiles


# ---- FV07: object list --------------------------------------------------------

def test_object_list_and_map_share_one_selection(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    path_id, stamp_id, label_id, tiles = build_scene(ed)
    objects_tab(ed)
    expect(page.locator('#objectCount')).to_have_text('4 von 4 Objekten')
    expect(row(ed, path_id)).to_contain_text('Königsweg')
    tile_key = f"tiles:{tiles['id']}:{GRASS}"
    expect(row(ed, tile_key)).to_contain_text(f"Kacheln: {len(tiles['tiles'])}")

    # list → map, staying in the list
    row(ed, stamp_id).click()
    summary = ed.summary()
    assert summary['tool'] == 'select' and summary['selectedIds'] == [stamp_id]
    expect(page.locator('#pane-objects')).to_be_visible()
    expect(row(ed, stamp_id)).to_have_attribute('aria-pressed', 'true')
    expect(row(ed, stamp_id)).to_be_focused()
    row(ed, label_id).click(modifiers=['Shift'])
    assert sorted(ed.summary()['selectedIds']) == sorted([stamp_id, label_id])
    expect(row(ed, stamp_id)).to_have_attribute('aria-pressed', 'true')
    expect(row(ed, label_id)).to_have_attribute('aria-pressed', 'true')

    # a tile group selects exactly its cells through the tile selection
    row(ed, tile_key).click()
    summary = ed.summary()
    assert summary['selectedIds'] == [] and summary['activeLayer'] == tiles['id']
    assert summary['selectedTiles']['layerId'] == tiles['id']
    assert len(summary['selectedTiles']['keys']) == len(tiles['tiles']) == summary['selectionCount']
    expect(row(ed, tile_key)).to_have_attribute('aria-pressed', 'true')

    # map → list (the list centred the view on the tiles; fit the whole map first)
    page.locator('#zoomFit').click()
    ed.click_doc(600, 450)
    assert ed.summary()['selectedIds'] == [path_id]
    expect(row(ed, path_id)).to_have_attribute('aria-pressed', 'true')
    expect(row(ed, tile_key)).to_have_attribute('aria-pressed', 'false')

    # filters and counts
    page.locator('#objectKind').select_option('paths')
    expect(page.locator('#objectCount')).to_have_text('1 von 4 Objekten')
    page.locator('#objectKind').select_option('')
    page.locator('#objectLayer').select_option('symbols')
    expect(page.locator('#objectList .mm-object')).to_have_count(1)
    expect(row(ed, stamp_id)).to_be_visible()
    page.locator('#objectLayer').select_option('')
    page.locator('#objectSearch').fill('könig')
    expect(page.locator('#objectList .mm-object')).to_have_count(1)
    expect(row(ed, path_id)).to_be_visible()
    page.locator('#objectSearch').fill('nichts dergleichen')
    expect(page.locator('#objectList')).to_contain_text('Keine Objekte für diesen Filter.')
    page.locator('#objectSearch').fill('')

    # path naming is reachable from the list
    row(ed, path_id).click()
    page.locator('#objectEdit').click()
    expect(page.locator('#pane-tool')).to_be_visible()
    expect(page.locator('#selPathName')).to_be_focused()
    expect(page.locator('#selPathName')).to_have_value('Königsweg')

    # hidden layers stay visible in the list but cannot be selected from it
    ed.tab('Ebenen')
    page.locator('#layerList .mm-layer[data-layer="labels"] [data-layer-control="visible"]').click()
    objects_tab(ed)
    expect(row(ed, label_id)).to_be_disabled()
    expect(row(ed, label_id)).to_contain_text('Ebene ausgeblendet')
    ed.assert_clean()


def test_object_list_fits_the_phone_layout(open_editor):
    ed = open_editor(width=390)
    page = ed.page
    objects_tab(ed)
    first = page.locator('#objectList .mm-object:not([disabled])').first
    expect(first).to_be_visible()
    key = first.get_attribute('data-key')
    first.click()
    summary = ed.summary()
    assert key in summary['selectedIds'] or (summary['selectedTiles'] and key.startswith('tiles:'))
    expect(row(ed, key)).to_have_attribute('aria-pressed', 'true')
    assert page.evaluate('() => document.documentElement.scrollWidth <= window.innerWidth + 1')
    ed.assert_clean()


# ---- FV07: label preview and rotation presets ---------------------------------

def test_label_preview_follows_the_pointer_without_changing_the_map(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('label')
    page.locator('#labelKind').select_option('')  # plain label: name only
    x, y = ed.client(1200, 800)
    page.mouse.move(x, y + 300)
    page.evaluate(TWO_FRAMES)
    before = screen_region(ed, x - 60, y - 30, 120, 60)
    steps, generation = ed.summary()['historySteps'], ed.summary()['generation']
    page.mouse.move(x, y)
    page.evaluate(TWO_FRAMES)
    preview = screen_region(ed, x - 60, y - 30, 120, 60)
    assert changed_pixels(before, preview) > 80, 'no label preview under the pointer'
    summary = ed.summary()
    assert summary['items'] == [] and summary['historySteps'] == steps and summary['generation'] == generation
    page.mouse.move(x, y + 300)
    page.evaluate(TWO_FRAMES)
    assert changed_pixels(before, screen_region(ed, x - 60, y - 30, 120, 60)) < 20, 'preview did not follow the pointer'
    ed.click_doc(1200, 800)
    (placed,) = ed.summary()['items']
    assert (placed['x'], placed['y']) == pytest.approx((1200, 800), abs=1.5)
    ed.assert_clean()


def test_rotation_presets_store_the_same_value_as_the_slider(open_editor, tmp_path):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('stamp')
    choose_stamp(page, 'kenney-cartography', CASTLE)
    ed.click_doc(1000, 1000)
    (stamp,) = ed.summary()['items']
    ed.tool('select')
    ed.click_doc(1000, 1000)
    assert ed.summary()['selection'] == stamp['id']
    steps = ed.summary()['historySteps']
    page.locator('#inspectStamp .mm-rot-presets button[data-rot="90"]').click()
    assert item(ed, stamp['id'])['rot'] == 90 and ed.summary()['historySteps'] == steps + 1
    expect(page.locator('#selStampRot')).to_have_value('90')
    page.locator('#mapCanvas').focus()
    page.keyboard.press('Control+z')
    assert item(ed, stamp['id'])['rot'] == 0
    ed.set_range('#selStampRot', 90)
    assert item(ed, stamp['id'])['rot'] == 90 and ed.summary()['historySteps'] == steps + 1
    page.locator('#inspectStamp .mm-rot-presets button[data-rot="90"]').click()  # same value: no extra step
    assert ed.summary()['historySteps'] == steps + 1

    ed.tool('label')
    ed.click_doc(1400, 600)
    (label,) = [entry for entry in ed.summary()['items'] if 'text' in entry]
    assert ed.summary()['selection'] == label['id']
    page.locator('#inspectLabel .mm-rot-presets button[data-rot="-45"]').click()
    assert item(ed, label['id'])['rot'] == -45
    expect(page.locator('#selRot')).to_have_value('-45')
    saved = save_file(ed, tmp_path / 'rotation.rdmap.json')
    stored = {entry['id']: entry['rot'] for layer in saved['layers'] for entry in layer.get('items', [])}
    assert stored == {stamp['id']: 90, label['id']: -45}
    ed.assert_clean()


# ---- FV08: node-by-node paths -------------------------------------------------

def test_set_nodes_mode_finishes_removes_cancels_and_roundtrips(open_editor, tmp_path):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('path')
    ed.drag([(300, 1500), (500, 1550), (700, 1500)])  # an existing freehand path
    (existing,) = paths(ed)
    page.locator('input[name="pathMode"][value="nodes"]').check()
    expect(page.locator('#pathNodesHint')).to_be_visible()
    expect(page.locator('#pathFreehandHint')).to_be_hidden()
    steps = ed.summary()['historySteps']

    for point in [(400, 400), (600, 500), (800, 420)]:
        ed.click_doc(*point)
    expect(page.locator('#pathDraftStatus')).to_have_text('Punkte gesetzt: 3')
    assert len(paths(ed)) == 1 and ed.summary()['historySteps'] == steps  # nothing stored yet
    page.keyboard.press('Backspace')
    expect(page.locator('#pathDraftStatus')).to_have_text('Punkte gesetzt: 2')
    ed.click_doc(800, 420)
    page.keyboard.press('Control+z')  # undo removes the last node while drafting
    expect(page.locator('#pathDraftStatus')).to_have_text('Punkte gesetzt: 2')
    assert ed.summary()['historySteps'] == steps
    ed.click_doc(900, 500)
    page.keyboard.press('Enter')
    expect(page.locator('#pathDraftBar')).to_be_hidden()
    (path,) = [entry for entry in paths(ed) if entry['id'] != existing['id']]
    summary = ed.summary()
    assert summary['historySteps'] == steps + 1 and summary['selection'] == path['id'] and summary['tool'] == 'path'
    assert (path['x'], path['y']) == pytest.approx((400, 400), abs=1)
    assert [(p['x'], p['y']) for p in path['points']] == pytest.approx([(0, 0), (200, 100), (500, 100)], abs=1)
    assert all(isinstance(v, int) or float(v).is_integer() for p in path['points'] for v in p.values())

    page.keyboard.press('Control+z')
    assert [entry['id'] for entry in paths(ed)] == [existing['id']]
    page.keyboard.press('Control+Shift+z')
    assert item(ed, path['id']) == path

    target = tmp_path / 'nodes.rdmap.json'
    raw = save_file(ed, target)
    saved = next(entry for layer in raw['layers'] if layer['kind'] == 'paths' for entry in layer['items'] if entry['id'] == path['id'])
    assert (saved['x'], saved['y'], saved['points']) == (path['x'], path['y'], path['points'])
    page.locator('#fileInput').set_input_files(str(target))
    expect(page.locator('#toast')).to_contain_text('geladen')
    reopened = item(ed, path['id'])
    assert (reopened['x'], reopened['y'], reopened['points']) == (path['x'], path['y'], path['points'])

    # double-click finishes; its second click adds no duplicate node
    ed.tool('path')
    ed.click_doc(400, 800)
    ed.click_doc(700, 850)
    page.mouse.dblclick(*ed.client(900, 800))
    newest = paths(ed)[-1]
    assert len(paths(ed)) == 3 and len(newest['points']) == 3

    # Esc cancels the draft first, the next Esc leaves the tool
    ed.click_doc(400, 1100)
    ed.click_doc(600, 1150)
    page.keyboard.press('Escape')
    expect(page.locator('#pathDraftBar')).to_be_hidden()
    assert len(paths(ed)) == 3 and ed.summary()['tool'] == 'path'
    page.keyboard.press('Escape')
    assert ed.summary()['tool'] == 'select'
    assert item(ed, existing['id']) == existing  # drawing never touched the older path
    ed.assert_clean()


def test_draft_buttons_and_tool_switch(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('path')
    page.locator('input[name="pathMode"][value="nodes"]').check()
    ed.click_doc(400, 400)
    expect(page.locator('#pathDraftFinish')).to_be_disabled()
    ed.click_doc(700, 400)
    page.locator('#pathDraftUndo').click()
    expect(page.locator('#pathDraftStatus')).to_have_text('Punkte gesetzt: 1')
    ed.click_doc(700, 500)
    page.locator('#pathDraftFinish').click()
    assert len(paths(ed)) == 1
    ed.click_doc(400, 900)
    ed.click_doc(700, 900)
    page.locator('#pathDraftCancel').click()
    expect(page.locator('#pathDraftBar')).to_be_hidden()
    ed.click_doc(400, 1200)
    ed.click_doc(700, 1200)
    page.keyboard.press('v')
    expect(page.locator('#toast')).to_contain_text('Unfertiger Weg verworfen')
    assert len(paths(ed)) == 1 and ed.summary()['tool'] == 'select'
    ed.assert_clean()


def test_freehand_still_draws_and_draw_edit_switch_is_explicit(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('path')
    expect(page.locator('input[name="pathMode"][value="freehand"]')).to_be_checked()
    ed.drag([(500, 600), (700, 640), (900, 600)])
    (path,) = paths(ed)
    assert len(path['points']) > 3  # freehand samples the drag
    page.locator('#pathEditNodes').click()
    summary = ed.summary()
    assert summary['tool'] == 'select' and summary['selection'] == path['id']
    expect(page.locator('#pathNodeMode')).to_be_checked()
    point = path['points'][1]
    node = (path['x'] + point['x'], path['y'] + point['y'])
    ed.drag([node, (node[0] + 30, node[1] + 40)])
    moved = item(ed, path['id'])
    assert moved['points'][1] != point
    assert moved['points'][:1] + moved['points'][2:] == path['points'][:1] + path['points'][2:]
    expect(page.locator('#selPathDraw')).to_be_visible()
    page.locator('#selPathDraw').click()
    assert ed.summary()['tool'] == 'path'
    ed.assert_clean()
