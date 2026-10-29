// Stamp palette: curated Kenney Cartography Pack (CC0) as the primary set,
// plus a tiny built-in set (compass, pin; simple fallbacks if the pack is missing).

const MANIFEST_URL = "assets/kenney-cartography/manifest.json";
const PACK_DIR = "assets/kenney-cartography/";
const FILE_RE = /^[a-z0-9_]{1,40}\.png$/;
const KENNEY_ID_RE = /^kenney:[a-z0-9_-]{1,40}$/;
const INK = "#3b2a1a";

function loadImage(src) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.decoding = "async";
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error(`Bild fehlt: ${src}`));
        img.src = src;
    });
}

function drawBuiltin(kind) {
    const canvas = document.createElement("canvas");
    canvas.width = 128;
    canvas.height = 128;
    const ctx = canvas.getContext("2d");
    ctx.strokeStyle = INK;
    ctx.fillStyle = INK;
    ctx.lineWidth = 5;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    if (kind === "compass") {
        ctx.beginPath();
        ctx.arc(64, 64, 40, 0, Math.PI * 2);
        ctx.stroke();
        for (let i = 0; i < 4; i += 1) {
            const a = (Math.PI / 2) * i - Math.PI / 2;
            ctx.beginPath();
            ctx.moveTo(64 + Math.cos(a) * 60, 64 + Math.sin(a) * 60);
            ctx.lineTo(64 + Math.cos(a + 0.5) * 12, 64 + Math.sin(a + 0.5) * 12);
            ctx.lineTo(64 + Math.cos(a - 0.5) * 12, 64 + Math.sin(a - 0.5) * 12);
            ctx.closePath();
            if (i === 0) ctx.fill();
            else ctx.stroke();
        }
        ctx.font = "700 22px Cinzel, serif";
        ctx.textAlign = "center";
        ctx.fillText("N", 64, 18);
    } else if (kind === "pin") {
        ctx.fillStyle = "#9c3b2a";
        ctx.beginPath();
        ctx.arc(64, 46, 24, Math.PI, 0);
        ctx.quadraticCurveTo(88, 70, 64, 116);
        ctx.quadraticCurveTo(40, 70, 40, 46);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = "#efe2c0";
        ctx.beginPath();
        ctx.arc(64, 46, 9, 0, Math.PI * 2);
        ctx.fill();
    } else if (kind === "mountain") {
        ctx.beginPath();
        ctx.moveTo(10, 110);
        ctx.lineTo(52, 26);
        ctx.lineTo(74, 70);
        ctx.lineTo(88, 50);
        ctx.lineTo(118, 110);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(52, 26);
        ctx.lineTo(44, 80);
        ctx.stroke();
    } else if (kind === "tree") {
        ctx.beginPath();
        ctx.moveTo(64, 14);
        ctx.lineTo(96, 90);
        ctx.lineTo(32, 90);
        ctx.closePath();
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(64, 90);
        ctx.lineTo(64, 116);
        ctx.stroke();
    } else if (kind === "house") {
        ctx.strokeRect(34, 60, 60, 48);
        ctx.beginPath();
        ctx.moveTo(26, 64);
        ctx.lineTo(64, 28);
        ctx.lineTo(102, 64);
        ctx.stroke();
    } else if (kind === "castle") {
        ctx.strokeRect(30, 50, 68, 62);
        for (let x = 30; x < 98; x += 17) ctx.strokeRect(x, 36, 10, 14);
        ctx.strokeRect(56, 82, 16, 30);
    }
    return canvas;
}

const BUILTINS = [
    { id: "builtin:compass", label: "Windrose (einfach)", always: true, kind: "compass", defaultSize: 160 },
    { id: "builtin:pin", label: "Ortsnadel", always: true, kind: "pin", defaultSize: 48 },
    { id: "builtin:mountain", label: "Berg (einfach)", kind: "mountain", defaultSize: 88 },
    { id: "builtin:tree", label: "Baum (einfach)", kind: "tree", defaultSize: 56 },
    { id: "builtin:house", label: "Haus (einfach)", kind: "house", defaultSize: 72 },
    { id: "builtin:castle", label: "Burg (einfach)", kind: "castle", defaultSize: 88 },
];

/**
 * Returns {stamps: Map(id → stamp), groups: [{name, ids}], packLoaded, texture, packError}.
 * Every built-in stays resolvable (so documents referencing them load),
 * but fallback shapes are only offered in the palette without the pack.
 */
export async function loadPalette() {
    const stamps = new Map();
    const groups = [];
    let packLoaded = false;
    let packError = "";
    let texture = null;

    try {
        const response = await fetch(MANIFEST_URL, { cache: "no-cache" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const manifest = await response.json();
        const entries = Array.isArray(manifest.stamps) ? manifest.stamps.slice(0, 200) : [];
        const loaded = await Promise.all(entries.map(async (entry) => {
            if (!entry || !KENNEY_ID_RE.test(entry.id) || !FILE_RE.test(entry.file)) return null;
            try {
                const image = await loadImage(PACK_DIR + entry.file);
                return {
                    id: entry.id,
                    label: String(entry.label || entry.id).slice(0, 40),
                    group: String(entry.group || "Symbole").slice(0, 30),
                    image,
                    w: image.naturalWidth || 128,
                    h: image.naturalHeight || 128,
                    defaultSize: clampSize(entry.defaultSize),
                };
            } catch (_error) {
                return null;
            }
        }));
        for (const stamp of loaded) {
            if (!stamp) continue;
            stamps.set(stamp.id, stamp);
            let group = groups.find((g) => g.name === stamp.group);
            if (!group) {
                group = { name: stamp.group, ids: [] };
                groups.push(group);
            }
            group.ids.push(stamp.id);
        }
        packLoaded = stamps.size > 0;
        const textureEntry = (manifest.textures || []).find((t) => t && t.id === "kenney:parchment" && FILE_RE.test(t.file));
        if (textureEntry) {
            texture = await loadImage(PACK_DIR + textureEntry.file).catch(() => null);
        }
    } catch (error) {
        packError = String(error.message || error);
    }

    const builtinGroup = { name: packLoaded ? "Extras" : "Einfache Symbole", ids: [] };
    for (const def of BUILTINS) {
        const canvas = drawBuiltin(def.kind);
        stamps.set(def.id, { id: def.id, label: def.label, group: builtinGroup.name, image: canvas, w: 128, h: 128, defaultSize: def.defaultSize });
        if (def.always || !packLoaded) builtinGroup.ids.push(def.id);
    }
    groups.push(builtinGroup);

    return { stamps, groups, packLoaded, packError, texture };
}

function clampSize(value) {
    const n = Number(value);
    return Number.isFinite(n) ? Math.min(256, Math.max(16, n)) : 88;
}

/** Draw width/height for a stamp item (size = longest side in map pixels). */
export function stampExtent(stamp, size) {
    const longest = Math.max(stamp.w, stamp.h) || 1;
    return { w: (size * stamp.w) / longest, h: (size * stamp.h) / longest };
}
