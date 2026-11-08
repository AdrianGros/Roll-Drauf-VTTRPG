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
- Öffentliche Künstler-Credits: `credits.html`, aus Kopfzeile, Stempelbereich und Hilfe erreichbar. Alle Bildpakete sind CC0; Kartenexporte benötigen daher keine verpflichtende Bild-Attribution. Die Werkstatt nennt die Künstler freiwillig.
- Vollständiges Bildinventar: `assets/inventory.csv`; reproduzierbare Quellen: `assets/source-lock.json`; deterministischer Import: `tools/import_mapmaker_assets.py`.
