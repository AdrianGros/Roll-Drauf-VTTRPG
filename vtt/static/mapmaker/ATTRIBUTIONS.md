# Kartenwerkstatt – Herkunft der Inhalte

| Inhalt | Quelle | Lizenz |
|---|---|---|
| `assets/kenney-cartography/*.png` (38 Symbole, 2 Pergament-Texturen) | Kenney Cartography Pack 1.0, https://kenney.nl/assets/cartography-pack — kuratiert von Codex, siehe `assets/kenney-cartography/README.md` und `manifest.json` | CC0 1.0 (`assets/kenney-cartography/License.txt`); Namensnennung „Kenney (www.kenney.nl)“ freiwillig |
| Schriften Cinzel, Literata, Bad Script (`/static/fonts/*.woff2`, nur referenziert) | Google Fonts, bereits im Repository vendored | SIL Open Font License 1.1 |
| Einfache Ersatzsymbole (Windrose, Ortsnadel, Berg, Baum, Haus, Burg) in `js/stamps.js` | im Projekt per Canvas-Code gezeichnet | Teil dieses Projekts |
| Geländemuster, Meereswellen, Startkarte „Die Silbermark“ | im Projekt prozedural erzeugt (`js/brush.js`, `js/render.js`, `js/starter.js`) | Teil dieses Projekts |

Bewusst **nicht** verwendet: `assets/sternenstaub/backgrounds/background-old-paper.jpg` (CC BY-SA 4.0), damit
exportierte Karten keine Share-Alike-Bedingungen erben. Die Pergamentoberfläche stammt aus der CC0-Textur oben.

## Erweiterung vom 08.11.2026

- Zwölf historische Karten-Sets von **K. M. Alexander / #NoBadMaps**, CC0 1.0. Originale: https://kmalexander.com/free-stuff/fantasy-map-brushes/ . Historische Vorlagen, Originalpfade, Download-URLs und Original-/Ergebnis-SHA256 sind pro Paket in `assets/kma-*/manifest.json` dokumentiert; Original-Readmes einschließlich Lizenz in `License.txt`.
- Acht fotografierte Geländematerialien von **Rob Tuytel, Rico Cilliers und Dimitrios Savva / Poly Haven**, CC0 1.0. Einzelautoren je Textur in `assets/polyhaven-terrain/manifest.json`, Lizenzfreigabe https://polyhaven.com/license , Ausschluss generativer KI: https://polyhaven.com/contribute . Alle Assets dort ebenfalls kostenlos erhältlich.
- Keine Bildgenerierung oder KI-basierte Hochskalierung: nur Alpha-Randzuschnitt und klassische Lanczos-Verkleinerung mit Pillow; Stempel bis 384 px, nahtlose Farbtexturen 256 px.
- Öffentliche Künstler-Credits: `credits.html`, aus Kopfzeile, Stempelbereich und Hilfe erreichbar. Die oben beschriebenen historischen Pakete und Fototexturen sind CC0. Die unten aufgeführten farbigen Erweiterungen enthalten zusätzlich verpflichtende Künstler-Attribution.
- Vollständiges Bildinventar: `assets/inventory.csv`; reproduzierbare Quellen: `assets/source-lock.json`; deterministischer Import: `tools/import_mapmaker_assets.py`.

## Vier farbige Batches vom 08.11.2026

- Kenney Roguelike/RPG, Tiny Town, Medieval RTS, Isometric Buildings und Indie Squid Green Village: CC0. Originaldateien, Autorennennungen und unveränderte Lizenztexte im jeweiligen Paket.
- LPC Revised: OGA-BY 3.0. Alle Künstler der Root-Credits sowie sämtliche 35 Credits-Dateien werden mitgeliefert. Exakte Revision `f07f7f5892e67c932c68f70bb04472f2c64e46bc`; Archivhash in `assets/color-source-lock.json`. Eine leere Originaldatei enthält keine Grafik und wird in `coverage.json` als upstream-defekt dokumentiert.
- Acht RPG-Sets von Jana Ochse / 2D-Retroperspectives / 2DPIXX: CC BY 4.0 nach konkreter Archivfreigabe; die Webseiten nennen zusätzlich 3.0. SVGs werden technisch in PNG gerastert, vorhandene PNGs unverändert übernommen.
- Isometric Medieval Props: rubberduck, Daniel Andersson, yd und Lucian Pavel, CC0; 3D-Rendering/GIMP-Bearbeitung von 2018, kein generatives Verfahren.
- LPC castle: Evert, Lanea Zimmerman (Sharm), Xenodora; Castle Tiles for RPG's: Zabin, Hyptosis, Daniel Cook (Originalangabe Danial Cook). Beide CC BY 3.0. Nur die eigentlichen Burg-Tilesets; die gemischt lizenzierten Beispielbilder des zweiten Pakets werden nicht übernommen.
- Vollständige, kostenlose kommerzielle Nutzungsroute pro Paket: `assets/color-source-lock.json`, lokale `License.txt`, `manifest.json` und `coverage.json`. Künstlerarbeit und technische Aufbereitung sind dokumentiert. Keine KI-Bilder oder KI-Upscaling.
- PNG-Exporte enthalten UTF-8-iTXt-Credits aller verwendeten Bildpakete; das ZIP enthält zusätzlich `CREDITS.txt`. Bei Veröffentlichung die Angaben auch im Begleittext bzw. verlinkten Credits nennen, besonders wenn Plattformen Metadaten entfernen. Alle Original-Künstlerhinweise bleiben über `credits.html` zugänglich.
- Bildblätter sind als Gesamtbild und über frei wählbare Originalpixel-Ausschnitte platzierbar. Ausschnitte werden in der Kartendatei gespeichert; alte Editor-Versionen vor dieser Erweiterung verstehen dieses zusätzliche Feld nicht.
- Deterministischer Import: `tools/import_mapmaker_color_assets.py --batch 1..4 --cache <Verzeichnis>`. Gemeinsamer additiver Kataloggenerator: `tools/mapmaker_catalog.py`.
