# Vollständiger UI-/Playtable-Auftrag: Design und Umsetzungshandoff

Datum 17.11.2026, Profil standard, Aufbewahrung dauerhaft. Status: konsolidierter
Apply-Vertrag; der Owner hat die Umsetzung aller 14 Punkte bis zur vollständigen
Lieferung autorisiert und zusätzliche Freigabestopps für Einzelpakete abgelehnt.
Die Änderungen werden im selben Arbeitszyklus geprüft, committed, gepusht und live
über die bestehende Oberfläche ausgeliefert. Dieser Vertrag wird vor dem Produktcode festgehalten.

## Basis und Grenze

Basis: HEAD 3939766e7, App d4ff7e4fe, laufendes Image
sha256:7d8f4a54b36b125611ac116b37d10c09632dbea9a920c8c5b0413ea63efd4617.
Neue saubere Arbeitskopie: roll-drauf-vtt-ui-playtable-20261117. Fremde dirty
Änderungen aus anderen Arbeitsbäumen werden nicht übernommen. Discover vom 16.11.
und Lösungsrecherche samt Koordinationsprüfung sind Eingaben. Kein neuer Character
Importer, keine G1-Wiederbelebung, kein Delay-Umbau, kein 3D und kein neues Laufzeitpaket.

## Festgelegte Zielverträge

- **U01/U05/U06:** Gemeinsame Dokument-Buchschale für Conversations, Karten, Atlas,
  Creation Engine, Rulebook und Compendium. Bestehende Module behalten ihren
  Lebenszyklus und ihre Deep Links. Keine pauschale Übernahme in die innerHTML-
  Wechsel von BookScene. Eagle-Fenster bleiben außerhalb der Seitenfläche erreichbar;
  Canvas-Arbeitsflächen behalten ihre Größe. Night nutzt Edo #5E4A8C, Gray #8A8A8A,
  Ink #1C1C1C und Natural #F8F4E9 als Grundpalette; Text-/Linienpaare werden nach
  gemessenem Kontrast zugeordnet. Standardakzent und harte Tisch-Chrome-Regeln werden
  mitbehandelt. Benutzerkarten/-bilder bleiben in ihren Farben. Markierungen heißen
  Wände/Lichter; Wand-Sicht, Wand-Licht und Player-Vorschau haben getrennte Bedeutungen.
- **U02:** Historische öffentliche, nicht gelöschte/nicht moderierte Sessiontexte
  und öffentliche Würfe werden in Conversations über einen sichtbaren Bereich
  „Frühere Sitzungen“ mit Herkunft und Cursor lesbar. Originaldaten bleiben erhalten;
  keine Kopie in die Kampagnentexttabelle. Mitgliedschaft/Sperren bei jedem Abruf prüfen;
  keine privaten Paargespräche oder gm_only/blind/self-Inhalte in dieser persönlichen
  Oberfläche. Neue Kampagnentexte und ihr vorhandener Cursor bleiben unverändert.
- **U03/U04:** Vollständiges strukturiertes englisches SRD 5.2.1 mit Navigation,
  Suche und englischem Compendium im eigenen Buch-/Lesestil; dokumentierte Originalquelle,
  Attribution, deterministische Generierung und Sprachtrennung. Englisches Original-PDF
  bleibt Referenz. Mechanische Felder dürfen durch Neufassung nicht verändert werden;
  deutsche Charakter-Pins und Katalog-IDs behalten ihre Bedeutung. Kein dynamischer
  Übersetzungsdienst. English in Einstellungen wählt englische Inhalte; direkte Links
  dürfen Sprachwahl nicht zufällig wechseln. Redaktionelle Herkunft und tatsächlicher
  Bearbeitungsgrad werden explizit ausgewiesen, niemals Extraktion als Paraphrase ausgeben.
- **U07/U08:** Sicht und Licht werden durch getrennte wandbegrenzte 2D-Strahlenpolygone
  berechnet. Bestehende natürliche Sichtweiten bleiben gültig; Licht erweitert Sicht nur
  bei freier Token-Sicht und freier Lichtausbreitung. Darkness bleibt eine explizite
  Ausschlusszone. Spieler erhalten eine serverberechnete Bild-/Maskenprojektion ohne
  vollständige Wand-/Lichtgeometrie; PIL und SVG/PNG genügen, keine GPU-Abhängigkeit.
  DM sieht die ganze Karte und kann die Spielerperspektive eines gewählten Tokens
  ausdrücklich an-/ausschalten. Vorschau verändert keine gespeicherte Player-Aufklärung.
  DM-Wand-/Lichtuntermenü listet bestehende Geometrie und öffnet vorhandene CRUD-Wege.
  Fog-/Geometrieereignisse aktualisieren die Darstellung; Reconnect/Kartenwechsel
  verwirft alte Projektionen. Serverrollen, Ressourcenbindung und Datenrechte bleiben erhalten.
- **U09:** Freie Cursorposition ist Standard. Snap ist eine explizite Option;
  geometrisches Messen und Spielbewegungs-/Diagonalregel werden nicht über denselben
  Schalter verändert. Formursprung, Kreisradius außen und cursornahe Distanz bleiben
  bei Zoom lesbar. Vier Quadranten, Abbruch und Touch berücksichtigen. Vorhandene
  Wegpunkte bleiben nutzbar, keine dauerhafte Messobjekt-Datenbank.
- **U10:** Ein eigenständiger DM-Rasterdialog bietet Pixelgröße, sichtbares Raster
  und Aufklärungs-/Lichtoptionen; physischer Maßstab bleibt eigener vorhandener Wert.
  Serverseitig validierter Tischkontext, optimistische Revision, Ereignis an andere
  Clients. Weltkoordinaten der Tokens/Wände/Lichter bleiben erhalten. Bestehende
  Aufklärung wird beim Rasterwechsel konservativ auf neue Zellen abgebildet oder
  nach ausdrücklicher UI-Bestätigung zurückgesetzt; keine versehentliche Freilegung.
- **U11:** Select und Pan bleiben klar erkennbar. Ein expliziter Pan-Schalter und
  temporäre Pan-Geste erlauben den Wechsel; leere Kartenflächen lassen sich mit
  Schwellwert verschieben. Eigen-/Fremdtoken, Eingabefokus und Pinch bleiben korrekt.
- **U12:** Token platzieren öffnet zuerst die persönliche Bibliothek. Gewählte Vorlage
  plus bewusster Kartenklick erzeugt genau einen Token ohne redundanten Dialog. Neue
  Tokens/Upload behalten den Erstellungsweg. Abbruch/Werkzeugwechsel löscht die Vorlage.
  Serverseitige erlaubte Werte und Bindung werden weiter geprüft; Name/Bild/Größe/Typ/
  Rotation/HP-Max/Sichtweite werden übernommen, keine alte Initiative, Position oder
  Zustände. Eine Figur pro Karte, kein Heilen einer gebundenen Figur durch Platzierung.
- **U13:** Erster gültiger Initiativewurf wird übernommen; weitere verschiedene
  Würfe werden zur DM-Auswahl vorgemerkt, ohne stilles Überschreiben. Ein Transport-
  Replay ist kein neuer Kandidat. Native Sheet-, externe und verbleibende Turn-Tracker-
  Wege laufen unter demselben Besitz-/Kontextvertrag; bloße Namen sind keine Autorität.
  DM kann einen Kandidaten bestätigen und eine neue Sammelrunde ausdrücklich starten.
  Gleichzeitige Bestätigung benutzt Revision/Sperren; aktiver Zug bleibt bei Sortierung
  stabil. Player ohne Bogen sehen keinen unpassenden eigenen Würfelbutton; NPC-/DM-
  Eingabe bleibt möglich. Combatfehler wird mit konkreter Reise geprüft und korrigiert.
- **U14:** Hierarchie ist kampagnenweit und wird über Sitzungen erhalten. Oberseiten
  sind vorhandene Karten; zusätzliche kartenlose Ordner gehören nicht zum Startumfang.
  Karte kann Elternkarte sein; beliebige sichere Tiefe statt festem Drei-Ebenenlimit.
  Server verhindert Zyklen und fremde Eltern; Revisionen schützen konkurrierendes Umhängen.
  Verborgene Eltern verraten Playern keine Namen/IDs; erlaubte Kinder erscheinen dann
  als Wurzeln. Entfernen einer Seite hebt ihre Kinder eine Ebene hoch; aktive Karte
  bekommt eine gültige Folgeseite. Baum-/Breadcrumb-UI mit Elternauswahl ohne Drag.

## Risiken und Behandlung

Die Medium-Risiken aus Research werden durch die vorstehenden Daten-/Rollenregeln,
additive Modelle, Geometriebudget/Caching, Sprach-/Quelltrennung und gezielte positive
und negative Tests behandelt. Implementierungsbefunde werden im Deploy-Protokoll
festgehalten; nötige begrenzte Designkorrekturen werden vor dem zugehörigen Code ergänzt.
Kein pauschales Öffnen alter Endpunkte oder Rollenfallback. Kein unnötiges Zurücksetzen
von Produktivdaten; Schemaeingriffe sind additiv und werden vorher gesichert.

## Abnahme und Deploy-Handoff

Normale Navigation für alle sechs Buchflächen, DE/EN/Night, Desktop und 390px;
Bibliothek → Platzierung/Abbruch; Messung bei Zoom; DM-Rasteränderung mit zweitem
Client; Altverlauf mit Entzug/Fremdkampagne; eigener Sheet-/Beyond20-Wurf und bestätigter
Reroll; sichtbare wandbegrenzte Beleuchtung und DM-Vorschau ohne Player-Datenleck;
Hierarchie über Reload/Sitzungswechsel und Owner-as-Player-Negativfälle; vollständige
englische Navigation/Compendium-Suche und unveränderte deutsche Pins.

Umsetzung folgt jetzt auf diese Verträge. Claude-Dateibesitz wird vor jedem Lauf
festgehalten, keine geteilten gleichzeitigen Schreibdateien. Codex prüft/integriert,
führt gezielte Tests im vorhandenen Image aus, erstellt Commit/Push und liefert nur
diesen Auftrag mit recoverbarem Vorimage, Schema-/Compose-Beleg und Live-UI-Prüfung.
Die bestehenden Forschungsdokumente bleiben historische Aufnahme, keine Lieferbehauptung.

## Deploy-Befund: Koordinatenvertrag

Die vorhandene Kartenansicht interpretiert alte Tokens ohne Positionsmodus bei
kleinen x/y-Werten als Rasterkoordinaten, die ältere Fog-Berechnung benutzte dagegen
Pixel. Die neue Projektion und Fog verwenden denselben expliziten Resolver. Vor
einem Rastergrößenwechsel werden bestehende Tokens unter Kartensperre in
Pixelkoordinaten überführt; ihre Kartenposition bleibt erhalten. Reine
Geometrieaufrufer bleiben bei Weltkoordinaten. Tests mit beabsichtigten Pixelwerten
kennzeichnen diese ausdrücklich. Dies korrigiert die bestehende Inkonsistenz
innerhalb des autorisierten Licht-/Rastervertrags.

Auch alte Kartendimensionen bis 200 werden wie im bestehenden Renderer als
Rasteranzahl aufgelöst. Projektion und konservative Fehlerabdeckung verwenden
die vollständige Weltgröße. Beim Rasterwechsel werden solche Dimensionen
zusammen mit alten Tokenpositionen in Pixel normalisiert, um die bestehende
Fläche und Platzierung zu erhalten.

## Deploy-Befund: Messformen und Darkness

Quadrate werden wie Kreise am ersten Punkt zentriert und vom zweiten Punkt bis
zum Rand aufgezogen; die Oberfläche benennt den Mittelpunkt ausdrücklich. Dies
vermeidet den Sprung einer ganzen Quadratseite beim Überqueren einer Achse.
Radiusbeschriftungen liegen radial außerhalb und berücksichtigen ihre Textanker.
Darkness behält die etablierte kreisförmige Ausschlusszone unabhängig von Wänden;
Fog, Tokenvorschau und Bildprojektion verwenden dieselbe Bedeutung. Lichtverläufe
werden direkt auf die begrenzte Projektionsfläche abgebildet, sodass sehr große
zulässige Radien keine unbeschränkt großen Zwischenbilder erzeugen.

Normalisierte Kartendimensionen tragen in der bestehenden JSON-Konfiguration
`light_rules.dimensions_mode = "pixel"`; auch sehr kleine normalisierte Flächen
werden dadurch beim nächsten Rendern nicht erneut als Rasteranzahl interpretiert.
Bildantworten müssen außerdem zur lokalen aktiven Karten-ID passen; bei einem
Kartenrennen wird konservativ abgedeckt und Bootstrap neu geladen.

## Abschließender Sprachwechselvertrag

Eine ausdrücklich im Einstellungsdialog geänderte Sprache wählt auf einer bereits
geöffneten Regelwerk-/Compendium-Seite die entsprechende Edition. Dabei darf ein
automatisch ergänzter `locale=de`-Parameter den Wechsel nicht verhindern. Die
Compendium-Kategorie bleibt erhalten; sprachabhängige Detail-IDs und Filter werden
beim bewussten Editionswechsel zurückgesetzt. Ohne diesen ausdrücklichen
Einstellungswechsel bleiben direkte DE-/EN-Verweise sprachstabil.

## Abnahmebefund: Wand-/Lichteditoren

Die bestehenden Geometrieeditoren werden in der DM-Komposition wie andere
verschiebbare Tischfenster auf Body-Ebene eingebunden. Dadurch bleiben
Bearbeiten/Schließen über dem neuen Raster-/Lichtmanager erreichbar; die
vorhandenen CRUD-Handler und die Rollenprüfung bleiben maßgeblich.

## Visuelle Abnahme: SVG-Markierungen

Die Bildkontrolle fand eine bestehende DOM-Annahme: SVG unterstützt die
`HTMLElement.hidden`-Eigenschaft nicht wie HTML. Markerschalter und
Spielervorschau verwenden deshalb das tatsächliche `hidden`-Attribut mit einer
expliziten SVG-CSS-Regel. Browser- und Live-Prüfung kontrollieren die berechnete
Sichtbarkeit der Ebene, nicht nur eine JavaScript-Eigenschaft.

Der Optionsvertrag wird auch ohne platzierte Lichter geprüft: Bei aktiviertem
dynamischem Sichtmodell begrenzen vorhandene Wände die aktuelle Sicht. Ohne
dynamisches Licht bleibt eingeschaltete Aufklärung eine Sichtmaske mit voller
Helligkeit der sichtbaren Bereiche; DM-Tokenvorschau und Player verwenden dieselbe
Bedeutung. Sind beide Optionen aus, wird die öffentliche Karte unmaskiert gezeigt.
