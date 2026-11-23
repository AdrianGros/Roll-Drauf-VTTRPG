globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
import { creditsForDocument } from "./credits.js";
import { renderPngBlob } from "./snapshot.js";
// Kartenwerkstatt editor controller: document state, commands, view, files, autosave.

import {
    LIMITS, LABEL_STYLES, TILE_GRID_DEFAULT, ValidationError, cellKey, cellOf, cleanText, clamp, collectIds, countItems,
    countLayers, countTiles, createLayer, customAssetId, findItem, isCustomAsset, materialize, newId, referencedAssetIds,
    serialize, tileGridSize, validateAssets, validateDocument,
} from "./document.js";
import { reorderItems } from "./selection.js";
import { OwnImageDialogs } from "./asset-dialogs.js";
import { History } from "./history.js";
import { drawStampImage, stampExtent, loadPalette } from "./stamps.js";
import { COAST_PAD, Renderer, drawPath, itemBounds, pathHit, replacedTitleLabel } from "./render.js";
import { StrokeEngine, imageBrush, rectClamp, rectUnion, registerMaterialTextures } from "./brush.js";
import { createEmptyMap, createStarterMap } from "./starter.js";
import { AutosaveUnavailable, DraftStore, downloadBlob, slugify } from "./storage.js";
import { attachInput } from "./tools.js";
import { UI } from "./ui.js";
import { Selection } from "./selection.js";
import { zipFiles } from "./zip.js";
import { Library } from "./library.js";
import { AtlasLibrary } from "./atlas-bridge.js";
import { LandmassDialog } from "./landmass-dialog.js";

const KIND_NAMES = { raster: globalThis.VTTUi("Malebene"), paths: globalThis.VTTUi("Wegeebene"), stamps: globalThis.VTTUi("Symbolebene"), labels: globalThis.VTTUi("Beschriftungsebene"), tiles: globalThis.VTTUi("Kachelebene") };
const MIN_ZOOM = 0.1;
const MAX_ZOOM = 4;
export const MAX_EXPORT_PIXELS = 16777216; // same bound as the export dialog (ui.js openExport)
export const PATH_SNAP = 32; // explicit endpoint connection: same layer and material, at most this many map pixels
const AREA_MAX_ITEMS = 400; // one area fill never places more stamps than this

function pad(rect, amount) {
    return { x: rect.x - amount, y: rect.y - amount, w: rect.w + amount * 2, h: rect.h + amount * 2 };
}

function snapshot(item) {
    return JSON.parse(JSON.stringify(item));
}

class Editor {
    get brush() { return this.tool === 'eraser' ? this.eraserBrush : this.paintBrush; }
    get selection() { return this._selection || null; }
    set selection(id) { this._selection=id;this.selectionSet?.reset(id); }
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
        this.paintBrush = { material: "forest", size: 64, opacity: 0.9, softness: 45, pressureEnabled: true, shape: 'round', texture: 1, colorEnabled: false, color: '#8ea566', image: null };
        this.eraserBrush = { material: 'forest', size: 64, opacity: 1, softness: 0, pressureEnabled: true, shape: 'round' };
        this.stampOpts = { asset: null, size: 88, rot: 0, flip: false, vary: false, scatter: false, area: false, grid: 0 };
        this.labelOpts = { named: true, style: "town", kind: "landmark", pin: true, symbol: null, symbolSize: 56, font: null };
        // Brush clip: alpha of a chosen lower raster layer or the occupied cells of a tile layer (never the sea).
        this.clipOpts = { layerId: null, notice: "" };
        this.wheelOrder = null; // Alt+wheel reorder session: one undo step per gesture
        this.areaPreview = null;
        this.pathOpts = { material: "road", width: 14, curve: true };
        this.tileOpts = { asset: null, erase: false, size: TILE_GRID_DEFAULT, radius: 0, variants: [] };
        this.tileGesture = null;
        this.eraseScope = "active"; // "active" (default) or explicit "visible"
        this.eraseGesture = null;
        this.previewPath = null;
        this.showReferenceGrid = false; // page-session view state, never part of a document
        this.selectionSet = new Selection(this);
        this.selection = null;
        this.editPathNodes = false;
        this.activeLayerId = null;
        this.cursor = null;
        this.strokeActive = false;
        this.pendingEdit = null;
        this.dirtyRect = null;
        this.dirtyAll = false;
        this.frame = 0;
        this.history = new History({ onChange: () => this.onHistoryChange() });
        this.drafts = new DraftStore();
        this.autosave = { state: "idle", timer: 0, saving: false, again: false, generation: -1 };
        // Document generation: bumped on every document mutation and on document
        // replacement. Saves record the generation their snapshot was taken at
        // and only mark the map clean when nothing changed since.
        this.generation = 0;
        this.fileGeneration = 0;
        this.ui = new UI(this);
        this.library = new URLSearchParams(location.search).has("atlas_world") ? new AtlasLibrary(this) : new Library(this);
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
        this.landmass = new LandmassDialog(this);
        this.ownImages = new OwnImageDialogs(this);
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
            if (this.needsLeaveWarning()) {
                event.preventDefault();
                event.returnValue = "";
            }
        });
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden || !this.doc) return;
            this.cancelInteractions();
            this.commitEdit();
            clearTimeout(this.autosave.timer);
            if (this.drafts) this.runAutosave();
        });

        await this.library.initialize();
        if (this.library.atlas) { this.ui.ready(); return; }
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
                    this.autosave.generation = this.generation;
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
        this.landmass?.close();
        this.ownImages?.close();
        this.cancelInteractions();
        this.finishWheelOrder(false);
        this.doc = doc;
        this.ui.clearTileGridOffer();
        // Own images belong to exactly this project; the palette lists only these.
        doc.assets ||= [];
        this.palette.showDocumentAssets(doc);
        this.clipOpts.layerId = null;
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
        this.sanitizeAssetChoices();
        this.fit();
        this.ui.refreshAll();
        this.ui.refreshCustomAssets();
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
        this.selectionSet.draw(ctx,zoom);
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
                    // Larger gold handles while dragging a node edits it (node mode in the select tool).
                    const nodeMode = this.editPathNodes && this.tool === "select";
                    ctx.save();
                    ctx.fillStyle = nodeMode ? "#f2c66d" : "#ffffff";
                    ctx.strokeStyle = "#17424b";
                    ctx.lineWidth = 2 / zoom;
                    for (const point of found.item.points) {
                        ctx.beginPath();
                        ctx.arc(found.item.x + point.x, found.item.y + point.y, (nodeMode ? 6 : 5) / zoom, 0, Math.PI * 2);
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
        if (this.areaPreview) {
            const { a, b, count } = this.areaPreview;
            ctx.save();
            ctx.lineWidth = 2 / zoom;
            ctx.setLineDash([8 / zoom, 5 / zoom]);
            ctx.strokeStyle = count > 0 ? "#f2c66d" : "#e0806a";
            ctx.fillStyle = "rgba(242,198,109,0.12)";
            ctx.fillRect(Math.min(a.x, b.x), Math.min(a.y, b.y), Math.abs(a.x - b.x), Math.abs(a.y - b.y));
            ctx.strokeRect(Math.min(a.x, b.x), Math.min(a.y, b.y), Math.abs(a.x - b.x), Math.abs(a.y - b.y));
            ctx.restore();
        }
        if (this.tool === "tile") this.drawTileOverlay(ctx, zoom);
        else if (this.showReferenceGrid) this.drawTileOverlay(ctx, zoom, true);
        if (!this.cursor || this.strokeActive && this.tool === "stamp") return;
        if (this.tool === "stamp" && (this.stampOpts.scatter || this.stampOpts.area)) {
            // Visible scatter coverage: the spacing that separates scattered stamps.
            ctx.save();
            ctx.beginPath();
            ctx.arc(this.cursor.x, this.cursor.y, this.scatterSpacing(), 0, Math.PI * 2);
            ctx.setLineDash([5 / zoom, 4 / zoom]);
            ctx.lineWidth = 1.5 / zoom;
            ctx.strokeStyle = "rgba(255,255,255,0.75)";
            ctx.stroke();
            ctx.restore();
        }
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
            const at = this.stampPoint(this.cursor); // same rounded position as the placement
            ctx.translate(at.x, at.y);
            ctx.rotate((this.stampOpts.rot * Math.PI) / 180);
            if (this.stampOpts.flip) ctx.scale(-1, 1);
            drawStampImage(ctx, stamp, this.stampOpts.crop, -w / 2, -h / 2, w, h);
            ctx.restore();
        }
    }

    /** Grid of the tile layer being painted, and the cell under the cursor with a preview. */
    drawTileOverlay(ctx, zoom, gridOnly = false) {
        const layer = this.targetLayer("tiles", { quiet: true });
        const size = gridOnly && this.stampOpts.grid ? this.stampOpts.grid : layer ? layer.grid.size : this.tileOpts.size;
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
        if (gridOnly || !this.cursor || !this.insideMap(this.cursor)) return;
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
        // Full brush coverage, not only the centre cell.
        for (const cell of this.tileBrushCells(col, row)) ctx.strokeRect(cell.col * size, cell.row * size, size, size);
        ctx.restore();
    }

    // ---- tiles -------------------------------------------------------------

    /** Start painting or erasing grid tiles; the first tile creates a tile layer above the painted land. */
    beginTiles(point) {
        if (!this.insideMap(point)) {
            this.ui.toast(globalThis.VTTUi("Kacheln lassen sich nur auf der Karte setzen."));
            return false;
        }
        const erase = this.tileOpts.erase;
        if (!erase && !this.tileOpts.asset && !this.tileOpts.variants.length) {
            this.ui.toast(globalThis.VTTUi("Wähle zuerst eine Kachel aus der Kachelauswahl."));
            return false;
        }
        if (!erase && ![this.tileOpts.asset, ...this.tileOpts.variants].filter(Boolean).every((id) => this.assetAvailable(id))) {
            this.ui.toast(globalThis.VTTUi("Dieses eigene Bild gehört nicht zu dieser Karte. Bitte eine andere Kachel wählen."));
            return false;
        }
        const exists = this.doc.layers.some((layer) => layer.kind === "tiles");
        let layer = exists ? this.targetLayer("tiles") : null;
        if (exists && !layer) return false;
        let created = null;
        if (!layer) {
            if (erase) {
                this.ui.toast(globalThis.VTTUi("Es gibt noch keine Kachelebene zum Löschen."));
                return false;
            }
            if (this.doc.layers.length >= LIMITS.layers) {
                this.ui.toast(globalThis.VTTUi("Höchstens {p0} Ebenen.",{p0:(LIMITS.layers)}));
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
            this.paintTileBrush(gesture, Math.round(from.col + (cell.col - from.col) * t), Math.round(from.row + (cell.row - from.row) * t));
        }
        gesture.last = cell;
        this.requestFrame();
    }

    /** Brush coverage in whole cells; independent of the pixel grid and physical scale. */
    tileBrushCells(col, row) {
        const radius = Math.max(0, Math.min(6, Math.round(this.tileOpts.radius) || 0));
        const cells = [];
        for (let dr = -radius; dr <= radius; dr += 1) {
            for (let dc = -radius; dc <= radius; dc += 1) {
                if (dc * dc + dr * dr <= radius * radius + radius) cells.push({ col: col + dc, row: row + dr });
            }
        }
        return cells;
    }

    paintTileBrush(gesture, col, row) {
        for (const cell of this.tileBrushCells(col, row)) this.setTile(gesture, cell.col, cell.row);
    }

    /** At most one random pick per cell and gesture, so dragging back and forth never flickers. */
    chooseTile(gesture, key) {
        if (this.tileOpts.erase) return undefined;
        const pool = this.tileOpts.variants.length ? this.tileOpts.variants : [this.tileOpts.asset];
        if (pool.length === 1) return pool[0];
        gesture.choice ||= new Map();
        if (!gesture.choice.has(key)) gesture.choice.set(key, pool[Math.floor(Math.random() * pool.length)]);
        return gesture.choice.get(key);
    }

    /** Only tiles already present in the loaded catalog can become variants (max. 16). */
    addTileVariant(id) {
        const stamp = id && this.palette.stamps.get(id);
        if (!stamp || !stamp.tile) {
            this.ui.toast(globalThis.VTTUi("Wähle zuerst eine Kachel aus der Kachelauswahl."));
            return false;
        }
        if (this.tileOpts.variants.includes(id)) return true;
        if (this.tileOpts.variants.length >= 16) {
            this.ui.toast(globalThis.VTTUi("Höchstens 16 Kachelvarianten."));
            return false;
        }
        this.tileOpts.variants = [...this.tileOpts.variants, id];
        return true;
    }

    setTile(gesture, col, row) {
        const { layer } = gesture;
        const size = layer.grid.size;
        const { cols, rows } = tileGridSize(this.doc, size);
        if (col < 0 || row < 0 || col >= cols || row >= rows) return;
        const key = cellKey(col, row);
        const before = layer.cells.get(key);
        const after = this.chooseTile(gesture, key);
        if (before === after) return;
        if (before === undefined && countTiles(this.doc) >= LIMITS.tiles) {
            if (!gesture.full) this.ui.toast(globalThis.VTTUi("Höchstens {p0} Kacheln pro Karte.",{p0:(LIMITS.tiles.toLocaleString("de"))}));
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
        }, [layer]);
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
        if (id !== this.activeLayerId) this.ui.clearTileGridOffer();
        this.activeLayerId = id;
        this.ui.noteLayerUse(this.layerById(id));
        this.validateClip();
        this.ui.refreshLayers();
        this.ui.updateTargets();
    }

    /** Layer kind a tool works on (null: select/pan/eraser work across kinds). */
    toolKind(tool = this.tool) {
        return { brush: "raster", stamp: "stamps", label: "labels", path: "paths", tile: "tiles" }[tool] || null;
    }

    /** Keyboard layer switch in the tool context: next/previous layer of the tool's kind (top = first). */
    cycleLayer(step) {
        if (!this.doc) return;
        const kind = this.toolKind();
        const eraser = this.tool === "eraser" ? new Set(["raster", "tiles", "stamps"]) : null;
        const candidates = [...this.doc.layers].reverse().filter((layer) => (kind ? layer.kind === kind : !eraser || eraser.has(layer.kind)));
        if (!candidates.length) {
            this.ui.toast(globalThis.VTTUi("Keine passende Ebene für dieses Werkzeug."));
            return;
        }
        const index = candidates.findIndex((layer) => layer.id === this.activeLayerId);
        const next = candidates[(index + step + candidates.length) % candidates.length] || candidates[0];
        this.setActiveLayer(next.id);
        this.ui.toast(globalThis.VTTUi("Aktive Ebene: {name}", { name: next.name }));
    }

    // ---- brush clip (paint only inside a reference) --------------------------

    /** Valid references for the active raster layer: lower raster layers and any tile layer. */
    clipCandidates() {
        const target = this.activeLayer();
        if (!this.doc || !target || target.kind !== "raster") return [];
        const index = this.doc.layers.indexOf(target);
        return this.doc.layers.filter((layer, i) => (layer.kind === "raster" && i < index) || layer.kind === "tiles");
    }

    /** A missing, deleted or no longer lower reference switches the clip off with an explanation. */
    validateClip() {
        const id = this.clipOpts.layerId;
        if (!id || !this.doc) return;
        const target = this.activeLayer();
        if (target && target.kind !== "raster") return; // kept for when a raster layer is active again
        if (!this.clipCandidates().some((layer) => layer.id === id)) {
            const layer = this.layerById(id);
            this.clipOpts.layerId = null;
            this.clipOpts.notice = layer
                ? globalThis.VTTUi("Malbegrenzung aus: „{name}“ liegt nicht mehr unter der aktiven Malebene.", { name: layer.name })
                : globalThis.VTTUi("Malbegrenzung aus: Die Bezugsebene wurde gelöscht.");
        }
    }

    setClip(id) {
        this.clipOpts.notice = "";
        this.clipOpts.layerId = id && this.clipCandidates().some((layer) => layer.id === id) ? id : null;
        this.ui.refreshClip();
    }

    clipReference() {
        this.validateClip();
        const layer = this.clipOpts.layerId && this.layerById(this.clipOpts.layerId);
        if (!layer) return null;
        return layer.kind === "tiles" ? { cells: layer.cells, size: layer.grid.size } : { canvas: layer.canvas };
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
            if (!quiet) this.ui.toast(globalThis.VTTUi("Keine {p0} vorhanden – lege unter „Ebenen“ eine an.",{p0:(KIND_NAMES[kind])}));
            return null;
        }
        if (!layer.visible && !quiet) {
            this.ui.toast(globalThis.VTTUi("„{p0}“ ist ausgeblendet – blende die Ebene ein, um darauf zu arbeiten.",{p0:(layer.name)}));
            return null;
        }
        return layer;
    }

    layerCommand(label, apply, revert, bytes = 256, layers = []) {
        apply();
        this.afterLayerChange();
        this.commit({
            label,
            bytes,
            undo: () => { revert(); this.afterLayerChange(); },
            redo: () => { apply(); this.afterLayerChange(); },
        }, layers);
    }

    afterLayerChange() {
        if (!this.layerById(this.activeLayerId)) {
            const top = this.doc.layers[this.doc.layers.length - 1];
            this.activeLayerId = top ? top.id : null;
        }
        this.validateClip();
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
            this.ui.toast(globalThis.VTTUi("Höchstens {p0} Ebenen.",{p0:(LIMITS.layers)}));
            return;
        }
        if (kind === "raster" && countLayers(this.doc, "raster") >= LIMITS.rasterLayers) {
            this.ui.toast(globalThis.VTTUi("Höchstens {p0} Malebenen.",{p0:(LIMITS.rasterLayers)}));
            return;
        }
        if (kind === "raster" && !this.canAddRaster()) {
            this.ui.toast(globalThis.VTTUi("Die Malebenen wären zusammen zu groß für diese Kartengröße."));
            return;
        }
        const names = { raster: globalThis.VTTUi("Malebene"), paths: globalThis.VTTUi("Wege (Vektor)"), stamps: globalThis.VTTUi("Symbole"), labels: globalThis.VTTUi("Beschriftung"), tiles: globalThis.VTTUi("Kacheln") };
        const layer = createLayer(kind, `${names[kind]} ${countLayers(this.doc, kind) + 1}`, this.doc.size, collectIds(this.doc));
        if (kind === "tiles") layer.grid.size = this.tileOpts.size;
        const active = this.doc.layers.indexOf(this.activeLayer());
        const index = active >= 0 ? active + 1 : this.doc.layers.length;
        const bytes = kind === "raster" ? this.doc.size.w * this.doc.size.h * 4 : 256;
        this.layerCommand("Ebene hinzufügen",
            () => { this.doc.layers.splice(index, 0, layer); this.activeLayerId = layer.id; },
            () => { this.doc.layers.splice(this.doc.layers.indexOf(layer), 1); },
            bytes, [layer]);
        return layer;
    }

    deleteLayer(id) {
        const layer = this.layerById(id);
        if (!layer) return;
        if (this.doc.layers.length <= 1) {
            this.ui.toast(globalThis.VTTUi("Die letzte Ebene kann nicht gelöscht werden."));
            return;
        }
        const index = this.doc.layers.indexOf(layer);
        const bytes = layer.kind === "raster" ? this.doc.size.w * this.doc.size.h * 4 : layer.kind === "tiles" ? 256 + layer.cells.size * 48 : 256;
        this.layerCommand(`Ebene „${layer.name}“ löschen`,
            () => { this.doc.layers.splice(this.doc.layers.indexOf(layer), 1); },
            () => { this.doc.layers.splice(index, 0, layer); this.activeLayerId = layer.id; },
            bytes, [layer]);
        this.ui.toast(globalThis.VTTUi("Ebene „{p0}“ gelöscht – Strg+Z holt sie zurück.",{p0:(layer.name)}));
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
        this.layerCommand("Ebene verschieben", () => swap(from, to), () => swap(to, from), 256, [layer]);
    }

    setLayerProp(id, key, value) {
        const layer = this.layerById(id);
        if (!layer) return;
        const effect = ['coast', 'coastColor', 'coastWidth'].includes(key);
        const get = () => (effect ? layer.effects[key] : key === "gridSize" ? layer.grid.size : layer[key]);
        const set = (v) => {
            if (effect) { if (v === undefined) delete layer.effects[key]; else layer.effects[key] = v; }
            else if (key === "gridSize") layer.grid.size = v;
            else layer[key] = v;
        };
        const before = get();
        if (before === value) return;
        if (key === "gridSize") {
            if (layer.cells.size) {
                this.ui.offerTileGrid(value);
                this.ui.refreshLayers();
                return false;
            }
            this.ui.clearTileGridOffer();
            // Cells keep their column/row; refuse a size that would push used cells off the map.
            const { cols, rows } = tileGridSize(this.doc, value);
            if ([...layer.cells.keys()].some((k) => cellOf(k).col >= cols || cellOf(k).row >= rows)) {
                this.ui.toast(globalThis.VTTUi("Diese Kachelgröße ist zu groß: belegte Kacheln lägen außerhalb der Karte."));
                this.ui.refreshLayers();
                return;
            }
        }
        const labels = { visible: value ? globalThis.VTTUi("Ebene einblenden") : globalThis.VTTUi("Ebene ausblenden"), name: globalThis.VTTUi("Ebene umbenennen"), opacity: globalThis.VTTUi("Deckkraft"), coast: globalThis.VTTUi("Küstenlinie"), gridSize: globalThis.VTTUi("Kachelgröße") };
        this.layerCommand(labels[key] || "Ebene ändern", () => set(value), () => set(before), 256, [layer]);
        return true;
    }

    /** A new empty layer is the explicit alternative to moving occupied cells. */
    newTileLayer(size) {
        const previous = this.tileOpts.size;
        this.tileOpts.size = size;
        const layer = this.addLayer("tiles");
        if (!layer) this.tileOpts.size = previous;
        else this.ui.clearTileGridOffer();
        return layer;
    }

    // ---- items -------------------------------------------------------------

    addItems(layer, items, label) {
        if (countItems(this.doc) + items.length > LIMITS.items) {
            this.ui.toast(globalThis.VTTUi("Höchstens {p0} Symbole und Beschriftungen pro Karte.",{p0:(LIMITS.items)}));
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
        this.commit({ label, bytes: 256 * items.length, undo: revert, redo: apply }, [layer]);
        return true;
    }

    pathTarget() {
        if (this.doc.layers.some((layer) => layer.kind === "paths")) return this.targetLayer("paths") || false;
        if (this.doc.layers.length >= LIMITS.layers || countItems(this.doc) >= LIMITS.items) {
            this.ui.toast(globalThis.VTTUi("Höchstgrenze an Ebenen oder Kartenelementen erreicht."));
            return false;
        }
        return null; // No existing target: creation belongs to the committed stroke, not pointerdown.
    }

    addPath(item, targetId = undefined) {
        let layer;
        if (targetId || this.doc.layers.some((entry) => entry.kind === "paths")) {
            layer = targetId === undefined ? this.pathTarget() : this.layerById(targetId);
            if (!layer || layer.kind !== "paths" || !layer.visible) {
                this.ui.toast(globalThis.VTTUi("Die gewählte Wegeebene ist nicht mehr sichtbar oder vorhanden."));
                return false;
            }
            return this.addItems(layer, [item], item.material === "river" ? "Fluss zeichnen" : "Weg zeichnen");
        }
        if (this.doc.layers.length >= LIMITS.layers || countItems(this.doc) >= LIMITS.items) {
            this.ui.toast(globalThis.VTTUi("Höchstgrenze an Ebenen oder Kartenelementen erreicht."));
            return false;
        }
        layer = createLayer("paths", globalThis.VTTUi("Wege (Vektor)"), this.doc.size, collectIds(this.doc));
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
        this.commit({ label: item.material === "river" ? globalThis.VTTUi("Fluss zeichnen") : globalThis.VTTUi("Weg zeichnen"), bytes: 1024 + item.points.length * 24, undo: revert, redo: apply }, [layer]);
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
        this.commit({ label: items.length > 1 ? globalThis.VTTUi("Symbole streuen") : globalThis.VTTUi("Symbol setzen"), bytes: 256 * items.length, undo: revert, redo: apply }, [layer]);
    }

    removeLive(layer, items) {
        for (const item of items) {
            const index = layer.items.indexOf(item);
            if (index >= 0) layer.items.splice(index, 1);
            this.invalidateItem(item);
        }
    }

    deleteSelection() {
        this.commitEdit();
        if (this.selectionSet.count) this.selectionSet.remove();
    }

    // ---- canonical object order (render = list order, hit test = reverse) ----

    orderState(layers) {
        return new Map([...layers].map((layer) => [layer, layer.items.slice()]));
    }

    applyOrder(state) {
        for (const [layer, items] of state) layer.items.splice(0, layer.items.length, ...items);
        this.invalidate(null);
        this.afterItemChange();
    }

    /** Reorder the selected objects inside their layers without committing (returns changed). */
    reorderLive(mode) {
        const rows = this.selectionSet.objects;
        const byLayer = new Map();
        for (const { layer, item } of rows) {
            if (!byLayer.has(layer)) byLayer.set(layer, new Set());
            byLayer.get(layer).add(item);
        }
        let changed = false;
        for (const [layer, chosen] of byLayer) {
            const next = reorderItems(layer.items, chosen, mode);
            if (next.some((item, index) => item !== layer.items[index])) changed = true;
            layer.items.splice(0, layer.items.length, ...next);
        }
        if (changed) { this.invalidate(null); this.afterItemChange(); }
        return { changed, layers: byLayer.keys() };
    }

    reorderSelection(mode) {
        this.commitEdit();
        if (this.selectionSet.tiles || !this.selectionSet.objects.length) {
            this.ui.toast(globalThis.VTTUi("Wähle zuerst Symbole, Wege oder Beschriftungen aus."));
            return false;
        }
        const layers = new Set(this.selectionSet.objects.map(({ layer }) => layer));
        const before = this.orderState(layers);
        const { changed } = this.reorderLive(mode);
        if (!changed) {
            this.ui.toast(mode === "forward" || mode === "front" ? globalThis.VTTUi("Die Auswahl liegt bereits ganz vorne.") : globalThis.VTTUi("Die Auswahl liegt bereits ganz hinten."));
            return false;
        }
        const after = this.orderState(layers);
        const labels = { forward: globalThis.VTTUi("Eine Stufe nach vorne"), backward: globalThis.VTTUi("Eine Stufe nach hinten"),
            front: globalThis.VTTUi("Ganz nach vorne"), back: globalThis.VTTUi("Ganz nach hinten") };
        this.commit({ label: labels[mode], bytes: 256 + [...after.values()].reduce((sum, list) => sum + list.length * 8, 0),
            undo: () => this.applyOrder(before), redo: () => this.applyOrder(after) }, [...layers]);
        return true;
    }

    /** Alt+wheel: live steps, committed as one undo step when the wheel gesture pauses. */
    wheelReorder(forward) {
        if (this.selectionSet.tiles || !this.selectionSet.objects.length) return false;
        if (!this.wheelOrder) {
            this.commitEdit();
            const layers = new Set(this.selectionSet.objects.map(({ layer }) => layer));
            this.wheelOrder = { layers, before: this.orderState(layers), timer: 0 };
        }
        this.reorderLive(forward ? "forward" : "backward");
        clearTimeout(this.wheelOrder.timer);
        this.wheelOrder.timer = setTimeout(() => this.finishWheelOrder(true), 450);
        return true;
    }

    finishWheelOrder(commit = true) {
        const session = this.wheelOrder;
        if (!session) return;
        this.wheelOrder = null;
        clearTimeout(session.timer);
        const after = this.orderState(session.layers);
        const changed = [...after].some(([layer, items]) => items.some((item, i) => item !== session.before.get(layer)[i]));
        if (!changed) return;
        if (!commit) { this.applyOrder(session.before); return; }
        this.commit({ label: globalThis.VTTUi("Reihenfolge ändern"), bytes: 256 + [...after.values()].reduce((sum, list) => sum + list.length * 8, 0),
            undo: () => this.applyOrder(session.before), redo: () => this.applyOrder(after) }, [...session.layers]);
        this.gestureEnded();
    }

    // ---- named paths and explicit endpoint connection ----

    /**
     * Join the selected path with the nearest endpoint of another path in the same
     * layer and material within PATH_SNAP. Crossing paths are never joined implicitly.
     */
    connectPathEndpoints() {
        this.commitEdit();
        const found = this.selection && findItem(this.doc, this.selection);
        if (!found || !("points" in found.item)) return false;
        const { layer, item } = found;
        const absolute = (path) => path.points.map((p) => ({ x: path.x + p.x, y: path.y + p.y }));
        const own = absolute(item);
        const ends = [{ at: "start", p: own[0] }, { at: "end", p: own[own.length - 1] }];
        let best = null;
        for (const other of layer.items) {
            if (other === item || !("points" in other) || other.material !== item.material) continue;
            const points = absolute(other);
            for (const mine of ends) {
                for (const theirs of [{ at: "start", p: points[0] }, { at: "end", p: points[points.length - 1] }]) {
                    const distance = Math.hypot(mine.p.x - theirs.p.x, mine.p.y - theirs.p.y);
                    if (distance <= PATH_SNAP && (!best || distance < best.distance)) best = { other, points, mine: mine.at, theirs: theirs.at, distance };
                }
            }
        }
        if (!best) {
            this.ui.toast(globalThis.VTTUi("Kein passender Endpunkt in der Nähe (gleiche Ebene und Art, höchstens {px} px).", { px: PATH_SNAP }));
            return false;
        }
        const theirs = best.theirs === "start" ? best.points : best.points.slice().reverse(); // starts at the joined end
        const merged = best.mine === "end" ? [...own, ...theirs.slice(1)] : [...theirs.slice().reverse(), ...own.slice(1)];
        if (merged.length > LIMITS.pathPoints) {
            this.ui.toast(globalThis.VTTUi("Zusammen hätten die Wege mehr als {count} Punkte. Bitte einen Weg vereinfachen.", { count: LIMITS.pathPoints }));
            return false;
        }
        const before = snapshot(item), other = best.other, otherIndex = layer.items.indexOf(other);
        const after = { ...before, x: merged[0].x, y: merged[0].y, points: merged.map((p) => ({ x: p.x - merged[0].x, y: p.y - merged[0].y })),
            ...(item.name || other.name ? { name: item.name || other.name } : {}) };
        const apply = () => {
            this.invalidateItem(item);
            Object.assign(item, snapshot(after));
            const index = layer.items.indexOf(other);
            if (index >= 0) layer.items.splice(index, 1);
            this.invalidate(null);
            this.afterItemChange();
        };
        const revert = () => {
            for (const key of Object.keys(item)) if (!(key in before)) delete item[key];
            Object.assign(item, snapshot(before));
            if (!layer.items.includes(other)) layer.items.splice(Math.min(otherIndex, layer.items.length), 0, other);
            this.invalidate(null);
            this.afterItemChange();
        };
        apply();
        this.commit({ label: globalThis.VTTUi("Wege verbinden"), bytes: 1024 + merged.length * 32, undo: revert, redo: apply }, [layer]);
        this.ui.toast(globalThis.VTTUi("Wege verbunden."));
        return true;
    }

    // ---- stamp scatter coverage and area fill ----

    scatterSpacing() {
        return Math.max(12, this.stampOpts.size * 0.75);
    }

    /** Planned stamp count for an area, computed before anything is allocated. */
    areaPlan(a, b) {
        const spacing = this.scatterSpacing();
        const x0 = clamp(Math.min(a.x, b.x), 0, this.doc.size.w), x1 = clamp(Math.max(a.x, b.x), 0, this.doc.size.w);
        const y0 = clamp(Math.min(a.y, b.y), 0, this.doc.size.h), y1 = clamp(Math.max(a.y, b.y), 0, this.doc.size.h);
        const cols = Math.max(1, Math.floor((x1 - x0) / spacing)), rows = Math.max(1, Math.floor((y1 - y0) / spacing));
        return { x0, y0, x1, y1, cols, rows, spacing, count: cols * rows };
    }

    fillArea(a, b) {
        const layer = this.targetLayer("stamps");
        if (!layer) return false;
        if (!this.stampOpts.asset || !this.assetAvailable(this.stampOpts.asset)) {
            this.ui.toast(globalThis.VTTUi("Wähle zuerst ein Symbol aus der Palette."));
            return false;
        }
        const plan = this.areaPlan(a, b);
        if (plan.count > AREA_MAX_ITEMS || countItems(this.doc) + plan.count > LIMITS.items || !this.history.canFit(256 * plan.count)) {
            this.ui.toast(globalThis.VTTUi("Diese Fläche bräuchte {count} Symbole und überschreitet das Budget (höchstens {max} je Fläche, {limit} pro Karte). Bitte kleiner ziehen oder Symbolgröße erhöhen.",
                { count: plan.count, max: AREA_MAX_ITEMS, limit: LIMITS.items }));
            return false;
        }
        this.commitEdit();
        const items = [], used = new Set();
        const cellW = (plan.x1 - plan.x0) / plan.cols, cellH = (plan.y1 - plan.y0) / plan.rows;
        for (let row = 0; row < plan.rows; row += 1) {
            for (let col = 0; col < plan.cols; col += 1) {
                const jitter = this.stampOpts.vary ? 0.35 : 0.15;
                const point = { x: plan.x0 + (col + 0.5 + (Math.random() - 0.5) * jitter) * cellW,
                    y: plan.y0 + (row + 0.5 + (Math.random() - 0.5) * jitter) * cellH };
                const item = this.createStamp(point, this.stampOpts.asset);
                const key = `${item.x},${item.y}`;
                if (used.has(key)) continue; // a stamp grid never stacks two stamps on one position
                used.add(key);
                items.push(item);
            }
        }
        return this.addItems(layer, items, globalThis.VTTUi("Fläche füllen"));
    }

    // ---- own images: project-bound, content-addressed PNG assets ----

    /** Catalog assets are always available; own images only when embedded in this document. */
    assetAvailable(id) {
        return !isCustomAsset(id) || !!this.doc?.assets?.some((asset) => asset.id === id);
    }

    /** Drop tool choices that point to own images of another (or no longer present) document. */
    sanitizeAssetChoices() {
        if (!this.doc || !this.palette) return;
        if (this.stampOpts.asset && !this.assetAvailable(this.stampOpts.asset)) {
            const fallback = this.palette.stamps.has("kenney:forest") ? "kenney:forest" : this.palette.groups.find((g) => !g.custom && g.ids.length)?.ids[0];
            this.stampOpts.asset = null;
            this.stampOpts.crop = null;
            if (fallback) this.ui.chooseStamp(fallback, { openSheet: false });
        }
        if (this.tileOpts.asset && !this.assetAvailable(this.tileOpts.asset)) this.tileOpts.asset = null;
        this.tileOpts.variants = this.tileOpts.variants.filter((id) => this.assetAvailable(id));
        if (this.labelOpts.symbol && !this.assetAvailable(this.labelOpts.symbol)) this.labelOpts.symbol = null;
        if (this.paintBrush.image?.asset && !this.assetAvailable(this.paintBrush.image.asset)) {
            this.paintBrush.image = null;
            if (this.paintBrush.shape === "image") this.paintBrush.shape = "round";
        }
    }

    assetUsage() {
        const list = this.doc?.assets || [];
        return { count: list.length, bytes: list.reduce((sum, a) => sum + a.bytes.length, 0), pixels: list.reduce((sum, a) => sum + a.width * a.height, 0) };
    }

    /** Same bounds as both validators, checked before decoding or storing anything. */
    assetBudgetProblem(byteLength, width, height) {
        const usage = this.assetUsage();
        if (usage.count + 1 > LIMITS.customAssets) return globalThis.VTTUi("Höchstens {count} eigene Bilder pro Karte. Entferne zuerst ein unbenutztes Bild.", { count: LIMITS.customAssets });
        if (width < 1 || height < 1 || width > LIMITS.customAssetSide || height > LIMITS.customAssetSide) return globalThis.VTTUi("Eigene Bilder dürfen höchstens {px} Pixel je Seite haben.", { px: LIMITS.customAssetSide });
        if (byteLength > LIMITS.customAssetBytes) return globalThis.VTTUi("Das PNG ist größer als 4 MiB. Bitte verkleinern oder zuschneiden.");
        if (usage.bytes + byteLength > LIMITS.customAssetTotalBytes) return globalThis.VTTUi("Eigene Bilder wären zusammen größer als 12 MiB.");
        if (usage.pixels + width * height > LIMITS.customAssetPixels) return globalThis.VTTUi("Eigene Bilder hätten zusammen mehr als 8 Millionen Pixel.");
        return null;
    }

    /**
     * Embed a finished PNG as own image (one undo step). A different image always
     * gets a new id; identical bytes reuse the existing entry.
     */
    async addCustomAsset({ bytes, width, height, label, style, perspective, source, license }) {
        const doc = this.doc;
        if (!doc) return null;
        const id = customAssetId(bytes);
        const existing = doc.assets.find((asset) => asset.id === id);
        if (existing) {
            this.ui.chooseStamp(id, { openSheet: false });
            this.ui.toast(globalThis.VTTUi("Dieses Bild ist bereits in der Karte vorhanden."));
            return existing;
        }
        const problem = this.assetBudgetProblem(bytes.length, width, height);
        if (problem) throw new ValidationError(problem);
        if (!this.history.canFit(bytes.length + 512)) throw new ValidationError(globalThis.VTTUi("Das Bild ist zu groß für den Verlauf."));
        const [entry] = validateAssets([{ id, label, width, height, style, perspective, source, license, pngBytes: bytes }], "binary");
        await this.palette.registerCustomAssets([entry]);
        if (this.doc !== doc) return null;
        const apply = () => {
            if (!doc.assets.includes(entry)) doc.assets.push(entry);
            this.afterAssetChange();
        };
        const revert = () => {
            const index = doc.assets.indexOf(entry);
            if (index >= 0) doc.assets.splice(index, 1);
            this.afterAssetChange();
        };
        apply();
        this.commit({ label: globalThis.VTTUi("Eigenes Bild hinzufügen"), bytes: bytes.length + 512, undo: revert, redo: apply });
        this.ui.chooseStamp(id, { openSheet: false });
        return entry;
    }

    removeCustomAsset(id) {
        const doc = this.doc, entry = doc.assets.find((asset) => asset.id === id);
        if (!entry) return false;
        this.commitEdit();
        if (referencedAssetIds(doc).has(id)) {
            this.ui.toast(globalThis.VTTUi("„{label}“ wird noch auf der Karte verwendet und bleibt erhalten.", { label: entry.label }));
            return false;
        }
        const index = doc.assets.indexOf(entry);
        const apply = () => { const at = doc.assets.indexOf(entry); if (at >= 0) doc.assets.splice(at, 1); this.afterAssetChange(); };
        const revert = () => { if (!doc.assets.includes(entry)) doc.assets.splice(Math.min(index, doc.assets.length), 0, entry); this.afterAssetChange(); };
        apply();
        this.commit({ label: globalThis.VTTUi("Eigenes Bild entfernen"), bytes: entry.bytes.length + 512, undo: revert, redo: apply });
        return true;
    }

    afterAssetChange() {
        this.palette.showDocumentAssets(this.doc);
        this.sanitizeAssetChoices();
        this.ui.refreshCustomAssets();
    }

    updateItem(item, before, after, label) {
        const set = (state) => {
            this.invalidateItem(item);
            Object.assign(item, snapshot(state));
            this.invalidateItem(item);
            this.afterItemChange();
        };
        this.afterItemChange();
        this.commit({ label, bytes: 512, undo: () => set(before), redo: () => set(after) }, [findItem(this.doc, item.id)?.layer].filter(Boolean));
    }

    afterItemChange() {
        if (this.selection && !findItem(this.doc, this.selection)) this.selection = null;
        this.ui.refreshPlaces();
        this.ui.refreshInspector();
        this.requestFrame();
    }

    select(itemId,add=false) {
        if (this.selection !== itemId || add) this.commitEdit();
        this.selectionSet.choose(itemId,add);
        if (itemId) {
            const found = findItem(this.doc, itemId);
            if (found && found.layer.id !== this.activeLayerId) {
                this.activeLayerId = found.layer.id;
                this.ui.noteLayerUse(found.layer);
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
        if('text' in found.item){
            const next={...found.item,...patch};
            if(!next.text.trim() && !next.pin && !next.symbol){
                this.ui.toast(globalThis.VTTUi('Ohne Namen muss ein Symbol oder eine Ortsnadel sichtbar bleiben.'));this.ui.refreshInspector();return;
            }
        }
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
        if (this.wheelOrder) this.finishWheelOrder(true);
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

    stampGridSize(value) {
        return Math.max(8, Math.min(256, Math.round(Number(value)) || 32));
    }

    /** Single source for stamp preview and placement; grid is optional and off by default. */
    stampPoint(point) {
        const grid = this.stampOpts.grid;
        const x = grid ? Math.round(point.x / grid) * grid : point.x;
        const y = grid ? Math.round(point.y / grid) * grid : point.y;
        return this.clampToMap(x, y);
    }

    createStamp(point, assetId) {
        const opts = this.stampOpts;
        const vary = opts.vary ? 1 + (Math.random() - 0.5) * 0.24 : 1;
        const rot = opts.vary ? opts.rot + (Math.random() - 0.5) * 12 : opts.rot;
        const at = this.stampPoint(point);
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
            text: this.labelOpts.named || (!this.labelOpts.pin && !this.labelOpts.symbol) ? globalThis.VTTUi("Neuer Ort") : "",
            style,
            size: LABEL_STYLES[style].size,
            rot: 0,
            color: style === "water" ? "#1d4654" : "#3b2a1a",
            pin: this.labelOpts.pin,
            symbol: kind && this.labelOpts.symbol && this.assetAvailable(this.labelOpts.symbol) ? { asset: this.labelOpts.symbol, size: this.labelOpts.symbolSize } : null,
            place: kind ? { kind, lore: "" } : null,
            ...(this.labelOpts.font ? { font: this.labelOpts.font } : {}),
        };
    }

    // ---- strokes -----------------------------------------------------------

    beginStroke(point, pressure) {
        const layer = this.targetLayer("raster");
        if (!layer) return false;
        this.commitEdit();
        // The clip reference is captured once at stroke start (frozen for this gesture).
        const clip = this.tool === "brush" ? this.clipReference() : null;
        this.engine.begin(layer, { ...this.brush, erase: this.tool === "eraser" }, clip);
        this.engine.addPoint(point.x, point.y, pressure);
        this.strokeActive = true;
        this.requestFrame();
        return true;
    }

    continueStroke(point, pressure) {
        if (!this.strokeActive) return;
        this.engine.addPoint(point.x, point.y, pressure);
        const active = this.engine.active;
        const rect = active && rectClamp(rectUnion(active.total, active.pending), this.doc.size.w, this.doc.size.h);
        if (rect && !this.history.canFit(rect.w * rect.h * 8 + 256)) {
            // Preflight: revert the whole stroke instead of clearing earlier undo steps.
            this.cancelStroke();
            this.ui.toast(globalThis.VTTUi("Diese Fläche ist zu groß für den Verlauf und wurde zurückgesetzt. Bitte in kleineren Schritten malen."));
            return;
        }
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
            label: this.tool === "eraser" ? globalThis.VTTUi("Radieren") : globalThis.VTTUi("Pinselstrich"),
            bytes: imgBefore.data.length + imgAfter.data.length,
            undo: () => put(imgBefore),
            redo: () => put(imgAfter),
        }, [layer]);
    }

    cancelStroke() {
        if (!this.strokeActive) return;
        const layer = this.engine.active.layer;
        const rect = this.engine.cancel();
        this.strokeActive = false;
        if (rect) this.invalidate(pad(rect, layer.effects.coast ? COAST_PAD : 0));
    }

    // ---- general eraser (raster, tiles, stamps; paths and labels are never touched) ----

    eraseTargets() {
        const supported = new Set(["raster", "tiles", "stamps"]);
        if (this.eraseScope === "visible") return this.doc.layers.filter((layer) => layer.visible && supported.has(layer.kind));
        const layer = this.activeLayer(); // no silent switch to another layer
        return layer && layer.visible && supported.has(layer.kind) ? [layer] : [];
    }

    beginErase(point, pressure) {
        const targets = this.eraseTargets();
        if (!targets.length) {
            this.ui.toast(globalThis.VTTUi("Der Radierer wirkt nur auf sichtbare Raster-, Kachel- und Symbolebenen. Wähle eine solche Ebene oder „Alle sichtbaren Ebenen“."));
            return false;
        }
        this.commitEdit();
        const gesture = { rasters: [], tiles: new Map(), stamps: new Map(), last: null, refused: false, size: this.brush.size };
        for (const layer of targets.filter((entry) => entry.kind === "raster")) {
            const engine = new StrokeEngine(this.doc.size.w, this.doc.size.h);
            engine.begin(layer, { ...this.brush, erase: true });
            gesture.rasters.push({ layer, engine });
        }
        this.eraseGesture = gesture;
        gesture.targets = targets;
        this.continueErase(point, pressure);
        return true;
    }

    eraseEstimate(gesture) {
        let bytes = 512;
        for (const { layer, engine } of gesture.rasters) {
            const rect = rectClamp(rectUnion(engine.active?.total, engine.active?.pending), layer.canvas.width, layer.canvas.height);
            if (rect) bytes += rect.w * rect.h * 8; // before + after ImageData
        }
        for (const cells of gesture.tiles.values()) bytes += cells.before.size * 96;
        for (const entry of gesture.stamps.values()) bytes += entry.removed.size * 512;
        return bytes;
    }

    continueErase(point, pressure) {
        const gesture = this.eraseGesture;
        if (!gesture || gesture.refused) return;
        const radius = Math.max(1, gesture.size / 2);
        const from = gesture.last || point;
        const steps = Math.max(1, Math.ceil(Math.hypot(point.x - from.x, point.y - from.y) / Math.max(1, radius / 2)));
        for (let i = gesture.last ? 1 : 0; i <= steps; i += 1) {
            const t = i / steps;
            this.eraseAt(gesture, { x: from.x + (point.x - from.x) * t, y: from.y + (point.y - from.y) * t }, radius);
        }
        for (const { layer, engine } of gesture.rasters) {
            engine.addPoint(point.x, point.y, pressure);
            const rect = engine.flush();
            if (rect) this.invalidate(pad(rect, layer.effects.coast ? COAST_PAD : 0));
        }
        gesture.last = point;
        // Preflight against the 64 MiB history budget: refuse and fully revert instead of
        // letting push() discard the user's earlier undo steps.
        if (!this.history.canFit(this.eraseEstimate(gesture))) {
            this.cancelErase();
            this.ui.toast(globalThis.VTTUi("Diese Radierfläche ist zu groß für den Verlauf und wurde zurückgesetzt. Bitte in kleineren Schritten radieren."));
            return;
        }
        this.requestFrame();
    }

    eraseAt(gesture, at, radius) {
        const near = (rect) => {
            const dx = Math.max(rect.x - at.x, 0, at.x - (rect.x + rect.w));
            const dy = Math.max(rect.y - at.y, 0, at.y - (rect.y + rect.h));
            return dx * dx + dy * dy <= radius * radius;
        };
        for (const layer of gesture.targets) {
            if (layer.kind === "tiles") {
                const size = layer.grid.size;
                const record = gesture.tiles.get(layer) || { before: new Map() };
                for (let row = Math.floor((at.y - radius) / size); row <= Math.floor((at.y + radius) / size); row += 1) {
                    for (let col = Math.floor((at.x - radius) / size); col <= Math.floor((at.x + radius) / size); col += 1) {
                        const key = cellKey(col, row);
                        if (!layer.cells.has(key) || !near({ x: col * size, y: row * size, w: size, h: size })) continue;
                        if (!record.before.has(key)) record.before.set(key, layer.cells.get(key));
                        layer.cells.delete(key);
                        this.invalidate({ x: col * size, y: row * size, w: size, h: size });
                    }
                }
                if (record.before.size) gesture.tiles.set(layer, record);
            } else if (layer.kind === "stamps") {
                const entry = gesture.stamps.get(layer) || { original: layer.items.slice(), removed: new Set() };
                for (const item of [...layer.items]) {
                    const bounds = itemBounds(item, this.palette);
                    if (!near(bounds)) continue;
                    entry.removed.add(item);
                    layer.items.splice(layer.items.indexOf(item), 1);
                    this.invalidate(pad(bounds, 4));
                }
                if (entry.removed.size) gesture.stamps.set(layer, entry);
            }
        }
    }

    /** Restore tiles/stamps of a gesture (cancel or refused commit). */
    restoreErased(gesture) {
        for (const [layer, { before }] of gesture.tiles) {
            const size = layer.grid.size;
            for (const [key, asset] of before) {
                layer.cells.set(key, asset);
                const { col, row } = cellOf(key);
                this.invalidate({ x: col * size, y: row * size, w: size, h: size });
            }
        }
        for (const [layer, { original }] of gesture.stamps) {
            layer.items.splice(0, layer.items.length, ...original);
            this.invalidate({ x: 0, y: 0, w: this.doc.size.w, h: this.doc.size.h });
        }
    }

    /** Release the canvases of a per-gesture StrokeEngine (never the editor's shared engine). */
    disposeGestureEngines(gesture) {
        for (const { engine } of gesture.rasters) {
            if (engine === this.engine) continue;
            for (const canvas of [engine.base, engine.mask, engine.work]) {
                canvas.width = 0;
                canvas.height = 0;
            }
            engine.active = null;
        }
    }

    cancelErase() {
        const gesture = this.eraseGesture;
        this.eraseGesture = null;
        if (!gesture) return;
        try {
            for (const { layer, engine } of gesture.rasters) {
                const rect = engine.cancel(); // restores the layer from engine.base first
                if (rect) this.invalidate(pad(rect, layer.effects.coast ? COAST_PAD : 0));
            }
            this.restoreErased(gesture);
        } finally {
            this.disposeGestureEngines(gesture); // only after the restore has read the base copies
        }
        this.requestFrame();
    }

    endErase() {
        const gesture = this.eraseGesture;
        this.eraseGesture = null;
        if (!gesture) return;
        const rasters = [];
        try {
            if (gesture.refused) {
                for (const { engine } of gesture.rasters) engine.cancel();
                return;
            }
            for (const { layer, engine } of gesture.rasters) {
                const result = engine.end(); // before/after are independent ImageData copies
                this.invalidate(pad({ x: 0, y: 0, w: layer.canvas.width, h: layer.canvas.height }, 0));
                if (result) rasters.push({ layer, ...result });
            }
        } finally {
            this.disposeGestureEngines(gesture);
        }
        if (gesture.refused) return;
        const tiles = [...gesture.tiles].map(([layer, { before }]) =>
            ({ layer, before, after: new Map([...before.keys()].map((key) => [key, undefined])) }));
        const stamps = [...gesture.stamps].map(([layer, entry]) =>
            ({ layer, original: entry.original, kept: entry.original.filter((item) => !entry.removed.has(item)) }));
        if (!rasters.length && !tiles.length && !stamps.length) return;
        const bytes = rasters.reduce((sum, r) => sum + r.before.data.length + r.after.data.length, 512)
            + tiles.reduce((sum, t) => sum + t.before.size * 96, 0) + stamps.reduce((sum, s) => sum + (s.original.length - s.kept.length) * 512, 0);
        const putRaster = (r, image) => {
            r.layer.canvas.getContext("2d").putImageData(image, r.rect.x, r.rect.y);
            r.layer.rev += 1;
            this.invalidate(pad(r.rect, r.layer.effects.coast ? COAST_PAD : 0));
        };
        const putTiles = (t, values) => {
            const size = t.layer.grid.size;
            for (const [key, asset] of values) {
                if (asset === undefined) t.layer.cells.delete(key);
                else t.layer.cells.set(key, asset);
                const { col, row } = cellOf(key);
                this.invalidate({ x: col * size, y: row * size, w: size, h: size });
            }
        };
        const putStamps = (s, items) => {
            s.layer.items.splice(0, s.layer.items.length, ...items);
            this.invalidate({ x: 0, y: 0, w: this.doc.size.w, h: this.doc.size.h });
        };
        const undo = () => {
            rasters.forEach((r) => putRaster(r, r.before));
            tiles.forEach((t) => putTiles(t, t.before));
            stamps.forEach((s) => putStamps(s, s.original));
            this.requestFrame();
        };
        const command = { label: globalThis.VTTUi("Radieren"), bytes, strict: true, undo, redo: () => {
            rasters.forEach((r) => putRaster(r, r.after));
            tiles.forEach((t) => putTiles(t, t.after));
            stamps.forEach((s) => putStamps(s, s.kept));
            this.requestFrame();
        } };
        // Refuse rather than clear: the gesture is reverted and earlier history stays intact.
        if (!this.history.push(command)) {
            undo();
            this.ui.toast(globalThis.VTTUi("Diese Radierfläche ist zu groß für den Verlauf und wurde zurückgesetzt. Bitte in kleineren Schritten radieren."));
        } else {
            for (const { layer } of [...rasters, ...tiles, ...stamps]) this.ui.noteLayerUse(layer);
            this.ui.refreshLayers();
        }
    }

    cancelInteractions() {
        if (this.input) this.input.cancel();
        this.cancelStroke();
        this.cancelErase();
        this.cancelTiles();
    }

    // ---- history & persistence ---------------------------------------------

    commit(command, layers = []) {
        for (const layer of new Set(layers)) this.ui.noteLayerUse(layer);
        if (!this.history.push(command)) {
            this.ui.toast(globalThis.VTTUi("Dieser Schritt war zu groß für den Verlauf – ältere Schritte wurden verworfen."));
        }
    }

    undo() {
        this.cancelInteractions();
        this.commitEdit();
        const command = this.history.undo();
        if (command) this.ui.toast(globalThis.VTTUi("Rückgängig: {p0}",{p0:(command.label)}));
    }

    redo() {
        this.cancelInteractions();
        this.commitEdit();
        const command = this.history.redo();
        if (command) this.ui.toast(globalThis.VTTUi("Wiederholt: {p0}",{p0:(command.label)}));
    }

    onHistoryChange() {
        this.ui.updateUndo();
        this.ui.clearTileGridOffer();
        this.ui.refreshLayers();
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

    needsLeaveWarning() {
        if (!this.doc) return false;
        if (this.isMutating()) return true;
        if (!this.hasUnsavedChanges()) return false;
        return !!this.library.atlas || !this.drafts || this.autosave.generation !== this.generation;
    }

    savePrimary() {
        return this.library.accountId !== null ? this.library.save() : this.saveFile();
    }

    /** True while a gesture has live, not yet committed document changes. */
    isMutating() {
        return this.strokeActive || !!this.eraseGesture || !!this.wheelOrder || !!(this.input && this.input.mutating());
    }

    /** Called by the input layer whenever a gesture ends or is cancelled. */
    gestureEnded() {
        if (this.autosave.deferred) {
            this.autosave.deferred = false;
            this.scheduleAutosave();
        }
    }

    setTitle(value) {
        this.doc.meta.title = cleanText(value, LIMITS.title) || globalThis.VTTUi("Unbenannte Karte");
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
        this.commit({ label: globalThis.VTTUi("Kartenstil ändern"), bytes: 128, undo: () => apply(before), redo: () => apply(value) });
    }

    setAutosaveState(state, time) {
        const previous = this.autosave.state;
        this.autosave.state = state;
        this.ui.setStatus(state, time);
        if ((state === "failed" || state === "unavailable") && previous !== state) {
            this.ui.toast(state === "failed"
                ? globalThis.VTTUi("Autosave fehlgeschlagen – bitte über „Datei → Als Datei speichern“ sichern.")
                : globalThis.VTTUi("Autosave ist in diesem Browser nicht verfügbar – bitte als Datei speichern."));
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
            if (this.drafts === store && this.generation === generation) {
                this.autosave.generation = generation;
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
            if (this.isMutating()) { this.ui.toast(globalThis.VTTUi('Bitte die laufende Zeichenbewegung zuerst beenden.')); return false; }
            const generation = this.generation;
            const data = await serialize(this.doc, "file"); // snapshot taken synchronously at this generation
            const blob = new Blob([JSON.stringify(data)], { type: "application/json" });
            downloadBlob(blob, `${slugify(data.meta.title)}.rdmap.json`);
            // Only edits up to the snapshot are in the file; newer edits stay unsaved.
            if (generation > this.fileGeneration) this.fileGeneration = generation;
            this.ui.toast(this.generation === generation
                ? globalThis.VTTUi("Karte als Datei gespeichert.")
                : globalThis.VTTUi("Karte als Datei gespeichert – Änderungen während des Speicherns sind noch nicht in der Datei."));
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
            this.ui.toast(globalThis.VTTUi("„{p0}“ geladen.",{p0:(doc.meta.title)}));
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
        const doc = this.doc;
        const generation = this.generation;
        // Same pure helper the DM table uses for its library preview.
        const { blob } = await renderPngBlob({
            doc, palette: this.palette, renderer: this.renderer, scale, maxPixels: MAX_EXPORT_PIXELS,
            isStale: () => doc !== this.doc || generation !== this.generation,
            beforeRender: () => this.flushRender(),
        });
        return blob;
    }

    async exportBundle(scale) {
        this.commitEdit();
        if (this.isMutating()) { this.ui.toast(globalThis.VTTUi('Bitte die laufende Zeichenbewegung zuerst beenden.')); return; }
        const generation = this.generation;
        // Portable package: only own images the map actually shows travel with it (credits follow).
        const projectPromise = serialize(this.doc, "file", { referencedOnly: true });
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
        if (!initial) this.ui.toast(kind === "empty" ? globalThis.VTTUi("Leere Karte angelegt.") : globalThis.VTTUi("Startkarte geladen."));
    }

    setTool(tool) {
        if (this.tool === tool) return;
        this.cancelInteractions();
        this.commitEdit();
        this.tool = tool;
        if (tool !== "select" && tool !== "label") this.selection = null;
        // The eraser follows the active layer or the explicit all-visible scope; no silent layer switch.
        const kind = tool === "brush" ? "raster" : tool === "stamp" ? "stamps" : tool === "label" ? "labels"
            : tool === "path" ? "paths" : tool === "tile" ? "tiles" : null;
        if (kind) {
            const layer = this.targetLayer(kind, { quiet: true });
            if (layer) this.activeLayerId = layer.id;
        }
        this.ui.setTool(tool);
        this.requestFrame();
    }

    async useImageBrush(asset, crop = null) {
        const source = this.palette.stamps.get(asset), doc = this.doc;
        if (!source) { this.ui.toast(globalThis.VTTUi('Wähle zuerst ein Symbol oder eine Kachel.')); return; }
        try {
            const image = await this.palette.loadStamp(asset);
            if (this.doc !== doc) return;
            this.paintBrush.image = { ...imageBrush(image, crop, source.label), asset };
            this.paintBrush.shape = 'image';
            this.setTool('brush');this.ui.syncBrush();
            this.ui.toast(globalThis.VTTUi('Bildpinsel gewählt: {p0}', { p0: source.label }));
        } catch (error) { this.ui.showError(error.message); }
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
                selectionCount: editor.selectionSet.count,
                selectedIds: editor.selectionSet.ids.slice(),
                selectedTiles: editor.selectionSet.tiles ? snapshot(editor.selectionSet.tiles) : null,
                canUndo: editor.history.canUndo,
                canRedo: editor.history.canRedo,
                historySteps: editor.history.undoStack.length,
                autosave: editor.autosave.state,
                generation: editor.generation,
                localGeneration: editor.autosave.generation,
                leaveWarning: editor.needsLeaveWarning(),
                unsavedFile: editor.hasUnsavedFileChanges(),
                mutating: editor.isMutating(),
                layers: doc.layers.map((l) => ({ id: l.id, name: l.name, kind: l.kind, visible: l.visible, opacity: l.opacity, items: l.items ? l.items.length : null,
                    ...(l.kind === "tiles" ? { grid: l.grid.size, tiles: [...l.cells].map(([key, asset]) => ({ ...cellOf(key), asset })) } : {}) })),
                stamps: doc.layers.filter((l) => l.kind === "stamps").reduce((n, l) => n + l.items.length, 0),
                labels: labels.length,
                places: labels.filter((i) => i.place).map((i) => i.text),
                items: doc.layers.flatMap((l) => (l.items || []).map((i) => ({ layer: l.id, ...snapshot(i) }))),
                assets: (doc.assets || []).map(({ id, label, width, height, style, perspective, source, license, bytes }) =>
                    ({ id, label, width, height, style, perspective, source, license, bytes: bytes.length })),
                clip: editor.clipOpts.layerId,
                clipNotice: editor.clipOpts.notice,
                stampAsset: editor.stampOpts.asset,
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
    if (!(editor.library.atlas && error.status)) throw error;
});
exposeApi(editor, ready);
