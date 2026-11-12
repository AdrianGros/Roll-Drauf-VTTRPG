# Apply C05 – begrenzte Landmassen als normale Rasterebene

Status: Design abgeschlossen, Launch erst nach geprüftem C04. Profil standard,
dauerhaft. Grundlage: C05-Discover, P5/R29 und vorhandene Dokument-/Historygrenzen.
Kein neuer Renderer, Dokumenttyp oder Generator für Klima, Flüsse und Siedlungen.

## Ziel und Vertrag

Ein sichtbarer Editor-Einstieg „Landmasse erzeugen“ öffnet Seed (uint32), Form
„Insel“ oder „zusammenhängende Landmasse“, Landanteil 10–80 %, Küstenunruhe 0–100
und Vorschauauflösung mit längster Kante 128/256/512. Die kürzere Kante folgt dem
Projektseitenverhältnis, mindestens 8. Parameter werden strikt normalisiert,
Generatorversion ist fest `landmass-v1`. Kein Zeitstempel oder Math.random im
Generator; „Neuer Seed“ ändert nur den sichtbaren Parameter. Dieselben normalisierten
Parameter samt Seitenverhältnis erzeugen dieselbe Uint8-Maske und denselben Digest.

Ein reines ES-Modul verwendet die vorhandene Mulberry-/Value-Noise-Methodik mit
fünf Oktaven. Insel nutzt einen Rand-/Zentrumabfall, Landmasse einen schwächeren
Abfall; Küstenunruhe gewichtet Noise gegen Form. Von einem deterministischen
Zentrum startet eine nach Feldhöhe priorisierte Vierernachbarschafts-Frontier;
Gleichstände entscheidet der Zellindex. Wachstum bis zur gewünschten Zellenzahl
liefert genau eine zusammenhängende Landfläche und einen nachvollziehbaren
Landanteil. Insel lässt einen begrenzten Wasserrand frei; nicht erfüllbare Parameter
werden sichtbar abgewiesen, nicht still verändert. Das ist eine bewusste kleine
Generatorlösung, keine geophysikalische Simulation.

Ein Worker unter festem same-origin Modulpfad berechnet ausschließlich Parameter
und Maske. Höchstens 262.144 Zellen, ca. 1,31 Millionen Noise-Oktavenschritte plus
begrenzte Frontier; keine projektgroßen Pixel im Worker. Transfer des Maskenbuffers
statt weiterer Kopien. Es läuft nur ein Auftrag; Parameter-/Projektwechsel,
Abbrechen oder Dialogschließen beendet den Worker. Sequenz und Projektgeneration
verhindern die Übernahme einer alten Antwort. 10-Sekunden-Walltimeout beendet den
Auftrag mit sichtbarem Hinweis. Das vorhandene CSP erlaubt same-origin Worker über
default-src self; kein blob, eval oder externes Script erforderlich.

Vorschau bleibt höchstens 512², rein lokal und ohne Dokument-/Autosaveänderung.
Die UI zeigt effektive Parameter, Version und tatsächlichen Landanteil. Übernehmen
fügt ausschließlich eine neue normale Rasterebene mit bestehendem Landmaterial und
Küstenflag hinzu. Vorhandene Zeichnungen bleiben erhalten. Ein lesbarer Ebenenname
enthält Version, Seed und Parameter innerhalb der vorhandenen Namensgrenze. Keine
neuen Metadatenfelder oder Änderung des Import-/Serverformats. PNG/JSON/ZIP und die
private Bibliothek erhalten das Ergebnis über die bereits vorhandene Serialisierung.

## Speicher, Undo und Abnahme

Vor Vollauflösungsallokation gelten vorhandene Grenzen: 32 Ebenen, acht Rasterebenen,
32 Millionen Rasterpixel insgesamt. Die neue Canvas kostet w*h*4 Bytes plus kleinen
Befehlsheader; der History-Schritt rechnet diesen tatsächlichen gehaltenen Speicher
an und hält genau eine Canvasreferenz. Kein Vorher-/Nachher-Vollbild und keine
Änderung einer bestehenden Rasterebene. Übersteigt der Schritt das aktuelle
64-MiB-Budget, wird die Übernahme vorher verweigert; 4096² plus Header passt nicht.
Die UI erklärt diese Grenze. Kein verstecktes Downsampling des Projekts. Ein Undo
entfernt die neue Ebene, ein Redo stellt genau dasselbe Raster wieder her; spätere
Zeichenbefehle verwenden die bestehende Reihenfolge. Cancel verändert keine History.

Prüfungen im Deploy: feste Maskendigest-Vektoren, andere Seeds, Parametergrenzen,
Viererzusammenhang und Landanteil; Workerantwort nach Parameter-/Projektwechsel,
Abbruch und Timeout; Vorschau ohne Dokumentänderung; Übernahme genau ein Undo/Redo,
Layer-/Pixel-/Historygrenze vor Mutation; Save/Reload und JSON/ZIP/PNG-Rundlauf.
Gezielte Browsermessung der maximalen Vorschau: Desktop-Ziel unter zwei Sekunden,
390-px-Browser unter fünf Sekunden auf der Testmaschine, jeweils mit gemessenen
Werten im Beleg. Diese Werte sind Abnahmekriterien, noch keine Messbehauptung;
Timeout bleibt die harte Laufzeitgrenze. DE/EN und Nacht/Papier prüfen.

Medium-Risiken UI-Blockade, veraltete Vorschau und Undo-/Speicherverlust sind durch
Workerterminierung, Generation und Allokations-Preflight behandelt. Handoff nach
C04-Quellabgleich: exakt zugewiesene Editor-/Worker-/Generator-/Dialogdateien,
tasks/c05.json und fokussierte Tests; kein Backend oder Schema. Claude implementiert,
Koordinator prüft und lässt einen separaten Diffreview durchführen, pusht und liefert
app-only mit Vorimage und normaler Live-Editorreise. Danach Monitor; C09 erst nach
diesem und dem Bibliothek-zum-Tisch-Gate.

Primärquellen aus Discover: [Worker](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Using_web_workers),
[Transferable objects](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Transferable_objects),
[ImageData](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/createImageData).
Algorithmus und Budget sind explizite Repo-Entscheidungen, keine Zusagen dieser Quellen.
