# DAD-M DISCOVER: Lösungsrecherche U01/U05/U06, U09–U11, U12, U14

**Status:** Der Discover-Teilbericht ist fertig. Ich habe nichts geändert, keine Datei geschrieben, keinen Test ausgeführt und keinen Browser verwendet. Der Plan-Modus war aktiv; die Plan-Datei habe ich nicht angelegt, weil der Bericht laut Auftrag nur in diese Antwort gehört.

**Input:** Codex-Auftrag Scope A–D und das Feedbackprotokoll vom 16.11.2026. Quellbasis ist der Arbeitsbaum `3939766e7`; die App entspricht `d4ff7e4fe`.

**Geladen:** `AGENTS.md`, `AI_BIOS.md`, `file-registry.yaml`, die Standardkarten (core-rules, phase-map, deliverables-min, governance-min) und die discover-card.

**Artefakt:** dieser Bericht, Aufbewahrung *permanent* über die Codex-Ablage.

**Kennzeichnung:**
- **[R]** Fakt aus dem Repository
- **[Q]** externe Primärquelle
- **[S]** eigene Schlussfolgerung

Die Webquellen habe ich am 16.11.2026 über ein zusammenfassendes Abrufwerkzeug gelesen. Vor einer normativen Übernahme in Apply sollten die Zitate am Original gegengeprüft werden.

---

## A. U01/U05/U06: Book-UI, Palette, Sicht/Licht

### Codebefund

**Drei verschiedene „Rahmen“-Stufen existieren [R]:**

1. **Echte Buchlaufzeit `BookScene`.** Sie rendert im selben Dokument und kennt nur `login`, `signup`, `register`, `dashboard`, `campaigns`, `characters` und `character-sheet` (`vtt/static/js/book-scene.js:107-161`).
   - Bei jedem Routenwechsel ersetzt sie das `innerHTML` der Szene (`book-scene.js:2472-2481`).
   - Für Query-/Intent-Routen und fehlende Vorlagen fällt `pageTurn` auf eine volle Navigation zurück (`book-scene.js:2815-2826`).
   - Auch `vtt-main-nav.js:67` behandelt nur diese drei Routen als „Book“.
2. **Dokument-Buchseite ohne Laufzeit.** `play.html:2459-2473` nutzt die Klassen `book-dashboard-page book-route-page book-workspace-page` samt Topbar und Ribbon aus `book-scene.css`. Gleichzeitig hebt es dort den Deckel `min(1680px)` (`book-scene.css:582`) für den Vollbild-Canvas auf (`play.html:118-131`). Das ist ein vorhandenes Muster für einen geteilten Rahmen ohne `BookScene`.
3. **Nur Ribbon:**
   - `conversations.html:11-13` und `atlas.html:5` (`body.regelwerk-page` mit `regelwerk-site-header`; das Ribbon wird über `vtt-main-nav.js:197-202` eingespeist)
   - `regelwerk.html:17-41` (eigenes Reader-Layout)
   - `regelwerk-compendium.html:20-26`
   - Creation Engine: `.ce-page` mit eigener `book-dashboard-topbar` (`creation-engine.html:28-46`)
   - Karten: `mapmaker.html:6-11` leitet auf das statische `/static/mapmaker/index.html` weiter, also kein Jinja (`.mm-app` :19, `.vtt-map-nav` :70, `main.mm-stage` :108).

**Eagle-Dialoge [R]:** Sie werden in `#ce-eagle-mount` außerhalb von `.ce-page` montiert (`creation-engine.html:146`). `.eh-window` ist `position:fixed; z-index:100; top:5rem; right:1rem` (`vtt/static/eagle-homebrew/shim.css:4`), der Kopf ist ziehbar (`shim.css:13`).

**Deep Links [R]:**
- Regelwerk über Hash (`regelwerk-reader.js:129-131`, `:409-410`)
- Compendium über `?entry=` mit `pushState`/`popstate` (`regelwerk-compendium.js:356-368`, `:523-544`)
- Gespräche über `?id=` bzw. `?campaign_id=` (`private-conversations.js:98`, `:176`)
- Atlas über `?world=` (`atlas.js:5`)

**Farben [R]:**
- Die Night-Tokens sind warmbraun (`display-preferences.css:12-16`, u. a. `#211a17`, Plum `#6f292c`).
- Leder-/Verkohlungsverläufe stehen in `:41-51`.
- Der Night-Standardakzent ist `#f29a90` (`display-preferences.js:47`). [S] Das erklärt plausibel die „pinke“ und „ledrige“ Wirkung.
- Laufzeitprüfungen existieren bereits: Ein Branding-Akzent wird nur bei ≥4,5:1 übernommen (`:49`), die Action-Textfarbe wird nach Kontrast gewählt (`:52`). Es gibt die Akzentoptionen `default`, `bronze` und `teal` (`:7`, `:78`).

**Harte Playtable-Farbregel [R]:**
- Der Playtable bindet in beiden Themes ein eigenes dunkles Paar (`display-preferences.css:122-135`).
- Ausdrücklich gilt: „Canvas, grid, SVG layers and map/token/user content … keep their own colors“.
- Helle Schrift `#fdfaf3` auf aktiven Buttons ist hart codiert (`:160-161`).
- Den Test dazu gibt es: `tests/test_play_presentation_browser.py:113` (`test_play_chrome_does_not_recolor_canvas_or_map_layers`).
- Die Messfarben `#ffd23f`/`#241a12` sind lokal in `play.html:1018-1040`.

**U06 [R]:**
- Der Toolbar-Button `btnVisionToggle` blendet nur Wand-/Licht-Markierungen aus (`play-dm.js:150-160`). Sein Titel lautet „Wand-/Licht-Markierungen ein-/ausblenden“, sein Label ist der Key `u_696b3e46c7d5` = „Sicht“/„Sight“ (`vtt/play/surfaces/dm.json`, Slot `map-tools`).
- **Derselbe Key** beschriftet im Wand-Popover die Eigenschaft „Sicht: Blockiert“ (`wallEditSight`). „Licht“/„Light“ ist genauso doppelt belegt (`u_97999345b7b1`).
- [S] Ein Label trägt also zwei Bedeutungen. Das „Side“ im Transkript passt zum englischen „Sight“; das bleibt Annahme.

### Optionen U01

| Option | Nutzen | Aufwand | Risiken / Voraussetzungen |
|---|---|---|---|
| **A1 Gemeinsame Dokument-Buchschale** nach dem Muster von `play.html`. Modi: *reader* (Regelwerk, Compendium, Gespräche), *workspace* vollflächig (Karten, Atlas), *studio* (Creation Engine; Eagle-Fenster bleiben außerhalb). | Echter gemeinsamer Markup-Rahmen; jede Seite behält ihren JS-Lebenszyklus, ihre URLs und Deep Links. | mittel | Der Mapmaker ist statisches HTML: Die Schale muss dort per JS eingespeist oder doppelt gepflegt werden (`vtt-main-nav.js` speist bereits das Ribbon ein). Die Kopfhöhe kollidiert evtl. mit `.eh-window top:5rem`. Voraussetzung: Die U05-Tokens stehen. |
| **A2 BookScene-Laufzeit um sechs Routen erweitern** | Durchgängige Seitenwechsel im selben Dokument | hoch | Die `innerHTML`-Ersetzung zerstört Eagle-/Canvas-/Polling-Zustand. Deep Links müssten in die Routing-Logik von `BookScene` übertragen werden. Faktisch eine neue gemeinsame Laufzeit, also nahe am ausgeschlossenen Frontend-Rewrite. |
| **A3 Nur Theme/Ribbon angleichen** | Gering, schnell | gering | Ist kein echter Buchrahmen; die Owner-Erwartung wird wahrscheinlich verfehlt. Taugt als U05-Vorstufe. |

**PRÜFKANDIDAT: A1**, mit A3 als vorgezogenem Farbslice.
- Begründung [S]: Es gibt ein existierendes Muster (`play.html`), keine Lebenszykluszerstörung, und Deep Links bleiben erhalten.
- A2 kollidiert mit eingebetteten Editoren und mit der Vorgabe „kein Rewrite“.
- Keine der Optionen benötigt die G1-Engine.

### Optionen U05

- **P-a: Vorhandene semantische Tokens umbelegen.** Gemeint sind `--ui-paper/panel/soft/ink/muted/line/accent/action-*` im Night-Theme und in der Playtable-Neubindung (`:128-135`, `:163-165`), dazu abgeleitete Tönungen. Die Lederverläufe entfallen. Aufwand gering bis mittel. Restfarben bleiben in Legacy-CSS (`docs/VTT_BUILD_REPORT_2026-08-24.md:193`).
- **P-b: Drittes Theme neben Night.** Das erleichtert ein Rollback, verdoppelt aber die Testmatrix.

**PRÜFKANDIDAT: P-a.**

### Palette: OFFEN

- Für „Edo Purple, Mouse Gray, Ink Black, Natural“ liegt mir **keine Primärquelle und kein Farbwert** vor. Ich nenne bewusst keine Hexwerte.
- [S, unbestätigt] Die Namen könnten traditionellen japanischen Farbnamen entsprechen. Eine mögliche normative Quelle wäre JIS Z 8102; geprüft habe ich sie nicht.
- [S] Bedingt durch die Werte gilt:
  - Ein mittleres „Mouse Gray“ als Text auf „Ink Black“ könnte 4,5:1 verfehlen.
  - Ein dunkles „Edo Purple“ eignet sich eher als Fläche mit „Natural“-Text als als Textfarbe.
  - Eine Grautönung kann nicht zugleich Fläche und Trennlinie mit 3:1 sein, dafür braucht es abgeleitete Stufen.

**Messziele [Q]:**
- WCAG 2.2 SC 1.4.3: Text ≥4,5:1; große Schrift (≥24px oder ≥18,5px fett) ≥3:1.
- SC 1.4.11: UI-Grenzen, Zustände und Fokus ≥3:1 gegen die angrenzende Farbe.
- Werte werden nicht gerundet: 4,499 besteht nicht.
- Gemessen wird gegen den tatsächlich gemalten Hintergrund.

### Optionen U06

- **(1) Bedeutungen trennen.**
  - Der Overlay-Schalter heißt „Wände & Lichter anzeigen“ / EN etwa „Show walls & lights“.
  - Die Wandeigenschaften heißen „Blockiert Sicht“ / „Blockiert Licht“.
  - „Spielerperspektive“ bleibt für die künftige U07-Vorschau reserviert.
  - Getrennte Katalog-Keys.
- **(2) Nur Tooltips anpassen.** Die Mehrdeutigkeit bliebe.

**PRÜFKANDIDAT: (1).** Die EN-Begriffe sind Apply-Frage.

### Apply-Fragen A

1. Quelle und Hexwerte der vier Farben?
2. Zuordnung zu Fläche, Text, Linie, Akzent und Zustand? Was ist mit Danger/Success/Warning, die nicht in der Palette sind?
3. Bleiben die Akzentoptionen `bronze`/`teal` und der Branding-Akzent?
4. Gilt die neue Palette auch fürs Paper-Theme?
5. Werden die Messfarben (SVG im Canvas) von der Palette ausgenommen? Die harte Regel nimmt SVG-Layer bisher aus.
6. Was heißt „Buchdarstellung“ genau: Folio, Running Head, Seitenfläche?
7. Bleibt der Mapmaker statisch?

### Akzeptanz-/Negativmatrix A

| # | Prüfung | Messbar |
|---|---|---|
| 1 | Sechs Nav-Einträge bei 1280 und 390px | Gemeinsames Rahmenelement vorhanden; `aria-current` korrekt; `scrollWidth ≤ clientWidth` |
| 2 | Deep Links | `/regelwerk#…`, `/regelwerk/compendium?entry=…`, `/conversations?id=…`, `/atlas?world=…` zeigen nach Reload denselben Zustand |
| 3 | Eagle | Fensterkopf liegt vollständig im Viewport und ist nicht vom Rahmen verdeckt; Drag funktioniert; Fokus kehrt nach Schließen zurück |
| 4 | Canvas-Breite | Karten/Atlas bei 1440px mindestens so breit wie vorher |
| 5 | Kontrast | Alle Textpaare ≥4,5:1 (groß ≥3:1); Grenzen/Fokus ≥3:1; Paper und Night |
| N1 | Canvas, Raster, Karten und Tokens nicht umgefärbt | Bestehender Test :113 bleibt grün |
| N2 | Fensterpositionen und Token-/Fensterspeicher | Unverändert nach Theme-Wechsel |
| N3 | Player-Komposition | Lädt durch Rahmenänderungen keine DM-Fragmente |
| N4 | U06 | Kein Katalog-Key mit zwei Funktionsbedeutungen |

### Slices A

1. Palettenwerte entscheiden und Kontrasttabelle (nur Dokument)
2. Token-Umbelegung Night + Playtable-Chrome
3. U06-Labels
4. A1 *reader*: Gespräche, Regelwerk, Compendium
5. A1 *workspace*: Atlas, Karten
6. A1 *studio*: Creation Engine

---

## B. U09/U10/U11: Messen, Raster, Select/Pan

### Codebefund U09 [R]

**Zustand und Snap:**
- `measureSnapEnabled = true` als Vorgabe (`play-ui.js:104-108`).
- Der Snap-Button und die Formauswahl erscheinen nur beim Messwerkzeug (`:1080-1083`). Der Button heißt „Raster“, EN **„Grid“**, mit dem Titel „Rastereinrasten für Messungen an/aus“ (`play.html:2759`, Katalog `u_4e92822e2798`).

**Eingabe:**
- Maus: Wegpunkt per Klick (`:1351-1358`).
- Touch: Langdruck 550ms mit 12px Toleranz (`:1319-1350`).
- Vorschau bei `pointermove` (`:1359-1365`); Rechtsklick entfernt den letzten Punkt (`:1366-1370`).
- Formen sind **Klick-Klick, kein Ziehen**. Ein dritter Klick setzt zurück (`:1423`).

**Koordinaten:**
- `_worldPointFromEvent` rechnet `(client − mapWorld.getBoundingClientRect().left) / (zoom/100)` und klemmt an den Kartenrand (`:1373-1384`).
- Zoom ist `transform: scale()` auf `#mapWorld` (`:1172`).
- [S] Für reine Skalierung ist diese Rechnung konsistent. Rahmen oder Padding von `#mapWorld` habe ich nicht geprüft; einen Fehler reproduziert habe ich nicht.

**Snap:**
- Rundet auf **Rastereckpunkte** und kennt keinen Versatz (`:1392-1401`).
- Mit Snap ist der Ursprung also nie die Cursorposition. Ohne Snap ist er exakt.

**Kopplung:**
- Der Snap-Schalter wechselt zugleich die Diagonalregel: max(dx,dy) statt euklidisch (`:1403-1412`).
- Formen messen dagegen immer euklidisch (`:1458-1468`).
- [S] Unter Snap weichen Linie und Kreis damit voneinander ab.

**Beschriftung:**
- Formen beschriften am Ursprung `(a.x+10, a.y−10)` (`:1470`); die Linie zeigt „Gesamt“ am letzten Punkt (`:1488`).
- `.measure-label` hat `font-size:12px` (`play.html:1032-1040`) und liegt in `#measureLayer` innerhalb des skalierten `#mapWorld` (`play.html:2520-2525`).
- [S] Bildschirmgröße = 12px × Zoom, also 2,4px bei 20% und 36px bei 300%.
- Der Radius steht nicht außen am Kreis.

**Quadrat:**
- `side = max(|dx|,|dy|)`, an der Ecke `a` verankert; der Quadrant springt mit dem Vorzeichen (`:1463-1464`).
- [S] Bei Diagonalen nahe den Achsen und beim Einrasten auf ganze Felder kann es springen. Plausible Ursache für „janky“, **nicht reproduziert**.

**Rastergröße inkonsistent:**
- Darstellung: `max(16, grid_size || 70)` (`:4318`).
- Messen: `grid_size || 0` sowie `none`/`gridless` → 0 (`:1386-1390`).
- Das Backend akzeptiert nur `square` (`campaigns/routes.py:1071`, `:1168`).

### Codebefund U10 [R]

- **Modell:** nur `grid_type`, `grid_size` (`models/campaign_map.py:18-19`). Kein Versatz, keine Farbe/Deckkraft, kein Sichtbarkeitsschalter. Der Rasterlayer wird immer gezeichnet (`play-ui.js:4336`).
- **Kampagnenroute `PUT /campaigns/<id>/maps/<id>`** (`campaigns/routes.py:1134-1204`): prüft `_is_dm(campaign, user.id)` auf Kampagnenebene, **ohne Tischkontext**, ohne Socket-Broadcast, 30/h.
- **Maßstabsroute als Gegenmodell** (`play/presentation.py:22-54`):
  - Tischkontext `g.table_context` und `is_operator_role(current_role(...))`
  - Revisions-CAS (Versionsvergleich) und Event `scene:scale_updated`
  - Tests: `tests/test_map_scale_contexts.py:18/30/40`, darunter „owner as player cannot calibrate“
  - UI in `play-dm.js:27-49`
- **Rastergröße wirkt auf mehr als die Anzeige:** auf Sichtzellen (`vision.py:43` `cell_of`; `service.py:720`), auf Token-Snapping (`play-ui.js:4890`) und auf die Platzierung (`:1510-1513`). Beim Import gilt 16–300 (`map_library.py:68`).
- **Hypothese [S]:** Der vom Owner geklickte „Grid“-Einstieg war wahrscheinlich dieser Snap-Toggle. Er reagiert nur über eine Klassenänderung; ein Einstellungsmenü existiert nicht. Nicht reproduziert.

### Codebefund U11 [R]

- **Pan:** Werkzeug `pan` mit linker Taste oder mittlere Taste in jedem Werkzeug, mit Pointer Capture (`play-ui.js:1266-1293`).
- **Touch:** zwei Finger = Pinch-Zoom und Pan (`:1211-1240`); `touch-action:none` am Viewport (`play.html:528-536`).
- **Token-Drag:** außer bei Mess- und Pan-Werkzeug (`:4799-4800`).
- **Tastatur:** keine Werkzeugkürzel gefunden. Die Zifferntasten gehören der Hotbar und haben einen Fokus-Guard (`:2520-2544`).
- [S] Leeres Ziehen im Select-Werkzeug hat keinen Handler (Grep, nicht im Browser geprüft). Ein-Finger-Pan geht dort also nicht.
- Der Katalog übersetzt „Bewegen“ mit **„Pan“** (`u_5f489a216d95`). Das stützt die Annahme Pen = Pan; sie bleibt bis zur Bestätigung Annahme.

### Externe Quellen B [Q]

- **MDN Pointer Events:**
  - Capture lenkt Folgeereignisse auf das Element und endet implizit bei `pointerup`/`pointercancel`.
  - `pointercancel` kommt u. a., wenn der Browser die Geste als Pan/Zoom deutet; `touch-action:none` verhindert das.
  - `isPrimary` und `pointerType` (`mouse`/`pen`/`touch`) unterscheiden die Geräte.
- **Foundry Measurement:**
  - Das Lineal startet per Klick bei aktivem Werkzeug (Taste R).
  - **Shift beim Wegpunkt unterdrückt Snap.**
  - Rechtsklick entfernt den letzten Wegpunkt.
  - Rechteck-Template: Ursprung ist eine Ecke und gehört zur Fläche.
- **Foundry Scenes:**
  - Rastergröße in px pro Feld, Grid Scale als Einheitentext.
  - „Offset Background (X/Y)“, Farbe/Deckkraft (Deckkraft 0 = unsichtbar).
  - Grid Alignment Tool und Grid Configuration Tool mit Live-Vorschau.
- **Foundry API v14:** `shiftX`/`shiftY` und `padding` sind Felder der Scene selbst, nicht des Grid-Schemas.

### Optionen U09

- **M1 Minimal:** Klick-Klick bleibt. Die Beschriftung wird gegenskaliert (`font-size/scale`) oder in einen Bildschirm-Overlay gelegt; Radius außen am Punkt b, Distanz am Cursor; Quadrat-Anker stabil. *Aufwand gering; Risiko: „Aufziehen“ bleibt unerfüllt.*
- **M2 Ziehbasiert:**
  - `pointerdown` setzt den Ursprung exakt am Cursor (oder nach der Snap-Regel), `pointermove` zeigt die Vorschau, `pointerup` schließt ab.
  - Pointer Capture; Shift schaltet Snap temporär um (Foundry-analog).
  - Klick-Klick und Langdruck bleiben für Touch und Tastatur.
  - Getrennte Schalter für „Punkt einrasten“ und Diagonalregel; Beschriftung in Bildschirmgröße.
  - *Aufwand mittel. Risiken: Konflikt mit Pinch/Pan, Doppelplatzierung Klick/Pointer.*
- **M3:** M2 plus eine eigene reine Geometriefunktion pro Form mit expliziter Snap-Politik (Ecke/Mitte/keine). *Aufwand mittel bis hoch, am besten testbar.*

**PRÜFKANDIDAT: M2**, mit reinen Funktionen innerhalb des bestehenden Messabschnitts. Erfüllt alle vier Punkte, ohne neues Modul vorauszusetzen.

### Optionen U10

- **G1 Nur klarstellen:** Den Snap-Button umbenennen, z. B. „Einrasten“ / „Snap“. *Gering; behebt die vermutete Verwechslung, liefert aber kein Rastermenü.*
- **G2 DM-Rasterdialog am Tisch als Kartenparameter:**
  - Mindestens Größe, ggf. Sichtbarkeit/Deckkraft, gemeinsam mit dem vorhandenen Maßstab.
  - Neuer **Tischkontext-Endpunkt nach Muster `presentation.py`**: Operatorrolle, Revisions-CAS, Socket-Event.
  - **Nicht** die Kampagnenroute wiederverwenden.
  - *Aufwand mittel.*
- **G3 Kalibrierwerkzeug:** Ein Feld aufziehen, daraus Größe und Versatz ableiten. Braucht ein Versatzschema, das in Darstellung, Snapping, Sicht und Platzierung wirkt. *Aufwand hoch.*

**PRÜFKANDIDAT: G2 + G1** (Label-Klarstellung immer). G3 nur, wenn Apply einen Versatz bestätigt.

### Optionen U11

- **S1 Getrennte Werkzeuge bleiben,** dazu Space halten = temporär Pan und Tastaturkürzel. *Gering.*
- **S2 Select pannt bei leerem Ziehen,** Token-Ziehen bleibt auf Tokens. Pan-Werkzeug wird „nur verschieben“-Sperre (das Ein/Aus des Owners). Touch: ein Finger auf leerer Karte = Pan. *Mittel; Risiko: versehentliche Tokenbewegung, daher Schwellwert und Prüfung von `canMove`.*
- **S3 Ein Umschalter ersetzt beide Werkzeuge.** *Mittel; Moduszustand weniger sichtbar.*

**PRÜFKANDIDAT: S2.** Es entspricht dem Transkriptgedanken, beide Gesten gemeinsam zu bedienen; die Sperre bleibt als expliziter Schalter.

### Apply-Fragen B

1. Snap-Politik pro Form: Ecke, Mitte oder keine?
2. Vorgabe beim Öffnen: Snap an oder aus?
3. Diagonalregel getrennt?
4. Einheiten m/ft? (`VTTDisplay.formatDistance` existiert.)
5. Rasterumfang: Größe, Sichtbarkeit, Deckkraft, Versatz?
6. Darf eine Größenänderung bestehende Fog-/Sichtzellen und Tokenpositionen verändern, oder werden sie umgerechnet?
7. Bestätigt der Owner Pen = Pan?
8. Welche Tastenbelegung, ohne Kollision mit den Ziffern der Hotbar?

### Matrix B

| # | Prüfung | Messbar |
|---|---|---|
| 1 | Freier Ursprung bei Zoom 20/100/300 % und nach Pan | Abstand Ursprung–Cursor ≤1 Bildschirmpixel |
| 2 | Beschriftung | Bildschirmhöhe ≥12px bei 20–300 % Zoom; Radiuslabel außerhalb des Kreises; Distanzlabel ≤40px vom Cursor |
| 3 | Quadrat | In allen vier Quadranten stetig, kein Sprung >1 Feld bei Mausweg <1 Feld |
| 4 | Raster | DM ändert Größe, Reload und anderer Client zeigen denselben Wert; Revisionskonflikt → 409 |
| 5 | Select/Pan | Leeres Ziehen pannt; Ziehen eines eigenen Tokens bewegt nur ihn; 2-Finger-Pinch unverändert |
| N1 | Owner im Player-Kontext ändert das Raster | 403, analog `test_map_scale_contexts.py:30` |
| N2 | Player-Komposition | Enthält keinen Rasterdialog |
| N3 | Pan über fremdes Token | Bewegt es nicht |
| N4 | Hotbar-Ziffern | Feuern im Eingabefeld weiterhin nicht |

### Slices B

1. Reproduktionsreisen für Quadrat und Grid-Klick
2. U09-Beschriftung und Snap-Trennung
3. U09-Ziehmodus
4. U11 S2
5. U10 G1+G2
6. Optional G3

---

## C. U12: Bibliothek zuerst, dann platzieren

### Codebefund [R]

**Einstiege:**
- „Neuen Token platzieren“ setzt `pendingTokenTemplate = null`, aktiviert das Werkzeug und schließt das Fenster (`play-token-library.js:12-13`).
- Der Zeilen-Button „Platzieren“ setzt Vorlage und Bild (`:44-51`).
- Die leere Bibliothek zeigt einen Hinweistext (`:35`).

**Kartenklick:**
- Öffnet immer `_openTokenCreatePanel` (`play-ui.js:1297-1309`).
- Das Panel rastet auf Eckpunkte ein (`:1510-1513`), leert erst den Namen und füllt dann aus der Vorlage Name, Größe und Typ (`:1529-1556`).
- Für Nicht-Operatoren ist der Typ fest `player` (`:1544-1550`). Die Sichtbarkeit kommt aus dem aktiven Layer, nicht aus der Vorlage (`:1536-1540`).
- Eine Charakterbindung wird nur vorausgewählt, wenn sie noch verknüpfbar ist (`:1560-1578`).

**Bestätigung (`:1590-1633`):**
- Die Vorlage liefert `hp_current = hp_max`, Rotation und Sichtweite.
- Erzeugt wird über den bestehenden Socket-/HTTP-Erstellweg. **Eine Vorlagen-ID wird nicht übertragen**; die Werte setzt der Client.

**Zustandsleck [R]:**
- `_cancelTokenPlacement` setzt `pendingTokenTemplate` nicht zurück (`:1580-1588`). Zurückgesetzt wird nur in `play-token-library.js:13` und im Konstruktor (`play-ui.js:137`).
- [S] Ein späterer Bild-Upload (`:2906-2918`) könnte noch alte Vorlagenwerte übernehmen. Nicht reproduziert.

**Serverseite:**
- Die Bibliothek ist auf Nutzer + Kampagne + `g.table_context.mode` begrenzt, mit den Rollen PLAYER/DM/CO_DM (`play/token_library.py:13-24`).
- Speichern ist nur aus sichtbaren, für Player eigenen Tokens möglich (`:43-47`), mit erlaubten Werten und geprüfter Charakterbindung (`:62-69`).

**Vertragsbezug:** Der vorige Apply-Vertrag legt fest: „Kartenklick öffnet weiterhin den Platzierungsdialog“ (`docs/DADM_APPLY_SESSION_FEEDBACK_2026-11-16.md:28-29`). U12 ersetzt das; Apply muss das **ausdrücklich** festhalten.

### Optionen

| Option | Nutzen | Aufwand | Risiken |
|---|---|---|---|
| **T1 Geführt:** „Token platzieren“ öffnet das Tokenfenster mit Fokus in der Bibliothek. Vorlage wählen → Werkzeug mit Vorlage aktiv (Status „Vorlage X – auf Karte klicken, Esc bricht ab“) → Kartenklick erzeugt direkt über den bestehenden Erstellweg. „Neu erstellen“/Upload behält den Dialog. | Erfüllt U12; Zielposition bleibt in Nutzerhand; geringe Rechteänderung | gering–mittel | Bindungskonflikt (eine Figur pro Karte) muss als klare Meldung kommen statt stiller Fehler; DM-Sichtbarkeit muss explizit sichtbar sein |
| **T2 Sofort automatisch:** Vorlage wählen → Token am Viewport-Mittelpunkt oder in freier Zelle, danach verschieben | Ein Klick weniger | mittel | Platzierung im Nebel, hinter Wänden, außerhalb des Kartenrands oder in Kollision; für Player kann das Informationen preisgeben; ein Zielbereich lässt sich schwer serverseitig validieren |
| **T3 Minimal:** Bibliothek zuerst, Dialog bleibt vorausgefüllt mit Fokus auf „Platzieren“ | Sehr gering | gering | Redundanter Dialog bleibt, Owner-Anforderung verfehlt |

**PRÜFKANDIDAT: T1.** Begründung [S]: Es trifft die Owner-Formulierung, nutzt den vorhandenen autorisierten Erstellweg und vermeidet die Datenschutz- und Validierungsfragen von T2.

### Apply-Fragen C

1. Soll der Server `template_id` erhalten und die Werte selbst lesen, statt dass der Client sie setzt?
2. Bleibt das Werkzeug nach einer Platzierung mit der Vorlage aktiv (mehrere Goblins)?
3. Welche DM-Sichtbarkeit (Layer) gilt bei direkter Platzierung?
4. Was genau bedeutet „gleiche Einstellungen“? Bisher: Bild, Größe, Typ, Rotation, HP-Maximum, Sichtweite, Bindung. Weder HP-Verlust noch Initiative noch Zustände.
5. Was zeigt die leere Bibliothek: direkt „Neu erstellen“/„Bild hochladen“?

### Matrix C

| # | Prüfung | Erwartung |
|---|---|---|
| 1 | Einstieg „Token platzieren“ | Bibliothek sichtbar, Fokus auf erster Vorlage oder Leer-Aktion |
| 2 | Vorlage + Kartenklick | Genau ein Token mit Vorlagenname/-werten, **0 Dialoge**, neue ID |
| 3 | Esc / Werkzeugwechsel | Kein Token; Vorlagenzustand leer (das Leck ist geschlossen) |
| 4 | Leere Bibliothek / Neu | Bisheriger Dialog funktioniert |
| N1 | Fremde Vorlage (anderer Nutzer, Modus, Kampagne) | 404 |
| N2 | Bindung zweimal auf derselben Karte | Abgelehnt, klare Meldung; bestehender Token und Hotbar bleiben |
| N3 | Player | Typ bleibt `player`, keine DM-Layer-Option |
| N4 | Platzierter Token | Ohne Initiative, Zustände, alte HP-Verluste |

**Inventar:**
- `tests/test_session_feedback.py:37`, `:56`, `:174`
- `tests/test_session_feedback_browser.py:17`

### Slices C

1. Zustandsleck beheben und Einstieg „Bibliothek zuerst“
2. Direktplatzierung T1
3. Optional: Server-seitige Vorlagenübernahme

---

## D. U14: Seitenhierarchie

### Codebefund [R]

**Modell:**
- `SceneStack` ist **pro GameSession eindeutig** (`models/scene_stack.py:15`).
- `SceneLayer` hat `campaign_map_id`, `label`, `order_index` und `is_player_visible`, aber **keine Elternbeziehung** (`models/scene_layer.py:14-18`), mit Unique-Schlüssel (Stack, Karte) (`:25`).

**Dienste (`play/service.py`):**
- Init aus allen Kampagnenkarten nach Erstellzeit (`:391-442`).
- Hinzufügen kopiert die Karte bei Duplikat (`:462-540`).
- Umsortieren ohne Revision oder Eindeutigkeit (`:553-577`).
- Löschen befördert die erste Seite nach `order_index` (`:580-612`).
- Aktivieren (`:615-627`).
- Player erhalten nur `is_player_visible` (`:372-388`).

**Routen:** alle nur für Operatoren (`play/routes.py:371-558`).

**UI:**
- `#layerList role="listbox"` (`play.html:2601`); die Optionen enthalten **Eingabefeld und sechs Buttons** (`play-ui.js:3645-3688`).
- Roving Tabindex mit Pfeiltasten, Home/End, Enter aktiviert (`:3690-3777`); Suche (`:3779-3791`).
- Verschieben per Tausch auf/ab (`:4057-4072`), Löschen mit Bestätigung (`:4032-4042`).
- Pill „aktive Seite“ (`:4074-4094`).
- Einrücken per Maus gibt es nicht.

**Atlas:** ein getrenntes Domänenmodell (`atlas.js`), hier nicht vertieft und nicht mit Seiten gleichzusetzen.

### Externe Quellen D [Q]

- **APG Tree View:**
  - Rechts öffnet einen geschlossenen Knoten oder geht zum ersten Kind; links schließt oder geht zum Elternknoten.
  - Hoch/runter, Home/End, Enter für die Standardaktion; Type-ahead empfohlen (ab 7 Wurzeln); `*` optional.
  - Rollen `tree/treeitem/group`, `aria-expanded` nur an Elternknoten.
  - Bei dynamischem Laden `aria-level/setsize/posinset`.
  - Es gibt ein Beispiel „Navigation Treeview“. Zu interaktiven Elementen innerhalb eines Treeitem äußert sich die Seite nicht.
- **APG Treegrid:** für „hierarchical data … editable or interactive“; Zeilen und Zellen sind fokussierbar.
- **APG Listbox:** unterstützt keine Interaktion mit Elementen in einer Option und verweist dafür auf das Grid-Pattern. [S] Die vorhandene Seitenliste verletzt das bereits; das ist bestehende Schuld.
- **APG Breadcrumb:** `nav` mit Label, Linkliste, `aria-current="page"`.
- **Foundry Folders:**
  - Dokumente per Drag in Ordner; Sortierung alphabetisch oder manuell.
  - „Remove Folder“ verschiebt den Inhalt eine Ebene hoch, „Delete All“ löscht ihn.
  - Rechte über „Configure Permissions“.
  - **Eine Tiefengrenze nennt die Seite nicht.**
- **Foundry Scenes:** aktive Szene (für alle gleich) versus betrachtete Szene (pro Nutzer); „GM Only“.

### Optionen UI

| Option | Nutzen | Aufwand | Risiken |
|---|---|---|---|
| **H1 Baum** (APG Navigation Treeview) mit nicht interaktiven Zeilen. Aktionen (umbenennen, sichtbar, auf/ab, **„Verschieben nach…“-Elternauswahl**, Ebene hoch/tiefer, duplizieren, aktivieren, löschen) in einer Werkzeugleiste für den fokussierten Knoten | Erfüllt Auf-/Zuklappen; behebt die Listbox-Schuld; Umhängen ohne Maus | mittel–hoch | Platz bei 390px; Fokus nach Server-Refresh halten |
| **H2 Gruppierte flache Liste:** bestehende Liste, Einrückung oder Pfadtext, Gruppenköpfe | Nutzt Bestehendes | gering–mittel | Tiefe schlecht erkennbar; Listbox-Schuld bleibt |
| **H3 Breadcrumb-Reise:** nur Kinder des aktuellen Knotens plus Pfad oben | Mobil stark, einfach | mittel | Wenig Überblick für den DM; aktive Seite liegt evtl. nicht im Blick |

**PRÜFKANDIDAT: H1.** Bei schmaler Breite kann H3 als Darstellung derselben Daten dienen (Apply-Frage). Begründung [S]: Die Owner-Abnahme verlangt Auf-/Zuklappen und Ebenenwechsel, und H1 trennt Navigation und Aktionen APG-konform.

### Datenoptionen (nur zu untersuchen)

- **(i) `parent_layer_id` an `scene_layers`:** Adjazenzliste, sessiongebunden, klein, kein Kartenbezug für reine Oberseiten.
- **(ii) Kampagnenweite Knotentabelle:** `campaign_id`, `parent_id`, optional `map_id`, Ordnung, Revision; der Session-Stack verweist darauf.
- **(iii) Materialisierter Pfad oder Closure-Table:** nur bei großen Bäumen nötig.

**Zentrale Frage [S]:** Weil `SceneStack` pro Session neu aus Kampagnenkarten entsteht (`service.py:391`), ginge eine Hierarchie unter (i) mit jeder neuen Session verloren oder müsste kopiert werden.

**Querschnitt für alle Varianten:**
- Zyklusprüfung beim Umhängen auf dem Server (Vorfahrenkette prüfen)
- Revision oder Transaktion beim Umsortieren
- Definiertes Verhalten für „erste Seite“ beim Löschen des aktiven Blatts

### Apply-Fragen D

1. Ist die Hierarchie kampagnen- oder sessionweit?
2. Darf eine Oberseite selbst eine spielbare Karte sein oder nur ein Gruppenknoten?
3. Löschen einer Oberseite: Kinder hochziehen, Löschen verbieten oder kaskadieren?
4. Verborgene Oberseite mit sichtbarem Kind: Wo erscheint das Kind für Player, und darf der Pfadname durchsickern?
5. Ändert ein Umhängen die Sichtbarkeit?
6. Tiefengrenze nur technisch (Schutz), nicht fachlich? **Keine Dreiebenengrenze festlegen.**
7. Wird die Baumansicht mobil zum Breadcrumb?

### Matrix D

| # | Prüfung | Erwartung |
|---|---|---|
| 1 | Tastatur | Rechts/links klappt, Pfeiltasten navigieren, Enter aktiviert; Umhängen über „Verschieben nach…“ ohne Maus |
| 2 | Touch 390px | Alle Aktionen ohne Drag erreichbar; Ziele ≥24×24px (WCAG 2.5.8, hier nicht neu abgerufen) |
| 3 | Reload/zweiter Client | Gleicher Baum, gleiche Ordnung, gleiche aktive Seite |
| N1 | Umhängen eines Knotens unter einen eigenen Nachfahren | 4xx, keine Änderung |
| N2 | Player | Erhält keine verborgenen Knoten oder Labels in Bootstrap, Socket oder Resync |
| N3 | Owner im Player-Kontext ändert die Hierarchie | 403 |
| N4 | Löschen einer aktiven Oberseite | Definierte Folgeseite, keine verwaisten Kinder |

**Inventar:**
- `tests/test_scene_stack_api.py`
- `tests/test_layer_add_flow.py`
- `tests/test_table_contexts.py:192` (Legacy-Pfade)
- `tests/test_token_layers_browser.py:14`

### Slices D

1. Datenvertrag und Persistenzebene (nur Dokument)
2. Server: Eltern, Zyklus, Revision, Projektion
3. Baum-UI mit Aktionsleiste
4. Mobile Darstellung

---

## Unresolved Medium+ Risiken

| Schwere | Risiko | Gruppe |
|---|---|---|
| Mittel | Palettenwerte und -quelle unbelegt; Kontrast nicht messbar, bis Werte feststehen | A |
| Mittel | A2/BookScene würde per `innerHTML` den Zustand eingebetteter Editoren zerstören | A |
| Mittel | Neuer Rahmenkopf kann `.eh-window` (fix bei 5rem) verdecken; Mapmaker ist statisch | A |
| Mittel | Messfarben fallen unter die harte SVG-Ausnahme; Lesbarkeit (U09) und Palette (U05) brauchen eine explizite Abgrenzung | A/B |
| Mittel | Snap-Schalter koppelt Punktsnap und Diagonalregel; eine Änderung verschiebt angezeigte Distanzen | B |
| Mittel | Änderung von `grid_size` wirkt auf Sichtzellen, Fog, Token-Snap und Platzierung bestehender Karten | B |
| Mittel | Kampagnenroute `update_map` ohne Tischkontext und Broadcast; darf am Tisch nicht wiederverwendet werden | B |
| Mittel | U12 ersetzt einen Vertrag aus dem vorigen Apply; Vorlagen-Zustandsleck | C |
| Mittel | Sessiongebundener `SceneStack` gegenüber einer kampagnenweiten Hierarchie | D |
| Mittel | Verborgene Eltern-/Kindknoten könnten DM-Labels an Player weitergeben | D |
| Mittel | Umsortieren ohne Revision; konkurrierende DM/Co-DM-Umhängungen und Zyklen | D |
| Niedrig | Listbox mit interaktiven Optionen (bestehende Schuld) | D |
| Niedrig | Pen = Pan und Grid-Klick = Snap-Toggle sind Annahmen | B |

## Testinventar (nicht ausgeführt)

- `test_play_presentation_browser.py`
- `test_c01_navigation_browser.py`
- `test_core_book_runtime_routes.py`
- `test_atlas_browser.py`
- `test_mapmaker_browser.py`
- `test_private_conversations_browser.py`
- `test_feedback_b07_browser.py:33` (Messformen)
- `test_mobile_playtable_browser.py:138` (Touch, Pan, Pinch, Abbruch)
- `test_map_scale_contexts.py`
- `test_session_feedback.py`
- `test_session_feedback_browser.py`
- `test_scene_stack_api.py`
- `test_layer_add_flow.py`
- `test_table_contexts.py`

Welche bisherigen Annahmen diese Tests festschreiben (z. B. Klick-Klick-Formen, Dialog bei Kartenklick), ist vor Apply zu prüfen.

## Nächster Schritt (Apply)

1. Owner-Entscheidung zu Palettenwerten und -quelle sowie Bestätigung Pen = Pan.
2. Kurze Browserreisen am Live-Image: Quadrat, Grid-Klick, Vorlagenleck.
3. Danach Apply-Verträge in der Reihenfolge U05 → U06 → U01/A1 und, unabhängig davon, U12/T1 → U09/M2 → U11/S2 → U10/G2 → U14 (zuerst Datenvertrag).

Delay bleibt unberührt.

## Quellen (abgerufen 16.11.2026)

- [W3C APG Tree View](https://www.w3.org/WAI/ARIA/apg/patterns/treeview/)
- [W3C APG Treegrid](https://www.w3.org/WAI/ARIA/apg/patterns/treegrid/)
- [W3C APG Listbox](https://www.w3.org/WAI/ARIA/apg/patterns/listbox/)
- [W3C APG Breadcrumb](https://www.w3.org/WAI/ARIA/apg/patterns/breadcrumb/)
- [WCAG 2.2 Understanding 1.4.11 Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast)
- [WCAG 2.2 Understanding 1.4.3 Contrast (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
- [MDN Pointer events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events)
- [Foundry VTT: Scenes](https://foundryvtt.com/article/scenes/)
- [Foundry VTT: Measurement](https://foundryvtt.com/article/measurement/)
- [Foundry VTT: Folders](https://foundryvtt.com/article/folders/)
- [Foundry VTT API v14: BaseScene](https://foundryvtt.com/api/classes/foundry.documents.BaseScene.html)
