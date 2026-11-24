"""FV06 native shortcuts/palette and persistent colors through ordinary Maps entry."""
import hashlib,json,os
from pathlib import Path
from playwright.sync_api import expect,sync_playwright
from tests.test_mapmaker_browser import Editor

root=Path(os.environ['PROOF_ROOT']);fixture=json.loads((root/'private-live-credentials.json').read_text());origin='https://vtt.roll-drauf.de'
proof={'status':'running','journeys':[],'real_oauth_tested':False,'remote_projects_created':False};expect.set_options(timeout=30000)
def save():(root/'live.json').write_text(json.dumps(proof,indent=2)+'\n')
def tool_pane(page):
 if not page.locator('#pane-tool').is_visible():page.locator('#tab-tool').click()
def canvas_ready(page,width):
 if width<760 and page.locator('#pane-tool').is_visible():page.locator('#tab-tool').click()
def state(ed):
 s=ed.summary();return {k:s[k] for k in ['items','layers','generation','historySteps']}
save()
with sync_playwright() as p:
 for engine,role,width,language,theme in [('chromium','dm',1440,'de','night'),('firefox','player',390,'en','paper')]:
  browser=getattr(p,engine).launch(headless=True,**({'args':['--no-sandbox']} if engine=='chromium' else {}))
  context=browser.new_context(viewport={'width':width,'height':1000},accept_downloads=True,reduced_motion='reduce')
  prefs={'language':language,'theme':theme,'accent':'teal'};context.add_init_script("localStorage.setItem('vtt.display.v1',"+json.dumps(json.dumps(prefs))+")")
  auth=fixture['users'][role];context.add_cookies([{'name':'access_token_cookie','value':auth['token'],'url':origin,'httpOnly':True,'secure':True},{'name':'csrf_access_token','value':auth['csrf'],'url':origin,'secure':True}])
  page=context.new_page();page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  try:
   page.goto(origin+'/dashboard');page.locator('.book-dashboard-ribbon:visible a[href="/mapmaker"]').click();page.wait_for_selector('#app[data-state=ready]');page.locator('#newEmpty').click()
   ed=Editor(context,page,errors);ed.tool('brush');tool_pane(page)
   page.locator('#brushColorEnabled').check();page.locator('#brushColor').fill('#407e75');ed.set_range('#brushSize',24)
   canvas_ready(page,width);ed.click_doc(600,500);tool_pane(page)
   expect(page.locator('#recentColors button[data-color="#407e75"]')).to_be_visible()
   canvas_ready(page,width);page.locator('#mapCanvas').focus();page.keyboard.press('3');expect(page.locator('#brushOpacity')).to_have_value('30');page.keyboard.press('0')
   page.mouse.move(*ed.client(700,500));zoom=ed.summary()['zoom'];size=int(page.locator('#brushSize').input_value())
   page.keyboard.down('Shift');page.mouse.wheel(0,-120);page.keyboard.up('Shift');expect(page.locator('#brushSize')).not_to_have_value(str(size));assert ed.summary()['zoom']==zoom
   material=page.locator('#materials [aria-checked=true]').get_attribute('data-material');page.keyboard.down('Alt');page.mouse.wheel(0,-120);page.keyboard.up('Alt')
   expect(page.locator('#materials [aria-checked=true]')).not_to_have_attribute('data-material',material);assert ed.summary()['zoom']==zoom
   before=state(ed)
   if width>=760:
    page.locator('#mapCanvas').focus();page.keyboard.down('q');expect(page.locator('#quickPalette')).to_be_visible();assert state(ed)==before
    page.locator('#quickTools [data-tool=label]').hover();assert state(ed)==before;page.keyboard.up('q');expect(page.locator('#quickPalette')).not_to_be_visible();assert ed.summary()['tool']=='label'
   else:
    tool_pane(page);page.locator('#quickPaletteOpen').click();expect(page.locator('#quickPalette')).to_be_visible();page.keyboard.press('Tab');assert page.evaluate("!!document.activeElement.closest('#quickPalette')")
    page.locator('#quickTools [data-tool=eraser]').click();assert ed.summary()['tool']=='eraser'
   assert state(ed)==before;tool_pane(page);page.locator('#quickPaletteOpen').click()
   box=page.locator('#quickPalette').bounding_box();assert box['x']>=0 and box['x']+box['width']<=width+1
   page.screenshot(path=str(root/f'palette-{engine}-{width}-{language}.png'))
   page.locator('#quickColors [data-color="#407e75"]').click();assert ed.summary()['tool']=='brush';expect(page.locator('#brushColor')).to_have_value('#407e75');assert state(ed)==before
   exported=root/f'brush-{engine}-{width}.rdmap.json'
   with page.expect_download() as pending:page.locator('#fileMenuBtn').click();page.locator('#saveBtn').click()
   pending.value.save_as(exported);raw=json.loads(exported.read_text());assert 'recentColors' not in raw and 'recentColors' not in raw.get('meta',{})
   expect(page.locator('#saveStatus')).to_have_attribute('data-state','saved',timeout=30000);page.reload();page.wait_for_selector('#restoreDialog[open]');page.locator('#restoreYes').click();page.wait_for_selector('#app[data-state=ready]')
   assert page.locator('#recentColors button').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.color)')==['#407e75']
   tool_pane(page);page.locator('#quickPaletteOpen').click();expect(page.locator('#quickColors [data-color="#407e75"]')).to_be_visible();page.keyboard.press('Escape');expect(page.locator('#quickPaletteOpen')).to_be_focused()
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');assert not errors,errors
   proof['journeys'].append({'engine':engine,'role':role,'width':width,'language':language,'theme':theme,'normal_maps_navigation':True,'completed_color_stroke_and_reselection':True,'opacity_size_material_shortcuts_synchronized':True,'modifier_shortcuts_leave_zoom_unchanged':True,'temporary_hover_or_native_keyboard_button_palette':True,'opening_hover_and_choice_leave_document_history_unchanged':True,'color_history_survives_actual_autosave_reload':True,'local_file_contains_no_color_preference_fields':True,'native_escape_focus_return':True,'palette_fits_and_no_horizontal_overflow':True,'file_sha256':hashlib.sha256(exported.read_bytes()).hexdigest(),'browser_errors':errors});save()
  except Exception as e:
   proof.update(status='failed',error=str(e));page.screenshot(path=str(root/f'failure-{engine}-{width}.png'));save();raise
  finally:context.close();browser.close()
proof['status']='pass';save()
