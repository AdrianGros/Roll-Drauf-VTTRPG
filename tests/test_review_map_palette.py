"""Own-image dialogs inherit night controls while image canvases stay untouched."""
from tests.test_mapmaker_browser import browser,open_editor,preview_origin  # noqa: F401


def test_own_image_dialog_fields_follow_night_palette(open_editor):
    ed=open_editor(choose_template=False,init_script="localStorage.setItem('vtt.display.v1',JSON.stringify({schema:1,theme:'night',language:'de',accent:'default',unit:'m'}))")
    page=ed.page;page.locator('#newEmpty').click();ed.tool('stamp')
    for trigger,dialog,field,cancel in [('#ownUploadBtn','#ownUploadDialog','#ownUploadLabel','#ownUploadCancel'),('#ownPixelBtn','#pixelDialog','#pixelLabel','#pixelCancel')]:
        page.locator(trigger).click()
        values=page.evaluate("""({dialog,field})=>{const color=token=>{const e=document.createElement('i');e.style.color=`var(${token})`;document.body.append(e);const c=getComputedStyle(e).color;e.remove();return c;};return [dialog,field].map(selector=>{const css=getComputedStyle(document.querySelector(selector));return {selector,bg:css.backgroundColor,ink:css.color,allowed:['--ui-panel','--ui-paper','--ui-soft'].map(color),expectedInk:color('--ui-ink')};});}""",{'dialog':dialog,'field':field})
        for row in values:
            assert row['bg'] in row['allowed'],row
            assert row['ink']==row['expectedInk'],row
        page.locator(cancel).click()
    ed.assert_clean()
