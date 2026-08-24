"""Real scenarios, not just page pins — the human half views.py cannot
see: does the flow actually make sense end to end.

First flow: the real-time layer itself. A DM creates a campaign and a
session through the real API (page.request, so the browser's own auth
cookies are used — same effect as filling forms, less brittle for
multi-step JSON flows), opens /play for that session, and rolls dice
through the actual dice-roller UI. The interesting part is not the
roll -- it is that the result has to travel client -> Socket.IO ->
server -> broadcast -> back to the SAME client's own socket and land in
the DOM (#diceLog, #activityLog), proving the whole real-time round
trip most VTT features (map/token sync, session snapshots, initiative)
build on top of.

    python -m tools.robots.flows
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from tools.robots.accounts import mint_registration_keys
from tools.robots.stack import disposable_stack


def _dice_roll_flow(stack, workdir: Path) -> list[str]:
    from playwright.sync_api import sync_playwright
    from tools.robots.session import RobotSession

    findings: list[str] = []
    keys = mint_registration_keys(stack.database_url, count=1)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        session = RobotSession(context, base_url=stack.base_url,
                               robot_name="spielleitung",
                               artifacts_dir=workdir)
        session.open()
        registered = session.register(
            username="spielleitung_bot",
            email="spielleitung_bot@robots.roll-drauf.de",
            password="Ro8ot-Test-Passw0rd!", registration_key=keys[0])
        if not registered:
            findings.extend(f"[setup] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        page = session.page
        api = context.request
        # JWT_COOKIE_CSRF_PROTECT is on (vtt/config.py) -- Flask-JWT-Extended's
        # double-submit pattern needs the csrf_access_token cookie echoed
        # back as a header on every mutating request. page.request shares
        # the browser context's cookies automatically but does NOT read
        # them into headers for you (that is normally the frontend JS's
        # job, e.g. auth.js) -- do it explicitly for the same effect.
        csrf_token = next((c["value"] for c in context.cookies()
                           if c["name"] == "csrf_access_token"), None)
        if not csrf_token:
            findings.append("[setup] no csrf_access_token cookie after "
                            "registration — cannot make authenticated API calls")
            browser.close()
            return findings
        json_headers = {"Content-Type": "application/json",
                        "X-CSRF-TOKEN": csrf_token}

        campaign_response = api.post(
            f"{stack.base_url}/api/campaigns",
            data=json.dumps({"name": "Robotertestkampagne", "max_players": 6}),
            headers=json_headers)
        if campaign_response.status != 201:
            findings.append(
                f"[campaign] POST /api/campaigns returned "
                f"HTTP {campaign_response.status}: {campaign_response.text()[:300]}")
            browser.close()
            return findings
        campaign_id = campaign_response.json()["campaign"]["id"] \
            if "campaign" in campaign_response.json() \
            else campaign_response.json()["id"]

        session_response = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
            data=json.dumps({"name": "Robotertestsitzung"}),
            headers=json_headers)
        if session_response.status != 201:
            findings.append(
                f"[session] POST /api/campaigns/{campaign_id}/sessions "
                f"returned HTTP {session_response.status}: "
                f"{session_response.text()[:300]}")
            browser.close()
            return findings
        body = session_response.json()
        session_id = body["session"]["id"] if "session" in body else body["id"]

        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[play] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        try:
            page.wait_for_selector("#diceInput", state="visible", timeout=15_000)
            # The socket join (session:join, emitted automatically on
            # connect by play-socket.js) is itself a round trip -- give it
            # a moment to land before rolling, rather than racing it.
            page.wait_for_timeout(1_500)
            page.fill("#diceInput", "1d20+5")
            page.click("#btnRoll")
            # The roll has to complete a full client -> server -> broadcast
            # -> client round trip before #diceLog shows a line -- this is
            # the actual thing under test, not just a UI click.
            page.wait_for_selector("#diceLog div", state="attached", timeout=10_000)
        except Exception as error:
            findings.append(
                f"[dice] roll never produced a #diceLog entry within "
                f"10s (real-time round trip failed or was too slow): {error}")
            findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
            try:
                shot = workdir / "dice-roll-timeout.png"
                page.screenshot(path=str(shot))
                findings.append(f"[dice] screenshot: {shot.name}")
            except Exception:
                pass
            browser.close()
            return findings

        log_text = page.locator("#diceLog").inner_text()
        if "gewürfelt" not in log_text:
            findings.append(f"[dice] #diceLog updated but text looks wrong: {log_text[:200]!r}")

        activity_text = page.locator("#activityLog").inner_text() \
            if page.locator("#activityLog").count() else ""
        if "gewürfelt" not in activity_text:
            findings.append(
                f"[dice] #diceLog updated but #activityLog was not "
                f"(only one of the two broadcast handlers fired): {activity_text[:200]!r}")

        findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
        browser.close()
    return findings


def _map_token_table_flow(stack, workdir: Path) -> list[str]:
    """The journey the 2026-08-23 table refactor exists for: a DM uploads
    a map image, creates a CampaignMap from it, activates it for the
    session, places a token -- and the play table must actually RENDER
    both. Before the refactor this failed at every step: no upload path
    on the table, tokens invisible under overlapping panels, map world
    clamped/letterboxed so grid and art never aligned."""
    import struct
    import zlib

    from playwright.sync_api import sync_playwright
    from tools.robots.session import RobotSession

    def _make_png(width, height, rgb):
        def chunk(tag, data):
            piece = struct.pack(">I", len(data)) + tag + data
            return piece + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        raw = b""
        row = bytes(rgb) * width
        for _ in range(height):
            raw += b"\x00" + row
        ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))

    findings: list[str] = []
    keys = mint_registration_keys(stack.database_url, count=1)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        session = RobotSession(context, base_url=stack.base_url,
                               robot_name="karten_dm", artifacts_dir=workdir)
        session.open()
        if not session.register(
                username="karten_dm_bot",
                email="karten_dm_bot@robots.roll-drauf.de",
                password="Ro8ot-Test-Passw0rd!", registration_key=keys[0]):
            findings.extend(f"[setup] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        page = session.page
        api = context.request
        csrf_token = next((c["value"] for c in context.cookies()
                           if c["name"] == "csrf_access_token"), None)
        json_headers = {"Content-Type": "application/json",
                        "X-CSRF-TOKEN": csrf_token}

        campaign = api.post(f"{stack.base_url}/api/campaigns",
                            data=json.dumps({"name": "Kartenkampagne", "max_players": 6}),
                            headers=json_headers).json()
        campaign_id = (campaign.get("campaign") or campaign)["id"]
        game_session = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
            data=json.dumps({"name": "Kartensitzung"}), headers=json_headers).json()
        session_id = (game_session.get("session") or game_session)["id"]

        # The map goes in through the REAL widget upload: click the button,
        # let the browser's file chooser open (this exact path was dead
        # until 2026-08-24 -- a global book-shell click handler
        # preventDefault-ed every click, which cancels the file-picker
        # default action; robots only ever set_input_files directly and
        # missed it), then feed the file through the chooser.
        map_file = workdir / "robot_map.png"
        map_file.write_bytes(_make_png(700, 490, (70, 110, 60)))

        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[play] {f.detail}" for f in session.findings)
            browser.close()
            return findings
        try:
            page.wait_for_function("() => window.RollDraufTable", timeout=15_000)
            page.wait_for_timeout(1_000)
            body_route_leak = page.evaluate("() => document.body.hasAttribute('data-book-route')")
            if body_route_leak:
                findings.append("[click-defaults] body carries data-book-route again - "
                                "the app-wide preventDefault bug is back")
            layer_widget_classes = page.locator("#layersWidget").get_attribute("class") or ""
            if "collapsed" in layer_widget_classes.split():
                findings.append("[menu] layer menu is collapsed on first DM render")
                page.click('#layersWidget .widget-toggle')
            if page.locator("#btnMapUpload").inner_text().strip() != "Datei hinzufügen":
                findings.append("[menu] map file action is not labelled 'Datei hinzufügen'")
            if not page.locator("#btnTokenUpload").count():
                findings.append("[token-upload] no direct token file-dialog action is visible")
            page.click("#btnSidebarToggle")
            page.wait_for_selector(".right-sidebar.is-open", timeout=15_000)
            for tab in ("journal", "chat", "tools", "session"):
                page.click(f'.sidebar-tab[data-tab="{tab}"]')
                if not page.locator(f"#panel-{tab}.active").count():
                    findings.append(f"[menu] sidebar tab {tab!r} did not activate its panel")
            page.click("#btnSidebarToggle")
            page.wait_for_selector("#btnMapUpload", state="visible", timeout=15_000)
            with page.expect_file_chooser(timeout=10_000) as chooser_info:
                page.click("#btnMapUpload")
            chooser_info.value.set_files(str(map_file))
            page.wait_for_function(
                "() => (document.getElementById('activePageName')?.textContent || '')"
                ".includes('robot_map')", timeout=20_000)
        except Exception as error:
            findings.append(f"[upload-ui] map upload through the real file chooser "
                            f"failed: {type(error).__name__}: {str(error)[:200]}")
            browser.close()
            return findings

        # Token art has its own direct file-dialog entry point. It should be
        # usable before the placement panel is opened; the uploaded image is
        # kept as pending art for the next TOK placement.
        try:
            page.click('#tokenWidget .widget-toggle')
            page.wait_for_selector("#btnTokenUpload", state="visible", timeout=15_000)
            token_file = workdir / "robot_token_face.png"
            token_file.write_bytes(_make_png(96, 96, (200, 170, 40)))
            with page.expect_file_chooser(timeout=10_000) as chooser_info:
                page.click("#btnTokenUpload")
            chooser_info.value.set_files(str(token_file))
            page.wait_for_function(
                "() => (document.getElementById('tokenUploadStatus')?.textContent || '')"
                ".includes('Tokenbild geladen')", timeout=20_000)
        except Exception as error:
            findings.append(f"[token-upload] direct token file chooser failed: "
                            f"{type(error).__name__}: {str(error)[:200]}")

        # Token art: uploaded as a token asset, referenced via
        # metadata_json.image_url, must render as an image face.
        art = api.post(
            f"{stack.base_url}/api/assets/campaigns/{campaign_id}/upload",
            multipart={"file": {"name": "robot_face.png", "mimeType": "image/png",
                                "buffer": _make_png(96, 96, (200, 170, 40))},
                       "asset_type": "token"},
            headers={"X-CSRF-TOKEN": csrf_token})
        art_id = art.json().get("asset_id") if art.status == 201 else None
        if not art_id:
            findings.append(f"[token-art] token asset upload returned HTTP {art.status}")
        token_response = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions/{session_id}/tokens",
            data=json.dumps({"name": "Robotertoken", "x": 140, "y": 140,
                             "token_type": "npc",
                             "metadata_json": {"position_mode": "pixel",
                                               "image_url": f"/api/assets/{art_id}/preview"}}),
            headers=json_headers)
        if token_response.status != 201:
            findings.append(f"[token] create returned HTTP {token_response.status}: {token_response.text()[:200]}")

        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[play] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        try:
            page.wait_for_selector("#mapImage", state="visible", timeout=15_000)
        except Exception:
            findings.append("[render] #mapImage never became visible - map background not rendered")

        page.wait_for_timeout(1_500)

        token_art = page.evaluate(
            """() => {
                const img = document.querySelector('.token-marker .token-image');
                return img ? {src: img.getAttribute('src'), loaded: img.complete && img.naturalWidth > 0} : null;
            }""")
        if not token_art:
            findings.append("[token-art] token marker did not render its image face")
        elif not token_art.get("loaded"):
            findings.append(f"[token-art] token image present but did not load: {token_art.get('src')!r}")
        ui_controls = page.evaluate(
            """() => ({
                createImage: Boolean(document.getElementById('btnTokenCreateImage')),
                setImage: Boolean(document.getElementById('btnTokenImageSet')),
            })""")
        for key, ok in (ui_controls or {}).items():
            if not ok:
                findings.append(f"[token-art] visible token-image control missing: {key}")
        verdict = page.evaluate(
            """() => {
                const img = document.getElementById('mapImage');
                const world = document.getElementById('mapWorld');
                const marker = document.querySelector('.token-marker');
                const markerRect = marker ? marker.getBoundingClientRect() : null;
                const viewport = document.getElementById('mapViewport');
                const viewRect = viewport ? viewport.getBoundingClientRect() : null;
                return {
                    imgLoaded: Boolean(img && img.complete && img.naturalWidth > 0),
                    worldWidth: world ? world.style.width : null,
                    markerExists: Boolean(marker),
                    markerVisibleInViewport: Boolean(markerRect && viewRect
                        && markerRect.width > 0
                        && markerRect.left >= viewRect.left && markerRect.right <= viewRect.right
                        && markerRect.top >= viewRect.top && markerRect.bottom <= viewRect.bottom),
                    uploadControlExists: Boolean(document.getElementById('btnMapUpload')),
                };
            }"""
        )
        if not verdict.get("imgLoaded"):
            findings.append("[render] map background image did not load on the table")
        if verdict.get("worldWidth") != "700px":
            findings.append(
                f"[scale] map world width is {verdict.get('worldWidth')!r}, expected '700px' "
                "(the declared pixel size - clamping/letterboxing is back)")
        if not verdict.get("markerExists"):
            findings.append("[token] no .token-marker rendered for the created token")
        elif not verdict.get("markerVisibleInViewport"):
            findings.append("[token] token marker exists but is outside/hidden in the viewport")
        if not verdict.get("uploadControlExists"):
            findings.append("[upload-ui] #btnMapUpload missing - the DM upload path left the table again")

        if findings:
            try:
                shot = workdir / "map-token-flow.png"
                page.screenshot(path=str(shot))
                findings.append(f"[debug] screenshot: {shot.name}")
            except Exception:
                pass

        findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
        browser.close()
    return findings


def _beyond20_bridge_flow(stack, workdir: Path) -> list[str]:
    """External-roll compatibility (M-Beyond20): dispatch the exact DOM
    event the Beyond20 extension fires into registered pages
    (Beyond20_RenderedRoll, detail as an argument array -- see
    https://beyond20.here-for-more.info/api) and prove the roll travels
    bridge -> normalized envelope -> socket -> server (sanitize +
    persist) -> room broadcast -> dice log + chat, and SURVIVES a page
    reload via chat history."""
    from playwright.sync_api import sync_playwright
    from tools.robots.session import RobotSession

    findings: list[str] = []
    keys = mint_registration_keys(stack.database_url, count=1)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        session = RobotSession(context, base_url=stack.base_url,
                               robot_name="beyond_dm", artifacts_dir=workdir)
        session.open()
        if not session.register(
                username="beyond_dm_bot",
                email="beyond_dm_bot@robots.roll-drauf.de",
                password="Ro8ot-Test-Passw0rd!", registration_key=keys[0]):
            findings.extend(f"[setup] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        page = session.page
        api = context.request
        csrf_token = next((c["value"] for c in context.cookies()
                           if c["name"] == "csrf_access_token"), None)
        json_headers = {"Content-Type": "application/json",
                        "X-CSRF-TOKEN": csrf_token}
        campaign = api.post(f"{stack.base_url}/api/campaigns",
                            data=json.dumps({"name": "Beyondkampagne", "max_players": 4}),
                            headers=json_headers).json()
        campaign_id = (campaign.get("campaign") or campaign)["id"]
        game_session = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
            data=json.dumps({"name": "Beyondsitzung"}), headers=json_headers).json()
        session_id = (game_session.get("session") or game_session)["id"]

        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[play] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        try:
            page.wait_for_function(
                "() => window.RollDraufTable && document.body.dataset.playTransitionStage === 'table'",
                timeout=15_000)
            page.wait_for_timeout(1_500)  # session:join round trip
        except Exception:
            findings.append("[bridge] window.RollDraufTable never appeared - "
                            "the external-roll surface is gone")
            browser.close()
            return findings

        # HP sync needs a token whose name matches the D&D Beyond
        # character -- set up a map + token through the API first.
        map_response = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/maps",
            data=json.dumps({"name": "Beyondkarte", "width": 700, "height": 490,
                             "grid_size": 70}), headers=json_headers)
        map_id = map_response.json().get("id")
        api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions/{session_id}/maps/activate",
            data=json.dumps({"map_id": map_id}), headers=json_headers)
        api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions/{session_id}/tokens",
            data=json.dumps({"name": "Rilbo Steinfaust", "x": 70, "y": 70,
                             "token_type": "npc", "hp_current": 25, "hp_max": 25,
                             "metadata_json": {"position_mode": "pixel"}}),
            headers=json_headers)
        # Reload so the table picks up map + token, then wait for the socket.
        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[reload-setup] {f.detail}" for f in session.findings)
            browser.close()
            return findings
        page.wait_for_function("() => window.RollDraufTable", timeout=15_000)
        page.wait_for_timeout(1_500)

        # The exact shape Beyond20 dispatches (detail is an ARRAY of args).
        page.evaluate(
            """() => {
                const request = {
                    action: "rendered-roll",
                    title: "Langschwert: Angriff",
                    character: {name: "Rilbo Steinfaust", type: "Character"},
                    whisper: 0,
                    attack_rolls: [{
                        formula: "1d20+7",
                        parts: [{rolls: [{roll: 20}]}, "+", 7],
                        total: 27,
                        "critical-success": true,
                        "critical-failure": false,
                        type: "to-hit",
                    }],
                    damage_rolls: [["Slashing", {formula: "1d8+4",
                                                 parts: [{rolls: [{roll: 6}]}, "+", 4],
                                                 total: 10}, 0]],
                    total_damages: {"Slashing": 10},
                    roll_info: [["Save DC", "15 CON"]],
                    source: "beyond20-robot",
                };
                document.dispatchEvent(new CustomEvent(
                    "Beyond20_RenderedRoll", {detail: [request]}));
            }""")

        # Broadcast round trip: the sender renders only on receiving the
        # server's broadcast, so this asserts the full server path.
        try:
            page.wait_for_selector("#diceLog .ext-roll-card", state="attached",
                                   timeout=10_000)
        except Exception:
            findings.append("[bridge] Beyond20 roll never rendered a roll card "
                            "(bridge -> socket -> broadcast chain broke)")
        card_checks = page.evaluate(
            """() => {
                const card = document.querySelector('#diceLog .ext-roll-card');
                if (!card) return null;
                const text = card.textContent || '';
                return {
                    crit: card.classList.contains('crit') && text.includes('KRIT'),
                    character: text.includes('Rilbo Steinfaust'),
                    damageRow: text.includes('Slashing') && text.includes('1d8+4'),
                    dice: text.includes('[20]') && text.includes('[6]'),
                    info: text.includes('Save DC: 15 CON'),
                    source: text.includes('via beyond20'),
                };
            }""")
        if not card_checks:
            findings.append("[card] no .ext-roll-card in the dice log")
        else:
            for key, ok in card_checks.items():
                if not ok:
                    findings.append(f"[card] roll card missing expected part: {key}")
        chat_text = page.locator("#chatLog").text_content() or ""
        if "Rilbo Steinfaust" not in chat_text:
            findings.append("[bridge] Beyond20 roll missing from the chat log")

        # HP sync: Beyond20_UpdateHP must patch the matching token's HP.
        page.evaluate(
            """() => {
                document.dispatchEvent(new CustomEvent("Beyond20_UpdateHP", {
                    detail: [{action: "hp-update",
                              character: {name: "Rilbo Steinfaust", hp: 18,
                                          "max-hp": 25, "temp-hp": 0}}],
                }));
            }""")
        try:
            page.wait_for_function(
                "() => (document.getElementById('tokenList')?.textContent || '')"
                ".includes('HP 18 / 25')", timeout=10_000)
        except Exception:
            token_text = page.locator("#tokenList").text_content() or ""
            findings.append(f"[hp-sync] Beyond20 hp-update never reached the token "
                            f"(token list shows: {token_text[:120]!r})")

        # Conditions sync: conditions array + exhaustion land as a marker
        # badge and a token-list line.
        page.evaluate(
            """() => {
                document.dispatchEvent(new CustomEvent("Beyond20_UpdateConditions", {
                    detail: [{action: "conditions-update",
                              character: {name: "Rilbo Steinfaust",
                                          conditions: ["Poisoned", "Prone"],
                                          exhaustion: 1}}],
                }));
            }""")
        try:
            page.wait_for_function(
                "() => (document.getElementById('tokenList')?.textContent || '')"
                ".includes('Poisoned, Prone, Erschöpfung 1')", timeout=10_000)
        except Exception:
            token_text = page.locator("#tokenList").text_content() or ""
            findings.append(f"[conditions] Beyond20 conditions-update never reached "
                            f"the token list (shows: {token_text[:120]!r})")
        badge = page.evaluate(
            "() => document.querySelector('.token-marker .token-conditions')?.textContent || null")
        if badge != "3":
            findings.append(f"[conditions] marker badge should show 3 conditions, shows {badge!r}")

        # Turn tracker sync: initiative + current-turn flag from D&D
        # Beyond's encounter tracker; unknown combatants are ignored.
        page.evaluate(
            """() => {
                document.dispatchEvent(new CustomEvent("Beyond20_UpdateCombat", {
                    detail: [{action: "update-combat",
                              combat: [
                                  {name: "Rilbo Steinfaust", initiative: 17,
                                   turn: true, tags: ["character"]},
                                  {name: "Fremder Ork", initiative: 12,
                                   turn: false, tags: ["monster"]},
                              ]}],
                }));
            }""")
        try:
            page.wait_for_function(
                """() => {
                    const current = document.querySelector('#turnOrderList .turn-item.current');
                    return current && current.textContent.includes('Rilbo Steinfaust')
                        && current.textContent.includes('17');
                }""", timeout=10_000)
        except Exception:
            turn_text = page.locator("#turnOrderList").text_content() or ""
            findings.append(f"[turn-tracker] Beyond20 update-combat never marked Rilbo "
                            f"as current with initiative 17 (turn order: {turn_text[:120]!r})")
        turn_items = page.locator("#turnOrderList .turn-item").count()
        if turn_items != 1:
            findings.append(f"[turn-tracker] expected 1 turn entry (unknown combatant "
                            f"ignored), turn order lists {turn_items}")

        # Reload: the roll must come back via bootstrap chat history.
        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[reload] {f.detail}" for f in session.findings)
        else:
            try:
                page.wait_for_function(
                    "() => (document.getElementById('chatLog')?.textContent || '')"
                    ".includes('Rilbo Steinfaust')", timeout=10_000)
            except Exception:
                findings.append("[bridge] Beyond20 roll did not survive a page "
                                "reload (chat history persistence broke)")

        findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
        browser.close()
    return findings


FLOWS = {
    "dice_roll_realtime": _dice_roll_flow,
    "map_token_table": _map_token_table_flow,
    "beyond20_bridge": _beyond20_bridge_flow,
}


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="tools.robots.flows")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    workdir = Path(tempfile.mkdtemp(prefix="vtt-flows-"))
    print(f"Flows: disposable stack in {workdir} …")
    all_findings: dict[str, list[str]] = {}
    with disposable_stack(workdir) as stack:
        for name, runner in FLOWS.items():
            print(f"  running {name} …")
            all_findings[name] = runner(stack, workdir)

    total = sum(len(v) for v in all_findings.values())
    print(f"\n{len(FLOWS)} flow(s) · {total} finding(s)")
    for name, findings in all_findings.items():
        for finding in findings:
            print(f"  - [{name}] {finding}")

    report = args.out or workdir.parent / "vtt-flows.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(
        {"status": "failed" if total else "passed", "flows": all_findings},
        indent=2), encoding="utf-8")
    print(f"JSON: {report}")
    import shutil
    shutil.rmtree(workdir, ignore_errors=True)
    return 0 if not total else 1


if __name__ == "__main__":
    sys.exit(main())
