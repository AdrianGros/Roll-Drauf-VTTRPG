import json
from pathlib import Path
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 browser=p.firefox.launch(headless=True);page=browser.new_page();page.goto('https://vtt.roll-drauf.de/static/mapmaker/index.html')
 result=page.evaluate('''async()=>{
 const {createCanvas}=await import('/static/mapmaker/js/document.js');
 const a=createCanvas(128,128),ctx=a.getContext('2d');ctx.fillStyle='rgba(204,51,51,.35)';ctx.fillRect(10,10,100,100);
 const original=ctx.getImageData(0,0,128,128).data;
 const copy=createCanvas(128,128);copy.getContext('2d').drawImage(a,0,0);const copied=copy.getContext('2d').getImageData(0,0,128,128).data;
 const blob=await new Promise(r=>copy.toBlob(r,'image/png'));const bitmap=await createImageBitmap(blob);const c=createCanvas(128,128);c.getContext('2d').drawImage(bitmap,0,0);const decoded=c.getContext('2d').getImageData(0,0,128,128).data;
 const diff=x=>({max:Math.max(...x.map((n,i)=>Math.abs(n-original[i]))),count:x.reduce((a,n,i)=>a+(n!==original[i]),0),sample:[...x.slice((20*128+20)*4,(20*128+20)*4+4)]});
 return {original:[...original.slice((20*128+20)*4,(20*128+20)*4+4)],copy:diff(copied),png:diff(decoded)};
 }''');Path('/delivery/firefox-codec-probe.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));browser.close()
