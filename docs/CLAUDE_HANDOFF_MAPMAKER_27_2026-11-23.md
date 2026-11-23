# Claude-Übergabe: die 27 Karteneditor-Punkte in sechs Arbeitspaketen

Stand: 23.11.2026. Dieses Papier bündelt **E01–E27 aus dem ersten Review** vollständig. Es ist zum direkten Übergeben an Claude gedacht; es startet selbst keinen Claude-/Agentenlauf. Das [zweite Review](DADM_DISCOVER_EDITOR_CREATOR_FEEDBACK_2026-11-23.md) ist separat ausgewertet. Dessen gemeldeter Sitzungseinstiegsfehler T1/N18 hat im Gesamtprojekt Vorrang; er erweitert nicht stillschweigend die folgenden sechs Editor-Pakete.

## Auftrag zum Kopieren

> Arbeite am Roll-Drauf-VTT-Karteneditor anhand dieses Übergabepapiers und der dort verlinkten Quellen. Lies zuerst AGENTS.md und den kleinsten DAD-M-Kontext. Verifiziere vorhandene Funktionen, statt sie erneut zu bauen. Beginne mit den DE-Hotkeys, der Größenmerkliste je Asset und den Katalogfiltern; prüfe dabei auch die Auffindbarkeit der vorhandenen Wegpunktbearbeitung. Halte den ersten Implementierungsschnitt klein. Beschreibe vor Änderungen Zielverhalten, betroffene Verträge und Abnahme; setze anschließend die eindeutig beschriebenen Korrekturen um und liefere sie nach den Repo-Regeln. Bearbeite danach die übrigen Pakete in der genannten Reihenfolge. Offene Produktentscheidungen darfst du nicht als bereits beschlossen behandeln. Arbeite selbst, ohne weitere Agents oder Orchestratoren. Bewahre die bereits ausgelieferten Playtable-, Rollen-, Fenster- und Kamerafunktionen. Dokumentiere tatsächliche Prüfungen, bekannte Vorbefunde, Source/Image und den Rückweg. Markiere eine Funktion erst nach nachgewiesener Erreichbarkeit durch die vorgesehene Rolle als geliefert.

## Projekt und verlässlicher Ausgangspunkt

- Repository: `AdrianGros/Roll-Drauf-VTTRPG`, aktueller Arbeitsbaum `/home/admin/projects/roll-drauf-vtt-canvas-scenes-20261123`.
- Übergabebasis: Commit `41519a2c0` auf `fix/canvas-scenes-20261123`. Den aktuellen Stand vor dem Abzweigen prüfen; spätere Commits dürfen nicht versehentlich verloren gehen.
- Aktuelle dokumentierte App-Funktionsquelle: `ca61fc4fd0d28ee524bb6353114c30bf8ea83e1b`, Image `sha256:16304c0ba8313ac37b3129878e3303e74e1cfae4a8010fb1b628181484aa0b7f`. Vor jedem Deploy die tatsächlich laufende Version neu feststellen.
- Normale Editor-Navigation: angemeldete Kartenwerkstatt/Karteneditor; etablierter Einstieg `/mapmaker`, der zum Editor-Dokument weiterleitet. Die Änderungen müssen dort auffindbar sein.
- Der Discord-Bot ist ein anderes Projekt. Seine Lane-/Release-Regeln sind kein VTT-Deploymentverfahren.
- Neuer Arbeitszweig/Worktree vom aktuellen integrierten VTT-Stand; weder alte Workerstände noch ein veraltetes `main` ungeprüft über Produktion legen.

Quellen: [27-Punkte-Discover mit Zeitmarken](DADM_DISCOVER_MAPMAKER_REVIEW_2026-11-23.md), [frühere W02-Implementierung](DADM_DEPLOY_REVIEW_MAPS_2026-11-18.md), [integrierte Lieferung](DADM_MONITOR_REVIEW_WEB_2026-11-22.md), [zu bewahrender Playtable-Stand](DADM_MONITOR_CANVAS_SCENES_2026-11-23.md). Die ursprüngliche Aufnahme heißt `2026-11-23-1024-vtt-garteneditor-im-funktionsreview.txt`; ihre Herkunft/Prüfsumme steht im Discover. Die Rohaufnahme muss für dieses Papier nicht öffentlich hochgeladen werden.

## Bereits vorhanden – zuerst benutzen und prüfen

Pinsel mit Größe/Deckkraft/Weichheit, abschaltbarer Textur, eigener Farbe, drei geometrischen Spitzen und Bildspitzen; Undo/Redo; Ebenen und kontextbezogene Zielebenenwahl; Wegnamen und bewusstes Verbinden; Wegpunkte verschieben; globale Wegglättung; eigene Bild-Uploads und Pixelzeichnung; Kachel-/Stempelplatzierung, Malbegrenzung und Generatorpresets.

Wichtige Einstiege: Weg auswählen → „Wegpunkte bearbeiten“ (`pathNodeMode`) beziehungsweise Umschalt+Ziehen; `selPathName` für Namen; `toolLayer` und Alt+↑/↓ für Zielebenen; „Eigenes Bild hochladen …“ für einzelne Eigenbilder. Vorhandensein im Code beweist noch keine gute Auffindbarkeit oder aktuelle Browserabnahme.

„Fläche füllen“ verteilt derzeit Symbole und ist kein Farb-Füllwerkzeug. Ein einzelner portabler Eigenstempel ist kein kompletter Tileset-Paketimport. Glättung eines ganzen Wegs ist keine Kurvensteuerung je Knoten.

## Vollständige Bündelung

| Paket | Inhalt | Ursprüngliche IDs | Reihenfolge |
| --- | --- | --- | --- |
| M1 | Eingaben, Pinselzustand und schnelle Auswahl | E02, E03, E04, E07, E08, E22 | M1a zuerst; Radialmenü später |
| M2 | Ebenenziele, Ebenenübersicht und kompakte Bedienung | E09, E10, E20, E21, E23 | nach dem ersten Fehlerschnitt |
| M3 | Wege/Linien und gemeinsame Objektbearbeitung | E11, E12, E13, E14, E15, E16, E17, E18, E19 | vorhandene Bearbeitung früh prüfen; Ausbau danach |
| M4 | Katalog, korrekte Filter und persönliche Sets | E26, E27 | M4a zuerst; Personalisierung später |
| M5 | Eigene Tilesets, Formate und Herkunft | E24, E25 | vorhandenen Upload prüfen; Paketvertrag anschließend |
| M6 | Landfüllung und weitere Küstengestaltung | E01, E05, E06 | ausdrücklich nachgelagert |

### M1 – Eingaben und Zustand

**M1a, erster Schnitt:** E03 und E22. In `tools.js` werden Klammer-Hotkeys über `event.key` geprüft, aber Ctrl/Alt vorher ausgeschlossen. Wenn AltGr als Ctrl/Alt ankommt, kann die DE-Belegung daran scheitern. Tatsächliche Ereignisse auf DE/US prüfen; keine unbewiesene universelle Browserursache behaupten. `ui.js:chooseStamp` setzt die Größe beim erneuten Wählen auf `stamp.defaultSize`; Größen je Asset sollen innerhalb der Sitzung erhalten bleiben. Ein Reset zwischen Sitzungen ist ausdrücklich erlaubt; dafür ist kein neuer Server-Persistenzdienst nötig.

**M1b:** E02 – letzte acht benutzte eigene Farben; E04 – Deckkraft per Hotkey; E07 – schnellere Pinsel-/Größenwahl über konfliktfreie Modifikatoren. E08 bleibt eine gesonderte Gestaltung des Radialmenüs. Normales Mausrad zoomt, Alt+Rad ordnet bereits ausgewählte Objekte um, Mitteltaste verschiebt die Ansicht. Diese Bindungen nicht stillschweigend überschreiben.

Abnahme: DE-/US-Ereignisse einschließlich AltGr; kein Auslösen beim Schreiben oder in nativen Eingabefeldern. Asset A auf 16 px → B wählen → A wieder wählen bleibt 16 px. Die acht Farben sind wirklich wieder auswählbar. Größen-, Weichheit- und Deckkraftänderungen zeigen denselben Zustand in Vorschau und Reglern. Bestehendes Zoom/Pan/Undo bleibt erhalten.

### M2 – Ebenen und Anordnung

E09/E10: die vorhandene Zielebenenwahl deutlich zugänglich machen und eine kompakte Ebenenübersicht gestalten. E21: Filter nach sinnvollen Typ-/Objektmerkmalen; „zuletzt verwendet“ braucht eine definierte Bedeutung. E23: häufig benötigte Assetauswahl früh zeigen, seltene Einstellungen zunächst zuklappen und den Zugriff stabil halten.

**E20 ist ein Typ-/Zielproblem:** `starter.js` erzeugt „Flüsse & Wege“ als Raster. `app.js:addPath` braucht dagegen Vektor-`paths`, nimmt die oberste sichtbare solche Ebene und berücksichtigt dabei nicht vorrangig die bewusst aktive passende Ebene. Einen gleich benannten Rasterlayer nicht allein wegen seines Namens umtypen. Unsichtbare Ebenen nicht unbemerkt bearbeiten. Wiederverwendung und eine bewusste neue Ebene müssen unterscheidbar bleiben.

Abnahme: zwei kompatible Ebenen anlegen, die untere auswählen und dort tatsächlich zeichnen; bei vorhandener geeigneter leerer Ebene kein ungewolltes Duplikat; bestehende Rasterpixel bleiben erhalten. Wechsel und Radierer zeigen klar das Ziel. Oberfläche und Palette bleiben bei 390/1440 Pixeln erreichbar. Klare Tastatur-/Fokusreihenfolge und Undo für strukturelle Änderungen.

### M3 – Wege und Objekte

E11/E17 zunächst verifizieren: vorhandene Wegpunkte und Wegnamen auffindbar machen; keinen zweiten konkurrierenden Editor bauen. E12: zusätzlich zum Freehand-Zeichnen einzelne Knoten setzen. E13: Knotenart/Kurvenhärte unterscheiden von bestehender globaler `curve`-Glättung. E14: Zeichnen/Bearbeiten bewusst umschalten. E15/E19: Straßen-/Weg-/Fluss-/Grenzstile, Breite, punktierte/gestrichelte Linien. E16: wählbare Objektübersicht für Wege, Stempel, Kacheln und Beschriftungen; `refreshPlaces` ist bislang eine Ortsliste. E18: freie Linienfarben und eine definierte Anbindung an das Meer; das Meer besitzt zwei Verlaufsfarben. E17 zusätzlich: gewünschte Beziehung zu nahen Orten/Sehenswürdigkeiten präzisieren.

Abnahme: existierenden Punkt verschieben, Undo/Redo, Speichern und Wiederladen prüfen. Freehand und Knotenmodus dürfen keine alten Wege beschädigen. Eigenschaften/Stile müssen in Projektdatei, ZIP, Vorschau und Export dieselbe Bedeutung haben. Bewusstes Verbinden bleibt explizit; eine bloße Kreuzung erzeugt keinen Anschluss. Objektliste und Karte wählen dasselbe Objekt aus.

### M4 – Katalog und Filter

**M4a, erster Schnitt:** E26. `ui.js:renderPalette` akzeptiert Standardkatalog-Assets bei gewähltem Stil bisher nur als Pixelgrafik mit `pixelArt`; konkrete Perspektiven setzen `stamp.custom` voraus. Daher können Filter den Standardbestand komplett ausschließen. Das belegt weder das Fehlen gemalter Motive noch eine korrekte Klassifizierung aller vorhandenen Bilder.

Bestands-/Metadatenabgleich vor Massentagging. Kategorie, Motiv, Stil, Perspektive, Auflösung und Eignung für Weltkarte/Battlemap sind verschiedene Merkmale. Keine dieser Eigenschaften allein aus Dateigröße oder „ist eine Kachel“ ableiten. E27 folgt mit persönlichen Ausblendungen und Sets, nachdem Filter und Ergebniszahlen stimmen.

Abnahme: Standard- und Eigenassets in Filterfällen getrennt prüfen; fehlende Metadaten ehrlich behandeln; keine irreführend leeren Listen. Suche/Pack/Kategorie kombinieren und zurücksetzen können. Asset-IDs und Referenzen vorhandener Projekte bleiben gültig. Keine unbelegte Neubeschaffung oder komplette Reklassifizierung des Bestands als Nebenarbeit.

### M5 – Eigene Inhalte

E24: vorhandenen Upload/Crop/Pixel-Einstieg prüfen und erklären. Für einen echten Tileset-Paketimport Dateiformat, Raster/Teilausschnitte, Metadaten, Mengen-/Bildgrenzen und verständliche Fehler festlegen. Bestehende private Eigenbilder sind in den Dokument-/Speicher-/Exportvertrag integriert; daran anschließen.

E25: Quellen-/Lizenzangaben und vorhandene Rechtebestätigung erhalten. Die Aufnahme enthält **keine abschließend beschlossene öffentliche KI-Freigaberegel**. Private Nutzung, Kennzeichnung und öffentliche Veröffentlichung nicht zu einer erfundenen globalen Verbotsregel zusammenziehen. Offene öffentliche Produktpolitik getrennt behandeln; sie blockiert die eindeutig beschriebenen privaten Bedienkorrekturen nicht.

Abnahme: Import → Platzierung → Undo → Save/Reload → Bibliothek → Atlas/Tabellensnapshot → PNG/ZIP samt Herkunft. Bestehende Validatoren und Budgets vor teuren Dekodierungen beachten. Fremde Projekte dürfen Eigenassets nicht allein wegen eines zuvor im Browser geladenen Bilds benutzen.

### M6 – Nachgelagerte Zeichenfunktionen

E01: geschlossene Outline füllen, ohne Küstenlinie und andere Ebenen zu beschädigen; eine Aktion muss rückgängig werden können. E05: raue Küste/Dreieck/Polygonspitzen, bestehende Bildspitzen berücksichtigen. E06: Küstenwellen zusätzlich zu vorhandener Küstenfarbe/-breite.

Diese Punkte wurden ausdrücklich als spätere Erweiterungen beziehungsweise Nice-to-have beschrieben. Vor Umsetzung Semantik, Ebenenbezug, Budget und Undo klären. Kein Flood-Fill, der andere Rasterebenen oder das Meer unbemerkt verändert. Bestehendes Pinselgefühl, Texturabschaltung und eigene Farben sind Erhaltungsbedingungen.

## Code-Einstiege und Prüfungen

| Bereich | Einstieg |
| --- | --- |
| Tastatur/Maus/Gesten | `vtt/static/mapmaker/js/tools.js` |
| Werkzeugzustand, Ebenenziele, Weganlage | `vtt/static/mapmaker/js/app.js` (`targetLayer`, `addPath`) |
| Regler, Assetwahl, Filter, Inspector | `vtt/static/mapmaker/js/ui.js` (`nudge`, `chooseStamp`, `renderPalette`, `refreshPlaces`) |
| Raster-/Vektor-Startzustand | `vtt/static/mapmaker/js/starter.js` |
| Pinsel/Farbe/Küste/Rendern | `brush.js`, `render.js` im selben Verzeichnis |
| Projektvertrag/Materialisierung/History | `document.js`, `history.js`, `storage.js`, `zip.js`, `snapshot.js` |
| Katalog/Eigenbilder | `stamps.js`, `asset-dialogs.js`, `atlas-bridge.js` |
| Oberfläche | `vtt/static/mapmaker/index.html`, `mapmaker.css` |
| Serverseitige Dokumentvalidierung | `vtt/mapmaker_document.py` |

Vorhandene passende Tests: `tests/test_mapmaker_browser.py`, `test_c04_mapmaker_browser.py`, `test_review_maps_browser.py`, `test_review_maps_server.py`, `test_mapmaker_tiles_server.py`, `test_mapmaker_library.py`, `test_mapmaker_library_browser.py`, `test_mapmaker_sheet_slicer.py`, `test_atlas_browser.py`, `test_landmass_browser.py`. Wähle die für den tatsächlichen Schnitt relevanten Fälle; diese Liste behauptet keine jetzt ausgeführte oder vollständig grüne Suite. Bestehende Fehler zuerst mit unverändertem Ausgangsstand vergleichen. Keine Produktfunktion zurückbauen, um veraltete String-/Gestenannahmen eines Tests zu erfüllen.

Neue UI-Texte in DE/EN über den vorhandenen Katalogpfad ergänzen: `tools/i18n/tasks/`, `python3 tools/i18n/build_catalog.py`, anschließend `--check`. Benutzertexte und Assetnamen werden nicht global übersetzt. Dokument-/Formatänderungen berühren Client **und** Servervalidierung sowie sämtliche Speicher-/Exportwege.

## Lieferung und Nachweis

Repo-AGENTS.md gilt: gebundener Apply-Entwurf, gezielte Implementierung, passende Prüfungen, Commit/Push, tatsächliche Live-Quelle/Compose-Konfiguration feststellen, begrenztes Overlay auf der aktuellen App und normale rollenrichtige Live-Abnahme. Produktion ist die bestehende Abnahmeumgebung; eine zusätzliche Staging-Umgebung ist keine Voraussetzung. Testdatenbanken/Fixtures bleiben isoliert, reale Benutzerprojekte werden nicht als Testdaten verwendet. Andere Dienste, Reminder und neuere Live-Arbeit erhalten; Sicherung/Schema/Rollback passend zum tatsächlichen Schnitt dokumentieren.

Für jeden Teilabschluss liefern: enthaltene E-IDs, bereits vorhandene vs. neue Funktion, geänderte Dateien, echte Einstiegsfolge, Prüfungen mit Ergebnis, verbleibende Grenzen, Source/Image und Rückweg. Keine Erledigung nur anhand eines vorhandenen Buttons, eines unbenutzten Moduls oder einer lokalen Vorschau behaupten.

## Start- und Arbeitsreihenfolge

1. Aktuellen Quell-/Live-Stand lesen; M1a/E03+E22 und M4a/E26 reproduzieren, E11 bedienen und die bestehenden Einstiege erklären.
2. Kleinsten eindeutigen Korrekturschnitt beschreiben, implementieren und vollständig liefern.
3. M2 als zusammenhängenden Ebenen-/Bedienungsschnitt bearbeiten.
4. M3 vorhandene Funktionen verbessern und danach Linien-/Objektverträge erweitern.
5. M5 und M4-Personalisierung mit den jeweils erforderlichen Produkt-/Formatentscheidungen bearbeiten.
6. M6 und M1-Radialmenü als eigene nachgelagerte Schritte behandeln.

Noch offene Entscheidungen: konkrete konfliktfreie neue Gesten, Bedeutung von Ebenen-Nutzungszeiten, Knoten-/Tangentenvertrag, Tileset-Paketformat und öffentliche KI-Kennzeichnung. Für sichere Teilpakete fortfahren; nur die jeweils davon abhängigen Entscheidungen offenlassen. Keine neuen strategischen Festlegungen unter einem reinen Bugfix verstecken.

Artefakt: dauerhaftes Übergabepapier, keine neue Anwendungsversion. Die zweite Aufnahme ist im [neuen Discover](DADM_DISCOVER_EDITOR_CREATOR_FEEDBACK_2026-11-23.md) mit N-IDs erfasst; neue Punkte daraus ersetzen die E-IDs nicht.
