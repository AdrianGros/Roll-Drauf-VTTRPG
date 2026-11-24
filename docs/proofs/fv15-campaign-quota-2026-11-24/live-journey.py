"""Normal production profile journeys, acting only on manifest-owned QA requests."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import expect, sync_playwright

root=Path(os.environ['PROOF_ROOT'])
fixture=json.loads((root/'private-live-credentials.json').read_text())
repo=Path(__file__).resolve().parents[3]
messages=json.loads((repo/'tools/i18n/tasks/fv15-campaign-quota.json').read_text())
origin='https://vtt.roll-drauf.de'
proof={'status':'running','origin':origin,'journeys':[],'real_accounts_adjusted':False,'real_oauth_tested':False}
expect.set_options(timeout=30000)
reason='QA quota literal {total} <img src=x onerror="window.cqInjected=1">'
main_reason='QA quota explicit manual approval {total}'
reject_reason='QA quota explicit rejection {total}'
owner_note='QA review Charaktere {total} <literal>'
admin_note='QA rejected Charaktere {total} <literal>'

def save(): (root/'live.json').write_text(json.dumps(proof,indent=2)+'\n')
def text(source,lang):
    return messages[source][lang] if source in messages else {'Ablehnen':{'de':'Ablehnen','en':'Reject'}}[source][lang]

def post(page,path,action,actor):
    with page.expect_response(lambda r:r.request.method=='POST' and urlsplit(r.url).path==path) as pending:action()
    response=pending.value
    assert response.status in (200,201),(path,response.status)
    data=response.json();assert data['accountId']==fixture['users'][actor]['id']
    return data

def current(panel,quota):expect(panel.locator('.cq-facts .cq-fact-value').first).to_have_text(str(quota))

with sync_playwright() as p:
    browsers={'chromium':p.chromium.launch(headless=True,args=['--no-sandbox']),'firefox':p.firefox.launch(headless=True)}
    pages={};contexts=[];errors=[]
    try:
        for role,engine,width,lang,theme in [('dm','chromium',1440,'de','night'),('player','firefox',390,'en','paper'),('owner','firefox',390,'en','paper'),('admin','chromium',1440,'de','night')]:
            context=browsers[engine].new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
            contexts.append(context);auth=fixture['users'][role]
            context.add_cookies([{'name':'access_token_cookie','value':auth['token'],'url':origin,'httpOnly':True,'secure':True},{'name':'csrf_access_token','value':auth['csrf'],'url':origin,'secure':True}])
            context.add_init_script("if(!localStorage.getItem('vtt.display.v1'))localStorage.setItem('vtt.display.v1',"+json.dumps(json.dumps({'language':lang,'theme':theme}))+")")
            page=context.new_page();page.set_default_timeout(30000)
            page.on('pageerror',lambda e:errors.append(str(e)))
            pages[role]=(page,lang,engine,width)

        def profile(role):
            page,lang,_,_=pages[role];page.goto(origin+'/dashboard')
            page.locator('.vtt-account-profile:visible').first.click()
            dialog=page.locator('#reviewOwnProfile')
            expect(dialog.locator('h2')).to_have_text(fixture['users'][role]['username'])
            panel=dialog.locator('.cq-panel');expect(panel.locator('.cq-title')).to_have_text(text('Kampagnenlimit',lang))
            return page,panel,lang

        def request(desired,note):
            page,panel,lang=profile('dm')
            panel.get_by_label(text('Gewünschtes Gesamtlimit',lang),exact=True).fill(str(desired))
            panel.get_by_label(text('Begründung',lang),exact=True).fill(note)
            data=post(page,'/api/campaign-quota/requests',lambda:panel.get_by_role('button',name=text('Anfrage senden',lang),exact=True).click(),'dm')
            assert data['quota_changed'] is False
            expect(panel.locator('.cq-history')).to_contain_text(note)
            expect(panel.get_by_role('button',name=text('Anfrage zurückziehen',lang),exact=True)).to_be_visible()
            return data['request']['id'],page,panel,lang

        first,page,panel,lang=request(7,reason);current(panel,4)
        assert panel.locator('img').count()==0 and page.evaluate('window.cqInjected') is None
        withdrawn=post(page,f'/api/campaign-quota/requests/{first}/cancel',lambda:panel.get_by_role('button',name=text('Anfrage zurückziehen',lang),exact=True).click(),'dm')
        assert withdrawn['request']['id']==first and withdrawn['quota_changed'] is False
        expect(panel.get_by_label(text('Gewünschtes Gesamtlimit',lang),exact=True)).to_be_visible();current(panel,4)
        main,page,panel,lang=request(7,main_reason);current(panel,4)
        proof['journeys'].append({'role':'dm','engine':'chromium','width':1440,'language':'de','normal_profile_entry':True,'request_then_cancel_without_increase':True,'second_request_without_increase':True,'authored_reason_literal':True,'request_ids':[first,main]});save()

        page,panel,lang=profile('player');current(panel,4)
        expect(panel).to_contain_text(text('Anfragen sind nur für Konten möglich, die Kampagnen erstellen dürfen.',lang))
        expect(panel.locator('form,button')).to_have_count(0)
        expect(panel).not_to_contain_text(main_reason)
        page.screenshot(path=str(root/'quota-player-firefox-390-en.png'))
        proof['journeys'].append({'role':'player','engine':'firefox','width':390,'language':'en','normal_profile_entry':True,'truthful_ineligibility_without_review_controls':True,'other_request_not_exposed':True});save()

        page,panel,lang=profile('owner')
        panel.get_by_role('button',name=text('Anfragen prüfen',lang),exact=True).click()
        entry=panel.locator('.cq-review .cq-item').filter(has_text=fixture['users']['dm']['username']).filter(has_text=main_reason)
        expect(entry).to_have_count(1)
        total=entry.get_by_label(text('Neues Gesamtlimit (manuell festlegen)',lang),exact=True)
        expect(total).to_have_attribute('id',f"cqDecision{fixture['users']['owner']['id']}-{main}-total")
        expect(total).to_have_value('');expect(entry.locator('.cq-confirm')).to_be_hidden()
        total.fill('9');entry.get_by_label(text('Notiz (optional, für die anfragende Person sichtbar)',lang),exact=True).fill(owner_note)
        entry.get_by_role('button',name=text('Genehmigen …',lang),exact=True).click()
        expect(entry.locator('.cq-confirm-text')).to_contain_text('from 4 to 9')
        decision=post(page,f'/api/campaign-quota/review-requests/{main}/decision',lambda:entry.get_by_role('button',name=text('Gesamtlimit bestätigen',lang),exact=True).click(),'owner')
        assert decision['id']==main and decision['requester']['id']==fixture['users']['dm']['id'] and decision['approved_total']==9 and decision['quota_changed'] is True
        proof['journeys'].append({'role':'owner','engine':'firefox','width':390,'language':'en','normal_profile_review_entry':True,'only_manifest_owned_request_decided':True,'explicit_manual_total':9,'requested_total':7,'old_total':4,'literal_review_note':True});save()

        page,panel,lang=profile('dm');current(panel,9)
        expect(panel.locator('.cq-history')).to_contain_text(owner_note)
        expect(panel.locator('.cq-history')).to_contain_text(text('Anfrage genehmigt',lang))
        last,page,panel,lang=request(12,reject_reason);current(panel,9)
        page,panel,lang=profile('admin')
        panel.get_by_role('button',name=text('Anfragen prüfen',lang),exact=True).click()
        entry=panel.locator('.cq-review .cq-item').filter(has_text=fixture['users']['dm']['username']).filter(has_text=reject_reason)
        expect(entry).to_have_count(1)
        total=entry.get_by_label(text('Neues Gesamtlimit (manuell festlegen)',lang),exact=True)
        expect(total).to_have_attribute('id',f"cqDecision{fixture['users']['admin']['id']}-{last}-total")
        entry.get_by_label(text('Notiz (optional, für die anfragende Person sichtbar)',lang),exact=True).fill(admin_note)
        decision=post(page,f'/api/campaign-quota/review-requests/{last}/decision',lambda:entry.get_by_role('button',name=text('Ablehnen',lang),exact=True).click(),'admin')
        assert decision['id']==last and decision['requester']['id']==fixture['users']['dm']['id'] and decision['status']=='rejected' and decision['quota_changed'] is False and decision['live']['current']==9
        proof['journeys'].append({'role':'admin','engine':'chromium','width':1440,'language':'de','normal_profile_review_entry':True,'only_manifest_owned_request_decided':True,'explicit_rejection_without_increase':True});save()

        page,panel,lang=profile('dm');current(panel,9)
        for value in [owner_note,admin_note,text('Anfrage genehmigt',lang),text('Anfrage abgelehnt',lang),text('Anfrage zurückgezogen',lang)]:expect(panel.locator('.cq-history')).to_contain_text(value)
        assert panel.locator('img').count()==0 and page.evaluate('window.cqInjected') is None
        page.reload();page.locator('.vtt-account-profile:visible').first.click()
        panel=page.locator('#reviewOwnProfile .cq-panel');current(panel,9)
        expect(panel.locator('.cq-history')).to_contain_text(admin_note)
        page.screenshot(path=str(root/'quota-dm-chromium-1440-de.png'))
        proof['requester_reload_status_notes']=True;proof['only_synthetic_quota_adjusted']={'user_id':fixture['users']['dm']['id'],'from':4,'to':9};proof['request_ids']=[first,main,last]
        assert not errors,errors
        proof['browser_errors']=errors;proof['status']='pass';save()
    except Exception as e:
        proof.update(status='failed',error=str(e));save();raise
    finally:
        for context in contexts:context.close()
        for browser in browsers.values():browser.close()
