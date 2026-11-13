"""Two real authors, a separate Reader, three maps, publication and existing editor."""
from pathlib import Path
import pytest
from flask_jwt_extended import create_access_token
from playwright.sync_api import sync_playwright,expect
from tests.test_personal_actions_browser import action_site  # noqa:F401
from tests.test_presentation_browser import preferences,contrast
from tests.test_mapmaker_library import document
from vtt.extensions import db
from vtt.models import User,Role
from vtt.models.atlas import AtlasWorld,AtlasMap

def test_atlas_three_map_author_reader_editor_and_revocation(action_site,tmp_path):
 app,origin,info=action_site
 with app.app_context():
  app.config.update(LOCAL_STORAGE_PATH=str(tmp_path/'storage'),STORAGE_PROVIDER='local')
  owner=User.query.filter_by(username='action-dm').one();owner.storage_quota_gb=1
  reader=User(username='atlas-reader',email='atlas-reader@example.test',role_id=Role.query.first().id,is_active=True,password_hash='test',storage_quota_gb=1);db.session.add(reader);db.session.commit();reader_auth=create_access_token(identity=str(reader.id))
  client=app.test_client();client.set_cookie('access_token_cookie',info['dm_auth']);doc=document();doc['meta']['title']='SECRET-SOURCE-TITLE';source=client.post('/api/assets/mapmaker/projects',json={'document':doc},headers={'X-Mapmaker-Account':str(owner.id)});assert source.status_code==201,source.json;project=source.json['project']
 with sync_playwright() as p:
  chrome=p.chromium.launch(headless=True,args=['--no-sandbox']);ff=p.firefox.launch(headless=True)
  contexts=[];pages=[];errors=[];reader_requests=[]
  def accept_dialog(dialog):dialog.accept()
  for browser,token,width,language,theme in [(chrome,info['dm_auth'],1440,'de','paper'),(ff,info['player_auth'],390,'en','night'),(ff,reader_auth,390,'en','night')]:
   context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce');contexts.append(context);preferences(context,language=language,theme=theme);context.add_cookies([{'name':'access_token_cookie','value':token,'url':origin,'httpOnly':True}]);page=context.new_page();page.set_default_timeout(30000);page.on('dialog',accept_dialog);page.on('pageerror',lambda error:errors.append({'message':str(error),'stack':error.stack}));pages.append(page)
  owner,editor,reader=pages;reader.on('request',lambda request:reader_requests.append(request.url))
  owner.goto(origin+'/characters');owner.locator('a[href="/atlas"]').click();owner.locator('#atlasNewTitle').fill('Three map Atlas');owner.locator('#atlasCreate').click();expect(owner.locator('#atlasTitle')).to_be_visible();world=owner.url.split('world=')[-1]
  owner.locator('#atlasPrivateLore').fill('SECRET-WORLD');owner.locator('#atlasSummary').fill('A navigable world');owner.locator('#atlasSave').click();expect(owner.locator('#atlasAuthorStatus')).to_have_text('Gespeichert.')
  owner.locator('#atlasLibraryLoad').click();expect(owner.locator('#atlasLibrarySelect option')).to_have_count(1)
  map_ids=[]
  for title in ('Continent','Coast','Harbour'):
   owner.locator('#atlasAttach').click();expect(owner.locator('#atlasAttachConfirm')).to_be_visible(timeout=60000);owner.locator('#atlasAttachConfirm').click();expect(owner.locator('dialog.atlas-dialog')).to_have_count(0,timeout=30000)
   expect(owner.locator('#atlasAuthorMap option')).to_have_count(len(map_ids)+1);mid=owner.locator('#atlasAuthorMap').input_value();map_ids.append(mid)
   owner.locator('#atlasMapTitle').fill(title);owner.locator('#atlasMapVisible').check();owner.locator('#atlasMapScale').fill('1.5');owner.locator('#atlasSave').click();expect(owner.locator('#atlasAuthorStatus')).to_have_text('Gespeichert.')
  owner.locator('#atlasAddPlace').click();owner.locator('#atlasPlaceName').fill('Visible coast');owner.locator('#atlasPlaceLore').fill('Public coastline');owner.locator('#atlasPlacePrivate').fill('SECRET-COAST');owner.locator('#atlasPlaceVisible').check();owner.locator('#atlasPlaceMap').select_option(map_ids[0]);owner.locator('#atlasPlace-x').fill('30');owner.locator('#atlasPlace-y').fill('40');owner.locator('#atlasSave').click();expect(owner.locator('#atlasAuthorStatus')).to_have_text('Gespeichert.');first_place=owner.locator('#atlasPlaceSelect').input_value()
  owner.locator('#atlasAddPlace').click();owner.locator('#atlasPlaceName').fill('Visible harbour');owner.locator('#atlasPlaceLore').fill('Public harbour');owner.locator('#atlasPlaceVisible').check();owner.locator('#atlasParent').select_option(first_place);owner.locator('#atlasPlaceMap').select_option(map_ids[1]);owner.locator('#atlasPlace-x').fill('50');owner.locator('#atlasPlace-y').fill('60');owner.locator('#atlasPlaceLinks').select_option(first_place);owner.locator('#atlasSave').click();expect(owner.locator('#atlasAuthorStatus')).to_have_text('Gespeichert.');second_place=owner.locator('#atlasPlaceSelect').input_value()
  owner.locator('#atlasAddPlace').click();owner.locator('#atlasPlaceName').fill('SECRET-PLACE');owner.locator('#atlasPlacePrivate').fill('SECRET-LORE');owner.locator('#atlasSave').click();expect(owner.locator('#atlasAuthorStatus')).to_have_text('Gespeichert.')
  for username,role in [('action-player','editor'),('atlas-reader','reader')]:
   owner.locator('#atlasMemberName').fill(username);owner.locator('#atlasMemberRole').select_option(role);owner.locator('#atlasGrant').click();expect(owner.locator('#atlasMembers')).to_contain_text(username)
  owner.locator('#atlasPreview').click();expect(owner.locator('dialog #atlasPlaces')).to_contain_text('Visible coast');expect(owner.locator('dialog')).not_to_contain_text('SECRET');owner.locator('#atlasPublishConsent').check();owner.locator('#atlasPublish').click();expect(owner.locator('dialog.atlas-dialog')).to_have_count(0)
  reader.goto(origin+f'/atlas?world={world}&place={second_place}');expect(reader.locator('#atlasPlaceDetail')).to_contain_text('Public harbour');expect(reader.locator('#atlasMapSelect')).to_have_value(map_ids[1]);reader.locator('#atlasPlaceDetail nav a').click();expect(reader.locator('#atlasMapSelect')).to_have_value(map_ids[0]);expect(reader.locator('#atlasScale')).to_contain_text('1.5 km')
  contrast(reader,'#atlasRoot h1,#atlasRoot label,#atlasScale')
  expect(reader.locator('#atlasRoot')).not_to_contain_text('SECRET');expect(reader.locator('#atlasSave')).to_have_count(0);assert not any('/atlas-author.js' in url or '/maps/'+map_ids[0]+'?' in url for url in reader_requests)
  reader.locator('#atlasSearch').fill('SECRET');expect(reader.locator('#atlasPlaces a')).to_have_count(0);reader.locator('#atlasSearch').fill('')
  assert reader.evaluate('document.documentElement.scrollWidth')<=391
  reader_data=reader.request.get(origin+f'/api/atlas/worlds/{world}/published').json();image_url=origin+f'/api/atlas/worlds/{world}/published/maps/{map_ids[0]}.png?version='+reader_data['publication_id'];published_pixels=reader.request.get(image_url).body()
  # Actual Player global profile gets only its explicit world Editor rights.
  editor.goto(origin+f'/atlas?world={world}');expect(editor.locator('#atlasSave')).to_be_visible();expect(editor.locator('#atlasMemberName')).to_have_count(0);editor.locator('#atlasAuthorMap').select_option(map_ids[0]);editor.locator('#atlasEditMap').click();expect(editor.locator('#app')).to_have_attribute('data-state','ready',timeout=60000)
  expect(editor.locator('#cloudSave')).to_have_text('Save Atlas map');expect(editor.locator('#libraryBtn')).to_be_hidden();expect(editor.locator('#atlasEditorStatus')).to_have_text('Atlas map saved.')
  owner_map=contexts[0].new_page();owner_map.set_default_timeout(30000);owner_map.on('pageerror',lambda error:errors.append({'message':str(error)}));owner_map.goto(editor.url);expect(owner_map.locator('#app')).to_have_attribute('data-state','error',timeout=60000);expect(owner_map.locator('#loadingText')).to_contain_text('anderen Fenster')
  editor.locator('#landmassBtn').click();editor.locator('#landmassPreview').click();expect(editor.locator('#landmassAdopt')).to_be_enabled(timeout=30000);editor.locator('#landmassAdopt').click();expect(editor.locator('#undoBtn')).to_be_enabled();editor.locator('#undoBtn').click();expect(editor.locator('#redoBtn')).to_be_enabled();editor.locator('#redoBtn').click()
  # The private Atlas working copy has no personal autosave: actual reload must warn.
  warnings=[]
  def keep_unsaved(dialog):warnings.append(dialog.type);dialog.dismiss()
  editor.remove_listener('dialog',accept_dialog);editor.on('dialog',keep_unsaved)
  before=editor.evaluate('window.rdMapmaker.summary()')
  from playwright.sync_api import Error
  try:editor.reload(timeout=5000)
  except Error:pass  # browsers report a canceled navigation differently
  assert warnings==['beforeunload'],warnings
  assert editor.evaluate('window.rdMapmaker.summary()')==before
  editor.remove_listener('dialog',keep_unsaved);editor.on('dialog',accept_dialog)
  with editor.expect_response(lambda r:r.request.method=='PUT' and '/maps/' in r.url) as saved:editor.locator('#cloudSave').click()
  assert saved.value.status==200,saved.value.text();expect(editor.locator('#atlasEditorStatus')).to_have_text('Atlas map saved.')
  assert reader.request.get(image_url).body()==published_pixels
  assert contexts[0].request.get(origin+'/api/assets/mapmaker/projects/'+project['id']).json()['project']['revision']==1
  editor.locator('#atlasEditorBack').click();expect(editor.locator('#atlasSave')).to_be_visible();owner_map.reload();expect(owner_map.locator('#app')).to_have_attribute('data-state','ready',timeout=60000);owner_map.close()
  owner.locator('#atlasReload').click();expect(owner.locator('#atlasAuthorStatus')).to_have_text('Gespeichert.');owner.locator('#atlasPreview').click();owner.locator('#atlasPublishConsent').check();owner.locator('#atlasPublish').click();expect(owner.locator('dialog.atlas-dialog')).to_have_count(0)
  expect(reader.locator('#atlasPlaceDetail')).to_be_visible();reader.wait_for_function('old=>document.querySelector(".atlas-map-canvas img")?.src.includes(old)===false',arg=reader_data['publication_id'],timeout=15000)
  with owner.expect_download() as backed:owner.locator('#atlasBackup-zip').click()
  backup=tmp_path/'atlas.zip';backed.value.save_as(backup);assert backup.stat().st_size>1000
  owner.locator('#atlasMemberName').fill('atlas-reader');owner.locator('#atlasMemberRole').select_option('remove');owner.locator('#atlasGrant').click();expect(reader.locator('#atlasDenied')).to_be_visible(timeout=15000);expect(reader.locator('.atlas-map-canvas')).to_have_count(0)
  assert not errors,errors
  for context in contexts:context.close()
  chrome.close();ff.close()
