globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Compositing: sea → layers (raster with optional coast effect, stamps,
// labels) → parchment/vignette/frame. The same routine renders the cached
// map-resolution composite (region by region) and the PNG export.

import { cellKey, cellOf, createCanvas } from "./document.js";
import { stampExtent, drawStampImage } from "./stamps.js";
import { rectClamp, rectUnion } from "./brush.js";

// Coast glow uses shadowBlur 26 (σ≈13 px); 64 px ≈ 5σ keeps region re-renders exact.
export const COAST_PAD = 64;
const PARCHMENT = "#efe2c0";

export const LABEL_FONTS = {
    realm: { weight: "700", family: "Cinzel, 'Times New Roman', serif", spacing: 0.16, upper: true },
    region: { weight: "400", family: "Cinzel, 'Times New Roman', serif", spacing: 0.22, upper: true },
    city: { weight: "400", family: "BadScript, 'Segoe Script', cursive", spacing: 0.02, upper: false },
    town: { weight: "400", family: "BadScript, 'Segoe Script', cursive", spacing: 0.02, upper: false },
    water: { weight: "italic 400", family: "Literata, Georgia, serif", spacing: 0.12, upper: false },
    feature: { weight: "italic 400", family: "Literata, Georgia, serif", spacing: 0.05, upper: false },
};

function labelFont(item) {
    const f = LABEL_FONTS[item.style] || LABEL_FONTS.town;
    return { font: `${f.weight} ${item.size}px ${f.family}`, spacing: f.spacing * item.size, upper: f.upper };
}

function labelText(item) {
    const f = LABEL_FONTS[item.style] || LABEL_FONTS.town;
    return f.upper ? item.text.toLocaleUpperCase("de-DE") : item.text;
}

const measureCanvas = createCanvas(4, 4);
const measureCtx = measureCanvas.getContext("2d");
const supportsLetterSpacing = "letterSpacing" in measureCtx;

/** Axis-aligned bounds of a label in map coordinates (incl. halo and pin). */
export function labelBounds(item) {
    const { font, spacing } = labelFont(item);
    measureCtx.font = font;
    const text = labelText(item);
    const width = measureCtx.measureText(text).width + (supportsLetterSpacing ? spacing * text.length : 0);
    const h = item.size * 1.3;
    const cx = item.x;
    const cy = item.pin || item.symbol ? item.y - item.size * 0.9 : item.y;
    const angle = (item.rot * Math.PI) / 180;
    const cos = Math.abs(Math.cos(angle));
    const sin = Math.abs(Math.sin(angle));
    const bw = width * cos + h * sin + item.size * 0.4;
    const bh = width * sin + h * cos + item.size * 0.4;
    let rect = { x: cx - bw / 2, y: cy - bh / 2, w: bw, h: bh };
    if (item.pin) rect = rectUnion(rect, { x: item.x - 12, y: item.y - 12, w: 24, h: 24 });
    if (item.symbol) rect = rectUnion(rect, { x: item.x - item.symbol.size / 2, y: item.y - item.symbol.size / 2,
        w: item.symbol.size, h: item.symbol.size });
    return rect;
}

export function stampBounds(item, palette) {
    const stamp = palette.stamps.get(item.asset);
    const ext = stamp ? stampExtent(stamp, item.size, item.crop) : { w: item.size, h: item.size };
    const angle = (item.rot * Math.PI) / 180;
    const cos = Math.abs(Math.cos(angle));
    const sin = Math.abs(Math.sin(angle));
    const w = ext.w * cos + ext.h * sin;
    const h = ext.w * sin + ext.h * cos;
    return { x: item.x - w / 2, y: item.y - h / 2, w, h };
}

export function itemBounds(item, palette) {
    return "points" in item ? pathBounds(item) : "asset" in item ? stampBounds(item, palette) : labelBounds(item);
}

export function pathBounds(item) {
    const xs = item.points.map((p) => item.x + p.x);
    const ys = item.points.map((p) => item.y + p.y);
    const pad = item.width / 2 + 5;
    return { x: Math.min(...xs) - pad, y: Math.min(...ys) - pad,
        w: Math.max(...xs) - Math.min(...xs) + pad * 2, h: Math.max(...ys) - Math.min(...ys) + pad * 2 };
}

export function pathHit(item, point, tolerance) {
    for (let i = 1; i < item.points.length; i += 1) {
        const a = item.points[i - 1];
        const b = item.points[i];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const length2 = dx * dx + dy * dy;
        const px = point.x - item.x - a.x;
        const py = point.y - item.y - a.y;
        const t = length2 ? Math.max(0, Math.min(1, (px * dx + py * dy) / length2)) : 0;
        if (Math.hypot(px - dx * t, py - dy * t) <= item.width / 2 + tolerance) return true;
    }
    return false;
}

export function drawPath(ctx, item) {
    if (item.points.length < 2) return;
    ctx.save();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(item.x + item.points[0].x, item.y + item.points[0].y);
    for (const point of item.points.slice(1)) ctx.lineTo(item.x + point.x, item.y + point.y);
    ctx.strokeStyle = item.material === "river" ? "#294d5b" : "#4d3527";
    ctx.lineWidth = item.width + (item.material === "river" ? 3 : 4);
    ctx.stroke();
    ctx.strokeStyle = item.material === "river" ? "#5d93a0" : "#ab8759";
    ctx.lineWidth = item.width;
    ctx.stroke();
    ctx.restore();
}

/** A centered realm label in the header band is the author's existing map heading. */
export function replacedTitleLabel(doc) {
    if (!doc.meta.showTitle) return null;
    const candidates = doc.layers.filter((layer) => layer.kind === "labels" && layer.visible)
        .flatMap((layer) => layer.items)
        .filter((label) => label.style === "realm" && !label.place && label.y < doc.size.h * 0.22
            && Math.abs(label.x - doc.size.w / 2) < doc.size.w * 0.25);
    return candidates.length === 1 ? candidates[0] : null;
}

function intersects(a, b) {
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}

function drawStamp(ctx, item, palette) {
    const stamp = palette.stamps.get(item.asset);
    if (!stamp) return;
    if (!stamp.image) {
        palette.loadStamp(stamp.id).catch(() => {});
        return;
    }
    const ext = stampExtent(stamp, item.size, item.crop);
    ctx.save();
    ctx.translate(item.x, item.y);
    if (item.rot) ctx.rotate((item.rot * Math.PI) / 180);
    if (item.flip) ctx.scale(-1, 1);
    drawStampImage(ctx, stamp, item.crop, -ext.w / 2, -ext.h / 2, ext.w, ext.h);
    ctx.restore();
}

function drawLabel(ctx, item, palette) {
    const { font, spacing } = labelFont(item);
    const text = labelText(item);
    ctx.save();
    if (item.symbol) drawStamp(ctx, { ...item.symbol, x: item.x, y: item.y, rot: 0, flip: false }, palette);
    else if (item.pin) {
        ctx.fillStyle = "#9c3b2a";
        ctx.strokeStyle = "#3b2a1a";
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.arc(item.x, item.y, 7, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
    }
    const cy = item.pin || item.symbol ? item.y - item.size * 0.9 : item.y;
    ctx.translate(item.x, cy);
    if (item.rot) ctx.rotate((item.rot * Math.PI) / 180);
    ctx.font = font;
    if (supportsLetterSpacing) ctx.letterSpacing = `${spacing}px`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.lineJoin = "round";
    ctx.strokeStyle = "rgba(239,226,192,0.82)";
    ctx.lineWidth = Math.max(3, item.size * 0.2);
    ctx.strokeText(text, 0, 0);
    ctx.fillStyle = item.color;
    ctx.fillText(text, 0, 0);
    ctx.restore();
}

/** Tiles fill whole grid cells at integer positions, so neighbours meet without seams. */
export function drawTiles(ctx, layer, region, palette) {
    const size = layer.grid.size;
    const c0 = Math.max(0, Math.floor(region.x / size));
    const r0 = Math.max(0, Math.floor(region.y / size));
    const c1 = Math.floor((region.x + region.w - 0.001) / size);
    const r1 = Math.floor((region.y + region.h - 0.001) / size);
    if (c1 < c0 || r1 < r0) return;
    const draw = (col, row, asset) => {
        const stamp = palette.stamps.get(asset);
        if (!stamp) return;
        if (!stamp.image) {
            palette.loadStamp(asset).catch(() => {});
            return;
        }
        ctx.imageSmoothingEnabled = !stamp.pixelArt;
        ctx.drawImage(stamp.image, col * size, row * size, size, size);
    };
    ctx.save();
    ctx.globalAlpha = layer.opacity;
    if ((c1 - c0 + 1) * (r1 - r0 + 1) < layer.cells.size) {
        for (let row = r0; row <= r1; row += 1) {
            for (let col = c0; col <= c1; col += 1) {
                const asset = layer.cells.get(cellKey(col, row));
                if (asset) draw(col, row, asset);
            }
        }
    } else {
        for (const [key, asset] of layer.cells) {
            const { col, row } = cellOf(key);
            if (col >= c0 && col <= c1 && row >= r0 && row <= r1) draw(col, row, asset);
        }
    }
    ctx.restore();
}

export class Renderer {
    constructor(palette) {
        this.palette = palette;
        this.doc = null;
        this.composite = null;
        this.sea = null;
        this.paper = null;
    }

    setDocument(doc) {
        this.doc = doc;
        const { w, h } = doc.size;
        if (!this.composite || this.composite.width !== w || this.composite.height !== h) {
            this.composite = createCanvas(w, h);
        }
        this.buildSea();
        this.renderRegion(null);
    }

    buildSea() {
        const { w, h } = this.doc.size;
        if (!this.sea || this.sea.width !== w || this.sea.height !== h) this.sea = createCanvas(w, h);
        const ctx = this.sea.getContext("2d");
        const gradient = ctx.createLinearGradient(0, 0, w * 0.25, h);
        gradient.addColorStop(0, this.doc.sea.top);
        gradient.addColorStop(1, this.doc.sea.bottom);
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, w, h);
        // faint engraved wave strokes
        let seed = 7;
        const rand = () => {
            seed = (seed * 16807) % 2147483647;
            return seed / 2147483647;
        };
        ctx.strokeStyle = "rgba(235,245,240,0.16)";
        ctx.lineWidth = 1.6;
        ctx.lineCap = "round";
        const count = Math.round((w * h) / 9000);
        for (let i = 0; i < count; i += 1) {
            const x = rand() * w;
            const y = rand() * h;
            const s = 6 + rand() * 7;
            ctx.beginPath();
            ctx.moveTo(x - s, y);
            ctx.quadraticCurveTo(x - s / 2, y - s / 2.6, x, y);
            ctx.quadraticCurveTo(x + s / 2, y + s / 2.6, x + s, y);
            ctx.stroke();
        }
        this.buildPaper();
    }

    /**
     * Pre-scale the CC0 parchment to map resolution so region re-renders copy
     * it 1:1 (identical pixels for partial and full renders). The basic
     * parchment is laid out in 2×4 blocks with visible seams, so a single
     * block is stretched over the map.
     */
    buildPaper() {
        const texture = this.palette.texture;
        if (!texture) {
            this.paper = null;
            return;
        }
        const { w, h } = this.doc.size;
        if (!this.paper || this.paper.width !== w || this.paper.height !== h) {
            this.paper = createCanvas(w, h);
            const ctx = this.paper.getContext("2d");
            const bw = texture.naturalWidth / 2;
            const bh = texture.naturalHeight / 4;
            ctx.imageSmoothingQuality = "high";
            ctx.drawImage(texture, 0, bh, bw, bh, 0, 0, w, h);
        }
    }

    /** Re-composite a region (null = everything) into the cached composite. */
    renderRegion(rect) {
        const { w, h } = this.doc.size;
        const region = rect ? rectClamp(rect, w, h) : { x: 0, y: 0, w, h };
        if (!region) return;
        const ctx = this.composite.getContext("2d");
        ctx.save();
        ctx.beginPath();
        ctx.rect(region.x, region.y, region.w, region.h);
        ctx.clip();
        this.drawMap(ctx, region, 1);
        ctx.restore();
    }

    /** Draw the whole map into ctx (already scaled by `scale`) limited to region. */
    drawMap(ctx, region, scale) {
        const doc = this.doc;
        const { w, h } = doc.size;
        const replacedTitle = replacedTitleLabel(doc);
        ctx.globalCompositeOperation = "source-over";
        ctx.globalAlpha = 1;
        ctx.drawImage(this.sea, region.x, region.y, region.w, region.h, region.x, region.y, region.w, region.h);
        for (const layer of doc.layers) {
            if (!layer.visible || layer.opacity <= 0) continue;
            if (layer.kind === "raster") this.drawRaster(ctx, layer, region, scale);
            else if (layer.kind === "tiles") drawTiles(ctx, layer, region, this.palette);
            else {
                ctx.globalAlpha = layer.opacity;
                for (const item of layer.items) {
                    if (item === replacedTitle) continue;
                    if (!intersects(itemBounds(item, this.palette), region)) continue;
                    if (layer.kind === "stamps") drawStamp(ctx, item, this.palette);
                    else if (layer.kind === "paths") drawPath(ctx, item);
                    else drawLabel(ctx, item, this.palette);
                }
                ctx.globalAlpha = 1;
            }
        }
        if (doc.meta.showTitle) this.drawTitle(ctx, w, h);
        this.drawFinish(ctx, region, w, h);
    }

    drawTitle(ctx, w, h) {
        const title = this.doc.meta.title.toLocaleUpperCase("de-DE");
        ctx.save();
        let size = Math.min(72, w * 0.045);
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        while (size > 16) {
            ctx.font = `700 ${size}px Cinzel, 'Times New Roman', serif`;
            if (ctx.measureText(title).width < w * 0.78) break;
            size -= 2;
        }
        ctx.lineJoin = "round";
        ctx.lineWidth = Math.max(5, size * 0.18);
        ctx.strokeStyle = "rgba(239,226,192,0.88)";
        ctx.strokeText(title, w / 2, Math.max(80, h * 0.09));
        ctx.fillStyle = "#3b2a1a";
        ctx.fillText(title, w / 2, Math.max(80, h * 0.09));
        ctx.restore();
    }

    drawRaster(ctx, layer, region, scale) {
        const { w, h } = this.doc.size;
        const pad = layer.effects.coast ? COAST_PAD : 0;
        const src = rectClamp({ x: region.x - pad, y: region.y - pad, w: region.w + pad * 2, h: region.h + pad * 2 }, w, h);
        if (!src) return;
        const draw = () => ctx.drawImage(layer.canvas, src.x, src.y, src.w, src.h, src.x, src.y, src.w, src.h);
        ctx.save();
        ctx.globalAlpha = layer.opacity;
        if (layer.effects.coast) {
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = 0;
            ctx.shadowColor = "rgba(206,232,226,0.85)";
            ctx.shadowBlur = 26 * scale;
            draw();
            ctx.shadowColor = "rgba(59,42,26,0.9)";
            ctx.shadowBlur = 2.5 * scale;
            draw();
            ctx.shadowColor = "transparent";
            ctx.shadowBlur = 0;
        }
        draw();
        ctx.restore();
    }

    drawFinish(ctx, region, w, h) {
        if (this.paper) {
            ctx.save();
            ctx.globalCompositeOperation = "multiply";
            ctx.globalAlpha = 0.3;
            ctx.drawImage(this.paper, region.x, region.y, region.w, region.h, region.x, region.y, region.w, region.h);
            ctx.restore();
        }
        ctx.save();
        const vignette = ctx.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.45, w / 2, h / 2, Math.hypot(w, h) * 0.56);
        vignette.addColorStop(0, "rgba(60,40,20,0)");
        vignette.addColorStop(1, "rgba(60,40,20,0.28)");
        ctx.fillStyle = vignette;
        ctx.fillRect(region.x, region.y, region.w, region.h);
        // engraved double frame
        ctx.strokeStyle = "#3b2a1a";
        ctx.lineWidth = 6;
        ctx.strokeRect(14, 14, w - 28, h - 28);
        ctx.lineWidth = 1.6;
        ctx.strokeRect(26, 26, w - 52, h - 52);
        ctx.strokeStyle = PARCHMENT;
        ctx.lineWidth = 8;
        ctx.strokeRect(4, 4, w - 8, h - 8);
        ctx.restore();
    }

    /** Full-resolution export canvas at the given scale. */
    renderExport(scale) {
        const { w, h } = this.doc.size;
        const canvas = createCanvas(Math.round(w * scale), Math.round(h * scale));
        const ctx = canvas.getContext("2d");
        ctx.imageSmoothingQuality = "high";
        ctx.scale(scale, scale);
        this.drawMap(ctx, { x: 0, y: 0, w, h }, scale);
        return canvas;
    }
}
