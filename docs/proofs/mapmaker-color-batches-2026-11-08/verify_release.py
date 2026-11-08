import sys,json,pathlib,os,subprocess,time,io,zipfile,hashlib,urllib.request
from PIL import Image
from playwright.sync_api import sync_playwright,expect
scratch=pathlib.Path('/tmp/mapmaker-color-batches-20261108');batch=int(sys.argv[1]);state=json.loads((scratch/f'release-{batch}/release-state.json').read_text());commit=state['sourceCommit'];origin='https://vtt.roll-drauf.de';proof=scratch/f'release-{batch}'
def committed(path):return subprocess.check_output(['git','show',commit+':vtt/static/mapmaker/'+path],cwd='/home/admin/projects/roll-drauf-vtt')
catalog=json.loads(committed('assets/packs.json'));new=json.loads(committed('assets/color-source-lock.json'))['sources'];source_by={p['id']:p for p in new};states=json.loads((scratch/'live-contexts.json').read_text());results=[]
with sync_playwright() as p:
 env=dict(os.environ);env['LD_LIBRARY_PATH']='/tmp/roll-drauf-mapmaker/browser-libs/usr/lib/x86_64-linux-gnu';browser=p.chromium.launch(headless=True,executable_path='/home/admin/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell',args=['--no-sandbox'],env=env)
 for role,width in [('dm',1440),('player',390)]:
  ctx=browser.new_context(storage_state=states[role],viewport={'width':width,'height':900 if width>600 else 844},accept_downloads=True);ctx.add_init_script("window.__csp=[];document.addEventListener('securitypolicyviolation',e=>window.__csp.push(e.violatedDirective+' '+e.blockedURI));");page=ctx.new_page();page.set_default_timeout(60000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  def show_palette():
   if page.locator('#app').get_attribute('data-sheet')!='open' or page.locator('#tab-tool').get_attribute('aria-selected')!='true':page.locator('#tab-tool').click()
  def hide_palette():
   if page.locator('#app').get_attribute('data-sheet')=='open' and page.locator('#tab-tool').get_attribute('aria-selected')=='true':page.locator('#tab-tool').click()
  assert page.goto(origin+'/dashboard' ,wait_until='domcontentloaded').status==200
  page.get_by_role('navigation',name='VTT-Hauptnavigation').get_by_role('link',name='Karten',exact=True).click();page.wait_for_selector('#app[data-state=ready]');ready=round(page.evaluate('performance.now()'))
  assert page.url==origin+'/static/mapmaker/index.html';assert page.locator('#stampPack option').count()==len(catalog['packs'])+1 # empty all option; builtin replaces texture-only pack
  if batch>=2:
   stats=page.evaluate('window.rdMapmaker.catalogue()');assert not stats['errors'];expected={pack['id']:len(json.loads(committed('assets/'+pack['manifest']))['stamps']) for pack in catalog['packs']};assert all(stats['packs'].get(k,0)==n for k,n in expected.items())
   assert stats['total']==sum(expected.values())+6
  else:stats=None
  page.locator('.mm-tool[data-tool="stamp"]').click()
  if width<600:show_palette()
  chosen=[]
  packs=[s for s in new if s['batch']==batch]
  if batch==4:packs.extend(s for s in new if s['id'] in ['2dpixx-mountain','2dpixx-village'])
  # Real UI for every newly added pack, plus both full LPC houses and a figure frame.
  for index,s in enumerate(packs):
   m=json.loads(committed('assets/'+s['id']+'/manifest.json'))
   if s['id']=='lpc-revised':entries=[next(e for e in m['stamps'] if e['group']=='Fertige Häuser'),next(e for e in m['stamps'] if e['group']=='Figuren & Kleidung')]
   elif s['id']=='green-village':entries=[next(e for e in m['stamps'] if e['group']=='Fertige Häuser')]
   else:entries=[next(e for e in m['stamps'] if e['group']!='Referenzen & Szenen')]
   for entry in entries:
    page.locator('#stampPack').select_option(s['id']);page.locator('#stampSearch').fill(entry['label']);button=page.locator('.mm-stamp[data-asset="'+entry['id']+'"]');button.click()
    crop=None
    if entry['sheet']:
     expect(page.locator('#sheetDialog')).to_be_visible();
     with Image.open(io.BytesIO(committed('assets/'+s['id']+'/'+entry['file']))) as im:
      alpha=im.convert('RGBA').getchannel('A');bounds=alpha.getbbox()
     assert bounds
     if batch==4:
      initial={k:int(page.locator('#sheet'+k.upper()).input_value()) for k in ('x','y','w','h')}
      assert alpha.crop((initial['x'],initial['y'],initial['x']+initial['w'],initial['y']+initial['h'])).getbbox(),('Invisible initial crop',entry['id'],initial)
     if s['id']=='2dpixx-village':crop={'x':238,'y':0,'w':328,'h':321}
     elif entry['grid']>1:
      grid=entry['grid'];cells=((x,y,min(grid,entry['w']-x),min(grid,entry['h']-y)) for y in range(0,entry['h'],grid) for x in range(0,entry['w'],grid));x,y,w,h=next(cell for cell in cells if alpha.crop((cell[0],cell[1],cell[0]+cell[2],cell[1]+cell[3])).getbbox());crop={'x':x,'y':y,'w':w,'h':h}
     else:crop={'x':bounds[0],'y':bounds[1],'w':bounds[2]-bounds[0],'h':bounds[3]-bounds[1]}

     for k,v in crop.items():page.locator('#sheet'+k.upper()).fill(str(v))
     page.screenshot(path=str(proof/f'live-{role}-{s["id"]}-sheet.png'),mask=[page.locator('.vtt-account-memo')]);page.locator('#sheetUse').click()
    if width<600:hide_palette()
    before=page.evaluate('window.rdMapmaker.summary().stamps');pixel_before=page.evaluate('window.rdMapmaker.sampleRegion(1370,160,260,260)');at=page.evaluate('window.rdMapmaker.docToClient(1500, 290)');page.mouse.click(at['x'],at['y']);assert page.evaluate('window.rdMapmaker.summary().stamps')==before+1
    assert pixel_before!=page.evaluate('window.rdMapmaker.sampleRegion(1370,160,260,260)'),entry['id']
    item=page.evaluate('(id)=>window.rdMapmaker.summary().items.filter(i=>i.asset===id).at(-1)',entry['id']);assert item is not None
    if crop:assert item['crop']==crop
    chosen.append({'asset':entry['id'],'crop':crop})
    if width<600:show_palette()
  with page.expect_download() as d:page.locator('#fileMenuBtn').click();page.locator('#saveBtn').click()
  target=proof/f'live-{role}.rdmap.json';d.value.save_as(target)
  page.locator('#fileInput').set_input_files(target);expect(page.locator('#toast')).to_contain_text('geladen')
  page.locator('#fileMenuBtn').click();page.locator('#exportBtn').click()
  with page.expect_download(timeout=120000) as d:page.locator('#exportBundle').click()
  target_zip=proof/f'live-{role}.zip';d.value.save_as(target_zip)
  with zipfile.ZipFile(target_zip) as z:
   credits=z.read('CREDITS.txt').decode();png=z.read(next(n for n in z.namelist() if n.endswith('.png')))
   with Image.open(io.BytesIO(png)) as image:image.load();assert image.info['Credits']==credits
   for s in packs:assert s['author'].split(',')[0] in credits
  page.screenshot(path=str(proof/f'live-{role}-map.png'),mask=[page.locator('.vtt-account-memo')])
  if width<600:
   page.locator('.mm-tool[data-tool="stamp"]').click();show_palette();link=page.get_by_role('link',name='Künstler, Quellen & Lizenzen')
  else:link=page.get_by_role('link',name='Künstler & Credits',exact=True)
  with page.expect_popup() as pop:link.click()
  credits_page=pop.value;credits_page.wait_for_load_state();assert credits_page.locator('article').count()==len(catalog['packs'])+1;assert credits_page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  assert not errors,errors;assert not page.evaluate('window.__csp');assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  results.append(dict(role=role,width=width,entry='Dashboard → Karten → Stempel → Paket → Motiv/Ausschnitt → Karte',readyMs=ready,catalogue=stats,placed=chosen,saveReimport=True,pngCredits=True,zipCredits=True,creditsPage=True,pageErrors=errors,cspViolations=[]));ctx.close()
 browser.close()
checks=[]
for path in ['index.html','js/app.js','js/stamps.js','js/credits.js','assets/packs.json','credits.html']:
 with urllib.request.urlopen(origin+'/static/mapmaker/'+path,timeout=60) as r:data=r.read()
 assert data==committed(path),path;checks.append(path)
(proof/'live-verification.json').write_text(json.dumps(dict(batch=batch,sourceCommit=commit,verifiedAt=time.strftime('%Y-%m-%dT%H:%M:%S%z'),journeys=results,httpsHashes=checks),indent=2)+'\n')
print(json.dumps(dict(batch=batch,journeys=[{k:v for k,v in r.items() if k!='catalogue'} for r in results]),indent=2))
