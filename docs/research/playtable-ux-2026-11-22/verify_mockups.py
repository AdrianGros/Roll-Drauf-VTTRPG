"""Inspect the proposed interfaces, not production functionality or user performance."""
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright,expect

HERE=Path(__file__).resolve().parent
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(HERE)))
thread=Thread(target=server.serve_forever,daemon=True);thread.start()
proof={'status':'running','scope':'Mockup rendering and local interactions only; no VTT integration or user study','checks':[]}
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        ctx=browser.new_context(viewport={'width':1080,'height':1100},ignore_https_errors=True,reduced_motion='reduce')
        page=ctx.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(f'http://127.0.0.1:{server.server_port}/evidence/mockup-preview.html')
        frame=page.frame_locator('iframe');expect(frame.locator('[data-design=groups] .pt-panel h3')).to_have_text('Karte & Sicht')
        expect(frame.locator('.viz-carousel-next')).to_be_visible()
        # The preview runtime supplies the same icon family as the inline surface.
        expect(frame.locator('[data-design=groups] .pt-dock svg').first).to_be_visible(timeout=30000)
        for index,kind in enumerate(['groups','workspaces','personal']):
            if index:frame.locator('.viz-carousel-next').click()
            app=frame.locator('[data-design='+kind+']');expect(app).to_be_visible()
            app.screenshot(path=str(HERE/'evidence'/('draft-'+kind+'-desktop.png')))
            if kind=='groups':
                app.locator('[data-group=tools] [data-command=measure]').click()
                expect(app.locator('[data-group=tools] [data-command=measure]')).to_have_attribute('aria-pressed','true')
                expect(app.get_by_label('Am Raster einrasten')).to_be_visible()
                app.locator('.pt-dock [data-command=map]').click()
                app.locator('.pt-panel [data-command=floors]').click()
            elif kind=='workspaces':
                app.locator('[data-workspace=Vorbereiten]').click()
                expect(app.locator('[data-workspace=Vorbereiten]')).to_have_attribute('aria-pressed','true')
                app.locator('.pt-panel [data-command=floors]').click()
            else:
                app.locator('[data-command-page="1"]').click()
                expect(app.locator('.pt-panel [data-command=journal]')).to_be_visible()
                app.locator('[data-command-page="1"]').click()
                expect(app.locator('.pt-panel [data-command="session-end"]')).to_be_visible()
                app.locator('[data-command-page="-1"]').click()
                app.locator('[data-command-page="-1"]').click()
                app.locator('[data-command-search]').fill('Etagen')
                expect(app.locator('.pt-command-line')).to_have_count(1)
                app.locator('[data-pin=floors]').click()
                expect(app.locator('.pt-dock [data-command=floors]')).to_have_count(1)
                app.locator('.pt-panel [data-command=floors]').click()
            expect(app.locator('.pt-panel h3')).to_have_text('Etagen & Balkonsicht')
            expect(app.get_by_label('Aktive Etage',exact=True)).to_have_value('Balkon')
            proof['checks'].append({'design':kind,'local_navigation_to_floors':'pass'})
        for width in [1024,390,320]:
            page.set_viewport_size({'width':width,'height':1200})
            for _ in range(3):
                # No custom carousel controller: use the supplied runtime.
                visible=frame.locator('.pt-app:visible');kind=visible.get_attribute('data-design')
                bounds=visible.evaluate("""app=>{const a=app.getBoundingClientRect();return [...app.querySelectorAll('button,input,select,textarea')].filter(e=>e.getClientRects().length).filter(e=>{const r=e.getBoundingClientRect();return r.left<a.left-1||r.right>a.right+1;}).map(e=>({tag:e.tagName,text:e.textContent,id:e.id}));}""")
                assert not bounds,(width,kind,bounds)
                if width==390:visible.screenshot(path=str(HERE/'evidence'/('draft-'+kind+'-mobile.png')))
                proof['checks'].append({'design':kind,'width':width,'horizontal_clipping':False})
                frame.locator('.viz-carousel-next').click()
        page.set_viewport_size({'width':1080,'height':1100})
        app=frame.locator('.pt-app:visible')
        app.locator('.pt-top [data-command=settings]').click()
        app.locator('[data-palette-select]').select_option('paper')
        color=app.evaluate('e=>getComputedStyle(e).backgroundColor');assert color=='rgb(248, 243, 233)',color
        app.locator('[data-palette-select]').select_option('night')
        color=app.evaluate('e=>getComputedStyle(e).backgroundColor');assert color=='rgb(28, 28, 28)',color
        proof['checks'].append({'palette_switch':'pass','night_background':color})
        assert not errors,errors
        proof['javascript_errors']=errors;proof['status']='pass'
        browser.close()
finally:
    server.shutdown();thread.join(timeout=3);server.server_close()
    (HERE/'evidence/mockup-verification.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(proof,ensure_ascii=False,indent=2))
