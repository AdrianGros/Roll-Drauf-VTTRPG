"""Tilesheet slicing: detection proposals, reviewed profiles and compiled stamps.

Covers tools/mapmaker_sheet_slicer.py and the Kenney Tiny Town profile in
tools/mapmaker_slices/. Pixels are compared against the pinned original sheet.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import mapmaker_sheet_slicer as slicer  # noqa: E402

ASSETS = ROOT / "vtt" / "static" / "mapmaker" / "assets"
PROFILE = json.loads((ROOT / "tools" / "mapmaker_slices" / "kenney-tiny.json").read_text())


def _tiny_sheet():
    _entry, digest, img = slicer.load_sheet("kenney-tiny", PROFILE["sheet"]["path"], PROFILE["sheet"]["sha256"])
    grid = slicer.Grid(img, PROFILE["grid"])
    return digest, img, grid


def test_detector_keeps_tall_trees_and_multi_tile_objects_whole():
    _digest, img, grid = _tiny_sheet()
    cells = slicer.alpha_cells(img, grid)
    groups = {slicer.fmt_cells(g) for g in slicer.detect_groups(cells, grid, slicer.outline_colours(img))}
    # Two-tile trees and the well were offered as halves before slicing.
    for expected in ("0,3 1,3", "0,4 1,4", "7,8 8,8", "3,11 4,11 5,11", "6,8 6,9 6,10",
                     "0,6 0,7 0,8 1,6 1,7 1,8 2,6 2,7 2,8", "0,9 0,10 0,11 1,9 1,10 1,11 2,9 2,10 2,11",
                     "3,8 3,9 3,10 4,8 4,10 5,8 5,9 5,10"):
        assert expected in groups
    # Objects that only touch outline to outline stay separate (well above the pitchfork, stacked tools).
    for single in ("9,8", "9,9", "10,7", "10,8", "4,9", "0,5", "2,5"):
        assert single in groups
    # Opaque terrain tiles are never glued together.
    for terrain in ("0,0", "0,1", "2,1", "6,1"):
        assert terrain in groups


def test_reviewed_profile_accounts_for_every_visible_cell():
    _digest, img, grid = _tiny_sheet()
    cells = slicer.alpha_cells(img, grid)
    visible = {slicer.fmt_cells([k]) for k, c in cells.items() if c["state"] != "empty"}
    assert set(PROFILE["cells"]) == visible and len(visible) == 132
    assert PROFILE["review"]["status"] == "reviewed"
    for unit in PROFILE["composites"]:
        members = slicer.parse_cells(unit["cells"]) if "cells" in unit else [k for row in slicer.parse_rows(unit["rows"]) for k in row if k]
        assert all(slicer.fmt_cells([k]) in visible for k in members), unit["label"]


def test_every_slice_stamp_copies_original_sheet_pixels():
    digest, img, grid = _tiny_sheet()
    manifest = json.loads((ASSETS / "kenney-tiny" / "manifest.json").read_text())
    slices = [s for s in manifest["stamps"] if "slice" in s]
    assert len(slices) == len(PROFILE["composites"]) == 17
    for stamp in slices:
        layout = stamp["slice"]["layout"]
        expected = (slicer.compose_rows(img, grid, slicer.parse_rows(layout.split("/"))) if "/" in layout
                    else slicer.compose(img, grid, slicer.parse_cells(layout)))
        data = (ASSETS / "kenney-tiny" / stamp["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == stamp["sha256"]
        with Image.open(ASSETS / "kenney-tiny" / stamp["file"]) as png:
            assert png.convert("RGBA").tobytes() == expected.tobytes(), stamp["label"]
        assert (stamp["w"], stamp["h"]) == expected.size and stamp["defaultSize"] == max(expected.size)
        assert stamp["id"] == slicer.slice_id("kenney-tiny", digest, layout)
        assert stamp["originalSha256"] == digest and stamp["sheet"] is False


def test_slice_ids_are_pinned_and_parts_stay_resolvable():
    manifest = json.loads((ASSETS / "kenney-tiny" / "manifest.json").read_text())
    by_label = {s["label"]: s for s in manifest["stamps"]}
    # Published identities: changing them would orphan saved maps.
    assert by_label["Hoher Laubbaum"]["id"] == "color:kenney-tiny_9becbdb192215735"
    assert by_label["Haus mit Schieferdach"]["id"] == "color:kenney-tiny_93c819cbff90ae23"
    assert (by_label["Hoher Laubbaum"]["w"], by_label["Hoher Laubbaum"]["h"]) == (16, 32)
    assert by_label["Haus mit Schieferdach"]["slice"]["layout"] == "4,0 4,3 4,2/5,0 5,3 5,2/6,0 7,1 6,3"
    hidden = {s["id"] for s in manifest["stamps"] if s.get("hidden")}
    assert {by_label["Hoher Laubbaum · Krone"]["id"], by_label["Hoher Laubbaum · Stamm"]["id"],
            by_label["Brunnen · Dach"]["id"]} <= hidden
    assert len(hidden) == 12
    # Original single tiles keep their IDs; only label and category change.
    tile = next(s for s in manifest["stamps"] if s["originalPath"] == "Tiles/tile_0004.png")
    assert tile["id"] == "color:kenney-tiny_" + hashlib.sha256(b"Tiles/tile_0004.png").hexdigest()[:16]
    spec = importlib.util.spec_from_file_location("mapmaker_document", ROOT / "vtt" / "mapmaker_document.py")
    document = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(document)
    known = document.known_assets()
    assert hidden <= set(known) and by_label["Hoher Laubbaum"]["id"] in known
    palette = json.loads((ASSETS / "kenney-tiny" / "palette.json").read_text())
    assert set(palette["hidden"]) == hidden and len(palette["rows"]) == len(manifest["stamps"])


def test_sheet_without_review_is_refused(tmp_path, monkeypatch):
    draft = dict(PROFILE, review=dict(status="draft"))
    (tmp_path / "kenney-tiny.json").write_text(json.dumps(draft))
    monkeypatch.setattr(slicer, "PROFILES", tmp_path)
    try:
        slicer.cmd_build(type("Args", (), {"pack": "kenney-tiny"}))
    except SystemExit as error:
        assert "reviewed" in str(error)
    else:
        raise AssertionError("an unreviewed profile must not build")


def test_tiles_and_stamps_are_classified_from_the_review():
    manifest = json.loads((ASSETS / "kenney-tiny" / "manifest.json").read_text())
    palette = json.loads((ASSETS / "kenney-tiny" / "palette.json").read_text())
    by_label = {s["label"]: s for s in manifest["stamps"]}
    tiles = {s["id"] for s in manifest["stamps"] if s.get("tile")}
    assert len(tiles) == 97 and palette["tiles"] == [s["id"] for s in manifest["stamps"] if s.get("tile")]
    # Ground, roofs, walls, fences and castle parts are grid tiles ...
    for label in ("Gras", "Erdfläche · Mitte", "Schieferdach · Giebel", "Holzwand · Tür", "Zaungehege · links", "Burghof · Mitte"):
        assert by_label[label]["id"] in tiles, label
    # ... trees, items and every assembled object stay stamps; hidden halves are neither.
    for label in ("Busch", "Axt", "Bienenstock", "Hoher Laubbaum", "Haus mit Schieferdach", "Waldstück", "Brunnen"):
        assert by_label[label]["id"] not in tiles, label
    assert not tiles & {s["id"] for s in manifest["stamps"] if s.get("hidden")}
    assert all(s["w"] == s["h"] == 16 for s in manifest["stamps"] if s.get("tile"))
