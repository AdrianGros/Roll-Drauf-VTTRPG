# Mobile-Audit & Designrichtung Telefon (2026-08-24)

Erweiterung des Designbriefs (DESIGNBRIEF_BUCH_UI_2026-08-24.md) um die
Telefon-Perspektive. These des Eigentümers, vom Audit bestätigt: Der Markt
für Online-TTRPGs ist nicht für Mobile-Play optimiert — hier können wir
legitim innovieren.

Messmethode: Playwright, echte Touch-Kontexte, iPhone-14-Metrik
(390×844 Portrait, 844×390 Landscape, DPR 3), eingeloggt, mit aktiver
Karte + Token auf dem Tisch. Harte Messwerte, keine Eindrücke.

---

## 1. Messergebnisse (Stand nach Phase B1)

| Ansicht | H-Overflow | Scrollhöhe | Tap-Ziele <44px | Befund |
|---|---|---|---|---|
| Login | 0 | 3.588px (4,3 Screens) | 4 (Nav 38px) | funktioniert; Registrierung am Telefon erfolgreich |
| Übersicht | 0 | **8.955px (10,6 Screens)** | 4 | strukturell intakt, aber Endlos-Kolumne |
| Kampagnen | 0 | 4.463px | 4 | wie Übersicht |
| Charaktere | 0 | 4.491px | 4 | wie Übersicht |
| **Spieltisch Portrait** | 0 | — | **13** | **unbenutzbar, s.u.** |
| **Spieltisch Landscape** | 0 | — | **18** | **unbenutzbar, s.u.** |

**Spieltisch Portrait (390×844), im Detail:**
- Karten-Viewport: **46×563px** — ein 46 Pixel breiter Schlitz. Auto-Fit
  rechnet die 700px-Karte auf das 20%-Zoom-Minimum und selbst das passt
  nicht. Der Rest der Breite geht an Buch-Chrome (Einband-Ränder,
  Seitenrahmen) und die absolute Werkzeugleiste.
- Würfelknopf: bei x=537 mit 445px Breite — **vollständig off-screen**
  (Viewport 390px). Chat-Eingabe und Senden-Knopf: **zero-size**
  (Sidebar-Layout kollabiert). Karten-Upload-Knopf: zero-size.
  FIT-Knopf: x=−38, halb außerhalb.
- Werkzeugleiste (SEL/PAN/TOK/BACK): 36×44px-Knöpfe, per Media-Query
  absolut positioniert, **überlappen einander als Doppelspalten-Stapel**
  (Screenshot-Befund).
- Nav-Ribbon: Buttons laufen rechts aus dem Bild („KAMPA…", „SPIELT…").
- `#zoomRange` mit 13,3px Schrift → iOS-Auto-Zoom beim Fokussieren.
- Landscape ist NICHT besser: Karten-Viewport 42×203px, Würfelknopf
  below-fold UND off-screen.
- Kein `svh` im gesamten CSS (Goblin-Delve-Lektion: `100vh` lügt auf
  Telefonen — Browser-Chrome verdeckt den unteren Streifen).

**Buchseiten (Login/Übersicht/Kampagnen/Charaktere):** strukturell
überlebensfähig — kein horizontaler Overflow, Formulare bedienbar,
Literata gut lesbar auf 390px. Aber: Desktop-Zweispalter stapelt zur
10-Screen-Kolumne; der Einband/Buchrücken-Backdrop verschwendet ~15 %
der ohnehin knappen Breite; Nav-Buttons clippen; 38px-Tap-Ziele.

## 2. Die Marktlücke (warum hier Innovation legitim ist)

Roll20 und Foundry sind Desktop-Software im Browser: Maus-Hover,
Rechtsklick-Menüs, dichte Toolbars, Multi-Panel-Layouts. Auf dem Telefon
sind sie praktisch unbenutzbar; die verbreitete Erwartung ist „für VTT
brauchst du einen Rechner". Genau deshalb ist Telefon-Play eine echte
Lücke — und zwei reale Nutzungssituationen warten darauf:

1. **Am physischen Tisch**: Alle sitzen zusammen, niemand will Laptops
   aufklappen — jede*r hat ein Telefon. Bogen, Würfel, Initiative, HP.
2. **Remote vom Sofa**: Mitspielen ohne Schreibtisch — lesen, würfeln,
   chatten, Karte ansehen.

Unser struktureller Vorteil: kein Legacy-Desktop-Publikum, und eine
Design-Metapher, die auf dem Telefon **stärker** wird statt schwächer.

## 3. Die zentrale Design-Einsicht

**Ein Portrait-Telefon ist eine einzelne Buchseite.** Das Buch-Modell
des Designbriefs (Einzelseite < 1200px; Doppelseite ist die
Desktop-Erweiterung) bedeutet: Mobile ist nicht die „geschrumpfte"
Version — es ist die *reinste* Form der Metapher. Seitenverhältnis,
Blättern per Geste, ein Kapitel nach dem anderen: das ist ein Buch in
der Hand. Konsequenzen:

- **B2 (Seitenmodell) wird mobile-first gebaut**: Die Einzelseite ist
  der Grundzustand, der Desktop-Spread die Erweiterung — nicht
  umgekehrt. Kolumnentitel + Folio funktionieren identisch.
- **Blättern = horizontale Wisch-Geste** (plus Tap auf Blätterkanten);
  View Transitions API funktioniert auf allen mobilen Browsern.
  Reduced-Motion gilt unverändert.
- Der Einband-Backdrop verschwindet auf dem Telefon: die Seite IST der
  Screen (Ränder als Satzspiegel innerhalb der Seite, nicht als
  Bühnenbild außenrum).

## 4. Der Spieltisch auf dem Telefon: zwei Modi

Die Ausklappkarten-Grenze aus dem Designbrief (§4.5) gilt auch mobil —
aber das Telefon bekommt zwei bewusste Modi statt eines geschrumpften
Desktops:

### 4a. Spielerbuch (Portrait — die eigentliche Innovation)
Das Telefon ist das **Handbuch des Spielers**, nicht der Tisch:
- Seiten (per Blättern erreichbar): **Bogen** (HP, Werte, Zustände des
  eigenen Tokens live), **Würfel** (große Würfelfläche, letzte Würfe
  aller — inkl. Beyond20-Karten), **Chat/Journal**, **Karte**
  (read-mostly Mini-Ansicht: sehen wo man steht, eigenen Token per
  Tap-Tap versetzen — kein Präzisions-Drag).
- Alles hängt am existierenden Echtzeit-Layer (state:snapshot,
  external:roll, chat) — es ist eine andere ANSICHT desselben Tisches,
  kein neues Backend.
- Damit ist Telefon-Teilnahme an jeder Session sofort vollwertig für
  Spieler; die DM-Werkzeuge (Upload, Ebenen, Fog) bleiben Desktop-first.

### 4b. Voller Tisch (Landscape, Stufe 2)
- Karte full-bleed, `100svh`, kein Buch-Chrome.
- Untere **Daumenzonen-Leiste** (Goblin-Delve-Mobile-Lektion):
  Würfel · Token · Chat · Menü — Panels als Bottom-Sheets, nie als
  schwebende Widgets über der Karte.
- Pinch-Zoom auf der Karte (Pointer-Events existieren schon),
  `touch-action: none` auf dem Karten-Viewport, `manipulation` auf
  Controls (Doppeltipp-Zoom frisst sonst Aktionen),
  `overscroll-behavior-y: contain` (Pull-to-Refresh mitten im Kampf
  „fühlt sich exakt wie ein Crash an").

## 5. Sofort-Fixes (unabhängig von B2+, kleine Klasse)

1. Nav-Ribbon: umbrechen statt clippen; Tap-Ziele auf ≥44px.
2. `#zoomRange`/alle Inputs: `font-size ≥ 16px` (iOS-Zoom-Trigger).
3. Spieltisch < 700px Breite: Werkzeugleisten-Media-Query reparieren
   (der überlappende Stapel), Widgets/Sidebar full-width als Sheets.
4. `100vh` → `100svh` in play.html.
5. Der 46px-Karten-Schlitz: Buch-Chrome (Einband-Ränder) auf dem
   Spieltisch unter 1040px komplett abwerfen — die Ausklappkarte
   braucht den ganzen Screen.

## 6. Mess-Gates (Erweiterung von Designbrief §7)

- Robot-Viewports erweitert um **390×844 und 844×390** (und je einen
  Punkt ober-/unterhalb jedes Breakpoints — GD-Monotonie-Invariante
  gilt auch abwärts: schmaleres Fenster ⇒ nie horizontaler Overflow).
- **Tap-Ziel-Gate**: interaktive Elemente ≥44px auf Touch-Viewports
  (heutige Zahl: 13–18 Verstöße auf dem Tisch — darf nur sinken).
- **Fold/Reichweite-Gate**: Würfeln, Chat-Senden, eigener Token — auf
  jedem Viewport sichtbar UND im unteren Drittel (Daumenzone) auf
  Touch.
- **Kern-Loop-Gate Spielerbuch**: Bogen sehen → würfeln → Ergebnis
  landet bei allen — als Fullsession-Erweiterung mit Telefon-Kontext.
- `svh`-Pin: kein `100vh` in Play-Styles.

## 7. Phasen-Einordnung

- **B2** wird mobile-first umgesetzt (Einzelseite als Grundzustand) —
  kein separates „Mobile-Projekt", sondern dieselbe Phase.
- **Sofort-Fixes (§5)** laufen als eigener kleiner Wurf vor/mit B2.
- **B6 (neu): Spielerbuch-Modus** (Portrait-Companion, §4a) — nach B4,
  auf dem dann vereinheitlichten Tisch-Material.
- **B7 (neu): Voller Tisch Landscape** (§4b) — nach B6, wenn das
  Spielerbuch die Echtzeit-Ansichten bewiesen hat.

Quellen: Goblin Delve MOBILE_GUI_RESEARCH_2026-08-19 (svh, Daumenzone,
touch-action, overscroll; Patch-117-Regression), RCA_COCKPIT_BREAKPOINT
(Beide-Seiten-des-Breakpoints-Messung), Designbrief-Quellen (§9),
eigene Messreihe 2026-08-24 (dieses Dokument, Skript: Playwright-Probe
mit Touch-Kontexten; Screenshots im Sessionarchiv).
