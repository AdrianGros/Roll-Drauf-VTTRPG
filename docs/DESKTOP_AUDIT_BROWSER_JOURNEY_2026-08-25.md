# Desktop-Audit — Browser-VTT, Mission-Critical Journey (2026-08-25)

> **Follow-up:** Die Fix-Recherche zu allen Registereinträgen (Optionen, Empfehlungen,
> Entscheidungsliste) liegt in
> [FIX_RESEARCH_DESKTOP_AUDIT_2026-08-25.md](FIX_RESEARCH_DESKTOP_AUDIT_2026-08-25.md).

**Auditor:** Claude (Hauptsession) · **Baum-Stand:** Commit `08f77d1`, Arbeitsbaum sauber ·
**Sicherheit:** Robot-Läufe ausschließlich gegen den Wegwerf-Stack (§12); im Repo nur dieses
Dokument + Evidence unter `docs/proofs/desktop_audit_2026-08-25/` geschrieben.

**Messmethode** (Gegenstück zum Mobile-Audit vom 2026-08-24, gleiche Disziplin: harte Messwerte,
keine Eindrücke): Playwright-Probe (`proofs/…/probe.py`), zwei Teile —

1. **Journey durch die echte UI** (1440×900, DM- und Spieler-Browser): Registrieren →
   Kampagne anlegen → Spieler einladen → Session/Karte per Schnellstart → beide am Tisch.
   Wichtig: fullsession macht Kampagne + Invite per **API** — dieser Lauf klickt, was der
   Mensch sieht.
2. **Geometrie-Matrix** über 8 Desktop-Viewports (1024×768, 1199/1201×900 = beide Seiten des
   1200er-Breakpoints, 1280×720, 1366×768, 1440×900, 1920×1080, 2560×1440): H-Overflow,
   Scrollhöhen, angeschnittene Controls, Karten-Anteil, Widget-/Sidebar-Kollisionen.

---

## Klartext-Fazit

Der Desktop steht **strukturell viel besser da als das Telefon vor den Mobile-Fixes** — kein
einziger Pixel horizontaler Overflow auf irgendeiner Buchseite in irgendeinem Viewport, die
Karte besitzt den Tisch (85–99 % Breite), und die DM-Reise funktioniert komplett durch die
sichtbare Buch-UI, inklusive des Ein-Klick-Schnellstarts bis auf den Tisch.

**Aber die Spieler-Hälfte der Journey hat auf dem Desktop ein Loch:** Ein eingeladener Spieler
findet in der sichtbaren Buch-Ansicht von /campaigns **keinerlei Beitreten-Möglichkeit**. Der
Klick auf den Kampagnen-Eintrag tut nichts (toter Klick, §2-Klasse), und der einzige Weg zum
„Beitreten"-Knopf führt über „Kampagnen-Hub öffnen" in die Alt-Ansicht mit der alten Tab-Leiste
(„Alle" → Karte → Beitreten → `window.prompt`). Genau die Fehlerklasse „verstecktes Alt-Markup
vs. sichtbare Buch-Kopie", die der Crawler am Dashboard fand — hier kostet sie den F4-Funnel.

## 1. Journey-Ergebnis (echte UI, 1440×900)

| Schritt | Rolle | Ergebnis |
|---|---|---|
| Registrieren (Formular) | DM + Spieler | ✅ |
| Kampagne anlegen („Neue Kampagne anlegen" → Formular → Hub öffnet sich) | DM | ✅ |
| Einladung erzeugen (Hub, Spielername → Code) | DM | ✅, aber Code kommt per `window.prompt` — kein Copy-Button, kein teilbarer Link |
| Schnellstart (Session + Karte hochladen + Start + /play in einem Klick) | DM | ✅ — bester Moment der Journey |
| **Kampagne beitreten** | Spieler | 🔶 **nur über die Alt-Ansicht erreichbar** (s. Fazit); Buch-Ansicht: kein Join-Affordance, Kampagnen-Eintrag = toter Klick |
| Tisch betreten („Session betreten") | Spieler | ✅ — Rolle PLAYER, Karte live, Presence-Chip zeigt beide |

Nebenbefunde auf dem Weg (Screenshots in `proofs/`):

- Dem Spieler wird auf /campaigns ein nacktes rotes **„forbidden"**-Banner gezeigt (ein
  403 einer Hub-API für Nicht-Mitglieder landet ungefiltert als Fehlertext in der UI).
- Der DM-Hub zeigt **doppelte Knöpfe** („Spieler einladen" zweimal übereinander, „Einladung
  erzeugen" doppelt) und englische Chrome-Strings („Campaign Prep / Session Hub", „Prep
  Overview", „Refresh", „Participants / Invite Context") plus „Sessions pruefen"
  (Umlaut-Ersatz — R4-Klasse, Rendered-Text-Scan ist bekanntes Upgrade-3-Backlog).
- `lobby.html` (mit Einladungstoken-Feld!) hat **keine Route** — totes Template; der einzige
  gebaute Token-Eingabe-Screen ist unerreichbar.

## 2. Geometrie-Matrix (8 Viewports)

- **Buchseiten (Login/Übersicht/Kampagnen/Charaktere): sauber.** H-Overflow überall 0
  (auch beidseits des 1200er-Breakpoints — GD-Monotonie-Invariante hält), Scrollhöhen
  1,0–2,8 Screens. Das 10-Screen-Kolumnen-Problem des Mobile-Audits existiert am Desktop nicht.
- **Karten-Anteil am Tisch:** 85–99 % bis 1920px. Bei 2560×1440 deckelt die Kartenfläche bei
  **1624px (63 %)** — die Karte wächst auf sehr großen Monitoren nicht mit (low; ggf. Absicht
  des Buch-Satzspiegels, dann bitte als Soll dokumentieren).
- **Offene rechte Sidebar überdeckt das Token-Widget vollständig (~12.600px²) auf JEDEM
  Desktop-Viewport von 1199 bis 2560** — der als „Offener Layout-Befund an Codex" notierte
  Bug ist nicht viewport-spezifisch, sondern global (nur 1024 ist frei, weil dort das
  <1040-Layout greift). Zusammen mit dem Robot-Befund „Sidebar fängt Widget-Klicks ab" ist
  das der wichtigste Tisch-Layout-Fix.
- **Geschlossene Sidebar leckt einen Streifen:** ab ≥1200px ragen Tab-Beschriftungen und
  Controls der zugeklappten Sidebar 5–19px in den rechten Rand (Journal-Tab 19px, Action-/
  Würfel-Inputs ~5px); unter 1200px sind sie sauber draußen. Geometrie-Befund (low),
  Sichtprüfung per Screenshot steht aus — kann durch Overflow-Clipping unsichtbar sein.
- **Layers-Widget klemmt unter dem Seiten-Chip:** die Kopfzeile „Seiten (Kartenebenen)" wird
  vom „Seite: …"-Chip oben links angeschnitten (Screenshot `play-1440x900.png`) — kleiner
  Stapel-/Offset-Fix.
- Keine Konsolen-Fehler auf DM-Seite über alle Viewports; Spieler-Seite: der eine 403 (s.o.).

## 3. Empfehlungen (beratend; Priorisierung bei Adrian, §10 gilt: erst Szenario, dann Fix)

**P1 — das Journey-Loch:**
1. **Beitreten in die Buch-Ansicht bringen.** Sichtbarer Weg für Spieler mit Code: Feld/Knopf
   direkt auf der Kampagnen-Buchseite (oder ein teilbarer Invite-**Link**, der Token-Paste ganz
   erübrigt — DM erzeugt Link, Spieler klickt, fertig; löst auch das `window.prompt`-Sharing).
   Vorher als Robot-Szenario: fullsession bekommt eine **UI-Invite-Phase** (Kampagne + Invite
   + Accept durch echte Klicks statt API) — dann kann dieser Pfad nie wieder stumm brechen.
2. **Toter Klick auf den Kampagnen-Eintrag** (§2): Eintrag öffnet den Hub — oder ist kein
   Klickziel. Vertraglich erfassen (contracts/campaigns.json gehört ohnehin zur offenen
   23er-Liste des Crawlers; B3-Doppel-Markup-Abriss deckt /campaigns mit ab, nicht nur das
   Dashboard).

**P2 — Tisch-Layout:**
3. Sidebar-über-Token-Widget global fixen (Befund jetzt über alle Viewports belegt; das
   Robot-Workaround „DOM-Klick statt UI-Klick" in fullsession danach zurückbauen, damit die
   UI wieder das ist, was getestet wird).
4. Layers-Widget vs. Seiten-Chip entstapeln; den 1624px-Karten-Deckel bewusst entscheiden.

**P3 — Politur:** „forbidden"-Banner durch verständliche Meldung ersetzen (bzw. den 403-Call
für Nicht-Mitglieder gar nicht erst feuern); doppelte Hub-Knöpfe zusammenlegen; englische
Strings + „pruefen" (stützt den geplanten Rendered-Text-Scan); `lobby.html` routen oder löschen.

**Robot-Anschluss:** Dieser Lauf ist genau das, was R3 (Funnel-Budget, F3/F4) dauerhaft täte —
der Spieler-Funnel F4 wäre heute rot. Argument, R3 nach dem B3-Netz vorzuziehen.

---

## 4. Vollständiges Befundregister (fürs Planning — jeder Befund einzeln)

Severity nach Gate-I-Taxonomie (blocker/high/medium/low/info) — aber **Severity beschreibt
nur die Wirkung, sie schließt nichts**. Hausregel ab diesem Audit (Adrian, 2026-08-25, nach
wiederholten „low"-Verbrennungen — Empty-State-Overlay „Ein-Zeilen-Fix" lag live über dem
ganzen Tisch, die „6px"-Overflow-Randnotiz war die komplette URL-Leisten-Fehlerklasse):
**Jeder Befund endet in genau einem von dreien — Fix, Robot-Netz (Gate/Vertrag/Szenario)
oder dokumentierte Entscheidung von Adrian. Kein Befund wird per Label geparkt, und
„unverifiziert" ist keine zulässige Endstation** (D15 wurde deshalb noch in diesem Audit
nachgemessen statt als „low, Sichtprüfung offen" liegenzulassen). Positives ist bewusst mit
registriert — das sind die Werte, die als Gates eingefroren gehören, damit sie bleiben.

### A. Spieler-Funnel (F4)

| # | Befund | Severity | Beleg | Netz / Phase |
|---|---|---|---|---|
| D01 | Spieler mit Invite-Code hat in der sichtbaren Buch-Ansicht von /campaigns **keine Join-Affordance** (kein Knopf, kein Token-Feld) | **blocker** (F4) | Action-Dump im `report-journey-run.json`; `journey-pc-legacy-alle-tab.png` | fullsession UI-Invite-Phase; contracts/campaigns.json |
| D02 | Klick auf den Kampagnen-Eintrag in „Meine Kampagnen"/Lesefluss ist ein **toter Klick** (identischer Action-Dump vorher/nachher) | high (§2) | Journey-Log Schritt „player after campaign click" | R2-Vertrag „Eintrag → Hub" |
| D03 | Join nur über Umweg erreichbar: „Kampagnen-Hub öffnen" → alte Tab-Leiste → „Alle" → Karte → „Beitreten" | high | Journey-Log „legacy escape hatch" | wie D01 |
| D04 | Zweite versteckte Join-Affordance „Einladung eingeben" existiert ebenfalls nur in der Alt-Ansicht | medium | Action-Dump „player hub visible actions" | wie D01 |
| D05 | `lobby.html` (einziger gebauter Token-Eingabe-Screen, `#inviteToken`) ist **unverlinkt** — korrigiert 2026-08-25: der Template-Catch-all ([vtt/__init__.py:287-315](../vtt/__init__.py#L287-L315)) serviert `/lobby` sehr wohl; es zeigt nur nichts darauf. Zusätzlich: dritter Render-Stil, `window.prompt`-Create, verlangt numerische Kampagnen-ID | medium | Fix-Research §4 | Empfehlung: löschen nach A1/A2 (Catch-all ⇒ Löschen ist der einzige echte Un-Route) — Entscheidung Adrian |
| D06 | Invite-Code wird per `window.prompt` übergeben — kein Copy-Button, kein teilbarer Link | medium (UX) | campaigns.html:3906 | Design-Entscheidung „Invite-Link" (Adrian) |
| D07 | Spieler sieht auf /campaigns ein nacktes rotes **„forbidden"**-Banner (403-Rohtext in der UI) | medium | `journey-pc-legacy-alle-tab.png` (oben links) | R12 (4xx-Überwachung) |
| D08 | Spieler-Konsole: `403 FORBIDDEN` beim Laden von /campaigns (Hub-API feuert für Nicht-Mitglied) — Ursache von D07, und ein Client, der Rollen-Grenzen erst per 4xx „ertastet", ist dieselbe Denkweise wie das clientseitige dm_only-Filtern (P0 des Playtable-Audits) | medium | Journey-Findings | R12 (unerwartete 4xx als Finding); Fix zusammen mit D07 |

### B. Doppel-Markup / Alt-Ansicht (Fehlerklasse aus dem Dashboard-Crawlerfund, jetzt /campaigns)

| # | Befund | Severity | Beleg | Netz / Phase |
|---|---|---|---|---|
| D09 | /campaigns trägt verstecktes Template-Markup UND Buch-Render mit **doppelten IDs** (`#campaignCreateToggle`, `#campaignCreateName`, …) — `getElementById` trifft immer das erste; Probe musste `:visible` erzwingen | high (latent) | Erster Probe-Lauf: Klick auf `#campaignCreateToggle` = Timeout (verdeckt); `journey-FAIL-create…png` | B3-Doppel-Markup-Abriss + §13 data-testids |
| D10 | Mitten in der Journey wechselt die UI von Buch-Nav (Übersicht/Kampagnen/…) in die Alt-Ansicht mit **„Cockpit"**-Nav — zwei Navigationssysteme in einem Flow | medium (Design) | Action-Dumps: beide Nav-Sätze sichtbar | B3; R5/R7 |
| D11 | DM-Hub: **doppelte Knöpfe** — „Spieler einladen" zweimal übereinander (rot+grau), „Einladung erzeugen" doppelt | medium | Screenshot des Hubs (`journey-FAIL-player_accepts…png`, DM-Seite) | R2-Verträge Hub; B3 |
| D12 | Englische Chrome-Strings im Hub: „Campaign Prep / Session Hub", „Prep Overview", „Prep Headquarters", „Session Flow", „Map + Assets", „Refresh", „Participants / Invite Context", „Asset Library", „Map Prep", „Preview", „Download" | low (Ratchet) | Screenshots + Action-Dumps | R4 Rendered-Text-Scan (Upgrade-3-Backlog) |
| D13 | Umlaut-Ersatz sichtbar: „Sessions **pruefen**" | low | Hub-Screenshot | R4 (Muster existiert, Datei erfassen) |

### C. Spieltisch-Layout (Desktop)

| # | Befund | Severity | Beleg | Netz / Phase |
|---|---|---|---|---|
| D14 | Offene rechte Sidebar **überdeckt das Token-Widget vollständig** auf JEDEM Viewport 1199–2560 (10.140–12.600px²; 1024 frei, weil <1040-Layout) | high | Matrix-Findings aller Läufe; `play-1440x900.png` unten rechts | fullsession: DOM-Klick-Workaround zurückbauen, echter UI-Klick als Gate |
| D15 | Geschlossene Sidebar: Geometrie ragt ab ≥1200px 5–19px in den Viewport (Journal-Tab, Würfel-Inputs). **Nachgemessen 2026-08-25 (`sliver-closed-right-edge.png` + elementFromPoint): NICHT sichtbar und NICHT hit-testbar** — geclippt/hinter dem Backdrop, kein Klick-Diebstahl. Kein Defekt heute, aber eine z-index-Änderung würde es stumm zum Defekt machen | verified — Invariante pinnen | `sliver-closed-1440x900.png`, `sliver-closed-right-edge.png`, Hit-Test-JSON | Neues Gate für contracts/play.json: „Off-Canvas-Inhalt ist weder sichtbar noch hit-testbar" |
| D16 | Layers-Widget-Kopf „Seiten (Kartenebenen)" wird vom „Seite: …"-Chip **angeschnitten** — auf jedem Tisch-Load, DM UND Spieler; der erste Eindruck des Tisches ist ein Layout-Fehler | medium | `play-1440x900.png`, `journey-pc-table.png`, `sliver-closed-1440x900.png` | Fix + R6-Baseline Tisch |
| D17 | Kartenfläche **deckelt bei 1624px** — bei 2560×1440 nur noch 63 % Kartenanteil (85–99 % bis 1920) | Entscheidung (Adrian) | Matrix: mapW 1624 bei 1920 UND 2560 | Soll (Satzspiegel) oder Fix — danach als Gate festschreiben, nicht offen lassen |
| D18 | **Spieler sieht im Layers-Widget Bearbeitungs-Controls** (Namensfeld, Auge, rotes ×) — Server lehnt Schreibpfad ab (getestet), aber die UI bietet Klicks an, die nur scheitern können (§2-Geruch: „Knopf ohne erreichbare Wirkung" für die Rolle) | medium (prüfen) | `journey-pc-table.png` links oben | R2-Verträge mit Rollen-Dimension (contracts/play.json) |

### D. Positivbefunde (als Gates einfrieren, damit sie bleiben)

| # | Befund | Beleg | Gate-Vorschlag |
|---|---|---|---|
| D19 | **0px H-Overflow auf allen Buchseiten × allen 8 Viewports**, auch beidseits des 1200er-Breakpoints (Monotonie-Invariante hält abwärts) | Matrix, 32 Zellen | Desktop-Viewports in die Robot-Matrix aufnehmen (Mess-Gates §6 des Mobile-Audits um 1024/1280/1920/2560 erweitern) |
| D20 | Scrollhöhen Buchseiten 1,0–2,8 Screens (kein Endlos-Kolumnen-Problem wie mobil); Sprung 1199→1201 ist der erwartete Spread-Wechsel | Matrix | Trend beobachten (R3) |
| D21 | Kartenanteil am Tisch 85–99 % bis 1920px | Matrix | Fold-out-Gate ≥55 % gilt auch Desktop — heute weit drüber |
| D22 | DM-Journey durch die echte UI komplett grün: Registrieren → Kampagne → Hub → Invite → **Ein-Klick-Schnellstart** (Session+Karte+Start+/play) | Journey-Log; `journey-hub-after-create.png`, `journey-dm-table-after-quickstart.png` | F3-Funnel-Budget einfrieren (R3): heute 5 Klicks Kern-Pfad |
| D23 | Spieler landet als PLAYER live am Tisch, Karte sichtbar, **Presence-Chip zeigt beide** („Am Tisch: desk_dm_bot, desk_pc_bot") | `journey-pc-table.png` | bleibt fullsession-Phase |
| D24 | Null Konsolen-Fehler DM-seitig über alle 8 Viewports × 5 Seiten | Matrix | R12 |

### E. Netz-Lücken (Prozess — warum das keiner der 12 Robots sah)

| # | Befund | Severity | Konsequenz |
|---|---|---|---|
| D25 | fullsession macht Kampagne + Invite + Accept per **API** — die UI-Hälfte von F3/F4 war nie robot-geklickt; D01–D04 konnten nicht auffallen | high (Netz) | UI-Invite-Phase in fullsession (dieses Probe-Skript ist die Vorlage: `proofs/…/probe.py`) |
| D26 | `contracts/` kennt nur das Dashboard — /campaigns, Hub und /play sind vertragsfrei; D02/D11/D18 sind genau die Lücken | medium (Netz) | contracts/campaigns.json + play.json in die B3-Liste (§13) |
| D27 | R3 (Funnel-Budget) existiert nicht — F4 wäre heute rot, und niemand misst es | medium (Netz) | R3 nach dem B3-Netz vorziehen (Empfehlung §3) |

---

*Evidence: `docs/proofs/desktop_audit_2026-08-25/` (Probe-Skript, Journey-Report,
Screenshots). Buchseiten-/Tisch-Messwerte im Volltext dieses Audits; Roh-Matrix im
Sessionarchiv. Schwesterdokumente: MOBILE_AUDIT_BUCH_UI_2026-08-24, PLAYTABLE_AUDIT_2026-08-25,
ROBOT_FLEET_AND_RULEBOOK_2026-08-24.*
