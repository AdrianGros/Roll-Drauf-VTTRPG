globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Small STORE-only ZIP writer for a PNG and its editable project file.
// No compression is useful for PNG, and this keeps the download offline-ready.

const encoder = new TextEncoder();
const table = new Uint32Array(256);
for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
}

function crc32(bytes) {
    let crc = 0xffffffff;
    for (const byte of bytes) crc = table[(crc ^ byte) & 0xff] ^ (crc >>> 8);
    return (crc ^ 0xffffffff) >>> 0;
}

export async function zipFiles(files) {
    const locals = [];
    const centers = [];
    let offset = 0;
    for (const [name, data] of files) {
        const filename = encoder.encode(name);
        const bytes = data instanceof Blob ? new Uint8Array(await data.arrayBuffer())
            : data instanceof Uint8Array ? data : encoder.encode(String(data));
        if (filename.length > 65535 || bytes.length > 0xffffffff) throw new Error(globalThis.VTTUi("Datei ist zu groß für ZIP."));
        const crc = crc32(bytes);
        const local = new Uint8Array(30 + filename.length);
        const l = new DataView(local.buffer);
        l.setUint32(0, 0x04034b50, true);
        l.setUint16(4, 20, true);
        l.setUint32(14, crc, true);
        l.setUint32(18, bytes.length, true);
        l.setUint32(22, bytes.length, true);
        l.setUint16(26, filename.length, true);
        local.set(filename, 30);
        locals.push(local, bytes);

        const center = new Uint8Array(46 + filename.length);
        const c = new DataView(center.buffer);
        c.setUint32(0, 0x02014b50, true);
        c.setUint16(4, 20, true);
        c.setUint16(6, 20, true);
        c.setUint32(16, crc, true);
        c.setUint32(20, bytes.length, true);
        c.setUint32(24, bytes.length, true);
        c.setUint16(28, filename.length, true);
        c.setUint32(42, offset, true);
        center.set(filename, 46);
        centers.push(center);
        offset += local.length + bytes.length;
    }
    const directorySize = centers.reduce((sum, part) => sum + part.length, 0);
    if (offset + directorySize > 0xffffffff) throw new Error(globalThis.VTTUi("Paket ist zu groß für ZIP."));
    const end = new Uint8Array(22);
    const e = new DataView(end.buffer);
    e.setUint32(0, 0x06054b50, true);
    e.setUint16(8, centers.length, true);
    e.setUint16(10, centers.length, true);
    e.setUint32(12, directorySize, true);
    e.setUint32(16, offset, true);
    return new Blob([...locals, ...centers, end], { type: "application/zip" });
}
