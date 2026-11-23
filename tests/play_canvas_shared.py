"""Public UI/geometry checks, shared by isolated and normal-role live journeys."""
import math
from playwright.sync_api import expect


def usable(page):
    return page.evaluate("""() => {
      const v=document.getElementById('mapViewport').getBoundingClientRect();
      const h=document.querySelector('.stage-topbar').getBoundingClientRect();
      const bars=['.left-toolbar','#personalActionBar','#actionHotbar'].map(s=>document.querySelector(s)?.getBoundingClientRect()).filter(r=>r?.width&&r.height&&r.top<v.bottom&&r.bottom>v.top);
      return {left:v.left+16,right:v.right-16,top:Math.max(v.top+16,h.bottom+12),bottom:Math.min(v.bottom-16,...bars.map(r=>r.top-12)),viewport:{left:v.left,right:v.right,top:v.top,bottom:v.bottom,width:v.width,height:v.height}};
    }""")


def fit(page):
    page.locator('#btnZoomFit').click()
    area=usable(page)
    page.wait_for_function("""a=>{const r=document.getElementById('mapWorld').getBoundingClientRect();return r.left>=a.left-1&&r.right<=a.right+2&&r.top>=a.top-1&&r.bottom<=a.bottom+2} """,arg=area)
    return area


def pan_by(page, dx, dy, touch=None):
    area=usable(page);cx=round((area['left']+area['right'])/2);cy=round((area['top']+area['bottom'])/2)
    steps=max(1,math.ceil(max(abs(dx)/100,abs(dy)/100)))
    moved_x=moved_y=0
    for index in range(steps):
        target_x=round(dx*(index+1)/steps);target_y=round(dy*(index+1)/steps)
        step_x=target_x-moved_x;step_y=target_y-moved_y
        moved_x,moved_y=target_x,target_y
        if touch:
            touch.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':cx,'y':cy}]})
            touch.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':cx+step_x,'y':cy+step_y}]})
            touch.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        else:
            page.mouse.move(cx,cy);page.mouse.down();page.mouse.move(cx+step_x,cy+step_y,steps=3);page.mouse.up()


def exercise_camera(page, touch=None):
    area=fit(page)
    assert float(page.locator('#zoomLabel').inner_text().rstrip('%'))<20
    page.locator('[data-tool=pan]').click()
    cx=(area['left']+area['right'])/2;cy=(area['top']+area['bottom'])/2
    for x,y in [(0,0),(1,0),(1,1),(0,1)]:
        r=page.locator('#mapWorld').bounding_box()
        pan_by(page,cx-r['x']-x*r['width'],cy-r['y']-y*r['height'],touch)
        r=page.locator('#mapWorld').bounding_box()
        assert abs(r['x']+x*r['width']-cx)<2 and abs(r['y']+y*r['height']-cy)<2,r
    pan_by(page,area['viewport']['width']*1.2,0,touch)
    assert page.locator('#mapWorld').bounding_box()['x']>area['viewport']['right']
    fit(page)
    px=round(cx+35);py=round(cy+20)
    before=page.locator('#mapWorld').bounding_box()
    normalized=((px-before['x'])/before['width'],(py-before['y'])/before['height'])
    zoom=page.locator('#zoomLabel').inner_text()
    page.mouse.move(px,py);page.mouse.wheel(0,-120)
    expect(page.locator('#zoomLabel')).not_to_have_text(zoom)
    after=page.locator('#mapWorld').bounding_box()
    assert after['width']>before['width']
    assert abs((px-after['x'])/after['width']-normalized[0])<0.0001,(before,after,px,py,normalized)
    assert abs((py-after['y'])/after['height']-normalized[1])<0.0001,(before,after,px,py,normalized)
    if touch:
        start=after
        nx=(cx-start['x'])/start['width'];ny=(cy-start['y'])/start['height']
        touch.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'id':0,'x':cx-30,'y':cy},{'id':1,'x':cx+30,'y':cy}]})
        touch.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'id':0,'x':cx-50,'y':cy+15},{'id':1,'x':cx+50,'y':cy+15}]})
        touch.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        after=page.locator('#mapWorld').bounding_box()
        assert after['width']>start['width']
        assert abs((cx-after['x'])/after['width']-nx)<0.0001
        assert abs((cy+15-after['y'])/after['height']-ny)<0.0001
    fit(page);page.locator('[data-tool=select]').click()
    assert page.evaluate('visualViewport.scale')==1
    return {'all_corners_centered':True,'pan_beyond_document':True,'fit_below_20_percent':True,'zoom_anchor_kept':True,'pinch':bool(touch)}
