"""C27-S1 browser journeys in the real Kartenwerkstatt (headless Chromium, production CSP).

E03 layout-aware bracket keys, E22 per-asset session tool size, E26 declared-trait
filters, E11 node editing from the inspector, N02 image-brush colour state, N17 recent
place symbols and N16a staged Escape.

Keyboard coverage: real keypresses use Playwright's default US layout. The DE cases
(Windows AltGr as Ctrl+Alt, macOS Option as Alt, Linux AltGraph state) are synthetic
KeyboardEvents shaped after the UI Events/MDN modifier tables; they do not prove what
a physical DE keyboard reports, which needs the live keydown log.
"""
import json

import pytest
from playwright.sync_api import expect

from tests.test_mapmaker_browser import STATIC, browser, open_editor, preview_origin  # noqa: F401
from tests.test_review_maps_browser import make_pixel_asset, new_empty, save_file

CARTOGRAPHY = json.loads((STATIC / 'mapmaker/assets/kenney-cartography/manifest.json').read_text())
DEFAULT_SIZE = {stamp['id']: stamp['defaultSize'] for stamp in CARTOGRAPHY['stamps']}
CASTLE, FOREST = 'kenney:castle', 'kenney:forest'
FILTERS = ('#stampSearch', '#stampPack', '#stampCategory', '#stampStyle', '#stampPerspective')

SYNTHETIC_KEYDOWN = """(init) => {
    const canvas = document.getElementById('mapCanvas');
    canvas.focus();
    const event = new KeyboardEvent('keydown', {bubbles: true, cancelable: true, ...init});
    canvas.dispatchEvent(event);
    return {prevented: event.defaultPrevented, altGraph: event.getModifierState('AltGraph')};
}"""


def number(page, selector):
    return int(page.locator(selector).input_value())


def result_count(page):
    return int(page.locator('#stampResults').inner_text().split(' ')[0].replace('.', ''))


def focus_canvas(page):
    page.locator('#mapCanvas').focus()


def synthetic_key(page, **init):
    return page.evaluate(SYNTHETIC_KEYDOWN, init)


def show_tool_pane(ed):
    """The phone layout keeps the tool pane in a closable sheet."""
    page = ed.page
    if page.locator('#app').get_attribute('data-sheet') != 'open' or page.locator('#pane-tool').is_hidden():
        ed.tab('Werkzeug')


def choose_stamp(page, pack, asset=None):
    """Choose a stamp with the visible pack filter and palette; a sheet is taken whole."""
    page.locator('#stampPack').select_option(pack)
    button = page.locator(f'.mm-stamp[data-asset="{asset}"]') if asset else page.locator('.mm-stamp:not([disabled])').first
    asset = button.get_attribute('data-asset')
    button.click()
    expect(page.locator(f'.mm-stamp[data-asset="{asset}"]')).to_have_attribute('aria-checked', 'true')
    if page.locator('#sheetDialog').is_visible():
        page.locator('#sheetWhole').click()
    return asset


def item(ed, item_id):
    return next(entry for entry in ed.summary()['items'] if entry['id'] == item_id)


# ---- E03 ----------------------------------------------------------------------

def test_bracket_keys_us_layout_change_size_and_softness(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('stamp')
    focus_canvas(page)
    size = number(page, '#stampSize')
    page.keyboard.press('BracketRight')
    bigger = number(page, '#stampSize')
    assert bigger > size
    page.keyboard.press('BracketLeft')
    assert number(page, '#stampSize') < bigger
    ed.click_doc(600, 600)
    (placed,) = ed.summary()['items']
    assert placed['size'] == number(page, '#stampSize')  # the nudged value is what gets placed

    ed.tool('brush')
    focus_canvas(page)
    size, softness = number(page, '#brushSize'), number(page, '#brushSoftness')
    page.keyboard.press('BracketRight')
    bigger = number(page, '#brushSize')
    assert bigger > size and number(page, '#brushSoftness') == softness
    page.keyboard.press('BracketLeft')
    assert number(page, '#brushSize') < bigger and number(page, '#brushSoftness') == softness
    size = number(page, '#brushSize')
    page.keyboard.press('Shift+BracketLeft')  # US layout produces "{"
    assert number(page, '#brushSoftness') == softness - 10 and number(page, '#brushSize') == size
    page.keyboard.press('Shift+BracketRight')  # "}"
    assert number(page, '#brushSoftness') == softness and number(page, '#brushSize') == size
    ed.assert_clean()


def test_bracket_keys_synthetic_altgr_and_option_events(open_editor):
    """Synthetic events only (see module docstring); no physical DE keyboard is claimed."""
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('brush')
    size, softness = number(page, '#brushSize'), number(page, '#brushSoftness')
    # Windows DE: AltGr+8 = "[" arrives as Ctrl+Alt.
    assert synthetic_key(page, key='[', code='Digit8', ctrlKey=True, altKey=True)['prevented']
    assert number(page, '#brushSize') < size
    size = number(page, '#brushSize')
    # Windows DE: AltGr+0 = "}" reaches softness without Shift.
    assert synthetic_key(page, key='}', code='Digit0', ctrlKey=True, altKey=True)['prevented']
    assert number(page, '#brushSoftness') == softness + 10 and number(page, '#brushSize') == size
    # macOS DE: Option+5 = "[" arrives as Alt.
    assert synthetic_key(page, key='[', code='Digit5', altKey=True)['prevented']
    assert number(page, '#brushSize') < size
    size = number(page, '#brushSize')
    # Linux DE: AltGr+9 = "]" as the AltGraph modifier state.
    event = synthetic_key(page, key=']', code='Digit9', modifierAltGraph=True)
    assert event['altGraph'], 'Chromium ignored modifierAltGraph in the KeyboardEvent init'
    assert event['prevented'] and number(page, '#brushSize') > size
    # Ctrl-only and Cmd brackets stay with the browser: unchanged and not prevented.
    size, softness = number(page, '#brushSize'), number(page, '#brushSoftness')
    for init in ({'key': '[', 'code': 'BracketLeft', 'ctrlKey': True}, {'key': ']', 'code': 'BracketRight', 'metaKey': True},
                 {'key': '}', 'code': 'Digit0', 'metaKey': True, 'altKey': True}):
        assert not synthetic_key(page, **init)['prevented'], init
        assert (number(page, '#brushSize'), number(page, '#brushSoftness')) == (size, softness), init
    ed.tool('stamp')
    stamp = number(page, '#stampSize')
    assert synthetic_key(page, key=']', code='Digit9', ctrlKey=True, altKey=True)['prevented']
    assert number(page, '#stampSize') > stamp
    ed.assert_clean()


def test_bracket_keys_ignored_while_typing_and_other_shortcuts_unchanged(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('stamp')
    stamp, softness = number(page, '#stampSize'), number(page, '#brushSoftness')
    page.locator('#stampSearch').focus()
    page.keyboard.type('[{')
    expect(page.locator('#stampSearch')).to_have_value('[{')
    page.keyboard.press('BracketRight')
    expect(page.locator('#stampSearch')).to_have_value('[{]')
    assert number(page, '#stampSize') == stamp and number(page, '#brushSoftness') == softness
    page.locator('#stampSearch').fill('')
    # Undo, layer switching and the plain wheel keep working next to the bracket keys.
    ed.click_doc(600, 600)
    assert ed.summary()['stamps'] == 1
    page.keyboard.press('Control+z')
    assert ed.summary()['stamps'] == 0
    ed.tool('brush')
    page.locator('#toolLayer').select_option('land')
    focus_canvas(page)
    page.keyboard.press('Alt+ArrowUp')
    assert ed.summary()['activeLayer'] == 'terrain'
    zoom = ed.summary()['zoom']
    page.mouse.move(*ed.client(1200, 800))
    page.mouse.wheel(0, -240)
    page.wait_for_function(f'() => window.rdMapmaker.summary().zoom !== {zoom}')
    ed.assert_clean()


# ---- E22 ----------------------------------------------------------------------

def test_stamp_size_is_kept_per_asset_and_crop_for_the_session(open_editor):
    assert DEFAULT_SIZE[CASTLE] != 16 and DEFAULT_SIZE[FOREST] not in (16, DEFAULT_SIZE[CASTLE])
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('stamp')
    choose_stamp(page, 'kenney-cartography', CASTLE)
    assert number(page, '#stampSize') == DEFAULT_SIZE[CASTLE]
    steps = ed.summary()['historySteps']
    page.locator('#stampSizeNumber').fill('16')
    page.locator('#stampSizeNumber').press('Tab')
    expect(page.locator('#stampSize')).to_have_value('16')
    choose_stamp(page, 'kenney-cartography', FOREST)
    assert number(page, '#stampSize') == DEFAULT_SIZE[FOREST]
    choose_stamp(page, 'kenney-cartography', CASTLE)
    assert number(page, '#stampSize') == 16
    ed.click_doc(600, 600)
    assert [entry['size'] for entry in ed.summary()['items'] if entry.get('asset') == CASTLE] == [16]
    assert ed.summary()['historySteps'] == steps + 1  # size choices are not document edits
    focus_canvas(page)
    page.keyboard.press('BracketRight')
    assert number(page, '#stampSize') == 18
    choose_stamp(page, 'kenney-cartography', FOREST)
    assert number(page, '#stampSize') == DEFAULT_SIZE[FOREST]
    choose_stamp(page, 'kenney-cartography', CASTLE)
    assert number(page, '#stampSize') == 18

    def use_crop():
        for key, value in (('X', 0), ('Y', 0), ('W', 64), ('H', 64)):
            page.locator(f'#sheet{key}').fill(str(value))
        page.locator('#sheetUse').click()
        expect(page.locator('#sheetDialog')).to_be_hidden()

    # A crop has its own natural size, so it is remembered separately from the whole image.
    page.locator('#stampCrop').click()
    use_crop()
    assert number(page, '#stampSize') == 64
    ed.set_range('#stampSize', 40)
    page.locator('#stampCrop').click()
    page.locator('#sheetWhole').click()
    assert number(page, '#stampSize') == 18
    page.locator('#stampCrop').click()
    use_crop()
    assert number(page, '#stampSize') == 40
    assert ed.summary()['historySteps'] == steps + 1

    page.wait_for_function('() => window.rdMapmaker.summary().autosave === "saved"')
    page.reload()
    expect(page.locator('#restoreDialog')).to_be_visible(timeout=30000)
    page.locator('#restoreYes').click()
    page.wait_for_selector('#app[data-state=ready]')
    ed.tool('stamp')
    choose_stamp(page, 'kenney-cartography', CASTLE)
    assert number(page, '#stampSize') == DEFAULT_SIZE[CASTLE]  # nothing was persisted
    assert [entry['size'] for entry in ed.summary()['items'] if entry.get('asset') == CASTLE] == [16]
    ed.assert_clean()


# ---- E26 ----------------------------------------------------------------------

def test_trait_filters_count_undeclared_symbols_and_reset(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('stamp')
    results, reset = page.locator('#stampResults'), page.locator('#stampFilterReset')
    expect(page.locator('#stampTraitHint')).to_be_visible()
    assert page.locator('#stampStyle').get_attribute('title') is None  # visible hint instead of a tooltip
    expect(reset).to_be_hidden()
    full = result_count(page)

    # No catalogue pack declares "painted": nothing matches, and the hidden ones are counted.
    page.locator('#stampStyle').select_option('painted')
    expect(page.locator('.mm-stamp')).to_have_count(0)
    expect(results).to_contain_text('Stil-/Perspektivangabe')
    expect(results).to_contain_text('Ohne Angabe')
    expect(reset).to_be_visible()
    page.locator('#stampStyle').select_option('unknown')
    assert page.locator('.mm-stamp').count() > 0
    page.locator('#stampStyle').select_option('pixel')  # declared via the catalogue pixelArt flag
    assert page.locator('.mm-stamp').count() > 0
    expect(results).to_contain_text('weitere ohne Stil-/Perspektivangabe ausgeblendet')

    page.locator('#stampStyle').select_option('')
    page.locator('#stampPack').select_option('kenney-cartography')
    total = result_count(page)
    page.locator('#stampStyle').select_option('pixel')
    expect(page.locator('.mm-stamp')).to_have_count(0)
    expect(results).to_contain_text(f'{total} passende Symbole haben keine Stil-/Perspektivangabe')
    page.locator('#stampStyle').select_option('')
    page.locator('#stampPerspective').select_option('top')  # no catalogue pack states a perspective
    expect(page.locator('.mm-stamp')).to_have_count(0)
    expect(results).to_contain_text(f'{total} passende Symbole')
    page.locator('#stampPerspective').select_option('unknown')
    expect(page.locator('.mm-stamp')).to_have_count(total)
    page.locator('#stampPerspective').select_option('')

    # Own images always declare both traits.
    make_pixel_asset(page, 'Turm', '#aa2211')
    (own,) = ed.summary()['assets']
    assert (own['style'], own['perspective']) == ('pixel', 'top')
    page.locator('#stampPack').select_option('custom')
    page.locator('#stampStyle').select_option('pixel')
    page.locator('#stampPerspective').select_option('top')
    expect(page.locator(f'.mm-stamp[data-asset="{own["id"]}"]')).to_have_count(1)
    page.locator('#stampStyle').select_option('unknown')
    expect(page.locator('.mm-stamp')).to_have_count(0)
    expect(results).to_contain_text('Keine Symbole gefunden')

    page.locator('#stampSearch').fill('Turm')
    reset.click()
    for selector in FILTERS:
        expect(page.locator(selector)).to_have_value('')
    expect(reset).to_be_hidden()
    expect(page.locator('#stampPack')).to_be_focused()
    assert result_count(page) == full + 1
    ed.assert_clean()


# ---- E11 ----------------------------------------------------------------------

def test_node_mode_checkbox_switches_to_select_and_moves_one_node(open_editor, tmp_path):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('path')
    ed.drag([(500, 600), (700, 640), (900, 600)])
    (path,) = [entry for entry in ed.summary()['items'] if 'points' in entry]
    summary = ed.summary()
    assert summary['tool'] == 'path' and summary['selection'] == path['id']
    expect(page.locator('#pathEditHint')).to_contain_text('Wege-Werkzeug')
    page.locator('#pathNodeMode').check()
    summary = ed.summary()
    assert summary['tool'] == 'select' and summary['selection'] == path['id']
    expect(page.locator('.mm-tool[data-tool=select]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#toast')).to_contain_text('Wegpunkte ziehen')
    expect(page.locator('#pathNodeMode')).to_be_checked()

    point = path['points'][1]
    node = (path['x'] + point['x'], path['y'] + point['y'])
    page.mouse.move(*ed.client(*node))
    expect(page.locator('#mapCanvas')).to_have_attribute('data-cursor', 'node')
    page.mouse.move(*ed.client(node[0], node[1] + 200))
    expect(page.locator('#mapCanvas')).to_have_attribute('data-cursor', 'select')

    steps = ed.summary()['historySteps']
    ed.drag([node, (node[0] + 30, node[1] + 40)])  # plain drag, no Shift
    moved = item(ed, path['id'])
    assert len([entry for entry in ed.summary()['items'] if 'points' in entry]) == 1
    assert (moved['x'], moved['y']) == (path['x'], path['y'])
    assert moved['points'][1] != point
    assert moved['points'][:1] + moved['points'][2:] == path['points'][:1] + path['points'][2:]
    assert ed.summary()['historySteps'] == steps + 1
    page.keyboard.press('Control+z')
    assert item(ed, path['id'])['points'] == path['points']
    page.keyboard.press('Control+Shift+z')
    assert item(ed, path['id'])['points'] == moved['points']

    target = tmp_path / 'nodes.rdmap.json'
    raw = save_file(ed, target)
    (saved,) = [entry for layer in raw['layers'] if layer['kind'] == 'paths' for entry in layer['items']]
    assert saved['points'] == moved['points']
    page.locator('#fileInput').set_input_files(str(target))
    expect(page.locator('#toast')).to_contain_text('geladen')
    (reopened,) = [entry for entry in ed.summary()['items'] if 'points' in entry]
    assert reopened['points'] == moved['points']
    ed.assert_clean()


# ---- N02 ----------------------------------------------------------------------

def test_image_brush_explains_original_colours_and_material_restores_colour(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('brush')
    expect(page.locator('.mm-swatch[aria-checked=true]')).to_have_count(1)
    ed.tool('stamp')
    choose_stamp(page, 'kenney-cartography', CASTLE)
    page.locator('#stampAsBrush').click()
    expect(page.locator('#brushShape')).to_have_value('image')
    for selector in ('#brushColorEnabled', '#brushColor', '#brushTexture'):
        expect(page.locator(selector)).to_be_disabled()
        expect(page.locator(selector)).to_have_attribute('aria-describedby', 'brushImageInfo')
    info = page.locator('#brushImageInfo')
    expect(info).to_be_visible()
    expect(info).to_contain_text('Originalfarben bleiben erhalten')
    expect(info).to_contain_text('Ein Material wählen')
    expect(page.locator('.mm-swatch[aria-checked=true]')).to_have_count(0)
    expect(page.locator('.mm-swatch[tabindex="0"]')).to_have_count(1)
    expect(page.locator('.mm-swatch').first).to_have_attribute('tabindex', '0')

    before = ed.region(480, 480, 150, 100)
    ed.drag([(500, 500), (600, 520)])
    assert ed.region(480, 480, 150, 100) != before
    page.keyboard.press('Control+z')
    assert ed.region(480, 480, 150, 100) == before

    page.locator('.mm-swatch[data-material=forest]').click()
    expect(page.locator('#brushShape')).to_have_value('round')
    expect(page.locator('#brushColor')).to_be_enabled()
    expect(page.locator('.mm-swatch[data-material=forest]')).to_have_attribute('aria-checked', 'true')
    expect(info).to_be_hidden()
    ed.assert_clean()


# ---- N17 ----------------------------------------------------------------------

@pytest.mark.parametrize('width', [1440, 390])
def test_place_symbol_picker_offers_recent_symbols_first(open_editor, width):
    ed = open_editor(width=width, choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('stamp')
    show_tool_pane(ed)
    castle = choose_stamp(page, 'kenney-cartography', CASTLE)
    other = choose_stamp(page, 'kenney-rpg')
    assert other != castle
    ed.tool('label')
    show_tool_pane(ed)
    recent = [option.get_attribute('value') for option in
              page.locator('#placeSymbol optgroup[label="Zuletzt gewählte Symbole"] option').all()]
    current = [option.get_attribute('value') for option in
               page.locator('#placeSymbol optgroup[label="Aktuelle Symbolpalette"] option').all()]
    assert recent[:2] == [other, castle]
    assert current and not set(recent) & set(current)
    expect(page.locator('#placeSymbol option').first).to_have_attribute('value', '')
    expect(page.locator('#placeSymbolHint')).to_be_visible()
    box = page.locator('#placeSymbol').bounding_box()
    assert box['x'] >= 0 and box['x'] + box['width'] <= width + 1
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    if width > 600:
        page.locator('#placeSymbol').select_option(other)
        ed.click_doc(900, 700)
        (label,) = [entry for entry in ed.summary()['items'] if 'text' in entry]
        assert label['symbol']['asset'] == other
    ed.assert_clean()


# ---- N16a ---------------------------------------------------------------------

def test_escape_cancels_first_then_leaves_the_placement_tool(open_editor):
    ed = open_editor(choose_template=False)
    new_empty(ed)
    page = ed.page
    ed.tool('stamp')
    ed.click_doc(500, 500)
    ed.click_doc(700, 500)
    summary = ed.summary()
    assert summary['stamps'] == 2 and summary['tool'] == 'stamp'  # repeated placement stays in the tool
    steps = summary['historySteps']

    # During a gesture Escape only cancels it.
    page.mouse.move(*ed.client(900, 500))
    page.mouse.down()
    page.keyboard.press('Escape')
    page.mouse.up()
    summary = ed.summary()
    assert (summary['stamps'], summary['tool'], summary['historySteps'], summary['mutating']) == (2, 'stamp', steps, False)
    page.keyboard.press('Escape')
    assert ed.summary()['tool'] == 'select'
    expect(page.locator('.mm-tool[data-tool=select]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#toast')).to_contain_text('Platzieren beendet')

    # With a selection the first Escape deselects, the second leaves the tool.
    ed.tool('label')
    ed.click_doc(900, 800)
    assert ed.summary()['selection']
    expect(page.locator('#selText')).to_be_focused()
    focus_canvas(page)
    page.keyboard.press('Escape')
    summary = ed.summary()
    assert summary['tool'] == 'label' and summary['selection'] is None
    page.keyboard.press('Escape')
    assert ed.summary()['tool'] == 'select'

    # Painting tools keep Escape as before.
    ed.tool('brush')
    focus_canvas(page)
    page.keyboard.press('Escape')
    assert ed.summary()['tool'] == 'brush'
    ed.assert_clean()
