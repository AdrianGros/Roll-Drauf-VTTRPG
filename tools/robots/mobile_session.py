"""Mobile DM/player session robot.

This is the role-aware companion to ``tools.robots.mobile``.  The existing
mobile suite proves phone geometry with one owner-like account; this suite
proves that a DM and a player can use the live table from touch contexts
without leaking DM-only state.

    python -m tools.robots.mobile_session [--out FILE]
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from tools.robots.accounts import mint_registration_keys
from tools.robots.fullsession import GRID, _make_png
from tools.robots.mobile import PHONE_LANDSCAPE, PHONE_PORTRAIT
from tools.robots.session import RobotSession
from tools.robots.stack import disposable_stack

STEP_TIMEOUT_MS = 15_000


def _phone_context(browser, viewport, cookies=None):
    context = browser.new_context(
        viewport=viewport,
        device_scale_factor=3,
        is_mobile=True,
        has_touch=True,
    )
    if cookies:
        context.add_cookies(cookies)
    return context


class MobileSessionScript:
    def __init__(self, stack, workdir: Path):
        self.stack = stack
        self.workdir = workdir
        self.findings: list[str] = []
        self.browser = None
        self.dm: RobotSession | None = None
        self.player: RobotSession | None = None
        self.campaign_id = None
        self.session_id = None

    def fail(self, step: str, detail: str, page=None) -> None:
        shot = ""
        if page is not None:
            try:
                path = self.workdir / f"mobile-session-{step}-{len(self.findings)}.png"
                page.screenshot(path=str(path))
                shot = f" (screenshot: {path.name})"
            except Exception:
                pass
        self.findings.append(f"[{step}] {detail}{shot}")

    def _csrf(self, context) -> str | None:
        return next((c["value"] for c in context.cookies()
                     if c["name"] == "csrf_access_token"), None)

    def _headers(self, context) -> dict:
        return {"Content-Type": "application/json",
                "X-CSRF-TOKEN": self._csrf(context)}

    def _wait_text(self, page, element_id: str, needle: str, step: str) -> bool:
        try:
            page.wait_for_function(
                "([id, needle]) => (document.getElementById(id)?.textContent || '').includes(needle)",
                arg=[element_id, needle], timeout=STEP_TIMEOUT_MS)
            return True
        except Exception:
            self.fail(step, f"#{element_id} never contained {needle!r}", page)
            return False

    def _open_sidebar(self, page, tab: str) -> bool:
        try:
            if not page.locator(".right-sidebar.is-open").count():
                page.click("#btnSidebarToggle")
                page.wait_for_selector(".right-sidebar.is-open", timeout=STEP_TIMEOUT_MS)
            page.click(f'.sidebar-tab[data-tab="{tab}"]')
            return True
        except Exception as error:
            self.fail("sidebar", f"could not open {tab!r}: {error}", page)
            return False

    def _map_point(self, page, cell_x: int, cell_y: int) -> tuple[float, float]:
        box = page.locator("#mapWorld").bounding_box()
        map_width = float(page.locator("#mapWorld").get_attribute("data-map-width") or 700)
        scale = box["width"] / map_width
        return (box["x"] + (cell_x * GRID + GRID / 2) * scale,
                box["y"] + (cell_y * GRID + GRID / 2) * scale)

    def _touch_place_token(self, page, *, cell: tuple[int, int], name: str) -> bool:
        try:
            page.click('.tool-btn[data-tool="token"]')
            x, y = self._map_point(page, *cell)
            page.touchscreen.tap(x, y)
            page.wait_for_selector("#tokenCreatePanel:not([hidden])",
                                   timeout=STEP_TIMEOUT_MS)
            page.fill("#tokenCreateName", name)
            page.click("#btnTokenCreateConfirm")
            page.wait_for_selector(f'.token-marker[title="{name}"]',
                                   state="attached", timeout=STEP_TIMEOUT_MS)
            page.click('.tool-btn[data-tool="select"]')
            return True
        except Exception as error:
            self.fail("player-token", f"touch token placement failed: {error}", page)
            return False

    def setup(self, playwright) -> bool:
        keys = mint_registration_keys(self.stack.database_url, count=2)
        self.browser = playwright.chromium.launch()

        dm_context = _phone_context(self.browser, PHONE_PORTRAIT)
        self.dm = RobotSession(dm_context, base_url=self.stack.base_url,
                               robot_name="mobile_dm", artifacts_dir=self.workdir)
        self.dm.open()
        if not self.dm.register(username="mobile_dm_bot",
                                email="mobile_dm_bot@robots.roll-drauf.de",
                                password="Ro8ot-Test-Passw0rd!",
                                registration_key=keys[0]):
            self.findings.extend(f"[setup-dm] {f.detail}" for f in self.dm.findings)
            return False

        player_context = _phone_context(self.browser, PHONE_PORTRAIT)
        self.player = RobotSession(
            player_context, base_url=self.stack.base_url,
            robot_name="mobile_player", artifacts_dir=self.workdir)
        self.player.open()
        if not self.player.register(username="mobile_player_bot",
                                    email="mobile_player_bot@robots.roll-drauf.de",
                                    password="Ro8ot-Test-Passw0rd!",
                                    registration_key=keys[1]):
            self.findings.extend(f"[setup-player] {f.detail}" for f in self.player.findings)
            return False

        self.dm.page.on("dialog", lambda dialog: dialog.accept())
        self.player.page.on("dialog", lambda dialog: dialog.accept())

        dm_api = dm_context.request
        campaign_response = dm_api.post(
            f"{self.stack.base_url}/api/campaigns",
            data=json.dumps({"name": "Mobile Rollenrunde", "max_players": 4}),
            headers=self._headers(dm_context))
        if campaign_response.status != 201:
            self.fail("setup", f"campaign returned HTTP {campaign_response.status}")
            return False
        campaign = campaign_response.json()
        self.campaign_id = (campaign.get("campaign") or campaign)["id"]

        invite = dm_api.post(
            f"{self.stack.base_url}/api/campaigns/{self.campaign_id}/invite",
            data=json.dumps({"player_username": "mobile_player_bot"}),
            headers=self._headers(dm_context))
        if invite.status not in (200, 201):
            self.fail("invite", f"invite returned HTTP {invite.status}: {invite.text()[:200]}")
            return False
        accept = self.player.context.request.post(
            f"{self.stack.base_url}/api/campaigns/{self.campaign_id}/accept-invite",
            data=json.dumps({"token": invite.json()["invite_token"]}),
            headers=self._headers(self.player.context))
        if accept.status != 200:
            self.fail("invite", f"accept-invite returned HTTP {accept.status}: {accept.text()[:200]}")
            return False

        session_response = dm_api.post(
            f"{self.stack.base_url}/api/campaigns/{self.campaign_id}/sessions",
            data=json.dumps({"name": "Mobile Rollenrunde I"}),
            headers=self._headers(dm_context))
        if session_response.status != 201:
            self.fail("setup", f"session returned HTTP {session_response.status}: {session_response.text()[:200]}")
            return False
        body = session_response.json()
        self.session_id = (body.get("session") or body)["id"]

        asset = dm_api.post(
            f"{self.stack.base_url}/api/assets/campaigns/{self.campaign_id}/upload",
            multipart={"file": {"name": "mobile_map.png", "mimeType": "image/png",
                                 "buffer": _make_png(self.workdir / "mobile_map.png", 700, 490, (60, 100, 70)).read_bytes()}},
            headers={"X-CSRF-TOKEN": self._csrf(dm_context)})
        if asset.status != 201:
            self.fail("setup", f"map asset returned HTTP {asset.status}: {asset.text()[:200]}")
            return False
        map_response = dm_api.post(
            f"{self.stack.base_url}/api/campaigns/{self.campaign_id}/maps",
            data=json.dumps({"name": "Mobilekarte", "width": 700, "height": 490,
                             "grid_size": 70,
                             "background_url": f"/api/assets/{asset.json()['asset_id']}/preview"}),
            headers=self._headers(dm_context))
        if map_response.status != 201:
            self.fail("setup", f"map creation returned HTTP {map_response.status}: {map_response.text()[:200]}")
            return False
        map_id = (map_response.json().get("map") or map_response.json())["id"]
        activate = dm_api.post(
            f"{self.stack.base_url}/api/campaigns/{self.campaign_id}/sessions/{self.session_id}/maps/activate",
            data=json.dumps({"map_id": map_id}), headers=self._headers(dm_context))
        if activate.status != 200:
            self.fail("setup", f"map activation returned HTTP {activate.status}: {activate.text()[:200]}")
            return False

        for name, visibility in (("Wachposten", "public"), ("Geheimboss", "dm_only")):
            token = dm_api.post(
                f"{self.stack.base_url}/api/campaigns/{self.campaign_id}/sessions/{self.session_id}/tokens",
                data=json.dumps({"name": name, "x": 140 if visibility == "public" else 350,
                                 "y": 140, "token_type": "npc",
                                 "visibility": visibility,
                                 "metadata_json": {"position_mode": "pixel"}}),
                headers=self._headers(dm_context))
            if token.status != 201:
                self.fail("setup", f"{name} token returned HTTP {token.status}: {token.text()[:200]}")
                return False
        return True

    def open_tables(self) -> bool:
        path = f"/play?campaign_id={self.campaign_id}&session_id={self.session_id}"
        for robot, label in ((self.dm, "dm"), (self.player, "player")):
            if not robot.goto(path):
                self.findings.extend(f"[{label}-play] {f.detail}" for f in robot.findings)
                return False
            try:
                robot.page.wait_for_selector("#mapImage", state="visible", timeout=STEP_TIMEOUT_MS)
                robot.page.wait_for_selector("#mapViewport", state="visible", timeout=STEP_TIMEOUT_MS)
            except Exception as error:
                self.fail(f"{label}-play", f"map never rendered: {error}", robot.page)
                return False
        return True

    def start_from_dm_phone(self) -> bool:
        page = self.dm.page
        if not self._open_sidebar(page, "session"):
            return False
        try:
            page.click("#btnReadyCheck")
            self._wait_text(page, "readyCheckOutput", "Kann starten", "ready-check")
            page.click("#btnToReady")
            self._wait_text(page, "sessionStatusPill", "ready", "lifecycle")
            page.click("#btnStart")
            return self._wait_text(page, "sessionStatusPill", "in_progress", "lifecycle")
        except Exception as error:
            self.fail("lifecycle", f"DM could not start session on phone: {error}", page)
            return False

    def verify_player_and_sync(self) -> bool:
        dm_page = self.dm.page
        player_page = self.player.page
        try:
            player_page.wait_for_selector('.token-marker[title="Wachposten"]',
                                          state="attached", timeout=STEP_TIMEOUT_MS)
        except Exception:
            self.fail("player-view", "player never saw the public token", player_page)
            return False
        leaks = player_page.evaluate(
            """() => {
                const spots = [];
                if (document.querySelector('.token-marker[title="Geheimboss"]')) spots.push('map marker');
                if ((document.getElementById('tokenList')?.textContent || '').includes('Geheimboss')) spots.push('token list');
                if ((document.getElementById('turnOrderList')?.textContent || '').includes('Geheimboss')) spots.push('turn order');
                return spots;
            }""")
        if leaks:
            self.fail("dm-layer-leak", f"DM-only token visible to player in: {', '.join(leaks)}", player_page)
        if player_page.locator(".token-marker").count() != 1:
            self.fail("player-view", "player should see exactly one public token", player_page)

        if not self._touch_place_token(player_page, cell=(5, 4), name="Handyheld"):
            return False
        try:
            dm_page.wait_for_selector('.token-marker[title="Handyheld"]',
                                      state="attached", timeout=STEP_TIMEOUT_MS)
        except Exception:
            self.fail("sync", "player token never reached DM phone table", dm_page)
            return False

        if not self._open_sidebar(player_page, "chat"):
            return False
        player_page.fill("#chatInput", "Angriff vom Telefon!")
        player_page.click("#btnSendChat")
        self._wait_text(player_page, "chatLog", "Angriff vom Telefon!", "chat")
        self._wait_text(dm_page, "chatLog", "Angriff vom Telefon!", "chat")

        if not self._open_sidebar(dm_page, "tools"):
            return False
        dm_page.fill("#diceInput", "1d20+2")
        dm_page.click("#btnRoll")
        self._wait_text(dm_page, "diceResult", "1d20+2 ->", "dice")
        self._wait_text(player_page, "diceLog", "gewürfelt", "dice")
        return True

    def check_landscape_role_surfaces(self) -> bool:
        path = f"/play?campaign_id={self.campaign_id}&session_id={self.session_id}"
        contexts = []
        try:
            for robot, label in ((self.dm, "dm"), (self.player, "player")):
                landscape = _phone_context(self.browser, PHONE_LANDSCAPE,
                                           robot.context.cookies())
                contexts.append(landscape)
                page = landscape.new_page()
                page.goto(f"{self.stack.base_url}{path}", wait_until="networkidle")
                page.wait_for_timeout(1200)
                viewport = page.locator("#mapViewport").bounding_box()
                if not viewport or viewport["width"] < PHONE_LANDSCAPE["width"] * 0.55:
                    self.fail("landscape", f"{label} map does not own at least 55% of phone width", page)
                if label == "player":
                    leaks = page.locator('.token-marker[title="Geheimboss"]').count()
                    if leaks:
                        self.fail("dm-layer-leak", "landscape player sees DM-only token", page)
                page.screenshot(path=str(self.workdir / f"mobile-session-{label}-landscape.png"))
        finally:
            for context in contexts:
                context.close()
        return True

    def end_from_dm_phone(self) -> bool:
        page = self.dm.page
        if not self._open_sidebar(page, "session"):
            return False
        page.click("#btnEnd")
        ok = self._wait_text(page, "sessionStatusPill", "ended", "end")
        ok = self._wait_text(self.player.page, "sessionStatusPill", "ended", "end") and ok
        return ok

    def run(self) -> list[str]:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            if self.setup(playwright):
                for phase in (self.open_tables, self.start_from_dm_phone,
                              self.verify_player_and_sync,
                              self.check_landscape_role_surfaces,
                              self.end_from_dm_phone):
                    if not phase():
                        break
            if self.dm:
                self.findings.extend(f"[{f.kind}] {f.detail}" for f in self.dm.findings)
            if self.player:
                self.findings.extend(f"[{f.kind}] {f.detail}" for f in self.player.findings)
            if self.browser:
                self.browser.close()
        return self.findings


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="tools.robots.mobile_session")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    workdir = Path(tempfile.mkdtemp(prefix="vtt-mobile-session-"))
    print(f"Mobile session: disposable stack in {workdir} …")

    with disposable_stack(workdir) as stack:
        findings = MobileSessionScript(stack, workdir).run()

    print(f"\nmobile_session · {len(findings)} finding(s)")
    for finding in findings:
        print(f"  - {finding}")
    report = args.out or workdir / "vtt-mobile-session.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(
        {"status": "failed" if findings else "passed",
         "findings": findings}, indent=2), encoding="utf-8")
    print(f"JSON: {report}")
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
