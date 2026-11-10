"""Compact sheet journeys in Chromium and Firefox, including keyboard and money."""
import os
from pathlib import Path

import pytest

from tests.test_srd_sheet import site  # noqa: F401
from tests.test_srd_creator_api import data, wizard_state  # noqa: F401
from vtt.extensions import db
from vtt.models import Character
from vtt.rules_content.creator_drafts import character_values
from vtt.rules_content.creator_rules import evaluate


@pytest.mark.parametrize('engine,width', [('chromium',1440), ('chromium',390), ('chromium',320), ('firefox',1440), ('firefox',390)])
def test_compact_sheet_tabs_filters_display_and_inventory(site, data, engine, width):
    from playwright.sync_api import sync_playwright, expect
    app, origin, info = site
    state = wizard_state(data, 'Feedback Eulenfeder')
    with app.app_context():
        character = Character(user_id=info['user_id'], **character_values(data, state, evaluate(data, state), draft_id=1, finalized_at='2026-11-10T12:00:00Z'))
        db.session.add(character); db.session.commit()
        char_id = character.id
    with sync_playwright() as p:
        browser = getattr(p, engine).launch(headless=True, args=['--no-sandbox'] if engine == 'chromium' else [])
        context = browser.new_context(viewport={'width':width,'height':1000}, reduced_motion='reduce')
        context.add_init_script("if (!localStorage.getItem('vtt.sheet.display.v1')) localStorage.setItem('vtt.sheet.display.v1', JSON.stringify('invalid-old-value'))")
        context.add_cookies([{'name':'access_token_cookie','value':info['token'],'url':origin,'httpOnly':True}])
        page = context.new_page(); page.set_default_timeout(20000)
        errors=[]; page.on('pageerror',lambda error: errors.append(str(error)))
        page.goto(f'{origin}/character-sheet?id={char_id}')
        expect(page.locator('#sfPanel-play')).to_be_visible()
        expect(page.locator('#sfPanel-inventory')).to_be_hidden()
        expect(page.locator('#sfWallet')).to_contain_text('0 GM')
        assert page.locator('.sf-tab').count() == 5
        page.locator('#sfTab-play').focus(); page.keyboard.press('ArrowRight')
        expect(page.locator('#sfTab-spells')).to_be_focused()
        expect(page.locator('#sfPanel-spells')).to_be_visible()
        options=page.locator('#sfSpellGrade option').evaluate_all('(nodes)=>nodes.map(n=>n.value)')
        grade=next(v for v in options if v and v != '0')
        page.locator('#sfSpellGrade').select_option(grade)
        visible=page.locator('.sf-spell-card:visible')
        assert visible.count() > 0
        assert all(f'{grade}. Grad' in text for text in visible.all_text_contents())
        page.locator('#sfTab-play').click()
        page.locator('#sfUnits').select_option('ft')
        expect(page.locator('#sfPanel-play')).to_contain_text('30 ft')
        page.locator('#sfTheme').select_option('night')
        expect(page.locator('body')).to_have_attribute('data-sheet-theme','night')
        page.wait_for_function("() => getComputedStyle(document.querySelector('.sf-heading h3')).color === 'rgb(245, 232, 209)' && getComputedStyle(document.querySelector('.sheet-next-hint')).backgroundColor === 'rgb(48, 38, 58)'")
        # Catch conflicting legacy book colors as well as the new tabs.
        contrasts = page.evaluate('''() => {
            const rgb = value => value.match(/[\\d.]+/g).slice(0,3).map(Number);
            const luminance = values => values.map(v => { v /= 255; return v <= .04045 ? v/12.92 : ((v+.055)/1.055)**2.4; }).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
            return ['#srdSheetHeading','.sf-heading h3','.srd-roll-result','.srd-rollbar-head label','.sheet-next-hint'].map(selector => {
                const node = document.querySelector(selector);
                let surface=node;
                while (surface.parentElement && getComputedStyle(surface).backgroundColor === 'rgba(0, 0, 0, 0)') surface=surface.parentElement;
                const foreground=luminance(rgb(getComputedStyle(node).color));
                const background=luminance(rgb(getComputedStyle(surface).backgroundColor));
                return [selector,(Math.max(foreground,background)+.05)/(Math.min(foreground,background)+.05)];
            });
        }''')
        assert all(ratio >= 4.5 for _, ratio in contrasts), contrasts
        if width > 620:
            page.get_by_role('button',name='Waffenangriffe',exact=True).click()
            expect(page.locator('#sfPanel-inventory')).to_be_visible()
            page.get_by_role('button',name='Attribute & Rettungswürfe',exact=True).click()
            expect(page.locator('#sfPanel-play')).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth') <= width+1
        proof=os.environ.get('VTT_PROOF_DIR')
        if proof:
            Path(proof).mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(Path(proof)/f'sheet-{engine}-{width}.png'),full_page=True)
        page.reload()
        expect(page.locator('#sfTheme')).to_have_value('night')
        expect(page.locator('#sfUnits')).to_have_value('ft')
        page.get_by_role('button',name='Bogen bearbeiten',exact=True).click()
        page.locator('#sfTab-inventory').click()
        page.locator('#srdCoinGM').fill('37')
        page.get_by_role('button',name='Münzen speichern',exact=True).click()
        expect(page.locator('#sfWallet')).to_contain_text('37 GM')
        page.locator('#sfTab-manage').click()
        expect(page.locator('#sheetIdentityGrid')).to_be_visible()
        assert errors == [], errors
        browser.close()
