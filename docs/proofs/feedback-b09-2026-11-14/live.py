import json
from playwright.sync_api import sync_playwright
out={'errors':[]}
with sync_playwright() as pw:
    b=pw.chromium.launch(headless=True,args=['--no-sandbox'])
    for name,vp in [('desktop',{'width':1440,'height':1000}),('mobile',{'width':390,'height':844})]:
        ctx=b.new_context(viewport=vp);p=ctx.new_page();p.on('pageerror',lambda e:out['errors'].append(str(e)))
        p.goto('https://vtt.roll-drauf.de/regelwerk');link=p.locator('#regelwerkBooks a[href="/regelwerk/en"]');link.wait_for(state='visible')
        out[name+'_label']=link.text_content();link.click();p.wait_for_url('**/regelwerk/en')
        out[name+'_title']=p.locator('h1').text_content();out[name+'_frame']=p.locator('iframe.regelwerk-pdf-frame').get_attribute('src')
        out[name+'_open_visible']=p.locator('.regelwerk-pdf-open').is_visible()
        out[name+'_no_hscroll']=p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        p.locator('.regelwerk-books a[href="/regelwerk"]').click();p.wait_for_url('**/regelwerk')
        p.goto('https://vtt.roll-drauf.de/regelwerk/en');p.screenshot(path=f'/delivery/b09-{name}.png');ctx.close()
    b.close()
out['status']='pass' if not out['errors'] else 'fail'
open('/delivery/live.json','w').write(json.dumps(out,indent=1));print(json.dumps(out,indent=1))
