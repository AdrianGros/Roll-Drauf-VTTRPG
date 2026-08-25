# Agent-Report 3/4 — Code-Analyse /campaigns, Join, Doppel-Markup (D01–D13) (2026-08-25)

(Voller Report des Code-Agenten, read-only; Synthese in docs/FIX_RESEARCH_DESKTOP_AUDIT_2026-08-25.md §1–§4, §6.)

## 1. How /campaigns is actually rendered (two engines, one DOM)

### Serving
- **No explicit Flask route for page templates.** Catch-all `serve_static` at `vtt/__init__.py:287-315` serves any file in `vtt/templates/` by name, extensionless included (`/campaigns` → `campaigns.html`, :306-310). Consequence for D05: **lobby.html is technically reachable** at `/lobby` and `/lobby.html` — "keine Route" is true for explicit routes, but the template is served; it is **unlinked** (no navigation points to it).

### Mode switch (book vs. legacy)
- `bootstrapCampaignsScene` — `campaigns.html:1498-1521`: `?campaign_id=…` or `?classic=1` → removes `campaigns-route-book-scene` from body, runs legacy `loadCampaigns()` (:1500-1507); otherwise `BookScene.bootstrapProtectedRoute({routeKey:'campaigns'})` (:1515-1520).
- The body class only HIDES the legacy page: `campaigns.html:1297-1301` (`body.campaigns-route-book-scene > header, > main, > footer { display:none }`). **Full legacy markup (tab bar, cards, hub) stays in the DOM on every book-mode load.**

### The visible book render
- `book-scene.js`: `bootstrapProtectedRoute` (:1787) → `loadSceneSnapshot` (:1589-1615; GET /api/campaigns + /api/characters/mine) → `renderSceneRoute` → `buildRouteMarkup` (:1174) → `buildCampaignsMarkup` (:991-1082). Injected into `#book-dashboard-scene` (create() :214-251), prepended to body over the hidden legacy main.
- **"Meine Kampagnen" list:** `buildCampaignLedger` (:684-721), invoked at :1028. Each `.book-scene-ledger-item` (:703-717) = plain divs + ONE button "Hub öffnen"/"Hub und Vorbereitung" with `data-dashboard-href="/campaigns?campaign_id=<id>&classic=1"` (:710-716).
- **Dead click (D02):** `bindSceneNavigation` (:1184-1237) wires only `[data-dashboard-route]`, `[data-dashboard-href]`, `[data-dashboard-section]`, `[data-dashboard-action]`. The ledger row carries none — only the inner button does.
- **"Kampagnen-Hub öffnen" (D03):** :1022-1026 → `/campaigns?campaign_id=<campaigns[0].id>&classic=1` (or just `classic=1` with zero campaigns); handler does hard `window.location.href` (:1199-1207) → full reload → legacy branch. `classic=1` appears at :692, 713, 758, 762, 775, 779, 1018, 1024-1025, 1039, 1044….
- **No join affordance in the book render (D01):** "Einladungen" is a decorative non-interactive div (:1063-1066).

### The legacy view (classic=1 / campaign_id)
- Legacy header nav with **"Cockpit"**: `campaigns.html:1327` (D10; book ribbon comes from `buildRibbon` via `buildPageShell`, book-scene.js:903-907).
- Tab bar :1423-1427 (Meine/Beigetreten/Alle; `switchTab` :1690-1708).
- Cards with **"Beitreten"** for non-members: `renderCampaigns` :1710-1752, button at :1725. `joinCampaign` :1812-1826 — `window.prompt` then POST accept-invite.
- Second hidden join affordance (D04): "Einladung eingeben" for non-managers at :3058.
- Invite creation (D06): `invitePlayer` :3892-3911 — token via `window.prompt("Code zum Teilen:", …)` at **:3906**.

### Duplicate-ID / hidden-markup surface (D09)
- Literal duplicate ID inside campaigns.html: only `campaignSessionPrepSurface` (:2450, :2528) — mutually exclusive branches (early return :2448), never both live.
- Real mechanism = dashboard crawler class: in book mode the served DOM contains hidden legacy `#campaignCreateToggle` (:1365), `#campaignCreateName` (:1392), `#campaignCreateForm` (:1388), `#messageBox` (:1374), `#campaignsGrid` (:1455), `#campaignDetail` (:1461), tab bar — while the visible book render is **ID-free**. `getElementById` always resolves to the invisible copy.
- Note: signup/register/character-sheet use inert `<template id="…SceneTemplate">` (signup.html:16, register.html:16, character-sheet.html:713) — template content doesn't collide. **campaigns/characters/dashboard are the pages keeping live hidden markup.**
- Doubled hub buttons (D11): `hub-primary-actions` (:3122-3127) — `primaryAction.action` can be a primary "Spieler einladen" (getSessionPrepAction :2166-2170, fresh-campaign state) and :3124 unconditionally adds a secondary "Spieler einladen" for managers → stacked duplicates. `focusInviteControls()` targets recur at :2571, :2169, :2783.

## 2. Invite backend (vtt/campaigns/routes.py)

- Token model `vtt/models/invite_token.py:9-39`: `secrets.token_urlsafe(32)`, **globally unique + indexed** (:16, :31-34) → token alone identifies the campaign. **Single-use** (`used_at`, routes.py:662; `is_valid()` :36-39). **Expiry 7 days** (:22). **User-bound** (`invited_user_email` :18; accept rejects mismatch, routes.py:652-653).
- `POST /api/campaigns/<id>/invite` — routes.py:541-614: DM-only (`_is_dm` :554-555, 403 `{"error":"forbidden"}`); requires existing username (:562-564, 404); creates/reactivates CampaignMember `status="invited"` (:566-591); returns invite_token/campaign_id/expires_at (:607-614).
- `POST /api/campaigns/<id>/accept-invite` — routes.py:617-670: JWT login, token for campaign (:635-637), `is_valid()` (:638-639), member row in `invited` for current user (:641-650; none → 403 "no invitation found"), email match (:652-653), capacity (:655-656). Flips to `active`, stamps `used_at`.
- **Deep-link feasibility: cheap.** `GET /invite/<token>` resolves token → campaign_id, reuses accept logic. Only backend work: one small login-aware route (`next=` redirect). **Caveat:** invite is username-bound at creation — the link works only for the invited account. An "open share link" (any logged-in user) requires relaxing `invited_user_email` and creating the member row at accept — a deliberate model change (Adrian).

### The 403/"forbidden" chain (D07/D08)
1. GET /api/campaigns lists ALL public campaigns (routes.py:308-321); "invited" ≠ member (serializer counts only `status=="active"`, :53-82) → `is_member:false`.
2. Player clicks Hub öffnen → `/campaigns?campaign_id=<id>&classic=1`.
3. Legacy `loadCampaigns` → `viewCampaign` (campaigns.html:1672-1675) → GET /api/campaigns/<id> (:3832).
4. `_is_active_member` false (routes.py:107-116) → 403 `{"error":"forbidden"}` (:388-389).
5. `Auth.makeAuthRequest` throws `new Error(error.error || …)` (auth.js:139-140) — raw string "forbidden".
6. `viewCampaign` catch → `showMessage(error.message, true)` (:3838-3840) → red banner `#messageBox` (:1523-1531/:1374).
Not a background poll — **the only navigation the book page offers the player is aimed at a guaranteed 403.**

## 3. lobby.html — routed-in-practice, linked-nowhere

- Reachable via catch-all; `book-routes.js:98-113` even has `/lobby` metadata; **zero inbound links**.
- Unique: the only built token-entry form (`#campaignId` + `#inviteToken`, :58-65; `joinByInvite()` :188-212). Everything else worse duplicates: create via three `window.prompt`s (:164-186), list from /api/campaigns/mine (:134-162), delete via confirm (:214-226). Third render style (book-shell legacy adapter, book-shell.js:4), English strings, requires numeric campaign ID.
- **Assessment: delete with B3 teardown after the join affordance lands**; routing it would add a fourth live copy. Its one good idea (token form in book styling) moves into /campaigns.

## 4. Fix options per cluster

(✔B3 = aligns with one-render-engine phase; §13 = data-testid + contract per touched element.)

### Cluster A — join hole (D01–D04, D06)
- **A1 (M, empfohlen):** Invite-Deep-Link `GET /invite/<token>` (login-aware, `next=`, POST-accept, land on `/campaigns?campaign_id=<id>`) + copy-link block replacing prompt at :3906 in the invite controls (:3048-3052). Kills paste-a-code; token model already safe. B3-neutral. Doesn't fix the dead row alone.
- **A2 (M, empfohlen dazu):** Join affordance in `buildCampaignLedger` for `is_member:false` (button + inline token field, wired via bindSceneNavigation; reuse accept call shape from :1817); row itself becomes click target (kills D02). ✔B3. Still token-paste unless with A1.
- A3 (S, abgeraten): point book buttons at the legacy "Alle" tab directly — invests in markup B3 demolishes, keeps prompt.
- **Empfehlung: A1+A2**; §10 first: fullsession UI-invite phase.

### Cluster B — forbidden banner (D07, D08)
- **B1 (S, empfohlen):** don't fire the doomed call — client knows `is_member`; hub-href only for members (book-scene.js:1022-1026); guard `viewCampaign(queryCampaignId)` (campaigns.html:1672-1675) with membership check + proper German state.
- **B2 (S, empfohlen dazu):** map known API error codes to German at the seam (auth.js:139-140) — helps every raw-error banner app-wide.
- B3-opt (M): distinct 403 payload `{"error":"not_a_member"}` — overkill, client already has is_member.

### Cluster C — doubled markup / navs / buttons (D09–D11)
- **C1 (L, = B3 phase, empfohlen als Ziel):** BookScene sole renderer; move create-form/tabs/roster/hub into scene builders or inert `<template>`s (proven pattern signup.html:16 / book-scene.js:533-538); strip legacy body (:1324-1480); retire `classic=1` (hub = book route with campaign_id); testids + contracts everywhere. D09/D10 die by construction; Cockpit header (:1327) disappears. Sequencing: contracts first, then consolidate.
- **C2 (S, jetzt, empfohlen):** suppress unconditional "Spieler einladen" at :3124 when primaryAction is already invite (:2166-2170 guard); unique-ify `campaignSessionPrepSurface`; add data-testid to VISIBLE book elements (survive C1).
- C3 (M, abgeraten): server-side template split book/classic — codifies two variants, sideways move.

### Cluster D — lobby.html (D05)
- **D1 (S, empfohlen):** delete file + `/lobby` entries in book-routes.js:98-113 after A1/A2. Catch-all ⇒ deletion is the only true un-route. Adrian decision per Hausregel.
- D2 (S): route it as interim join screen — every argument in §3 says no; only as ≤1-sprint stopgap with deletion date.

### Cluster E — language (D12, D13)
- **E1 (S, empfohlen):** one sweep over §5 list; files are UTF-8 ("prüfen" appears correctly at :3200 — authoring slip, not encoding); do BEFORE arming the R4 rendered-text scan so the ratchet starts green.
- E2 (M): strings as `page_content` catalog data (content_defaults.py, book-scene.js content() :1243-1267) — only for strings surviving C1.

## 5. Concrete language list (visible render paths)

Umlaut substitutes — campaigns.html: :1860 `Map Prep pruefen` · :3125 `Sessions pruefen` · :3232 `Kartenstand pruefen` · :3410 `unveraendert` + `geprueft`.

English chrome strings — campaigns.html: :1327 `Cockpit` · :1342/:1344 `Chronicles` · :1348 `Campaign Atlas` · :1349 `<h1>Campaigns</h1>` · :1350-1352 English paragraph · :1356 `Roster + Detail` · :1357 `Wave 1 Ready` · :1465 `Refresh` · :1479 English footer · :2500 `Unknown` fallback · :2561 `Map Prep` · :2202/:2625/:2812/:3233 `Map Prep ansehen` · :2568 `Participants / Invite Context` · :2571 `Invite-Kontext` · :2644/:3236/:3238/:3406 `Asset Library` · :3082 `Launch-Status` · :3090 `Campaign Prep / Session Hub` · :3107-3110 badges (`Campaign Prep`, `Prep Headquarters`, `Session Flow`, `Map + Assets`) · :3134 `Prep Overview` · :3255 `Hub Flow` · :3476/:3512 `Preview` · :3529 `Download`.
lobby.html (moot under D1): :19 `Loading...` · :165/:170/:171 English prompts · :181 `Campaign #… created` · :194/:199 English validation · :207 `Joined campaign.` · :215 `Delete this campaign?` · :222 `Campaign deleted.`

## 6. Suggested sequencing
1. Robot net: fullsession UI-invite phase (D25) + contracts/campaigns.json skeleton with "Eintrag → Hub" (D02).
2. B1+B2 (S). 3. A1+A2 (M). 4. C2 (S). 5. D1 (S, Adrian). 6. E1 (S) then arm R4 scan. 7. C1 (L, = B3 for /campaigns).
