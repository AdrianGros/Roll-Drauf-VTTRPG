globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Panels, dialogs and status. All user-provided text is written via
// textContent/value only.

import { ASSET_PERSPECTIVES, ASSET_STYLES, LABEL_FAMILIES, LABEL_STYLES, LIMITS, PLACE_KINDS, cleanText, findItem, clamp, referencedAssetIds } from "./document.js";
import { CUSTOM_PACK } from "./stamps.js";
import { MATERIALS, StrokeEngine, materialTile } from "./brush.js";
import { labelBounds, pathBounds, replacedTitleLabel } from "./render.js";

const $ = (id) => document.getElementById(id);

function el(tag, attrs = {}, text) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
        if (key === "class") node.className = value;
        else if (key === "dataset") Object.assign(node.dataset, value);
        else if (value === true) node.setAttribute(key, "");
        else if (value !== false && value !== null && value !== undefined) node.setAttribute(key, String(value));
    }
    if (text !== undefined) node.textContent = text;
    return node;
}

function svgIcon(paths) {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    for (const d of paths) {
        const path = document.createElementNS(ns, "path");
        path.setAttribute("d", d);
        svg.appendChild(path);
    }
    return svg;
}

const ICONS = {
    eyeOn: ["M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z", "M12 9a3 3 0 100 6 3 3 0 000-6z"],
    eyeOff: ["M3 3l18 18", "M10.6 5.1A10 10 0 0112 5c6.4 0 10 7 10 7a17 17 0 01-3.2 4M6.6 6.6A17 17 0 002 12s3.6 7 10 7a10 10 0 005.4-1.6"],
    up: ["M12 19V5", "M6 11l6-6 6 6"],
    down: ["M12 5v14", "M6 13l6 6 6-6"],
    rename: ["M4 20h4L19 9l-4-4L4 16z"],
    trash: ["M4 7h16", "M9 7V4h6v3", "M6 7l1 13h10l1-13"],
};

const KIND_LABEL = { raster: globalThis.VTTUi("Malen"), paths: globalThis.VTTUi("Wege"), stamps: globalThis.VTTUi("Symbole"), labels: globalThis.VTTUi("Text"), tiles: globalThis.VTTUi("Kacheln") };

/** Thumbnail without object URLs (CSP): catalog images by src, own and built-in images drawn to a canvas. */
function stampThumb(stamp, size, label = null) {
    if (stamp.src) return el("img", { src: stamp.src, width: size, height: size, alt: label || "", loading: "lazy", decoding: "async", class: stamp.pixelArt ? "mm-pixel" : null });
    const canvas = el("canvas", { width: size, height: size, class: stamp.pixelArt ? "mm-pixel" : null, ...(label ? { role: "img", "aria-label": label } : { "aria-hidden": "true" }) });
    if (stamp.image) {
        const ctx = canvas.getContext("2d");
        ctx.imageSmoothingEnabled = !stamp.pixelArt;
        const scale = Math.min((size - 8) / stamp.w, (size - 8) / stamp.h);
        const w = stamp.w * scale, h = stamp.h * scale;
        ctx.drawImage(stamp.image, (size - w) / 2, (size - h) / 2, w, h);
    }
    return canvas;
}

/** Sides where opaque pixels inside the crop continue into opaque pixels just outside it. */
export function cropCutSides(crop, { w, h, alpha }) {
    const at = (x, y) => alpha[y * w + x];
    const sides = [];
    const row = (inside, outside) => { for (let x = crop.x; x < crop.x + crop.w; x += 1) if (at(x, inside) && at(x, outside)) return true; return false; };
    const col = (inside, outside) => { for (let y = crop.y; y < crop.y + crop.h; y += 1) if (at(inside, y) && at(outside, y)) return true; return false; };
    if (crop.y > 0 && row(crop.y, crop.y - 1)) sides.push("top");
    if (crop.x + crop.w < w && col(crop.x + crop.w - 1, crop.x + crop.w)) sides.push("right");
    if (crop.y + crop.h < h && row(crop.y + crop.h - 1, crop.y + crop.h)) sides.push("bottom");
    if (crop.x > 0 && col(crop.x, crop.x - 1)) sides.push("left");
    return sides;
}

/**
 * Clean own crop: grow while visible content continues past an edge, then trim
 * fully transparent margins. Returns null for an empty crop. A diagnosis aid,
 * not a claim that every catalogue sheet is sliced correctly.
 */
export function fitCropToContent(crop, { w, h, alpha }) {
    let { x, y, w: cw, h: ch } = crop;
    const rowAny = (r, x0, x1) => { for (let i = Math.max(0, x0); i < Math.min(w, x1); i += 1) if (alpha[r * w + i]) return true; return false; };
    const colAny = (c, y0, y1) => { for (let j = Math.max(0, y0); j < Math.min(h, y1); j += 1) if (alpha[j * w + c]) return true; return false; };
    for (let guard = 0, changed = true; changed && guard < w + h; guard += 1) {
        changed = false;
        if (y > 0 && rowAny(y, x, x + cw) && rowAny(y - 1, x - 1, x + cw + 1)) { y -= 1; ch += 1; changed = true; }
        if (y + ch < h && rowAny(y + ch - 1, x, x + cw) && rowAny(y + ch, x - 1, x + cw + 1)) { ch += 1; changed = true; }
        if (x > 0 && colAny(x, y, y + ch) && colAny(x - 1, y - 1, y + ch + 1)) { x -= 1; cw += 1; changed = true; }
        if (x + cw < w && colAny(x + cw - 1, y, y + ch) && colAny(x + cw, y - 1, y + ch + 1)) { cw += 1; changed = true; }
    }
    while (ch > 0 && !rowAny(y, x, x + cw)) { y += 1; ch -= 1; }
    while (ch > 0 && !rowAny(y + ch - 1, x, x + cw)) ch -= 1;
    while (cw > 0 && ch > 0 && !colAny(x, y, y + ch)) { x += 1; cw -= 1; }
    while (cw > 0 && ch > 0 && !colAny(x + cw - 1, y, y + ch)) cw -= 1;
    return cw > 0 && ch > 0 ? { x, y, w: cw, h: ch } : null;
}

const TRAIT_UNKNOWN = "unknown";
const STYLE_FILTERS = () => ({ "": globalThis.VTTUi("Alle Darstellungen"), pixel: globalThis.VTTUi("Pixelgrafik"), painted: globalThis.VTTUi("Gemalt"),
    ink: globalThis.VTTUi("Tusche/Linie"), other: globalThis.VTTUi("Sonstiges"), [TRAIT_UNKNOWN]: globalThis.VTTUi("Ohne Angabe") });
const PERSPECTIVE_FILTERS = () => ({ "": globalThis.VTTUi("Alle Perspektiven"), top: globalThis.VTTUi("Draufsicht"), side: globalThis.VTTUi("Seitenansicht"),
    isometric: globalThis.VTTUi("Isometrisch"), other: globalThis.VTTUi("Sonstige"), [TRAIT_UNKNOWN]: globalThis.VTTUi("Ohne Angabe") });
const STAMP_FILTER_IDS = ["stampSearch", "stampPack", "stampCategory", "stampStyle", "stampPerspective"];

/** Declared traits only: own images state style/perspective; catalogue packs only state pixel art. null = no claim. */
function assetTraits(stamp) {
    return stamp.custom ? { style: stamp.style || null, perspective: stamp.perspective || null }
        : { style: stamp.pixelArt ? "pixel" : null, perspective: null };
}
const traitMatches = (value, filter) => !filter || (filter === TRAIT_UNKNOWN ? value === null : value === filter);
const FONT_NAMES = () => ({ "": globalThis.VTTUi("Wie der Stil"), cinzel: globalThis.VTTUi("Cinzel (Antiqua-Versalien)"),
    badscript: globalThis.VTTUi("Bad Script (Schreibschrift)"), literata: globalThis.VTTUi("Literata (Buchschrift)") });

const STATUS_TEXT = {
    idle: globalThis.VTTUi("Noch keine Änderungen"),
    pending: globalThis.VTTUi("Ungespeicherte Änderungen"),
    saving: globalThis.VTTUi("Speichert …"),
    saved: globalThis.VTTUi("Lokal gespeichert"),
    failed: globalThis.VTTUi("Autosave fehlgeschlagen – bitte als Datei speichern"),
    unavailable: globalThis.VTTUi("Autosave nicht verfügbar – bitte als Datei speichern"),
};

export class UI {
    constructor(editor) {
        this.ed = editor;
        this.toastTimer = 0;
        this.pane = "tool";
        // Page-lifetime only: never saved, autosaved or put in undo.
        this.stampSizes = new Map();
        this.recentStamps = [];
        this.layerUse = new WeakMap();
        this.layerUseClock = 0;
        this.stageLayersExpanded = false;
        this.tileGridOffer = null;
        this.rasterContent = new WeakMap();
    }

    // ---- wiring ------------------------------------------------------------

    bind() {
        const ed = this.ed;
        document.querySelectorAll(".mm-tool").forEach((button) => {
            button.addEventListener("click", () => ed.setTool(button.dataset.tool));
        });
        document.querySelectorAll(".mm-tabs [role=tab]").forEach((tab) => {
            tab.addEventListener("click", () => this.togglePane(tab.dataset.pane));
            tab.addEventListener("keydown", (event) => this.tabKeys(event));
        });

        $("undoBtn").addEventListener("click", () => ed.undo());
        $("redoBtn").addEventListener("click", () => ed.redo());
        $("zoomIn").addEventListener("click", () => ed.zoomStep(1.25));
        $("zoomOut").addEventListener("click", () => ed.zoomStep(0.8));
        $("zoomFit").addEventListener("click", () => ed.fit());
        $("activeLayerJump").addEventListener("click", () => {
            if (this.isNarrow()) {
                this.stageLayersExpanded = !this.stageLayersExpanded;
                this.syncStageLayers();
            } else this.openLayerManagement();
        });
        $("manageStageLayers").addEventListener("click", () => this.openLayerManagement());
        $("stageLayerPanel").addEventListener("keydown", (event) => {
            if (event.key === "Escape" && this.isNarrow()) {
                event.preventDefault();
                event.stopPropagation();
                this.stageLayersExpanded = false;
                this.syncStageLayers();
                $("activeLayerJump").focus();
            }
        });
        window.matchMedia("(max-width: 760px)").addEventListener("change", () => this.syncStageLayers());
        this.syncStageLayers();
        $("referenceGrid").addEventListener("change", (event) => {
            ed.showReferenceGrid = event.target.checked;
            ed.requestFrame();
        });
        for (const id of ["layerFilterKind", "layerFilterName", "layerFilterContent", "layerSort"]) {
            $(id).addEventListener(id === "layerFilterName" ? "input" : "change", () => this.refreshLayers());
        }
        for (const id of ["tileNewLayer", "layerNewGrid"]) {
            $(id).addEventListener("click", () => {
                if (this.tileGridOffer?.doc === ed.doc) ed.newTileLayer(this.tileGridOffer.size);
            });
        }
        $("helpBtn").addEventListener("click", () => $("helpDialog").showModal());
        $("helpClose").addEventListener("click", () => $("helpDialog").close());
        $("errorClose").addEventListener("click", () => $("errorDialog").close());
        $("reloadBtn").addEventListener("click", () => window.location.reload());

        const title = $("mapTitle");
        title.addEventListener("input", () => ed.doc && ed.setTitle(title.value));
        title.addEventListener("keydown", (event) => {
            if (event.key === "Enter") title.blur();
        });

        // file menu
        const menuButton = $("fileMenuBtn");
        const menu = $("fileMenuList");
        const closeMenu = () => {
            menu.hidden = true;
            menuButton.setAttribute("aria-expanded", "false");
        };
        menuButton.addEventListener("click", () => {
            const open = menu.hidden;
            menu.hidden = !open;
            menuButton.setAttribute("aria-expanded", String(open));
            if (open) menu.querySelector("button").focus();
        });
        document.addEventListener("pointerdown", (event) => {
            if (!menu.hidden && !event.target.closest(".mm-menu")) closeMenu();
        });
        menu.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                event.preventDefault();
                event.stopPropagation();
                closeMenu();
                menuButton.focus();
            }
        });
        menu.querySelectorAll("button").forEach((button) => button.addEventListener("click", closeMenu));
        $("newBtn").addEventListener("click", () => ed.library.show());
        $("openBtn").addEventListener("click", () => $("fileInput").click());
        $("saveBtn").addEventListener("click", () => ed.saveFile());
        $("exportBtn").addEventListener("click", () => this.openExport());
        $("fileInput").addEventListener("change", async (event) => {
            const file = event.target.files && event.target.files[0];
            event.target.value = "";
            await ed.openFile(file);
        });

        // new / export dialogs
        $("newStarter").addEventListener("click", async () => {
            $("newDialog").close();
            await ed.newMap("starter");
        });
        $("newEmpty").addEventListener("click", async () => {
            $("newDialog").close();
            await ed.newMap("empty");
        });
        $("newCancel").addEventListener("click", () => $("newDialog").close());
        $("exportCancel").addEventListener("click", () => $("exportDialog").close());
        $("exportGo").addEventListener("click", () => this.runExport());
        $("exportBundle").addEventListener("click", () => this.runExport(true));

        this.bindBrush();
        this.bindPath();
        this.bindStamp();
        this.bindTiles();
        this.bindLabelTool();
        this.bindInspector();
        this.bindLayers();
        this.bindReviewControls();
        $("addPlaceBtn").addEventListener("click", () => {
            ed.setTool("label");
            this.openPane("tool");
            this.toast(globalThis.VTTUi("Tippe auf die Karte, um den Ort zu setzen."));
        });
    }

    /** Tool-context layer choice, brush clip, object order, own images, style filters and help rows. */
    bindReviewControls() {
        const ed = this.ed, t = globalThis.VTTUi;
        const labels = {
            toolLayerLabel: t("Ebene für dieses Werkzeug"), toolLayerHint: t("Alt+↑ / Alt+↓ wechselt die Ebene."),
            brushClipLabel: t("Malbegrenzung"), selFontLabel: t("Schriftfamilie"), labelFontLabel: t("Schriftfamilie"),
            selPathNameLabel: t("Name des Wegs (optional)"), selPathConnect: t("Endpunkt mit Nachbarweg verbinden"),
            selPathConnectHint: t("Verbindet nur mit einem Endpunkt derselben Ebene und Art in höchstens {px} px Abstand. Kreuzungen bleiben getrennt.", { px: 32 }),
            stampPlacementLabel: t("Platzierung"), stampAreaLabel: t("Fläche füllen (Rechteck ziehen)"),
            ownUploadBtn: t("Eigenes Bild hochladen …"), ownPixelBtn: t("Pixelbild zeichnen …"), ownAssetManageLabel: t("Eigene Bilder dieser Karte"),
            stampStyleLabel: t("Darstellung"), stampPerspectiveLabel: t("Perspektive"), sheetFitContent: t("Zusammenhängenden Inhalt erfassen"),
            helpOrder: t("Auswahl eine Stufe nach vorne/hinten (mit Umschalt: ganz)"), helpWheelKey: t("Mausrad"),
            helpWheel: t("Reihenfolge der Auswahl ändern (Auswählen-Werkzeug)"), helpLayer: t("Ebene des Werkzeugs wechseln"),
            stampTraitHint: t("Stil und Perspektive geben nur eigene Bilder an; Katalogpakete kennen nur „Pixelgrafik“."),
            stampFilterReset: t("Filter zurücksetzen"), helpBracketNote: t("Deutsche Tastatur: AltGr+8/9 für [ ], AltGr+7/0 für { }."),
            helpNodeKey: t("Ziehen"), helpNode: t("Wegpunkt des ausgewählten Wegs verschieben (Auswählen)"),
            placeSymbolHint: t("Zuletzt gewählte Symbole und die aktuelle Seite der Symbolpalette (mit deren Suche und Filtern)."),
            helpEscape: t("Auswahl oder Geste abbrechen; sonst das Platzieren beenden."),
            stageLayerLegend: t("Aktive Zeichenebene"), manageStageLayers: t("Alle Ebenen verwalten"),
            referenceGridLabel: t("Raster bei allen Werkzeugen"),
            layerFilterKindLabel: t("Ebenentyp"), layerFilterNameLabel: t("Ebenen suchen"),
            layerFilterContentLabel: t("Ebeneninhalt"),
            layerSortLabel: t("Ebenen sortieren"),
            layerRecentHint: t("Zuletzt genutzt: in dieser Editorsitzung ausgewählt oder bearbeitet."),
            stampAdvancedLabel: t("Weitere Platzierungsoptionen"),
            editPlacedLabel: t("Ausgewählte Beschriftung bearbeiten"),
        };
        Object.entries(labels).forEach(([id, text]) => { $(id).textContent = text; });
        $("editPlacedLabel").addEventListener("click", () => this.focusLabelName());
        $("layerFilterKind").appendChild(el("option", { value: "" }, t("Alle Ebenentypen")));
        for (const [kind, label] of Object.entries(KIND_LABEL)) $("layerFilterKind").appendChild(el("option", { value: kind }, label));
        $("layerSort").append(el("option", { value: "stack" }, t("Zeichenreihenfolge")), el("option", { value: "recent" }, t("Zuletzt genutzt")));
        for (const [value, label] of [["", t("Alle Inhalte")], ["filled", t("Mit Inhalt")], ["empty", t("Ohne Inhalt")], ["used", t("In dieser Sitzung genutzt")]]) {
            $("layerFilterContent").appendChild(el("option", { value }, label));
        }
        const orderNames = { back: t("Ganz nach hinten"), backward: t("Nach hinten"), forward: t("Nach vorne"), front: t("Ganz nach vorne") };
        document.querySelectorAll(".mm-order-row").forEach((row) => row.setAttribute("aria-label", t("Reihenfolge")));
        document.querySelectorAll(".mm-order-label").forEach((node) => { node.textContent = t("Reihenfolge"); });
        document.querySelectorAll(".mm-order-hint").forEach((node) => { node.textContent = t("Bild↑/Bild↓ oder Alt+Mausrad ändern die Reihenfolge in der Ebene."); });
        document.querySelectorAll("[data-order]").forEach((button) => {
            button.textContent = orderNames[button.dataset.order];
            button.addEventListener("click", () => ed.reorderSelection(button.dataset.order));
        });
        $("toolLayer").addEventListener("change", (event) => { if (event.target.value) ed.setActiveLayer(event.target.value); });
        $("brushClip").addEventListener("change", (event) => ed.setClip(event.target.value || null));
        for (const [id, names] of [["stampStyle", STYLE_FILTERS()], ["stampPerspective", PERSPECTIVE_FILTERS()]]) {
            for (const [value, name] of Object.entries(names)) $(id).appendChild(el("option", { value }, name));
            $(id).addEventListener("change", () => { this.palettePage = 0; this.renderPalette(); });
        }
        $("stampFilterReset").addEventListener("click", () => {
            for (const id of STAMP_FILTER_IDS) $(id).value = "";
            this.palettePage = 0;
            this.renderPalette();
            $("stampPack").focus(); // the button hides itself; keep focus in the filter group
        });
        for (const select of [$("labelFont"), $("selFont")]) {
            for (const [value, name] of Object.entries(FONT_NAMES())) select.appendChild(el("option", { value }, name));
        }
        $("labelFont").addEventListener("change", (event) => { ed.labelOpts.font = LABEL_FAMILIES.includes(event.target.value) ? event.target.value : null; });
        $("selFont").addEventListener("change", (event) => {
            ed.liveEdit({ font: LABEL_FAMILIES.includes(event.target.value) ? event.target.value : null });
            ed.commitEdit();
        });
        $("selPathName").addEventListener("input", (event) => ed.liveEdit({ name: cleanText(event.target.value, LIMITS.pathName) }));
        $("selPathName").addEventListener("change", () => ed.commitEdit());
        $("selPathName").addEventListener("keydown", (event) => { if (event.key === "Enter") event.target.blur(); });
        $("selPathConnect").addEventListener("click", () => ed.connectPathEndpoints());
        $("stampArea").addEventListener("change", (event) => {
            ed.stampOpts.area = event.target.checked;
            if (event.target.checked) { ed.stampOpts.scatter = false; $("stampScatter").checked = false; }
            this.showAreaPlan(null);
            ed.requestFrame();
        });
        this.showAreaPlan(null);
    }

    showAreaPlan(count) {
        const ed = this.ed, info = $("stampAreaInfo");
        const mode = ed.stampOpts.area ? globalThis.VTTUi("Fläche füllen (Rechteck ziehen)")
            : ed.stampOpts.scatter ? globalThis.VTTUi("Streuen beim Ziehen (Wälder, Gebirge)") : "";
        $("stampAdvancedLabel").textContent = globalThis.VTTUi("Weitere Platzierungsoptionen") + (mode ? ` · ${mode}` : "");
        if (!ed.stampOpts.area) { info.textContent = ""; return; }
        if (count === null) {
            info.textContent = globalThis.VTTUi("Rechteck auf der Karte aufziehen. Abstand wie beim Streuen; ein Rückgängig-Schritt.");
            return;
        }
        const free = LIMITS.items - (ed.doc ? ed.doc.layers.reduce((sum, layer) => sum + (layer.items ? layer.items.length : 0), 0) : 0);
        info.textContent = count > 400 || count > free
            ? globalThis.VTTUi("{count} Symbole – zu viele für diese Fläche (höchstens 400 je Fläche, frei: {free}).", { count, free })
            : globalThis.VTTUi("{count} Symbole werden gesetzt.", { count });
    }

    refreshToolLayer() {
        const ed = this.ed;
        if (!ed.doc) return;
        const select = $("toolLayer"), kind = ed.toolKind();
        const eraser = ed.tool === "eraser" ? ["raster", "tiles", "stamps"] : null;
        const layers = [...ed.doc.layers].reverse().filter((layer) => (kind ? layer.kind === kind : !eraser || eraser.includes(layer.kind)));
        select.replaceChildren();
        for (const layer of layers) {
            select.appendChild(el("option", { value: layer.id }, layer.visible ? layer.name : globalThis.VTTUi("{name} (ausgeblendet)", { name: layer.name })));
        }
        if (!layers.length) select.appendChild(el("option", { value: "" }, kind === "tiles" || kind === "paths"
            ? globalThis.VTTUi("Neue Ebene beim ersten Einsatz") : globalThis.VTTUi("Keine passende Ebene")));
        const target = layers.find((layer) => layer.id === ed.activeLayerId) || (kind && ed.targetLayer(kind, { quiet: true })) || layers[0];
        select.value = target ? target.id : "";
        select.disabled = !layers.length;
    }

    refreshClip() {
        const ed = this.ed;
        if (!ed.doc) return;
        const select = $("brushClip"), candidates = ed.clipCandidates();
        select.replaceChildren(el("option", { value: "" }, globalThis.VTTUi("Keine Begrenzung")));
        for (const layer of candidates) {
            select.appendChild(el("option", { value: layer.id }, layer.kind === "tiles"
                ? globalThis.VTTUi("Nur auf belegten Kacheln von „{name}“", { name: layer.name })
                : globalThis.VTTUi("Nur auf der Deckung von „{name}“", { name: layer.name })));
        }
        select.value = ed.clipOpts.layerId || "";
        select.disabled = !candidates.length;
        const target = ed.activeLayer();
        $("brushClipHint").textContent = ed.clipOpts.notice
            || (!candidates.length ? (target && target.kind === "raster"
                ? globalThis.VTTUi("Keine Bezugsebene: Eine Malebene darunter oder eine Kachelebene kann die Malfläche begrenzen.")
                : globalThis.VTTUi("Malbegrenzung gilt für die aktive Malebene."))
                : ed.clipOpts.layerId ? globalThis.VTTUi("Neue Striche erscheinen nur dort; vorhandene Pixel außerhalb bleiben unverändert.") : "");
    }

    refreshCustomAssets() {
        const ed = this.ed;
        if (!ed.doc || !ed.palette) return;
        const usage = ed.assetUsage();
        $("ownAssetUsage").textContent = globalThis.VTTUi("{count}/{max} eigene Bilder · {mib} von 12 MiB · nur in dieser Karte gespeichert", {
            count: usage.count, max: LIMITS.customAssets, mib: `${(usage.bytes / 1048576).toLocaleString("de", { maximumFractionDigits: 2 })} MiB` });
        const list = $("ownAssetList"), used = referencedAssetIds(ed.doc);
        list.replaceChildren();
        for (const asset of ed.doc.assets) {
            const stamp = ed.palette.stamps.get(asset.id);
            const item = el("li", { class: "mm-own-item", dataset: { asset: asset.id } });
            if (stamp) item.appendChild(stampThumb(stamp, 40));
            const text = el("div", { class: "mm-own-text" });
            text.append(el("strong", {}, asset.label), el("span", { class: "mm-hint" },
                `${asset.width}×${asset.height} px · ${STYLE_FILTERS()[asset.style] || asset.style} · ${asset.license || globalThis.VTTUi("ohne Lizenzangabe")}`));
            const actions = el("div", { class: "mm-own-buttons" });
            const choose = el("button", { type: "button", class: "mm-btn mm-btn-small", "aria-label": globalThis.VTTUi("„{label}“ als Stempel wählen", { label: asset.label }) }, globalThis.VTTUi("Verwenden"));
            choose.addEventListener("click", () => { ed.setTool("stamp"); this.chooseStamp(asset.id, { openSheet: false }); });
            const inUse = used.has(asset.id);
            const remove = el("button", { type: "button", class: "mm-btn mm-btn-small", disabled: inUse, "aria-label": globalThis.VTTUi("„{label}“ aus der Karte entfernen", { label: asset.label }),
                title: inUse ? globalThis.VTTUi("Wird auf der Karte verwendet") : "" }, globalThis.VTTUi("Entfernen"));
            remove.addEventListener("click", () => ed.removeCustomAsset(asset.id));
            actions.append(choose, remove);
            item.append(text, actions);
            list.appendChild(item);
        }
        if (!ed.doc.assets.length) list.appendChild(el("li", { class: "mm-empty" }, globalThis.VTTUi("Noch keine eigenen Bilder in dieser Karte.")));
        this.renderPalette();
        this.renderTilePalette();
        this.renderTileVariants();
    }

    range(id, outId, format, onInput) {
        const input = $(id);
        const out = $(outId);
        const number = $(`${id}Number`);
        const sync = () => {
            out.textContent = format(Number(input.value));
            if (number) number.value = input.value;
        };
        input.addEventListener("input", () => {
            sync();
            onInput(Number(input.value));
        });
        if (number) number.addEventListener("change", () => {
            const value = Number(number.value);
            if (!Number.isFinite(value) || number.value === "") {
                sync();
                return;
            }
            input.value = String(Math.round(clamp(value, Number(input.min), Number(input.max))));
            sync();
            onInput(Number(input.value));
        });
        return { input, sync, set: (value) => { input.value = String(value); sync(); } };
    }

    bindBrush() {
        const ed = this.ed;
        const container = $("materials");
        for (const material of MATERIALS) {
            const button = el("button", { type: "button", class: "mm-swatch", role: "radio", "aria-checked": "false", title: material.name, dataset: { material: material.id } });
            const chip = el("canvas", { width: 40, height: 40, "aria-hidden": "true" });
            const cctx = chip.getContext("2d");
            cctx.fillStyle = cctx.createPattern(materialTile(material.id), "repeat");
            cctx.fillRect(0, 0, 40, 40);
            button.append(chip, el("span", {}, material.name));
            button.addEventListener("click", () => {
                ed.brush.material = material.id;
                ed.paintBrush.image = null;
                if (ed.paintBrush.shape === 'image') ed.paintBrush.shape = 'round';
                this.syncBrush();
                this.syncMaterials();
                this.drawBrushPreview();
                const targetId = material.id === "land" ? "land"
                    : material.id === "river" || material.id === "road" ? "rivers" : "terrain";
                const target = ed.layerById(targetId);
                if (target && target.kind === "raster" && target.visible && target.id !== ed.activeLayerId) {
                    ed.setActiveLayer(target.id);
                    this.toast(globalThis.VTTUi("Malt jetzt auf „{p0}“.",{p0:(target.name)}));
                }
            });
            container.appendChild(button);
        }
        this.brushSize = this.range("brushSize", "brushSizeOut", (v) => `${v} px`, (v) => { ed.brush.size = v; this.drawBrushPreview(); ed.requestFrame(); });
        this.brushOpacity = this.range("brushOpacity", "brushOpacityOut", (v) => `${v} %`, (v) => { ed.brush.opacity = v / 100; this.drawBrushPreview(); });
        this.brushSoftness = this.range("brushSoftness", "brushSoftnessOut", (v) => `${v} %`, (v) => { ed.brush.softness = v; this.drawBrushPreview(); });
        this.brushTexture = this.range('brushTexture', 'brushTextureOut', v => `${v} %`, v => { ed.paintBrush.texture = v / 100;this.drawBrushPreview(); });
        $('brushShape').addEventListener('change', e => { ed.brush.shape = e.target.value;this.syncBrush(); });
        $('brushColorEnabled').addEventListener('change', e => { ed.paintBrush.colorEnabled = e.target.checked;this.syncBrush(); });
        $('brushColor').addEventListener('input', e => { ed.paintBrush.color = e.target.value;this.drawBrushPreview(); });
        $('stampAsBrush').addEventListener('click', () => ed.useImageBrush(ed.stampOpts.asset, ed.stampOpts.crop));
        $('tileAsBrush').addEventListener('click', () => ed.useImageBrush(ed.tileOpts.asset));
        const coast = (key, value) => { const layer = ed.activeLayer();if (layer?.kind === 'raster') ed.setLayerProp(layer.id, key, value); };
        $('brushCoast').addEventListener('change', e => coast('coast', e.target.checked));
        $('brushCoastColor').addEventListener('change', e => coast('coastColor', e.target.value));
        $('brushCoastWidth').addEventListener('input', e => { $('brushCoastWidthOut').textContent = `${e.target.value} px`; });
        $('brushCoastWidth').addEventListener('change', e => coast('coastWidth', Number(e.target.value)));
        this.brushSize.set(ed.brush.size);
        this.brushOpacity.set(Math.round(ed.brush.opacity * 100));
        this.brushSoftness.set(ed.brush.softness);
        $("brushPressure").addEventListener("change", (event) => {
            ed.brush.pressureEnabled = event.target.checked;
        });
        this.syncMaterials();
        this.drawBrushPreview();
    }

    syncBrush() {
        const b = this.ed.brush, image = !!b.image && b.shape === 'image';
        this.brushSize.set(b.size);this.brushOpacity.set(Math.round(b.opacity * 100));this.brushSoftness.set(b.softness);
        $('brushShape').value = b.shape || 'round';$('brushShape').querySelector('[value=image]').disabled = !b.image;
        $('brushPressure').checked = b.pressureEnabled;
        $('brushColorEnabled').checked = !!b.colorEnabled;$('brushColor').value = b.color || '#8ea566';
        this.brushTexture.set(Math.round((b.texture ?? 1) * 100));
        for (const id of ['brushColorEnabled', 'brushColor', 'brushTexture']) $(id).disabled = image;
        $('brushImageInfo').hidden = !image;
        $('brushImageInfo').textContent = image ? `${globalThis.VTTUi('Bildpinsel: {p0}. Originalfarben bleiben erhalten; Materialfarbe und Texturanteil gelten nur für Materialpinsel.', {p0:b.image.label})} ${globalThis.VTTUi('Ein Material wählen, um wieder mit Materialfarbe zu malen.')}` : '';
        this.syncMaterials();
        this.drawBrushPreview();
    }

    syncMaterials() {
        // The image brush paints its original colours, so no material is checked; the first swatch stays focusable.
        const b = this.ed.brush, image = !!b.image && b.shape === "image";
        document.querySelectorAll(".mm-swatch").forEach((button, index) => {
            const on = !image && button.dataset.material === b.material;
            button.setAttribute("aria-checked", String(on));
            button.tabIndex = on || (image && index === 0) ? 0 : -1;
        });
    }

    drawBrushPreview() {
        const canvas = $("brushPreview");
        const ctx = canvas.getContext("2d");
        const { brush, tool } = this.ed;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "#e9dcb8";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        const scale = Math.min(1, 70 / brush.size);
        const radius = Math.max(1, (brush.size / 2) * scale);
        const mask = document.createElement("canvas");mask.width = canvas.width;mask.height = canvas.height;
        const engine = new StrokeEngine(mask.width, mask.height);
        engine.begin({canvas:mask,rev:0}, {...brush,size:radius*2,pressureEnabled:false,erase:false,
            ...(tool === 'eraser' ? {material:'river',colorEnabled:true,color:'#2f5d6e',texture:0,image:null} : {})});
        const step = Math.max(1, radius * 2 * 0.12);
        for (let x = 40; x <= canvas.width - 40; x += step) {
            const y = canvas.height / 2 + Math.sin((x / canvas.width) * Math.PI * 2) * 14;
            engine.addPoint(x, y, null);
        }
        engine.end();
        ctx.drawImage(mask, 0, 0);
        ctx.globalAlpha = 1;
    }

    nudge(kind, up) {
        const ed = this.ed;
        if (ed.tool === "stamp" && kind === "size") {
            const value = clamp(Math.round(ed.stampOpts.size * (up ? 1.15 : 1 / 1.15)), 16, 320);
            ed.stampOpts.size = value;
            this.stampSize.set(value);
            this.rememberStampSize();
        } else if (kind === "softness") {
            ed.brush.softness = clamp(ed.brush.softness + (up ? 10 : -10), 0, 100);
            this.brushSoftness.set(ed.brush.softness);
        } else {
            ed.brush.size = clamp(Math.round(ed.brush.size * (up ? 1.2 : 1 / 1.2)), 2, 800);
            this.brushSize.set(ed.brush.size);
        }
        this.drawBrushPreview();
        ed.requestFrame();
    }

    showPressure() {
        $("pressureRow").hidden = false;
    }

    bindStamp() {
        const ed = this.ed;
        this.stampSize = this.range("stampSize", "stampSizeOut", (v) => `${v} px`, (v) => { ed.stampOpts.size = v; this.rememberStampSize(); ed.requestFrame(); });
        this.stampRot = this.range("stampRot", "stampRotOut", (v) => `${v}°`, (v) => { ed.stampOpts.rot = v; ed.requestFrame(); });
        this.stampSize.set(ed.stampOpts.size);
        this.stampRot.set(ed.stampOpts.rot);
        $("stampFlip").addEventListener("change", (event) => { ed.stampOpts.flip = event.target.checked; ed.requestFrame(); });
        $("stampVary").addEventListener("change", (event) => { ed.stampOpts.vary = event.target.checked; });
        $("stampScatter").addEventListener("change", (event) => {
            ed.stampOpts.scatter = event.target.checked;
            if (event.target.checked && ed.stampOpts.area) { ed.stampOpts.area = false; $("stampArea").checked = false; }
            this.showAreaPlan(null);
            ed.requestFrame();
        });
        // Optional stamp grid: off by default; preview and placement share ed.stampPoint().
        $("stampGridOn").addEventListener("change", (event) => {
            ed.stampOpts.grid = event.target.checked ? ed.stampGridSize(Number($("stampGridSize").value)) : 0;
            $("stampGridSize").disabled = !event.target.checked;
            ed.requestFrame();
        });
        $("stampGridSize").addEventListener("input", (event) => {
            if (ed.stampOpts.grid) ed.stampOpts.grid = ed.stampGridSize(Number(event.target.value));
            ed.requestFrame();
        });
        $("eraseScope").addEventListener("change", (event) => { ed.eraseScope = event.target.value === "visible" ? "visible" : "active"; });
        $("importActionBtn").addEventListener("click", () => $("fileInput").click());
        $("exportActionBtn").addEventListener("click", () => this.openExport());
    }

    bindTiles() {
        const ed = this.ed;
        this.tilePage = 0;
        $("tileMode").addEventListener("change", (event) => { ed.tileOpts.erase = event.target.value === "erase"; ed.requestFrame(); });
        $("tileRadius").addEventListener("input", (event) => { ed.tileOpts.radius = Math.max(0, Math.min(6, Math.round(Number(event.target.value)) || 0)); ed.requestFrame(); });
        // Variants are chosen visually from known catalog tiles: the currently selected palette
        // tile is added with "+"; chips remove single variants; "×" clears the list.
        const addLabel = globalThis.VTTUi("Gewählte Kachel als Variante hinzufügen");
        $("tileVariantAdd").setAttribute("aria-label", addLabel);
        $("tileVariantAdd").title = addLabel;
        const clearLabel = globalThis.VTTUi("Alle Varianten entfernen");
        $("tileVariantClear").setAttribute("aria-label", clearLabel);
        $("tileVariantClear").title = clearLabel;
        $("tileVariantAdd").addEventListener("click", () => { ed.addTileVariant(ed.tileOpts.asset); this.renderTileVariants(); });
        $("tileVariantClear").addEventListener("click", () => { ed.tileOpts.variants = []; this.renderTileVariants(); });
        this.renderTileVariants();
        $("tileSize").value = String(ed.tileOpts.size);
        $("tileSize").addEventListener("change", (event) => {
            ed.tileOpts.size = Number(event.target.value);
            const layer = ed.doc && ed.targetLayer("tiles", { quiet: true });
            if (layer) ed.setLayerProp(layer.id, "gridSize", ed.tileOpts.size);
            this.updateTargets();
            ed.requestFrame();
        });
        for (const id of ["tileSearch", "tilePack"]) {
            $(id).addEventListener(id === "tileSearch" ? "input" : "change", () => { this.tilePage = 0; this.renderTilePalette(); });
        }
        $("tilePrev").addEventListener("click", () => { this.tilePage -= 1; this.renderTilePalette(); });
        $("tileNext").addEventListener("click", () => { this.tilePage += 1; this.renderTilePalette(); });
    }

    buildTilePalette() {
        const { palette } = this.ed;
        const tileIds = palette.tileGroups.flatMap((group) => group.ids);
        $("tilePack").appendChild(el("option", { value: CUSTOM_PACK }, palette.customGroupName));
        for (const pack of palette.packs) {
            if (tileIds.some((id) => palette.stamps.get(id).pack === pack.id)) $("tilePack").appendChild(el("option", { value: pack.id }, pack.name));
        }
        this.renderTilePalette();
        if (tileIds.length) this.chooseTile(tileIds[0]);
        else $("tileSelected").textContent = globalThis.VTTUi("Noch keine Kachelpakete verfügbar.");
    }

    renderTilePalette() {
        const { palette } = this.ed;
        const normalize = (text) => text.toLocaleLowerCase("de").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        const terms = normalize($("tileSearch").value).trim().split(/\s+/).filter(Boolean);
        const pack = $("tilePack").value;
        const ids = palette.tileGroups.flatMap((group) => group.ids).filter((id) => {
            const stamp = palette.stamps.get(id);
            return (!pack || stamp.pack === pack) && terms.every((term) => stamp.searchText.includes(term));
        });
        const pageSize = 64;
        const pageCount = Math.max(1, Math.ceil(ids.length / pageSize));
        this.tilePage = Math.max(0, Math.min(this.tilePage, pageCount - 1));
        $("tileResults").textContent = ids.length
            ? globalThis.VTTUi("{p0} Kacheln · Seite {p1} von {p2}",{p0:(ids.length.toLocaleString("de")),p1:(this.tilePage + 1),p2:(pageCount)})
            : globalThis.VTTUi("Keine Kacheln gefunden. Suche oder Filter ändern.");
        $("tilePrev").disabled = this.tilePage === 0;
        $("tileNext").disabled = this.tilePage >= pageCount - 1;
        const container = $("tilePalette");
        container.replaceChildren();
        let currentGroup = null;
        let grid = null;
        for (const id of ids.slice(this.tilePage * pageSize, (this.tilePage + 1) * pageSize)) {
            const stamp = palette.stamps.get(id);
            if (stamp.group !== currentGroup) {
                currentGroup = stamp.group;
                const section = el("div", { class: "mm-tile-group" });
                section.appendChild(el("h3", { class: "mm-h3" }, stamp.group));
                grid = el("div", { class: "mm-palette-grid", role: "radiogroup", "aria-label": stamp.group });
                section.appendChild(grid);
                container.appendChild(section);
            }
            const button = el("button", { type: "button", class: "mm-tile-btn", role: "radio", "aria-checked": String(this.ed.tileOpts.asset === id),
                "aria-label": stamp.label, title: `${stamp.label} · ${stamp.packName}`, dataset: { tile: id } });
            button.appendChild(stampThumb(stamp, 48));
            button.appendChild(el("span", {}, stamp.label));
            button.addEventListener("click", () => this.chooseTile(id));
            grid.appendChild(button);
        }
    }

    renderTileVariants() {
        const ed = this.ed, list = $("tileVariantList");
        list.replaceChildren();
        $("tileVariantClear").disabled = !ed.tileOpts.variants.length;
        for (const id of ed.tileOpts.variants) {
            const stamp = ed.palette.stamps.get(id);
            if (!stamp) continue;
            const item = el("li", { class: "mm-variant-chip", dataset: { tile: id } });
            item.appendChild(stampThumb(stamp, 32, stamp.label));
            const remove = el("button", { type: "button", class: "mm-btn mm-btn-small", "aria-label": globalThis.VTTUi("Variante „{p0}“ entfernen", { p0: stamp.label }) }, "×");
            remove.addEventListener("click", () => { ed.tileOpts.variants = ed.tileOpts.variants.filter((entry) => entry !== id); this.renderTileVariants(); });
            item.appendChild(remove);
            list.appendChild(item);
        }
    }

    chooseTile(id) {
        const ed = this.ed;
        const stamp = ed.palette.stamps.get(id);
        if (!stamp) return;
        ed.tileOpts.asset = id;
        if (ed.tileOpts.erase) {
            ed.tileOpts.erase = false;
            $("tileMode").value = "paint";
        }
        $("tileSelected").textContent = globalThis.VTTUi("Kachel: {p0} · {p1}",{p0:(stamp.label),p1:(stamp.packName)});
        document.querySelectorAll(".mm-tile-btn").forEach((button) => button.setAttribute("aria-checked", String(button.dataset.tile === id)));
        ed.palette.loadStamp(id).then(() => ed.requestFrame()).catch(() => this.toast(globalThis.VTTUi("Die Kachel konnte nicht geladen werden.")));
    }

    bindPath() {
        const ed = this.ed;
        this.pathWidth = this.range("pathWidth", "pathWidthOut", (v) => `${v} px`, (v) => { ed.pathOpts.width = v; });
        this.pathWidth.set(ed.pathOpts.width);
        $("pathMaterial").addEventListener("change", (event) => { ed.pathOpts.material = event.target.value; });
    }

    buildPalette() {
        const { palette } = this.ed;
        this.palettePage = 0;
        const packSelect = $("stampPack");
        // Own images are listed per opened project; the option is always offered.
        packSelect.appendChild(el("option", { value: CUSTOM_PACK }, palette.customGroupName));
        $("stampCategory").appendChild(el("option", { value: palette.customGroupName }, palette.customGroupName));
        for (const pack of palette.packs) {
            if ([...palette.stamps.values()].some((stamp) => stamp.pack === pack.id)) {
                packSelect.appendChild(el("option", { value: pack.id }, pack.name));
            }
        }
        for (const group of palette.groups) {
            if (group.ids.length && !group.custom) $("stampCategory").appendChild(el("option", { value: group.name }, group.name));
        }
        $("stampCrop").addEventListener("click", () => this.openSheet(this.ed.stampOpts.asset));
        this.bindSheet();
        for (const id of ["stampSearch", "stampPack", "stampCategory"]) {
            $(id).addEventListener(id === "stampSearch" ? "input" : "change", () => {
                this.palettePage = 0;
                this.renderPalette();
            });
        }
        $("stampPrev").addEventListener("click", () => { this.palettePage -= 1; this.renderPalette(); });
        $("stampNext").addEventListener("click", () => { this.palettePage += 1; this.renderPalette(); });
        if (palette.packError) {
            $("packNote").hidden = false;
            $("packNote").textContent = palette.packError;
        }
        const first = palette.stamps.has("kenney:forest") ? "kenney:forest" : palette.groups.find((g) => g.ids.length).ids[0];
        this.renderPalette();
        this.chooseStamp(first);
        this.buildTilePalette();
    }

    renderPalette() {
        const { palette } = this.ed;
        const normalize = (text) => text.toLocaleLowerCase("de").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        const terms = normalize($("stampSearch").value).trim().split(/\s+/).filter(Boolean);
        const pack = $("stampPack").value;
        const category = $("stampCategory").value;
        const style = $("stampStyle").value, perspective = $("stampPerspective").value;
        // Matching symbols hidden only because they make no style/perspective claim (shown as a count, never guessed).
        let undeclared = 0;
        const ids = palette.groups.flatMap((group) => group.ids).filter((id) => {
            const stamp = palette.stamps.get(id);
            const text = stamp.searchText || normalize(`${stamp.label} ${stamp.group} ${stamp.packName} ${stamp.search}`);
            if ((pack && stamp.pack !== pack) || (category && stamp.group !== category) || !terms.every((term) => text.includes(term))) return false;
            const traits = assetTraits(stamp);
            const failing = [[traits.style, style], [traits.perspective, perspective]].filter(([value, filter]) => !traitMatches(value, filter));
            if (!failing.length) return true;
            if (failing.every(([value, filter]) => value === null && filter !== TRAIT_UNKNOWN)) undeclared += 1;
            return false;
        });
        const pageSize = 64;
        const pageCount = Math.max(1, Math.ceil(ids.length / pageSize));
        this.palettePage = Math.max(0, Math.min(this.palettePage, pageCount - 1));
        const count = undeclared.toLocaleString("de");
        $("stampResults").textContent = ids.length
            ? globalThis.VTTUi("{p0} Symbole · Seite {p1} von {p2}",{p0:(ids.length.toLocaleString("de")),p1:(this.palettePage + 1),p2:(pageCount)})
                + (undeclared ? ` · ${globalThis.VTTUi("{count} weitere ohne Stil-/Perspektivangabe ausgeblendet", { count })}` : "")
            : undeclared
                ? globalThis.VTTUi("Keine Symbole mit dieser Angabe. {count} passende Symbole haben keine Stil-/Perspektivangabe – „Ohne Angabe“ zeigt sie.", { count })
                : globalThis.VTTUi("Keine Symbole gefunden. Suche oder Filter ändern.");
        $("stampFilterReset").hidden = !STAMP_FILTER_IDS.some((id) => $(id).value);
        $("stampPrev").disabled = this.palettePage === 0;
        $("stampNext").disabled = this.palettePage >= pageCount - 1;
        const container = $("palette");
        container.replaceChildren();
        let currentGroup = null;
        let grid = null;
        const pageIds = ids.slice(this.palettePage * pageSize, (this.palettePage + 1) * pageSize);
        this.palettePageIds = pageIds;
        this.updateSymbolOptions(pageIds);
        for (const id of pageIds) {
            const stamp = palette.stamps.get(id);
            if (stamp.group !== currentGroup) {
                currentGroup = stamp.group;
                const section = el("div", { class: "mm-palette-group" });
                section.appendChild(el("h3", { class: "mm-h3" }, stamp.group));
                grid = el("div", { class: "mm-palette-grid", role: "radiogroup", "aria-label": stamp.group });
                section.appendChild(grid);
                container.appendChild(section);
            }
            const button = el("button", { type: "button", class: "mm-stamp", role: "radio", "aria-checked": String(this.ed.stampOpts.asset === id), "aria-label": stamp.label, title: `${stamp.label} · ${stamp.packName}`, dataset: { asset: id } });
            if (stamp.src) {
                const thumb = el("img", { src: stamp.src, width: 56, height: 56, alt: "", loading: "lazy", decoding: "async", class: stamp.pixelArt ? "mm-pixel" : null });
                thumb.addEventListener("error", () => {
                    button.disabled = true;
                    button.title = globalThis.VTTUi("{p0} – Bild konnte nicht geladen werden",{p0:(stamp.label)});
                    $("packNote").hidden = false;
                    $("packNote").textContent = globalThis.VTTUi("Einige Symbolbilder fehlen. Bitte neu laden oder ein anderes Paket wählen.");
                });
                button.appendChild(thumb);
            } else button.appendChild(stampThumb(stamp, 56));
            button.appendChild(el("span", {}, stamp.label));
            button.addEventListener("click", () => this.chooseStamp(id));
            grid.appendChild(button);
        }
    }

    chooseStamp(id, { crop = null, openSheet = true, size = null } = {}) {
        const ed = this.ed;
        const stamp = ed.palette.stamps.get(id);
        if (!stamp) return;
        this.pendingStamp = id;
        const select = () => {
            if (this.pendingStamp !== id) return;
            ed.stampOpts.asset = id;
            ed.stampOpts.crop = crop;
            const remembered = this.stampSizes.get(this.stampSizeKey(id, crop));
            ed.stampOpts.size = size !== null ? clamp(size,16,320) : remembered ?? (crop ? Math.min(256, Math.max(16, crop.w, crop.h)) : stamp.defaultSize);
            if (size !== null) this.rememberStampSize();
            this.stampSize.set(ed.stampOpts.size);
            this.recentStamps = [id, ...this.recentStamps.filter((entry) => entry !== id)].slice(0, 12);
            this.updateSymbolOptions(this.palettePageIds || []);
            $("stampSelected").textContent = globalThis.VTTUi("Ausgewählt: {p0} · {p1}",{p0:(stamp.label),p1:(stamp.packName)});
            document.querySelectorAll(".mm-stamp").forEach((button) => {
                button.setAttribute("aria-checked", String(button.dataset.asset === id));
            });
            $("stampCrop").disabled = !(stamp.src || stamp.custom); // built-ins have no source pixels to crop
            if (crop) $("stampSelected").textContent += globalThis.VTTUi(" · Ausschnitt {p0}×{p1}",{p0:(crop.w),p1:(crop.h)});
            ed.requestFrame();
            if (stamp.sheet && openSheet) this.openSheet(id);
        };
        if (stamp.image) select();
        else ed.palette.loadStamp(id).then(select).catch(() => {
            this.toast(globalThis.VTTUi("Das Symbol konnte nicht geladen werden. Bitte ein anderes wählen oder neu laden."));
        });
    }

    /** Session tool size per asset; a crop and the whole sheet have different natural sizes. */
    stampSizeKey(id, crop) {
        return crop ? `${id}@${crop.x},${crop.y},${crop.w},${crop.h}` : id;
    }

    rememberStampSize() {
        const { asset, crop, size } = this.ed.stampOpts;
        if (asset) this.stampSizes.set(this.stampSizeKey(asset, crop), size);
    }

    symbolOption(id) {
        const stamp = this.ed.palette.stamps.get(id);
        return stamp ? el("option", { value: id }, `${stamp.label} · ${stamp.packName}`) : null;
    }

    ensureSymbolOption(select, id) {
        if (id && ![...select.options].some((option) => option.value === id)) {
            const option = this.symbolOption(id);
            if (option) select.appendChild(option);
        }
    }

    /** Place symbols come from deliberate sources: recently chosen stamps, then the current palette page. */
    updateSymbolOptions(ids) {
        const ed = this.ed, t = globalThis.VTTUi;
        const recent = this.recentStamps.filter((id) => ed.assetAvailable(id));
        const groups = [[t("Zuletzt gewählte Symbole"), recent], [t("Aktuelle Symbolpalette"), ids.filter((id) => !recent.includes(id))]];
        for (const select of [$("placeSymbol"), $("selSymbol")]) {
            const value = select.value;
            select.replaceChildren(el("option", { value: "" }, t("Kein Symbol")));
            for (const [label, group] of groups) {
                const options = group.map((id) => this.symbolOption(id)).filter(Boolean);
                if (!options.length) continue;
                const optgroup = el("optgroup", { label });
                optgroup.append(...options);
                select.appendChild(optgroup);
            }
            for (const id of [value, ed.labelOpts.symbol]) this.ensureSymbolOption(select, id);
            select.value = value;
        }
    }

    bindSheet() {
        const dialog = $("sheetDialog"), canvas = $("sheetCanvas");
        $("sheetZoom").addEventListener("change", () => {
            const stamp = this.ed.palette.stamps.get(this.sheetId), value = $("sheetZoom").value;
            canvas.style.maxWidth = value === "fit" ? "100%" : "none";
            canvas.style.width = value === "fit" ? "" : `${stamp.w * Number(value)}px`;
        });
        $("sheetCancel").addEventListener("click", () => dialog.close());
        dialog.addEventListener("close", () => { this.sheetAlphaCache = null; });
        $("sheetFitContent").addEventListener("click", () => {
            const stamp = this.ed.palette.stamps.get(this.sheetId), crop = this.readSheetCrop(), alpha = stamp && this.sheetAlpha(stamp);
            if (!crop || !alpha) return;
            const fitted = fitCropToContent(crop, alpha);
            if (!fitted) { $("sheetCropInfo").textContent = globalThis.VTTUi("Der Ausschnitt enthält keine sichtbaren Pixel."); return; }
            for (const key of ["x", "y", "w", "h"]) $("sheet" + key.toUpperCase()).value = fitted[key];
            this.drawSheet();
        });
        $("sheetWhole").addEventListener("click", () => { this.chooseStamp(this.sheetId, { openSheet: false }); dialog.close(); });
        $("sheetUse").addEventListener("click", () => {
            const crop = this.readSheetCrop();
            if (!crop) return;
            this.chooseStamp(this.sheetId, { crop, openSheet: false }); dialog.close();
        });
        for (const key of ["X", "Y", "W", "H"]) $(`sheet${key}`).addEventListener("input", () => this.drawSheet());
        const point = (event) => {
            const rect = canvas.getBoundingClientRect(), stamp = this.ed.palette.stamps.get(this.sheetId);
            const step = Math.max(1, Number($("sheetGrid").value) || 1);
            return { x: Math.min(stamp.w - 1, Math.max(0, Math.floor((event.clientX - rect.left) / rect.width * stamp.w / step) * step)), y: Math.min(stamp.h - 1, Math.max(0, Math.floor((event.clientY - rect.top) / rect.height * stamp.h / step) * step)), step };
        };
        canvas.addEventListener("pointerdown", (event) => { event.preventDefault(); this.sheetStart = point(event); canvas.setPointerCapture(event.pointerId); this.selectSheetRect(this.sheetStart, this.sheetStart); });
        canvas.addEventListener("pointermove", (event) => { if (this.sheetStart) this.selectSheetRect(this.sheetStart, point(event)); });
        for (const name of ["pointerup", "pointercancel", "lostpointercapture"]) canvas.addEventListener(name, () => { this.sheetStart = null; });
    }

    selectSheetRect(a, b) {
        const stamp = this.ed.palette.stamps.get(this.sheetId);
        const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y);
        const w = Math.min(stamp.w - x, Math.abs(a.x - b.x) + a.step), h = Math.min(stamp.h - y, Math.abs(a.y - b.y) + a.step);
        for (const [key, value] of Object.entries({ X:x, Y:y, W:w, H:h })) $(`sheet${key}`).value = value;
        this.drawSheet();
    }

    readSheetCrop() {
        const stamp = this.ed.palette.stamps.get(this.sheetId);
        const crop = Object.fromEntries(["x", "y", "w", "h"].map((key) => [key, Number($("sheet" + key.toUpperCase()).value)]));
        const valid = Object.values(crop).every(Number.isInteger) && crop.x >= 0 && crop.y >= 0 && crop.w > 0 && crop.h > 0 && crop.x + crop.w <= stamp.w && crop.y + crop.h <= stamp.h;
        $("sheetUse").disabled = !valid;
        $("sheetError").hidden = valid;
        return valid ? crop : null;
    }

    drawSheet() {
        const stamp = this.ed.palette.stamps.get(this.sheetId), canvas = $("sheetCanvas"), ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height); ctx.imageSmoothingEnabled = !stamp.pixelArt;
        ctx.drawImage(stamp.image, 0, 0, canvas.width, canvas.height);
        const crop = this.readSheetCrop();
        if (crop) {
            const sx = canvas.width / stamp.w, sy = canvas.height / stamp.h;
            ctx.fillStyle = "rgba(220,170,40,0.25)"; ctx.fillRect(crop.x*sx, crop.y*sy, crop.w*sx, crop.h*sy);
            ctx.strokeStyle = "#ffca4b"; ctx.lineWidth = 2; ctx.strokeRect(crop.x*sx+1, crop.y*sy+1, Math.max(1,crop.w*sx-2), Math.max(1,crop.h*sy-2));
        }
        this.drawCropCompare(stamp, crop);
    }

    /** Opaque-pixel map of the open source image (bounded), cached while the dialog is open. */
    sheetAlpha(stamp) {
        if (this.sheetAlphaCache && this.sheetAlphaCache.id === stamp.id) return this.sheetAlphaCache;
        if (!stamp.image || stamp.w * stamp.h > 4096 * 4096) return null;
        const canvas = document.createElement("canvas"); canvas.width = stamp.w; canvas.height = stamp.h;
        const ctx = canvas.getContext("2d", { willReadFrequently: true }); ctx.drawImage(stamp.image, 0, 0);
        const data = ctx.getImageData(0, 0, stamp.w, stamp.h).data, alpha = new Uint8Array(stamp.w * stamp.h);
        for (let i = 0; i < alpha.length; i += 1) alpha[i] = data[i * 4 + 3] > 8 ? 1 : 0;
        canvas.width = 0; canvas.height = 0;
        this.sheetAlphaCache = { id: stamp.id, w: stamp.w, h: stamp.h, alpha };
        return this.sheetAlphaCache;
    }

    /** Source-versus-crop comparison: the crop at true pixels and whether content runs past an edge. */
    drawCropCompare(stamp, crop) {
        const preview = $("sheetCropPreview"), info = $("sheetCropInfo");
        if (!crop) { preview.width = preview.height = 1; info.textContent = ""; return; }
        const scale = Math.min(4, 160 / Math.max(crop.w, crop.h));
        preview.width = Math.max(1, Math.round(crop.w * scale)); preview.height = Math.max(1, Math.round(crop.h * scale));
        preview.style.imageRendering = stamp.pixelArt ? "pixelated" : "auto";
        const pctx = preview.getContext("2d"); pctx.imageSmoothingEnabled = !stamp.pixelArt;
        pctx.clearRect(0, 0, preview.width, preview.height);
        pctx.drawImage(stamp.image, crop.x, crop.y, crop.w, crop.h, 0, 0, preview.width, preview.height);
        const alpha = this.sheetAlpha(stamp);
        const parts = [globalThis.VTTUi("Quelle {w}×{h} px · Ausschnitt {cw}×{ch} px ab {x},{y}", { w: stamp.w, h: stamp.h, cw: crop.w, ch: crop.h, x: crop.x, y: crop.y })];
        if (alpha) {
            const cut = cropCutSides(crop, alpha);
            const names = { top: globalThis.VTTUi("oben"), right: globalThis.VTTUi("rechts"), bottom: globalThis.VTTUi("unten"), left: globalThis.VTTUi("links") };
            parts.push(cut.length ? globalThis.VTTUi("Sichtbarer Inhalt läuft über den Rand ({sides}) – vermutlich abgeschnitten.", { sides: cut.map((side) => names[side]).join(", ") })
                : globalThis.VTTUi("Kein sichtbarer Inhalt wird am Rand abgeschnitten."));
        }
        info.textContent = parts.join(" ");
    }

    sheetDefaultCrop(stamp) {
        if (stamp.initialCrop) return stamp.initialCrop;
        const grid = stamp.grid || 1;
        if (grid === 1) return { x: 0, y: 0, w: stamp.w, h: stamp.h };
        const canvas = document.createElement("canvas"); canvas.width = stamp.w; canvas.height = stamp.h;
        const ctx = canvas.getContext("2d", { willReadFrequently: true }); ctx.drawImage(stamp.image, 0, 0);
        const pixels = ctx.getImageData(0, 0, stamp.w, stamp.h).data;
        let crop = { x: 0, y: 0, w: Math.min(grid, stamp.w), h: Math.min(grid, stamp.h) };
        outer: for (let y = 0; y < stamp.h; y += grid) for (let x = 0; x < stamp.w; x += grid) {
            const w = Math.min(grid, stamp.w - x), h = Math.min(grid, stamp.h - y);
            for (let dy = 0; dy < h; dy += 1) for (let dx = 0; dx < w; dx += 1) {
                if (pixels[((y + dy) * stamp.w + x + dx) * 4 + 3] > 0) {
                    crop = { x, y, w, h }; break outer;
                }
            }
        }
        canvas.width = 0; canvas.height = 0; stamp.initialCrop = crop; return crop;
    }

    openSheet(id) {
        const stamp = this.ed.palette.stamps.get(id);
        if (!stamp || !stamp.image) return;
        this.sheetId = id; this.sheetStart = null;
        $("sheetName").textContent = globalThis.VTTUi("{p0} · {p1}×{p2} Pixel",{p0:(stamp.label),p1:(stamp.w),p2:(stamp.h)});
        const canvas = $("sheetCanvas"), scale = Math.min(2, 960 / Math.max(stamp.w, stamp.h));
        canvas.width = Math.max(1, Math.round(stamp.w*scale)); canvas.height = Math.max(1, Math.round(stamp.h*scale));
        $("sheetZoom").value = "fit"; canvas.style.width = ""; canvas.style.maxWidth = "100%";
        canvas.style.imageRendering = stamp.pixelArt ? "pixelated" : "auto";
        $("sheetGrid").value = stamp.grid || 1;
        const crop = this.ed.stampOpts.crop || this.sheetDefaultCrop(stamp);
        for (const key of ["x", "y", "w", "h"]) $("sheet"+key.toUpperCase()).value = crop[key];
        this.drawSheet(); if (!$("sheetDialog").open) $("sheetDialog").showModal();
    }

    bindLabelTool() {
        const ed = this.ed;
        const styleSelect = $("labelStyle");
        const kindSelect = $("labelKind");
        for (const select of [styleSelect, $("selStyle")]) {
            for (const [value, def] of Object.entries(LABEL_STYLES)) select.appendChild(el("option", { value }, def.name));
        }
        for (const select of [kindSelect, $("selKind")]) {
            select.appendChild(el("option", { value: "" }, globalThis.VTTUi("Nur Beschriftung")));
            for (const [value, name] of Object.entries(PLACE_KINDS)) select.appendChild(el("option", { value }, name));
        }
        styleSelect.value = ed.labelOpts.style;
        kindSelect.value = ed.labelOpts.kind;
        styleSelect.addEventListener("change", () => { ed.labelOpts.style = styleSelect.value; });
        kindSelect.addEventListener("change", () => { ed.labelOpts.kind = kindSelect.value; });
        $("placeSymbol").addEventListener("change", (event) => { ed.labelOpts.symbol = event.target.value || null; });
        this.placeSymbolSize = this.range("placeSymbolSize", "placeSymbolSizeOut", (v) => `${v} px`, (v) => { ed.labelOpts.symbolSize = v; });
        this.placeSymbolSize.set(ed.labelOpts.symbolSize);
        $("labelPin").addEventListener("change", (event) => { ed.labelOpts.pin = event.target.checked; });
    }

    bindInspector() {
        const ed = this.ed;
        const labels={undoVisible:globalThis.VTTUi('Rückgängig'),redoVisible:globalThis.VTTUi('Wiederholen'),
            groupScaleLabel:globalThis.VTTUi('Gemeinsame Größe (%)'),groupScaleApply:globalThis.VTTUi('Größe anwenden'),
            groupDelete:globalThis.VTTUi('Auswahl löschen'),groupClear:globalThis.VTTUi('Auswahl aufheben'),
            selPathCurveLabel:globalThis.VTTUi('Geglätteter Verlauf'),pathCurveLabel:globalThis.VTTUi('Geglätteter Verlauf'),
            pathNodeModeLabel:globalThis.VTTUi('Wegpunkte bearbeiten'),labelNamedLabel:globalThis.VTTUi('Name anzeigen'),
            tileAsSymbol:globalThis.VTTUi('Gewählte Kachel frei als Symbol platzieren'),
            pathEditHint:globalThis.VTTUi('Wegpunkte bearbeiten einschalten und einen sichtbaren Punkt ziehen. Umschalt + Ziehen funktioniert ebenfalls.'),
            selectionHint:globalThis.VTTUi('Auf freier Fläche einen Auswahlrahmen ziehen. Umschalt-Klick erweitert die Auswahl. Ziehen verschiebt die Auswahl; Entf löscht sie. Leertaste verschiebt die Ansicht.')};
        Object.entries(labels).forEach(([id,text])=>$(id).textContent=text);
        $('undoVisible').addEventListener('click',()=>ed.undo());$('redoVisible').addEventListener('click',()=>ed.redo());
        $('groupClear').addEventListener('click',()=>ed.select(null));$('groupDelete').addEventListener('click',()=>ed.deleteSelection());
        $('groupScaleApply').addEventListener('click',()=>{const f=Number($('groupScale').value)/100;if(Number.isFinite(f)&&f>=.1&&f<=5)ed.selectionSet.scale(f);$('groupScale').value='100';});
        $('selPathCurve').addEventListener('change',e=>{ed.liveEdit({curve:e.target.checked});ed.commitEdit();});
        $('pathNodeMode').addEventListener('change',e=>{
            ed.editPathNodes=e.target.checked;
            // Node dragging lives in the select tool; the path tool always draws a new path.
            if(e.target.checked&&ed.tool!=='select'){ed.setTool('select');this.toast(globalThis.VTTUi('Auswählen (V): Wegpunkte ziehen. Ohne Haken verschiebt Ziehen den ganzen Weg.'));}
            ed.requestFrame();
        });
        $('pathCurve').addEventListener('change',e=>{ed.pathOpts.curve=e.target.checked;});
        $('labelNamed').addEventListener('change',e=>{ed.labelOpts.named=e.target.checked;});
        $('tileAsSymbol').addEventListener('click',()=>{
            if(!ed.tileOpts.asset){this.toast(globalThis.VTTUi('Wähle zuerst eine Kachel.'));return;}
            this.chooseStamp(ed.tileOpts.asset,{openSheet:false,size:ed.activeLayer()?.kind==='tiles'?ed.activeLayer().grid.size:ed.tileOpts.size});ed.setTool('stamp');
        });
        const commit = () => ed.commitEdit();
        this.selStampSize = this.range("selStampSize", "selStampSizeOut", (v) => `${v} px`, (v) => ed.liveEdit({ size: v }));
        this.selStampRot = this.range("selStampRot", "selStampRotOut", (v) => `${v}°`, (v) => ed.liveEdit({ rot: v }));
        this.selSize = this.range("selSize", "selSizeOut", (v) => `${v} px`, (v) => ed.liveEdit({ size: v }));
        this.selRot = this.range("selRot", "selRotOut", (v) => `${v}°`, (v) => ed.liveEdit({ rot: v }));
        this.selSymbolSize = this.range("selSymbolSize", "selSymbolSizeOut", (v) => `${v} px`, (v) => {
            const found = findItem(ed.doc, ed.selection);
            if (found && found.item.symbol) ed.liveEdit({ symbol: { ...found.item.symbol, size: v } });
        });
        this.selPathWidth = this.range("selPathWidth", "selPathWidthOut", (v) => `${v} px`, (v) => ed.liveEdit({ width: v }));
        $("selPathWidth").addEventListener("change", commit);
        $("selPathWidthNumber").addEventListener("change", commit);
        $("selPathMaterial").addEventListener("change", (event) => { ed.liveEdit({ material: event.target.value }); commit(); });
        for (const id of ["selStampSize", "selStampRot", "selSize", "selRot", "selSymbolSize", "selColor", "selText", "selLore"]) {
            $(id).addEventListener("change", commit);
        }
        $("selStampFlip").addEventListener("change", (event) => { ed.liveEdit({ flip: event.target.checked }); commit(); });
        $("selPin").addEventListener("change", (event) => { ed.liveEdit({ pin: event.target.checked }); commit(); });
        $("selText").addEventListener("input", (event) => {
            const text = event.target.value.slice(0, LIMITS.labelText);
            const found=ed.selection && findItem(ed.doc,ed.selection);
            if(text.trim() || found?.item.pin || found?.item.symbol)ed.liveEdit({text});
        });
        $("selText").addEventListener("blur", (event) => {
            if (!event.target.value.trim()) this.refreshInspector();
        });
        $("selText").addEventListener("keydown", (event) => {
            if (event.key === "Enter") event.target.blur();
        });
        $("selColor").addEventListener("input", (event) => ed.liveEdit({ color: event.target.value.toLowerCase() }));
        $("selStyle").addEventListener("change", (event) => {
            const style = event.target.value;
            ed.liveEdit({ style, size: LABEL_STYLES[style].size });
            commit();
        });
        $("selKind").addEventListener("change", (event) => {
            const found = findItem(ed.doc, ed.selection);
            if (!found) return;
            const kind = event.target.value;
            ed.liveEdit({ place: kind ? { kind, lore: found.item.place ? found.item.place.lore : "" } : null,
                symbol: kind ? found.item.symbol : null });
            commit();
        });
        $("selSymbol").addEventListener("change", (event) => {
            ed.liveEdit({ symbol: event.target.value ? { asset: event.target.value, size: 56 } : null });
            commit();
            this.refreshInspector();
        });
        $("selLore").addEventListener("input", (event) => {
            const found = findItem(ed.doc, ed.selection);
            if (!found || !found.item.place) return;
            const lore = event.target.value.slice(0, LIMITS.lore);
            ed.liveEdit({ place: { kind: found.item.place.kind, lore } });
            $("selLoreCount").textContent = `${lore.length}/${LIMITS.lore}`;
        });
        $("selDelete").addEventListener("click", () => ed.deleteSelection());
        $("selDeselect").addEventListener("click", () => ed.select(null));
        $("showMapBtn").addEventListener("click", () => {
            $("app").dataset.sheet = "closed";
            const found = ed.selection && findItem(ed.doc, ed.selection);
            if (found) {
                const item = found.item;
                if ("points" in item) {
                    const bounds = pathBounds(item);
                    ed.centerOn(bounds.x + bounds.w / 2, bounds.y + bounds.h / 2);
                } else ed.centerOn(item.x, item.y);
            }
        });
    }

    focusLabelName() {
        this.openPane("tool");
        const input = $("selText");
        requestAnimationFrame(() => {
            input.focus({ preventScroll: false });
            input.select();
        });
    }

    refreshInspector() {
        const ed = this.ed;
        const box = $("inspector");
        const found = ed.selection && ed.doc ? findItem(ed.doc, ed.selection) : null;
        $("editPlacedLabel").disabled = !found || !("text" in found.item);
        const count=ed.doc?ed.selectionSet.count:0,group=count>1||!!ed.selectionSet.tiles;
        $('groupInspector').hidden=!group;
        if(group){
            $('groupTitle').textContent=globalThis.VTTUi('{count} ausgewählt',{count});
            $('groupHint').textContent=ed.selectionSet.tiles?globalThis.VTTUi('Kacheln bewegen sich in ganzen Rasterzellen. Belegte Zielzellen bleiben geschützt.'):globalThis.VTTUi('Die Auswahl gemeinsam ziehen oder löschen. Größe ändert die einzelnen Symbole und Beschriftungen.');
            const canScale=!ed.selectionSet.tiles && ed.selectionSet.objects.every(({item})=>!('points' in item));
            $('groupScaleRow').hidden=!canScale;$('groupScaleApply').hidden=!canScale;
            $('groupInspector').querySelector('.mm-order-row').hidden=!!ed.selectionSet.tiles;
            box.hidden=true;return;
        }
        if (!found) {
            box.hidden = true;
            return;
        }
        box.hidden = false;
        const { item } = found;
        const isStamp = "asset" in item;
        const isPath = "points" in item;
        $("inspectStamp").hidden = !isStamp;
        $("inspectPath").hidden = !isPath;
        $("inspectLabel").hidden = isStamp || isPath;
        $("showMapBtn").textContent = isPath ? globalThis.VTTUi("Weg auf Karte zeigen") : globalThis.VTTUi("Ort auf Karte zeigen");
        const editing = (id) => document.activeElement === $(id);
        if (isStamp) {
            const stamp = ed.palette.stamps.get(item.asset);
            $("inspectorTitle").textContent = globalThis.VTTUi("Symbol");
            $("selStampName").textContent = stamp ? stamp.label : item.asset;
            if (!editing("selStampSize")) this.selStampSize.set(Math.round(item.size));
            if (!editing("selStampRot")) this.selStampRot.set(Math.round(item.rot));
            $("selStampFlip").checked = !!item.flip;
        } else if (isPath) {
            const kind = item.material === "river" ? globalThis.VTTUi("Fluss") : globalThis.VTTUi("Weg");
            $("inspectorTitle").textContent = item.name ? `${kind}: ${item.name}` : kind;
            if (!editing("selPathName")) $("selPathName").value = item.name || "";
            $("selPathMaterial").value = item.material;
            $("selPathCurve").checked=!!item.curve;$("pathNodeMode").checked=ed.editPathNodes;
            $("pathEditHint").textContent = ed.tool === "path"
                ? globalThis.VTTUi("Im Wege-Werkzeug zeichnet Ziehen immer einen neuen Weg. „Wegpunkte bearbeiten“ wechselt zu Auswählen (V).")
                : globalThis.VTTUi("Wegpunkte bearbeiten einschalten und einen sichtbaren Punkt ziehen. Umschalt + Ziehen funktioniert ebenfalls.");
            if (!editing("selPathWidth") && !editing("selPathWidthNumber")) this.selPathWidth.set(item.width);
        } else {
            $("inspectorTitle").textContent = item.place ? globalThis.VTTUi("Ort") : globalThis.VTTUi("Beschriftung");
            if (!editing("selText")) $("selText").value = item.text;
            $("selStyle").value = item.style;
            $("selFont").value = item.font || "";
            if (!editing("selColor")) $("selColor").value = item.color;
            if (!editing("selSize")) this.selSize.set(Math.round(item.size));
            if (!editing("selRot")) this.selRot.set(Math.round(item.rot));
            $("selPin").checked = !!item.pin;
            $("selKind").value = item.place ? item.place.kind : "";
            $("selSymbol").disabled = !item.place;
            this.ensureSymbolOption($("selSymbol"), item.symbol ? item.symbol.asset : "");
            $("selSymbol").value = item.symbol ? item.symbol.asset : "";
            $("selSymbolSizeRow").hidden = !item.symbol;
            if (item.symbol && !editing("selSymbolSize")) this.selSymbolSize.set(item.symbol.size);
            const lore = $("selLore");
            lore.disabled = !item.place;
            if (!editing("selLore")) lore.value = item.place ? item.place.lore : "";
            $("selLoreCount").textContent = item.place ? `${lore.value.length}/${LIMITS.lore}` : globalThis.VTTUi("(nur für Orte)");
            const bounds = labelBounds(item);
            const replacedTitle = replacedTitleLabel(ed.doc);
            const overlaps = ed.doc.layers.filter((layer) => layer.kind === "labels" && layer.visible)
                .flatMap((layer) => layer.items)
                .filter((other) => other.id !== item.id && other !== replacedTitle)
                .filter((other) => {
                    const b = labelBounds(other);
                    return bounds.x < b.x + b.w && bounds.x + bounds.w > b.x
                        && bounds.y < b.y + b.h && bounds.y + bounds.h > b.y;
                });
            $("collisionHint").hidden = !overlaps.length;
            $("collisionHint").textContent = overlaps.length
                ? globalThis.VTTUi("Überlappt {p0} Beschriftung{p1}. Mit Auswählen (V) verschieben.",{p0:(overlaps.length),p1:(overlaps.length === 1 ? "" : "en")}) : "";
        }
    }

    // ---- layers ------------------------------------------------------------

    bindLayers() {
        const ed = this.ed;
        $("addRaster").addEventListener("click", () => ed.addLayer("raster"));
        $("addPaths").addEventListener("click", () => ed.addLayer("paths"));
        $("addStamps").addEventListener("click", () => ed.addLayer("stamps"));
        $("addTiles").addEventListener("click", () => ed.addLayer("tiles"));
        $("layerGrid").addEventListener("change", (event) => {
            const layer = ed.activeLayer();
            if (layer && layer.kind === "tiles") ed.setLayerProp(layer.id, "gridSize", Number(event.target.value));
        });
        $("addLabels").addEventListener("click", () => ed.addLayer("labels"));
        $("showTitle").addEventListener("change", (event) => ed.setMapStyle("showTitle", event.target.checked));
        $("seaTop").addEventListener("change", (event) => ed.setMapStyle("top", event.target.value));
        $("seaBottom").addEventListener("change", (event) => ed.setMapStyle("bottom", event.target.value));
        const opacity = this.range("layerOpacity", "layerOpacityOut", (v) => `${v} %`, (v) => {
            const layer = ed.activeLayer();
            if (!layer) return;
            if (!this.opacityEdit || this.opacityEdit.layer !== layer) this.opacityEdit = { layer, before: layer.opacity };
            layer.opacity = v / 100;
            ed.invalidate(null);
        });
        this.layerOpacity = opacity;
        opacity.input.addEventListener("change", () => {
            const edit = this.opacityEdit;
            this.opacityEdit = null;
            if (!edit) return;
            const value = edit.layer.opacity;
            edit.layer.opacity = edit.before;
            ed.setLayerProp(edit.layer.id, "opacity", value);
        });
        $("layerCoast").addEventListener("change", (event) => {
            const layer = ed.activeLayer();
            if (layer) ed.setLayerProp(layer.id, "coast", event.target.checked);
        });
    }

    refreshLayers() {
        const ed = this.ed;
        if (!ed.doc) return;
        this.refreshToolLayer();
        this.refreshClip();
        const focused = document.activeElement;
        const focusList = focused?.closest('#layerList, #stageLayerList');
        const focusLayer = focused?.closest('[data-layer]')?.dataset.layer;
        const focusControl = focused?.dataset.layerControl;
        const panelScroll = $("pane-tool").scrollTop;
        const stripScroll = $("stageLayerList").scrollLeft;
        const list = $("layerList");
        list.replaceChildren();
        const all = [...ed.doc.layers].reverse();
        const kind = $("layerFilterKind").value, term = $("layerFilterName").value.trim().toLowerCase();
        const content = $("layerFilterContent").value;
        const layers = all.filter((layer) => (!kind || layer.kind === kind) && this.layerMatchesSearch(layer, term)
            && (!content || (content === "used" ? this.layerUse.has(layer) : this.layerHasContent(layer) === (content === "filled"))));
        if ($("layerSort").value === "recent") layers.sort((a, b) => (this.layerUse.get(b) || 0) - (this.layerUse.get(a) || 0));
        layers.forEach((layer) => {
            const index = ed.doc.layers.indexOf(layer);
            const active = layer.id === ed.activeLayerId;
            const li = el("li", { class: `mm-layer${active ? " is-active" : ""}${layer.visible ? "" : " is-hidden"}`, dataset: { layer: layer.id } });
            const eye = el("button", { type: "button", class: "mm-icon-btn mm-eye", "aria-pressed": String(layer.visible), "aria-label": `${layer.name} ${layer.visible ? "ausblenden" : "einblenden"}`, title: layer.visible ? globalThis.VTTUi("Ausblenden") : globalThis.VTTUi("Einblenden") });
            eye.appendChild(svgIcon(layer.visible ? ICONS.eyeOn : ICONS.eyeOff));
            eye.dataset.layerControl = "visible";
            eye.addEventListener("click", () => ed.setLayerProp(layer.id, "visible", !layer.visible));
            const name = el("button", { type: "button", class: "mm-layer-name", "aria-current": active ? "true" : null, title: globalThis.VTTUi("Als aktive Ebene wählen") });
            name.dataset.layerControl = "select";
            name.append(el("span", { class: "mm-layer-title" }, layer.name), el("span", { class: `mm-kind mm-kind-${layer.kind}` }, `${KIND_LABEL[layer.kind]} · ${this.layerCount(layer)}`));
            name.addEventListener("click", () => ed.setActiveLayer(layer.id));
            name.addEventListener("dblclick", () => this.renameLayer(li, layer));
            const actions = el("div", { class: "mm-layer-actions" });
            const up = el("button", { type: "button", class: "mm-icon-btn", "aria-label": globalThis.VTTUi("{p0} nach oben",{p0:(layer.name)}), title: globalThis.VTTUi("Nach oben"), disabled: index === ed.doc.layers.length - 1, dataset: { layerControl: "up" } });
            up.appendChild(svgIcon(ICONS.up));
            up.addEventListener("click", () => ed.moveLayer(layer.id, 1));
            const down = el("button", { type: "button", class: "mm-icon-btn", "aria-label": globalThis.VTTUi("{p0} nach unten",{p0:(layer.name)}), title: globalThis.VTTUi("Nach unten"), disabled: index === 0, dataset: { layerControl: "down" } });
            down.appendChild(svgIcon(ICONS.down));
            down.addEventListener("click", () => ed.moveLayer(layer.id, -1));
            const rename = el("button", { type: "button", class: "mm-icon-btn", "aria-label": `${layer.name} umbenennen`, title: globalThis.VTTUi("Umbenennen") });
            rename.appendChild(svgIcon(ICONS.rename));
            rename.addEventListener("click", () => this.renameLayer(li, layer));
            const remove = el("button", { type: "button", class: "mm-icon-btn mm-danger-icon", "aria-label": globalThis.VTTUi("{p0} löschen",{p0:(layer.name)}), title: globalThis.VTTUi("Löschen"), disabled: ed.doc.layers.length <= 1 });
            remove.appendChild(svgIcon(ICONS.trash));
            remove.addEventListener("click", () => ed.deleteLayer(layer.id));
            actions.append(up, down, rename, remove);
            li.append(eye, name, actions);
            list.appendChild(li);
        });
        if (!layers.length) list.appendChild(el("li", { class: "mm-hint" }, globalThis.VTTUi("Keine passende Ebene.")));
        const strip = $("stageLayerList");
        strip.querySelectorAll('.mm-stage-layer').forEach((row) => row.remove());
        for (const layer of all) {
            const active = layer.id === ed.activeLayerId;
            const row = el("div", { class: `mm-stage-layer${active ? " is-active" : ""}${layer.visible ? "" : " is-hidden"}`, dataset: { layer: layer.id } });
            const label = el("label", { class: "mm-stage-layer-name", title: `${layer.name} · ${KIND_LABEL[layer.kind]} · ${this.layerCount(layer)}` });
            const radio = el("input", { type: "radio", name: "stage-active-layer", value: layer.id, checked: active, dataset: { layerControl: "select" } });
            radio.addEventListener("change", () => { if (radio.checked) ed.setActiveLayer(layer.id); });
            const caption = el("span", { class: "mm-stage-layer-caption" });
            caption.append(el("span", {}, layer.name), el("small", {}, KIND_LABEL[layer.kind]));
            label.append(radio, caption);
            const eye = el("button", { type: "button", class: "mm-icon-btn", "aria-pressed": String(layer.visible), "aria-label": globalThis.VTTUi("Sichtbarkeit von {name}", { name: layer.name }), dataset: { layerControl: "visible" } });
            eye.appendChild(svgIcon(layer.visible ? ICONS.eyeOn : ICONS.eyeOff));
            eye.addEventListener("click", () => ed.setLayerProp(layer.id, "visible", !layer.visible));
            row.append(label, eye);
            strip.appendChild(row);
        }
        strip.scrollLeft = stripScroll;
        if (this.stripActiveLayer !== ed.activeLayerId) {
            this.revealActiveStageLayer();
            this.stripActiveLayer = ed.activeLayerId;
        }
        const active = ed.activeLayer();
        $("layerProps").hidden = !active;
        if (active) {
            if (!this.opacityEdit) this.layerOpacity.set(Math.round(active.opacity * 100));
            $("layerCoastRow").hidden = active.kind !== "raster";
            $("layerCoast").checked = !!active.effects.coast;
            $('brushCoastControls').hidden = active.kind !== 'raster';
            $('brushCoastTarget').textContent = globalThis.VTTUi('Aktive Malebene: {p0}', {p0:active.name});
            $('brushCoast').checked = !!active.effects.coast;
            $('brushCoastColor').value = active.effects.coastColor || '#3b2a1a';
            $('brushCoastWidth').value = active.effects.coastWidth ?? 2.5;
            $('brushCoastWidthOut').textContent = `${active.effects.coastWidth ?? 2.5} px`;
            $("layerGridRow").hidden = active.kind !== "tiles";
            if (active.kind === "tiles") $("layerGrid").value = String(active.grid.size);
        }
        const addRaster = $("addRaster");
        addRaster.disabled = ed.doc.layers.length >= LIMITS.layers || !ed.canAddRaster();
        addRaster.title = addRaster.disabled ? globalThis.VTTUi("Für diese Kartengröße sind keine weiteren Malebenen möglich.") : "";
        $("addStamps").disabled = ed.doc.layers.length >= LIMITS.layers;
        $("addTiles").disabled = ed.doc.layers.length >= LIMITS.layers;
        $("addLabels").disabled = ed.doc.layers.length >= LIMITS.layers;
        $("addPaths").disabled = ed.doc.layers.length >= LIMITS.layers;
        if (focusList && focusLayer && focusControl) {
            const row = [...$(focusList.id).querySelectorAll('[data-layer]')].find((node) => node.dataset.layer === focusLayer);
            row?.querySelector(`[data-layer-control="${focusControl}"]`)?.focus({ preventScroll: true });
        }
        $("pane-tool").scrollTop = panelScroll;
    }

    noteLayerUse(layer) {
        if (layer) this.layerUse.set(layer, ++this.layerUseClock);
    }

    layerCount(layer) {
        return layer.kind === "raster" ? globalThis.VTTUi("Rasterbild") : globalThis.VTTUi("Elemente: {count}", { count: layer.kind === "tiles" ? layer.cells.size : layer.items.length });
    }

    layerMatchesSearch(layer, term) {
        if (!term || layer.name.toLowerCase().includes(term)) return true;
        const assetName = (id) => this.ed.palette.stamps.get(id)?.name || id || "";
        if (layer.kind === "tiles") return [...layer.cells.values()].some((id) => assetName(id).toLowerCase().includes(term));
        return (layer.items || []).some((item) => [item.name, item.text, assetName(item.asset)].some((value) => value?.toLowerCase().includes(term)));
    }

    layerHasContent(layer) {
        if (layer.kind !== "raster") return layer.kind === "tiles" ? layer.cells.size > 0 : layer.items.length > 0;
        const cached = this.rasterContent.get(layer);
        if (cached && cached.revision === layer.rev) return cached.filled;
        const { width, height } = layer.canvas, context = layer.canvas.getContext("2d");
        let filled = false;
        // Scan bounded strips only for an explicit content filter, and cache by raster revision.
        for (let y = 0; y < height && !filled; y += 64) {
            const bytes = context.getImageData(0, y, width, Math.min(64, height - y)).data;
            for (let index = 3; index < bytes.length; index += 4) {
                if (bytes[index]) { filled = true; break; }
            }
        }
        this.rasterContent.set(layer, { revision: layer.rev, filled });
        return filled;
    }

    syncStageLayers() {
        $("stageLayerTools").dataset.expanded = String(this.stageLayersExpanded);
        if (this.isNarrow()) $("activeLayerJump").setAttribute("aria-expanded", String(this.stageLayersExpanded));
        else $("activeLayerJump").removeAttribute("aria-expanded");
        $("activeLayerJump").setAttribute("aria-controls", this.isNarrow() ? "stageLayerPanel" : "pane-layers");
        if (!this.isNarrow() || this.stageLayersExpanded) this.revealActiveStageLayer();
    }

    revealActiveStageLayer() {
        const strip = $("stageLayerList"), row = strip.querySelector('input:checked')?.closest('.mm-stage-layer');
        if (!row) return;
        const box = row.getBoundingClientRect(), viewport = strip.getBoundingClientRect();
        if (box.left < viewport.left) strip.scrollLeft += box.left - viewport.left;
        else if (box.right > viewport.right) strip.scrollLeft += box.right - viewport.right;
    }

    openLayerManagement() {
        this.stageLayersExpanded = false;
        this.syncStageLayers();
        this.openPane("layers");
        $("layerList").querySelector('.mm-layer.is-active .mm-layer-name')?.focus({ preventScroll: true });
    }

    offerTileGrid(size) {
        this.tileGridOffer = { doc: this.ed.doc, size };
        const message = globalThis.VTTUi("Belegte Kacheln behalten ihre Größe. Für {size} px eine neue Ebene anlegen.", { size });
        for (const id of ["tileGridNotice", "layerGridNotice"]) { $(id).textContent = message; $(id).hidden = false; }
        for (const id of ["tileNewLayer", "layerNewGrid"]) { $(id).textContent = globalThis.VTTUi("Neue Kachelebene mit {size} px", { size }); $(id).hidden = false; }
        this.toast(message);
    }

    clearTileGridOffer() {
        this.tileGridOffer = null;
        for (const id of ["tileGridNotice", "layerGridNotice", "tileNewLayer", "layerNewGrid"]) $(id).hidden = true;
    }

    renameLayer(li, layer) {
        const nameButton = li.querySelector(".mm-layer-name");
        const input = el("input", { type: "text", class: "mm-layer-input", maxlength: LIMITS.layerName, "aria-label": globalThis.VTTUi("Neuer Ebenenname") });
        input.value = layer.name;
        nameButton.replaceWith(input);
        input.focus();
        input.select();
        let done = false;
        const finish = (save) => {
            if (done) return;
            done = true;
            const value = input.value.replace(/[\u0000-\u001f\u007f]/g, "").trim().slice(0, LIMITS.layerName);
            if (save && value && value !== layer.name) this.ed.setLayerProp(layer.id, "name", value);
            else this.refreshLayers();
        };
        input.addEventListener("keydown", (event) => {
            if (event.key === "Enter") finish(true);
            if (event.key === "Escape") {
                event.stopPropagation();
                finish(false);
            }
        });
        input.addEventListener("blur", () => finish(true));
    }

    // ---- places ------------------------------------------------------------

    refreshPlaces() {
        const ed = this.ed;
        if (!ed.doc) return;
        const list = $("placeList");
        list.replaceChildren();
        const places = ed.doc.layers.filter((l) => l.kind === "labels").flatMap((l) => l.items.filter((i) => i.place).map((i) => ({ layer: l, item: i })));
        if (!places.length) {
            list.appendChild(el("li", { class: "mm-empty" }, globalThis.VTTUi("Noch keine Orte. Setze einen mit dem Werkzeug „Ort“.")));
            return;
        }
        for (const { layer, item } of places) {
            const li = el("li");
            const button = el("button", { type: "button", class: `mm-place${item.id === ed.selection ? " is-selected" : ""}`, dataset: { item: item.id } });
            const head = el("span", { class: "mm-place-head" });
            head.append(el("strong", { class: "mm-place-name" }, item.text || globalThis.VTTUi("Symbol ohne Namen")), el("span", { class: "mm-place-kind" }, PLACE_KINDS[item.place.kind] || ""));
            button.appendChild(head);
            button.appendChild(el("span", { class: "mm-place-lore" }, item.place.lore || globalThis.VTTUi("Noch keine Beschreibung.")));
            if (!layer.visible) button.appendChild(el("span", { class: "mm-place-kind" }, globalThis.VTTUi("Ebene ausgeblendet")));
            button.addEventListener("click", () => {
                ed.setTool("select");
                ed.select(item.id);
                this.openPane("tool");
                ed.centerOn(item.x, item.y);
                this.focusLabelName();
            });
            li.appendChild(button);
            list.appendChild(li);
        }
    }

    // ---- panes, tools, status ----------------------------------------------

    isNarrow() {
        return window.matchMedia("(max-width: 760px)").matches;
    }

    togglePane(pane) {
        const app = $("app");
        if (this.isNarrow() && app.dataset.sheet === "open" && this.pane === pane) {
            app.dataset.sheet = "closed";
            return;
        }
        this.openPane(pane);
    }

    openPane(pane) {
        this.pane = pane;
        $("app").dataset.sheet = "open";
        document.querySelectorAll(".mm-tabs [role=tab]").forEach((tab) => {
            const on = tab.dataset.pane === pane;
            tab.setAttribute("aria-selected", String(on));
            tab.tabIndex = on ? 0 : -1;
        });
        for (const name of ["tool", "layers", "places"]) $(`pane-${name}`).hidden = name !== pane;
    }

    tabKeys(event) {
        const tabs = [...document.querySelectorAll(".mm-tabs [role=tab]")];
        const index = tabs.indexOf(event.currentTarget);
        let next = null;
        if (event.key === "ArrowRight") next = tabs[(index + 1) % tabs.length];
        if (event.key === "ArrowLeft") next = tabs[(index + tabs.length - 1) % tabs.length];
        if (next) {
            event.preventDefault();
            next.focus();
            this.openPane(next.dataset.pane);
        }
    }

    setTool(tool) {
        $("app").dataset.tool = tool;
        $("eraseScopeField").hidden = $("eraseScopeHint").hidden = tool !== "eraser";
        $("eraseScopeHint").textContent = globalThis.VTTUi("Der Radierer wirkt nur auf Raster, Kacheln und Symbole; Beschriftungen und Wege bleiben erhalten.");
        document.querySelectorAll(".mm-tool").forEach((button) => {
            button.setAttribute("aria-pressed", String(button.dataset.tool === tool));
        });
        document.querySelectorAll("[data-options]").forEach((node) => {
            node.hidden = !node.dataset.options.split(" ").includes(tool);
        });
        if (this.ed.updateCursorClass) this.ed.updateCursorClass();
        this.updateTargets();
        this.refreshInspector();
        this.refreshLayers();
        this.showAreaPlan(null);
        this.syncBrush();
        if (!this.isNarrow()) this.openPane("tool");
    }

    updateTargets() {
        const ed = this.ed;
        if (!ed.doc) return;
        $("activeLayerJump").textContent = globalThis.VTTUi("Ebene: {p0}",{p0:(ed.activeLayer()?.name || 'keine')});
        const name = (kind) => {
            const layer = ed.targetLayer(kind, { quiet: true });
            return layer ? layer.name : "keine passende Ebene";
        };
        $("brushTarget").textContent = name("raster");
        $("stampTarget").textContent = name("stamps");
        $("labelTarget").textContent = name("labels");
        $("pathTarget").textContent = ed.doc.layers.some((layer) => layer.kind === "paths") ? name("paths") : globalThis.VTTUi("Neue Ebene beim ersten Weg");
        const tiles = ed.targetLayer("tiles", { quiet: true });
        $("tileTarget").textContent = tiles ? tiles.name : globalThis.VTTUi("Neue Kachelebene bei der ersten Kachel");
        $("tileSize").value = String(tiles ? tiles.grid.size : ed.tileOpts.size);
        this.refreshToolLayer();
        this.refreshClip();
    }

    updateUndo() {
        $("undoBtn").disabled = !this.ed.history.canUndo;
        $("redoBtn").disabled = !this.ed.history.canRedo;
        $("undoVisible").disabled=!this.ed.history.canUndo;$("redoVisible").disabled=!this.ed.history.canRedo;
    }

    updateZoom() {
        $("zoomLevel").textContent = `${Math.round(this.ed.view.zoom * 100)} %`;
    }

    setStatus(state, time) {
        const status = $("saveStatus");
        status.dataset.state = state;
        let text = STATUS_TEXT[state] || "";
        if (state === "saved" && time) {
            text = `${text} ${new Date(time).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })}`;
        }
        status.textContent = text;
        status.title = state === "unavailable"
            ? globalThis.VTTUi("Dieser Browser erlaubt keine lokale Speicherung (z. B. privater Modus). Speichere die Karte über „Datei → Als Datei speichern“.")
            : state === "failed"
                ? globalThis.VTTUi("Die lokale Speicherung ist fehlgeschlagen (z. B. Speicher voll). Speichere die Karte als Datei.")
                : "";
    }

    toast(message) {
        const toast = $("toast");
        toast.textContent = message;
        toast.hidden = false;
        clearTimeout(this.toastTimer);
        this.toastTimer = setTimeout(() => {
            toast.hidden = true;
        }, 3200);
    }

    showError(message) {
        $("errorText").textContent = message;
        const dialog = $("errorDialog");
        if (!dialog.open) dialog.showModal();
    }

    openExport() {
        const { w, h } = this.ed.doc.size;
        $("exportLabel1").textContent = globalThis.VTTUi("1× – {p0} × {p1} px",{p0:(w),p1:(h)});
        const tooBig = w * h * 4 > 16777216;
        const two = document.querySelector("input[name=exportScale][value='2']");
        two.disabled = tooBig;
        $("exportLabel2").textContent = tooBig ? globalThis.VTTUi("2× – zu groß für Browser") : globalThis.VTTUi("2× – {p0} × {p1} px",{p0:(w * 2),p1:(h * 2)});
        if (tooBig) document.querySelector("input[name=exportScale][value='1']").checked = true;
        $("exportError").hidden = true;
        $("exportGo").disabled = false;
        $("exportBundle").disabled = false;
        $("exportDialog").showModal();
    }

    async runExport(bundle = false) {
        const go = bundle ? $("exportBundle") : $("exportGo");
        const scale = Number(document.querySelector("input[name=exportScale]:checked").value) === 2 ? 2 : 1;
        go.disabled = true;
        $("exportCancel").disabled = true;
        $("exportGo").disabled = true;
        $("exportBundle").disabled = true;
        go.textContent = globalThis.VTTUi("Wird erstellt …");
        try {
            await new Promise((resolve) => requestAnimationFrame(resolve));
            if (bundle) await this.ed.exportBundle(scale);
            else await this.ed.exportPng(scale);
            $("exportDialog").close();
            this.toast(bundle ? globalThis.VTTUi("PNG und Projekt exportiert.") : globalThis.VTTUi("PNG exportiert."));
        } catch (error) {
            const box = $("exportError");
            box.hidden = false;
            box.textContent = globalThis.VTTUi("Export fehlgeschlagen: {p0}",{p0:(error.message || error)});
        } finally {
            $("exportCancel").disabled = false;
            $("exportGo").disabled = false;
            $("exportBundle").disabled = false;
            go.textContent = bundle ? globalThis.VTTUi("PNG + Projekt (.zip)") : globalThis.VTTUi("Exportieren (PNG)");
        }
    }

    askRestore(draft) {
        const dialog = $("restoreDialog");
        const when = draft.savedAt ? new Date(draft.savedAt).toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" }) : "unbekannt";
        const title = draft.doc && draft.doc.meta && typeof draft.doc.meta.title === "string" ? draft.doc.meta.title.slice(0, LIMITS.title) : "Karte";
        $("restoreText").textContent = globalThis.VTTUi("„{p0}“ wurde zuletzt am {p1} in diesem Browser gespeichert. Möchtest du daran weiterarbeiten?",{p0:(title),p1:(when)});
        return new Promise((resolve) => {
            const done = (value) => {
                dialog.close();
                resolve(value);
            };
            $("restoreYes").onclick = () => done(true);
            $("restoreNo").onclick = () => done(false);
            dialog.oncancel = (event) => {
                event.preventDefault();
            };
            dialog.showModal();
            $("restoreYes").focus();
        });
    }

    confirmReplace() {
        if (!this.ed.hasUnsavedChanges()) return Promise.resolve(true);
        const dialog = $("replaceDialog");
        return new Promise((resolve) => {
            const finish = (value) => {
                dialog.close();
                resolve(value);
            };
            $("replaceCancel").onclick = () => finish(false);
            $("replaceDiscard").onclick = () => finish(true);
            $("replaceSave").onclick = async () => {
                const button = $("replaceSave");
                button.disabled = true;
                try {
                    if (await this.ed.savePrimary()) finish(true);
                } finally {
                    button.disabled = false;
                }
            };
            dialog.oncancel = (event) => {
                event.preventDefault();
                finish(false);
            };
            dialog.showModal();
            $("replaceCancel").focus();
        });
    }

    setLoading(text) {
        const overlay = $("loading");
        overlay.hidden = !text;
        $("loadingText").textContent = text;
    }

    ready() {
        this.setLoading("");
        $("app").dataset.state = "ready";
        this.ed.requestFrame();
    }

    fatal(error) {
        $("app").dataset.state = "error";
        $("loading").hidden = false;
        $("loading").classList.add("is-error");
        $("loadingText").textContent = globalThis.VTTUi("Die Kartenwerkstatt konnte nicht starten: {p0}",{p0:(error && error.message ? error.message : error)});
        $("reloadBtn").hidden = false;
    }

    refreshAll() {
        const ed = this.ed;
        $("mapTitle").value = ed.doc.meta.title;
        this.refreshMapStyle();
        this.setTool(ed.tool);
        this.refreshLayers();
        this.refreshPlaces();
        this.refreshInspector();
        this.updateUndo();
        this.updateZoom();
    }

    refreshMapStyle() {
        if (!this.ed.doc) return;
        $("showTitle").checked = !!this.ed.doc.meta.showTitle;
        $("seaTop").value = this.ed.doc.sea.top;
        $("seaBottom").value = this.ed.doc.sea.bottom;
    }
}
