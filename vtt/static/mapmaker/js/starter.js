// Seeded starter map „Die Silbermark“ and the empty map. Everything produced
// here is an ordinary editable document (raster layers + stamp/label items).

import { createCanvas } from "./document.js";
import { materialTile, paintPath } from "./brush.js";

export const STARTER_SEED = 1337;
const W = 2400;
const H = 1600;
const Q = 4; // generator grid works at quarter resolution
const GW = W / Q;
const GH = H / Q;

function mulberry(seed) {
    let t = seed >>> 0;
    return () => {
        t += 0x6d2b79f5;
        let r = Math.imul(t ^ (t >>> 15), 1 | t);
        r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
        return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
}

function makeNoise(seed) {
    const rand = mulberry(seed);
    const size = 256;
    const values = new Float32Array(size * size);
    for (let i = 0; i < values.length; i += 1) values[i] = rand();
    const at = (x, y) => values[((y & 255) << 8) | (x & 255)];
    const smooth = (t) => t * t * (3 - 2 * t);
    const value = (x, y) => {
        const xi = Math.floor(x);
        const yi = Math.floor(y);
        const tx = smooth(x - xi);
        const ty = smooth(y - yi);
        const a = at(xi, yi) + (at(xi + 1, yi) - at(xi, yi)) * tx;
        const b = at(xi, yi + 1) + (at(xi + 1, yi + 1) - at(xi, yi + 1)) * tx;
        return a + (b - a) * ty;
    };
    return (x, y, octaves = 5) => {
        let sum = 0;
        let amp = 0.5;
        let freq = 1;
        let norm = 0;
        for (let o = 0; o < octaves; o += 1) {
            sum += value(x * freq, y * freq) * amp;
            norm += amp;
            amp *= 0.5;
            freq *= 2.03;
        }
        return sum / norm;
    };
}

const smoothstep = (a, b, v) => {
    const t = Math.min(1, Math.max(0, (v - a) / (b - a)));
    return t * t * (3 - 2 * t);
};

const bump = (nx, ny, cx, cy, r) => Math.max(0, 1 - Math.hypot(nx - cx, ny - cy) / r);

function segDist(px, py, ax, ay, bx, by) {
    const dx = bx - ax;
    const dy = by - ay;
    const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)));
    return Math.hypot(px - (ax + dx * t), py - (ay + dy * t));
}

/** Build a quarter-res field into a full-res alpha mask canvas. */
function maskFromField(field) {
    const small = createCanvas(GW, GH);
    const ctx = small.getContext("2d");
    const image = ctx.createImageData(GW, GH);
    for (let i = 0; i < field.length; i += 1) {
        image.data[i * 4] = 255;
        image.data[i * 4 + 1] = 255;
        image.data[i * 4 + 2] = 255;
        image.data[i * 4 + 3] = Math.round(field[i] * 255);
    }
    ctx.putImageData(image, 0, 0);
    const full = createCanvas(W, H);
    const fctx = full.getContext("2d");
    fctx.imageSmoothingEnabled = true;
    fctx.imageSmoothingQuality = "high";
    fctx.drawImage(small, 0, 0, W, H);
    return full;
}

function fillMaterial(target, materialId, mask, alpha = 1) {
    const temp = createCanvas(W, H);
    const ctx = temp.getContext("2d");
    ctx.fillStyle = ctx.createPattern(materialTile(materialId), "repeat");
    ctx.fillRect(0, 0, W, H);
    ctx.globalCompositeOperation = "destination-in";
    ctx.drawImage(mask, 0, 0);
    const tctx = target.getContext("2d");
    tctx.globalAlpha = alpha;
    tctx.drawImage(temp, 0, 0);
    tctx.globalAlpha = 1;
}

function rasterLayer(id, name, coast) {
    return { id, name, kind: "raster", visible: true, opacity: 1, effects: { coast }, canvas: createCanvas(W, H), rev: 0 };
}

function baseLayers() {
    return [
        rasterLayer("land", "Land", true),
        rasterLayer("terrain", "Gelände", false),
        rasterLayer("rivers", "Flüsse & Wege", false),
        { id: "symbols", name: "Symbole", kind: "stamps", visible: true, opacity: 1, effects: { coast: false }, items: [], canvas: null, rev: 0 },
        { id: "labels", name: "Beschriftung", kind: "labels", visible: true, opacity: 1, effects: { coast: false }, items: [], canvas: null, rev: 0 },
    ];
}

function meta(title, seed) {
    const now = new Date().toISOString();
    return { title, seed, created: now, modified: now };
}

export function createEmptyMap() {
    return { meta: meta("Neue Karte", 0), size: { w: W, h: H }, sea: { top: "#2f5d6e", bottom: "#7fa9a8" }, layers: baseLayers() };
}

/**
 * pick(kenneyId, builtinId) chooses the curated stamp when the pack is
 * loaded and a simple built-in otherwise.
 */
export function createStarterMap(palette, engine) {
    const has = (id) => palette.stamps.has(id);
    const pick = (id, fallback) => (has(id) ? id : fallback);
    const noise = makeNoise(STARTER_SEED);
    const noise2 = makeNoise(STARTER_SEED + 11);
    const rand = mulberry(STARTER_SEED + 99);

    // ---- landmass ----
    const height = new Float32Array(GW * GH);
    const land = new Float32Array(GW * GH);
    const ridge = [0.585, 0.2, 0.7, 0.58];
    for (let y = 0; y < GH; y += 1) {
        for (let x = 0; x < GW; x += 1) {
            const nx = x / GW;
            const ny = y / GH;
            const d = Math.hypot((nx - 0.47) / 0.4, (ny - 0.53) / 0.41);
            let base = 1 - d;
            base = Math.max(base, bump(nx, ny, 0.86, 0.76, 0.085) * 0.95 - 0.05);
            base = Math.max(base, bump(nx, ny, 0.11, 0.19, 0.05) * 0.9 - 0.08);
            let hgt = base * 0.95 + (noise(nx * 6, ny * 4) - 0.5) * 0.62;
            hgt -= bump(nx, ny, 0.405, 0.405, 0.05) * 0.95; // Nebelsee
            const i = y * GW + x;
            height[i] = hgt;
            land[i] = smoothstep(0.17, 0.2, hgt);
        }
    }
    const isLand = (px, py, min = 0.9) => {
        const gx = Math.round(px / Q);
        const gy = Math.round(py / Q);
        if (gx < 0 || gy < 0 || gx >= GW || gy >= GH) return false;
        return land[gy * GW + gx] >= min;
    };
    const nearestLand = (px, py) => {
        if (isLand(px, py)) return [px, py];
        for (let r = 8; r < 400; r += 8) {
            for (let a = 0; a < 16; a += 1) {
                const x = px + Math.cos((a / 16) * Math.PI * 2) * r;
                const y = py + Math.sin((a / 16) * Math.PI * 2) * r;
                if (isLand(x, y)) return [x, y];
            }
        }
        return [px, py];
    };

    const layers = baseLayers();
    const [landLayer, terrainLayer, riverLayer, symbolLayer, labelLayer] = layers;
    const landMask = maskFromField(land);
    fillMaterial(landLayer.canvas, "land", landMask);

    // ---- terrain zones (clipped to land afterwards) ----
    const zone = (fn) => {
        const field = new Float32Array(GW * GH);
        for (let y = 0; y < GH; y += 1) {
            for (let x = 0; x < GW; x += 1) field[y * GW + x] = fn(x / GW, y / GH) * land[y * GW + x];
        }
        return field;
    };
    const ridgeDist = (nx, ny) => segDist(nx, ny, ridge[0], ridge[1], ridge[2], ridge[3]);
    const meadow = zone((nx, ny) => smoothstep(0.48, 0.56, noise2(nx * 5, ny * 5)));
    const forestField = zone((nx, ny) => smoothstep(0.55, 0.62, noise2(nx * 7 + 3, ny * 7) * 0.55 + bump(nx, ny, 0.27, 0.64, 0.15) * 0.75));
    const rock = zone((nx, ny) => smoothstep(0.075, 0.035, ridgeDist(nx, ny) + (noise(nx * 20, ny * 20) - 0.5) * 0.03));
    const snow = zone((nx, ny) => smoothstep(0.03, 0.012, ridgeDist(nx, ny)) * smoothstep(0.5, 0.3, ny));
    const steppe = zone((nx, ny) => smoothstep(0.35, 0.6, bump(nx, ny, 0.55, 0.76, 0.15) + (noise2(nx * 9, ny * 9) - 0.5) * 0.4));
    const desert = zone((nx, ny) => smoothstep(0.45, 0.7, bump(nx, ny, 0.57, 0.79, 0.08) + (noise(nx * 12, ny * 12) - 0.5) * 0.3));
    const swamp = zone((nx, ny) => smoothstep(0.3, 0.55, bump(nx, ny, 0.43, 0.5, 0.06) + (noise(nx * 18, ny * 18) - 0.5) * 0.3));
    fillMaterial(terrainLayer.canvas, "meadow", maskFromField(meadow), 0.8);
    fillMaterial(terrainLayer.canvas, "steppe", maskFromField(steppe), 0.9);
    fillMaterial(terrainLayer.canvas, "desert", maskFromField(desert), 0.95);
    fillMaterial(terrainLayer.canvas, "forest", maskFromField(forestField), 0.92);
    fillMaterial(terrainLayer.canvas, "swamp", maskFromField(swamp), 0.85);
    fillMaterial(terrainLayer.canvas, "rock", maskFromField(rock), 0.9);
    fillMaterial(terrainLayer.canvas, "snow", maskFromField(snow), 0.95);
    const tctx = terrainLayer.canvas.getContext("2d");
    tctx.globalCompositeOperation = "destination-in";
    tctx.drawImage(landMask, 0, 0);
    tctx.globalCompositeOperation = "source-over";

    // ---- river: from the ridge westwards to the coast ----
    const source = [0.6 * W, 0.37 * H];
    let mouth = [0.3 * W, 0.47 * H];
    while (isLand(mouth[0], mouth[1], 0.5) && mouth[0] > 40) mouth = [mouth[0] - 8, mouth[1] + 1.5];
    const meander = (a, b, depth, out) => {
        if (depth === 0) {
            out.push(b);
            return;
        }
        const mx = (a[0] + b[0]) / 2;
        const my = (a[1] + b[1]) / 2;
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const nx = -(b[1] - a[1]) / (len || 1);
        const ny = (b[0] - a[0]) / (len || 1);
        const off = (rand() - 0.5) * len * 0.35;
        const m = [mx + nx * off, my + ny * off];
        meander(a, m, depth - 1, out);
        meander(m, b, depth - 1, out);
    };
    const riverPts = [source];
    meander(source, mouth, 6, riverPts);
    const riverStroke = riverPts.map(([x, y], i) => [x, y, 0.25 + 0.75 * (i / (riverPts.length - 1))]);
    paintPath(engine, riverLayer, riverStroke, { size: 15, opacity: 0.95, softness: 25, material: "river", erase: false, pressureEnabled: true });
    // a short brook out of the lake towards the south coast
    const brookStart = [0.41 * W, 0.45 * H];
    let brookEnd = [0.42 * W, 0.6 * H];
    while (isLand(brookEnd[0], brookEnd[1], 0.5) && brookEnd[1] < H - 40) brookEnd = [brookEnd[0] - 2, brookEnd[1] + 8];
    const brookPts = [brookStart];
    meander(brookStart, brookEnd, 5, brookPts);
    paintPath(engine, riverLayer, brookPts.map(([x, y], i) => [x, y, 0.3 + 0.6 * (i / (brookPts.length - 1))]),
        { size: 11, opacity: 0.9, softness: 25, material: "river", erase: false, pressureEnabled: true });

    // ---- places ----
    const riverNear = (tx, ty) => riverPts.reduce((best, p) => (Math.hypot(p[0] - tx, p[1] - ty) < Math.hypot(best[0] - tx, best[1] - ty) ? p : best));
    const hohenfurt = riverNear(0.36 * W, 0.47 * H);
    const harbor = nearestLand(riverPts[riverPts.length - 2][0] + 30, riverPts[riverPts.length - 2][1] - 50);
    const rabenfels = nearestLand(0.545 * W, 0.3 * H);
    const kesselbruck = nearestLand(0.52 * W, 0.68 * H);
    const ascheturm = nearestLand(0.79 * W, 0.4 * H);
    const abtei = nearestLand(0.395 * W, 0.335 * H);
    const glut = nearestLand(0.865 * W, 0.755 * H);

    // road network (dashed ink on the river/road layer)
    const rctx = riverLayer.canvas.getContext("2d");
    rctx.save();
    rctx.strokeStyle = "rgba(122,90,54,0.85)";
    rctx.lineWidth = 4;
    rctx.lineCap = "round";
    rctx.setLineDash([16, 11]);
    const road = (a, b, bend) => {
        rctx.beginPath();
        rctx.moveTo(a[0], a[1]);
        rctx.quadraticCurveTo((a[0] + b[0]) / 2 + bend, (a[1] + b[1]) / 2 - bend, b[0], b[1]);
        rctx.stroke();
    };
    road(hohenfurt, kesselbruck, 40);
    road(hohenfurt, rabenfels, -60);
    road(hohenfurt, harbor, 20);
    road(kesselbruck, [0.66 * W, 0.74 * H], 30);
    rctx.restore();
    riverLayer.rev += 1;

    // ---- stamps ----
    let sid = 0;
    const stamp = (asset, x, y, size, rot = 0, flip = false) => {
        sid += 1;
        symbolLayer.items.push({ id: `s${sid}`, asset, x: Math.round(x), y: Math.round(y), size: Math.round(size), rot, flip });
    };
    const mountain = pick("kenney:mountains", "builtin:mountain");
    const crags = pick("kenney:crags", "builtin:mountain");
    for (let t = 0; t <= 1.0001; t += 0.075) {
        const x = (ridge[0] + (ridge[2] - ridge[0]) * t) * W + (rand() - 0.5) * 50;
        const y = (ridge[1] + (ridge[3] - ridge[1]) * t) * H + (rand() - 0.5) * 40;
        if (!isLand(x, y)) continue;
        stamp(rand() < 0.7 ? mountain : crags, x, y, 104 + rand() * 30, 0, rand() < 0.4);
        const side = rand() < 0.5 ? -1 : 1;
        if (isLand(x + side * 70, y + 30)) stamp(mountain, x + side * 70, y + 30, 76 + rand() * 18, 0, rand() < 0.5);
    }
    if (has("kenney:rocks")) {
        stamp("kenney:rocks", ...nearestLand(0.53 * W, 0.42 * H), 64);
        stamp("kenney:rocks", ...nearestLand(0.66 * W, 0.62 * H), 60, 0, true);
    }
    const forestIds = [pick("kenney:forest", "builtin:tree"), pick("kenney:pine", "builtin:tree"), pick("kenney:tree", "builtin:tree")];
    let trees = 0;
    for (let y = 120; y < H - 120 && trees < 54; y += 64) {
        for (let x = 120; x < W - 120 && trees < 54; x += 70) {
            const jx = x + (rand() - 0.5) * 40;
            const jy = y + (rand() - 0.5) * 36;
            const gi = Math.round(jy / Q) * GW + Math.round(jx / Q);
            if (forestField[gi] > 0.7 && rock[gi] < 0.2 && isLand(jx, jy)) {
                const tooClose = [hohenfurt, kesselbruck, rabenfels, abtei].some((p) => Math.hypot(p[0] - jx, p[1] - jy) < 110);
                if (!tooClose) {
                    stamp(forestIds[Math.floor(rand() * forestIds.length)], jx, jy, 58 + rand() * 18, 0, rand() < 0.5);
                    trees += 1;
                }
            }
        }
    }
    if (has("kenney:scrub")) {
        for (let i = 0; i < 8; i += 1) {
            const x = (0.47 + rand() * 0.14) * W;
            const y = (0.7 + rand() * 0.1) * H;
            if (isLand(x, y) && Math.hypot(x - kesselbruck[0], y - kesselbruck[1]) > 110) stamp("kenney:scrub", x, y, 44 + rand() * 12, 0, rand() < 0.5);
        }
    }
    if (has("kenney:cactus")) stamp("kenney:cactus", ...nearestLand(0.585 * W, 0.8 * H), 52);
    if (has("kenney:mesa")) stamp("kenney:mesa", ...nearestLand(0.55 * W, 0.81 * H), 84);

    stamp(pick("kenney:citadel", "builtin:castle"), hohenfurt[0], hohenfurt[1] - 30, 116);
    if (has("kenney:harbor")) stamp("kenney:harbor", harbor[0] - 26, harbor[1] + 10, 80);
    stamp(pick("kenney:lighthouse", "builtin:house"), harbor[0] + 32, harbor[1] - 26, 70);
    stamp(pick("kenney:castle", "builtin:castle"), rabenfels[0], rabenfels[1], 96);
    stamp(pick("kenney:town", "builtin:house"), kesselbruck[0], kesselbruck[1], 92);
    stamp(pick("kenney:tower", "builtin:castle"), ascheturm[0], ascheturm[1], 92);
    stamp(pick("kenney:ruins", "builtin:house"), abtei[0], abtei[1], 84);
    stamp(pick("kenney:volcano", "builtin:mountain"), glut[0], glut[1], 104);
    if (has("kenney:village")) {
        stamp("kenney:village", ...nearestLand(0.3 * W, 0.36 * H), 70);
        stamp("kenney:village", ...nearestLand(0.6 * W, 0.62 * H), 70);
    }
    if (has("kenney:mill")) stamp("kenney:mill", ...nearestLand(0.44 * W, 0.6 * H), 72);
    if (has("kenney:ship")) {
        stamp("kenney:ship", 0.17 * W, 0.74 * H, 96, -8);
        stamp("kenney:ship", 0.72 * W, 0.11 * H, 76, 6, true);
    }
    if (has("kenney:danger")) stamp("kenney:danger", 0.93 * W, 0.56 * H, 56);
    stamp(pick("kenney:compass", "builtin:compass"), 0.9 * W, 0.18 * H, 210);

    // ---- labels ----
    let pid = 0;
    const label = (text, x, y, style, size, extra = {}) => {
        pid += 1;
        labelLayer.items.push({
            id: `p${pid}`, x: Math.round(x), y: Math.round(y), text, style, size, rot: extra.rot || 0,
            color: extra.color || "#3b2a1a", pin: !!extra.pin, place: extra.place || null,
        });
    };
    const place = (kind, lore) => ({ place: { kind, lore } });
    label("Die Silbermark", 0.47 * W, 0.075 * H, "realm", 84);
    label("Eisenzähne", 0.69 * W, 0.37 * H, "region", 34, { rot: 66 });
    label("Grauwald", 0.25 * W, 0.6 * H, "region", 36, { rot: -6, color: "#2f3d22" });
    label("Das Graue Meer", 0.14 * W, 0.9 * H, "water", 46, { color: "#1d4654" });
    label("Nebelsee", 0.405 * W, 0.405 * H + 4, "water", 22, { color: "#1d4654" });
    const bend = riverPts[Math.round(riverPts.length * 0.3)];
    label("Silberlauf", bend[0], bend[1] - 30, "feature", 24, { rot: -8, color: "#1d4654" });
    label("Hohenfurt", hohenfurt[0], hohenfurt[1] + 52, "city", 44, place("city",
        "Die Hauptstadt der Silbermark liegt an der einzigen Furt des Silberlaufs. Wer die Brücke hält, hält das Land."));
    label("Möwenhafen", harbor[0], harbor[1] + 56, "town", 32, place("harbor",
        "Fischer, Schmuggler und Kartenzeichner teilen sich die Kaimauer. Bei Nebel läutet die Hafenglocke ohne Unterlass."));
    label("Rabenfels", rabenfels[0], rabenfels[1] + 60, "town", 34, place("castle",
        "Eine Grenzfeste am Fuß der Eisenzähne. Seit dem letzten Winter schweigen ihre Signalfeuer."));
    label("Kesselbruck", kesselbruck[0], kesselbruck[1] + 56, "town", 32, place("town",
        "Ein Marktflecken, berühmt für Kupferkessel und noch berühmter für seine Wirtshausstreitereien."));
    label("Ascheturm", ascheturm[0], ascheturm[1] + 58, "town", 30, place("landmark",
        "Der schwarze Turm eines verbannten Magiers. Nachts glimmt in seinen Fenstern ein grünes Licht."));
    label("Abtei Nebelruh", abtei[0], abtei[1] - 52, "town", 28, place("ruin",
        "Die Mönche verschwanden in einer einzigen Nacht. Ihre Bibliothek soll unter dem See weiterbrennen."));
    label("Glutinsel", glut[0], glut[1] + 66, "town", 30, place("landmark",
        "Ein rauchender Kegel im Grauen Meer. Seeleute opfern dem Berg einen Becher Rum, bevor sie vorbeisegeln."));

    for (const layer of layers) layer.rev += 1;
    return { meta: meta("Die Silbermark", STARTER_SEED), size: { w: W, h: H }, sea: { top: "#2f5d6e", bottom: "#7fa9a8" }, layers };
}
