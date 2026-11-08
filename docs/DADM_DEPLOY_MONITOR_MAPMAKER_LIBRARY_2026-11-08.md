# Deploy / Monitor: persönliche Kartenbibliothek

## Ergebnis und Nutzerweg
Live auf https://vtt.roll-drauf.de. Einstieg für aktive Player und DMs:
**Hauptnavigation → Karten → Deine Karten**. Der Startdialog bietet gespeicherte
Karte, leere Karte und Silbermark-Template. Im Editor öffnen das Bibliothekssymbol
oder „Datei → Meine Karten“ die persönliche Bibliothek. Die Diskette,
„Datei → In Bibliothek speichern“ oder Strg+S sichern das vollständig editierbare
Projekt. „Als Kopie in Bibliothek speichern“ erzeugt ein unabhängiges Projekt.
Suchen, paginiertes Auflisten, Versionsstand und bestätigtes Löschen sind vorhanden.

Der angezeigte Speicher ist das vorhandene Kontingent des Kontos, gemeinsam mit
Uploads; übliche Zuteilung Player 5 GiB, DM 20 GiB. Keine Tarife oder Kontingente
wurden geändert. Konten ohne Zuteilung können lokal arbeiten, importieren und
exportieren; serverseitiges Vergrößern/Anlegen benötigt zugewiesenen Speicher.
Lokales Autosave bleibt getrennt vom ausdrücklich gesicherten Bibliotheksstand.
Authentifizierte lokale Entwürfe verwenden eigene Schlüssel pro Konto.

## Umsetzung und Dateigruppen
- `vtt/models/mapmaker_project.py`: private Projektmetadaten und Revision.
- `vtt/mapmaker_document.py`: Normalisierung/Validierung des bestehenden v1-Formats
  mit allen 72.064 Symbolkennungen, PNG-Integrität und Ausschnitten.
- `vtt/endpoints/mapmaker.py`, Registrierung in `vtt/endpoints/assets.py`: JWT/CSRF,
  aktive Konten, Eigentümerfilter auch für Staff, zusätzliche Kontobindung,
  atomare gemeinsame Speicherabrechnung und Revisionskonflikte.
- `tools/migrate_mapmaker_library.py`: additive, wiederholbare Tabellenmigration.
- `vtt/static/mapmaker/index.html`, `mapmaker.css`, `js/library.js`, `app.js`,
  `storage.js`, `tools.js`, `ui.js`: Startdialog, Bibliothek, Save-/Copy-/Delete-
  Bedienung, geschützte asynchrone Saves, Kontobindung der Entwürfe, mobile Leiste.
- Drei neue Testmodule; vorhandener Browserharness startet bestehende Editorfälle
  über die Template-Auswahl. Keine neuen Dependencies oder Künstler-Assets.

## Quelle, Image und Release
Implementierungscommit: `f37e1136d1890fac7407e7311d62f9096a72658d`, gepusht nach
`origin/feat/mapmaker-library-20261108`.

Ausgeliefertes Image: `roll-drauf-vtt-app:mapmaker-library-20261108-f37e1136`,
ID `sha256:1d56fef8b325eba15653a9520b7ad5f7e2187f3302ba4a00d8ba8ed1f15174ad`.
Auslieferung: 2026-11-08 19:12:08 Europe/Berlin.

Während des Builds erschien die neue Fullscreen-Auslieferung. Der erste
Deployversuch brach vor der Migration am Imagevergleich ab. Anschließend wurden
alle berührten Bestandsdateien erneut abgeglichen und das Overlay auf
`roll-drauf-vtt-app:playtable-fullscreen-20261108-72229c7`,
`sha256:2bdcccc4ee829406f63957c0cd32cda02e376b8d9b9cd91df304cdf73f556200`,
neu gebaut und getestet. Alle Basis-Layer und Image-Konfigurationen blieben erhalten.
Nur zwölf protokollierte Quellpfade wurden darübergelegt. Neuere Playtable-Arbeit,
alle Künstler-Dateien und bestehende Produktionskonfiguration sind dadurch erhalten.

Compose-Projekt `migration-production`, Dateien in `/srv/migration/2026-10-07/setup`:
`production.compose.json` und `production.duck-species.override.yml`. Nur der
App-Service wurde mit `up -d --no-deps --no-build app` erneuert. Die neue Tabelle
wurde davor mit dem exakten committed Modell additiv angelegt; bestehende Tabellen
und Kontingentzuteilungen wurden nicht geändert. Daten liegen auf dem bestehenden
Volume `roll-drauf-vtt_vtt_assets_data` unter `/data/vtt-assets`.

Rollback: `/srv/migration/2026-10-07/setup/mapmaker-library-20261108/rollback.sh`.
Das Skript prüft das aktuelle Image und stellt das vorherige Compose-Image wieder
her. Tag `roll-drauf-vtt-app:before-mapmaker-library-20261108` hält die Basis bereit.
Neue Tabelle und gespeicherte Projekte bleiben bei einem Image-Rollback erhalten.

## Prüfungen und Nachweise
122 unterschiedliche Prüffälle wurden abgedeckt; die Läufe und notwendigen
Korrekturprüfungen sind ausdrücklich getrennt dokumentiert:

- Neue API: 30 bestanden, einschließlich privater Zugriffe, CSRF, Kontowechsel,
  vollständigem Dokument, Delta-Abrechnung, Quota-Senkung, Konflikten und
  simulierten Disk-/DB-Fehlern mit Erhalt der letzten Version.
- Neue Browserfälle: acht abgedeckt. Ein gemeinsamer Lauf hatte 37 bestandene
  Fälle und einen zu kurzen Reload-Wait; korrigierter Kontowechsel und Save-
  Snapshot separat grün. Vier abschließende UI-/Restore-Prüfungen grün,
  einschließlich 320/390/1440 px und Strg+S aus dem Titelfeld.
- PostgreSQL in eigener kurzlebiger Testdatenbank: drei bestanden. Acht parallele
  Creates teilen die Restquota korrekt; Karten- und bestehende Asset-Reservierung
  verwenden denselben Lock; sechs konkurrierende Updates lassen nur eine Revision zu.
- Bestehende Kampagnen-Asset-Bibliothek: 24 bestanden.
- Bestehender Mapmaker: kompletter Lauf 55 bestanden, zwei korrigierte Fälle danach
  separat bestanden. Restore wartet auf den tatsächlich geöffneten Dialog; der
  4096px-Import wartet auf seine konkrete Nachricht statt auf eine ältere Toast-
  Meldung. Keine offene Fehlfunktion aus diesen Läufen.
- Auf dem echten neuen Image: Create/Read/Update/Delete und Quota-Rückkehr grün.
- Öffentlich: Health 200; sämtliche zwölf Overlay-Dateien im Container und vier
  öffentliche Einstiegsmodule entsprechen per SHA-256 dem Implementierungscommit.
- Live: DM bei 1440 px und Player bei 390 px jeweils über Dashboard → Karten.
  Template bzw. leere Karte, farbiges Künstlergebäude platzieren, privat speichern,
  in unabhängigem Browser laden, Ebenen und Pixel vergleichen, bearbeiten und als
  Revision 2 speichern. Fremdes Konto erhält 404. Löschen über die UI, Speicher
  exakt zurück auf Ausgangsstand, keine Seitenfehler oder CSP-Verletzungen.
- Live-Katalog hat weiterhin 72.064 platzierbare Symbolkennungen. Die zwei
  synthetischen Testkarten wurden entfernt; keine Benutzerkarten gelöscht,
  keine Konten oder Quotas geändert. Temporäre JWT-Cookie-Datei wurde entfernt.

Nachweise: `docs/proofs/mapmaker-library-2026-11-08/`, insbesondere `checks.json`,
`release-state.json`, `deployed-proof.json`, `image-proof.json`,
`live-journeys.json`, sechs maskierte Live-Screenshots und die Prüfprotokolle.
Bestehende Eventlet-/ORM-Warnungen sind in den Läufen sichtbar.

## Akzeptanz und verbleibende Grenzen
- [x] Startauswahl und persönlicher Einstieg auf Desktop und Mobilgerät.
- [x] Bearbeitbare private Projekte für Player und DM ohne Kampagne.
- [x] Eigentümergrenze, Kontowechsel und parallele Revisionen abgesichert.
- [x] Gemeinsame Quota, Delta bei Ersetzen, Freigabe bei Löschen.
- [x] Bestehende Editorfunktionen, Import/Export, Credits und Artist-Katalog erhalten.
- [x] Commit/Push, additive Migration, produktives Image und Live-Nutzerweg belegt.

Low: Ein Prozessabbruch zwischen Storage und DB kann unreferenzierte Dateien
hinterlassen; normale Fehlerpfade räumen neue Dateien auf. Ein gezielter späterer
Storage-Audit kann solche Objekte bereinigen. Kein automatisches Entfernen fremder
Dateien. Der produktive lokale Provider ist geprüft; S3 wurde in diesem Slice
nicht separat gegen einen echten Bucket getestet. Bibliothekseinträge zeigen
Metadaten; zusätzliche Vorschaubilder sind nicht Bestandteil dieses Slices.
Empfehlung: Slice schließen, weitere Templates bei Bedarf als eigenen Inhaltsschritt.
