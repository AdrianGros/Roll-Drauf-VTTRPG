"""Authenticated normal Maps journeys with synthetic QA accounts and local-only map files.

Create and remove accounts with the existing feedback-harness live-fixture.py.
Credentials stay in the protected release directory, never in these audit artifacts.
"""
import hashlib
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from tests.test_full_version_layers_browser import add_paths, paths
from tests.test_mapmaker_browser import Editor
from tests.test_review_maps_browser import save_file


root = Path(os.environ["PROOF_ROOT"])
fixture = json.loads((root / "private-live-credentials.json").read_text())
origin = "https://vtt.roll-drauf.de"
proof = {"status": "running", "origin": origin, "journeys": [], "real_oauth_tested": False}
expect.set_options(timeout=30000)


def save():
    (root / "live.json").write_text(json.dumps(proof, indent=2) + "\n")


with sync_playwright() as playwright:
    for engine, user, width, language, theme in [
        ("chromium", "dm", 1440, "de", "night"),
        ("firefox", "player", 390, "en", "paper"),
    ]:
        browser = getattr(playwright, engine).launch(headless=True,
            **({"args": ["--no-sandbox"]} if engine == "chromium" else {}))
        context = browser.new_context(viewport={"width": width, "height": 1000},
                                      accept_downloads=True, reduced_motion="reduce")
        prefs = {"schema": 1, "language": language, "theme": theme, "accent": "teal"}
        context.add_init_script(f"localStorage.setItem('vtt.display.v1', {json.dumps(json.dumps(prefs))})")
        auth = fixture["users"][user]
        context.add_cookies([
            {"name": "access_token_cookie", "value": auth["token"], "url": origin, "httpOnly": True, "secure": True},
            {"name": "csrf_access_token", "value": auth["csrf"], "url": origin, "secure": True},
        ])
        page = context.new_page()
        page.set_default_timeout(30000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(origin + "/dashboard")
            page.locator('.book-dashboard-ribbon:visible a[href="/mapmaker"]').click()
            page.wait_for_selector("#app[data-state=ready]")
            page.locator("#newEmpty").click()
            ed = Editor(context, page, errors)
            lower, upper = add_paths(ed), add_paths(ed)
            ed.tool("path")
            page.locator("#toolLayer").select_option(lower)
            ed.drag([(500, 500), (650, 550), (800, 500)])
            (path,) = ed.summary()["items"]
            assert path["layer"] == lower and len(paths(ed)) == 2
            assert next(layer for layer in paths(ed) if layer["id"] == upper)["items"] == 0

            if width < 760:
                page.locator("#activeLayerJump").click()
            radio = page.locator("#stageLayerList input:checked")
            old = radio.input_value()
            radio.focus()
            radio.press("ArrowRight")
            assert ed.summary()["activeLayer"] != old
            expect(page.locator("#stageLayerList input:checked")).to_be_focused()
            if width < 760:
                page.locator("#stageLayerList input:checked").press("Escape")
                expect(page.locator("#activeLayerJump")).to_be_focused()
            page.locator("#tab-layers").click()
            page.locator("#layerFilterKind").select_option("paths")
            expect(page.locator("#layerList .mm-layer")).to_have_count(2)
            page.locator("#layerSort").select_option("recent")
            page.locator("#layerFilterKind").select_option("")

            ed.tool("tile")
            page.locator("#tileSize").select_option("32")
            ed.click_doc(700, 650)
            (before,) = [layer for layer in ed.summary()["layers"] if layer["kind"] == "tiles"]
            assert before["tiles"]
            page.locator("#tileSize").select_option("64")
            (after,) = [layer for layer in ed.summary()["layers"] if layer["kind"] == "tiles"]
            assert before == after
            expect(page.locator("#tileSize")).to_have_value("32")
            page.locator("#tileNewLayer").click()
            assert len([layer for layer in ed.summary()["layers"] if layer["kind"] == "tiles"]) == 2
            page.locator("#mapCanvas").focus()
            page.keyboard.press("Control+z")
            assert [layer for layer in ed.summary()["layers"] if layer["kind"] == "tiles"] == [before]

            ed.tool("stamp")
            options = page.locator("#stampAdvanced")
            expect(options).not_to_have_attribute("open", "")
            options.locator("summary").click()
            page.locator("#stampScatter").check()
            options.locator("summary").click()
            expect(options.locator("summary")).to_contain_text("Streuen" if language == "de" else "Scatter")
            page.locator("#fileMenuBtn").click()
            page.locator("#fileMenuList button").first.press("Escape")
            assert ed.summary()["tool"] == "stamp"
            page.locator("#referenceGrid").check()

            exported = root / f"map-{engine}-{width}.rdmap.json"
            bundle = save_file(ed, exported)
            assert bundle
            generation = ed.summary()["generation"]
            page.locator("#fileInput").set_input_files(str(exported))
            page.wait_for_function("before => window.rdMapmaker.summary()?.generation > before", arg=generation)
            assert ed.summary()["items"][0]["layer"] == lower
            assert [layer for layer in ed.summary()["layers"] if layer["kind"] == "tiles"][0]["tiles"] == before["tiles"]
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            assert not errors, errors
            page.screenshot(path=str(root / f"layers-{engine}-{width}-{language}.png"))
            proof["journeys"].append({"engine": engine, "role": user, "width": width,
                "language": language, "theme": theme, "normal_maps_navigation": True,
                "lower_target_and_no_duplicate": True, "native_radio_keyboard": True,
                "filters_and_recent_order_available": True, "occupied_grid_unchanged": True,
                "explicit_new_grid_layer_and_undo": True, "disclosure_and_active_mode_visible": True,
                "menu_escape_keeps_tool": True, "reference_grid_independent": True,
                "file_save_reload_keeps_content": True, "file_sha256": hashlib.sha256(exported.read_bytes()).hexdigest(),
                "browser_errors": errors})
            save()
        except Exception as error:
            proof.update(status="failed", error=str(error))
            page.screenshot(path=str(root / f"failure-{engine}-{width}.png"))
            save()
            raise
        finally:
            context.close()
            browser.close()
proof["status"] = "pass"
save()
print(json.dumps({"status": "pass", "journeys": len(proof["journeys"])}))
