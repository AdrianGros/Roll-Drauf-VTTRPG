# Kartenwerkstatt: Deploy und Monitor, 2026-11-08

**Status:** Implementierung und gezielte Verifikation abgeschlossen; Live-Auslieferung und Monitor werden vor Abschluss dieses Slices ergänzt. **Input:** Discover, Apply und ausdrücklicher Auftrag zur direkten Integration. **Artefakte:** Anwendung, Quellen-Lock, Importer, Inventar-CSV und dieser Bericht (dauerhaft); Originalarchive und HTTP-Quellen unter `/tmp/mapmaker-assets-20261108` (Arbeitscache); Bildbelege und Testlog unter `docs/proofs/mapmaker-assets-2026-11-08` (Review-Nachweis).

## Implementierung

- 6.418 neue CC0-Stempel in zwölf historischen KMA-Paketen; 38 bestehende Kenney-Stempel unverändert. Dazu sechs Canvas-Projektsymbole, von denen bei intaktem Kenney-Paket zwei in der Palette sichtbar sind.
- Acht neue CC0-Fotomaterialien: Gras/Fels, steiniger Boden, Felswand, Erde, Küstensand, Waldboden, trockener Stein und Schnee. Insgesamt 22 Pinselmaterialien einschließlich 14 bisheriger prozeduraler Materialien; zwei bisherige Pergamente bleiben erhalten.
- Sieben Kategorien für neue Motive; bisherige Kenney-Kategorien bleiben vorhanden. Suche, Paketfilter, Kategorienfilter und Seiten mit maximal 64 Treffern. Bilder erst beim Anzeigen/Verwenden; Fotomaterialien vorab geladen. Auf schmalen Bildschirmen scrollt die Materialauswahl, damit Größenregler erreichbar bleiben.
- Stabile `kma:`-Kennungen, explizit gegen den geladenen Katalog validiert. Import, Entwurfswiederherstellung und Export warten auf tatsächlich verwendete Bilder. Fehlende Bilder verhindern einen unvollständigen Export sichtbar. Dokumentänderungen während des asynchronen Exports werden erkannt.
- Credits aus Kopfzeile, Stempelbereich und Hilfe erreichbar; Künstler, historische Herkunft, konkrete Poly-Haven-Texturen, Quellen und lokale Lizenzbelege. Keine generativen Bilder oder KI-Hochskalierung; ausschließlich klassische Bildverarbeitung.
- `tools/import_mapmaker_assets.py`: nur fixierte Quellen und Hashes; kein Laufzeit-Scraping. Original- und Ergebnis-Hashes sowie Lizenzbelege je Paket. Nachher-CSV enthält 6.466 Bilddatei-Einträge: 6.456 Stempel + zehn Texturen; Code-Symbole und prozedurale Materialien separat im Vorher-Bericht.
- Dateigrenze: `vtt/static/mapmaker/`, zwei Kartenwerkstatt-Testdateien, Importer, genau benannte Research-Dokumente und eigener Proof-Ordner. Fremde Dirty-/Staged-Dateien werden nicht mit committed.

## Gezielte Verifikation

```text
VTT_PROOF_DIR=docs/proofs/mapmaker-assets-2026-11-08 \
/tmp/roll-drauf-mapmaker/test-venv/bin/python -m pytest -q \
  tests/test_mapmaker_static.py tests/test_mapmaker_browser.py --tb=short
49 passed, 8 warnings in 393.46s
```

Die acht Warnungen stammen aus vorhandenen ReportLab-/SQLAlchemy-Modellen, nicht aus der Asset-Erweiterung. Kein Test übersprungen. Datei-/Lizenz-/Hash-Vollständigkeit, Quellen-Namespace, Startup ohne vollständige Bildladung, Suchfilter/Seitenwechsel, jede neue Set-Familie mit Pixelnachweis, Projektimport nach Reload, PNG-/ZIP-Export, Ortssymbole, alle Fotomaterialien/Undo, fehlende Zusatzpakete/Bilder, CSP, Desktop, Mobilansicht und Credits geprüft. Vorhandene Tests decken unter anderem Pinsel, Stiftdruck, Touch-Abbruch, Ebenen, Pfade, Autosave, Importschranken, Exportgrenzen und Flask-Auslieferung ab.

`git diff --check` und Python-Kompilierung des Importers und der Testdateien ebenfalls erfolgreich. Repräsentative Originalmotive aus allen zwölf Sets im Kontaktbogen geprüft; keine Behauptung einer manuellen Einzelprüfung aller 6.418 Bilder.

## Rollout-Grenze

Während der Umsetzung wurde ein anderer autorisierter Release ausgeliefert. Neu festgestellte Basis: `roll-drauf-vtt-app:entry-beyond20-20261108`, Image `sha256:e6477ac8ef803c4681e7db724be9a207043d81a2cac0675f1c092125587a5269`. Dessen Kartenwerkstatt ist per vollständigem Verzeichnisvergleich identisch zur Discover-Basis. Die neue Auslieferung wird genau darauf aufgebaut und ersetzt ausschließlich `vtt/static/mapmaker`; Entry-/Beyond20-/Species-/Umfrage- und weitere Live-Änderungen bleiben erhalten. Aktive Compose-Dateien jetzt ausschließlich `production.compose.json` und `production.duck-species.override.yml` im Projekt `migration-production`.

## Nutzerweg und Rollen

VTT-Hauptnavigation → **Karten** → **Stempel** → Paket/Kategorie/Suche → Karte; für neue Malmaterialien **Pinsel → Material**. Mobil zusätzlich den bestehenden Reiter **Werkzeug** öffnen. Credits über **Künstler & Credits** im Kopf, **Künstler, Quellen & Lizenzen** unter den Stempeln oder Hilfe. Zielrollen: DM und Spieler; der bestehende öffentliche statische Editor bleibt auch für Gäste erreichbar. Keine Erweiterung von Playtable-Berechtigungen, keine Datenbankmigration, keine Änderung von Konten oder Kampagnen.

## Abnahme vor Live

- [x] Vollständiges Vorher- und Nachher-Inventar.
- [x] Lizenz, Herkunft und Hash jeder neuen Bilddatei vorhanden.
- [x] Alle zwölf Stempelsets und acht Texturpinsel funktional geprüft.
- [x] Bestehende Karten/Mechaniken und Fehlerpfade gezielt geprüft.
- [x] Credits über normale UI erreichbar und auf schmalem Bildschirm geprüft.
- [ ] Source-Commit und erfolgreicher Push festgehalten.
- [ ] Neues Image und Rollback-Referenz festgehalten.
- [ ] Öffentliche HTTPS- und DM-/Spieler-Browserprüfung abgeschlossen.

## Restrisiken

**Niedrig:** historische Set-Stile unterscheiden sich; kleine Originalgrafiken werden nicht künstlich hochskaliert. Herkunft ist anhand Künstlerangaben und historischer Vorlagen geprüft, nicht mit einer vermeintlich sicheren KI-Erkennung. 21 weitere recherchierte KMA-Sets sowie zusätzliche Anbieter sind Kandidaten für einen weiteren abgegrenzten Content-Slice; sie werden nicht als eingebaut dargestellt. Bei unklarer kommerzieller Rohasset-Freigabe wurde nichts übernommen.
