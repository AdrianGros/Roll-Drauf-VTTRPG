// GIMP-style brush engine: dabs with size/softness are accumulated into a
// stroke mask at full strength, and the mask is composited onto the layer
// once with the chosen opacity (no build-up where a stroke overlaps itself).

import { createCanvas } from "./document.js";

export const MATERIALS = [
    { id: "land", name: "Land", base: "#e6d5a8", ink: "#b89f6c", motif: "speckle" },
    { id: "meadow", name: "Wiese", base: "#c9cd8c", ink: "#8f9a55", motif: "ticks" },
    { id: "forest", name: "Wald", base: "#8ea566", ink: "#566f37", motif: "dots" },
    { id: "steppe", name: "Steppe", base: "#d9c381", ink: "#a8914f", motif: "speckle" },
    { id: "desert", name: "Wüste", base: "#ecd59c", ink: "#c6a663", motif: "dunes" },
    { id: "snow", name: "Schnee", base: "#f6f3ec", ink: "#c9d6dc", motif: "speckle" },
    { id: "swamp", name: "Sumpf", base: "#97a373", ink: "#5c6b45", motif: "reeds" },
    { id: "rock", name: "Fels", base: "#b5aa94", ink: "#827762", motif: "hatch" },
    { id: "ash", name: "Asche", base: "#746e6a", ink: "#4d4948", motif: "speckle" },
    { id: "basalt", name: "Basalt", base: "#494646", ink: "#27282a", motif: "hatch" },
    { id: "lava", name: "Lava", base: "#a43f24", ink: "#e07c31", motif: "waves" },
    { id: "shallow", name: "Flachwasser", base: "#9cc8c1", ink: "#6fa39c", motif: "waves" },
    { id: "river", name: "Fluss", base: "#5d93a0", ink: "#5d93a0", motif: "flat" },
    { id: "road", name: "Weg", base: "#8a6a44", ink: "#8a6a44", motif: "flat" },
];

export const SPACING = 0.12;

function rng(seed) {
    let t = seed >>> 0;
    return () => {
        t += 0x6d2b79f5;
        let r = Math.imul(t ^ (t >>> 15), 1 | t);
        r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
        return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
}

const tileCache = new Map();

/** Register already decoded, local CC0 photographic brush materials. */
export function registerMaterialTextures(entries) {
    for (const entry of entries) {
        if (!MATERIALS.some((material) => material.id === entry.id)) {
            MATERIALS.push({ id: entry.id, name: entry.name });
        }
        tileCache.set(entry.id, entry.image);
    }
}


export function materialTile(materialId) {
    if (tileCache.has(materialId)) return tileCache.get(materialId);
    const material = MATERIALS.find((m) => m.id === materialId) || MATERIALS[0];
    const size = 96;
    const tile = createCanvas(size, size);
    const ctx = tile.getContext("2d");
    const rand = rng(materialId.length * 7919 + material.base.charCodeAt(2));
    ctx.fillStyle = material.base;
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = material.ink;
    ctx.strokeStyle = material.ink;
    ctx.lineCap = "round";
    if (material.motif !== "flat") {
        // subtle mottling for every textured material
        for (let i = 0; i < 70; i += 1) {
            ctx.globalAlpha = 0.05 + rand() * 0.08;
            ctx.beginPath();
            ctx.arc(rand() * size, rand() * size, 2 + rand() * 7, 0, Math.PI * 2);
            ctx.fill();
        }
    }
    ctx.globalAlpha = 0.5;
    ctx.lineWidth = 1.3;
    const scatter = (count, draw) => {
        for (let i = 0; i < count; i += 1) {
            const x = rand() * size;
            const y = rand() * size;
            // draw wrapped copies so the tile repeats seamlessly
            for (const dx of [-size, 0, size]) for (const dy of [-size, 0, size]) draw(x + dx, y + dy);
        }
    };
    if (material.motif === "speckle") {
        scatter(26, (x, y) => ctx.fillRect(x, y, 1.4, 1.4));
    } else if (material.motif === "ticks") {
        scatter(22, (x, y) => {
            ctx.beginPath();
            ctx.moveTo(x, y);
            ctx.lineTo(x - 1.5, y - 4);
            ctx.moveTo(x + 2, y);
            ctx.lineTo(x + 3, y - 4);
            ctx.stroke();
        });
    } else if (material.motif === "dots") {
        ctx.globalAlpha = 0.45;
        scatter(16, (x, y) => {
            ctx.beginPath();
            ctx.arc(x, y, 3.2, 0, Math.PI * 2);
            ctx.fill();
        });
    } else if (material.motif === "dunes") {
        scatter(9, (x, y) => {
            ctx.beginPath();
            ctx.arc(x, y + 6, 8, Math.PI * 1.15, Math.PI * 1.85);
            ctx.stroke();
        });
    } else if (material.motif === "reeds") {
        scatter(18, (x, y) => {
            ctx.beginPath();
            ctx.moveTo(x - 4, y);
            ctx.lineTo(x + 4, y);
            ctx.moveTo(x, y);
            ctx.lineTo(x, y - 4);
            ctx.stroke();
        });
    } else if (material.motif === "hatch") {
        ctx.globalAlpha = 0.28;
        for (let i = -size; i < size * 2; i += 9) {
            ctx.beginPath();
            ctx.moveTo(i, 0);
            ctx.lineTo(i + size, size);
            ctx.stroke();
        }
    } else if (material.motif === "waves") {
        scatter(10, (x, y) => {
            ctx.beginPath();
            ctx.moveTo(x - 6, y);
            ctx.quadraticCurveTo(x - 3, y - 3, x, y);
            ctx.quadraticCurveTo(x + 3, y + 3, x + 6, y);
            ctx.stroke();
        });
    }
    ctx.globalAlpha = 1;
    tileCache.set(materialId, tile);
    return tile;
}

const tipCache = new Map();
const customTiles = new Map();
let imageSequence = 0;

/** One explicitly selected local catalog image, bounded independently of sheet size. */
export function imageBrush(image, crop, label) {
    const area = crop || { x: 0, y: 0, w: image.width, h: image.height };
    const scale = Math.min(1, 256 / Math.max(area.w, area.h));
    const canvas = createCanvas(Math.max(1, Math.round(area.w * scale)), Math.max(1, Math.round(area.h * scale)));
    canvas.getContext('2d').drawImage(image, area.x, area.y, area.w, area.h, 0, 0, canvas.width, canvas.height);
    return Object.freeze({ canvas, label, id: ++imageSequence });
}

/** Material definitions stay immutable; a gesture captures its own optional tint. */
export function brushMaterial(settings) {
    const source = materialTile(settings.material);
    const amount = Math.max(0, Math.min(1, settings.texture ?? 1));
    const color = settings.colorEnabled && /^#[0-9a-f]{6}$/i.test(settings.color || '') ? settings.color : null;
    if (!color && amount === 1) return source;
    const key = `${settings.material}|${color}|${amount}`;
    if (customTiles.has(key)) return customTiles.get(key);
    const tile = createCanvas(96, 96), ctx = tile.getContext('2d');
    ctx.drawImage(source, 0, 0, 96, 96);
    const data = ctx.getImageData(0, 0, 96, 96), pixels = data.data, mean = [0, 0, 0];
    for (let i = 0; i < pixels.length; i += 4) for (let c = 0; c < 3; c++) mean[c] += pixels[i + c] / (pixels.length / 4);
    const rgb = color && [1, 3, 5].map(i => parseInt(color.slice(i, i + 2), 16));
    const brightness = mean.reduce((a, b) => a + b, 0) / 3;
    for (let i = 0; i < pixels.length; i += 4) {
        const shade = 1 + amount * ((pixels[i] + pixels[i + 1] + pixels[i + 2]) / 3 - brightness) / 255;
        for (let c = 0; c < 3; c++) pixels[i + c] = rgb ? rgb[c] * shade : mean[c] + (pixels[i + c] - mean[c]) * amount;
    }
    ctx.putImageData(data, 0, 0);
    if (customTiles.size >= 32) customTiles.delete(customTiles.keys().next().value);
    customTiles.set(key, tile);
    return tile;
}

/** White alpha tip of the given radius; softness 0 = hard edge, 100 = fully feathered. */
export function brushTip(radius, softness, shape = 'round') {
    const r = Math.max(0.5, Math.round(radius * 2) / 2);
    const soft = Math.round(softness);
    const key = `${r}|${soft}|${shape}`;
    if (tipCache.has(key)) return tipCache.get(key);
    const dim = Math.ceil(r * 2) + 2;
    const tip = createCanvas(dim, dim);
    const ctx = tip.getContext("2d");
    const c = dim / 2;
    const hardness = 1 - soft / 100;
    if (shape === 'square' || shape === 'diamond') {
        const data = ctx.createImageData(dim, dim);
        for (let y = 0; y < dim; y++) for (let x = 0; x < dim; x++) {
            const dx = Math.abs(x + .5 - c) / r, dy = Math.abs(y + .5 - c) / r;
            const distance = shape === 'square' ? Math.max(dx, dy) : dx + dy;
            const alpha = distance >= 1 ? 0 : distance <= hardness ? 1 : (1 - distance) / Math.max(.001, 1 - hardness);
            const i = (y * dim + x) * 4;
            data.data[i] = data.data[i + 1] = data.data[i + 2] = 255; data.data[i + 3] = Math.round(255 * alpha);
        }
        ctx.putImageData(data, 0, 0);
    } else if (hardness >= 0.99) {
        ctx.fillStyle = "#fff";
        ctx.beginPath();
        ctx.arc(c, c, r, 0, Math.PI * 2);
        ctx.fill();
    } else {
        const gradient = ctx.createRadialGradient(c, c, 0, c, c, r);
        gradient.addColorStop(0, "rgba(255,255,255,1)");
        gradient.addColorStop(Math.max(0, hardness * 0.98), "rgba(255,255,255,1)");
        gradient.addColorStop(1, "rgba(255,255,255,0)");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, dim, dim);
    }
    if (tipCache.size > 64) tipCache.delete(tipCache.keys().next().value);
    const entry = { canvas: tip, offset: c };
    tipCache.set(key, entry);
    return entry;
}

export function rectUnion(a, b) {
    if (!a) return b ? { ...b } : null;
    if (!b) return { ...a };
    const x = Math.min(a.x, b.x);
    const y = Math.min(a.y, b.y);
    return { x, y, w: Math.max(a.x + a.w, b.x + b.w) - x, h: Math.max(a.y + a.h, b.y + b.h) - y };
}

export function rectClamp(rect, w, h) {
    if (!rect) return null;
    const x = Math.max(0, Math.floor(rect.x));
    const y = Math.max(0, Math.floor(rect.y));
    const x2 = Math.min(w, Math.ceil(rect.x + rect.w));
    const y2 = Math.min(h, Math.ceil(rect.y + rect.h));
    if (x2 <= x || y2 <= y) return null;
    return { x, y, w: x2 - x, h: y2 - y };
}

/**
 * One reusable stroke engine per document size. Scratch canvases are
 * allocated once; a stroke copies the layer once at pointerdown (base),
 * accumulates dabs in `mask`, and re-composites only dirty regions.
 */
export class StrokeEngine {
    constructor(w, h) {
        this.w = w;
        this.h = h;
        this.base = createCanvas(w, h);
        this.mask = createCanvas(w, h);
        this.work = createCanvas(w, h);
        this.active = null;
    }

    begin(layer, settings) {
        const baseCtx = this.base.getContext("2d");
        baseCtx.clearRect(0, 0, this.w, this.h);
        baseCtx.drawImage(layer.canvas, 0, 0);
        this.mask.getContext("2d").clearRect(0, 0, this.w, this.h);
        const frozen = { ...settings };
        if (!frozen.erase && !frozen.image) frozen.materialCanvas = brushMaterial(frozen);
        this.active = { layer, settings: frozen, last: null, carry: 0, total: null, pending: null };
    }

    /** Add a pointer sample; returns nothing, dirty region is collected for flush(). */
    addPoint(x, y, pressure) {
        const a = this.active;
        if (!a) return;
        const s = a.settings;
        const usePressure = s.pressureEnabled && pressure !== null;
        const p = usePressure ? Math.min(1, Math.max(0.05, pressure)) : 1;
        const radius = Math.max(0.5, (s.size / 2) * (usePressure ? 0.25 + 0.75 * p : 1));
        const alpha = usePressure ? 0.35 + 0.65 * p : 1;
        if (!a.last) {
            this.dab(x, y, radius, alpha);
            a.last = { x, y };
            return;
        }
        const dx = x - a.last.x;
        const dy = y - a.last.y;
        const dist = Math.hypot(dx, dy);
        const step = Math.max(1, radius * 2 * SPACING);
        let travelled = step - a.carry;
        while (travelled <= dist) {
            const t = travelled / dist;
            this.dab(a.last.x + dx * t, a.last.y + dy * t, radius, alpha);
            travelled += step;
        }
        a.carry = dist - (travelled - step);
        a.last = { x, y };
    }

    dab(x, y, radius, alpha) {
        const a = this.active;
        let tip = brushTip(radius, a.settings.softness, a.settings.shape);
        if (a.settings.image && !a.settings.erase) {
            const source = a.settings.image;
            const key = `image|${source.id}|${radius}|${a.settings.softness}`;
            if (!tipCache.has(key)) {
                const canvas = createCanvas(tip.canvas.width, tip.canvas.height), c = canvas.width / 2;
                const ctx = canvas.getContext('2d'), scale = radius * 2 / Math.max(source.canvas.width, source.canvas.height);
                const w = source.canvas.width * scale, h = source.canvas.height * scale;
                ctx.drawImage(source.canvas, c - w / 2, c - h / 2, w, h);
                ctx.globalCompositeOperation = 'destination-in';ctx.drawImage(tip.canvas, 0, 0);
                if (tipCache.size >= 64) tipCache.delete(tipCache.keys().next().value);
                tipCache.set(key, { canvas, offset: c });
            }
            tip = tipCache.get(key);
        }
        const ctx = this.mask.getContext("2d");
        ctx.globalAlpha = alpha;
        ctx.drawImage(tip.canvas, x - tip.offset, y - tip.offset);
        ctx.globalAlpha = 1;
        const rect = { x: x - tip.offset, y: y - tip.offset, w: tip.canvas.width, h: tip.canvas.height };
        a.pending = rectUnion(a.pending, rect);
    }

    /** Apply pending dabs to the layer; returns the clamped dirty rect or null. */
    flush() {
        const a = this.active;
        if (!a || !a.pending) return null;
        const rect = rectClamp(a.pending, this.w, this.h);
        a.pending = null;
        if (!rect) return null;
        a.total = rectUnion(a.total, rect);
        const { x, y, w, h } = rect;
        const s = a.settings;
        const layerCtx = a.layer.canvas.getContext("2d");
        layerCtx.save();
        layerCtx.clearRect(x, y, w, h);
        layerCtx.drawImage(this.base, x, y, w, h, x, y, w, h);
        layerCtx.globalAlpha = s.opacity;
        if (s.erase) {
            layerCtx.globalCompositeOperation = "destination-out";
            layerCtx.drawImage(this.mask, x, y, w, h, x, y, w, h);
        } else if (s.image) {
            layerCtx.drawImage(this.mask, x, y, w, h, x, y, w, h);
        } else {
            const workCtx = this.work.getContext("2d");
            workCtx.save();
            workCtx.globalCompositeOperation = "source-over";
            workCtx.clearRect(x, y, w, h);
            workCtx.fillStyle = workCtx.createPattern(s.materialCanvas, "repeat");
            workCtx.fillRect(x, y, w, h);
            workCtx.globalCompositeOperation = "destination-in";
            workCtx.drawImage(this.mask, x, y, w, h, x, y, w, h);
            workCtx.restore();
            layerCtx.drawImage(this.work, x, y, w, h, x, y, w, h);
        }
        layerCtx.restore();
        a.layer.rev += 1;
        return rect;
    }

    /** Finish: returns {layer, rect, before, after} or null if nothing was painted. */
    end() {
        this.flush();
        const a = this.active;
        this.active = null;
        if (!a || !a.total) return null;
        const rect = rectClamp(a.total, this.w, this.h);
        if (!rect) return null;
        const before = this.base.getContext("2d").getImageData(rect.x, rect.y, rect.w, rect.h);
        const after = a.layer.canvas.getContext("2d").getImageData(rect.x, rect.y, rect.w, rect.h);
        return { layer: a.layer, rect, before, after };
    }

    /** Abort: restore the touched region from the base copy; returns the rect to repaint. */
    cancel() {
        const a = this.active;
        this.active = null;
        if (!a) return null;
        const rect = rectClamp(rectUnion(a.total, a.pending), this.w, this.h);
        if (!rect) return null;
        const layerCtx = a.layer.canvas.getContext("2d");
        layerCtx.clearRect(rect.x, rect.y, rect.w, rect.h);
        layerCtx.drawImage(this.base, rect.x, rect.y, rect.w, rect.h, rect.x, rect.y, rect.w, rect.h);
        a.layer.rev += 1;
        return rect;
    }
}

/** Paint a polyline directly (used by the starter generator). */
export function paintPath(engine, layer, points, settings) {
    engine.begin(layer, settings);
    for (const [x, y, pressure] of points) engine.addPoint(x, y, pressure ?? null);
    engine.flush();
    engine.active = null;
}
