import re
import pytest
from tests.test_srd_sheet import site  # noqa: F401
from tests.test_srd_creator_api import wizard_state
from vtt.rules_content.creator_rules import load_creator_data


@pytest.mark.parametrize('engine,width',[('chromium',1440),('firefox',390)])
def test_eagle_companion_to_creator_and_explained_sheet(site,engine,width):
    from playwright.sync_api import sync_playwright,expect
    app,origin,info=site;app.config.update(CE_AUTHORING=True,CE_PLAYABLE_ORIGINS=True)
    with sync_playwright() as p:
        browser=getattr(p,engine).launch(headless=True,args=['--no-sandbox'] if engine=='chromium' else [])
        context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        context.add_cookies([{'name':'access_token_cookie','value':info['token'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(origin+'/characters')
        entry=page.locator('[data-creation-engine-nav]').first
        expect(entry).to_have_attribute('aria-disabled','false');entry.click()
        expect(page.locator('#ce-origins')).to_be_visible()
        page.locator('#ce-origin-new-feat').click()
        expect(page.locator('#ce-origin-name')).to_have_value('Wachsamer Pfadfinder')
        page.locator('#ce-origin-name').fill('Kundiger Pfadfinder')
        page.locator('#ce-origin-check').click()
        expect(page.locator('#ce-origin-report')).to_contain_text('Spielbar:')
        page.locator('#ce-origin-publish').click()
        expect(page.locator('#ce-origin-report')).to_contain_text('Veröffentlicht · Fassung 1')
        fid=page.evaluate("async()=>{const r=await Auth.makeAuthRequest('/api/srd-creator/origin-catalog');return r.feats.find(f=>f.name==='Kundiger Pfadfinder').id;}")
        page.locator('#ce-origin-new-background').click()
        expect(page.locator('#ce-origin-name')).to_have_value('Pfadwanderer')
        page.locator('#ce-origin-feat').select_option(fid)
        page.locator('#ce-origin-check').click()
        expect(page.locator('#ce-origin-report')).to_contain_text('50 GM')
        page.locator('#ce-origin-publish').click()
        expect(page.locator('#ce-origin-report')).to_contain_text('Veröffentlicht · Fassung 1')
        page.reload();expect(page.locator('#ce-origins')).to_be_visible()
        # Prepare the already-covered core wizard choices, then choose this new
        # background through the normal Creator and finalize there.
        state=wizard_state(load_creator_data(),'Herkunftstest')
        draft=page.evaluate("async state=>Auth.makeAuthRequest('/api/srd-creator/drafts','POST',{state})",state)
        page.goto(f"{origin}/srd-creator?draft={draft['draft']['id']}&schritt=herkunft")
        page.get_by_role('button',name=re.compile('^Pfadwanderer')).click()
        page.locator('#scBgPlus2').select_option('int');page.locator('#scBgPlus1').select_option('con')
        page.get_by_role('button',name='Hintergrund-Text lesen').click()
        expect(page.locator('#scDialogBody')).to_contain_text('Homebrew · Fassung 1');page.locator('#scDialogClose').click()
        page.locator('#scSteps').get_by_role('button',name=re.compile('Prüfung')).click()
        expect(page.locator('#scSave')).to_have_text('Gespeichert')
        expect(page.locator('#scFinalize-btn')).to_be_enabled();page.locator('#scFinalize-btn').click()
        page.get_by_role('link',name='Zum Charakterbogen').click()
        expect(page.locator('#srdProvenance')).to_be_visible()
        page.locator('#srdProvenance > summary').click()
        expect(page.locator('#srdProvenance')).to_contain_text('Kundiger Pfadfinder · Homebrew-Fassung 1')
        row=page.locator('[data-provenance-key="initiative"]');expect(row.locator('summary')).to_have_text('Initiative: 4');row.locator('summary').click()
        expect(row).to_contain_text('Kundiger Pfadfinder: +3')
        expect(page.locator('[data-provenance-key="skill.arkane-kunde"]')).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth')<=width+1
        assert not errors,errors
        browser.close()
