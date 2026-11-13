"""Editor gestures must preserve every selected object/cell and survive undo/file IO."""
import json
from pathlib import Path
import pytest
from playwright.sync_api import expect
from tests.test_mapmaker_browser import browser,preview_origin,open_editor,GRASS  # noqa:F401


def blank(open_editor,width=1440):
    ed=open_editor(width=width,choose_template=False);ed.page.locator('#newEmpty').click();return ed


@pytest.mark.parametrize('width',[1440,390])
def test_marquee_group_move_cancel_delete_and_undo(open_editor,width):
    ed=blank(open_editor,width);ed.tool('stamp')
    if width<600:ed.tab('Werkzeug')
    ed.page.locator('.mm-stamp').first.click()
    if width<600:ed.tab('Werkzeug')
    ed.click_doc(400,400);ed.click_doc(700,500);ed.tool('select')
    original=ed.summary()['items'];assert len(original)==2
    ed.drag([(250,250),(850,650)]);assert ed.summary()['selectionCount']==2
    if width<600:ed.tab('Werkzeug')
    expect(ed.page.locator('#groupInspector')).to_be_visible()
    if width<600:ed.tab('Werkzeug')
    history=ed.summary()['historySteps'];ed.drag([(400,400),(500,450)])
    moved=ed.summary()['items'];assert ed.summary()['historySteps']==history+1
    for a,b in zip(original,moved):assert abs(b['x']-a['x']-100)<4 and abs(b['y']-a['y']-50)<4
    # A canceled live group gesture restores both objects and does not create history.
    start=ed.client(moved[0]['x'],moved[0]['y']);ed.page.mouse.move(*start);ed.page.mouse.down();ed.page.mouse.move(start[0]+60,start[1]+20,steps=3)
    ed.page.keyboard.press('Escape');ed.page.mouse.up();assert ed.summary()['items']==moved
    assert ed.summary()['historySteps']==history+1
    ed.drag([(250,250),(1000,800)])
    if width<600:ed.tab('Werkzeug')
    ed.page.locator('#groupScale').fill('150');ed.page.locator('#groupScaleApply').click()
    assert all(abs(b['size']/a['size']-1.5)<.01 for a,b in zip(moved,ed.summary()['items']))
    ed.page.locator('#groupDelete').click();assert ed.summary()['items']==[]
    ed.page.locator('#undoVisible').click();assert len(ed.summary()['items'])==2
    ed.page.locator('#redoVisible').click();assert ed.summary()['items']==[];ed.assert_clean()


def test_tile_group_collision_move_and_undo_preserve_assets(open_editor):
    ed=blank(open_editor);ed.tool('tile');ed.page.locator('#tilePack').select_option('kenney-tiny');ed.page.locator('#tileSearch').fill('Gras');ed.page.locator(f'.mm-tile-btn[data-tile="{GRASS}"]').click()
    for x in (325,357,453):ed.click_doc(x,325)
    def tiles():return next(l for l in ed.summary()['layers'] if l['kind']=='tiles')['tiles']
    original=tiles();assert len(original)==3
    ed.tool('select');ed.drag([(315,315),(385,355)]);assert ed.summary()['selectionCount']==2
    history=ed.summary()['historySteps'];ed.drag([(335,335),(431,335)])
    assert tiles()==original and ed.summary()['historySteps']==history
    expect(ed.page.locator('#toast')).to_contain_text('Zielzellen')
    ed.drag([(335,335),(335,399)]);assert ed.summary()['historySteps']==history+1
    assert {(t['col'],t['row']) for t in tiles()}=={(10,12),(11,12),(14,10)}
    ed.page.locator('#groupDelete').click();assert len(tiles())==1
    ed.page.locator('#undoVisible').click();assert len(tiles())==3
    ed.page.locator('#undoVisible').click();assert tiles()==original
    ed.tool('tile');ed.page.locator('#tileAsSymbol').click();expect(ed.page.locator('#stampSelected')).to_contain_text('Gras');ed.click_doc(1000,400)
    assert any(i.get('asset')==GRASS for i in ed.summary()['items']);assert tiles()==original;ed.assert_clean()


def test_nameless_pin_curve_nodes_and_roundtrip_match_server(open_editor,tmp_path):
    ed=blank(open_editor);ed.tool('label');ed.page.locator('#labelNamed').uncheck();ed.click_doc(500,500)
    item=ed.summary()['items'][0];assert item['text']=='' and item['pin']
    ed.page.locator('#selPin').click();expect(ed.page.locator('#selPin')).to_be_checked()
    ed.tool('path');ed.drag([(1000,400),(1200,650),(1400,400)])
    path=next(i for i in ed.summary()['items'] if 'points' in i);assert path['curve']
    ed.tool('select');ed.page.locator('#pathNodeMode').check();point=path['points'][1];start=(path['x']+point['x'],path['y']+point['y'])
    ed.drag([start,(start[0]+35,start[1]+35)])
    changed=next(i for i in ed.summary()['items'] if 'points' in i);assert changed['points'][1]!=point
    ed.page.locator('#undoVisible').click();assert next(i for i in ed.summary()['items'] if 'points' in i)['points'][1]==point
    # Hit testing uses the same actual curve geometry, not its old straight control polygon.
    assert ed.page.evaluate('''async()=>{const {pathHit}=await import('/mapmaker/js/render.js');const item={x:0,y:0,width:2,curve:true,points:[{x:0,y:0},{x:200,y:200},{x:400,y:0}]};return pathHit(item,{x:175,y:125},1)&&!pathHit({...item,curve:false},{x:175,y:125},1)}''')
    with ed.page.expect_download() as download:ed.menu('Als Datei speichern')
    target=tmp_path/'group.rdmap.json';download.value.save_as(target);saved=json.loads(target.read_text())
    from vtt.mapmaker_document import normalize_document
    normalized,_=normalize_document(saved)
    assert next(l for l in normalized['layers'] if l['kind']=='labels')['items'][0]['text']==''
    assert next(l for l in normalized['layers'] if l['kind']=='paths')['items'][0]['curve'] is True
    ed.page.locator('#fileInput').set_input_files(str(target));expect(ed.page.locator('#toast')).to_contain_text('geladen')
    assert any(i.get('curve') for i in ed.summary()['items']);assert any(i.get('text')=='' and i.get('pin') for i in ed.summary()['items']);ed.assert_clean()
