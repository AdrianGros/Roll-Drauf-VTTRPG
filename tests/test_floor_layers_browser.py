"""Real Chromium module journey against isolated, authenticated live floor APIs.

The small host supplies the parent-owned PlayUI/window integration contract;
the actual shipped floor modules, controls and API are used unchanged.
"""
import json
import os
from pathlib import Path
import threading

from werkzeug.serving import make_server, WSGIRequestHandler
from tests.test_floor_layers import floor_registration, floor_table, png, prefix, floor_path
from tests.test_table_contexts import enter
from vtt.extensions import db
from vtt.models import SceneWall

pytest_plugins = ["tests.play_shared"]


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        pass


def host(info, headers, dm):
    # This route is fulfilled by Playwright, not registered in production.
    return """<!doctype html><html lang="de"><head><link rel="stylesheet" href="/static/css/play-floor.css"></head>
    <body><div id="mapStage" style="position:relative;width:512px;height:384px;background:black"><img id="mapImage" width="512" height="384" style="image-rendering:pixelated"></div>
    <div id="visionLayer"></div><section id="settings"></section><main id="windows"></main>
    <script>
    const info=INFO, tableHeaders=HEADERS;
    window.Auth={buildHeaders:(method,jsonBody)=>({...tableHeaders,...(jsonBody?{'Content-Type':'application/json'}:{})}),
      makeAuthRequest:async(url,method='GET',body=null)=>{const r=await fetch(url,{method,credentials:'include',headers:Auth.buildHeaders(method,body!==null),body:body===null?undefined:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw new Error(data.error||data.code);return data;},refreshAccessToken:async()=>false};
    window.ui={campaignId:info.campaign,sessionId:info.session,_composedOperator:IS_DM,readOnly:false,
      bootstrap:{state_payload:{active_map:{id:info.map,width:128,height:96,grid_size:16,light_rules:{dimensions_mode:'pixel'},background_url:'/legacy-map.png'}}},
      feedback:{previewToken:null,image:document.createElement('img'),scheduleLighting:()=>{}},feedbackDM:{root:document.getElementById('settings')},
      windows:{items:new Map(),add(id,title,root){const win=document.createElement('section');win.id='window-'+id;win.append(root);win.hidden=true;document.getElementById('windows').append(win);this.items.set(id,{root:win});},toggle(id){this.items.get(id).root.hidden=!this.items.get(id).root.hidden;}},
      _renderMapCanvas(){document.getElementById('mapImage').src=this.floorView.background(this.bootstrap.state_payload.active_map);}};
    </script><script src="/static/js/play-floor-view.js"></script>DM_SCRIPT
    <script>ui.floorView=new PlayFloorView(ui);if(IS_DM)ui.floorDM=new PlayFloorDM(ui);ui._renderMapCanvas();</script></body></html>""".replace("INFO", json.dumps(info)).replace("HEADERS", json.dumps(headers)).replace(
        "IS_DM", "true" if dm else "false").replace(
        "DM_SCRIPT", '<script src="/static/js/play-floor-dm.js"></script>' if dm else "")


def pixel(page, x, y):
    return page.evaluate("""async ([x,y])=>{const image=document.getElementById('mapImage');await image.decode();const canvas=document.createElement('canvas');canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0);return [...ctx.getImageData(x,y,1,1).data];}""", [x, y])


def test_dm_upload_balcony_and_member_receives_only_masked_raster(
        play_app, floor_table, play_dm_client, play_player_client):
    from playwright.sync_api import sync_playwright, expect
    campaign, session, map_, token = floor_table
    dm_headers = enter(play_dm_client, campaign, session, "dm")
    player_headers = enter(play_player_client, campaign, session)
    map_.fog_enabled = True
    db.session.add(SceneWall(campaign_map_id=map_.id, x0=64, y0=0, x1=64, y1=96,
                             sight="normal", light="normal", created_by=campaign.owner_id))
    db.session.commit()
    info = dict(campaign=campaign.id, session=session.id, map=map_.id, token=token.id)
    server = make_server("127.0.0.1", 0, play_app, threaded=True, request_handler=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            dm_context = browser.new_context(viewport={"width": 1200, "height": 1000})
            player_context = browser.new_context(viewport={"width": 900, "height": 700})
            for context, client in [(dm_context, play_dm_client), (player_context, play_player_client)]:
                context.add_cookies([dict(name="access_token_cookie", value=client.get_cookie("access_token_cookie").value, url=origin)])
            dm, player = dm_context.new_page(), player_context.new_page()
            errors = []
            for page, headers, operator in [(dm, dm_headers, True), (player, player_headers, False)]:
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.route("**/__floor_host", lambda route, request, html=host(info, headers, operator): route.fulfill(content_type="text/html", body=html))
                page.goto(origin + "/__floor_host")
            dm.locator("#btnMapFloors").click()
            expect(dm.locator("#floorLimitation")).to_contain_text("gemeinsamen 2D-Karte")
            for name, color in [("Ground", "red"), ("Balcony", "lime")]:
                dm.locator("#newFloorName").fill(name)
                dm.locator("#newFloorFile").set_input_files(dict(name=name + ".png", mimeType="image/png", buffer=png(color)))
                dm.locator("#uploadFloor").click()
                expect(dm.locator("#floorEditorStatus")).to_contain_text("hochgeladen")
                expect(dm.locator("#floorList .floor-card")).to_have_count(1 if name == "Ground" else 2)
            card = dm.locator("#floorList .floor-card").nth(1)
            upper = int(card.get_attribute("data-floor-id"))
            card.locator('input[type="checkbox"]').check()
            card.get_by_role("button", name="Rechteckige Öffnung hinzufügen").click()
            for key, value in [("x", "10"), ("y", "12"), ("width", "20"), ("height", "25")]:
                card.locator(f'input[data-rect-key="{key}"]').fill(value)
            card.get_by_role("button", name="Etage speichern", exact=True).click()
            expect(dm.locator("#floorEditorStatus")).to_have_text("Etagen gespeichert.")
            dm.locator("#floorEnabled").check()
            dm.locator("#activeFloor").select_option(str(upper))
            with dm.expect_response(lambda response: response.request.method == "PUT" and response.url.endswith("/floors")):
                dm.locator("#applyFloorDeck").click()
            player.evaluate("ui.floorView.refresh(true)")
            player.wait_for_function("ui.floorView.enabled===true")
            assert pixel(player, 15, 15) == [255, 0, 0, 255]
            assert pixel(player, 45, 40) == [0, 255, 0, 255]
            assert pixel(player, 110, 48) == [0, 0, 0, 255]
            player.reload()
            player.wait_for_function("ui.floorView.enabled===true")
            assert pixel(player, 15, 15) == [255, 0, 0, 255]
            assert player.evaluate("typeof window.PlayFloorDM") == "undefined"
            assert player.locator("#btnMapFloors").count() == 0
            denied = player.evaluate("""async path=>({source:(await fetch(path+'/image',{headers:tableHeaders})).status,config:(await fetch(path.replace(/\\/\\d+$/,''),{headers:tableHeaders})).status})""", floor_path(floor_table) + f"/{upper}")
            assert denied == {"source": 403, "config": 403}
            # DM preview immediately covers the unmasked image, then gets the
            # same wall-clipped source pixels as the selected player's token.
            covered = dm.evaluate("""()=>{ui.feedback.previewToken=info.token;ui.floorView.refresh(true);return document.getElementById('mapImage').src.startsWith('data:image/svg+xml,');}""")
            assert covered
            dm.wait_for_function("ui.floorView.enabled===true&&ui.floorView.preview===info.token")
            assert pixel(dm, 110, 48) == [0, 0, 0, 255]
            proof = os.environ.get("FLOOR_PROOF_DIR")
            if proof:
                Path(proof).mkdir(parents=True, exist_ok=True)
                dm.screenshot(path=str(Path(proof) / "floor-dm-editor-preview.png"), full_page=True)
                player.screenshot(path=str(Path(proof) / "floor-member-raster.png"), full_page=True)
            # A failed update covers prior artwork and never exposes a source.
            player.route("**/floors/view*", lambda route: route.fulfill(status=503, content_type="application/json", body='{"error":"isolated failure"}'))
            player.evaluate("ui.floorView.refresh(true)")
            expect(player.locator("#floorViewStatus")).to_contain_text("nicht aktualisiert")
            assert player.locator("#mapImage").get_attribute("src").startswith("data:image/svg+xml,")
            if proof:
                player.screenshot(path=str(Path(proof) / "floor-member-failure-cover.png"), full_page=True)
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=3)
