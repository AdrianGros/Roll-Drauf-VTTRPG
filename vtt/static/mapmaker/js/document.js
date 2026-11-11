globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Document model, limits and import validation for the rd-mapmaker v1 format.

export const FORMAT = "rd-mapmaker";
export const VERSION = 1;

export const LIMITS = Object.freeze({
    fileBytes: 50 * 1024 * 1024,
    minSide: 256,
    maxSide: 4096,
    layers: 32,
    rasterLayers: 8,
    items: 2000,
    tiles: 65536,
    tileGrid: [8, 256],
    tilePalette: 256,
    rasterArea: 32000000,
    title: 80,
    layerName: 40,
    labelText: 80,
    lore: 500,
    stampSize: [4, 512],
    labelSize: [8, 200],
    rotation: 360,
    pathPoints: 128,
});

export const LAYER_KINDS = ["raster", "paths", "stamps", "labels", "tiles"];
export const TILE_GRID_DEFAULT = 32;
export const LABEL_STYLES = {
    realm: { name: globalThis.VTTUi("Reich"), size: 72 },
    region: { name: globalThis.VTTUi("Region"), size: 40 },
    city: { name: globalThis.VTTUi("Stadt"), size: 40 },
    town: { name: globalThis.VTTUi("Ort"), size: 30 },
    water: { name: globalThis.VTTUi("Gewässer"), size: 34 },
    feature: { name: globalThis.VTTUi("Landmarke"), size: 28 },
};
export const PLACE_KINDS = {
    city: "Stadt",
    town: "Dorf",
    castle: "Burg",
    harbor: "Hafen",
    ruin: "Ruine",
    landmark: "Landmarke",
};

const ID_RE = /^[A-Za-z0-9_-]{1,40}$/;
const COLOR_RE = /^#[0-9a-fA-F]{6}$/;
const ASSET_RE = /^(builtin|kenney|kma|color):[a-z0-9_-]{1,40}$/;
const PNG_PREFIX = "data:image/png;base64,";
const PNG_SIGNATURE = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
// Control characters except tab and newline (lore may contain line breaks).
const CONTROL_RE = /[\u0000-\u0008\u000b-\u001f\u007f]/g;

export class ValidationError extends Error {}

let idCounter = 0;
export function newId(prefix, taken) {
    let id;
    do {
        idCounter += 1;
        id = `${prefix}${Date.now().toString(36).slice(-4)}${idCounter.toString(36)}`;
    } while (taken && taken.has(id));
    return id;
}

export function collectIds(doc) {
    const ids = new Set();
    for (const layer of doc.layers) {
        ids.add(layer.id);
        for (const item of layer.items || []) ids.add(item.id);
    }
    return ids;
}

export function cleanText(value, max) {
    return String(value ?? "").replace(CONTROL_RE, "").trim().slice(0, max);
}

export function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

export function createLayer(kind, name, size, taken) {
    const layer = {
        id: newId(({ raster: "r", paths: "w", stamps: "s", labels: "t", tiles: "k" })[kind], taken),
        name,
        kind,
        visible: true,
        opacity: 1,
        effects: { coast: false },
        items: kind === "raster" || kind === "tiles" ? undefined : [],
        canvas: null,
        rev: 0,
    };
    if (kind === "raster") layer.canvas = createCanvas(size.w, size.h);
    if (kind === "tiles") Object.assign(layer, { grid: { size: TILE_GRID_DEFAULT }, cells: new Map() });
    return layer;
}

// ---- tile layers -----------------------------------------------------------
// Runtime cells: Map(cellKey → asset id). The key packs column and row; the
// grid never exceeds 4096 / 8 = 512 cells per side.

export function cellKey(col, row) {
    return row * 1024 + col;
}

export function cellOf(key) {
    return { col: key % 1024, row: Math.floor(key / 1024) };
}

export function tileGridSize(doc, size) {
    return { cols: Math.ceil(doc.size.w / size), rows: Math.ceil(doc.size.h / size) };
}

export function countTiles(doc) {
    return doc.layers.reduce((sum, layer) => sum + (layer.kind === "tiles" ? layer.cells.size : 0), 0);
}

export function createCanvas(w, h) {
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    return canvas;
}

export function countLayers(doc, kind) {
    return doc.layers.filter((layer) => layer.kind === kind).length;
}

export function countItems(doc) {
    return doc.layers.reduce((sum, layer) => sum + (layer.items ? layer.items.length : 0), 0);
}

export function findItem(doc, itemId) {
    for (const layer of doc.layers) {
        if (!layer.items) continue;
        const index = layer.items.findIndex((item) => item.id === itemId);
        if (index >= 0) return { layer, item: layer.items[index], index };
    }
    return null;
}

// ---- PNG helpers ---------------------------------------------------------

export function base64ToBytes(b64) {
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    return bytes;
}

export function pngDimensions(bytes) {
    if (!(bytes instanceof Uint8Array) || bytes.length < 33) return null;
    for (let i = 0; i < PNG_SIGNATURE.length; i += 1) {
        if (bytes[i] !== PNG_SIGNATURE[i]) return null;
    }
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const chunkLength = view.getUint32(8);
    const chunkType = String.fromCharCode(bytes[12], bytes[13], bytes[14], bytes[15]);
    if (chunkLength !== 13 || chunkType !== "IHDR") return null;
    return { w: view.getUint32(16), h: view.getUint32(20) };
}

// ---- validation ----------------------------------------------------------

function fail(message) {
    throw new ValidationError(message);
}

function isPlainObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
}

function num(value, min, max, label) {
    if (typeof value !== "number" || !Number.isFinite(value) || value < min || value > max) {
        fail(`${label}: Zahl zwischen ${min} und ${max} erwartet.`);
    }
    return value;
}

function bool(value, fallback) {
    if (value === undefined) return fallback;
    if (typeof value !== "boolean") fail("Ja/Nein-Wert erwartet.");
    return value;
}

function color(value, label) {
    if (typeof value !== "string" || !COLOR_RE.test(value)) fail(`${label}: Farbe im Format #rrggbb erwartet.`);
    return value.toLowerCase();
}

function id(value, ids) {
    if (typeof value !== "string" || !ID_RE.test(value)) fail("Ungültige Kennung in der Datei.");
    if (ids.has(value)) fail(`Kennung „${value}“ ist doppelt vergeben.`);
    ids.add(value);
    return value;
}

/**
 * Validate an untrusted parsed document. Returns a fresh normalized object
 * whose raster layers carry `pngBytes` (Uint8Array) instead of data URLs.
 * Throws ValidationError; never mutates the current document.
 *
 * `rasterSource` lets autosave pass already-binary PNG data
 * (layer.pngBytes as ArrayBuffer/Uint8Array) instead of a data URL.
 */
export function validateDocument(raw, { knownAssets, rasterSource = "dataurl" }) {
    if (!isPlainObject(raw)) fail("Die Datei enthält kein Kartenobjekt.");
    if (raw.format !== FORMAT) fail("Keine Roll-Drauf-Kartendatei (format fehlt oder falsch).");
    if (raw.version !== VERSION) fail(`Nicht unterstützte Version ${String(raw.version).slice(0, 10)}.`);

    if (!isPlainObject(raw.size)) fail("Kartengröße fehlt.");
    const w = raw.size.w;
    const h = raw.size.h;
    for (const side of [w, h]) {
        if (!Number.isInteger(side) || side < LIMITS.minSide || side > LIMITS.maxSide) {
            fail(`Kartengröße muss zwischen ${LIMITS.minSide} und ${LIMITS.maxSide} Pixeln liegen.`);
        }
    }

    const metaIn = isPlainObject(raw.meta) ? raw.meta : {};
    const meta = {
        title: cleanText(metaIn.title, LIMITS.title) || globalThis.VTTUi("Unbenannte Karte"),
        seed: Number.isInteger(metaIn.seed) ? metaIn.seed : 0,
        created: cleanText(metaIn.created, 40),
        modified: cleanText(metaIn.modified, 40),
        showTitle: bool(metaIn.showTitle, false),
    };

    const seaIn = isPlainObject(raw.sea) ? raw.sea : {};
    const sea = {
        top: seaIn.top === undefined ? "#2f5d6e" : color(seaIn.top, "Meeresfarbe"),
        bottom: seaIn.bottom === undefined ? "#7fa9a8" : color(seaIn.bottom, "Meeresfarbe"),
    };

    if (!Array.isArray(raw.layers) || raw.layers.length < 1) fail("Die Karte hat keine Ebenen.");
    if (raw.layers.length > LIMITS.layers) fail(`Höchstens ${LIMITS.layers} Ebenen erlaubt.`);

    const ids = new Set();
    let rasterCount = 0;
    let itemCount = 0;
    let tileCount = 0;
    const layers = raw.layers.map((layerIn, index) => {
        if (!isPlainObject(layerIn)) fail(`Ebene ${index + 1} ist ungültig.`);
        if (!LAYER_KINDS.includes(layerIn.kind)) fail(`Ebene ${index + 1}: unbekannte Art.`);
        const layer = {
            id: id(layerIn.id, ids),
            name: cleanText(layerIn.name, LIMITS.layerName) || `Ebene ${index + 1}`,
            kind: layerIn.kind,
            visible: bool(layerIn.visible, true),
            opacity: layerIn.opacity === undefined ? 1 : num(layerIn.opacity, 0, 1, "Deckkraft"),
            effects: { coast: false },
        };
        if (layer.kind === "raster") {
            rasterCount += 1;
            if (rasterCount > LIMITS.rasterLayers) fail(`Höchstens ${LIMITS.rasterLayers} Malebenen erlaubt.`);
            if ((rasterCount * w * h) > LIMITS.rasterArea) fail("Die Malebenen sind zusammen zu groß.");
            layer.effects.coast = isPlainObject(layerIn.effects) ? bool(layerIn.effects.coast, false) : false;
            layer.pngBytes = rasterBytes(layerIn, rasterSource, w, h);
            return layer;
        }
        if (layer.kind === "tiles") {
            const tiles = validateTiles(layerIn, knownAssets, w, h, layer.name);
            tileCount += tiles.cells.size;
            if (tileCount > LIMITS.tiles) fail(`Höchstens ${LIMITS.tiles} Kacheln pro Karte erlaubt.`);
            return Object.assign(layer, tiles);
        }
        if (!Array.isArray(layerIn.items)) fail(`Ebene „${layer.name}“: Elementliste fehlt.`);
        itemCount += layerIn.items.length;
        if (itemCount > LIMITS.items) fail(`Höchstens ${LIMITS.items} Kartenelemente erlaubt.`);
        layer.items = layerIn.items.map((itemIn) => (layer.kind === "stamps"
            ? validateStamp(itemIn, ids, knownAssets, w, h)
            : layer.kind === "paths" ? validatePath(itemIn, ids, w, h)
                : validateLabel(itemIn, ids, knownAssets, w, h)));
        return layer;
    });

    return { meta, size: { w, h }, sea, layers };
}

function rasterBytes(layerIn, source, w, h) {
    let bytes;
    if (source === "binary") {
        const data = layerIn.pngBytes;
        if (data instanceof Uint8Array) bytes = data;
        else if (data instanceof ArrayBuffer) bytes = new Uint8Array(data);
        else fail("Malebene ohne Bilddaten.");
    } else {
        const png = layerIn.png;
        if (typeof png !== "string" || !png.startsWith(PNG_PREFIX)) {
            fail("Malebenen müssen eingebettete PNG-Daten enthalten (keine externen Bilder).");
        }
        const b64 = png.slice(PNG_PREFIX.length);
        if (!/^[A-Za-z0-9+/]*={0,2}$/.test(b64)) fail("Beschädigte PNG-Daten.");
        try {
            bytes = base64ToBytes(b64);
        } catch (_error) {
            fail("Beschädigte PNG-Daten.");
        }
    }
    const dims = pngDimensions(bytes);
    if (!dims) fail("Malebene ist kein gültiges PNG.");
    if (dims.w !== w || dims.h !== h) fail(`Malebene hat ${dims.w}×${dims.h} statt ${w}×${h} Pixel.`);
    return bytes;
}

/** Tile layer: {grid: {size}, palette: [asset ids], cells: [col, row, paletteIndex, …]}. */
function validateTiles(layerIn, knownAssets, w, h, name) {
    const size = isPlainObject(layerIn.grid) ? layerIn.grid.size : undefined;
    if (!Number.isInteger(size) || size < LIMITS.tileGrid[0] || size > LIMITS.tileGrid[1]) {
        fail(`Kachelebene „${name}“: Kachelgröße muss zwischen ${LIMITS.tileGrid[0]} und ${LIMITS.tileGrid[1]} Pixeln liegen.`);
    }
    const palette = layerIn.palette;
    if (!Array.isArray(palette) || palette.length > LIMITS.tilePalette) fail(`Kachelebene „${name}“: ungültige Kachelliste.`);
    if (new Set(palette).size !== palette.length) fail(`Kachelebene „${name}“: Kachel doppelt aufgeführt.`);
    for (const asset of palette) {
        if (typeof asset !== "string" || !ASSET_RE.test(asset) || !knownAssets.has(asset)) {
            fail(`Unbekannte Kachel „${String(asset).slice(0, 60)}“ – das Paket ist nicht geladen oder passt nicht.`);
        }
    }
    const flat = layerIn.cells;
    if (!Array.isArray(flat) || flat.length % 3 !== 0 || flat.length / 3 > LIMITS.tiles) fail(`Kachelebene „${name}“: ungültige Zellen.`);
    const cols = Math.ceil(w / size);
    const rows = Math.ceil(h / size);
    const cells = new Map();
    for (let i = 0; i < flat.length; i += 3) {
        const [col, row, index] = [flat[i], flat[i + 1], flat[i + 2]];
        if (![col, row, index].every(Number.isInteger) || col < 0 || row < 0 || col >= cols || row >= rows
            || index < 0 || index >= palette.length) fail(`Kachelebene „${name}“: Zelle außerhalb der Karte oder ohne Kachel.`);
        const key = cellKey(col, row);
        if (cells.has(key)) fail(`Kachelebene „${name}“: Zelle ${col},${row} ist doppelt belegt.`);
        cells.set(key, palette[index]);
    }
    return { grid: { size }, cells };
}

function validateCrop(value, asset, knownAssets) {
    const source = typeof knownAssets.get === "function" ? knownAssets.get(asset) : null;
    if (!source || !isPlainObject(value)) fail("Ausschnitt ohne bekannte Bildmaße.");
    for (const key of ["x", "y", "w", "h"]) if (!Number.isInteger(value[key])) fail("Ausschnitt muss ganzzahlige Bildpixel verwenden.");
    const { x, y, w, h } = value;
    if (x < 0 || y < 0 || w < 1 || h < 1 || x + w > source.w || y + h > source.h) fail("Ausschnitt liegt außerhalb des Quellbilds.");
    return { x, y, w, h };
}

function validateStamp(itemIn, ids, knownAssets, w, h) {
    if (!isPlainObject(itemIn)) fail("Ungültiges Symbol.");
    if (typeof itemIn.asset !== "string" || !ASSET_RE.test(itemIn.asset)) fail("Ungültige Symbolkennung.");
    if (!knownAssets.has(itemIn.asset)) {
        fail(`Unbekanntes Symbol „${itemIn.asset}“ – das Symbolpaket ist nicht geladen oder passt nicht.`);
    }
    return {
        id: id(itemIn.id, ids),
        asset: itemIn.asset,
        ...(itemIn.crop === undefined || itemIn.crop === null ? {} : { crop: validateCrop(itemIn.crop, itemIn.asset, knownAssets) }),
        x: num(itemIn.x, -w, 2 * w, "Position"),
        y: num(itemIn.y, -h, 2 * h, "Position"),
        size: num(itemIn.size, LIMITS.stampSize[0], LIMITS.stampSize[1], "Symbolgröße"),
        rot: itemIn.rot === undefined ? 0 : num(itemIn.rot, -LIMITS.rotation, LIMITS.rotation, "Drehung"),
        flip: bool(itemIn.flip, false),
    };
}

function validatePath(itemIn, ids, w, h) {
    if (!isPlainObject(itemIn) || !Array.isArray(itemIn.points)
        || itemIn.points.length < 2 || itemIn.points.length > LIMITS.pathPoints) fail("Ungültiger Weg oder Fluss.");
    if (itemIn.material !== "road" && itemIn.material !== "river") fail("Unbekanntes Wegmaterial.");
    const points = itemIn.points.map((point) => {
        if (!isPlainObject(point)) fail("Ungültiger Wegpunkt.");
        return { x: num(point.x, -2 * w, 2 * w, "Wegpunkt"), y: num(point.y, -2 * h, 2 * h, "Wegpunkt") };
    });
    if (points[0].x !== 0 || points[0].y !== 0) fail("Der erste Wegpunkt muss bei 0,0 liegen.");
    return {
        id: id(itemIn.id, ids),
        x: num(itemIn.x, -w, 2 * w, "Position"),
        y: num(itemIn.y, -h, 2 * h, "Position"),
        material: itemIn.material,
        width: num(itemIn.width, 2, 80, "Wegbreite"),
        points,
    };
}

function validateLabel(itemIn, ids, knownAssets, w, h) {
    if (!isPlainObject(itemIn)) fail("Ungültige Beschriftung.");
    const text = cleanText(itemIn.text, LIMITS.labelText);
    if (!text) fail("Beschriftung ohne Text.");
    if (!Object.hasOwn(LABEL_STYLES, itemIn.style)) fail("Unbekannter Beschriftungsstil.");
    let place = null;
    if (itemIn.place !== undefined && itemIn.place !== null) {
        if (!isPlainObject(itemIn.place) || !Object.hasOwn(PLACE_KINDS, itemIn.place.kind)) fail("Unbekannte Ortsart.");
        if (itemIn.place.lore !== undefined && typeof itemIn.place.lore !== "string") fail("Ortsbeschreibung muss Text sein.");
        place = { kind: itemIn.place.kind, lore: cleanText(itemIn.place.lore, LIMITS.lore) };
    }
    let symbol = null;
    if (itemIn.symbol !== undefined && itemIn.symbol !== null) {
        if (!place || !isPlainObject(itemIn.symbol) || typeof itemIn.symbol.asset !== "string"
            || !ASSET_RE.test(itemIn.symbol.asset) || !knownAssets.has(itemIn.symbol.asset)) {
            fail("Ungültiges Ortssymbol.");
        }
        symbol = { asset: itemIn.symbol.asset, size: num(itemIn.symbol.size, 16, 320, "Ortssymbolgröße") };
    }
    return {
        id: id(itemIn.id, ids),
        x: num(itemIn.x, -w, 2 * w, "Position"),
        y: num(itemIn.y, -h, 2 * h, "Position"),
        text,
        style: itemIn.style,
        size: num(itemIn.size, LIMITS.labelSize[0], LIMITS.labelSize[1], "Schriftgröße"),
        rot: itemIn.rot === undefined ? 0 : num(itemIn.rot, -LIMITS.rotation, LIMITS.rotation, "Drehung"),
        color: itemIn.color === undefined ? "#3b2a1a" : color(itemIn.color, "Schriftfarbe"),
        pin: bool(itemIn.pin, false),
        place,
        symbol,
    };
}

/** Decode validated PNG bytes into runtime canvases. Throws on decode failure. */
export async function materialize(validated) {
    const layers = [];
    for (const layerIn of validated.layers) {
        const layer = { ...layerIn, canvas: null, rev: 0 };
        if (layer.kind === "raster") {
            let bitmap;
            try {
                bitmap = await createImageBitmap(new Blob([layerIn.pngBytes], { type: "image/png" }));
            } catch (_error) {
                throw new ValidationError(`Malebene „${layer.name}“ ließ sich nicht dekodieren.`);
            }
            layer.canvas = createCanvas(validated.size.w, validated.size.h);
            layer.canvas.getContext("2d").drawImage(bitmap, 0, 0);
            if (bitmap.close) bitmap.close();
            delete layer.pngBytes;
        }
        layers.push(layer);
    }
    return { meta: validated.meta, size: validated.size, sea: validated.sea, layers };
}

// ---- serialization -------------------------------------------------------

function canvasToBlob(canvas) {
    return new Promise((resolve, reject) => {
        canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error(globalThis.VTTUi("PNG-Kodierung fehlgeschlagen")))), "image/png");
    });
}

// layer.canvas → {rev, bytes}; rev is the layer revision the bytes were captured at.
const encodeCache = new WeakMap();

/**
 * Synchronous raster snapshot: cached bytes when the revision is unchanged,
 * otherwise a pixel copy taken now, so later edits cannot leak into an
 * encoding that is still in flight.
 */
function snapshotRaster(layer) {
    const rev = layer.rev;
    const cached = encodeCache.get(layer.canvas);
    if (cached && cached.rev === rev) return { key: layer.canvas, rev, bytes: cached.bytes, copy: null };
    const copy = createCanvas(layer.canvas.width, layer.canvas.height);
    copy.getContext("2d").drawImage(layer.canvas, 0, 0);
    return { key: layer.canvas, rev, bytes: null, copy };
}

/** PNG bytes of a raster layer as it is at call time (later edits never leak in). */
export function layerPngBytes(layer) {
    return rasterBytesOf(snapshotRaster(layer));
}

async function rasterBytesOf(snap) {
    if (snap.bytes) return snap.bytes;
    try {
        const blob = await canvasToBlob(snap.copy);
        const bytes = new Uint8Array(await blob.arrayBuffer());
        const current = encodeCache.get(snap.key);
        if (!current || current.rev < snap.rev) encodeCache.set(snap.key, { rev: snap.rev, bytes });
        return bytes;
    } finally {
        snap.copy.width = 0;
        snap.copy.height = 0;
    }
}

function bytesToBase64(bytes) {
    let binary = "";
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
        binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    return btoa(binary);
}

function plainItem(item) {
    if ("points" in item) return { id: item.id, x: round(item.x), y: round(item.y), material: item.material,
        width: round(item.width), points: item.points.map((p) => ({ x: round(p.x), y: round(p.y) })) };
    if ("asset" in item) {
        return { id: item.id, asset: item.asset, x: round(item.x), y: round(item.y), size: round(item.size), rot: round(item.rot), flip: item.flip, ...(item.crop ? { crop: { ...item.crop } } : {}) };
    }
    return {
        id: item.id, x: round(item.x), y: round(item.y), text: item.text, style: item.style, size: round(item.size),
        rot: round(item.rot), color: item.color, pin: item.pin, place: item.place ? { ...item.place } : null,
        ...(item.symbol ? { symbol: { ...item.symbol } } : {}),
    };
}

/** Deterministic tile encoding: palette in first-use order of row-major cells. */
function plainTiles(layer) {
    const palette = [];
    const index = new Map();
    const cells = [];
    for (const key of [...layer.cells.keys()].sort((a, b) => a - b)) {
        const asset = layer.cells.get(key);
        if (!index.has(asset)) {
            index.set(asset, palette.length);
            palette.push(asset);
        }
        const { col, row } = cellOf(key);
        cells.push(col, row, index.get(asset));
    }
    return { grid: { size: layer.grid.size }, palette, cells };
}

function round(value) {
    return Math.round(value * 100) / 100;
}

/**
 * Serialize. mode "file" embeds data URLs; mode "binary" keeps PNG bytes (autosave).
 * Everything (meta, layers, items, raster pixels) is captured synchronously
 * when serialize() is called; only PNG encoding happens asynchronously.
 */
export function serialize(doc, mode = "file") {
    const meta = { ...doc.meta, modified: new Date().toISOString() };
    const size = { ...doc.size };
    const sea = { ...doc.sea };
    const layers = doc.layers.map((layer) => {
        const out = { id: layer.id, name: layer.name, kind: layer.kind, visible: layer.visible, opacity: layer.opacity };
        if (layer.kind === "raster") {
            out.effects = { coast: !!layer.effects.coast };
            out.snap = snapshotRaster(layer);
        } else if (layer.kind === "tiles") {
            Object.assign(out, plainTiles(layer));
        } else {
            out.items = layer.items.map(plainItem);
        }
        return out;
    });
    return (async () => {
        for (const out of layers) {
            if (!out.snap) continue;
            const bytes = await rasterBytesOf(out.snap);
            delete out.snap;
            if (mode === "binary") out.pngBytes = bytes;
            else out.png = PNG_PREFIX + bytesToBase64(bytes);
        }
        return { format: FORMAT, version: VERSION, meta, size, sea, layers };
    })();
}
