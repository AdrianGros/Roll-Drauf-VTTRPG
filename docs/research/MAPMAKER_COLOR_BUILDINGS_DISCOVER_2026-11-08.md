# Discover: Farbige Fantasy-Gebäude und RPG-Tilesets

**Status:** Recherche abgeschlossen, 2026-11-08, Profil `standard`. **Input:** kostenlose Künstlergrafiken im RPG-Maker-Stil, ganze farbige Gebäude und ein großer Asset-Markt; kommerzielle Nutzung und Auslieferung im eigenen Karteneditor mit Credits; weiterhin keine KI-Bilder. **Artefakte:** dieser Bericht (dauerhaft); zwei untersuchte Originalarchive und Bildbeispiele unter `/tmp/rpg-color-assets-20261108` (temporärer Recherchecache). Keine neuen Anwendungsgrafiken integriert und keine Live-Anwendung geändert.

## Ergebnis und aktueller Bestand

Der vorhandene Karteneditor hat bereits eine lokale, nach Herkunft getrennte Bildpalette, Suche, Kategorien, Credits und PNG-Stempel. Die letzte Lieferung umfasst vor allem historische einfarbige Symbole. Die jetzt gesuchte farbige Gebäudeauswahl ist ein weiterer Content-Bereich. Der aktuelle Editor kann PNG-Objekte setzen; seine Palette ist kein vollständiger RPG-Tilemap-Baukasten. Ein Tilesheet mit vielen Wand-/Dachsegmenten entspricht daher nicht derselben Anzahl sofort platzierbarer Häuser.

**Passendster großer Marktplatz: [OpenGameArt](https://opengameart.org/content/lpc-collection).** Die LPC-Sammlungen bündeln viele kompatible RPG-Sets. Die kuratierte Variante [LPC Revised](https://github.com/ElizaWy/LPC) ist der stärkste konkrete Kandidat für einen einheitlichen farbigen Bestand. Zusätzlich bieten Kenney und einzelne OGA-Künstler fertige Gebäude und Dorfobjekte.

## Geprüfte Kandidaten

| Quelle / Originalpaket | Konkreter Inhalt | Lizenz und Beleg | Stand |
|---|---|---|---|
| [LPC Revised](https://github.com/ElizaWy/LPC) | Farbige 32-Pixel-Grafiken in Dreiviertelperspektive; Struktur, Objekte, Gelände und Figuren. | README nennt CC BY 3.0 / OGA-BY 3.0. [Root-Credits](https://github.com/ElizaWy/LPC/blob/main/Credits.txt) beschreiben die Zeichnungen als handgezeichnet und erlauben kommerzielle Nutzung mit Künstler-Credits. | Projektstruktur und konkrete Credits gelesen; keine vollständige Einzelprüfung des gesamten Bestands. |
| [LPC Revised: fertige Häuser](https://github.com/ElizaWy/LPC/tree/main/Structure/Structures) | `Brick House A.png`, `Brick House B.png`, `Paneled House A.png`; komplette Gebäude. Daneben modulare Wände, Dächer, Türen, Fenster, Treppen und Brücken. | [Ordner-Credits](https://github.com/ElizaWy/LPC/blob/main/Structure/Structures/Credits.txt): Lanea Zimmerman (Sharm), Eliza Wyatt (DeathsDarling), OGA-BY 3.0. Teilweise ausdrücklich als von Hand bemalte Details beschrieben. | Brick House A heruntergeladen und visuell geprüft: farbiges Haus mit Dach, Fassade, Fenstern, Eingang und Kamin. |
| [Kenney Roguelike/RPG](https://kenney.nl/assets/roguelike-rpg-pack) | Anbieter nennt 1.700 Grafiken/Tiles, 16×16; Stadt-/Gebäude-Bauteile und Ausstattung. | CC0, Release 2015. | Produktseite geprüft; Anzahl bezeichnet keine 1.700 vollständigen Gebäude. |
| [Kenney Tiny Town](https://kenney.nl/assets/tiny-town) | 130 Grafiken/Tiles, 16×16; kompakter farbiger Dorf-Baukasten. | CC0, Release 2023. | Produktseite geprüft. |
| [Kenney Medieval RTS](https://kenney.nl/assets/medieval-rts) | 120 Grafiken, mittelalterliche Karten-/Gebäudeobjekte. | CC0, Release 2016. | Produktseite geprüft. |
| [Kenney Isometric Tiles Buildings](https://kenney.nl/assets/isometric-tiles-buildings) | 128 Grafiken für Gebäude und Siedlungen in isometrischer Ansicht; Architektur vor Auswahl visuell auf Fantasy-Eignung prüfen. | CC0, Release 2014. | Produktseite geprüft, kein pauschales Fantasy-Prädikat. |
| [Green Village – Isometric Tiles](https://opengameart.org/content/green-village-isometric-tiles) | Vier vollständige Haus-PNGs (`house1` bis `house4`), Bäume, Wege, Brücken und Beispielszene. Künstler: Indie Squid. | Seite listet CC BY 3.0 und CC0; Archivhinweis bestätigt ausdrücklich CC0. | Originalarchiv und Beispielszene visuell geprüft; kleine, direkt greifbare Gebäudeauswahl. |
| [2DPIXX: RPG Tilesets](https://opengameart.org/content/rpg-tilesets), insbesondere [Village – Isometric](https://opengameart.org/content/rpg-village-isometric) | Zusammenhängende RPG-Umgebungen; das Dorfset enthält eine farbige SVG-Grafik. Autorin: Jana Ochse / 2D-Retroperspectives / 2DPIXX; laut Beschreibung in Inkscape gezeichnet, 2015 veröffentlicht. | Webseite: CC BY 3.0. Originalarchiv `LICENSE.TXT`: CC BY 4.0 mit Autorinnenangabe. Beide Nachweise erhalten; bei Aufnahme konkrete gewählte Fassung dokumentieren. | Originalarchiv geöffnet, SVG und Lizenztext geprüft. Für PNG-Palette ist deterministisches Rendern/Ausschneiden nötig. |
| [rubberduck: Isometric Medieval Props](https://opengameart.org/content/isometric-medieval-props) | Farbige Brunnen, Stände, Wagen, Kisten, Fässer und Dorfdekoration; Sommer-/Wintervarianten, mehrere Schattenvarianten, zwei Größen. | CC0; Quelle dokumentiert 3D-Rendering und GIMP-Nachbearbeitung, Release 2018. Weitere Ursprungsautoren genannt. | Produktseite und Herkunft geprüft; Ergänzung zu Gebäuden. |
| [LPC castle](https://opengameart.org/content/lpc-castle) | Farbige Burgmauern, Türme, Tore und Zugbrücke, 32×32. | CC BY 3.0. Credits: Evert, Lanea Zimmerman (Sharm), Xenodora. | Primärseite mit Bauteil- und Autorenbeschreibung geprüft, Veröffentlichung 2015. |
| [Castle Tiles for RPG's](https://opengameart.org/content/castle-tiles-for-rpgs) | Farbige Burg-/RPG-Bauteile, 32×32. | CC BY 3.0; Hyptosis, Zabin, Daniel Cook; Veröffentlichung 2012. | Primärseite geprüft. |

Kenney bestätigt selbst, dass seine enthaltenen Assets ohne KI erstellt wurden: [offizielle Antwort „No AI?“](https://itch.io/t/7318991/no-ai). Bei älteren OGA-Sets stützt sich die Herkunftsprüfung zusätzlich auf dokumentierte Künstlerarbeit und historische Veröffentlichungen; sie ist keine vermeintlich sichere Bilddetektor-Prüfung.

## Tatsächlich untersuchte Downloads

- Green Village: `https://opengameart.org/sites/default/files/Tiles_0.zip`, 432.357 Bytes, SHA-256 `c1228cb7c83c7e9e89da5ab37888acede78ec56c02af00841a18bef9cfdc4a38`. `Tiles/Indie Squid Tiles.txt` bestätigt CC0; vier Hausdateien vorhanden. Unveränderte Original-Beispielszene angesehen.
- 2DPIXX Village: `https://opengameart.org/sites/default/files/2DRP_CCArt_Village_Isometric.tar.gz`, 37.031 Bytes, SHA-256 `9b8bd1c308825b6ddae129da0da3a4e859b4d21a44a4d3327192bced0b4179d5`. Enthält `2DRP_CCArt_Village_Addon_Isometric.svg` und `LICENSE.TXT` mit CC BY 4.0 sowie Jana Ochse als Autorin.
- LPC: README, allgemeine Credits, Wände-Credits, vollständige-Häuser-Credits und ein konkretes Haus-PNG gelesen/geprüft. Rekursiver GitHub-API-Abruf lieferte 504. Das Gesamtarchiv überschritt die für diesen Rechercheversuch gesetzte 100-MB-Auswertungsgrenze; daher keine exakte Gesamtzahl aller Grafiken behauptet. Einzelne Primärdateien sind erreichbar.

## Nicht pauschal übernehmen

- **Allgemeine LPC-Collections:** Die Lizenz gilt pro Werk und Version. Zum Beispiel sind der alte [Base Structure Kit](https://opengameart.org/content/lpc-revised-base-structure-kit) und das [Castle Mega-Pack](https://opengameart.org/content/lpc-castle-mega-pack) als CC BY-SA 3.0 gelistet. Sie sind kein reines „nur Credits“-Angebot. Die aktuelle Revised-Sammlung muss anhand ihrer eigenen Credits geprüft werden.
- **itch.io als Ganzes:** Viele Treffer, aber kein einheitlicher Lizenzpool und keine pauschale Zusicherung gegen KI. [Pixel Village Pack von lazydev_OH](https://lazydev-oh.itch.io/pixel-village-pack), [Polyy.AI Village Buildings](https://polyyai.itch.io/city-builder-village-buildings) und [Fantasy Village Free Sampler](https://venicemenacebakingco.itch.io/fantasy-village-topdown-pack-free-sampler) geben KI-Erstellung/-Mitwirkung an und scheiden nach dem Auftrag aus.
- **[Reiner's Tilesets](https://www.reinerstilesets.de/graphics/lizenz/):** Kommerzielle Spielnutzung mit Credits wird erlaubt, Rohasset-Veröffentlichung und konkurrierende Ressourcenseiten sind eingeschränkt. Das ist keine belegte pauschale Freigabe für unseren öffentlich ausgelieferten Editor-Katalog; daher kein sofort freigegebener Kandidat.
- Hersteller-RTPs oder kommerzielle RPG-Maker-Pakete sind durch eine ähnliche Optik nicht automatisch für einen unabhängigen Webeditor lizenziert.

## Abhängigkeiten, Risiken und offene Fragen

- **Mittel, für Apply:** CC BY-/OGA-BY-Inhalte benötigen die konkreten Künstler-/Quellen-/Lizenzangaben. Die bisherige Credits-Seite und deren Aussage „alle Bildpakete CC0“ müssten bei einer späteren Integration zutreffend erweitert werden. Exporte benötigen eine passende mitlieferbare Attribution. Keine stillschweigende Übernahme in den bisherigen CC0-Import.
- **Mittel, für Apply:** Ganze Gebäude und modulare Tiles getrennt inventarisieren. Kleine Tiles müssen korrekt zusammengesetzt werden; 16×16/32×32 sind Rastermaße und keine garantierte Ausgabegröße eines vollständigen Hauses. SVG-Quellen sind für die bestehende PNG-Palette aufzubereiten.
- **Mittel, eingegrenzt:** Unterschiedliche Perspektiven und Pixelmaßstäbe dürfen nicht als einheitliches Set ausgegeben werden. LPC ist Dreiviertelansicht, Green Village/2DPIXX sind isometrisch.
- **Niedrig:** Webseite/Archiv bei 2DPIXX nennen unterschiedliche CC-BY-Versionen; beide erlauben kommerzielle Bearbeitung/Weitergabe mit Attribution, die konkrete Lizenzroute bleibt pro importiertem Asset festzuhalten. [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Niedrig:** Nicht jedes Asset der umfangreichen LPC-Sammlung wurde in dieser Recherche einzeln geprüft; keine globale Aussage über alle jemals eingestellten OGA-/itch-Inhalte.
- **Offene Produktfrage für den nächsten Entwurf:** gewünschte erste Stilfamilie: detaillierte LPC-Pixelgrafik oder isometrische Dorfobjekte. Dies blockiert die abgeschlossene Quellensuche nicht.

**Nächster Schritt in Apply:** anhand der belegten Quellen einen begrenzten farbigen Gebäudebestand spezifizieren, ganze Gebäude einzeln inventarisieren und die Credits-/Exportpflichten der gewählten Dateien festlegen. Die Recherche selbst ändert keine Anwendung und benötigt kein Deployment.
