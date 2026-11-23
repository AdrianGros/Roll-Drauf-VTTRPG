# Discover: neues Karteneditor-Funktionsreview

Status: als eigenes Feedback-Arbeitspaket aufgenommen, mit dem vorhandenen Code abgeglichen; keine Editor-Implementierung in diesem Schritt. Die laufenden Playtable-Korrekturen für Szenen/Ansicht bleiben ein eigener Lieferumfang. Die Ebenen im Editor sind Zeichenebenen; die Szenen im Playtable sind Karten-/Seitenzugänge. Ihre Fehler werden nicht gleichgesetzt.

Quelle: Owner-Anhang `2026-11-23-1024-vtt-garteneditor-im-funktionsreview.txt`, Aufnahme 26:32. SHA-256: `b35a93f391719f9c65974070894ce9e01ff16bb6c267a65efcfe45fde560ab6d`. Zeitmarken unten beziehen sich auf diesen Anhang. Das unveränderte Original bleibt beim Anhang; belanglose Gesprächsteile werden nicht ins Backlog übernommen. Quellstand des geprüften Editors: geerbter Live-Stand `3fd012f42`; keine Karteneditor-Datei wurde für die parallel laufende Playtable-Arbeit geändert. Statische Prüfung ist keine Browserabnahme.

## Index und Einordnung

Priorität P0: gemeldeter Bedienfehler/Fehlzustand; P1: nächster Funktions-/UX-Schnitt; P2: ausdrücklich später oder noch eine Gestaltungsidee. „Vorhanden“ benennt den tatsächlichen Einstieg und darf nicht als neue offene Implementierung eingeplant werden.

| ID | Zeit | Feedback / gewünschte Wirkung | Abgleich / Einstufung |
| --- | --- | --- | --- |
| E01 | 03:03–03:40, 11:03 | Geschlossene Land-Outline innen füllen, Küste erhalten | Offen; Flächenfüllung für Symbolverteilung und Malbegrenzung aus W02 sind kein Farb-Füllwerkzeug. Im Review ausdrücklich später erlaubt; P2, mit eigener Fill-/Undo-/Layer-Abnahme. |
| E02 | 04:15, 09:35 | Letzte acht eigene Farben wieder auswählbar | Keine eigene Acht-Farben-Historie in der geprüften Pinsel-UI gefunden; derzeit einzelner Farbwert. P1. |
| E03 | 05:17–05:29, 07:20–08:32 | Größen-/Weichheit-Hotkeys funktionieren auf DE-Tastatur nicht | Konkreter Codebefund: tools.js prüft `event.key` auf `[ ] { }`, kehrt jedoch vorher bei Ctrl/Alt zurück. Auf DE werden die Klammern typischerweise über AltGr erzeugt; wenn dies als Ctrl/Alt gemeldet wird, trifft es diesen Ausschluss. P0; DE/US und AltGr gezielt reproduzieren. |
| E04 | 05:17 | Deckkraft auch per Tastatur ändern | `nudge` behandelt Größe und Weichheit, keine Deckkraft. P1; zusätzliche Bindung und Fokus-/Eingabefeldschutz fehlen. |
| E05 | 06:24, 11:49–12:14 | Raue Küste, Dreieck-/zufällige Polygonspitze | Zusätzliche Spitzen bzw. Rauheit offen; runde/quadratische/rautenförmige Spitze und eigene Bildspitzen sind bestehende Basis. Im Review Nice-to-have; P2. |
| E06 | 06:48 | Küstenwellen als Abgrenzung | Küstenfarbe/-breite und Aktivierung existieren, Wellen bleiben separate Erweiterung; P2. |
| E07 | 08:56–09:26, 20:17–20:33 | Modifikator+Mausrad für Pinselwechsel und Größen | Normales Rad zoomt; Alt+Rad ordnet aktuell eine Auswahl um. Neue Größen-/Pinselbindungen nicht vorhanden; P1. Bestehende Zoom-/Reorder-Gesten erhalten. |
| E08 | 09:16–09:32, 20:55–21:11 | Temporäre radiale Werkzeug-/Farbpalette | Gestaltungsidee, noch kein beschlossener Tastenvertrag. Mitteltaste ist bereits Pan; ein vorgeschlagenes Maus-3-Rad kollidiert damit. P2 / Apply nötig. |
| E09 | 13:05–13:43 | Zielebene bewusst wählen, mehrere Landebenen unterstützen | Werkzeugbezogener Ebenenwähler `toolLayer` und Alt+↑/↓ existieren (W02/K24). Auffindbarkeit verbessern; Raster-Material-/Zielebenenverhalten separat reproduzieren. Teilweise vorhanden; P1. |
| E10 | 13:43–13:59 | Kleine direkt erreichbare Ebenenleiste | Aktuelle Ebenenliste und Kontextwahl vorhanden; gewünschte kompakte dauerhafte Leiste ist zusätzliche UX-Arbeit, P1. |
| E11 | 14:35–15:36 | Bestehende Wegpunkte auswählen/verschieben | Bereits vorhanden: Weg auswählen → „Wegpunkte bearbeiten“ (`pathNodeMode`) oder Umschalt+Ziehen an einem Punkt. `tools.js` hat die echte `pathNode`-Geste. Als Auffindbarkeits-/Abnahmeproblem erfassen, nicht als komplett fehlende Mechanik. P0/P1. |
| E12 | 15:01–15:36 | Wege durch einzeln gesetzte Knoten zeichnen | Aktuelles Zeichnen ist Freehand mit automatisch verteilten Punkten; expliziter Knoten-Zeichenmodus offen, P1. |
| E13 | 15:36 | Pro Knoten gerade/gekrümmt und Kurvenhärte | Glättung `curve` pro ganzem Weg existiert; lokale Knotentypen/Tangenten sind nicht derselbe Vertrag. Erweiterung mit Dokument-/Export-/Undo-Vertrag, P1/P2. |
| E14 | 15:51–16:14 | Zwischen Neuzeichnen und Bearbeiten schneller wechseln | Werkzeuge W/V und Wegpunktmodus existieren; gewünschter Moduswechsel per Rad ist neue Ergonomieentscheidung, P1. |
| E15 | 16:11–16:21 | Feldweg/Straße/Waldweg und Stilpresets | Derzeit Weg/Fluss plus Breite/Glättung. Zusätzliche Presets/Materialien offen, P1. |
| E16 | 16:28–16:58 | Gemeinsame auswählbare Objektliste für Wege/Symbole/Kacheln/Texte | `refreshPlaces` listet bereits Orts-/Labelobjekte mit `place`; allgemeine Objektliste ist offen, P1. |
| E17 | 17:12–17:19 | Wege benennen, nahe Orte/Sehenswürdigkeiten zuordnen | Wegnamen `selPathName` samt Speicherkette sind W02/K23; Orte sind eigene bestehende Objekte. Explizite Relation Weg–Ort ist zusätzliche Funktion, P1. |
| E18 | 17:25–18:01 | Fluss farblich an Meer anschließen, Wege mit eigener Palette färben | Meer hat zwei Verlaufsfarben; freie Linienfarbe/automatische Flussanbindung benötigen eigenen Vertrag. P1, kein beliebiger einzelner Meerwert als fertige Lösung behauptet. |
| E19 | 18:01–18:44 | Gepunktete/gestrichelte Grenzen; Wege/Flüsse/Grenzen unter einem Linienkonzept | Zusätzliche konfigurierbare Linienarten und passende Darstellung/Speicherung offen, P1. Tab-/Werkzeugnamen noch gestalten. |
| E20 | 18:44–19:17 | Vorhandene leere Wegeebene verwenden, nicht doppelt erzeugen | Wichtiger Typunterschied: Starter erzeugt „Flüsse & Wege“ als Raster, `addPath` benötigt Vektor-`paths` und sucht nur sichtbare solche Ebenen. Es ignoriert außerdem die aktive passende Ebene zugunsten der obersten sichtbaren. P0; Wiederverwendung muss typgerecht sein, keine nichtleere Rasterebene blind umtypen. |
| E21 | 19:10–19:17 | Ebenen als filterbare Tabelle nach Typ/Objekten/letzter Nutzung | Vorhanden ist eine Ebenenliste mit Sichtbarkeit/Reihenfolge/Name/Deckkraft, keine solche Filtertabelle. P1. |
| E22 | 19:42–20:17 | Größe je Asset während der Sitzung merken | Bestätigter Codepfad: `chooseStamp` setzt ohne explizite Größe wieder `stamp.defaultSize`. Sitzungscache pro Asset fehlt. P0; Reset zwischen Sitzungen ist ausdrücklich erlaubt, Serverpersistenz nicht gefordert. |
| E23 | 21:25–21:58 | Konfiguration standardmäßig zuklappen, Assetpalette schneller erreichen | Bestehende Werkzeug-/Ebenenbereiche und Platzierungsoptionen bleiben Basis; gewünschte progressive Anzeige ist zusätzliche UX-Arbeit, P1. Nicht nur mehr Menüs hinzufügen. |
| E24 | 21:58–22:50 | Auffindbarer Custom-Tileset-Einstieg samt unterstütztem Format | W02 hat „Eigenes Bild hochladen …“, Crop und private portable PNG-Eigenstempel. Das ist noch kein fertig spezifizierter Tileset-Paketimport. Bestehenden Einstieg erklären/prüfen; Paketformat und Tile-Metadaten separat definieren, P1. |
| E25 | 22:22–22:50 | KI-/Herkunftsangaben, Umgang mit öffentlicher Freigabe | Eigene Bilder besitzen Quellen-/Lizenzmetadaten und Rechtebestätigung. Das Gespräch lässt die öffentliche KI-Regel ausdrücklich offen; daraus keine neue Freigabe-/Verbotsregel erfinden. Entscheidung offen, separat vom privaten Upload. |
| E26 | 22:56–26:13 | Kategorien, Stil-/Perspektivfilter und Weltkarten/Battlemaps sinnvoll trennen | Pack/Kategorie/Suche existieren. Klarer Befund: `renderPalette` akzeptiert Standardkatalog-Assets bei Stil nur als `pixel` mit `pixelArt`; jede konkrete Perspektive verlangt `stamp.custom`. Daher werden Standardassets bei Gemalt/Tusche/Perspektive ausgeschlossen. Kein Beleg, dass entsprechende Motive im Bestand fehlen. P0 für Filtervertrag/Metadaten, P1 für semantische Kategorien. |
| E27 | 23:58–24:34 | Persönliche Auswahl, ausgeblendete Assets und Sets/Presets | Packfilter als Basis vorhanden, persönliche Ausblendungen und Weltkarten-/Battlemap-Sets nicht damit gleichsetzen. P1/P2; erst korrekte Filter und Katalogmetadaten, danach Personalisierung. |

## Was bereits eingeplant bzw. geliefert war

Die frühere W02-Lieferung ([Deploy](DADM_DEPLOY_REVIEW_MAPS_2026-11-18.md), [integrierter Live-Monitor](DADM_MONITOR_REVIEW_WEB_2026-11-22.md)) enthält eigene Bilder/Pixelzeichnung, begrenzte Stil-/Perspektivfilter, bewusste Wege-Verbindungen und Namen, Ebenenwahl im Werkzeugkontext, Reihenfolge, Malbegrenzung und Generatorpresets. „Fläche füllen“ dort verteilt Stempel; es erfüllt E01 nicht. Bereits vorhandene Wegpunkte/Glättung und Benennung werden vor neuer Implementierung auf Auffindbarkeit geprüft.

Die positiven Rückmeldungen sind Erhaltungsbedingungen: Pinselgefühl, abschaltbarer Texturanteil, freie Pinsel-/Küstenfarben, weiche/hart einstellbare Spitzen, Rückgängig, gezieltes Radieren auf der Ebene, funktionierende Wegverbindungen und freie Editor-Navigation. Keine bestehende, ausdrücklich gelobte Mechanik durch eine andere Bedienart ersetzen.

## Engster nächster Schnitt

Empfehlung für Apply: zuerst E03/E22/E26 reproduzierbar schließen (DE-Hotkeys, Assetgrößen, ehrliche Katalogfilter), dazu E11 als Auffindbarkeitsprüfung. Danach E09/E20/E21/E23 als gemeinsamer Ebenen-/Bedienungsschnitt; E12–E19 als Linien-/Objektbearbeitungsschnitt. E01/E05/E06/E08 und zusätzliche Sets bleiben bewusst nachgelagert. Das ist eine Priorisierung, keine Behauptung einer erteilten Freigabe sämtlicher Architektur-/Datenformatänderungen.

Abnahmeentwürfe: DE- und US-Keyevents einschließlich AltGr und Textfeldfokus; Asset A auf 16 px, B wählen, A bleibt in derselben Sitzung 16 px; Katalogfilter mit Standard- und Eigenassets getrennt, keine unbegründete leere Liste; ausgewählten Wegpunkt tatsächlich verschieben und Undo/Save/Reload; manuelle Zielebene wird respektiert; vorhandene kompatible leere Ebene erzeugt kein Duplikat; Paneele auf 390/1440 ohne unnötige Scrollstrecke. Formatänderungen müssen Projektvalidierung, Speichern, Laden, Export und private Freigaben berücksichtigen.

Risiken: mittel — Shortcutkonflikte, falsche Bulk-Klassifizierung, Raster-/Vektorverwechslung, Dokument-/Undo-Kompatibilität. Die öffentliche Inhaltsregel ist offen. Keine Abhängigkeit installieren oder neue Veröffentlichungsregel aus dem Gespräch ableiten. Artefakt permanent im Projekt; der Rohanhang bleibt unverändert. Nächster Schritt: Apply für den priorisierten Editor-Schnitt; der aktuelle Playtable-Deploy wird davon nicht unterbrochen.
