"""Focused live acceptance of Select/Pan and middle-button gestures in both seats."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

origin = 'https://vtt.roll-drauf.de'
root = Path('/proof')
fixture = json.loads(Path('/private.json').read_text())
expect.set_options(timeout=25000)
proof = {'origin': origin, 'status': 'running', 'journeys': [], 'page_errors': []}
with sync_playwright() as p:
    for kind, engine in [('dm', p.chromium), ('player', p.firefox)]:
        browser = engine.launch(headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        user = fixture['users'][kind]
        context.add_cookies([
            {'name': 'access_token_cookie', 'value': user['token'], 'url': origin, 'httpOnly': True, 'secure': True},
            {'name': 'csrf_access_token', 'value': user['csrf'], 'url': origin, 'secure': True},
        ])
        page = context.new_page()
        page.set_default_timeout(25000)
        page.on('pageerror', lambda error: proof['page_errors'].append(str(error)))
        page.goto(origin + f"/campaigns?campaign_id={fixture['campaign_id']}")
        action = 'open-session-dm' if kind == 'dm' else 'open-session'
        page.locator(f'[data-hub-action="{action}"]').first.click()
        expect(page.locator('body')).to_have_attribute('data-table-seat', kind)
        expect(page.locator('#presenceRoster')).to_contain_text(user['username'])
        if kind == 'player':
            expect(page.locator('#btnMapPresentation')).to_have_count(0)
        for _ in range(10):
            page.locator('#btnZoomIn').click()
        viewport = page.locator('#mapViewport')
        box = viewport.bounding_box()
        x, y = box['x'] + box['width'] * .65, box['y'] + box['height'] * .5
        positions = page.locator('.token-marker').evaluate_all('rows=>rows.map(e=>[e.dataset.tokenId,e.style.left,e.style.top])')
        def offset():
            return viewport.evaluate('e=>({x:e.scrollLeft,y:e.scrollTop})')
        def drag(dx, dy, button='left'):
            before = offset()
            page.mouse.move(x, y)
            page.mouse.down(button=button)
            page.mouse.move(x + dx, y + dy, steps=12)
            page.mouse.up(button=button)
            after = offset()
            assert abs(after['x'] - before['x']) >= abs(dx) - 3, (kind, before, after)
            return {'before': before, 'after': after}
        page.locator('[data-tool="pan"]').click()
        pan = drag(-120, -70)
        page.locator('[data-tool="select"]').click()
        select = drag(-90, -50)
        middle = drag(60, 30, 'middle')
        assert positions == page.locator('.token-marker').evaluate_all('rows=>rows.map(e=>[e.dataset.tokenId,e.style.left,e.style.top])')
        proof['journeys'].append({'role': kind, 'status': 'pass', 'pan': pan, 'empty_select': select, 'middle_button': middle, 'token_world_positions_unchanged': True})
        context.close()
        browser.close()
assert not proof['page_errors'], proof['page_errors']
proof['status'] = 'pass'
(root / 'live-pan.json').write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps({'status': 'pass', 'role_journeys': len(proof['journeys'])}))
