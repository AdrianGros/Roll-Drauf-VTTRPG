# FV04-REVIEW-CLOSE: M1 recheck

This is a source review of the supplied diff only. I have not run any tests or done any live verification.

## Verdict on M1: resolved

No high or medium blocker remains.

### Why it is resolved

- **`commit` no longer credits the active layer.** `commit(command, layers = [])` (`app.js`) marks only the refs passed in, de-duplicated with a `Set`. When no layers are passed it marks nothing, so callers that skip the argument fall back to no credit, not wrong credit.
- **`layerCommand` passes the real target.** Add, delete, move and `setLayerProp` (visibility, name, opacity, coast, grid) all pass `[layer]`. A strip or panel eye toggle on a non-active layer now credits that layer. This matches the new test, which expects `upper` first after its eye click while `lower` stays active.
- **Write paths use their resolved targets:**
  - `addItems` and stamp placement pass `[layer]`.
  - `addPath`, in both the existing-target and created-layer branches, passes `[layer]`.
  - Tile commit, brush stroke and join-paths pass `[layer]`.
  - Item update passes `findItem(...).layer`.
  - Order and wheel-order pass `[...layers]` and `[...session.layers]`.
  - Erase marks only after a successful `history.push`.
- **Selection writes carry their layers.** Tile move and delete pass `[g.layer]` and `[layer]`. Object move now keeps `layer` in the `beginMove` snapshot, so it passes `g.objects.map(o => o.layer)`. Delete and scale use the row layers.
- **Deliberate selection counts.** `setActiveLayer` and the cross-layer item-select branch both call `noteLayerUse`.
- **The gesture case is correct.** Alt+↑ marks the newly active layer at time T1. At mouseup, `addPath(item, targetId)` reaches `addItems(lower)`, which marks `lower` at T2 > T1. So `lower` sorts first, which is what the extended test asserts.
- **Undo/Redo leaves usage order unchanged.** `onHistoryChange` only refreshes and clears the offer. This matches the stated Apply decision.

### Two items to confirm (low, not blocking)

1. **Order commits: what are `layers` and `session.layers`?** Spreading them assumes they are a `Set` or array of layer objects. If either is a `Map`, `[...map]` yields `[key, value]` pairs. `WeakMap.set` would then accept those arrays without any error, and no layer would get credit. Their declarations are outside the diff, so please check them.
2. **Erase credit: do the arrays hold only changed layers?** The erase loop credits every entry in `rasters`, `tiles` and `stamps`. If those arrays include layers that were scanned but left unchanged (for example, in `eraseScope = "visible"`), untouched layers would get credit. The loop also never credits paths or labels. That is correct only if erase never removes those item kinds.

## Earlier low notes

| Note | Status |
|---|---|
| L1 stale grid offer | Fixed. The offer is cleared on load, on active-layer change, on every history change, on empty-layer resize and after creation. |
| L2 reference-grid source | Accepted as numeric, as stated. The `gridOnly && this.stampOpts.grid` guard falls back safely when it is `0` or `null`. |
| L3 `aria-expanded` on desktop | Fixed. It is set only when narrow and removed otherwise. |
| L6 "1 Elemente" | Fixed by the label-first "Elemente: {count}". Catalog entries for the new strings are still unverified here. |
| L7 hidden active placement modes | Improved. The summary now appends the active area or scatter mode. |
| L8 tile-as-symbol preview | Now covered by a preview-change assertion. |
| L4 breakpoint, L5 rename survives refresh | Not visible in this diff, so still open as checks. |

## Scope note

The group and erase geometry is unchanged, as stated. I found no new defect introduced by the marking changes. M1 can be closed from source once the two items above are confirmed, pending your combined test run.
