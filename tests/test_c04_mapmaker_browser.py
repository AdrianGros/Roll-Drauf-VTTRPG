"""C04 static composition/contract checks.

These do NOT replace the pointer/editor-to-table browser journeys, which still need a
real browser run by the coordinator (see the handoff's proposed checks).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "vtt/static"


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
    assert 'value="active">Aktive Ebene' in html and 'value="visible">Alle sichtbaren Ebenen' in html
    assert 'id="stampGridOn" type="checkbox" checked' not in html  # stamp grid is off by default
