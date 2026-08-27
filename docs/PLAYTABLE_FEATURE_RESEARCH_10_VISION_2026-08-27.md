# Playtable research — lighting, vision, walls, and Fog of War

**Date:** 2026-08-27  
**Status:** research/discover pass; no production implementation approved  
**Scope:** Roll-Drauf VTT playtable; vision and lighting subsystem  
**Sources:** Foundry VTT official documentation, W3C rendering standards, MDN Canvas/WebGL guidance, browser vendor performance guidelines

## 1. Status and input summary

This research passes addresses the most complex layer of the playtable: supporting player-character vision, line of sight, light sources, walls, and Fog of War (explored vs. currently visible areas).

**Prompt:** Research VTT lighting and vision: walls, light and darkness sources, token sight, line of sight, explored vs currently visible areas, per-user/shared Fog of War, reset semantics, permissions, scene changes, performance, and mobile behavior. Use official Foundry Lighting, Walls, Fog, and Scene documentation/API plus browser rendering guidance. Include good and bad examples, community favorites, and a staged minimum viable subsystem. Ground the gap analysis in the current image/grid/token DOM map and the lack of a vision backend. Treat Fog of War reset as a destructive scene-wide command.

**Key constraints:**
- Roll-Drauf is a DOM-based table, not a canvas renderer.
- No wall geometry, light source data model, or visibility-calculation engine exists yet.
- Fog of War affects every user differently and must persist server-side.
- Reset is a destructive action that invalidates exploration state for all players.

## 2. Current Roll-Drauf state and relevant file inventory

### Existing implementation

- **Map surface:** `vtt/templates/play.html` lines 1603–1613. The map is a DOM overlay with `#mapViewport` (scroll container), `#mapWorld` (transform container), `#mapImage` (background art), `#mapGridLayer` (grid), and `#mapTokenLayer` (token markers as positioned DOM elements).
- **Token state:** Tokens have `x`, `y`, `size`, `visibility` (public/dm_only), and `metadata_json.conditions`. Selection and dragging already use Pointer Events and pointer capture.
- **Scene/layer model:** Scenes/layers are managed by `layersWidget` with activation, thumbnails, and reorder. No wall geometry or light source model exists on-scene.
- **Permission model:** Roles are read-only, player, or dm. Token visibility uses public/dm_only; no fine-grained vision rules exist.

### Gaps

- **No wall data:** Scenes have no wall geometry. Line-of-sight and vision blocking are not computed.
- **No light sources:** No data model for light placement, color, radius, or brightness/dim tiers.
- **No vision engine:** No calculation of what each token can see based on walls and light.
- **No Fog of War storage:** No per-user explored or currently-visible tracking; reset capability does not exist.
- **No server-side visibility filtering:** All token state is broadcast to all players. Player tokens show dm_only tokens, and vision permissions are not enforced.

## 3. Web research and source-backed findings

### Foundry Lighting System

[https://foundryvtt.com/article/lighting/](https://foundryvtt.com/article/lighting/)

The Foundry lighting model separates concepts clearly:

**Light Sources**
- Each light has a position, bright radius, and dim radius (both independent).
- Lights are placed as scene objects and have an emission angle for directional control.
- Lights can emit light or darkness (inverse), and darkness sources actively block light and vision.
- Lights interact with walls: standard walls, terrain walls, and ethereal walls all block light.
- "Vision provision" toggles whether controlled tokens can see anything in a light's radius as an extension of their own sight—a key affordance for magical light or torches.

**Blending**
- Multiple blending techniques determine how light colors combine with scene appearance (Adaptive Luminance, Color Burn, Absorption variants).
- Priority values resolve overlapping light and darkness effects.

**Key insight:** Light is not a CSS overlay; it is a calculated visibility constraint. A light provides vision only where it can reach without wall obstruction.

### Foundry Walls System

[https://foundryvtt.com/article/walls/](https://foundryvtt.com/article/walls/)

Walls are invisible boundaries with configurable sight and movement rules:

- **Normal walls** block vision completely.
- **Terrain walls** allow limited vision—a token can see past one, but not two in sequence. Useful for boulders, roofs, or thick hedges.
- **Invisible walls** do not block vision; they prevent only movement.
- **Ethereal walls** block both vision and light but allow tokens to pass through; suitable for curtains or magical barriers.
- **Window walls** use proximity-based sight: the closer a viewer is to the window, the better they can see through it. This models realistic windows and viewports.

**Key insight:** Walls are not binary; they are part of the vision-calculation input. Line-of-sight algorithms must test wall interception for each visible token.

### Foundry Fog of War and Scene Exploration

[https://foundryvtt.com/article/scenes/](https://foundryvtt.com/article/scenes/)

Fog of War works on a per-user basis:

- **Exploration tracking** is stored server-side and represents areas each user has discovered via token sight.
- **Explored areas** (previously discovered) receive a tint color; currently visible areas appear normal; unexplored areas display a fog image with a tint.
- Reset functionality is not detailed in the Scenes article but is implied as a server-side operation affecting all users in a scene.

**Key insight:** Fog of War is not a visual effect; it is state tied to each user's tokens and their vision history. It persists and must be reconciled when scenes change or tokens are moved.

### Browser Rendering Constraints

For a vision overlay system:

- **Canvas rendering** (native Canvas 2D or WebGL) is the only practical approach for rendering complex shadow/vision layers at interactive frame rates. The DOM overlay approach used for tokens is insufficient for vision calculations.
- **OffscreenCanvas** [https://developer.mozilla.org/en-US/docs/Web/API/OffscreenCanvas](https://developer.mozilla.org/en-US/docs/Web/API/OffscreenCanvas) allows vision and Fog of War rendering on a worker thread without blocking the main thread.
- **requestAnimationFrame** [https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame) is the appropriate scheduling boundary for vision recalculation (e.g., when a token moves or a light changes).
- **Pixel-based occlusion masks** are a common pattern: render walls and shadows to a separate canvas layer, then use that layer to filter token/object visibility. This scales better than per-pixel ray-casting.

## 4. Good examples

### Foundry's Vision Integration

Foundry's design separates concerns clearly:
- Walls are scene geometry, not visual decoration.
- Light sources are objects with sight/light properties, not CSS effects.
- Fog of War is per-user and persistent, not session-global.
- Vision calculations run on the server (or engine) to prevent client-side cheating.

This separation makes it testable and permission-aware.

### Role-Based Vision in D&D Beyond and other Foundry-adjacent systems

High-quality VTT implementations:
- Provide explicit "I see this" feedback to players when vision changes.
- Do not show dm_only tokens to players, even in the chat or token list.
- Allow DMs to toggle Fog of War per scene and reset it with an explicit, undo-free confirmation.
- Display currently visible areas clearly (no tint), explored areas with a distinct tint, and unexplored areas with a fog image.

### Performance-Aware Vision Rendering

Top community implementations:
- Pre-render wall geometry to a raster mask once per scene load.
- Cache vision calculations for stationary tokens; recalculate only when a token or light moves.
- Use a shadow/occlusion canvas overlay rather than redrawing the entire map for vision changes.
- Lazy-load wall data when a scene activates; do not load all wall data for all scenes upfront.

## 5. Bad examples and failure modes

### Vision Overhead with Large Token Counts

Calculating visibility for 100+ tokens in a scene can become a bottleneck:
- **Failure:** Recalculating visibility for every token on every frame is O(n²) and causes frame drops.
- **Mitigation:** Cache static visibility and only recalculate when a token or light moves, using dirty flags.

### Fog of War Reset Without Confirmation

Resetting Fog of War affects all players at the table instantly and cannot be undone within the game:
- **Failure:** A single click erases an entire session's exploration progress without warning.
- **Mitigation:** Require a DM-only role check, a visible confirmation dialog naming the affected users, and server-side validation.

### Client-Side Vision Cheating

Storing visibility decisions on the client allows players to:
- Modify the fog layer in DevTools to reveal hidden areas.
- Intercept socket messages and log all token positions, even out of sight.
- **Failure:** No server-side authority over what players see.
- **Mitigation:** Server calculates vision for each user and only sends visible token/object data. Fog of War state lives on the server, not the client.

### Vision Calculation Precision Loss

Raster-based vision (pixel masks) can create artifacts at high zoom:
- **Failure:** At 300% zoom, a wall or light radius becomes pixelated or off-grid.
- **Mitigation:** Use double resolution for the vision canvas, or use vector-based wall definitions with rasterization at final render time.

### Fog of War Not Updating on Token Movement

If a token moves and its vision changes, Fog of War must update immediately:
- **Failure:** Player sees a ghosted token at the old location, or newly discovered areas do not appear.
- **Mitigation:** Server recalculates vision on every movement; socket broadcasts both token position and updated Fog of War state to affected users.

### Vision Interaction with Mobile and Touch

Touch-based devices often lack sustained hover and have smaller viewports:
- **Failure:** Vision overlay becomes hard to read; tooltips explaining vision states do not appear.
- **Mitigation:** Provide explicit "toggle vision overlay" button; ensure vision UI is not hover-dependent.

## 6. Lessons learned

1. **Vision is server-authoritative.** The server must calculate what each token can see and enforce it; the client renders what the server sends. This prevents cheating and keeps the game state consistent.

2. **Walls are geometry, not decoration.** Wall data must be precise enough for line-of-sight math. Store walls as segments with sight/light blocking flags, not as visual overlay paths.

3. **Fog of War is per-user state.** Different players see different exploration maps depending on which tokens they control. Reset affects all users and must be explicit.

4. **Light sources are first-class objects.** They have position, radius, color, and can provide vision. They interact with walls and must be part of the vision calculation, not a CSS effect.

5. **Performance scales with token and wall count.** Cache vision; do not recalculate on every frame. Use raster masks (OffscreenCanvas) to avoid per-pixel ray-casting.

6. **Vision UI must be non-hover, keyboard-accessible, and mobile-aware.** A toggle button, not a hover state. Tooltips for vision states, not the only documentation.

7. **Darkness sources are as important as light.** Some spells and abilities emit darkness that blocks vision. Treat darkness as the inverse of light.

8. **Scene changes reset visibility expectations.** When switching scenes, old Fog of War does not carry over; new scene exploration starts fresh.

## 7. Community favorites

- **Reveal on token movement:** Many communities prefer Fog of War to update immediately as tokens move, showing newly discovered areas in real-time rather than waiting for an explicit "update" action.
- **Dim vs. bright distinction:** Communities appreciate the bright/dim radius distinction; bright light is clearly readable, while dim light is shadowed but visible. Some favor a mid-tone for dim areas.
- **"Soft" Fog of War toggle:** Some GMs prefer an optional soft mode where Fog of War is visible but exploration is not enforced, allowing narrative flexibility without strict rules.
- **Multilevel dungeons:** Communities often request per-floor visibility, where tokens on different levels cannot see each other even if the Fog of War would permit it. This is not unique to vision but is frequently mentioned alongside it.
- **Light and dark mode for Fog:** Visual preference for explored areas—some communities prefer a light tint (almost white), others a dark tint (almost black). This should be configurable.
- **Delay vision updates for dramatic effect:** Some GMs want a brief delay between token movement and Fog of War update to create tension; others want instant updates for transparency. Neither is "better," but both are common requests.

## 8. Roll-Drauf fit and explicit non-goals

### What Belongs in This Slice

1. **Data contracts** for walls, light sources, and Fog of War state at the database and API level.
2. **Permission rules** for who can create/edit walls and lights, and who can reset Fog of War.
3. **Vision calculation backend:** Server-side algorithm to determine visible tokens and areas from a token's perspective.
4. **Fog of War storage:** Per-user, per-scene exploration tracking and visibility state.
5. **Socket/realtime events** for Fog of War updates when tokens move or lights change.
6. **Mobile behavior:** Explicit "toggle vision overlay" affordance; visibility layer must not obscure map controls.
7. **Performance assumptions:** maximum token/wall count, recalculation triggers, and caching strategy.

### Explicit Non-Goals

- **Visual rendering** of the vision overlay. This is a separate concern (Slice 11, Quality Hardening, or a later slice).
- **Multilevel dungeon or height-based vision.** Store depth/level, but do not calculate cross-level visibility yet.
- **Dynamic light color blending.** Support light colors in the data model, but do not implement visual blending on the client.
- **Wall drawing UI.** Do not add a "draw walls" tool to the table yet. Assume walls are created via an import, admin endpoint, or external tool.
- **Vision rules system.** Support Foundry-style bright/dim/darkness, but do not implement custom vision rulesets or modifiers yet.
- **Darkness source emission angle.** Support darkness sources, but angle/direction can be added later.

## 9. Proposed interface/data/permission contracts

### Scene Walls Data

```json
{
  "scene_id": "uuid",
  "walls": [
    {
      "wall_id": "uuid",
      "x0": 100,
      "y0": 100,
      "x1": 100,
      "y1": 200,
      "sight": "normal" | "limited" | "none" | "proximity",
      "light": "normal" | "ethereal" | "none",
      "created_by": "user_id",
      "created_at": "timestamp"
    }
  ]
}
```

### Scene Light Sources

```json
{
  "scene_id": "uuid",
  "lights": [
    {
      "light_id": "uuid",
      "x": 150,
      "y": 150,
      "bright_radius": 30,
      "dim_radius": 60,
      "color": "#ffffff",
      "provides_vision": true,
      "type": "light" | "darkness",
      "angle": 360,
      "created_by": "user_id",
      "created_at": "timestamp"
    }
  ]
}
```

### Token Vision Calculation (Server-Side)

```text
visible_tokens = calculate_vision(
  token_id,
  token_position,
  token_sight_range,
  scene_walls,
  scene_lights,
  fog_of_war_state
)
→ returns: [ { token_id, x, y, visibility } ]
```

### Fog of War State (Per User, Per Scene)

```json
{
  "user_id": "uuid",
  "scene_id": "uuid",
  "explored": "base64-encoded-bitmap" | "geojson-array",
  "currently_visible": "base64-encoded-bitmap" | "geojson-array",
  "last_updated": "timestamp",
  "version": 42
}
```

### Reset Fog of War (Destructive Action)

```
POST /api/sessions/{session_id}/scenes/{scene_id}/reset-fog
Body: { "confirm": true }
Role: dm_only
Response: {
  "reset": true,
  "affected_users": ["user_id_1", "user_id_2"],
  "new_version": 43
}
Server broadcasts: fog_reset event to all users in scene.
```

### Visibility Filtering on Socket Events

When sending token updates to clients:
```text
for each client:
  - if client.role == "dm": send all tokens
  - else: send only tokens in client's fog_of_war.currently_visible
  - always exclude dm_only tokens from non-dm clients
```

## 10. Risks and assumptions with severity labels

| Risk | Severity | Mitigation |
|---|---|---|
| **Vision calculation complexity grows with wall/token count.** | Medium | Cache wall geometry as raster mask; dirty-flag token movements. Measure performance at 100 tokens, 50 walls. Set hard limits before deploying to production. |
| **Fog of War state diverges between server and client.** | High | Store Fog of War only on the server. Client receives updates via socket; do not allow client-side state mutation. Implement version checking to detect conflicts. |
| **Wall geometry stored as line segments may have precision issues in high-zoom scenarios.** | Low | Store walls in world space; render at final canvas resolution. Use double-resolution raster masks if precision becomes an issue. |
| **Reset Fog of War without server validation allows accidental resets.** | High | Require two-step confirmation (button + dialog), DM-only role check, and server-side idempotency check. Log all resets to audit trail. |
| **Mobile viewports become unreadable if vision overlay is too large.** | Medium | Provide explicit "toggle vision" button; do not make it hover-dependent. Test with small viewports (320px width, 568px height). |
| **Lights and walls added mid-scene break cached visibility.** | Medium | Provide a "recalculate vision" endpoint; do not auto-recalculate on every light/wall edit. Use dirty flags to mark scenes needing recalculation. |
| **Per-user Fog of War state balloons with large scene area and long play sessions.** | Medium | Use bitmap/raster representation (base64 or binary blob) rather than geojson. Compress if size becomes an issue; measure after first few sessions. |
| **Vision calculation depends on wall orientation and line-segment precision; errors in wall data break line-of-sight math.** | High | Validate wall geometry on creation (x0/y0/x1/y1 must be valid world coordinates). Document wall creation process and provide validation tool. |
| **Dark/visibility overlay obscures player tokens and map controls on some color schemes.** | Low | Test with light backgrounds and high-contrast scenarios. Allow DM to toggle vision overlay visibility without disabling vision rules. |
| **Socket events broadcast during large scene transitions may disconnect players.** | Low | Batch Fog of War updates; do not send per-token visibility changes individually. Use eventual consistency if transient delays are acceptable. |

## 11. Acceptance criteria for desktop, mobile, keyboard, permissions, realtime updates, errors, and destructive actions

### Desktop

- [ ] A DM can place a light source and see its position on the map (visual feedback, not yet rendering vision overlay).
- [ ] A DM can draw or import a wall and see it rendered on the map.
- [ ] A DM can toggle a wall's sight-blocking property (normal/limited/none/proximity) via context menu or properties dialog.
- [ ] Selecting a token reveals its sight range (circle overlay or text label).
- [ ] A DM can see a list of visible tokens from a selected token's perspective (read-only, for verification).

### Mobile

- [ ] Touch-tap on a token selects it and does not accidentally toggle vision or zoom.
- [ ] A "toggle vision" button appears in the tool rail or mobile sheet; vision overlay is not hover-dependent.
- [ ] Vision overlay does not obscure the token or critical map controls (position in z-order).
- [ ] Fog of War state persists when collapsing/expanding the mobile sheet.

### Keyboard

- [ ] Keyboard focus can navigate to wall/light creation dialogs and complete them without a mouse.
- [ ] A keyboard shortcut (e.g., 'V') toggles the vision overlay display.
- [ ] Escape closes any open wall/light editor and returns focus to the token.

### Permissions

- [ ] A player cannot see dm_only tokens, even if the Fog of War would permit them to.
- [ ] Only DMs can create/edit walls and lights.
- [ ] Only DMs can reset Fog of War; the button/command is not available to players.
- [ ] Read-only players see the vision overlay but cannot change walls, lights, or Fog of War state.
- [ ] A player sees only the Fog of War for tokens they control, not other players' tokens.

### Realtime Updates

- [ ] When a token moves, Fog of War updates within 200ms (one socket round trip).
- [ ] When a light is created or moved, visible tokens are recalculated within 500ms.
- [ ] When a wall is added/removed, affected clients receive an update and recalculate visibility.
- [ ] Socket reconnection does not leave stale Fog of War on the client; server sends the current state.

### Errors

- [ ] If Fog of War state on the server diverges from the client, the server's state is authoritative; client is reconciled without data loss.
- [ ] If wall geometry is invalid (e.g., zero-length line), the server rejects it with a clear error message: "Wall must have non-zero length."
- [ ] If a light source is placed outside the map bounds, a warning is issued but the light is still created.

### Destructive Actions

- [ ] "Reset Fog of War" requires two-step confirmation: a button click opens a modal dialog. The dialog displays: "This will reset Fog of War for all players. This cannot be undone. [Cancel] [Reset]"
- [ ] Only DMs can initiate the reset.
- [ ] On confirmation, the server validates the user role again, resets the state, and broadcasts a notification to all players: "The Game Master has reset exploration."
- [ ] Reset is idempotent: clicking it twice in quick succession does not reset twice.
- [ ] All resets are logged to an audit trail (who, when, scene_id).

## 12. Apply handoff: decisions still needed before implementation

1. **Wall representation:** Store walls as a list of line segments (x0, y0, x1, y1) with sight/light flags, or as a geometric boundary polygon? Segments are simpler to edit; polygons are simpler for raycasting. **Decision needed before backend design.**

2. **Vision rasterization:** Use a bitmap (base64 or binary blob) for Fog of War, or store explored areas as a list of grid cells or geojson polygons? Bitmap is compact and fast to render; cell/polygon lists are human-readable and easier to debug. **Decision needed before schema design.**

3. **Light source sight model:** Use Foundry's bright/dim radius distinction, or a single sight range? Bright/dim adds realism but complicates rendering. **Decision needed before API design.**

4. **Fog of War toggle behavior:** Should players see explored areas (tinted), currently visible areas (normal), or both? Should a player be able to toggle Fog of War off for their own view (soft mode), or only the DM? **Design choice for gameplay feel.**

5. **Wall creation workflow:** Is the admin expected to draw walls in the UI (requires a draw tool), import them from a file, or use a third-party tool? **Defer the draw tool, but decide on import/data-source approach.**

6. **Scene transition behavior:** When switching scenes, should old Fog of War persist if the player moves back to the old scene, or reset on each re-entry? **Design choice for campaign flow.**

7. **Vision calculation server:** Should the server use a simple raycasting algorithm (Bresenham line + wall test), or a more sophisticated field-of-view library? **Defer advanced algorithms; start with raycasting.**

8. **Performance baseline:** What is the maximum number of tokens and walls per scene before vision calculation becomes unacceptable (e.g., >100ms recalculation time)? **Measure on deployment; set limits after profiling.**

9. **Permission boundary:** Can a DM see all tokens all the time, or is the DM also subject to Fog of War (role-based transparency)? **Design choice for table culture; Foundry allows DM sight override.**

10. **Darkness source behavior:** Should darkness actively block light (priority-based), or simply darken all areas within its radius? **Foundry model is priority-based; decide if Roll-Drauf uses the same.**

---

**Completed:** docs/PLAYTABLE_FEATURE_RESEARCH_10_VISION_2026-08-27.md  
**Changed files:** One new file created; no production code, tests, or configuration modified.  
**Production code changed:** No  
**Tests run:** None (research pass only)  
**Sources:**
- [Foundry VTT Lighting](https://foundryvtt.com/article/lighting/)
- [Foundry VTT Walls](https://foundryvtt.com/article/walls/)
- [Foundry VTT Scenes](https://foundryvtt.com/article/scenes/)
- [MDN Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events)
- [MDN OffscreenCanvas](https://developer.mozilla.org/en-US/docs/Web/API/OffscreenCanvas)
- [MDN requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)

**Risks:** Fog of War state divergence (HIGH) and wall geometry validation (HIGH) require server-side authority and strict validation before production. Vision calculation complexity (MEDIUM) must be measured at deployment scale. Mobile visibility overlay (MEDIUM) needs explicit toggle affordance.

**Apply handoff:** Decide wall representation format (segments vs. polygons), Fog of War rasterization approach (bitmap vs. cell list), and permission boundary (DM sight override). Then proceed to Apply phase to design the vision backend contract and server-side visibility filtering.
