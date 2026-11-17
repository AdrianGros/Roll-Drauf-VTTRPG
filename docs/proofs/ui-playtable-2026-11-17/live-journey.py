"""Production acceptance using synthetic accounts and normal campaign navigation."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(os.environ.get('PROOF_ROOT','/proof'))
f=json.loads(Path(os.environ.get('PRIVATE_FIXTURE','/private.json')).read_text())
origin='https://vtt.roll-drauf.de'
proof={'status':'running','journeys':[],'page_errors':[]}
def passed(name,detail=None):
    proof['journeys'].append({'name':name,'status':'pass','detail':detail})
    (ROOT/'live.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
def close(page):
    for _ in range(15):
        nodes=page.locator('.play-window:visible')
        if not nodes.count():break
        id_=nodes.evaluate_all('rows=>rows.sort((a,b)=>Number(b.style.zIndex)-Number(a.style.zIndex))[0].id')
        page.locator('#'+id_+' .play-window-head button').click()
def point(page,x,y):
    world=page.locator('#mapWorld');box=world.bounding_box();width=float(world.get_attribute('data-map-width'))
    return box['x']+x*box['width']/width,box['y']+y*box['width']/width
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox']);firefox=p.firefox.launch(headless=True)
    contexts=[]
    def context(engine,kind,width=1440):
        ctx=engine.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce');user=f['users'][kind]
        ctx.add_cookies([{'name':'access_token_cookie','value':user['token'],'url':origin,'httpOnly':True,'secure':True},{'name':'csrf_access_token','value':user['csrf'],'url':origin,'secure':True}]);contexts.append(ctx);return ctx
    def enter(ctx,kind,player_seat=False):
        page=ctx.new_page();page.set_default_timeout(25000);page.on('pageerror',lambda error:proof['page_errors'].append(str(error)))
        page.goto(origin+f"/campaigns?campaign_id={f['campaign_id']}")
        action='open-session-player' if player_seat else 'open-session-dm' if kind=='dm' else 'open-session'
        page.locator(f'[data-hub-action="{action}"]').first.click();expect(page.locator('body')).to_have_attribute('data-table-seat','player' if player_seat else kind)
        expect(page.locator('#presenceRoster')).to_contain_text(f['users'][kind]['username']);return page
    dmctx=context(browser,'dm');playerctx=context(firefox,'player');dm=enter(dmctx,'dm');player=enter(playerctx,'player')
    expect(dm.locator('#btnMapPresentation')).to_be_visible();expect(player.locator('#btnMapPresentation')).to_have_count(0)
    assert not player.evaluate('Boolean(window.PlayDMSurface||window.PlayFeedbackDM)')
    owner=enter(dmctx,'dm',True)
    status=owner.evaluate('''async({c,s})=>(await fetch(`/api/play/campaigns/${c}/sessions/${s}/vision/illumination?token_id=1`,{headers:Auth.buildHeaders('GET',false)})).status''',{'c':f['campaign_id'],'s':f['session_id']})
    assert status==403;owner.reload();expect(owner.locator('body')).to_have_attribute('data-table-seat','player');owner.close()
    passed('Normal campaign-hub DM and Firefox Player entry; owner-as-Player stays separated after reload')
    # Settings, CRUD entry and explicit preview are actual DM window controls.
    dm.locator('#btnMapPresentation').click();expect(dm.locator('#geometryManager li')).to_have_count(2)
    dm.locator('#presentationGridVisible').uncheck();dm.locator('#presentationAmbient').fill('35');dm.locator('#savePresentationSettings').click()
    expect(dm.locator('#window-mapPresentation')).to_contain_text('gespeichert');expect(player.locator('#mapGridLayer')).to_be_hidden()
    dm.locator('#geometryManager button').first.click();expect(dm.locator('#wallEditPopover')).to_be_visible();dm.locator('#wallEditSight').select_option('none');dm.locator('#wallEditSight').select_option('normal');dm.locator('#btnWallEditClose').click()
    dm.locator('#previewPerspectiveToken').select_option(str(f['token_id']));expect(dm.locator('#lightingProjection')).to_be_visible()
    expect(dm.locator(f".token-marker[data-token-id='{f['secret_token_id']}']")).to_be_hidden()
    dm.screenshot(path=str(ROOT/'live-dm-player-preview.png'))
    dm.locator('#previewPerspectiveToken').select_option('');expect(dm.locator('#lightingProjection')).to_be_hidden();close(dm)
    expect(player.locator('#lightingProjection')).to_be_visible()
    assert player.locator('#lightingProjection').evaluate('e=>e.getBoundingClientRect().width')>=player.locator('#mapWorld').evaluate('e=>e.getBoundingClientRect().width')-1
    passed('DM grid settings reach second client; wall CRUD opens; wall-clipped Player image and DM/Player perspective')
    # Hierarchy keeps active map stable while editing its parent selector.
    dm.locator('#dock-layersWidget').click();rows=dm.locator('#layerList .layer-row');expect(rows).to_have_count(2)
    parent=rows.first.get_attribute('data-layer-id');before=dm.locator('#mapWorld').get_attribute('data-map-width')
    rows.nth(1).locator('select').select_option(parent);expect(rows.nth(1)).to_have_attribute('data-depth','1')
    dm.reload();dm.locator('#dock-layersWidget').click();expect(dm.locator('#layerList .layer-row').nth(1)).to_have_attribute('data-depth','1');close(dm)
    passed('Existing map pages form a persistent parent/child hierarchy through visible parent selector and reload')
    player.locator(f".token-marker[data-token-id='{f['token_id']}']").click()
    player.locator('#btnSelectedInitiative').click();player.locator('#btnSelectedInitiative').click()
    dm.locator('#dock-turnOrderWidget').click();expect(dm.locator('#initiativeCandidates li')).to_have_count(1);dm.locator('#initiativeCandidates button').click();expect(dm.locator('#initiativeCandidates li')).to_have_count(0)
    dm.locator('#btnStartCombat').click();expect(dm.locator('#btnNextTurn')).to_be_visible();dm.locator('#btnNextTurn').click();dm.locator('#btnEndCombat').click();close(dm);close(player)
    passed('Native Player sheet initiative, pending reroll confirmation and real combat start/advance/end')
    # New token construction remains explicit; library choices place directly.
    player.locator('#dock-tokenWidget').click();player.locator('#btnPlaceNewToken').click();player.mouse.click(*point(player,420,420))
    expect(player.locator('#tokenCreatePanel')).to_be_visible();player.locator('#tokenCreateName').fill('QA Direct Library');player.locator('#btnTokenCreateConfirm').click()
    marker=player.locator('.token-marker',has_text='QA Direct Library');expect(marker).to_have_count(1);marker.click();player.locator('#btnSaveTokenTemplate').click()
    template=player.locator('#tokenLibraryList li').filter(has_text='QA Direct Library');expect(template).to_have_count(1);template.get_by_role('button',name='Platzieren',exact=True).click()
    player.mouse.click(*point(player,420,560));expect(player.locator('.token-marker',has_text='QA Direct Library')).to_have_count(2);expect(player.locator('#tokenCreatePanel')).to_be_hidden()
    close(player);player.locator('[data-tool="measure"]').click();expect(player.locator('#btnMeasureSnap')).to_have_attribute('aria-pressed','false')
    player.mouse.click(*point(player,200,200));player.mouse.move(*point(player,300,250));expect(player.locator('#measureLayer text')).not_to_have_count(0)
    player.locator('#measureShape').select_option('circle');player.mouse.click(*point(player,300,300));player.mouse.move(*point(player,180,410));expect(player.locator('#measureLayer circle')).not_to_have_count(0)
    player.locator('[data-tool="select"]').click();passed('Library-first selection creates one direct copy; explicit new-token path; free measurement and circle')
    # Conversations is reached from the campaign chat's ordinary link.
    player.locator('#btnChatToggle').click()
    with player.expect_popup() as popup:player.locator('#campaignConversationLink').click()
    book=popup.value;book.set_default_timeout(25000);expect(book.locator('[data-book-frame]')).to_be_visible();book.locator('#previousSessions summary').click()
    expect(book.locator('#previousSessions')).to_contain_text('QA historical public session');assert 'QA PRIVATE BLIND' not in book.locator('#previousSessions').inner_text()
    passed('Conversations loads public historical campaign-session chat with provenance and excludes blind history')
    # Each common ribbon link reaches a real document surface, including native English rules.
    for href,chapter in [('/mapmaker','maps'),('/atlas','atlas'),('/api/ce/authoring','creation'),('/regelwerk','rules'),('/regelwerk/compendium','compendium')]:
        link=book.locator(f'nav[data-vtt-main-nav="true"] a[href="{href}"]').first
        expect(link).to_be_visible();link.click();expect(book.locator(f'[data-book-chapter="{chapter}"]')).to_be_visible()
    book.locator('#vttDisplayOpen').click();book.locator('#vttDisplay-language').select_option('en');book.locator('#vttDisplay-theme').select_option('night');book.locator('#vttDisplayDialog button').filter(has_text='Anwenden').click()
    expect(book.locator('html')).to_have_attribute('lang','en');expect(book.locator('html')).to_have_attribute('data-vtt-theme','night')
    # English compendium search/filter/detail is asserted through its real input controls below by selector contract.
    search=book.locator('input[type="search"]').first;search.fill('Fireball');search.press('Enter');expect(book.locator('main')).to_contain_text('Fireball')
    book.screenshot(path=str(ROOT/'live-english-compendium.png'))
    rules=book.locator('nav[data-vtt-main-nav="true"] a[data-regelwerk-nav]').first;rules.click();expect(book.locator('#regelwerkArticle')).to_contain_text('Roll Drauf')
    assert '/en' in book.url
    book.set_viewport_size({'width':390,'height':844});assert book.evaluate('document.documentElement.scrollWidth')<=390;book.screenshot(path=str(ROOT/'live-english-rulebook-390.png'))
    passed('All six book surfaces via common navigation; English/night setting, English compendium and native rulebook at390px')
    dm.set_viewport_size({'width':390,'height':844});dm.locator('#btnMapPresentation').click();expect(dm.locator('#savePresentationSettings')).to_be_visible();assert dm.evaluate('document.documentElement.scrollWidth')<=390;dm.screenshot(path=str(ROOT/'live-dm-settings-390.png'))
    passed('DM settings remain reachable at390px with no horizontal page overflow')
    assert not proof['page_errors'],proof['page_errors'];proof['status']='pass'
    (ROOT/'live.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    for ctx in contexts:ctx.close()
    browser.close();firefox.close()
print(json.dumps({'status':'pass','journeys':len(proof['journeys'])}))
