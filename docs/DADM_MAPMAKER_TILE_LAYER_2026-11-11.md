---
date: 2026-11-11
profile: standard
phases: discover, apply, deploy, monitor
status: deployed and live-verified
---

# Kartenwerkstatt: Kacheln getrennt von Stempeln (Kachelebene)

## Auftrag und Owner-Entscheidung

Owner, 11.11.2026, im Anschluss an das Tilesheet-Slicing: Stempel-Assets
(Gegenstände, Bäume) und echte Tiles müssen unterschieden werden. Zur Wahl
standen Raster-Einrasten im Stempel-Layer, eine reine Palettentrennung und eine
eigene Kachelebene. **Gewählt: eigene Kachelebene.**

## Discover

- Das Dokument `rd-mapmaker` v1 kennt nur die Ebenen `raster`, `paths`, `stamps`
  und `labels`. Stempel werden frei mit Mittelpunkt platziert, es gibt kein Raster.
  Eine Karte erlaubt höchstens 2000 Elemente (`document.js` `LIMITS.items`,
  Server `item_count`).
- Der einzige Server-Konsument ist die persönliche Bibliothek
  (`vtt/endpoints/mapmaker.py` → `normalize_document`).
- Live lief der Editor von `feat/protocol-feedback-20261110` (`32cc5bfee`). Vor den
  Änderungen wurden `index.html`, `ui.js`, `tools.js`, `mapmaker.css` und die
  Browser-Tests exakt auf diesen Stand gebracht (Commit `be54198cb`).

## Apply

1. **Format (additiv in v1):** Ebenenart `tiles` mit `grid.size` (8–256
   Kartenpixel), `palette` (≤ 256 eindeutige, bekannte Asset-IDs) und
   `cells = [spalte, zeile, index, …]`, zeilenweise sortiert. Zellen müssen in
   `ceil(w/size) × ceil(h/size)` liegen, jede Zelle höchstens einmal. Höchstens
   65.536 Kacheln pro Karte, getrennt vom 2000-Elemente-Limit. Client
   (`document.js`) und Server (`mapmaker_document.py`) prüfen identisch.
2. **Katalog:** Das Review-Profil des Slicers entscheidet. Zellen mit `kind`
   `tile` werden Kacheln, `object` und alle Komposite sind Stempel, ausgeblendete
   Objekthälften sind keins von beiden. `palette.json` erhält eine additive
   `tiles`-Liste. Die Stempelauswahl zeigt keine Kacheln, die Kachelauswahl nur
   Kacheln (quadratisch). Alle IDs bleiben überall auflösbar; ältere Karten, die
   Kacheln als Stempel nutzen, laden unverändert.
3. **Editor:** Werkzeug „Kacheln“ (Taste K) mit Setzen/Löschen, eigener Palette
   (Suche, Paket, Seiten) und Kachelgröße. Klicken oder Ziehen füllt Zellen,
   schnelle Züge werden lückenlos interpoliert, ein Zug ist ein Undo-Schritt. Die
   erste Kachel legt „Kacheln N“ direkt über der obersten Malebene an (unter Wegen,
   Symbolen und Text); Undo entfernt die automatisch angelegte Ebene wieder.
   Raster und Zellvorschau erscheinen nur im Kachelwerkzeug. „+ Kachelebene“ und
   die Kachelgröße stehen auch unter „Ebenen“. Eine Größenänderung skaliert die
   Ebene und wird abgelehnt, wenn belegte Zellen außerhalb der Karte lägen.
4. **Darstellung/Export:** Kacheln füllen ganzzahlige Zellen, Pixelart ohne
   Glättung, bei Teil-Neuzeichnen nur betroffene Zellen. Zu PNG, ZIP, Autosave
   und Bibliothek kommen die Credits der Kachelpakete. Die Handy-Werkzeugleiste
   fasst acht Werkzeuge; unter 360 px zeigt sie nur Symbole.

Bewusst nicht enthalten: Terrain-Autotiling, Kacheln aus noch nicht zerlegten
Paketen, Einrasten frei platzierter Stempel am Kachelraster.

## Deploy

| Bereich | Dateien |
| --- | --- |
| Dokument/Server | `js/document.js`, `vtt/mapmaker_document.py` |
| Editor | `js/app.js` (Malen/Löschen, Undo, Vorschau), `js/tools.js` (Werkzeug, Taste K), `js/ui.js` (Kachelpalette, Ebenen), `js/render.js`, `js/stamps.js`, `js/credits.js`, `index.html`, `mapmaker.css` |
| Katalog | `tools/mapmaker_sheet_slicer.py` (Klassifizierung), `tools/mapmaker_catalog.py` (`tiles`), `assets/kenney-tiny/manifest.json`, `palette.json` |
| Tests | `test_mapmaker_tiles_server.py` (neu: gültige/ungültige Kachelebenen, Obergrenze 65.536), Kachelreise und Importvertrag in `test_mapmaker_browser.py`, Klassifizierung in `test_mapmaker_sheet_slicer.py`, `tiles`-Projektion in `test_mapmaker_static.py` |

Tiny Town: 97 Kacheln, 44 Stempeleinträge (17 zusammengesetzte Objekte,
23 Einzelobjekte, je 2 Sheets und Referenzbilder), 12 ausgeblendete Hälften.

Checks: letzter vollständiger Lauf 81 bestanden, 3 übersprungen (Flask-Varianten;
Flask fehlt in der Scratch-venv). Zwei Zwischenbefunde sind in
[`regression.txt`](proofs/mapmaker-tile-layer-2026-11-11/regression.txt) beschrieben
und behoben bzw. als lastabhängiger Timing-Ausreißer eingeordnet.

Release: Commits `be54198cb` (Live-Abgleich), `cb6c7d136` (Funktion), `f526e937b`
(Beschriftung) auf `feat/creation-engine-g1`, gepusht. Zwischen den beiden
Tiny-Town-Releases hatte jemand anders `feedback-contexts-20261111-721fc1c8c`
ausgeliefert; dieses Image enthielt den Tiny-Town-Stand bereits. Alle 12
überschriebenen Dateien waren dort byteidentisch mit der Basis `be54198cb`.
Overlay aus `git archive`, Hashes im Image geprüft. Aktives Image
`roll-drauf-vtt-app:tile-layer-20261111-f526e937`
(`sha256:d32dd25233615598d03020860f1f0c9a81d79b5b357d0e2eadf02c0b13d76895`);
`…-cb6c7d13` lief von 08:28 bis 08:31 UTC. Nur der App-Dienst wurde neu
erstellt. Rollback auf `feedback-contexts`:
`/srv/migration/2026-11-11/tile-layer/rollback.sh`. Danach öffnet der ältere
Editor Karten mit Kachelebenen nicht mehr, bis erneut ausgeliefert wird.

## Monitor

- `/health/live` ok (Start 08:31:54 UTC), keine Fehler im App-Log, DB/Redis/Mail
  unverändert. Öffentlich ausgelieferte Editor-Dateien und die Tiny-Town-Palette
  sind hashgleich zum Commit.
- Live über **Hauptnavigation → Karten** (`/mapmaker`), Chromium 1440 px und
  390 px ([`live-journey.json`](proofs/mapmaker-tile-layer-2026-11-11/live-journey.json)):
  Die Stempelauswahl für Tiny Town zeigt 44 Einträge und kein Gras. Das
  Kachelwerkzeug zeigt 97 Kacheln. Ein Zug mit „Gras“ legt „Kacheln 1“ (32 px)
  mit 7 Zellen lückenlos an; Undo entfernt die Ebene, Redo stellt sie wieder her.
  Die gespeicherte Projektdatei enthält `grid`, `palette` und 7 Zellen. Keine
  Konsolen- oder CSP-Fehler. Screenshots `live-*.png`.
- **Lücke wie beim Slicing-Release:** Die Abnahme lief als Gast. Angemeldete
  Player-/DM-Durchläufe, darunter Speichern in die persönliche Bibliothek mit
  Kachelebene, sind live nicht ausgeführt. Die Server-Validierung dafür ist
  durch `test_mapmaker_tiles_server.py` und eine Prüfung im fertigen Image belegt.

## Restrisiken und nächster Schritt

- Niedrig: Eine Zelle hält genau eine Kachel. Transparente Kacheln (Zäune,
  Waldränder) brauchen eine zweite Kachelebene; der Hinweis steht im Werkzeug.
- Niedrig: Frei platzierte Stempel rasten nicht am Kachelraster ein (Tiny-Town-
  Stempel stehen im Maßstab 1:1, Kacheln standardmäßig 2:1).
- Offen: Kacheln gibt es bisher nur aus Tiny Town. Weitere Pakete kommen über
  `detect` → Review (`kind: tile/object`) → `build` hinzu.
