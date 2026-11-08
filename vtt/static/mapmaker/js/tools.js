// Pointer, wheel and keyboard input. One gesture at a time; a second touch
// cancels the running gesture (reverting a partial stroke) and starts a pinch.

const TEXT_INPUT_TYPES = new Set(["text", "search", "number", "email", "url", "password", "tel", "color"]);

function isTextEntry(target) {
    if (!target || !target.closest) return false;
    if (target.closest("textarea, select, [contenteditable='true']")) return true;
    const input = target.closest("input");
    return !!input && TEXT_INPUT_TYPES.has((input.type || "text").toLowerCase());
}

function isControl(target) {
    return !!(target && target.closest && target.closest("input, textarea, select, button, a, [contenteditable='true']"));
}

export function attachInput(ed) {
    const canvas = ed.canvas;
    const pointers = new Map();
    let gesture = null;
    let spaceDown = false;

    const local = (event) => {
        const rect = canvas.getBoundingClientRect();
        return { x: event.clientX - rect.left, y: event.clientY - rect.top };
    };
    const pressureOf = (event) => (event.pointerType === "pen" ? event.pressure : null);

    function updateCursorClass() {
        const panning = spaceDown || ed.tool === "pan" || (gesture && gesture.type === "pan");
        canvas.dataset.cursor = panning ? (gesture && gesture.type === "pan" ? "grabbing" : "grab") : ed.tool;
    }

    function cancelGesture() {
        if (!gesture) return;
        if (gesture.type === "stroke") ed.cancelStroke();
        if (gesture.type === "drag" && gesture.moved) {
            ed.invalidateItem(gesture.item);
            gesture.item.x = gesture.orig.x;
            gesture.item.y = gesture.orig.y;
            ed.invalidateItem(gesture.item);
        }
        if (gesture.type === "scatter") ed.removeLive(gesture.layer, gesture.items);
        if (gesture.type === "pathNode" && gesture.moved) {
            ed.invalidateItem(gesture.item);
            Object.assign(gesture.item, gesture.orig);
            ed.invalidateItem(gesture.item);
        }
        if (gesture.type === "path") ed.previewPath = null;
        gesture = null;
        updateCursorClass();
        ed.requestFrame();
        ed.gestureEnded();
    }

    ed.input = {
        cancel: cancelGesture,
        // live, uncommitted document changes (autosave must not persist them)
        mutating: () => !!gesture && (gesture.type === "stroke" || gesture.type === "scatter"
            || (gesture.type === "drag" && gesture.moved) || (gesture.type === "pathNode" && gesture.moved)),
    };

    function startPinch() {
        const [a, b] = [...pointers.values()];
        gesture = {
            type: "pinch",
            dist: Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)),
            mid: { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 },
            zoom: ed.view.zoom,
            panX: ed.view.panX,
            panY: ed.view.panY,
        };
    }

    canvas.addEventListener("pointerdown", (event) => {
        if (event.pointerType === "pen") ed.ui.showPressure();
        try {
            canvas.setPointerCapture(event.pointerId);
        } catch (_error) {
            // synthetic or already-released pointers cannot be captured; continue without capture
        }
        pointers.set(event.pointerId, local(event));
        canvas.focus({ preventScroll: true });
        if (pointers.size === 2) {
            cancelGesture();
            startPinch();
            return;
        }
        if (pointers.size > 2 || gesture) return;
        event.preventDefault();
        const point = ed.clientToDoc(event.clientX, event.clientY);
        ed.cursor = point;
        const wantsPan = event.button === 1 || spaceDown || ed.tool === "pan";
        if (wantsPan) {
            gesture = { type: "pan", pointerId: event.pointerId, last: local(event) };
            updateCursorClass();
            return;
        }
        if (event.button !== 0) return;

        if (ed.tool === "brush" || ed.tool === "eraser") {
            if (ed.beginStroke(point, pressureOf(event))) gesture = { type: "stroke", pointerId: event.pointerId };
        } else if (ed.tool === "path") {
            if (!ed.insideMap(point)) return;
            ed.commitEdit();
            const at = ed.clampToMap(point.x, point.y);
            const item = { id: null, x: at.x, y: at.y, material: ed.pathOpts.material,
                width: ed.pathOpts.width, points: [{ x: 0, y: 0 }] };
            ed.previewPath = item;
            gesture = { type: "path", pointerId: event.pointerId, item, spacing: 28 };
        } else if (ed.tool === "stamp") {
            if (!ed.stampOpts.asset) {
                ed.ui.toast("Wähle zuerst ein Symbol aus der Palette.");
                return;
            }
            if (!ed.insideMap(point)) {
                ed.ui.toast("Symbole lassen sich nur auf der Karte setzen.");
                return;
            }
            const layer = ed.targetLayer("stamps");
            if (!layer) return;
            ed.commitEdit();
            const item = ed.createStamp(point, ed.stampOpts.asset);
            if (!ed.placeLive(layer, item)) {
                ed.ui.toast("Höchstgrenze an Symbolen erreicht.");
                return;
            }
            gesture = { type: "scatter", pointerId: event.pointerId, layer, items: [item], last: point };
        } else if (ed.tool === "label") {
            if (!ed.insideMap(point)) {
                ed.ui.toast("Orte lassen sich nur auf der Karte setzen.");
                return;
            }
            const layer = ed.targetLayer("labels");
            if (!layer) return;
            const item = ed.createLabel(point);
            if (ed.addItems(layer, [item], "Ort setzen")) {
                ed.select(item.id);
                ed.ui.focusLabelName();
            }
        } else if (ed.tool === "select") {
            const selected = ed.selection && ed.doc.layers.flatMap((layer) => layer.items || []).find((item) => item.id === ed.selection);
            if (selected && selected.points && event.shiftKey && !event.altKey) {
                const node = selected.points.findIndex((p) => Math.hypot(selected.x + p.x - point.x, selected.y + p.y - point.y) <= 9 / ed.view.zoom);
                if (node >= 0) {
                    gesture = { type: "pathNode", pointerId: event.pointerId, item: selected, node,
                        orig: JSON.parse(JSON.stringify(selected)), startLocal: local(event), moved: false };
                    return;
                }
            }
            const hits = ed.hitTestAll(point);
            const current = hits.findIndex(({ item }) => item.id === ed.selection);
            const hit = event.altKey && hits.length ? hits[(current + 1) % hits.length] : hits[0];
            if (hit) {
                ed.select(hit.item.id);
                if (!event.altKey) gesture = { type: "drag", pointerId: event.pointerId, item: hit.item, start: point, orig: { x: hit.item.x, y: hit.item.y }, moved: false, startLocal: local(event) };
            } else {
                ed.select(null);
                gesture = { type: "pan", pointerId: event.pointerId, last: local(event) };
                updateCursorClass();
            }
        }
    });

    canvas.addEventListener("pointermove", (event) => {
        if (pointers.has(event.pointerId)) pointers.set(event.pointerId, local(event));
        if (gesture && gesture.type === "pinch") {
            if (pointers.size < 2) return;
            const [a, b] = [...pointers.values()];
            const dist = Math.max(1, Math.hypot(a.x - b.x, a.y - b.y));
            const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
            const zoom = Math.min(4, Math.max(0.1, gesture.zoom * (dist / gesture.dist)));
            const docX = (gesture.mid.x - gesture.panX) / gesture.zoom;
            const docY = (gesture.mid.y - gesture.panY) / gesture.zoom;
            ed.view.zoom = zoom;
            ed.view.panX = mid.x - docX * zoom;
            ed.view.panY = mid.y - docY * zoom;
            ed.ui.updateZoom();
            ed.requestFrame();
            return;
        }
        const point = ed.clientToDoc(event.clientX, event.clientY);
        if (!gesture) {
            ed.cursor = point;
            if (ed.tool === "brush" || ed.tool === "eraser" || ed.tool === "stamp") ed.requestFrame();
            return;
        }
        if (gesture.pointerId !== event.pointerId) return;
        if (gesture.type === "pan") {
            const now = local(event);
            ed.view.panX += now.x - gesture.last.x;
            ed.view.panY += now.y - gesture.last.y;
            gesture.last = now;
            ed.requestFrame();
        } else if (gesture.type === "stroke") {
            const samples = typeof event.getCoalescedEvents === "function" ? event.getCoalescedEvents() : [];
            for (const sample of samples.length ? samples : [event]) {
                ed.continueStroke(ed.clientToDoc(sample.clientX, sample.clientY), pressureOf(sample));
            }
            ed.cursor = point;
        } else if (gesture.type === "path") {
            const at = ed.clampToMap(point.x, point.y);
            const points = gesture.item.points;
            const last = points[points.length - 1];
            const next = { x: at.x - gesture.item.x, y: at.y - gesture.item.y };
            if (Math.hypot(next.x - last.x, next.y - last.y) >= gesture.spacing) {
                if (points.length >= 128) {
                    gesture.item.points = points.filter((_, index) => index % 2 === 0);
                    gesture.spacing *= 2;
                }
                gesture.item.points.push(next);
            }
            ed.requestFrame();
        } else if (gesture.type === "pathNode") {
            const now = local(event);
            if (!gesture.moved && Math.hypot(now.x - gesture.startLocal.x, now.y - gesture.startLocal.y) < 3) return;
            gesture.moved = true;
            const at = ed.clampToMap(point.x, point.y);
            ed.invalidateItem(gesture.item);
            if (gesture.node === 0) {
                const dx = at.x - gesture.orig.x;
                const dy = at.y - gesture.orig.y;
                gesture.item.x = at.x;
                gesture.item.y = at.y;
                gesture.item.points = gesture.orig.points.map((p, index) => index === 0 ? { x: 0, y: 0 } : { x: p.x - dx, y: p.y - dy });
            } else {
                gesture.item.points[gesture.node] = { x: at.x - gesture.item.x, y: at.y - gesture.item.y };
            }
            ed.invalidateItem(gesture.item);
        } else if (gesture.type === "drag") {
            const now = local(event);
            if (!gesture.moved && Math.hypot(now.x - gesture.startLocal.x, now.y - gesture.startLocal.y) < 3) return;
            gesture.moved = true;
            ed.invalidateItem(gesture.item);
            const at = ed.clampToMap(gesture.orig.x + point.x - gesture.start.x, gesture.orig.y + point.y - gesture.start.y);
            gesture.item.x = at.x;
            gesture.item.y = at.y;
            ed.invalidateItem(gesture.item);
            ed.requestFrame();
        } else if (gesture.type === "scatter") {
            ed.cursor = point;
            if (ed.stampOpts.scatter) {
                const spacing = Math.max(12, ed.stampOpts.size * 0.75);
                if (ed.insideMap(point) && Math.hypot(point.x - gesture.last.x, point.y - gesture.last.y) >= spacing) {
                    const item = ed.createStamp(point, ed.stampOpts.asset);
                    if (ed.placeLive(gesture.layer, item)) gesture.items.push(item);
                    gesture.last = point;
                }
            }
            ed.requestFrame();
        }
    });

    function release(event) {
        pointers.delete(event.pointerId);
        try {
            if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
        } catch (_error) {
            // ignore
        }
    }

    canvas.addEventListener("pointerup", (event) => {
        release(event);
        if (!gesture) return;
        if (gesture.type === "pinch") {
            if (pointers.size < 2) gesture = null;
            return;
        }
        if (gesture.pointerId !== event.pointerId) return;
        const done = gesture;
        gesture = null;
        if (done.type === "stroke") ed.endStroke();
        else if (done.type === "path") {
            ed.previewPath = null;
            const at = ed.clampToMap(ed.clientToDoc(event.clientX, event.clientY).x, ed.clientToDoc(event.clientX, event.clientY).y);
            const end = { x: at.x - done.item.x, y: at.y - done.item.y };
            const last = done.item.points[done.item.points.length - 1];
            if (Math.hypot(end.x - last.x, end.y - last.y) >= 3) {
                if (done.item.points.length >= 128) done.item.points[done.item.points.length - 1] = end;
                else done.item.points.push(end);
            }
            if (done.item.points.length > 1 && Math.hypot(end.x, end.y) >= 5) {
                done.item.id = ed.newPathId();
                if (ed.addPath(done.item)) ed.select(done.item.id);
            }
        } else if (done.type === "pathNode" && done.moved) {
            ed.updateItem(done.item, done.orig, JSON.parse(JSON.stringify(done.item)), "Wegpunkt verschieben");
        }
        else if (done.type === "drag" && done.moved) {
            const after = { ...done.item };
            const before = { ...done.item, x: done.orig.x, y: done.orig.y };
            ed.updateItem(done.item, before, after, "Verschieben");
        } else if (done.type === "scatter") ed.commitPlaced(done.layer, done.items);
        updateCursorClass();
        ed.requestFrame();
        ed.gestureEnded();
    });

    canvas.addEventListener("pointercancel", (event) => {
        release(event);
        if (gesture && (gesture.type === "pinch" || gesture.pointerId === event.pointerId)) cancelGesture();
    });

    canvas.addEventListener("pointerleave", () => {
        if (!gesture) {
            ed.cursor = null;
            ed.requestFrame();
        }
    });

    canvas.addEventListener("contextmenu", (event) => event.preventDefault());

    canvas.addEventListener("wheel", (event) => {
        event.preventDefault();
        const unit = event.deltaMode === 1 ? 0.05 : event.deltaMode === 2 ? 0.5 : 0.0015;
        const factor = Math.exp(-event.deltaY * unit * (event.ctrlKey ? 2.5 : 1));
        const p = local(event);
        ed.zoomAt(factor, p.x, p.y);
    }, { passive: false });

    const toolKeys = { h: "pan", b: "brush", e: "eraser", s: "stamp", t: "label", v: "select", w: "path" };

    document.addEventListener("keydown", (event) => {
        if (document.querySelector("dialog[open]")) return;
        const typing = isTextEntry(event.target);
        if (event.code === "Space") {
            if (typing || event.target.closest("select, input[type='range']")) return;
            // Keep native Space activation for a focused button. If the user
            // drags the canvas before keyup, the held key still pans it.
            if (!isControl(event.target) || event.target === canvas) event.preventDefault();
            if (!spaceDown) {
                spaceDown = true;
                updateCursorClass();
            }
            return;
        }
        const mod = event.ctrlKey || event.metaKey;
        const key = event.key.toLowerCase();
        if (mod && key === "s") {
            event.preventDefault();
            ed.savePrimary();
            return;
        }
        if (typing) return;
        if (mod && key === "z") {
            event.preventDefault();
            if (event.shiftKey) ed.redo();
            else ed.undo();
            return;
        }
        if (mod && key === "y") {
            event.preventDefault();
            ed.redo();
            return;
        }
        if (mod || event.altKey) return;
        if (toolKeys[key]) {
            ed.setTool(toolKeys[key]);
            return;
        }
        if (event.key === "[" || event.key === "]" || event.key === "{" || event.key === "}") {
            const up = event.key === "]" || event.key === "}";
            ed.ui.nudge(event.shiftKey ? "softness" : "size", up);
            event.preventDefault();
            return;
        }
        if (event.key === "Delete" || event.key === "Backspace") {
            if (ed.selection) {
                event.preventDefault();
                ed.deleteSelection();
            }
            return;
        }
        if (event.key === "Escape") {
            cancelGesture();
            ed.select(null);
            return;
        }
        if (event.key === "+" || event.key === "=") ed.zoomStep(1.25);
        else if (event.key === "-") ed.zoomStep(0.8);
        else if (key === "f") ed.fit();
    });

    document.addEventListener("keyup", (event) => {
        if (event.code === "Space" && spaceDown) {
            spaceDown = false;
            updateCursorClass();
        }
    });

    window.addEventListener("blur", () => {
        spaceDown = false;
        updateCursorClass();
    });

    updateCursorClass();
    ed.updateCursorClass = updateCursorClass;
}
