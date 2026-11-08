# Deploy: Spieltisch als Vollbild mit einer transparenten Steuerzeile

Datum: 2026-11-08. Phase: **Deploy + Live-Prüfung**. Auftrag des Owners (beim
Spielabend bemerkt): Auf kleineren Auflösungen nehmen das obere
Orientierungsmenü und die Slider zu viel Platz weg. Am Spieltisch soll oben nur
eine Reihe Knöpfe ohne Hintergrund stehen; jeder Pixel, der nicht für
Navigation gebraucht wird, gehört dem Tisch. Die MMO-Elemente sollen den
Überblick nicht verdecken.

## Befund vor der Änderung

Gemessen mit einer Wegwerf-Kopie des Live-Images
(`mapmaker-color-b4-20261108-dd1084c4`), DM-Ansicht, Anteil der Kartenfläche am
Fenster:

| Fenster | Karte beginnt bei | Kartenhöhe | Anteil |
| --- | ---: | ---: | ---: |
| 1440×900 | 208 px | 607 px | 65 % |
| 1366×768 | 208 px | 475 px | 59 % |
| 1280×720 | 204 px | 433 px | 58 % |
| 1024×768 | 125 px | 602 px | 75 % |
| 844×390 (Handy quer) | 123 px | 228 px | 56 % |
| 390×844 (Handy hoch) | 119 px | 686 px | 73 % |

Oben lagen Sitzungstitel, Hauptnavigation mit Kontokasten, eine Zoomzeile mit
Slider und fünf Statuschips. Dazu kamen Seitenränder, ein Rahmen und unten ein
eigener Streifen für die Werkzeugleiste. Auf dem Handy lag die Aktionsleiste
hinter der unteren Werkzeugleiste. Die Mobilregel zum Ausblenden der
Hauptnavigation wirkte nicht, weil `vtt-main-nav.css` danach geladen wird.

## Änderung

Commit `7fda74a` auf `feat/playtable-fullscreen-20261108` (basiert auf dem live
ausgelieferten `d48d727`). Geändert sind nur `vtt/templates/play.html` und
`vtt/static/js/play-ui.js`.

- `body.play-fullscreen`: eigener, zuletzt geladener Stilblock. Der Tisch füllt
  das ganze Fenster (`100dvh`), ohne Buchrahmen, Ränder und Abrundungen.
- Eine Zeile oben, ohne Hintergrund: Sitzungstitel, kompakte Chips (Rolle,
  deutscher Status, „nur lesen“ nur wenn zutreffend, Anwesende) und Zoom −/%/+/FIT.
  Slider und RST entfallen. Unter 560 px Breite entfallen die Anwesenden.
- Werkzeugleiste, Aktionsleiste und Widgets liegen halbtransparent über der
  Karte. Die Aktionsleiste sitzt auf dem Handy über der unteren Leiste und
  verschwindet, solange das Menü-Sheet offen ist.
- Navigation (Übersicht, Charaktere, Karten) steht im Sitzungsmenü (↩ Zurück),
  neben „Zur Kampagne zurückkehren“.
- Das Seiten-Widget startet eingeklappt, außer am DM-Platz auf Bildschirmen ab
  820 px Höhe.

## Prüfungen

Nach der Änderung belegt die Karte in allen sechs Fenstern 100 % der Fläche;
keine Seitenfehler. Screenshots der geöffneten Seitenleiste, des Sitzungsmenüs
und des Tisch-Sheets auf Desktop und Handy geprüft.

Testlauf und Auslieferung werden unten ergänzt.

Testlauf auf allen Testdateien, die `play.html`, `play-ui.js` oder `/play`
berühren: 231 bestanden, 2 fehlgeschlagen, 14 Errors. Die Errors sind
Firefox-Starts (auf diesem Host nicht startbar), die zwei Fehlschläge
(`test_pre_table_usability_closeout`) bestehen auch auf dem unveränderten Stand.

Dabei fiel `test_session_exit_and_reload_keep_modern_campaign_hub[chromium-return]`
sporadisch aus: Seit dem Tischplatz-Paket wurden die Knöpfe erst nach dem
Bootstrap gebunden, ein früher Klick auf „Zurück“ verpuffte. Commit `72229c7`
bindet Sitzungsmenü und Navigation sofort; der Platz-Menüpunkt wird delegiert.
Danach: dieser Test 5 von 5 grün, Vertrags-, Tischplatz-, Würfel-, Balu- und
Creation-Engine-Navigationstests 81 von 81 grün (Chromium).

## Auslieferung

- Commits `7fda74a` und `72229c7` auf `feat/playtable-fullscreen-20261108`,
  gepusht.
- Image `roll-drauf-vtt-app:playtable-fullscreen-20261108-72229c7`,
  `sha256:2bdcccc4ee829406f63957c0cd32cda02e376b8d9b9cd91df304cdf73f556200`,
  gebaut `FROM roll-drauf-vtt-app:mapmaker-color-b4-20261108-dd1084c4` (das um
  18:09 UTC laufende Image; dessen `play.html`/`play-ui.js` waren gleich dem
  Ausgangsstand `d48d727`). Beide Dateien im Image hashgleich mit `72229c7`.
- `production.duck-species.override.yml` umgestellt (Sicherung
  `.bak-playtable-fullscreen-20261108`), `up -d --no-deps --no-build app` um
  2026-11-08 18:09:08 UTC, Health 200 nach 11 s.

## Live-Prüfung

- `/play` und `/static/js/play-ui.js` öffentlich hashgleich mit `72229c7`;
  Startlog ohne Fehler.
- Nicht geprüft: die angemeldete Live-Ansicht (kein Live-Testkonto; lesende
  Container-Prüfungen lehnt die Berechtigungsprüfung ab). Nach einem Reload
  zeigt der Tisch oben nur noch die eine Zeile.

## Rollback

```
cd /srv/migration/2026-10-07/setup
cp -p production.duck-species.override.yml.bak-playtable-fullscreen-20261108 production.duck-species.override.yml
docker compose -p migration-production -f production.compose.json -f production.duck-species.override.yml up -d --no-deps --no-build app
```
Das vorherige Image `mapmaker-color-b4-20261108-dd1084c4` bleibt lokal erhalten.
