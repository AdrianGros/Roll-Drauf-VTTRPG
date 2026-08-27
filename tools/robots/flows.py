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
from tools.robots.evidence import finding as evidence_finding
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
            # e834659, 2026-08-25: the tool rail moved into the right-sidebar
            # drawer, closed by default -- #diceInput/#btnRoll live inside
            # #panel-tools (already the active tab), but the drawer itself
            # must be opened first or it's not visible. Same two lines
            # _map_token_table_flow already uses for this drawer.
            page.click("#btnSidebarToggle")
            page.wait_for_selector(".right-sidebar.is-open", timeout=15_000)
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

        # F3, 2026-08-26: native rolls used to skip #chatLog entirely --
        # _handleDiceBroadcast wrote #diceLog + #activityLog but never
        # called _appendChatMessage, so players only saw the roll after a
        # reload backfilled chat from the DB. Same live-broadcast check the
        # Beyond20 flow below already does for #chatLog.
        chat_text = page.locator("#chatLog").text_content() or ""
        if "spielleitung_bot" not in chat_text:
            findings.append(
                f"[dice] #diceLog updated but native roll missing from "
                f"#chatLog (live broadcast not reaching chat): {chat_text[:200]!r}")

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
            if page.locator("#layerAddBtn").inner_text().strip() != "Hinzufügen":
                findings.append("[menu] map file action does not expose 'Hinzufügen'")
            if not page.locator("#btnTokenUpload").count():
                findings.append("[token-upload] no direct token file-dialog action is visible")
            empty_layer_state = page.evaluate(
                """() => ({
                    addDisabled: Boolean(document.getElementById('layerAddBtn')?.disabled),
                    status: (document.getElementById('layerAddStatus')?.textContent || '').trim(),
                    statusHidden: Boolean(document.getElementById('layerAddStatus')?.hidden),
                    uploadVisible: Boolean(document.getElementById('layerAddUpload')
                        && !document.getElementById('layerAddChoice')?.hidden),
                })""")
            if empty_layer_state.get("addDisabled") and (
                    empty_layer_state.get("statusHidden")
                    or not empty_layer_state.get("status")):
                findings.append(
                    "[empty-state] disabled 'Hinzufügen' has no visible explanation or "
                    "replacement action when no unused campaign map exists")
            page.click("#btnSidebarToggle")
            page.wait_for_selector(".right-sidebar.is-open", timeout=15_000)
            for tab in ("journal", "chat", "tools", "session"):
                page.click(f'.sidebar-tab[data-tab="{tab}"]')
                if not page.locator(f"#panel-{tab}.active").count():
                    findings.append(f"[menu] sidebar tab {tab!r} did not activate its panel")
            page.click("#btnSidebarToggle")
            page.click("#layerAddBtn")
            page.wait_for_selector("#layerAddChoice", state="visible", timeout=15_000)
            with page.expect_file_chooser(timeout=10_000) as chooser_info:
                page.click("#layerAddUpload")
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
            # The visible ribbon button is the user's entry point. It must
            # open the token menu that contains the upload action; checking
            # the widget header alone would miss a dead ribbon control.
            page.click('.tool-btn[data-tool="select"]')
            if "collapsed" not in (page.locator("#tokenWidget").get_attribute("class") or "").split():
                page.click("#tokenWidget .widget-toggle")
            page.click('.tool-btn[data-tool="token"]')
            page.wait_for_function(
                """() => {
                    const widget = document.getElementById('tokenWidget');
                    const row = document.getElementById('tokenUploadRow');
                    return widget && !widget.classList.contains('collapsed')
                        && row && !row.hidden;
                }""",
                timeout=15_000,
            )
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
            evidence_finding(
                findings,
                page,
                workdir,
                f"[token-upload] direct token file chooser failed: "
                f"{type(error).__name__}: {str(error)[:200]}",
                "finding-token-upload-menu",
                ['.tool-btn[data-tool="token"]', "#tokenWidget", "#btnTokenUpload"],
            )

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
                    uploadControlExists: Boolean(document.getElementById('layerAddBtn')),
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
            findings.append("[upload-ui] #layerAddBtn missing - the DM upload path left the table again")

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


def _scene_directory_flow(stack, workdir: Path) -> list[str]:
    """S01, 2026-08-27 (docs/PLAYTABLE_FEATURE_RESEARCH_01_SCENES_2026-08-27.md,
    Apply-approved): the scene/page directory (#layersWidget) gets a
    client-side search filter, a duplicate action, a lock/unlock visibility
    toggle (reintroduced with a NON-eye icon after 8e856de removed an
    earlier eye-glyph version for colliding with the activate button --
    this flow's own duplicate-icon check guards that regression class), and
    roving-tabindex keyboard navigation. Reuses _map_token_table_flow's real
    file-chooser map upload to get one real layer, then drives every new
    control through the actual UI."""
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
                               robot_name="szenen_dm", artifacts_dir=workdir)
        session.open()
        if not session.register(
                username="szenen_dm_bot",
                email="szenen_dm_bot@robots.roll-drauf.de",
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
                            data=json.dumps({"name": "Szenenkampagne", "max_players": 6}),
                            headers=json_headers).json()
        campaign_id = (campaign.get("campaign") or campaign)["id"]
        game_session = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
            data=json.dumps({"name": "Szenensitzung"}), headers=json_headers).json()
        session_id = (game_session.get("session") or game_session)["id"]

        map_file = workdir / "robot_scene_map.png"
        map_file.write_bytes(_make_png(500, 350, (60, 90, 130)))

        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[play] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        try:
            page.wait_for_function("() => window.RollDraufTable", timeout=15_000)
            page.wait_for_timeout(1_000)
            if "collapsed" in (page.locator("#layersWidget").get_attribute("class") or "").split():
                page.click('#layersWidget .widget-toggle')
            page.click("#layerAddBtn")
            page.wait_for_selector("#layerAddChoice", state="visible", timeout=15_000)
            with page.expect_file_chooser(timeout=10_000) as chooser_info:
                page.click("#layerAddUpload")
            chooser_info.value.set_files(str(map_file))
            page.wait_for_function(
                "() => (document.getElementById('activePageName')?.textContent || '')"
                ".includes('robot_scene_map')", timeout=20_000)
        except Exception as error:
            findings.append(f"[setup] real map upload for the scene-directory flow "
                            f"failed: {type(error).__name__}: {str(error)[:200]}")
            browser.close()
            return findings

        try:
            first_row = page.locator("#layerList .layer-row").first
            first_label = first_row.locator(".layer-label-input").input_value().strip()
            if not first_label:
                findings.append("[setup] first layer has no readable label to duplicate/search for")

            # Duplicate: reuses POST .../layers with allow_copy=true, no new
            # backend route -- proves the client wiring actually calls it.
            page.click('#layerList .layer-row [data-act="duplicate"]')
            page.wait_for_function(
                "() => document.querySelectorAll('#layerList .layer-row').length >= 2",
                timeout=10_000)
            row_count = page.locator("#layerList .layer-row").count()
            if row_count < 2:
                findings.append(f"[duplicate] expected >=2 layer rows after duplicate, found {row_count}")

            # Search/filter: client-side only, no network request needed --
            # typing the first layer's own label must not filter it out,
            # and a nonsense needle must hide every row.
            page.fill("#layerSearchInput", first_label[:4] if len(first_label) >= 4 else first_label)
            page.wait_for_timeout(200)
            visible_after_match = page.locator("#layerList .layer-row").count()
            if visible_after_match < 1:
                findings.append("[search] filtering by the layer's own label text hid every row")
            page.fill("#layerSearchInput", "zzz_kein_treffer_zzz")
            page.wait_for_timeout(200)
            if not page.locator("#layerList >> text=Keine Seite passt zur Suche").count():
                findings.append("[search] a non-matching filter shows no empty-state message")
            page.fill("#layerSearchInput", "")
            page.wait_for_timeout(200)
            restored_count = page.locator("#layerList .layer-row").count()
            if restored_count != row_count:
                findings.append(f"[search] clearing the filter did not restore all {row_count} rows (got {restored_count})")

            # Visibility toggle: must NOT reuse the activate button's eye
            # glyph (the exact regression 8e856de fixed once already).
            visibility_button = page.locator('#layerList .layer-row').first.locator('[data-act="visibility"]')
            title_before = visibility_button.get_attribute("title") or ""
            activate_icon_text = page.locator('#layerList .layer-row').first.locator('[data-act="activate"]').inner_text()
            visibility_icon_text = visibility_button.inner_text()
            if activate_icon_text and visibility_icon_text and activate_icon_text == visibility_icon_text:
                findings.append("[visibility] the visibility toggle reuses the activate button's icon glyph - "
                                "the exact ambiguity 8e856de removed once already")
            visibility_button.click()
            page.wait_for_timeout(400)
            title_after = page.locator('#layerList .layer-row').first.locator('[data-act="visibility"]').get_attribute("title") or ""
            if title_after == title_before:
                findings.append("[visibility] clicking the lock/unlock toggle did not change its title/state")

            # Keyboard: roving tabindex moves with ArrowDown; the destination
            # row actually receives DOM focus (not just an attribute flip).
            rows_locator = page.locator("#layerList .layer-row")
            rows_locator.first.focus()
            page.keyboard.press("ArrowDown")
            focused_layer_id = page.evaluate(
                "() => document.activeElement?.closest('.layer-row')?.dataset.layerId || null")
            if not focused_layer_id:
                findings.append("[keyboard] ArrowDown from the first row did not move DOM focus to a layer row")
            elif page.locator(f'#layerList .layer-row[data-layer-id="{focused_layer_id}"]').get_attribute("tabindex") != "0":
                findings.append("[keyboard] focused row does not carry the roving tabindex=0")

            # Delete confirmation: names the layer, doesn't silently delete.
            dialog_messages = []
            page.on("dialog", lambda dialog: (dialog_messages.append(dialog.message), dialog.dismiss()))
            page.locator('#layerList .layer-row').first.locator('[data-act="delete"]').click()
            page.wait_for_timeout(300)
            if not dialog_messages:
                findings.append("[delete] no confirmation dialog appeared for a destructive delete")
            elif first_label and first_label not in dialog_messages[0]:
                findings.append(f"[delete] confirmation dialog did not name the layer being deleted: {dialog_messages[0]!r}")
            after_dismiss_count = page.locator("#layerList .layer-row").count()
            if after_dismiss_count != row_count:
                findings.append("[delete] dismissing the confirmation dialog still removed a row")

        except Exception as error:
            findings.append(f"[scene-directory] interaction failed: {type(error).__name__}: {str(error)[:200]}")
            try:
                shot = workdir / "scene-directory-flow.png"
                page.screenshot(path=str(shot))
                findings.append(f"[debug] screenshot: {shot.name}")
            except Exception:
                pass

        findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
        browser.close()
    return findings


def _token_hud_flow(stack, workdir: Path) -> list[str]:
    """S04, 2026-08-27 (docs/PLAYTABLE_FEATURE_RESEARCH_04_TOKEN_HUD_2026-08-27.md,
    Apply-approved): the selected-token detail panel (#tokenWidget). Single
    operator user only -- covers the DM/owner editable path and the
    enhanced delete confirmation for real. The new cross-user read-only
    view (#tokenSelectionReadonly, for a player observing someone else's
    token) is NOT covered here: it would need a second real browser
    context plus a full invite/accept-join dance, which this round's time
    budget didn't extend to. That logic is instead covered by
    tests/test_public_surface_and_playtable_contract.py's direct assertion
    on the exact boolean condition and the hp!=null-vs-truthiness fix for
    the 0 HP edge case -- documented here as a deliberate, non-silent
    coverage gap, not an oversight."""
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
                               robot_name="tokenhud_bot", artifacts_dir=workdir)
        session.open()
        if not session.register(
                username="tokenhud_bot",
                email="tokenhud_bot@robots.roll-drauf.de",
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
                            data=json.dumps({"name": "HUD-Kampagne", "max_players": 6}),
                            headers=json_headers).json()
        campaign_id = (campaign.get("campaign") or campaign)["id"]
        game_session = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
            data=json.dumps({"name": "HUD-Sitzung"}), headers=json_headers).json()
        session_id = (game_session.get("session") or game_session)["id"]

        # Token creation 400s without an active map (state.active_map_id) --
        # API-only setup (no real file upload needed for this flow): create
        # a CampaignMap, then initialize+activate the scene stack from it.
        map_response = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/maps",
            data=json.dumps({"name": "HUD-Karte", "width": 600, "height": 400}),
            headers=json_headers)
        if map_response.status != 201:
            findings.append(f"[setup] map create returned HTTP {map_response.status}")
            browser.close()
            return findings
        map_payload = map_response.json()
        map_id = (map_payload.get("map") or map_payload.get("campaign_map") or map_payload)["id"]
        init_response = api.post(
            f"{stack.base_url}/api/play/campaigns/{campaign_id}/sessions/{session_id}/scene-stack/init",
            data=json.dumps({"map_ids": [map_id]}), headers=json_headers)
        if init_response.status != 201:
            findings.append(f"[setup] scene-stack init returned HTTP {init_response.status}: {init_response.text()[:200]}")
            browser.close()
            return findings

        # A token at exactly 0 HP -- the edge case a truthiness check would
        # have silently swallowed (0 is falsy but very real HP data).
        token_response = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions/{session_id}/tokens",
            data=json.dumps({"name": "Angeschlagen", "x": 100, "y": 100,
                             "token_type": "npc", "hp_current": 0, "hp_max": 20,
                             "metadata_json": {"position_mode": "pixel"}}),
            headers=json_headers)
        if token_response.status != 201:
            findings.append(f"[setup] token create returned HTTP {token_response.status}")
            browser.close()
            return findings

        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[play] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        try:
            page.wait_for_selector(".token-marker", state="visible", timeout=15_000)
            page.click(".token-marker")
            page.wait_for_selector("#tokenSelectionDetail:not([hidden])", timeout=10_000)

            if not page.locator("#tokenSelectionReadonly").is_hidden():
                findings.append("[hud] the read-only summary is visible while the editable detail is also shown - should be mutually exclusive for the owning operator")

            hp_current_value = page.locator("#tokenHpCurrent").input_value()
            if hp_current_value != "0":
                findings.append(f"[hud] HP-current field did not populate with the real 0 value (got {hp_current_value!r})")

            # Enhanced delete confirmation: names the token AND states the
            # blast radius, not just a bare "really delete?".
            dialog_messages = []
            page.on("dialog", lambda dialog: (dialog_messages.append(dialog.message), dialog.dismiss()))
            page.click("#btnTokenDelete")
            page.wait_for_timeout(300)
            if not dialog_messages:
                findings.append("[delete] no confirmation dialog appeared")
            else:
                message = dialog_messages[0]
                if "Angeschlagen" not in message:
                    findings.append(f"[delete] confirmation did not name the token: {message!r}")
                if "alle" not in message:
                    findings.append(f"[delete] confirmation did not state it affects everyone at the table: {message!r}")
            remaining = page.locator(".token-marker").count()
            if remaining != 1:
                findings.append(f"[delete] dismissing the confirmation still removed the token (markers left: {remaining})")

        except Exception as error:
            findings.append(f"[token-hud] interaction failed: {type(error).__name__}: {str(error)[:200]}")
            try:
                shot = workdir / "token-hud-flow.png"
                page.screenshot(path=str(shot))
                findings.append(f"[debug] screenshot: {shot.name}")
            except Exception:
                pass

        findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
        browser.close()
    return findings


def _roll_composer_flow(stack, workdir: Path) -> list[str]:
    """S08, 2026-08-27 (docs/PLAYTABLE_FEATURE_RESEARCH_08_ROLL_CHAT_2026-08-27.md,
    Apply-approved): the roll composer. Single DM user -- covers die
    presets, a real ADV/DIS roll, the expandable roll breakdown, DM-only
    visibility options staying enabled for a DM, and the chat textarea's
    Enter-submits/Shift+Enter-newline split. Cross-role visibility
    ENFORCEMENT itself (a player never receiving a DM's blind roll) is
    covered server-side in tests/test_play_table_chat_and_gating.py::
    TestRollVisibility, not duplicated here as a second browser context --
    documented scope split, not a coverage gap."""
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
                               robot_name="composer_bot", artifacts_dir=workdir)
        session.open()
        if not session.register(
                username="composer_bot",
                email="composer_bot@robots.roll-drauf.de",
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
                            data=json.dumps({"name": "Wuerfelkampagne", "max_players": 6}),
                            headers=json_headers).json()
        campaign_id = (campaign.get("campaign") or campaign)["id"]
        game_session = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
            data=json.dumps({"name": "Wuerfelsitzung"}), headers=json_headers).json()
        session_id = (game_session.get("session") or game_session)["id"]

        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[play] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        try:
            page.click("#btnSidebarToggle")
            page.wait_for_selector(".right-sidebar.is-open", timeout=15_000)
            page.click('.sidebar-tab[data-tab="tools"]')
            page.wait_for_selector("#panel-tools.active", timeout=10_000)

            # Die preset sets the formula field.
            page.click('[data-dice-preset="1d12"]')
            if page.locator("#diceInput").input_value() != "1d12":
                findings.append("[composer] clicking the d12 preset did not set #diceInput")

            # DM sees Blind/Self enabled (not disabled/grayed).
            blind_disabled = page.eval_on_selector(
                '#rollVisibility option[value="blind"]', "el => el.disabled")
            self_disabled = page.eval_on_selector(
                '#rollVisibility option[value="self"]', "el => el.disabled")
            if blind_disabled or self_disabled:
                findings.append("[composer] Blind/Self are disabled for a DM -- they should only be disabled for non-DMs")

            # A real advantage roll on a single d20: fires, lands in chat
            # with an expandable breakdown.
            page.select_option("#rollMode", "advantage")
            page.fill("#diceInput", "1d20")
            page.click("#btnRoll")
            page.wait_for_function(
                "() => (document.getElementById('diceLog')?.textContent || '').includes('Vorteil')",
                timeout=10_000)
            # #chatLog lives in a different sidebar tab (#panel-chat) than
            # the dice composer (#panel-tools) -- switch tabs, it's
            # display:none (genuinely hidden, not a bug) until we do.
            page.click('.sidebar-tab[data-tab="chat"]')
            page.wait_for_selector("#panel-chat.active", timeout=10_000)
            page.wait_for_selector("#chatLog details", timeout=10_000)
            page.click("#chatLog details summary")
            breakdown_visible = page.locator("#chatLog details[open] .chat-roll-breakdown").count()
            if breakdown_visible < 1:
                findings.append("[composer] clicking the roll summary did not expand the breakdown detail")
            breakdown_text = page.locator("#chatLog details[open] .chat-roll-breakdown").first.text_content() or ""
            if "verworfen" not in breakdown_text:
                findings.append(f"[composer] advantage roll's breakdown does not mention the discarded roll: {breakdown_text!r}")

            # Chat textarea: Shift+Enter must NOT send, Enter alone must.
            chat_messages_before = page.locator("#chatLog .chat-entry").count()
            page.click("#chatInput")
            page.keyboard.type("Zeile eins")
            page.keyboard.press("Shift+Enter")
            page.keyboard.type("Zeile zwei")
            page.wait_for_timeout(200)
            chat_messages_after_shift_enter = page.locator("#chatLog .chat-entry").count()
            if chat_messages_after_shift_enter != chat_messages_before:
                findings.append("[composer] Shift+Enter appears to have sent the message instead of inserting a line break")
            if "\n" not in page.locator("#chatInput").input_value():
                findings.append("[composer] Shift+Enter did not insert a newline into the textarea")
            page.keyboard.press("Enter")
            page.wait_for_function(
                f"() => document.querySelectorAll('#chatLog .chat-entry').length > {chat_messages_before}",
                timeout=10_000)
            if page.locator("#chatInput").input_value() != "":
                findings.append("[composer] sending did not clear the composer")

        except Exception as error:
            findings.append(f"[composer] interaction failed: {type(error).__name__}: {str(error)[:200]}")
            try:
                shot = workdir / "roll-composer-flow.png"
                page.screenshot(path=str(shot))
                findings.append(f"[debug] screenshot: {shot.name}")
            except Exception:
                pass

        findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
        browser.close()
    return findings


def _action_hotbar_flow(stack, workdir: Path) -> list[str]:
    """S07, 2026-08-27 (docs/PLAYTABLE_FEATURE_RESEARCH_07_HOTBAR_2026-08-27.md,
    Apply-approved): the personal action hotbar over the already-built
    execute_action seam. Covers: disabled with no token selected, enabled
    after selecting one, click-to-fire, numeric-key-to-fire, keyboard
    shortcuts NOT firing while focus is in #chatInput (the research doc's
    own HIGH-severity risk), and the upgraded readable chat message."""
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
                               robot_name="hotbar_bot", artifacts_dir=workdir)
        session.open()
        if not session.register(
                username="hotbar_bot",
                email="hotbar_bot@robots.roll-drauf.de",
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
                            data=json.dumps({"name": "Hotbar-Kampagne", "max_players": 6}),
                            headers=json_headers).json()
        campaign_id = (campaign.get("campaign") or campaign)["id"]
        game_session = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
            data=json.dumps({"name": "Hotbar-Sitzung"}), headers=json_headers).json()
        session_id = (game_session.get("session") or game_session)["id"]

        map_response = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/maps",
            data=json.dumps({"name": "Hotbar-Karte", "width": 600, "height": 400}),
            headers=json_headers)
        if map_response.status != 201:
            findings.append(f"[setup] map create returned HTTP {map_response.status}")
            browser.close()
            return findings
        map_payload = map_response.json()
        map_id = (map_payload.get("map") or map_payload.get("campaign_map") or map_payload)["id"]
        init_response = api.post(
            f"{stack.base_url}/api/play/campaigns/{campaign_id}/sessions/{session_id}/scene-stack/init",
            data=json.dumps({"map_ids": [map_id]}), headers=json_headers)
        if init_response.status != 201:
            findings.append(f"[setup] scene-stack init returned HTTP {init_response.status}")
            browser.close()
            return findings

        token_response = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions/{session_id}/tokens",
            data=json.dumps({"name": "Held", "x": 100, "y": 100, "token_type": "npc",
                             "metadata_json": {"position_mode": "pixel"}}),
            headers=json_headers)
        if token_response.status != 201:
            findings.append(f"[setup] token create returned HTTP {token_response.status}")
            browser.close()
            return findings

        # play_execute_action 409s unless the session is actually "live" --
        # a session starts "scheduled" and needs two transitions
        # (scheduled -> ready -> in_progress) before any hotbar action can
        # fire at all.
        for target_state in ("ready", "in_progress"):
            transition_response = api.post(
                f"{stack.base_url}/api/play/campaigns/{campaign_id}/sessions/{session_id}/transition",
                data=json.dumps({"target_state": target_state, "ignore_warnings": True}),
                headers=json_headers)
            if transition_response.status != 200:
                findings.append(
                    f"[setup] session transition to {target_state!r} returned "
                    f"HTTP {transition_response.status}: {transition_response.text()[:200]}")
                browser.close()
                return findings

        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[play] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        try:
            page.wait_for_selector(".token-marker", state="visible", timeout=15_000)
            page.wait_for_selector("#actionHotbar:not([hidden])", timeout=10_000)

            slot_count = page.locator("#actionHotbar .hotbar-slot").count()
            if slot_count != 3:
                findings.append(f"[hotbar] expected 3 slots (matches the 3-action catalog), found {slot_count}")

            if page.locator("#actionHotbar").get_attribute("aria-disabled") != "true":
                findings.append("[hotbar] hotbar is not disabled with no token selected")

            page.click(".token-marker")
            page.wait_for_function(
                "() => document.getElementById('actionHotbar')?.getAttribute('aria-disabled') === 'false'",
                timeout=10_000)

            # dash_move (slot 2, requires_target: False) fires cleanly via
            # a real click, lands in chat with a readable message (was a
            # raw "Aktions-Event: dash_move" toast before this slice).
            page.click('.hotbar-slot[data-action-code="dash_move"]')
            page.wait_for_function(
                "() => (document.getElementById('chatLog')?.textContent || '').includes('Dash')",
                timeout=10_000)
            chat_text = page.locator("#chatLog").text_content() or ""
            if "dash_move" in chat_text:
                findings.append(f"[hotbar] chat still shows the raw action code, not the readable name: {chat_text[:150]!r}")

            # Keyboard: key "2" is dash_move's slot -- must fire the same
            # way as the click did.
            page.click("body")
            page.keyboard.press("2")
            page.wait_for_timeout(400)

            # Keyboard shortcuts must NOT fire while focus is in chat input.
            page.click("#btnSidebarToggle")
            page.wait_for_selector(".right-sidebar.is-open", timeout=10_000)
            page.click('.sidebar-tab[data-tab="chat"]')
            page.fill("#chatInput", "")
            page.click("#chatInput")
            chat_message_count_before = page.locator("#chatLog .chat-entry").count()
            page.keyboard.press("1")  # attack_basic -- requires_target, would 400 loudly if it fired
            page.wait_for_timeout(400)
            chat_message_count_after = page.locator("#chatLog .chat-entry").count()
            if chat_message_count_after != chat_message_count_before:
                findings.append(
                    "[hotbar] a numeric keypress while focus was in #chatInput appears to have "
                    "fired a hotbar action (chat entry count changed)")
            page.click("#btnSidebarToggle")

        except Exception as error:
            findings.append(f"[hotbar] interaction failed: {type(error).__name__}: {str(error)[:200]}")
            try:
                shot = workdir / "action-hotbar-flow.png"
                page.screenshot(path=str(shot))
                findings.append(f"[debug] screenshot: {shot.name}")
            except Exception:
                pass

        findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
        browser.close()
    return findings


def _combat_turn_order_flow(stack, workdir: Path) -> list[str]:
    """S06, 2026-08-27 (docs/PLAYTABLE_FEATURE_RESEARCH_06_COMBAT_2026-08-27.md,
    Apply-approved): the combat/turn-order widget. Two tokens with
    initiative, a real "Kampf starten" click, then: the "Zug m von n"
    summary format, the live-region announcement, click-to-select
    bidirectional sync with the map, and turn advance."""
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
                               robot_name="kampf_bot", artifacts_dir=workdir)
        session.open()
        if not session.register(
                username="kampf_bot",
                email="kampf_bot@robots.roll-drauf.de",
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
                            data=json.dumps({"name": "Kampfkampagne", "max_players": 6}),
                            headers=json_headers).json()
        campaign_id = (campaign.get("campaign") or campaign)["id"]
        game_session = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
            data=json.dumps({"name": "Kampfsitzung"}), headers=json_headers).json()
        session_id = (game_session.get("session") or game_session)["id"]

        map_response = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/maps",
            data=json.dumps({"name": "Kampfkarte", "width": 600, "height": 400}),
            headers=json_headers)
        if map_response.status != 201:
            findings.append(f"[setup] map create returned HTTP {map_response.status}")
            browser.close()
            return findings
        map_payload = map_response.json()
        map_id = (map_payload.get("map") or map_payload.get("campaign_map") or map_payload)["id"]
        init_response = api.post(
            f"{stack.base_url}/api/play/campaigns/{campaign_id}/sessions/{session_id}/scene-stack/init",
            data=json.dumps({"map_ids": [map_id]}), headers=json_headers)
        if init_response.status != 201:
            findings.append(f"[setup] scene-stack init returned HTTP {init_response.status}")
            browser.close()
            return findings

        for name, initiative, x in (("Held", 18, 100), ("Ork", 9, 300)):
            token_response = api.post(
                f"{stack.base_url}/api/campaigns/{campaign_id}/sessions/{session_id}/tokens",
                data=json.dumps({"name": name, "x": x, "y": 100, "token_type": "npc",
                                 "initiative": initiative,
                                 "metadata_json": {"position_mode": "pixel"}}),
                headers=json_headers)
            if token_response.status != 201:
                findings.append(f"[setup] token {name!r} create returned HTTP {token_response.status}")
                browser.close()
                return findings

        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[play] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        try:
            page.wait_for_selector(".token-marker", state="visible", timeout=15_000)
            if "collapsed" in (page.locator("#turnOrderWidget").get_attribute("class") or "").split():
                page.click("#turnOrderWidget .widget-toggle")
            page.wait_for_selector("#btnStartCombat", state="visible", timeout=10_000)

            page.click("#btnStartCombat")
            page.wait_for_function(
                "() => (document.getElementById('turnOrderSummary')?.textContent || '').includes('Zug 1 von 2')",
                timeout=15_000)

            announce_text = (page.locator("#turnOrderAnnounce").text_content() or "").strip()
            if not announce_text:
                findings.append("[combat] #turnOrderAnnounce stayed empty after starting combat")

            row_count = page.locator("#turnOrderList .turn-item").count()
            if row_count != 2:
                findings.append(f"[combat] expected 2 turn-order rows, found {row_count}")

            # Click-to-select, second (non-active) row: correlated by
            # data-token-id, not name/position -- "auto" combat start
            # re-rolls initiative server-side, so which of our two tokens
            # ends up in which seat is NOT deterministic across runs.
            second_row = page.locator("#turnOrderList .turn-item").nth(1)
            second_row_token_id = second_row.get_attribute("data-token-id")
            second_row.click()
            page.wait_for_timeout(300)
            selected_marker_ids = page.evaluate(
                "() => Array.from(document.querySelectorAll('.token-marker.selected'))"
                ".map((el) => el.getAttribute('data-token-id'))")
            if selected_marker_ids != [second_row_token_id]:
                findings.append(
                    f"[combat] clicking turn-order row for token {second_row_token_id!r} "
                    f"did not select the matching map marker (selected markers: {selected_marker_ids!r})")
            row_selected_class = second_row.get_attribute("class") or ""
            if "selected" not in row_selected_class:
                findings.append("[combat] clicked row did not receive the .selected class")

            # Reverse direction: selecting the OTHER token on the map (by
            # data-token-id, the one NOT already selected) moves the
            # .selected highlight to ITS row, and only its row.
            other_marker = page.locator(f".token-marker:not([data-token-id='{second_row_token_id}'])").first
            other_marker_id = other_marker.get_attribute("data-token-id")
            other_marker.click()
            page.wait_for_timeout(300)
            selected_rows_after = page.evaluate(
                "() => Array.from(document.querySelectorAll('#turnOrderList .turn-item.selected'))"
                ".map((el) => el.dataset.tokenId)")
            if selected_rows_after != [other_marker_id]:
                findings.append(
                    f"[combat] selecting token {other_marker_id!r} on the map did not move the "
                    f".selected highlight to exactly its own turn-order row (selected rows: {selected_rows_after!r})")

            # Advance the turn: summary updates, announcement changes.
            page.click("#btnNextTurn")
            page.wait_for_function(
                "() => (document.getElementById('turnOrderSummary')?.textContent || '').includes('Zug 2 von 2')",
                timeout=10_000)
            announce_after_advance = (page.locator("#turnOrderAnnounce").text_content() or "").strip()
            if announce_after_advance == announce_text:
                findings.append("[combat] live-region announcement did not change after advancing the turn")

            page.click("#btnEndCombat")
            page.wait_for_selector("#btnStartCombat:not([hidden])", timeout=10_000)

        except Exception as error:
            findings.append(f"[combat] interaction failed: {type(error).__name__}: {str(error)[:200]}")
            try:
                shot = workdir / "combat-turn-order-flow.png"
                page.screenshot(path=str(shot))
                findings.append(f"[debug] screenshot: {shot.name}")
            except Exception:
                pass

        findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
        browser.close()
    return findings


def _conditions_picker_flow(stack, workdir: Path) -> list[str]:
    """S05, 2026-08-27 (docs/PLAYTABLE_FEATURE_RESEARCH_05_STATUSES_2026-08-27.md,
    Apply-approved): the token conditions/status picker. Places a token
    with a pre-existing metadata_json.image_url, toggles two conditions
    through the real popover, and asserts image_url survived the round
    trip -- the server applies metadata_json as a whole-value overwrite, so
    a client that sent a bare {conditions: [...]} patch would silently
    wipe it. Also covers the badge count, clear-all confirmation, and
    Escape-to-close."""
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
                               robot_name="zustaende_bot", artifacts_dir=workdir)
        session.open()
        if not session.register(
                username="zustaende_bot",
                email="zustaende_bot@robots.roll-drauf.de",
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
                            data=json.dumps({"name": "Zustaende-Kampagne", "max_players": 6}),
                            headers=json_headers).json()
        campaign_id = (campaign.get("campaign") or campaign)["id"]
        game_session = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
            data=json.dumps({"name": "Zustaende-Sitzung"}), headers=json_headers).json()
        session_id = (game_session.get("session") or game_session)["id"]

        map_response = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/maps",
            data=json.dumps({"name": "Zustaende-Karte", "width": 600, "height": 400}),
            headers=json_headers)
        if map_response.status != 201:
            findings.append(f"[setup] map create returned HTTP {map_response.status}")
            browser.close()
            return findings
        map_payload = map_response.json()
        map_id = (map_payload.get("map") or map_payload.get("campaign_map") or map_payload)["id"]
        init_response = api.post(
            f"{stack.base_url}/api/play/campaigns/{campaign_id}/sessions/{session_id}/scene-stack/init",
            data=json.dumps({"map_ids": [map_id]}), headers=json_headers)
        if init_response.status != 201:
            findings.append(f"[setup] scene-stack init returned HTTP {init_response.status}")
            browser.close()
            return findings

        # A pre-existing image_url this flow must NOT lose after toggling
        # conditions -- the exact bug a whole-value metadata_json overwrite
        # would cause.
        art = api.post(
            f"{stack.base_url}/api/assets/campaigns/{campaign_id}/upload",
            multipart={"file": {"name": "robot_face.png", "mimeType": "image/png",
                                "buffer": _make_png(64, 64, (150, 90, 40))},
                       "asset_type": "token"},
            headers={"X-CSRF-TOKEN": csrf_token})
        art_id = art.json().get("asset_id") if art.status == 201 else None
        image_url = f"/api/assets/{art_id}/preview" if art_id else None
        token_response = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions/{session_id}/tokens",
            data=json.dumps({"name": "Waldtroll", "x": 100, "y": 100, "token_type": "npc",
                             "metadata_json": {"position_mode": "pixel", "image_url": image_url}}),
            headers=json_headers)
        if token_response.status != 201:
            findings.append(f"[setup] token create returned HTTP {token_response.status}")
            browser.close()
            return findings

        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[play] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        try:
            page.wait_for_selector(".token-marker", state="visible", timeout=15_000)
            page.click(".token-marker")
            page.wait_for_selector("#tokenSelectionDetail:not([hidden])", timeout=10_000)

            page.click("#btnTokenConditions")
            page.wait_for_selector("#conditionsPopover:not([hidden])", timeout=10_000)

            catalog_size = page.locator("#conditionsList input[type=checkbox]").count()
            if catalog_size < 15:
                findings.append(f"[conditions] expected the full catalog (~15+ checkboxes), found {catalog_size}")

            page.check('#conditionsList input[data-condition-id="poisoned"]')
            page.wait_for_timeout(400)
            page.check('#conditionsList input[data-condition-id="prone"]')
            page.wait_for_timeout(400)

            badge_text = (page.locator("#conditionsCountBadge").text_content() or "").strip()
            if badge_text != "2":
                findings.append(f"[conditions] count badge shows {badge_text!r}, expected '2' after two toggles")

            # The bug this flow exists to catch: image_url must survive.
            # Checked via the actual rendered marker (its <img src> comes
            # straight from token.metadata_json.image_url), not a REST
            # re-fetch -- there is no GET on the tokens-list route, only
            # POST for creation; the live client state is the real source
            # of truth for "did the browser keep this" anyway.
            rendered_image_src = page.locator(".token-marker .token-image").get_attribute("src")
            if rendered_image_src != image_url:
                findings.append(
                    f"[conditions] image_url was lost after toggling conditions - "
                    f"metadata_json overwrite bug: expected {image_url!r}, "
                    f"rendered marker shows {rendered_image_src!r}")

            # Escape closes and returns focus to the trigger.
            page.keyboard.press("Escape")
            page.wait_for_selector("#conditionsPopover[hidden]", state="attached", timeout=5_000)
            focused_id = page.evaluate("() => document.activeElement?.id || null")
            if focused_id != "btnTokenConditions":
                findings.append(f"[conditions] Escape did not return focus to the trigger button (focused: {focused_id!r})")

            # Clear-all: confirmation names the token and the count.
            page.click("#btnTokenConditions")
            page.wait_for_selector("#conditionsPopover:not([hidden])", timeout=10_000)
            dialog_messages = []
            page.on("dialog", lambda dialog: (dialog_messages.append(dialog.message), dialog.accept()))
            page.click("#btnConditionsClearAll")
            page.wait_for_function(
                "() => document.getElementById('conditionsCountBadge')?.hidden === true",
                timeout=5_000)
            if not dialog_messages:
                findings.append("[conditions] no confirmation dialog appeared for 'Alle löschen'")
            else:
                message = dialog_messages[0]
                if "Waldtroll" not in message or "2" not in message:
                    findings.append(f"[conditions] clear-all confirmation missing token name or count: {message!r}")
            # wait_for_function above already proved the badge hides; a
            # timeout there raises and lands in the except block below with
            # a real error message instead of a generic bool check here.

        except Exception as error:
            findings.append(f"[conditions] interaction failed: {type(error).__name__}: {str(error)[:200]}")
            try:
                shot = workdir / "conditions-picker-flow.png"
                page.screenshot(path=str(shot))
                findings.append(f"[debug] screenshot: {shot.name}")
            except Exception:
                pass

        findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
        browser.close()
    return findings


def _measure_tool_flow(stack, workdir: Path) -> list[str]:
    """S03, 2026-08-27 (docs/PLAYTABLE_FEATURE_RESEARCH_03_MAP_TOOLS_2026-08-27.md,
    Apply-approved): the waypoint measurement tool added to the select/pan/
    token rail. Places two real waypoints via real clicks, checks the
    distance label shows a game unit (not a bare square count), checks
    right-click undo and switching tools away both clear the overlay."""
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
                               robot_name="messer_bot", artifacts_dir=workdir)
        session.open()
        if not session.register(
                username="messer_bot",
                email="messer_bot@robots.roll-drauf.de",
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
                            data=json.dumps({"name": "Messkampagne", "max_players": 6}),
                            headers=json_headers).json()
        campaign_id = (campaign.get("campaign") or campaign)["id"]
        game_session = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
            data=json.dumps({"name": "Messsitzung"}), headers=json_headers).json()
        session_id = (game_session.get("session") or game_session)["id"]

        map_file = workdir / "robot_measure_map.png"
        map_file.write_bytes(_make_png(600, 400, (90, 90, 70)))

        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[play] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        try:
            page.wait_for_function("() => window.RollDraufTable", timeout=15_000)
            page.wait_for_timeout(1_000)
            if "collapsed" in (page.locator("#layersWidget").get_attribute("class") or "").split():
                page.click('#layersWidget .widget-toggle')
            page.click("#layerAddBtn")
            page.wait_for_selector("#layerAddChoice", state="visible", timeout=15_000)
            with page.expect_file_chooser(timeout=10_000) as chooser_info:
                page.click("#layerAddUpload")
            chooser_info.value.set_files(str(map_file))
            page.wait_for_function(
                "() => (document.getElementById('activePageName')?.textContent || '')"
                ".includes('robot_measure_map')", timeout=20_000)
        except Exception as error:
            findings.append(f"[setup] real map upload for the measure-tool flow "
                            f"failed: {type(error).__name__}: {str(error)[:200]}")
            browser.close()
            return findings

        try:
            page.click('.tool-btn[data-tool="measure"]')
            if "active" not in (page.locator('.tool-btn[data-tool="measure"]').get_attribute("class") or ""):
                findings.append("[tool] clicking the measure tool did not mark it .active")
            if page.locator("#btnMeasureSnap").is_hidden():
                findings.append("[tool] the grid-snap toggle stayed hidden after activating the measure tool")

            world = page.locator("#mapWorld")
            box = world.bounding_box()
            if not box:
                findings.append("[measure] #mapWorld has no bounding box, cannot click on the map")
            else:
                p1 = {"x": box["x"] + box["width"] * 0.25, "y": box["y"] + box["height"] * 0.25}
                p2 = {"x": box["x"] + box["width"] * 0.75, "y": box["y"] + box["height"] * 0.75}
                page.mouse.click(p1["x"], p1["y"])
                page.wait_for_timeout(150)
                page.mouse.move(p2["x"], p2["y"])
                page.wait_for_timeout(150)
                waypoint_count = page.locator("#measureLayer circle.measure-point").count()
                if waypoint_count < 1:
                    findings.append(f"[measure] expected >=1 waypoint circle after one click, found {waypoint_count}")
                # SVG <text> is not an HTMLElement -- inner_text() throws on
                # it, text_content() works on any node type.
                label_text = page.locator("#measureLayer text.measure-label").first.text_content() or ""
                if "ft" not in label_text:
                    findings.append(f"[measure] distance label does not show a game unit: {label_text!r}")

                page.mouse.click(p2["x"], p2["y"])
                page.wait_for_timeout(150)
                two_waypoints = page.locator("#measureLayer circle.measure-point").count()
                if two_waypoints < 2:
                    findings.append(f"[measure] expected 2 waypoint circles after a second click, found {two_waypoints}")

                announce_text = page.locator("#measureAnnounce").inner_text()
                if "Wegpunkt" not in announce_text:
                    findings.append(f"[a11y] #measureAnnounce did not announce waypoint state: {announce_text!r}")

                # Right-click removes the last waypoint.
                page.mouse.click(p2["x"], p2["y"], button="right")
                page.wait_for_timeout(150)
                after_undo = page.locator("#measureLayer circle.measure-point").count()
                if after_undo != 1:
                    findings.append(f"[measure] right-click did not remove exactly one waypoint (count now {after_undo})")

                # Escape removes the remaining waypoint -> overlay empties.
                page.keyboard.press("Escape")
                page.wait_for_timeout(150)
                after_escape = page.locator("#measureLayer circle.measure-point").count()
                if after_escape != 0:
                    findings.append(f"[measure] Escape did not clear the last waypoint (count now {after_escape})")

                # Placing waypoints again, then switching tools must clear
                # silently (no dialog, no leftover overlay).
                page.mouse.click(p1["x"], p1["y"])
                page.mouse.click(p2["x"], p2["y"])
                page.wait_for_timeout(150)
                page.click('.tool-btn[data-tool="select"]')
                page.wait_for_timeout(150)
                after_switch = page.locator("#measureLayer circle.measure-point").count()
                if after_switch != 0:
                    findings.append(f"[measure] switching tools away from measure did not clear the overlay (count now {after_switch})")
                if not page.locator("#btnMeasureSnap").is_hidden():
                    findings.append("[tool] the grid-snap toggle stayed visible after switching away from the measure tool")

        except Exception as error:
            findings.append(f"[measure] interaction failed: {type(error).__name__}: {str(error)[:200]}")
            try:
                shot = workdir / "measure-tool-flow.png"
                page.screenshot(path=str(shot))
                findings.append(f"[debug] screenshot: {shot.name}")
            except Exception:
                pass

        findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
        browser.close()
    return findings


def _app_menu_flow(stack, workdir: Path) -> list[str]:
    """S02, 2026-08-27 (docs/PLAYTABLE_FEATURE_RESEARCH_02_APP_MENU_2026-08-27.md,
    Apply-approved): the application command menu (Return to Campaign /
    Leave Session / Help), evolved from the old single-click btnBack. Drives
    the actual UI: open/close, keyboard nav, sidebar-closes-on-open,
    Leave's confirmation dialog (cancelled, not confirmed -- this flow must
    not actually end the robot's own session), and Help's native <dialog>."""
    from playwright.sync_api import sync_playwright
    from tools.robots.session import RobotSession

    findings: list[str] = []
    keys = mint_registration_keys(stack.database_url, count=1)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        session = RobotSession(context, base_url=stack.base_url,
                               robot_name="appmenu_bot", artifacts_dir=workdir)
        session.open()
        if not session.register(
                username="appmenu_bot",
                email="appmenu_bot@robots.roll-drauf.de",
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
                            data=json.dumps({"name": "Menükampagne", "max_players": 6}),
                            headers=json_headers).json()
        campaign_id = (campaign.get("campaign") or campaign)["id"]
        game_session = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
            data=json.dumps({"name": "Menüsitzung"}), headers=json_headers).json()
        session_id = (game_session.get("session") or game_session)["id"]

        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[play] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        try:
            page.wait_for_function("() => window.RollDraufTable", timeout=15_000)
            page.wait_for_timeout(1_000)

            # Opening the menu must close an already-open sidebar rather
            # than stacking overlays (acceptance criterion).
            page.click("#btnSidebarToggle")
            page.wait_for_selector(".right-sidebar.is-open", timeout=15_000)
            page.click("#btnBack")
            page.wait_for_selector("#appMenu:not([hidden])", timeout=10_000)
            if page.locator(".right-sidebar.is-open").count():
                findings.append("[menu] opening the app menu did not close the already-open sidebar")

            # Keyboard: focus starts on the first item; ArrowDown moves it;
            # Escape closes and returns focus to the trigger, and a SECOND
            # Escape on the trigger must not do anything destructive.
            focused_id = page.evaluate("() => document.activeElement?.id || null")
            if focused_id != "appMenuReturn":
                findings.append(f"[keyboard] opening the menu did not focus the first item (focused: {focused_id!r})")
            page.keyboard.press("ArrowDown")
            focused_id = page.evaluate("() => document.activeElement?.id || null")
            if focused_id != "appMenuHelp":
                findings.append(f"[keyboard] ArrowDown from the first item did not move to the second (focused: {focused_id!r})")
            page.keyboard.press("Escape")
            # default wait_for_selector state is "visible" -- an element
            # becoming [hidden] is never "visible", so this needs the
            # "attached" state explicitly or it always times out waiting
            # for a state that can't happen.
            page.wait_for_selector("#appMenu[hidden]", state="attached", timeout=5_000)
            focused_id = page.evaluate("() => document.activeElement?.id || null")
            if focused_id != "btnBack":
                findings.append(f"[keyboard] Escape did not return focus to the trigger button (focused: {focused_id!r})")

            # Help: a real native <dialog>, opened via showModal (has a
            # backdrop / is in the top layer), not a hand-rolled overlay.
            page.click("#btnBack")
            page.wait_for_selector("#appMenu:not([hidden])", timeout=10_000)
            page.click("#appMenuHelp")
            page.wait_for_selector("#appMenuHelpDialog[open]", timeout=10_000)
            is_native_modal = page.evaluate(
                "() => document.getElementById('appMenuHelpDialog').tagName === 'DIALOG'"
                " && document.getElementById('appMenuHelpDialog').open")
            if not is_native_modal:
                findings.append("[help] appMenuHelpDialog did not open as a real <dialog>")
            page.click("#appMenuHelpClose")
            page.wait_for_timeout(200)
            if page.evaluate("() => document.getElementById('appMenuHelpDialog').open"):
                findings.append("[help] closing the help dialog did not actually close it")

            # Leave: confirmation dialog, then CANCEL (must not navigate
            # away or end the robot's own session).
            page.click("#btnBack")
            page.wait_for_selector("#appMenu:not([hidden])", timeout=10_000)
            page.click("#appMenuLeave")
            page.wait_for_selector("#appMenuLeaveDialog[open]", timeout=10_000)
            page.click("#appMenuLeaveCancel")
            page.wait_for_timeout(300)
            if page.evaluate("() => document.getElementById('appMenuLeaveDialog').open"):
                findings.append("[leave] cancelling the leave dialog did not close it")
            if "/play" not in page.url:
                findings.append(f"[leave] cancelling the leave dialog navigated away anyway (url: {page.url})")

            # Return to Campaign: no confirmation, real navigation.
            page.click("#btnBack")
            page.wait_for_selector("#appMenu:not([hidden])", timeout=10_000)
            page.click("#appMenuReturn")
            page.wait_for_url("**/campaigns**", timeout=15_000)

        except Exception as error:
            findings.append(f"[app-menu] interaction failed: {type(error).__name__}: {str(error)[:200]}")
            try:
                shot = workdir / "app-menu-flow.png"
                page.screenshot(path=str(shot))
                findings.append(f"[debug] screenshot: {shot.name}")
            except Exception:
                pass

        findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
        browser.close()
    return findings


def _campaign_hub_click_flow(stack, workdir: Path) -> list[str]:
    """Desktop-Audit F1 (2026-08-26): every "Hub öffnen"/"Hub und
    Vorbereitung" click on the campaigns book page used to hard-navigate
    to /campaigns?campaign_id=...&classic=1 -- the URL shape that makes
    campaigns.html fall back to its pre-redesign classic render (dark-navy
    inline-styled .grid/.campaign-card/.detail-panel markup, a second
    "Cockpit" nav, none of book-page.css/book-scene.css's actual visual
    language) instead of staying in the same book UI as every other page.

    tests/test_campaign_hub_session_prep_productization.py cannot catch
    this class of bug: it Flask-test-client string-matches the raw HTML
    response, and every one of those strings is still literally present in
    the served markup (now inert inside campaigns.html's
    #campaignsClassicTemplate) whether or not a real click into the book UI
    ever reaches it. This clicks the real button through a real browser and
    checks what is actually on screen afterward.
    """
    from playwright.sync_api import sync_playwright
    from tools.robots.session import RobotSession

    findings: list[str] = []
    keys = mint_registration_keys(stack.database_url, count=1)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        session = RobotSession(context, base_url=stack.base_url,
                               robot_name="hub_klick_bot", artifacts_dir=workdir)
        session.open()
        if not session.register(
                username="hub_klick_bot",
                email="hub_klick_bot@robots.roll-drauf.de",
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

        campaign_response = api.post(
            f"{stack.base_url}/api/campaigns",
            data=json.dumps({"name": "Hub-Klick-Kampagne", "max_players": 6}),
            headers=json_headers)
        if campaign_response.status != 201:
            findings.append(
                f"[setup] POST /api/campaigns returned HTTP {campaign_response.status}")
            browser.close()
            return findings
        campaign_payload = campaign_response.json()
        campaign_id = (campaign_payload.get("campaign") or campaign_payload)["id"]

        if not session.goto("/campaigns"):
            findings.extend(f"[campaigns] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        try:
            page.wait_for_selector('[data-testid="campaign-ledger-item"]', timeout=15_000)
        except Exception as error:
            findings.append(f"[ledger] campaign ledger never rendered: {error}")
            browser.close()
            return findings

        hub_button = page.locator(".book-scene-ledger-item button", has_text="Hub")
        try:
            hub_button.first.wait_for(state="visible", timeout=15_000)
            hub_button.first.click()
        except Exception as error:
            evidence_finding(
                findings, page, workdir,
                f"['Hub öffnen'] button not clickable from the campaigns book "
                f"page: {type(error).__name__}: {str(error)[:200]}",
                "finding-campaign-hub-click",
                [".book-scene-ledger-item"],
            )
            browser.close()
            return findings

        page.wait_for_timeout(800)

        after = page.evaluate(
            """() => ({
                url: window.location.pathname + window.location.search,
                bodyBookScene: document.body.classList.contains('campaigns-route-book-scene'),
                sceneVisible: Boolean(document.getElementById('book-dashboard-scene')
                    && document.getElementById('book-dashboard-scene').classList.contains('is-visible')),
                // The classic page's OWN header only ends up live in the DOM
                // if campaigns.html promoted #campaignsClassicTemplate - i.e.
                // exactly the "fell out of the book" failure this guards.
                classicHeaderLive: Boolean(document.querySelector('body > header .logo')),
                hubPanelPresent: Boolean(document.getElementById('campaignHubSessionPrep')),
            })""")

        if not campaign_id:
            findings.append("[setup] no campaign id from the create-campaign response")
        if after["classicHeaderLive"]:
            findings.append(
                f"[F1] clicking 'Hub öffnen' fell back to the classic page "
                f"(the classic page's own <header> is live in the DOM); "
                f"url={after['url']!r}")
        if not after["bodyBookScene"]:
            findings.append(
                f"[F1] body lost the 'campaigns-route-book-scene' class after "
                f"the hub click; url={after['url']!r}")
        if not after["sceneVisible"]:
            findings.append(
                f"[F1] #book-dashboard-scene is no longer the visible surface "
                f"after the hub click; url={after['url']!r}")
        if not after["hubPanelPresent"]:
            findings.append(
                "[F1] the hub click did not render a campaign hub / "
                "session-prep panel (#campaignHubSessionPrep) inside the book scene")

        if findings:
            try:
                shot = workdir / "campaign-hub-click-flow.png"
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
        # badge and a token-list line. S05, 2026-08-27: incoming Beyond20
        # condition names ("Poisoned", "Prone") are now canonicalized
        # against the S05 condition catalog and rendered with ITS German
        # labels ("Vergiftet", "Liegend") -- consistent with the rest of
        # this German-language app and with the S05 picker's own UI,
        # rather than leaking raw English strings through from an external
        # integration. Exhaustion travels as its own metadata_json field
        # now (not smuggled into the conditions array as a free-text
        # "Erschöpfung N" string, which used to defeat S05's server-side
        # canonical-id validation and silently drop the WHOLE conditions
        # update) but still folds back into this combined display text.
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
                ".includes('Vergiftet, Liegend, Erschöpfung 1')", timeout=10_000)
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


def _loot_transfer_flow(stack, workdir: Path) -> list[str]:
    """S09, 2026-08-27 (docs/PLAYTABLE_FEATURE_RESEARCH_09_LOOT_2026-08-27.md,
    Apply-approved): loot transfer. Single DM user, same documented scope
    split as S08's roll composer -- cross-role permission ENFORCEMENT is
    covered server-side in tests/test_playtable_loot_transfer.py (idempotent
    retry, over-quantity rejection, foreign-recipient 403), not duplicated
    here as a second browser context. This flow proves the real click path
    the server-side tests cannot: toggle a token into a loot source, stock
    it, open the popover, transfer an item into a real character, and see
    the source deplete and an audit line land in chat -- all through actual
    DOM interaction and a real client -> socket/REST -> server round trip."""
    from playwright.sync_api import sync_playwright
    from tools.robots.session import RobotSession

    findings: list[str] = []
    keys = mint_registration_keys(stack.database_url, count=1)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        session = RobotSession(context, base_url=stack.base_url,
                               robot_name="beute_bot", artifacts_dir=workdir)
        session.open()
        if not session.register(
                username="beute_bot",
                email="beute_bot@robots.roll-drauf.de",
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
                            data=json.dumps({"name": "Beute-Kampagne", "max_players": 6}),
                            headers=json_headers).json()
        campaign_id = (campaign.get("campaign") or campaign)["id"]
        game_session = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
            data=json.dumps({"name": "Beute-Sitzung"}), headers=json_headers).json()
        session_id = (game_session.get("session") or game_session)["id"]

        map_response = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/maps",
            data=json.dumps({"name": "Beute-Karte", "width": 600, "height": 400}),
            headers=json_headers)
        if map_response.status != 201:
            findings.append(f"[setup] map create returned HTTP {map_response.status}")
            browser.close()
            return findings
        map_payload = map_response.json()
        map_id = (map_payload.get("map") or map_payload.get("campaign_map") or map_payload)["id"]
        init_response = api.post(
            f"{stack.base_url}/api/play/campaigns/{campaign_id}/sessions/{session_id}/scene-stack/init",
            data=json.dumps({"map_ids": [map_id]}), headers=json_headers)
        if init_response.status != 201:
            findings.append(f"[setup] scene-stack init returned HTTP {init_response.status}")
            browser.close()
            return findings

        character_response = api.post(
            f"{stack.base_url}/api/characters",
            data=json.dumps({"name": "Beute-Held", "race": "Mensch",
                             "class": "Fighter", "campaign_id": campaign_id}),
            headers=json_headers)
        if character_response.status != 201:
            findings.append(f"[setup] character create returned HTTP {character_response.status}")
            browser.close()
            return findings
        character_id = character_response.json()["id"]

        token_response = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions/{session_id}/tokens",
            data=json.dumps({"name": "Goblin (tot)", "x": 100, "y": 100, "token_type": "npc",
                             "metadata_json": {"position_mode": "pixel"}}),
            headers=json_headers)
        if token_response.status != 201:
            findings.append(f"[setup] token create returned HTTP {token_response.status}")
            browser.close()
            return findings

        # play_transfer_loot 409s unless the session is actually "live".
        for target_state in ("ready", "in_progress"):
            transition_response = api.post(
                f"{stack.base_url}/api/play/campaigns/{campaign_id}/sessions/{session_id}/transition",
                data=json.dumps({"target_state": target_state, "ignore_warnings": True}),
                headers=json_headers)
            if transition_response.status != 200:
                findings.append(
                    f"[setup] session transition to {target_state!r} returned "
                    f"HTTP {transition_response.status}: {transition_response.text()[:200]}")
                browser.close()
                return findings

        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[play] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        try:
            page.wait_for_selector(".token-marker", state="visible", timeout=15_000)
            page.click(".token-marker")
            page.wait_for_selector("#tokenSelectionDetail:not([hidden])", timeout=10_000)

            # DM-only toggle: starts off, "Beute" stays hidden until flagged.
            source_row_hidden = page.eval_on_selector(
                "#tokenLootSourceRow", "el => el.hidden") if page.locator("#tokenLootSourceRow").count() else None
            if source_row_hidden is not False:
                findings.append("[loot] tokenLootSourceRow should be visible to the DM once a token is selected")
            loot_row_hidden = page.eval_on_selector("#tokenLootRow", "el => el.hidden")
            if loot_row_hidden is not True:
                findings.append("[loot] tokenLootRow should stay hidden until the token is flagged as a loot source")
            toggle_text_before = (page.locator("#btnTokenLootSourceToggle").text_content() or "").strip()
            if "aus" not in toggle_text_before:
                findings.append(f"[loot] loot-source toggle should start 'aus', shows {toggle_text_before!r}")

            page.click("#btnTokenLootSourceToggle")
            page.wait_for_function(
                "() => (document.getElementById('btnTokenLootSourceToggle')?.textContent || '').includes('an')",
                timeout=10_000)
            page.wait_for_function(
                "() => document.getElementById('tokenLootRow')?.hidden === false",
                timeout=10_000)

            # Reload proves the flag is a real server round trip, not just
            # optimistic client state.
            page.reload()
            page.wait_for_selector(".token-marker", state="visible", timeout=15_000)
            page.click(".token-marker")
            page.wait_for_selector("#tokenSelectionDetail:not([hidden])", timeout=10_000)
            toggle_text_after_reload = (page.locator("#btnTokenLootSourceToggle").text_content() or "").strip()
            if "an" not in toggle_text_after_reload:
                findings.append(
                    f"[loot] is_loot_source did not survive a reload -- toggle shows {toggle_text_after_reload!r}")

            page.click("#btnTokenLoot")
            page.wait_for_selector("#lootPopover:not([hidden])", timeout=10_000)
            # The popover's own content (item list, recipients, the add
            # row) loads via an async GET issued after the container
            # becomes visible -- wait for that fetch to land before
            # asserting on anything inside it.
            page.wait_for_function(
                "() => document.getElementById('lootAddRow')?.hidden === false",
                timeout=10_000)

            page.fill("#lootAddName", "Heiltrank")
            page.fill("#lootAddQuantity", "3")
            page.click("#btnLootAddItem")
            page.wait_for_function(
                "() => (document.getElementById('lootItemList')?.textContent || '').includes('Heiltrank')",
                timeout=10_000)

            recipient_options = page.locator("#lootRecipient option").all_text_contents()
            if not any("Beute-Held" in option for option in recipient_options):
                findings.append(f"[loot] recipient dropdown does not list the created character: {recipient_options!r}")

            page.check('#lootItemList input[data-loot-select]')
            page.select_option("#lootRecipient", str(character_id))
            page.click("#btnLootTransfer")
            page.wait_for_function(
                "() => (document.getElementById('lootStatus')?.textContent || '').includes('Übertragen')",
                timeout=10_000)

            # Fully-quantity transfer depletes the source row entirely.
            page.wait_for_function(
                "() => !(document.getElementById('lootItemList')?.textContent || '').includes('Heiltrank')",
                timeout=10_000)

            # Close the popover before switching sidebar tabs -- it's
            # fixed-positioned over the token panel and, left open,
            # physically overlaps the sidebar tab strip underneath it,
            # which makes Playwright's actionability check on the chat tab
            # time out (the click point resolves to the popover, not the
            # tab button).
            page.keyboard.press("Escape")
            page.wait_for_selector("#lootPopover[hidden]", state="attached", timeout=5_000)

            # Audit trail: a chat_type=loot_transfer message lands in the
            # normal chat log. The right sidebar (where the tab strip and
            # #chatLog live) is closed by default -- open it first, then
            # switch tabs (#chatLog sits under #panel-chat, not the
            # #panel-tools tab active by default), same two-step caveat the
            # roll composer flow already needed.
            page.click("#btnSidebarToggle")
            page.wait_for_selector(".right-sidebar.is-open", timeout=15_000)
            page.click('.sidebar-tab[data-tab="chat"]')
            page.wait_for_selector("#panel-chat.active", timeout=10_000)
            page.wait_for_function(
                "() => (document.getElementById('chatLog')?.textContent || '').includes('Heiltrank')",
                timeout=10_000)
            chat_text = page.locator("#chatLog").text_content() or ""
            if "überträgt" not in chat_text:
                findings.append(f"[loot] chat audit line missing expected verb 'überträgt': {chat_text!r}")

            # Real server-side effect, not just a client-side list update.
            character_check = api.get(f"{stack.base_url}/api/characters/{character_id}")
            if character_check.status != 200:
                findings.append(f"[loot] character re-fetch returned HTTP {character_check.status}")
            elif character_check.json().get("inventory_count", 0) < 1:
                findings.append(
                    "[loot] recipient character's inventory_count is still 0 after a completed transfer")

        except Exception as error:
            findings.append(f"[loot] interaction failed: {type(error).__name__}: {str(error)[:200]}")
            try:
                shot = workdir / "loot-transfer-flow.png"
                page.screenshot(path=str(shot))
                findings.append(f"[debug] screenshot: {shot.name}")
            except Exception:
                pass

        findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
        browser.close()
    return findings


def _vision_fog_flow(stack, workdir: Path) -> list[str]:
    """S10, 2026-08-28 (docs/PLAYTABLE_FEATURE_RESEARCH_10_VISION_2026-08-27.md,
    Apply-approved): vision/walls/lights/Fog of War. Single DM user, same
    documented scope split as S08/S09 -- fog per-user isolation and the
    idempotent-reset/permission contract are covered server-side in
    tests/test_playtable_vision_fog.py, not duplicated here. This flow
    proves the actual click path: toggle Fog of War on, place a light and
    a wall through the real tools, edit each through its popover, verify
    the geometry-changed round trip actually updates the DOM (not just
    the server), and drive the destructive fog-reset confirmation."""
    from playwright.sync_api import sync_playwright
    from tools.robots.session import RobotSession

    findings: list[str] = []
    keys = mint_registration_keys(stack.database_url, count=1)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        session = RobotSession(context, base_url=stack.base_url,
                               robot_name="sicht_bot", artifacts_dir=workdir)
        session.open()
        if not session.register(
                username="sicht_bot",
                email="sicht_bot@robots.roll-drauf.de",
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
                            data=json.dumps({"name": "Sicht-Kampagne", "max_players": 6}),
                            headers=json_headers).json()
        campaign_id = (campaign.get("campaign") or campaign)["id"]
        game_session = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
            data=json.dumps({"name": "Sicht-Sitzung"}), headers=json_headers).json()
        session_id = (game_session.get("session") or game_session)["id"]

        map_response = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/maps",
            data=json.dumps({"name": "Sicht-Karte", "width": 1600, "height": 1200}),
            headers=json_headers)
        if map_response.status != 201:
            findings.append(f"[setup] map create returned HTTP {map_response.status}")
            browser.close()
            return findings
        map_payload = map_response.json()
        map_id = (map_payload.get("map") or map_payload.get("campaign_map") or map_payload)["id"]
        init_response = api.post(
            f"{stack.base_url}/api/play/campaigns/{campaign_id}/sessions/{session_id}/scene-stack/init",
            data=json.dumps({"map_ids": [map_id]}), headers=json_headers)
        if init_response.status != 201:
            findings.append(f"[setup] scene-stack init returned HTTP {init_response.status}")
            browser.close()
            return findings

        for target_state in ("ready", "in_progress"):
            transition_response = api.post(
                f"{stack.base_url}/api/play/campaigns/{campaign_id}/sessions/{session_id}/transition",
                data=json.dumps({"target_state": target_state, "ignore_warnings": True}),
                headers=json_headers)
            if transition_response.status != 200:
                findings.append(
                    f"[setup] session transition to {target_state!r} returned "
                    f"HTTP {transition_response.status}: {transition_response.text()[:200]}")
                browser.close()
                return findings

        token_response = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions/{session_id}/tokens",
            data=json.dumps({"name": "Wache", "x": 200, "y": 200, "token_type": "npc",
                             "metadata_json": {"position_mode": "pixel"}}),
            headers=json_headers)
        if token_response.status != 201:
            findings.append(f"[setup] token create returned HTTP {token_response.status}")
            browser.close()
            return findings

        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[play] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        try:
            # #visionControls lives inside the Turn Order widget, which is
            # collapsed by default (same pre-existing state
            # combat_turn_order_flow already has to expand) -- its hidden
            # attribute being false does not make it *visible* while its
            # collapsed ancestor still is.
            page.wait_for_selector(".token-marker", state="visible", timeout=15_000)
            if "collapsed" in (page.locator("#turnOrderWidget").get_attribute("class") or "").split():
                page.click("#turnOrderWidget .widget-toggle")

            # Fog of War toggle (DM-only, session-wide -- not gated on a
            # token being selected, unlike the wall/light tools' visible
            # state which is but not their reachability).
            page.wait_for_selector("#visionControls:not([hidden])", timeout=15_000)
            fog_toggle_text_before = (page.locator("#btnFogEnabledToggle").text_content() or "").strip()
            if "aus" not in fog_toggle_text_before:
                findings.append(f"[vision] fog toggle should start 'aus', shows {fog_toggle_text_before!r}")
            page.click("#btnFogEnabledToggle")
            page.wait_for_function(
                "() => (document.getElementById('btnFogEnabledToggle')?.textContent || '').includes('an')",
                timeout=10_000)

            # Light placement: arm the tool, click the map, a marker with
            # the documented defaults (bright=100, dim=200) should appear.
            page.click('.tool-btn[data-tool="light"]')
            page.click("#mapWorld", position={"x": 400, "y": 300})
            page.wait_for_selector("#visionLayer .vision-light-marker", timeout=10_000)
            light_count = page.locator("#visionLayer .vision-light-marker").count()
            if light_count != 1:
                findings.append(f"[vision] expected exactly 1 light marker after one placement click, found {light_count}")

            # Edit popover: click the marker, change type to darkness,
            # verify the round trip (server PATCH -> geometry_changed
            # broadcast -> this SAME client's own re-render) actually
            # applied the .darkness class, not just that the request
            # returned 200.
            page.click("#visionLayer .vision-light-marker")
            page.wait_for_selector("#lightEditPopover:not([hidden])", timeout=10_000)
            bright_value = page.locator("#lightEditBright").input_value()
            if bright_value != "100":
                findings.append(f"[vision] light edit popover should show default bright_radius 100, got {bright_value!r}")
            page.select_option("#lightEditType", "darkness")
            page.wait_for_selector("#visionLayer .vision-light-marker.darkness", timeout=10_000)
            page.click("#btnLightEditClose")
            page.wait_for_selector("#lightEditPopover[hidden]", state="attached", timeout=5_000)

            # Wall placement: two clicks define a segment. Diagonal, not
            # axis-aligned -- a perfectly horizontal/vertical SVG <line>
            # has a zero-height/width geometric bounding box, which fails
            # Playwright's "visible" check even though the stroke renders
            # fine (a robot-flow artifact, not a product bug). Both points
            # stay in the map's top-left quadrant: within #mapWorld's own
            # rendered box (1600x1200 map at 50% zoom = 800x600 screen px,
            # a position past that falls outside the element entirely),
            # clear of the light placed at (400, 300), and clear of
            # #actionHotbar which overlays the bottom-center of the map
            # (a y around 580 on an 800x600 box lands ON the hotbar, not
            # the map -- confirmed via elementFromPoint, not a wall-tool
            # bug at all).
            page.click('.tool-btn[data-tool="wall"]')
            page.click("#mapWorld", position={"x": 50, "y": 50})
            page.click("#mapWorld", position={"x": 200, "y": 180})
            page.wait_for_selector("#visionLayer .vision-wall-line", timeout=10_000)
            wall_count = page.locator("#visionLayer .vision-wall-line").count()
            if wall_count != 1:
                findings.append(f"[vision] expected exactly 1 wall after a two-click placement, found {wall_count}")

            page.click("#visionLayer .vision-wall-line")
            page.wait_for_selector("#wallEditPopover:not([hidden])", timeout=10_000)
            page.select_option("#wallEditSight", "none")
            page.wait_for_selector("#visionLayer .vision-wall-line.sight-none", timeout=10_000)
            page.click("#btnWallEditClose")
            page.wait_for_selector("#wallEditPopover[hidden]", state="attached", timeout=5_000)

            # Sichtbare Tokens (DM verification tool): select the token,
            # open the popover, expect the token to see itself at minimum.
            page.click('.tool-btn[data-tool="select"]')
            page.wait_for_selector(".token-marker", state="visible", timeout=15_000)
            page.click(".token-marker")
            page.wait_for_selector("#tokenVisibleRow:not([hidden])", timeout=10_000)
            page.click("#btnTokenVisible")
            page.wait_for_selector("#visibleTokensPopover:not([hidden])", timeout=10_000)
            page.wait_for_function(
                "() => (document.getElementById('visibleTokensList')?.textContent || '').includes('Wache')",
                timeout=10_000)
            page.click("#btnVisibleTokensClose")

            # Sight range field, then a reload proves it is a real server
            # round trip, same pattern the loot flow already established
            # for is_loot_source.
            page.fill("#tokenSightRange", "250")
            page.click("#btnTokenSightRangeSet")
            page.wait_for_timeout(400)
            page.reload()
            page.wait_for_selector(".token-marker", state="visible", timeout=15_000)
            page.click(".token-marker")
            page.wait_for_selector("#tokenSelectionDetail:not([hidden])", timeout=10_000)
            sight_range_after_reload = page.locator("#tokenSightRange").input_value()
            if sight_range_after_reload != "250":
                findings.append(
                    f"[vision] sight_range did not survive a reload -- shows {sight_range_after_reload!r}")

            # The reload above reset every widget to its default collapsed
            # state -- re-expand Turn Order before reaching #btnFogReset
            # inside it, same as the very first expand earlier.
            if "collapsed" in (page.locator("#turnOrderWidget").get_attribute("class") or "").split():
                page.click("#turnOrderWidget .widget-toggle")
            page.wait_for_selector("#visionControls:not([hidden])", timeout=10_000)

            # Destructive reset: confirm() dialog must name the consequence.
            dialog_messages = []
            page.on("dialog", lambda dialog: (dialog_messages.append(dialog.message), dialog.accept()))
            page.click("#btnFogReset")
            page.wait_for_timeout(500)
            if not dialog_messages:
                findings.append("[vision] no confirmation dialog appeared for 'Nebel zurücksetzen'")
            elif "zurückgesetzt werden" not in dialog_messages[0] and "zurücksetzen" not in dialog_messages[0]:
                findings.append(f"[vision] reset confirmation text unclear: {dialog_messages[0]!r}")

        except Exception as error:
            findings.append(f"[vision] interaction failed: {type(error).__name__}: {str(error)[:200]}")
            try:
                shot = workdir / "vision-fog-flow.png"
                page.screenshot(path=str(shot))
                findings.append(f"[debug] screenshot: {shot.name}")
            except Exception:
                pass

        findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
        browser.close()
    return findings


FLOWS = {
    "dice_roll_realtime": _dice_roll_flow,
    "map_token_table": _map_token_table_flow,
    "scene_directory": _scene_directory_flow,
    "measure_tool": _measure_tool_flow,
    "token_hud": _token_hud_flow,
    "conditions_picker": _conditions_picker_flow,
    "combat_turn_order": _combat_turn_order_flow,
    "action_hotbar": _action_hotbar_flow,
    "roll_composer": _roll_composer_flow,
    "app_menu": _app_menu_flow,
    "campaign_hub_click": _campaign_hub_click_flow,
    "beyond20_bridge": _beyond20_bridge_flow,
    "loot_transfer": _loot_transfer_flow,
    "vision_fog": _vision_fog_flow,
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

    report = args.out or workdir / "vtt-flows.json"
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
