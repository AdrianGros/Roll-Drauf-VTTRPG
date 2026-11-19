import {normalizeLandmass, LANDMASS_PRESETS, LANDMASS_VERSION, decorationPoints, validPresetParameters} from './landmass.js';
import {createLayer, collectIds, cellKey, cleanText, countItems, countTiles, newId, tileGridSize, LIMITS} from './document.js';
import {MATERIALS, materialTile} from './brush.js';

// A single cancellable job. The factory/timeout parameters allow actual stale,
// cancellation and timeout tests without allocating a project-sized image.
export class LandmassJob {
    constructor(factory = () => new Worker(new URL('./landmass-worker.js', import.meta.url), {type: 'module'}), timeout = 10000) {
        this.factory = factory; this.timeout = timeout; this.sequence = 0;
    }
    cancel() {
        this.sequence++;
        if (this.current) {
            const {worker, timer, reject} = this.current;
            this.current = null; clearTimeout(timer); worker.terminate(); reject(new Error('cancelled'));
        }
    }
    run(parameters, size) {
        this.cancel(); const id = this.sequence;
        return new Promise((resolve, reject) => {
            const worker = this.factory();
            const finish = (error, result) => {
                if (!this.current || this.current.id !== id) return;
                clearTimeout(this.current.timer); worker.terminate(); this.current = null;
                if (error) reject(new Error(error)); else resolve(result);
            };
            const timer = setTimeout(() => finish('timeout'), this.timeout);
            this.current = {id, worker, timer, reject};
            worker.onmessage = ({data}) => { if (data?.id === id) finish(data.error, data); };
            worker.onerror = () => finish('worker');
            try { worker.postMessage({id, parameters, size}); } catch (_error) { finish('worker'); }
        });
    }
}

const ui = (source, parameters) => globalThis.VTTUi(source, parameters);
const node = (tag, parent, text, attributes = {}) => {
    const element = document.createElement(tag);
    if (text !== null) element.textContent = text;
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
    parent.append(element); return element;
};

const PRESET_STORE = 'rd-mapmaker-landmass-presets';
const MAX_USER_PRESETS = 12;
// Decoration only with shipped assets: the Kenney pack, else the simple built-ins.
const DECORATION_ASSETS = {mountains: ['kenney:mountains', 'builtin:mountain'], forest: ['kenney:forest', 'builtin:tree']};

export function readUserPresets(storage = globalThis.localStorage) {
    try {
        const rows = JSON.parse(storage?.getItem(PRESET_STORE) || '[]');
        if (!Array.isArray(rows)) return [];
        return rows.slice(0, MAX_USER_PRESETS).filter(row => row && typeof row.name === 'string' && typeof row.version === 'string'
            && validPresetParameters(row.parameters)).map(row => ({
            name: cleanText(row.name, 40) || 'Vorlage', version: row.version.slice(0, 40), parameters: {...row.parameters},
            output: row.output === 'tile' ? 'tile' : 'material',
            material: MATERIALS.some(m => m.id === row.material) ? row.material : 'land',
            mountains: row.mountains === true, forest: row.forest === true,
        }));
    } catch (_error) { return []; }
}

export class LandmassDialog {
    constructor(editor) {
        this.editor = editor; this.job = new LandmassJob(); this.ticket = 0;
        const dialog = this.dialog = node('dialog', document.body, null,
            {id: 'landmassDialog', class: 'mm-dialog mm-dialog-wide mm-landmass', 'aria-labelledby': 'landmassTitle'});
        node('h2', dialog, ui('Landmasse erzeugen'), {id: 'landmassTitle'});
        node('p', dialog, ui('Die Vorschau verändert deine Karte nicht. Übernehmen legt eine neue Ebene an und ist ein einziger Rückgängig-Schritt.'));
        const form = this.form = node('form', dialog, null, {class: 'mm-landmass-fields'});
        const input = (name, label, attrs) => node('input', node('label', form, label), null, {name, ...attrs});
        this.select = (name, label, options, parent = form) => {
            const select = node('select', node('label', parent, label), null, {name, 'aria-label': label});
            for (const [value, text] of options) node('option', select, text, {value});
            return select;
        };
        this.preset = this.select('preset', ui('Vorlage'), [['', ui('Eigene Werte')]]);
        this.preset.id = 'landmassPreset';
        this.seed = input('seed', ui('Seed'), {type: 'number', min: 0, max: 4294967295, step: 1, value: 1337, required: ''});
        this.select('form', ui('Form'), [['island', ui('Insel')], ['continent', ui('Zusammenhängende Landmasse')]]);
        input('land', ui('Landanteil (%)'), {type: 'number', min: 10, max: 80, step: 1, value: 45, required: ''});
        input('roughness', ui('Küstenunruhe'), {type: 'number', min: 0, max: 100, step: 1, value: 60, required: ''});
        this.select('resolution', ui('Vorschauauflösung'), [128, 256, 512].map(n => [n, String(n)]));
        this.output = this.select('output', ui('Ausgabe'), [['material', ui('Material (Malebene)')], ['tile', ui('Gewählte Kachel (Kachelebene)')]]);
        this.material = this.select('material', ui('Material'), MATERIALS.map(m => [m.id, ui(m.name)]));
        this.material.value = 'land';
        const check = (name, label) => {
            const row = node('label', form, null, {class: 'mm-check'});
            const box = node('input', row, null, {type: 'checkbox', name});
            node('span', row, label); return box;
        };
        this.mountains = check('mountains', ui('Berge streuen'));
        this.forest = check('forest', ui('Wälder streuen'));
        this.outputHint = node('p', form, '', {class: 'mm-hint', id: 'landmassOutputHint'});
        const random = node('button', form, ui('Neuer Seed'), {type: 'button'});
        random.onclick = () => { this.seed.value = crypto.getRandomValues(new Uint32Array(1))[0]; this.preset.value = ''; this.reset(); };
        const presets = node('div', dialog, null, {class: 'mm-landmass-presets'});
        this.presetName = node('input', node('label', presets, ui('Name der Vorlage')), null, {type: 'text', maxlength: 40, id: 'landmassPresetName', autocomplete: 'off'});
        node('button', presets, ui('Als Vorlage speichern'), {type: 'button', class: 'mm-btn mm-btn-small', id: 'landmassPresetSave'}).onclick = () => this.savePreset();
        this.presetDelete = node('button', presets, ui('Vorlage löschen'), {type: 'button', class: 'mm-btn mm-btn-small', id: 'landmassPresetDelete', disabled: ''});
        this.presetDelete.onclick = () => this.deletePreset();
        this.canvas = node('canvas', dialog, null, {width: 128, height: 128, 'aria-label': ui('Landmassenvorschau'), hidden: ''});
        this.status = node('p', dialog, '', {role: 'status', 'aria-live': 'polite', id: 'landmassStatus'});
        const actions = node('div', dialog, null, {class: 'mm-dialog-actions'});
        this.previewButton = node('button', actions, ui('Vorschau berechnen'), {type: 'button', class: 'mm-btn', id: 'landmassPreview'});
        this.adoptButton = node('button', actions, ui('Übernehmen'), {type: 'button', class: 'mm-btn mm-btn-primary', id: 'landmassAdopt', disabled: ''});
        node('button', actions, ui('Abbrechen'), {type: 'button', class: 'mm-btn', id: 'landmassCancel'}).onclick = () => dialog.close();
        form.onsubmit = event => { event.preventDefault(); this.preview(); };
        form.oninput = (event) => { if (event.target !== this.preset) this.preset.value = ''; this.reset(); };
        form.onchange = (event) => { if (event.target === this.preset) this.applyPreset(); this.reset(); };
        this.previewButton.onclick = () => { if (form.reportValidity()) this.preview(); };
        this.adoptButton.onclick = () => this.adopt();
        dialog.addEventListener('close', () => this.reset());
        document.getElementById('landmassBtn').onclick = () => this.open();
        this.renderPresets();
    }
    open() {
        if (!this.editor.doc) return;
        this.reset(); this.syncAvailability(); this.dialog.showModal(); this.seed.focus();
    }
    close() { this.reset(); if (this.dialog.open) this.dialog.close(); }
    reset() {
        this.ticket++; this.job.cancel(); this.result = null;
        this.adoptButton.disabled = true; this.previewButton.disabled = false;
        this.canvas.hidden = true; this.status.textContent = '';
        this.dialog.setAttribute('aria-busy', 'false');
    }
    // ---- presets ---------------------------------------------------------
    renderPresets() {
        const value = this.preset.value;
        this.userPresets = readUserPresets();
        this.preset.replaceChildren();
        node('option', this.preset, ui('Eigene Werte'), {value: ''});
        for (const preset of LANDMASS_PRESETS) node('option', this.preset, `${ui(preset.name)} · ${preset.version}`, {value: 'builtin:' + preset.id});
        this.userPresets.forEach((preset, index) => {
            const supported = preset.version === LANDMASS_VERSION;
            const option = node('option', this.preset, supported ? `${preset.name} · ${preset.version}`
                : ui('{name} · {version} (andere Generatorversion, nicht anwendbar)', {name: preset.name, version: preset.version}), {value: 'user:' + index});
            option.disabled = !supported;
        });
        this.preset.value = [...this.preset.options].some(option => option.value === value && !option.disabled) ? value : '';
        this.presetDelete.disabled = !this.preset.value.startsWith('user:');
    }
    selectedPreset() {
        const value = this.preset.value;
        if (value.startsWith('builtin:')) return LANDMASS_PRESETS.find(p => 'builtin:' + p.id === value) || null;
        if (value.startsWith('user:')) return this.userPresets[Number(value.slice(5))] || null;
        return null;
    }
    applyPreset() {
        const preset = this.selectedPreset();
        this.presetDelete.disabled = !this.preset.value.startsWith('user:');
        if (!preset || preset.version !== LANDMASS_VERSION) return;
        const fields = this.form.elements;
        for (const key of ['seed', 'form', 'land', 'roughness', 'resolution']) fields[key].value = String(preset.parameters[key]);
        if (preset.output) {
            this.output.value = preset.output; this.material.value = preset.material;
            this.mountains.checked = preset.mountains; this.forest.checked = preset.forest;
        }
        this.presetName.value = preset.name ? ui(preset.name) : '';
        this.syncAvailability();
    }
    writePresets(rows) {
        try { localStorage.setItem(PRESET_STORE, JSON.stringify(rows)); return true; }
        catch (_error) { this.status.textContent = ui('Vorlagen lassen sich in diesem Browser nicht speichern.'); return false; }
    }
    savePreset() {
        const name = cleanText(this.presetName.value, 40);
        const parameters = this.parameters();
        const shape = {seed: parameters.seed, form: parameters.form, land: parameters.land, roughness: parameters.roughness, resolution: parameters.resolution};
        if (!name || !this.form.reportValidity() || !validPresetParameters(shape)) {
            this.status.textContent = ui('Bitte einen Namen und gültige Werte für die Vorlage angeben.'); return;
        }
        const options = this.options();
        const rows = readUserPresets().filter(row => row.name !== name);
        if (rows.length >= MAX_USER_PRESETS) { this.status.textContent = ui('Höchstens {count} eigene Vorlagen.', {count: MAX_USER_PRESETS}); return; }
        rows.push({name, version: LANDMASS_VERSION, parameters: shape, output: options.output, material: options.material,
            mountains: options.mountains, forest: options.forest});
        if (!this.writePresets(rows)) return;
        this.renderPresets();
        this.preset.value = 'user:' + (this.userPresets.findIndex(row => row.name === name));
        this.presetDelete.disabled = false;
        this.status.textContent = ui('Vorlage „{name}“ gespeichert ({version}).', {name, version: LANDMASS_VERSION});
    }
    deletePreset() {
        const value = this.preset.value;
        if (!value.startsWith('user:')) return;
        const rows = readUserPresets();
        rows.splice(Number(value.slice(5)), 1);
        if (!this.writePresets(rows)) return;
        this.preset.value = ''; this.renderPresets();
    }
    // ---- options -----------------------------------------------------------
    decorationAsset(kind) {
        const stamps = this.editor.palette?.stamps;
        return stamps ? DECORATION_ASSETS[kind].find(id => stamps.get(id)?.image) || null : null;
    }
    tileAsset() {
        const ed = this.editor, id = ed.tileOpts?.asset, stamp = id && ed.palette?.stamps.get(id);
        return stamp && stamp.tile && (!ed.assetAvailable || ed.assetAvailable(id)) ? id : null;
    }
    syncAvailability() {
        const tile = this.tileAsset();
        this.output.querySelector('[value=tile]').disabled = !tile;
        if (!tile && this.output.value === 'tile') this.output.value = 'material';
        this.material.disabled = this.output.value === 'tile';
        const hints = [];
        if (!tile) hints.push(ui('Für Kacheln zuerst im Kachelwerkzeug eine Kachel wählen.'));
        else hints.push(ui('Kachel: {label}', {label: this.editor.palette.stamps.get(tile).label}));
        for (const [box, kind] of [[this.mountains, 'mountains'], [this.forest, 'forest']]) {
            box.disabled = !this.decorationAsset(kind);
            if (box.disabled) box.checked = false;
        }
        if (this.mountains.disabled || this.forest.disabled) hints.push(ui('Dekoration nur mit geladenen Berg- oder Waldsymbolen.'));
        this.outputHint.textContent = hints.join(' ');
    }
    parameters() {
        const values = Object.fromEntries(new FormData(this.form));
        for (const key of ['seed', 'land', 'roughness', 'resolution']) values[key] = Number(values[key]);
        return values;
    }
    options() {
        const output = this.output.value === 'tile' ? 'tile' : 'material';
        return {output, material: this.material.value || 'land', mountains: this.mountains.checked, forest: this.forest.checked,
            tile: output === 'tile' ? this.tileAsset() : null, grid: this.editor.tileOpts?.size || 32};
    }
    // ---- preview -----------------------------------------------------------
    async preview() {
        this.reset(); this.syncAvailability();
        const ticket = this.ticket, doc = this.editor.doc, generation = this.editor.generation;
        const parameters = this.parameters(), options = this.options();
        try {
            normalizeLandmass(parameters, doc.size);
            if (options.output === 'tile' && !options.tile) throw new Error('tile');
            this.previewButton.disabled = true; this.dialog.setAttribute('aria-busy', 'true');
            this.status.textContent = ui('Vorschau wird berechnet …');
            const result = await this.job.run(parameters, doc.size);
            if (ticket !== this.ticket || !this.dialog.open || this.editor.doc !== doc || this.editor.generation !== generation) return;
            const {w, h, target} = result.parameters;
            if (!(result.mask instanceof Uint8Array) || result.mask.length !== w * h) throw new Error('worker');
            const mask = document.createElement('canvas'); mask.width = w; mask.height = h;
            const image = mask.getContext('2d').createImageData(w, h);
            for (let i = 0; i < result.mask.length; i++) {
                image.data[i * 4] = 130; image.data[i * 4 + 1] = 154; image.data[i * 4 + 2] = 88;
                image.data[i * 4 + 3] = result.mask[i] ? 255 : 0;
            }
            mask.getContext('2d').putImageData(image, 0, 0);
            const effective = result.parameters, decorations = this.decorations(result.mask, effective, options, doc.size);
            this.canvas.width = w; this.canvas.height = h;
            const ctx = this.canvas.getContext('2d');
            ctx.drawImage(mask, 0, 0);
            for (const deco of decorations) {
                ctx.fillStyle = deco.kind === 'mountains' ? '#5b4636' : '#2f5a2a';
                ctx.beginPath();
                if (deco.kind === 'mountains') { ctx.moveTo(deco.cx, deco.cy - 3); ctx.lineTo(deco.cx + 3, deco.cy + 2); ctx.lineTo(deco.cx - 3, deco.cy + 2); }
                else ctx.arc(deco.cx + .5, deco.cy + .5, 2, 0, Math.PI * 2);
                ctx.fill();
            }
            this.canvas.hidden = false;
            const extras = decorations.length ? ` · ${ui('{count} Symbole', {count: decorations.length})}` : '';
            this.status.textContent = `${effective.version} · Seed ${effective.seed} · ${this.form.elements.form.selectedOptions[0].textContent} · ${w}×${h} · ${(100 * target / (w * h)).toFixed(2)}% · ${ui('Küstenunruhe')} ${effective.roughness}${extras}`;
            this.result = {doc, generation, effective, options, mask: result.mask, maskCanvas: mask, decorations}; this.adoptButton.disabled = false;
        } catch (error) {
            if (ticket !== this.ticket) return;
            this.status.textContent = error.message === 'timeout'
                ? ui('Die Vorschau dauerte zu lange. Bitte versuche eine kleinere Auflösung.')
                : error.message === 'tile' ? ui('Für Kacheln zuerst im Kachelwerkzeug eine Kachel wählen.')
                    : ui('Keine Vorschau möglich. Prüfe Parameter und Inselrand oder versuche es erneut.');
        } finally {
            if (ticket === this.ticket) { this.previewButton.disabled = false; this.dialog.setAttribute('aria-busy', 'false'); }
        }
    }
    /** Fixed seed, separate random streams; placed only with loaded, matching assets. */
    decorations(mask, effective, options, size) {
        const result = [], mountains = [];
        for (const kind of ['mountains', 'forest']) {
            if (!options[kind]) continue;
            const asset = this.decorationAsset(kind);
            if (!asset) continue;
            const stamp = this.editor.palette.stamps.get(asset);
            const points = decorationPoints(mask, effective.w, effective.h, effective.seed, kind, undefined, kind === 'forest' ? mountains : []);
            if (kind === 'mountains') mountains.push(...points);
            for (const point of points) result.push({kind, asset, cx: point.cx, cy: point.cy,
                x: Math.round(point.x * size.w), y: Math.round(point.y * size.h), size: stamp.defaultSize || 88});
        }
        return result;
    }
    tileCells(result) {
        const {doc, mask, effective: {w, h}, options} = result;
        const grid = options.grid, {cols, rows} = tileGridSize(doc, grid), cells = new Map();
        for (let row = 0; row < rows; row++) for (let col = 0; col < cols; col++) {
            const mx = Math.min(w - 1, Math.floor((col + .5) * grid / doc.size.w * w));
            const my = Math.min(h - 1, Math.floor((row + .5) * grid / doc.size.h * h));
            if (mask[my * w + mx]) cells.set(cellKey(col, row), options.tile);
        }
        return cells;
    }
    // ---- adoption: every budget before any allocation, one undo step ----------
    adopt() {
        const ed = this.editor, result = this.result;
        if (!result || ed.doc !== result.doc || ed.generation !== result.generation) { this.reset(); return; }
        const {effective: p, options, decorations} = result;
        const tiles = options.output === 'tile';
        const cells = tiles ? this.tileCells(result) : null;
        const layersNeeded = 1 + (decorations.length ? 1 : 0);
        const bytes = (tiles ? 512 + cells.size * 48 : ed.doc.size.w * ed.doc.size.h * 4 + 512) + decorations.length * 256;
        if (ed.doc.layers.length + layersNeeded > LIMITS.layers || (!tiles && !ed.canAddRaster()) || !ed.history.canFit(bytes)) {
            this.status.textContent = ui('Die neue Ebene überschreitet das Ebenen-, Pixel- oder Undo-Budget. Verkleinere die Karte oder entferne eine Malebene.');
            return;
        }
        if ((tiles && countTiles(ed.doc) + cells.size > LIMITS.tiles) || (decorations.length && countItems(ed.doc) + decorations.length > LIMITS.items)) {
            this.status.textContent = ui('Das Ergebnis überschreitet das Kachel- oder Symbol-Budget der Karte. Wähle eine größere Kachel oder weniger Dekoration.');
            return;
        }
        if (tiles && !this.tileAsset()) { this.status.textContent = ui('Für Kacheln zuerst im Kachelwerkzeug eine Kachel wählen.'); return; }
        const name = `landmass-v1 ${p.seed} ${p.form === 'island' ? 'I' : 'C'} ${p.land}/${p.roughness}/${p.resolution}`;
        const taken = collectIds(ed.doc);
        const layer = createLayer(tiles ? 'tiles' : 'raster', name, ed.doc.size, taken);
        taken.add(layer.id);
        if (tiles) {
            layer.grid.size = options.grid;
            for (const [key, asset] of cells) layer.cells.set(key, asset);
        } else {
            const ctx = layer.canvas.getContext('2d');
            ctx.fillStyle = ctx.createPattern(materialTile(options.material), 'repeat'); ctx.fillRect(0, 0, layer.canvas.width, layer.canvas.height);
            ctx.globalCompositeOperation = 'destination-in'; ctx.imageSmoothingEnabled = true;
            ctx.drawImage(result.maskCanvas, 0, 0, layer.canvas.width, layer.canvas.height); ctx.globalCompositeOperation = 'source-over';
            layer.effects.coast = true; layer.rev++;
        }
        let deco = null;
        if (decorations.length) {
            deco = createLayer('stamps', ui('Landmasse-Symbole'), ed.doc.size, taken);
            taken.add(deco.id);
            for (const entry of decorations) {
                const id = newId('s', taken); taken.add(id);
                deco.items.push({id, asset: entry.asset, x: entry.x, y: entry.y, size: entry.size, rot: 0, flip: false});
            }
        }
        const index = ed.doc.layers.length, previous = ed.activeLayerId;
        const apply = () => {
            ed.doc.layers.splice(index, 0, layer);
            if (deco) ed.doc.layers.splice(index + 1, 0, deco);
            ed.activeLayerId = layer.id; ed.afterLayerChange();
        };
        const undo = () => {
            for (const entry of [deco, layer]) { const at = entry ? ed.doc.layers.indexOf(entry) : -1; if (at >= 0) ed.doc.layers.splice(at, 1); }
            ed.activeLayerId = previous; ed.afterLayerChange();
        };
        apply();
        if (!ed.history.push({label: ui('Landmasse erzeugen'), bytes, strict: true, undo, redo: apply})) { undo(); return; }
        this.dialog.close();
    }
}
