# FV06 remaining brush controls and temporary quick palette

Status: Discover closed; Apply approved for the retained FV06 technical scope. Permanent. Inputs: E02/E04/E07/E08, the earlier map review's S5/S11 candidates, current tools/UI/brush source and delivered File-menu Escape. No owner input, new art, dependency, data format or schema is required.

## Discovered boundary

The editor already keeps separate paint/eraser preferences, material choices, size/opacity/softness controls and an image-brush mode that preserves original pixels/colors. `UI.nudge` synchronizes size/softness and the per-asset stamp-size cache. Ordinary wheel zooms; Ctrl-wheel/pinch zoom, Alt-wheel reorders only in Select, middle/right/Space pan, brackets and AltGr are established behavior. The generic input typing/dialog guards exist. Own material color is one value, with no eight-color history. No quick palette exists. All new data can remain browser/editor preference state.

## Contracts

1. **Eight recent custom colors.** Record a validated lowercase six-digit hex color only after an actual, completed, changed paint stroke using a material brush with custom color enabled. Capture that color at stroke start, not from a later preference value. Canceled/no-op strokes and erasing/image brushes add nothing. Deduplicate most-recent-first, cap at eight and persist under `rd.mapmaker.recentColors.v1`; invalid/unavailable storage degrades to in-memory/empty safely. Undo of a painted stroke does not erase its useful color history. Chips select the exact color for a material brush; explicitly leaving an image brush does not tint or alter its original. Neither project JSON nor Undo contains this preference.

2. **Opacity keys.** With canvas focus, Brush or Eraser active, no dialog/gesture and no modifier, physical digits1–9/0 set10–90/100%. Use the existing opacity control, preview and brush preference together. Text fields, browser Ctrl/Meta chords, AltGr and other tools retain their behavior.

3. **Faster size/brush switching.** Shift+wheel in Brush/Eraser/Stamp changes size through the existing bounded nudge path. Alt+wheel in Brush cycles the actual registered material brushes through the same selection/target behavior as palette clicks, preserving other brush settings and leaving image mode explicitly. Ctrl/Meta combinations continue zoom behavior; Alt+wheel in Select keeps ordering; ordinary wheel/pinch/pan are unchanged. Use deltaY or deltaX, normalize deltaMode, accumulate high-resolution wheel input and cap work per event. During an active gesture consume the new chord without changing its captured brush/target. Existing brackets stay unchanged. Factor normal material selection into one shared UI method so quick selection and ordinary buttons cannot diverge.

4. **Temporary radial tools/colors.** Hold Q with canvas focus and no modifier/active pointer gesture to open a native modal dialog centered near the pointer and clamped to the viewport. Releasing Q selects only the explicitly hovered choice; release in the center dismisses without change. Eight familiar tools use their existing icons/labels in an inner ring; the recent colors use an outer ring with44px targets. No hover changes the document or preferences. A visible “Schnellpalette” button opens the same dialog persistently for touch and keyboard: native Tab/Enter choose, Escape/cancel/backdrop dismiss. Native modality prevents accidental canvas input behind it and supplies focus containment; closing restores the trigger/canvas. For small viewports use a bounded layout/fallback rather than off-screen controls. There is no middle-button override. The tool panel/help explains Q, wheel modifiers and the accessible button; use the existing DE/EN catalog.

The palette uses existing vectors, text and CSS colors. No image generation, generative use, source-art modification or new image asset is part of this work. Ducky originals never become inputs. No rule state, map pixels, source metadata or project history changes until the user deliberately paints or chooses an existing tool action.

## Interfaces and bounded implementation

Keep changes in mapmaker UI/input/editor and index/CSS, plus a catalog fragment and focused browser cases. Add an internal busy-input predicate covering both gestures and held pointers; do not expose write access through the diagnostic API. UI owns recent-color validation/storage, shared material choice and native quick-dialog focus/selection state. Editor captures stroke color and records it only after a nonempty completion. The existing renderer, server validator, exports, project library, Atlas and snapshots need no schema changes.

Medium risks are resolved by explicit modifier priority, typing/modality/pointer guards, start-of-stroke capture, strict local-storage values and native focus handling. Existing image colors and artist restrictions remain intact. There is no unresolved strategic decision or permission gate.

## Acceptance and Deploy handoff

- Real completed/canceled/no-op strokes prove eight-color order/dedup/reselection/reload and corrupt/unavailable-storage fallback; preferences do not enter map JSON/history.
- Keys/sliders/previews agree; text entry and browser modifiers remain protected. Wheel size/material shortcuts preserve zoom/pinch/pan and Select ordering. A captured stroke keeps its initial target/preferences.
- Q hold/release/cancel and the persistent button work through real controls; hover/opening leave document/history unchanged; mouse, native keyboard and390px layout are covered. Image-brush color preservation is retained.
- Run the smallest relevant existing brush/input/selection/roundtrip cases plus focused new behavior cases, catalog freshness, JS syntax and whitespace. No lane DB. No blanket full-suite claim.
- Commit/push; protect the actual current live image/source; guarded overlay, readable DB archive with no migrations, checked rollback, app-only activation; ordinary DM/Player dashboard→Maps journeys at1440/390; verify no overflow/state drift and remove scoped QA data/credentials. Only then close FV06, keeping FV05/FV09/FV12 and the other packets separate.
