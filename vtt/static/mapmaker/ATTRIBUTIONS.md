# Kartenwerkstatt – Herkunft der Inhalte

| Inhalt | Quelle | Lizenz |
|---|---|---|
| `assets/kenney-cartography/*.png` (38 Symbole, 2 Pergament-Texturen) | Kenney Cartography Pack 1.0, https://kenney.nl/assets/cartography-pack — kuratiert von Codex, siehe `assets/kenney-cartography/README.md` und `manifest.json` | CC0 1.0 (`assets/kenney-cartography/License.txt`); Namensnennung „Kenney (www.kenney.nl)“ freiwillig |
| Schriften Cinzel, Literata, Bad Script (`/static/fonts/*.woff2`, nur referenziert) | Google Fonts, bereits im Repository vendored | SIL Open Font License 1.1 |
| Einfache Ersatzsymbole (Windrose, Ortsnadel, Berg, Baum, Haus, Burg) in `js/stamps.js` | im Projekt per Canvas-Code gezeichnet | Teil dieses Projekts |
| Geländemuster, Meereswellen, Startkarte „Die Silbermark“ | im Projekt prozedural erzeugt (`js/brush.js`, `js/render.js`, `js/starter.js`) | Teil dieses Projekts |

Bewusst **nicht** verwendet: `assets/sternenstaub/backgrounds/background-old-paper.jpg` (CC BY-SA 4.0), damit
exportierte Karten keine Share-Alike-Bedingungen erben. Die Pergamentoberfläche stammt aus der CC0-Textur oben.
