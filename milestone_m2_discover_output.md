# Discover Output Template

Use this template to record the result of a Discover phase. Fill in all sections before
closing the phase. This artifact is immutable once the phase is closed.

For the standard phase output structure and retention rules, see `framework/core/deliverables.md`.

---

```
artifact: discover-output
milestone: M2
phase: DISCOVER
status: complete
date: 2026-03-26
```

---

## Input Summary

- M1 Monitor Output: Dice API ✅ working
- Requirements from DM Interview: Map display, token placement, drag-and-drop, All-in-One UI
- Tech Decision: React + Canvas for frontend
- Constraints: Web-based, self-hosted, real-time sync via WebSockets

---

## Current-State Summary

- Backend: Flask server running, dice API functional, Socket.IO ready
- Frontend: None yet – need to create index.html, React component structure
- UI Framework: Decision pending (plain CSS vs Tailwind)

---

## Inventory

| # | Name | Description | Location | Status |
|---|---|---|---|---|
| I1 | Canvas Library | For map rendering (HTML5 Canvas or Pixi.js) | TBD | unclear |
| I2 | React Setup | Frontend framework | TBD | missing |
| I3 | UI Components | Map, tokens, token list | TBD | missing |
| I4 | WebSocket Client | Socket.IO client for real-time sync | npm | present |

---

## Dependencies

- React 18+: not installed
- Socket.IO Client: not installed
- Canvas or Pixi.js: not selected
- Bundler: Webpack/Vite: not selected

---

## Feature Breakdown

### Map Display
- Canvas-based rendering (HTML5 Canvas is simple + lightweight)
- Grid overlay (square or hex, from M1 Discover)
- Zoom/pan controls (nice-to-have)

### Token Placement
- Drag-and-drop tokens on canvas
- Real-time sync via Socket.IO
- Token properties: id, x, y, type (player, npc, etc.)

### All-in-One UI
- Single page with map on left, character/chat on right
- No multiple pages for core features

### Technical Choices
- Canvas: HTML5 Canvas sufficient for MVP (vs WebGL/Pixi.js)
- Bundler: Vite (fast, modern)
- CSS: Tailwind for quick styling

---

## Open Questions
- Hex or square grid?
- Token size/scaling?
- Minimap needed for zoom?

---

## Risks
- Canvas performance with many tokens (>100)
- Sync latency over WebSockets

---

## Next Steps
- Apply Phase: Design component tree, API contracts, pseudocode