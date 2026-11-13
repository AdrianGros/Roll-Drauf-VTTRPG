"""Bounded server validation of the editor's rd-mapmaker v1 interchange format.

Keep limits in step with static/mapmaker/js/document.js. Only normalized fields
are stored; image URLs, arbitrary paths and executable content are not accepted.
"""

import base64
import binascii
from functools import lru_cache
import io
import json
import math
from pathlib import Path
import re

from PIL import Image

MAX_PROJECT_BYTES = 50 * 1024 * 1024
MAX_TILES = 65536
MAX_TILE_PALETTE = 256
PREFIX = "data:image/png;base64,"
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class InvalidDocument(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidDocument(message)


def number(value, low, high):
    require(type(value) in (int, float) and math.isfinite(value) and low <= value <= high,
            "Ungültige Zahl im Kartenprojekt.")
    return value


def integer(value, low, high):
    require(type(value) is int, "Ganzzahl erwartet.")
    return number(value, low, high)


def text(value, limit, fallback=""):
    require(value is None or isinstance(value, str), "Text erwartet.")
    return CONTROL.sub("", value or "").strip()[:limit] or fallback


def boolean(value):
    require(type(value) is bool, "Ja/Nein-Wert erwartet.")
    return value


def color(value):
    require(isinstance(value, str) and re.fullmatch(r"#[a-fA-F0-9]{6}", value), "Ungültige Farbe.")
    return value.lower()


@lru_cache(maxsize=1)
def known_assets():
    assets = Path(__file__).parent / "static" / "mapmaker" / "assets"
    result = {"builtin:" + name: None for name in ("compass", "pin", "mountain", "tree", "house", "castle")}
    packs = json.loads((assets / "packs.json").read_text())["packs"]
    for pack in packs:
        manifest = json.loads((assets / pack.get("palette", pack["manifest"])).read_text())
        if manifest.get("schemaVersion") == 2:
            entries = ({"id": row[0], "w": row[3], "h": row[4]} for row in manifest["rows"])
        else:
            entries = manifest["stamps"]
        for entry in entries:
            result[entry["id"]] = (entry["w"], entry["h"])
    return result


def normalize_document(raw):
    require(isinstance(raw, dict) and raw.get("format") == "rd-mapmaker"
            and type(raw.get("version")) is int and raw["version"] == 1,
            "Kein unterstütztes Roll-Drauf-Kartenprojekt (Version 1).")
    size = raw.get("size")
    require(isinstance(size, dict), "Kartengröße fehlt.")
    w, h = (integer(size.get(side), 256, 4096) for side in ("w", "h"))
    meta = raw.get("meta", {})
    sea = raw.get("sea", {})
    require(isinstance(meta, dict) and isinstance(sea, dict), "Kartenmetadaten sind ungültig.")
    result = {
        "format": "rd-mapmaker", "version": 1,
        "size": {"w": w, "h": h},
        "meta": {"title": text(meta.get("title"), 80, "Unbenannte Karte"),
                 "seed": meta.get("seed") if type(meta.get("seed")) is int else 0,
                 "created": text(meta.get("created"), 40),
                 "modified": text(meta.get("modified"), 40),
                 "showTitle": boolean(meta.get("showTitle", False))},
        "sea": {"top": color(sea.get("top", "#2f5d6e")),
                "bottom": color(sea.get("bottom", "#7fa9a8"))},
        "layers": [],
    }
    layers = raw.get("layers")
    require(isinstance(layers, list) and 1 <= len(layers) <= 32, "1 bis 32 Ebenen erwartet.")
    ids, raster_count, item_count, tile_count = set(), 0, 0, 0
    assets = known_assets()

    def identifier(value):
        require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,40}", value)
                and value not in ids, "Ungültige oder doppelte Kennung.")
        ids.add(value)
        return value

    def asset(value):
        require(isinstance(value, str) and value in assets, "Unbekanntes Kartensymbol.")
        return value

    for incoming in layers:
        require(isinstance(incoming, dict), "Ungültige Ebene.")
        kind = incoming.get("kind")
        require(kind in ("raster", "paths", "stamps", "labels", "tiles"), "Unbekannte Ebenenart.")
        layer = {"id": identifier(incoming.get("id")), "kind": kind,
                 "name": text(incoming.get("name"), 40, "Ebene"),
                 "visible": boolean(incoming.get("visible", True)),
                 "opacity": number(incoming.get("opacity", 1), 0, 1)}
        if kind == "raster":
            raster_count += 1
            require(raster_count <= 8 and raster_count * w * h <= 32000000, "Zu viele oder zu große Malebenen.")
            effects = incoming.get("effects", {})
            require(isinstance(effects, dict), "Ungültige Ebeneneffekte.")
            layer["effects"] = {"coast": boolean(effects.get("coast", False))}
            if "coastColor" in effects:
                layer["effects"]["coastColor"] = color(effects["coastColor"])
            if "coastWidth" in effects:
                layer["effects"]["coastWidth"] = number(effects["coastWidth"], 0, 16)
            png = incoming.get("png")
            require(isinstance(png, str) and png.startswith(PREFIX), "Eingebettetes PNG erwartet.")
            try:
                data = base64.b64decode(png[len(PREFIX):], validate=True)
                with Image.open(io.BytesIO(data)) as image:
                    require(image.format == "PNG" and image.size == (w, h)
                            and getattr(image, "n_frames", 1) == 1, "PNG-Größe oder Format passt nicht zur Karte.")
                    image.verify()
                with Image.open(io.BytesIO(data)) as image:
                    image.load()
            except (OSError, ValueError, binascii.Error, Image.DecompressionBombError) as error:
                raise InvalidDocument("Beschädigte oder ungültige PNG-Malebene.") from error
            layer["png"] = png
        elif kind == "tiles":
            grid = incoming.get("grid")
            require(isinstance(grid, dict), "Kachelraster fehlt.")
            size = integer(grid.get("size"), 8, 256)
            palette = incoming.get("palette")
            require(isinstance(palette, list) and len(palette) <= MAX_TILE_PALETTE
                    and all(isinstance(entry, str) for entry in palette)
                    and len(set(palette)) == len(palette), "Ungültige Kachelliste.")
            for entry in palette:
                asset(entry)
            cells = incoming.get("cells")
            require(isinstance(cells, list) and len(cells) % 3 == 0, "Ungültige Kachelzellen.")
            cols, rows = math.ceil(w / size), math.ceil(h / size)
            occupied = set()
            for i in range(0, len(cells), 3):
                col, row, index = cells[i:i + 3]
                require(all(type(v) is int for v in (col, row, index))
                        and 0 <= col < cols and 0 <= row < rows and 0 <= index < len(palette)
                        and (col, row) not in occupied, "Kachel außerhalb der Karte oder doppelt belegt.")
                occupied.add((col, row))
            tile_count += len(occupied)
            require(tile_count <= MAX_TILES, f"Höchstens {MAX_TILES} Kacheln pro Karte erlaubt.")
            layer.update(grid={"size": size}, palette=list(palette), cells=list(cells))
        else:
            items = incoming.get("items")
            require(isinstance(items, list), "Elementliste fehlt.")
            item_count += len(items)
            require(item_count <= 2000, "Höchstens 2000 Kartenelemente erlaubt.")
            layer["items"] = []
            for entry in items:
                require(isinstance(entry, dict), "Ungültiges Kartenelement.")
                item = {"id": identifier(entry.get("id")),
                        "x": number(entry.get("x"), -w, 2*w),
                        "y": number(entry.get("y"), -h, 2*h)}
                if kind == "stamps":
                    item.update(asset=asset(entry.get("asset")), size=number(entry.get("size"), 4, 512),
                                rot=number(entry.get("rot", 0), -360, 360), flip=boolean(entry.get("flip", False)))
                    if entry.get("crop") is not None:
                        crop, dims = entry["crop"], assets[item["asset"]]
                        require(isinstance(crop, dict) and dims is not None, "Ungültiger Bildausschnitt.")
                        c = {k: integer(crop.get(k), 0 if k in ("x", "y") else 1, 65536) for k in ("x", "y", "w", "h")}
                        require(c["x"]+c["w"] <= dims[0] and c["y"]+c["h"] <= dims[1], "Bildausschnitt liegt außerhalb des Symbols.")
                        item["crop"] = c
                elif kind == "paths":
                    require(entry.get("material") in ("road", "river"), "Ungültiges Wegmaterial.")
                    points = entry.get("points")
                    require(isinstance(points, list) and 2 <= len(points) <= 128, "Ungültige Wegpunkte.")
                    clean_points = []
                    for point in points:
                        require(isinstance(point, dict), "Ungültiger Wegpunkt.")
                        clean_points.append({"x": number(point.get("x"), -2*w, 2*w), "y": number(point.get("y"), -2*h, 2*h)})
                    require(clean_points[0] == {"x": 0, "y": 0}, "Erster Wegpunkt muss 0,0 sein.")
                    item.update(material=entry["material"], width=number(entry.get("width"), 2, 80), points=clean_points, curve=boolean(entry.get("curve", False)))
                else:
                    label = text(entry.get("text"), 80)
                    require(entry.get("style") in ("realm", "region", "city", "town", "water", "feature"), "Ungültige Beschriftung.")
                    item.update(text=label, style=entry["style"], size=number(entry.get("size"), 8, 200),
                                rot=number(entry.get("rot", 0), -360, 360), color=color(entry.get("color", "#3b2a1a")),
                                pin=boolean(entry.get("pin", False)), place=None, symbol=None)
                    place = entry.get("place")
                    if place is not None:
                        require(isinstance(place, dict) and place.get("kind") in ("city", "town", "castle", "harbor", "ruin", "landmark"), "Ungültiger Ort.")
                        item["place"] = {"kind": place["kind"], "lore": text(place.get("lore"), 500)}
                    symbol = entry.get("symbol")
                    if symbol is not None:
                        require(place is not None and isinstance(symbol, dict), "Ungültiges Ortssymbol.")
                        item["symbol"] = {"asset": asset(symbol.get("asset")), "size": number(symbol.get("size"), 16, 320)}
                    require(label or item["pin"] or item["symbol"], "Leere Beschriftung braucht ein Symbol oder eine Ortsnadel.")
                layer["items"].append(item)
        result["layers"].append(layer)
    data = json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    require(len(data) <= MAX_PROJECT_BYTES, "Das Kartenprojekt ist größer als 50 MiB.")
    return result, data
