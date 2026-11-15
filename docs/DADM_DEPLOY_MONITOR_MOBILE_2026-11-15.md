# Deploy / Monitor: Mobile DM, 15.11.2026

- status: complete_in_mobile_engine_boundary
- input_summary: Android/DuckDuckGo für die 15-Uhr-Session, iPhone mitprüfen;
  autorisierte Umsetzung gemäß [Apply](DADM_APPLY_MOBILE_2026-11-15.md).
- artifacts: Spezifikation, Funktionsmatrix, Browser-Test und Nachweise unter
  `proofs/mobile-2026-11-15/`, retention_class=durable. Datenbankbackup privat im
  Releaseverzeichnis; Testpasswörter und synthetische Testdaten sind gelöscht.
- risks_and_assumptions: physische Geräteabnahme offen; siehe unten.
- next_step: echte Android-/iPhone-Geräteabnahme nach M-H01–M-H07; keine zusätzliche
  Featurearbeit im Monitor.

## Implementierung und Auslieferung

Navigation: **https://vtt.roll-drauf.de → Anmeldung → Kampagne → Sitzung als DM öffnen**.
Rollen: DM für Steuerung, Player als unabhängiger Daten-/Bedienungs-Gegencheck.
DM-Komposition bleibt serverautorisiert; kein neuer Rollenflag und keine neue
HTTP-/Socket-Schnittstelle. Die Player-Oberfläche lädt keine DM-Bedienmodule.

| Bereich | Änderung |
|---|---|
| `play-ui.js` | Zwei-Finger-Zoom/-Pan, Pointer-IDs, Gestenabbruch ohne Speicherung, Pan auf Tokenflächen; Touch-Tap öffnet Details mit begrenztem Schutz vor dem Kompatibilitätsklick, Drag lässt die Karte frei |
| `play-dm.js` | Kein versehentlicher Touch-Auswahlrahmen, Abbruch vorhandener Rahmen, Aktualisierung sichtbarer Clipboard-Aktionen |
| `play-token-layers-dm.js` | Sichtbare Mehrfachauswahl, Kopier-/Einfügebuttons, Einfügen im aktiven Layer |
| `play-token-layers-dm.css`, `play-workspace.css`, `play.html` | 44px Auswahlaktionen, lesbare mobile Formulare, begrenzte Karten-Gestenfläche |
| `test_mobile_playtable_browser.py` | Chromium-/WebKit-Touch-Kernabläufe und native Chromium-Multitouch-/Abbruchprüfung |

- Funktionaler Quellstand im Image: `344641a896b284e5330e675ff329937eef258210`.
- Image: `roll-drauf-vtt-app:feedback-mobile-touch-final-20261115-20261111-344641a89`.
- Laufende Image-ID: `sha256:edb580f988ae8d71cbc41f33e6bb921fd08fe17c7f597e048882c9f35694d4dd`.
- Aktiviert am 15.11.2026 gegen **14:50 Uhr Europe/Berlin**.
- Tatsächliches Compose-Projekt: `migration-production`, Dateien
  `/srv/migration/2026-10-07/setup/production.compose.json` und
  `/srv/migration/2026-10-07/setup/production.duck-species.override.yml`.
- Nur App neu erstellt; Datenbank-, Redis- und Mail-Containeridentitäten und
  Startzeiten unverändert. Keine Schemaänderung; Backup-Archiv lesbar, Restore
  nicht ausgeführt.
- Vorheriges Image `sha256:5093f63b8420f079a432702bc311f8868d43f427376408f428929ced99363032`
  bleibt wiederherstellbar. Rollback:
  `/srv/migration/2026-11-11/feedback-mobile-touch-final-20261115/344641a89/rollback.sh`
  (Syntax geprüft, nicht ausgeführt).

## Verifikation und Nachweisgrenze

**40 gezielte Tests bestanden** am ersten mobilen Stand (`acdc3d5ee`, 1043 Warnungen).
Nach der Touch-Nachbesserung **11 relevante Tests erneut bestanden** am finalen
Stand `344641a89` (547 Warnungen), jetzt mit Pixel-7-/iPhone-13-Profil und realer
Kartengröße. Das sind Wiederholungsprüfungen innerhalb derselben 40 Fälle.
Die vollständige Repository-Suite wurde
nicht ausgeführt. Testimage `roll-drauf-vtt-mobile-tests:20261115` enthält nur
zusätzliche Test-Browser-Abhängigkeiten; Produktionsabhängigkeiten unverändert.

```text
python -m pytest tests/test_mobile_playtable_browser.py \
  tests/test_token_layer_permissions.py tests/test_table_contexts.py \
  tests/test_playtable_token_clipboard_browser.py tests/test_token_layers_browser.py \
  tests/test_play_presentation_browser.py -q -x --disable-warnings --tb=short
```

Image-Abgleich: **80.855 Dateien geprüft**, 0 Abweichungen, 0 uncommittete
Anwendungsdateien. 81 bereits absichtlich nicht ausgelieferte G1-Dateien bleiben
abwesend; keine Wiederbelebung abgelöster Implementierungen. Laufendes Image und
Commitlabel stimmen mit dem Build überein. Acht geänderte beziehungsweise zentrale
Anwendungsdateien zusätzlich im laufenden Container gehasht; keine
Anwendungsdatei-Schreibvorgänge und keine Quellcode-Mounts. Statische Ressourcen
werden mit `Cache-Control: no-cache` ausgeliefert, normales Neuladen revalidiert.

## Akzeptanzcheckliste

- [x] Android-/Chromium- und iPhone-/WebKit-Touch: Gruppenauswahl, Clipboard,
  versteckte Token-Erstellung, Layerfreigabe, Chat, Würfel, Journal.
- [x] Native Chromium-Toucheingabe: Drag speichert, Pan auf Tokenfläche mutiert
  nicht, Pinch verändert Kartenzoom statt Seitenzoom, Abbruch/zweiter Finger
  speichert nichts, anschließender Tap zeigt Details; neue Berührung beendet den Klickschutz.
- [x] Hoch-/Querformat: Dock, Initiative mit Kampfstart/Zugwechsel/Kampfende und
  Pan erreichbar; Reload erhält Rolle und gespeicherten Zustand.
- [x] Gezielte Desktop-, Rollen-, HTTP- und Socket-Regressionen bestanden.
- [x] Quellcommit gepusht, committed Image aktiviert, Health und Laufzeitintegrität grün.
- [x] Dieselben Kernabläufe über öffentlichen Login/Kampagnenhub auf Live bestätigt.
- [x] Ausschließlich synthetische Testdaten und sämtliche Testzugangsdaten entfernt.

## Restpunkte und nächste Abnahme

- **Mittel / offen:** echtes Android/DuckDuckGo und echtes iPhone; System-WebView,
  Safari-Version, Bildschirmtastatur, Screenlock/Appwechsel und Netzwechsel sind
  mit Desktop-Engine-Emulation nicht vollständig abgebildet. Benutzerabnahme wird
  gesondert erfasst und nicht aus automatischen Tests abgeleitet.
- **Mittel / offen:** große reale Karten, Handy-Dateiauswahl, vollständige Bogen-/HP-/
  Zustandsabläufe sowie Wand-/Licht-/Fog-Authoring brauchen den Gerätekatalog.
- **Niedrig:** Button-Einfügen verwendet die Mitte der Kartenansicht mit
  Begrenzung auf die Kartengrenzen. Bei einer eingepassten kleinen Karte kann die
  Position randnah sein; Tokens bleiben verschiebbar. Die Auswahlleiste kann
  Teile der Karte überdecken; vor einer dortigen Geste **Auswahl aufheben**.

Konkrete Hardwarefälle und Bedienungsanleitung:
[Funktionsmatrix und Gerätekatalog](MOBILE_COMPATIBILITY_2026-11-15.md).

## Ergebnis der Live-Abnahme

Alle **15 funktionalen Live-Checkgruppen** bestanden: Chromium/Pixel 7 acht,
WebKit/iPhone 13 sieben. Sechs Screenshots und die Rohdaten sind im Proof-Ordner.
Der strikte ursprüngliche Browserlauf bleibt transparent als `status: fail` in
`live.json` erhalten: Nach dem Passwort-Login navigierte das Testskript sofort
vom Dashboard weg; WebKit meldete dabei zehn abgebrochene Dashboard-Fetches als
Access-Control-Fehler. Alle funktionalen Prüfschritte hatten bereits bestanden.
Die gezielte Wiederholung **Login → Dashboard abwarten → Hub → Tisch** für DM und
Player lief anschließend ohne einen Browserfehler durch (`navigation-recheck.json`).
Die Zuordnung der ursprünglichen Meldungen zur Testnavigation ist eine aus
API-Pfaden und dieser Nachprüfung abgeleitete Schlussfolgerung. Das Proof-Skript
wartet nun auf den Dashboard-Abschluss und versucht keine Fehleraufnahme einer
bereits geschlossenen Browserseite. Es wurde danach keine Produktionslogik verändert.

Health und Quellintegrität sind grün; synthetische Kampagne, Nutzer, Spielzustände
und beide privaten Credential-Dateien wurden entfernt. Keine menschliche
Handy-Abnahme aus diesen Automatikprüfungen abgeleitet.

Kleine verbleibende Textpolitur: Der Kopier-Toast nennt noch das Desktopkürzel;
die sichtbaren Kopier-/Einfügebuttons und die Handy-Anleitung sind nutzbar.
