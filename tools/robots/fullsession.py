"""A complete play session, driven through the real UI in two browsers.

The most end-to-end thing the suite owns (built 2026-08-23, on the
user's request for exactly this scenario): a Dungeon Master and a
player, side by side, playing an actual session --

  DM:  register -> campaign -> invite -> session -> open the table ->
       upload THREE real map files through the table's own upload
       control -> switch between the pages -> place a public token and
       a DM-only token -> ready-check -> live start -> roll initiative
       -> execute an action -> roll dice -> end the session.
  PC:  register -> accept invite -> join the live table -> must see the
       public token but NEVER the DM-only one (map, token list, turn
       order) -> place their own hero token -> drag it across the grid
       -> chat -> and watch every DM action arrive in real time.

Every step asserts on what the OTHER browser can see, because the
entire point of a VTT table is that both ends stay in sync.

    python -m tools.robots.fullsession [--out FILE]
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

GRID = 70
STEP_TIMEOUT_MS = 15_000


def _make_png(path: Path, width: int, height: int, rgb: tuple[int, int, int]) -> Path:
    def chunk(tag, data):
        piece = struct.pack(">I", len(data)) + tag + data
        return piece + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b""
    row = bytes(rgb) * width
    for _ in range(height):
        raw += b"\x00" + row
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    return path


class SessionScript:
    """Keeps the two-browser choreography readable: every step either
    passes silently or appends one precise finding (with screenshot)."""

    def __init__(self, stack, workdir: Path):
        self.stack = stack
        self.workdir = workdir
        self.findings: list[str] = []
        self.dm = None
        self.pc = None
        self.campaign_id = None
        self.session_id = None

    def fail(self, step: str, detail: str, page=None) -> None:
        shot = ""
        if page is not None:
            try:
                path = self.workdir / f"fullsession-{step}-{len(self.findings)}.png"
                page.screenshot(path=str(path))
                shot = f" (screenshot: {path.name})"
            except Exception:
                pass
        self.findings.append(f"[{step}] {detail}{shot}")

    # ── helpers ─────────────────────────────────────────────────────

    def _csrf(self, context) -> str | None:
        return next((c["value"] for c in context.cookies()
                     if c["name"] == "csrf_access_token"), None)

    def _json_headers(self, context) -> dict:
        return {"Content-Type": "application/json",
                "X-CSRF-TOKEN": self._csrf(context)}

    def _open_sidebar_tab(self, page, tab: str) -> None:
        """The sidebar starts closed (translateX(100%)) -- clicking a tab
        that is currently off-screen is flaky, so open the drawer first."""
        if not page.locator(".right-sidebar.is-open").count():
            page.click("#btnSidebarToggle")
            page.wait_for_selector(".right-sidebar.is-open", timeout=STEP_TIMEOUT_MS)
        page.click(f'.sidebar-tab[data-tab="{tab}"]')

    def _world_click_point(self, page, cell_x: int, cell_y: int):
        box = page.locator("#mapWorld").bounding_box()
        map_width = float(page.locator("#mapWorld").get_attribute("data-map-width") or 700)
        scale = box["width"] / map_width
        return (box["x"] + (cell_x * GRID + GRID / 2) * scale,
                box["y"] + (cell_y * GRID + GRID / 2) * scale)

    def _place_token_via_ui(self, page, *, cell: tuple[int, int], name: str,
                            token_type: str | None, dm_only: bool = False) -> bool:
        """TOK tool -> click the map -> fill the panel -> Platzieren."""
        page.click('.tool-btn[data-tool="token"]')
        x, y = self._world_click_point(page, *cell)
        page.mouse.click(x, y)
        try:
            page.wait_for_selector("#tokenCreatePanel:not([hidden])",
                                   timeout=STEP_TIMEOUT_MS)
        except Exception:
            self.fail("token-place", f"create panel never opened for {name!r}", page)
            return False
        page.fill("#tokenCreateName", name)
        if token_type is not None:
            page.select_option("#tokenCreateType", token_type)
        if dm_only:
            page.select_option("#tokenCreateVisibility", "dm_only")
        page.click("#btnTokenCreateConfirm")
        try:
            page.wait_for_selector(f'.token-marker[title="{name}"]',
                                   state="attached", timeout=STEP_TIMEOUT_MS)
        except Exception:
            self.fail("token-place", f"marker for {name!r} never appeared", page)
            return False
        page.click('.tool-btn[data-tool="select"]')
        return True

    def _wait_text(self, page, js_id: str, needle: str, step: str,
                   description: str) -> bool:
        """textContent-based (works inside hidden sidebar tabs)."""
        try:
            page.wait_for_function(
                "([id, needle]) => (document.getElementById(id)?.textContent || '').includes(needle)",
                arg=[js_id, needle], timeout=STEP_TIMEOUT_MS)
            return True
        except Exception:
            self.fail(step, description, page)
            return False

    # ── phases ──────────────────────────────────────────────────────

    def setup_accounts_and_campaign(self, playwright) -> bool:
        from tools.robots.session import RobotSession

        keys = mint_registration_keys(self.stack.database_url, count=2)
        browser = playwright.chromium.launch()
        self.browser = browser

        dm_context = browser.new_context(viewport={"width": 1500, "height": 940})
        self.dm = RobotSession(dm_context, base_url=self.stack.base_url,
                               robot_name="regie_dm", artifacts_dir=self.workdir)
        self.dm.open()
        if not self.dm.register(username="regie_dm_bot",
                                email="regie_dm_bot@robots.roll-drauf.de",
                                password="Ro8ot-Test-Passw0rd!",
                                registration_key=keys[0]):
            self.findings.extend(f"[setup-dm] {f.detail}" for f in self.dm.findings)
            return False

        pc_context = browser.new_context(viewport={"width": 1500, "height": 940})
        self.pc = RobotSession(pc_context, base_url=self.stack.base_url,
                               robot_name="held_pc", artifacts_dir=self.workdir)
        self.pc.open()
        if not self.pc.register(username="held_pc_bot",
                                email="held_pc_bot@robots.roll-drauf.de",
                                password="Ro8ot-Test-Passw0rd!",
                                registration_key=keys[1]):
            self.findings.extend(f"[setup-pc] {f.detail}" for f in self.pc.findings)
            return False

        # Auto-accept confirm() dialogs (live-start warnings, session end).
        self.dm.page.on("dialog", lambda dialog: dialog.accept())
        self.pc.page.on("dialog", lambda dialog: dialog.accept())

        dm_api = dm_context.request
        headers = self._json_headers(dm_context)
        campaign = dm_api.post(f"{self.stack.base_url}/api/campaigns",
                               data=json.dumps({"name": "Robota-Chroniken",
                                                "max_players": 5}),
                               headers=headers).json()
        self.campaign_id = (campaign.get("campaign") or campaign)["id"]

        invite = dm_api.post(
            f"{self.stack.base_url}/api/campaigns/{self.campaign_id}/invite",
            data=json.dumps({"player_username": "held_pc_bot"}), headers=headers)
        if invite.status != 201 and invite.status != 200:
            self.fail("invite", f"invite returned HTTP {invite.status}: {invite.text()[:200]}")
            return False
        invite_token = invite.json()["invite_token"]

        accept = pc_context.request.post(
            f"{self.stack.base_url}/api/campaigns/{self.campaign_id}/accept-invite",
            data=json.dumps({"token": invite_token}),
            headers=self._json_headers(pc_context))
        if accept.status != 200:
            self.fail("invite", f"accept-invite returned HTTP {accept.status}: {accept.text()[:200]}")
            return False

        session_response = dm_api.post(
            f"{self.stack.base_url}/api/campaigns/{self.campaign_id}/sessions",
            data=json.dumps({"name": "Robota Session I"}), headers=headers)
        body = session_response.json()
        self.session_id = (body.get("session") or body)["id"]
        return True

    def dm_uploads_three_maps(self) -> bool:
        page = self.dm.page
        if not self.dm.goto(f"/play?campaign_id={self.campaign_id}&session_id={self.session_id}"):
            self.findings.extend(f"[dm-play] {f.detail}" for f in self.dm.findings)
            return False
        try:
            page.wait_for_selector("#layersWidget", timeout=STEP_TIMEOUT_MS)
        except Exception:
            self.fail("dm-play", "play table never rendered #layersWidget", page)
            return False

        # Widgets start collapsed -- open the layer panel like a user would.
        page.click('#layersWidget .widget-toggle')
        try:
            page.wait_for_selector("#btnMapUpload", state="visible",
                                   timeout=STEP_TIMEOUT_MS)
        except Exception:
            self.fail("upload", "DM upload control never became visible", page)
            return False

        maps = [
            ("wald_ebene.png", 700, 490, (66, 110, 58)),
            ("hafen_stadt.png", 560, 560, (52, 84, 140)),
            ("lava_grotte.png", 840, 420, (150, 62, 44)),
        ]
        for index, (filename, width, height, rgb) in enumerate(maps, start=1):
            real_file = _make_png(self.workdir / filename, width, height, rgb)
            page.set_input_files("#mapUploadFile", str(real_file))
            expected_name = filename.rsplit(".", 1)[0]
            try:
                page.wait_for_function(
                    "count => document.querySelectorAll('#layerList .layer-row').length >= count",
                    arg=index, timeout=STEP_TIMEOUT_MS)
                page.wait_for_function(
                    "name => (document.getElementById('activePageName')?.textContent || '').includes(name)",
                    arg=expected_name, timeout=STEP_TIMEOUT_MS)
            except Exception:
                self.fail("upload", f"map {index} ({filename}) never became an "
                          f"active layer after file upload", page)
                return False

        rows = page.locator("#layerList .layer-row").count()
        if rows != 3:
            self.fail("upload", f"expected 3 layers after 3 uploads, layer list shows {rows}", page)

        # The activity journal must reflect every upload.
        journal = page.locator("#activityLog").text_content() or ""
        for filename, *_rest in maps:
            base = filename.rsplit(".", 1)[0]
            if base not in journal:
                self.fail("journal", f"activity journal never mentioned uploaded map {base!r}", page)

        # Asset library accuracy: exactly the three uploaded map files.
        listing = self.dm.context.request.get(
            f"{self.stack.base_url}/api/assets/campaigns/{self.campaign_id}/list")
        if listing.status != 200:
            self.fail("assets", f"asset list returned HTTP {listing.status}")
        else:
            asset_maps = listing.json().get("assets", {}).get("maps", [])
            listed = sorted(a.get("filename", "") for a in asset_maps)
            expected = sorted(name for name, *_ in maps)
            if listed != expected:
                self.fail("assets", f"asset library maps {listed} != uploaded {expected}")

        page.screenshot(path=str(self.workdir / "fullsession-dm-three-maps.png"))
        return True

    def dm_uploads_token_assets(self) -> bool:
        """'Upload tokens': token ART lives in the asset library (the
        TokenState model has no image column yet - markers render as
        initials), so the honest check is that token-type uploads land
        and are categorized accurately."""
        api = self.dm.context.request
        csrf = self._csrf(self.dm.context)
        for filename, rgb in (("goblin_token.png", (90, 140, 60)),
                              ("held_token.png", (70, 100, 180))):
            real_file = _make_png(self.workdir / filename, 128, 128, rgb)
            response = api.post(
                f"{self.stack.base_url}/api/assets/campaigns/{self.campaign_id}/upload",
                multipart={"file": {"name": filename, "mimeType": "image/png",
                                    "buffer": real_file.read_bytes()},
                           "asset_type": "token"},
                headers={"X-CSRF-TOKEN": csrf})
            if response.status != 201:
                self.fail("token-assets", f"{filename} upload returned "
                          f"HTTP {response.status}: {response.text()[:200]}")
                return False

        listing = api.get(
            f"{self.stack.base_url}/api/assets/campaigns/{self.campaign_id}/list")
        token_assets = listing.json().get("assets", {}).get("tokens", [])
        listed = sorted(a.get("filename", "") for a in token_assets)
        if listed != ["goblin_token.png", "held_token.png"]:
            self.fail("token-assets",
                      f"asset library token category shows {listed}, expected the two uploads")
        return True

    def dm_places_tokens(self) -> bool:
        page = self.dm.page
        ok = self._place_token_via_ui(page, cell=(2, 2), name="Goblin",
                                      token_type="monster")
        ok = self._place_token_via_ui(page, cell=(5, 2), name="Geheimboss",
                                      token_type="monster", dm_only=True) and ok
        if not ok:
            return False
        markers = page.locator(".token-marker").count()
        if markers != 2:
            self.fail("token-place", f"DM should see 2 markers, sees {markers}", page)
        return True

    def dm_switches_layers(self) -> bool:
        """Page switching: back to map 1, then return to map 3 -- the
        active-page pill must follow, and the tokens (placed on map 3)
        must disappear on map 1 and come back on map 3."""
        page = self.dm.page
        activate_buttons = page.locator('#layerList [data-act="activate"]')
        if not activate_buttons.count():
            self.fail("layers", "no Aktivieren buttons in the layer list", page)
            return False
        activate_buttons.first.click()
        if not self._wait_text(page, "activePageName", "wald_ebene", "layers",
                               "switching to map 1 never updated the page pill"):
            return False
        try:
            page.wait_for_function(
                "() => document.querySelectorAll('.token-marker').length === 0",
                timeout=STEP_TIMEOUT_MS)
        except Exception:
            self.fail("layers", "map-3 tokens still render while map 1 is active", page)

        page.locator('#layerList [data-act="activate"]').last.click()
        if not self._wait_text(page, "activePageName", "lava_grotte", "layers",
                               "switching back to map 3 never updated the page pill"):
            return False
        try:
            page.wait_for_function(
                "() => document.querySelectorAll('.token-marker').length === 2",
                timeout=STEP_TIMEOUT_MS)
        except Exception:
            self.fail("layers", "tokens did not come back after returning to map 3", page)
        return True

    def dm_starts_session(self) -> bool:
        page = self.dm.page
        self._open_sidebar_tab(page, "session")
        page.click("#btnReadyCheck")
        self._wait_text(page, "readyCheckOutput", "Kann starten", "ready-check",
                        "ready check never produced output")
        page.click("#btnToReady")
        if not self._wait_text(page, "sessionStatusPill", "ready", "lifecycle",
                               "'Bereit setzen' never reached status ready"):
            return False
        page.click("#btnStart")
        if not self._wait_text(page, "sessionStatusPill", "in_progress", "lifecycle",
                               "'Live starten' never reached status in_progress"):
            return False
        # Close the sidebar so it does not overlap the map for later clicks.
        page.click("#btnSidebarToggle")
        return True

    def player_joins_and_verifies_visibility(self) -> bool:
        page = self.pc.page
        if not self.pc.goto(f"/play?campaign_id={self.campaign_id}&session_id={self.session_id}"):
            self.findings.extend(f"[pc-play] {f.detail}" for f in self.pc.findings)
            return False
        try:
            page.wait_for_selector("#mapImage", state="visible", timeout=STEP_TIMEOUT_MS)
            page.wait_for_selector('.token-marker[title="Goblin"]', state="attached",
                                   timeout=STEP_TIMEOUT_MS)
        except Exception:
            self.fail("pc-view", "player never saw the map with the public token", page)
            return False

        # THE visibility assertion: the DM layer stays hidden -- no marker,
        # no token-list entry, no turn-order entry, nowhere in the DOM text.
        leaks = page.evaluate(
            """() => {
                const spots = [];
                if (document.querySelector('.token-marker[title="Geheimboss"]'))
                    spots.push('map marker');
                if ((document.getElementById('tokenList')?.textContent || '').includes('Geheimboss'))
                    spots.push('token list');
                if ((document.getElementById('turnOrderList')?.textContent || '').includes('Geheimboss'))
                    spots.push('turn order');
                if ((document.getElementById('actionTargetTokenId')?.textContent || '').includes('Geheimboss'))
                    spots.push('action target select');
                return spots;
            }""")
        if leaks:
            self.fail("dm-layer-leak",
                      f"DM-only token 'Geheimboss' is visible to the player in: {', '.join(leaks)}",
                      page)

        public_markers = page.locator(".token-marker").count()
        if public_markers != 1:
            self.fail("pc-view", f"player should see exactly 1 marker (Goblin), sees {public_markers}", page)

        page.screenshot(path=str(self.workdir / "fullsession-player-view.png"))
        return True

    def player_places_and_moves_hero(self) -> bool:
        page = self.pc.page
        if not self._place_token_via_ui(page, cell=(8, 4), name="Held",
                                        token_type=None):  # pinned to player for non-DMs
            return False

        # The hero must ALSO arrive on the DM's table (live sync).
        try:
            self.dm.page.wait_for_selector('.token-marker[title="Held"]',
                                           state="attached", timeout=STEP_TIMEOUT_MS)
        except Exception:
            self.fail("sync", "player's hero token never appeared on the DM table", self.dm.page)

        # Drag the hero two grid cells to the right.
        marker = page.locator('.token-marker[title="Held"]')
        start_left = int(marker.get_attribute("data-token-left") or 0)
        box = marker.bounding_box()
        map_width = float(page.locator("#mapWorld").get_attribute("data-map-width") or 700)
        scale = page.locator("#mapWorld").bounding_box()["width"] / map_width
        start_x = box["x"] + box["width"] / 2
        start_y = box["y"] + box["height"] / 2
        page.mouse.move(start_x, start_y)
        page.mouse.down()
        for i in range(1, 7):
            page.mouse.move(start_x + (2 * GRID * scale) * i / 6, start_y, steps=2)
        page.mouse.up()

        expected_left = start_left + 2 * GRID
        try:
            page.wait_for_function(
                """expected => {
                    const m = document.querySelector('.token-marker[title="Held"]');
                    return m && Number(m.getAttribute('data-token-left')) === expected;
                }""", arg=expected_left, timeout=STEP_TIMEOUT_MS)
        except Exception:
            actual = marker.get_attribute("data-token-left")
            self.fail("move", f"hero drag: expected world x {expected_left}, marker reports {actual}", page)
            return False

        # And the DM must see the moved position too.
        try:
            self.dm.page.wait_for_function(
                """expected => {
                    const m = document.querySelector('.token-marker[title="Held"]');
                    return m && Number(m.getAttribute('data-token-left')) === expected;
                }""", arg=expected_left, timeout=STEP_TIMEOUT_MS)
        except Exception:
            self.fail("sync", "hero move never reached the DM's table", self.dm.page)
        return True

    def combat_round(self) -> bool:
        dm_page = self.dm.page

        # Initiative for every token, from the DM's turn-order widget.
        dm_page.click('#turnOrderWidget .widget-toggle')
        try:
            dm_page.wait_for_selector("#btnRollInitiative", state="visible",
                                      timeout=STEP_TIMEOUT_MS)
        except Exception:
            self.fail("initiative", "DM initiative button never became visible", dm_page)
            return False
        dm_page.click("#btnRollInitiative")
        try:
            dm_page.wait_for_function(
                "() => document.querySelectorAll('#turnOrderList .turn-item').length === 3",
                timeout=STEP_TIMEOUT_MS)
        except Exception:
            count = dm_page.locator("#turnOrderList .turn-item").count()
            self.fail("initiative", f"DM turn order should list 3 combatants, lists {count}", dm_page)

        # Player's turn order: only the two visible tokens, never the boss.
        try:
            self.pc.page.wait_for_function(
                "() => document.querySelectorAll('#turnOrderList .turn-item').length === 2",
                timeout=STEP_TIMEOUT_MS)
        except Exception:
            count = self.pc.page.locator("#turnOrderList .turn-item").count()
            self.fail("initiative", f"player turn order should list 2 combatants, lists {count}", self.pc.page)
        if "Geheimboss" in (self.pc.page.locator("#turnOrderList").text_content() or ""):
            self.fail("dm-layer-leak", "DM-only token leaked into the player's turn order", self.pc.page)

        # One action from the action bar (DM: Goblin acts on the hero).
        self._open_sidebar_tab(dm_page, "tools")
        goblin_option = dm_page.locator('#actionTokenId option', has_text="Goblin")
        held_option = dm_page.locator('#actionTargetTokenId option', has_text="Held")
        if not goblin_option.count() or not dm_page.locator("#actionCode option").count():
            self.fail("combat", "action bar selects are not populated", dm_page)
        else:
            dm_page.select_option("#actionTokenId",
                                  goblin_option.first.get_attribute("value"))
            if held_option.count():
                dm_page.select_option("#actionTargetTokenId",
                                      held_option.first.get_attribute("value"))
            dm_page.select_option("#actionCode",
                                  index=0)
            dm_page.click("#btnExecuteAction")
            self._wait_text(dm_page, "activityLog", "Aktion ausgeführt", "combat",
                            "action execution never confirmed on the DM side")
            self._wait_text(self.pc.page, "activityLog", "Aktions-Event", "combat",
                            "the executed action never reached the player's journal")

        # Dice: DM rolls; the roller's OWN result display must work (the
        # ack path -- broken until 2026-08-23, the server never returned
        # the ack) AND the result must land in the PLAYER's dice log.
        dm_page.fill("#diceInput", "1d20+3")
        dm_page.click("#btnRoll")
        self._wait_text(dm_page, "diceResult", "1d20+3 ->", "dice",
                        "the roller's own #diceResult never showed the ack result")
        self._wait_text(self.pc.page, "diceLog", "gewürfelt", "dice",
                        "DM dice roll never reached the player's dice log")

        # Chat: player talks, DM reads.
        self._open_sidebar_tab(self.pc.page, "chat")
        self.pc.page.fill("#chatInput", "Angriff auf den Goblin!")
        self.pc.page.click("#btnSendChat")
        self._wait_text(self.pc.page, "chatLog", "Angriff auf den Goblin!", "chat",
                        "player's own chat log never showed the sent message")
        self._wait_text(dm_page, "chatLog", "Angriff auf den Goblin!", "chat",
                        "player chat message never reached the DM")

        dm_page.screenshot(path=str(self.workdir / "fullsession-combat-dm.png"))
        self.pc.page.screenshot(path=str(self.workdir / "fullsession-combat-pc.png"))
        return True

    def dm_ends_session(self) -> bool:
        page = self.dm.page
        self._open_sidebar_tab(page, "session")
        page.click("#btnEnd")
        ok = self._wait_text(page, "sessionStatusPill", "ended", "lifecycle",
                             "session end never reached status ended on the DM side")
        ok = self._wait_text(self.pc.page, "sessionStatusPill", "ended", "lifecycle",
                             "session end never propagated to the player") and ok
        return ok

    # ── driver ──────────────────────────────────────────────────────

    def run(self) -> list[str]:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            if not self.setup_accounts_and_campaign(playwright):
                return self.findings
            for phase in (self.dm_uploads_three_maps,
                          self.dm_uploads_token_assets,
                          self.dm_places_tokens,
                          self.dm_switches_layers,
                          self.dm_starts_session,
                          self.player_joins_and_verifies_visibility,
                          self.player_places_and_moves_hero,
                          self.combat_round,
                          self.dm_ends_session):
                if not phase():
                    break
            # Console/JS/HTTP-5xx findings both robots collected on the way.
            self.findings.extend(f"[{f.kind}] {f.detail}" for f in self.dm.findings)
            self.findings.extend(f"[{f.kind}] {f.detail}" for f in self.pc.findings)
            self.browser.close()
        return self.findings


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="tools.robots.fullsession")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    workdir = Path(tempfile.mkdtemp(prefix="vtt-fullsession-"))
    print(f"Fullsession: disposable stack in {workdir} …")
    with disposable_stack(workdir) as stack:
        findings = SessionScript(stack, workdir).run()

    print(f"\nfullsession · {len(findings)} finding(s)")
    for finding in findings:
        print(f"  - {finding}")

    report = args.out or workdir.parent / "vtt-fullsession.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(
        {"status": "failed" if findings else "passed",
         "findings": findings}, indent=2), encoding="utf-8")
    print(f"JSON: {report}")
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
