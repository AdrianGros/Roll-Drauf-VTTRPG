// Stamp palette: curated Kenney Cartography Pack (CC0) as the primary set,
// plus a tiny built-in set (compass, pin; simple fallbacks if the pack is missing).

const FILE_RE = /^[a-z0-9_]{1,40}\.png$/;
const ASSET_ID_RE = /^(kenney|kma):[a-z0-9_-]{1,40}$/;
const PACK_ID_RE = /^[a-z0-9][a-z0-9-]{0,50}$/;
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

/** Local reviewed manifests; only Kenney and brush textures decode at startup.
 * Additional stamp pixels are loaded on use, never all at once.
 */
export async function loadPalette(onImageReady = () => {}, onImageError = () => {}) {
    const stamps = new Map();
    const groups = [];
    const packs = [];
    const materialTextures = [];
    const errors = [];
    const pending = new Map();
    let texture = null;
    let packLoaded = false;

    const loadStamp = (id) => {
        const stamp = stamps.get(id);
        if (!stamp) return Promise.reject(new Error("Unbekanntes Symbol."));
        if (stamp.image) return Promise.resolve(stamp.image);
        if (!pending.has(id)) {
            const promise = loadImage(stamp.src).then((image) => {
                stamp.image = image;
                onImageReady();
                return image;
            }).catch((error) => {
                onImageError(`„${stamp.label}“ konnte nicht geladen werden.`);
                throw error;
            });
            pending.set(id, promise);
        }
        return pending.get(id);
    };
    const ensureDocumentImages = (doc) => {
        const ids = new Set();
        for (const layer of doc.layers) for (const item of layer.items || []) {
            if (item.asset) ids.add(item.asset);
            if (item.symbol) ids.add(item.symbol.asset);
        }
        return Promise.all([...ids].map(loadStamp));
    };
    const addStamp = (stamp) => {
        if (stamps.has(stamp.id)) return;
        stamps.set(stamp.id, stamp);
        let group = groups.find((g) => g.name === stamp.group);
        if (!group) {
            group = { name: stamp.group, ids: [] };
            groups.push(group);
        }
        group.ids.push(stamp.id);
    };
    const readPack = async (pack) => {
        try {
            const response = await fetch(`assets/${pack.id}/manifest.json`, { cache: "no-cache" });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const manifest = await response.json();
            const entries = Array.isArray(manifest.stamps) ? manifest.stamps.slice(0, 10000) : [];
            const accepted = [];
            for (const entry of entries) {
                if (!entry || !ASSET_ID_RE.test(entry.id) || !FILE_RE.test(entry.file)) continue;
                if (!(entry.w > 0 && entry.w <= 4096 && entry.h > 0 && entry.h <= 4096)) continue;
                if (pack.id === "kenney-cartography" ? !entry.id.startsWith("kenney:") : !entry.id.startsWith("kma:")) continue;
                accepted.push({
                    id: entry.id, label: String(entry.label || entry.id).slice(0, 100),
                    group: String(entry.group || "Symbole").slice(0, 50),
                    pack: pack.id, packName: pack.name,
                    search: String(entry.search || entry.label || "").slice(0, 500),
                    src: `assets/${pack.id}/${entry.file}`, image: null,
                    w: entry.w, h: entry.h, defaultSize: clampSize(entry.defaultSize),
                });
            }
            if (pack.id === "kenney-cartography") {
                const loaded = await Promise.all(accepted.map(async (stamp) => {
                    stamp.image = await loadImage(stamp.src).catch(() => null);
                    return stamp;
                }));
                for (const stamp of loaded) if (stamp.image) addStamp(stamp);
                packLoaded = loaded.some((stamp) => stamp.image);
                if (loaded.some((stamp) => !stamp.image)) errors.push("Einige Kenney-Symbole fehlen.");
            } else for (const stamp of accepted) addStamp(stamp);
            for (const entry of manifest.textures || []) {
                if (!entry || !FILE_RE.test(entry.file)) continue;
                const image = await loadImage(`assets/${pack.id}/${entry.file}`).catch(() => null);
                if (!image) {
                    errors.push(`Textur „${entry.label || entry.id}“ fehlt.`);
                    continue;
                }
                if (entry.id === "kenney:parchment") texture = image;
                if (entry.purpose === "material" && /^ph_[a-z0-9_]{1,35}$/.test(entry.id)) {
                    materialTextures.push({ id: entry.id, name: String(entry.label).slice(0, 50), image });
                }
            }
            packs.push(pack);
        } catch (_error) {
            errors.push(`Paket „${pack.name}“ konnte nicht geladen werden.`);
        }
    };
    await readPack({ id: "kenney-cartography", name: "Kenney · Cartography" });
    try {
        const response = await fetch("assets/packs.json", { cache: "no-cache" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const catalog = await response.json();
        // Sequential insertion keeps catalogue ordering stable across connections.
        for (const pack of (catalog.packs || []).slice(0, 32)) {
            if (!pack || !PACK_ID_RE.test(pack.id) || pack.id === "kenney-cartography") continue;
            if (pack.manifest !== `${pack.id}/manifest.json`) continue;
            await readPack({ id: pack.id, name: String(pack.name || pack.id).slice(0, 80) });
        }
    } catch (_error) {
        errors.push("Die Zusatzbibliothek konnte nicht geladen werden.");
    }
    const builtinGroup = { name: packLoaded ? "Extras" : "Einfache Symbole", ids: [] };
    for (const def of BUILTINS) {
        const canvas = drawBuiltin(def.kind);
        stamps.set(def.id, { id: def.id, label: def.label, group: builtinGroup.name, pack: "builtin", packName: "Roll Drauf · Einfache Symbole", search: def.label, image: canvas, w: 128, h: 128, defaultSize: def.defaultSize });
        if (def.always || !packLoaded) builtinGroup.ids.push(def.id);
    }
    packs.push({ id: "builtin", name: "Roll Drauf · Einfache Symbole" });
    groups.push(builtinGroup);
    if (!packLoaded) errors.unshift("Das Kenney-Paket fehlt – einfache Ersatzsymbole stehen bereit.");
    return { stamps, groups, packs, packLoaded, packError: errors.join(" "), texture, materialTextures, loadStamp, ensureDocumentImages };
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
