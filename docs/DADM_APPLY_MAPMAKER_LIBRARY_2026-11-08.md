# Apply: persönliche Kartenbibliothek

## Ziel und Grenze
Autorisierter Funktionsumfang: persönliches Auflisten, Speichern, Öffnen,
Aktualisieren, Kopieren und Löschen vollständig editierbarer Karten. Einstieg
Hauptnavigation → Karten → Startdialog „Deine Karten“; zusätzlich sichtbarer
Bibliotheks- und Speicherzugriff im Editor. Leere Karte und Silbermark-Template
erzeugen unabhängige Projekte. Dateiimport/-export, lokales Autosave, alle
Künstler-Assets und Credits bleiben verwendbar. Keine Kampagnen-/Playtable-
Berechtigungen, neue Tarifregeln, öffentliche Karten oder neue Dependencies.

## Verträge und Entscheidungen
- Neues Modell `MapmakerProject`: UUID, owner_id → users, Titel, Abmessungen,
  Revisionsnummer, Zeitstempel, Storage-Provider, unveränderlicher Storage-Key,
  exakte JSON-Bytegröße. Keine Bilder/Skripte aus beliebigen URLs.
- Eigener Blueprint wird unter dem vorhandenen assets_bp registriert, ohne die
  in anderen Arbeiten geänderten zentralen App-/Model-Registrierungen anzufassen.
  API `/api/assets/mapmaker/projects`: GET paginiert mit Suche und Speicherstand,
  POST erstellt. `/<uuid>`: GET Dokument+Metadaten, PUT mit revision ersetzt,
  DELETE mit revision löscht. JWT und aktive Konten sind immer erforderlich.
  Eigentümerfilter gilt auch für Admins; fremde IDs ergeben 404.
- Liste bootstrapt die serverbestätigte accountId. Folgezugriffe senden
  X-Mapmaker-Account; schreibende Zugriffe verlangen diese Bindung zusätzlich zum
  bestehenden JWT/CSRF. Kontowechsel ergibt 409, keine stillschweigende Zuordnung.
- Server validiert und normalisiert das bestehende v1-Format und dessen Limits,
  bekannte Asset-IDs/Ausschnitte sowie tatsächliche PNG-Dimensionen und -Integrität.
  Maximal 50 MiB kanonisches JSON. Rasterdaten bleiben im Projekt eingebettet.
  Die erste Version zeigt Metadatenkarten statt zusätzlicher Vorschaubilder;
  damit wird exakt das editierbare Projekt auf das Kontingent angerechnet.
- Nutzer-UPDATE sperrt die Kontingentzeile in derselben Transaktion wie die
  Projektänderung. Quota-Prüfung und Delta-Anrechnung erfolgen atomar, kompatibel
  mit vorhandenen Asset-Reservierungen. Revision wird unter Sperre geprüft.
  Staff/Headmaster folgen vorhandener Unlimited-Policy. Fehlende Zuteilung ergibt
  507; Löschen und Verkleinern bleiben möglich, auch nach einer Quota-Senkung.
- Storage schreibt ausschließlich neue servergenerierte Versions-Keys. Bei
  Fehlern werden neue Objekte entfernt und DB/Zähler zurückgerollt. Alte Version
  bleibt bis Commit verfügbar; danach bestmögliche Bereinigung. GET sperrt kurz
  die Nutzerzeile während des Lesens, damit ein paralleles Ersetzen/Löschen keine
  Datei vor dem Download entfernt. Keine beliebigen Keys aus Requests.
- Konflikte liefern 409; Editor bietet „Als Kopie speichern“. Laufende Saves
  binden sich an Dokument und Generation; spätere Änderungen bleiben ungespeichert.
  Ersetzen fragt bei ungesicherten Änderungen nach. Serverstand und lokales
  Autosave werden getrennt bezeichnet. Eigene IndexedDB-Schlüssel je accountId;
  der alte globale Gastentwurf wird keinem angemeldeten Nutzer zugewiesen.
- Additive Migration legt nur die neue Tabelle/Indizes an. Rückrollen des Images
  lässt Projekte und Tabelle erhalten. Release über selektives Overlay auf das
  direkt zuvor abgeglichene Produktionsimage, keine fremden Dirty-Dateien.

## Akzeptanz und Prüfungen
1. Erster Aufruf bietet Bibliothek, leere Karte, Template, auch mobil.
2. Player und DM speichern, öffnen auf anderer Sitzung und bearbeiten Ebenen,
   Raster, Orte und Ausschnitte weiter; keine Kampagne erforderlich.
3. Andere Nutzer/Staff können fremde Projekte weder lesen noch verändern/löschen.
4. Erstellen/Ersetzen/Löschen hält den gemeinsamen Speicherstand korrekt;
   Quota-, Storage- und Versionsfehler erhalten das letzte gespeicherte Projekt.
5. Dateiimporte, Exporte, Credits, Editorwerkzeuge und eigener lokaler Entwurf
   funktionieren weiterhin. Kontowechsel und veraltete Tabs überschreiben nichts.
6. Fokussierte API-/Browserchecks, reale PostgreSQL-Konkurrenzprüfung, Commit,
   Push, Migration, selektiver Release und Liveprüfung über Hauptnavigation.
   Commit, Image, Rollen, Nachweise und Rollback werden protokolliert.

## Risiken und Deploy-Handoff
Die drei Medium-Befunde aus Discover sind durch atomare gemeinsame Zähler,
Kontobindung und abgeglichenes Image-Overlay im Design aufgelöst; Prüfung ist
verbindlich. Low-Rest: Prozessabbruch kann unreferenzierte Dateien hinterlassen;
normale Fehler werden bereinigt, ein späterer gezielter Storage-Audit kann solche
Dateien finden. Keine automatische Löschung fremder Bestandsdateien.
Deploy setzt ausschließlich diese Verträge um. Die Nutzeranweisung autorisiert
Implementierung und etablierte Live-Auslieferung; keine offene Freigabe.
