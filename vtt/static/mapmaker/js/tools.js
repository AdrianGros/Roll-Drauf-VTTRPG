globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Pointer, wheel and keyboard input. One gesture at a time; a second touch
// cancels the running gesture (reverting a partial stroke) and starts a pinch.

const TEXT_INPUT_TYPES = new Set(["text", "search", "number", "email", "url", "password", "tel", "color"]);
// Bracket characters depend on the layout: DE/macOS type them with AltGr/Option, which
// arrives as Ctrl+Alt (Windows), Alt (macOS) or the AltGraph state (Linux). Match the character.
const BRACKET_NUDGE = { "[": ["size", false], "]": ["size", true], "{": ["softness", false], "}": ["softness", true] };
const altGraph = (event) => event.getModifierState?.("AltGraph") || (event.ctrlKey && event.altKey);
// Escape without a gesture or selection leaves these tools; clicking keeps placing repeatedly.
const PLACEMENT_TOOLS = new Set(["stamp", "label", "tile", "path"]);
const PATH_POINTS_MAX = 128; // LIMITS.pathPoints
const TAP_SLOP = 6; // CSS px a click may move and still set a node

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
    // Node-by-node path ("Punkte setzen"): lives across clicks, outside the document until finished.
    let draft = null;

    const local = (event) => {
        const rect = canvas.getBoundingClientRect();
        return { x: event.clientX - rect.left, y: event.clientY - rect.top };
    };
    const pressureOf = (event) => (event.pointerType === "pen" ? event.pressure : null);
    /** The single selected path, if any (node editing needs exactly one). */
    const selectedPath = () => {
        if (!ed.selection || ed.selectionSet.count !== 1) return null;
        const item = ed.doc.layers.flatMap((layer) => layer.items || []).find((entry) => entry.id === ed.selection);
        return item && item.points ? item : null;
    };
    const nodeUnder = (item, point) => item.points.findIndex((p) => Math.hypot(item.x + p.x - point.x, item.y + p.y - point.y) <= 9 / ed.view.zoom);

    function updateCursorClass() {
        const panning = spaceDown || ed.tool === "pan" || (gesture && gesture.type === "pan");
        canvas.dataset.cursor = panning ? (gesture && gesture.type === "pan" ? "grabbing" : "grab") : ed.tool;
    }

    function cancelGesture() {
        if (!gesture) return;
        if (gesture.type === "groupDrag") ed.selectionSet.restoreMove(gesture.move);
        if (gesture.type === "marquee") ed.selectionSet.marquee=null;
        if (gesture.type === "stroke") ed.cancelStroke();
        if (gesture.type === "tiles") ed.cancelTiles();
        if (gesture.type === "erase") ed.cancelErase();
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
        if (gesture.type === "area") ed.areaPreview = null;
        gesture = null;
        updateCursorClass();
        ed.requestFrame();
        ed.gestureEnded();
    }

    function syncDraft() {
        ed.pathDraft = draft;
        ed.ui.syncPathDraft(draft ? draft.item.points.length : 0);
        ed.requestFrame();
    }

    function addDraftNode(point) {
        if (!ed.insideMap(point)) return;
        const at = ed.clampToMap(Math.round(point.x), Math.round(point.y));
        if (!draft) {
            const target = ed.pathTarget();
            if (target === false) return;
            ed.commitEdit();
            ed.select(null);
            draft = { targetId: target?.id || null, cursor: at,
                item: { id: null, x: at.x, y: at.y, material: ed.pathOpts.material, width: ed.pathOpts.width,
                    curve: ed.pathOpts.curve, points: [{ x: 0, y: 0 }] } };
            syncDraft();
            return;
        }
        const { item } = draft;
        const last = item.points[item.points.length - 1];
        const next = { x: at.x - item.x, y: at.y - item.y };
        if (Math.hypot(next.x - last.x, next.y - last.y) * ed.view.zoom <= 3) return; // second click of a double-click
        if (item.points.length >= PATH_POINTS_MAX) {
            ed.ui.toast(globalThis.VTTUi("Höchstens {count} Wegpunkte – Enter schließt den Weg ab.", { count: PATH_POINTS_MAX }));
            return;
        }
        item.points.push(next);
        syncDraft();
    }

    function removeDraftNode() {
        if (!draft) return false;
        draft.item.points.pop();
        if (!draft.item.points.length) draft = null;
        syncDraft();
        return true;
    }

    function discardDraft(notice) {
        if (!draft) return;
        draft = null;
        syncDraft();
        if (notice) ed.ui.toast(globalThis.VTTUi("Unfertiger Weg verworfen."));
    }

    /** Same rule as a freehand path: at least two nodes and leaving the start by 5 px. */
    function finishDraft() {
        if (!draft) return;
        const { item, targetId } = draft;
        if (item.points.length < 2 || !item.points.some((p) => Math.hypot(p.x, p.y) >= 5)) {
            ed.ui.toast(globalThis.VTTUi("Für einen Weg mindestens zwei Punkte setzen."));
            return;
        }
        draft = null;
        syncDraft();
        item.id = ed.newPathId();
        if (ed.addPath(item, targetId)) ed.select(item.id);
    }

    ed.input = {
        cancel: (keepDraft = false) => {
            cancelGesture();
            if (!keepDraft) discardDraft(true);
        },
        finishDraft,
        removeDraftNode,
        discardDraft: () => discardDraft(false),
        undoDraftNode: removeDraftNode,
        busy: () => !!gesture || pointers.size > 0,
        // live, uncommitted document changes (autosave must not persist them)
        mutating: () => !!gesture && (gesture.type === "stroke" || gesture.type === "erase" || gesture.type === "scatter" || gesture.type === "tiles"
            || (gesture.type === "groupDrag" && gesture.moved) || (gesture.type === "drag" && gesture.moved) || (gesture.type === "pathNode" && gesture.moved)),
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
        const wantsPan = event.button === 1 || (event.pointerType === "mouse" && event.button === 2) || spaceDown || ed.tool === "pan";
        if (wantsPan) {
            gesture = { type: "pan", pointerId: event.pointerId, last: local(event) };
            updateCursorClass();
            return;
        }
        if (event.button !== 0) return;

        if (ed.tool === "eraser") {
            if (ed.beginErase(point, pressureOf(event))) gesture = { type: "erase", pointerId: event.pointerId };
        } else if (ed.tool === "brush") {
            if (ed.beginStroke(point, pressureOf(event))) gesture = { type: "stroke", pointerId: event.pointerId };
        } else if (ed.tool === "tile") {
            if (ed.beginTiles(point)) gesture = { type: "tiles", pointerId: event.pointerId };
        } else if (ed.tool === "path" && ed.pathOpts.mode === "nodes") {
            // A node is set on release, so a drag, pan or pinch never adds one by accident.
            gesture = { type: "pathClick", pointerId: event.pointerId, startLocal: local(event), moved: false };
        } else if (ed.tool === "path") {
            if (!ed.insideMap(point)) return;
            const target = ed.pathTarget();
            if (target === false) return;
            ed.commitEdit();
            const at = ed.clampToMap(point.x, point.y);
            const item = { id: null, x: at.x, y: at.y, material: ed.pathOpts.material,
                width: ed.pathOpts.width, curve: ed.pathOpts.curve, points: [{ x: 0, y: 0 }] };
            ed.previewPath = item;
            gesture = { type: "path", pointerId: event.pointerId, item, spacing: 28, targetId: target?.id || null };
        } else if (ed.tool === "stamp") {
            if (!ed.stampOpts.asset || !ed.assetAvailable(ed.stampOpts.asset)) {
                ed.ui.toast(globalThis.VTTUi("Wähle zuerst ein Symbol aus der Palette."));
                return;
            }
            if (!ed.insideMap(point)) {
                ed.ui.toast(globalThis.VTTUi("Symbole lassen sich nur auf der Karte setzen."));
                return;
            }
            const layer = ed.targetLayer("stamps");
            if (!layer) return;
            if (ed.stampOpts.area) {
                // Area fill: the rectangle is only previewed; stamps are created on release.
                gesture = { type: "area", pointerId: event.pointerId, start: point, startLocal: local(event) };
                ed.areaPreview = { a: point, b: point, count: ed.areaPlan(point, point).count };
                ed.requestFrame();
                return;
            }
            ed.commitEdit();
            const item = ed.createStamp(point, ed.stampOpts.asset);
            if (!ed.placeLive(layer, item)) {
                ed.ui.toast(globalThis.VTTUi("Höchstgrenze an Symbolen erreicht."));
                return;
            }
            gesture = { type: "scatter", pointerId: event.pointerId, layer, items: [item], last: point };
        } else if (ed.tool === "label") {
            if (!ed.insideMap(point)) {
                ed.ui.toast(globalThis.VTTUi("Orte lassen sich nur auf der Karte setzen."));
                return;
            }
            const layer = ed.targetLayer("labels");
            if (!layer) return;
            const item = ed.createLabel(point);
            if (ed.addItems(layer, [item], "Ort setzen")) {
                ed.select(item.id);
                ed.cursor = null; // the preview returns with the next pointer move, not on top of the new label
            }
        } else if (ed.tool === "select") {
            const selected = selectedPath();
            if (selected && (event.shiftKey || ed.editPathNodes) && !event.altKey) {
                const node = nodeUnder(selected, point);
                if (node >= 0) {
                    gesture = { type: "pathNode", pointerId: event.pointerId, item: selected, node,
                        orig: JSON.parse(JSON.stringify(selected)), startLocal: local(event), moved: false };
                    return;
                }
            }
            if (ed.selectionSet.tileAt(point,event.shiftKey)) {
                if(!event.shiftKey)gesture={type:'groupDrag',pointerId:event.pointerId,start:point,startLocal:local(event),move:ed.selectionSet.beginMove(),moved:false};
                return;
            }
            const hits = ed.hitTestAll(point);
            const current = hits.findIndex(({ item }) => item.id === ed.selection);
            const hit = event.altKey && hits.length ? hits[(current + 1) % hits.length] : hits[0];
            if (hit) {
                if(event.shiftKey){ed.select(hit.item.id,true);return;}
                if(event.altKey || !ed.selectionSet.ids.includes(hit.item.id))ed.select(hit.item.id);
                if(!event.altKey)gesture={type:'groupDrag',pointerId:event.pointerId,start:point,startLocal:local(event),move:ed.selectionSet.beginMove(),moved:false};
            } else {
                if(!event.shiftKey)ed.select(null);
                gesture={type:'marquee',pointerId:event.pointerId,start:point,add:event.shiftKey};
                ed.selectionSet.marquee={a:point,b:point};ed.requestFrame();
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
            if (ed.tool === "select" && !spaceDown) {
                // Show where a drag moves a single node instead of the whole selection.
                const path = (ed.editPathNodes || event.shiftKey) && !event.altKey ? selectedPath() : null;
                canvas.dataset.cursor = path && nodeUnder(path, point) >= 0 ? "node" : "select";
            }
            if (draft) draft.cursor = point;
            if (ed.tool === "brush" || ed.tool === "eraser" || ed.tool === "stamp" || ed.tool === "tile" || ed.tool === "label" || draft) ed.requestFrame();
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
        } else if (gesture.type === "erase") {
            const samples = typeof event.getCoalescedEvents === "function" ? event.getCoalescedEvents() : [];
            for (const sample of samples.length ? samples : [event]) {
                ed.continueErase(ed.clientToDoc(sample.clientX, sample.clientY), pressureOf(sample));
            }
            ed.cursor = point;
        } else if (gesture.type === "tiles") {
            const samples = typeof event.getCoalescedEvents === "function" ? event.getCoalescedEvents() : [];
            for (const sample of samples.length ? samples : [event]) ed.continueTiles(ed.clientToDoc(sample.clientX, sample.clientY));
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
        } else if (gesture.type === "pathClick") {
            const now = local(event);
            if (Math.hypot(now.x - gesture.startLocal.x, now.y - gesture.startLocal.y) >= TAP_SLOP) gesture.moved = true;
            if (draft) {
                draft.cursor = point;
                ed.requestFrame();
            }
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
        } else if (gesture.type === "area") {
            ed.cursor = point;
            ed.areaPreview = { a: gesture.start, b: point, count: ed.areaPlan(gesture.start, point).count };
            ed.ui.showAreaPlan(ed.areaPreview.count);
            ed.requestFrame();
        } else if (gesture.type === 'marquee') {
            ed.selectionSet.marquee={a:gesture.start,b:point};ed.requestFrame();
        } else if (gesture.type === 'groupDrag') {
            const now=local(event);
            if(!gesture.moved && Math.hypot(now.x-gesture.startLocal.x,now.y-gesture.startLocal.y)<3)return;
            gesture.moved=true;ed.selectionSet.previewMove(gesture.move,point.x-gesture.start.x,point.y-gesture.start.y);
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
                    // With the optional stamp grid, several pointer positions snap to one cell:
                    // never stack a second stamp on a grid position already used in this gesture.
                    // (Same stampPoint() as the preview and createStamp; normal scatter is unchanged.)
                    const snapped = ed.stampOpts.grid ? ed.stampPoint(point) : null;
                    if (snapped && gesture.items.some((placed) => placed.x === snapped.x && placed.y === snapped.y)) {
                        // keep gesture.last so the next sample in a fresh cell is placed at once
                    } else {
                        const item = ed.createStamp(point, ed.stampOpts.asset);
                        if (ed.placeLive(gesture.layer, item)) gesture.items.push(item);
                        gesture.last = point;
                    }
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
        if (done.type === "area") {
            ed.areaPreview = null;
            const now = local(event);
            if (Math.hypot(now.x - done.startLocal.x, now.y - done.startLocal.y) < 6) ed.ui.toast(globalThis.VTTUi("Für „Fläche füllen“ ein Rechteck auf der Karte aufziehen."));
            else ed.fillArea(done.start, ed.clientToDoc(event.clientX, event.clientY));
        } else if (done.type === 'marquee') {
            ed.selectionSet.marquee=null;
            const p=ed.clientToDoc(event.clientX,event.clientY);
            if(Math.hypot(p.x-done.start.x,p.y-done.start.y)*ed.view.zoom>=3)ed.selectionSet.rectangle(done.start,p,done.add);
            ed.requestFrame();
        }
        else if (done.type === 'groupDrag' && done.moved) ed.selectionSet.finishMove(done.move);
        else if (done.type === "stroke") ed.endStroke();
        else if (done.type === "erase") ed.endErase();
        else if (done.type === "tiles") ed.endTiles();
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
                if (ed.addPath(done.item, done.targetId)) ed.select(done.item.id);
            }
        } else if (done.type === "pathClick") {
            const now = local(event);
            if (!done.moved && Math.hypot(now.x - done.startLocal.x, now.y - done.startLocal.y) < TAP_SLOP) addDraftNode(ed.clientToDoc(event.clientX, event.clientY));
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
    canvas.addEventListener("dblclick", (event) => {
        if (!draft) return;
        event.preventDefault();
        finishDraft();
    });

    let wheelCarry = 0;
    let brushWheelCarry = 0, brushWheelMode = "", brushWheelAt = 0, brushWheelSign = 0;
    canvas.addEventListener("wheel", (event) => {
        event.preventDefault();
        const mode = !event.ctrlKey && !event.metaKey && event.shiftKey && !event.altKey && ["brush","eraser","stamp"].includes(ed.tool) ? "size"
            : !event.ctrlKey && !event.metaKey && event.altKey && !event.shiftKey && ed.tool === "brush" ? "material" : "";
        if (mode !== brushWheelMode) { brushWheelCarry = 0; brushWheelMode = mode; }
        if (mode) {
            wheelCarry = 0;
            if (ed.input.busy()) return;
            const delta = event.deltaY || event.deltaX;
            const pixels = event.deltaMode === 1 ? delta*33 : event.deltaMode === 2 ? delta*400 : delta;
            const now = performance.now(), sign = Math.sign(pixels);
            if (now-brushWheelAt > 400 || sign !== brushWheelSign) brushWheelCarry = 0;
            brushWheelAt = now; brushWheelSign = sign;
            brushWheelCarry = Math.max(-300,Math.min(300,brushWheelCarry+pixels));
            while (Math.abs(brushWheelCarry) >= 100) {
                const up = brushWheelCarry < 0;
                if (mode === "size") ed.ui.nudge("size",up); else ed.ui.cycleBrush(up);
                brushWheelCarry -= Math.sign(brushWheelCarry)*100;
            }
            return;
        }
        // Optional Alt+wheel reorders a selection in the select tool; every other
        // wheel (including Ctrl/pinch) keeps zooming as before.
        if (event.altKey && !event.ctrlKey && !event.metaKey && ed.tool === "select" && ed.selectionSet.count && !ed.selectionSet.tiles) {
            const pixels = event.deltaMode === 1 ? event.deltaY * 33 : event.deltaMode === 2 ? event.deltaY * 400 : event.deltaY;
            wheelCarry += pixels || event.deltaX || 0;
            while (Math.abs(wheelCarry) >= 60) {
                ed.wheelReorder(wheelCarry < 0);
                wheelCarry -= Math.sign(wheelCarry) * 60;
            }
            return;
        }
        wheelCarry = 0;
        const unit = event.deltaMode === 1 ? 0.05 : event.deltaMode === 2 ? 0.5 : 0.0015;
        const factor = Math.exp(-event.deltaY * unit * (event.ctrlKey ? 2.5 : 1));
        const p = local(event);
        ed.zoomAt(factor, p.x, p.y);
    }, { passive: false });

    const toolKeys = { h: "pan", b: "brush", e: "eraser", s: "stamp", k: "tile", t: "label", v: "select", w: "path" };

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
        if (!mod && !event.altKey && !event.shiftKey && !altGraph(event) && event.target === canvas && !ed.input.busy()) {
            if (key === "q") {
                event.preventDefault();
                if (!event.repeat) ed.ui.showQuickPalette(true);
                return;
            }
            const digit = /^Digit([0-9])$/.exec(event.code);
            if (digit && ["brush","eraser"].includes(ed.tool)) {
                event.preventDefault();
                ed.ui.setBrushOpacity(Number(digit[1] || 0) === 0 ? 100 : Number(digit[1])*10);
                return;
            }
        }
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
        // Layer switch in the tool context: Alt+↑ / Alt+↓ (top of the layer list first).
        if (event.altKey && !mod && (event.key === "ArrowUp" || event.key === "ArrowDown")) {
            event.preventDefault();
            ed.cycleLayer(event.key === "ArrowUp" ? -1 : 1);
            return;
        }
        // Cmd+[ / Cmd+] and Ctrl-only brackets stay with the browser.
        const nudge = BRACKET_NUDGE[event.key];
        if (nudge && !event.metaKey && (!event.ctrlKey || altGraph(event))) {
            ed.ui.nudge(nudge[0], nudge[1]);
            event.preventDefault();
            return;
        }
        if (mod || event.altKey) return;
        // Object order: Bild↑/Bild↓ one step, with Umschalt to front/back (selection, canvas focus).
        if ((event.key === "PageUp" || event.key === "PageDown") && ed.tool === "select" && ed.selectionSet.count
            && (event.target === canvas || event.target === document.body)) {
            event.preventDefault();
            const up = event.key === "PageUp";
            ed.reorderSelection(event.shiftKey ? (up ? "front" : "back") : (up ? "forward" : "backward"));
            return;
        }
        if (draft && event.key === "Enter" && (!isControl(event.target) || event.target === canvas)) {
            event.preventDefault();
            finishDraft();
            return;
        }
        if (draft && (event.key === "Backspace" || event.key === "Delete")) {
            event.preventDefault();
            removeDraftNode();
            return;
        }
        if (toolKeys[key]) {
            ed.setTool(toolKeys[key]);
            return;
        }
        if (event.key === "Delete" || event.key === "Backspace") {
            if (ed.selectionSet.count) {
                event.preventDefault();
                ed.deleteSelection();
            }
            return;
        }
        if (event.key === "Escape") {
            // Staged: first cancel the gesture or clear the selection, then leave the placement tool.
            const busy = !!gesture || !!draft || ed.selectionSet.count > 0;
            cancelGesture();
            discardDraft(false);
            ed.select(null);
            if (!busy && PLACEMENT_TOOLS.has(ed.tool)) {
                ed.setTool("select");
                ed.ui.toast(globalThis.VTTUi("Platzieren beendet – Auswählen (V)."));
            }
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
