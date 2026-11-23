from pathlib import Path
from tempfile import TemporaryDirectory
import json

from pytest import MonkeyPatch
from playwright.sync_api import sync_playwright, expect
from tests.test_srd_creator_browser import site


def contrast(a, b):
    def luminance(rgb):
        values = [v / 255 for v in rgb[:3]]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
        return sum(a * b for a, b in zip(linear, [.2126, .7152, .0722]))
    x, y = sorted([luminance(a), luminance(b)])
    return (y + .05) / (x + .05)


out = Path('docs/proofs/feedback-harness-2026-11-23/creator')
out.mkdir(parents=True, exist_ok=True)
results = []
with TemporaryDirectory(prefix='vtt-creator-probe-') as temporary:
    patch = MonkeyPatch()
    fixture = site.__wrapped__(Path(temporary), patch)
    app, origin, info = next(fixture)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
            for width in [390, 1440]:
                context = browser.new_context(viewport={'width': width, 'height': 1000}, reduced_motion='reduce')
                context.add_cookies([{'name': 'access_token_cookie', 'value': info['token'], 'url': origin, 'httpOnly': True}])
                page = context.new_page()
                page.set_default_timeout(15000)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(origin + '/srd-creator')
                page.locator('#scNewGuided').click()
                page.get_by_role('button', name='Kämpfer', exact=False).first.click()
                for theme in ['paper', 'night']:
                    backgrounds = []
                    for accent in ['default', 'bronze', 'teal']:
                        page.locator('#vttDisplayOpen').click()
                        page.locator('#vttDisplay-theme').select_option(theme)
                        page.locator('#vttDisplay-accent').select_option(accent)
                        page.get_by_role('button', name='Anwenden', exact=True).click()
                        colors = page.locator('#scRandomize').evaluate('''button => {
                            const context = document.createElement('canvas').getContext('2d');
                            const rgb = color => {
                                context.clearRect(0,0,1,1); context.fillStyle = color; context.fillRect(0,0,1,1);
                                return Array.from(context.getImageData(0,0,1,1).data);
                            };
                            const style = getComputedStyle(button);
                            return {text:rgb(style.color), background:rgb(style.backgroundColor)};
                        }''')
                        ratio = contrast(colors['text'], colors['background'])
                        assert ratio >= 4.5, (theme, accent, colors, ratio)
                        backgrounds.append(colors['background'])
                        results.append({'width': width, 'theme': theme, 'accent': accent,
                                        'random_button': colors, 'contrast': round(ratio, 2)})
                    assert len({tuple(c) for c in backgrounds}) == 3, backgrounds
                page.get_by_role('button', name='Klassentext lesen').click()
                expect(page.locator('#scDialog')).to_be_visible()
                expect(page.locator('#scDialogBody dl').first).to_have_css('display', 'grid')
                assert page.locator('#scDialogBody dl').evaluate_all('''lists => lists.every(list =>
                    [...list.querySelectorAll('dt')].every(term => {
                        const value = term.nextElementSibling;
                        const a=term.getBoundingClientRect(), b=value.getBoundingClientRect();
                        return a.bottom <= b.top + 1 || a.right <= b.left + 1;
                    }))''')
                page.screenshot(path=str(out / f'class-facts-teal-night-{width}.png'))
                assert not errors, errors
                context.close()
            browser.close()
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass
        patch.undo()
(out / 'probe.json').write_text(json.dumps({'status':'pass','cases':results,'class_facts_widths':[390,1440]}, indent=2)+'\n')
print(json.dumps({'status':'pass','accent_cases':len(results),'class_facts_widths':[390,1440]}))
