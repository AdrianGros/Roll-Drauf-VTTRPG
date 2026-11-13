import json,re
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from tests.test_feedback_invocation_prerequisites import warlock,PREFIX
ROOT=Path('/delivery');ORIGIN='https://vtt.roll-drauf.de'
fixture=json.loads((ROOT/'live-credentials.json').read_text())
proof={'status':'running','journeys':[],'checks':{},'errors':[]}

def login(context,kind):
    page=context.new_page();page.set_default_timeout(45000)
    page.on('pageerror',lambda e:proof['errors'].append(str(e)))
    page.goto(ORIGIN+'/login.html')
    page.locator('#loginUsername').fill(fixture['users'][kind]['username'])
    page.locator('#loginPassword').fill(fixture['users'][kind]['password'])
    page.locator('#passwordLoginSubmitBtn').click();page.wait_for_url(lambda u:'/login' not in u)
    return page

with sync_playwright() as p:
    chrome=p.chromium.launch(headless=True,args=['--no-sandbox'])
    firefox=p.firefox.launch(headless=True)
    dc=chrome.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    pc=firefox.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    try:
        dm=login(dc,'dm');player=login(pc,'player')
        for page,kind,action in [(dm,'dm','open-session-dm'),(player,'player','open-session')]:
            page.goto(f'{ORIGIN}/campaigns?campaign_id={fixture["campaign_id"]}')
            page.locator(f'[data-hub-action="{action}"][data-hub-session-id="{fixture["session_id"]}"]').click()
            page.wait_for_url(lambda u:'/play' in u);page.wait_for_function('() => !!window.RollDraufTable')
            if kind=='player':assert not page.evaluate('() => !!window.PlayDMSurface')
            page.locator('#btnBack').click()
            page.locator('#appMenu [data-book-return-target="/mapmaker"]').click()
            page.wait_for_url(ORIGIN+'/static/mapmaker/index.html')
            expect(page.locator('#cloudSave')).to_be_visible()
            proof['journeys'].append(kind+': campaign hub → own session → Back → Maps → editor')
            page.screenshot(path=str(ROOT/(kind+'-back-maps.png')),full_page=True)

        player.locator('.vtt-map-nav a[href="/characters"]').click()
        player.wait_for_url(ORIGIN+'/characters')
        # Normal archive entry, followed by the actual creator's new-draft control.
        player.get_by_role('button',name='Held anlegen',exact=True).click()
        player.wait_for_url(lambda u:'/srd-creator' in u)
        player.locator('#scNewQuick').click();expect(player.locator('#scBuilder')).to_be_visible()
        data=pc.request.get(ORIGIN+'/api/srd-creator/creator-data').json()
        state=warlock(data)
        state['featureChoices']['warlock']['eldritch-invocations']=[PREFIX+'eldritch-mind']
        player.evaluate('(state)=>window.SrdCreator.mutate(s=>{Object.keys(s).forEach(k=>delete s[k]);Object.assign(s,state);})',state)
        expect(player.locator('#scSave')).to_have_text('Gespeichert')
        smite=player.get_by_role('checkbox',name=re.compile('^Schauerliches Niederstrecken'))
        pact=player.get_by_role('checkbox',name=re.compile('^Pakt der Klinge'))
        expect(smite).to_be_disabled();pact.check()
        expect(player.locator('#scSave')).to_have_text('Gespeichert');expect(smite).to_be_enabled()
        smite.check();expect(player.locator('#scSave')).to_have_text('Gespeichert')
        pact.uncheck();expect(player.locator('#scSave')).to_have_text('Gespeichert')
        expect(smite).to_be_checked();expect(smite).to_be_enabled()
        expect(smite.locator('xpath=../..')).to_contain_text('Erfordert die gültige Anrufung')
        player.screenshot(path=str(ROOT/'creator-prerequisite.png'),full_page=True)
        proof['checks']['creator_selection_updates_and_keeps_invalid_selection_removable']=True

        invalid=warlock(data)
        invalid['featureChoices']['warlock']['eldritch-invocations']=[PREFIX+x for x in
            ['eldritch-mind','devils-sight','fiendish-vigor','ascendant-step','eldritch-smite']]
        result=player.evaluate('''async state=>{
            const SC=window.SrdCreator;const created=await SC.api('/drafts','POST',{state});
            if(!created.ok)return {create:created.status};
            const d=created.data.draft;const final=await SC.api('/drafts/'+d.id+'/finalize','POST',{version:d.version});
            return {create:created.status,finalize:final.status,codes:(final.data.blockers||[]).map(b=>b.code)};
        }''',invalid)
        assert result['finalize']==422 and 'class-option-prerequisite' in result['codes'],result
        proof['checks']['direct_finalize_rejected']=result

        state=warlock(data,4)
        state['featureChoices']['warlock']['eldritch-invocations']=[PREFIX+x for x in
            ['eldritch-mind','devils-sight','fiendish-vigor']]
        result=player.evaluate('''async state=>{
            const SC=window.SrdCreator;const c=await SC.api('/drafts','POST',{state});const d=c.data.draft;
            const f=await SC.api('/drafts/'+d.id+'/finalize','POST',{version:d.version});
            if(!f.ok)return {status:f.status,body:f.data};const id=f.data.character.id;
            const a=await SC.api('/characters/'+id+'/progression','PUT',{mode:'milestone',milestoneTarget:5});
            return {status:a.status,id};
        }''',state)
        assert result['status']==200,result
        player.goto(f'{ORIGIN}/character-sheet?id={result["id"]}&mode=edit')
        player.get_by_role('tab',name='Verwaltung',exact=True).click()
        player.get_by_role('button',name='Stufe 5 aufsteigen').click()
        smite=player.locator(f'#srdWizard input[value="{PREFIX}eldritch-smite"]')
        pact=player.locator(f'#srdWizard input[value="{PREFIX}pact-of-the-blade"]')
        expect(smite).to_be_disabled();pact.check();expect(smite).to_be_enabled()
        smite.check();pact.uncheck()
        expect(smite.locator('xpath=..')).to_contain_text('Erfordert die gültige Anrufung')
        expect(player.locator('#srdWizConfirm')).to_be_disabled()
        player.screenshot(path=str(ROOT/'progression-prerequisite.png'),full_page=True)
        proof['journeys'].append('Player archive → creator → dependent selection → sheet management → level-up prerequisites')
        proof['checks']['progression_uses_current_server_preview']=True
        assert not proof['errors'],proof['errors'];proof['status']='pass'
    except BaseException as e:
        proof['status']='fail';proof['failure']=str(e)
        raise
    finally:
        (ROOT/'live-result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
        dc.close();pc.close();chrome.close();firefox.close()
