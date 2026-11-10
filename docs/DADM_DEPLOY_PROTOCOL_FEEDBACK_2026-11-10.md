# Deploy: Protokollfeedback – Creator, Bogen, Kampagnen und Karten

Status: implementiert und veröffentlicht; abschließende Abnahme im Monitor-Bericht.
Dauerhaft aufbewahren.
Vertrag: `DADM_APPLY_PROTOCOL_FEEDBACK_2026-11-10.md`; vollständige Zuordnung aller
40 Karten: `PROTOCOL_FEEDBACK_SPECIFICATIONS_2026-11-10.md`.

## Umsetzung und Grenzen

- Creator: Würfel-Multimengen, Stufenmerkmale, klare Zauberauswahl und sticky
  Filter. Rüstung/Schild aus Startpaketen, serverseitige Finalisierungsprüfung.
  Die vorher pauschalen A/B-Menüs nutzen jetzt tatsächliche Paket-IDs; etwa beim
  Kämpfer ist C das reine Goldpaket, B enthält ebenfalls Ausrüstung.
- SRD-Bogen: fünf tastaturbedienbare Bereiche, kompaktere Spielwerte, Bilder,
  Münzen und angelegte Ausrüstung im Kopf. Grad-/Suchfilter für vorhandene Zauber.
  Nacht/Pergament und Bewegung m/ft als robuste lokale Anzeigepräferenzen.
  Bestehende Inventar-, Stufen-, Verwaltungs-, Export- und Upload-Roots erhalten.
- Kampagnenliste: Suche nach Name/Beschreibung und fünf Einträge pro Seite;
  bestehende Einladungs- und Hub-Aktionen bleiben an ihren DOM-Knoten.
  Kontobutton Abmelden lesbar formatiert.
- Karten: Rechtsziehen verschiebt ohne Dokumentänderung und ohne Werkzeugwechsel;
  sichtbarer Einstieg zur aktiven Ebene; Ortsliste fokussiert die Bearbeitung.

Keine Datenbankschemamigration und keine neue App-Abhängigkeit. Keine Änderung
an Tischkontexten/-rechten, keine vollständige Hotbar-/Sprach-/Atlaslieferung.
Nacht und Einheitenwahl gelten für den beschriebenen Bogenumfang, nicht global.

## Dateien und Quellenabgrenzung

Funktionale Änderungen liegen unter `vtt/characters`, `vtt/rules_content`,
`vtt/static/{css,js,mapmaker}` und `vtt/templates/character-sheet.html`.
Neue Module: `sheet-feedback.js` und `sheet-feedback.css`.
Gezielte Akzeptanztests: `test_protocol_feedback*.py`,
`test_campaign_list_feedback.py` und Ergänzungen bestehender Browserreisen.

Ausgangs-Worktree war nicht sauber und repräsentierte die Produktion nicht. Die
isolierte Branch `feat/protocol-feedback-20261110` rekonstruiert deshalb zuerst
die bereits produktiven Dateien in `5bb9ae9bd`; der ursprüngliche Arbeitsbaum
bleibt unberührt. Das Release baut auf dem tatsächlich laufenden Ausgangsimage
auf und kopiert ausschließlich neue Funktionsänderungen seit `5e24565fb` hinein.
Das schützt neuere Beyond20-, Tischplatz-, Fullscreen-, Buch- und Bibliotheksarbeit.

## Prüfungen vor Veröffentlichung

Prüfimage `roll-drauf-vtt-feedback-tests:20261110`: passende Playwright-Browser und
OS-Abhängigkeiten getrennt von der App; isolierte SQLite-Daten und kein externes
Netz. Produktionsimage enthält diese zusätzlich installierte Testlaufzeit nicht.

1. Creator-/Sheet-/Inventar-/Progression-/Manage-APIs und Browser, Mapmaker-Static,
   private Projektbibliothek und gesamter Karten-Browserkatalog: **159 bestanden**
   in 1053,11 s. Enthält Touch/Cancel, Autosave, Undo, Import/Export, Asset-/Crop-
   Rundläufe und bestehende neuere Funktionen.
2. Gezielte neue Creator-/Finalisierungs-/Pan-Prüfungen inklusive Weiterzeichnen
   nach Rechtsziehen: **5 bestanden**, 47 bewusst nicht ausgewählt, 32,65 s.
3. Neue Bogenreisen Chromium 1440/390/320 und Firefox 1440/390:
   **5 bestanden**, 88,59 s. Prüft Tastatur, Gradfilter, Münzupdate, Uploadzugang,
   Einheiten-/Theme-Reload, keine JS-Fehler und Kontrast der Nacht-Kernelemente.
4. Ergänzte Navigation/Layout/Bogenprüfung: **28 bestanden**, 389,87 s.
   Kampagnenliste mit 50 Einträgen separat: **2 bestanden**, 55,12 s.
   Zwei alte Tests verwendeten den vor der aktuellen Produktion gültigen
   `open-session`-Ownerselektor. Die Tests wählen nun ausdrücklich
   `open-session-dm` und erwarten `seat=dm`; App-Rollenlogik wird nicht verändert.
   Der Klick auf den Kampagnennamen vermeidet außerdem einen mehrdeutigen
   Kartenmittelpunkt, der je Browser einen darunterliegenden Unterbutton trifft.
5. `git diff --check`: bestanden. Fehlläufe wegen fehlender Browserbibliotheken,
   falscher alter Paket-/Geschwindigkeitsannahmen und CSS-Kontrastkollisionen
   wurden nachvollzogen und korrigiert; sie sind keine erfolgreichen Nachweise.
6. Sichtprüfung der ersten Live-Abnahme zeigte einen unten abgeschnittenen
   Abmeldebutton im Editor: die bisher feste 64/66-px-Zeile bot für den neuen
   32-px-Button zu wenig Platz. Zusätzlich verringerte der geerbte 12-px-Abstand
   der Buchnavigation den tatsächlich nutzbaren Bereich. Die Editorzeile bekommt
   84 px ohne diesen Abstand. Final: **4 gezielte Kartenfälle bestanden**,
   46 nicht ausgewählt, 46,01 s. Enthält vollständige Button-Geometrie mit
   eingeblendeter Sessionzahl bei 1440/390 px, Pan/Weiterzeichnen und mobile
   Ortsauswahl. Die Gastvorschau allein hatte diesen zusätzlichen Text ausgeblendet;
   die Live-Messung mit angemeldetem Konto deckte den Unterschied auf. Keine erneute
   vollständige Katalogprüfung nötig, da nur die Navigationshöhe geändert wurde.

Insgesamt 195 verschiedene automatisierte Fälle bestanden; fokussierte Wiederholungen
sind darin nicht doppelt gezählt. Die große Regression gehört zum Funktionsstand
`b8f3b54ba`; die anschließenden App-Änderungen in `187dc90a7` und `32cc5bfee`
betreffen ausschließlich Höhe/Abstand der Editor-Navigationszeile und wurden
gezielt erneut geprüft.

## Benutzerwege und Live-Abnahme

| Rolle | Normaler UI-Einstieg | Akzeptanz |
| --- | --- | --- |
| Player, eigener Charakter | Übersicht → Charaktere → Held anlegen → Creator → Zum Charakterbogen | Paketwahl/Herkunft; spielbarer Bogen; Tastaturtabs; Nacht/ft; Münzen; Uploadzugang |
| Berechtigte Kampagnenperson | Hauptnavigation → Kampagnen | Suche, Seiten, weiterhin Hub-/Gruppeneinstieg; 50er-Fall ausschließlich lokal |
| DM, eigene private Karte | Übersicht → Karten → Leere Karte | Zeichnen → rechts verschieben → weiterzeichnen; Ebene hinzufügen; Ort erneut bearbeiten; Bibliothek speichern/öffnen/löschen |

Live nur dedizierte temporäre Player-/DM-Konten und eigene synthetische Inhalte.
Keine fremden Charaktere/Karten verändern. Temporäre Konten/Inhalte anschließend
entfernen; Cookies/Tokens nicht in Repo oder Nachweisdateien aufnehmen.

## Release und Rollback

- Laufendes Ausgangsimage: `roll-drauf-vtt-app:oglan-oc1-20261109-8167236`;
  `sha256:496595790afb006e6907fe6ecef49ea617d65802583e300bbb91aeeb01908cf4`.
- Gesicherter lokaler Rücksprungtag:
  `roll-drauf-vtt-app:feedback-rollback-20261110-496595790afb`.
- Aktives Projekt: `migration-production`; Compose:
  `/srv/migration/2026-10-07/setup/production.compose.json` plus
  `production.duck-species.override.yml`. Nur Dienst `app` neu erstellen;
  Datenbank, Redis und Mail bleiben laufend.
- Sicherung der bisherigen Override-Datei:
  `/srv/migration/2026-11-10/protocol-feedback/previous.override.yml`.
- Vor Umschaltung aktuelle Image-ID erneut vergleichen; bei unerwartetem
  Produktionswechsel nicht überschreiben. Neues Commit/Image, Dateimanifest,
  Push-, Health-, Live- und Bereinigungsnachweise werden im Monitor ergänzt.

Veröffentlichter Funktionsstand: `32cc5bfee66419176d38248f68d5941144dad79f` auf
`feat/protocol-feedback-20261110`, gepusht. Aktives Image:
`roll-drauf-vtt-app:protocol-feedback-20261110-32cc5bfee`,
`sha256:f6bc1008f0bb03962fba266d3f3477e5edf7c81fcfe205586dab6bd2cc0b445a`.
17 Overlaypfade und 225 erwartete Datei-Hashes im fertigen Image geprüft;
App-Factory erfolgreich gestartet. Releasezeit und öffentlicher Healthcheck stehen
im finalen `deployment.json`. Datenbank, Redis und Mail wurden laut
Container-ID/Startzeit-Vergleich bei keiner Veröffentlichung neu gestartet.
Rollback: `/srv/migration/2026-11-10/protocol-feedback/rollback.sh`.
