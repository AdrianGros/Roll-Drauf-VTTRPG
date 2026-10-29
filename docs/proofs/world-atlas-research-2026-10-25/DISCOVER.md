# Discover: Karteneditor → kollaborativer Weltatlas

Stand: 25.10.2026. DAD-M `standard`. Dieses Dokument enthält Bestandsaufnahme und Recherche; Lösungsvorschläge stehen getrennt im [Apply-Paket](../../WORLDBUILDING_ATLAS_PLAN_2026-10-25.md). Desktop-Monitor-Berichte werden separat verlinkt. Kein Produktcode, keine Migration und keine Veröffentlichung in diesem Auftrag.

## Eingabe und Untersuchungsgrenze

Der Nutzer beschreibt zwei Einstiege: eine einzelne Karte für D&D zeichnen und herunterladen; oder eine persönliche bzw. mit mehreren DMs betreute Welt aus verbundenen Karten aufbauen. Gewünschte Navigation: Welt → Kontinent → Land/Region → Stadt/Dorf/Wald/Weg. Orte, Gruppen und Detailkarten sollen interaktiv erreichbar sein. Zu untersuchen sind vollständige CRUD-Bedienung, komfortabler Desktop-Arbeitsbereich, Zusammenarbeit und Rechte, Roll20-Übergabe, Ausschnitte, Hochskalieren, Detailgenerierung und Raster-/Kacheluploads.

Es gibt kein zusätzliches verbindliches „Sheet“: Der Nutzer hat klargestellt, dass damit praktische Werkzeugbedienung gemeint war. Wettbewerber sind Vergleichsquellen, keine vollständige Funktionsvorgabe. Mobile/Tablet ist ausdrücklich später; die zuvor dokumentierte mobile Ortsnavigation bleibt offen. Der frühere unvollständige Sicherheitsreview wird durch diesen UX-/Rechercheauftrag nicht ersetzt.

## Bestand mit Belegen

| Bereich | Beobachteter Stand | Beleg |
|---|---|---|
| Kartenwerkstatt | Eigenständige statische Canvas-2D-Anwendung mit Werkzeugleiste, Pinseln, Stempeln, Text-/Ortsobjekten, Ebenen und Verlauf | [index.html](../../../vtt/static/mapmaker/index.html), [app.js](../../../vtt/static/mapmaker/js/app.js) |
| Dokument | `rd-mapmaker`, Version 1; Rasterebenen enthalten Bilddaten, Stempel und Texte besitzen Objekt-IDs; ein Ort ist bisher Metadatum eines Textobjekts | [document.js](../../../vtt/static/mapmaker/js/document.js) |
| Grenzen | 256–4096 Pixel je Seite; maximal 32 Ebenen, davon 8 Rasterebenen; 32 Mio. Rasterpixel insgesamt; 2000 Objekte; Projektdatei maximal 50 MiB | `document.js:6` |
| Speicherung | Lokaler IndexedDB-Autosave unter einem Entwurfsschlüssel; JSON-Datei zum Weiterbearbeiten und PNG-Export. Keine serverseitige Welt- oder Projektbibliothek | [storage.js](../../../vtt/static/mapmaker/js/storage.js), `app.js:751–861` |
| Semantik | Sechs Ortsarten mit kurzer Lore; kein eigenständiges Welt-Ortsregister, kein Karten-Elternverweis, keine Gruppenpositionen, keine Weltmitglieder | `document.js:32`, Dokumentvalidierung und Editor-UI |
| Inhalt | Bestehende Silbermark-Beispielkarte und kuratierte CC0-Kenney-Bibliothek mit 38 Stempeln und 2 Texturen; alle 40 Assetdateien entsprechen ihren Manifest-Prüfsummen. Keine automatische Welterzeugung im Editor | [starter.js](../../../vtt/static/mapmaker/js/starter.js), [Manifest](../../../vtt/static/mapmaker/assets/kenney-cartography/manifest.json), [Hersteller/Lizenz](https://kenney.nl/assets/cartography-pack) |
| VTT-Karte | `CampaignMap` enthält kampagnengebundenen Namen, Hintergrund, Abmessungen, Raster und Licht-/Nebelparameter. Keine Atlas-Hierarchie | [campaign_map.py](../../../vtt/models/campaign_map.py) |
| Bestehender Importpfad | Kampagnen-Asset-Upload und anschließendes Erstellen einer `CampaignMap`; PNG lässt sich als Hintergrund übernehmen. Keine automatische Übernahme von Editorobjekten oder Lore | [assets.py](../../../vtt/endpoints/assets.py), [routes.py](../../../vtt/campaigns/routes.py), früherer [Übergabenachweis](../mapmaker-dao-2026-10-24/coverage/report.md) |
| Mitgliedschaft | `CampaignMember` kennt DM/CO_DM/Player/Observer und Einladungsstatus pro Kampagne. Das ist keine weltweite Autorenrolle | [campaign_member.py](../../../vtt/models/campaign_member.py) |
| Assetbestand | Vorhandene Speicherung, Quoten, Uploadvalidierung, Miniaturen und Assetversionen. Assets sind bisher kampagnenbezogen | [asset.py](../../../vtt/models/asset.py), `assets.py:291` |
| Spielzustand | Sitzungszustand und Tokens verweisen auf taktische Kampagnenkarten. Keine dauerhafte, kampagnenübergreifende Welt-Gruppenposition gefunden | [session_state.py](../../../vtt/models/session_state.py), [token_state.py](../../../vtt/models/token_state.py) |
| Frühere Recherche | Editor bereits als eigener Arbeitsstrang gegenüber MMO/Meta-Layer benannt. Späteres Atlas-Modell mit Elternbezug und verknüpften Entitäten skizziert; bisher keine umgesetzte Migration | [MMO-Discover](../../DADM_DISCOVER_MMO_META_LAYER_CONCEPT_2026-07-21.md), [Atlas-Analyse §10.5](../../UI_ANALYSE_WORLD_ATLAS_HOME_2026-08-18.md) |

Negativaussagen beziehen sich auf die untersuchten Mapmaker-, Modelle-, Kampagnen-, Asset- und Atlas-Dokumentationsbereiche, nicht auf einen Beweis über jedes externe System. Der Kampagnen-Import wurde früher auf API-Ebene mit einer Wegwerfdatenbank geprüft; ein vollständiger angemeldeter Roll20- oder VTT-Browserdurchlauf ist hier noch nicht nachgewiesen.

## Primärquellen: Bedienung und Kartenzeichnung

Abrufdatum aller Quellen: 25.10.2026. Funktionsbeschreibungen wurden anhand von Hersteller-/Projektunterlagen geprüft. Es wurden keine kostenpflichtigen Vergleichsprodukte eingerichtet oder systematisch live getestet.

| Quelle | Belegtes Muster | Relevanz für die Untersuchung |
|---|---|---|
| [Inkarnate 2.0](https://feedback.inkarnate.com/changelog/inkarnate-20-star) | Eigene Ebenen, Objektorganisation, überarbeiteter Pinsel und Kopieren zwischen Szenen | Direkter Werkzeugzugriff und nachvollziehbares Ziel von Änderungen; der aktuelle Prototyp hat bereits Ebenen und Pinsel, aber keine vollständige Objektliste |
| [Inkarnate veröffentlichte Fehlerkorrekturen](https://feedback.inkarnate.com/changelog?c=Fixed) | Historische Korrekturen an Wiederherstellung, Notizen, Verlauf und Darstellung | Prüfkategorien für dauerhaften Inhalt und Browser-Zoom. Keine Behauptung, dass diese Fehler heute noch bestehen |
| [GIMP: Verschieben](https://docs.gimp.org/3.0/en/gimp-tool-move.html) | Werkzeug per Icon/Shortcut; Auswahl unter dem Zeiger oder Beschränkung auf ausgewählte Ebenen | Falsches Objekt bei überlappenden Elementen auswählen ist ein konkretes Interaktionsrisiko; sichtbarer Auswahlzustand ist zu prüfen |
| [GIMP: Export](https://docs.gimp.org/3.0/en/gimp-export-dialog.html) | Bearbeitbares Projekt und exportiertes Bild haben getrennte Speicherwege | JSON muss weiterhin bearbeitbar bleiben; PNG darf nicht als vollständige Sicherung von Lore und Ebenen dargestellt werden |
| [GIMP 3.0](https://www.gimp.org/release-notes/gimp-3.0.html) | Mehrfachauswahl, besser sichtbare Ebenensperren und vereinfachtes Einfügen | Referenz für Schutz vor unbeabsichtigten Änderungen und verständliche Zustände, keine Forderung nach einem GIMP-Klon |
| [Wonderdraft](https://wonderdraft.net/) | Land-/Küstenzeichnung, Flüsse, Straßen, Symbole und Beschriftung als Kartenwerkzeuge | Ein Waldpinsel oder eine Straßenzeichnung muss im Ergebnis brauchbar sein; reines Vorhandensein eines Buttons reicht nicht |
| [Roll20: Art Library](https://help.roll20.net/hc/en-us/articles/360039675113-Art-Library) | Eigene Bilder hochladen und im Spiel verwenden; Bildformate und Uploadgrenzen sind dokumentiert | PNG als manuelle Übergabe ist realistisch. Kein Beleg für direkte Synchronisierung unseres JSON-Formats |
| [Roll20: neue Rasterausrichtung, Beta vom 19.08.2026](https://blog.roll20.net/posts/align-to-grid-new/) | Sichtbarer Einstieg auf der Kartenebene; geführtes Ausrichten über Anker, Skalierung und Feinabgleich | Wichtig für spätere gridded Imports: klarer Assistent statt versteckter Einstellungen; Beta-Status ist zu berücksichtigen |

## Primärquellen: interaktive Welten und Zusammenarbeit

| Quelle | Belegtes Muster | Grenze der Übertragbarkeit |
|---|---|---|
| [Rare Thief: Sea-of-Thieves-Weltkarte](https://rarethief.com/sea-of-thieves-interactive-world-map/) und [Kartenansicht](https://maps.seaofthieves.rarethief.com/) | Kategorien, Suche und interaktive Informationen über Orte und Spielinhalte | Vergleich für Leserführung. Kein Nachweis einer offenen kollaborativen Autorenplattform oder automatisch erfasster Live-Gruppenpositionen |
| [LegendKeeper](https://www.legendkeeper.com/) | Verschachtelte Karten, verknüpfte Landmarken/Wikiseiten, Zusammenarbeit und geschützte Geheimnisse werden vom Hersteller beschrieben | Belegt die Kombination Atlas + Lore. Nicht unabhängig auf Konfliktverhalten, Rechteumsetzung oder Exportvollständigkeit geprüft |
| [World Anvil FAQ](https://www.worldanvil.com/faq) | Hochgeladene Karten interaktiv machen; von Welt über Gegend/Stadt bis zu Gebäude-/Schlachtkarten verlinken; Inhalte unterschiedlich freigeben | Ein Bildeditor und ein interaktiver Weltatlas erfüllen verschiedene Aufgaben |
| [World Anvil: Co-Autoren](https://www.worldanvil.com/learn/access-rights/co-authors) | Abgestufte Autorenrollen; Kennzeichnung und Sperre beim gleichzeitigen Bearbeiten eines Artikels | Zusammenarbeit erfordert Bearbeitungs- und Veröffentlichungsrechte sowie einen expliziten Konfliktweg; die Rollen dieses Produkts sind keine unveränderte Vorgabe für uns |
| [World Anvil: Geografie](https://www.worldanvil.com/learn/article-templates/geography) | Natürliche Orte verschiedener Maßstäbe, Elternorte und optionale Beschreibungsfelder | „Ort“ muss mehr bedeuten können als Stadt/Burg. Fragen zur Weltbeschreibung können helfen, dürfen den Einstieg aber nicht verpflichtend aufblasen |
| [Tiled: Worlds](https://doc.mapeditor.org/en/stable/manual/worlds/) | Mehrere Karten mit Positionen zusammen anzeigen und zwischen ihnen wechseln; nur Nachbarn laden ist möglich | Nebeneinanderliegende Kartenstücke sind ein anderes Modell als Welt-/Stadt-Karten mit wechselndem Maßstab |
| [Tiled: Infinite Maps](https://doc.mapeditor.org/en/stable/manual/using-infinite-maps/) | Wachsende Tile-Ebenen statt fester äußerer Kartengrenze | Geeignetes Vorbild für einen späteren Kachelmodus; unser bestehendes Rasterdokument ist derzeit endlich und kein Tile-Editor |
| [Azgaar: Knowledge Base](https://github.com/Azgaar/Fantasy-Map-Generator/wiki/Knowledge-Base) | Submap/Transform erzeugen Karten aus vorhandener Grundlage neu; Details können sich ändern; Seed allein genügt nicht ohne Optionen und Generatorversion | Ausschnittgenerierung ist möglich, aber kein verlustfreies Vergrößern. Ergebnis muss als neuer Entwurf überprüfbar bleiben |
| [Azgaar: Journeys](https://github.com/Azgaar/Fantasy-Map-Generator/wiki/Journeys) | Benannte Reise mit Segmenten und unterschiedlichen Fortbewegungsarten | Reisen/Route und aktuelle Gruppenposition sind getrennte Informationen |
| [Red Blob Games: Terrain aus Noise](https://www.redblobgames.com/maps/terrain-from-noise/) | Höhen-/Biomdaten entstehen aus expliziten Regeln, Frequenzen und Parametern | Veranschaulicht den Unterschied zwischen gezeichneten Pixeln und einem strukturierten geografischen Modell |

## Primärquellen: technische Bausteine

| Quelle | Belegt | Noch keine Produktentscheidung |
|---|---|---|
| [Leaflet: nicht geografische Karten](https://leafletjs.com/examples/crs-simple/crs-simple.html) | Bild, Marker und Linien in einem lokalen Koordinatensystem; Karteneinheiten müssen nicht Bildpixel sein; API-Reihenfolge ist y/x | Eignung für unseren konkreten Stack und die gewünschte Markerdichte müsste in einem begrenzten Versuch gemessen werden |
| [OpenSeadragon](https://openseadragon.github.io/) und [DZI](https://openseadragon.github.io/examples/tilesource-dzi/) | Viewer für große Bilder und mehrere Bildpyramiden-/Kachelquellen | Alternative für sehr große Bildatlanten, keine Hierarchie-/Rechte-/Lore-Lösung |
| [MapLibre: Quellen](https://maplibre.org/maplibre-style-spec/sources/) | Raster-, Vektor- und Bildquellen; Bildkoordinaten werden geografisch beschrieben | Mächtiger Kandidat, dessen Koordinaten- und Projektionsmodell erst zum Fantasieatlas passen muss |
| [GDAL: gdal2tiles](https://gdal.org/en/stable/programs/gdal2tiles.html) | Bildkacheln, Auflösungsstufen, Rasterprofil und unterschiedliche TMS/XYZ-y-Richtung | Die aktuelle Dokumentation kündigt ab 3.13 den Übergang zu `gdal raster tile` an. Kein Installations- oder Versionsentscheid in dieser Recherche |
| [RFC 9110, If-Match](https://www.rfc-editor.org/rfc/rfc9110.html#name-if-match) | Bedingtes Schreiben kann veraltete Änderungen vor dem Überschreiben abweisen | Konfliktschutz ist zusätzlich zu Anwesenheitsanzeigen nötig; Datenbankprüfung muss atomar sein |
| [Yjs: gemeinsamer Editor](https://docs.yjs.dev/getting-started/a-collaborative-editor) | Synchronisierte Datentypen, Editorbindung und Transportprovider als getrennte Bausteine | Daraus folgt keine automatische Zusammenführung von Rasterbildern, kein Rollenmodell und keine fachlich korrekte Auflösung jeder Kartenänderung |

## Technische Befunde zu Ausschnitten, Maßstab und Raster

**Bilder und Geografie:** Unser Raster speichert Farben und Transparenz. Daraus sind politische Grenzen, Flussnetze, Höhen oder die Bedeutung einzelner Wälder nicht zuverlässig wiederherstellbar. Ein Textobjekt „Nordwald“ ist noch keine Waldfläche mit Grenzen. Diese Feststellung folgt aus dem vorhandenen Dokumentformat, nicht aus einer Einschränkung der genannten Vergleichsprodukte.

**Hochskalieren:** Ein 400×300-Pixel-Ausschnitt wird durch eine Vergrößerung auf 1600×1200 nicht mit neuen, gesicherten geografischen Informationen angereichert. Interpolation glättet/vergrößert vorhandene Daten. Generative Verfahren könnten neue Details vorschlagen, würden diese aber erfinden. Die gewünschte Ableitung einer Stadt aus einem Weltsymbol ist deshalb eine zusätzliche Autorenentscheidung.

**Drei unterschiedliche Rasterbegriffe:** (1) Spielraster für Entfernungen/Snapping; (2) räumliche Zusammensetzung mehrerer gleichmaßstäblicher Kartenstücke; (3) technische Bildkacheln in mehreren Auflösungen für schnelles Laden. Keines der drei erzeugt von selbst die inhaltliche Hierarchie Welt → Stadt. Tiled dokumentiert (2), Roll20 (1), Bildpyramiden-/Viewer-Dokumentation (3).

**Kontinente zählen:** Eine vorhandene Weltkarte in X Rechtecke zu schneiden ergibt X Ausschnitte, nicht zwangsläufig X Kontinente. Selbst zusammenhängende Landmassen benötigen fachliche Benennung/Zuordnung. Ein Generator könnte X gewünschte Landmassen als Erzeugungsziel bekommen; das ist eine andere Operation als das Zerschneiden einer fertigen Karte. Es ist kein entsprechender Generator im aktuellen Editor vorhanden.

## Abhängigkeiten, Risiken und offene Fragen

| ID | Schwere | Befund / Voraussetzung | Behandlung im nächsten Schritt |
|---|---|---|---|
| D01 | Hoch | Private DM-Lore und unveröffentlichte Karten dürften nicht an Spieler ausgeliefert werden. Bestehende Asset-Rechte behandeln Karten nicht wie geheime Handouts (`assets.py:37–52`) | Weltweite Leserechte, Inhaltsprojektion und geschützte Bild-/Kachelzugriffe separat entwerfen; vorhandenen Kampagnenpfad nicht als Geheimnisschutz voraussetzen |
| D02 | Hoch | Gemeinsames Bearbeiten ganzer lokaler Dokumente ohne Konfliktschutz könnte Arbeit überschreiben | Konflikt-/Versionskonzept vor einer Serverfreigabe festlegen; kein stilles „letzter Speichervorgang gewinnt“ |
| D03 | Mittel | Vollständiges CRUD jedes gezeichneten Elements ist bei zusammengeführten Rasterpixeln nicht gleichbedeutend mit Objekt-CRUD | Ergebnis der beiden UI-/Quellenprüfungen ausweisen; ausdrücklich zwischen Rasterkorrektur und eigenständigem Pfad/Objekt unterscheiden |
| D04 | Mittel | Hierarchieverschiebung oder neues Hintergrundbild kann Markerpositionen und Links verfälschen | Koordinaten-/Transformationsvertrag und Lösch-/Verschieberegeln als Apply-Artefakt erforderlich |
| D05 | Mittel | Große Weltbilder überschreiten schnell Dokument-/Browser-/Exportlimits | Bildbetrachtung und Bearbeitung getrennt messen; lokale Editorgrenzen nicht unbemerkt aufheben |
| D06 | Mittel | Bildexport transportiert keine interaktive Lore, Rollen oder Detailkarten | Bild und bearbeitbares Projekt/Atlas-Paket eindeutig unterscheiden |
| D07 | Mittel | Verborgene Informationen können bereits im gezeichneten Bild stehen | Spieleransicht benötigt eine bewusst freigegebene Darstellung; Verstecken von Marker-JSON genügt dann nicht |
| D08 | Mittel, ausdrücklich vertagt | Bekannte mobile Ortsnavigation verdeckt das Ziel mit offenem Panel | Desktop-Auftrag darf abgeschlossen werden, ohne dies als behoben zu erklären |
| D09 | Hoch / Mittel, Prüfung abgeschlossen | Frischer Claude-Durchlauf und unabhängige Codex-Reproduktion bestätigen Datei-Rundlauf und Objekt-CRUD, aber auch ungeschütztes Dateiöffnen, Fokusfehler beim Verschieben und riskanten Wiederherstellungseinstieg | [Monitor-Einordnung](INTERPRETATION.md) enthält tatsächliche CRUD-Matrix, Belege und Gewichtung; E0 muss diese offenen Befunde vor strenger Abnahme auflösen |
| D10 | Offen | Umfang gleichzeitiger Bearbeitung, Besucherfreigaben, Weltgröße und gewünschte Generatorart sind noch nicht festgelegt | Empfehlungen mit klaren ersten Grenzen formulieren; keine kostenpflichtigen Dienste oder dauerhaften Architekturabhängigkeiten einführen |

Relevante wiederverwendbare Grundlagen sind Anmeldung, Kampagnen-Mitgliedschaften als Referenz, Datei-/Assetvalidierung, Speicheradapter und das bestehende lokale Editorformat. Offene Integrationsgrenzen: Welt kann mehrere Kampagnen umfassen; eine Karte kann ohne Welt existieren; Spieltokens haben andere Lebensdauer und Rechte als Atlas-Gruppenpositionen.

## Discover-Abschluss und nächster Schritt

Es gibt einen nutzbaren Karteneditor-Prototyp sowie ältere Atlas-Konzeptarbeit, aber noch keinen nachgewiesenen kollaborativen Weltatlas. Die Recherche zeigt belastbare Vergleichsmuster für verschachtelte Karten, Informationen auf Bildern, gemeinsame Autorenarbeit und räumlich angeordnete Kartenstücke. Sie belegt keine fertige Import-/Synchronisierungslösung für unseren Stack.

Nächste Phase: getrenntes Apply-Paket mit zwei Einstiegen, flexibler Hierarchie, Vertragsentwurf für Karte/Ort/Platzierung/Version, Rechte- und Konfliktmodell, begrenztem Ausschnittworkflow sowie prüfbaren Etappen. D01–D07 werden dabei als Designbedingungen behandelt; vor einem späteren Deploy müssen die jeweils relevanten Bedingungen und die frischen Desktop-Befunde aufgelöst oder ausdrücklich akzeptiert sein. Diese Recherche enthält keinen Deploy-Auftrag.
