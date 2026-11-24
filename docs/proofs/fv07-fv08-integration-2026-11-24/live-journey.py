"""FV07/FV08 normal Maps acceptance with isolated DM/Player accounts; local map files only."""
import hashlib
import json
import os
from pathlib import Path

from playwright.sync_api import expect,sync_playwright
from tests.test_mapmaker_browser import Editor
from tests.test_c27_mapmaker_browser import CASTLE,choose_stamp
from tests.test_fv07_fv08_mapmaker_browser import GRASS

root=Path(os.environ['PROOF_ROOT'])
fixture=json.loads((root/'private-live-credentials.json').read_text())
origin='https://vtt.roll-drauf.de'
proof={'status':'running','origin':origin,'journeys':[],'real_oauth_tested':False,'remote_projects_created':False}
expect.set_options(timeout=30000)

def save(): (root/'live.json').write_text(json.dumps(proof,indent=2)+'\n')
def tool(ed,name):
    ed.tool(name)
    if not ed.page.locator('#pane-tool').is_visible():ed.page.locator('#tab-tool').click()
def path_items(ed):return [x for x in ed.summary()['items'] if 'points' in x]

with sync_playwright() as p:
    for engine,role,width,language,theme in [('chromium','dm',1440,'de','night'),('firefox','player',390,'en','paper')]:
        browser=getattr(p,engine).launch(headless=True,**({'args':['--no-sandbox']} if engine=='chromium' else {}))
        context=browser.new_context(viewport={'width':width,'height':1000},accept_downloads=True,reduced_motion='reduce')
        prefs={'language':language,'theme':theme,'accent':'teal'}
        context.add_init_script("localStorage.setItem('vtt.display.v1',"+json.dumps(json.dumps(prefs))+")")
        auth=fixture['users'][role]
        context.add_cookies([{'name':'access_token_cookie','value':auth['token'],'url':origin,'httpOnly':True,'secure':True},
                            {'name':'csrf_access_token','value':auth['csrf'],'url':origin,'secure':True}])
        page=context.new_page();page.set_default_timeout(30000);errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(origin+'/dashboard')
            page.locator('.book-dashboard-ribbon:visible a[href="/mapmaker"]').click()
            page.wait_for_selector('#app[data-state=ready]');page.locator('#newEmpty').click()
            ed=Editor(context,page,errors)
            tool(ed,'path');page.locator('input[name="pathMode"][value="nodes"]').check()
            ed.click_doc(400,400)
            expect(page.locator('#undoVisible')).to_be_enabled()
            page.locator('#undoVisible').click()
            expect(page.locator('#pathDraftBar')).to_be_hidden()
            assert not path_items(ed)
            steps=ed.summary()['historySteps']
            for point in [(400,400),(650,500),(900,420)]:ed.click_doc(*point)
            page.keyboard.press('Backspace');ed.click_doc(900,500);page.keyboard.press('Enter')
            (path,)=path_items(ed);assert len(path['points'])==3 and ed.summary()['historySteps']==steps+1
            page.locator('#mapCanvas').focus();page.keyboard.press('Control+z');assert not path_items(ed)
            page.keyboard.press('Control+Shift+z');assert path_items(ed)==[path]
            page.locator('#selPathName').fill('QA Route');page.locator('#selPathName').press('Enter')
            path=path_items(ed)[0]
            page.locator('#pathEditNodes').click()
            assert ed.summary()['tool']=='select';expect(page.locator('#pathNodeMode')).to_be_checked()
            page.locator('#selPathDraw').click();assert ed.summary()['tool']=='path'
            # Label preview is transient; neither an ID nor a history step is allocated by hovering.
            tool(ed,'label');before=ed.summary();page.mouse.move(*ed.client(1400,600))
            page.evaluate('() => new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(done)))')
            after=ed.summary();assert before['items']==after['items'] and before['historySteps']==after['historySteps'] and before['generation']==after['generation']
            ed.click_doc(1400,600)
            page.locator('#selText').fill('QA Place');page.locator('#selText').press('Enter')
            page.locator('#inspectLabel .mm-rot-presets button[data-rot="45"]').click()
            label=next(x for x in ed.summary()['items'] if 'text' in x);assert label['rot']==45
            tool(ed,'stamp');choose_stamp(page,'kenney-cartography',CASTLE);ed.click_doc(1000,1000)
            page.locator('#inspectStamp .mm-rot-presets button[data-rot="90"]').click()
            stamp=next(x for x in ed.summary()['items'] if 'asset' in x);assert stamp['rot']==90
            tool(ed,'tile');page.locator('#tilePack').select_option('kenney-tiny');page.locator('#tileSearch').fill('Gras')
            page.locator('.mm-tile-btn[data-tile="'+GRASS+'"]').click();ed.click_doc(1600,1300)
            tiles=next(x for x in ed.summary()['layers'] if x['kind']=='tiles')
            page.locator('#tab-objects').click()
            expect(page.locator('#objectList .mm-object')).to_have_count(4)
            for key in [path['id'],label['id'],stamp['id'],'tiles:'+tiles['id']+':'+GRASS]:
                row=page.locator('#objectList .mm-object[data-key="'+key+'"]');row.click()
                expect(page.locator('#objectList .mm-object[data-key="'+key+'"]')).to_have_attribute('aria-pressed','true')
                summary=ed.summary()
                assert key in summary['selectedIds'] or (summary['selectedTiles'] and key.startswith('tiles:'))
            page.locator('#objectSearch').fill('QA Route')
            expect(page.locator('#objectList .mm-object')).to_have_count(1)
            page.locator('#objectList .mm-object').click();page.locator('#objectEdit').click()
            expect(page.locator('#selPathName')).to_be_focused();expect(page.locator('#selPathName')).to_have_value('QA Route')
            exported=root/f'fv07-fv08-{engine}-{width}.rdmap.json'
            with page.expect_download() as download:
                page.locator('#fileMenuBtn').click();page.locator('#saveBtn').click()
            download.value.save_as(exported)
            bundle=json.loads(exported.read_text());stored={i['id']:i for l in bundle['layers'] for i in l.get('items',[])}
            assert stored[path['id']]['points']==path['points']
            assert stored[label['id']]['rot']==45 and stored[stamp['id']]['rot']==90
            generation=ed.summary()['generation'];page.locator('#fileInput').set_input_files(str(exported))
            page.wait_for_function('before => rdMapmaker.summary().generation>before',arg=generation)
            reopened={i['id']:i for i in ed.summary()['items']}
            assert reopened[path['id']]['points']==path['points'] and reopened[label['id']]['rot']==45 and reopened[stamp['id']]['rot']==90
            assert next(x for x in ed.summary()['layers'] if x['kind']=='tiles')['tiles']==tiles['tiles']
            page.locator('#tab-objects').click();page.locator('#objectSearch').fill('')
            expect(page.locator('#objectList .mm-object')).to_have_count(4)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.screenshot(path=str(root/f'objects-{engine}-{width}-{language}.png'))
            assert not errors,errors
            proof['journeys'].append({'engine':engine,'role':role,'width':width,'language':language,'theme':theme,
                'normal_maps_navigation':True,'node_draft_toolbar_undo':True,'node_finish_remove_undo_redo':True,
                'explicit_draw_edit_switch':True,'preview_does_not_change_document_history_or_generation':True,
                'rotation_presets_persist':True,'all_four_object_kinds_select_same_map_state':True,
                'filter_and_naming_route':True,'file_roundtrip_exact_nodes_rotations_tiles':True,'no_horizontal_overflow':True,
                'file_sha256':hashlib.sha256(exported.read_bytes()).hexdigest(),'browser_errors':errors});save()
        except Exception as e:
            proof.update(status='failed',error=str(e));page.screenshot(path=str(root/f'failure-{engine}-{width}.png'));save();raise
        finally:context.close();browser.close()
proof['status']='pass';save();print(json.dumps({'status':'pass','journeys':len(proof['journeys'])}))
