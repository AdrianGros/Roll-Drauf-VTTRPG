// Pure, bounded and versioned. This module never reads the clock or a document.
export const LANDMASS_VERSION = 'landmass-v1';
const integer = (n, low, high) => Number.isInteger(n) && n >= low && n <= high;

export function normalizeLandmass(input, size) {
    const {seed, form, land, roughness, resolution} = input;
    if (!integer(seed, 0, 0xffffffff) || !['island', 'continent'].includes(form)
        || !integer(land, 10, 80) || !integer(roughness, 0, 100)
        || ![128, 256, 512].includes(resolution)
        || !integer(size?.w, 256, 4096) || !integer(size?.h, 256, 4096)) throw new Error('parameters');
    const scale = resolution / Math.max(size.w, size.h);
    const w = Math.max(8, Math.round(size.w * scale)), h = Math.max(8, Math.round(size.h * scale));
    const margin = form === 'island' ? Math.max(1, Math.floor(Math.min(w, h) * .03)) : 0;
    const target = Math.round(w * h * land / 100);
    if (target > (w - margin * 2) * (h - margin * 2)) throw new Error('island-border');
    return {version: LANDMASS_VERSION, seed, form, land, roughness, resolution, w, h, margin, target};
}

function noise(seed) {
    let t = seed >>> 0;
    const values = new Float64Array(65536);
    for (let i = 0; i < values.length; i++) {
        t += 0x6d2b79f5;
        let r = Math.imul(t ^ (t >>> 15), 1 | t);
        r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
        values[i] = ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    }
    const at = (x, y) => values[((y & 255) << 8) | (x & 255)];
    return (x, y) => {
        let sum = 0, amp = .5, freq = 1, norm = 0;
        for (let octave = 0; octave < 5; octave++) {
            const px = x * freq, py = y * freq, ix = Math.floor(px), iy = Math.floor(py);
            const tx = px - ix, ty = py - iy, sx = tx * tx * (3 - 2 * tx), sy = ty * ty * (3 - 2 * ty);
            const a = at(ix, iy) * (1 - sx) + at(ix + 1, iy) * sx;
            const b = at(ix, iy + 1) * (1 - sx) + at(ix + 1, iy + 1) * sx;
            sum += (a * (1 - sy) + b * sy) * amp; norm += amp;
            amp *= .5; freq *= 2.03;
        }
        return sum / norm;
    };
}

export function generateLandmass(input, size) {
    const parameters = normalizeLandmass(input, size);
    const {w, h, margin, target, form, roughness, seed} = parameters;
    const n = w * h, heights = new Float64Array(n), queued = new Uint8Array(n), mask = new Uint8Array(n);
    const sample = noise(seed), weight = roughness / 100;
    for (let y = margin; y < h - margin; y++) for (let x = margin; x < w - margin; x++) {
        const nx = (x + .5) / w * 2 - 1, ny = (y + .5) / h * 2 - 1;
        const falloff = (nx * nx + ny * ny) * (form === 'island' ? .65 : .25);
        heights[y * w + x] = sample(x / w * 5, y / h * 5) * (.25 + weight * .75) - falloff;
    }
    // Max heap, stable cell-index tie break. Enqueue once; every accepted cell
    // touches the existing four-connected mask, including at maximum roughness.
    const heap = [];
    const above = (a, b) => heights[a] > heights[b] || heights[a] === heights[b] && a < b;
    function push(cell) {
        if (queued[cell]) return;
        queued[cell] = 1; let i = heap.length; heap.push(cell);
        while (i) { const p = (i - 1) >> 1; if (!above(cell, heap[p])) break; heap[i] = heap[p]; i = p; }
        heap[i] = cell;
    }
    function pop() {
        const top = heap[0], last = heap.pop();
        if (heap.length) {
            let i = 0;
            while (i * 2 + 1 < heap.length) {
                let child = i * 2 + 1;
                if (child + 1 < heap.length && above(heap[child + 1], heap[child])) child++;
                if (!above(heap[child], last)) break;
                heap[i] = heap[child]; i = child;
            }
            heap[i] = last;
        }
        return top;
    }
    push(Math.floor(h / 2) * w + Math.floor(w / 2));
    for (let count = 0; count < target; count++) {
        const cell = pop(), x = cell % w, y = Math.floor(cell / w); mask[cell] = 1;
        if (x > margin) push(cell - 1);
        if (x < w - margin - 1) push(cell + 1);
        if (y > margin) push(cell - w);
        if (y < h - margin - 1) push(cell + w);
    }
    return {parameters, mask};
}
