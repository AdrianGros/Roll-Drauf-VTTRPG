"""Mobile gates: phone viewports, and measurements that CAN fail.

Born from the 2026-08-24 mobile audit, which found the play table
collapsed to a 46px map sliver with the dice button fully off-screen --
and no robot had ever looked at a phone viewport (the exact blind spot
Goblin Delve's cockpit RCA documented for widths below 1440px).

Gates (each one maps to a measured failure from the audit):
  * book pages at 390x844: no horizontal overflow
  * play table portrait + landscape: the map gets >= 55% of the
    viewport width (the fold-out map owns the screen)
  * toolbar buttons: >= 44px tall, mutually non-overlapping, and in
    the bottom thumb zone
  * the dice button is fully inside the viewport once the tools tab is
    open, >= 44px tall
  * no visible input renders below 16px font (iOS focus-zoom trigger)

    python -m tools.robots.mobile [--out FILE]
"""

from __future__ import annotations

import json
import struct
import sys
import tempfile
import zlib
from pathlib import Path

from tools.robots.accounts import mint_registration_keys
from tools.robots.stack import disposable_stack

PHONE_PORTRAIT = {"width": 390, "height": 844}
PHONE_LANDSCAPE = {"width": 844, "height": 390}
BOOK_PAGES = ["/login.html", "/dashboard", "/campaigns", "/characters"]


def _make_png(width, height, rgb):
    def chunk(tag, data):
        piece = struct.pack(">I", len(data)) + tag + data
        return piece + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _phone_context(browser, viewport, cookies):
    context = browser.new_context(
        viewport=viewport, device_scale_factor=3,
        is_mobile=True, has_touch=True)
    context.add_cookies(cookies)
    return context


def _check_play_table(page, orientation: str, findings: list[str]) -> None:
    verdict = page.evaluate(
        """() => {
            const r = {};
            const visible = el => {
                const box = el.getBoundingClientRect();
                const style = getComputedStyle(el);
                return box.width > 0 && box.height > 0
                    && style.display !== 'none'
                    && style.visibility !== 'hidden'
                    && box.bottom > 0 && box.right > 0
                    && box.top < innerHeight && box.left < innerWidth;
            };
            r.innerW = window.innerWidth;
            const vp = document.getElementById('mapViewport');
            r.mapW = vp ? vp.getBoundingClientRect().width : 0;
            const buttons = [...document.querySelectorAll('.left-toolbar .tool-btn')]
                .map(b => { const x = b.getBoundingClientRect();
                            return {id: b.textContent.trim(), l: x.left, t: x.top,
                                    r: x.right, b: x.bottom, h: x.height}; })
                .filter(b => b.h > 0);
            r.buttons = buttons;
            r.overlaps = [];
            for (let i = 0; i < buttons.length; i++) {
                for (let j = i + 1; j < buttons.length; j++) {
                    const a = buttons[i], c = buttons[j];
                    if (a.l < c.r - 1 && c.l < a.r - 1 && a.t < c.b - 1 && c.t < a.b - 1) {
                        r.overlaps.push(`${a.id}/${c.id}`);
                    }
                }
            }
            r.smallInputs = [...document.querySelectorAll('input, select, textarea')]
                .filter(el => el.offsetParent && parseFloat(getComputedStyle(el).fontSize) < 16)
                .map(el => `${el.id || el.tagName} ${getComputedStyle(el).fontSize}`);
            // Global spellbook button rules have higher specificity than the
            // table's local rules. On touch, the sticky :hover state made
            // visible table controls parchment-white instead of the dark
            // play surface. Keep this as a user-facing visual gate: every
            // visible play-table button must stay off the bright paper fill.
            r.brightButtons = [...document.querySelectorAll('button')]
                .filter(visible)
                .filter(button => /255,\\s*248|255,\\s*249/.test(
                    `${getComputedStyle(button).backgroundColor} ${getComputedStyle(button).backgroundImage}`))
                .map(button => button.id || button.textContent.trim());
            return r;
        }""")

    inner_w = verdict["innerW"]
    if verdict["mapW"] < inner_w * 0.55:
        findings.append(
            f"[{orientation}] map viewport is {verdict['mapW']:.0f}px of {inner_w}px "
            f"(< 55%) - the fold-out map does not own the screen")
    if verdict["overlaps"]:
        findings.append(f"[{orientation}] toolbar buttons overlap: {verdict['overlaps']}")
    inner_h = page.evaluate("() => window.innerHeight")
    for button in verdict["buttons"]:
        if button["h"] < 44:
            findings.append(f"[{orientation}] tool button {button['id']} is {button['h']:.0f}px tall (< 44)")
        if button["t"] < inner_h * 0.75:
            findings.append(
                f"[{orientation}] tool button {button['id']} at y={button['t']:.0f} "
                f"is outside the bottom thumb zone (>= {inner_h * 0.75:.0f})")
    if verdict["smallInputs"]:
        findings.append(f"[{orientation}] inputs below 16px (iOS zoom trigger): {verdict['smallInputs'][:4]}")
    if verdict["brightButtons"]:
        findings.append(
            f"[{orientation}] visible table buttons use the bright paper palette: "
            f"{verdict['brightButtons'][:8]}")

    # Selecting a tool must produce the Roll-Drauf purple state after the
    # touch hover/focus transition has settled, not just toggle a class.
    for tool in ("pan", "token", "select"):
        button = page.locator(f'.tool-btn[data-tool="{tool}"]')
        if not button.is_visible():
            continue
        button.click()
        page.wait_for_timeout(350)
        selected = page.evaluate(
            """tool => {
                const button = document.querySelector(`.tool-btn[data-tool="${tool}"]`);
                if (!button) return null;
                const style = getComputedStyle(button);
                const surface = `${style.backgroundColor} ${style.backgroundImage}`;
                return {
                    active: button.classList.contains('active'),
                    purple: /47,\\s*22,\\s*56|75,\\s*35,\\s*90/.test(surface),
                    surface,
                };
            }""",
            tool,
        )
        if not selected or not selected["active"]:
            findings.append(f"[{orientation}] tool {tool!r} did not become selected")
        elif not selected["purple"]:
            findings.append(
                f"[{orientation}] selected tool {tool!r} is not Roll-Drauf purple: "
                f"{selected['surface']}")

    # Dice must be reachable: open the sidebar tools tab, then measure.
    zoom_before = page.evaluate("() => document.getElementById('mapWorld')?.style.transform || ''")
    page.click("#btnZoomIn")
    page.wait_for_timeout(150)
    zoom_after = page.evaluate("() => document.getElementById('mapWorld')?.style.transform || ''")
    if zoom_before == zoom_after:
        findings.append(f"[{orientation}] zoom-in button did not change the map zoom")
    page.click("#btnZoomOut")

    table_button = page.locator("#btnTableSheet")
    if table_button.is_visible():
        table_button.click()
        page.wait_for_timeout(150)
        table_state = page.evaluate(
            """() => {
                const button = document.getElementById('btnTableSheet');
                const style = getComputedStyle(button);
                const surface = `${style.backgroundColor} ${style.backgroundImage}`;
                return {
                    open: !document.getElementById('tableSheet').hidden,
                    active: button.classList.contains('active'),
                    purple: /47,\\s*22,\\s*56|75,\\s*35,\\s*90/.test(surface),
                };
            }""")
        if not table_state["open"]:
            findings.append(f"[{orientation}] Tisch button did not open the table sheet")
        if not table_state["active"] or not table_state["purple"]:
            findings.append(f"[{orientation}] open Tisch button is not Roll-Drauf purple")
        page.locator("#tableSheetBackdrop").click(position={"x": 5, "y": 5})
        page.wait_for_timeout(150)
        if page.locator("#tableSheet").get_attribute("hidden") is None:
            findings.append(f"[{orientation}] table sheet backdrop did not close the sheet")

    page.click("#btnSidebarToggle")
    for tab in ("journal", "chat", "tools", "session"):
        page.click(f'.sidebar-tab[data-tab="{tab}"]')
        page.wait_for_timeout(120)
        tab_state = page.evaluate(
            """tab => {
                const button = document.querySelector(`.sidebar-tab[data-tab="${tab}"]`);
                const style = getComputedStyle(button);
                const surface = `${style.backgroundColor} ${style.backgroundImage}`;
                return {
                    active: button.classList.contains('active'),
                    panel: document.getElementById(`panel-${tab}`)?.classList.contains('active'),
                    purple: /47,\\s*22,\\s*56|75,\\s*35,\\s*90/.test(surface),
                };
            }""",
            tab,
        )
        if not tab_state["active"] or not tab_state["panel"]:
            findings.append(f"[{orientation}] sidebar tab {tab!r} did not activate its panel")
        if not tab_state["purple"]:
            findings.append(f"[{orientation}] selected sidebar tab {tab!r} is not Roll-Drauf purple")
    page.click('.sidebar-tab[data-tab="tools"]')
    page.wait_for_timeout(400)
    dice = page.evaluate(
        """() => {
            const b = document.getElementById('btnRoll');
            if (!b) return null;
            const x = b.getBoundingClientRect();
            return {l: x.left, t: x.top, r: x.right, b: x.bottom, h: x.height,
                    w: window.innerWidth, ih: window.innerHeight};
        }""")
    if not dice:
        findings.append(f"[{orientation}] #btnRoll missing")
    else:
        if dice["l"] < 0 or dice["r"] > dice["w"] or dice["t"] < 0 or dice["b"] > dice["ih"]:
            findings.append(
                f"[{orientation}] dice button not fully inside the viewport "
                f"(box {dice['l']:.0f},{dice['t']:.0f}-{dice['r']:.0f},{dice['b']:.0f} "
                f"in {dice['w']}x{dice['ih']})")
        if dice["h"] < 44:
            findings.append(f"[{orientation}] dice button {dice['h']:.0f}px tall (< 44)")
    # The full-screen sheet must be closable from within (gate): the
    # desktop toggle is covered while it is open.
    close_button = page.locator("#btnSidebarClose")
    if not close_button.is_visible():
        findings.append(f"[{orientation}] sidebar sheet has no visible close button")
        page.keyboard.press("Escape")
    else:
        close_button.click()
        page.wait_for_timeout(250)
        if page.locator(".right-sidebar.is-open").count():
            findings.append(
                f"[{orientation}] sidebar close button left the mobile sheet open")


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="tools.robots.mobile")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    findings: list[str] = []
    workdir = Path(tempfile.mkdtemp(prefix="vtt-mobile-"))
    print(f"Mobile gates: disposable stack in {workdir} …")

    with disposable_stack(workdir) as stack:
        from playwright.sync_api import sync_playwright
        from tools.robots.session import RobotSession
        keys = mint_registration_keys(stack.database_url, count=1)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            desktop = browser.new_context(viewport={"width": 1440, "height": 900})
            session = RobotSession(desktop, base_url=stack.base_url,
                                   robot_name="mobil", artifacts_dir=workdir)
            session.open()
            if not session.register(username="mobil_gate_bot",
                                    email="mobil_gate_bot@robots.roll-drauf.de",
                                    password="Ro8ot-Test-Passw0rd!",
                                    registration_key=keys[0]):
                findings.extend(f"[setup] {f.detail}" for f in session.findings)
                browser.close()
                _write_report(args, workdir, findings)
                return 2

            api = desktop.request
            csrf = next(c["value"] for c in desktop.cookies()
                        if c["name"] == "csrf_access_token")
            headers = {"Content-Type": "application/json", "X-CSRF-TOKEN": csrf}
            campaign_id = api.post(
                f"{stack.base_url}/api/campaigns",
                data=json.dumps({"name": "Mobilgate", "max_players": 4}),
                headers=headers).json()["id"]
            session_id = api.post(
                f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
                data=json.dumps({"name": "Mobilgate S1"}), headers=headers).json()["id"]
            asset_id = api.post(
                f"{stack.base_url}/api/assets/campaigns/{campaign_id}/upload",
                multipart={"file": {"name": "gate.png", "mimeType": "image/png",
                                    "buffer": _make_png(700, 490, (70, 110, 60))}},
                headers={"X-CSRF-TOKEN": csrf}).json()["asset_id"]
            map_id = api.post(
                f"{stack.base_url}/api/campaigns/{campaign_id}/maps",
                data=json.dumps({"name": "Gatekarte", "width": 700, "height": 490,
                                 "grid_size": 70,
                                 "background_url": f"/api/assets/{asset_id}/preview"}),
                headers=headers).json()["id"]
            api.post(f"{stack.base_url}/api/campaigns/{campaign_id}"
                     f"/sessions/{session_id}/maps/activate",
                     data=json.dumps({"map_id": map_id}), headers=headers)
            api.post(f"{stack.base_url}/api/campaigns/{campaign_id}"
                     f"/sessions/{session_id}/tokens",
                     data=json.dumps({"name": "Gateheld", "x": 140, "y": 140,
                                      "token_type": "npc",
                                      "metadata_json": {"position_mode": "pixel"}}),
                     headers=headers)
            cookies = desktop.cookies()

            # Book pages, portrait: no horizontal overflow.
            portrait = _phone_context(browser, PHONE_PORTRAIT, cookies)
            page = portrait.new_page()
            for path in BOOK_PAGES:
                page.goto(f"{stack.base_url}{path}", wait_until="networkidle")
                page.wait_for_timeout(1200)
                overflow = page.evaluate(
                    "() => document.documentElement.scrollWidth - window.innerWidth")
                if overflow > 1:
                    findings.append(f"[portrait] {path}: {overflow}px horizontal overflow")

            play_url = f"{stack.base_url}/play?campaign_id={campaign_id}&session_id={session_id}"
            page.goto(play_url, wait_until="networkidle")
            page.wait_for_timeout(2500)
            page.screenshot(path=str(workdir / "gate-play-portrait.png"))
            _check_play_table(page, "portrait", findings)
            portrait.close()

            landscape = _phone_context(browser, PHONE_LANDSCAPE, cookies)
            page = landscape.new_page()
            page.goto(play_url, wait_until="networkidle")
            page.wait_for_timeout(2500)
            page.screenshot(path=str(workdir / "gate-play-landscape.png"))
            _check_play_table(page, "landscape", findings)
            landscape.close()
            browser.close()

    _write_report(args, workdir, findings)
    return 0 if not findings else 1


def _write_report(args, workdir: Path, findings: list[str]) -> None:
    print(f"\nmobile · {len(findings)} finding(s)")
    for finding in findings:
        print(f"  - {finding}")
    report = args.out or workdir / "vtt-mobile.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(
        {"status": "failed" if findings else "passed", "findings": findings},
        indent=2), encoding="utf-8")
    print(f"JSON: {report}")


if __name__ == "__main__":
    sys.exit(main())
