import pathlib,json,base64,os,time,threading,functools
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
root=pathlib.Path('/home/admin/projects/roll-drauf-vtt/vtt/static/mapmaker');scratch=pathlib.Path('/tmp/mapmaker-color-batches-20261108');catalog=json.loads((root/'assets/packs.json').read_text())['packs'];seen={};logical=0
for pack in catalog:
 m=json.loads((root/'assets'/pack['manifest']).read_text())
 for e in m['stamps']:
  logical+=1;key=e['sha256']
  if key not in seen:seen[key]=(pack['id'],e)
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(root)));threading.Thread(target=server.serve_forever,daemon=True).start();start=time.time();failures=[];checked=0
with sync_playwright() as p:
 env=dict(os.environ);env['LD_LIBRARY_PATH']='/tmp/roll-drauf-mapmaker/browser-libs/usr/lib/x86_64-linux-gnu';browser=p.chromium.launch(headless=True,executable_path='/home/admin/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell',args=['--no-sandbox'],env=env);page=browser.new_page();page.goto(f'http://127.0.0.1:{server.server_port}/credits.html');cdp=page.context.new_cdp_session(page);entries=list(seen.values())
 for offset in range(0,len(entries),64):
  batch=[dict(id=e['id'],w=e['w'],h=e['h'],pixelArt=e.get('pixelArt',False),png=base64.b64encode((root/'assets'/pack/e['file']).read_bytes()).decode()) for pack,e in entries[offset:offset+64]]
  output=page.evaluate('''async (batch) => {
      const {drawStampImage,stampExtent}=await import('./js/stamps.js');
      const canvas=document.createElement('canvas');canvas.width=256;canvas.height=256;const ctx=canvas.getContext('2d',{willReadFrequently:true});
      const failures=[];
      for(const entry of batch) {
          try {
              const image=new Image();image.src='data:image/png;base64,'+entry.png;await image.decode();
              if(image.naturalWidth!==entry.w || image.naturalHeight!==entry.h) throw new Error('Dimension mismatch');
              const stamp={...entry,image};const ext=stampExtent(stamp,256);ctx.clearRect(0,0,256,256);
              drawStampImage(ctx,stamp,null,0,0,ext.w,ext.h);
              const pixels=ctx.getImageData(0,0,256,256).data;let visible=false;
              for(let i=3;i<pixels.length;i+=4) if(pixels[i]>0){visible=true;break;}
              if(!visible) throw new Error('No visible rendered pixels');
              const crop={x:entry.w-1,y:entry.h-1,w:1,h:1};drawStampImage(ctx,stamp,crop,0,0,16,16);
              image.removeAttribute('src');
          }catch(error){failures.push({id:entry.id,error:String(error)});}
      }
      canvas.width=0;canvas.height=0;return failures;
  }''',batch)
  failures.extend(output);checked+=len(batch)
  if offset%3200==0:print('Browser decoded/rendered',checked,'of',len(entries),'failures',len(failures),flush=True);cdp.send('HeapProfiler.collectGarbage')
 browser.close()
server.shutdown();result=dict(logicalStampEntries=logical,uniquePngHashes=checked,fullImagesDrawn=checked,edgeCropsDrawn=checked,failures=failures,elapsedSeconds=round(time.time()-start,2),method='All distinct catalogue PNG bytes decoded by Chromium Image.decode, passed through production stampExtent/drawStampImage, nontransparent output verified, then bottom-right 1x1 crop drawn. Source duplicates share identical SHA256; every logical ID separately covered by placement/import validation.');(scratch/'all-pixels-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert not failures
