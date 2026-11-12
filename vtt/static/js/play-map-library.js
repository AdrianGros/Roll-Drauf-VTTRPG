globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
// DM-only: own Mapmaker library -> table page. Loaded by play-dm.js; the Player
// composition never imports this file. No Editor instance, iframe or hidden draw handler:
// the preview is the shared pure snapshot helper over the saved project.
import { loadSnapshotPalette, snapshotFromProject } from "/static/mapmaker/js/snapshot.js";
import { loadPalette } from "/static/mapmaker/js/stamps.js";

const LIBRARY = "/api/assets/mapmaker/projects";

function el(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
        if (key === "text") node.textContent = value;
        else if (key in node) node[key] = value;
        else node.setAttribute(key, value);
    }
    node.append(...children);
    return node;
}

function requestId() {
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    return "lib-" + Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export class MapLibraryController {
    constructor(ui) {
        this.ui = ui;
        this.page = 1;
        this.listSequence = 0;
        this.selectSequence = 0;
        this.selection = null;     // immutable snapshot; replaced or dropped on every change
        this.pending = null;       // {requestId, mapId, layerId} for one confirmed selection
        this.busy = false;
        this.palette = null;
        this.previewUrl = null;
        this.build();
    }

    build() {
        this.dialog = el("dialog", { id: "mapLibraryDialog", className: "map-library-dialog" });
        this.dialog.setAttribute("aria-labelledby", "mapLibraryTitle");
        this.search = el("input", { id: "mapLibrarySearch", type: "search", maxLength: 80 });
        this.search.setAttribute("aria-label", globalThis.VTTUi("Eigene Karten durchsuchen"));
        this.list = el("ul", { id: "mapLibraryList", className: "map-library-list" });
        this.prev = el("button", { id: "mapLibraryPrev", type: "button", className: "mini-btn secondary", text: globalThis.VTTUi("Zurück") });
        this.next = el("button", { id: "mapLibraryNext", type: "button", className: "mini-btn secondary", text: globalThis.VTTUi("Weiter") });
        this.pageLabel = el("span", { id: "mapLibraryPage", className: "muted" });
        this.preview = el("img", { id: "mapLibraryPreview", alt: "", hidden: true });
        this.previewInfo = el("p", { id: "mapLibraryPreviewInfo", className: "muted" });
        this.nameInput = el("input", { id: "mapLibraryName", type: "text", maxLength: 120, disabled: true });
        this.nameInput.setAttribute("aria-label", globalThis.VTTUi("Titel der Tischkarte"));
        this.gridInput = el("input", { id: "mapLibraryGrid", type: "number", min: 16, max: 300, step: 1, value: 70, disabled: true });
        this.gridInput.setAttribute("aria-label", globalThis.VTTUi("Raster in Pixel"));
        this.consent = el("input", { id: "mapLibraryConsent", type: "checkbox", disabled: true });
        this.confirm = el("button", { id: "mapLibraryConfirm", type: "button", className: "mini-btn",
            text: globalThis.VTTUi("Zum Tisch hinzufügen"), disabled: true });
        this.status = el("p", { id: "mapLibraryStatus", className: "muted" });
        this.status.setAttribute("role", "status");
        const close = el("button", { id: "mapLibraryClose", type: "button", className: "mini-btn secondary", text: globalThis.VTTUi("Schließen") });
        this.dialog.append(
            el("h2", { id: "mapLibraryTitle", text: globalThis.VTTUi("Eigene Bibliothek") }),
            this.search, this.list,
            el("div", { className: "button-row" }, this.prev, this.pageLabel, this.next),
            this.preview, this.previewInfo,
            el("label", {}, el("span", { text: globalThis.VTTUi("Titel") }), this.nameInput),
            el("label", {}, el("span", { text: globalThis.VTTUi("Raster") }), this.gridInput),
            el("label", {}, this.consent, el("span", { text: globalThis.VTTUi("Ich bestätige: Dieses Bild wird für alle am Tisch sichtbar. Das private Projekt wird nicht geteilt.") })),
            el("div", { className: "button-row" }, this.confirm, close), this.status);
        document.body.append(this.dialog);
        close.onclick = () => this.close();
        this.dialog.addEventListener("cancel", (event) => { if (this.busy) event.preventDefault(); });
        this.search.addEventListener("input", () => {
            clearTimeout(this.searchTimer);
            this.searchTimer = setTimeout(() => { this.page = 1; this.refresh(); }, 250);
        });
        this.prev.onclick = () => { this.page -= 1; this.refresh(); };
        this.next.onclick = () => { this.page += 1; this.refresh(); };
        this.consent.onchange = () => this.syncConfirm();
        this.nameInput.oninput = () => this.syncConfirm();
        this.confirm.onclick = () => this.submit();
    }

    open() {
        if (!this.dialog.open) this.dialog.showModal();
        this.refresh();
    }

    close() {
        if (this.busy) return;
        this.dropSelection();
        this.dialog.close();
    }

    setStatus(text, error = false) {
        this.status.textContent = text || "";
        this.status.classList.toggle("error", error);
    }

    async libraryRequest(path) {
        const call = async () => {
            const headers = window.Auth.buildHeaders("GET", false);
            // The private library is account-owned, never table-scoped.
            delete headers["X-VTT-Context"];
            delete headers["X-VTT-Tab"];
            return fetch(LIBRARY + path, { headers, credentials: "include", cache: "no-store" });
        };
        let response = await call();
        if (response.status === 401 && await window.Auth.refreshAccessToken?.()) response = await call();
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || globalThis.VTTUi("Die Kartenbibliothek ist momentan nicht erreichbar. Bitte erneut versuchen."));
        return data;
    }

    async refresh() {
        const sequence = ++this.listSequence;
        this.setStatus(globalThis.VTTUi("Bibliothek wird geladen …"));
        try {
            const query = new URLSearchParams({ page: String(this.page), q: this.search.value });
            const data = await this.libraryRequest(`?${query}`);
            if (sequence !== this.listSequence) return;
            this.list.replaceChildren();
            for (const project of data.projects) {
                const choose = el("button", { type: "button", className: "mini-btn secondary", text: project.title });
                choose.dataset.projectId = project.id;
                choose.setAttribute("aria-label", globalThis.VTTUi("Vorschau von „{p0}“", { p0: project.title }));
                choose.onclick = () => this.select(project);
                this.list.append(el("li", {}, choose, el("span", { className: "muted", text: ` ${project.width} × ${project.height}` })));
            }
            this.prev.disabled = data.page <= 1;
            this.next.disabled = data.page * data.pageSize >= data.total;
            this.pageLabel.textContent = globalThis.VTTUi("Seite {p0} von {p1}", { p0: data.page, p1: Math.max(1, Math.ceil(data.total / data.pageSize)) });
            this.setStatus(data.total ? "" : globalThis.VTTUi("Keine eigenen Karten gefunden."));
        } catch (error) {
            if (sequence === this.listSequence) this.setStatus(error.message, true);
        }
    }

    dropSelection() {
        this.selectSequence += 1;
        this.selection = null;
        this.pending = null;
        if (this.previewUrl) URL.revokeObjectURL(this.previewUrl);
        this.previewUrl = null;
        this.preview.hidden = true;
        this.preview.removeAttribute("src");
        this.previewInfo.textContent = "";
        for (const input of [this.nameInput, this.gridInput, this.consent]) input.disabled = true;
        this.consent.checked = false;
        this.syncConfirm();
    }

    async select(project) {
        if (this.busy) return;
        this.dropSelection();
        const sequence = this.selectSequence;
        const isCurrent = () => sequence === this.selectSequence;
        this.setStatus(globalThis.VTTUi("Vorschau wird erzeugt …"));
        try {
            const data = await this.libraryRequest(`/${project.id}`);
            if (!isCurrent()) return;
            this.palette ||= await loadSnapshotPalette(loadPalette);
            if (!isCurrent()) return;
            const selection = await snapshotFromProject({ project: data.project, document: data.document, palette: this.palette, isCurrent });
            if (!isCurrent()) return;
            this.selection = selection;
            this.previewUrl = URL.createObjectURL(selection.blob);
            this.preview.src = this.previewUrl;
            this.preview.alt = globalThis.VTTUi("Vorschau von „{p0}“", { p0: selection.title });
            this.preview.hidden = false;
            this.previewInfo.textContent = `${selection.width} × ${selection.height} · ${globalThis.VTTUi("Revision {p0}", { p0: selection.revision })}`;
            this.nameInput.value = selection.title.slice(0, 120);
            for (const input of [this.nameInput, this.gridInput, this.consent]) input.disabled = false;
            this.setStatus("");
        } catch (error) {
            // A superseded answer must neither show a preview nor an error for the new choice.
            if (isCurrent()) { this.dropSelection(); this.setStatus(error.message, true); }
        }
        this.syncConfirm();
    }

    syncConfirm() {
        const grid = Number(this.gridInput.value);
        this.confirm.disabled = this.busy || !this.selection || !this.consent.checked
            || !this.nameInput.value.trim() || !(grid >= 16 && grid <= 300);
    }

    async uploadSnapshot() {
        const selection = this.selection, pending = this.pending;
        const form = new FormData();
        form.append("project_id", selection.projectId);
        form.append("revision", String(selection.revision));
        form.append("request_id", pending.requestId);
        form.append("grid_size", String(pending.gridSize));
        form.append("name", pending.name);
        form.append("credits", selection.credits);
        form.append("file", selection.blob, "snapshot.png");
        const response = await fetch(`/api/play/campaigns/${this.ui.campaignId}/sessions/${this.ui.sessionId}/map-library-snapshots`, {
            method: "POST", credentials: "include", headers: window.Auth.buildHeaders("POST", false), body: form });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
            if (response.status === 409 && body.error === "revision_conflict") this.pending = null;
            throw new Error(body.message || body.error || globalThis.VTTUi("Die Karte konnte nicht übernommen werden."));
        }
        return body.map_id;
    }

    /** Two explicit stages. Stage 2 may be retried without a second upload. */
    async submit() {
        if (this.busy || !this.selection || this.confirm.disabled) return;
        const ui = this.ui;
        // Freeze what the user confirmed; later edits to the inputs cannot change a started attempt.
        this.pending ||= { requestId: requestId(), name: this.nameInput.value.trim().slice(0, 120),
            gridSize: Math.round(Number(this.gridInput.value)), mapId: null, layerId: null };
        const pending = this.pending;
        this.busy = true;
        this.confirm.disabled = true;
        try {
            if (!pending.mapId) {
                this.setStatus(globalThis.VTTUi("Karte wird übernommen …"));
                pending.mapId = await this.uploadSnapshot();
            }
            this.setStatus(globalThis.VTTUi("Füge Seite hinzu..."));
            const stack = ui.bootstrap?.scene_stack;
            if (stack && Array.isArray(stack.layers)) {
                if (!pending.layerId) {
                    const added = await ui.api.addLayer(ui.campaignId, ui.sessionId, pending.mapId, pending.name);
                    pending.layerId = added?.layer?.id
                        || (added?.scene_stack?.layers || []).find((l) => Number(l.campaign_map_id) === Number(pending.mapId))?.id;
                }
                if (!pending.layerId) throw new Error(globalThis.VTTUi("Seite konnte nicht hinzugefügt werden."));
                await ui.api.activateLayer(ui.campaignId, ui.sessionId, pending.layerId);
            } else {
                await ui.api.initSceneStack(ui.campaignId, ui.sessionId, [pending.mapId]);
            }
            const title = pending.name;
            this.busy = false;
            this.dropSelection();
            this.dialog.close();
            ui._showMessage(globalThis.VTTUi("Karte \"{p0}\" übernommen und aktiviert.", { p0: title }));
            await ui.loadBootstrap();
        } catch (error) {
            this.busy = false;
            // Keep createdMapId: the retry button only repeats the table stage.
            const created = this.pending?.mapId;
            this.confirm.textContent = globalThis.VTTUi("Zum Tisch hinzufügen");
            this.setStatus(created
                ? globalThis.VTTUi("Die Karte wurde angelegt, aber noch nicht aktiviert. „Zum Tisch hinzufügen“ wiederholt nur diesen Schritt.")
                : error.message, true);
            if (created) this.status.dataset.createdMapId = String(created);
            this.syncConfirm();
        }
    }
}

export function mount(ui) {
    ui._mapLibrary ||= new MapLibraryController(ui);
    return ui._mapLibrary;
}
