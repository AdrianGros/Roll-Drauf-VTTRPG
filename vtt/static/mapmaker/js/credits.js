globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Credits accompany the composed image. Text comes only from reviewed local manifests.
export function creditsForDocument(doc, palette) {
    const used = new Set();
    for (const layer of doc.layers) {
        for (const item of layer.items || []) {
            for (const id of [item.asset, item.symbol && item.symbol.asset].filter(Boolean)) {
                const stamp = palette.stamps.get(id);
                if (stamp) used.add(stamp.pack);
            }
        }
        // Tile layers: runtime cells (Map) or the serialized palette of a saved project.
        for (const id of layer.cells instanceof Map ? new Set(layer.cells.values()) : layer.palette || []) {
            const stamp = palette.stamps.get(id);
            if (stamp) used.add(stamp.pack);
        }
    }
    // Raster pixels retain no asset provenance after painting/import. Keep the
    // reviewed source collection, including image brush sources, across saves
    // and rollbacks rather than guess which artist supplied a pixel.
    const raster = doc.layers.some((layer) => layer.kind === "raster");
    for (const pack of palette.packs) if (raster || pack.id === "polyhaven-terrain") used.add(pack.id);
    return [
        `Künstler-Credits – ${doc.meta.title}`,
        "Bearbeitung: Ausschnitte, Skalierung, Spiegelung und Komposition in der Roll-Drauf-Kartenwerkstatt. Die Originalkünstler unterstützen dieses Projekt nicht automatisch.",
        "Bei Veröffentlichung diese Angaben auch in einem Begleittext oder einer Credits-Seite nennen; Bilddienste können eingebettete Metadaten entfernen.",
        ...(raster ? ["Rasterquellensammlung: Alle freigegebenen lokalen Katalogquellen sind aufgeführt. Dies bedeutet nicht, dass jedes Paket in dieser Karte sichtbar verwendet wurde."] : []),
        ...palette.packs.filter((pack) => used.has(pack.id) && pack.credit).map((pack) => pack.credit),
    ].join("\n\n");
}

function crc32(bytes) {
    let crc = 0xffffffff;
    for (const byte of bytes) {
        crc ^= byte;
        for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
    }
    return (crc ^ 0xffffffff) >>> 0;
}

export async function embedCredits(blob, credits) {
    const png = new Uint8Array(await blob.arrayBuffer());
    // Insert an uncompressed UTF-8 iTXt chunk immediately before IEND.
    const encoder = new TextEncoder();
    const payload = encoder.encode(`Credits\0\0\0\0\0${credits}`);
    const chunk = new Uint8Array(12 + payload.length);
    const view = new DataView(chunk.buffer);
    view.setUint32(0, payload.length);
    chunk.set(encoder.encode("iTXt"), 4);
    chunk.set(payload, 8);
    view.setUint32(chunk.length - 4, crc32(chunk.subarray(4, chunk.length - 4)));
    if (png.length < 20 || String.fromCharCode(...png.subarray(-8, -4)) !== "IEND") throw new Error(globalThis.VTTUi("PNG-Abschluss fehlt."));
    return new Blob([png.subarray(0, -12), chunk, png.subarray(-12)], { type: "image/png" });
}
