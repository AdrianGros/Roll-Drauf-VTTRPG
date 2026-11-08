# Apply: vier Batches farbiger Künstlergrafiken

Status: Implementierungsauftrag des Owners „Take it all … in 4 batches … wirklich alle … platzieren“ vom 08.11.2026. Profil standard; Grundlage: MAPMAKER_COLOR_BUILDINGS_DISCOVER_2026-11-08.md. Discover-Nachprüfung: die konkreten 17 freigegebenen Pakete sind erreichbar, auch die vier Kenney-Pakete über dessen eigene OpenGameArt-Veröffentlichungen. Keine Übernahme der im Discover ausgeschlossenen KI-, SA- oder eingeschränkt weiterverteilbaren Pakete. Ein unbeschränktes Spiegeln des gesamten Marktplatzes ist kein Teil dieses Auftrags.

## Ergänzende Discover-Fakten

- Die laufende Produktion ist `roll-drauf-vtt-app:mapmaker-assets-20261108-a3db81ed`, Image `sha256:85338a2498ce88cd1575cab86d19c53a2cffbd438d43e2fe27ea0190511bd127`. Compose-Projekt migration-production, bestehende production.compose.json und production.duck-species.override.yml unter /srv/migration/2026-10-07/setup. Vor Release erneut prüfen.
- Bestehend: 6.456 PNG-Stempel, sechs integrierte Symbole, zehn Texturen; 14 Quellpakete, 22 Pinselmaterialien. Das Inventar liegt unter static/mapmaker/assets/inventory.csv.
- LPC-Gesamtarchiv: SHA256 132bbf6191e281d3eedc4e0259b2e8ca403a3067ea377269b837aa4aad4a20f4, 307.567.038 Bytes. 64.311 PNG-Pfade, davon eine leere upstream-Datei. 63.972 gültige Figuren-/Kleidungsblätter, 188 Objekte, 98 Strukturen, 29 Terrain, fünf FX, zwölf Farbpaletten, fünf Testszenen und ein README-Vorschaubild. 35 Credits-Dateien; alle erfassten Lizenzzeilen OGA-BY 3.0. Root-Credits bezeugen handgezeichnete Künstlerarbeit. Figurenblätter typischerweise 64-Pixel-Zellen; Landschaft meist 32 Pixel. Vollständige Häuser bleiben als solche auswählbar.
- Kenney liefert teilweise einzelne PNGs, Roguelike aber ein Bildblatt. 2DPIXX liefert acht Pakete, teils nur SVG. Archive erlauben CC BY 4.0; die OGA-Seiten nennen zusätzlich 3.0. Gewählte Route: konkrete Archivlizenz 4.0. Rubberduck liefert 708 einzelne PNGs mit Größen-/Winter-/Schattenvarianten.
- Aktuelle Laufzeit verwirft weitere Namensräume, begrenzt Manifeste still auf 10.000 Einträge und Katalog auf 32 Pakete. Ortsauswahllisten bauen alle Optionen doppelt. Das ist für diese Menge ungeeignet.

## Ziel und vier Batches

1. **CC0-Grundbestand:** Kenney Roguelike/RPG, Tiny Town, Medieval RTS, Isometric Buildings, Green Village. Zusätzlich gemeinsame Unterstützung für Bildblattausschnitte, skalierende Palette und vollständiges Quelleninventar.
2. **LPC Revised:** sämtliche gültigen PNGs einschließlich Figurenvarianten, Gebäude, Gelände, Objekte, FX und getrennt benannter Referenzen. Leere Originaldatei wird mit genauem Pfad als upstream-defekt dokumentiert. Sämtliche Credits mitliefern.
3. **Dorf und Umgebungen:** alle acht 2DPIXX-RPG-Pakete und rubberduck Medieval Props, einschließlich vorhandener Varianten. SVGs deterministisch rasterisieren; keine generative Bearbeitung.
4. **Burgen und Abnahme:** LPC castle und Castle Tiles for RPG's. Gesamtprüfung aller Pakete, Rückimport, PNG/ZIP-Credits, Mobilansicht und Live-Navigation.

Je Batch eigener nachvollziehbarer Import-/Commitstand; Veröffentlichung auf derselben bestehenden VTT. Gemeinsame Infrastruktur zuerst, danach nur Daten ergänzen. Kein Eingriff in Auth, Playtable, Datenbank oder andere laufende Features.

## Verträge und Bedienung

- Neue IDs: `color:<paket>_<stabiler Pfadhash>`, lokale Dateinamen aus Inhalts-Hash. Identische PNG-Bytes innerhalb eines Pakets dürfen eine Datei teilen; jeder Originalpfad behält einen nachweisbaren Katalogeintrag. Kein stiller Mengen-Cutoff. Pixel werden erst bei Benutzung geladen.
- Pro Quellpaket: Originaldownload-URL und SHA256, Künstler, Lizenz, Provenienz, unveränderte Lizenz-/Credits-Nachweise, Manifest und Coverage-Liste. Jede Datei wird als platzierbar, technische Quelle/Alternativformat oder ausdrücklich begründet ausgeschlossen inventarisiert. Vorschauen/Szenen/Paletten werden getrennt als Referenzen angeboten, nicht mit fertigen Gebäuden verwechselt. Quellarchive werden nicht ausgeführt.
- Bildblätter bekommen eine lokale, tastatur- und touchbedienbare Ausschnittauswahl. X/Y/Breite/Höhe in Originalpixeln, Rasterhilfe, sichtbare Auswahl und Bildansichten Einpassen/Originalgröße/2×/4×; ganzes Bild ebenfalls platzierbar. Frei wählbare Rechtecke erlauben sowohl einzelne 16/32/64-Pixel-Tiles/Frames als auch zusammenhängende größere Gebäude. PNG-Einzelobjekte benötigen keinen Zusatzschritt. Auswahl darf wieder geöffnet werden.
- Optionales Dokumentfeld `crop: {x,y,w,h}` bei Stempeln; ausschließlich ganzzahlige positive, innerhalb der bekannten Originalmaße liegende Ausschnitte. Fehlt das Feld, gilt bisheriges Vollbildverhalten. Speicherung, Entwurf, Undo/Redo, Auswahlgeometrie, Vorschau, Spiegelung, Drehung und Export verwenden dieselbe Geometrie. Ungültiger Import bleibt atomar abgewiesen. Dokumentformatversion bleibt 1 als additive Erweiterung; alte Editoren können Ausschnitte nicht korrekt darstellen, Hinweis im Liefernachweis.
- Für große Pakete wird aus dem vollständigen Herkunftsmanifest zusätzlich ein kompaktes `palette.json` erzeugt. Vertrag: schemaVersion 2, rows mit genau zehn Feldern in fester Reihenfolge (id, file, label, w, h, group, sheet, grid, pixelArt, defaultSize); dazu paketbezogene Export-Credits. packs.json verweist nur auf den geprüften relativen Pfad `<paket>/palette.json`. Das kanonische Manifest mit allen Hashes/Originalpfaden bleibt separat abrufbar. Die kompakte Projektion vermeidet die dreifache Übertragung langer LPC-Pfade; keine Einträge dürfen dabei entfallen.
- Seitengröße 64 bleibt. Suche/Kategorie/Quelle greifen auf alle Metadaten zu; normalisierte Suche einmal je Eintrag vorbereiten. Orts-Symbollisten zeigen die aktuelle Palette plus ausgewählte/bereits verwendete Symbole; keine zehntausenden nativen DOM-Optionen. Bilder pixeliger Pakete werden ohne Glättung gezeichnet, gerenderte Vektoren/3D nach Paketkennzeichnung.
- Globale Credits werden aus allen registrierten Manifesten erzeugt, vorhandene Pakete beim erneuten Import erhalten. Keine globale Behauptung „alles CC0“ nach Aufnahme von BY-Inhalten.
- PNG erhält eingebettete iTXt-Credits der verwendeten Quellpakete mit Künstlern, Quelle, Lizenz-URL und Bearbeitungshinweis (Ausschnitt/Skalierung/Komposition). ZIP enthält zusätzlich lesbare CREDITS.txt. Exportdialog erklärt das Weitergeben der Credits; lokale Credits sind im Editor erreichbar. Original-URLs nur als Credits, keine extern nachgeladenen Laufzeitbilder.

## Risiken und Auflösung

- Mittel, Attribution: aufgelöst durch lokale Originalnachweise, paketbezogene Export-Credits und lesbare ZIP-Beilage. LPC erhält alle 35 Credits-Dateien, damit Original-Zuordnungen erhalten bleiben.
- Mittel, Bildblattbenutzbarkeit: aufgelöst durch generische Rechteckauswahl statt nur eines Gesamtblatt-Stempels. Keine Behauptung eines automatischen RPG-Tilemap-/Autotile-Systems.
- Mittel, Umfang: 64k Metadateneinträge benötigen Pagination, verzögertes Bildladen, Inhalts-Deduplizierung und begrenzte DOM-Listen. Kein Decodieren aller LPC-Bilder bei Anwendungsstart. Mechanische Vollprüfung vor Veröffentlichung, UI-Abnahme repräsentativer Grenzfälle.
- Mittel, fremde Änderungen: ausschließlich freigegebene statische Karteneditor-Dateien aus Quellcommit über aktuellem Produktionsimage bauen. Explizite Pfad-Commits, bestehendes gestagtes Fremdwerk nicht aufnehmen. Recoverable Image/Override sichern.
- Niedrig, defekte Originaldatei: keine Bilddaten rekonstruieren oder als Erfolg zählen; genaue Ausnahme öffentlich in Coverage. Das leere Original ist kein platzierbares Bild.

## Akzeptanz und Deploy-Handoff

- Alle 17 konkret freigegebenen neuen Pakete plus 14 Bestandspakete im Katalog; pro Originalgrafik nachvollziehbarer Editor-Zugang. Mengen und Ausnahmen prüfbar, keine stillen Filter/Dateiverluste.
- Alle akzeptierten PNGs gültig decodierbar; IDs/Dateihashes/Lizenzbelege konsistent; alle Bildblattbereiche innerhalb der Quelle auswählbar und platzierbar.
- Browserbelege für vollständiges Haus, einzelnes RPG-Tile, LPC-Figur, LPC-Hausteil, SVG-Dorfausschnitt und Burgteil; speichern/laden/Undo/PNG/ZIP respektieren Ausschnitt und Credits. Alte Stempel/Materialien bleiben nutzbar.
- Fokusprüfungen vor Release, danach bestehende Mapmaker-Suite soweit ausführbar. Konkrete Live-UI-Journeys für DM/Player über Dashboard → Karten, Desktop und Mobile; keine neue geheime URL.
- Lieferung dokumentiert Commit, Produktionsimage, Navigation/Rollen, Prüfungen, verbleibende Risiken und Rollback. Vier Batches dürfen gemeinsame Infrastruktur verwenden; fehlende Quellen/Prüfungen explizit offen, niemals als abgeschlossen ausgeben.

Deploy darf innerhalb dieser vom Owner autorisierten Content-Erweiterung fortfahren. Keine neue kostenpflichtige Quelle oder Laufzeitabhängigkeit vorgesehen; vorhandenes Pillow und Chromium dienen ausschließlich der technischen Aufbereitung und Prüfung.
