"""FV04 layer contracts and FV05 grid safety through actual editor input."""

import json

import pytest
from playwright.sync_api import expect

from tests.test_mapmaker_browser import browser, open_editor, preview_origin  # noqa: F401
from tests.test_review_maps_browser import new_empty, save_file


def paths(ed):
    return [layer for layer in ed.summary()['layers'] if layer['kind'] == 'paths']


def add_paths(ed):
    if not ed.page.locator('#addPaths').is_visible():
        ed.page.locator('#tab-layers').click()
    ed.page.locator('#addPaths').click()
    return ed.summary()['activeLayer']


def test_path_respects_selected_lower_layer_and_roundtrips(open_editor, tmp_path):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    lower, upper = add_paths(ed), add_paths(ed)
    ed.tool('path')
    ed.page.locator('#toolLayer').select_option(lower)
    ed.drag([(500, 500), (700, 550), (900, 500)])
    (item,) = ed.summary()['items']
    assert item['layer'] == lower
    assert len(paths(ed)) == 2
    assert next(layer for layer in paths(ed) if layer['id'] == upper)['items'] == 0
    saved = save_file(ed, tmp_path / 'lower-path.rdmap.json')
    assert next(layer for layer in saved['layers'] if layer['id'] == lower)['items'][0]['id'] == item['id']
    ed.assert_clean()


def test_occupied_grid_cannot_silently_move_tiles(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    ed.tool('tile')
    ed.page.locator('#tileSize').select_option('32')
    ed.click_doc(640, 640)
    (before,) = [layer for layer in ed.summary()['layers'] if layer['kind'] == 'tiles']
    assert before['tiles']
    ed.page.locator('#tileSize').select_option('64')
    (after,) = [layer for layer in ed.summary()['layers'] if layer['kind'] == 'tiles']
    assert after['grid'] == before['grid']
    assert after['tiles'] == before['tiles']
    expect(ed.page.locator('#tileSize')).to_have_value('32')
    ed.page.locator('#tileNewLayer').click()
    layers = [layer for layer in ed.summary()['layers'] if layer['kind'] == 'tiles']
    assert len(layers) == 2
    assert next(layer for layer in layers if layer['id'] == before['id']) == before
    new = next(layer for layer in layers if layer['id'] != before['id'])
    assert new['grid'] == 64 and not new['tiles']
    ed.page.locator('#mapCanvas').focus()
    ed.page.keyboard.press('Control+z')
    assert [layer for layer in ed.summary()['layers'] if layer['kind'] == 'tiles'] == [before]
    ed.assert_clean()


def test_hidden_path_layer_refuses_drawing_without_duplicate(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    hidden = add_paths(ed)
    ed.page.locator(f'#layerList [data-layer="{hidden}"] .mm-eye').click()
    ed.tool('path')
    before = ed.summary()
    ed.drag([(500, 500), (700, 600), (900, 500)])
    after = ed.summary()
    assert after['layers'] == before['layers'] and after['items'] == before['items']
    assert after['historySteps'] == before['historySteps']
    expect(ed.page.locator('#toast')).to_contain_text('ausgeblendet')
    ed.assert_clean()


def test_first_path_is_one_undo_and_keeps_raster_pixels(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    ed.tool('brush')
    ed.click_doc(500, 500)
    pixels, steps = ed.region(470, 470, 60, 60), ed.summary()['historySteps']
    raster = [layer for layer in ed.summary()['layers'] if layer['kind'] == 'raster']
    ed.tool('path')
    ed.drag([(700, 700), (850, 750), (1000, 700)])
    assert len(paths(ed)) == 1 and ed.summary()['historySteps'] == steps + 1
    ed.page.keyboard.press('Control+z')
    assert not paths(ed)
    assert [layer for layer in ed.summary()['layers'] if layer['kind'] == 'raster'] == raster
    assert ed.region(470, 470, 60, 60) == pixels
    ed.assert_clean()


def test_path_keeps_gesture_target_when_keyboard_changes_active_layer(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    lower, _ = add_paths(ed), add_paths(ed)
    ed.tool('path')
    ed.page.locator('#toolLayer').select_option(lower)
    mouse = ed.page.mouse
    mouse.move(*ed.client(500, 500))
    mouse.down()
    mouse.move(*ed.client(700, 550), steps=6)
    ed.page.keyboard.press('Alt+ArrowUp')
    assert ed.summary()['activeLayer'] != lower
    mouse.move(*ed.client(900, 500), steps=6)
    mouse.up()
    assert ed.summary()['items'][0]['layer'] == lower
    ed.page.locator('#tab-layers').click()
    ed.page.locator('#layerSort').select_option('recent')
    expect(ed.page.locator('#layerList .mm-layer').first).to_have_attribute('data-layer', lower)
    ed.assert_clean()


@pytest.mark.parametrize('width,language', [(1440, 'de'), (390, 'en')])
def test_compact_layers_keyboard_visibility_and_narrow_disclosure(open_editor, width, language):
    prefs = json.dumps({'schema': 1, 'language': language, 'theme': 'night'})
    ed = open_editor(width=width, choose_template=False,
                     init_script=f"localStorage.setItem('vtt.display.v1', {json.dumps(prefs)})")
    # Use IDs so the exact same journey covers both languages.
    ed.page.locator('#newEmpty').click()
    before = ed.summary()['historySteps']
    page = ed.page
    if width == 390:
        expect(page.locator('#stageLayerPanel')).not_to_be_visible()
        page.locator('#activeLayerJump').click()
        expect(page.locator('#stageLayerPanel')).to_be_visible()
    radio = page.locator('#stageLayerList input:checked')
    old = radio.input_value()
    radio.focus()
    radio.press('ArrowRight')
    assert ed.summary()['activeLayer'] != old
    expect(page.locator('#stageLayerList input:checked')).to_be_focused()
    expect(page.locator('#stageLayerList input:checked')).to_be_in_viewport()
    assert ed.summary()['historySteps'] == before
    current = ed.summary()['activeLayer']
    page.locator(f'#stageLayerList [data-layer="{current}"] button').click()
    assert not next(layer for layer in ed.summary()['layers'] if layer['id'] == current)['visible']
    assert ed.summary()['historySteps'] == before + 1
    if width == 390:
        page.locator('#stageLayerList input:checked').press('Escape')
        expect(page.locator('#stageLayerPanel')).not_to_be_visible()
        expect(page.locator('#activeLayerJump')).to_be_focused()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    ed.assert_clean()


def test_layer_filters_recent_use_and_reorder_use_actual_stack(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    lower, upper = add_paths(ed), add_paths(ed)
    page = ed.page
    page.locator('#layerFilterKind').select_option('paths')
    expect(page.locator('#layerList .mm-layer')).to_have_count(2)
    before = [layer['id'] for layer in ed.summary()['layers']]
    top = page.locator(f'#layerList [data-layer="{upper}"] [data-layer-control="up"]')
    expect(top).to_be_enabled()  # other kinds still exist above the filtered rows
    top.click()
    after = [layer['id'] for layer in ed.summary()['layers']]
    assert after.index(upper) == before.index(upper) + 1
    page.locator(f'#layerList [data-layer="{lower}"] .mm-layer-name').click()
    page.locator('#layerSort').select_option('recent')
    expect(page.locator('#layerList .mm-layer').first).to_have_attribute('data-layer', lower)
    page.locator(f'#layerList [data-layer="{upper}"] .mm-eye').click()
    assert ed.summary()['activeLayer'] == lower
    expect(page.locator('#layerList .mm-layer').first).to_have_attribute('data-layer', upper)
    page.locator('#layerFilterName').fill('does not exist')
    expect(page.locator('#layerList .mm-layer')).to_have_count(0)
    assert ed.summary()['activeLayer'] == lower
    page.locator('#layerFilterName').fill('')
    expect(page.locator('#layerList .mm-layer')).to_have_count(2)
    ed.assert_clean()


def test_reference_grid_changes_only_view_and_not_snapping(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    ed.tool('select')
    page = ed.page
    before = ed.summary()
    canvas = page.locator('#mapCanvas')
    image = canvas.evaluate('canvas => canvas.toDataURL()')
    page.locator('#referenceGrid').check()
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    assert canvas.evaluate('canvas => canvas.toDataURL()') != image
    after = ed.summary()
    assert after['layers'] == before['layers'] and after['historySteps'] == before['historySteps']
    assert after['generation'] == before['generation']
    expect(page.locator('#stampGridOn')).not_to_be_checked()
    ed.assert_clean()


def test_layer_search_and_content_filters_inspect_actual_objects_and_raster(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    lower, upper = add_paths(ed), add_paths(ed)
    page = ed.page
    ed.tool('path')
    page.locator('#toolLayer').select_option(lower)
    ed.drag([(500, 500), (700, 550), (900, 500)])
    page.locator('#selPathName').fill('High Road')
    page.locator('#selPathName').press('Tab')
    page.locator('#tab-layers').click()
    page.locator('#layerFilterName').fill('High Road')
    expect(page.locator('#layerList .mm-layer')).to_have_count(1)
    expect(page.locator('#layerList .mm-layer')).to_have_attribute('data-layer', lower)
    page.locator('#layerFilterName').fill('')
    page.locator('#layerFilterKind').select_option('paths')
    page.locator('#layerFilterContent').select_option('empty')
    expect(page.locator('#layerList .mm-layer')).to_have_attribute('data-layer', upper)
    page.locator('#layerFilterContent').select_option('filled')
    expect(page.locator('#layerList .mm-layer')).to_have_attribute('data-layer', lower)
    page.locator('#layerFilterKind').select_option('raster')
    expect(page.locator('#layerList .mm-layer')).to_have_count(0)
    page.locator('#layerFilterContent').select_option('empty')
    raster_count = len([layer for layer in ed.summary()['layers'] if layer['kind'] == 'raster'])
    expect(page.locator('#layerList .mm-layer')).to_have_count(raster_count)
    ed.tool('brush')
    ed.click_doc(600, 700)
    page.locator('#tab-layers').click()
    expect(page.locator('#layerList .mm-layer')).to_have_count(raster_count - 1)
    page.locator('#layerFilterContent').select_option('filled')
    expect(page.locator('#layerList .mm-layer')).to_have_count(1)
    ed.assert_clean()


def test_palette_disclosure_and_label_controls_stay_stable(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('stamp')
    advanced = page.locator('#stampAdvanced')
    expect(advanced).not_to_have_attribute('open', '')
    assert page.evaluate("document.getElementById('palette').compareDocumentPosition(document.getElementById('stampAdvanced')) & Node.DOCUMENT_POSITION_FOLLOWING")
    advanced.locator('summary').click()
    page.locator('#stampScatter').check()
    advanced.locator('summary').click()
    expect(advanced.locator('summary')).to_contain_text('Streuen')
    advanced.locator('summary').click()
    ed.click_doc(600, 600)
    expect(advanced).to_have_attribute('open', '')
    ed.tool('label')
    panel = page.locator('#pane-tool')
    panel.evaluate('node => { node.scrollTop = 0; }')
    position = page.locator('#editPlacedLabel').bounding_box()['y']
    ed.click_doc(900, 700)
    assert abs(page.locator('#editPlacedLabel').bounding_box()['y'] - position) <= 1
    expect(page.locator('#editPlacedLabel')).to_be_enabled()
    expect(page.locator('#mapCanvas')).to_be_focused()
    page.locator('#editPlacedLabel').click()
    expect(page.locator('#selText')).to_be_focused()
    page.locator('#selText').fill('Label after placement')
    page.locator('#selText').press('Tab')
    assert any(item.get('text') == 'Label after placement' for item in ed.summary()['items'])
    ed.assert_clean()


def test_tile_as_symbol_still_places_the_chosen_asset_and_menu_escape_is_local(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('tile')
    page.locator('#tileAsSymbol').click()
    chosen = ed.summary()['stampAsset']
    assert chosen and ed.summary()['tool'] == 'stamp'
    page.mouse.move(*ed.client(500, 600))
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    preview = page.locator('#mapCanvas').evaluate('canvas => canvas.toDataURL()')
    page.mouse.move(*ed.client(700, 600))
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    assert page.locator('#mapCanvas').evaluate('canvas => canvas.toDataURL()') != preview
    ed.click_doc(700, 600)
    assert ed.summary()['items'][0]['asset'] == chosen
    page.locator('#fileMenuBtn').click()
    page.locator('#fileMenuList button').first.press('Escape')
    expect(page.locator('#fileMenuList')).not_to_be_visible()
    assert ed.summary()['tool'] == 'stamp'
    expect(page.locator('#fileMenuBtn')).to_be_focused()
    ed.assert_clean()
