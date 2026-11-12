globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
// Shared, pure PNG snapshot pipeline. The editor export and the DM table's library
// preview both go through here; no Editor instance, DOM or input handler is needed.
import { materialize, validateDocument } from "./document.js";
import { Renderer } from "./render.js";
import { registerMaterialTextures } from "./brush.js";
import { creditsForDocument, embedCredits } from "./credits.js";
import { loadPalette } from "./stamps.js";

export const MAX_SNAPSHOT_PIXELS = 64 * 1024 * 1024;

// The editor's five existing local faces (see mapmaker.css). The table page does not
// load the editor stylesheet, so the snapshot helper loads exactly these faces itself.
const FONT_FACES = [
    ["Literata", "literata-var.woff2", { weight: "200 900", style: "normal" }],
    ["Literata", "literata-italic-var.woff2", { weight: "200 900", style: "italic" }],
    ["Cinzel", "cinzel-regular.woff2", { weight: "400", style: "normal" }],
    ["Cinzel", "cinzel-bold.woff2", { weight: "700", style: "normal" }],
    ["BadScript", "badscript-regular.woff2", { weight: "400", style: "normal" }],
];

/** Await all five faces before any label is drawn; reuse faces the page already declares. */
export async function loadSnapshotFonts() {
    const declared = [...document.fonts];
    try {
        await Promise.all(FONT_FACES.map(([family, file, descriptor]) => {
            let face = declared.find((entry) => entry.family.replace(/["']/g, "") === family
                && entry.style === descriptor.style && entry.weight === descriptor.weight);
            if (!face) {
                face = new FontFace(family, `url("${new URL(`../../fonts/${file}`, import.meta.url).href}")`, descriptor);
                document.fonts.add(face);
            }
            return face.load();
        }));
    } catch (_error) {
        throw new Error(globalThis.VTTUi("Schriften für die Vorschau konnten nicht geladen werden. Bitte erneut versuchen."));
    }
}

/**
 * Palette loader that is safe on any page: same catalog and material textures the
 * editor registers (own asset URLs are module-relative inside stamps.js).
 */
export async function loadSnapshotPalette() {
    const palette = await loadPalette(() => {}, () => {});
    if (!palette.packLoaded) throw new Error(globalThis.VTTUi("Symbolpakete konnten nicht vollständig geladen werden. Bitte erneut versuchen."));
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
    await loadSnapshotFonts();
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
