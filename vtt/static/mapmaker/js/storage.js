// Browser-local autosave (IndexedDB) and file download helpers.

const DB_NAME = "rd-mapmaker";
const STORE = "drafts";
const KEY = "autosave";

export class AutosaveUnavailable extends Error {}

function requestToPromise(request) {
    return new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error || new Error("IndexedDB-Fehler"));
    });
}

export class DraftStore {
    constructor(scope = "guest") {
        this.dbPromise = null;
        this.key = scope === "guest" ? KEY : `${KEY}:${scope}`;
    }

    open() {
        if (this.dbPromise) return this.dbPromise;
        this.dbPromise = new Promise((resolve, reject) => {
            let request;
            try {
                if (typeof indexedDB === "undefined" || !indexedDB) throw new Error("IndexedDB fehlt");
                request = indexedDB.open(DB_NAME, 1);
            } catch (error) {
                reject(new AutosaveUnavailable(String(error.message || error)));
                return;
            }
            request.onupgradeneeded = () => request.result.createObjectStore(STORE);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(new AutosaveUnavailable(String(request.error || "IndexedDB blockiert")));
            request.onblocked = () => reject(new AutosaveUnavailable("IndexedDB blockiert"));
        });
        return this.dbPromise;
    }

    async load() {
        const db = await this.open();
        const tx = db.transaction(STORE, "readonly");
        return requestToPromise(tx.objectStore(STORE).get(this.key));
    }

    async save(record) {
        const db = await this.open();
        await new Promise((resolve, reject) => {
            let tx;
            try {
                tx = db.transaction(STORE, "readwrite");
                tx.objectStore(STORE).put(record, this.key);
            } catch (error) {
                reject(error);
                return;
            }
            tx.oncomplete = () => resolve();
            tx.onabort = () => reject(tx.error || new Error("Speichern abgebrochen"));
            tx.onerror = () => reject(tx.error || new Error("Speichern fehlgeschlagen"));
        });
    }
}

/** Trigger a download via an <a download>; blob URLs are only used for navigation, never as image sources. */
export function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.rel = "noopener";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
}

export function slugify(title) {
    const slug = String(title || "karte")
        .toLowerCase()
        .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss")
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")
        .slice(0, 60);
    return slug || "karte";
}
