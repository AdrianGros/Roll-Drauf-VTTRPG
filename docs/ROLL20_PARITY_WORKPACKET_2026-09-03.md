# Roll20 parity work packet

**Phase:** Apply
**Status:** in progress
**Scope:** Five feature gaps closed against Roll20, chosen and specced with
Adrian directly (grilling session, 2026-09-02/03), following the same
Discover → Apply → Deploy shape this repo's own `AGENTS.md` prescribes.

## Context

A DM-secrecy audit (2026-09-02) found and fixed four visibility leaks
(walls/lights geometry, secret-roll chat history, a legacy unfiltered
token-state endpoint, unrevealed handouts — see the four commits landed
that day). The same audit produced a feature census against Roll20; this
doc is the Apply-phase design for closing the gaps that census found.

**The actual goal, stated plainly (Adrian, 2026-09-02/03, correcting an
assumption I'd made):** this VTT is meant to **compete with Roll20**, not
just be good enough for one friend group. Full Roll20 parity is the
near-term bar. Compendium/monster stat blocks and macro/scripting are
explicitly **deferred** — both are large, architecture-defining efforts
(a licensed-content or homebrew-authoring decision for the former, a
security-sandbox decision for the latter) that don't belong in this pass.
Once parity is reached, the plan shifts to improving/redesigning beyond
what Roll20 does.

The product is **pre-launch**. No real playtest data exists yet to
prioritize by felt pain — this is being built toward a first real
session, not reacting to one. Frequent changes are expected.

## Scope: five gaps, in build order

Build order chosen for shared infrastructure, not raw priority: fog
rendering, AOE templates, and freehand drawing all reuse the same
SVG-overlay/grid-cell approach already proven by the existing wall/light
marker layer (`vtt/static/js/play-ui.js`'s `visionLayer`), so building
them in this order makes each next one cheaper. Whispers and audio are
independent and can land in either order relative to the rest.

### 1. Visual fog-of-war rendering — ✅ DONE (2026-09-03)

Client-only change: `_fogCellMarkup()`/`_renderVisionLayer()` in
`vtt/static/js/play-ui.js` paint per-grid-cell `<rect>`s into the existing
`#visionLayer` SVG, gated to non-operator roles. Also wired `this.api.
getFog()` (existed since S10, never called) into `_loadVisionGeometry`'s
non-operator branch so fog is correct on first paint, not just after the
first live `fog:updated` event, and made `fog:updated` actually trigger a
re-render (it previously only stored the payload). No backend changes —
full test suite (565) green, unaffected by this slice.

**No design decision needed** — the backend already implements Roll20's
own semantics exactly: `vtt/play/vision.py` (`calculate_visible_cells`,
real raycasting against `SceneWall`/`SceneLight`) and
`vtt/models/fog_of_war_state.py` (`explored_cells` cumulative/never
shrinks, `visible_cells` this-tick snapshot, per-`(user_id,
campaign_map_id)`) already match "explored areas stay revealed, currently
visible areas are un-tinted, unexplored areas are hidden" per-user. The
client receives this data over the `fog:updated` socket event and even
stores it (`play-ui.js:467`, `this._fog`) but never paints it — explicit
comment there: "There is NO fog-of-war mask/shadow rendering in this
slice."

**Target state:** the existing `visionLayer` SVG overlay (already used for
wall/light markers) gains a fog mask: unexplored cells solid-hidden,
explored-but-not-currently-visible cells tinted, currently-visible cells
untinted. Grid-cell rects, not a raster/canvas approach — `fog_of_war_
state.py`'s own cells are grid coordinates, not pixels, so this is a
rect-per-cell draw, not image compositing.

**Interfaces:** none new. Reads the fog payload the client already
receives and stores.

**Acceptance:** a Player's own view shows fog correctly reflecting their
`explored_cells`/`visible_cells`; the DM's own view is unaffected (DM
already sees everything per the vision leak fix). Fog updates live on
token move via the existing `fog:updated` event, no new round trip
needed.

### 2. AOE templates

**Shapes:** all four of Roll20's — circle, cone, line/ray, square (cube).

**Persistence:** templates persist on the map once placed (matches real
Roll20 behavior — they stay until removed), not a single-use/ephemeral
cast effect. DM gets an easy clear/delete action (single template and
"clear all" for the active map).

**Target state:** a new `SceneTemplate` model (mirrors `SceneWall`/
`SceneLight`'s own shape: `campaign_map_id`, `shape` enum, origin point,
size/length, rotation, `created_by`), CRUD REST routes mirroring
`vtt/play/routes.py`'s wall/light routes (DM/CO-DM write, and — per the
vision-leak fix precedent — DM/CO-DM-only read too, since template
placement previews DM intent before a spell resolves; open question for
implementation time, not a blocker: whether resolved/triggered templates
should become player-visible). Socket events `template:create`/`template:
update`/`template:delete` mirroring `token:*`'s pattern. Client tool
mirrors the existing wall-placement click-to-place UX
(`play-ui.js`'s `toolWall` handler) for line/cone (two-click: origin +
direction/length) and a single-click + drag-radius for circle/square.

**Interfaces:** `SceneTemplate.serialize()` → `{id, campaign_map_id,
shape, origin_x, origin_y, length, width_or_angle, rotation,
created_by}`. Shares `SHAPE_PREVIEW_PARAMS`-style registry pattern with
`vtt/brawl` sibling project's own `AbilityShape` if useful precedent, but
implemented locally — no cross-project dependency.

**Acceptance:** DM can place all 4 shapes, they persist and reappear on
reload, DM can delete individually or clear the map, all connected
clients see placement in real time.

### 3. Freehand drawing, per-player layers

**Who can draw:** both DM and Players (not DM-only).

**Layer model:** every user (DM included) gets their **own** personal
drawing layer, private by default. A per-user checkbox toggles whether
their layer is shared into the view **other players** see. The **DM
always sees every layer unconditionally**, regardless of any player's
checkbox — this matches every other secrecy boundary already in this
codebase (hidden tokens, walls/lights, handouts, secret rolls: operator
role always bypasses). The checkbox is a player↔player visibility
control only, never a control over DM visibility.

**Target state:** a new `SceneDrawing` model (`campaign_map_id`,
`owner_user_id`, `path_data` — an SVG path `d` string or point array,
`is_shared` boolean, `created_by`). Pointer-capture stroke tool on the
client (genuinely new interaction code — unlike wall/template placement,
this is continuous pointermove capture, not click-based; needs move-event
throttling and path simplification for performance, per the existing
vision-research doc's own performance guidance). Read filtering: a
non-owner, non-operator viewer only receives `SceneDrawing` rows where
`is_shared = true` OR `owner_user_id == viewer_id` — same shape as
`is_token_visible_to` in `vtt/play/service.py`.

**Interfaces:** `PATCH /scenes/.../drawings/<id>` to toggle `is_shared`.
Socket event `drawing:created`/`drawing:updated`(share toggle)/`drawing:
deleted`, role/owner-filtered at emit time like `_emit_token_event`
already does for tokens.

**Acceptance:** a Player's own strokes are visible only to them until they
toggle share; once shared, other Players (not just DM) see them; DM sees
every stroke from every user regardless of share state, at all times.

### 4. Whispers

**Direction:** both DM→Player and Player→Player, not DM-only. Roll20's
own `/w` works between any two members.

**Target state:** extend `ChatMessage` with a `recipient_user_id` column
(nullable — null means public/broadcast, as today). Reuse `user_room()`
(`vtt/utils/realtime.py:39-41`, already exists purely for single-user
targeting) for delivery: a whisper emits to the sender's own room and the
recipient's room only, never the session-wide room. Reuses the exact
"never trust a client-supplied secrecy claim" enforcement pattern
`ChatMessage.visibility` already established for dice rolls
(`vtt/socket_handlers.py`'s `handle_roll_dice`) — the server, not the
client, decides who a whisper reaches.

**Interfaces:** `handle_chat_message` (`socket_handlers.py:1319+`) gains
an optional `recipient_user_id` in its payload; validates the recipient
is an active member of the same campaign before sending. History reads
(`bootstrap_play_runtime`'s chat_history, `list_chat_messages`) must
apply the same recipient filter the visibility fix (2026-09-02) just
added for `gm_only`/`blind`/`self` — a whisper history row is visible
only to its sender and its recipient (DM included only if DM is sender or
recipient, not unconditionally — a whisper is a whisper, this is the one
secrecy mechanism in this app that is NOT DM-omniscient by design, since
real Roll20 whispers are genuinely private between the two parties).

**Acceptance:** a whisper reaches only sender+recipient live; history
reads for a third party (including the DM, if not party to it) never
show its content; a public message is completely unaffected.

### 5. Shared table audio

**Scope:** a single DM/CO-DM-controlled track for the whole table — Roll20's
actual baseline jukebox, not their later playlist/crossfade tier.
Playlists are explicitly a later layer once basic sync is proven, not
part of this pass.

**Uploads:** DM/CO-DM-uploaded files only, via the existing asset
pipeline. No licensing/marketplace angle.

**Target state:** add audio MIME types to `vtt/upload_security.py`'s
`ALLOWED_MIME_TYPES` (a new `asset_type` value, e.g. `audio`, alongside
map/token/handout/image). A `SessionAudioState` model or a few columns on
`SessionState` (`current_track_asset_id`, `is_playing`, `started_at_
server_time`, `volume`) — playback position derives from `started_at_
server_time` rather than being pushed every tick, so clients that join
late or reconnect compute their own correct seek position instead of
needing a continuous sync stream (this is a genuinely new problem class
for this codebase — existing events are one-shot state mutations, not
continuous media sync). Socket events `audio:play`/`audio:pause`/`audio:
change_track`/`audio:volume`, DM/CO-DM-only to emit, broadcast to the
whole session room.

**Interfaces:** client `<audio>` element driven by the derived seek
position on join/reconnect and by the four socket events thereafter.

**Acceptance:** DM starts a track, all connected clients hear
approximately the same moment (not sample-accurate — "everyone's roughly
in sync" is the real bar, not broadcast-grade sync); a client joining
mid-track starts at the correct elapsed position, not from zero.

## Deferred (explicitly out of scope for this pass)

- **Compendium / monster stat blocks / spell lookup** — needs a licensed-
  SRD-content-vs-homebrew-authoring decision before any code gets
  written; that's a content/legal call, not an engineering one.
- **Macros / custom scripting** — needs a security-sandbox decision
  before implementation (arbitrary user-authored logic is a real RCE
  surface on a shared multiplayer server); scope is undefined until that
  decision is made.

## How this gets used

Each of the five sections above is its own Deploy-phase slice — tested,
committed, and (pending Adrian's own deploy confirmation per slice, same
as the 2026-09-02 leak fixes) shipped independently, not batched into one
giant change. This doc is the standing reference for the whole packet
across however many sessions it takes; update it in place as sections
land rather than leaving it to drift the way the Definition-of-Finished-
style docs in the Goblin Delve project do when a fix outpaces its own
doc.
