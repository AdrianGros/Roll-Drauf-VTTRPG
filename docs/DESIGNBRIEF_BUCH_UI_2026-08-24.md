# Designbrief: Das Buch-UI (2026-08-24)

Grundlage: (a) Recherche aus Primärquellen (Nielsen Norman Group, Butterick's
Practical Typography, Bringhurst, Material-Design-Motion-Spezifikation, W3C/WCAG
2.2, MDN View Transitions API, dokumentierte Flipbook-Postmortems), (b) die in
Goblin Delve über ~140 Patches bezahlten UX-Lektionen (GUI_AUDIT_2026-08-18 ff.,
RCA_COCKPIT_BREAKPOINT, MOBILE_GUI_RESEARCH), (c) ein vollständiger Audit des
bestehenden Buch-Shells inkl. Screenshots. Quellen-URLs am Ende.

Kriterium des Eigentümers (fix): **Die Website soll sich anfühlen wie das Lesen
eines Buches — Seiten umblättern, um neue Ansichten zu erreichen.**

---

## 1. Design-These

Die Seite soll wie ein Buch **lesen** (cremefarbenes Papier, dunkle Tinte,
Serifen-Mengensatz bei ~66 Zeichen Zeilenlänge und 140 % Durchschuss, Kapitel,
Kolumnentitel, Folios, ein Inhaltsverzeichnis als Home) und nur an
**Kapitel-/Seitengrenzen** wie ein Buch **blättern** — ein einziger,
richtungstreuer Seitenumschlag von 350–500 ms (View Transitions API,
emphasized easing, Cross-Fade bei `prefers-reduced-motion`). Der Spieltisch ist
die **ausklappbare Karte** im Buch: dort schlägt das Buch flach auf und tritt
zurück. Genau an dieser Linie trennen NN/g, Apples eigene Geschichte (iBooks
behielt den Page-Curl nur auf der Lesefläche) und die Flipbook-Postmortems
Metapher-die-orientiert von Metapher-die-behindert.

## 2. Diagnose: warum es sich heute „terrible" anfühlt

Nicht die Metapher ist das Problem, sondern ihre **Fragmentierung**. Der Audit
zählt: **5 Farbsysteme** (Pergament + Legacy-Duplikate + Flat-UI-Statusfarben +
halbfertiger Dark-Mode + das Navy-System des Spieltischs), **4
Transitions-Engines** (GSAP-Shell-Flip, der bei 0,36 s von 0,82 s durch den
Seiten-Reload geköpft wird; BookScene-SPA-Timelines; CSS-Vorhänge in play.html;
eine 📖-Emoji-Animation), **3 Navigations-Bindungen** auf denselben Buttons
(dieselbe Route animiert je nach Eingabemethode dreifach verschieden) und **3
Sprachen** (Englisch, ö-Deutsch, oe-Deutsch — teils im selben Formular:
Username/Password/„Anmelden").

Dazu die Ironie vom 2026-08-23: Die vier .woff2-„Fonts" waren monatelang
HTML-Fehlerseiten. Seit sie repariert sind, rendert erstmals die echte
Deklaration `--vtt-font-body: 'PirataOne'` (theme.css:46) — **Piraten-
Displayschrift als Mengentext der gesamten App**. Zwei Kernseiten
(campaigns/characters) laden theme.css gar nicht, weshalb dort andere
Schriften/Farben gelten als nebenan. Die grauen Kopf-Kacheln, Meta-Prosa über
die App selbst („Die Produktlinie führt jetzt…") und Dev-Chips („BookScene
Runtime", „Arrow Keys Turn") tun das Übrige: Der Nutzer erlebt Nähte, keine
Seiten.

## 3. Leitprinzipien (Recherche × Goblin-Delve-Lektionen)

1. **Buch als Material und Ordnung, nicht als Simulator.** Skeuomorphismus nur
   dort, wo er Verständnis stiftet (NN/g); keine 3D-Physik auf jedem Klick,
   kein Leder-Chrome, keine erzwungenen Doppelseiten. „Flat 2.0": flache
   Flächen mit subtilen Tiefen-Hinweisen für Bedienbarkeit.
2. **Eine Quelle pro Sache.** Ein Token-Set, eine Transitions-Engine, eine
   Navigations-Bindung, eine Render-Quelle pro Inhalt (Goblin Delve F2/Patch
   109: doppelte Darstellungen driften immer).
3. **Deutsch, mit echten Umlauten, überall.** Goblin Delve Patch 110: „eine
   Sprache, ein Menü". Rest-Anglizismen werden benannte Schuld, nicht Drift.
4. **Inhalt statt Selbstbeschreibung.** Keine Prosa, die erklärt, was die Seite
   ist — die Seite zeigt es (Goblin-Delve-F7: Scaffolding-Gefühl).
5. **Vitals ohne Klick.** Kolumnentitel trägt Ort („Kapitel II · Kampagnen"),
   Lesezeichen trägt „Weiterlesen"; nichts Wichtiges unter der Falz.
6. **Blättern ist Wegweisung.** Vorwärts im Buch = Seite schlägt nach links;
   zurück = nach rechts; tiefer (Kapitel→Detail) öffnet statt blättert. Nie
   blättern für Aktionen innerhalb einer Seite.
7. **Paging nie als einziger Weg.** Nutzer scannen (F-Pattern); das
   Inhaltsverzeichnis ist von überall eine Interaktion entfernt.
8. **Ehrliches UI.** Jede Verweigerung nennt die Zahl; Gesperrtes bleibt
   sichtbar, aber lesbar gesperrt; keine toten Knöpfe (unsere eigene
   Play-Table-Lektion + Goblin Delve Patch 112/130).
9. **Bewegung verdient ihre Kosten.** Häufige Animationen kurz und subtil
   (≤200 ms); der Umschlag nur an Ansichtsgrenzen; `prefers-reduced-motion`
   ersetzt ihn durch ~150 ms Cross-Fade; In-App-Schalter „Blätter-Animation".
10. **Messen mit Gates, nicht Notizen.** Robots, die durchfallen können
    (Goblin-Delve-RCA): Layout-Monotonie, Kontrast, Sprach-Lint,
    Ein-Engine-Invariante.

## 4. Das Designsystem

### 4.1 Material (ein Token-Set, ersetzt alle fünf)

- **Papier**: `#F8F3E9` (Seiten), `#F1E9D8` (vertiefte Flächen). Kein oranges
  Sepia; höchstens kaum wahrnehmbare Papierkörnung, nie unter Mengentext.
- **Tinte**: `#3A322C` (warmes Anthrazit, ≈10:1 auf Papier), Sekundärtext nicht
  unter 4.5:1 (WCAG 1.4.3 — die Gefahrenzone sind „verblasste" Grautöne).
- **Rubrizierung** (Buchtradition: rote Kapitelziffern/Initialen): ein tiefes
  Oxblood `#7A2E2E` für Links/Primäraktionen/Kapitelnummern.
- **Gold** `#A8842C` nur als Zierlinie/Folio-Akzent, nie als Textfarbe auf
  Papier (Kontrast).
- **Status in Buchsprache**: Erfolg = Tannengrün `#3F6B4F`, Warnung = Ocker
  `#9A6B1F`, Fehler = Rubrizierungsrot — die Flat-UI-Farben (#27ae60, #3498db…)
  entfallen ersatzlos.
- **Schließen/Nacht**: dunkler Ledereinband um die Seite herum (heutiges Plum
  vereinheitlicht); „Nachtlesung"-Modus (helle warme Tinte auf Braunschwarz)
  als eigene, bewusste Phase — der halbe `prefers-color-scheme`-Patch
  (theme.css:315) wird vorher entfernt.

### 4.2 Typografie

- **Mengentext**: eine Lese-Serife mit großer x-Höhe und echten Kursiven —
  **Literata** (für E-Book-Lesen entworfen, variabel, self-hostbar; Alternative
  Source Serif 4). 18–19 px, Zeilenhöhe 1,45, **max-width ~66ch** für Prosa;
  16 px/1,3 in dichten Werkzeugflächen.
- **Auszeichnung**: Cinzel NUR für Kapitel-/Displayköpfe und Kolumnentitel
  (Kapitälchen-Wirkung, +5–12 % Sperrung). **PirataOne wird aus dem Body
  entfernt** und höchstens als seltene Zier (Drop-Cap-Alternative) geführt;
  BadScript nur für „Marginalien"/handschriftliche Akzente.
- **Deutsch-Satz**: `lang="de"` + `hyphens: auto`; Flattersatz mit Trennung
  (nie Blocksatz ohne Trennung — deutsche Komposita).
- **Absätze** buchtypisch mit Erstzeilen-Einzug in narrativen Flächen, nicht
  Einzug + Abstand zugleich (Butterick).
- **Serife = Prosa, Sans = Werkzeug**: Der Schriftwechsel selbst markiert die
  Grenze zwischen Buchseite und Werkzeugfläche (ein System-Sans für Stat-Blöcke,
  Formulareingaben, Tisch-Controls).

### 4.3 Seitenmodell

- Zentrierter Textblock mit sichtbar großzügigen, leicht **asymmetrischen**
  Rändern (innen < oben < außen < unten — die Web-Übersetzung der klassischen
  Satzspiegel-Kanons). Der großzügige Rand ist das stärkste „Buchseiten"-Signal
  — billiger und robuster als jede Textur.
- **Kolumnentitel** (running header): kleine Kapitälchen-Zeile oben —
  „Kapitel II · Kampagnen — Die Nebelkrone"; bleibt beim Blättern stehen
  (`view-transition-name`).
- **Folio**: Seitenzahl im Fuß/Außenrand; Kapitel sind nummeriert, damit die
  Blätterrichtung stabil bedeutungsvoll bleibt.
- **Lesebändchen**: sichtbares Ribbon-Element = „Weiterlesen, wo du warst"
  (letzte Kampagne/Session).
- **Doppelseite nur ≥1200 px**, mobil strikt Einzelseite (Flipbook-Postmortem:
  Spreads sind auf Telefonen unbenutzbar). Breite Werkzeugansichten (Listen,
  Karten) nutzen die Goblin-Delve-Regel: Panels fluid, Prosa *innerhalb* auf
  ~66ch gekappt — nie die 720px-Korsett-Falle (GD Patches 107–111).

### 4.4 Bewegung (eine Engine)

- **View Transitions API** ist die einzige Engine. Same-document überall
  verfügbar (Chrome 111+/Safari 18+/Firefox 133+); cross-document als
  Progressive Enhancement; ohne Support: sofortiger Swap = korrekter Fallback
  gratis.
- **Der Umschlag**: nur bei Wechsel der Hauptansicht. 350–500 ms,
  `cubic-bezier(0.05, 0.7, 0.1, 1)` (emphasized-decelerate) rein,
  `(0.3, 0, 0.8, 0.15)` raus. Richtungslogik aus §3.6. Kolumnentitel + Folio
  persistieren via `view-transition-name`.
- Alles andere ≤200 ms Standard-Easing; einfaches Feedback ~100 ms.
- `prefers-reduced-motion: reduce` → Cross-Fade ~150 ms; zusätzlich In-App-
  Schalter. (WCAG 2.3.3; Vollbild-3D-Flips sind exakt die vestibulär
  problematische Bewegungsklasse.)
- **Gelöscht werden**: der GSAP-Reload-Flip in book-shell.js, die
  BookScene-Turn-Timelines als Navigations-Engine, die 📖/✨-Animation
  (book-animation.js), die Curtain-State-Machine in play.html (ersetzt durch
  EINEN zeremoniellen Umschlag beim Tischeintritt), die globale
  Pfeiltasten-Hijack-Navigation (Pfeile gehören auf einem VTT der Karte).
- Nie Daten/Eingaben hinter der Animation blockieren (View Transitions
  arbeitet nativ auf Snapshots).

### 4.5 Die Grenze: der Spieltisch

Der Tisch ist **keine Seite** — er ist die ausklappbare Karte/Battle-Mat. Beim
Eintritt ein letzter zeremonieller Umschlag; drinnen gilt: Buch-**Material**
bleibt (Papierton in Panels, Serifen in Journal/Chat-Prosa, Token-Set),
Buch-**Mechanik** endet (kein Paging, keine Spreads, keine Folio). Die heutige
Navy-Welt (play.html :root) wird auf das gemeinsame Token-Set umgezogen —
dunkle Tischfläche ist erlaubt (die „Karte" darf dunkel sein), aber aus
denselben Tokens abgeleitet, nicht aus einem Fremdsystem.

## 5. Struktur (Buch ↔ App)

| Buchelement | App | 
|---|---|
| Einband/Titelseite | Login (einmalige Zeremonie — hier darf es theatralisch sein) |
| **Inhaltsverzeichnis** | Dashboard: echte Kapitelliste mit Stand (Kampagnen, Charaktere, Kompendium, Spieltisch) statt Selbstbeschreibungs-Prosa |
| Kapitel | Hauptbereiche, nummeriert (Kapitel I Home/ToC, II Kampagnen, III Charaktere, …) |
| Seiten im Kapitel | einzelne Kampagne / Charakterbogen (Geschwister → blättern) |
| Kolumnentitel + Folio | persistente Ortsanzeige, bleibt bei Transitions stehen |
| Lesebändchen | „Weiterlesen": letzte Kampagne/Session, prominent auf dem ToC |
| Marginalien | Sekundärinfos/Progressive Disclosure am Seitenrand statt Modal-Flut |
| Ausklappkarte | der Spieltisch (§4.5) |

## 6. Abrissliste (konkret)

1. `theme.css:46` PirataOne-Body → Literata-System (Sofortmaßnahme).
2. theme.css in **alle** Templates, eine Ladereihenfolge; danach: ein
   Token-Set, Duplikate (`--vtt-primary`/`--vtt-plum`, `--vtt-accent`/
   `--vtt-gold`), Flat-UI-Statusfarben, Dark-Mode-Patch (315) entfernen.
3. book-animation.js löschen; book-shell-GSAP-Navigationsflip löschen;
   BookScene-Markup-Builder (book-scene.js:911–1140, zweite Render-Quelle)
   löschen; Curtains ersetzen.
4. Dreifach-Bindung auflösen: eine Navigations-API, `goTo()`-Kopien (4
   Templates, driftend) durch ein Modul ersetzen; Pfeiltasten-Hijack raus.
5. Dev-Chips („BookScene Runtime" …), Meta-Prosa, Grau-Kacheln raus; Inhalte
   (echte Zahlen, echte Aktionen, Lesebändchen) rein.
6. Sprach-Pass: Deutsch mit echten Umlauten; Chrome (Nav, Buttons, Login-Form)
   zuerst; Reste als benannte Schuld gelistet.

## 7. Mess-Gates (Robots, die durchfallen können)

- **Layout-Monotonie**: breiteres Fenster ⇒ nie kleinere Inhaltsfläche
  (GD-Invariante); Messpunkte ober- UND unterhalb jedes Breakpoints, inkl.
  <1440 px und Mobil (svh, Thumb-Zone).
- **Kontrast-Pin**: axe-core/eigener Check ≥4.5:1 für allen Text auf Papier,
  besonders Sekundärgrau.
- **Ein-Engine-Invariante**: Robot navigiert per Klick, Tastatur und Link —
  alle drei müssen dieselbe Transition auslösen (Regression der
  Dreifach-Bindung).
- **Sprach-Lint**: `oeffnen|zurueck|wuerfel|loeschen`-Grep = 0 in Templates;
  englische Chrome-Strings-Liste schrumpft monoton.
- **Reduced-Motion-Pin**: mit emulierter Präferenz keine Transform-Animation
  > 0 bei Navigation.
- **Token-Lint**: keine neuen Hex-Literale in Templates/CSS außerhalb
  theme.css (heute ~226 — Zahl darf nur sinken).

## 8. Phasenplan (Vorschlag)

- **B1 — Fundament (sofort, geringes Risiko):** Body-Font-Hotfix; theme.css
  überall laden, Ladereihenfolge vereinheitlichen; EIN Token-Set inkl.
  Buch-Statusfarben; Literata vendoren; Sprach-Pass fürs Chrome (Nav, Login,
  Buttons) mit echten Umlauten. Größter sichtbarer Gewinn pro Risiko.
- **B2 — Seitenmodell:** Satzspiegel (Ränder, 66ch), Kolumnentitel + Folio,
  Dashboard → Inhaltsverzeichnis + Lesebändchen, Meta-Prosa/Grau-Kacheln/
  Dev-Chips raus, Marginalien-Muster für Sekundärinfo.
- **B3 — Eine Blätter-Engine:** View Transitions API; Richtungslogik;
  Abriss der vier Alt-Engines und der Dreifach-Bindung; Reduced-Motion +
  Schalter; Pfeiltasten frei für die Karte.
- **B4 — Tisch-Material:** play.html auf das Token-Set; Eintritts-Umschlag
  statt Curtains; Journal/Chat-Prosa in Serife; Karte darf dunkel bleiben.
- **B5 — Nachtlesung + Gates:** bewusster Dunkelmodus; alle §7-Gates in
  tools/robots verdrahtet; Restsprach-Schuld abgetragen.

Jede Phase: voller Pytest + Robot-Suite + Screenshot-Review vor Commit,
Deploy einzeln (Haus-Disziplin).

## 8b. Mobile (Erweiterung 2026-08-24)

Vollständiger Telefon-Audit + Designrichtung in
**MOBILE_AUDIT_BUCH_UI_2026-08-24.md**: Der Spieltisch ist auf Telefonen
heute unbenutzbar (46px-Karten-Schlitz, Würfelknopf off-screen, Chat
zero-size); die Buchseiten überleben strukturell. Kernentscheidungen:
Ein Portrait-Telefon ist die reinste Form der Einzelseite (B2 wird
mobile-first gebaut); der Tisch bekommt zwei Telefon-Modi — Spielerbuch
(Portrait-Companion: Bogen/Würfel/Chat/Mini-Karte, neue Phase B6) und
Voller Tisch (Landscape, Daumenzonen-Leiste, Phase B7); Sofort-Fix-Wurf
plus Telefon-Viewports/Tap-Ziel/Daumenzonen-Gates in den Robots.

## 9. Quellen

- NN/g: Skeuomorphism; Flat Design; Animation Duration; Animation Purpose;
  Progressive Disclosure; F-Pattern (nngroup.com/articles/…)
- Butterick's Practical Typography: Summary of Key Rules; Line Length; Line
  Spacing (practicaltypography.com)
- Bringhurst-Zusammenfassungen: inkwell.ie/typography/bringhurst.html;
  oert.org/en/typography-and-proportions/
- Material Design: M2 Duration & Easing; M3 Motion Tokens (m3.material.io)
- MDN: View Transition API; Browser-Support-Tracker
  (events-3bg.pages.dev/jotter/in-all-major-browsers/)
- W3C: WCAG 2.2 SC 1.4.3 (Kontrast), SC 2.3.3 + Technique C39
  (prefers-reduced-motion)
- Flipbook-Postmortems: FlipViewer-Usability-Studie (ResearchGate);
  makethingsaccessible.com (Flipbook-Accessibility); prospectus.plus
  (Mobil-Kritik); turn.js/StPageFlip als Anti-Referenz für Content-Traps
- Apple-Fallstudie: iMore/AppleInsider zur iOS-7-Abkehr vom Skeuomorphismus
  (und dem Überleben des Page-Curls in Books)
- Intern: goblin_delve_bot/docs/GUI_AUDIT_2026-08-18.md, GUI_AUDIT_2,
  RCA_COCKPIT_BREAKPOINT_2026-08-19.md, MOBILE_GUI_RESEARCH_2026-08-19.md,
  Patches 106–133; VTT-Buch-Shell-Audit vom 2026-08-24 (Agentenbericht,
  Zahlen in §2)
