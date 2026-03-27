# Apply Output

```
artifact: apply-output
milestone: M2
phase: APPLY
status: complete
date: 2026-03-26
```

---

## Input Summary

- M1 Discover/Apply/Deploy/Monitor: Complete (Dice API works)
- M2 Discover: Canvas-based map, HTML5 Canvas, Vite + React, Tailwind
- Tech Stack Confirmed: React, Vite, Socket.IO Client

---

## Solution Design

### Architecture Overview

```
Frontend (React)
├── MapCanvas (HTML5 Canvas for rendering)
├── TokenLayer (drag-drop handling)
├── Sidebar
│   ├── CharacterList
│   ├── DiceRoller
│   └── Chat
└── Socket.IO Client (real-time sync)
     ↓ (REST/WebSocket)
Backend (Flask)
├── /api/map/init (load map state)
├── /api/tokens (CRUD tokens)
└── socket.io events (token updates, dice rolls)
```

### Component Tree

```
App
├── GameBoard (main container)
│   ├── MapCanvas
│   │   ├── Grid
│   │   ├── Tokens[] (draggable)
│   │   └── Lighting (if fog of war)
│   └── Sidebar
│       ├── DiceRoller
│       ├── TokenList
│       └── Chat
└── ConnectionStatus
```

### Data Models

**Token (frontend)**
```javascript
{
  id: "token_1",
  x: 10,           // grid units
  y: 10,
  type: "player",  // or "npc"
  name: "Aragorn",
  image: "url_or_datauri",
  size: 1          // grid squares
}
```

**Map State (frontend)**
```javascript
{
  id: "map_1",
  width: 20,       // grid units
  height: 20,
  gridSize: 32,    // pixels per grid square
  tokens: [Token]
}
```

### API Contracts

**WebSocket Events**

- `connect`: Client connects to server
- `token_update`: {token} – broadcast token movement
- `token_create`: {token} – add new token
- `token_delete`: {token_id} – remove token
- `map_sync`: {map_state} – full state sync on load

**REST Endpoints**

- `GET /api/game/state` → {map_state, tokens}
- `POST /api/tokens` → {token} (create)
- `PUT /api/tokens/{id}` → {token} (update position)
- `DELETE /api/tokens/{id}` → success

### Pseudocode (Canvas Rendering)

```python
def render_map():
    # Clear canvas
    canvas.fillStyle = "#f0f0f0"
    canvas.fillRect(0, 0, width, height)
    
    # Draw grid
    for x in range(0, width, gridSize):
        canvas.strokeStyle = "#ddd"
        canvas.beginPath()
        canvas.moveTo(x, 0)
        canvas.lineTo(x, height)
        canvas.stroke()
    
    # Draw tokens
    for token in tokens:
        cx = token.x * gridSize + gridSize/2
        cy = token.y * gridSize + gridSize/2
        canvas.fillStyle = token.color
        canvas.beginPath()
        canvas.arc(cx, cy, gridSize/2 - 2, 0, 2*PI)
        canvas.fill()
        canvas.fillStyle = "black"
        canvas.fillText(token.name, cx - 20, cy + 30)

def handle_token_drag(mouseX, mouseY):
    gridX = Math.floor(mouseX / gridSize)
    gridY = Math.floor(mouseY / gridSize)
    token.x = gridX
    token.y = gridY
    emit("token_update", {token})
```

### Pseudocode (Socket.IO Sync)

```python
socket.on("token_update", (token) => {
    # Find token in local state
    localToken = tokens.find(t => t.id === token.id)
    if (localToken) {
        localToken.x = token.x
        localToken.y = token.y
        render_map()  # redraw
    }
})
```

---

## Acceptance Criteria

1. Map displays with square grid (32px per square)
2. Tokens render as circles with names
3. Drag-and-drop moves tokens (visual feedback)
4. Token movement syncs to other clients via Socket.IO
5. All-in-One UI (map + sidebar fit on screen)
6. Page loads without console errors