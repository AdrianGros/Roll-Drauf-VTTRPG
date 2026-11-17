# UI und Playtable: vollständige Umsetzung und Lieferung

17.11.2026 · DAD-M standard / Deploy. Der Owner hat Umsetzung bis zur Live-Lieferung
aller Feedbackpunkte autorisiert. Ausgangsbasis 3939766e7; laufende Anwendung vor
der Lieferung d4ff7e4fe, Image sha256:7d8f4a54b36b125611ac116b37d10c09632dbea9a920c8c5b0413ea63efd4617.
Implementierung im separaten Arbeitsbaum `roll-drauf-vtt-ui-playtable-20261117`;
der ursprüngliche dirty Arbeitsbaum bleibt unangetastet.

## Ergebnis und Benutzerwege

| Bereich | Normaler Einstieg und Rolle | Abnahmekriterium |
| --- | --- | --- |
| Buchoberflächen | Gemeinsame Navigation → Gespräche, Karten, Atlas, Creation Engine, Regelwerk, Compendium; bestehende Kontorechte | Gemeinsamer Buchrahmen, Modul-/Dialogfunktion, DE/EN, Desktop/390/320 |
| Frühere Nachrichten | Kampagnenchat → Conversations → Frühere Sitzungen; aktive Mitglieder | Öffentliche historische Sessiontexte mit Herkunft; kein Blind-/Privatinhalt; Entzug wird geprüft |
| Englisches SRD | Einstellungen → English → Regelwerk/Compendium; bestehender Regelzugang | Vollständige strukturierte Edition, Suche/Filter/Details und sprachstabile Links; DE-Pins bleiben gültig |
| Nachtfarben | Einstellungen → Nacht → Standardakzent; alle Rollen | Edo/Gray/Ink/Natural; messbarer Text-/Chatkontrast, aktive Tischwerkzeuge sichtbar |
| Licht und Wände | Tisch → Raster & Licht; DM | DM-Gesamtkarte, ausdrückliche Token-Spielervorschau, Wand-/Lichtliste und vorhandenes CRUD |
| Spielersicht | Derselbe Tisch, Player-Komposition | Wandbegrenzte Bildprojektion; keine vollständige Geometrie; Vorschau schreibt keine Aufklärung; konservative Fehlerabdeckung |
| Raster | Tisch → Raster & Licht; DM | Größe/Anzeige/Licht/Aufklärung, Revision und zweiter Client; alte Weltpositionen bleiben erhalten; Aufklärungsreset ausdrücklich |
| Messung/Bewegen | Tisch → Messen, Select/Bewegen; alle Tischrollen | Freier Cursor als Standard, eigener Snap, lesbare Labels, Mittelpunktformen und Radius außen; Pan/Token-Drag/Touch erhalten |
| Tokenbibliothek | Tisch → Tokens → Vorlage → Kartenklick; eigene Bibliothek je Sitzmodus | Ein direkter neuer Token, Name/Bild/Größe/Typ/Rotation/HP-Max/Sichtweite, keine alte Initiative/Zustände; neue Tokens/Uploads eigener Weg |
| Initiative/Kampf | Eigener Bogen bzw. Beyond20 → Initiative; DM → Initiative-Fenster | Erster Wurf angenommen, weitere Kandidaten bestätigt, Wiederholung dedupliziert, neue Runde ausdrücklich; Kampfstart/-zug/-ende |
| Seitenhierarchie | Tisch → Seiten → Unterseite von; DM, erlaubte Projektion für Player | Kampagnenpersistenz, keine Zyklen/fremden Eltern, verborgene Eltern nicht verraten; Reload/Sitzungswechsel |

Delay bleibt gemäß Owner-Entscheidung bestehen. Kein neuer Importer, keine neue
Laufzeitabhängigkeit und keine separate Staging-Voraussetzung.

## Umsetzung und Daten

Additive Tabellen: `map_view_settings`, `page_hierarchy_states`, `map_page_parents`,
`initiative_rounds`, `initiative_candidates`. Die vorhandene JSON-Kartenkonfiguration
kennzeichnet bei einem Rasterwechsel normalisierte Pixeldimensionen; Tokens werden
dabei aus alten Rasterkoordinaten in identische Weltpositionen überführt.
Lichtberechnung und Bildprojektion teilen den Koordinaten- und Darkness-Vertrag.
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
Relevante Ausgangstests wurden auf den ausdrücklich autorisierten Tischkontext
und die neue Farbentscheidung gebracht; Berechtigungen wurden nicht gelockert.

Belege: `docs/proofs/ui-playtable-2026-11-17/`. `review.md` trennt Quellprüfung
von tatsächlich ausgeführten Tests. Endgültiger Quellcommit, Imageidentität,
Backup/Schema, Compose-Lieferung und Rückrollreferenz werden in `release.json`
bzw. `delivery.json` abgelegt; Live-Reisen in `live.json`, Bereinigung in
`cleanup.json`. Diese Verweise sind keine vorweggenommene Fertigmeldung.

## Restrisiken

Eine kalte Polygonprobe mit 400 Wänden brauchte 0,732 s im Prüfimage; sehr komplexe
Karten bleiben ein Performancefall. Projektionsgröße und Zwischenbildspeicher
sind begrenzt, statische Polygone gecacht. Die installierte Beyond20-Erweiterung
kann durch den DOM-Vertrag getestet werden, ersetzt jedoch keine reale
Browserinstallation beim jeweiligen Spieler. Live-Abnahme und Imagegleichheit
werden nach der Auslieferung separat aufgezeichnet.
