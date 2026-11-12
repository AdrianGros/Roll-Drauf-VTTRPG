import {normalizeLandmass} from './landmass.js';
import {createLayer, collectIds, LIMITS} from './document.js';
import {materialTile} from './brush.js';

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

const ui = source => globalThis.VTTUi(source);
const node = (tag, parent, text, attributes = {}) => {
    const element = document.createElement(tag);
    if (text !== null) element.textContent = text;
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
    parent.append(element); return element;
};

export class LandmassDialog {
    constructor(editor) {
        this.editor = editor; this.job = new LandmassJob(); this.ticket = 0;
        const dialog = this.dialog = node('dialog', document.body, null,
            {id: 'landmassDialog', class: 'mm-dialog mm-dialog-wide mm-landmass', 'aria-labelledby': 'landmassTitle'});
        node('h2', dialog, ui('Landmasse erzeugen'), {id: 'landmassTitle'});
        node('p', dialog, ui('Die Vorschau verändert deine Karte nicht. Übernehmen legt eine neue Malebene an.'));
        const form = this.form = node('form', dialog, null, {class: 'mm-landmass-fields'});
        const input = (name, label, attrs) => node('input', node('label', form, label), null, {name, ...attrs});
        this.seed = input('seed', ui('Seed'), {type: 'number', min: 0, max: 4294967295, step: 1, value: 1337, required: ''});
        this.select = (name, label, options) => {
            const select = node('select', node('label', form, label), null, {name, 'aria-label': label});
            for (const [value, text] of options) node('option', select, text, {value});
            return select;
        };
        this.select('form', ui('Form'), [['island', ui('Insel')], ['continent', ui('Zusammenhängende Landmasse')]]);
        input('land', ui('Landanteil (%)'), {type: 'number', min: 10, max: 80, step: 1, value: 45, required: ''});
        input('roughness', ui('Küstenunruhe'), {type: 'number', min: 0, max: 100, step: 1, value: 60, required: ''});
        this.select('resolution', ui('Vorschauauflösung'), [128, 256, 512].map(n => [n, String(n)]));
        const random = node('button', form, ui('Neuer Seed'), {type: 'button'});
        random.onclick = () => { this.seed.value = crypto.getRandomValues(new Uint32Array(1))[0]; this.reset(); };
        this.canvas = node('canvas', dialog, null, {width: 128, height: 128, 'aria-label': ui('Landmassenvorschau'), hidden: ''});
        this.status = node('p', dialog, '', {role: 'status', 'aria-live': 'polite', id: 'landmassStatus'});
        const actions = node('div', dialog, null, {class: 'mm-dialog-actions'});
        this.previewButton = node('button', actions, ui('Vorschau berechnen'), {type: 'button', class: 'mm-btn', id: 'landmassPreview'});
        this.adoptButton = node('button', actions, ui('Übernehmen'), {type: 'button', class: 'mm-btn mm-btn-primary', id: 'landmassAdopt', disabled: ''});
        node('button', actions, ui('Abbrechen'), {type: 'button', class: 'mm-btn', id: 'landmassCancel'}).onclick = () => dialog.close();
        form.onsubmit = event => { event.preventDefault(); this.preview(); };
        form.oninput = () => this.reset(); form.onchange = () => this.reset();
        this.previewButton.onclick = () => { if (form.reportValidity()) this.preview(); };
        this.adoptButton.onclick = () => this.adopt();
        dialog.addEventListener('close', () => this.reset());
        document.getElementById('landmassBtn').onclick = () => this.open();
    }
    open() {
        if (!this.editor.doc) return;
        this.reset(); this.dialog.showModal(); this.seed.focus();
    }
    close() { this.reset(); if (this.dialog.open) this.dialog.close(); }
    reset() {
        this.ticket++; this.job.cancel(); this.result = null;
        this.adoptButton.disabled = true; this.previewButton.disabled = false;
        this.canvas.hidden = true; this.status.textContent = '';
        this.dialog.setAttribute('aria-busy', 'false');
    }
    parameters() {
        const values = Object.fromEntries(new FormData(this.form));
        for (const key of ['seed', 'land', 'roughness', 'resolution']) values[key] = Number(values[key]);
        return values;
    }
    async preview() {
        this.reset(); const ticket = this.ticket, doc = this.editor.doc, generation = this.editor.generation;
        const parameters = this.parameters();
        try {
            normalizeLandmass(parameters, doc.size);
            this.previewButton.disabled = true; this.dialog.setAttribute('aria-busy', 'true');
            this.status.textContent = ui('Vorschau wird berechnet …');
            const result = await this.job.run(parameters, doc.size);
            if (ticket !== this.ticket || !this.dialog.open || this.editor.doc !== doc || this.editor.generation !== generation) return;
            const {w, h, target} = result.parameters;
            if (!(result.mask instanceof Uint8Array) || result.mask.length !== w * h) throw new Error('worker');
            this.canvas.width = w; this.canvas.height = h;
            const ctx = this.canvas.getContext('2d'), image = ctx.createImageData(w, h);
            for (let i = 0; i < result.mask.length; i++) {
                image.data[i * 4] = 130; image.data[i * 4 + 1] = 154; image.data[i * 4 + 2] = 88;
                image.data[i * 4 + 3] = result.mask[i] ? 255 : 0;
            }
            ctx.putImageData(image, 0, 0); this.canvas.hidden = false;
            const effective = result.parameters;
            this.status.textContent = `${effective.version} · Seed ${effective.seed} · ${this.form.elements.form.selectedOptions[0].textContent} · ${w}×${h} · ${(100 * target / (w * h)).toFixed(2)}% · ${ui('Küstenunruhe')} ${effective.roughness}`;
            this.result = {doc, generation, effective}; this.adoptButton.disabled = false;
        } catch (error) {
            if (ticket !== this.ticket) return;
            this.status.textContent = error.message === 'timeout'
                ? ui('Die Vorschau dauerte zu lange. Bitte versuche eine kleinere Auflösung.')
                : ui('Keine Vorschau möglich. Prüfe Parameter und Inselrand oder versuche es erneut.');
        } finally {
            if (ticket === this.ticket) { this.previewButton.disabled = false; this.dialog.setAttribute('aria-busy', 'false'); }
        }
    }
    adopt() {
        const ed = this.editor, result = this.result;
        if (!result || ed.doc !== result.doc || ed.generation !== result.generation) { this.reset(); return; }
        const bytes = ed.doc.size.w * ed.doc.size.h * 4 + 512;
        // Do every budget check before allocating the full raster or changing history.
        if (ed.doc.layers.length >= LIMITS.layers || !ed.canAddRaster() || !ed.history.canFit(bytes)) {
            this.status.textContent = ui('Die neue Ebene überschreitet das Ebenen-, Pixel- oder Undo-Budget. Verkleinere die Karte oder entferne eine Malebene.');
            return;
        }
        const {effective: p} = result;
        const name = `landmass-v1 ${p.seed} ${p.form === 'island' ? 'I' : 'C'} ${p.land}/${p.roughness}/${p.resolution}`;
        const layer = createLayer('raster', name, ed.doc.size, collectIds(ed.doc));
        const ctx = layer.canvas.getContext('2d');
        ctx.fillStyle = ctx.createPattern(materialTile('land'), 'repeat'); ctx.fillRect(0, 0, layer.canvas.width, layer.canvas.height);
        ctx.globalCompositeOperation = 'destination-in'; ctx.imageSmoothingEnabled = true;
        ctx.drawImage(this.canvas, 0, 0, layer.canvas.width, layer.canvas.height); ctx.globalCompositeOperation = 'source-over';
        layer.effects.coast = true; layer.rev++;
        const index = ed.doc.layers.length, previous = ed.activeLayerId;
        const apply = () => { ed.doc.layers.splice(index, 0, layer); ed.activeLayerId = layer.id; ed.afterLayerChange(); };
        const undo = () => { ed.doc.layers.splice(ed.doc.layers.indexOf(layer), 1); ed.activeLayerId = previous; ed.afterLayerChange(); };
        apply();
        if (!ed.history.push({label: ui('Landmasse erzeugen'), bytes, strict: true, undo, redo: apply})) { undo(); return; }
        this.dialog.close();
    }
}
