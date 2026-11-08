// Panels, dialogs and status. All user-provided text is written via
// textContent/value only.

import { LABEL_STYLES, LIMITS, PLACE_KINDS, findItem, clamp } from "./document.js";
import { MATERIALS, brushTip, materialTile } from "./brush.js";
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

const KIND_LABEL = { raster: "Malen", paths: "Wege", stamps: "Symbole", labels: "Text" };

const STATUS_TEXT = {
    idle: "Noch keine Änderungen",
    pending: "Ungespeicherte Änderungen",
    saving: "Speichert …",
    saved: "Lokal gespeichert",
    failed: "Autosave fehlgeschlagen – bitte als Datei speichern",
    unavailable: "Autosave nicht verfügbar – bitte als Datei speichern",
};

export class UI {
    constructor(editor) {
        this.ed = editor;
        this.toastTimer = 0;
        this.pane = "tool";
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
                closeMenu();
                menuButton.focus();
            }
        });
        menu.querySelectorAll("button").forEach((button) => button.addEventListener("click", closeMenu));
        $("newBtn").addEventListener("click", () => $("newDialog").showModal());
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
        this.bindLabelTool();
        this.bindInspector();
        this.bindLayers();
        $("addPlaceBtn").addEventListener("click", () => {
            ed.setTool("label");
            this.openPane("tool");
            this.toast("Tippe auf die Karte, um den Ort zu setzen.");
        });
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
                this.syncMaterials();
                this.drawBrushPreview();
                const targetId = material.id === "land" ? "land"
                    : material.id === "river" || material.id === "road" ? "rivers" : "terrain";
                const target = ed.layerById(targetId);
                if (target && target.kind === "raster" && target.visible && target.id !== ed.activeLayerId) {
                    ed.setActiveLayer(target.id);
                    this.toast(`Malt jetzt auf „${target.name}“.`);
                }
            });
            container.appendChild(button);
        }
        this.brushSize = this.range("brushSize", "brushSizeOut", (v) => `${v} px`, (v) => { ed.brush.size = v; this.drawBrushPreview(); ed.requestFrame(); });
        this.brushOpacity = this.range("brushOpacity", "brushOpacityOut", (v) => `${v} %`, (v) => { ed.brush.opacity = v / 100; this.drawBrushPreview(); });
        this.brushSoftness = this.range("brushSoftness", "brushSoftnessOut", (v) => `${v} %`, (v) => { ed.brush.softness = v; this.drawBrushPreview(); });
        this.brushSize.set(ed.brush.size);
        this.brushOpacity.set(Math.round(ed.brush.opacity * 100));
        this.brushSoftness.set(ed.brush.softness);
        $("brushPressure").addEventListener("change", (event) => {
            ed.brush.pressureEnabled = event.target.checked;
        });
        this.syncMaterials();
        this.drawBrushPreview();
    }

    syncMaterials() {
        document.querySelectorAll(".mm-swatch").forEach((button) => {
            const on = button.dataset.material === this.ed.brush.material;
            button.setAttribute("aria-checked", String(on));
            button.tabIndex = on ? 0 : -1;
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
        const mask = document.createElement("canvas");
        mask.width = canvas.width;
        mask.height = canvas.height;
        const mctx = mask.getContext("2d");
        const tip = brushTip(radius, brush.softness);
        const step = Math.max(1, radius * 2 * 0.12);
        for (let x = 40; x <= canvas.width - 40; x += step) {
            const y = canvas.height / 2 + Math.sin((x / canvas.width) * Math.PI * 2) * 14;
            mctx.drawImage(tip.canvas, x - tip.offset, y - tip.offset);
        }
        mctx.globalCompositeOperation = "source-in";
        if (tool === "eraser") mctx.fillStyle = "#2f5d6e";
        else mctx.fillStyle = mctx.createPattern(materialTile(brush.material), "repeat");
        mctx.fillRect(0, 0, mask.width, mask.height);
        ctx.globalAlpha = brush.opacity;
        ctx.drawImage(mask, 0, 0);
        ctx.globalAlpha = 1;
    }

    nudge(kind, up) {
        const ed = this.ed;
        if (ed.tool === "stamp" && kind === "size") {
            const value = clamp(Math.round(ed.stampOpts.size * (up ? 1.15 : 1 / 1.15)), 16, 320);
            ed.stampOpts.size = value;
            this.stampSize.set(value);
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
        this.stampSize = this.range("stampSize", "stampSizeOut", (v) => `${v} px`, (v) => { ed.stampOpts.size = v; ed.requestFrame(); });
        this.stampRot = this.range("stampRot", "stampRotOut", (v) => `${v}°`, (v) => { ed.stampOpts.rot = v; ed.requestFrame(); });
        this.stampSize.set(ed.stampOpts.size);
        this.stampRot.set(ed.stampOpts.rot);
        $("stampFlip").addEventListener("change", (event) => { ed.stampOpts.flip = event.target.checked; ed.requestFrame(); });
        $("stampVary").addEventListener("change", (event) => { ed.stampOpts.vary = event.target.checked; });
        $("stampScatter").addEventListener("change", (event) => { ed.stampOpts.scatter = event.target.checked; });
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
        for (const pack of palette.packs) {
            if ([...palette.stamps.values()].some((stamp) => stamp.pack === pack.id)) {
                packSelect.appendChild(el("option", { value: pack.id }, pack.name));
            }
        }
        for (const group of palette.groups) {
            if (group.ids.length) $("stampCategory").appendChild(el("option", { value: group.name }, group.name));
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
    }

    renderPalette() {
        const { palette } = this.ed;
        const normalize = (text) => text.toLocaleLowerCase("de").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        const terms = normalize($("stampSearch").value).trim().split(/\s+/).filter(Boolean);
        const pack = $("stampPack").value;
        const category = $("stampCategory").value;
        const ids = palette.groups.flatMap((group) => group.ids).filter((id) => {
            const stamp = palette.stamps.get(id);
            const text = stamp.searchText || normalize(`${stamp.label} ${stamp.group} ${stamp.packName} ${stamp.search}`);
            return (!pack || stamp.pack === pack) && (!category || stamp.group === category) && terms.every((term) => text.includes(term));
        });
        const pageSize = 64;
        const pageCount = Math.max(1, Math.ceil(ids.length / pageSize));
        this.palettePage = Math.max(0, Math.min(this.palettePage, pageCount - 1));
        $("stampResults").textContent = ids.length
            ? `${ids.length.toLocaleString("de")} Symbole · Seite ${this.palettePage + 1} von ${pageCount}`
            : "Keine Symbole gefunden. Suche oder Filter ändern.";
        $("stampPrev").disabled = this.palettePage === 0;
        $("stampNext").disabled = this.palettePage >= pageCount - 1;
        const container = $("palette");
        container.replaceChildren();
        let currentGroup = null;
        let grid = null;
        const pageIds = ids.slice(this.palettePage * pageSize, (this.palettePage + 1) * pageSize);
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
                const thumb = el("img", { src: stamp.src, width: 56, height: 56, alt: "", loading: "lazy", decoding: "async" });
                thumb.addEventListener("error", () => {
                    button.disabled = true;
                    button.title = `${stamp.label} – Bild konnte nicht geladen werden`;
                    $("packNote").hidden = false;
                    $("packNote").textContent = "Einige Symbolbilder fehlen. Bitte neu laden oder ein anderes Paket wählen.";
                });
                button.appendChild(thumb);
            } else {
                const thumb = el("canvas", { width: 56, height: 56, "aria-hidden": "true" });
                thumb.getContext("2d").drawImage(stamp.image, 4, 4, 48, 48);
                button.appendChild(thumb);
            }
            button.appendChild(el("span", {}, stamp.label));
            button.addEventListener("click", () => this.chooseStamp(id));
            grid.appendChild(button);
        }
    }

    chooseStamp(id, { crop = null, openSheet = true } = {}) {
        const ed = this.ed;
        const stamp = ed.palette.stamps.get(id);
        if (!stamp) return;
        this.pendingStamp = id;
        const select = () => {
            if (this.pendingStamp !== id) return;
            ed.stampOpts.asset = id;
            ed.stampOpts.crop = crop;
            ed.stampOpts.size = crop ? Math.min(256, Math.max(16, crop.w, crop.h)) : stamp.defaultSize;
            this.stampSize.set(ed.stampOpts.size);
            $("stampSelected").textContent = `Ausgewählt: ${stamp.label} · ${stamp.packName}`;
            document.querySelectorAll(".mm-stamp").forEach((button) => {
                button.setAttribute("aria-checked", String(button.dataset.asset === id));
            });
            $("stampCrop").disabled = !stamp.src;
            if (crop) $("stampSelected").textContent += ` · Ausschnitt ${crop.w}×${crop.h}`;
            ed.requestFrame();
            if (stamp.sheet && openSheet) this.openSheet(id);
        };
        if (stamp.image) select();
        else ed.palette.loadStamp(id).then(select).catch(() => {
            this.toast("Das Symbol konnte nicht geladen werden. Bitte ein anderes wählen oder neu laden.");
        });
    }

    ensureSymbolOption(select, id) {
        if (id && ![...select.options].some((option) => option.value === id)) {
            const stamp = this.ed.palette.stamps.get(id);
            if (stamp) select.appendChild(el("option", { value: id }, `${stamp.label} · ${stamp.packName}`));
        }
    }

    updateSymbolOptions(ids) {
        for (const select of [$("placeSymbol"), $("selSymbol")]) {
            const value = select.value;
            select.replaceChildren(el("option", { value: "" }, "Kein Symbol"));
            for (const id of new Set([...ids, value, this.ed.labelOpts.symbol].filter(Boolean))) this.ensureSymbolOption(select, id);
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
        $("sheetName").textContent = `${stamp.label} · ${stamp.w}×${stamp.h} Pixel`;
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
            select.appendChild(el("option", { value: "" }, "Nur Beschriftung"));
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
            if (text.trim()) ed.liveEdit({ text });
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
        $("showMapBtn").textContent = isPath ? "Weg auf Karte zeigen" : "Ort auf Karte zeigen";
        const editing = (id) => document.activeElement === $(id);
        if (isStamp) {
            const stamp = ed.palette.stamps.get(item.asset);
            $("inspectorTitle").textContent = "Symbol";
            $("selStampName").textContent = stamp ? stamp.label : item.asset;
            if (!editing("selStampSize")) this.selStampSize.set(Math.round(item.size));
            if (!editing("selStampRot")) this.selStampRot.set(Math.round(item.rot));
            $("selStampFlip").checked = !!item.flip;
        } else if (isPath) {
            $("inspectorTitle").textContent = item.material === "river" ? "Fluss" : "Weg";
            $("selPathMaterial").value = item.material;
            if (!editing("selPathWidth") && !editing("selPathWidthNumber")) this.selPathWidth.set(item.width);
        } else {
            $("inspectorTitle").textContent = item.place ? "Ort" : "Beschriftung";
            if (!editing("selText")) $("selText").value = item.text;
            $("selStyle").value = item.style;
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
            $("selLoreCount").textContent = item.place ? `${lore.value.length}/${LIMITS.lore}` : "(nur für Orte)";
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
                ? `Überlappt ${overlaps.length} Beschriftung${overlaps.length === 1 ? "" : "en"}. Mit Auswählen (V) verschieben.` : "";
        }
    }

    // ---- layers ------------------------------------------------------------

    bindLayers() {
        const ed = this.ed;
        $("addRaster").addEventListener("click", () => ed.addLayer("raster"));
        $("addPaths").addEventListener("click", () => ed.addLayer("paths"));
        $("addStamps").addEventListener("click", () => ed.addLayer("stamps"));
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
        const list = $("layerList");
        list.replaceChildren();
        const layers = [...ed.doc.layers].reverse();
        layers.forEach((layer, row) => {
            const active = layer.id === ed.activeLayerId;
            const li = el("li", { class: `mm-layer${active ? " is-active" : ""}${layer.visible ? "" : " is-hidden"}`, dataset: { layer: layer.id } });
            const eye = el("button", { type: "button", class: "mm-icon-btn mm-eye", "aria-pressed": String(layer.visible), "aria-label": `${layer.name} ${layer.visible ? "ausblenden" : "einblenden"}`, title: layer.visible ? "Ausblenden" : "Einblenden" });
            eye.appendChild(svgIcon(layer.visible ? ICONS.eyeOn : ICONS.eyeOff));
            eye.addEventListener("click", () => ed.setLayerProp(layer.id, "visible", !layer.visible));
            const name = el("button", { type: "button", class: "mm-layer-name", "aria-current": active ? "true" : null, title: "Als aktive Ebene wählen" });
            name.append(el("span", { class: "mm-layer-title" }, layer.name), el("span", { class: `mm-kind mm-kind-${layer.kind}` }, KIND_LABEL[layer.kind]));
            name.addEventListener("click", () => ed.setActiveLayer(layer.id));
            name.addEventListener("dblclick", () => this.renameLayer(li, layer));
            const actions = el("div", { class: "mm-layer-actions" });
            const up = el("button", { type: "button", class: "mm-icon-btn", "aria-label": `${layer.name} nach oben`, title: "Nach oben", disabled: row === 0 });
            up.appendChild(svgIcon(ICONS.up));
            up.addEventListener("click", () => ed.moveLayer(layer.id, 1));
            const down = el("button", { type: "button", class: "mm-icon-btn", "aria-label": `${layer.name} nach unten`, title: "Nach unten", disabled: row === layers.length - 1 });
            down.appendChild(svgIcon(ICONS.down));
            down.addEventListener("click", () => ed.moveLayer(layer.id, -1));
            const rename = el("button", { type: "button", class: "mm-icon-btn", "aria-label": `${layer.name} umbenennen`, title: "Umbenennen" });
            rename.appendChild(svgIcon(ICONS.rename));
            rename.addEventListener("click", () => this.renameLayer(li, layer));
            const remove = el("button", { type: "button", class: "mm-icon-btn mm-danger-icon", "aria-label": `${layer.name} löschen`, title: "Löschen", disabled: ed.doc.layers.length <= 1 });
            remove.appendChild(svgIcon(ICONS.trash));
            remove.addEventListener("click", () => ed.deleteLayer(layer.id));
            actions.append(up, down, rename, remove);
            li.append(eye, name, actions);
            list.appendChild(li);
        });
        const active = ed.activeLayer();
        $("layerProps").hidden = !active;
        if (active) {
            if (!this.opacityEdit) this.layerOpacity.set(Math.round(active.opacity * 100));
            $("layerCoastRow").hidden = active.kind !== "raster";
            $("layerCoast").checked = !!active.effects.coast;
        }
        const addRaster = $("addRaster");
        addRaster.disabled = ed.doc.layers.length >= LIMITS.layers || !ed.canAddRaster();
        addRaster.title = addRaster.disabled ? "Für diese Kartengröße sind keine weiteren Malebenen möglich." : "";
        $("addStamps").disabled = ed.doc.layers.length >= LIMITS.layers;
        $("addLabels").disabled = ed.doc.layers.length >= LIMITS.layers;
        $("addPaths").disabled = ed.doc.layers.length >= LIMITS.layers;
    }

    renameLayer(li, layer) {
        const nameButton = li.querySelector(".mm-layer-name");
        const input = el("input", { type: "text", class: "mm-layer-input", maxlength: LIMITS.layerName, "aria-label": "Neuer Ebenenname" });
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
            list.appendChild(el("li", { class: "mm-empty" }, "Noch keine Orte. Setze einen mit dem Werkzeug „Ort“."));
            return;
        }
        for (const { layer, item } of places) {
            const li = el("li");
            const button = el("button", { type: "button", class: `mm-place${item.id === ed.selection ? " is-selected" : ""}`, dataset: { item: item.id } });
            const head = el("span", { class: "mm-place-head" });
            head.append(el("strong", { class: "mm-place-name" }, item.text), el("span", { class: "mm-place-kind" }, PLACE_KINDS[item.place.kind] || ""));
            button.appendChild(head);
            button.appendChild(el("span", { class: "mm-place-lore" }, item.place.lore || "Noch keine Beschreibung."));
            if (!layer.visible) button.appendChild(el("span", { class: "mm-place-kind" }, "Ebene ausgeblendet"));
            button.addEventListener("click", () => {
                ed.setTool("select");
                ed.select(item.id);
                this.openPane("tool");
                ed.centerOn(item.x, item.y);
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
        this.drawBrushPreview();
        if (!this.isNarrow()) this.openPane("tool");
    }

    updateTargets() {
        const ed = this.ed;
        if (!ed.doc) return;
        const name = (kind) => {
            const layer = ed.targetLayer(kind, { quiet: true });
            return layer ? layer.name : "keine passende Ebene";
        };
        $("brushTarget").textContent = name("raster");
        $("stampTarget").textContent = name("stamps");
        $("labelTarget").textContent = name("labels");
        $("pathTarget").textContent = ed.doc.layers.some((layer) => layer.kind === "paths") ? name("paths") : "Neue Ebene beim ersten Weg";
    }

    updateUndo() {
        $("undoBtn").disabled = !this.ed.history.canUndo;
        $("redoBtn").disabled = !this.ed.history.canRedo;
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
            ? "Dieser Browser erlaubt keine lokale Speicherung (z. B. privater Modus). Speichere die Karte über „Datei → Als Datei speichern“."
            : state === "failed"
                ? "Die lokale Speicherung ist fehlgeschlagen (z. B. Speicher voll). Speichere die Karte als Datei."
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
        $("exportLabel1").textContent = `1× – ${w} × ${h} px`;
        const tooBig = w * h * 4 > 16777216;
        const two = document.querySelector("input[name=exportScale][value='2']");
        two.disabled = tooBig;
        $("exportLabel2").textContent = tooBig ? "2× – zu groß für Browser" : `2× – ${w * 2} × ${h * 2} px`;
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
        go.textContent = "Wird erstellt …";
        try {
            await new Promise((resolve) => requestAnimationFrame(resolve));
            if (bundle) await this.ed.exportBundle(scale);
            else await this.ed.exportPng(scale);
            $("exportDialog").close();
            this.toast(bundle ? "PNG und Projekt exportiert." : "PNG exportiert.");
        } catch (error) {
            const box = $("exportError");
            box.hidden = false;
            box.textContent = `Export fehlgeschlagen: ${error.message || error}`;
        } finally {
            $("exportCancel").disabled = false;
            $("exportGo").disabled = false;
            $("exportBundle").disabled = false;
            go.textContent = bundle ? "PNG + Projekt (.zip)" : "Exportieren (PNG)";
        }
    }

    askRestore(draft) {
        const dialog = $("restoreDialog");
        const when = draft.savedAt ? new Date(draft.savedAt).toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" }) : "unbekannt";
        const title = draft.doc && draft.doc.meta && typeof draft.doc.meta.title === "string" ? draft.doc.meta.title.slice(0, LIMITS.title) : "Karte";
        $("restoreText").textContent = `„${title}“ wurde zuletzt am ${when} in diesem Browser gespeichert. Möchtest du daran weiterarbeiten?`;
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
        if (!this.ed.hasUnsavedFileChanges()) return Promise.resolve(true);
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
                    if (await this.ed.saveFile()) finish(true);
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
        $("loadingText").textContent = `Die Kartenwerkstatt konnte nicht starten: ${error && error.message ? error.message : error}`;
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
