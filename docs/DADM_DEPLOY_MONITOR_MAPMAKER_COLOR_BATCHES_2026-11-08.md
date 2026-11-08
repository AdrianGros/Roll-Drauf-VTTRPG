# Deploy / Monitor: vier Batches farbiger Karteneditor-Assets

Status: vier Batches committed, gepusht, auf der bestehenden Produktions-VTT veröffentlicht und live geprüft. Profil `standard`. Auftrag: alle im Discover positiv geprüften Künstlerpakete in vier Batches nutzbar integrieren; kommerziell kostenlos, passende Credits, keine KI-Bilder. Apply: [MAPMAKER_COLOR_BATCHES_APPLY_2026-11-08.md](research/MAPMAKER_COLOR_BATCHES_APPLY_2026-11-08.md).

## Ergebnis und Benutzerweg

**VTT → Dashboard → Hauptnavigation „Karten“ → Stempel → Quelle/Kategorie/Suche → Motiv oder Bildblattausschnitt → Karte.** Rollen: DM und Player; keine neue URL muss bekannt sein. Bereits offene Editoren neu laden. Künstler-Credits sind in der Kopfzeile, im Stempelbereich und in der Hilfe erreichbar.

17 neue Quellen, 65.602 zusätzliche PNG-/Blatt-Einträge. Insgesamt 31 Pakete mit 72.058 Raster-Stempeln und zehn Texturen, 72.068 CSV-Zeilen. Die Zahl bezeichnet Quelldateien/Varianten/Bildblätter, keine Anzahl fertiger Häuser. LPC allein enthält 63.972 Figuren-/Kleidungsblätter, daneben Häuser, Objekte, Gelände, FX und klar benannte Referenzen. Identische Originaldateien behalten getrennte Katalog-IDs, teilen aber eine PNG-Datei. Alle unterschiedlichen Stempelbilder wurden tatsächlich im Browser gezeichnet.

Der bestehende Bestand bleibt erhalten: 38 Kenney-Cartography-Stempel, 6.418 K.-M.-Alexander-Stempel, zwei Pergamenttexturen, acht Foto-Materialien. Zusätzlich gibt es sechs Canvas-Symbole (Windrose und Ortsnadel regulär; Berg, Baum, Haus, Burg als Kenney-Fallback) und 22 Pinselmaterialien: Land, Wiese, Wald, Steppe, Wüste, Schnee, Sumpf, Fels, Asche, Basalt, Lava, Flachwasser, Fluss, Weg plus acht Poly-Haven-Fotomaterialien. Diese bereits vorhandenen Canvas-/Verfahrensinhalte sind keine neu heruntergeladenen Künstlerbilder.

Exaktes Inventar je Datei: [lokale CSV](../vtt/static/mapmaker/assets/inventory.csv), [öffentliche CSV](https://vtt.roll-drauf.de/static/mapmaker/assets/inventory.csv); SHA256 `3da095aabce8b26aa2ce2b5d2476d234ae2332ed690db3433d3ea172148bd16c`. Lizenz-/Originalpfad-/Dateihash-Nachweise: je Paket `manifest.json` und `License.txt`, für die neuen Pakete zusätzlich `coverage.json` und Original-Credits, sowie [Quell-Lock](../vtt/static/mapmaker/assets/color-source-lock.json). Die LPC-Revision ist `f07f7f5892e67c932c68f70bb04472f2c64e46bc`.

| Paket | Batch | Stempel/Blätter | Texturen | Lizenz |
|---|---:|---:|---:|---|
| Kenney · Cartography | Bestand | 38 | 2 | CC0-1.0 |
| Müller · Historische Karten | Bestand | 1.631 | 0 | CC0-1.0 |
| Myer · Historische Karten | Bestand | 148 | 0 | CC0-1.0 |
| Kensett · Historische Karten | Bestand | 387 | 0 | CC0-1.0 |
| Zuodong · Historische Karten | Bestand | 347 | 0 | CC0-1.0 |
| Ishikawa · Historische Karten | Bestand | 754 | 0 | CC0-1.0 |
| Hyacinth · Historische Karten | Bestand | 196 | 0 | CC0-1.0 |
| Homann · Historische Karten | Bestand | 429 | 0 | CC0-1.0 |
| Vischer · Historische Karten | Bestand | 959 | 0 | CC0-1.0 |
| Van der Aa · Historische Karten | Bestand | 192 | 0 | CC0-1.0 |
| Gomboust · Historische Karten | Bestand | 607 | 0 | CC0-1.0 |
| Blaeu · Historische Karten | Bestand | 513 | 0 | CC0-1.0 |
| Walser · Historische Karten | Bestand | 255 | 0 | CC0-1.0 |
| Poly Haven · Gelände | Bestand | 0 | 8 | CC0-1.0 |
| Kenney · Roguelike / RPG | 1 | 5 | 0 | CC0-1.0 |
| Kenney · Tiny Town | 1 | 136 | 0 | CC0-1.0 |
| Kenney · Medieval RTS | 1 | 260 | 0 | CC0-1.0 |
| Kenney · Isometric Buildings | 1 | 132 | 0 | CC0-1.0 |
| Indie Squid · Green Village | 1 | 39 | 0 | CC0-1.0 |
| LPC Revised · Häuser, Welt & Figuren | 2 | 64.310 | 0 | OGA-BY-3.0 |
| 2DPIXX · Wald | 3 | 1 | 0 | CC-BY-4.0 |
| 2DPIXX · Höhlen | 3 | 1 | 0 | CC-BY-4.0 |
| 2DPIXX · Schnee | 3 | 1 | 0 | CC-BY-4.0 |
| 2DPIXX · Stadt | 3 | 1 | 0 | CC-BY-4.0 |
| 2DPIXX · Isometrische Waldruinen | 3 | 2 | 0 | CC-BY-4.0 |
| 2DPIXX · Isometrische Einrichtung | 3 | 2 | 0 | CC-BY-4.0 |
| 2DPIXX · Isometrisches Dorf | 3 | 1 | 0 | CC-BY-4.0 |
| 2DPIXX · Dunkles Gebirge | 3 | 1 | 0 | CC-BY-4.0 |
| rubberduck · Mittelalterliche Dorfobjekte | 3 | 708 | 0 | CC0-1.0 |
| Evert · LPC Castle | 4 | 1 | 0 | CC-BY-3.0 |
| Zabin · Castle Tiles for RPGs | 4 | 1 | 0 | CC-BY-3.0 |

## Umsetzung

- Alle neuen PNGs und deterministisch gerasterten SVGs lokal verfügbar; keine generative Erstellung, KI-Hochskalierung oder Laufzeitbilder von externen Asset-Servern. Herkunft: Original-Künstlerveröffentlichungen, Original-Credits, Kenneys eigene No-AI-Erklärung und historische Künstler-/Renderingnachweise.
- Bildblätter: freier Originalpixel-Ausschnitt, Rasterhilfe, Zahlenfelder, Maus/Touch, Einpassen/Originalgröße/2×/4×. Voreinstellung: erster nichttransparenter Rasterbereich, bei Raster 1 das ganze Bild. Einzelne Frames, Bauteile und größere Gebäude bleiben damit verwendbar.
- Validiertes optionales `crop`-Feld bei Stempeln; gleiche Geometrie in Auswahl, Vorschau, Rendering, Undo/Redo, Entwurf, Projektdatei und PNG/ZIP. Ganzzahlige Quellgrenzen werden beim Import geprüft; keine beliebigen URL-Assets.
- Kein stiller 10.000-Einträge-/32-Pakete-Cutoff. Kompakter lokaler Index ohne Hash-/Pfad-Duplikate beim Start, vollständiges Herkunftsmanifest separat. Bilder erst bei Benutzung; 64 sichtbare Paletteneinträge, begrenzte Orts-Symbollisten statt 70.000 nativer Optionen. Pixelgrafik bleibt in der Kartenzeichnung scharf.
- PNG erhält UTF-8-iTXt-Credits der verwendeten Quellpakete. ZIP enthält dieselben Angaben zusätzlich als CREDITS.txt; Hinweise zur Veröffentlichung sind im Exportdialog und auf der Credits-Seite. LPC liefert alle 35 Original-Credits-Dateien mit. Keine pauschale CC0-Behauptung für BY-Inhalte.
- Additive Importwerkzeuge: `tools/import_mapmaker_color_assets.py --batch 1..4 --cache <Pfad>`, `tools/mapmaker_catalog.py`, SVG-Helfer `tools/render_mapmaker_svg.py`. Der bisherige CC0-Importer erhält neue Pakete bei Wiederholung.

Geändert wurden ausschließlich statische Karteneditor-Dateien, gezielte Tests, Import-/Katalogwerkzeuge und DAD-M-/Belegdokumente. Keine Datenbank-/Auth-/Playtable-Implementierung in diesen Commits; fremde Dirty-Dateien und die vorgemerkte fremde Migration wurden nicht in die Commits aufgenommen.

## Verifikation

- Vollständige Hash-/Lizenz-/Coverage-/Index-Abgleiche für alle 31 Pakete. Jedes akzeptierte PNG beim Import mit Pillow decodiert; zusätzliche Alpha-Prüfung ohne vollständig transparente Leerbilder.
- Chromium hat **62.960 unterschiedliche PNG-Hashes** per `Image.decode()` geladen, durch die produktiven `stampExtent`/`drawStampImage`-Funktionen gezeichnet, sichtbare Pixel geprüft und anschließend einen Randausschnitt gezeichnet. **0 Fehler**, 658.88 Sekunden. Bytegleiche Varianten werden durch ihren Hash abgedeckt; [Ergebnis](proofs/mapmaker-color-batches-2026-11-08/all-pixels-verification.json), ausführbarer Prüfhelfer im Belegordner.
- Alle **72.064 bekannten Symbol-IDs** (72.058 PNGs + sechs Canvas-Symbole) in zulässigen Dokumentbatches durch Platzierungs-/Importvalidierung und Rand-Crops geprüft. Grenzverletzungen, Nullmaße und gebrochene Crop-Zahlen werden abgewiesen.
- Gesamtlauf `tests/test_mapmaker_static.py tests/test_mapmaker_browser.py`: 54 erfolgreich, ein veralteter Credits-Zählwert schlug fehl. Nach Korrektur der Zählung und Wiederherstellung des bisherigen Rücklink-Wortlauts: **16 fokussierte Prüfungen erfolgreich**, darunter alle statischen Verträge, Credits/acht Fotomaterialien, Desktop/Handy, Pixeländerung, Zoom, PNG-/ZIP-Metadaten und neue sichtbare Crop-Vorauswahl. Über Gesamtlauf/Fokusnachläufe sind **57 unterschiedliche finale Testfälle** erfolgreich abgedeckt. Acht bestehende Eventlet/reportlab/ORM-Warnungen. [Genaue Testbilanz](proofs/mapmaker-color-batches-2026-11-08/test-summary.json); ursprüngliches Fehlerlog bleibt transparent erhalten.
- Laufende Produktion: **62970 Bilddateien** vollständig gelesen und jeweils SHA256/PNG-Maße mit dem Manifest verglichen, 72.058 Stempel plus zehn Texturen, **0 Fehler**. [Live-Dateinachweis](proofs/mapmaker-color-batches-2026-11-08/live-inventory-verification.json).
- Je Batch beide Rollen über die echte Dashboard-Navigation geprüft, jedes neu hinzugekommene Paket mit tatsächlicher UI-Platzierung; Haus, Figur, SVG-Haus, Geländetile und Burgteil. Projekt speichern/rückimportieren, PNG/ZIP-Credits, Credits-Seite, kein horizontaler Seitenüberlauf, keine Seitenfehler/CSP-Verletzungen. In Batch 4 zusätzlich die zuvor leere Mountain-Vorauswahl und SVG-Dorfquelle live geprüft. Sitzungen waren kurzlebige serverseitig signierte Kontexte vorhandener Konten; keine Kontenänderungen und kein simulierter Discord-Loginflow als Erfolgsbehauptung.

| Batch | Rolle | Breite | Startzeit im Test | Live-Abnahme |
|---:|---|---:|---:|---|
| 1 | dm | 1440 px | 4431 ms | 5 Motive, Speichern/Rückimport, PNG/ZIP-Credits |
| 1 | player | 390 px | 3940 ms | 5 Motive, Speichern/Rückimport, PNG/ZIP-Credits |
| 2 | dm | 1440 px | 6841 ms | 2 Motive, Speichern/Rückimport, PNG/ZIP-Credits |
| 2 | player | 390 px | 4724 ms | 2 Motive, Speichern/Rückimport, PNG/ZIP-Credits |
| 3 | dm | 1440 px | 6038 ms | 9 Motive, Speichern/Rückimport, PNG/ZIP-Credits |
| 3 | player | 390 px | 5495 ms | 9 Motive, Speichern/Rückimport, PNG/ZIP-Credits |
| 4 | dm | 1440 px | 5761 ms | 4 Motive, Speichern/Rückimport, PNG/ZIP-Credits |
| 4 | player | 390 px | 4752 ms | 4 Motive, Speichern/Rückimport, PNG/ZIP-Credits |

## Quellstände, Images und Schutz der laufenden Produktion

| Batch | Quellcommit | Veröffentlichtes Image |
|---:|---|---|
| 1 | `b5896f522f050316175bce9a47485af9a9a0c7d5` | `roll-drauf-vtt-app:mapmaker-color-b1-20261108-b5896f52` |
| 2 | `08fa90ea4f43137bf748ada03518f5f5ed9aae6b` | `roll-drauf-vtt-app:mapmaker-color-b2-20261108-08fa90ea` |
| 3 | `be52d043c7102b1fe5699c5aa3e6b3c7506f1d75` | `roll-drauf-vtt-app:mapmaker-color-b3-20261108-be52d043` |
| 4 | `dd1084c48b100ab7e227e8a806fb26a424773c4d` | `roll-drauf-vtt-app:mapmaker-color-b4-20261108-dd1084c4` |

Aktuell laufendes Image: `sha256:e72a98bc24943c658d76038cb8554038c9e444cefd1f64373be682e10a5d879b`. Statischer Quellstand: `dd1084c48b100ab7e227e8a806fb26a424773c4d`. Alle vier Quell-Commits wurden nach `origin/feat/mapmaker-content-20261108` gepusht.

Vor Batch 4 wurde parallel das Playtable-Image `roll-drauf-vtt-app:playtable-seats-20261108-ec20e46` mit Quellrevision `ec20e46fcb4846306466a0964fd8f58177f79d07` veröffentlicht. Vollständiger Vergleich: **63145 Karteneditor-Dateien identisch zu Batch 3**, sämtliche Batch-3-Layer im neuen Basisimage enthalten. Batch 4 wurde deshalb auf diesem aktuellen Image `sha256:e4ef683613731af648ad353156ea0194a7e53c5bdf415d7c70b7e733a1be94e1` gebaut. Alle Basis-Layer und Start-/Env-/Healthcheck-Konfiguration bleiben erhalten; nur `vtt/static/mapmaker` aus dem Quellcommit wurde darüber kopiert. [Abgleich](proofs/mapmaker-color-batches-2026-11-08/production-reconciliation.json).

Compose unverändert im Projekt `migration-production`, bestehende `/srv/migration/2026-10-07/setup/production.compose.json` und `production.duck-species.override.yml`; nur deren App-Image wurde ersetzt. App-Health und öffentliche HTTPS-Dateihashes geprüft.

**Aktueller Rollback:** `/srv/migration/2026-10-07/setup/mapmaker-color-b4-20261108/rollback.sh`, Vorimage `roll-drauf-vtt-app:before-mapmaker-color-b4-20261108` = `sha256:e4ef683613731af648ad353156ea0194a7e53c5bdf415d7c70b7e733a1be94e1`. Dieser Rückweg erhält die parallel gelieferte Playtable-Version. Frühere vollständige Image-Rollbacks auf Batch 1/2 würden inzwischen neue Backendarbeit entfernen und sind für den aktuellen Stand kein geeigneter Gesamtrückweg. Neue Karten mit den beiden Burgpaketen können nach einem Batch-4-Rollback erst mit erneut verfügbaren Paketen geöffnet werden.

## Akzeptanz und verbleibende Grenzen

- [x] Alle 17 im Discover freigegebenen neuen Quellen plus 14 Bestandspakete integriert; vollständige Coverage statt stiller Auslassungen.
- [x] Alle unterschiedlichen Künstler-PNGs wirklich im Browser gezeichnet; jede Katalog-ID durch Platzierungs-/Crop-Verträge geprüft.
- [x] Alle neuen Pakete aus der normalen UI erreichbar und je Batch für DM/Player live bedient.
- [x] Quellen, Künstler, konkrete Lizenzroute, Originalnachweise und mitlieferbare Export-Credits vorhanden; keine KI-Bilder aufgenommen.
- [x] Vier explizite Quell-Commits, Push, Live-Images, Prüfungen und aktueller geschützter Rückweg dokumentiert; neuere Playtable-Arbeit erhalten.

Eine ausdrücklich dokumentierte upstream-Ausnahme: `Characters/Clothing/Feminine, Thin/Torso 2/Sweater 01 - Cardigan/Charcoal/Emotes.png` ist im LPC-Originalarchiv **0 Bytes** groß und enthält kein platzierbares Bild. Sie wird nicht als erfolgreich importiertes Asset gezählt und nicht erfunden/rekonstruiert.

Niedrige Restgrenzen: Bildblätter sind manuell frei zuschneidbar; kein automatischer RPG-Autotile- oder animierter Figuren-Assembler. Die große LPC-Auswahl benötigt beim Erstladen Metadaten; der Browser lädt deren Pixel dennoch nur auf Verwendung. Das additive Crop-Feld bleibt Formatversion 1; alte Editorstände vor dieser Lieferung verstehen neue Ausschnitte nicht. PNG-Plattformen können Metadaten entfernen, deshalb ZIP-Credits/Begleittext bei Veröffentlichung nutzen. Künstler-Freigaben und historische Provenienz sind die Grundlage der No-AI-Auswahl, kein vermeintlich unfehlbarer Bilddetektor.

Monitor-Empfehlung: diesen begrenzten Content-Milestone schließen. Keine offenen Lieferblocker innerhalb des freigegebenen Umfangs.
