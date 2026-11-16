"""Authenticated synthetic accounts, normal campaign navigation, real production APIs.
Beyond20 is exercised at its DOM contract; this does not install the extension.
"""
import base64, json, os
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect

ROOT=Path(os.environ.get('PROOF_ROOT','/proof'))
fixture=json.loads((ROOT/'private-live-credentials.json').read_text())
origin='https://vtt.roll-drauf.de'
proof={'status':'running','journeys':[],'extension_test':'normalized DOM contract; installed extension NOT_RUN'}
def passed(name, details=None):
    proof['journeys'].append({'name':name,'status':'pass',**({'details':details} if details else {})})
    (ROOT/'live.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
def close_windows(page):
    for _ in range(12):
        rows=page.locator('.play-window:visible')
        if not rows.count():return
        id_=rows.evaluate_all('rows=>rows.sort((a,b)=>Number(b.style.zIndex)-Number(a.style.zIndex))[0].id')
        page.locator('#'+id_+' .play-window-head button').click()
def open_window(page,id_):
    if not page.locator('#window-'+id_).is_visible():page.locator('#dock-'+id_).click()
def point(page,x,y):
    box=page.locator('#mapWorld').bounding_box()
    width=float(page.locator('#mapWorld').get_attribute('data-map-width'))
    return box['x']+x*box['width']/width,box['y']+y*box['width']/width

def bootstrap(page):
    return page.evaluate('''async ({c,s})=>Auth.makeAuthRequest(`/api/play/campaigns/${c}/sessions/${s}/bootstrap`)''',{'c':fixture['campaign_id'],'s':fixture['session_id']})
def token_value(page,id_):
    return next(t for t in bootstrap(page)['state_payload']['tokens'] if t['id']==id_)

def launcher_metrics(page):
    values=page.locator('body > .left-toolbar').evaluate('''e=>({height:e.getBoundingClientRect().height,
        buttons:[...e.querySelectorAll('button')].map(b=>({id:b.id,hidden:b.hidden,
            display:getComputedStyle(b).display,width:b.getBoundingClientRect().width,
            height:b.getBoundingClientRect().height}))})''')
    assert values['height']<=90,values
    expect(page.locator('.left-toolbar [data-tool="select"] .tool-label')).to_be_visible()
    for button in values['buttons']:
        if button['hidden']:assert button['display']=='none',button
        elif button['display']!='none':assert button['width']<150 and button['height']<=64,button
    return {'height':values['height'],'buttons':len(values['buttons'])}

with sync_playwright() as p:
    dm_browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    player_browser=p.firefox.launch(headless=True)
    contexts=[];errors=[]
    def context(browser,kind,width=1440):
        result=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        user=fixture['users'][kind]
        result.add_cookies([{'name':'access_token_cookie','value':user['token'],'url':origin,'httpOnly':True,'secure':True},
                            {'name':'csrf_access_token','value':user['csrf'],'url':origin,'secure':True}])
        contexts.append(result);return result
    def enter(ctx,kind,owner_player=False):
        page=ctx.new_page();page.set_default_timeout(25000);page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(origin+f"/campaigns?campaign_id={fixture['campaign_id']}")
        action='open-session-player' if owner_player else 'open-session-dm' if kind=='dm' else 'open-session'
        page.locator('[data-hub-action="'+action+'"]').first.click()
        expect(page.locator('body')).to_have_attribute('data-table-seat','player' if owner_player else kind)
        expect(page.locator('#presenceRoster')).to_contain_text(fixture['users'][kind]['username'])
        assert f"session_id={fixture['session_id']}" in page.url,page.url
        return page
    dm_context=context(dm_browser,'dm');player_context=context(player_browser,'player')
    dm=enter(dm_context,'dm');player=enter(player_context,'player')
    launchers={'dm':launcher_metrics(dm),'player':launcher_metrics(player)}
    expect(player.locator('#presenceRoster')).to_contain_text(fixture['users']['dm']['username'])
    expect(player.locator('#tokenLayersWidget,#btnInitStack')).to_have_count(0)
    assert not player.evaluate('Boolean(window.PlayDMSurface)')
    assert 'QA_PRIVATE_SENTINEL' not in json.dumps(bootstrap(player))
    passed('DM and Firefox Player enter through campaign hub; role/data composition and compact labelled launcher',launchers)

    owner_player=enter(dm_context,'dm',True)
    negative=owner_player.evaluate('''async ({c,s})=>{
      const response=await fetch(`/api/play/campaigns/${c}/sessions/${s}/surface`,{headers:Auth.buildHeaders('GET',false),credentials:'include'});
      return {surface:response.status,dm:!!window.PlayDMSurface};
    }''',{'c':fixture['campaign_id'],'s':fixture['session_id']})
    assert negative=={'surface':403,'dm':False},negative
    owner_player.reload();expect(owner_player.locator('body')).to_have_attribute('data-table-seat','player')
    assert 'QA_PRIVATE_SENTINEL' not in json.dumps(bootstrap(owner_player));owner_player.close()
    passed('Owner-as-Player cannot mount DM controls or receive secret data, including reload',negative)

    player.locator('#btnBeyond20Setup').click()
    frame=player.frame_locator('#window-beyond20 iframe')
    expect(frame.locator('#beyond20CopyBtn')).to_be_visible();expect(frame.locator('ol').first.locator('li')).to_have_count(3)
    close_windows(player)
    player.locator('#dock-tokenWidget').click()
    png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aQ3sAAAAASUVORK5CYII=')
    with player.expect_file_chooser() as chooser:player.locator('#btnTokenUpload').click()
    chooser.value.set_files({'name':'session-token.png','mimeType':'image/png','buffer':png})
    expect(player.locator('#tokenUploadStatus')).to_contain_text('Tokenbild geladen')
    player.locator('#btnPlaceNewToken').click();player.mouse.click(*point(player,700,490))
    expect(player.locator('#tokenCreatePanel')).to_be_visible();player.locator('#tokenCreateName').fill('QA Reusable Token')
    player.locator('#btnTokenCreateConfirm').click()
    marker=player.locator('.token-marker',has_text='QA Reusable Token');expect(marker).to_be_visible();marker.click()
    player.locator('#btnSaveTokenTemplate').click();expect(player.locator('#tokenLibraryList [data-template-id]')).to_have_count(1)
    template=player.locator('#tokenLibraryList [data-template-id]');template_id=int(template.get_attribute('data-template-id'))
    template.get_by_role('button',name='Bearbeiten',exact=True).click();template.locator('input').first.fill('QA Saved Token')
    template.get_by_role('button',name='Speichern',exact=True).click();expect(template).to_contain_text('QA Saved Token')
    passed('Direct Player menu image upload, placement, personal save and template edit')

    window=player.locator('#window-tokenWidget');head=window.locator('.play-window-head strong').bounding_box()
    player.mouse.move(head['x']+20,head['y']+15);player.mouse.down();player.mouse.move(head['x']+120,head['y']+110,steps=8);player.mouse.up()
    moved=window.bounding_box();window.locator('.play-window-head button').click();player.locator('#dock-tokenWidget').click()
    again=window.bounding_box();assert abs(again['x']-moved['x'])<3 and abs(again['y']-moved['y'])<3,(moved,again)
    player.reload();open_window(player,'tokenWidget');again=window.bounding_box()
    assert abs(again['x']-moved['x'])<3 and abs(again['y']-moved['y'])<3,(moved,again)
    expect(player.locator('#tokenLibraryList')).to_contain_text('QA Saved Token')
    passed('Firefox window movement, close/reopen, reload and persistent token library')
    close_windows(player)

    player.locator(f".token-marker[data-token-id='{fixture['token_id']}']").click()
    with player.expect_file_chooser() as chooser:player.locator('#btnTokenImageSet').click()
    chooser.value.set_files({'name':'linked-hero.png','mimeType':'image/png','buffer':png})
    expect(player.locator('#activityLog')).to_contain_text('Token-Bild gesetzt')
    player.locator('#btnSaveTokenTemplate').click()
    bound_template=player.locator('#tokenLibraryList [data-template-id]').filter(has_text=fixture['character_name'])
    expect(bound_template).to_have_count(1)
    bound_template_id=int(bound_template.get_attribute('data-template-id'))
    with player.expect_response(lambda response:'/initiative-roll' in response.url and response.request.method=='POST') as response:
        player.locator('#btnSelectedInitiative').click()
    rolled=response.value.json()['total'];assert token_value(player,fixture['token_id'])['initiative']==rolled
    open_window(dm,'turnOrderWidget');dm.locator('#btnStartCombat').click();expect(dm.locator('#btnNextTurn')).to_be_visible()
    assert token_value(player,fixture['token_id'])['initiative']==rolled
    player.evaluate('''() => document.dispatchEvent(new CustomEvent('Beyond20_RenderedRoll',{detail:[{
      title:'Initiative',character:'QA actor',request:{type:'initiative',character:{name:'QA actor'}},
      attack_rolls:[{formula:'1d20+3',total:2,discarded:true,parts:[]},{formula:'1d20+3',total:18,parts:[]}]
    }]}))''')
    expect(player.locator('#beyond20Status')).to_contain_text('Wurf an dieser Sitzung angekommen')
    open_window(player,'turnOrderWidget');expect(player.locator(f"#turnOrderList [data-token-id='{fixture['token_id']}']")).to_contain_text('18')
    expect(dm.locator(f"#turnOrderList [data-token-id='{fixture['token_id']}']")).to_contain_text('18')
    assert token_value(player,fixture['token_id'])['initiative']==18
    denied=player.evaluate('''async ({c,s,t}) => (await fetch(`/api/play/campaigns/${c}/sessions/${s}/tokens/${t}/initiative-roll`,{
      method:'POST',credentials:'include',headers:Auth.buildHeaders('POST',true),body:JSON.stringify({request_id:crypto.randomUUID()})})).status''',
      {'c':fixture['campaign_id'],'s':fixture['session_id'],'t':fixture['secret_token_id']})
    assert denied==403,denied
    passed('Native Player initiative, preserved combat start, kept Beyond20 result and two-client order; foreign token denied')

    event_id=str(uuid4())
    player.evaluate('''id=>{const roll={event_id:id,source:'beyond20',title:'Replay probe',roll_type:'initiative',formula:'1d20+3',total:16};RollDraufTable.sendExternalRoll(roll);RollDraufTable.sendExternalRoll(roll);}''',event_id)
    expect(player.locator('#chatLog')).to_contain_text('Replay probe')
    assert sum('Replay probe' in row['message'] for row in bootstrap(player).get('chat_history',[]))==1
    totals=player.evaluate('''async({c,s,t})=>Promise.all([1,2].map(()=>Auth.makeAuthRequest(`/api/play/campaigns/${c}/sessions/${s}/tokens/${t}/initiative-roll`,'POST',{request_id:crypto.randomUUID()})))''',
                          {'c':fixture['campaign_id'],'s':fixture['session_id'],'t':fixture['token_id']})
    assert token_value(player,fixture['token_id'])['initiative'] in [r['total'] for r in totals]
    passed('External replay deduplicated and concurrent native PostgreSQL initiative requests serialized')
    dm.locator('#btnEndCombat').click();close_windows(dm);close_windows(player)

    player.locator('#btnChatToggle').click();player.locator('#chatInput').fill('QA same campaign room')
    player.locator('#btnSendChat').click();expect(player.locator('#campaignRoomLog')).to_contain_text('QA same campaign room')
    dm.locator('#btnChatToggle').click();expect(dm.locator('#campaignRoomLog')).to_contain_text('QA same campaign room',timeout=15000)
    with player.expect_popup() as popup:player.locator('#campaignConversationLink').click()
    conversation=popup.value;conversation.set_default_timeout(25000)
    expect(conversation.locator('#conversationHistory')).to_contain_text('QA same campaign room')
    conversation.locator('#privateMessage').fill('QA reply from Conversations');conversation.locator('#privateSend').click()
    expect(player.locator('#campaignRoomLog')).to_contain_text('QA reply from Conversations',timeout=15000)
    expect(dm.locator('#campaignRoomLog')).to_contain_text('QA reply from Conversations',timeout=15000)
    results=conversation.evaluate('''async c=>{const body={content:'QA concurrent campaign message',client_event_id:crypto.randomUUID()};return Promise.all([1,2].map(()=>Auth.makeAuthRequest(`/api/campaign-rooms/${c}`,'POST',body)));}''',fixture['campaign_id'])
    assert results[0]['message']['id']==results[1]['message']['id']
    passed('Campaign room is the same in DM table, Player table and Conversations; concurrent send replay is idempotent')
    conversation.close();close_windows(dm);close_windows(player)

    open_window(dm,'layersWidget')
    target=dm.locator('#layerList .layer-row').filter(has=dm.locator('input[value="Zweite Abnahmekarte"]'))
    target.locator('[data-act=activate]').click()
    expect(player.locator('.token-marker')).to_have_count(0)
    open_window(player,'tokenWidget');template=player.locator(f'[data-template-id="{bound_template_id}"]')
    template.get_by_role('button',name='Platzieren',exact=True).click();player.mouse.click(*point(player,700,490))
    expect(player.locator('#tokenCreateName')).to_have_value(fixture['character_name'])
    expect(player.locator('#tokenCreateCharacter')).to_have_value(str(fixture['character_id']))
    player.locator('#btnTokenCreateConfirm').click()
    expect(player.locator('.token-marker',has_text=fixture['character_name'])).to_be_visible()
    new_token=next(t for t in bootstrap(player)['state_payload']['tokens'] if t['name']==fixture['character_name'] and t['map_id']==fixture['second_map_id'])
    assert new_token['map_id']==fixture['second_map_id'] and new_token['initiative'] is None
    assert new_token['metadata_json'].get('image_url') and new_token['character_id']==fixture['character_id']
    passed('Template placed through the normal UI on a different active map, with saved image and no stale initiative')
    close_windows(dm);close_windows(player)
    dm.set_viewport_size({'width':390,'height':844});open_window(dm,'tokenWidget');expect(dm.locator('#btnTokenUpload')).to_be_visible()
    mobile_launcher=launcher_metrics(dm)
    assert dm.evaluate('document.documentElement.scrollWidth')<=390
    dm.screenshot(path=str(ROOT/'live-dm-mobile.png'));player.screenshot(path=str(ROOT/'live-player-map.png'))
    passed('390px DM token window remains usable; compact labelled launcher and no horizontal overflow',mobile_launcher)
    assert not errors,errors
    proof.update(status='pass',page_errors=errors,fixture_campaign_id=fixture['campaign_id'])
    (ROOT/'live.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    for ctx in contexts:ctx.close()
    dm_browser.close();player_browser.close()
print(json.dumps({'status':'pass','journeys':len(proof['journeys'])}))
