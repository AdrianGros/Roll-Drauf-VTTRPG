"""Browser regression suite for the Kartenwerkstatt prototype (vtt/static/mapmaker).

Runs the real editor in headless Chromium, served (a) by a stdlib static server
rooted at vtt/static that sends the app's production CSP header (preview mode,
no Flask needed) and (b) by the Flask app itself when it is importable.
Assertions read rendered pixels from the editor's composite canvas and drive
the UI with real pointer/keyboard input.

Environment knobs: PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH (browser binary),
MAPMAKER_BROWSER_LIBS (extra LD_LIBRARY_PATH for the browser), VTT_PROOF_DIR
(screenshots).
"""

import base64
import io
import functools
import json
import os
import re
import struct
import threading
import time
import zipfile
import zlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "vtt" / "static"
PREVIEW_PATH = "/mapmaker/"
FLASK_PATH = "/static/mapmaker/index.html"

SEA_A = (1500, 290)      # open sea north of the mountains
SEA_B = (1800, 1450)     # open sea south-east
LAND = (1000, 1000)      # plain land without terrain paint
ISLAND = (266, 309)      # small north-western island (meadow on land)

_BROWSER_CANDIDATES = (
    "/home/admin/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell",
    "/home/admin/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell",
)
_DEFAULT_LIBS = "/tmp/roll-drauf-mapmaker/browser-libs/usr/lib/x86_64-linux-gnu"

CSP_PROBE = """
window.__csp = [];
document.addEventListener('securitypolicyviolation', (e) => window.__csp.push(e.violatedDirective + ' ' + e.blockedURI));
"""


def _app_csp():
    source = (ROOT / "vtt" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r"Content-Security-Policy'\] = \"([^\"]+)\"", source)
    assert match, "CSP header not found in vtt/__init__.py"
    return match.group(1)


class _PreviewHandler(SimpleHTTPRequestHandler):
    csp = ""

    def end_headers(self):
        self.send_header("Content-Security-Policy", self.csp)
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def preview_origin():
    handler = type("Handler", (_PreviewHandler,), {"csp": _app_csp()})
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(handler, directory=str(STATIC)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture(scope="module")
def browser():
    executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or next(
        (path for path in _BROWSER_CANDIDATES if os.path.exists(path)), None)
    env = dict(os.environ)
    libs = os.environ.get("MAPMAKER_BROWSER_LIBS") or (_DEFAULT_LIBS if os.path.isdir(_DEFAULT_LIBS) else "")
    if libs:
        env["LD_LIBRARY_PATH"] = libs + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    with sync_playwright() as p:
        instance = p.chromium.launch(headless=True, args=["--no-sandbox"], executable_path=executable, env=env)
        yield instance
        instance.close()


class Editor:
    def __init__(self, context, page, errors):
        self.context = context
        self.page = page
        self.errors = errors

    # --- reading state ---
    def summary(self):
        return self.page.evaluate("() => window.rdMapmaker.summary()")

    def region(self, x, y, w=1, h=1):
        return self.page.evaluate("([x, y, w, h]) => window.rdMapmaker.sampleRegion(x, y, w, h)", [x, y, w, h])

    def pixel(self, x, y):
        return self.region(x, y)[:3]

    def client(self, x, y):
        point = self.page.evaluate("([x, y]) => window.rdMapmaker.docToClient(x, y)", [x, y])
        return point["x"], point["y"]

    # --- input ---
    def tool(self, name):
        self.page.locator(f".mm-tool[data-tool={name}]").click()

    def tab(self, name):
        self.page.get_by_role("tab", name=name).click()

    def set_range(self, selector, value):
        self.page.locator(selector).evaluate(
            "(el, v) => { el.value = String(v); el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true})); }",
            value)

    def drag(self, points, steps=6):
        mouse = self.page.mouse
        mouse.move(*self.client(*points[0]))
        mouse.down()
        for point in points[1:]:
            mouse.move(*self.client(*point), steps=steps)
        mouse.up()

    def click_doc(self, x, y):
        self.page.mouse.click(*self.client(x, y))

    def pointer(self, events):
        """Dispatch synthetic pointer events (pen pressure, multi-touch) on the canvas."""
        self.page.evaluate(
            """(events) => {
                const canvas = document.getElementById('mapCanvas');
                for (const e of events) {
                    const p = window.rdMapmaker.docToClient(e.x, e.y);
                    canvas.dispatchEvent(new PointerEvent(e.type, {
                        bubbles: true, cancelable: true, composed: true,
                        pointerId: e.id, pointerType: e.kind, isPrimary: !!e.primary,
                        pressure: e.pressure ?? 0.5, clientX: p.x, clientY: p.y,
                        button: e.type === 'pointermove' ? -1 : 0, buttons: e.type === 'pointerup' ? 0 : 1,
                    }));
                }
            }""",
            events)

    def menu(self, item):
        self.page.locator("#fileMenuBtn").click()
        self.page.locator("#fileMenuList").get_by_role("button", name=item).click()

    def assert_clean(self):
        csp = self.page.evaluate("() => window.__csp || []")
        assert not csp, csp
        assert not self.errors, self.errors

    def proof(self, name):
        directory = os.environ.get("VTT_PROOF_DIR")
        if directory:
            self.page.screenshot(path=os.path.join(directory, f"mapmaker-{name}.png"))


@pytest.fixture
def open_editor(browser, preview_origin):
    contexts = []

    def _open(width=1440, origin=None, path=PREVIEW_PATH, init_script=None, route=None, allow_errors=()):
        context = browser.new_context(viewport={"width": width, "height": 900 if width > 600 else 844},
                                      accept_downloads=True, reduced_motion="reduce")
        contexts.append(context)
        context.add_init_script(CSP_PROBE)
        if init_script:
            context.add_init_script(init_script)
        page = context.new_page()
        page.set_default_timeout(20000)
        if route:
            page.route(*route)
        errors = []
        page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))

        def on_console(message):
            if message.type == "error" and not any(token in message.text for token in allow_errors):
                errors.append(f"console: {message.text}")

        page.on("console", on_console)
        page.goto((origin or preview_origin) + path)
        page.wait_for_selector("#app[data-state=ready]")
        return Editor(context, page, errors)

    yield _open
    for context in contexts:
        context.close()


def _diff_count(a, b, threshold=12):
    return sum(1 for i in range(0, len(a), 4) if abs(a[i] - b[i]) + abs(a[i + 1] - b[i + 1]) + abs(a[i + 2] - b[i + 2]) > threshold)


def _mean_delta(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def _png_size(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    return struct.unpack(">II", data[16:24])


def _is_sea(rgb):
    return rgb[2] > rgb[0]


def _wait_until(ed, expression, timeout=15.0, arg=None):
    """Poll a JS function (CSP forbids Playwright's string-eval waiters)."""
    deadline = time.monotonic() + timeout
    while True:
        value = ed.page.evaluate(expression, arg)
        if value:
            return value
        if time.monotonic() > deadline:
            raise AssertionError(f"timed out waiting for {expression}")
        ed.page.wait_for_timeout(50)


# Holds every canvas.toBlob callback until released (deterministic async encoding).
HOLD_TO_BLOB = """() => {
    const original = HTMLCanvasElement.prototype.toBlob;
    window.__held = [];
    window.__hold = true;
    HTMLCanvasElement.prototype.toBlob = function (callback, ...args) {
        if (!window.__hold) return original.call(this, callback, ...args);
        return original.call(this, (blob) => window.__held.push(() => callback(blob)), ...args);
    };
    window.__release = () => {
        window.__hold = false;
        const held = window.__held.splice(0);
        held.forEach((resume) => resume());
        return held.length;
    };
}"""

READ_DRAFT = """() => new Promise((resolve, reject) => {
    const open = indexedDB.open('rd-mapmaker', 1);
    open.onerror = () => reject(open.error);
    open.onsuccess = () => {
        const get = open.result.transaction('drafts').objectStore('drafts').get('autosave');
        get.onerror = () => reject(get.error);
        get.onsuccess = () => {
            const draft = get.result;
            resolve(draft ? { title: draft.doc.meta.title, items: draft.doc.layers.filter((l) => l.items).flatMap((l) => l.items) } : null);
        };
    };
})"""

BEFOREUNLOAD_BLOCKS = """() => {
    const event = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(event);
    return event.defaultPrevented;
}"""

BLOCK_IDB = "IDBFactory.prototype.open = function () { throw new DOMException('blockiert', 'SecurityError'); };"


def _png_rgba_blank(w, h):
    raw = (b"\x00" + b"\x00" * (w * 4)) * h
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")


# ---------------------------------------------------------------------------


@pytest.mark.parametrize("width", [1440, 390])
def test_starter_map_renders_with_places_and_no_errors(open_editor, width):
    ed = open_editor(width)
    summary = ed.summary()
    assert summary["title"] == "Die Silbermark"
    assert summary["size"] == {"w": 2400, "h": 1600}
    assert len(summary["places"]) >= 6
    assert {"Hohenfurt", "Möwenhafen", "Rabenfels"} <= set(summary["places"])
    assert summary["stamps"] > 30
    assert [layer["name"] for layer in summary["layers"]] == ["Land", "Gelände", "Flüsse & Wege", "Symbole", "Beschriftung"]
    assert _is_sea(ed.pixel(*SEA_A)) and not _is_sea(ed.pixel(*LAND))
    assert any(item.get("asset", "").startswith("kenney:") for item in summary["items"]), "curated stamps are the primary palette"
    expect(ed.page.locator("#saveStatus")).to_have_attribute("data-state", "idle")
    ed.tab("Orte")
    expect(ed.page.locator("#placeList .mm-place")).to_have_count(len(summary["places"]))
    expect(ed.page.locator("#placeList")).to_contain_text("Hohenfurt")
    for tool in ("pan", "brush", "eraser", "stamp", "label", "select"):
        expect(ed.page.locator(f".mm-tool[data-tool={tool}]")).to_be_in_viewport()
    overflow = ed.page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert overflow <= 1, overflow
    ed.proof(f"starter-{width}")
    ed.assert_clean()


def test_brush_stroke_undo_redo_restores_exact_pixels(open_editor):
    ed = open_editor()
    x, y = SEA_A
    box = (x - 160, y - 60, 320, 120)
    before = ed.region(*box)
    ed.tool("brush")
    expect(ed.page.locator("#brushTarget")).to_have_text("Gelände")
    ed.page.locator(".mm-swatch[data-material=forest]").click()
    ed.set_range("#brushSize", 60)
    ed.drag([(x - 120, y), (x, y + 10), (x + 120, y)])
    painted = ed.region(*box)
    assert _diff_count(before, painted) > 2000
    expect(ed.page.locator("#undoBtn")).to_be_enabled()
    ed.page.locator("#undoBtn").click()
    assert ed.region(*box) == before, "undo must restore the exact pixels"
    ed.page.keyboard.press("Control+Shift+Z")
    assert ed.region(*box) == painted, "redo must reapply the stroke"
    ed.page.keyboard.press("Control+z")
    assert ed.region(*box) == before
    ed.page.keyboard.press("Control+y")
    assert ed.region(*box) == painted
    ed.assert_clean()


def test_brush_size_opacity_and_softness_change_the_result(open_editor):
    ed = open_editor()
    ed.tool("brush")
    ed.page.locator(".mm-swatch[data-material=snow]").click()
    ax, ay = SEA_A
    bx, by = SEA_B

    def dab(cx, cy, size, opacity, softness):
        ed.set_range("#brushSize", size)
        ed.set_range("#brushOpacity", opacity)
        ed.set_range("#brushSoftness", softness)
        box = (cx - 70, cy - 70, 140, 140)
        before = ed.region(*box)
        ed.click_doc(cx, cy)
        return before, ed.region(*box)

    small = dab(ax - 120, ay, 20, 100, 0)
    large = dab(ax + 40, ay, 110, 100, 0)
    assert _diff_count(*large) > 4 * _diff_count(*small)

    strong = dab(bx - 100, by, 90, 100, 0)
    faint = dab(bx + 60, by, 90, 25, 0)
    assert _mean_delta(*strong) > 2.5 * _mean_delta(*faint)

    # a feathered tip leaves the outer ring much weaker than a hard tip
    hard_before, hard_after = dab(ax + 200, ay, 100, 100, 0)
    soft_before, soft_after = dab(ax + 380, ay, 100, 100, 100)
    ring = lambda before, after: _mean_delta(before[4 * (70 * 140 + 112): 4 * (70 * 140 + 116)], after[4 * (70 * 140 + 112): 4 * (70 * 140 + 116)])  # noqa: E731
    assert ring(hard_before, hard_after) > 2 * ring(soft_before, soft_after)
    ed.assert_clean()


def test_pen_pressure_scales_the_dab(open_editor):
    ed = open_editor()
    ed.tool("brush")
    ed.page.locator(".mm-swatch[data-material=snow]").click()
    ed.set_range("#brushSize", 100)
    ed.set_range("#brushSoftness", 0)
    expect(ed.page.locator("#pressureRow")).to_be_hidden()
    results = []
    for offset, pressure in ((-90, 0.2), (90, 1.0)):
        cx, cy = SEA_A[0] + offset, SEA_A[1]
        box = (cx - 60, cy - 60, 120, 120)
        before = ed.region(*box)
        ed.pointer([
            {"type": "pointerdown", "id": 7, "kind": "pen", "primary": True, "pressure": pressure, "x": cx, "y": cy},
            {"type": "pointerup", "id": 7, "kind": "pen", "primary": True, "pressure": 0, "x": cx, "y": cy},
        ])
        results.append(_diff_count(before, ed.region(*box)))
    expect(ed.page.locator("#pressureRow")).to_be_visible()
    low, high = results
    assert low > 0 and high > 3 * low, results
    ed.assert_clean()


def test_second_finger_cancels_the_stroke_and_pinch_zooms(open_editor):
    ed = open_editor()
    ed.tool("brush")
    x, y = SEA_A
    box = (x - 200, y - 80, 400, 160)
    before = ed.region(*box)
    zoom_before = ed.summary()["zoom"]
    ed.pointer([
        {"type": "pointerdown", "id": 21, "kind": "touch", "primary": True, "x": x - 150, "y": y},
        {"type": "pointermove", "id": 21, "kind": "touch", "primary": True, "x": x - 60, "y": y},
        {"type": "pointermove", "id": 21, "kind": "touch", "primary": True, "x": x, "y": y},
    ])
    assert _diff_count(before, ed.region(*box)) > 500, "first finger paints live"
    ed.pointer([
        {"type": "pointerdown", "id": 22, "kind": "touch", "primary": False, "x": x + 150, "y": y},
        {"type": "pointermove", "id": 21, "kind": "touch", "primary": True, "x": x - 250, "y": y},
        {"type": "pointermove", "id": 22, "kind": "touch", "primary": False, "x": x + 250, "y": y},
        {"type": "pointerup", "id": 22, "kind": "touch", "primary": False, "x": x + 250, "y": y},
        {"type": "pointerup", "id": 21, "kind": "touch", "primary": True, "x": x - 250, "y": y},
    ])
    assert ed.region(*box) == before, "the partial stroke must be reverted"
    summary = ed.summary()
    assert summary["historySteps"] == 0
    assert summary["zoom"] > zoom_before * 1.3
    ed.assert_clean()


def test_eraser_on_land_layer_reveals_the_sea(open_editor):
    ed = open_editor()
    assert not _is_sea(ed.pixel(*ISLAND))
    ed.tab("Ebenen")
    ed.page.get_by_role("button", name="Gelände ausblenden").click()
    ed.page.locator(".mm-layer[data-layer=land] .mm-layer-name").click()
    ed.tool("eraser")
    expect(ed.page.locator("#brushTarget")).to_have_text("Land")
    ed.set_range("#brushSize", 160)
    ed.set_range("#brushOpacity", 100)
    ed.drag([(ISLAND[0] - 40, ISLAND[1]), (ISLAND[0] + 40, ISLAND[1])])
    assert _is_sea(ed.pixel(*ISLAND))
    ed.page.keyboard.press("Control+z")
    assert not _is_sea(ed.pixel(*ISLAND))
    ed.assert_clean()


def test_stamp_place_move_delete_and_undo(open_editor):
    ed = open_editor()
    count = ed.summary()["stamps"]
    ed.tool("stamp")
    ed.page.get_by_role("radio", name="Burg", exact=True).click()
    box = (SEA_B[0] - 60, SEA_B[1] - 60, 120, 120)
    before = ed.region(*box)
    ed.click_doc(*SEA_B)
    summary = ed.summary()
    assert summary["stamps"] == count + 1
    placed = [i for i in summary["items"] if i.get("asset") == "kenney:castle" and abs(i["x"] - SEA_B[0]) < 3]
    assert len(placed) == 1
    assert _diff_count(before, ed.region(*box)) > 100
    stamp_id = placed[0]["id"]

    ed.tool("select")
    ed.drag([SEA_B, (SEA_B[0] + 200, SEA_B[1] - 40)])
    moved = next(i for i in ed.summary()["items"] if i["id"] == stamp_id)
    assert abs(moved["x"] - (SEA_B[0] + 200)) < 4 and abs(moved["y"] - (SEA_B[1] - 40)) < 4
    expect(ed.page.locator("#inspector")).to_be_visible()
    expect(ed.page.locator("#selStampName")).to_have_text("Burg")

    ed.page.locator("#mapCanvas").focus()
    ed.page.keyboard.press("Delete")
    assert ed.summary()["stamps"] == count
    ed.page.keyboard.press("Control+z")
    restored = next(i for i in ed.summary()["items"] if i["id"] == stamp_id)
    assert restored["x"] == moved["x"]
    ed.page.keyboard.press("Control+z")
    back = next(i for i in ed.summary()["items"] if i["id"] == stamp_id)
    assert abs(back["x"] - SEA_B[0]) < 3
    ed.assert_clean()


def test_scatter_places_several_stamps_as_one_undo_step(open_editor):
    ed = open_editor()
    count = ed.summary()["stamps"]
    ed.tool("stamp")
    ed.page.get_by_role("radio", name="Tanne", exact=True).click()
    ed.page.locator("#stampScatter").check()
    ed.drag([(SEA_A[0] - 200, SEA_A[1]), (SEA_A[0] + 200, SEA_A[1])], steps=20)
    added = ed.summary()["stamps"] - count
    assert added >= 4
    ed.page.locator("#undoBtn").click()
    assert ed.summary()["stamps"] == count
    ed.assert_clean()


def test_layers_hide_reorder_rename_delete_with_undo(open_editor):
    ed = open_editor()
    ed.tab("Ebenen")
    assert not _is_sea(ed.pixel(*LAND))
    ed.page.get_by_role("button", name="Land ausblenden").click()
    assert _is_sea(ed.pixel(*LAND))
    assert ed.summary()["layers"][0]["visible"] is False
    ed.page.get_by_role("button", name="Land einblenden").click()
    assert not _is_sea(ed.pixel(*LAND))

    ed.page.get_by_role("button", name="Symbole nach unten").click()
    names = [layer["name"] for layer in ed.summary()["layers"]]
    assert names.index("Symbole") < names.index("Flüsse & Wege")
    expect(ed.page.locator(".mm-layer .mm-layer-title").nth(1)).to_have_text("Flüsse & Wege")

    ed.page.get_by_role("button", name="Gelände umbenennen").click()
    field = ed.page.get_by_role("textbox", name="Neuer Ebenenname")
    field.fill("Wälder <b>und</b> Wiesen")
    field.press("Enter")
    assert "Wälder <b>und</b> Wiesen" in [layer["name"] for layer in ed.summary()["layers"]]
    expect(ed.page.locator(".mm-layer-title", has_text="Wälder <b>und</b> Wiesen")).to_have_count(1)

    ed.page.get_by_role("button", name="Beschriftung löschen").click()
    assert ed.summary()["places"] == []
    ed.page.keyboard.press("Control+z")
    assert len(ed.summary()["places"]) >= 6
    ed.page.locator("#addRaster").click()
    assert [layer["kind"] for layer in ed.summary()["layers"]].count("raster") == 4
    ed.assert_clean()


def test_place_with_lore_is_rendered_as_literal_text(open_editor):
    ed = open_editor()
    ed.tool("label")
    ed.click_doc(*SEA_B)
    name = ed.page.locator("#selText")
    expect(name).to_be_focused()
    ed.page.keyboard.press("Space")  # typing in a field must not switch to panning
    assert ed.summary()["tool"] == "label"
    name.fill("Eulenruh")
    name.press("Enter")
    payload = '<img src=x onerror="window.__pwned=1">'
    lore = ed.page.locator("#selLore")
    lore.fill(payload)
    lore.blur()
    ed.page.locator("#selKind").select_option("ruin")
    item = next(i for i in ed.summary()["items"] if i.get("text") == "Eulenruh")
    assert item["place"] == {"kind": "ruin", "lore": payload}
    ed.tab("Orte")
    entry = ed.page.locator(".mm-place", has_text="Eulenruh")
    expect(entry).to_contain_text(payload)
    assert ed.page.locator("#placeList img").count() == 0
    assert ed.page.evaluate("() => window.__pwned") is None
    # editing again through the list
    entry.click()
    expect(ed.page.locator("#selText")).to_have_value("Eulenruh")
    ed.page.locator("#selText").fill("Eulenruh am Meer")
    ed.page.locator("#selText").press("Enter")
    assert "Eulenruh am Meer" in ed.summary()["places"]
    ed.page.keyboard.press("Control+z")
    assert "Eulenruh" in ed.summary()["places"]
    ed.assert_clean()


def test_space_and_tool_keys_are_ignored_while_typing_in_the_title(open_editor):
    ed = open_editor()
    title = ed.page.locator("#mapTitle")
    title.click()
    title.press("End")
    ed.page.keyboard.type(" bei Nacht")
    assert ed.summary()["tool"] == "brush"
    assert ed.summary()["title"] == "Die Silbermark bei Nacht"
    ed.assert_clean()


def test_space_drag_pans_from_focused_toolbar_button(open_editor):
    ed = open_editor()
    ed.tool("brush")
    box = (SEA_A[0] - 150, SEA_A[1] - 50, 300, 100)
    before = ed.region(*box)
    first = ed.client(*SEA_A)
    ed.page.locator("#zoomFit").focus()
    ed.page.keyboard.down("Space")
    ed.drag([(SEA_A[0] - 90, SEA_A[1]), (SEA_A[0] + 90, SEA_A[1])])
    ed.page.keyboard.up("Space")
    assert ed.region(*box) == before
    assert ed.client(*SEA_A) != first
    zoom = ed.summary()["zoom"]
    ed.page.locator("#zoomIn").focus()
    ed.page.keyboard.press("Space")
    assert ed.summary()["zoom"] > zoom
    ed.assert_clean()


def test_wheel_zoom_and_fit(open_editor):
    ed = open_editor()
    fit = ed.summary()["fitZoom"]
    zoom_label = ed.page.locator("#zoomLevel")
    initial = zoom_label.text_content()
    ed.page.mouse.move(*ed.client(*LAND))
    ed.page.mouse.wheel(0, -400)
    expect(zoom_label).not_to_have_text(initial)
    assert ed.summary()["zoom"] > fit * 1.3
    ed.page.locator("#zoomFit").click()
    expect(zoom_label).to_have_text(initial)
    assert abs(ed.summary()["zoom"] - fit) < 1e-6
    ed.page.locator("#zoomIn").click()
    assert ed.summary()["zoom"] > fit
    ed.assert_clean()


def test_json_round_trip_and_rejected_imports_keep_the_current_map(open_editor, tmp_path):
    ed = open_editor()
    with ed.page.expect_download() as info:
        ed.menu("Als Datei speichern")
    saved = tmp_path / "karte.rdmap.json"
    info.value.save_as(saved)
    assert info.value.suggested_filename == "die-silbermark.rdmap.json"
    data = json.loads(saved.read_text(encoding="utf-8"))
    assert data["format"] == "rd-mapmaker" and data["version"] == 1
    assert data["size"] == {"w": 2400, "h": 1600}
    rasters = [layer for layer in data["layers"] if layer["kind"] == "raster"]
    assert len(rasters) == 3 and all(layer["png"].startswith("data:image/png;base64,") for layer in rasters)
    original_places = ed.summary()["places"]
    reference = ed.region(LAND[0] - 40, LAND[1] - 40, 80, 80)

    # change the map, then load the saved file back
    ed.tool("label")
    ed.click_doc(*SEA_B)
    ed.page.locator("#selText").fill("Vergänglich")
    ed.page.locator("#selText").press("Enter")
    ed.page.locator("#mapTitle").fill("Anderer Titel")
    assert "Vergänglich" in ed.summary()["places"]
    ed.page.locator("#fileInput").set_input_files(str(saved))
    expect(ed.page.locator("#replaceDialog")).to_be_visible()
    ed.page.locator("#replaceDiscard").click()
    expect(ed.page.locator("#toast")).to_contain_text("geladen")
    summary = ed.summary()
    assert summary["places"] == original_places and summary["title"] == "Die Silbermark"
    assert ed.region(LAND[0] - 40, LAND[1] - 40, 80, 80) == reference

    def variant(mutate):
        doc = json.loads(saved.read_text(encoding="utf-8"))
        mutate(doc)
        return json.dumps(doc).encode()

    def first_raster(doc):
        return next(layer for layer in doc["layers"] if layer["kind"] == "raster")

    def stamps_layer(doc):
        return next(layer for layer in doc["layers"] if layer["kind"] == "stamps")

    def too_many(doc):
        layer = stamps_layer(doc)
        template = layer["items"][0]
        layer["items"] = [dict(template, id=f"x{i}") for i in range(2001)]

    def duplicate_id(doc):
        layer = stamps_layer(doc)
        layer["items"][1]["id"] = layer["items"][0]["id"]

    def infinite(doc):
        stamps_layer(doc)["items"][0]["x"] = 1e309  # serialised as Infinity by json.dumps

    bad_files = {
        "kein JSON": b"{not json",
        "falsches Format": json.dumps({"format": "other", "version": 1}).encode(),
        "externes Bild": variant(lambda d: first_raster(d).update(png="https://example.invalid/land.png")),
        "falsche Größe": variant(lambda d: d["size"].update(w=2000)),
        "unbekanntes Symbol": variant(lambda d: stamps_layer(d)["items"][0].update(asset="kenney:dragon")),
        "unbekanntes Ortssymbol": variant(lambda d: next(l for l in d["layers"] if l["kind"] == "labels")["items"][0].update(symbol={"asset": "kenney:dragon", "size": 56})),
        "zu viele Elemente": variant(too_many),
        "doppelte Kennung": variant(duplicate_id),
        "unendliche Zahl": variant(infinite),
        "zu große Schrift": variant(lambda d: next(l for l in d["layers"] if l["kind"] == "labels")["items"][0].update(size=5000)),
        "Farbe": variant(lambda d: next(l for l in d["layers"] if l["kind"] == "labels")["items"][0].update(color="red;}")),
        "zu viele Malebenen": variant(lambda d: d["layers"].extend([dict(first_raster(d), id=f"extra{i}") for i in range(6)])),
    }
    ed.page.locator("#mapTitle").fill("Behalten")
    for label, payload in bad_files.items():
        ed.page.locator("#fileInput").set_input_files({"name": "kaputt.rdmap.json", "mimeType": "application/json", "buffer": payload})
        dialog = ed.page.locator("#errorDialog")
        expect(dialog).to_be_visible()
        assert ed.page.locator("#errorText").text_content().strip(), label
        ed.page.locator("#errorClose").click()
        expect(dialog).to_be_hidden()
        summary = ed.summary()
        assert summary["title"] == "Behalten", label
        assert summary["places"] == original_places, label
    assert ed.region(LAND[0] - 40, LAND[1] - 40, 80, 80) == reference
    ed.assert_clean()


def test_png_export_at_1x_and_2x(open_editor, tmp_path):
    ed = open_editor()
    expect(ed.page.locator("#exportDialog")).to_be_hidden()
    sizes = {}
    for scale in ("1", "2"):
        ed.menu("Als PNG exportieren …")
        dialog = ed.page.locator("#exportDialog")
        expect(dialog).to_be_visible()
        expect(dialog).to_contain_text("Karte hinzufügen")
        dialog.locator(f"input[name=exportScale][value='{scale}']").check()
        with ed.page.expect_download(timeout=60000) as info:
            dialog.get_by_role("button", name="Exportieren").click()
        target = tmp_path / f"export-{scale}.png"
        info.value.save_as(target)
        sizes[scale] = _png_size(target.read_bytes())
        expect(dialog).to_be_hidden()
    assert sizes == {"1": (2400, 1600), "2": (4800, 3200)}
    ed.assert_clean()


def test_autosave_restores_the_draft_after_reload(open_editor):
    ed = open_editor()
    ed.page.locator("#mapTitle").fill("Mein Entwurf")
    ed.tool("brush")
    ed.drag([(SEA_A[0] - 100, SEA_A[1]), (SEA_A[0] + 100, SEA_A[1])])
    painted = ed.region(SEA_A[0] - 120, SEA_A[1] - 40, 240, 80)
    status = ed.page.locator("#saveStatus")
    expect(status).to_have_attribute("data-state", "saved", timeout=15000)
    expect(status).to_contain_text("Lokal gespeichert")

    ed.page.reload()
    dialog = ed.page.locator("#restoreDialog")
    expect(dialog).to_be_visible()
    expect(dialog).to_contain_text("Mein Entwurf")
    expect(dialog.get_by_role("button", name="Entwurf wiederherstellen")).to_be_focused()
    dialog.get_by_role("button", name="Entwurf wiederherstellen").click()
    ed.page.wait_for_selector("#app[data-state=ready]")
    assert ed.summary()["title"] == "Mein Entwurf"
    assert ed.region(SEA_A[0] - 120, SEA_A[1] - 40, 240, 80) == painted
    assert ed.summary()["canUndo"] is False

    ed.page.reload()
    ed.page.locator("#restoreDialog").get_by_role("button", name="Neue Startkarte").click()
    ed.page.wait_for_selector("#app[data-state=ready]")
    assert ed.summary()["title"] == "Die Silbermark"
    ed.assert_clean()


def test_dirty_replacement_can_cancel_or_save_before_open(open_editor, tmp_path):
    ed = open_editor()
    with ed.page.expect_download() as info:
        ed.menu("Als Datei speichern")
    original = tmp_path / "original.rdmap.json"
    info.value.save_as(original)

    ed.page.locator("#mapTitle").fill("Turtonia in Arbeit")
    ed.page.locator("#fileInput").set_input_files(str(original))
    dialog = ed.page.locator("#replaceDialog")
    expect(dialog).to_be_visible()
    expect(dialog.locator("#replaceCancel")).to_be_focused()
    dialog.locator("#replaceCancel").click()
    expect(dialog).to_be_hidden()
    assert ed.summary()["title"] == "Turtonia in Arbeit"

    ed.menu("Neue Karte …")
    ed.page.locator("#newEmpty").click()
    expect(dialog).to_be_visible()
    dialog.locator("#replaceCancel").click()
    assert ed.summary()["title"] == "Turtonia in Arbeit"

    ed.page.locator("#fileInput").set_input_files(str(original))
    expect(dialog).to_be_visible()
    with ed.page.expect_download() as saved_info:
        dialog.locator("#replaceSave").click()
    saved = tmp_path / "work.rdmap.json"
    saved_info.value.save_as(saved)
    expect(dialog).to_be_hidden()
    expect(ed.page.locator("#toast")).to_contain_text("geladen")
    assert json.loads(saved.read_text(encoding="utf-8"))["meta"]["title"] == "Turtonia in Arbeit"
    assert ed.summary()["title"] == "Die Silbermark"
    ed.assert_clean()


def test_material_targets_and_exact_size_fields(open_editor):
    ed = open_editor()
    ed.tool("brush")
    ed.page.locator("#brushSizeNumber").fill("183")
    ed.page.locator("#brushSizeNumber").press("Tab")
    expect(ed.page.locator("#brushSize")).to_have_value("183")
    ed.page.locator(".mm-swatch[data-material=land]").click()
    assert ed.summary()["activeLayer"] == "land"
    ed.page.locator(".mm-swatch[data-material=forest]").click()
    assert ed.summary()["activeLayer"] == "terrain"
    ed.page.locator(".mm-swatch[data-material=river]").click()
    assert ed.summary()["activeLayer"] == "rivers"
    ed.tool("stamp")
    ed.page.locator("#stampSizeNumber").fill("73")
    ed.page.locator("#stampSizeNumber").press("Tab")
    expect(ed.page.locator("#stampSize")).to_have_value("73")
    ed.assert_clean()


def test_label_tool_creates_over_existing_label_and_warns_about_overlap(open_editor):
    ed = open_editor()
    ed.tool("label")
    ed.click_doc(*SEA_A)
    ed.page.locator("#selText").fill("DIE ASCHENMARK")
    ed.page.locator("#selText").press("Enter")
    original = next(i for i in ed.summary()["items"] if i.get("text") == "DIE ASCHENMARK")
    before = ed.summary()["labels"]
    ed.click_doc(*SEA_A)
    assert ed.summary()["labels"] == before + 1
    assert next(i for i in ed.summary()["items"] if i["id"] == original["id"])["text"] == "DIE ASCHENMARK"
    expect(ed.page.locator("#collisionHint")).to_be_visible()
    ed.page.locator("#selText").fill("Dorum")
    ed.page.locator("#selText").press("Enter")
    assert "Dorum" in ed.summary()["places"]
    ed.assert_clean()


def test_vector_path_nodes_undo_and_project_roundtrip(open_editor, tmp_path):
    ed = open_editor()
    ed.tool("path")
    ed.page.locator("#pathMaterial").select_option("river")
    ed.page.locator("#pathWidthNumber").fill("19")
    ed.page.locator("#pathWidthNumber").press("Tab")
    ed.drag([(1510, 260), (1590, 360), (1710, 310)])
    paths = [i for i in ed.summary()["items"] if "points" in i]
    assert len(paths) == 1
    item = paths[0]
    assert item["material"] == "river" and item["width"] == 19 and len(item["points"]) >= 2
    assert [l["kind"] for l in ed.summary()["layers"]].count("paths") == 1
    ed.tool("select")
    point = item["points"][1]
    start = (item["x"] + point["x"], item["y"] + point["y"])
    ed.page.keyboard.down("Shift")
    ed.drag([start, (start[0] + 35, start[1] + 25)])
    ed.page.keyboard.up("Shift")
    moved = next(i for i in ed.summary()["items"] if i["id"] == item["id"])
    assert moved["points"][1] != point
    ed.page.keyboard.press("Control+z")
    assert next(i for i in ed.summary()["items"] if i["id"] == item["id"])["points"][1] == point
    ed.page.keyboard.press("Control+Shift+z")
    assert next(i for i in ed.summary()["items"] if i["id"] == item["id"])["points"][1] == moved["points"][1]
    current = next(i for i in ed.summary()["items"] if i["id"] == item["id"])
    center = (current["x"] + current["points"][1]["x"], current["y"] + current["points"][1]["y"])
    ed.drag([center, (center[0] + 40, center[1] + 20)])
    shifted = next(i for i in ed.summary()["items"] if i["id"] == item["id"])
    assert (shifted["x"], shifted["y"]) == (current["x"] + 40, current["y"] + 20)
    ed.proof("vector-path")
    ed.page.locator("#selPathMaterial").select_option("road")
    with ed.page.expect_download() as info:
        ed.menu("Als Datei speichern")
    saved = tmp_path / "path.rdmap.json"
    info.value.save_as(saved)
    data = json.loads(saved.read_text())
    path_layer = next(l for l in data["layers"] if l["kind"] == "paths")
    assert path_layer["items"][0]["material"] == "road"
    ed.page.locator("#fileInput").set_input_files(str(saved))
    assert next(i for i in ed.summary()["items"] if "points" in i)["points"] == path_layer["items"][0]["points"]
    bad = json.loads(saved.read_text())
    next(l for l in bad["layers"] if l["kind"] == "paths")["items"][0]["points"] = [{"x": 0, "y": 0}]
    ed.page.locator("#fileInput").set_input_files({"name": "bad.rdmap.json", "mimeType": "application/json", "buffer": json.dumps(bad).encode()})
    expect(ed.page.locator("#errorDialog")).to_be_visible()
    ed.page.locator("#errorClose").click()
    assert len([i for i in ed.summary()["items"] if "points" in i]) == 1
    ed.assert_clean()


def test_terrain_style_and_combined_export(open_editor, tmp_path):
    ed = open_editor()
    expect(ed.page.locator("#stampVary")).not_to_be_checked()
    ed.tool("brush")
    ed.page.locator("#brushSizeNumber").fill("800")
    ed.page.locator("#brushSizeNumber").press("Tab")
    expect(ed.page.locator("#brushSize")).to_have_value("800")
    for material in ("ash", "basalt", "lava"):
        ed.page.locator(f".mm-swatch[data-material={material}]").click()
    ed.page.locator("#mapTitle").fill("Turtonia")
    before = ed.region(1180, 120, 40, 40)
    ed.tab("Ebenen")
    ed.page.locator("#showTitle").check()
    assert ed.region(1180, 120, 40, 40) != before
    ed.page.locator("#showTitle").uncheck()
    assert ed.region(1180, 120, 40, 40) == before
    ed.page.locator("#showTitle").check()
    ed.page.locator("#seaTop").fill("#172631")
    ed.page.locator("#seaTop").dispatch_event("change")
    ed.page.locator("#seaBottom").fill("#35424b")
    ed.page.locator("#seaBottom").dispatch_event("change")
    assert ed.region(1180, 120, 40, 40) != before
    ed.proof("map-style")
    ed.menu("Als PNG exportieren …")
    with ed.page.expect_download(timeout=60000) as info:
        ed.page.locator("#exportBundle").click()
    target = tmp_path / "turtonia.zip"
    info.value.save_as(target)
    with zipfile.ZipFile(io.BytesIO(target.read_bytes())) as archive:
        names = archive.namelist()
        assert len(names) == 2 and any(n.endswith(".png") for n in names) and any(n.endswith(".rdmap.json") for n in names)
        assert _png_size(archive.read(next(n for n in names if n.endswith(".png")))) == (2400, 1600)
        project = json.loads(archive.read(next(n for n in names if n.endswith(".rdmap.json"))))
    assert project["meta"]["showTitle"] is True
    assert project["sea"] == {"top": "#172631", "bottom": "#35424b"}
    ed.assert_clean()


def test_place_symbol_and_overlap_selection_survive_roundtrip(open_editor, tmp_path):
    ed = open_editor()
    ed.tool("label")
    ed.page.locator("#placeSymbol").select_option("kenney:castle")
    ed.click_doc(*SEA_A)
    ed.page.locator("#selText").fill("Turtonia")
    ed.page.locator("#selText").press("Enter")
    place = next(i for i in ed.summary()["items"] if i.get("text") == "Turtonia")
    assert place["symbol"] == {"asset": "kenney:castle", "size": 56}

    ed.tool("stamp")
    ed.page.get_by_role("radio", name="Burg", exact=True).click()
    ed.click_doc(*SEA_A)
    stamp = next(i for i in ed.summary()["items"] if i.get("asset") == "kenney:castle" and abs(i["x"] - SEA_A[0]) < 1)
    ed.tool("select")
    ed.click_doc(*SEA_A)
    assert ed.summary()["selection"] == place["id"]
    ed.page.keyboard.down("Alt")
    ed.page.mouse.click(*ed.client(*SEA_A))
    assert ed.summary()["selection"] == stamp["id"]
    ed.page.mouse.click(*ed.client(*SEA_A))
    ed.page.keyboard.up("Alt")
    assert ed.summary()["selection"] == place["id"]
    ed.drag([SEA_A, (SEA_A[0] + 140, SEA_A[1] + 80)])
    moved = next(i for i in ed.summary()["items"] if i["id"] == place["id"])
    assert (moved["x"], moved["y"]) == (SEA_A[0] + 140, SEA_A[1] + 80)
    assert moved["symbol"] == place["symbol"]

    with ed.page.expect_download() as info:
        ed.menu("Als Datei speichern")
    saved = tmp_path / "turtonia.rdmap.json"
    info.value.save_as(saved)
    ed.page.locator("#fileInput").set_input_files(str(saved))
    expect(ed.page.locator("#toast")).to_contain_text("geladen")
    restored = next(i for i in ed.summary()["items"] if i.get("text") == "Turtonia")
    assert restored["symbol"] == {"asset": "kenney:castle", "size": 56}
    assert (restored["x"], restored["y"]) == (SEA_A[0] + 140, SEA_A[1] + 80)
    ed.assert_clean()


def test_mobile_place_selection_stays_above_sheet(open_editor):
    ed = open_editor(390)
    ed.tab("Orte")
    ed.page.locator(".mm-place").first.click()
    summary = ed.summary()
    selected = next(i for i in summary["items"] if i["id"] == summary["selection"])
    point = ed.client(selected["x"], selected["y"])
    panel = ed.page.locator("#panel").bounding_box()
    assert point[1] < panel["y"], (point, panel)
    ed.page.locator("#showMapBtn").click()
    expect(ed.page.locator("#app")).to_have_attribute("data-sheet", "closed")
    ed.assert_clean()


def test_autosave_unavailable_and_failed_states_are_visible(open_editor):
    blocked = open_editor(init_script="IDBFactory.prototype.open = function () { throw new DOMException('blockiert', 'SecurityError'); };")
    status = blocked.page.locator("#saveStatus")
    expect(status).to_have_attribute("data-state", "unavailable")
    blocked.tool("brush")
    blocked.drag([(SEA_A[0] - 80, SEA_A[1]), (SEA_A[0] + 80, SEA_A[1])])
    expect(status).to_have_attribute("data-state", "unavailable")
    expect(status).to_contain_text("Autosave nicht verfügbar")
    blocked.assert_clean()

    full = open_editor(init_script="IDBObjectStore.prototype.put = function () { throw new DOMException('voll', 'QuotaExceededError'); };")
    status = full.page.locator("#saveStatus")
    full.tool("brush")
    full.drag([(SEA_A[0] - 80, SEA_A[1]), (SEA_A[0] + 80, SEA_A[1])])
    expect(status).to_have_attribute("data-state", "failed", timeout=15000)
    expect(status).to_contain_text("Autosave fehlgeschlagen")
    full.assert_clean()


def test_missing_asset_pack_falls_back_to_simple_stamps(open_editor):
    ed = open_editor(route=("**/kenney-cartography/manifest.json", lambda route: route.fulfill(status=404, body="missing")),
                     allow_errors=("404", "Failed to load resource"))
    summary = ed.summary()
    assert summary["stamps"] > 20
    assert all(item["asset"].startswith("builtin:") for item in summary["items"] if "asset" in item)
    ed.tool("stamp")
    expect(ed.page.locator("#packNote")).to_be_visible()
    expect(ed.page.locator(".mm-palette-group h3")).to_have_text(["Einfache Symbole"])
    ed.assert_clean()


def test_narrow_viewport_sheet_and_tools(open_editor):
    ed = open_editor(390)
    pane = ed.page.locator("#pane-tool")
    expect(pane).to_be_hidden()
    ed.tab("Werkzeug")
    expect(pane).to_be_visible()
    expect(ed.page.locator("#brushSize")).to_be_in_viewport()
    ed.tab("Werkzeug")
    expect(pane).to_be_hidden()
    ed.tab("Ebenen")
    expect(ed.page.locator("#layerList .mm-layer")).to_have_count(5)
    ed.proof("narrow-layers")
    ed.tab("Ebenen")
    ed.tool("brush")
    box = (SEA_A[0] - 150, SEA_A[1] - 60, 300, 120)
    before = ed.region(*box)
    ed.drag([(SEA_A[0] - 120, SEA_A[1]), (SEA_A[0] + 120, SEA_A[1])])
    assert _diff_count(before, ed.region(*box)) > 300
    overflow = ed.page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert overflow <= 1, overflow
    ed.assert_clean()


# --- Codex review repairs R1–R5 -----------------------------------------------


def test_r1_serialize_snapshots_synchronously_and_cache_tracks_revisions(open_editor):
    ed = open_editor()
    result = ed.page.evaluate("""async () => {
        const d = await import('./js/document.js');
        const layer = d.createLayer('raster', 'R', { w: 256, h: 256 });
        const ctx = layer.canvas.getContext('2d');
        ctx.fillStyle = '#ff0000'; ctx.fillRect(0, 0, 256, 256);
        const doc = {
            meta: { title: 'A', seed: 0, created: '', modified: '' }, size: { w: 256, h: 256 },
            sea: { top: '#2f5d6e', bottom: '#7fa9a8' },
            layers: [layer, { id: 'sym', name: 'S', kind: 'stamps', visible: true, opacity: 1, effects: { coast: false },
                              items: [{ id: 'i1', asset: 'builtin:pin', x: 10, y: 10, size: 40, rot: 0, flip: false }] }],
        };
        const pending = d.serialize(doc, 'binary');
        // everything below happens after the call returned, while encoding is in flight
        ctx.fillStyle = '#0000ff'; ctx.fillRect(0, 0, 256, 256); layer.rev += 1;
        doc.meta.title = 'B';
        doc.layers[1].items[0].x = 99;
        doc.layers[1].items.push({ id: 'i2', asset: 'builtin:pin', x: 20, y: 20, size: 40, rot: 0, flip: false });
        const first = await pending;
        const second = await d.serialize(doc, 'binary');
        const pixel = async (bytes) => {
            const bitmap = await createImageBitmap(new Blob([bytes], { type: 'image/png' }));
            const canvas = d.createCanvas(256, 256);
            canvas.getContext('2d').drawImage(bitmap, 0, 0);
            return Array.from(canvas.getContext('2d').getImageData(5, 5, 1, 1).data);
        };
        const view = (out) => ({ title: out.meta.title, items: out.layers[1].items.map((i) => [i.id, i.x]) });
        return { first: { ...view(first), pixel: await pixel(first.layers[0].pngBytes) },
                 second: { ...view(second), pixel: await pixel(second.layers[0].pngBytes) },
                 legacy: Array.from(await pixel(await d.layerPngBytes(layer))) };
    }""")
    assert result["first"] == {"title": "A", "items": [["i1", 10]], "pixel": [255, 0, 0, 255]}
    assert result["second"] == {"title": "B", "items": [["i1", 99], ["i2", 20]], "pixel": [0, 0, 255, 255]}
    assert result["legacy"] == [0, 0, 255, 255]
    ed.assert_clean()


def test_r1_r4_async_file_save_keeps_newer_edits_unsaved(open_editor, tmp_path):
    ed = open_editor(init_script=BLOCK_IDB)
    expect(ed.page.locator("#saveStatus")).to_have_attribute("data-state", "unavailable")
    ed.tool("brush")
    a_box = (SEA_A[0] - 140, SEA_A[1] - 50, 280, 100)
    b_box = (SEA_B[0] - 140, SEA_B[1] - 50, 280, 100)
    ed.drag([(SEA_A[0] - 110, SEA_A[1]), (SEA_A[0] + 110, SEA_A[1])])
    after_a = ed.region(*a_box)
    before_b = ed.region(*b_box)
    assert ed.summary()["unsavedFile"] is True
    assert ed.page.evaluate(BEFOREUNLOAD_BLOCKS) is True

    ed.page.evaluate(HOLD_TO_BLOB)
    ed.menu("Als Datei speichern")
    _wait_until(ed, "() => window.__held.length > 0")
    # edits while the file snapshot is still encoding
    ed.drag([(SEA_B[0] - 110, SEA_B[1]), (SEA_B[0] + 110, SEA_B[1])])
    after_b = ed.region(*b_box)
    ed.page.locator("#mapTitle").fill("Während des Speicherns")
    with ed.page.expect_download() as first_info:
        ed.page.evaluate("() => window.__release()")
    first = tmp_path / "first.rdmap.json"
    first_info.value.save_as(first)
    summary = ed.summary()
    assert summary["unsavedFile"] is True, "edits made during the save must stay unsaved"
    assert ed.page.evaluate(BEFOREUNLOAD_BLOCKS) is True

    with ed.page.expect_download() as second_info:
        ed.menu("Als Datei speichern")
    second = tmp_path / "second.rdmap.json"
    second_info.value.save_as(second)
    assert ed.summary()["unsavedFile"] is False
    assert ed.page.evaluate(BEFOREUNLOAD_BLOCKS) is False

    assert json.loads(first.read_text(encoding="utf-8"))["meta"]["title"] == "Die Silbermark"
    ed.page.locator("#fileInput").set_input_files(str(first))
    expect(ed.page.locator("#toast")).to_contain_text("geladen")
    assert ed.region(*a_box) == after_a
    assert ed.region(*b_box) == before_b, "the first file is the snapshot from before stroke B"
    ed.page.locator("#fileInput").set_input_files(str(second))
    expect(ed.page.locator("#toast")).to_contain_text("Während des Speicherns")
    assert ed.region(*b_box) == after_b, "a later save must not reuse stale cached raster bytes"
    ed.assert_clean()


def test_r4_autosave_does_not_claim_saved_when_edits_arrive_during_encoding(open_editor):
    ed = open_editor()
    ed.page.evaluate(HOLD_TO_BLOB)
    ed.page.locator("#mapTitle").fill("Erster Stand")
    _wait_until(ed, "() => window.__held.length > 0")
    ed.tool("brush")
    box = (SEA_A[0] - 140, SEA_A[1] - 50, 280, 100)
    ed.drag([(SEA_A[0] - 110, SEA_A[1]), (SEA_A[0] + 110, SEA_A[1])])
    painted = ed.region(*box)
    ed.page.evaluate("""() => {
        window.__states = [];
        new MutationObserver(() => window.__states.push(document.getElementById('saveStatus').dataset.state))
            .observe(document.getElementById('saveStatus'), { attributes: true, attributeFilter: ['data-state'] });
    }""")
    ed.page.evaluate("() => window.__release()")
    expect(ed.page.locator("#saveStatus")).to_have_attribute("data-state", "saved", timeout=15000)
    states = ed.page.evaluate("() => window.__states")
    first_saved = states.index("saved")
    assert "saving" in states[:first_saved], f"saved claimed for an outdated snapshot: {states}"
    ed.page.reload()
    ed.page.locator("#restoreDialog").get_by_role("button", name="Entwurf wiederherstellen").click()
    ed.page.wait_for_selector("#app[data-state=ready]")
    assert ed.summary()["title"] == "Erster Stand"
    assert ed.region(*box) == painted
    ed.assert_clean()


def _ship(ed):
    return next(i for i in ed.summary()["items"] if i.get("asset") == "kenney:ship" and i["x"] < 1000)


def test_r2_cancelled_drag_is_never_autosaved(open_editor):
    ed = open_editor()
    ship = _ship(ed)
    ed.tool("select")
    ed.page.locator("#mapTitle").fill("Zugbrücke")  # starts the autosave timer
    ed.pointer([
        {"type": "pointerdown", "id": 41, "kind": "mouse", "primary": True, "x": ship["x"], "y": ship["y"]},
        {"type": "pointermove", "id": 41, "kind": "mouse", "primary": True, "x": ship["x"] + 60, "y": ship["y"]},
        {"type": "pointermove", "id": 41, "kind": "mouse", "primary": True, "x": ship["x"] + 150, "y": ship["y"]},
    ])
    moved = next(i for i in ed.summary()["items"] if i["id"] == ship["id"])
    assert moved["x"] == ship["x"] + 150
    ed.page.wait_for_timeout(2300)  # the pending autosave timer fires during the drag
    summary = ed.summary()
    assert summary["mutating"] is True
    assert summary["autosave"] == "pending"
    ed.pointer([{"type": "pointercancel", "id": 41, "kind": "mouse", "primary": True, "x": ship["x"] + 150, "y": ship["y"]}])
    assert next(i for i in ed.summary()["items"] if i["id"] == ship["id"])["x"] == ship["x"]
    expect(ed.page.locator("#saveStatus")).to_have_attribute("data-state", "saved", timeout=15000)
    draft = ed.page.evaluate(READ_DRAFT)
    assert draft["title"] == "Zugbrücke"
    assert next(i for i in draft["items"] if i["id"] == ship["id"])["x"] == ship["x"]
    assert ed.summary()["historySteps"] == 0
    ed.assert_clean()


def test_r2_scatter_cancelled_by_second_touch_is_never_autosaved(open_editor):
    ed = open_editor()
    count = ed.summary()["stamps"]
    ed.tool("stamp")
    ed.page.get_by_role("radio", name="Tanne", exact=True).click()
    ed.page.locator("#stampScatter").check()
    ed.page.locator("#mapTitle").fill("Streuwald")
    x, y = SEA_A
    ed.pointer([{"type": "pointerdown", "id": 51, "kind": "touch", "primary": True, "x": x - 200, "y": y}]
               + [{"type": "pointermove", "id": 51, "kind": "touch", "primary": True, "x": x - 200 + step * 40, "y": y} for step in range(1, 11)])
    assert ed.summary()["stamps"] >= count + 4
    ed.page.wait_for_timeout(2300)
    assert ed.summary()["autosave"] == "pending"
    ed.pointer([
        {"type": "pointerdown", "id": 52, "kind": "touch", "primary": False, "x": x + 300, "y": y + 100},
        {"type": "pointerup", "id": 52, "kind": "touch", "primary": False, "x": x + 300, "y": y + 100},
        {"type": "pointerup", "id": 51, "kind": "touch", "primary": True, "x": x + 200, "y": y},
    ])
    assert ed.summary()["stamps"] == count
    expect(ed.page.locator("#saveStatus")).to_have_attribute("data-state", "saved", timeout=15000)
    draft = ed.page.evaluate(READ_DRAFT)
    assert draft["title"] == "Streuwald"
    assert sum(1 for item in draft["items"] if "asset" in item) == count
    assert ed.summary()["historySteps"] == 0
    ed.assert_clean()


def test_r3_raster_area_limit_and_2x_export_limit_on_a_4096_map(open_editor, tmp_path):
    ed = open_editor()
    png = "data:image/png;base64," + base64.b64encode(_png_rgba_blank(4096, 4096)).decode()
    big = {
        "format": "rd-mapmaker", "version": 1,
        "meta": {"title": "Großkarte", "seed": 0, "created": "", "modified": ""},
        "size": {"w": 4096, "h": 4096}, "sea": {"top": "#2f5d6e", "bottom": "#7fa9a8"},
        "layers": [
            {"id": "land", "name": "Land", "kind": "raster", "visible": True, "opacity": 1, "effects": {"coast": True}, "png": png},
            {"id": "sym", "name": "Symbole", "kind": "stamps", "visible": True, "opacity": 1,
             "items": [{"id": "s1", "asset": "kenney:castle", "x": 2048, "y": 2048, "size": 120, "rot": 0, "flip": False}]},
            {"id": "txt", "name": "Beschriftung", "kind": "labels", "visible": True, "opacity": 1, "items": []},
        ],
    }
    ed.page.locator("#fileInput").set_input_files({"name": "gross.rdmap.json", "mimeType": "application/json", "buffer": json.dumps(big).encode()})
    expect(ed.page.locator("#toast")).to_contain_text("geladen")
    assert ed.summary()["size"] == {"w": 4096, "h": 4096}
    steps = ed.summary()["historySteps"]

    ed.tab("Ebenen")
    add_raster = ed.page.locator("#addRaster")
    expect(add_raster).to_be_disabled()
    assert ed.page.evaluate("() => { document.getElementById('addRaster').disabled = false; document.getElementById('addRaster').click(); return true; }")
    summary = ed.summary()
    assert [layer["kind"] for layer in summary["layers"]] == ["raster", "stamps", "labels"]
    assert summary["historySteps"] == steps
    expect(ed.page.locator("#toast")).to_contain_text("zu groß")
    ed.page.locator("#addStamps").click()
    assert len(ed.summary()["layers"]) == 4
    ed.page.locator("#mapTitle").fill("Großkarte zwei")

    with ed.page.expect_download() as info:
        ed.menu("Als Datei speichern")
    saved = tmp_path / "gross.rdmap.json"
    info.value.save_as(saved)
    ed.page.locator("#fileInput").set_input_files(str(saved))
    expect(ed.page.locator("#toast")).to_contain_text("„Großkarte zwei“ geladen")
    expect(ed.page.locator("#errorDialog")).to_be_hidden()
    assert len(ed.summary()["layers"]) == 4

    ed.menu("Als PNG exportieren …")
    dialog = ed.page.locator("#exportDialog")
    two = dialog.locator("input[name=exportScale][value='2']")
    expect(two).to_be_disabled()
    expect(dialog.locator("#exportLabel2")).to_contain_text("zu groß")
    expect(dialog.locator("#exportLabel1")).to_contain_text("4096 × 4096")
    # the export path itself refuses oversized output even if the UI is bypassed
    two.evaluate("(el) => { el.disabled = false; el.checked = true; }")
    dialog.get_by_role("button", name="Exportieren").click()
    expect(dialog.locator("#exportError")).to_contain_text("zu groß")
    dialog.get_by_role("button", name="Abbrechen").click()
    ed.assert_clean()


def test_r5_off_map_placement_is_rejected_and_drags_stay_in_contract(open_editor, tmp_path):
    ed = open_editor()
    for _ in range(10):
        ed.page.locator("#zoomOut").click()
    assert abs(ed.summary()["zoom"] - 0.1) < 1e-9
    box = ed.page.locator("#mapCanvas").bounding_box()
    outside = (box["x"] + 20, box["y"] + box["height"] / 2)
    before = ed.summary()
    ed.tool("stamp")
    ed.page.mouse.click(*outside)
    expect(ed.page.locator("#toast")).to_contain_text("nur auf der Karte")
    ed.tool("label")
    ed.page.mouse.click(*outside)
    expect(ed.page.locator("#toast")).to_contain_text("nur auf der Karte")
    after = ed.summary()
    assert (after["stamps"], after["labels"], after["historySteps"]) == (before["stamps"], before["labels"], 0)

    # a stamp placed at the very edge, then dragged far off the map
    ed.tool("stamp")
    ed.page.get_by_role("radio", name="Burg", exact=True).click()
    ed.click_doc(5, 800)
    edge = next(i for i in ed.summary()["items"] if i.get("asset") == "kenney:castle" and i["x"] < 50)
    ed.tool("select")
    ed.page.mouse.move(*ed.client(edge["x"], edge["y"]))
    ed.page.mouse.down()
    ed.page.mouse.move(box["x"] + 4, box["y"] + 4, steps=8)
    ed.page.mouse.up()
    dragged = next(i for i in ed.summary()["items"] if i["id"] == edge["id"])
    assert (dragged["x"], dragged["y"]) == (0, 0)

    label = next(i for i in ed.summary()["items"] if i.get("text") == "Glutinsel")
    ed.page.mouse.move(*ed.client(label["x"], label["y"]))
    ed.page.mouse.down()
    ed.page.mouse.move(box["x"] + box["width"] - 4, box["y"] + box["height"] - 4, steps=8)
    ed.page.mouse.up()
    moved = next(i for i in ed.summary()["items"] if i["id"] == label["id"])
    assert (moved["x"], moved["y"]) == (2400, 1600)

    with ed.page.expect_download() as info:
        ed.menu("Als Datei speichern")
    saved = tmp_path / "rand.rdmap.json"
    info.value.save_as(saved)
    for layer in json.loads(saved.read_text(encoding="utf-8"))["layers"]:
        for item in layer.get("items", []):
            assert 0 <= item["x"] <= 2400 and 0 <= item["y"] <= 1600, item
    ed.page.locator("#fileInput").set_input_files(str(saved))
    expect(ed.page.locator("#toast")).to_contain_text("geladen")
    expect(ed.page.locator("#errorDialog")).to_be_hidden()
    assert next(i for i in ed.summary()["items"] if i["id"] == label["id"])["x"] == 2400
    ed.assert_clean()


# --- real Flask serving (skipped when the app cannot be imported) -------------


@pytest.fixture(scope="module")
def flask_origin(tmp_path_factory):
    try:
        from werkzeug.serving import make_server

        from vtt import create_app
        from vtt.config import TestingConfig
    except Exception as error:  # pragma: no cover - depends on the local venv
        pytest.skip(f"Flask app not importable here: {error}")
    db_path = tmp_path_factory.mktemp("mapmaker") / "app.db"
    original = TestingConfig.SQLALCHEMY_DATABASE_URI
    TestingConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
    try:
        app = create_app("testing")
    finally:
        TestingConfig.SQLALCHEMY_DATABASE_URI = original
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", app
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_flask_serves_entry_redirect_and_static_app(flask_origin, open_editor):
    origin, app = flask_origin
    client = app.test_client()
    stub = client.get("/mapmaker")
    assert stub.status_code == 200
    assert 'url=/static/mapmaker/index.html' in stub.get_data(as_text=True)
    page = client.get(FLASK_PATH)
    assert page.status_code == 200 and "Content-Security-Policy" in page.headers
    assert client.get("/static/mapmaker/js/app.js").status_code == 200
    assert client.get("/static/mapmaker/assets/kenney-cartography/manifest.json").status_code == 200

    ed = open_editor(origin=origin, path="/mapmaker")
    assert ed.page.url.endswith(FLASK_PATH)
    assert ed.summary()["title"] == "Die Silbermark"
    assert _is_sea(ed.pixel(*SEA_A)) and not _is_sea(ed.pixel(*LAND))
    ed.proof("flask")
    ed.assert_clean()
