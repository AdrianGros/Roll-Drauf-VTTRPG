globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
// Shared, pure PNG snapshot pipeline. The editor export and the DM table's library
// preview both go through here; no Editor instance, DOM or input handler is needed.
import { materialize, validateDocument } from "./document.js";
import { Renderer } from "./render.js";
import { registerMaterialTextures } from "./brush.js";
import { creditsForDocument, embedCredits } from "./credits.js";

export const MAX_SNAPSHOT_PIXELS = 64 * 1024 * 1024;
const ASSET_BASE = new URL("../", import.meta.url).pathname; // /static/mapmaker/

/**
 * stamps.js resolves "assets/..." relative to the *page*. In the editor that is
 * /static/mapmaker/; on the play table it is not. When this helper runs outside the
 * editor page, narrowly rewrite exactly the relative "assets/" prefix (fetch + Image.src)
 * to the module-relative location. Editor pages are untouched.
 */
export function ensureAssetBase() {
    if (new URL("assets/", document.baseURI).pathname === ASSET_BASE + "assets/" || ensureAssetBase.installed) return;
    ensureAssetBase.installed = true;
    const rewrite = (value) => (typeof value === "string" && value.startsWith("assets/") ? ASSET_BASE + value : value);
    const nativeFetch = globalThis.fetch.bind(globalThis);
    globalThis.fetch = (input, init) => nativeFetch(rewrite(input), init);
    const descriptor = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, "src");
    Object.defineProperty(HTMLImageElement.prototype, "src", {
        ...descriptor, set(value) { descriptor.set.call(this, rewrite(value)); },
    });
}

/**
 * Palette loader that is safe on any page: same catalog and material textures the
 * editor registers. An incomplete pack catalog aborts visibly instead of rendering a
 * wrong preview. (Web fonts come from the page; the editor stylesheet is not loaded
 * on the table, so label glyphs may use fallback fonts there.)
 */
export async function loadSnapshotPalette(loadPalette) {
    ensureAssetBase();
    const palette = await loadPalette(() => {}, () => {});
    if (palette.packError) throw new Error(globalThis.VTTUi("Symbolpakete konnten nicht vollständig geladen werden. Bitte erneut versuchen."));
    registerMaterialTextures(palette.materialTextures);
    return palette;
}
const CREDIT_SUMMARY_LIMIT = 600;

/** Short, readable credit text for the table map description (the PNG keeps the full text). */
export function creditSummary(credits) {
    return String(credits).split("\n\n").slice(3).join(" · ").replace(/\s+/g, " ").trim().slice(0, CREDIT_SUMMARY_LIMIT);
}

/**
 * Render an already materialized document to a credits-embedded PNG blob.
 * `isStale` is checked after asynchronous image loading so a changed document
 * is rejected instead of silently exported.
 */
export async function renderPngBlob({ doc, palette, renderer, scale = 1, maxPixels = MAX_SNAPSHOT_PIXELS,
    isStale = () => false, beforeRender = () => {}, staleMessage }) {
    if (doc.size.w * scale * doc.size.h * scale > maxPixels) {
        throw new Error(globalThis.VTTUi("Diese Auflösung ist zu groß für den Browser."));
    }
    const credits = creditsForDocument(doc, palette);
    await palette.ensureDocumentImages(doc);
    if (isStale()) throw new Error(staleMessage || globalThis.VTTUi("Die Karte wurde während des Exports geändert. Bitte erneut exportieren."));
    beforeRender();
    const canvas = renderer.renderExport(scale);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
    canvas.width = 0;
    canvas.height = 0;
    if (!blob) throw new Error(globalThis.VTTUi("Der Browser konnte das Bild nicht erzeugen (zu groß?)."));
    return { blob: await embedCredits(blob, credits), credits };
}

/**
 * Validate + materialize a stored project document and render it at 1:1.
 * Returns an immutable selection bound to project id and saved revision.
 */
export async function snapshotFromProject({ project, document, palette, isCurrent = () => true }) {
    const validated = validateDocument(document, { knownAssets: palette.stamps });
    await palette.ensureDocumentImages(validated);
    const doc = await materialize(validated);
    if (!isCurrent()) throw new Error(globalThis.VTTUi("Die Auswahl hat sich geändert. Bitte die Vorschau erneut öffnen."));
    const renderer = new Renderer(palette);
    renderer.setDocument(doc);
    const { blob, credits } = await renderPngBlob({
        doc, palette, renderer, scale: 1, isStale: () => !isCurrent(),
        staleMessage: globalThis.VTTUi("Die Auswahl hat sich geändert. Bitte die Vorschau erneut öffnen."),
    });
    return Object.freeze({
        projectId: project.id, revision: project.revision, title: doc.meta.title,
        width: doc.size.w, height: doc.size.h, blob, credits: creditSummary(credits),
    });
}
