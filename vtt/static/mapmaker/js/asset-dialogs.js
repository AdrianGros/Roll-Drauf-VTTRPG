// Own images for one project: upload (crop + simple transparent colour key) and a
// small pixel editor. Both produce one rasterized PNG that is embedded in the
// project through Editor.addCustomAsset (same limits as both validators).
// No AI cut-out, no animation or plugin system; no URL, SVG or script input.
import { ASSET_PERSPECTIVES, ASSET_STYLES, LIMITS, cleanText, clamp } from "./document.js";

const ui = (source, parameters) => globalThis.VTTUi(source, parameters);
const MAX_UPLOAD_FILE = 32 * 1024 * 1024;
const MAX_UPLOAD_SIDE = 8192;
export const PIXEL_SIZES = [16, 24, 32, 48, 64, 96, 128, 192, 256];
const PIXEL_HISTORY = 40;

function el(tag, parent, text = null, attributes = {}) {
    const node = document.createElement(tag);
    if (text !== null) node.textContent = text;
    for (const [key, value] of Object.entries(attributes)) {
        if (value === true) node.setAttribute(key, "");
        else if (value !== false && value !== null && value !== undefined) node.setAttribute(key, String(value));
    }
    if (parent) parent.append(node);
    return node;
}

function field(parent, label, tag = "input", attributes = {}) {
    const wrap = el("label", parent, null, { class: "mm-field" });
    el("span", wrap, label);
    return el(tag, wrap, null, attributes);
}

const STYLE_NAMES = () => ({ pixel: ui("Pixelgrafik"), painted: ui("Gemalt"), ink: ui("Tusche/Linie"), other: ui("Sonstiges") });
const PERSPECTIVE_NAMES = () => ({ top: ui("Draufsicht"), side: ui("Seitenansicht"), isometric: ui("Isometrisch"), other: ui("Sonstige") });

/** Shared metadata block: label, style, perspective, source and licence (bounded strings). */
function metadata(parent, prefix, defaults) {
    const box = el("fieldset", parent, null, { class: "mm-own-meta" });
    el("legend", box, ui("Angaben zum Bild"));
    const label = field(box, ui("Name"), "input", { type: "text", maxlength: LIMITS.assetLabel, id: `${prefix}Label`, autocomplete: "off" });
    const row = el("div", box, null, { class: "mm-field-row" });
    const style = field(row, ui("Stil"), "select", { id: `${prefix}Style` });
    for (const value of ASSET_STYLES) el("option", style, STYLE_NAMES()[value], { value });
    const perspective = field(row, ui("Perspektive"), "select", { id: `${prefix}Perspective` });
    for (const value of ASSET_PERSPECTIVES) el("option", perspective, PERSPECTIVE_NAMES()[value], { value });
    const source = field(box, ui("Quelle / Urheber"), "input", { type: "text", maxlength: LIMITS.assetSource, id: `${prefix}Source`, autocomplete: "off" });
    const license = field(box, ui("Lizenz oder Nutzungsrecht"), "input", { type: "text", maxlength: LIMITS.assetLicense, id: `${prefix}License`, autocomplete: "off" });
    const reset = () => {
        label.value = defaults.label(); style.value = defaults.style; perspective.value = "top";
        source.value = defaults.source(); license.value = defaults.license();
    };
    reset();
    return {
        reset,
        read: () => ({ label: cleanText(label.value, LIMITS.assetLabel) || ui("Eigenes Bild"), style: style.value, perspective: perspective.value,
            source: cleanText(source.value, LIMITS.assetSource), license: cleanText(license.value, LIMITS.assetLicense) }),
        label, style, perspective, source, license,
    };
}

export function canvasPngBytes(canvas) {
    return new Promise((resolve, reject) => canvas.toBlob(async (blob) => {
        if (!blob) { reject(new Error(ui("Der Browser konnte das PNG nicht erzeugen."))); return; }
        resolve(new Uint8Array(await blob.arrayBuffer()));
    }, "image/png"));
}

function formatMiB(bytes) {
    return (bytes / 1048576).toLocaleString(globalThis.VTTI18n?.locale?.() === "en" ? "en" : "de", { maximumFractionDigits: 2 });
}

function usageText(editor) {
    const usage = editor.assetUsage();
    return ui("Eigene Bilder dieser Karte: {count}/{max} · {mib} von 12 MiB · {mpx} von 8 Mio. Pixel", {
        count: usage.count, max: LIMITS.customAssets, mib: formatMiB(usage.bytes),
        mpx: (usage.pixels / 1e6).toLocaleString("de", { maximumFractionDigits: 2 }),
    });
}

// ---------------------------------------------------------------------------
// Upload: crop, optional transparent background colour, preview, embed.
// ---------------------------------------------------------------------------

export class UploadDialog {
    constructor(editor) {
        this.ed = editor;
        this.bitmap = null;
        this.crop = null;
        this.pick = false;
        const dialog = this.dialog = el("dialog", document.body, null, { id: "ownUploadDialog", class: "mm-dialog mm-dialog-wide mm-own-dialog", "aria-labelledby": "ownUploadTitle" });
        el("h2", dialog, ui("Eigenes Bild als Stempel"), { id: "ownUploadTitle" });
        el("p", dialog, ui("Das Bild wird als PNG nur in dieses Kartenprojekt eingebettet, nicht öffentlich freigegeben. Es bleibt ein Rasterbild ohne bearbeitbare Einzelteile. PNG, JPEG oder WebP; keine SVG-Dateien oder Links."), { class: "mm-hint" });
        this.file = field(dialog, ui("Bilddatei"), "input", { type: "file", accept: "image/png,image/jpeg,image/webp", id: "ownUploadFile" });
        const body = el("div", dialog, null, { class: "mm-own-grid" });
        const left = el("div", body, null, { class: "mm-own-col" });
        el("p", left, ui("Ausschnitt: im Bild ziehen oder Zahlen eingeben (Originalpixel)."), { class: "mm-hint" });
        const sourceBox = el("div", left, null, { class: "mm-own-checker" });
        this.source = el("canvas", sourceBox, null, { id: "ownUploadSource", width: 1, height: 1, "aria-label": ui("Quellbild mit Ausschnitt") });
        const crop = el("div", left, null, { class: "mm-sheet-fields" });
        this.cropFields = {};
        for (const [key, label] of [["x", "X"], ["y", "Y"], ["w", ui("Breite")], ["h", ui("Höhe")]]) {
            const wrap = el("label", crop, null);
            el("span", wrap, label);
            this.cropFields[key] = el("input", wrap, null, { type: "number", min: key === "x" || key === "y" ? 0 : 1, step: 1, id: `ownCrop${key.toUpperCase()}` });
        }
        this.side = field(left, ui("Größte Seite im Ergebnis (px, höchstens {px})", { px: LIMITS.customAssetSide }), "input", { type: "number", min: 1, max: LIMITS.customAssetSide, step: 1, id: "ownUploadSide" });
        const key = el("fieldset", left, null, { class: "mm-own-meta" });
        el("legend", key, ui("Hintergrund entfernen (einfache Farbe)"));
        const keyRow = el("label", key, null, { class: "mm-check" });
        this.keyOn = el("input", keyRow, null, { type: "checkbox", id: "ownKeyOn" });
        el("span", keyRow, ui("Diese Farbe transparent machen"));
        const keyFields = el("div", key, null, { class: "mm-field-row" });
        this.keyColor = field(keyFields, ui("Farbe"), "input", { type: "color", value: "#ffffff", id: "ownKeyColor" });
        this.keyTolerance = field(keyFields, ui("Toleranz"), "input", { type: "range", min: 0, max: 128, value: 24, id: "ownKeyTolerance" });
        this.pickButton = el("button", key, ui("Farbe im Bild wählen"), { type: "button", class: "mm-btn mm-btn-small", id: "ownKeyPick", "aria-pressed": "false" });
        const right = el("div", body, null, { class: "mm-own-col" });
        el("p", right, ui("Vorschau des Stempels"), { class: "mm-hint" });
        const previewBox = el("div", right, null, { class: "mm-own-checker mm-own-preview" });
        this.preview = el("canvas", previewBox, null, { id: "ownUploadPreview", width: 1, height: 1, "aria-label": ui("Vorschau des eigenen Bilds") });
        this.info = el("p", right, "", { class: "mm-hint", id: "ownUploadInfo", role: "status", "aria-live": "polite" });
        this.meta = metadata(right, "ownUpload", { label: () => ui("Eigenes Bild"), style: "painted", source: () => "", license: () => "" });
        const rights = el("label", right, null, { class: "mm-check" });
        this.rights = el("input", rights, null, { type: "checkbox", id: "ownUploadRights" });
        el("span", rights, ui("Ich darf dieses Bild in meinen Karten verwenden."));
        this.error = el("p", dialog, "", { class: "mm-error", role: "alert", id: "ownUploadError", hidden: true });
        const actions = el("div", dialog, null, { class: "mm-dialog-actions" });
        el("button", actions, ui("Abbrechen"), { type: "button", class: "mm-btn", id: "ownUploadCancel" }).onclick = () => this.close();
        this.save = el("button", actions, ui("Als eigenes Bild speichern"), { type: "button", class: "mm-btn mm-btn-primary", id: "ownUploadSave", disabled: true });
        this.save.onclick = () => this.commit();
        this.file.addEventListener("change", () => this.load(this.file.files && this.file.files[0]));
        for (const input of [...Object.values(this.cropFields), this.side, this.keyOn, this.keyColor, this.keyTolerance, this.meta.style]) {
            input.addEventListener("input", () => this.schedule());
            input.addEventListener("change", () => this.schedule());
        }
        this.pickButton.onclick = () => { this.pick = !this.pick; this.pickButton.setAttribute("aria-pressed", String(this.pick)); };
        this.bindSource();
        dialog.addEventListener("close", () => this.release());
    }

    open() {
        if (!this.ed.doc) return;
        this.release();
        this.meta.reset();
        this.rights.checked = false;
        this.file.value = "";
        this.showError("");
        this.info.textContent = usageText(this.ed);
        this.save.disabled = true;
        if (!this.dialog.open) this.dialog.showModal();
    }

    close() { if (this.dialog.open) this.dialog.close(); }

    release() {
        if (this.bitmap && this.bitmap.close) this.bitmap.close();
        this.bitmap = null;
        this.output = null;
        this.source.width = this.source.height = 1;
        this.preview.width = this.preview.height = 1;
    }

    showError(message) {
        this.error.hidden = !message;
        this.error.textContent = message;
    }

    async load(file) {
        this.release();
        this.save.disabled = true;
        if (!file) return;
        // Bounds before decoding: bounded file, raster types only (never SVG or scripts).
        if (file.size > MAX_UPLOAD_FILE) { this.showError(ui("Die Datei ist größer als 32 MiB.")); return; }
        if (!/^image\/(png|jpeg|webp)$/.test(file.type) || /\.svgz?$/i.test(file.name)) { this.showError(ui("Bitte ein PNG-, JPEG- oder WebP-Bild wählen (keine SVG-Dateien).")); return; }
        let bitmap;
        try {
            bitmap = await createImageBitmap(file);
        } catch (_error) {
            this.showError(ui("Das Bild ließ sich nicht lesen."));
            return;
        }
        if (bitmap.width > MAX_UPLOAD_SIDE || bitmap.height > MAX_UPLOAD_SIDE) {
            if (bitmap.close) bitmap.close();
            this.showError(ui("Das Bild ist größer als {px} Pixel je Seite. Bitte vorher verkleinern.", { px: MAX_UPLOAD_SIDE }));
            return;
        }
        this.showError("");
        this.bitmap = bitmap;
        const name = cleanText(file.name.replace(/\.[a-z0-9]+$/i, "").replace(/[_-]+/g, " "), LIMITS.assetLabel);
        if (name) this.meta.label.value = name;
        if (!this.meta.source.value) this.meta.source.value = cleanText(file.name, LIMITS.assetSource);
        this.setCrop({ x: 0, y: 0, w: bitmap.width, h: bitmap.height });
        this.side.value = String(Math.min(LIMITS.customAssetSide, Math.max(bitmap.width, bitmap.height)));
        const scale = Math.min(1, 520 / Math.max(bitmap.width, bitmap.height));
        this.source.width = Math.max(1, Math.round(bitmap.width * scale));
        this.source.height = Math.max(1, Math.round(bitmap.height * scale));
        this.render();
    }

    setCrop(crop) {
        this.crop = crop;
        for (const key of ["x", "y", "w", "h"]) this.cropFields[key].value = String(crop[key]);
    }

    readCrop() {
        if (!this.bitmap) return null;
        const c = Object.fromEntries(["x", "y", "w", "h"].map((key) => [key, Math.round(Number(this.cropFields[key].value))]));
        const valid = Object.values(c).every(Number.isInteger) && c.x >= 0 && c.y >= 0 && c.w >= 1 && c.h >= 1
            && c.x + c.w <= this.bitmap.width && c.y + c.h <= this.bitmap.height;
        return valid ? c : null;
    }

    bindSource() {
        const point = (event) => {
            const rect = this.source.getBoundingClientRect();
            return {
                x: clamp(Math.floor((event.clientX - rect.left) / rect.width * this.bitmap.width), 0, this.bitmap.width - 1),
                y: clamp(Math.floor((event.clientY - rect.top) / rect.height * this.bitmap.height), 0, this.bitmap.height - 1),
            };
        };
        this.source.addEventListener("pointerdown", (event) => {
            if (!this.bitmap) return;
            event.preventDefault();
            const p = point(event);
            if (this.pick) {
                const probe = document.createElement("canvas");
                probe.width = probe.height = 1;
                const ctx = probe.getContext("2d", { willReadFrequently: true });
                ctx.drawImage(this.bitmap, p.x, p.y, 1, 1, 0, 0, 1, 1);
                const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data;
                this.keyColor.value = `#${[r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("")}`;
                this.keyOn.checked = true;
                this.pick = false;
                this.pickButton.setAttribute("aria-pressed", "false");
                this.render();
                return;
            }
            this.dragStart = p;
            try { this.source.setPointerCapture(event.pointerId); } catch (_error) { /* synthetic pointer */ }
        });
        this.source.addEventListener("pointermove", (event) => {
            if (!this.dragStart || !this.bitmap) return;
            const p = point(event), a = this.dragStart;
            this.setCrop({ x: Math.min(a.x, p.x), y: Math.min(a.y, p.y), w: Math.abs(a.x - p.x) + 1, h: Math.abs(a.y - p.y) + 1 });
            this.schedule();
        });
        for (const name of ["pointerup", "pointercancel"]) this.source.addEventListener(name, () => { this.dragStart = null; });
    }

    schedule() {
        if (this.frame) return;
        this.frame = requestAnimationFrame(() => { this.frame = 0; this.render(); });
    }

    /** Result size for the current crop and maximum side. */
    targetSize(crop) {
        const side = clamp(Math.round(Number(this.side.value)) || LIMITS.customAssetSide, 1, LIMITS.customAssetSide);
        const scale = Math.min(1, side / Math.max(crop.w, crop.h));
        return { w: Math.max(1, Math.round(crop.w * scale)), h: Math.max(1, Math.round(crop.h * scale)) };
    }

    render() {
        if (!this.bitmap) return;
        const crop = this.readCrop();
        const sctx = this.source.getContext("2d");
        sctx.clearRect(0, 0, this.source.width, this.source.height);
        sctx.drawImage(this.bitmap, 0, 0, this.source.width, this.source.height);
        if (!crop) {
            this.output = null;
            this.save.disabled = true;
            this.info.textContent = ui("Der Ausschnitt muss innerhalb des Bildes liegen.");
            return;
        }
        const sx = this.source.width / this.bitmap.width, sy = this.source.height / this.bitmap.height;
        sctx.save();
        sctx.fillStyle = "rgba(20,20,20,0.45)";
        sctx.fillRect(0, 0, this.source.width, this.source.height);
        sctx.drawImage(this.bitmap, crop.x, crop.y, crop.w, crop.h, crop.x * sx, crop.y * sy, crop.w * sx, crop.h * sy);
        sctx.strokeStyle = "#ffca4b";
        sctx.lineWidth = 2;
        sctx.strokeRect(crop.x * sx + 1, crop.y * sy + 1, Math.max(1, crop.w * sx - 2), Math.max(1, crop.h * sy - 2));
        sctx.restore();
        const { w, h } = this.targetSize(crop);
        const output = document.createElement("canvas");
        output.width = w;
        output.height = h;
        const ctx = output.getContext("2d", { willReadFrequently: true });
        ctx.imageSmoothingEnabled = this.meta.style.value !== "pixel";
        ctx.imageSmoothingQuality = "high";
        ctx.drawImage(this.bitmap, crop.x, crop.y, crop.w, crop.h, 0, 0, w, h);
        if (this.keyOn.checked) {
            const key = [1, 3, 5].map((i) => parseInt(this.keyColor.value.slice(i, i + 2), 16));
            const tolerance = Number(this.keyTolerance.value) || 0;
            const image = ctx.getImageData(0, 0, w, h), data = image.data;
            for (let i = 0; i < data.length; i += 4) {
                const distance = Math.max(Math.abs(data[i] - key[0]), Math.abs(data[i + 1] - key[1]), Math.abs(data[i + 2] - key[2]));
                if (distance <= tolerance) data[i + 3] = 0;
            }
            ctx.putImageData(image, 0, 0);
        }
        this.output = output;
        const scale = Math.min(4, 256 / Math.max(w, h));
        this.preview.width = Math.max(1, Math.round(w * scale));
        this.preview.height = Math.max(1, Math.round(h * scale));
        const pctx = this.preview.getContext("2d");
        pctx.imageSmoothingEnabled = this.meta.style.value !== "pixel" && scale < 1;
        pctx.clearRect(0, 0, this.preview.width, this.preview.height);
        pctx.drawImage(output, 0, 0, this.preview.width, this.preview.height);
        this.info.textContent = `${ui("Ergebnis {w}×{h} Pixel", { w, h })} · ${usageText(this.ed)}`;
        this.save.disabled = false;
    }

    async commit() {
        this.render();
        if (!this.output) return;
        if (!this.rights.checked) { this.showError(ui("Bitte bestätigen, dass du dieses Bild verwenden darfst.")); return; }
        this.save.disabled = true;
        try {
            const bytes = await canvasPngBytes(this.output);
            const entry = await this.ed.addCustomAsset({ bytes, width: this.output.width, height: this.output.height, ...this.meta.read() });
            if (!entry) return;
            this.close();
            this.ed.ui.toast(ui("„{label}“ ist als eigenes Bild in dieser Karte verfügbar.", { label: entry.label }));
        } catch (error) {
            this.showError(error.message || String(error));
        } finally {
            this.save.disabled = !this.output;
        }
    }
}

// ---------------------------------------------------------------------------
// Pixel editor: new 16–256 px image, pen, eraser, colour/alpha, undo/redo, zoom.
// ---------------------------------------------------------------------------

export class PixelEditor {
    constructor(editor) {
        this.ed = editor;
        this.size = 32;
        this.tool = "pen";
        this.undoStack = [];
        this.redoStack = [];
        const dialog = this.dialog = el("dialog", document.body, null, { id: "pixelDialog", class: "mm-dialog mm-dialog-wide mm-own-dialog", "aria-labelledby": "pixelTitle" });
        el("h2", dialog, ui("Pixelbild zeichnen"), { id: "pixelTitle" });
        el("p", dialog, ui("Ein neues Pixelbild von 16 bis 256 Pixeln. Gespeichert wird ein PNG-Stempel nur in dieser Karte."), { class: "mm-hint" });
        const bar = el("div", dialog, null, { class: "mm-pixel-bar" });
        this.sizeSelect = field(bar, ui("Größe"), "select", { id: "pixelSize" });
        for (const size of PIXEL_SIZES) el("option", this.sizeSelect, `${size} × ${size}`, { value: size });
        this.sizeSelect.value = "32";
        el("button", bar, ui("Neu anlegen"), { type: "button", class: "mm-btn mm-btn-small", id: "pixelNew" }).onclick = () => this.reset(Number(this.sizeSelect.value));
        const tools = el("div", bar, null, { class: "mm-pixel-tools", role: "group", "aria-label": ui("Werkzeug") });
        this.penButton = el("button", tools, ui("Stift"), { type: "button", class: "mm-btn mm-btn-small", id: "pixelPen", "aria-pressed": "true" });
        this.eraserButton = el("button", tools, ui("Radierer"), { type: "button", class: "mm-btn mm-btn-small", id: "pixelEraser", "aria-pressed": "false" });
        this.penButton.onclick = () => this.setTool("pen");
        this.eraserButton.onclick = () => this.setTool("eraser");
        this.color = field(bar, ui("Farbe"), "input", { type: "color", value: "#3b2a1a", id: "pixelColor" });
        this.alpha = field(bar, ui("Deckkraft (%)"), "input", { type: "number", min: 0, max: 100, step: 1, value: 100, id: "pixelAlpha" });
        this.zoom = field(bar, ui("Zoom"), "select", { id: "pixelZoom" });
        el("option", this.zoom, ui("Automatisch"), { value: "auto" });
        for (const factor of [1, 2, 4, 8, 12, 16]) el("option", this.zoom, `${factor}×`, { value: factor });
        this.zoom.addEventListener("change", () => this.applyZoom());
        const history = el("div", bar, null, { class: "mm-pixel-tools" });
        this.undoButton = el("button", history, ui("Rückgängig"), { type: "button", class: "mm-btn mm-btn-small", id: "pixelUndo", disabled: true });
        this.redoButton = el("button", history, ui("Wiederholen"), { type: "button", class: "mm-btn mm-btn-small", id: "pixelRedo", disabled: true });
        this.undoButton.onclick = () => this.undo();
        this.redoButton.onclick = () => this.redo();
        const stage = el("div", dialog, null, { class: "mm-own-checker mm-pixel-stage" });
        this.canvas = el("canvas", stage, null, { id: "pixelCanvas", width: 32, height: 32, "aria-label": ui("Pixelfläche") });
        this.meta = metadata(dialog, "pixel", { label: () => ui("Pixelbild"), style: "pixel", source: () => ui("Eigene Pixelgrafik (Kartenwerkstatt)"), license: () => ui("Eigene Arbeit") });
        this.error = el("p", dialog, "", { class: "mm-error", role: "alert", id: "pixelError", hidden: true });
        this.info = el("p", dialog, "", { class: "mm-hint", id: "pixelInfo", role: "status" });
        const actions = el("div", dialog, null, { class: "mm-dialog-actions" });
        el("button", actions, ui("Abbrechen"), { type: "button", class: "mm-btn", id: "pixelCancel" }).onclick = () => this.close();
        el("button", actions, ui("Als eigenen Stempel speichern"), { type: "button", class: "mm-btn mm-btn-primary", id: "pixelSave" }).onclick = () => this.commit();
        this.bindCanvas();
        // The editor's global shortcuts pause while a dialog is open; the pixel editor has its own.
        dialog.addEventListener("keydown", (event) => {
            const mod = event.ctrlKey || event.metaKey, key = event.key.toLowerCase();
            if (!mod || event.target.closest("input[type=text]")) return;
            if (key === "z") { event.preventDefault(); if (event.shiftKey) this.redo(); else this.undo(); }
            else if (key === "y") { event.preventDefault(); this.redo(); }
        });
        this.reset(32);
    }

    open() {
        if (!this.ed.doc) return;
        this.meta.reset();
        this.showError("");
        this.info.textContent = usageText(this.ed);
        if (!this.dialog.open) this.dialog.showModal();
    }

    close() { if (this.dialog.open) this.dialog.close(); }

    showError(message) {
        this.error.hidden = !message;
        this.error.textContent = message;
    }

    reset(size) {
        this.size = PIXEL_SIZES.includes(size) ? size : 32;
        this.sizeSelect.value = String(this.size);
        this.canvas.width = this.canvas.height = this.size;
        this.image = new ImageData(this.size, this.size);
        this.undoStack = [];
        this.redoStack = [];
        this.paint();
        this.applyZoom();
        this.updateHistory();
    }

    setTool(tool) {
        this.tool = tool;
        this.penButton.setAttribute("aria-pressed", String(tool === "pen"));
        this.eraserButton.setAttribute("aria-pressed", String(tool === "eraser"));
    }

    /** CSS zoom only: the bitmap is never smoothed (image-rendering: pixelated). */
    applyZoom() {
        const factor = this.zoom.value === "auto" ? clamp(Math.floor(320 / this.size), 1, 16) : Number(this.zoom.value);
        this.canvas.style.width = `${this.size * factor}px`;
        this.canvas.style.height = `${this.size * factor}px`;
    }

    paint() {
        this.canvas.getContext("2d").putImageData(this.image, 0, 0);
    }

    updateHistory() {
        this.undoButton.disabled = !this.undoStack.length;
        this.redoButton.disabled = !this.redoStack.length;
    }

    copy() {
        return new ImageData(new Uint8ClampedArray(this.image.data), this.size, this.size);
    }

    undo() {
        if (!this.undoStack.length) return;
        this.redoStack.push(this.copy());
        this.image = this.undoStack.pop();
        this.paint();
        this.updateHistory();
    }

    redo() {
        if (!this.redoStack.length) return;
        this.undoStack.push(this.copy());
        this.image = this.redoStack.pop();
        this.paint();
        this.updateHistory();
    }

    rgba() {
        if (this.tool === "eraser") return [0, 0, 0, 0];
        const alpha = Math.round(clamp(Number(this.alpha.value) || 0, 0, 100) * 2.55);
        return [...[1, 3, 5].map((i) => parseInt(this.color.value.slice(i, i + 2), 16)), alpha];
    }

    plot(x, y, color) {
        if (x < 0 || y < 0 || x >= this.size || y >= this.size) return false;
        const i = (y * this.size + x) * 4, data = this.image.data;
        if (data[i] === color[0] && data[i + 1] === color[1] && data[i + 2] === color[2] && data[i + 3] === color[3]) return false;
        data.set(color, i);
        return true;
    }

    /** Bresenham line so quick strokes leave no gaps. */
    line(a, b, color) {
        let changed = false, x = a.x, y = a.y;
        const dx = Math.abs(b.x - a.x), dy = -Math.abs(b.y - a.y), sx = a.x < b.x ? 1 : -1, sy = a.y < b.y ? 1 : -1;
        let error = dx + dy;
        for (;;) {
            changed = this.plot(x, y, color) || changed;
            if (x === b.x && y === b.y) break;
            const e2 = 2 * error;
            if (e2 >= dy) { error += dy; x += sx; }
            if (e2 <= dx) { error += dx; y += sy; }
        }
        return changed;
    }

    bindCanvas() {
        const cell = (event) => {
            const rect = this.canvas.getBoundingClientRect();
            return { x: Math.floor((event.clientX - rect.left) / rect.width * this.size), y: Math.floor((event.clientY - rect.top) / rect.height * this.size) };
        };
        this.canvas.addEventListener("pointerdown", (event) => {
            if (event.button !== 0) return;
            event.preventDefault();
            try { this.canvas.setPointerCapture(event.pointerId); } catch (_error) { /* synthetic pointer */ }
            const at = cell(event);
            // One undo step per stroke, bounded; the snapshot is only kept if pixels changed.
            this.stroke = { last: at, before: this.copy(), changed: false, color: this.rgba() };
            this.stroke.changed = this.line(at, at, this.stroke.color);
            this.paint();
        });
        this.canvas.addEventListener("pointermove", (event) => {
            if (!this.stroke) return;
            const at = cell(event);
            if (at.x === this.stroke.last.x && at.y === this.stroke.last.y) return;
            this.stroke.changed = this.line(this.stroke.last, at, this.stroke.color) || this.stroke.changed;
            this.stroke.last = at;
            this.paint();
        });
        const end = () => {
            const stroke = this.stroke;
            this.stroke = null;
            if (!stroke || !stroke.changed) return;
            this.undoStack.push(stroke.before);
            if (this.undoStack.length > PIXEL_HISTORY) this.undoStack.shift();
            this.redoStack = [];
            this.updateHistory();
        };
        this.canvas.addEventListener("pointerup", end);
        this.canvas.addEventListener("pointercancel", () => {
            if (this.stroke) { this.image = this.stroke.before; this.paint(); }
            this.stroke = null;
        });
    }

    async commit() {
        if (!this.image.data.some((value, index) => index % 4 === 3 && value > 0)) {
            this.showError(ui("Das Pixelbild ist noch leer."));
            return;
        }
        try {
            this.paint();
            const bytes = await canvasPngBytes(this.canvas);
            const entry = await this.ed.addCustomAsset({ bytes, width: this.size, height: this.size, ...this.meta.read() });
            if (!entry) return;
            this.close();
            this.ed.ui.toast(ui("„{label}“ ist als eigener Stempel in dieser Karte verfügbar.", { label: entry.label }));
        } catch (error) {
            this.showError(error.message || String(error));
        }
    }
}

export class OwnImageDialogs {
    constructor(editor) {
        this.upload = new UploadDialog(editor);
        this.pixel = new PixelEditor(editor);
        document.getElementById("ownUploadBtn").addEventListener("click", () => this.upload.open());
        document.getElementById("ownPixelBtn").addEventListener("click", () => this.pixel.open());
    }

    close() {
        this.upload.close();
        this.pixel.close();
    }
}
