"""C04: static contract checks plus REAL browser journeys.

Static checks (first section) are not browser acceptance. The journeys below drive real
pointer gestures in the editor and the real DM Library -> table -> Firefox Player path,
reusing the existing mapmaker (open_editor) and action_site fixtures.
"""
from contextlib import closing
import json
import math
import os
import re
import time
from pathlib import Path

import pytest

try:  # fixtures are reused as-is; a missing browser stack must not hide the static checks
    from tests.test_mapmaker_browser import (  # noqa: F401
        preview_origin, open_editor, LAND, _is_sea, _BROWSER_CANDIDATES, _DEFAULT_LIBS)
    from tests.test_personal_actions_browser import action_site  # noqa: F401
except BaseException:  # pragma: no cover - depends on the local Playwright install
    LAND, _is_sea = (1000, 1000), (lambda rgb: rgb[2] > rgb[0])
    _BROWSER_CANDIDATES, _DEFAULT_LIBS = (), ""


# One Playwright manager for the whole module. The sync API cannot be started twice in
# one thread, so the (shadowed) chromium `browser` fixture used by `open_editor` and the
# Firefox Player of the table journey are both launched from this single manager.
@pytest.fixture(scope="module")
def playwright_manager():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as manager:
        yield manager


@pytest.fixture(scope="module")
def browser(playwright_manager):
    executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or next(
        (path for path in _BROWSER_CANDIDATES if os.path.exists(path)), None)
    env = dict(os.environ)
    libs = os.environ.get("MAPMAKER_BROWSER_LIBS") or (_DEFAULT_LIBS if os.path.isdir(_DEFAULT_LIBS) else "")
    if libs:
        env["LD_LIBRARY_PATH"] = libs + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    instance = playwright_manager.chromium.launch(headless=True, args=["--no-sandbox"], executable_path=executable, env=env)
    yield instance
    instance.close()

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "vtt/static"
GRASS = "color:kenney-tiny_33382ddbb14436e9"
WALL = "color:kenney-tiny_1a2fdb62b6610bca"


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_player_composition_never_references_the_dm_library_controller():
    for path in ("vtt/templates/play.html", "vtt/static/js/play-player.js"):
        assert "play-map-library" not in read(path)
    # The controller is requested only from the DM-only composition module.
    importers = [p.name for p in (STATIC / "js").glob("*.js") if "play-map-library.js" in p.read_text(encoding="utf-8")]
    assert importers == ["play-dm.js"]
    assert "layerAddLibrary" in read("vtt/play/surfaces/dm.json")
    assert "layerAddLibrary" not in read("vtt/templates/play.html")


def test_controller_sends_no_private_source_or_storage_path():
    controller = read("vtt/static/js/play-map-library.js")
    for forbidden in ("storage_key", "background_url", "document:"):
        assert forbidden not in controller.split("async uploadSnapshot")[1].split("/** Two explicit")[0]
    assert "snapshotFromProject" in controller and "new Editor" not in controller


def test_snapshot_helper_is_shared_and_editor_free():
    helper = read("vtt/static/mapmaker/js/snapshot.js")
    assert all(name in helper for name in ("validateDocument", "materialize", "ensureDocumentImages", "Renderer", "embedCredits"))
    assert "new Editor" not in helper and "./app.js" not in helper and "./ui.js" not in helper
    assert "renderPngBlob" in read("vtt/static/mapmaker/js/app.js")


def test_history_has_preflight_and_strict_refusal():
    history = read("vtt/static/mapmaker/js/history.js")
    assert "canFit" in history and "command.strict" in history
    app = read("vtt/static/mapmaker/js/app.js")
    assert "this.history.canFit(" in app and "strict: true" in app


def test_editor_actions_are_visibly_labelled_and_eraser_has_explicit_scope():
    html = read("vtt/static/mapmaker/index.html")
    for marker in ("libraryBtn", "cloudSave", "importActionBtn", "exportActionBtn", "eraseScope", "stampGridOn", "tileRadius"):
        assert marker in html
    markers = json.loads(read("docs/proofs/claude-c04-2026-11-12/locale-markers.json"))
    for value, text in (("active", "Aktive Ebene"), ("visible", "Alle sichtbaren Ebenen")):
        option = re.search(rf'<option value="{value}"([^>]*)>{re.escape(text)}</option>', html)
        assert option, (value, text)  # the real option value AND visible text...
        assert f'data-ui-key="{markers[text]}"' in option.group(1)  # ...plus its explicit locale marker
    assert 'id="stampGridOn" type="checkbox" checked' not in html  # stamp grid is off by default


def test_no_global_shim_asset_urls_are_module_relative_and_fonts_preloaded():
    helper = read("vtt/static/mapmaker/js/snapshot.js")
    assert "globalThis.fetch =" not in helper and "HTMLImageElement" not in helper
    stamps = read("vtt/static/mapmaker/js/stamps.js")
    assert "import.meta.url" in stamps and 'fetch("assets/' not in stamps and "`assets/" not in stamps
    for face in ("literata-var", "literata-italic-var", "cinzel-regular", "cinzel-bold", "badscript-regular"):
        assert face in helper
        assert (STATIC / "fonts" / (face + ".woff2")).exists()


def test_explicit_locale_markers_and_visual_variant_selection():
    markers = json.loads(read("docs/proofs/claude-c04-2026-11-12/locale-markers.json"))
    html = read("vtt/static/mapmaker/index.html") + read("vtt/play/surfaces/dm.json")
    for source, key in markers.items():
        assert f'data-ui-key=\\"{key}\\">{source}' in html or f'data-ui-key="{key}">{source}' in html, source
    assert 'id="tileVariants"' not in html and "tileVariantAdd" in html  # no raw-ID text input
    tasks = json.loads(read("tools/i18n/tasks/c04.json"))
    for source in markers:
        assert tasks[source]["de"] == source and tasks[source]["en"]


# --------------------------------------------------------------------------- real editor pointer journeys

def _summary(ed):
    return ed.summary()


def _cells(summary):
    tiles = next((layer for layer in summary["layers"] if layer["kind"] == "tiles"), None)
    return [] if tiles is None else tiles["tiles"]


def _vector_items(summary):
    return sorted(item["id"] for item in summary["items"] if "points" in item or "text" in item)


def _stamps(summary):
    """Stamp items in document order (identity = id); labels carry symbols, not a top-level asset."""
    return [item for item in summary["items"] if "asset" in item and "points" not in item and "text" not in item]


def _stamp_ids(summary):
    return [item["id"] for item in _stamps(summary)]


def _segment_distance(point, a, b):
    ax, ay, bx, by = *a, *b
    t = max(0.0, min(1.0, ((point[0] - ax) * (bx - ax) + (point[1] - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
    return math.hypot(point[0] - (ax + t * (bx - ax)), point[1] - (ay + t * (by - ay)))


def _pick_tile(ed, search, tile_id):
    ed.page.locator("#tilePack").select_option("kenney-tiny")
    ed.page.locator("#tileSearch").fill(search)
    ed.page.locator(f'.mm-tile-btn[data-tile="{tile_id}"]').click()


def test_history_preflight_refuses_without_clearing_earlier_undo(open_editor):
    ed = open_editor()
    result = ed.page.evaluate("""async () => {
        // Module path relative to the page actually served (preview fixture: /mapmaker/, Flask: /static/mapmaker/).
        const { History } = await import(new URL('./js/history.js', location.href).href);
        const history = new History({ maxBytes: 1000 });
        const log = [];
        const step = (name, bytes, extra = {}) => ({ label: name, bytes, undo: () => log.push('u' + name), redo: () => {}, ...extra });
        const first = history.push(step('a', 400));
        const fits = history.canFit(5000);
        const refused = history.push(step('big', 5000, { strict: true }));
        const afterRefusal = { canUndo: history.canUndo, bytes: history.bytes, steps: history.undoStack.length };
        history.undo();
        return { first, fits, refused, afterRefusal, log };
    }""")
    assert result["first"] is True and result["fits"] is False and result["refused"] is False
    assert result["afterRefusal"] == {"canUndo": True, "bytes": 400, "steps": 1}  # earlier step still undoable
    assert result["log"] == ["ua"]
    ed.assert_clean()


def test_mixed_layer_eraser_scopes_cancel_single_undo_stamp_grid_and_tile_variants(open_editor):
    ed = open_editor()
    base = _summary(ed)
    vectors = _vector_items(base)
    assert not _is_sea(ed.pixel(*LAND))
    # One stamp and one tile on top of the painted land (tile tool last: the tile layer is active).
    ed.tool("stamp")
    ed.page.get_by_role("radio", name="Burg", exact=True).click()
    ed.click_doc(*LAND)
    ed.tool("tile")
    _pick_tile(ed, "Gras", GRASS)
    ed.click_doc(*LAND)
    placed = _summary(ed)
    assert placed["stamps"] == base["stamps"] + 1 and len(_cells(placed)) == 1
    # Identity bookkeeping: the starter map already has stamps near LAND, so the erased set is
    # derived from the gesture geometry (below), never assumed to be exactly the placed stamp.
    deliberate = [i for i in _stamp_ids(placed) if i not in _stamp_ids(base)]
    assert len(deliberate) == 1
    deliberate = deliberate[0]
    ids_placed = _stamp_ids(placed)
    capsule = ((LAND[0] - 50, LAND[1]), (LAND[0] + 50, LAND[1]))
    radius = 80  # brush size 160
    ed.tool("eraser")
    ed.set_range("#brushSize", 160)
    ed.set_range("#brushOpacity", 100)
    # Default scope is the ACTIVE layer (the tile layer): no silent switch to a raster layer.
    assert ed.page.locator("#eraseScope").input_value() == "active"
    assert ed.summary()["activeLayer"] == placed["activeLayer"]
    steps = placed["historySteps"]
    ed.drag([(LAND[0] - 50, LAND[1]), (LAND[0] + 50, LAND[1])])
    active = _summary(ed)
    assert _cells(active) == [] and _stamp_ids(active) == ids_placed  # active tile layer only: stamps untouched
    assert not _is_sea(ed.pixel(*LAND))  # raster untouched in active scope
    assert active["activeLayer"] == placed["activeLayer"] and active["historySteps"] == steps + 1
    ed.page.keyboard.press("Control+z")
    assert len(_cells(_summary(ed))) == 1 and _summary(ed)["historySteps"] == steps

    # Explicit all-visible scope, interrupted by a real pointercancel: everything is restored.
    ed.page.locator("#eraseScope").select_option("visible")
    ed.pointer([{"type": "pointerdown", "id": 7, "kind": "mouse", "primary": True, "x": LAND[0] - 50, "y": LAND[1]},
                {"type": "pointermove", "id": 7, "kind": "mouse", "primary": True, "x": LAND[0], "y": LAND[1]},
                {"type": "pointermove", "id": 7, "kind": "mouse", "primary": True, "x": LAND[0] + 50, "y": LAND[1]}])
    assert ed.summary()["mutating"] is True
    ed.pointer([{"type": "pointercancel", "id": 7, "kind": "mouse", "primary": True, "x": LAND[0] + 50, "y": LAND[1]}])
    cancelled = _summary(ed)
    assert cancelled["mutating"] is False and cancelled["historySteps"] == steps
    assert _stamp_ids(cancelled) == ids_placed and len(_cells(cancelled)) == 1  # exact identities and order restored
    assert not _is_sea(ed.pixel(*LAND))

    # Real all-visible gesture: raster, tile and stamp content go; paths and labels stay; one undo step.
    ed.drag([(LAND[0] - 50, LAND[1]), (LAND[0] + 50, LAND[1])])
    erased = _summary(ed)
    assert _cells(erased) == []
    assert _is_sea(ed.pixel(*LAND))
    assert _vector_items(erased) == vectors
    assert erased["historySteps"] == steps + 1
    kept_ids = _stamp_ids(erased)
    removed = [i for i in ids_placed if i not in kept_ids]
    assert deliberate in removed  # the stamp placed for this test is gone
    assert kept_ids == [i for i in ids_placed if i not in removed]  # nothing else disappeared or moved
    by_id = {item["id"]: item for item in _stamps(placed)}
    for stamp_id in removed:  # every erased original lies within reach of the gesture ...
        item = by_id[stamp_id]
        assert _segment_distance((item["x"], item["y"]), *capsule) <= radius + item["size"], item
    for stamp_id in kept_ids:  # ... and every survivor's centre is outside the brush radius
        item = by_id[stamp_id]
        assert _segment_distance((item["x"], item["y"]), *capsule) > radius, item
    ed.page.keyboard.press("Control+z")
    restored = _summary(ed)
    assert len(_cells(restored)) == 1 and _stamp_ids(restored) == ids_placed and restored["historySteps"] == steps
    assert not _is_sea(ed.pixel(*LAND))
    ed.page.keyboard.press("Control+Shift+z")
    again = _summary(ed)
    assert _cells(again) == [] and _stamp_ids(again) == kept_ids and _is_sea(ed.pixel(*LAND))
    ed.page.keyboard.press("Control+z")
    assert not _is_sea(ed.pixel(*LAND))

    # Optional stamp grid: off by default, preview and placement share one rounded position.
    ed.tool("stamp")
    assert not ed.page.locator("#stampGridOn").is_checked()
    ed.page.locator("#stampGridOn").check()
    ed.page.locator("#stampGridSize").fill("40")
    ed.click_doc(LAND[0] + 213, LAND[1] + 227)
    snapped = [i for i in _summary(ed)["items"] if i.get("asset") == "kenney:castle" and i["x"] % 40 == 0]
    assert snapped and snapped[-1]["x"] == 1200 and snapped[-1]["y"] == 1240

    # Tile brush: visually chosen known variants, radius in whole cells, one random pick per cell
    # and gesture; the whole gesture (including a back-and-forth drag) is one undo step.
    ed.tool("tile")
    _pick_tile(ed, "Gras", GRASS)
    ed.page.locator("#tileVariantAdd").click()
    _pick_tile(ed, "Steinmauer", WALL)
    ed.page.locator("#tileVariantAdd").click()
    expect_chips = ed.page.locator("#tileVariantList li")
    assert expect_chips.count() == 2
    ed.set_range("#tileRadius", 1)
    before_cells = len(_cells(_summary(ed)))
    steps = _summary(ed)["historySteps"]
    y = 32 * 45 + 10
    ed.drag([(900, y), (1250, y), (900, y)], steps=4)
    painted = _summary(ed)
    new_cells = _cells(painted)
    assert {c["asset"] for c in new_cells} <= {GRASS, WALL} and {GRASS, WALL} <= {c["asset"] for c in new_cells}
    assert len(new_cells) - before_cells >= 30  # radius 1: three rows of cells
    assert painted["historySteps"] == steps + 1
    ed.page.keyboard.press("Control+z")
    assert len(_cells(_summary(ed))) == before_cells and _summary(ed)["historySteps"] == steps
    ed.assert_clean()


def test_dense_scatter_on_a_stamp_grid_never_stacks_positions_one_undo_and_cancel(open_editor):
    """Regression: grid 128 + size 88 + scatter. Many pointer samples snap to one cell."""
    ed = open_editor()
    ed.tool("stamp")
    ed.page.get_by_role("radio", name="Tanne", exact=True).click()
    ed.page.locator("#stampScatter").check()
    ed.page.locator("#stampGridOn").check()
    ed.page.locator("#stampGridSize").fill("128")
    ed.set_range("#stampSize", 88)
    before = _summary(ed)
    ids0 = _stamp_ids(before)
    stroke = [(1100, 290), (1900, 290), (1900, 420), (1100, 420)]

    # Dense real pointer stroke (many samples per cell): positions of this gesture are unique grid points.
    ed.drag(stroke, steps=60)
    after = _summary(ed)
    new = [item for item in _stamps(after) if item["id"] not in ids0]
    positions = [(item["x"], item["y"]) for item in new]
    assert len(new) >= 8, positions  # a dense stroke over two grid rows still places a real scatter
    assert len(set(positions)) == len(positions), positions  # no duplicate snapped x/y
    assert all(x % 128 == 0 and y % 128 == 0 for x, y in positions), positions
    assert after["historySteps"] == before["historySteps"] + 1  # the whole gesture is one undo step
    ed.page.keyboard.press("Control+z")
    undone = _summary(ed)
    assert _stamp_ids(undone) == ids0 and undone["historySteps"] == before["historySteps"]  # exact prior stamps
    ed.page.keyboard.press("Control+Shift+z")
    assert [(i["x"], i["y"]) for i in _stamps(_summary(ed)) if i["id"] not in ids0] == positions
    ed.page.keyboard.press("Control+z")

    # Cancelling a dense gesture removes every live stamp of it.
    events = [{"type": "pointerdown", "id": 9, "kind": "mouse", "primary": True, "x": stroke[0][0], "y": stroke[0][1]}]
    events += [{"type": "pointermove", "id": 9, "kind": "mouse", "primary": True, "x": 1100 + 20 * i, "y": 290} for i in range(1, 40)]
    ed.pointer(events)
    live = _summary(ed)
    assert live["mutating"] is True and len(_stamp_ids(live)) > len(ids0)
    live_new = [(i["x"], i["y"]) for i in _stamps(live) if i["id"] not in ids0]
    assert len(set(live_new)) == len(live_new)
    ed.pointer([{"type": "pointercancel", "id": 9, "kind": "mouse", "primary": True, "x": 1880, "y": 290}])
    cancelled = _summary(ed)
    assert cancelled["mutating"] is False and _stamp_ids(cancelled) == ids0
    assert cancelled["historySteps"] == before["historySteps"]
    ed.assert_clean()


# --------------------------------------------------------------------------- real DM library -> Player table

def _open_layers(page):
    """The pages widget starts collapsed for Players and on short screens: open it like a user."""
    from playwright.sync_api import expect
    widget = page.locator("#layersWidget")
    if "collapsed" in (widget.get_attribute("class") or ""):
        widget.locator(".widget-toggle").click()
    expect(page.locator("#layersWidgetBody")).to_be_visible()


def test_dm_library_to_table_firefox_player_sees_card_source_unchanged_and_retry_uploads_once(
        action_site, tmp_path, playwright_manager, browser):
    from playwright.sync_api import expect
    from tests.test_mapmaker_library import document
    from vtt.extensions import db
    from vtt.models import Asset, Campaign, CampaignMap, GameSession, SceneLayer, User
    from vtt.models.mapmaker_project import MapmakerProject
    from vtt.play.service import init_scene_stack

    app, origin, info = action_site
    app.config.update(LOCAL_STORAGE_PATH=str(tmp_path / "storage"), STORAGE_PROVIDER="local")
    with app.app_context():
        owner = User.query.filter_by(username="action-dm").one()
        owner.storage_quota_gb = 5
        db.session.commit()
        init_scene_stack(db.session.get(Campaign, info["campaign"]), db.session.get(GameSession, info["session"]), owner)
        owner_id = owner.id
    api = app.test_client()
    api.set_cookie("access_token_cookie", info["dm_auth"])
    projects = "/api/assets/mapmaker/projects"
    created = api.post(projects, json={"document": document("Bibliothekswelt")}, headers={"X-Mapmaker-Account": str(owner_id)})
    assert created.status_code == 201, created.get_json()
    project = created.get_json()["project"]
    source_before = api.get(f"{projects}/{project['id']}").get_json()

    posts, player_requests, errors = [], [], []
    # Single Playwright manager (module fixture): real Firefox Player, real Chromium DM.
    with closing(playwright_manager.firefox.launch(headless=True)) as player_browser:
        player_context = player_browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
        dm_context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
        player_context.add_cookies([{"name": "access_token_cookie", "value": info["player_auth"], "url": origin, "httpOnly": True}])
        dm_context.add_cookies([{"name": "access_token_cookie", "value": info["dm_auth"], "url": origin, "httpOnly": True}])
        player, dm = player_context.new_page(), dm_context.new_page()
        for page in (player, dm):
            page.set_default_timeout(60000)
            page.on("pageerror", lambda error: errors.append(str(error)))
        player.on("request", lambda request: player_requests.append(request.url))
        dm.on("request", lambda request: posts.append(request.url) if request.method == "POST" and request.url.endswith("/map-library-snapshots") else None)
        table = f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}"
        player.goto(table + "&seat=player")
        dm.goto(table + "&seat=dm")
        expect(player.locator("#presenceRoster")).to_contain_text("action-dm", timeout=30000)
        expect(dm.locator("#presenceRoster")).to_contain_text("action-player", timeout=30000)

        # The Player seat has no DM composition at all.
        expect(player.locator("#layerAddBtn")).to_have_count(0)
        expect(player.locator("#mapLibraryDialog")).to_have_count(0)
        assert player.evaluate("() => !window.PlayDMSurface") is True

        # Normal DM entry: open the pages widget, Hinzufügen -> Eigene Bibliothek -> search -> preview -> confirm.
        _open_layers(dm)
        expect(dm.locator("#layerAddBtn")).to_be_visible()
        # The add control is bound asynchronously after bootstrap: act like a user and retry the visible
        # controls until the library dialog really opens (never click a hidden control).
        dialog = dm.locator("#mapLibraryDialog")
        for _ in range(40):
            if dialog.count() and dialog.is_visible():
                break
            if not dm.locator("#layerAddLibrary").is_visible():
                dm.locator("#layerAddBtn").click()
            if dm.locator("#layerAddLibrary").is_visible():
                dm.locator("#layerAddLibrary").click()
            dm.wait_for_timeout(250)
        expect(dm.locator("#mapLibraryDialog")).to_be_visible()
        dm.locator("#mapLibrarySearch").fill("Bibliotheks")
        expect(dm.locator("#mapLibraryList")).to_contain_text("Bibliothekswelt")
        dm.locator("#mapLibraryList button").first.click()
        expect(dm.locator("#mapLibraryPreview")).to_be_visible(timeout=60000)
        dm.wait_for_function("() => document.querySelector('#mapLibraryPreview')?.complete && document.querySelector('#mapLibraryPreview')?.naturalWidth === 256")
        assert dm.locator("#mapLibraryPreview").evaluate("img => img.complete && img.naturalWidth") == 256
        expect(dm.locator("#mapLibraryPreviewInfo")).to_contain_text("256 × 256")
        dm.locator("#mapLibraryName").fill("Bibliothekskarte")
        expect(dm.locator("#mapLibraryConfirm")).to_be_disabled()  # explicit consent is required
        dm.locator("#mapLibraryConsent").check()
        expect(dm.locator("#mapLibraryConfirm")).to_be_enabled()

        # Stage 2 fails (activation aborted): the created map stays, no false success.
        dm.route("**/scene-stack/layers/*/activate", lambda route: route.abort())
        dm.locator("#mapLibraryConfirm").click()
        expect(dm.locator("#mapLibraryStatus")).to_contain_text("noch nicht aktiviert")
        expect(dm.locator("#mapLibraryDialog")).to_be_visible()
        assert len(posts) == 1
        expect(dm.locator("#layerList .layer-row.active-row")).not_to_contain_text("Bibliothekskarte")
        # Retry repeats only the table stage; no second snapshot upload.
        dm.unroute("**/scene-stack/layers/*/activate")
        expect(dm.locator("#mapLibraryConfirm")).to_be_enabled()
        dm.locator("#mapLibraryConfirm").click()
        expect(dm.locator("#mapLibraryDialog")).to_be_hidden()
        assert len(posts) == 1
        expect(dm.locator("#layerList .layer-row.active-row")).to_contain_text("Bibliothekskarte")
        # The Firefox Player sees the new active card (widget opened like a user; independent of the DM view).
        _open_layers(player)
        expect(player.locator("#layerList .layer-row.active-row")).to_contain_text("Bibliothekskarte")
        expect(player.locator("#layerList .layer-row.active-row")).to_be_visible()
        with app.app_context():
            maps = CampaignMap.query.filter_by(campaign_id=info["campaign"], name="Bibliothekskarte").all()
            assert len(maps) == 1 and (maps[0].width, maps[0].height) == (256, 256)
            layer = SceneLayer.query.filter_by(campaign_map_id=maps[0].id).one()
            assert layer.is_player_visible  # server truth: Players are allowed to see the activated page
            assert "Revision 1" in maps[0].description
            asset_id = int(maps[0].background_url.split("/")[3])
            assert Asset.query.filter_by(asset_type="map", campaign_id=info["campaign"]).filter(Asset.id == asset_id).count() == 1
        shared = player_context.request.get(f"{origin}/api/assets/{asset_id}/preview")
        assert shared.status == 200 and shared.body()[:8] == b"\x89PNG\r\n\x1a\n"

        forbidden = ("play-dm.js", "play-map-library", "/mapmaker/", "map-library-snapshots", "/surface")
        assert not [url for url in player_requests if any(token in url for token in forbidden)], player_requests
        assert player.evaluate("() => !window.PlayDMSurface") is True
        player_context.close()
        dm_context.close()
    assert not errors, errors

    # The private source is untouched: same revision, same stored document and key.
    assert api.get(f"{projects}/{project['id']}").get_json() == source_before
    with app.app_context():
        row = db.session.get(MapmakerProject, project["id"])
        assert row.revision == project["revision"]
