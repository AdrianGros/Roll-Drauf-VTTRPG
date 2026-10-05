# VTT Bugfix & Debugging Action Plan — 2026-09-18

**Phase:** Apply (mixed with Discover for a few items — see status column)
**Status:** in progress
**Why this doc exists:** Adrian reviewed cross-project urgency and moved the
VTT to sole primary project — the RollDrauf Discord bot is now
maintenance-only, since its functionality is either already covered inside
the bot itself or by other bots. This doc is the live register for the
resulting debugging session: every open VTT-relevant defect, sourced from
two feeds and cross-checked, gets one entry here with a primary-source root
cause (not a guess) before it gets a fix. Method follows this repo's own
`AGENTS.md`: research/discover before implementing on anything ambiguous,
cite file:line evidence, don't hide design decisions inside a summary.

## Sources

1. **Discord `#roll` feedback channel**, screenshotted 2026-09-18 by Adrian
   (Cleo/Donut, Owners): 3 items, 2026-09-06 to 2026-09-18.
2. **RollDrauf bot's `/it` IT-Testing-Dashboard → Bugs queue**
   (`rolldrauf_bot`, table `it_bug_report`, guild `1546562619098275940`),
   pulled read-only 2026-09-18: 13 open/pending reports, most filed
   2026-09-15 to 2026-09-18 by live testers. Folded in per Adrian's explicit
   mid-session instruction — this queue is the same kind of live-user signal
   as the Discord screenshot, not a separate lower-priority backlog.

Both feeds are cross-referenced below where they describe the same defect.

## Register

| # | Source | One-line | Status |
|---|--------|----------|--------|
| A | Discord (Donut, 09-18) | Password reset doesn't work | **Root-caused + fixed this session** |
| B | Bug #7 (09-18) | "VTT Passwort zurücksetzen" — no reset email received | Same defect as A |
| C | Bug #8, #9, #10, #12 (09-18) | Multiple flows (leave session, open characters, open campaigns) land back on an "old, non-functional HUD" | **Needs live reproduction before fixing** — see below |
| D | Bug #14 (09-18) | VTT freezes on browser back-navigation | Likely same family as C — needs repro |
| E | Discord (Donut, 09-18) | Invite button not visible in campaigns | Backend confirmed present — needs live/visual repro |
| F | Bug #15 (09-18) | Discord "Beitreten" button on VTT login page doesn't work | Distinct from E (OAuth login, not campaign invite) — needs config check, same bug class as A |
| G | Discord (Donut, 09-18) | New: dynamic field at Spieltisch for quick return to active session on view switch | Feature request, not a bug — spec below |
| H | Discord (Cleo, 09-06) | "Angebots-Frame visuell überarbeiten" | **Blocked — feature not found in codebase, need Adrian to clarify** |
| I | Bug #13 (09-18) | Battle map should snap to grid like Roll20 | Feature request — check against existing `ROLL20_PARITY_WORKPACKET_2026-09-03.md` scope |
| J | Bug #11 (09-18) | The bot's own Bug-Report dashboard "stops working after a while" | Bot-side (maintenance-only), but blocks further bug intake — worth a cheap look |
| K | Bugs #1–#4 (09-15/16) | Bot `/it` dashboard: test points/sessions and "mehr" menu items restricted beyond what's expected | Bot-side, maintenance-only — deprioritized, noted for whoever picks up bot maintenance |

---

## A/B — Password reset silently fails (FIXED this session)

**Root cause, from primary sources, fully chained:**

1. `vtt/auth/mailer.py:16-19` — `send_password_reset_email()` reads
   `current_app.config.get("MAIL_SERVER")` / `MAIL_DEFAULT_SENDER`; if either
   is falsy it raises `MailDeliveryError` before attempting any SMTP
   connection.
2. **Two `config.py` files exist in this repo** — the actually-used one is
   `vtt/config.py` (`vtt/__init__.py:14`, `from vtt.config import
   config_by_name`); the repo-root `config.py` is dead code, imported
   nowhere (verified by grepping every `.py` file for `from config import`/
   `import config` outside the `vtt/` package — zero hits, and `app.py`
   only ever imports `vtt.create_app`). I initially edited the wrong
   (root) file out of habit before checking which one the app factory
   actually loads — caught it via this same grep, reverted that edit, no
   trace of it left in `config.py`. Worth a cleanup decision later: root
   `config.py` looks like a pre-refactor leftover and should probably be
   deleted, not mine to do unprompted this session.
3. `vtt/config.py:141-146` **already** wires `MAIL_SERVER`/`MAIL_PORT`/
   `MAIL_USE_TLS`/`MAIL_USERNAME`/`MAIL_PASSWORD`/`MAIL_DEFAULT_SENDER` from
   `os.getenv(...)`, added 2026-09-04 (file mtime, `root:root`-owned — see
   hygiene note below) with an explicit comment: "Production supplies these
   through the deploy environment; without them the reset request remains
   generic but no misleading success mail is emitted." So the **code** has
   been correct since 2026-09-04 — the gap was purely that the live
   **environment** never supplied the values.
4. Confirmed via the live `.env.vtt.roll-drauf.de`: only `MAIL_PASSWORD` was
   present (a leftover credential from the mailserver's Aug 24
   provisioning); `MAIL_SERVER`/`MAIL_PORT`/`MAIL_USERNAME`/
   `MAIL_DEFAULT_SENDER` were simply never added. So
   `current_app.config.get("MAIL_SERVER")` really was `None` in production,
   `MailDeliveryError` really did fire on every single attempt.
5. Confirmed **not** an infra gap on top of that: `docker ps` shows
   `roll-drauf-vtt-mailserver-1` up 11 days
   (`ghcr.io/docker-mailserver/docker-mailserver:15.1.0`); live DNS lookup
   confirms MX/SPF/DKIM/DMARC for `vtt.roll-drauf.de` are all correctly set,
   matching `docs/MAILSERVER_DEPLOYMENT_2026-08-24.md` exactly. The
   compose service's network alias (`infra/docker/docker-compose.live.yml`
   mailserver service, `aliases: [vtt.roll-drauf.de]`, port 587 exposed)
   confirms `vtt.roll-drauf.de:587` as the correct internal SMTP host.
   **Root cause is a pure env-wiring gap: infra + code both ready since
   early September, the live `.env` file just never got the four missing
   keys.**
6. `vtt/auth/routes.py:677-691` (`request_password_reset`) catches
   `MailDeliveryError`, rolls back the token row, logs
   `current_app.logger.error(...)`, and **still returns the generic 202
   "check your email" response** — correct anti-enumeration behavior, not
   itself a bug, but it's why the failure was 100% silent to the user and
   to anyone not reading server logs.

**Fix applied:**
- `.env.vtt.roll-drauf.de` (live): added `MAIL_SERVER=vtt.roll-drauf.de`,
  `MAIL_PORT=587`, `MAIL_USE_TLS=true`,
  `MAIL_USERNAME=no-reply@vtt.roll-drauf.de`,
  `MAIL_DEFAULT_SENDER=no-reply@vtt.roll-drauf.de` (existing `MAIL_PASSWORD`
  untouched).
- `.env.vtt.roll-drauf.de.example` and `.env.example`: documented the same
  keys so a future re-provision can't silently reproduce this gap.
- `tests/test_password_reset.py`: added
  `test_reset_request_stays_privacy_safe_when_mail_transport_is_down` — the
  `MailDeliveryError` branch had **zero** test coverage before (both
  existing tests monkeypatched the mailer to always succeed). New test
  proves the 202-uniform-response contract holds under transport failure,
  the token row doesn't get stranded (rollback verified via a 0-count
  query), and a subsequent real request still works end-to-end.
- Verified: `pytest tests/test_password_reset.py` (3/3) and the full suite
  minus `journey` markers, both green after these changes.

**Hygiene note (not fixed, flagging only):** `vtt/config.py` is owned
`root:root` while the rest of the repo is `admin:admin` — same class of
"root-owned file silently blocks admin's future edits/commits" hazard
already seen twice on other Roll Drauf repos (Goblin Brawl, RollDrauf bot's
`.git/objects`). Didn't touch ownership since it wasn't blocking this
session's read-only need, but a future edit to this specific file may hit
it.

**Still open (deploy-side, not code):** this needs a real redeploy
(`docker compose -f infra/docker/docker-compose.live.yml --env-file
.env.vtt.roll-drauf.de up -d --build app`) to reach production — the
container running right now (built 2026-09-08) predates this fix. Per the
established pattern in this repo, direct docker mutation of the live prod
containers may be blocked for the harness; if so, Adrian needs to run that
command by hand, same as the 2026-08-27 migration cutover.

---

## C/D — "Old HUD" cluster (4 users, `Session verlassen` / `Charaktere öffnen` /
`Kampagnen öffnen` / browser back-navigation all land on a broken old page)

**Deliberately not fixed blind — reproduce first.** Static analysis ruled out
the three most likely causes without finding the real one:

- **Not stale inert markup.** The earlier-known C1 finding (2026-08-26:
  pre-redesign classic markup left inert inside `<template>` tags in
  `campaigns.html`) is confirmed still inert — `grep` for
  `cloneNode`/`querySelector('template'` etc. across `vtt/static/js/*.js`
  found zero call sites that would ever reactivate those blocks.
- **Not a stale deploy.** `docker images` shows `roll-drauf-vtt-app:latest`
  built 2026-09-08 17:57:06, matching HEAD's last commit (`e61e1ff`, same
  timestamp) exactly — the live site is running current code, not an old
  image.
- **Not aggressive browser caching.** Live response headers for
  `/static/js/book-scene.js` show `Cache-Control: no-cache` (revalidate via
  ETag every load), not a long `max-age` — ruling out "stale cached bundle"
  as the mechanism.

So the actual trigger is still unknown and guessing at a patch here would
violate the "primary sources only" instruction for this session. **Next
step:** reproduce live, by hand or via the existing Playwright robot fleet
(`tools/robots/`, 12+ registered flows already cover session/campaign
navigation), walking the exact reported paths: start a session → leave it;
open Characters from the book; open Campaigns from the book; use browser
back mid-session. Capture exactly which route/template actually renders and
what triggers it, then fix from that evidence. Given 4 independent reports
in 3 days, this is the highest-value item to reproduce next.

---

## E — Campaign invite button not visible

Backend is fully built and unrelated to this report: `vtt/campaigns/
routes.py:545-618` (`invite_player`), `:621-674` (`accept_invite`),
`:677-689` (`invite_info`, deliberately no-auth per its own docstring).
Templates/JS exist (`invite.html`, `book-scene.js` invite UI). This was
already the subject of a 2026-08-25 fix (A1 deep link + A2 join affordance,
per project memory) — the current report suggests either a regression from
the Sep 3-8 security-hardening batch (new CSP headers, socket hardening,
asset-verification changes all landed in that window and could plausibly
affect a button's visibility/render path) or a role/permission-gating edge
case. Needs the same live-repro treatment as C/D before fixing — don't
assume it's the same bug as before without checking.

## F — Discord "Beitreten" button on VTT login page non-functional

**The A/B "unwired config" theory is ruled out for this one** — checked
directly, not assumed: `vtt/config.py:71-91` already wires all 5 keys
`_discord_login_ready()` (`vtt/auth/routes.py:126-133`) requires
(`DISCORD_CLIENT_ID/SECRET/GUILD_ID/BOT_VERIFICATION_URL/BOT_SHARED_SECRET`),
and the live `.env.vtt.roll-drauf.de` has all of them populated
(non-empty). So this is a different bug than A/B, not the same class.

Also found: **there are two different "Discord" affordances on the login
page**, and the bug report's wording ("Beitreten" = "join") points at a
specific one. `vtt/templates/login.html:578` is `#discordLoginBtn` ("Mit
Discord anmelden" — OAuth login); `login.html:615` is
`.login-discord-join`, a plain `<a href="https://discord.gg/rolldrauf"
target="_blank">` static invite link — **this** is the "Beitreten" button.
Checked and ruled out: the invite link itself resolves live (`curl -L
https://discord.gg/rolldrauf` → HTTP 200). Also checked whether
`book-scene.js`'s global `document.addEventListener('click', ...)` handler
(loaded on this page, `login.html:640`) could be swallowing the click before
the browser navigates — the one handler close enough to matter
(`book-scene.js:344-348`) only acts on `.book-cover` clicks and never calls
`preventDefault()`, so it doesn't explain a broken click either.

**Still unexplained — needs live reproduction**, same as C/D/E: click it for
real (or via a Playwright robot) and see what actually happens (nothing?
console error? navigates but immediately gets bounced?) before guessing
further.

## G — Spieltisch: persistent quick-return field on view switch (feature)

Not a bug — Donut's ask (2026-09-18): when a session is active and the
player/DM navigates to another view (Campaigns, Characters), there's
currently no persistent way back into the live table except re-navigating
through the normal flow. Relevant existing code: `book-scene.js:1816-1869`
(`openPlayFromLaunch`, `quickStartSessionAndPlay`,
`quickCreateSessionAndPlay`, `quickCreateCampaignAndPlay`) already handles
entering play from a launch action, but nothing persists a "you have an
active session" affordance once the user has navigated away from it.

**Spec (draft, needs Adrian sign-off before build):** a small persistent
chip/button rendered in the book chrome (visible from Campaigns/Characters,
not just the dashboard) whenever the current user has a session in
`in_progress` state, reading e.g. "Zurück zum Tisch" and routing straight to
`/play?campaignId=&sessionId=` for that session — same target
`enterPlay()` already uses internally. Needs: (1) a lightweight
"do I have an active session" check available on every book page (likely a
small REST call or embedding it in the existing presence/session state
already pushed over sockets), (2) confirmation from Adrian on placement
(same tier as the Discord bot's request for "einlade button sichtbar" — this
may be one combined navigation-affordance pass rather than two separate
patches).

## H — "Angebots-Frame visuell überarbeiten" — BLOCKED, needs Adrian

Exhaustive grep (`angebot`, `offer`, `proposal`, `quote-frame`, case-
insensitive) across `vtt/`, `tests/`, `tools/`, all templates and JS found
**no matching feature**. The only repo hits are unrelated German prose in
docs (`Spielangebot`, `angebotene Weg` — ordinary word use, not a UI
component). This does not appear to exist in the VTT codebase under this or
any adjacent name. Flagging as a genuine block rather than guessing — see
question below.

## I — Battle map snap-to-grid

Not investigated in depth this session. `docs/ROLL20_PARITY_WORKPACKET_
2026-09-03.md` already scopes fog-of-war (done), AOE templates, freehand
drawing, whispers, and audio as the five build-order items, all reusing the
same SVG-overlay/grid-cell approach as the existing wall/light marker layer
— grid-cell math likely already exists somewhere in that pipeline and
snap-to-grid may be a small addition on top rather than new infrastructure.
Needs a real look at `vtt/static/js/play-ui.js`'s token-drag/placement code
before scoping.

## J — Bot's own Bug-Report dashboard degrades over time

Bot-side (`rolldrauf-bot-dev-work`), maintenance-only per the priority
shift — but self-referential: if the intake system itself breaks, further
bug signal from testers stops arriving, which undercuts this exact
debugging session. Worth a cheap look (not a feature-work exception) if it
resurfaces; not investigated this session.

## K — Bot `/it` dashboard access-tier complaints (bugs #1–#4)

Bot-side, maintenance-only. Bot repo's own `git log` shows migration
090/091 ("named permission tiers", dashboard runtime message_id column)
landed 2026-09-14/15, immediately before bug #1 (access-tier complaint,
09-15) — plausibly a regression from that migration. Noted for whoever
picks up bot maintenance; not in scope for this VTT-focused session per the
priority shift.

---

## Open question for Adrian

**H (Angebots-Frame):** what is this referring to? Not found anywhere in
the VTT codebase. Possibilities: (a) a page/feature not yet built, (b) a
non-standard name for something that does exist under a different name,
(c) this belongs to a different project entirely (Roll Drauf Studios
UG pricing/offer page? Something bot-side?). Need this before any fix can
be scoped, per the primary-sources-only instruction for this session.

## Sequencing (proposed)

1. **A/B** — done, needs redeploy only.
2. **C/D** — reproduce live (highest report count, 4+ independent hits).
3. **F** — check Discord OAuth env wiring (same bug class as A, cheap to
   verify).
4. **E** — reproduce live once C/D's repro method is in hand (same
   technique applies).
5. **G** — spec review with Adrian, then build (feature, not urgent bug).
6. **I** — scope against existing grid-cell code.
7. **H** — blocked on Adrian's answer.
8. **J/K** — bot-side, opportunistic only, not scheduled.
