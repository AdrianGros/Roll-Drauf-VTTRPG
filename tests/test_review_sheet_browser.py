"""The actual identity upload stays above stats and shortcuts reveal real tabs."""
import io
from PIL import Image
from playwright.sync_api import sync_playwright,expect
from tests.test_personal_actions_browser import action_site  # noqa: F401
from vtt.extensions import db
from vtt.models import User


def test_actual_avatar_upload_is_above_stats_and_section_links_reveal_hidden_panels(action_site):
    app,origin,info=action_site
    with app.app_context():
        db.session.get(User,info['player_id']).storage_quota_gb=1;db.session.commit()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':390,'height':1000},reduced_motion='reduce')
        context.add_init_script("localStorage.setItem('vtt.display.v1',JSON.stringify({schema:1,theme:'night',language:'en',accent:'default',unit:'m'}))")
        context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(20000)
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(origin+f"/character-sheet?id={info['character']}&mode=edit")
        grid=page.locator('#sheetIdentityGrid')
        expect(page.locator('#sfPanel-play')).to_be_visible()
        expect(page.locator('#sheetIdentityUpload-avatar')).to_be_visible()
        assert grid.bounding_box()['y']<page.locator('.sf-layout').bounding_box()['y']
        image=io.BytesIO();Image.new('RGB',(2,2),'purple').save(image,format='PNG')
        with page.expect_file_chooser() as picker:
            page.locator('#sheetIdentityUpload-avatar').click()
        picker.value.set_files({'name':'review-avatar.png','mimeType':'image/png','buffer':image.getvalue()})
        expect(page.locator('#sheetIdentityRemove-avatar')).to_be_visible()
        assert grid.bounding_box()['y']<page.locator('.sf-layout').bounding_box()['y']
        for target,panel in [('srdManage','manage'),('srdInventory','inventory'),('sfPanel-play','play')]:
            page.locator(f'[data-review-section="{target}"]').click()
            expect(page.locator('#sfPanel-'+panel)).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert not errors,errors
        browser.close()
