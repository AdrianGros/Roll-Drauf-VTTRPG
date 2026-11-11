globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Personal project library. JWT/CSRF and ownership are enforced by the server.
import { LIMITS, materialize, serialize, validateDocument } from "./document.js";
import { DraftStore } from "./storage.js";

const $ = (id) => document.getElementById(id);
const API = "/api/assets/mapmaker/projects";

function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
}

export function formatBytes(bytes) {
    const units = ["B", "KiB", "MiB", "GiB"];
    let value = bytes || 0, index = 0;
    while (value >= 1024 && index < units.length - 1) { value /= 1024; index += 1; }
    return `${new Intl.NumberFormat("de-DE", { maximumFractionDigits: index ? 2 : 0 }).format(value)} ${units[index]}`;
}

export class Library {
    constructor(editor) {
        this.ed = editor;
        this.accountId = null;
        this.project = null;
        this.savedGeneration = -1;
        this.busy = false;
        this.page = 1;
        this.listSequence = 0;
        this.authPresent = false;
    }

    bind() {
        $("libraryBtn").onclick = () => this.show();
        $("cloudSave").onclick = () => this.save();
        $("libraryMenuBtn").onclick = () => this.show();
        $("cloudSaveMenu").onclick = () => this.save();
        $("saveCopyBtn").onclick = () => this.save(true);
        $("newLibrary").onclick = () => {
            $("librarySection").hidden = false;
            $("librarySearch").focus();
        };
        $("libraryImport").onclick = () => $("fileInput").click();
        $("libraryRefresh").onclick = () => this.refresh();
        $("librarySearch").addEventListener("input", () => {
            clearTimeout(this.searchTimer);
            this.searchTimer = setTimeout(() => { this.page = 1; this.refresh(); }, 250);
        });
        $("libraryPrev").onclick = () => { this.page -= 1; this.refresh(); };
        $("libraryNext").onclick = () => { this.page += 1; this.refresh(); };
        $("newDialog").addEventListener("cancel", (event) => {
            if (!this.ed.mapOpened) event.preventDefault();
        });
    }

    async initialize() {
        this.bind();
        this.authPresent = !!window.Auth?.getCookie("csrf_access_token");
        if (this.authPresent) await this.refresh();
        else this.message("Melde dich an, um Karten in deiner persönlichen Bibliothek zu speichern. Dateiimport und lokales Arbeiten sind auch ohne Anmeldung möglich.");
        this.ed.drafts = this.accountId !== null ? new DraftStore(`user:${this.accountId}`)
            : this.authPresent ? null : new DraftStore();
        this.updateStatus();
    }

    async request(path = "", method = "GET", body, retry = true) {
        const headers = window.Auth ? window.Auth.buildHeaders(method, body !== undefined) : {};
        if (this.accountId !== null) headers["X-Mapmaker-Account"] = String(this.accountId);
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), method === "GET" ? 10000 : 60000);
        let response;
        try {
            response = await fetch(API + path, { method, headers, credentials: "include",
                body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal });
        } catch (_error) {
            throw new Error(globalThis.VTTUi("Keine Verbindung zur Kartenbibliothek. Deine Karte bleibt geöffnet. Bitte erneut versuchen oder als Datei sichern."));
        } finally { clearTimeout(timer); }
        if (response.status === 401 && retry && window.Auth?.getCookie("csrf_refresh_token")) {
            if (await window.Auth.refreshAccessToken()) return this.request(path, method, body, false);
        }
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const error = new Error(data.error || (response.status === 401
                ? globalThis.VTTUi("Bitte erneut anmelden, um deine Kartenbibliothek zu öffnen.")
                : globalThis.VTTUi("Die Kartenbibliothek ist momentan nicht erreichbar. Bitte erneut versuchen.")));
            error.code = data.code;
            error.status = response.status;
            throw error;
        }
        return data;
    }

    message(text, error = false) {
        $("libraryFeedback").textContent = text;
        $("libraryFeedback").classList.toggle("mm-error", error);
    }

    show() {
        if (!this.ed.doc) return;
        $("newCancel").hidden = !this.ed.mapOpened;
        if (!$("newDialog").open) $("newDialog").showModal();
        this.refresh();
    }

    close() { $("newDialog").close(); }

    storage(data) {
        this.storageInfo = data;
        const cap = data.unlimited ? "unbegrenzt" : formatBytes(data.quotaBytes);
        $("libraryQuota").textContent = globalThis.VTTUi("{p0} von {p1} belegt · Karten: {p2}. Gemeinsamer Speicher mit deinen Uploads.",{p0:(formatBytes(data.usedBytes)),p1:(cap),p2:(formatBytes(data.libraryBytes))});
        $("libraryMeter").hidden = data.unlimited || !data.quotaBytes;
        $("libraryMeter").max = data.quotaBytes || 1;
        $("libraryMeter").value = Math.min(data.usedBytes, data.quotaBytes || 1);
    }

    async refresh() {
        if (!window.Auth?.getCookie("csrf_access_token") && this.accountId === null) {
            this.updateStatus();
            return;
        }
        const sequence = ++this.listSequence;
        this.message("Bibliothek wird geladen …");
        try {
            const query = new URLSearchParams({ page: String(this.page), q: $("librarySearch").value });
            const data = await this.request(`?${query}`);
            if (sequence !== this.listSequence) return;
            if (this.accountId === null) {
                this.accountId = data.storage.accountId;
                this.ed.drafts = new DraftStore(`user:${this.accountId}`);
            }
            this.storage(data.storage);
            this.render(data);
            this.message(data.total ? `${data.total} Karte${data.total === 1 ? "" : "n"} in deiner Bibliothek.`
                : $("librarySearch").value ? "Keine Karten zu dieser Suche gefunden." : "Deine Bibliothek ist noch leer. Starte mit einer leeren Karte oder einem Template.");
        } catch (error) {
            if (sequence === this.listSequence) this.message(error.message, true);
        }
        this.updateStatus();
    }

    render(data) {
        const list = $("libraryList");
        list.replaceChildren();
        for (const project of data.projects) {
            const row = node("li", undefined, "mm-library-card");
            const content = node("div");
            content.appendChild(node("strong", project.title));
            const date = new Date(project.updatedAt).toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" });
            content.appendChild(node("p", `${project.width} × ${project.height} · ${formatBytes(project.sizeBytes)} · ${date}`, "mm-hint"));
            const actions = node("div", undefined, "mm-library-actions");
            const open = node("button", "Öffnen", "mm-btn mm-btn-primary");
            open.type = "button";
            open.onclick = () => this.open(project);
            open.setAttribute("aria-label", `Karte „${project.title}“ öffnen`);
            const remove = node("button", "Löschen", "mm-btn mm-btn-small");
            remove.type = "button";
            remove.onclick = () => this.remove(project);
            remove.setAttribute("aria-label", `Karte „${project.title}“ löschen`);
            row.dataset.projectId = project.id;
            actions.append(open, remove);
            row.append(content, actions);
            list.appendChild(row);
        }
        $("libraryPrev").disabled = data.page <= 1;
        $("libraryNext").disabled = data.page * data.pageSize >= data.total;
        $("libraryPage").textContent = globalThis.VTTUi("Seite {p0} von {p1}",{p0:(data.page),p1:(Math.max(1, Math.ceil(data.total / data.pageSize)))});
    }

    updateStatus() {
        const enabled = this.accountId !== null && !this.busy && !!this.ed.mapOpened;
        $("cloudSave").disabled = !enabled;
        $("cloudSaveMenu").disabled = !enabled;
        $("saveCopyBtn").disabled = !enabled;
        const label = this.busy ? "Bibliothek speichert …" : this.accountId === null ? "Bibliothek: Anmeldung nötig"
            : this.project && this.savedGeneration === this.ed.generation ? "In Bibliothek gespeichert"
                : this.project ? "Bibliothek: Änderungen offen" : "Noch nicht in Bibliothek";
        $("cloudStatus").textContent = label;
        $("cloudSave").title = label + globalThis.VTTUi(" (Strg+S)");
    }

    detach() {
        this.project = null;
        this.savedGeneration = -1;
        this.updateStatus();
    }

    async save(asCopy = false) {
        if (this.busy || this.accountId === null || !this.ed.mapOpened) return false;
        const ed = this.ed;
        ed.commitEdit();
        if (ed.isMutating()) { ed.ui.toast(globalThis.VTTUi("Bitte die laufende Zeichenbewegung zuerst beenden.")); return false; }
        const doc = ed.doc, generation = ed.generation;
        const project = asCopy ? null : this.project;
        this.busy = true;
        this.updateStatus();
        try {
            const document = await serialize(doc, "file");
            if (new Blob([JSON.stringify(document)]).size > LIMITS.fileBytes) throw new Error(globalThis.VTTUi("Das Projekt ist größer als 50 MiB. Bitte als Datei sichern."));
            const result = await this.request(project ? `/${project.id}` : "", project ? "PUT" : "POST",
                { document, ...(project ? { revision: project.revision } : {}) });
            this.storage(result.storage);
            // Do not attach a response from an old document to a newly opened map.
            if (ed.doc === doc) {
                this.project = result.project;
                this.savedGeneration = generation;
                ed.scheduleAutosave(); // persist project identity with the account's local draft
            }
            ed.ui.toast(ed.doc === doc && ed.generation === generation
                ? globalThis.VTTUi("Karte in deiner Bibliothek gespeichert.") : globalThis.VTTUi("Kartenstand gespeichert; neuere Änderungen sind noch offen."));
            return true;
        } catch (error) {
            this.message(error.message, true);
            ed.ui.showError(error.message);
            return false;
        } finally {
            this.busy = false;
            this.updateStatus();
        }
    }

    async open(project) {
        if (this.busy) return;
        this.close();
        if (!(await this.ed.ui.confirmReplace())) return;
        const previous = this.ed.doc, generation = this.ed.generation;
        this.busy = true;
        this.updateStatus();
        try {
            const result = await this.request(`/${project.id}`);
            const validated = validateDocument(result.document, { knownAssets: this.ed.palette.stamps });
            await this.ed.palette.ensureDocumentImages(validated);
            const doc = await materialize(validated);
            if (this.ed.doc !== previous || this.ed.generation !== generation) {
                throw new Error(globalThis.VTTUi("Die geöffnete Karte wurde während des Ladens verändert. Bitte die Bibliothekskarte erneut öffnen."));
            }
            this.ed.loadDocument(doc);
            this.ed.fileGeneration = -1;
            this.project = result.project;
            this.savedGeneration = this.ed.generation;
            this.ed.mapOpened = true;
            this.ed.scheduleAutosave();
            this.ed.ui.toast(globalThis.VTTUi("„{p0}“ aus deiner Bibliothek geöffnet.",{p0:(result.project.title)}));
        } catch (error) {
            if (!this.ed.mapOpened) this.show();
            this.ed.ui.showError(error.message);
        } finally {
            this.busy = false;
            this.updateStatus();
        }
    }

    async remove(project) {
        if (this.busy) return;
        const dialog = $("deleteMapDialog");
        $("deleteMapText").textContent = globalThis.VTTUi("„{p0}“ dauerhaft aus deiner Bibliothek löschen? Eine aktuell geöffnete Karte bleibt im Editor und kann als Kopie gespeichert werden.",{p0:(project.title)});
        const confirmed = await new Promise((resolve) => {
            const finish = (value) => { dialog.close(); resolve(value); };
            $("deleteMapCancel").onclick = () => finish(false);
            $("deleteMapConfirm").onclick = () => finish(true);
            dialog.oncancel = (event) => { event.preventDefault(); finish(false); };
            dialog.showModal();
            $("deleteMapCancel").focus();
        });
        if (!confirmed) return;
        this.busy = true;
        this.updateStatus();
        try {
            const result = await this.request(`/${project.id}`, "DELETE", { revision: project.revision });
            this.storage(result.storage);
            if (this.project?.id === project.id) { this.detach(); this.ed.scheduleAutosave(); }
            await this.refresh();
        } catch (error) {
            this.message(error.message, true);
        } finally { this.busy = false; this.updateStatus(); }
    }
}
