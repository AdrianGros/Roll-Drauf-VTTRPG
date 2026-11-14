// Small account/revision-bound previews; no editor or input handlers.
import { loadSnapshotPalette, thumbnailFromProject } from './snapshot.js';
let palettePromise;
function sharedPalette() {
    return palettePromise ||= loadSnapshotPalette().catch(error => { palettePromise = null; throw error; });
}
export class ProjectThumbnails {
    constructor({ request, palette = sharedPalette }) {
        this.request = request;
        this.palette = palette;
        this.cache = new Map();
        this.observer = new IntersectionObserver(entries => {
            for (const entry of entries) if (entry.isIntersecting) {
                this.observer.unobserve(entry.target);
                entry.target.__loadThumbnail?.();
            }
        });
    }
    reset(account) {
        this.observer.disconnect();
        if (this.account !== account) this.cache.clear();
        this.account = account;
    }
    card(project, isCurrent) {
        const frame = document.createElement('span');frame.className = 'project-thumbnail';
        const img = document.createElement('img');img.alt = '';img.hidden = true;
        const status = document.createElement('span');status.textContent = globalThis.VTTUi('Vorschau wird geladen …');
        frame.append(img, status);
        const key = `${this.account}:${project.id}:${project.revision}`;
        frame.__loadThumbnail = async () => {
            const current = () => frame.isConnected && isCurrent();
            if (!current()) return;
            try {
                let source = this.cache.get(key);
                if (!source) {
                    const snapshot = await thumbnailFromProject({ loadProject: () => this.request(project.id), palette: this.palette, isCurrent: current });
                    if (!snapshot || !current()) return;
                    source = await new Promise((resolve, reject) => {
                        const reader = new FileReader();reader.onload = () => resolve(reader.result);reader.onerror = reject;reader.readAsDataURL(snapshot.blob);
                    });
                    if (!current()) return;
                    this.cache.set(key, source);
                    while (this.cache.size > 32) this.cache.delete(this.cache.keys().next().value);
                }
                if (!current()) return;
                img.src = source;img.hidden = false;status.hidden = true;
            } catch (_error) {
                if (current()) status.textContent = globalThis.VTTUi('Vorschau nicht verfügbar');
            }
        };
        this.observer.observe(frame);
        return frame;
    }
}
