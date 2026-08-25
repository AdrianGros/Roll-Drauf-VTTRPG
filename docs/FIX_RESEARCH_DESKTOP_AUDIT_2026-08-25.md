# Fix-Research — Desktop-Audit-Befunde D01–D27 (2026-08-25)

> **Addendum (2026-08-25, später): P1-Fixes implementiert und verifiziert.**
> Umgesetzt: A1 (Invite-Deep-Link `GET /invite/<token>` + `/api/invites/<token>`,
> Copy-Link statt `window.prompt`), A2 (Beitreten-Affordance + klickbare
> Mitglieds-Zeile im Buch-Render), B1+B2 (kein 403-Sackgang mehr, Fehlercodes
> übersetzt), C2 (Doppel-Knopf-Guard), D14–D18 (Sidebar-Ausweichregel für das
> Token-Widget, explizite Off-Canvas-Invarianten, Layers-Widget-Offset,
> Karten-Deckel für den Tisch aufgehoben, Rollen-Gate für Layer-Controls), D1
> (`lobby.html` gelöscht), E1 (Sprach-Sweep in campaigns.html). Szenarien
> zuerst geschrieben (§10): `tests/test_desktop_audit_fixes.py`, 7/7 grün;
> voller Testlauf 473/473 grün; `fullsession` und `mobile` Robots 0 Findings;
> alle sechs Layout-/Journey-Befunde zusätzlich per echtem Playwright-Klick
> re-verifiziert (0 Findings). **Offen:** C1 (die eigentliche B3-Konsolidierung
> auf eine Render-Engine für /campaigns) sowie die Stufe-2-Entscheidungen aus
> §8 (offene Mehrfach-Links, Owlbear-Warteraum) — bewusst nicht Teil dieser
> Runde. Ein Lapsus unterwegs: ein Python-Sweep-Skript hatte einen
> `"".join([""])`-Bug, der `campaigns.html` durch `str.replace("", …)`
> aufblähte (196 KB → 13 MB) — per `git checkout` sofort zurückgesetzt, alle
> Sprach-Fixes danach einzeln über den Edit-Mechanismus wiederholt.

**Autor:** Claude (Hauptsession + 4 parallele Research-Agenten) · **Basis:**
[DESKTOP_AUDIT_BROWSER_JOURNEY_2026-08-25.md](DESKTOP_AUDIT_BROWSER_JOURNEY_2026-08-25.md) §4-Register ·
**Scope:** Read-only-Recherche (2 Stränge Web-Best-Practice mit Primärquellen, 2 Stränge
Code-Analyse mit file:line-Belegen). **Kein Fix wurde umgesetzt** — dieses Dokument ist die
Entscheidungsvorlage; §10 gilt (erst Robot-Szenario, dann Fix), Priorisierung bei Adrian.

---

## Klartext-Fazit

Drei Dinge hat die Recherche eindeutig geklärt: **(1)** Kein einziges vergleichbares Produkt
(Roll20, Foundry, Owlbear, Alchemy, Discord, Google Docs, BGA) lässt Spieler einen Code in
einen Dialog tippen — alle sind bei **einem teilbaren Link mit Kopieren-Knopf** gelandet;
unser Invite-Backend kann einen Deep-Link fast geschenkt, weil der Token schon global
eindeutig ist. **(2)** Für Panels, die während des Spiels offen bleiben (Chat/Journal), ist
**Reflow statt Overlay** der Industriestandard — Figma hat schwebende Panels über dem Canvas
öffentlich zurückgenommen, Roll20/VS Code/Photoshop reflowen, und Foundry (der einzige
Overlay-Verfechter) überlebt nur mit „standardmäßig zugeklappt" plus einer ganzen
Modul-Industrie, die seine Sidebar repariert. **(3)** Fast alle unsere Tisch-Befunde sind
**S-Fixes mit existierendem Vorbild im eigenen Code** — die Topbar weicht der Sidebar schon
aus, die Layer-Add-Zeile ist schon rollen-gegated; die Muster müssen nur auf die Nachbarn
angewendet werden.

**Faktenkorrektur zum Audit (D05):** `lobby.html` ist nicht „unrouted" — der Catch-all in
[vtt/__init__.py:287-315](../vtt/__init__.py#L287-L315) serviert JEDES Template per Namen
(`/lobby` funktioniert). Es ist **unverlinkt**, nicht unerreichbar. Register ist korrigiert.

---

## 1. Spieler-Funnel: Invite & Join (D01–D06)

### Was die Welt tut (Web-Strang, Primärquellen)

- **Roll20:** Link-first; Spieler-Join-Link mehrfach nutzbar ∞, **rotiert automatisch beim
  Kick eines Spielers**; GM-Invite-Links dagegen single-use + 48h (höheres Privileg =
  engerer Token). [help.roll20.net](https://help.roll20.net/hc/en-us/articles/29620515876375)
- **Owlbear Rodeo:** Raum-URL ist die Einladung; ohne Account, dafür **Warteraum mit
  DM-Bestätigung** — das Approval-Muster live in einem VTT. [docs.owlbear.rodeo](https://docs.owlbear.rodeo/docs/rooms/)
- **Discord:** Konfigurierbare Invites (Expire 30min–nie, Max-Uses 1–∞) + eine
  **Server-Einstellungen→Invites-Liste mit Widerrufen** — das Revocation-Vorbild.
  [Invites 101](https://support.discord.com/hc/en-us/articles/208866998)
- **Alchemy:** Multi-use Spiel-URL mit Copy-Button; eingeloggter Spieler, der sie öffnet,
  wird automatisch Mitglied. [help.alchemyrpg.com](https://help.alchemyrpg.com/en/articles/9820987)
- **Foundry:** maskiert den Invite-Link hinter einem Reveal-Toggle — Streamer-Schutz,
  billig, kopierenswert. [foundryvtt.com/article/tutorial-two](https://foundryvtt.com/article/tutorial-two/)
- **Flask-Handwerk:** Token `secrets.token_urlsafe(32)`, **serverseitig nur gehasht
  speichern** (Password-Reset-Muster); `GET /invite/<token>` ist reine Landing-Page,
  **Accept nur als CSRF-geschütztes POST** — Chat-Apps (auch Discord!) prefetchen URLs und
  würden einen mutierenden GET-Invite „verbrauchen"; Logged-out → Login/Registrieren mit
  `next=`-Rücksprung (Deferred-Deep-Link), niemals stilles Auto-Accept;
  `Referrer-Policy: no-referrer` auf Invite-Seiten; nach Accept auf saubere URL redirecten.
  (OWASP Session-Mgmt/CSRF-Cheatsheets, MDN.)

### Was unser Code hergibt (Code-Strang)

- Token-Modell [invite_token.py:9-39](../vtt/models/invite_token.py#L9-L39): global eindeutig
  + indiziert (→ **Deep-Link braucht keine campaign_id**), single-use, 7 Tage Expiry,
  **username-/email-gebunden** (Accept prüft E-Mail, [routes.py:652](../vtt/campaigns/routes.py#L652)).
- Accept-Logik existiert komplett ([routes.py:617-670](../vtt/campaigns/routes.py#L617-L670));
  eine `GET /invite/<token>`-Route ist ein kleiner Aufsatz: Token → Kampagne auflösen,
  login-aware Landing, Accept-POST wiederverwenden.
- Der tote Ledger-Klick (D02): [book-scene.js:684-721](../vtt/static/js/book-scene.js#L684)
  rendert die Zeile ohne `data-dashboard-*`-Attribut — nur der innere Hub-Knopf ist verdrahtet.
- Die Buch-Ansicht hat **null** Join-Affordance; „Einladungen" ist dort ein dekoratives Div
  ([book-scene.js:1063-1066](../vtt/static/js/book-scene.js#L1063)).

### Optionen

| # | Option | Aufwand | Bewertung |
|---|---|---|---|
| A1 | **Invite-Deep-Link** (`GET /invite/<token>` login-aware Landing + POST-Accept) + Copy-Link-Block statt `window.prompt` ([campaigns.html:3906](../vtt/templates/campaigns.html#L3906)) | M | **Empfohlen.** Tötet Code-Tippen und Prompt-Sharing in einem Zug; Token-Modell ist dafür schon sicher (single-use, 7d, gebunden). |
| A2 | **Join-Affordance im Buch-Render**: „Beitreten"-Knopf + Token-Feld in `buildCampaignLedger` für `is_member:false`; Ledger-Zeile selbst wird Klickziel (killt D02) | M | **Empfohlen als Ergänzung** — Fallback für Code-Weitergabe am Tisch, und die Funktionalität wandert in die überlebende Engine (B3-konform). |
| A3 | Stopgap: Buch-Knöpfe zielen direkter auf die Alt-Ansicht („Alle"-Tab) | S | **Abgeraten** — investiert in Markup, das B3 abreißt; behält `window.prompt`. |

**Stufe 2 (eigene Entscheidung, nicht Voraussetzung):** das Roll20/Discord-Modell —
**offene Mehrfach-Links** (nicht username-gebunden, Expiry/Max-Uses-Regler, Invite-Liste mit
Widerrufen, Rotate-on-Kick, optional Owlbear-Warteraum). Erfordert Modelländerung
(`invited_user_email` optional, Member-Row erst beim Accept). Die TTRPG-Realität („ein Link
in den Gruppenchat") spricht dafür; A1/A2 funktionieren aber auch ohne. Bei Umsetzung:
Token-Hashing + Foundry-Maskierung gleich mitnehmen.

## 2. Der 403/„forbidden"-Sackgang (D07, D08)

Exakte Kette gefunden: `GET /api/campaigns` listet allen Nutzern alle öffentlichen Kampagnen
([routes.py:308-321](../vtt/campaigns/routes.py#L308)) — aber „invited" zählt nicht als
Mitglied; der einzige Knopf, den die Buch-Seite dem Spieler anbietet, führt zu
`GET /api/campaigns/<id>` → `_is_active_member` false → 403 `{"error":"forbidden"}`
([routes.py:388](../vtt/campaigns/routes.py#L388)) → `auth.js` wirft den Roh-String
([auth.js:139](../vtt/static/js/auth.js#L139)) → rotes Banner. Kein Hintergrund-Poll — **die
Navigation selbst ist auf einen garantierten 403 gerichtet.**

- **B1 (S, empfohlen):** Den todgeweihten Call gar nicht feuern — `is_member` liegt dem
  Client bereits vor; Nicht-Mitglieder bekommen den Join-Zustand aus A2 statt des Hub-Links.
- **B2 (S, empfohlen dazu):** Fehler-Übersetzung an der Naht (`auth.js`): bekannte API-Codes
  → deutsche Nutzertexte. Wirkt app-weit gegen die ganze Roh-Banner-Klasse.

## 3. Doppel-Markup, zwei Navigationen, Doppel-Knöpfe (D09–D11)

Mechanik geklärt: `campaigns.html` liefert IMMER das komplette Legacy-Markup mit; Buch-Modus
versteckt es nur per CSS ([campaigns.html:1297-1301](../vtt/templates/campaigns.html#L1297)),
und `?classic=1`/`?campaign_id=` schalten zurück ([:1498-1521](../vtt/templates/campaigns.html#L1498)).
Das sichtbare Buch-Render ist **ID-frei** → jedes `getElementById` trifft die unsichtbare
Kopie. Positiv: signup/register/character-sheet nutzen bereits **inerte `<template>`-Elemente**
— das kollisionsfreie Muster existiert im Haus. Der Doppel-„Spieler einladen" (D11) ist ein
unbedingtes Zweit-Rendering bei [:3124](../vtt/templates/campaigns.html#L3124) neben der
identischen `primaryAction` aus [:2166-2170](../vtt/templates/campaigns.html#L2166).

- **C2 (S, jetzt):** Doppel-Knopf-Guard, IDs grep-sauber, `data-testid` auf die sichtbaren
  Buch-Elemente (überleben die spätere Konsolidierung — §13).
- **C1 (L, = die B3-Phase für /campaigns):** Eine Engine. Legacy-Body raus, Inhalte als
  Scene-Builder bzw. `<template>` (Haus-Muster), `classic=1` stirbt, „Cockpit"-Nav stirbt
  (D10). Reihenfolge laut Regelwerk: **erst Verträge spannen, dann umbauen** — der Crawler
  ist das Regressionsnetz.
- **C3 (abgeraten):** Server-seitige Seiten-Varianten = zweite Kopie in neuem Gewand.

## 4. lobby.html (D05 — Entscheidung)

Korrektur s.o.: erreichbar unter `/lobby`, aber nirgends verlinkt. Inhalt: das einzige
gebaute Token-Formular — plus drei `window.prompt`s für Campaign-Create, englische Strings,
und es verlangt die **numerische Kampagnen-ID**. Ein dritter Render-Stil.
**Empfehlung D1: löschen** (Datei + `/lobby`-Metadaten in book-routes.js), sobald A1/A2
gelandet sind — die eine gute Idee (Token-Formular in Buch-Optik) zieht nach /campaigns um.
Wegen Catch-all ist Löschen der einzige Weg, es wirklich zu entrouten.

## 5. Tisch-Layout (D14–D18)

### Was die Welt tut (Web-Strang)

- **Reflow ist der Standard für persistente Panels:** Roll20 (Sidebar = echte Spalte,
  ziehbar, Karte endet wo die Sidebar beginnt), VS Code, Photoshop. **Figma hat schwebende
  Panels über dem Canvas nach Nutzerprotest zurückgebaut** („content peeked out from behind
  panels") — exakt unsere Fehlerklasse. [figma.com/blog/our-approach-to-designing-ui3](https://www.figma.com/blog/our-approach-to-designing-ui3/)
- **Overlay-Verfechter kompensieren:** Foundry v13 startet die Sidebar bewusst ZUGEKLAPPT und
  reserviert die ganze rechte Kante exklusiv („one edge = one owner"); Owlbear-Bubbles
  **fließen dynamisch um das Dock herum** — dokumentierte Kollisionsvermeidung.
  [owlbear 2.2 notes](https://blog.owlbear.rodeo/owlbear-rodeo-2-2-release-notes/)
- **Technik für Reflow:** Grid `1fr` + `0fr`-Spalte (animierbar), Canvas-Refit via
  ResizeObserver, **Center-stabile Pan-Korrektur** (Weltpunkt der alten Viewport-Mitte
  festhalten, sonst „springt" die Karte). CSS **Anchor Positioning ist 2026 Baseline**
  (~90 %, Polyfill 8KB) — richtig für Chip/Widget-Beziehungen wie D16.
- **2560px+:** Kein VTT deckelt den Canvas. Gedeckelt werden Sidebar (rem, nicht %) und
  Textspalten (~65ch) — nie die Karte.

### Was unser Code hergibt (Code-Strang, alles mit file:line)

- Sidebar = absolutes Overlay z 26, Breite 340 ([play.html:759-778](../vtt/templates/play.html#L759));
  Widgets z 18 — daher D14. **Präzedenzfall existiert:** die Topbar weicht der offenen
  Sidebar bereits per `:has(.right-sidebar.is-open)` aus ([play.html:544-551](../vtt/templates/play.html#L544)) —
  diese Regel wurde für die Topbar schon zweimal erkämpft.
- D15-Wahrheit: zu ist NUR `translateX(100%)` — kein `visibility`, kein `pointer-events`;
  gerettet werden wir heute vom `overflow:hidden` eines **Vorfahren**
  ([play.html:101-105](../vtt/templates/play.html#L101)). Genau so fragil wie vermutet.
- D17-Quelle: `min(1680px, …)` auf `main` in
  [book-scene.css:580-585](../vtt/static/css/book-scene.css#L580) → 1680−54−2 = die
  gemessenen 1624px. Play überschreibt den generischen 1480er-Deckel schon einmal nach oben —
  das Satzspiegel-Argument ist auf dieser Seite halb aufgegeben.
- D18: `_renderLayers()` rendert Rename/Auge/Löschen für ALLE Rollen
  ([play-ui.js:1821-1877](../vtt/static/js/play-ui.js#L1821)); die Add-Zeile daneben ist
  korrekt operator-gegated ([play-ui.js:2065](../vtt/static/js/play-ui.js#L2065)) — Muster kopieren.

### Empfehlungen

| Befund | Fix jetzt | Aufwand | Endzustand |
|---|---|---|---|
| D14 | Token-Widget bekommt die Topbar-Ausweichregel (`:has(.is-open)` + `--sidebar-w`-Variable statt dritter Magic-Number-Kopie; Transition synchron zur Sidebar) | **S** | **Reflow-Sidebar als Grid-Spalte** (M) beim nächsten Tisch-Umbau — löst D14+D15 strukturell, löscht die Topbar-Hacks; deckt sich mit Figma/Roll20-Evidenz. Buch-Metapher: Journal öffnen = das Buch weiter aufklappen, nicht eine Karte über die Seite legen. |
| D15 | `visibility:hidden` + `pointer-events:none` (mit Delay-Transition) auf der zugeklappten Sidebar + `inert`-Toggle im JS (fängt auch Tab-Fokus — vom Audit nicht geprobt) | **S** | erledigt sich mit Reflow von selbst |
| D16 | `--topbar-h`-Token, Widget-`top` = `calc(0.85rem + var(--topbar-h) + 0.5rem)`; später Anchor-Positioning falls die Topbar je umbricht | **S** | — |
| D17 | **Empfehlung: Deckel für den Tisch heben** (`play.html`-Override: `max-width:none`), Character-Sheet behält 1680. Kein VTT deckelt den Canvas; ein 2560er-Monitor soll Karte sein. **Entscheidung Adrian** — bei „behalten" wird 1624 als Soll dokumentiert und gepinnt | **S** | Sidebar bei ~22rem deckeln, nicht die Karte |
| D18 | Operator-Gate in `_renderLayers` (Muster der Add-Zeile): Nicht-Operatoren bekommen Text statt Input, keine Aktions-Zeile, kein „Aktivieren"; Markup gar nicht erst emittieren (robusteste Variante der `hidden`-Lektion) | **S** | Bootstrap-`capabilities`-Objekt vom Server (M), wenn die Payload eh angefasst wird — passt zur P0-Linie „Client rät keine Rollen" |

## 6. Sprache (D12, D13) — konkrete Liste statt Gefühl

Vollständige Fundliste liegt vor (alle in `campaigns.html`, plus lobby.html das D1 löscht):
Umlaut-Ersatz `pruefen` bei :1860, :3125, :3232, `unveraendert`/`geprueft` :3410; englische
Strings u.a. :1327 (Cockpit), :1348-1352 (Campaign Atlas/Campaigns + engl. Absatz), :1465
(Refresh), :2568 (Participants / Invite Context), :3090 (Campaign Prep / Session Hub),
:3107-3110 (Badges), :3134 (Prep Overview), :3476/:3512 (Preview), :3529 (Download), :2500
(Unknown), :1479 (engl. Footer). **E1 (S):** ein Sweep über die Liste, DANN den
R4-Rendered-Text-Scan scharf schalten (Ratchet startet grün). E2 (Strings als
`page_content`-Katalogdaten) nur für Strings, die C1 überleben — sonst Doppelarbeit.

## 7. Robot-Netz zuerst (D25–D27, §10-Reihenfolge)

1. **fullsession UI-Invite-Phase** (Kampagne + Invite + Accept + Join per echten Klicks; die
   Audit-Probe `proofs/desktop_audit_2026-08-25/probe.py` ist die Vorlage) — Voraussetzung
   für Cluster A/B.
2. **contracts/campaigns.json**-Skelett mit dem „Eintrag → Hub"-Vertrag (D02) und den neuen
   A1/A2-Elementen (§13 gleich mitliefern).
3. **contracts/play.json** mit: elementFromPoint-Vertrag „Token-Widget klickbar bei offener
   Sidebar" (D14), Invariante „Off-Canvas nie sichtbar/hit-testbar/fokussierbar" (D15),
   Chip∩Widget=∅ (D16), Map-Share-Floor 1920/2560 (D17, je nach Entscheidung), Rollen-
   Dimension für Layer-Controls + R12 „Spieler-Session erzeugt null 4xx" (D18, D08).
4. Danach Fixes in der Reihenfolge: **B1+B2 → A1+A2 → C2 → D14–D18-S-Fixes → D1 → E1 → C1
   (=B3)**. fullsession-DOM-Klick-Workaround zurückbauen, sobald D14 gefixt ist.

---

## 8. Entscheidungsliste für Adrian (nummeriert, mit Empfehlung)

1. **Invite-Modell Stufe 2** — offene Mehrfach-Links mit Expiry/Widerruf-Liste (Roll20/
   Discord-Modell) statt nur username-gebundener Einzel-Invites? *Empfehlung: Ja, als
   eigene Phase nach A1/A2; mit Token-Hashing.*
2. **D17 Karten-Deckel** — 1624px-Cap für den Tisch heben oder als Soll dokumentieren?
   *Empfehlung: heben; kein VTT deckelt den Canvas.*
3. **D05 lobby.html** — löschen nach A1/A2? *Empfehlung: Ja.*
4. **D14 Endzustand** — Reflow-Sidebar (Grid-Spalte) als Ziel für den nächsten
   Tisch-Umbau einplanen (S-Fix jetzt unabhängig davon)? *Empfehlung: Ja; Figma/Roll20-
   Evidenz ist eindeutig, und es passt zur Buch-Metapher.*
5. **Owlbear-Warteraum** („Beitritte bestätigen" als Kampagnen-Toggle) — mitnehmen oder
   weglassen? *Empfehlung: Opt-in-Toggle erst mit Stufe 2; bis dahin reicht
   DM-Benachrichtigung beim Join.*

---

*Quellen: die vier vollständigen Agenten-Reports liegen unter
`docs/proofs/desktop_audit_2026-08-25/fix-research/` (agent-report-1…4); Kernquellen: Roll20 Help,
Foundry VTT Docs/v13-Releasenotes, Owlbear Rodeo Dev-Logs/2.2-Notes, Alchemy Help, Discord
Invites 101 + API, Google Drive Sharing, Figma UI3-Designblogs, VS Code Layout-Docs, OWASP
Session-Mgmt/CSRF-Cheatsheets, MDN (Clipboard, Web Share, ResizeObserver, Anchor
Positioning, Referer), web.dev/CSS-Tricks (Grid-Animation), webglfundamentals
(Canvas-Resize), caniuse (Anchor Positioning ~90 % Baseline 2026).*
