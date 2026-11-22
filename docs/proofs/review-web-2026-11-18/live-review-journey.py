"""Normal-role acceptance of calendar, creator, profile, print and world links."""
import json,os
from datetime import datetime,timedelta,timezone
from pathlib import Path
from playwright.sync_api import expect,sync_playwright

root=Path(os.environ['PROOF_ROOT']);fixture=json.loads((root/'private-live-credentials.json').read_text())
origin='https://vtt.roll-drauf.de';proof={'status':'running','journeys':[]};current=None
def save(): (root/'ui-live.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
def passed(name,**details): proof['journeys'].append({'name':name,'status':'pass',**details});save()

with sync_playwright() as p:
    browsers=[]
    def page_for(kind,engine='chromium',width=1440,language='de'):
        browser=getattr(p,engine).launch(headless=True,args=['--no-sandbox'] if engine=='chromium' else [])
        browsers.append(browser)
        context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        context.add_init_script("localStorage.setItem('vtt.display.v1',JSON.stringify({schema:1,theme:'night',language:'"+language+"',unit:'m',accent:'default'}))")
        user=fixture['users'][kind]
        context.add_cookies([{'name':'access_token_cookie','value':user['token'],'url':origin,'httpOnly':True,'secure':True},
                            {'name':'csrf_access_token','value':user['csrf'],'url':origin,'secure':True}])
        page=context.new_page();page.set_default_timeout(25000)
        page.on('dialog',lambda dialog:dialog.accept())
        return page
    try:
        dm=current=page_for('dm')
        dm.goto(origin+'/campaigns')
        dm.locator('.vtt-account-profile').first.click()
        expect(dm.locator('#reviewOwnProfile')).to_contain_text(fixture['users']['dm']['username'])
        dm.locator('#reviewOwnProfile button').click()
        dm.evaluate("localStorage.setItem('qa-review-draft-sentinel','keep');VTTDisplay.update({unit:'ft',accent:'teal'})")
        dm.locator('#vttDisplayOpen').click();dm.locator('#vttDisplayReset').click()
        assert dm.evaluate("VTTDisplay.get().unit==='m' && localStorage.getItem('qa-review-draft-sentinel')==='keep'")
        dm.evaluate("VTTDisplay.update({theme:'night'})")
        passed('Own profile and reset through normal settings preserve unrelated drafts')

        calendar=dm.locator('[data-own-calendar]')
        expect(calendar.locator('[data-calendar-content]')).to_have_attribute('aria-busy','false')
        reminders=calendar.locator('[data-personal-reminders]')
        expect(reminders).to_contain_text('QA Due preparation')
        dm.reload();expect(reminders).to_contain_text('QA Due preparation')
        reminders.locator('[data-dismiss]').first.click();expect(reminders).not_to_contain_text('QA Due preparation')
        cell=calendar.locator('[data-day]').first;day=cell.get_attribute('data-day');cell.click()
        dialog=calendar.locator('[data-calendar-dialog]');form=dialog.locator('[data-note-form]')
        form.locator('[name=title]').fill('QA Private preparation');form.locator('[name=body]').fill('Private QA note')
        form.locator('[name=color]').select_option('blue');form.locator('[type=submit]').click()
        expect(dialog.locator('[data-note]')).to_contain_text('QA Private preparation')
        dialog.locator('[data-day-close]').click();dm.reload()
        calendar.locator(f'[data-day="{day}"]').click()
        expect(dialog.locator('[data-note]')).to_contain_text('QA Private preparation')
        dialog.locator('[data-note-edit]').click();form.locator('[name=title]').fill('QA Edited preparation');form.locator('[type=submit]').click()
        expect(dialog.locator('[data-note]')).to_contain_text('QA Edited preparation')
        dm.screenshot(path=str(root/'calendar-note-night.png'))
        dialog.locator('[data-note-delete]').click();expect(dialog.locator('[data-note]')).to_have_count(0)
        dialog.locator('[data-day-close]').click()
        calendar.locator('[data-oneshots]').click();shot=dialog.locator('[data-oneshot-form]')
        shot.locator('[name=name]').fill('QA Review One-Shot')
        first=(datetime.now(timezone.utc)+timedelta(days=2)).replace(hour=19,minute=0,second=0,microsecond=0).isoformat(timespec='minutes')[:16]
        shot.locator('[name=first_local]').fill(first);shot.locator('[name=timezone]').fill('UTC');shot.locator('[type=submit]').click()
        expect(dialog.get_by_role('link',name='QA Review One-Shot')).to_be_visible()
        passed('Private note create/reload/edit/delete, durable ready reminder and real campaign-backed One-Shot',date=day)

        dm.goto(origin+'/srd-creator');dm.locator('#scNewRandom').click();dm.locator('#scModeQuick').click()
        details=dm.locator('#scStepBody details').first;details.locator('summary').click()
        field=dm.locator('#scId-name');field.fill('QA Stable Draft');field.evaluate('node=>{node.focus();node.setSelectionRange(2,6)}')
        before=field.bounding_box()['y'];dm.evaluate('() => SrdCreator.renderAll()')
        expect(field).to_be_focused();assert abs(field.bounding_box()['y']-before)<2
        assert details.evaluate('node=>node.open')
        expect(dm.locator('#scSave')).to_have_text('Gespeichert')
        passed('Creator all-at-once editing preserves focus, selection, disclosure and working scroll position')

        dm.goto(origin+'/regelwerk');expect(dm.locator('#regelwerkArticle')).to_have_attribute('aria-busy','false')
        dm.evaluate('() => {window.qaPrints=0;window.print=()=>window.qaPrints++}')
        dm.locator('#regelwerkPrint').click();assert dm.evaluate('window.qaPrints')==0
        dm.locator('#reviewPrintNext').click();assert dm.evaluate('window.qaPrints')==0
        with dm.expect_response(lambda response:response.url.endswith('/api/review-web/print-requests') and response.request.method=='POST') as request:
            dm.locator('#reviewPrintConfirm').click()
        assert request.value.status==201 and request.value.json()['recorded'] is True
        assert dm.evaluate('window.qaPrints')==1
        passed('Two deliberate print confirmations record one UI request; physical printing is not claimed')

        dm.goto(origin+'/atlas');dm.locator('#atlasNewTitle').fill('QA Review World')
        expect(dm.locator('#atlasNewCampaign option[value="'+str(fixture['campaign_id'])+'"]')).to_have_count(1)
        dm.locator('#atlasNewCampaign').select_option(str(fixture['campaign_id']));dm.locator('#atlasCreate').click()
        expect(dm.locator('#atlasCampaignLinks a')).to_contain_text('QA UI Playtable')
        dm.reload();expect(dm.locator('#atlasCampaignLinks a')).to_have_count(1)
        dm.screenshot(path=str(root/'atlas-campaign-link.png'))
        passed('Create an optional world-to-campaign link through Atlas and retain it after reload')

        dm.goto(origin+f"/conversations?campaign_id={fixture['campaign_id']}")
        dm.locator('#conversationThreads summary').click();dm.locator('#threadTitle').fill('<b>QA Plain Thread</b>')
        dm.locator('#threadCreate button').click();expect(dm.locator('#threadHeading')).to_have_text('<b>QA Plain Thread</b>')
        thread_id=dm.locator('#threadList [data-thread-id]').first.get_attribute('data-thread-id')
        dm.locator('#threadMessage').fill('<script>QA Plain Message</script>')
        dm.locator('#threadMessage').locator('..').locator('..').locator('button').click()
        expect(dm.locator('#threadHistory p')).to_have_text(['<script>QA Plain Message</script>'])
        assert dm.locator('#threadHistory script').count()==0
        passed('Campaign thread through Conversations stores only literal text')

        player=current=page_for('player','firefox',390,'en')
        player.goto(origin+f"/conversations?campaign_id={fixture['campaign_id']}")
        player.locator('#conversationThreads summary').click();player.locator('[data-thread-id="'+thread_id+'"]').click()
        expect(player.locator('#threadHistory p')).to_have_text(['<script>QA Plain Message</script>'])
        passed('Authorized Player reads the same campaign thread without interpreting HTML')
        player.goto(origin+f"/character-sheet?id={fixture['character_id']}&mode=edit")
        expect(player.locator('#sheetIdentityUpload-avatar')).to_be_visible()
        assert player.locator('#sheetIdentityGrid').bounding_box()['y']<player.locator('.sf-layout').bounding_box()['y']
        player.locator('[data-review-section=srdManage]').click();expect(player.locator('#sfPanel-manage')).to_be_visible()
        player.locator('#companionScaling summary').click()
        expect(player.locator('#companionScaling')).to_contain_text('QA Companion')
        player.screenshot(path=str(root/'sheet-mobile-night.png'))
        player.goto(origin+'/regelwerk/compendium?locale=de')
        expect(player.locator('html')).to_have_attribute('lang','en')
        player.locator('#cpContentLanguage').select_option('en');player.locator('#cpRulebookLink').click()
        expect(player.locator('#regelwerkArticle')).to_have_attribute('lang','en')
        expect(player.locator('#regelwerkArticle')).to_have_attribute('aria-busy','false')
        assert player.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        passed('Firefox mobile EN/night: real upload controls above stats, companion section, independent content language')
        proof['status']='pass';save()
    except Exception as error:
        proof['status']='failed';proof['error']=str(error)
        if current:current.screenshot(path=str(root/'ui-failure.png'))
        save();raise
    finally:
        for browser in browsers:browser.close()
