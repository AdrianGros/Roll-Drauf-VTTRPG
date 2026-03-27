# Complete Application Architecture: Navigation + Character System

## USER JOURNEY MAP

LOGIN → DASHBOARD → [Campaigns | Characters | Settings]
  ↓
  CAMPAIGN JOIN → LOBBY (Ready Check) → GAME SESSION
  
  CHARACTER VIEW/EDIT → Spells, Equipment, Inventory

## CORE PAGES NEEDED

1. dashboard.html - Main Hub (Recent campaigns, characters, stats)
2. campaigns.html - My Campaigns + Browse + Create
3. characters.html - My Characters + Create/Import
4. campaign-join.html - Join flow (select character, preview)
5. campaign-lobby.html - Pre-game (player list, ready check, launch)
6. character-editor.html - Full character builder (stats, equipment, spells)
7. character-sheet.html - Read-only view (for reference)
8. game.html - LIVE SESSION with MMO UI (map, hotbar, inventory, chat)

## DATA MODELS NEEDED

### Character Model
- name, class, race, level, xp
- base_stats (STR, DEX, CON, INT, WIS, CHA)
- hp_current, hp_max, mana_current, mana_max
- ac, proficiency_bonus
- campaign_id (active campaign)
- character_sheet_json (all abilities, feats, etc.)

### Spell Model
- name, level, school, damage, description
- cast_time, range, duration
- character_id (which character knows it)

### Equipment Model
- name, type (armor/weapon/shield)
- ac_bonus, damage_dice
- equipped_slot
- character_id

### InventoryItem Model
- item_name, quantity, weight
- slot (equipped or backpack)
- character_id

## IN-GAME MMO UI LAYOUT

Right Sidebar Character Panel:
```
┌────────────────────┐
│  [Avatar] Name     │
│  Class | Level     │
├────────────────────┤
│ HP: ████████░ 45   │
│ MP: ██████░░░ 30   │
├────────────────────┤
│ [1]Fire [2]Shield  │
│ [Q]Slash [E]Dodge  │
│ [R]Holy  [9]Vision │
├────────────────────┤
│ 🎒 📚 ⚔️ ⚙️        │
│ Inv  Spells Skills │
├────────────────────┤
│ Buffs/Debuffs      │
│ [Haste] 2 min      │
│ [Poison] 1 min     │
└────────────────────┘
```

## NAVIGATION FLOW (URLs)

/login.html
/dashboard.html ← Main hub
  ├─ /campaigns.html (sidebar click)
  ├─ /characters.html (sidebar click)
  └─ /profile.html (user menu)

/campaigns.html
  ├─ /campaign-create.html (new campaign form)
  ├─ /campaign-join.html?id=X (join preview)
  └─ /campaign-lobby.html?id=X (ready check)

/characters.html
  ├─ /character-editor.html?id=X (create/edit)
  └─ /character-sheet.html?id=X (view)

/game.html?campaign_id=X&session_id=Y ← LIVE SESSION

## API ENDPOINTS (New + Extended)

Characters:
- POST /api/characters (create)
- GET /api/characters/mine (list)
- PUT /api/characters/{id} (update)
- DELETE /api/characters/{id} (delete)

Spells:
- GET /api/characters/{id}/spells
- POST /api/characters/{id}/spells
- DELETE /api/characters/{id}/spells/{spell_id}

Equipment:
- GET /api/characters/{id}/equipment
- POST /api/characters/{id}/equipment
- PUT /api/characters/{id}/equipment/{item_id}

Campaign (extend M4):
- GET /api/campaigns/{id}/lobby (pre-game state)
- POST /api/campaigns/{id}/ready (player ready toggle)
- POST /api/campaigns/{id}/launch (start session)

## RESPONSIVE DESIGN

- Desktop (>1200px): 3-column (sidebar, center, char panel)
- Tablet (768-1200px): 2-column (sidebar collapse)
- Mobile (<768px): Full-screen tabs, bottom nav

## PHASE ROLLOUT

Phase 1: Navigation + Characters
- Dashboard, campaigns, characters pages
- Character CRUD models + APIs

Phase 2: Campaign Lobby
- campaign-lobby.html
- Ready check system
- Join flow

Phase 3: In-Game Session
- game.html with map
- Character panel with hotbar + inventory
- Socket.IO real-time sync

Phase 4: Combat
- Initiative tracker
- Turn order
- Damage calculations

---

Ready to implement Phase 1?
