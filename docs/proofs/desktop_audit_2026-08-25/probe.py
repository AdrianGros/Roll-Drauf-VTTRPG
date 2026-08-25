"""Desktop-browser audit probe for the mission-critical journey.

Mirrors the 2026-08-24 mobile audit's method (hard measurements, no
impressions) but at desktop viewports, and — new — walks the DM/player
journey THROUGH THE REAL UI (register, create campaign, invite,
accept, quickstart to the table), because fullsession does campaign +
invite via API and would never notice a broken button there.

Run:  cd /home/admin/projects/roll-drauf-vtt && venv/bin/python <this file>
"""
from __future__ import annotations

import json
import struct
import sys
import tempfile
import traceback
import zlib
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO = Path("/home/admin/projects/roll-drauf-vtt")
sys.path.insert(0, str(REPO))

from tools.robots.accounts import mint_registration_keys  # noqa: E402
from tools.robots.evidence import capture as capture_evidence  # noqa: E402
from tools.robots.stack import disposable_stack  # noqa: E402

SCRATCH = Path(__file__).parent
OUT = SCRATCH / "desktop-audit"
OUT.mkdir(exist_ok=True)

VIEWPORTS = [
    (1024, 768), (1199, 900), (1201, 900), (1280, 720),
    (1366, 768), (1440, 900), (1920, 1080), (2560, 1440),
]
BOOK_PAGES = ["/login.html", "/dashboard", "/campaigns", "/characters"]

findings: list[str] = []
metrics: list[dict] = []
journey_log: list[str] = []


def _png_bytes(width, height, rgb):
    def chunk(tag, data):
        piece = struct.pack(">I", len(data)) + tag + data
        return piece + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


MEASURE_JS = """() => {
    const r = {};
    r.innerW = window.innerWidth; r.innerH = window.innerHeight;
    r.scrollW = document.documentElement.scrollWidth;
    r.scrollH = document.documentElement.scrollHeight;
    r.hOverflow = r.scrollW - r.innerW;
    const els = [...document.querySelectorAll('button, a[href], input, select, textarea, [role=button]')];
    r.clipped = [];
    for (const el of els) {
        const cs = getComputedStyle(el);
        if (cs.visibility === 'hidden' || cs.display === 'none') continue;
        const b = el.getBoundingClientRect();
        if (b.width === 0 && b.height === 0) continue;
        const partialRight = b.left < r.innerW - 1 && b.right > r.innerW + 1;
        const partialLeft = b.left < -1 && b.right > 1;
        if (partialRight || partialLeft) {
            r.clipped.push({
                label: (el.id ? '#' + el.id : (el.textContent || el.tagName).trim().slice(0, 30)),
                l: Math.round(b.left), rgt: Math.round(b.right)});
        }
    }
    r.clipped = r.clipped.slice(0, 8);
    return r;
}"""

PLAY_JS = """() => {
    const r = {};
    r.innerW = window.innerWidth; r.innerH = window.innerHeight;
    const vp = document.getElementById('mapViewport');
    r.mapW = vp ? vp.getBoundingClientRect().width : 0;
    r.mapH = vp ? vp.getBoundingClientRect().height : 0;
    const grab = id => {
        const el = document.getElementById(id);
        if (!el) return null;
        const b = el.getBoundingClientRect();
        return {l: Math.round(b.left), t: Math.round(b.top),
                r: Math.round(b.right), b: Math.round(b.bottom),
                w: Math.round(b.width), h: Math.round(b.height),
                hidden: el.hidden || getComputedStyle(el).display === 'none'};
    };
    r.widgets = {};
    for (const id of ['layersWidget', 'turnOrderWidget', 'tokenWidget'])
        r.widgets[id] = grab(id);
    r.controls = {};
    for (const id of ['btnZoomFit', 'zoomRange', 'btnRoll', 'chatInput', 'btnSendChat'])
        r.controls[id] = grab(id);
    const closeBtn = document.getElementById('btnSidebarClose');
    const aside = closeBtn ? closeBtn.closest('aside, .sidebar, div[id*=idebar]') : null;
    r.sidebar = aside ? (() => { const b = aside.getBoundingClientRect();
        return {l: Math.round(b.left), t: Math.round(b.top), r: Math.round(b.right),
                b: Math.round(b.bottom), id: aside.id || aside.className}; })() : null;
    return r;
}"""


def overlap_area(a, b):
    if not a or not b:
        return 0
    w = min(a["r"], b["r"]) - max(a["l"], b["l"])
    h = min(a["b"], b["b"]) - max(a["t"], b["t"])
    return max(0, w) * max(0, h)


def shot(page, name, marks=None):
    try:
        return capture_evidence(page, OUT, name, marks=marks)
    except Exception:
        return None


def finding(page, detail, name, marks=None):
    path = shot(page, name, marks=marks or ["body"])
    if path:
        findings.append(f"{detail} (screenshot: {path})")
    else:
        findings.append(f"{detail} (screenshot failed)")


def watch_console(page, bucket):
    page.on("console", lambda m: bucket.append(m.text[:160]) if m.type == "error" else None)
    page.on("pageerror", lambda e: bucket.append(str(e)[:160]))


def main() -> int:
    workdir = Path(tempfile.mkdtemp(prefix="vtt-desktop-"))
    print(f"stack in {workdir} ...", flush=True)
    with disposable_stack(workdir) as stack:
        from playwright.sync_api import sync_playwright
        from tools.robots.session import RobotSession
        keys = mint_registration_keys(stack.database_url, count=2)

        with sync_playwright() as pw:
            browser = pw.chromium.launch()

            # ---------- Part A: the journey through the real UI ----------
            dm_ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            pc_ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            dm = RobotSession(dm_ctx, base_url=stack.base_url, robot_name="desk_dm",
                              artifacts_dir=workdir)
            pc = RobotSession(pc_ctx, base_url=stack.base_url, robot_name="desk_pc",
                              artifacts_dir=workdir)
            dm.open(); pc.open()
            dm_errors: list[str] = []; pc_errors: list[str] = []
            watch_console(dm.page, dm_errors); watch_console(pc.page, pc_errors)

            if not dm.register(username="desk_dm_bot",
                               email="desk_dm_bot@robots.roll-drauf.de",
                               password="Ro8ot-Test-Passw0rd!", registration_key=keys[0]):
                finding(
                    dm.page,
                    "[journey] DM registration via UI FAILED: "
                    + "; ".join(f.detail for f in dm.findings),
                    "finding-journey-dm-registration", ["#registerForm", "body"])
            else:
                journey_log.append("DM registered via real UI form")
            if not pc.register(username="desk_pc_bot",
                               email="desk_pc_bot@robots.roll-drauf.de",
                               password="Ro8ot-Test-Passw0rd!", registration_key=keys[1]):
                finding(
                    pc.page,
                    "[journey] Player registration via UI FAILED: "
                    + "; ".join(f.detail for f in pc.findings),
                    "finding-journey-player-registration", ["#registerForm", "body"])
            else:
                journey_log.append("Player registered via real UI form")

            page = dm.page
            campaign_id = None
            invite_token = {"value": None}

            def journey_step(name, fn, fail_page=None):
                try:
                    fn()
                    journey_log.append(f"OK: {name}")
                    return True
                except Exception as exc:
                    finding(
                        fail_page or page,
                        f"[journey] {name} FAILED: {exc.__class__.__name__}: "
                        f"{str(exc).splitlines()[0][:200]}",
                        f"finding-journey-FAIL-{name.replace(' ', '_')[:40]}")
                    return False

            def do_create_campaign():
                # Click what the user SEES (the book-scene render), never the
                # buried template markup — duplicate-id hazard is part of the test.
                page.goto(f"{stack.base_url}/campaigns", wait_until="networkidle")
                page.wait_for_timeout(800)
                page.get_by_role("button", name="Neue Kampagne anlegen").first.click(timeout=8000)
                page.wait_for_timeout(400)
                shot(page, "journey-create-form-open")
                page.locator("#campaignCreateName:visible").first.fill(
                    "Desktop Audit Kampagne", timeout=8000)
                page.locator("#campaignCreateSubmit:visible").first.click(timeout=8000)
                page.wait_for_selector("#inviteUsername:visible", timeout=10000)
                shot(page, "journey-hub-after-create")
            created = journey_step("create campaign via UI (opens hub)", do_create_campaign)

            if created:
                def on_dialog(dialog):
                    if dialog.type == "prompt" and dialog.default_value:
                        invite_token["value"] = dialog.default_value
                    dialog.accept()
                page.on("dialog", on_dialog)

                def do_invite():
                    page.locator("#inviteUsername:visible").first.fill(
                        "desk_pc_bot", timeout=8000)
                    page.get_by_role("button", name="Einladung erzeugen").first.click(
                        timeout=8000)
                    page.wait_for_timeout(1200)
                    if not invite_token["value"]:
                        raise RuntimeError("no invite token appeared (window.prompt not shown "
                                           "or empty)")
                journey_step("DM generates invite via UI", do_invite)

            if invite_token["value"]:
                ppage = pc.page

                VISIBLE_ACTIONS_JS = """() => {
                    const out = [];
                    for (const el of document.querySelectorAll('button, a[href]')) {
                        const cs = getComputedStyle(el);
                        if (cs.display === 'none' || cs.visibility === 'hidden') continue;
                        const b = el.getBoundingClientRect();
                        if (b.width === 0 || b.height === 0) continue;
                        const t = (el.textContent || '').trim().replace(/\\s+/g, ' ');
                        if (t) out.push(t.slice(0, 40));
                    }
                    return [...new Set(out)].slice(0, 50);
                }"""

                def do_accept():
                    import re as _re
                    ppage.goto(f"{stack.base_url}/campaigns", wait_until="networkidle")
                    ppage.wait_for_timeout(800)
                    acts = ppage.evaluate(VISIBLE_ACTIONS_JS)
                    journey_log.append(f"player /campaigns visible actions: {acts}")
                    entry = ppage.locator("text=Desktop Audit Kampagne")
                    entry.first.click(timeout=8000)
                    ppage.wait_for_timeout(1000)
                    shot(ppage, "journey-pc-campaign-entry")
                    acts2 = ppage.evaluate(VISIBLE_ACTIONS_JS)
                    journey_log.append(f"player after campaign click: {acts2}")
                    join = ppage.locator("button:visible, a:visible").filter(
                        has_text=_re.compile(r"beitreten|join", _re.I))
                    if join.count() == 0:
                        journey_log.append(
                            "NO join affordance in the book view -> trying the legacy "
                            "escape hatch: Hub öffnen -> Alle tab")
                        ppage.locator("button:visible").filter(
                            has_text=_re.compile(r"Hub öffnen")).first.click(timeout=8000)
                        ppage.wait_for_timeout(1200)
                        ppage.locator("button:visible").filter(
                            has_text=_re.compile(r"^\s*Alle\s*$")).first.click(timeout=8000)
                        ppage.wait_for_timeout(1000)
                        shot(ppage, "journey-pc-legacy-alle-tab")
                        acts3 = ppage.evaluate(VISIBLE_ACTIONS_JS)
                        journey_log.append(f"player legacy Alle tab actions: {acts3}")
                        join = ppage.locator("button:visible, a:visible").filter(
                            has_text=_re.compile(r"beitreten|join", _re.I))
                    if join.count() == 0:
                        raise RuntimeError(
                            f"no visible join affordance anywhere; actions were {acts2[:20]}")
                    ppage.once("dialog", lambda d: d.accept(invite_token["value"]))
                    join.first.click(timeout=8000)
                    ppage.wait_for_timeout(1500)
                    shot(ppage, "journey-pc-after-join")
                journey_step("player accepts invite via UI (Alle tab -> Beitreten -> prompt)",
                             do_accept, fail_page=ppage)

            def _unused():
                def do_player_to_table():
                    ppage.goto(f"{stack.base_url}/campaigns", wait_until="networkidle")
                    ppage.wait_for_timeout(800)
                    import re as _re
                    ppage.locator("button:visible").filter(
                        has_text=_re.compile(r"^\s*Hub öffnen\s*$")).first.click(timeout=8000)
                    ppage.wait_for_timeout(1200)
                    shot(ppage, "journey-pc-hub")
                    ppage.locator("button:visible, a:visible").filter(
                        has_text=_re.compile(r"Session betreten|Play|Tisch")).first.click(
                        timeout=8000)
                    ppage.wait_for_url("**/play*", timeout=15000)
                    ppage.wait_for_timeout(2000)
                    shot(ppage, "journey-pc-table")
                journey_step("player reaches the table via UI (hub -> session)",
                             do_player_to_table, fail_page=ppage)

            play_url = {"value": None}
            if created:
                def do_quickstart():
                    page.locator("#quickMapFile:visible").first.set_input_files(
                        files=[{"name": "audit-map.png", "mimeType": "image/png",
                                "buffer": _png_bytes(700, 490, (70, 110, 60))}],
                        timeout=8000)
                    page.locator("#quickStartButton:visible").first.click(timeout=8000)
                    page.wait_for_url("**/play*", timeout=20000)
                    play_url["value"] = page.url
                    shot(page, "journey-dm-table-after-quickstart")
                journey_step("DM quickstart: session + map + start + table open", do_quickstart)

            if invite_token["value"] and play_url["value"]:
                ppage = pc.page

                def do_player_to_table2():
                    import re as _re
                    ppage.goto(f"{stack.base_url}/campaigns", wait_until="networkidle")
                    ppage.wait_for_timeout(800)
                    ppage.locator("button:visible").filter(
                        has_text=_re.compile(r"Hub öffnen")).first.click(timeout=8000)
                    ppage.wait_for_timeout(1200)
                    shot(ppage, "journey-pc-hub")
                    acts = ppage.evaluate(VISIBLE_ACTIONS_JS)
                    journey_log.append(f"player hub visible actions: {acts}")
                    ppage.locator("button:visible, a:visible").filter(
                        has_text=_re.compile(r"Session betreten|Play|Tisch|fortsetzen")
                        ).first.click(timeout=8000)
                    ppage.wait_for_url("**/play*", timeout=15000)
                    ppage.wait_for_timeout(2000)
                    shot(ppage, "journey-pc-table")
                journey_step("player reaches the table via UI (hub -> session)",
                             do_player_to_table2, fail_page=ppage)

            if play_url["value"]:
                q = parse_qs(urlparse(play_url["value"]).query)
                campaign_id = q.get("campaign_id", [None])[0]
                session_id = q.get("session_id", [None])[0]
            else:
                campaign_id = session_id = None

            if dm_errors:
                finding(page, f"[journey] DM console errors: {dm_errors[:5]}",
                        "finding-journey-dm-console-errors")
            if pc_errors:
                finding(pc.page, f"[journey] player console errors: {pc_errors[:5]}",
                        "finding-journey-player-console-errors")

            # Fallback so Part B can still measure the table.
            if not campaign_id:
                api = dm_ctx.request
                csrf = next(c["value"] for c in dm_ctx.cookies()
                            if c["name"] == "csrf_access_token")
                headers = {"Content-Type": "application/json", "X-CSRF-TOKEN": csrf}
                campaign_id = api.post(f"{stack.base_url}/api/campaigns",
                                       data=json.dumps({"name": "Messkampagne",
                                                        "max_players": 4}),
                                       headers=headers).json()["id"]
                session_id = api.post(
                    f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
                    data=json.dumps({"name": "Mess S1"}), headers=headers).json()["id"]
                asset_id = api.post(
                    f"{stack.base_url}/api/assets/campaigns/{campaign_id}/upload",
                    multipart={"file": {"name": "m.png", "mimeType": "image/png",
                                        "buffer": _png_bytes(700, 490, (70, 110, 60))}},
                    headers={"X-CSRF-TOKEN": csrf}).json()["asset_id"]
                map_id = api.post(
                    f"{stack.base_url}/api/campaigns/{campaign_id}/maps",
                    data=json.dumps({"name": "Messkarte", "width": 700, "height": 490,
                                     "grid_size": 70,
                                     "background_url": f"/api/assets/{asset_id}/preview"}),
                    headers=headers).json()["id"]
                api.post(f"{stack.base_url}/api/campaigns/{campaign_id}"
                         f"/sessions/{session_id}/maps/activate",
                         data=json.dumps({"map_id": map_id}), headers=headers)
                journey_log.append("(table for Part B built via API fallback)")

            play_path = f"/play?campaign_id={campaign_id}&session_id={session_id}"
            dm_cookies = dm_ctx.cookies()

            # ---------- Part B: geometry matrix ----------
            for (w, h) in ([] if "--journey-only" in sys.argv else VIEWPORTS):
                ctx = browser.new_context(viewport={"width": w, "height": h})
                ctx.add_cookies(dm_cookies)
                mpage = ctx.new_page()
                errors: list[str] = []
                watch_console(mpage, errors)
                for path in BOOK_PAGES + [play_path]:
                    is_play = path.startswith("/play")
                    try:
                        mpage.goto(f"{stack.base_url}{path}",
                                   wait_until="networkidle", timeout=30000)
                        mpage.wait_for_timeout(1500 if not is_play else 2500)
                        shot(mpage, f"view-{w}x{h}-{path}")
                        m = mpage.evaluate(MEASURE_JS)
                        row = {"viewport": f"{w}x{h}", "page": "/play" if is_play else path,
                               "hOverflow": m["hOverflow"], "scrollH": m["scrollH"],
                               "screens": round(m["scrollH"] / m["innerH"], 1),
                               "clipped": m["clipped"], "consoleErrors": len(errors)}
                        if is_play:
                            p = mpage.evaluate(PLAY_JS)
                            row["mapW"] = p["mapW"]
                            row["mapShare"] = round(p["mapW"] / p["innerW"], 2)
                            row["widgets"] = p["widgets"]
                            row["controlsClosed"] = p["controls"]
                            # widget-vs-widget overlaps (closed sidebar state)
                            wid = {k: v for k, v in p["widgets"].items()
                                   if v and not v["hidden"]}
                            names = list(wid)
                            for i in range(len(names)):
                                for j in range(i + 1, len(names)):
                                    a, b = wid[names[i]], wid[names[j]]
                                    ov = overlap_area(a, b)
                                    if ov > 100:
                                        finding(
                                            mpage,
                                            f"[{w}x{h}] /play widgets overlap: "
                                            f"{names[i]}/{names[j]} ({ov}px^2)",
                                            f"finding-{w}x{h}-widgets-{names[i]}-{names[j]}",
                                            [f"#{names[i]}", f"#{names[j]}"])
                            # open sidebar -> tools tab, remeasure
                            mpage.click("#btnSidebarToggle")
                            mpage.click('.sidebar-tab[data-tab="tools"]')
                            mpage.wait_for_timeout(500)
                            p2 = mpage.evaluate(PLAY_JS)
                            row["sidebar"] = p2["sidebar"]
                            row["controlsOpen"] = p2["controls"]
                            if p2["sidebar"]:
                                for name, wrect in (p2["widgets"] or {}).items():
                                    if wrect and not wrect["hidden"]:
                                        ov = overlap_area(p2["sidebar"], wrect)
                                        if ov > 100:
                                            finding(
                                                mpage,
                                                f"[{w}x{h}] /play open sidebar covers "
                                                f"{name} ({ov}px^2)",
                                                f"finding-{w}x{h}-sidebar-covers-{name}",
                                                [".right-sidebar", f"#{name}"])
                            m_open = mpage.evaluate(MEASURE_JS)
                            if m_open["clipped"]:
                                finding(
                                    mpage,
                                    f"[{w}x{h}] /play (sidebar open): clipped controls: "
                                    + ", ".join(f"{c['label']}({c['l']}..{c['rgt']})"
                                                for c in m_open["clipped"]),
                                    f"finding-{w}x{h}-play-sidebar-clipped",
                                    ["button", "input", "select"])
                            roll = p2["controls"].get("btnRoll")
                            if not roll or roll["hidden"] or roll["w"] == 0:
                                finding(
                                    mpage,
                                    f"[{w}x{h}] /play dice button missing/"
                                    "zero-size with tools tab open",
                                    f"finding-{w}x{h}-dice-missing", ["#btnRoll"])
                            elif roll["r"] > p2["innerW"] or roll["b"] > p2["innerH"] \
                                    or roll["l"] < 0 or roll["t"] < 0:
                                finding(
                                    mpage,
                                    f"[{w}x{h}] /play dice button outside viewport: {roll}",
                                    f"finding-{w}x{h}-dice-outside", ["#btnRoll"])
                            mpage.click('.sidebar-tab[data-tab="chat"]')
                            mpage.wait_for_timeout(300)
                            p3 = mpage.evaluate(PLAY_JS)
                            chat = p3["controls"].get("chatInput")
                            send = p3["controls"].get("btnSendChat")
                            for nm, c in (("chat input", chat), ("chat send", send)):
                                if not c or c["hidden"] or c["w"] == 0 or c["h"] == 0:
                                    finding(
                                        mpage,
                                        f"[{w}x{h}] /play {nm} zero-size/"
                                        "missing with chat tab open",
                                        f"finding-{w}x{h}-chat-{nm.replace(' ', '-')}",
                                        ["#chatInput", "#btnSendChat"])
                            shot(mpage, f"play-{w}x{h}")
                        if m["hOverflow"] > 1:
                            finding(
                                mpage,
                                f"[{w}x{h}] {row['page']}: "
                                f"{m['hOverflow']}px horizontal overflow",
                                f"finding-{w}x{h}-{row['page']}-overflow", ["body"])
                        if m["clipped"]:
                            finding(
                                mpage,
                                f"[{w}x{h}] {row['page']}: clipped controls: "
                                + ", ".join(f"{c['label']}({c['l']}..{c['rgt']})"
                                            for c in m["clipped"]),
                                f"finding-{w}x{h}-{row['page']}-clipped",
                                ["button", "input", "select"])
                        metrics.append(row)
                    except Exception as exc:
                        finding(
                            mpage,
                            f"[{w}x{h}] {path} measurement crashed: "
                            f"{exc.__class__.__name__}: "
                            f"{str(exc).splitlines()[0][:160]}",
                            f"finding-{w}x{h}-measurement-crashed")
                if errors:
                    finding(
                        mpage,
                        f"[{w}x{h}] console errors across pages: "
                        f"{len(errors)} (first: {errors[0]})",
                        f"finding-{w}x{h}-console-errors")
                ctx.close()
            browser.close()

    screenshots = sorted(
        str(path.relative_to(OUT)) for path in OUT.glob("*.png"))
    report = {"journey": journey_log, "findings": findings,
              "metrics": metrics, "screenshots": screenshots}
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\n=== JOURNEY ===")
    for line in journey_log:
        print(" ", line)
    print(f"\n=== FINDINGS ({len(findings)}) ===")
    for f in findings:
        print(" -", f)
    print(f"\nscreenshots: {len(screenshots)}")
    print(f"report: {OUT / 'report.json'}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
