"""FV06 uses real brush strokes, native input, local preferences and modal focus behavior."""
import json
import pytest
from playwright.sync_api import expect
from tests.test_mapmaker_browser import browser,open_editor,preview_origin
from tests.test_review_maps_browser import new_empty,save_file

KEY='rd.mapmaker.recentColors.v1'

def color(page,value):
    page.locator('#brushColorEnabled').check()
    page.locator('#brushColor').fill(value)

def chips(page):return page.locator('#recentColors button').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.color)')
def shape(ed):
    value=ed.summary()
    return {k:value[k] for k in ['items','layers','generation','historySteps']}


def test_committed_color_history_is_bounded_reusable_and_not_project_state(open_editor,tmp_path):
    ed=open_editor(choose_template=False);new_empty(ed);page=ed.page
    ed.tool('brush');ed.set_range('#brushSize',16)
    values=['#110001','#220002','#330003','#440004','#550005','#660006','#770007','#880008','#990009','#aa000a']
    for i,value in enumerate(values):
        color(page,value);ed.click_doc(400+i*40,500)
    assert chips(page)==list(reversed(values[-8:]))
    # A canceled stroke has no effect on reusable colors.
    color(page,'#abcdef');page.mouse.move(*ed.client(500,800));page.mouse.down();page.mouse.move(*ed.client(650,850))
    page.keyboard.press('Escape');page.mouse.up()
    assert '#abcdef' not in chips(page)
    chosen=values[3];page.locator('#recentColors button[data-color="'+chosen+'"]').click()
    expect(page.locator('#brushColor')).to_have_value(chosen);expect(page.locator('#brushColorEnabled')).to_be_checked()
    before=chips(page);ed.click_doc(700,900);assert chips(page)==[chosen]+[v for v in before if v!=chosen]
    page.locator('#mapCanvas').focus();page.keyboard.press('Control+z');assert chips(page)[0]==chosen
    saved=save_file(ed,tmp_path/'color-preference.rdmap.json')
    assert 'recentColors' not in saved and 'recentColors' not in saved.get('meta',{})
    expected=chips(page)
    expect(page.locator('#saveStatus')).to_have_attribute('data-state','saved',timeout=15000)
    page.reload();page.wait_for_selector('#restoreDialog[open]');page.locator('#restoreYes').click();page.wait_for_selector('#app[data-state=ready]')
    assert chips(page)==expected
    ed.assert_clean()


def test_opacity_and_wheel_shortcuts_keep_zoom_typing_and_brush_controls_consistent(open_editor):
    ed=open_editor(choose_template=False);new_empty(ed);page=ed.page
    ed.tool('brush');page.locator('#mapCanvas').focus();page.keyboard.press('3')
    expect(page.locator('#brushOpacity')).to_have_value('30');expect(page.locator('#brushOpacityOut')).to_have_text('30 %')
    page.keyboard.press('0');expect(page.locator('#brushOpacity')).to_have_value('100')
    title=page.locator('#mapTitle');title.fill('QA');title.press('End');page.keyboard.type('3q')
    expect(title).to_have_value('QA3q');expect(page.locator('#brushOpacity')).to_have_value('100');expect(page.locator('#quickPalette')).not_to_be_visible()
    page.mouse.move(*ed.client(700,650));page.locator('#mapCanvas').focus()
    size=int(page.locator('#brushSize').input_value());zoom=ed.summary()['zoom'];steps=ed.summary()['historySteps']
    page.keyboard.down('Shift');page.mouse.wheel(0,-120);page.keyboard.up('Shift')
    expect(page.locator('#brushSize')).not_to_have_value(str(size));assert ed.summary()['zoom']==zoom
    expect(page.locator('#brushSizeNumber')).to_have_value(page.locator('#brushSize').input_value())
    old=page.locator('#materials [aria-checked=true]').get_attribute('data-material')
    page.keyboard.down('Alt');page.mouse.wheel(0,-120);page.keyboard.up('Alt')
    expect(page.locator('#materials [aria-checked=true]')).not_to_have_attribute('data-material',old)
    assert ed.summary()['zoom']==zoom and ed.summary()['historySteps']==steps
    page.keyboard.down('Control');page.mouse.wheel(0,-100);page.keyboard.up('Control')
    page.wait_for_function('z=>rdMapmaker.summary().zoom!==z',arg=zoom)
    ed.assert_clean()


def test_temporary_palette_hover_is_transient_and_button_supports_keyboard(open_editor):
    seed="localStorage.setItem('"+KEY+"',JSON.stringify(['#123456','#abcdef']))"
    ed=open_editor(choose_template=False,init_script=seed);new_empty(ed);page=ed.page
    before=shape(ed);page.mouse.move(*ed.client(1000,700));page.locator('#mapCanvas').focus()
    page.keyboard.down('q');expect(page.locator('#quickPalette')).to_be_visible()
    assert shape(ed)==before
    page.locator('#quickTools button[data-tool=label]').hover();assert shape(ed)==before
    page.keyboard.up('q');expect(page.locator('#quickPalette')).not_to_be_visible();assert ed.summary()['tool']=='label' and shape(ed)==before
    page.locator('#quickPaletteOpen').click();expect(page.locator('#quickPalette')).to_be_visible()
    page.keyboard.press('Tab');assert page.evaluate("!!document.activeElement.closest('#quickPalette')")
    page.keyboard.press('Escape');expect(page.locator('#quickPalette')).not_to_be_visible();expect(page.locator('#quickPaletteOpen')).to_be_focused()
    page.locator('#quickPaletteOpen').click();page.locator('#quickColors button[data-color="#abcdef"]').click()
    expect(page.locator('#brushColor')).to_have_value('#abcdef');assert ed.summary()['tool']=='brush' and shape(ed)==before
    # Native Escape closes only the palette, preserving a node path still being drafted.
    ed.tool('path');page.locator('input[name="pathMode"][value="nodes"]').check()
    ed.click_doc(500,500);ed.click_doc(750,550)
    page.locator('#quickPaletteOpen').click();page.keyboard.press('Escape')
    expect(page.locator('#quickPalette')).not_to_be_visible()
    expect(page.locator('#pathDraftStatus')).to_have_text('Punkte gesetzt: 2')
    page.locator('#pathDraftFinish').click()
    assert len([item for item in ed.summary()['items'] if 'points' in item])==1
    ed.assert_clean()


@pytest.mark.parametrize('blocked',[False,True])
def test_color_storage_validation_and_phone_palette_remain_usable(open_editor,blocked):
    if blocked:
        init="""const get=Storage.prototype.getItem,set=Storage.prototype.setItem;
        Storage.prototype.getItem=function(k){if(k==='rd.mapmaker.recentColors.v1')throw new Error('storage denied');return get.call(this,k)};
        Storage.prototype.setItem=function(k,v){if(k==='rd.mapmaker.recentColors.v1')throw new Error('storage denied');return set.call(this,k,v)};"""
    else:init="localStorage.setItem('"+KEY+"',JSON.stringify(['wrong','#123456','#123456','#ABCDEF']))"
    ed=open_editor(width=390,choose_template=False,init_script=init);new_empty(ed);page=ed.page
    ed.tool('brush');page.locator('#tab-tool').click()
    assert chips(page)==([] if blocked else ['#123456','#abcdef'])
    if blocked:
        color(page,'#112233');page.locator('#tab-tool').click();ed.click_doc(600,500);page.locator('#tab-tool').click()
        assert chips(page)==['#112233']
    page.locator('#quickPaletteOpen').click();expect(page.locator('#quickPalette')).to_be_visible()
    box=page.locator('#quickPalette').bounding_box();assert box['x']>=0 and box['x']+box['width']<=391
    page.locator('#quickTools button[data-tool=path]').click();expect(page.locator('#quickPalette')).not_to_be_visible();assert ed.summary()['tool']=='path'
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    ed.assert_clean()


def test_recent_color_uses_captured_stroke_and_ignores_clipped_noop(open_editor):
    ed=open_editor(choose_template=False);new_empty(ed);page=ed.page;ed.tool('brush')
    color(page,'#123456');page.locator('#brushClip').select_option('land')
    before=ed.region(450,450,100,100);ed.click_doc(500,500)
    assert ed.region(450,450,100,100)==before and chips(page)==[]
    page.locator('#brushClip').select_option('')
    page.mouse.move(*ed.client(500,500));page.mouse.down()
    # The same public control may change while a pointer gesture is captured.
    page.locator('#brushColor').evaluate("n=>{n.value='#abcdef';n.dispatchEvent(new Event('input',{bubbles:true}))}")
    page.mouse.move(*ed.client(650,550));page.mouse.up()
    assert chips(page)==['#123456']
    expect(page.locator('#brushColor')).to_have_value('#abcdef')
    ed.assert_clean()
