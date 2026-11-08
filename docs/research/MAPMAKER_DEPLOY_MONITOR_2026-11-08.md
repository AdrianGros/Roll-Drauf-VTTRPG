# Kartenwerkstatt: Deploy und Monitor, 2026-11-08

**Status:** Deploy und Monitor abgeschlossen; live erreichbar, geprüft, committed und auf GitHub gepusht. **Input:** Discover, Apply und ausdrücklicher Auftrag zur direkten Integration. **Artefakte:** Anwendung, Quellen-Lock, Importer, Inventar-CSV und dieser Bericht (dauerhaft); Originalarchive und HTTP-Quellen unter `/tmp/mapmaker-assets-20261108` (Arbeitscache); Bildbelege und Testlog unter `docs/proofs/mapmaker-assets-2026-11-08` (Review-Nachweis).

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
- [x] Source-Commit und erfolgreicher Push festgehalten.
- [x] Neues Image und Rollback-Referenz festgehalten.
- [x] Öffentliche HTTPS- und DM-/Spieler-Browserprüfung abgeschlossen.

## Restrisiken

**Niedrig:** historische Set-Stile unterscheiden sich; kleine Originalgrafiken werden nicht künstlich hochskaliert. Herkunft ist anhand Künstlerangaben und historischer Vorlagen geprüft, nicht mit einer vermeintlich sicheren KI-Erkennung. 21 weitere recherchierte KMA-Sets sowie zusätzliche Anbieter sind Kandidaten für einen weiteren abgegrenzten Content-Slice; sie werden nicht als eingebaut dargestellt. Bei unklarer kommerzieller Rohasset-Freigabe wurde nichts übernommen.

## Live-Auslieferung und Monitor

- **Source-Commit:** `a3db81ed04c1fecc8294a4bedf1a833aeecbd689` (`Expand Kartenwerkstatt with credited CC0 artist assets`). GitHub-Branch: [`feat/mapmaker-content-20261108`](https://github.com/AdrianGros/Roll-Drauf-VTTRPG/tree/feat/mapmaker-content-20261108). Der erste Push mit der Root-SSH-Identität wurde abgewiesen; mit der vorhandenen Admin-Repository-Identität war der Push erfolgreich. Keine Push-Lücke verbleibt.
- **Auslieferung:** 2026-11-08, 10:34:28 +0100. Image-Tag `roll-drauf-vtt-app:mapmaker-assets-20261108-a3db81ed`; laufende Image-ID `sha256:85338a2498ce88cd1575cab86d19c53a2cffbd438d43e2fe27ea0190511bd127`. OCI-Label `org.opencontainers.image.revision` entspricht dem Source-Commit.
- **Scope-Beweis:** Docker-Build aus `git archive` des Source-Commits; nur `vtt/static/mapmaker/` kopiert. Alle Basisschichten und die gesamte Image-Startkonfiguration sind identisch zum Entry-/Beyond20-Basisimage, genau eine Dateischicht kommt hinzu. Fremde lokale Änderungen einschließlich der bereits gestagten Migration bleiben außerhalb des Commits und Images.
- **Compose:** Projekt `migration-production`, dauerhafter Image-Eintrag in `/srv/migration/2026-10-07/setup/production.duck-species.override.yml`; nur App-Service mit `--no-deps --no-build` erneuert. Öffentlicher Healthcheck anschließend 200.
- **Rückfall:** erhaltenes Image `roll-drauf-vtt-app:before-mapmaker-assets-20261108` = `sha256:e6477ac8ef803c4681e7db724be9a207043d81a2cac0675f1c092125587a5269`; vorheriger Override unter `/srv/migration/2026-10-07/setup/mapmaker-assets-20261108/production.duck-species.override.before.yml`. Ausführbares, gegen spätere Image-Wechsel geschütztes Rollback-Skript daneben: `rollback.sh`. Keine Migration rückgängig zu machen.
- **Live-Navigation:** Dashboard → VTT-Hauptnavigation → Karten → Stempel/Pinsel; Credits anschließend aus der normalen UI. Mit kurzlebigen serverseitig signierten Prüfsitzungen bestehender DM- und Player-Konten geprüft. Keine neuen Konten oder Kampagnen angelegt; kein Discord-OAuth-Durchgang behauptet. Die Prüf-Token wurden nach Abschluss gelöscht.
- **DM, 1440 px:** neuer Stempel ausgewählt und gesetzt, Fotopinsel mit sichtbaren Pixeln und exaktem Undo, Projekt gespeichert und erneut importiert, PNG exportiert, Credits geöffnet und bis unten gescrollt. Editor nach Navigation in 5.539 ms bereit; 41 zusätzliche Stempelbilder vorgeladen, nicht die gesamte Bibliothek.
- **Player, 390 px:** derselbe Weg einschließlich bestehendem Werkzeug-Reiter erfolgreich; keine horizontale Überbreite. Editor in 5.192 ms bereit; null zusätzliche Stempelbilder beim Start geladen.
- **Auslieferungsintegrität:** 34 öffentliche HTTPS-Prüfungen mit Status 200 und SHA-256-Gleichheit zur committed Version: Einstieg, Laufzeitmodule, Credits, CSV, Katalog, jedes der 14 Paketmanifeste und je ein Bild aus jedem Paket. Alle übrigen Bilddateien wurden bereits vollständig gegen ihre Manifest-Hashes geprüft und aus dem Commit ins Image übernommen.
- **Browserbefund:** beide Rollen ohne `pageerror` und ohne CSP-Verstoß. Nach Hinzufügen von Lizenzbeleg-Hashes nochmals alle acht statischen Tests erfolgreich; Laufzeitcode seit dem vollständigen 49-Test-Lauf unverändert.
- **Nachweise:** `docs/proofs/mapmaker-assets-2026-11-08/live-verification.json`, `release-state.json`, `tests.txt`, `final-static-tests.txt` und die Desktop-/Mobil-Screenshots; keine Tokens oder persönlichen Kontodaten in den Belegen.

**Beobachtetes Ergebnis:** Die neue Bibliothek ist über den etablierten Karten-Einstieg verfügbar und kann live benutzt werden. Kein offener technischer Lieferblocker. **Empfohlener nächster begrenzter Schritt:** gestalterische Rückmeldung von Matt zu bevorzugten Sets/Kategorien auf der Live-Werkstatt sammeln; weitere recherchierte Sets anhand dieses Feedbacks auswählen. Nicht eingebundene Kandidaten sind ausdrücklich keine unbemerkte lokale Funktion.
