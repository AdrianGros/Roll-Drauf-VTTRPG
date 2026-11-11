---
date: 2026-11-11
profile: standard
phases: discover, apply, deploy, monitor
status: deployed and live-verified (Tiny Town); further packs open
---

# Kartenwerkstatt: Tilesheets in ganze Stempel zerlegen (Pilot Kenney Tiny Town)

## Auftrag

Owner, 11.11.2026: Viele Asset-Pakete liefern Tilesheets, also mehrere Teile auf
einem PNG. Diese sollen strukturiert zerlegt und als einzelne Stempel angeboten
werden. Zuerst geht es um Stempel; Pilot ist Kenney Tiny Town, wo Bäume falsch
geschnitten waren. **Owner-Entscheidung:** Bilderkennung zum Erkennen der Teile
ist erlaubt, solange nichts generiert wird.

## Discover: bisheriger Stand

- `tools/import_mapmaker_color_assets.py` legt pro Archiv-PNG genau einen Stempel
  an. Sheets erhalten `sheet: true` und ein Paket-`grid`. Beim Wählen öffnet der
  Editor den manuellen Ausschnittdialog (`ui.js` `openSheet`), Raster ab (0,0),
  ohne Abstände. Es gab keine Objekterkennung.
- Tiny Town bot die 132 Original-Einzelkacheln `Tiles/tile_XXXX.png` als
  16×16-Stempel an. **Ursache des Baumfehlers:** Kenneys hohe Bäume (Zellen
  0,3+1,3 und 0,4+1,4), der Brunnen und das Burgtor gehen über zwei bis vier
  Kacheln. Angeboten wurden nur die Hälften, etwa „Tiles · tile_0004“ als Krone
  ohne Stamm. Beleg: [`before-tiny-town-cells.png`](proofs/mapmaker-tilesheet-slicing-2026-11-11/before-tiny-town-cells.png).
- Live lief `protocol-feedback-20261110-32cc5bfee`; alle acht hier berührten Dateien
  waren byteidentisch mit `0748abb41`.
- Im Worktree `roll-drauf-vtt-sprite-pipeline` liegt eine **nicht committete und
  nicht ausgelieferte** Pipeline vom 09.11. (Plan
  `docs/decisions/MAPMAKER_ASSET_PIPELINE_10_MILESTONES_2026-11-08.md`, M01–M08
  „in_progress“). Ihr Tiny-Town-Profil führt ebenfalls nur 16×16-Teile, alle
  sichtbar, plus zwei handgepflegte Häuser. Der Plan lehnte Bildanalyse als
  autoritative Quelle ab. Dieser Slice ändert den Worktree nicht.

## Apply: Entscheidung

**Erkennung schlägt vor, ein geprüftes Profil entscheidet, der Build kopiert nur
Originalpixel.** Das verbindet die neue Owner-Freigabe für Bilderkennung mit dem
Grundsatz des 08.11.-Plans, überprüfbare Authoringdaten zu verwenden.

1. **Erkennung** `tools/mapmaker_sheet_slicer.py detect` (`grid-alpha-v1`):
   Raster mit Zellmaß, Rand und Abstand. Jede Zelle wird als leer, voll oder
   teilweise eingestuft. Teilweise Zellen werden verbunden, wenn ein Motiv von der
   gemeinsamen Kante durchschnitten wird, also Füllfarbe auf beiden Seiten liegt.
   Bei Pixelart mit Umrisslinie zählt ein Kontakt von Umriss an Umriss nicht,
   denn das sind zwei Objekte, die sich nur berühren. Teilweise Zellen innerhalb
   der Objektgrenzen werden einbezogen (Waldecken). Volle Geländekacheln bleiben
   einzeln, außer ein Objekt umschließt sie von drei Seiten. Ausgabe sind ein
   nummerierter Kontaktbogen und ein Profilentwurf.
2. **Review** (Bilderkennung/Sichtprüfung durch Claude Code): Namen, Kategorien,
   Trennung oder Ergänzung von Objekten und Rezepte. Rezepte ordnen Originalkacheln
   wie ein Tiled-Stamp an, für Häuser nach Kenneys `Sample.png`. Das Ergebnis liegt
   versioniert in `tools/mapmaker_slices/<pack>.json`, Status `reviewed`.
3. **Build** `... build <pack>`: Komposite als PNG mit unveränderten Quellpixeln.
   Wenn das Paket Einzelkacheln mitliefert, behalten diese ihre ID (Pixelgleichheit
   wird geprüft) und bekommen nur Name und Kategorie. Neue IDs werden aus
   Sheet-Hash und Layout gebildet (`color:<pack>_<16 hex>`). Teile fester Objekte
   (Baumhälften) erscheinen in `palette.json` unter `hidden`: Sie stehen nicht in
   der Palette, Editor und Server lösen sie für gespeicherte Karten aber weiter
   auf. Später entfallende Slice-IDs bleiben ausgeblendet erhalten. Der Build ist
   byte-reproduzierbar.

Grenzen: keine Laufzeit-Bildanalyse, kein Terrain-Autotiling, keine Änderung an
Dokumentformat, Ausschnittdialog oder Rendergeometrie. Ganze Sheets bleiben
unter „Referenzen & Szenen“ für eigene Ausschnitte erreichbar.

## Deploy

| Bereich | Dateien |
| --- | --- |
| Werkzeug | `tools/mapmaker_sheet_slicer.py` (neu), `tools/mapmaker_slices/kenney-tiny.json` (neu), `tools/mapmaker_catalog.py` (`hidden`-Projektion) |
| Editor | `vtt/static/mapmaker/js/stamps.js`: verborgene IDs registriert, nicht gelistet |
| Daten | `assets/kenney-tiny/` (Manifest, Palette, Coverage, 17 neue PNGs), `inventory.csv`, `credits.html` |
| Tests | `tests/test_mapmaker_sheet_slicer.py` (neu), `test_mapmaker_static.py` (Slices in Coverage, Batch-1-Summe 589), `test_mapmaker_browser.py` (Tiny-Town-Reise) |

Ergebnis Tiny Town: 141 sichtbare Stempel statt 136 (inkl. zwei Referenzbildern
und zwei Sheets). Neu sind 17 zusammengesetzte Stempel: hoher Laub- und
Herbstbaum (16×32), Waldstück, Herbstwald, vier Häuser, Brunnen, Zaungehege, zwei
Zäune, Burghof, Burgmauer, Burgtor mit Fallgitter, offenes Burgtor und Erdfläche.
Alle 132 Kacheln tragen jetzt echte Namen („Axt“, „Bienenstock“,
„Schieferdach · Giebel“ …) in den Kategorien Bäume & Pflanzen, Fertige Häuser,
Objekte & Ausstattung, Zäune, Burg & Mauern, Gebäude & Bauteile sowie
Gelände & Tiles. Zwölf Objekthälften sind ausgeblendet.
Abgleich Erkennung zu Review: 8 von 9 erkannten Mehrzellobjekten wurden
unverändert übernommen. Die Burgfront wurde bewusst in Mauer und Tor getrennt;
Burghof, Mauer, Tor und Erdfläche kamen hinzu, die Häuser als Rezepte.

Checks vor dem Release: 62 bestanden, 1 übersprungen (Flask-Variante; Flask fehlt
in der Scratch-venv). Abgedeckt sind die komplette Mapmaker-Browser-Regression,
statische Katalogtests und die neuen Slicer-Tests ([`regression.txt`](proofs/mapmaker-tilesheet-slicing-2026-11-11/regression.txt)).

Release: Commit `802321cd34dbf9fcc05e6f46a80e00f61c2c8fd9` auf
`feat/creation-engine-g1`, gepusht. Overlay aus `git archive` dieses Commits auf
das laufende Image, 162 Dateien, alle Hashes im Image geprüft. Image
`roll-drauf-vtt-app:tilesheet-slicing-20261111-802321cd`
(`sha256:b9cf16b34a11bafce75c0e5c0e03284abb659e91134075d2261f55bdf1075ccc`),
Basis/Rollback-Tag `roll-drauf-vtt-app:tilesheet-rollback-20261111-f6bc1008f0bb`.
Nur der App-Dienst von `migration-production` wurde neu erstellt; DB, Redis und
Mail blieben unverändert. Rollback:
`/srv/migration/2026-11-11/tilesheet-slicing/rollback.sh`. Danach fehlen in
Karten, die neue Slice-Stempel nutzen, diese Symbole, bis erneut ausgeliefert wird.

## Monitor: Live-Nachweis

- `/health/live` ok, neuer Start 2026-11-11 00:53:33 UTC; keine Fehler im App-Log.
- Öffentlich ausgelieferte `stamps.js`, Tiny-Town-Manifest/Palette, `credits.html`
  und `inventory.csv` sind hashgleich zum Commit. Der Server kennt 72.081
  Symbol-IDs (vorher 72.064).
- Live-Reise über **Hauptnavigation → Karten** (`/mapmaker`), Chromium bei 1440 px
  und 390 px: Paket „Kenney · Tiny Town“ mit 141 Symbolen; „Krone“ findet nichts;
  vier fertige Häuser. „Hoher Laubbaum“ wird ohne Ausschnittdialog in 32 px
  platziert, „Haus mit Schieferdach“ in 48 px. Die gespeicherte Projektdatei
  enthält beide IDs. Keine Konsolen- oder CSP-Fehler
  ([`live-journey.json`](proofs/mapmaker-tilesheet-slicing-2026-11-11/live-journey.json),
  Screenshots `live-*.png`).
- **Lücke:** Die Reise lief als Gast. Angemeldete Player-/DM-Durchläufe wurden
  nicht ausgeführt; für diese reine Static-Änderung wurden keine temporären Konten
  in der Produktionsdatenbank angelegt. Editor und Palette sind für alle Rollen
  dieselbe statische Seite; Bibliothek und Rechte sind unverändert.

## Restrisiken und nächster Schritt

- Niedrig: Pixelart bleibt im Maßstab 1 Quellpixel = 1 Kartenpixel und ist auf
  Weltkarten klein; Größe ist pro Stempel regelbar.
- Mittel, offen: Die übrigen Sheets sind noch nicht zerlegt. Der Probelauf ohne
  Katalogänderung zeigt, dass der Detektor trägt
  ([`dryrun-castle-rpg.png`](proofs/mapmaker-tilesheet-slicing-2026-11-11/dryrun-castle-rpg.png),
  [`dryrun-other-sheets.jsonl`](proofs/mapmaker-tilesheet-slicing-2026-11-11/dryrun-other-sheets.jsonl)).
  Bei gemalter Grafik ohne Umriss (Castle RPG) erkennt er Uhrenbaum, Brunnen,
  Banner, Statue, Laterne, Amboss und Regale. Gestapelte Kisten und
  Burgmauerzeilen verkleben dort noch und brauchen Review-Trennungen.
  Isometrische SVG-Sheets ohne Raster benötigen einen zweiten Detektormodus
  (Pixel-Zusammenhangskomponenten).
- Der 11-09-Worktree bleibt unangetastet. Ob er weitergeführt oder durch diesen
  Weg ersetzt wird, entscheidet der Owner.

Nächster begrenzter Schritt: je Paket `detect` → Review → `build`, beginnend mit
Castle RPG, LPC Castle und den 2DPIXX-Rastern, jeweils mit Kontaktbogen-Review
und Live-Abnahme.

Bildnachweise: Kenney Tiny Town, Kenney Vleugels, CC0-1.0. Castle Tiles for RPGs,
Zabin, Hyptosis, Daniel Cook, CC-BY-3.0,
https://opengameart.org/content/castle-tiles-for-rpgs.
