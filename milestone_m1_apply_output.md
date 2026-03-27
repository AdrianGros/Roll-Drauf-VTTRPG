# Apply Output Template

Use this template to record the result of an Apply phase. Fill in all sections before
closing the phase. This artifact is immutable once the phase is closed.

Apply converts Discover results into a design that can be implemented. It produces no
implementation code — only architecture, interfaces, data models, pseudocode, and
acceptance criteria.

For the standard phase output structure and retention rules, see `framework/core/deliverables.md`.

---

```
artifact: apply-output
milestone: M1
phase: APPLY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Discover Output: milestone_m1_discover_output.md (features analysis, DM feedback, Python preference).
- Resolved Questions: Target platform - Web-App for All-in-One experience; Team size - Solo; Asgard API - [TBD] check availability.
- Constraints: D&D focus, Discord integration, easy DM onboarding with standard setting.

---

## Solution Design

### Architecture Overview
- **Frontend**: JavaScript (React) for interactive UI (maps, tokens, sheets, swipe navigation). Handles rendering, user input, real-time updates via WebSockets.
- **Backend**: Python (Flask) for server logic, API endpoints, dice rolling, data persistence.
- **Database**: SQLite for MVP (switch to PostgreSQL later) to store campaigns, characters, maps.
- **Real-Time**: Socket.IO for multi-user sync (tokens, chat).
- **External Integrations**: D&D Beyond API for sheets; Asgard API for map generation [TBD].
- **Deployment**: Self-hosted like Foundry, but web-based for accessibility.

Components:
- Map Module: Canvas-based editor/generator (hex grids, dynamic lighting).
- Character Module: Clean sheets with D&D integration.
- DM Tools: Minigame for world/nation control (later milestone).
- Localization: i18n library for translations.

### Interface Definitions
- /api/dice/roll: POST {dice: "1d20+5"} -> {result: 17}
- /api/map/generate: POST {type: "dungeon", size: "small"} -> {map_data: {...}}
- /api/character/update: PUT {id: 1, hp: 20} -> success

### Data Models
- Campaign: {id, name, players: [user_ids], map_id, journal: [entries]}
- Character: {id, name, stats: {str: 15, dex: 12}, sheet_data: {...}}
- Map: {id, grid: [[cells]], tokens: [{x,y,type}], effects: [{type, position}]}

### Workflow Diagram (Text)
1. User logs in -> Load campaign.
2. DM generates map via integrated tool or Asgard API.
3. Players place tokens, roll dice via API.
4. Real-time sync via WebSockets.
5. DM uses overlay for cinematic effects.

### Pseudocode for Dice Rolling
def roll_dice(dice_string):
    # Parse "1d20+5" -> num=1, sides=20, mod=5
    total = 0
    for _ in range(num):
        total += random.randint(1, sides)
    return total + mod

### Open TBDs
- Asgard API details and integration.
- Specific D&D Beyond overlay implementation.
- DM Minigame mechanics (post-MVP).

---

## Acceptance Criteria

1. Web-App loads campaign with map, tokens, and chat.
2. Dice rolling works with macros (e.g., 1d20+5).
3. Map editor allows placing tokens and basic lighting.
4. Character sheets display stats cleanly, integrated with D&D Beyond.
5. Swipe navigation works on touch devices.
6. Localization supports at least German/English.
7. All-in-One UI without multiple pages for core features.</content>
<parameter name="filePath">c:\Users\adria\Desktop\DAD-M\02_Projects\Programmieren\Python\VTT\milestone_m1_apply_output.md