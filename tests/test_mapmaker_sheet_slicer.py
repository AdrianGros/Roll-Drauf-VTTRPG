"""Tilesheet slicing: detection proposals, reviewed profiles and compiled stamps.

Covers tools/mapmaker_sheet_slicer.py and the Kenney Tiny Town profile in
tools/mapmaker_slices/. Pixels are compared against the pinned original sheet.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest
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


PROFILES = sorted((ROOT / "tools" / "mapmaker_slices").glob("*.json"))


@pytest.mark.parametrize("path", PROFILES, ids=lambda p: p.stem)
def test_every_reviewed_slice_copies_its_sheet_pixels(path):
    """Grid cells, rectangle composites, recipes and gridless objects all match a fresh recomposition."""
    profile = json.loads(path.read_text())
    assert profile["review"]["status"] == "reviewed" and profile["review"]["method"]
    pack = profile["pack"]
    if profile["detector"] == slicer.SINGLES:
        return _check_named_singles(profile)
    manifest = json.loads((ASSETS / pack / "manifest.json").read_text())
    slices = [s for s in manifest["stamps"] if "slice" in s]
    assert slices and all(s["slice"]["profile"] == f"tools/mapmaker_slices/{path.name}" for s in slices)
    by_sheet = {}
    for stamp in slices: by_sheet.setdefault(stamp["originalPath"], []).append(stamp)
    specs = profile.get("sheets", [profile])
    assert set(by_sheet) == {spec["sheet"]["path"] for spec in specs}
    for spec in specs:
        digest = spec["sheet"]["sha256"]
        _entry, _digest, img = slicer.load_sheet(pack, spec["sheet"]["path"], digest)
        if spec["detector"] == slicer.COMPONENTS:
            params = spec["params"]
            found = {slicer.box_key(g["box"]): g for g in slicer.components(img, params["gap"], params["minArea"], params.get("split"), params.get("gridSplits"))[0]}
            assert set(found) == set(spec["objects"])
        else:
            grid = slicer.Grid(img, spec["grid"])
        for stamp in by_sheet[spec["sheet"]["path"]]:
            layout = stamp["slice"]["layout"]
            if layout.startswith("box:"):
                expected = slicer.component_image(img, found[layout[4:]])
            elif "/" in layout:
                expected = slicer.compose_rows(img, grid, slicer.parse_rows(layout.split("/")))
            else:
                expected = slicer.compose(img, grid, slicer.parse_cells(layout))
            with Image.open(ASSETS / pack / stamp["file"]) as png:
                assert png.convert("RGBA").tobytes() == expected.tobytes(), (pack, stamp["label"])
            assert stamp["id"] == slicer.slice_id(pack, digest, layout)
            assert (stamp["w"], stamp["h"]) == expected.size and stamp["originalSha256"] == digest
            assert not stamp.get("tile") or (stamp["w"] == stamp["h"] and "box:" not in layout and " " not in layout)
    # Exact duplicates are offered once as tiles; every id stays in the catalogue.
    tiles = [s for s in manifest["stamps"] if s.get("tile")]
    assert len({s["file"] for s in tiles}) == len(tiles)
    palette = json.loads((ASSETS / pack / "palette.json").read_text())
    assert len(palette["rows"]) == len(manifest["stamps"])


def test_reviewed_boundaries_of_complex_sheets():
    def stamps(pack):
        return {s["label"]: s for s in json.loads((ASSETS / pack / "manifest.json").read_text())["stamps"] if not s.get("hidden")}
    castle = stamps("castle-rpg")
    # Detection glued these together; the review separates them.
    assert (castle["Laternenpfahl"]["w"], castle["Laternenpfahl"]["h"]) == (32, 96)
    assert (castle["Ziehbrunnen"]["w"], castle["Ziehbrunnen"]["h"]) == (64, 64)
    assert (castle["Springbrunnen"]["w"], castle["Springbrunnen"]["h"]) == (64, 64)
    assert (castle["Uhrenbaum"]["w"], castle["Uhrenbaum"]["h"]) == (64, 128)
    lpc = stamps("lpc-castle")
    assert {"Fallgitter (schmal)", "Fallgitter (breit)"} <= set(lpc) and "Fallgitter" not in lpc
    coverage = json.loads((ASSETS / "lpc-castle" / "coverage.json").read_text())["slices"]
    assert sorted(e["cells"] for e in coverage["excluded"]) == ["0,0", "0,1", "7,14", "8,14"]
    ruins = json.loads((ASSETS / "2dpixx-ruins" / "manifest.json").read_text())["stamps"]
    assert sum("slice" in s for s in ruins) == 13  # staggered blocks overlap as boxes but stay separate
    assert not any(s.get("tile") for s in ruins)


def _check_named_singles(profile):
    """singles-v1: originals renamed in place, no new ids; hidden duplicates point at a visible twin."""
    manifest = json.loads((ASSETS / profile["pack"] / "manifest.json").read_text())
    by_path = {s["originalPath"]: s for s in manifest["stamps"]}
    assert not any("slice" in s for s in manifest["stamps"])
    for path, spec in profile["singles"].items():
        stamp = by_path[path]
        assert (stamp["label"], stamp["group"]) == (spec["label"], spec["group"]) and not stamp.get("hidden")
        assert bool(stamp.get("tile")) == (spec.get("kind") == "tile" and stamp["w"] == stamp["h"])
    for path, reason in profile.get("hidden", {}).items():
        twin = reason.split(" von ", 1)[1].split(" (", 1)[0]
        assert by_path[path].get("hidden") and not by_path[twin].get("hidden")
    assert all(s["originalPath"] in profile["singles"] or s["originalPath"] in profile.get("hidden", {})
               or s["group"] == "Referenzen & Szenen" for s in manifest["stamps"])


def test_rts_hd_twins_match_their_standard_images():
    """The HD set is hidden only because every HD image has its own standard twin."""
    from PIL import ImageChops, ImageStat
    profile = json.loads((ROOT / "tools" / "mapmaker_slices" / "kenney-rts.json").read_text())
    manifest = {s["originalPath"]: s for s in json.loads((ASSETS / "kenney-rts" / "manifest.json").read_text())["stamps"]}
    twins = [reason.split(" von ", 1)[1].split(" (", 1)[0] for reason in profile["hidden"].values()]
    assert len(profile["hidden"]) == len(set(twins)) == 126
    for hd_path, twin in zip(profile["hidden"], twins):
        def flat(path, size=None):
            img = Image.open(ASSETS / "kenney-rts" / manifest[path]["file"]).convert("RGBA")
            img = img.resize(size, Image.LANCZOS) if size else img
            base = Image.new("RGBA", img.size, (255, 0, 255, 255)); base.alpha_composite(img)
            return base.convert("RGB")
        diff = ImageChops.difference(flat(hd_path, (64, 64)), flat(twin))
        assert sum(ImageStat.Stat(diff).mean) < 8, hd_path


def test_lpc_slices_only_static_sheets_and_keeps_character_sheets_in_place():
    profile = json.loads((ROOT / "tools" / "mapmaker_slices" / "lpc-revised.json").read_text())
    paths = [spec["sheet"]["path"] for spec in profile["sheets"]]
    assert not any(p.startswith("Characters/") or "Emission" in p or "Shadows" in p or "Waterfall" in p for p in paths)
    assert not any(p.endswith(("12 Panel Door A.png", "15 Panel Door A.png", "Fire, Camp.png")) for p in paths)  # animation strips
    manifest = json.loads((ASSETS / "lpc-revised" / "manifest.json").read_text())
    characters = [s for s in manifest["stamps"] if s["originalPath"].startswith("Characters/")]
    assert len(characters) == 63972 and all(s["group"] == "Figuren & Kleidung" and s["sheet"] for s in characters)
    by_label = {s["label"]: s for s in manifest["stamps"] if "slice" in s and not s.get("hidden")}
    assert by_label["Baumschatten (Sommer)"]["h"] <= 32
    trees = [s for s in by_label.values() if s["originalPath"] == "Terrain/trees_summer.png" and s["label"].startswith("Baum (")]
    assert len(trees) >= 16 and all(s["w"] <= 96 for s in trees)  # packed crowns are split into single trees
