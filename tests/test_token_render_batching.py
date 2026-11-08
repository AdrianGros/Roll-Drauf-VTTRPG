"""Real browser regressions for bursts of token changes on large maps (IT-16)."""
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

SCRIPT = Path(__file__).resolve().parents[1] / 'vtt/static/js/play-ui.js'


@pytest.fixture(params=['chromium', 'firefox'])
def table(request):
    with sync_playwright() as playwright:
        browser = getattr(playwright, request.param).launch(headless=True)
        page = browser.new_page()
        page.set_content('<div id="mapWorld"><img id="mapImage"><div id="mapGridLayer"></div><div id="mapTokenLayer"></div></div>')
        # Expose the existing class only inside the isolated test page. Normal
        # app startup has already passed DOMContentLoaded and cannot run here.
        script = SCRIPT.read_text().replace(
            '    document.addEventListener("DOMContentLoaded", () => {',
            '    window.__PlayRuntimeUI = PlayRuntimeUI;\n    document.addEventListener("DOMContentLoaded", () => {')
        page.add_script_tag(content=script)
        page.evaluate('''() => {
          const ui=window.ui=Object.create(window.__PlayRuntimeUI.prototype);
          ui.bootstrap={state_payload:{active_map:{id:1,width:6000,height:4000,grid_size:70},tokens:Array.from({length:500},(_,i)=>({id:i+1,name:'Token '+i,x:i%30,y:Math.floor(i/30),size:1,version:1,metadata_json:{position_mode:'pixel'}}))}};
          ui.selectedTokenId=null;ui.combat=null;ui.tokenIndex=new Map();ui.autoFitMapId=1;ui._visionGeometryLoadedForMapId=1;
          ui._syncExtent=()=>{};ui._canMoveToken=()=>true;ui._visibleTokens=t=>t;
          ui._renderState=()=>{};ui._renderTurnOrder=()=>{};ui._renderTokenSelectors=()=>{};ui._renderChat=()=>{};ui._logActivity=()=>{};
          const render=ui._renderMapCanvas.bind(ui);ui.paints=0;
          ui._renderMapCanvas=()=>{ui.paints++;render();};
          ui._renderMapCanvas();ui.paints=0;
          window.flushFrames=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
        }''')
        yield page
        browser.close()


def test_burst_preserves_every_update_and_paints_once_per_frame(table):
    result = table.evaluate('''async () => {
      for(let n=0;n<100;n++)ui._handleTokenUpdated({token:{...ui.bootstrap.state_payload.tokens[n],x:n+10,version:2}});
      const synchronous=ui.bootstrap.state_payload.tokens.slice(0,100).every((t,n)=>t.x===n+10 && t.version===2);
      const beforePaint=ui.paints;
      await flushFrames();
      const firstPaints=ui.paints;
      const firstPosition=document.querySelector('[data-token-id="100"]').dataset.tokenLeft;
      ui._handleTokenUpdated({token:{...ui.bootstrap.state_payload.tokens[99],x:888,version:3}});
      await flushFrames();
      return {synchronous,beforePaint,firstPaints,firstPosition,paints:ui.paints,lastPosition:document.querySelector('[data-token-id="100"]').dataset.tokenLeft,markers:document.querySelectorAll('.token-marker').length};
    }''')
    assert result == dict(synchronous=True,beforePaint=0,firstPaints=1,firstPosition='109',paints=2,lastPosition='888',markers=500)


def test_create_update_move_delete_order_and_selection_are_preserved(table):
    result = table.evaluate('''async () => {
      ui._handleTokenCreated({token:{id:501,name:'new',x:1,y:1,metadata_json:{position_mode:'pixel'}}});
      ui._handleTokenUpdated({token:{id:501,name:'renamed',x:2,y:2,version:2,metadata_json:{position_mode:'pixel'}}});
      ui._handleTokenBatchMoved({moves:[{token_id:501,x:777,y:888}]});
      ui.selectedTokenId=1;
      ui._handleTokenDeleted({token_id:1});
      await flushFrames();
      const marker=document.querySelector('[data-token-id="501"]');
      return {paints:ui.paints,selected:ui.selectedTokenId,deleted:!document.querySelector('[data-token-id="1"]'),label:marker.title,x:marker.dataset.tokenLeft,y:marker.dataset.tokenTop,markers:document.querySelectorAll('.token-marker').length};
    }''')
    assert result == dict(paints=1,selected=None,deleted=True,label='renamed',x='777',y='888',markers=500)


def test_authoritative_snapshot_cancels_stale_queued_paint(table):
    result = table.evaluate('''async () => {
      ui._handleTokenUpdated({token:{...ui.bootstrap.state_payload.tokens[0],x:99}});
      const snapshot={...ui.bootstrap.state_payload,tokens:[{id:999,name:'replacement',x:55,y:22,metadata_json:{position_mode:'pixel'}}]};
      ui._handleSnapshot(snapshot);
      await flushFrames();
      return {paints:ui.paints,markers:document.querySelectorAll('.token-marker').length,x:document.querySelector('[data-token-id="999"]').dataset.tokenLeft};
    }''')
    assert result == dict(paints=1,markers=1,x='55')


def test_token_burst_keeps_drag_marker_until_pointer_release(table):
    result = table.evaluate('''async () => {
      const marker=document.querySelector('[data-token-id="1"]');
      ui.dragState={marker,tokenId:1,baseLeft:0,baseTop:0,moved:false};
      ui._handleTokenUpdated({token:{...ui.bootstrap.state_payload.tokens[1],x:999}});
      await flushFrames();
      const during={connected:marker.isConnected,paints:ui.paints};
      window.dispatchEvent(new PointerEvent('pointerup'));
      await flushFrames();
      return {during,dragEnded:ui.dragState===null,paints:ui.paints,x:document.querySelector('[data-token-id="2"]').dataset.tokenLeft};
    }''')
    assert result == dict(during=dict(connected=True,paints=0),dragEnded=True,paints=1,x='999')
