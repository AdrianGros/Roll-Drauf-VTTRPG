# Deploy: Beyond20-Würfe sichtbar am Vollbild-Tisch

Datum: 2026-11-08. Phase: **Deploy + Live-Prüfung**. Auftrag des Owners:
„Beyond20-Kompatibilität, das muss wieder laufen.“

## Nutzerreise und Rollen

| Einstieg | Rollen | Erwartung |
| --- | --- | --- |
| Spieltisch, Beyond20 nach `/beyond20.html` eingerichtet | Spieler und DM | Oben in der Tischzeile steht „Beyond20“, sobald die Erweiterung auf der Seite ist |
| Wurf auf D&D Beyond | alle am Tisch | Der Wurf erscheint einige Sekunden oben rechts auf der Karte (Name, Ergebnis, Titel, bei Angriffen Treffer- und Schadensteil) und dauerhaft im Würfel-Log unter Menü → Tools |

## Befund

Geprüft mit der **echten Beyond20-Erweiterung 2.21.0** (aus dem Quellstand
gebaut wie `gulp build`; die Testkopie bekam nur die Host-Berechtigung, die
sonst „Apply“ erteilt) gegen Wegwerf-Kopien der Images. Der Wurf wird wie von
D&D Beyond als Runtime-Nachricht `{action: "roll"}` in die Erweiterung
gegeben. Danach laufen Hintergrund-Routing, Injektion von `generic_site.js`,
Roll-Renderer und DOM-Ereignis unverändert.

| Prüfung | Ergebnis |
| --- | --- |
| Chromium, Live-Image `mapmaker-library-20261108-f37e1136` | Beyond20 aktiv, Wurf kommt bei Spieler und DM an |
| Firefox (Firefox-Build der Erweiterung, MV2, temporäres Add-on über das Remote-Debugging-Protokoll) | dasselbe |
| Chromium, Image vom 29.10. (`research-survey-20261029`) | kommt ebenfalls an; Charaktername fehlte dort noch (am Morgen behoben) |
| Login → Übersicht → Tisch, 6× Neuladen, 3× Buch ↔ Tisch | 10 von 10 Ankünften mit aktivem Beyond20 |
| Beyond20-Issues/Releases (GitHub, 2026-11-08) | 2.21.0 ist aktuell; kein gemeldeter Bruch durch D&D Beyond |

Die Übertragung funktionierte also. Am Vollbild-Tisch war sie aber nicht zu
sehen: Würfe landeten nur im Würfel-Log im eingeklappten Menü, und ob
Beyond20 verbunden ist, stand ebenfalls nur dort.

Nebenbefund in Beyond20 selbst (nicht änderbar von unserer Seite): Lädt eine
bereits registrierte Seite in unter 100 ms neu, injiziert Beyond20 nicht
erneut. Der Tisch braucht lokal mindestens 150 ms, die Falle greift nicht.

## Änderung

Commit `fa4fe5c` auf `fix/beyond20-table-feed-20261108` (basiert auf dem live
ausgelieferten Vollbild-Stand `72229c7`/`11d0421`).

- `play.html`, `play-ui.js`: `#rollFeed` oben rechts über der Karte. Jeder
  externe Wurf erscheint 9 s (höchstens vier zugleich), fängt keine Klicks
  ab und ist ausgeblendet, solange das Menü offen ist. Die Position hängt am
  Id-Selektor, weil `book-shell.css` alle Body-Kinder auf `position:
  relative` setzt.
- `beyond20-bridge.js`: Chip `#beyond20Chip` in der Tischzeile, sichtbar
  sobald Beyond20 aktiv ist.
- `beyond20.html`: Abschnitt „Wenn keine Würfe ankommen“ nennt Chip und
  Einblendung.
- Neuer Browser-Test `tests/test_beyond20_table_feed_browser.py`.

## Prüfungen

- Echte Erweiterung gegen eine Kopie des Release-Inhalts: In **Chromium**
  erscheint der Chip. Eine Fertigkeitsprobe und ein Angriff mit Schaden stehen
  beim Spieler (1366×768) und bei der Spielleitung (390×844) oben rechts.
  Unter der Einblendung kommt der Klick auf der Karte an. Nach 10 s ist sie
  leer, das Würfel-Log behält beide Würfe. In **Firefox** gilt dasselbe für
  Chip und Einblendung bei Spieler und Spielleitung. Keine Seitenfehler.
- Neuer Test `tests/test_beyond20_table_feed_browser.py`: 2 von 2 grün.
- Alle Testdateien, die `play.html`, `play-ui.js`, `/play` oder Beyond20
  berühren: 231 bestanden, 2 fehlgeschlagen, 14 Errors. Das ist dieselbe Liste
  wie vor der Änderung (`test_pre_table_usability_closeout` zweimal;
  Firefox-Starts, die auf diesem Host scheitern).

## Auslieferung

- Commit `fa4fe5c` auf `fix/beyond20-table-feed-20261108`, gepusht.
- Image `roll-drauf-vtt-app:beyond20-feed-20261108-fa4fe5c`,
  `sha256:b9708602f2db85d6e8a67e7fe2923412cea61640baa882cdf7ea79749e9c87bc`,
  gebaut `FROM roll-drauf-vtt-app:mapmaker-library-20261108-f37e1136` (das
  laufende Image; dessen vier betroffene Dateien waren gleich dem Stand
  `11d0421`). Alle vier Dateien im Image hashgleich mit `fa4fe5c`.
- `production.duck-species.override.yml` umgestellt (Sicherung
  `.bak-beyond20-feed-20261108`), `up -d --no-deps --no-build app` um
  2026-11-08 22:04:59 UTC, Health 200 nach 3 s.

## Live-Prüfung

- `/static/js/play-ui.js` und `/static/js/beyond20-bridge.js` öffentlich
  hashgleich mit `fa4fe5c`. `/play` enthält `#rollFeed` und `#beyond20Chip`,
  `/beyond20.html` den neuen Hinweis. Startlog ohne Fehler.
- Nicht geprüft: ein echter Wurf von dndbeyond.com in die Live-Instanz
  (kein Live-Testkonto, kein D&D-Beyond-Konto auf diesem Host). Erster
  Schritt beim nächsten Spielabend: Tisch neu laden, auf „Beyond20“ oben in
  der Zeile achten, einen Wurf auslösen.

## Rollback

```
cd /srv/migration/2026-10-07/setup
cp -p production.duck-species.override.yml.bak-beyond20-feed-20261108 production.duck-species.override.yml
docker compose -p migration-production -f production.compose.json -f production.duck-species.override.yml up -d --no-deps --no-build app
```
Das vorherige Image `mapmaker-library-20261108-f37e1136` bleibt lokal erhalten.
