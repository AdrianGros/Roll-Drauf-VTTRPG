"""Normal compendium -> owner inventory and validated progression, in both browsers."""
from urllib.parse import urlencode
import pytest
from playwright.sync_api import sync_playwright,expect
from tests.test_personal_actions_browser import action_site  # noqa:F401
from tests.test_presentation_browser import preferences
from tests.test_srd_progression_browser import _fill_open_steps
from vtt.extensions import db
from vtt.models import Character,CharacterCatalogReceipt,InventoryItem,Spell

@pytest.mark.parametrize('engine,width,language,theme',[('chromium',1440,'de','paper'),('firefox',390,'en','night')])
def test_compendium_receipt_retry_inventory_link_and_real_level_choices(action_site,engine,width,language,theme):
    app,origin,info=action_site
    with app.app_context():
        row=db.session.get(Character,info['character']);row.xp=14000;db.session.commit()
    with sync_playwright() as p:
        browser=getattr(p,engine).launch(headless=True,**({'args':['--no-sandbox']} if engine=='chromium' else {}))
        context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        preferences(context,language=language,theme=theme)
        context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(origin+'/characters');page.locator('a[href="/regelwerk/compendium"]').click()
        page.locator('#cpType').select_option('weapon');page.locator('#cpQ').fill('Dolch')
        page.locator('#cpBody a').filter(has_text='Dolch').first.click()
        expect(page.locator('#cpDetailTitle')).to_have_text('Dolch')
        page.locator('#cpCharacterOpen').click()
        expect(page.locator(f'#cpCharacterTarget option[value="{info["character"]}"]')).to_have_count(1)
        page.locator('#cpCharacterTarget').select_option(str(info['character']))
        page.locator('#cpCharacterQuantity').fill('2')
        assert page.evaluate('document.documentElement.scrollWidth')<=width+1
        attempts=[]
        pattern=f'**/api/srd-creator/characters/{info["character"]}/catalog-add'
        def lose_ack(route):
            attempts.append(route.request.post_data_json)
            if len(attempts)==1:
                response=route.fetch();assert response.status==201;route.abort()
            else:route.continue_()
        page.route(pattern,lose_ack)
        page.locator('#cpCharacterAdd').click()
        expect(page.locator('#cpCharacterStatus')).to_contain_text('dieselbe Übernahme' if language=='de' else 'same addition',timeout=30000)
        expect(page.locator('#cpCharacterTarget')).to_be_disabled()
        with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/catalog-add')) as replay:page.locator('#cpCharacterAdd').click()
        assert replay.value.status==200 and replay.value.json()['replayed']
        assert len(attempts)==2 and attempts[0]==attempts[1]
        expect(page.locator('#cpCharacterReceipt')).to_contain_text('2 × Dolch')
        page.unroute(pattern);page.locator('#cpCharacterSheet').click()
        expect(page.locator('#srdInventory')).to_be_visible(timeout=30000)
        expect(page.locator('#srdInventory')).to_contain_text('Dolch')
        page.reload();expect(page.locator('#sfTab-inventory')).to_be_visible(timeout=30000);page.locator('#sfTab-inventory').click()
        expect(page.locator('#srdInventory')).to_contain_text('Dolch')
        with app.app_context():
            assert InventoryItem.query.filter_by(character_id=info['character']).one().quantity==2
            assert CharacterCatalogReceipt.query.filter_by(character_id=info['character']).count()==1
        page.go_back();page.locator('a[href="/regelwerk/compendium"]').click()
        page.locator('#cpType').select_option('spell');page.locator('#cpQ').fill('Magierhand')
        page.locator('#cpBody a').filter(has_text='Magierhand').first.click()
        expect(page.locator('#cpDetailTitle')).to_have_text('Magierhand')  # source stays German in EN UI
        page.locator('#cpCharacterOpen').click()
        expect(page.locator(f'#cpCharacterTarget option[value="{info["character"]}"]')).to_have_count(1)
        page.locator('#cpCharacterTarget').select_option(str(info['character']))
        expect(page.locator('#cpCharacterAdd')).to_be_hidden()
        expect(page.locator('#cpCharacterHint')).to_contain_text('5 → 6')
        page.locator('#cpCharacterProgression').click()
        expect(page.locator('#srdProgression')).to_be_visible(timeout=30000)
        expect(page.locator('.srd-prog-levelup')).to_have_text('Stufe 6 aufsteigen' if language=='de' else 'Advance to level 6')
        page.locator('.srd-prog-levelup').click()
        expect(page.locator('#srdWizard')).to_be_visible();expect(page.locator('#srdWizConfirm')).to_be_disabled()
        _fill_open_steps(page);expect(page.locator('#srdWizConfirm')).to_be_enabled(timeout=30000)
        expect(page.locator('#srdWizConfirm')).to_have_text('Stufe 6 bestätigen' if language=='de' else 'Confirm level 6')
        assert page.evaluate('document.documentElement.scrollWidth')<=width+1
        with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/level-up')) as level:
            page.locator('#srdWizConfirm').click()
        assert level.value.status==200
        expect(page.locator('#charLevel')).to_have_value('6',timeout=30000)
        with app.app_context():
            assert db.session.get(Character,info['character']).level==6
            assert InventoryItem.query.filter_by(character_id=info['character']).one().quantity==2
            assert Spell.query.count()==0
        # A campaign DM can read the sheet, but never gets that figure as an add target.
        reader=browser.new_context(viewport={'width':width,'height':1000});preferences(reader,language=language,theme=theme)
        reader.add_cookies([{'name':'access_token_cookie','value':info['dm_auth'],'url':origin,'httpOnly':True}])
        dm=reader.new_page();dm.set_default_timeout(30000)
        dm.goto(origin+'/regelwerk/compendium?'+urlencode({'type':'weapon','entry':attempts[0]['entity_id']}))
        dm.locator('#cpCharacterOpen').click()
        expect(dm.locator('#cpCharacterStatus')).to_contain_text('Keine passenden' if language=='de' else 'No matching',timeout=30000)
        expect(dm.locator(f'#cpCharacterTarget option[value="{info["character"]}"]')).to_have_count(0)
        expect(dm.locator('#cpCharacterAdd')).to_be_disabled()
        assert not errors,errors
        browser.close()

def test_late_confirmation_cannot_enter_a_different_entity_or_character_dialog(action_site):
    from copy import deepcopy
    app,origin,info=action_site
    with app.app_context():
        original=db.session.get(Character,info['character'])
        other=Character(user_id=original.user_id,name='Second Own Figure',level=5,hp_current=32,hp_max=32,
                        character_data=deepcopy(original.character_data))
        db.session.add(other);db.session.commit();other_id=other.id
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':390,'height':1000})
        context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(30000);page.goto(origin+'/regelwerk/compendium')
        page.locator('#cpType').select_option('weapon');page.locator('#cpQ').fill('Dolch');page.locator('#cpBody a').filter(has_text='Dolch').first.click()
        page.locator('#cpCharacterOpen').click();expect(page.locator(f'#cpCharacterTarget option[value="{info["character"]}"]')).to_have_count(1)
        page.locator('#cpCharacterTarget').select_option(str(info['character']))
        held=[]
        def delay(route):held.append((route,route.fetch()))
        page.route(f'**/api/srd-creator/characters/{info["character"]}/catalog-add',delay)
        with page.expect_request(lambda r:r.method=='POST' and r.url.endswith('/catalog-add')):
            page.locator('#cpCharacterAdd').click()
        page.locator('#cpCharacterClose').click();page.locator('#cpDetailBack').click()
        page.locator('#cpQ').fill('Langschwert');page.locator('#cpBody a').filter(has_text='Langschwert').first.click()
        page.locator('#cpCharacterOpen').click();expect(page.locator(f'#cpCharacterTarget option[value="{other_id}"]')).to_have_count(1)
        page.locator('#cpCharacterTarget').select_option(str(other_id));assert held
        for route,response in held:route.fulfill(response=response)
        expect(page.locator('#cpCharacterReceipt')).to_be_empty()
        expect(page.locator('#cpCharacterTarget')).to_have_value(str(other_id))
        page.locator('#cpCharacterAdd').click();expect(page.locator('#cpCharacterReceipt')).to_contain_text('Second Own Figure',timeout=30000)
        expect(page.locator('#cpCharacterReceipt')).to_contain_text('Langschwert')
        with app.app_context():
            assert InventoryItem.query.filter_by(character_id=info['character']).one().quantity==1
            assert InventoryItem.query.filter_by(character_id=other_id).one().quantity==1
            assert CharacterCatalogReceipt.query.count()==2
        browser.close()

@pytest.mark.parametrize('engine,width,theme',[('firefox',390,'night'),('chromium',1440,'paper')])
def test_pending_search_hides_stale_rows_then_real_click_opens_entry_once(action_site,engine,width,theme):
    import time
    from tests.test_presentation_browser import contrast
    app,origin,info=action_site
    with sync_playwright() as p:
        browser=getattr(p,engine).launch(headless=True,**({'args':['--no-sandbox']} if engine=='chromium' else {}))
        context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce');preferences(context,language='en',theme=theme)
        context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(origin+'/regelwerk/compendium?type=weapon');expect(page.locator('#cpBody a').filter(has_text='Dolch')).to_have_count(1)
        held=[];pattern='**/api/rulesets/*/compendium?*'
        def delay(route):
            if 'q=Dolch' in route.request.url:held.append((route,route.fetch()))
            else:route.continue_()
        page.route(pattern,delay)
        with page.expect_request(lambda request:'q=Dolch' in request.url):page.locator('#cpQ').fill('Dolch')
        expect(page.locator('#cpTable')).to_be_hidden()
        deadline=time.monotonic()+10
        while not held and time.monotonic()<deadline:page.wait_for_timeout(20)
        assert held
        for route,response in held:route.fulfill(response=response)
        expect(page.locator('#cpTable')).to_be_visible();expect(page.locator('#cpBody tr')).to_have_count(1)
        contrast(page,'.compendium-field label,#cpCaption,#cpHead th,#cpBody td,#cpStatus,#cpReset')
        entries=[];page.on('request',lambda request:entries.append(request.url) if '/compendium/entry/' in request.url else None)
        page.locator('#cpBody a').filter(has_text='Dolch').click();expect(page.locator('#cpCharacterOpen')).to_be_visible()
        expect(page.locator('#cpDetailTitle')).to_have_text('Dolch');assert len(entries)==1
        contrast(page,'#cpDetailTitle,#cpDetailMeta,#cpDetailBack')
        page.locator('#cpCharacterOpen').click();expect(page.locator('#cpCharacterDialog')).to_be_visible()
        assert not errors,errors;browser.close()
