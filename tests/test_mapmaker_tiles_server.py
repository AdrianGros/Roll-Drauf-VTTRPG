"""Server validation of tile layers in the rd-mapmaker v1 document (vtt/mapmaker_document.py)."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GRASS = "color:kenney-tiny_33382ddbb14436e9"
WALL = "color:kenney-tiny_1a2fdb62b6610bca"


@pytest.fixture(scope="module")
def document():
    spec = importlib.util.spec_from_file_location("mapmaker_document", ROOT / "vtt" / "mapmaker_document.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _doc(**tiles):
    layer = {"id": "k1", "kind": "tiles", "name": "Boden", "visible": True, "opacity": 1,
             "grid": {"size": 32}, "palette": [GRASS, WALL], "cells": [0, 0, 0, 15, 7, 1]}
    layer.update(tiles)
    return {"format": "rd-mapmaker", "version": 1, "size": {"w": 512, "h": 256}, "meta": {"title": "Kacheln"},
            "sea": {}, "layers": [layer]}


def test_valid_tile_layer_is_normalized(document):
    result, data = document.normalize_document(_doc())
    layer = result["layers"][0]
    assert layer["kind"] == "tiles" and layer["grid"] == {"size": 32}
    assert layer["palette"] == [GRASS, WALL] and layer["cells"] == [0, 0, 0, 15, 7, 1]
    assert "items" not in layer and b'"kind":"tiles"' in data


@pytest.mark.parametrize("tiles", [
    {"grid": {"size": 4}},
    {"grid": {"size": 300}},
    {"grid": None},
    {"cells": [16, 0, 0]},
    {"cells": [0, 8, 0]},
    {"cells": [0, 0, 2]},
    {"cells": [0, 0, 0, 0, 0, 1]},
    {"cells": [0, 0]},
    {"cells": [0.5, 0, 0]},
    {"cells": [True, 0, 0]},
    {"palette": [GRASS, GRASS]},
    {"palette": ["color:kenney-tiny_0000000000000000"]},
    {"palette": [GRASS] + [f"x{i}" for i in range(256)]},
])
def test_invalid_tile_layers_are_rejected(document, tiles):
    with pytest.raises(document.InvalidDocument):
        document.normalize_document(_doc(**tiles))


def test_tile_count_is_bounded_per_map(document):
    full = [v for row in range(64) for col in range(128) for v in (col, row, 0)]  # 8192 cells at 8 px
    layers = [dict(_doc(grid={"size": 8}, cells=full)["layers"][0], id=f"k{i}") for i in range(8)]
    doc = dict(_doc(), size={"w": 1024, "h": 512}, layers=layers)
    document.normalize_document(doc)  # exactly 65,536 tiles
    doc["layers"].append(dict(layers[0], id="k9", cells=[0, 0, 0]))
    with pytest.raises(document.InvalidDocument):
        document.normalize_document(doc)
