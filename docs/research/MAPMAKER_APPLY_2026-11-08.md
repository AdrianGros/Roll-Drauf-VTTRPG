# Kartenwerkstatt: Apply, 2026-11-08

**Status:** abgeschlossen, Übergabe an Deploy im ausdrücklich beauftragten Integrationsumfang. **Input:** `MAPMAKER_DISCOVER_2026-11-08.md` und vollständiges Vorher-CSV. **Artefakte:** dieser Entwurf, lokale Paketmanifeste, Herkunftsregister und Nachher-Inventar (dauerhaft).

## Design und Grenze

Die bestehende Kartenwerkstatt bleibt der Einstieg für alle bisherigen Nutzerrollen. Zwölf ausgewählte historische KMA-Sets und acht Poly-Haven-Materialien ergänzen den bestehenden Kenney-Katalog. Nur nachweislich CC0; keine generierten Bilder, keine neue Laufzeitabhängigkeit, keine Konten-/Datenbank-/Playtable-Änderungen. Rein deterministische Bildaufbereitung (Transparenzrand zuschneiden, maximal 384 Pixel für Stempel, 256 Pixel für kachelbare Texturen), Originalarchiv- und Originaldatei-Hash erhalten. Leere PNGs und inhaltsgleiche Wiederholungen werden protokolliert und nicht als neue Motive gezählt.

## Verträge

- `assets/packs.json`: freigegebene lokale Paketverzeichnisse. Pro Paket `manifest.json`: Autor, Quelle, Download-URL, Lizenz, Herkunftsbeleg ohne KI, Retrievaldatum, Archivhash, Einträge mit stabiler ID, deutschem Label, Kategorie, Suchtext, lokaler Datei, Originalpfad und beiden Dateihashes.
- Bisherige `kenney:`/`builtin:`-IDs bleiben unverändert. Neue Stempel `kma:<set>_<Originalpfad-SHA256-Präfix>`; Import lässt diesen Namespace nur mit tatsächlich bekanntem Katalogeintrag zu. Dateinamen und Verzeichnisse werden restriktiv validiert.
- Alle Metadaten werden geladen; neue Stempelbilder erst bei sichtbarer Palette oder tatsächlicher Kartennutzung. Höchstens 64 Palette-Einträge je Seite. Suchfeld, Paketfilter und Kategorienfilter werden kombiniert; Trefferzahl und leere Ergebnisse sichtbar. Auswahl, Größe, Drehen, Spiegeln und Streuen bleiben bestehen.
- Renderer lädt benötigte Bilder und invalidiert danach die Komposition. Import/Entwurfswiederherstellung und Export warten auf verwendete Stempel. Fehler müssen sichtbar sein; ein Export darf keine still fehlenden Bilder enthalten.
- Acht vorab geladene Fototexturen werden über den bestehenden Materialpinsel samt Weichheit/Deckkraft/Undo genutzt. Rasterdateiformat bleibt unverändert.
- `credits.html` ist aus Editor-Kopfzeile, Stempelbereich und Hilfe erreichbar, verlinkt Künstler, Sets, Lizenzen und lokale Lizenzbelege. Auch CC0-Künstler werden freiwillig genannt. Hinweis: Assets sind kostenlos/public domain; keine Partnerschaft behauptet. Bestehende Schriften und prozedurale Projektinhalte werden aufgeführt.
- Ein fester Importer mit Hash-Lock kann die Integration reproduzieren; keine unsichere automatische Laufzeitübernahme beliebiger Webinhalte. Inventar-CSV enthält jede enthaltene Datei und jedes ausgeschlossene/leere/duplizierte Motiv wird im Importprotokoll gezählt.

## Abnahme und Verifikation

1. Vollständiges Vorher-/Nachher-Inventar und Quellenentscheidungen vorhanden; jeder neue Asset-Hash, Autor und Lizenzbeleg nachvollziehbar.
2. Neue Stempel über Hauptnavigation → Kartenwerkstatt → Stempel auffindbar; Suche/Paket/Kategorie/Seitenwechsel geprüft; mindestens ein Motiv je neuem Set platziert.
3. Neue Texturpinsel malen sichtbare, rückgängig machbare Pixel. PNG-/Projekt-/ZIP-Rundlauf mit neuen Motiven; alte Kenney-Karten bleiben importierbar.
4. Keine vollständige Bildladung beim Start; Fehlerfall eines Zusatzpakets oder Bildes führt zu sichtbarem Hinweis und funktionsfähigem Basiseditor. CSP, Desktop und schmale Ansicht geprüft.
5. Credits aus der normalen UI erreichbar; alle eingebauten Künstler und Lizenzlinks vorhanden.
6. Fokussierte statische und Browser-Prüfungen vor Release; danach öffentlicher HTTPS- und Browser-Nachweis derselben Wege.

## Risiken und Rollout

**Mittel, durch Entwurf behandelt:** Speicherdruck → Metadaten plus Bilder nach Bedarf; fehlende Bilder → Vorladen beim Import/Export und sichtbarer Fehler; fremde Arbeit → ausschließlich Kartenwerkstatt-Overlay auf dem festgestellten Live-Image. **Niedrig, akzeptiert:** unterschiedliche historische Stile und kleinere Originalstempel; keine generative Hochskalierung. Historische Kartendarstellungen sind Gestaltungsressourcen, keine aktuellen Ortsdaten.

**Deploy-Handoff:** Quellen und lokale Lizenzdateien fixieren, Assets deterministisch aufbereiten, Katalog/UI/Materialien/Credits implementieren, gezielt prüfen, ausschließlich eigene Dateien committen und pushen. Vorheriges Image als Rollback-Tag erhalten. Neues Image mit Source-Commit-Label auf dem tatsächlich laufenden Basisimage bauen; bestehenden Compose-Override auf dieses Image setzen, nur App-Service erneuern. Kein Datenbankschema, keine Nutzerdatenänderung. Monitor protokolliert Source-Commit, Image-ID, Navigation, Rollen, Checks, Live-Nachweise und Rollback.
