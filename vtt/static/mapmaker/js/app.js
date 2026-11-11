import { embedCredits, creditsForDocument } from "./credits.js";
// Kartenwerkstatt editor controller: document state, commands, view, files, autosave.

import {
    LIMITS, LABEL_STYLES, TILE_GRID_DEFAULT, ValidationError, cellKey, cellOf, cleanText, clamp, collectIds, countItems,
    countLayers, countTiles, createLayer, findItem, materialize, newId, serialize, tileGridSize, validateDocument,
} from "./document.js";
import { History } from "./history.js";
import { drawStampImage, stampExtent, loadPalette } from "./stamps.js";
import { COAST_PAD, Renderer, drawPath, itemBounds, pathHit, replacedTitleLabel } from "./render.js";
import { StrokeEngine, rectUnion, registerMaterialTextures } from "./brush.js";
import { createEmptyMap, createStarterMap } from "./starter.js";
import { AutosaveUnavailable, DraftStore, downloadBlob, slugify } from "./storage.js";
import { attachInput } from "./tools.js";
import { UI } from "./ui.js";
import { zipFiles } from "./zip.js";
import { Library } from "./library.js";

const KIND_NAMES = { raster: "Malebene", paths: "Wegeebene", stamps: "Symbolebene", labels: "Beschriftungsebene", tiles: "Kachelebene" };
const MIN_ZOOM = 0.1;
const MAX_ZOOM = 4;
export const MAX_EXPORT_PIXELS = 16777216; // same bound as the export dialog (ui.js openExport)

function pad(rect, amount) {
    return { x: rect.x - amount, y: rect.y - amount, w: rect.w + amount * 2, h: rect.h + amount * 2 };
}

function snapshot(item) {
    return JSON.parse(JSON.stringify(item));
}

class Editor {
    constructor() {
        this.canvas = document.getElementById("mapCanvas");
        this.stage = document.getElementById("stage");
        this.doc = null;
        this.palette = null;
        this.renderer = null;
        this.engine = null;
        this.view = { zoom: 1, panX: 0, panY: 0, fit: 1 };
        this.cssSize = { w: 0, h: 0 };
        this.dpr = 1;
        this.tool = "brush";
        this.brush = { material: "forest", size: 64, opacity: 0.9, softness: 45, pressureEnabled: true };
        this.stampOpts = { asset: null, size: 88, rot: 0, flip: false, vary: false, scatter: false };
        this.labelOpts = { style: "town", kind: "landmark", pin: true, symbol: null, symbolSize: 56 };
        this.pathOpts = { material: "road", width: 14 };
        this.tileOpts = { asset: null, erase: false, size: TILE_GRID_DEFAULT };
        this.tileGesture = null;
        this.previewPath = null;
        this.selection = null;
        this.activeLayerId = null;
        this.cursor = null;
        this.strokeActive = false;
        this.pendingEdit = null;
        this.dirtyRect = null;
        this.dirtyAll = false;
        this.frame = 0;
        this.history = new History({ onChange: () => this.onHistoryChange() });
        this.drafts = new DraftStore();
        this.autosave = { state: "idle", timer: 0, saving: false, again: false };
        // Document generation: bumped on every document mutation and on document
        // replacement. Saves record the generation their snapshot was taken at
        // and only mark the map clean when nothing changed since.
        this.generation = 0;
        this.fileGeneration = 0;
        this.ui = new UI(this);
        this.library = new Library(this);
        this.mapOpened = false;
    }

    // ---- startup -----------------------------------------------------------

    async init() {
        this.ui.setLoading("Symbole und Schriften werden geladen …");
        this.palette = await loadPalette(() => this.renderer && this.invalidate(), (message) => {
            this.ui.toast(message);
            const note = document.getElementById("packNote");
            note.hidden = false;
            note.textContent = message;
        });
        registerMaterialTextures(this.palette.materialTextures);
        this.ui.bind();
        this.renderer = new Renderer(this.palette);
        this.ui.buildPalette();
        await Promise.race([
            Promise.all([
                document.fonts.load("700 40px Cinzel"),
                document.fonts.load("400 40px Cinzel"),
                document.fonts.load("400 40px BadScript"),
                document.fonts.load("italic 400 30px Literata"),
            ]).catch(() => null),
            new Promise((resolve) => setTimeout(resolve, 2500)),
        ]);
        this.observeSize();
        attachInput(this);
        window.addEventListener("beforeunload", (event) => {
            const unprotected = this.autosave.state === "failed" || this.autosave.state === "unavailable";
            if (unprotected && this.hasUnsavedChanges()) {
                event.preventDefault();
                event.returnValue = "";
            }
        });

        await this.library.initialize();
        let draft = null;
        try {
            if (this.drafts) draft = await this.drafts.load();
            else this.setAutosaveState("unavailable");
        } catch (error) {
            this.setAutosaveState(error instanceof AutosaveUnavailable ? "unavailable" : "failed");
        }
        if (draft && draft.doc) {
            this.ui.setLoading("");
            const restore = await this.ui.askRestore(draft);
            if (restore) {
                this.ui.setLoading("Entwurf wird geladen …");
                try {
                    const validated = validateDocument(draft.doc, { knownAssets: this.palette.stamps, rasterSource: "binary" });
                    await this.palette.ensureDocumentImages(validated);
                    this.loadDocument(await materialize(validated));
                    this.mapOpened = true;
                    this.fileGeneration = draft.fileClean ? this.generation : -1;
                    if (draft.library?.accountId === this.library.accountId && this.library.accountId !== null) {
                        this.library.project = draft.library.project;
                        this.library.savedGeneration = draft.library.clean ? this.generation : -1;
                    }
                    this.library.updateStatus();
                    this.setAutosaveState("saved", draft.savedAt);
                    this.ui.ready();
                    return;
                } catch (error) {
                    this.ui.showError(`Der lokale Entwurf konnte nicht geladen werden: ${error.message || error}. Wähle eine Karte aus der Bibliothek oder starte eine neue Karte.`);
                }
            }
        }
        this.ui.setLoading("Karte wird gezeichnet …");
        await new Promise((resolve) => requestAnimationFrame(resolve));
        this.loadDocument(createEmptyMap());
        this.ui.ready();
        this.library.show();
    }

    engineFor(w, h) {
        if (!this.engine || this.engine.w !== w || this.engine.h !== h) this.engine = new StrokeEngine(w, h);
        return this.engine;
    }

    loadDocument(doc) {
        this.cancelInteractions();
        this.doc = doc;
        // A replaced document is a new generation; it starts "clean" relative to
        // files (callers that consider it a change call markChanged afterwards).
        this.generation += 1;
        this.fileGeneration = this.generation;
        this.engineFor(doc.size.w, doc.size.h);
        this.renderer.setDocument(doc);
        this.selection = null;
        this.pendingEdit = null;
        this.history.clear(false);
        const raster = doc.layers.find((layer) => layer.id === "terrain")
            || [...doc.layers].reverse().find((layer) => layer.kind === "raster");
        this.activeLayerId = (raster || doc.layers[doc.layers.length - 1]).id;
        this.fit();
        this.ui.refreshAll();
    }

    observeSize() {
        const resize = () => {
            const rect = this.stage.getBoundingClientRect();
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            const first = this.cssSize.w === 0;
            this.cssSize = { w: Math.max(1, rect.width), h: Math.max(1, rect.height) };
            this.dpr = dpr;
            this.canvas.width = Math.round(this.cssSize.w * dpr);
            this.canvas.height = Math.round(this.cssSize.h * dpr);
            this.canvas.style.width = `${this.cssSize.w}px`;
            this.canvas.style.height = `${this.cssSize.h}px`;
            if (first && this.doc) this.fit();
            else this.computeFit();
            this.requestFrame();
        };
        new ResizeObserver(resize).observe(this.stage);
        resize();
    }

    // ---- view --------------------------------------------------------------

    computeFit() {
        if (!this.doc) return 1;
        const margin = this.cssSize.w < 500 ? 12 : 32;
        this.view.fit = clamp(Math.min((this.cssSize.w - margin) / this.doc.size.w, (this.cssSize.h - margin) / this.doc.size.h), MIN_ZOOM, MAX_ZOOM);
        return this.view.fit;
    }

    fit() {
        if (!this.doc) return;
        const zoom = this.computeFit();
        this.view.zoom = zoom;
        this.view.panX = (this.cssSize.w - this.doc.size.w * zoom) / 2;
        // On narrow screens keep the map at the top so the bottom sheet does not cover it.
        this.view.panY = this.ui.isNarrow() ? 10 : (this.cssSize.h - this.doc.size.h * zoom) / 2;
        this.ui.updateZoom();
        this.requestFrame();
    }

    zoomAt(factor, sx, sy) {
        const zoom = clamp(this.view.zoom * factor, MIN_ZOOM, MAX_ZOOM);
        const docX = (sx - this.view.panX) / this.view.zoom;
        const docY = (sy - this.view.panY) / this.view.zoom;
        this.view.zoom = zoom;
        this.view.panX = sx - docX * zoom;
        this.view.panY = sy - docY * zoom;
        this.ui.updateZoom();
        this.requestFrame();
    }

    zoomStep(factor) {
        this.zoomAt(factor, this.cssSize.w / 2, this.cssSize.h / 2);
    }

    centerOn(x, y) {
        this.view.panX = this.cssSize.w / 2 - x * this.view.zoom;
        const sheet = this.ui.isNarrow() && document.getElementById("app").dataset.sheet === "open"
            ? document.getElementById("panel").getBoundingClientRect().height : 0;
        this.view.panY = (this.cssSize.h - sheet) / 2 - y * this.view.zoom;
        this.requestFrame();
    }

    clientToDoc(clientX, clientY) {
        const rect = this.canvas.getBoundingClientRect();
        return {
            x: (clientX - rect.left - this.view.panX) / this.view.zoom,
            y: (clientY - rect.top - this.view.panY) / this.view.zoom,
        };
    }

    docToClient(x, y) {
        const rect = this.canvas.getBoundingClientRect();
        return { x: rect.left + this.view.panX + x * this.view.zoom, y: rect.top + this.view.panY + y * this.view.zoom };
    }

    // ---- rendering ---------------------------------------------------------

    invalidate(rect) {
        if (!rect) this.dirtyAll = true;
        else this.dirtyRect = rectUnion(this.dirtyRect, rect);
        this.requestFrame();
    }

    invalidateItem(item) {
        this.invalidate(pad(itemBounds(item, this.palette), 6));
    }

    requestFrame() {
        if (!this.frame) this.frame = requestAnimationFrame(() => this.drawFrame());
    }

    flushRender() {
        if (this.strokeActive) {
            const rect = this.engine.flush();
            if (rect) {
                const layer = this.engine.active.layer;
                this.dirtyRect = rectUnion(this.dirtyRect, pad(rect, layer.effects.coast ? COAST_PAD : 0));
            }
        }
        if (!this.doc) return;
        if (this.dirtyAll) this.renderer.renderRegion(null);
        else if (this.dirtyRect) this.renderer.renderRegion(this.dirtyRect);
        this.dirtyAll = false;
        this.dirtyRect = null;
    }

    drawFrame() {
        this.frame = 0;
        this.flushRender();
        const ctx = this.canvas.getContext("2d");
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.fillStyle = "#1c2628";
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        if (!this.doc) return;
        const { zoom, panX, panY } = this.view;
        const dpr = this.dpr;
        ctx.setTransform(dpr * zoom, 0, 0, dpr * zoom, dpr * panX, dpr * panY);
        ctx.fillStyle = "rgba(0,0,0,0.35)";
        ctx.fillRect(10 / zoom, 12 / zoom, this.doc.size.w, this.doc.size.h);
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = zoom < 1 ? "high" : "medium";
        ctx.drawImage(this.renderer.composite, 0, 0);
        this.drawOverlay(ctx, zoom);
    }

    drawOverlay(ctx, zoom) {
        if (this.selection) {
            const found = findItem(this.doc, this.selection);
            if (found) {
                const b = pad(itemBounds(found.item, this.palette), 4);
                ctx.save();
                ctx.lineWidth = 2 / zoom;
                ctx.strokeStyle = "#f2c66d";
                ctx.setLineDash([6 / zoom, 4 / zoom]);
                ctx.strokeRect(b.x, b.y, b.w, b.h);
                ctx.restore();
                if ("points" in found.item) {
                    ctx.save();
                    ctx.fillStyle = "#ffffff";
                    ctx.strokeStyle = "#17424b";
                    ctx.lineWidth = 2 / zoom;
                    for (const point of found.item.points) {
                        ctx.beginPath();
                        ctx.arc(found.item.x + point.x, found.item.y + point.y, 5 / zoom, 0, Math.PI * 2);
                        ctx.fill();
                        ctx.stroke();
                    }
                    ctx.restore();
                }
            }
        }
        if (this.previewPath) {
            ctx.save();
            ctx.globalAlpha = 0.78;
            drawPath(ctx, this.previewPath);
            ctx.restore();
        }
        if (this.tool === "tile") this.drawTileOverlay(ctx, zoom);
        if (!this.cursor || this.strokeActive && this.tool === "stamp") return;
        if (this.tool === "brush" || this.tool === "eraser") {
            ctx.save();
            ctx.beginPath();
            ctx.arc(this.cursor.x, this.cursor.y, Math.max(1, this.brush.size / 2), 0, Math.PI * 2);
            ctx.lineWidth = 2.5 / zoom;
            ctx.strokeStyle = "rgba(255,255,255,0.8)";
            ctx.stroke();
            ctx.lineWidth = 1 / zoom;
            ctx.strokeStyle = "rgba(20,20,20,0.9)";
            ctx.stroke();
            ctx.restore();
        } else if (this.tool === "stamp" && this.stampOpts.asset) {
            const stamp = this.palette.stamps.get(this.stampOpts.asset);
            if (!stamp) return;
            if (!stamp.image) {
                this.palette.loadStamp(stamp.id).catch(() => {});
                return;
            }
            const { w, h } = stampExtent(stamp, this.stampOpts.size, this.stampOpts.crop);
            ctx.save();
            ctx.globalAlpha = 0.55;
            ctx.translate(this.cursor.x, this.cursor.y);
            ctx.rotate((this.stampOpts.rot * Math.PI) / 180);
            if (this.stampOpts.flip) ctx.scale(-1, 1);
            drawStampImage(ctx, stamp, this.stampOpts.crop, -w / 2, -h / 2, w, h);
            ctx.restore();
        }
    }

    /** Grid of the tile layer being painted, and the cell under the cursor with a preview. */
    drawTileOverlay(ctx, zoom) {
        const layer = this.targetLayer("tiles", { quiet: true });
        const size = layer ? layer.grid.size : this.tileOpts.size;
        const { cols, rows } = tileGridSize(this.doc, size);
        if (size * zoom >= 6) {
            const x0 = Math.max(0, Math.floor(-this.view.panX / zoom / size));
            const y0 = Math.max(0, Math.floor(-this.view.panY / zoom / size));
            const x1 = Math.min(cols, Math.ceil((this.cssSize.w - this.view.panX) / zoom / size));
            const y1 = Math.min(rows, Math.ceil((this.cssSize.h - this.view.panY) / zoom / size));
            ctx.save();
            ctx.beginPath();
            for (let c = x0; c <= x1; c += 1) { ctx.moveTo(c * size, y0 * size); ctx.lineTo(c * size, y1 * size); }
            for (let r = y0; r <= y1; r += 1) { ctx.moveTo(x0 * size, r * size); ctx.lineTo(x1 * size, r * size); }
            ctx.lineWidth = 1 / zoom;
            ctx.strokeStyle = "rgba(255,255,255,0.22)";
            ctx.stroke();
            ctx.restore();
        }
        if (!this.cursor || !this.insideMap(this.cursor)) return;
        const col = Math.floor(this.cursor.x / size);
        const row = Math.floor(this.cursor.y / size);
        const stamp = !this.tileOpts.erase && this.tileOpts.asset ? this.palette.stamps.get(this.tileOpts.asset) : null;
        ctx.save();
        if (stamp && stamp.image && !this.tileGesture) {
            ctx.globalAlpha = 0.6;
            ctx.imageSmoothingEnabled = !stamp.pixelArt;
            ctx.drawImage(stamp.image, col * size, row * size, size, size);
            ctx.globalAlpha = 1;
        } else if (stamp && !stamp.image) this.palette.loadStamp(stamp.id).catch(() => {});
        ctx.lineWidth = 2 / zoom;
        ctx.strokeStyle = this.tileOpts.erase ? "#e0806a" : "#f2c66d";
        ctx.strokeRect(col * size, row * size, size, size);
        ctx.restore();
    }

    // ---- tiles -------------------------------------------------------------

    /** Start painting or erasing grid tiles; the first tile creates a tile layer above the painted land. */
    beginTiles(point) {
        if (!this.insideMap(point)) {
            this.ui.toast("Kacheln lassen sich nur auf der Karte setzen.");
            return false;
        }
        const erase = this.tileOpts.erase;
        if (!erase && !this.tileOpts.asset) {
            this.ui.toast("Wähle zuerst eine Kachel aus der Kachelauswahl.");
            return false;
        }
        const exists = this.doc.layers.some((layer) => layer.kind === "tiles");
        let layer = exists ? this.targetLayer("tiles") : null;
        if (exists && !layer) return false;
        let created = null;
        if (!layer) {
            if (erase) {
                this.ui.toast("Es gibt noch keine Kachelebene zum Löschen.");
                return false;
            }
            if (this.doc.layers.length >= LIMITS.layers) {
                this.ui.toast(`Höchstens ${LIMITS.layers} Ebenen.`);
                return false;
            }
            layer = createLayer("tiles", `Kacheln ${countLayers(this.doc, "tiles") + 1}`, this.doc.size, collectIds(this.doc));
            layer.grid.size = this.tileOpts.size;
            created = { layer, index: this.doc.layers.findLastIndex((entry) => entry.kind === "raster") + 1 };
            this.doc.layers.splice(created.index, 0, layer);
            this.activeLayerId = layer.id;
            this.afterLayerChange();
        }
        this.commitEdit();
        this.tileGesture = { layer, created, before: new Map(), last: null, full: false };
        this.continueTiles(point);
        return true;
    }

    continueTiles(point) {
        const gesture = this.tileGesture;
        if (!gesture) return;
        const size = gesture.layer.grid.size;
        const cell = { col: Math.floor(point.x / size), row: Math.floor(point.y / size) };
        const from = gesture.last || cell;
        // Walk every cell between pointer samples so quick drags leave no gaps.
        const steps = Math.max(Math.abs(cell.col - from.col), Math.abs(cell.row - from.row));
        for (let i = gesture.last ? 1 : 0; i <= steps; i += 1) {
            const t = steps ? i / steps : 0;
            this.setTile(gesture, Math.round(from.col + (cell.col - from.col) * t), Math.round(from.row + (cell.row - from.row) * t));
        }
        gesture.last = cell;
        this.requestFrame();
    }

    setTile(gesture, col, row) {
        const { layer } = gesture;
        const size = layer.grid.size;
        const { cols, rows } = tileGridSize(this.doc, size);
        if (col < 0 || row < 0 || col >= cols || row >= rows) return;
        const key = cellKey(col, row);
        const before = layer.cells.get(key);
        const after = this.tileOpts.erase ? undefined : this.tileOpts.asset;
        if (before === after) return;
        if (before === undefined && countTiles(this.doc) >= LIMITS.tiles) {
            if (!gesture.full) this.ui.toast(`Höchstens ${LIMITS.tiles.toLocaleString("de")} Kacheln pro Karte.`);
            gesture.full = true;
            return;
        }
        if (!gesture.before.has(key)) gesture.before.set(key, before);
        if (after === undefined) layer.cells.delete(key);
        else layer.cells.set(key, after);
        this.invalidate({ x: col * size, y: row * size, w: size, h: size });
    }

    endTiles() {
        const gesture = this.tileGesture;
        this.tileGesture = null;
        if (!gesture) return;
        const { layer, created } = gesture;
        const changed = [...gesture.before.keys()].filter((key) => layer.cells.get(key) !== gesture.before.get(key));
        if (!changed.length) {
            if (created) this.removeCreatedTileLayer(created);
            return;
        }
        const before = new Map(changed.map((key) => [key, gesture.before.get(key)]));
        const after = new Map(changed.map((key) => [key, layer.cells.get(key)]));
        const put = (values) => {
            const size = layer.grid.size;
            for (const [key, asset] of values) {
                if (asset === undefined) layer.cells.delete(key);
                else layer.cells.set(key, asset);
                const { col, row } = cellOf(key);
                this.invalidate({ x: col * size, y: row * size, w: size, h: size });
            }
            this.requestFrame();
        };
        const label = this.tileOpts.erase ? "Kacheln löschen" : "Kacheln setzen";
        this.commit({
            label,
            bytes: 512 + changed.length * 48,
            undo: () => {
                put(before);
                if (created) this.removeCreatedTileLayer(created);
            },
            redo: () => {
                if (created) {
                    this.doc.layers.splice(Math.min(created.index, this.doc.layers.length), 0, layer);
                    this.activeLayerId = layer.id;
                    this.afterLayerChange();
                }
                put(after);
            },
        });
    }

    cancelTiles() {
        const gesture = this.tileGesture;
        this.tileGesture = null;
        if (!gesture) return;
        const size = gesture.layer.grid.size;
        for (const [key, asset] of gesture.before) {
            if (asset === undefined) gesture.layer.cells.delete(key);
            else gesture.layer.cells.set(key, asset);
            const { col, row } = cellOf(key);
            this.invalidate({ x: col * size, y: row * size, w: size, h: size });
        }
        if (gesture.created) this.removeCreatedTileLayer(gesture.created);
    }

    removeCreatedTileLayer(created) {
        const index = this.doc.layers.indexOf(created.layer);
        if (index >= 0) this.doc.layers.splice(index, 1);
        this.afterLayerChange();
    }

    // ---- layers ------------------------------------------------------------

    layerById(id) {
        return this.doc.layers.find((layer) => layer.id === id) || null;
    }

    activeLayer() {
        return this.layerById(this.activeLayerId);
    }

    setActiveLayer(id) {
        if (!this.layerById(id)) return;
        this.activeLayerId = id;
        this.ui.refreshLayers();
        this.ui.updateTargets();
    }

    /** Resolve the layer a tool works on; switches the active layer when needed. */
    targetLayer(kind, { quiet = false } = {}) {
        let layer = this.activeLayer();
        if (!layer || layer.kind !== kind) {
            layer = [...this.doc.layers].reverse().find((l) => l.kind === kind && l.visible)
                || [...this.doc.layers].reverse().find((l) => l.kind === kind) || null;
            if (layer && !quiet) this.setActiveLayer(layer.id);
        }
        if (!layer) {
            if (!quiet) this.ui.toast(`Keine ${KIND_NAMES[kind]} vorhanden – lege unter „Ebenen“ eine an.`);
            return null;
        }
        if (!layer.visible && !quiet) {
            this.ui.toast(`„${layer.name}“ ist ausgeblendet – blende die Ebene ein, um darauf zu arbeiten.`);
            return null;
        }
        return layer;
    }

    layerCommand(label, apply, revert, bytes = 256) {
        apply();
        this.afterLayerChange();
        this.commit({
            label,
            bytes,
            undo: () => { revert(); this.afterLayerChange(); },
            redo: () => { apply(); this.afterLayerChange(); },
        });
    }

    afterLayerChange() {
        if (!this.layerById(this.activeLayerId)) {
            const top = this.doc.layers[this.doc.layers.length - 1];
            this.activeLayerId = top ? top.id : null;
        }
        if (this.selection && !findItem(this.doc, this.selection)) this.selection = null;
        this.invalidate(null);
        this.ui.refreshLayers();
        this.ui.refreshPlaces();
        this.ui.refreshInspector();
        this.ui.updateTargets();
    }

    /** Same raster limits as the import contract, checked before any allocation. */
    canAddRaster() {
        const count = countLayers(this.doc, "raster") + 1;
        return count <= LIMITS.rasterLayers && count * this.doc.size.w * this.doc.size.h <= LIMITS.rasterArea;
    }

    insideMap(point) {
        return point.x >= 0 && point.y >= 0 && point.x <= this.doc.size.w && point.y <= this.doc.size.h;
    }

    /** Clamp a position to the map so emitted documents stay inside the import contract. */
    clampToMap(x, y) {
        return { x: Math.round(clamp(x, 0, this.doc.size.w)), y: Math.round(clamp(y, 0, this.doc.size.h)) };
    }

    addLayer(kind) {
        if (this.doc.layers.length >= LIMITS.layers) {
            this.ui.toast(`Höchstens ${LIMITS.layers} Ebenen.`);
            return;
        }
        if (kind === "raster" && countLayers(this.doc, "raster") >= LIMITS.rasterLayers) {
            this.ui.toast(`Höchstens ${LIMITS.rasterLayers} Malebenen.`);
            return;
        }
        if (kind === "raster" && !this.canAddRaster()) {
            this.ui.toast("Die Malebenen wären zusammen zu groß für diese Kartengröße.");
            return;
        }
        const names = { raster: "Malebene", paths: "Wege & Flüsse", stamps: "Symbole", labels: "Beschriftung", tiles: "Kacheln" };
        const layer = createLayer(kind, `${names[kind]} ${countLayers(this.doc, kind) + 1}`, this.doc.size, collectIds(this.doc));
        if (kind === "tiles") layer.grid.size = this.tileOpts.size;
        const active = this.doc.layers.indexOf(this.activeLayer());
        const index = active >= 0 ? active + 1 : this.doc.layers.length;
        const bytes = kind === "raster" ? this.doc.size.w * this.doc.size.h * 4 : 256;
        this.layerCommand("Ebene hinzufügen",
            () => { this.doc.layers.splice(index, 0, layer); this.activeLayerId = layer.id; },
            () => { this.doc.layers.splice(this.doc.layers.indexOf(layer), 1); },
            bytes);
    }

    deleteLayer(id) {
        const layer = this.layerById(id);
        if (!layer) return;
        if (this.doc.layers.length <= 1) {
            this.ui.toast("Die letzte Ebene kann nicht gelöscht werden.");
            return;
        }
        const index = this.doc.layers.indexOf(layer);
        const bytes = layer.kind === "raster" ? this.doc.size.w * this.doc.size.h * 4 : layer.kind === "tiles" ? 256 + layer.cells.size * 48 : 256;
        this.layerCommand(`Ebene „${layer.name}“ löschen`,
            () => { this.doc.layers.splice(this.doc.layers.indexOf(layer), 1); },
            () => { this.doc.layers.splice(index, 0, layer); this.activeLayerId = layer.id; },
            bytes);
        this.ui.toast(`Ebene „${layer.name}“ gelöscht – Strg+Z holt sie zurück.`);
    }

    moveLayer(id, delta) {
        const layer = this.layerById(id);
        const from = this.doc.layers.indexOf(layer);
        const to = from + delta;
        if (!layer || to < 0 || to >= this.doc.layers.length) return;
        const swap = (a, b) => {
            const list = this.doc.layers;
            list.splice(b, 0, list.splice(a, 1)[0]);
        };
        this.layerCommand("Ebene verschieben", () => swap(from, to), () => swap(to, from));
    }

    setLayerProp(id, key, value) {
        const layer = this.layerById(id);
        if (!layer) return;
        const get = () => (key === "coast" ? layer.effects.coast : key === "gridSize" ? layer.grid.size : layer[key]);
        const set = (v) => {
            if (key === "coast") layer.effects.coast = v;
            else if (key === "gridSize") layer.grid.size = v;
            else layer[key] = v;
        };
        const before = get();
        if (before === value) return;
        if (key === "gridSize") {
            // Cells keep their column/row; refuse a size that would push used cells off the map.
            const { cols, rows } = tileGridSize(this.doc, value);
            if ([...layer.cells.keys()].some((k) => cellOf(k).col >= cols || cellOf(k).row >= rows)) {
                this.ui.toast("Diese Kachelgröße ist zu groß: belegte Kacheln lägen außerhalb der Karte.");
                this.ui.refreshLayers();
                return;
            }
        }
        const labels = { visible: value ? "Ebene einblenden" : "Ebene ausblenden", name: "Ebene umbenennen", opacity: "Deckkraft", coast: "Küstenlinie", gridSize: "Kachelgröße" };
        this.layerCommand(labels[key] || "Ebene ändern", () => set(value), () => set(before));
    }

    // ---- items -------------------------------------------------------------

    addItems(layer, items, label) {
        if (countItems(this.doc) + items.length > LIMITS.items) {
            this.ui.toast(`Höchstens ${LIMITS.items} Symbole und Beschriftungen pro Karte.`);
            return false;
        }
        const apply = () => {
            for (const item of items) {
                if (!layer.items.includes(item)) layer.items.push(item);
                this.invalidateItem(item);
            }
            this.afterItemChange();
        };
        const revert = () => {
            for (const item of items) {
                const index = layer.items.indexOf(item);
                if (index >= 0) layer.items.splice(index, 1);
                this.invalidateItem(item);
            }
            this.afterItemChange();
        };
        apply();
        this.commit({ label, bytes: 256 * items.length, undo: revert, redo: apply });
        return true;
    }

    addPath(item) {
        let layer = [...this.doc.layers].reverse().find((entry) => entry.kind === "paths" && entry.visible);
        if (layer) return this.addItems(layer, [item], item.material === "river" ? "Fluss zeichnen" : "Weg zeichnen");
        if (this.doc.layers.length >= LIMITS.layers || countItems(this.doc) >= LIMITS.items) {
            this.ui.toast("Höchstgrenze an Ebenen oder Kartenelementen erreicht.");
            return false;
        }
        layer = createLayer("paths", "Wege & Flüsse", this.doc.size, collectIds(this.doc));
        layer.items.push(item);
        const lastRaster = this.doc.layers.findLastIndex((entry) => entry.kind === "raster");
        const index = lastRaster + 1;
        const apply = () => {
            this.doc.layers.splice(index, 0, layer);
            this.activeLayerId = layer.id;
            this.afterLayerChange();
        };
        const revert = () => {
            this.doc.layers.splice(this.doc.layers.indexOf(layer), 1);
            this.afterLayerChange();
        };
        apply();
        this.commit({ label: item.material === "river" ? "Fluss zeichnen" : "Weg zeichnen", bytes: 1024 + item.points.length * 24, undo: revert, redo: apply });
        return true;
    }

    /** Live placement during a scatter drag (committed later via commitPlaced). */
    placeLive(layer, item) {
        if (countItems(this.doc) >= LIMITS.items) return false;
        layer.items.push(item);
        this.invalidateItem(item);
        return true;
    }

    commitPlaced(layer, items) {
        if (!items.length) return;
        const apply = () => {
            for (const item of items) {
                if (!layer.items.includes(item)) layer.items.push(item);
                this.invalidateItem(item);
            }
            this.afterItemChange();
        };
        const revert = () => {
            for (const item of items) {
                const index = layer.items.indexOf(item);
                if (index >= 0) layer.items.splice(index, 1);
                this.invalidateItem(item);
            }
            this.afterItemChange();
        };
        this.afterItemChange();
        this.commit({ label: items.length > 1 ? "Symbole streuen" : "Symbol setzen", bytes: 256 * items.length, undo: revert, redo: apply });
    }

    removeLive(layer, items) {
        for (const item of items) {
            const index = layer.items.indexOf(item);
            if (index >= 0) layer.items.splice(index, 1);
            this.invalidateItem(item);
        }
    }

    deleteSelection() {
        if (!this.selection) return;
        this.commitEdit();
        const found = findItem(this.doc, this.selection);
        if (!found) return;
        const { layer, item, index } = found;
        const apply = () => {
            const i = layer.items.indexOf(item);
            if (i >= 0) layer.items.splice(i, 1);
            this.invalidateItem(item);
            this.afterItemChange();
        };
        const revert = () => {
            layer.items.splice(Math.min(index, layer.items.length), 0, item);
            this.invalidateItem(item);
            this.afterItemChange();
        };
        this.selection = null;
        apply();
        this.commit({ label: "Löschen", bytes: 256, undo: revert, redo: apply });
    }

    updateItem(item, before, after, label) {
        const set = (state) => {
            this.invalidateItem(item);
            Object.assign(item, snapshot(state));
            this.invalidateItem(item);
            this.afterItemChange();
        };
        this.afterItemChange();
        this.commit({ label, bytes: 512, undo: () => set(before), redo: () => set(after) });
    }

    afterItemChange() {
        if (this.selection && !findItem(this.doc, this.selection)) this.selection = null;
        this.ui.refreshPlaces();
        this.ui.refreshInspector();
        this.requestFrame();
    }

    select(itemId) {
        if (this.selection !== itemId) this.commitEdit();
        this.selection = itemId;
        if (itemId) {
            const found = findItem(this.doc, itemId);
            if (found && found.layer.id !== this.activeLayerId) {
                this.activeLayerId = found.layer.id;
                this.ui.refreshLayers();
                this.ui.updateTargets();
            }
        }
        this.ui.refreshInspector();
        this.ui.refreshPlaces();
        this.requestFrame();
    }

    /** Inspector edits: live update, one undo step per committed change. */
    liveEdit(patch) {
        const found = this.selection && findItem(this.doc, this.selection);
        if (!found) return;
        if (!this.pendingEdit || this.pendingEdit.item !== found.item) {
            this.commitEdit();
            this.pendingEdit = { item: found.item, before: snapshot(found.item) };
        }
        this.invalidateItem(found.item);
        Object.assign(found.item, patch);
        this.invalidateItem(found.item);
        this.ui.refreshPlaces();
        this.requestFrame();
        this.markChanged();
    }

    commitEdit() {
        const edit = this.pendingEdit;
        this.pendingEdit = null;
        if (!edit) return;
        const after = snapshot(edit.item);
        if (JSON.stringify(after) === JSON.stringify(edit.before)) return;
        this.updateItem(edit.item, edit.before, after, "Eigenschaften ändern");
    }

    hitTestAll(point, kinds = ["stamps", "labels", "paths"]) {
        const tolerance = 6 / this.view.zoom;
        const replacedTitle = replacedTitleLabel(this.doc);
        const hits = [];
        for (let li = this.doc.layers.length - 1; li >= 0; li -= 1) {
            const layer = this.doc.layers[li];
            if (!layer.visible || !kinds.includes(layer.kind)) continue;
            for (let i = layer.items.length - 1; i >= 0; i -= 1) {
                const item = layer.items[i];
                if (item === replacedTitle) continue;
                const b = itemBounds(item, this.palette);
                if (point.x >= b.x - tolerance && point.x <= b.x + b.w + tolerance && point.y >= b.y - tolerance && point.y <= b.y + b.h + tolerance
                    && (layer.kind !== "paths" || pathHit(item, point, tolerance))) {
                    hits.push({ layer, item });
                }
            }
        }
        return hits;
    }

    hitTest(point, kinds = ["stamps", "labels", "paths"]) {
        return this.hitTestAll(point, kinds)[0] || null;
    }

    createStamp(point, assetId) {
        const opts = this.stampOpts;
        const vary = opts.vary ? 1 + (Math.random() - 0.5) * 0.24 : 1;
        const rot = opts.vary ? opts.rot + (Math.random() - 0.5) * 12 : opts.rot;
        const at = this.clampToMap(point.x, point.y);
        return {
            id: newId("s", collectIds(this.doc)),
            asset: assetId,
            ...(opts.crop && opts.asset === assetId ? { crop: { ...opts.crop } } : {}),
            x: at.x,
            y: at.y,
            size: Math.round(clamp(opts.size * vary, LIMITS.stampSize[0], LIMITS.stampSize[1])),
            rot: Math.round(rot),
            flip: opts.vary ? (opts.flip !== (Math.random() < 0.3)) : opts.flip,
        };
    }

    newPathId() {
        return newId("w", collectIds(this.doc));
    }

    createLabel(point) {
        const style = this.labelOpts.style;
        const kind = this.labelOpts.kind;
        const at = this.clampToMap(point.x, point.y);
        return {
            id: newId("p", collectIds(this.doc)),
            x: at.x,
            y: at.y,
            text: "Neuer Ort",
            style,
            size: LABEL_STYLES[style].size,
            rot: 0,
            color: style === "water" ? "#1d4654" : "#3b2a1a",
            pin: this.labelOpts.pin,
            symbol: kind && this.labelOpts.symbol ? { asset: this.labelOpts.symbol, size: this.labelOpts.symbolSize } : null,
            place: kind ? { kind, lore: "" } : null,
        };
    }

    // ---- strokes -----------------------------------------------------------

    beginStroke(point, pressure) {
        const layer = this.targetLayer("raster");
        if (!layer) return false;
        this.commitEdit();
        this.engine.begin(layer, { ...this.brush, erase: this.tool === "eraser" });
        this.engine.addPoint(point.x, point.y, pressure);
        this.strokeActive = true;
        this.requestFrame();
        return true;
    }

    continueStroke(point, pressure) {
        if (!this.strokeActive) return;
        this.engine.addPoint(point.x, point.y, pressure);
        this.requestFrame();
    }

    endStroke() {
        if (!this.strokeActive) return;
        const layer = this.engine.active.layer;
        const coastPad = layer.effects.coast ? COAST_PAD : 0;
        const before = this.engine.active.total;
        const pending = this.engine.active.pending;
        const result = this.engine.end();
        this.strokeActive = false;
        const touched = rectUnion(before, pending);
        if (touched) this.invalidate(pad(touched, coastPad));
        if (!result) return;
        const { rect, before: imgBefore, after: imgAfter } = result;
        const put = (image) => {
            layer.canvas.getContext("2d").putImageData(image, rect.x, rect.y);
            layer.rev += 1;
            this.invalidate(pad(rect, layer.effects.coast ? COAST_PAD : 0));
        };
        this.commit({
            label: this.tool === "eraser" ? "Radieren" : "Pinselstrich",
            bytes: imgBefore.data.length + imgAfter.data.length,
            undo: () => put(imgBefore),
            redo: () => put(imgAfter),
        });
    }

    cancelStroke() {
        if (!this.strokeActive) return;
        const layer = this.engine.active.layer;
        const rect = this.engine.cancel();
        this.strokeActive = false;
        if (rect) this.invalidate(pad(rect, layer.effects.coast ? COAST_PAD : 0));
    }

    cancelInteractions() {
        if (this.input) this.input.cancel();
        this.cancelStroke();
        this.cancelTiles();
    }

    // ---- history & persistence ---------------------------------------------

    commit(command) {
        if (!this.history.push(command)) {
            this.ui.toast("Dieser Schritt war zu groß für den Verlauf – ältere Schritte wurden verworfen.");
        }
    }

    undo() {
        this.cancelInteractions();
        this.commitEdit();
        const command = this.history.undo();
        if (command) this.ui.toast(`Rückgängig: ${command.label}`);
    }

    redo() {
        this.cancelInteractions();
        this.commitEdit();
        const command = this.history.redo();
        if (command) this.ui.toast(`Wiederholt: ${command.label}`);
    }

    onHistoryChange() {
        this.ui.updateUndo();
        this.markChanged();
    }

    markChanged() {
        this.generation += 1;
        this.library.updateStatus();
        this.scheduleAutosave();
    }

    hasUnsavedFileChanges() {
        return this.generation !== this.fileGeneration;
    }

    hasUnsavedChanges() {
        return this.hasUnsavedFileChanges() && this.generation !== this.library.savedGeneration;
    }

    savePrimary() {
        return this.library.accountId !== null ? this.library.save() : this.saveFile();
    }

    /** True while a gesture has live, not yet committed document changes. */
    isMutating() {
        return this.strokeActive || !!(this.input && this.input.mutating());
    }

    /** Called by the input layer whenever a gesture ends or is cancelled. */
    gestureEnded() {
        if (this.autosave.deferred) {
            this.autosave.deferred = false;
            this.scheduleAutosave();
        }
    }

    setTitle(value) {
        this.doc.meta.title = cleanText(value, LIMITS.title) || "Unbenannte Karte";
        if (this.doc.meta.showTitle) this.invalidate(null);
        this.markChanged();
    }

    setMapStyle(key, value) {
        const target = key === "showTitle" ? this.doc.meta : this.doc.sea;
        const before = target[key];
        if (before === value) return;
        const apply = (next) => {
            target[key] = next;
            if (key !== "showTitle") this.renderer.buildSea();
            if (key === "showTitle" && this.selection === replacedTitleLabel(this.doc)?.id) this.select(null);
            this.invalidate(null);
            this.ui.refreshMapStyle();
        };
        apply(value);
        this.commit({ label: "Kartenstil ändern", bytes: 128, undo: () => apply(before), redo: () => apply(value) });
    }

    setAutosaveState(state, time) {
        const previous = this.autosave.state;
        this.autosave.state = state;
        this.ui.setStatus(state, time);
        if ((state === "failed" || state === "unavailable") && previous !== state) {
            this.ui.toast(state === "failed"
                ? "Autosave fehlgeschlagen – bitte über „Datei → Als Datei speichern“ sichern."
                : "Autosave ist in diesem Browser nicht verfügbar – bitte als Datei speichern.");
        }
    }

    scheduleAutosave() {
        if (!this.drafts) return;
        if (this.autosave.state === "unavailable") return;
        clearTimeout(this.autosave.timer);
        if (this.autosave.state !== "failed") this.setAutosaveState("pending");
        this.autosave.timer = setTimeout(() => this.runAutosave(), 1500);
    }

    async runAutosave() {
        if (this.isMutating()) {
            // Never persist live gesture state; gestureEnded() requeues the save.
            this.autosave.deferred = true;
            return;
        }
        if (this.autosave.saving) {
            this.autosave.again = true;
            return;
        }
        this.autosave.saving = true;
        this.setAutosaveState("saving");
        try {
            const generation = this.generation;
            const store = this.drafts;
            const fileClean = generation === this.fileGeneration;
            const library = { accountId: this.library.accountId, project: this.library.project,
                clean: generation === this.library.savedGeneration };
            const data = await serialize(this.doc, "binary"); // snapshot taken synchronously at this generation
            const savedAt = Date.now();
            await store.save({ savedAt, doc: data, fileClean, library });
            if (this.generation === generation) {
                this.setAutosaveState("saved", savedAt);
            } else {
                this.setAutosaveState("pending");
                this.autosave.again = true;
            }
        } catch (error) {
            this.setAutosaveState(error instanceof AutosaveUnavailable ? "unavailable" : "failed");
        } finally {
            this.autosave.saving = false;
            if (this.autosave.again) {
                this.autosave.again = false;
                this.scheduleAutosave();
            }
        }
    }

    async saveFile() {
        try {
            this.commitEdit();
            const generation = this.generation;
            const data = await serialize(this.doc, "file"); // snapshot taken synchronously at this generation
            const blob = new Blob([JSON.stringify(data)], { type: "application/json" });
            downloadBlob(blob, `${slugify(data.meta.title)}.rdmap.json`);
            // Only edits up to the snapshot are in the file; newer edits stay unsaved.
            if (generation > this.fileGeneration) this.fileGeneration = generation;
            this.ui.toast(this.generation === generation
                ? "Karte als Datei gespeichert."
                : "Karte als Datei gespeichert – Änderungen während des Speicherns sind noch nicht in der Datei.");
            return true;
        } catch (error) {
            this.ui.showError(`Speichern fehlgeschlagen: ${error.message || error}`);
            return false;
        }
    }

    async openFile(file) {
        try {
            if (!file) return;
            if (file.size > LIMITS.fileBytes) throw new ValidationError("Die Datei ist größer als 50 MB.");
            const text = await file.text();
            let raw;
            try {
                raw = JSON.parse(text);
            } catch (_error) {
                throw new ValidationError("Die Datei ist keine gültige JSON-Datei.");
            }
            const validated = validateDocument(raw, { knownAssets: this.palette.stamps });
            await this.palette.ensureDocumentImages(validated);
            const doc = await materialize(validated);
            if (!(await this.ui.confirmReplace())) return;
            this.loadDocument(doc);
            this.mapOpened = true;
            this.library.detach();
            this.library.close();
            this.markChanged(); // autosave the loaded map as the new draft
            this.fileGeneration = this.generation; // identical to the file just opened
            this.ui.toast(`„${doc.meta.title}“ geladen.`);
        } catch (error) {
            const message = error instanceof ValidationError ? error.message : "Die Datei konnte nicht vollständig geladen werden. Bitte prüfe die Symbolpakete und versuche es erneut.";
            this.ui.showError(message);
        }
    }

    async exportPng(scale) {
        this.commitEdit();
        const blob = await this.renderPngBlob(scale);
        downloadBlob(blob, `${slugify(this.doc.meta.title)}${scale > 1 ? `-${scale}x` : ""}.png`);
    }

    async renderPngBlob(scale) {
        if (this.doc.size.w * scale * this.doc.size.h * scale > MAX_EXPORT_PIXELS) {
            throw new Error("Diese Auflösung ist zu groß für den Browser.");
        }
        const doc = this.doc;
        const credits = creditsForDocument(doc, this.palette);
        const generation = this.generation;
        await this.palette.ensureDocumentImages(doc);
        if (doc !== this.doc || generation !== this.generation) throw new Error("Die Karte wurde während des Exports geändert. Bitte erneut exportieren.");
        this.flushRender();
        const canvas = this.renderer.renderExport(scale);
        const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
        canvas.width = 0;
        canvas.height = 0;
        if (!blob) throw new Error("Der Browser konnte das Bild nicht erzeugen (zu groß?).");
        return embedCredits(blob, credits);
    }

    async exportBundle(scale) {
        this.commitEdit();
        const generation = this.generation;
        const projectPromise = serialize(this.doc, "file");
        const pngPromise = this.renderPngBlob(scale);
        const [project, png] = await Promise.all([projectPromise, pngPromise]);
        const base = slugify(project.meta.title);
        const packageBlob = await zipFiles([
            [`${base}${scale > 1 ? `-${scale}x` : ""}.png`, png],
            [`${base}.rdmap.json`, JSON.stringify(project)],
            ["CREDITS.txt", creditsForDocument(project, this.palette)],
        ]);
        downloadBlob(packageBlob, `${base}-karte.zip`);
        if (generation > this.fileGeneration) this.fileGeneration = generation;
    }

    async newMap(kind) {
        const initial = !this.mapOpened;
        if (!(await this.ui.confirmReplace())) return;
        const doc = kind === "empty" ? createEmptyMap() : createStarterMap(this.palette, this.engineFor(2400, 1600));
        this.loadDocument(doc);
        this.mapOpened = true;
        this.library.detach();
        if (!initial) this.markChanged();
        if (!initial) this.ui.toast(kind === "empty" ? "Leere Karte angelegt." : "Startkarte geladen.");
    }

    setTool(tool) {
        if (this.tool === tool) return;
        this.cancelInteractions();
        this.commitEdit();
        this.tool = tool;
        if (tool !== "select" && tool !== "label") this.selection = null;
        const kind = tool === "brush" || tool === "eraser" ? "raster" : tool === "stamp" ? "stamps" : tool === "label" ? "labels"
            : tool === "path" ? "paths" : tool === "tile" ? "tiles" : null;
        if (kind) {
            const layer = this.targetLayer(kind, { quiet: true });
            if (layer) this.activeLayerId = layer.id;
        }
        this.ui.setTool(tool);
        this.requestFrame();
    }
}

// ---- automation/test surface (read-only views plus sampling) -----------------

function exposeApi(editor, ready) {
    window.rdMapmaker = Object.freeze({
        ready,
        summary() {
            const doc = editor.doc;
            if (!doc) return null;
            const labels = doc.layers.filter((l) => l.kind === "labels").flatMap((l) => l.items);
            return {
                title: doc.meta.title,
                size: { ...doc.size },
                tool: editor.tool,
                zoom: editor.view.zoom,
                fitZoom: editor.view.fit,
                activeLayer: editor.activeLayerId,
                selection: editor.selection,
                canUndo: editor.history.canUndo,
                canRedo: editor.history.canRedo,
                historySteps: editor.history.undoStack.length,
                autosave: editor.autosave.state,
                generation: editor.generation,
                unsavedFile: editor.hasUnsavedFileChanges(),
                mutating: editor.isMutating(),
                layers: doc.layers.map((l) => ({ id: l.id, name: l.name, kind: l.kind, visible: l.visible, opacity: l.opacity, items: l.items ? l.items.length : null,
                    ...(l.kind === "tiles" ? { grid: l.grid.size, tiles: [...l.cells].map(([key, asset]) => ({ ...cellOf(key), asset })) } : {}) })),
                stamps: doc.layers.filter((l) => l.kind === "stamps").reduce((n, l) => n + l.items.length, 0),
                labels: labels.length,
                places: labels.filter((i) => i.place).map((i) => i.text),
                items: doc.layers.flatMap((l) => (l.items || []).map((i) => ({ layer: l.id, ...snapshot(i) }))),
            };
        },
        catalogue() {
            const counts = new Map();
            for (const stamp of editor.palette.stamps.values()) counts.set(stamp.pack, (counts.get(stamp.pack) || 0) + 1);
            return { total: editor.palette.stamps.size, packs: Object.fromEntries(counts), errors: editor.palette.packError };
        },
        docToClient: (x, y) => editor.docToClient(x, y),
        sampleRegion(x, y, w, h) {
            editor.flushRender();
            return Array.from(editor.renderer.composite.getContext("2d").getImageData(x, y, w, h).data);
        },
    });
}

const editor = new Editor();
const ready = editor.init().catch((error) => {
    editor.ui.fatal(error);
    throw error;
});
exposeApi(editor, ready);
