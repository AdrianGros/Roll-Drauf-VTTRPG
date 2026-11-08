# Kartenwerkstatt: Discover / Asset-Inventar, 2026-11-08

**Status:** abgeschlossen; Profil `standard`. **Input:** bestehendes Inventar vollständig erfassen; breit nach kostenlosen, kommerziell und im Editor weitergebbaren Künstler-Assets suchen; keine generative KI; danach integrieren und Credits sichtbar machen. **Artefakte:** dieser Bericht und CSV-Inventar (dauerhaft); Originalarchive und Quellseiten unter `/tmp/mapmaker-assets-20261108` (temporärer Arbeitscache).

## Ist-Zustand

38 Kenney-PNG-Stempel in fünf Kategorien, zwei Pergament-PNGs, sechs Canvas-Ersatzsymbole (davon bei geladenem Paket zwei sichtbar), 14 prozedurale Malmaterialien. Sämtliche Dateien in der CSV mit SHA-256; unten alle nutzbaren Motive. Kenney Cartography Pack 1.0 (2020), CC0. Die alte README behauptet fünf Kategorien; maßgeblich sind die folgenden tatsächlichen Manifestwerte.

| ID | Name | Kategorie |
|---|---|---|
| `kenney:mountains` | Bergkette | Gelände |
| `kenney:crags` | Felsnadeln | Gelände |
| `kenney:rocks` | Felsen | Gelände |
| `kenney:mesa` | Tafelberg | Gelände |
| `kenney:volcano` | Vulkan | Gelände |
| `kenney:lake` | See | Gelände |
| `kenney:forest` | Nadelwald | Vegetation |
| `kenney:pine` | Tanne | Vegetation |
| `kenney:tall_pine` | Hohe Tanne | Vegetation |
| `kenney:tree` | Laubbaum | Vegetation |
| `kenney:palm` | Palme | Vegetation |
| `kenney:cactus` | Kaktus | Vegetation |
| `kenney:scrub` | Busch | Vegetation |
| `kenney:town` | Stadt | Siedlungen |
| `kenney:village` | Dorf | Siedlungen |
| `kenney:longhouse` | Langhaus | Siedlungen |
| `kenney:castle` | Burg | Siedlungen |
| `kenney:citadel` | Zitadelle | Siedlungen |
| `kenney:temple` | Tempel | Siedlungen |
| `kenney:tower` | Turm | Siedlungen |
| `kenney:lighthouse` | Leuchtturm | Siedlungen |
| `kenney:mill` | Windmühle | Siedlungen |
| `kenney:watermill` | Wassermühle | Siedlungen |
| `kenney:ruins` | Ruinen | Abenteuer |
| `kenney:mine` | Mine | Abenteuer |
| `kenney:graveyard` | Friedhof | Abenteuer |
| `kenney:campfire` | Lagerfeuer | Abenteuer |
| `kenney:camp` | Lager | Abenteuer |
| `kenney:ship` | Schiff | Abenteuer |
| `kenney:bridge` | Brücke | Abenteuer |
| `kenney:rope_bridge` | Hängebrücke | Abenteuer |
| `kenney:harbor` | Hafen | Abenteuer |
| `kenney:well` | Brunnen | Abenteuer |
| `kenney:watchtower` | Wachturm | Abenteuer |
| `kenney:danger` | Gefahr | Abenteuer |
| `kenney:compass` | Windrose | Navigation |
| `kenney:banner` | Banner | Navigation |
| `kenney:flag` | Flagge | Navigation |
| `kenney:parchment` | Pergament | Pergament |
| `kenney:folded_parchment` | Gefaltetes Pergament | Pergament |

**Ersatzsymbole:** builtin:compass, builtin:pin, builtin:mountain, builtin:tree, builtin:house, builtin:castle. **Materialien:** Land, Wiese, Wald, Steppe, Wüste, Schnee, Sumpf, Fels, Asche, Basalt, Lava, Flachwasser, Fluss, Weg. **Weitere Mechaniken:** editierbare Weg-/Flusspfade; Orte/Beschriftungen; Ebenen; Streustempel; Variation; Drehen/Spiegeln; PNG, Projektdatei und ZIP-Export; lokaler Entwurf. Keine externe Asset-Anfrage zur Laufzeit.

## Technisches und betriebliches Inventar

- `vtt/static/mapmaker/js/stamps.js`: bisher ein festes Manifest, höchstens 200 Einträge, ausschließlich `kenney:`; alle Bilder vorab geladen.
- `js/document.js`: Import erlaubt bisher nur `builtin:` und `kenney:`; neue Motive benötigen einen expliziten Namespace.
- `js/ui.js`: baut bisher alle Thumbnail-Canvases gleichzeitig; keine Suche oder Filter.
- `js/brush.js`: 14 prozedurale Materialien; `js/render.js` zeichnet Stempel aus dem Katalog.
- `index.html`: bestehender Einstieg über VTT-Hauptnavigation; Credits bisher nur `ATTRIBUTIONS.md`, kein sichtbarer Credits-Einstieg.
- Tests: `tests/test_mapmaker_static.py`, `tests/test_mapmaker_browser.py`; vorhandene Testumgebung `/tmp/roll-drauf-mapmaker/test-venv`.
- Live: nginx leitet an 127.0.0.1:15000, Container `roll-drauf-vtt-app-1`, Image `sha256:0febdcf788a3662a484e2a16429c82b588e4dc0d509b3a8d186849a00be20dd6` (`roll-drauf-vtt-app:research-survey-20261029`).
- Tatsächlicher Compose-Projektname `migration-production`; Dateien `/srv/migration/2026-10-07/setup/production.compose.json`, `production.duck-species.override.yml` und `/tmp/research-survey-deploy-20261029/override.yml`.
- `docker cp` + rekursiver Vergleich: Kartenwerkstatt lokal und live vor Änderungen identisch. Der übrige Arbeitsbaum enthält umfangreiche fremde Änderungen. Keine davon gehört in diese Lieferung.

## Quellenprüfung und Abhängigkeiten

| Quelle | Befund / Entscheidung |
|---|---|
| [Kenney](https://kenney.nl/assets/cartography-pack) | Bestehende 38 Motive und zwei Texturen; CC0, Ausgabe von 2020. Beibehalten. |
| [K. M. Alexander / #NoBadMaps](https://kmalexander.com/free-stuff/fantasy-map-brushes/) | 33 Set-Seiten und deren offizielle Downloads erfasst; zwölf vielfältige PNG-Pakete heruntergeladen, 6.418 PNGs vor Qualitäts-/Duplikatprüfung. Alle zwölf Readmes enthalten CC0; konkrete historische Karten als Ausgangsmaterial; Herkunftsgrundsätze seit 2019. |
| [Poly Haven](https://polyhaven.com/license) | CC0 inklusive Weitergabe. [Contribute](https://polyhaven.com/contribute) und FAQ schließen generative KI aus. Acht geeignete Boden-/Geländetexturen via öffentlicher API prüfbar; API-Bedingungen gesondert gelesen, eindeutiger User-Agent, keine Live-API-Abhängigkeit geplant. |
| [Game-icons.net](https://game-icons.net/about.html) | CC BY 3.0 und benannte Zeichner, als spätere POI-Ergänzung geeignet. In diesem Slice zugunsten kartografischer Stempel zurückgestellt. |
| [OpenGameArt](https://opengameart.org/content/cartography-pack) | Kenney-Mirror, keine zusätzlichen einzigartigen Assets; Einzelpaket-Lizenz entscheidend. |
| [CartographyAssets](https://cartographyassets.com/license/) | Unterschiedliche Einzel- und CAL-Lizenzen; kommerziell verwendbare Karten sind keine pauschale Weitergabefreigabe für einen Editor. KMA-Umsetzungen dort sind redundant, Originalquelle bevorzugt. |
| [2-Minute Tabletop](https://2minutetabletop.com/faq/license-and-attribution/) | NC-/spezielle kommerzielle Bedingungen; keine passende kostenlose kommerzielle Editor-Freigabe belegt. Ausgeschlossen. |
| [Forgotten Adventures](https://www.forgotten-adventures.net/info/) | Keine belegte freie Lizenz für diese Editor-Distribution; Webseite lieferte beim Direktabruf 403. Ausgeschlossen, keine Zugangssperre umgangen. |
| [Watabou](https://watabou.github.io/faq.html) | Freigabe generierter Karten ist keine Lizenz für einen unabhängigen Rohasset-Katalog; nicht übernommen. |

## Risiken, Annahmen und offene Fragen

- **Mittel, gelöst durch Grenze:** kommerzielle Kartenfreigaben ohne Rohasset-Weitergabe werden nicht übernommen. Nur CC0 mit Original-Lizenznachweis in dieser Lieferung.
- **Mittel, an Apply übergeben:** 6.418 Stempel dürfen nicht vollständig dekodiert oder gleichzeitig als Palette gerendert werden; bedarfsweises Laden und begrenzte Ergebnisse erforderlich.
- **Mittel, gelöst durch Liefergrenze:** fremde Änderungen und neuere Live-Funktionen schützen; Release auf dem verifizierten Live-Image aufbauen und nur den identischen Kartenwerkstatt-Teil ersetzen.
- **Niedrig:** Herkunftsprüfung beruht auf Künstlerdokumentation und historischen Originalquellen; keine universelle unabhängige KI-Erkennung behauptet.
- **Niedrig:** historische Symbole und Fototexturen haben unterschiedliche Stile; Paketwahl und Kategorien ermöglichen gezielte Auswahl.
- **Offene blockierende Fragen:** keine innerhalb dieser Grenze. Kostenpflichtige Pakete und Kontaktaufnahme zu Künstlern sind nicht Teil dieses Slices.

**Nächster Schritt:** Apply definiert lokalen Paketkatalog, stabile IDs, Suche/Filter, bedarfsweises Laden, neue Texturmaterialien, Credits-Navigation, Import-/Export-Kompatibilität, fokussierte Tests und Live-Rollout mit Rückfallimage.
