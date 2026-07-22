# Milestones M37-M46: Registration Keys + Session Management
**Vision:** Turn Roll-Drauf VTT into a magical spellbook with controlled access via registration keys
**Scope:** 10 strategic milestones for MVP session management + key system
**Timeline:** ~3-4 weeks (parallel development)

---

## Architecture Overview

```
Registration Keys (M37-M40)
    └─> Bulk generation, distribution, tracking, admin dashboard

Session Management (M41-M45)
    ├─> State machine (preparing → active → paused → ended)
    ├─> Multi-layer maps with full controls
    ├─> Roll20-style workspace (tokens, initiative, sheets, chat)
    ├─> Real-time socket.IO sync
    └─> File upload per session

Theme & Design (M46)
    └─> Spellbook UI foundation (book opening, magical elements)
```

---

## M37: Registration Key Model & Schema

**Goal:** Foundation for access control system

**Scope:**
- Create `RegistrationKey` model with fields:
  - `key_code` (unique, 16-char alphanumeric like "SPELL-ABCD-1234-XYZ9")
  - `key_name` (friendly name: "Ranger's Guild", "Wizard Circle", etc.)
  - `key_batch_id` (track which PDF batch it came from)
  - `tier` (free, player, dm, headmaster - tied to profile_tier)
  - `max_uses` (usually 1, but configurable)
  - `uses_remaining` (decrement on registration)
  - `created_at`, `used_at`, `expires_at`
  - `used_by_id` (FK to User, null if unused)
  - `is_revoked` (admin revocation)

**Database Migration (M37):**
- `registration_keys` table with indexes on: key_code, key_batch_id, tier, used_at

**Validation:**
- Key format: uppercase alphanumeric with hyphens
- Uniqueness: key_code is UNIQUE
- Soft constraints: expiration, max_uses

**Dependencies:** None (new model)
**Breaking Changes:** None
**Rollback:** Simple drop table

---

## M38: Bulk Key Generation & PDF Export

**Goal:** Admin can create 100-key batches and distribute as PDFs

**Scope:**
- CLI command: `flask generate-keys --count 100 --tier dm --name "Campaign Batch 1"`
  - Creates 100 unique keys
  - Groups them as a batch_id
  - Outputs JSON with all keys

- PDF export endpoint: `GET /api/admin/keys/batch/<batch_id>/pdf`
  - Generates PDF with:
    - Batch title & creation date
    - All 100 keys formatted nicely
    - QR codes linking to registration form with pre-filled key
    - Instructions (theme: "Share these spellbook access codes")
    - Unused keys on first page, used keys section at back

- Admin API endpoints:
  - `POST /api/admin/keys/generate` — Create batch
  - `GET /api/admin/keys/batches` — List all batches
  - `GET /api/admin/keys/batch/<id>` — View batch details
  - `GET /api/admin/keys/batch/<id>/pdf` — Download as PDF

**Libraries:**
- `reportlab` or `fpdf2` for PDF generation
- `qrcode` for QR code generation

**Validation:**
- Admin-only endpoints (require platform_role='admin' or 'owner')
- Batch metadata tracking (created_by, created_at)

**Dependencies:** M37 (RegistrationKey model)
**Breaking Changes:** None
**Rollback:** Delete batch records and files

---

## M39: Registration Flow with Key Validation

**Goal:** New users register with a key; system validates and grants tier

**Scope:**
- New registration endpoint: `POST /api/auth/register-with-key`
  - Accepts: username, email, password, registration_key
  - Validates key:
    - Exists in DB
    - Not revoked
    - Not expired
    - Has uses_remaining > 0
    - Not already used (or uses_remaining > 1)
  - On success:
    - Create User with profile_tier from key.tier
    - Decrement key.uses_remaining
    - Set key.used_at = now()
    - Set key.used_by_id = new_user.id
    - Log audit event: 'user_registered_with_key'
    - Return JWT token + user info

- Registration form (frontend ready):
  - Key input field with validation feedback
  - Suggestion: "Enter your access code from the spellbook"

**Error Handling:**
- Key not found → 404 "Code not found in spellbook"
- Key revoked → 403 "This code has been sealed"
- Key expired → 403 "This code's power has faded"
- Key exhausted → 403 "No uses remaining"
- Key already used (max_uses=1) → 403 "This code has been consumed"

**Audit Logging:**
- `action: 'user_registered_with_key'`
- `details: {key_code: '...', tier: 'dm'}`

**Dependencies:** M37, M38
**Breaking Changes:** None (new endpoint, existing POST /api/auth/register unchanged)
**Rollback:** Delete registered users from this endpoint (audit trail remains)

---

## M40: Key Management Dashboard (Admin)

**Goal:** Admins can view, create, revoke, and track key usage

**Scope:**
- Admin endpoints:
  - `GET /api/admin/keys/stats` — Overall statistics
    - Total keys: 500
    - Used: 342 (68%)
    - Unused: 158
    - Revoked: 5
    - By tier breakdown

  - `GET /api/admin/keys?batch_id=<id>&status=used&page=1` — Paginated list
    - Filters: batch_id, status (used/unused/revoked), tier, created_after, used_after
    - Columns: key_code, key_name, tier, created_at, used_at, used_by (username), status

  - `POST /api/admin/keys/<key_id>/revoke` — Revoke a key
    - Sets is_revoked = true
    - Logs: 'key_revoked' with reason

  - `POST /api/admin/keys/<key_id>/unrestrict` — Grant one more use
    - Increments uses_remaining
    - Logs: 'key_uses_incremented'

  - `GET /api/admin/keys/<key_id>/user` — See who used this key
    - Returns user profile (anonymized if deleted)

**Frontend Dashboard:**
- Key batches list with creation date, total keys, usage %
- Filter by status (created, in-use, exhausted)
- Quick actions: View PDF, Revoke, Extend uses
- Export batch as CSV (for backup/audit)

**Validation:**
- Only platform_role='admin' or 'owner' can access
- Audit all key operations

**Dependencies:** M37, M38, M39
**Breaking Changes:** None
**Rollback:** Keep audit logs, key records remain

---

## M41: Session Management & State Machine

**Goal:** Complete control of game session lifecycle

**Scope:**
- Extend `GameSession` model with:
  - `session_state` (preparing, active, paused, ended) — state machine
  - `session_password` (optional GM can lock session)
  - `player_limit` (based on GM's tier, e.g., DM tier=6 players, Headmaster=8)
  - `current_players_count` (increment on join, decrement on leave)
  - `started_at`, `paused_at`, `ended_at`
  - `is_archived` (soft-delete for old sessions)

- State transitions:
  ```
  preparing  → active (GM starts session, validate all players connected)
  active     → paused (GM pauses)
  paused     → active (GM resumes)
  active     → ended (GM ends session, generates session report)
  [any]      → archived (after 30 days or manual archival)
  ```

- Session events (Socket.IO):
  - `session:state_changed` → broadcast state to all players
  - `session:player_joined` → notify all
  - `session:player_left` → notify all
  - `session:paused`, `session:resumed`, `session:ended`

- Endpoints:
  - `POST /api/sessions/<id>/start` — Transition to active
  - `POST /api/sessions/<id>/pause` — Transition to paused
  - `POST /api/sessions/<id>/resume` — Transition back to active
  - `POST /api/sessions/<id>/end` — Transition to ended, generate report
  - `POST /api/sessions/<id>/archive` — Mark as archived

- Validation:
  - Only GM can change state
  - Can't start if players not ready
  - Can't pause if already ended
  - Player count must be ≤ player_limit

**Audit Logging:**
- `action: 'session_state_changed'`
- `details: {old_state: 'preparing', new_state: 'active', player_count: 4}`

**Dependencies:** M17-M36 (existing GameSession)
**Breaking Changes:** Backward compatible (new fields, old sessions have defaults)
**Rollback:** Keep existing sessions, new fields revert to defaults

---

## M42: Multi-Layer Map System

**Goal:** Dungeons with floor 1, floor 2, overland map, etc.

**Scope:**
- New model `SessionMapLayer`:
  - `session_id` (FK)
  - `layer_name` ("Dungeon - Floor 1", "Overland Map", etc.)
  - `layer_order` (1, 2, 3 for stacking)
  - `asset_id` (FK to background image)
  - `width`, `height` (in grid squares)
  - `grid_size` (in pixels, e.g., 32px)
  - `is_visible` (toggle on/off for players)
  - `fog_of_war_enabled` (for M44)
  - `created_at`

- Endpoints:
  - `POST /api/sessions/<id>/map-layers` — Create layer
  - `GET /api/sessions/<id>/map-layers` — List all layers
  - `PATCH /api/sessions/<id>/map-layers/<layer_id>` — Update (name, order, visibility)
  - `DELETE /api/sessions/<id>/map-layers/<layer_id>` — Delete layer
  - `POST /api/sessions/<id>/map-layers/<layer_id>/set-active` — Make this the visible layer

- Socket.IO events:
  - `map:layer_added`
  - `map:layer_removed`
  - `map:layer_reordered`
  - `map:layer_visibility_changed`
  - `map:active_layer_changed`

- Validation:
  - Layer order must be contiguous (no gaps)
  - Can have max 10 layers per session
  - Only GM can modify layers
  - Asset must be image type (map)

**Audit Logging:**
- `action: 'map_layer_created'` / `'removed'` / `'reordered'`
- `details: {layer_name, layer_order}`

**Dependencies:** M19 (Asset model), M41 (Session state)
**Breaking Changes:** None (new model)
**Rollback:** Delete map layers table

---

## M43: Roll20-Oriented Session Workspace

**Goal:** Familiar play interface for D&D players (tokens, initiative, sheets)

**Scope:**
- New `SessionToken` model:
  - `session_id`, `layer_id` (which map layer)
  - `character_id` (if PC) or `name` (if NPC)
  - `x`, `y` (position on grid)
  - `size` (1x1, 2x2, etc., in squares)
  - `color` (border color for teams)
  - `is_visible_to_players` (fog of war)
  - `rotation` (0-360 degrees)

- Workspace UI layout:
  - **Left sidebar:** Campaign info, player list, quick actions
  - **Center:** Map canvas with grid, tokens (drag-and-drop)
  - **Right sidebar 1:** Initiative tracker (ordered list of tokens)
  - **Right sidebar 2:** Character sheets (read-only for players, editable for owning PC)
  - **Bottom:** Chat log & command input

- Token operations:
  - Drag to move token
  - Right-click for context menu (size, color, visibility, delete)
  - Click to select (highlight)
  - Shift+click to multi-select

- Initiative tracker:
  - `POST /api/sessions/<id>/initiative/add` — Add character
  - `POST /api/sessions/<id>/initiative/roll` — Roll initiative (d20 + DEX)
  - `GET /api/sessions/<id>/initiative` — Get sorted list
  - `POST /api/sessions/<id>/initiative/next-turn` — Advance to next
  - `PATCH /api/sessions/<id>/initiative/<entry_id>` — Edit initiative value

- Character sheets display (read from existing Character model):
  - Show current PC sheet for active character
  - Display AC, HP, spell slots, abilities
  - GM can see all sheets
  - Players see only their own

**Endpoints:**
  - `POST /api/sessions/<id>/tokens` — Create token
  - `PATCH /api/sessions/<id>/tokens/<token_id>` — Update position/size/visibility
  - `DELETE /api/sessions/<id>/tokens/<token_id>` — Remove token

**Socket.IO events:**
  - `token:moved` → broadcast new position
  - `token:created`, `token:deleted`
  - `initiative:updated`
  - `character_sheet:requested` → send to requesting player

**Validation:**
  - Tokens must be on visible layer
  - Position must be within map bounds
  - Only GM can move NPC tokens; players move their own PCs
  - Only owning player can see full character sheet

**Dependencies:** M41 (Session state), M42 (Map layers), Character model
**Breaking Changes:** None (new models & UI)
**Rollback:** Delete token & initiative tables

---

## M44: Session-Specific File Upload

**Goal:** Upload maps, tokens, handouts **during a session**

**Scope:**
- New feature: "Session Library" (separate from campaign assets)
- Extend Asset model with `session_id` (optional, nullable)
  - Assets can be campaign-wide OR session-specific
  - Session assets only visible during that session

- Upload endpoints (reuse M19-M22 with session_id):
  - `POST /api/sessions/<id>/assets/upload` — Upload to session
  - `GET /api/sessions/<id>/assets` — List session assets
  - `GET /api/sessions/<id>/assets/<type>` — Filter by type (map, token, handout)

- Use cases:
  - GM uploads new battle map mid-session
  - GM uploads monster tokens as encounter begins
  - GM shares handout (player notes) with group
  - Player uploads character portrait

- Validation:
  - Max 50MB per file (same as campaign)
  - Max 100 files per session
  - Only GM can upload maps & tokens
  - Players can upload handouts & character images
  - Session must be active to upload

- Audit:
  - `action: 'session_asset_uploaded'`
  - `details: {asset_type, filename, session_id}`

**Dependencies:** M19-M22 (Asset system), M41 (Session state)
**Breaking Changes:** Asset.session_id (nullable, backward compatible)
**Rollback:** Set all session_id to NULL, delete session assets

---

## M45: Real-Time Session Synchronization

**Goal:** All session changes instant broadcast via Socket.IO

**Scope:**
- Socket.IO rooms:
  - `session:${session_id}` — All participants in session
  - `session:${session_id}:gm` — GM-only channel (secret rolls, etc.)

- Event broadcasting:
  - **Map changes:**
    - `map:layer_changed` → {layer_id, layer_name}
    - `map:layer_visibility_changed` → {layer_id, is_visible}

  - **Token movement:**
    - `token:moved` → {token_id, x, y, moved_by}
    - `token:created` → {token_id, character, position}
    - `token:deleted` → {token_id}

  - **Initiative:**
    - `initiative:updated` → {entry_id, name, roll}
    - `initiative:turn_changed` → {current_index, character_name}

  - **Chat:**
    - `chat:message_sent` → {speaker, message, timestamp}
    - `chat:action_performed` → {character, action} (for rolls)

  - **Session state:**
    - `session:paused`, `session:resumed`, `session:ended`
    - `session:player_joined`, `session:player_left`

  - **Character sheets:**
    - `sheet:hp_updated` → {character_id, hp, max_hp} (if allows dynamic HP)
    - `sheet:spell_cast` → {character_id, spell_name} (logging)

- Consistency guarantee:
  - Each event includes a `sequence_number` (monotonic counter)
  - Clients can detect missed events
  - Fallback: resync on disconnect/reconnect

- Performance:
  - Batch updates every 100ms (debounce rapid token moves)
  - Compress token position to {tid: x, tid: y} format
  - Only broadcast to subscribed room

**Validation:**
  - Only authenticated users in session can receive events
  - GM channel only for verified GM
  - No events after session ends

**Dependencies:** M41-M44, Socket.IO infrastructure
**Breaking Changes:** None (new events, no API changes)
**Rollback:** Disable socket handlers, fall back to polling

---

## M46: Spellbook Theme & Book-Opening Animation

**Goal:** Make VTT feel like opening a magical spellbook

**Scope:**
- **Brand/Theme Foundation:**
  - Color palette: Deep purples, golds, blacks, mystical blues
  - Font: Serif for headings (like old grimoires), sans-serif for body
  - Icons: Spell-book themed (📖, ✨, 🔮, 📜)

- **Registration Flow Theme:**
  - Landing page: "Enter the Spellbook"
  - Key input field: "Speak the access incantation"
  - Success: "✨ The spellbook opens before you..."
  - Error messages: "🔒 This incantation is sealed" (locked key)

- **Book-Opening Animation (Concept):**
  - On successful login with key, show animation:
    - Book icon closes at top of screen
    - Book "opens" with page-turn effect
    - Reveals campaign/session selector underneath
    - Takes 2-3 seconds, then fades
  - CSS/JS: `animation-name: book-open; duration: 2.5s;`
  - Libraries: `GSAP` or vanilla CSS animations

- **Session Workspace Theme:**
  - Background: Parchment texture (subtle)
  - Map canvas: Bordered like a tome page
  - Buttons: "Cast" instead of "Send" for chat
  - Initiative tracker: "Spell order" or "Combat order"
  - Status: "Spellbook is open" (session active), "Sealed" (paused)

- **Key Distribution Design:**
  - PDF template: Parchment texture, gold borders
  - Keys formatted as: "✨ SPELL-ABCD-1234-XYZ9 ✨"
  - Batch title example: "Wizard's Circle - Spring 2026"
  - Instructions: "Guard these runes carefully"
  - QR code label: "Quick entry to the spellbook"

- **Configuration:**
  - Admin can customize:
    - Theme colors (primary, accent, text)
    - Font choices
    - Book animation speed
    - Key format (prefix, length)
  - Stored in `app_settings` table

**Assets to Create:**
  - Logo redesign (book-themed)
  - Book icon animation (SVG)
  - Background textures
  - CSS theme variables
  - PDF template (for key distribution)

**Dependencies:** M37-M45 (all previous work)
**Breaking Changes:** UI overhaul (but functional compatibility maintained)
**Rollback:** Revert CSS & theme config, keep all data intact

---

## Implementation Sequence

### **Phase 1: Foundation (M37-M40)** — Weeks 1-2
- M37: Key model (1 day)
- M38: Bulk generation + PDF (2 days)
- M39: Registration flow (1 day)
- M40: Admin dashboard (2 days)
- **Test:** 100-key batch, distribute PDF, register 5 users

### **Phase 2: Session Management (M41-M45)** — Weeks 2-3 (parallel with Phase 1 day 3+)
- M41: State machine (1 day)
- M42: Map layers (1 day)
- M43: Workspace UI layout (2 days)
- M44: Session assets (1 day)
- M45: Socket.IO sync (2 days)
- **Test:** Full session workflow (create → start → move tokens → end)

### **Phase 3: Polish (M46)** — Week 4
- Design & theming (2 days)
- Animation implementation (1 day)
- PDF template design (1 day)
- **Test:** Full user journey (key registration → book-open animation → session play)

---

## Success Criteria

### **M37-M40 (Keys System)**
- ✅ Generate 100 unique keys in batch
- ✅ Export batch as PDF with QR codes
- ✅ Register user with key (key consumed)
- ✅ Admin can view stats, revoke keys

### **M41-M45 (Sessions)**
- ✅ Start/pause/resume/end session with state validation
- ✅ Create multiple map layers, switch between them
- ✅ Place tokens on map, drag to move (real-time broadcast)
- ✅ Initiative tracker shows turn order
- ✅ Upload maps mid-session
- ✅ All players see same view in real-time

### **M46 (Theme)**
- ✅ Spellbook-themed UI applied
- ✅ Book-opening animation on login with key
- ✅ Key PDF distribution template created
- ✅ Theme customizable by admin

---

## MVP Scope

**In Scope:**
- User registration with keys
- Session management (state machine)
- Map layers
- Token placement & movement
- Initiative tracking
- Session-specific file uploads
- Real-time synchronization
- Spellbook theme foundation

**Out of Scope (Future):**
- Dice roller integration (roll20 API)
- Character sheet builder
- Spell database
- Advanced fog of war (line-of-sight)
- Dynamic lighting
- Video/audio chat integration
- Battle music system
- Advanced theming customization

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Key code collisions | Use UUID-based generation + validation |
| Socket.IO disconnect loses state | Resync on reconnect, sequence numbers |
| Too many map layers slows rendering | Limit to 10 layers, lazy-load assets |
| Players modify tokens they shouldn't | Enforce GM-only checks on server |
| PDF generation fails | Fallback to CSV export |
| Theme breaks existing functionality | Keep all business logic separate from theme |

---

## Database Schema Changes

**New Tables:**
- `registration_keys` — Key data
- `session_map_layers` — Map layers per session
- `session_tokens` — Token positions
- `session_initiative` — Initiative tracker
- `session_library_assets` — Session-specific files

**Schema Changes:**
- `game_sessions`: Add session_state, player_limit, started_at, ended_at, is_archived
- `assets`: Add session_id (nullable)
- `app_settings`: Add theme config (new table for M46)

**Migrations:**
- M37: registration_keys table
- M41: game_sessions state fields
- M42: session_map_layers table
- M43: session_tokens + session_initiative tables
- M44: assets.session_id field
- M46: app_settings table

---

## Deployment Considerations

- **Database backup before M37** (adding keys system)
- **Zero-downtime deployment:** All migrations backward-compatible
- **Feature flags:** Enable key system via config `REGISTRATION_KEY_ENABLED`
- **Rollback plan:** Each milestone has clear rollback (drop table/revert field)

---

## Next: Approval

**Ready to proceed with M37-M46 implementation?**

Decisions needed:
1. **Timeline:** 4 weeks aggressive, or 6 weeks relaxed?
2. **Theme direction:** Keep current or full redesign?
3. **Animation library:** GSAP (powerful) or vanilla CSS (lighter)?
4. **Key format:** "SPELL-XXXX-XXXX-XXXX" or simpler?

