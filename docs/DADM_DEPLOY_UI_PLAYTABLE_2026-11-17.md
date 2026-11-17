# UI und Playtable: vollständige Umsetzung und Lieferung

17.11.2026 · DAD-M standard / Deploy → Monitor. Status: live ausgeliefert und geprüft.
Der Owner hat Umsetzung bis zur Live-Lieferung
aller Feedbackpunkte autorisiert. Ausgangsbasis 3939766e7; laufende Anwendung vor
der Lieferung d4ff7e4fe, Image sha256:7d8f4a54b36b125611ac116b37d10c09632dbea9a920c8c5b0413ea63efd4617.
Implementierung im separaten Arbeitsbaum `roll-drauf-vtt-ui-playtable-20261117`;
der ursprüngliche dirty Arbeitsbaum bleibt unangetastet.

Produktionsadresse: https://vtt.roll-drauf.de. Quellcommit:
`6a2fcedce2d2396a52109e1093194da902a7912e`, auf
`origin/feat/ui-playtable-20261117` gepusht. Laufendes Image:
`sha256:3de96a3ce53034adc559e5bca92b27d6adcb571848b75022d0bf3735493b358d`.
Diese gemeinsame Lieferidentität gilt für alle folgenden 14 Punkte. Der spätere
Belegcommit enthält ausschließlich Dokumentation und Prüfartefakte.

## Ergebnis und Benutzerwege

| ID / Bereich | Normaler Einstieg und Rolle | Erfülltes Abnahmekriterium |
| --- | --- | --- |
| U01 Buchoberflächen | Gemeinsame Navigation → Gespräche, Karten, Atlas, Creation Engine, Regelwerk, Compendium; bestehende Kontorechte | Gemeinsamer Buchrahmen, Modul-/Dialogfunktion, DE/EN, Desktop/390/320 |
| U02 Frühere Nachrichten | Kampagnenchat → Conversations → Frühere Sitzungen; aktive Mitglieder | Öffentliche historische Sessiontexte mit Herkunft; kein Blind-/Privatinhalt; Entzug wird geprüft |
| U03 Englisches Compendium | Einstellungen → English → Compendium; bestehender Regelzugang | Englische Suche/Filter/Details, bewusster Editionswechsel, DE-Pins bleiben gültig |
| U04 Englisches SRD | Einstellungen → English → Regelwerk; bestehender Regelzugang | Vollständige strukturierte native Edition mit eigenem Buchaufbau und Lesehinweisen; Originaltext/Attribution eindeutig |
| U05 Nachtfarben | Einstellungen → Nacht → Standardakzent; alle Rollen | Edo/Gray/Ink/Natural; messbarer Text-/Chatkontrast, aktive Tischwerkzeuge sichtbar |
| U06 Markierungen/Sicht | Tisch → Markierungen und Raster & Licht; DM | Markierungen schaltbar und von Licht/Sicht unterschieden; in Token-Spielervorschau tatsächlich verborgen |
| U07 Dynamisches Licht | Tisch → Raster & Licht → Perspektive; DM sowie gesonderter Player-Einstieg | Wandbegrenzte 2D-Strahlenprojektion, DM-Gesamtkarte und ausdrückliche Tokenvorschau; keine vollständige Geometrie für Player, keine Vorschau-Aufklärung |
| U08 Wanduntermenü | Tisch → Raster & Licht → Wände und Lichter bearbeiten; DM | Liste und vorhandene CRUD-Wege erreichbar, Editor über Fenster, Wand begrenzt Sicht |
| U09 Messung | Tisch → Messen; alle Tischrollen | Freier Cursor als Standard, eigener Snap, lesbare Labels, Mittelpunktformen und Radius außen |
| U10 Raster | Tisch → Raster & Licht; DM | Größe/Anzeige/Licht/Aufklärung, Revision und zweiter Client; alte Weltpositionen bleiben erhalten; Aufklärungsreset ausdrücklich |
| U11 Wählen/Bewegen | Tisch → Wählen bzw. Bewegen; alle Tischrollen | Eigenständiger Schalter, Ziehen leerer Fläche mit Wählen, mittlere Maustaste; Token-Weltpositionen bleiben gleich |
| U12 Tokenbibliothek | Tisch → Tokens → Vorlage → Kartenklick; eigene Bibliothek je Sitzmodus | Ein direkter neuer Token mit erlaubten Vorlagenwerten, keine alte Initiative/Zustände; neue Tokens/Uploads eigener Weg |
| U13 Initiative/Kampf | Eigener Bogen bzw. Beyond20 → Initiative; DM → Initiative-Fenster | Erster Wurf angenommen, weitere Kandidaten bestätigt, Wiederholung dedupliziert, neue Runde ausdrücklich; Kampfstart/-zug/-ende |
| U14 Seitenhierarchie | Tisch → Seiten → Unterseite von; DM, erlaubte Projektion für Player | Kampagnenpersistenz, keine Zyklen/fremden Eltern, verborgene Eltern nicht verraten; Reload/Sitzungswechsel |

Delay bleibt gemäß Owner-Entscheidung bestehen. Kein neuer Importer, keine neue
Laufzeitabhängigkeit und keine separate Staging-Voraussetzung.

## Umsetzung und Daten

Additive Tabellen: `map_view_settings`, `page_hierarchy_states`, `map_page_parents`,
`initiative_rounds`, `initiative_candidates`. Die vorhandene JSON-Kartenkonfiguration
kennzeichnet bei einem Rasterwechsel normalisierte Pixeldimensionen; Tokens werden
dabei aus alten Rasterkoordinaten in identische Weltpositionen überführt.
Lichtberechnung und Bildprojektion teilen den Koordinaten- und Darkness-Vertrag.
Wände begrenzen Sicht auch ohne platzierte Lichter; ausgeschaltetes dynamisches
Licht hebt gespeicherte Aufklärung nicht auf. SVG-Markierungen verwenden ein
tatsächliches `hidden`-Attribut, damit die Vorschau keine DM-Geometrie zeigt.
Die Player-Fläche lädt und initialisiert keinen DM-Controller; serverautorisierte
Tischkontexte begrenzen HTTP, Socket, Kandidaten und Vorschau.

Das englische Paket entsteht deterministisch aus dem gepinnten offiziellen SRD
5.2.1. Eigene englische Lesehinweise und Buchgliederung werden vom unveränderten
lizenzierten Regelkörper unterschieden. Der Text wird nicht als vollständig
paraphrasiert ausgegeben. Quellen, Lizenz, Seiten und vollständige Abdeckung
sind im Paket dokumentiert; die Original-PDF bleibt zugänglich.

Tatsächlich beauftragte Claude-Code-Worker lieferten die Ausgangsimplementierung
für Buch/Palette und englischen Builder; beide endeten am Fünf-Stunden-Limit.
Codex übernahm Integration und Korrekturen, einschließlich unabhängiger
Risikoprüfung. Es wurde kein kostenpflichtiger Provider-Fallback aktiviert.

## Verifikation und Lieferbeleg

Gezielte Backend-Suite: 92 bestanden. Buch-/Darstellungsprüfungen: 8 bestanden.
Englische Inhalte/API/Desktop/Mobil und deutsche Regressionen: 57 bestanden.
Abschließend: 12 Playtable-/Rollenprüfungen und eine gezielte Browserprüfung
für die ausdrückliche Aufklärungsreset-Bestätigung bestanden. Zusätzlich sind
der bewusste Editionswechsel im Einstellungsdialog und die bestehende
Beyond20-/Kampagnenraum-Reise geprüft; siehe `checks.json`.
Nach den Live-Befunden bestanden die gezielten Editor-/SVG-Browserprüfungen und
acht abschließende Backendprüfungen der Licht-/Wand-/Aufklärungskombinationen.
Die Zählungen überschneiden sich und sind keine Summe verschiedener Tests.
Relevante Ausgangstests wurden auf den ausdrücklich autorisierten Tischkontext
und die neue Farbentscheidung gebracht; Berechtigungen wurden nicht gelockert.

Belege: `docs/proofs/ui-playtable-2026-11-17/`. `review.md` trennt Quellprüfung
von tatsächlich ausgeführten Tests; `files-changed.json` enthält das Dateiinventar.
`release.json` und `delivery.json` dokumentieren Quellcommit, Imageidentität,
Backup/Schema, Compose und Rückrollreferenz. Alle 80.959 ausgelieferten Quelldateien
entsprechen dem committed Inhalt; 129 geänderte oder berechtigungsrelevante Dateien
sind zusätzlich im laufenden Container abgeglichen, ohne Quell-Bindmounts.

`live.json`: acht bestandene Produktionsreisen durch die normale Oberfläche,
Chromium-DM und Firefox-Player, einschließlich Owner-as-Player und Reload;
keine JavaScript-Seitenfehler. `live-pan.json`: zusätzliche bestandene
Mausgesten für DM und Player. Screenshots wurden auch visuell geprüft.
`cleanup.json` und `cleanup-pan.json`: beide ausschließlich synthetischen
Prüfkampagnen samt Konten, Sitzungen und Zugangsdateien entfernt.
`post-cleanup-health.json`: öffentliche Anwendung danach gesund.

Rückrollskript zur direkten Vorgängerversion:
`/srv/migration/2026-11-11/feedback-ui-playtable-vision-20261117/6a2fcedce/rollback.sh`.
Das Skript wurde syntaktisch geprüft; ein Rollback war nicht erforderlich.
Die Vorgängerimages und die validierten Datenbankarchive bleiben erhalten.
Andere Produktionsdienste wurden bei den App-Auslieferungen nicht neu gestartet.
Der Monitor-Abschluss steht in `DADM_MONITOR_UI_PLAYTABLE_2026-11-17.md`.

## Restrisiken

Eine kalte Polygonprobe mit 400 Wänden brauchte 0,732 s im Prüfimage; sehr komplexe
Karten bleiben ein Performancefall. Projektionsgröße und Zwischenbildspeicher
sind begrenzt, statische Polygone gecacht. Beyond20 wurde über den normalisierten
DOM-Vertrag geprüft; eine installierte Erweiterung beim jeweiligen Spieler wurde
nicht ausgeführt. Backup-Wiederherstellung und tatsächliche Rollbackausführung
wurden nicht geprobt. Es sind keine offenen Medium-/High-Befunde bekannt.
Prüfartefakte bleiben dauerhaft im Repository; Datenbankarchive verbleiben auf
dem Produktionshost, Zugangsdaten wurden nicht ins Repository übernommen.
