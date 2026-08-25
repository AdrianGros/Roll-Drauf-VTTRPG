# Agent-Report 1/4 — Invite-Flow-Patterns (Web-Recherche, 2026-08-25)

(Voller Report des Research-Agenten; Synthese in docs/FIX_RESEARCH_DESKTOP_AUDIT_2026-08-25.md §1.)

## Part 1 — How comparable products do it

### Roll20
- **Mechanism:** Link-first. The "Invite Players" dialog offers (a) email invites with an "Invite as Player/GM" role dropdown and (b) a **Player Join Link** to copy/share.
- **Expiry/revocation:** Player Join Link is **multi-use, unlimited**, but **rotates automatically whenever a player is kicked** — kicking doubles as revocation of the old link. **GM Invite Links are single-use and expire after 48 h** (higher privilege → tighter token).
- **Role on join:** Chosen at invite time (Player vs GM); separate link type per role.
- **Logged-out recipients:** The link lands on Roll20; account creation/login required, then the game is added (help center has a whole "Game Invite Troubleshooting" page because of this step).
- Sources: https://help.roll20.net/hc/en-us/articles/29620515876375-Invite-Promote-and-Manage-Players · https://help.roll20.net/hc/en-us/articles/360046018993-Game-Invite-Troubleshooting · https://wiki.roll20.net/Game_Management

### Foundry VTT
- Self-hosted: the "invite link" is the **server address** (Game Settings → Invitation Links). Players open the URL and pick their pre-created user; roles configured by the GM beforehand.
- **The public invite link is obscured by default with a reveal toggle** — explicitly to prevent leaking it on streams/screenshots. Third-party module "Foundry Redirect" exists purely to turn unstable IPs into stable share links — evidence that a stable, copyable URL is what users actually want.
- Sources: https://foundryvtt.com/article/tutorial-two/ · https://github.com/JarrettSpiker/FoundryRedirectModule

### Owlbear Rodeo
- Pure room link — the room URL itself is the invite. **No account needed**; player enters a display name and lands in a **waiting room**; the **GM approves the join request** before they enter (the member-approval pattern live in a shipping VTT).
- Sources: https://docs.owlbear.rodeo/docs/rooms/ · https://docs.owlbear.rodeo/docs/getting-started/

### Alchemy RPG
- Two paths: (a) a **unique multi-use game URL** with a chain-icon **copy-to-clipboard button** — a signed-in player who opens it is auto-added; (b) direct add by **username**.
- Logged-out: must sign in first; the link then auto-joins.
- Source: https://help.alchemyrpg.com/en/articles/9820987-inviting-players-joining-games

### Non-VTT references
- **Discord:** per-invite **Expire After** (30 min … 7 days … Never) and **Max Uses** (1 … ∞), optional temporary membership, and a **Server Settings → Invites** list where any invite can be **revoked** instantly. Logged-out users get an accept page that runs register/login then completes the join (deferred deep link). Sources: https://support.discord.com/hc/en-us/articles/208866998-Invites-101 · https://github.com/meew0/discord-api-docs-1/blob/master/docs/resources/INVITE.md
- **Google Docs:** named-person invites with a role PLUS optional "anyone with the link" link-with-role; logged-in stranger on a restricted doc gets "Request access" the owner approves. https://support.google.com/docs/answer/2494822
- **Board Game Arena:** invitation link per open seat; works even without a BGA account (signup funnel lands at the table). https://forum.boardgamearena.com/viewtopic.php?t=30914

**Cross-product pattern:** Nobody ships "paste a code into a prompt." Everyone converged on **one shareable URL + a copy button**, varying only in (a) role encoded in link vs assigned after, (b) expiry/uses knobs, (c) approval/waiting-room step.

## Part 2 — Best-practice link flow for a session-cookie Flask app

- Token: CSPRNG ≥128 bits — `secrets.token_urlsafe(32)`. OWASP requires ≥64 bits entropy; 128+ is the margin. **Store only a hash** server-side (password-reset pattern). https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- **Path, not query:** `/invite/<token>` (Discord `discord.gg/<code>` precedent).
- **Multi-use with expiry as default** (a table of friends = one link in the group chat), configurable; single-use/48h for GM-level invites (Roll20 split).
- **Revocation UI:** per-campaign invite list (Discord model): role, created, expires, uses, Widerrufen; "Neuen Link erzeugen" invalidates the old; rotate-on-kick as extra.
- `GET /invite/<token>` never mutates. Shows campaign, DM, role, and state-specific message (valid/expired/used/revoked — distinguish, per https://supertokens.com/blog/magiclinks).
- Logged in: "Kampagne beitreten" → `POST /invite/<token>/accept` (CSRF-protected). Logged out: login/register with `next=/invite/<token>` (deferred deep link); after auth return to landing — **no silent auto-accept**.
- **CSRF/prefetch:** accept must be POST — GET-that-mutates is the CSRF-by-prefetch bug class; chat apps prefetch URLs and would consume a single-use GET invite. https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html

## Part 3 — Clipboard & share UX

- Read-only input + "Kopieren" button; `navigator.clipboard.writeText` (secure context + user gesture), label swap "Kopiert ✓" ~2 s; fallback select+`document.execCommand('copy')`. https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Interact_with_the_clipboard
- Web Share API as progressive enhancement only (desktop coverage patchy). https://developer.mozilla.org/en-US/docs/Web/API/Web_Share_API
- Never `window.prompt`/`alert`: not copyable everywhere, blocked in embedded contexts, trains users to paste secrets into dialogs.

## Part 4 — Security notes

- Entropy ≥128 bits from `secrets`; store hashed; constant-time compare.
- URL leakage: browser history, logs, `Referer`. Mitigations: `Referrer-Policy: no-referrer` on invite pages, no third-party assets on landing, short expiry, redirect to clean URL after accept. https://owasp.org/www-community/vulnerabilities/Information_exposure_through_query_strings_in_url · https://www.cobalt.io/vulnerability-wiki/v4-access-control/token-leakage-referer
- Hide-by-default reveal toggle (Foundry) for streamers.
- Member approval: auto-join fine as default with short-expiry revocable links; offer opt-in "Beitritte bestätigen" (Owlbear/Google request-access) for semi-public links; at minimum notify the DM on join.

## Synthesized recommendation

**DM side:** invite dialog (no prompt): role selector (Spieler/Co-DM), expiry (24h/7 Tage/nie — default 7 Tage), optional max uses (Co-DM: single-use, 48h). Server: `secrets.token_urlsafe(32)`, hash stored with campaign_id/role/expiry/max_uses/created_by → `https://…/invite/<token>`. Dialog: masked link + reveal + Kopieren + Teilen (if `navigator.share`). "Einladungen" tab with uses/expiry/Widerrufen; removing a player offers "alle Links erneuern".

**Player side:** logged in — landing → Beitreten (POST+CSRF) → member with invite's role → clean-URL redirect. Logged out — same landing with Anmelden/Registrieren + `next`; explicit click, no auto-accept. Expired/used/revoked: distinct German messages.

**Tradeoffs:** multi-use default trades a little security for group-chat reality; expiry+revocation+rotate-on-kick recover most. Single-use-only reserved for GM links (Roll20's split is right). Waiting room opt-in, not default. Keep no separate paste-a-code UI — the token IS the link (same token acceptable on a form page if offline handover ever matters).
