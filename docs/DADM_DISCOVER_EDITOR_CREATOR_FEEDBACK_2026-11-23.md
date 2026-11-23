# Discover: zweites Feedback zu Karteneditor, Sitzungseinstieg und Charaktereditor

Status: vollständig ausgewertet und mit dem aktuellen Quellstand abgeglichen; keine Anwendung geändert. Die ursprünglichen E01–E27 bleiben unverändert im [ersten Discover](DADM_DISCOVER_MAPMAKER_REVIEW_2026-11-23.md) und sind im [Claude-Übergabepapier](CLAUDE_HANDOFF_MAPMAKER_27_2026-11-23.md) zu sechs Paketen gebündelt. Die N-IDs unten bezeichnen Beobachtungen aus der zweiten Aufnahme, keine pauschal neuen Implementierungsaufträge.

## Eingang und Aussagegrenzen

Quelle: Owner-Anhang `2026-11-23-1113-karteneditor-und-creation-engine-im-test.txt`, Beginn `2026-11-23T11:13:52.839Z`, Dauer 39:12. SHA-256: `32c7da185b9c1b07354055f346c62e78e7337fb687708923d1a44c7360df42b1`. Zeitmarken beziehen sich auf diese Aufnahme. Das Original bleibt unverändert beim Anhang; private Nebenunterhaltungen und Namen von Testkampagnen/-figuren werden nicht ins Backlog übernommen.

Geprüfter Arbeitsstand: `41519a2c0b8c50e3c0f3239a72001cdd193df9c3` auf `fix/canvas-scenes-20261123`. Dokumentierte und während der Bestandsaufnahme lesend geprüfte laufende Funktionsquelle: `ca61fc4fd0d28ee524bb6353114c30bf8ea83e1b`, Image `sha256:16304c0ba8313ac37b3129878e3303e74e1cfae4a8010fb1b628181484aa0b7f`. Vor einer späteren Umsetzung den dann aktuellen Stand feststellen. Die Aufnahme enthält keine verlässliche Versionskennung der dort geöffneten Browserseite.

**Berichtet** heißt: in der Aufnahme beobachtet, hier nicht erneut im Browser reproduziert. **Codebeleg** heißt: konkreter statisch geprüfter Pfad; daraus folgt keine vollständige Live-Abnahme. **Wunsch** heißt: gewünschte Erweiterung oder Bedienwirkung. Diese Auswertung ist keine vollständige Prüfung der Charakterregeln: Bei 28:09–28:30 wird der große Creation-Engine-Test ausdrücklich auf später verschoben.

Die charakterbezogenen Beobachtungen betreffen erkennbar den SRD-Charakterersteller mit Klassen, Herkunft, Attributen und Würfen (`srd-creator.js`). Die Bezeichnung „Creation Engine“ im Gespräch ist kein Beleg, dass sämtliche Punkte den separaten Homebrew-Authoring-/Compilerbereich betreffen.

## Wichtigste Befunde

1. **Sitzungseinstieg zuerst untersuchen.** Der Tester erreicht weder in einer bisherigen noch einer neu angelegten eigenen Kampagne zuverlässig den Tisch. Ein anderer Teilnehmer kommt mobil in seine Sitzung. Das ist ein dringender Einstiegsausfall, kein belegter Totalausfall aller Tische. Fehlende Mitspieler sind eine Vermutung. Der Code liefert einen konkreten Verdacht auf die Reihenfolge von Start und autorisiertem Tischbeitritt.
2. **Die Sprachvorgabe wurde im Gespräch geklärt.** Die Regelsprache soll den gesamten Charakterersteller und Charaktereditor bestimmen; die übrige Website darf ihre eigene Oberflächensprache behalten. Die zwischenzeitliche Idee deutscher Feldnamen mit englischen Regelwerten wurde bei 36:29–37:11 verworfen. Der aktuelle Ersteller liest fest deutsche Regeldaten und ist deshalb durch zusätzliche UI-Übersetzungen allein nicht konsistent englisch.
3. **Rasteränderungen bewegen Inhalte tatsächlich.** Die Kachelposition ergibt sich aus Zeile/Spalte × Rastergröße. Die Größenänderung behält Zeile/Spalte bei und verschiebt dadurch vorhandene Kacheln. Referenzraster, Einrasten und bewusste Inhaltsskalierung brauchen unterscheidbare Zielverträge.
4. **Vieles vertieft bestehende Pakete.** Ebenenziele und Bedienleiste gehören zu M2, Symbolauswahl/Filter zu M4. Schriftwahl, Stempelrotation und eine autorisierte Atlas-Speicheranbindung sind bereits vorhanden. Beschriftungsvorschau, native Kachelrotation, Textkrümmung und weitergehende Welt-/Kampagnenverknüpfungen gehen darüber hinaus.

## Nachvollziehbarer Index

Priorität in dieser Auswertung: **P0** blockierter Kernzugang, sofort reproduzieren; **P1** nächster Korrektur-/Bedienungsschnitt; **P2** Erweiterung oder nachgelagerte Gestaltung. Das ändert nicht rückwirkend die Einstufungen der E-Liste. „Neu“ bedeutet neu gegenüber den ursprünglichen 27 Punkten.

| ID | Zeit | Beobachtung und gewünschte Wirkung | Abgleich und nächste Grenze | Prio / Bezug |
| --- | --- | --- | --- | --- |
| N01 | 01:16–01:40 | Kachel als freies Symbol: Bild/Anzeige scheint zu verschwinden; freie Anordnung schwer verständlich. | Berichtet. `tileAsSymbol` übernimmt dieselbe Asset-ID in den Stempelmodus. Unklar, ob Palette, Vorschau oder gesetztes Objekt gemeint ist; diese drei Zustände getrennt reproduzieren. Kein belegter Assetverlust. | P1; M2/M4 ergänzen |
| N02 | 01:40–01:54 | Materialfarbe ist beim Bildpinsel ausgegraut, wird nach Materialwechsel wieder bedienbar. | Codebeleg: `syncBrush` deaktiviert Materialfarbe/-textur für Bildspitzen ausdrücklich, um Originalfarben zu erhalten. Bedienerklärung/Modusverständnis fehlt im Test; eine neue Bildtönung ist nicht automatisch beauftragt. | P1; M1 ergänzen |
| N03 | 01:58–03:34, 05:03 | Dasselbe Motiv landet je nach Raster, freiem Symbol oder Malen auf drei vorausgewählten Ebenen; gemeinsames Entfernen scheitert. | Bestätigte unterschiedliche Repräsentationen: Kachelzellen, Stempelobjekte, Rasterpixel. Vertieft das Ebenenzielproblem. Gewünschte zusammenhängende Bedienung festhalten; kein blindes Zusammenwerfen unvereinbarer Ebenentypen oder globales Radieren. | P1; E09/E16/E20, M2 |
| N04 | 03:51–04:42 | Zusätzlich an Ecken/Zwischenpositionen einrasten; Beispiel vier Ausgangsplätze plus neun Schnittpunkte. | Neuer Wunsch. „Halbes Raster“ und das genannte 13-Punkte-Muster sind nicht automatisch identisch. Gewünschte Fangpunkte, Anker und Überlappung in Apply anhand eines 2×2-Beispiels festlegen. | P2; M2 ergänzen |
| N05 | 04:42–05:15 | Raster auch beim freien Platzieren als Orientierung behalten; Größe schnell ändern. | Codebeleg: `renderOverlay` zeichnet das Kachelraster nur beim Werkzeug `tile`. Ein sichtbares Referenzraster muss von eingeschaltetem Einrasten unterscheidbar bleiben. | P1; M2 ergänzen |
| N06 | 05:32–06:24 | Wechsel 16 → 24 → 32 verschiebt vorhandene Kacheln; Position soll erhalten bleiben. | Codebeleg: `setLayerProp(..., "gridSize", ...)` hält Zellenindizes fest, `drawTiles` rendert mit `col * size`, `row * size`. Das erklärt die Bewegung. Zielvertrag und Altdokument-/Undo-Verhalten vor Formatänderungen klären. | P1; neu, M2 |
| N07 | 06:24–07:30 | Rastergröße frei eingeben, z. B. 70; alternativ Zeilen/Spalten, z. B. 50×70, und Karte darauf ausrichten. | Neue Battlemap-Kalibrierung. Pixel je Feld, Feldanzahl, Kartenabmessungen und Skalierung sind getrennte Größen. Die im Gespräch genannte 70 ist ein Beispiel, kein nachgewiesener allgemeiner Standard. | P2; neu, eigener Rastervertrag |
| N08 | 07:38–08:39 | Mehr gemalte/anders aufgelöste Motive statt überwiegend 16-Bit-Optik. | Vertieft Stil-/Katalogwunsch. Kachelformat ist kein Zeichenstil; zunächst vorhandene Motive und Filter prüfen, danach verbleibende Inhaltslücken und Rechte. Keine pauschale Neubeschaffung aus einem leeren Filter ableiten. | P2; E26/E27, M4/M5 |
| N09 | 08:52–09:28 | Native Kacheln drehen, etwa Dachanschlüsse in vier Richtungen. | Neue Kachelzellenfunktion; freie Stempel besitzen bereits Rotation. `drawTiles` zeichnet Zellen ohne Rotation. Zellenformat, Validator, Atlas-/Projekt-/PNG-/ZIP-Pfade müssten dieselbe Erweiterung verstehen. | P2; neu, M2/M5 berührt |
| N10 | 09:52–10:15, 16:46–17:05 | Lange Orts-/Text-Dropdowns laufen in Brave über; geöffnete Auswahl verändert Breite/Canvas und erzeugt schwarzen Rand. | Berichtet, genaue Ursache offen. Native Popupgröße von tatsächlichem Seiten-Reflow unterscheiden. Werkzeugwechsel und lange Einträge dürfen die Arbeitsfläche nicht unbeabsichtigt verschieben. | P1; E23, M2 |
| N11 | 10:23–11:11 | Atlas/Welt → Karteneditor als normaler Bearbeitungseinstieg; Kartenorte mit Welteinträgen verbinden; mehrere Kampagnen in einer DM-Welt. | Teilweise vorhanden: `atlas-bridge.js` lädt/speichert autorisierte Weltkarten und verlinkt zurück. Orts-/Welteintragsbeziehungen und kampagnenübergreifender Standardablauf sind ein eigener strategischer Umfang. | P2; neu, Atlas/Welt-Apply |
| N12 | 11:11–12:35 | Ortsymbol und Text vor Setzen als halbtransparenten Blueprint sehen; Größe abschätzen. | Neuer Vorschauwunsch. Stempel besitzen bereits einen Cursor-Ghost, Labels im geprüften Overlay keinen entsprechenden Zweig. Vorabkonfiguration soll ausdrücklich **nicht verpflichtend** werden. | P1; M3 ergänzen |
| N13 | 12:43–12:56 | Schnellwinkel 45/90/135 zusätzlich zum stufenlosen Regler. | Vorhandene freie Rotation als Basis; zusätzliche Presets/Erreichbarkeit sind neu. Von N09 zur nativen Kachelrotation unterscheiden. | P2; M3 ergänzen |
| N14 | 12:56–13:45 | Beschriftung entlang einer Biegung für Bergketten/Wälder. | Neue Textgeometrie; vorhandene gerade Textrotation ist keine Textkrümmung. Kurvenumfang, Auswahlfläche, Schriftmetriken und Export vor Implementierung klären. | P2; neu, M3 ergänzen |
| N15 | 14:05–14:42 | Schrift wählen und Buchstabenabstand separat vergrößern, ohne riesige Schriftgröße. | Schriftwahl `labelFont` und ausgelieferte Schriftfamilien existieren. Tracking ist im Renderer an Stil und Schriftgröße gebunden; ein frei bedienbarer Abstand wäre die Erweiterung. Keine zweite Fontauswahl bauen. | P2; teilweise vorhanden, M3 |
| N16 | 15:08–15:31 | Platzierungsmodus klar verlassen; Werkzeugauswahl bleibt an stabiler Stelle statt unter neuer Beschreibung zu verschwinden. | Codebeleg: Escape bricht Geste ab/entwählt, wechselt aber nicht zum Auswahlwerkzeug. Gewünschten Modusabschluss definieren; wiederholtes Platzieren bleibt ein bewusster Arbeitsablauf. Zusammen mit E23 bearbeiten. | P1; E23, M2 |
| N17 | 16:36–16:46 | Ortsymbolauswahl zeigt unabhängig vom Stil nur ähnliche Baum-/Buschoptionen. | `updateSymbolOptions` nutzt die IDs der aktuellen Palettenseite plus gewählte Assets. Filterlogik aus E26 und Quelle/Umfang des Pickers gemeinsam prüfen; kein isolierter zweiter Assetkatalog. | P1; E26, M4 |
| N18 | 17:25–21:34, 22:17–22:42 | Start/Eintritt führt zum Hub-Hinweis zurück; alte und neue Kampagne betroffen; Doppelklick erzeugt weitere Einträge. | Dringender Bericht mit konkretem Codeverdacht unten. Keine Spieler/Karte/Termin als bewiesene Ursache ausgeben. Erfolgreicher mobiler Zugang eines anderen Teilnehmers begrenzt die Aussage. Zusätzliche Einträge auf persistierte Duplikate vs. doppelte Darstellung prüfen. | **P0**; neu, Sitzungseinstieg |
| N19 | 22:03–23:30 | Gespräche/Atlas wirken kaputt, Compendium wirkt korrekt; Hub-Inhaltsverzeichnis startet bei 2, Schrift/Format und Einträge inkonsistent. | Berichtet. Seitenrahmen, Inhaltsverzeichnis und tatsächliche Inhalte getrennt prüfen. Fehlende „1“ nicht durch Wiederherstellen fachlich abgeschaffter Funktionen lösen; aktuelle Eintragsliste und einheitliche Gestaltung abgleichen. | P1; neu, gemeinsame Navigation |
| N20 | 24:20–25:21 | Header kurz doppelt; UI verändert sich beim Laden und hängt vom Navigationsweg ab. | Bericht ohne Screenshot; kein Codebeweis für konkrete Ursache. Direkter Aufruf, interne Navigation, Zurück/Vorwärts und langsames Laden vergleichen. Doppelte Initialisierung, CSS-Reihenfolge, Cache/BFCache sind Hypothesen. | P1; neu, gemeinsame Navigation |
| N21 | 25:40–27:48 | Nach Untermenüwahl fehlt sichtbarer aktiver Hauptbereich „Spiel & Figuren“; gelegentlich falsche Zuordnung. | Gemeinte Wirkung: aktueller Bereich bleibt auch bei geschlossenem Menü erkennbar. `vtt-main-nav.js` besitzt bereits `has-active`; Route, Fokus und Offen-Zustand sowie Aktualisierung bei BookScene-Wechseln prüfen. Kein Auftrag, das Menü permanent aufzuklappen. | P1; neu, gemeinsame Navigation |
| N22 | 29:15–30:12 | „Geführt / alles auf einmal“ wirkt doppelt/unklar; entfernte Formulierung „bewusst schlank“ wird begrüßt. | Text-/Hierarchiekorrektur, kein Wunsch nach Abschaffung eines Modus. Den positiv bewerteten entfernten Text nicht zurückbringen; beide Arbeitsweisen verständlich benennen. | P2; neu, Creator-Bedienung |
| N23 | 31:16–31:29 | Vier Standardherkünfte sind zu wenig. | Codebeleg: generierte DE-Basis enthält vier Hintergründe. Eigene Hintergründe/Talente werden zusätzlich über den Origin-Katalog geladen. Inhaltsausbau/Quelle/Rechte getrennt von einem unbewiesenen Ladefehler behandeln. | P2; neu, Inhaltsumfang |
| N24 | 32:19–33:09 | Bronze/Petrol ändern Akzente, Zufallscharakterbereich bleibt lila; Zählanzeigen sollen zum Farbschema passen. | Berichtet. Creator hat bereits spätere CSS-Overrides auf `--ui-accent`/`--ui-soft`; die erste lila Defaultdefinition allein beweist keine Ursache. Berechnete Stile der betroffenen Flächen prüfen, Warn-/Fehlersemantik erhalten. | P1; vertieft früheres Palette-Feedback |
| N25 | 33:21–33:57 | „Klassentext lesen“: Hauptattribut, Trefferpunkte/-würfel und Rettungswürfe schlecht lesbar; Listen verbessert. | Darstellungsbericht, kein Beleg falscher Regelwerte. Detail-Renderer/Definitionslisten und deren CSS prüfen; Quelle und strukturierte Regelwerte erhalten. Verbesserte Listen nicht zurückbauen. | P1; neu, Creator-Lesbarkeit |
| N26 | 34:09–38:52 | Trotz englischer Regel-/Oberflächensprache gemischte Klassennamen, Attribute, Waffen, Hintergründe, Methoden und Invocation-Texte; Compendium wirkt korrekt. | Bestätigter fester DE-Datenpfad im Creator; endgültige Sprachvorgabe und Annahmegrenzen unten. „Charisma“ allein ist kein geeigneter Sprachtest, da in beiden Sprachen gleich. | **P1, hohe Breite**; neu, Modul-Lokalisierung |

## N18: Einstieg und Kontext als erster Reproduktionsschnitt

Statisch nachgewiesene Kette:

- `book-scene.js:startCampaignHubSession` und `createCampaignHubSession` schicken zuerst `POST /api/sessions/<id>/start`. Erst nach Erfolg rufen sie `enterPlay(..., seat: 'dm')` auf.
- `vtt/play/contexts.py:install_http_guard` erfasst diesen Legacy-Pfad und verlangt bereits einen gültigen DM-Tischkontext. Auch `_is_gm` im Legacy-Endpunkt leitet die Rolle aus diesem Kontext ab.
- `auth.js:makeAuthRequest` bereitet für kampagnenqualifizierte Session-URLs einen Kontext vor; der Legacy-Startpfad fällt nicht unter diesen regulären Ausdruck. Ein frisch geöffneter Hub erzeugt durch diesen Startaufruf allein daher keinen Kontext für die Zielsitzung. Ein schon vorhandener Kontext kann zu einer anderen Sitzung gehören oder Player-Modus sein.
- Die UI bildet `table_context_required` auf genau die berichtete Aufforderung ab, über den Kampagnen-Hub erneut Platz zu nehmen. `play-ui.js:_prepareTableSeat` verarbeitet den ausdrücklichen Sitzplatz erst auf der nachfolgenden Tischseite.
- Es gibt daneben den kampagnenqualifizierten `campaigns/routes.py:start_session` mit `scheduled`/`in_progress`-Vertrag; der Legacy-Endpunkt ruft `GameSession.start()` auf. Diese Start-/Statusverträge sind nicht ohne Prüfung austauschbar. Der geprüfte Kampagnen-Start verlangt nicht ausdrücklich eine Mindestspielerzahl oder Karte.

Das ist ein **starker statischer Verdacht auf eine Eintrittsschleife**, kein in dieser Aufgabe aufgezeichneter HTTP-/Browserbeweis. Apply muss zuerst tatsächliche URL, Antwortcode/Fehler, Sessionstatus und Kontextzustand erfassen. Keinen Guard entfernen oder bei fehlendem Kontext allein anhand von Kampagneneigentum DM-Rechte geben.

Kleinste aussagekräftige Reproduktion: neue eigene Kampagne ohne weitere Mitspieler, ohne Karte/Termin, frisch angemeldeter Hub ohne Tischkontext → Sitzung erstellen/starten → ausdrücklich als DM eintreten. Danach Gegenproben mit vorhandenem Player-Kontext und einem Kontext einer anderen Sitzung. Variieren: bestehende/neue Kampagne; 0/1 weitere Mitglieder; 0/1 Karten; mit/ohne Termin; `scheduled`/bereits `in_progress`; Reload, interner Wechsel und Zurück. Brave wie im Bericht und ein Vergleichsbrowser; erfolgreicher Mobilfall als Gegenprobe.

Abnahme für den späteren Korrekturschnitt: autorisierter DM erreicht auch allein den Tisch; geplante und laufende Sitzung haben eindeutige Aktionen; Doppelklick erzeugt keinen unbeabsichtigten zweiten Start/Datensatz; Fehler zeigen die echte Ursache. Player, Owner im Player-Platz und fremde Benutzer erhalten weiterhin keine DM-Rechte/-Daten. Kontext, Bootstrap, HTTP und Socket bleiben konsistent. Isolierte Testdaten verwenden.

Die [letzte Playtable-Abnahme](DADM_MONITOR_CANVAS_SCENES_2026-11-23.md) deckt vier erfolgreiche DM-/Player-Reisen mit zwei QA-Benutzern und vorbereiteten Karten/Sitzungen ab. Sie belegt den frischen Leer-Kampagnen-Start nicht und widerlegt diesen Bericht deshalb nicht.

## N26: bestätigte Sprachvorgabe und technische Lücke

Die letzte ausdrückliche Einigung bei **36:29–37:11** ist maßgeblich:

| Website-Oberfläche | Regelsprache | Website-Navigation | Charakterersteller und Charaktereditor |
| --- | --- | --- | --- |
| DE | DE | DE | durchgehend DE |
| DE | EN | DE | durchgehend EN |
| EN | DE | EN | durchgehend DE |
| EN | EN | EN | durchgehend EN |
| DE/EN | automatisch | gewählte Oberflächensprache | folgt der Oberflächensprache |

Modul umfasst Feldnamen, Hilfetexte, Prüfmeldungen, Auswahlnamen, Methoden, Klassendetails und Regeltext. Eigene Charakter-/Weltnamen und freie Benutzertexte bleiben Benutzerdaten. Die bestehende Trennung von Oberflächen- und Regelsprache bleibt erhalten.

Codebelege: `srd-creator.js` setzt `COMP` fest auf `/api/rulesets/srd-5.2.1-de/compendium`; Initialisierung lädt `/api/srd-creator/creator-data` ohne Sprachparameter. `vtt/characters/srd_creator.py:creator_data` ruft den sprachlosen `load_creator_data()` auf; dieser lädt in `creator_rules.py` aus festem `PACKAGE_DIR = ... / "srd-5.2.1-de"`. Im geprüften Bestand gibt es keine englische generierte `creator-data.json`. Gleichzeitig werden viele Modulbezeichnungen über den globalen `VTTUi`-Pfad übersetzt, während Regeldatennamen aus der DE-Datei stammen. Das erklärt die unterschiedlichen Sprachquellen.

`display-preferences.js` stellt mit `contentLanguage` und `contentLocale()` bereits die unabhängige Regelsprachwahl bereit. Ob bzw. wie englische Creator-Anzeigedaten daraus gewonnen werden, ist eine Apply-Entscheidung; weder eine zweite Mechanikengine noch ein vollständiger EN-Creator ist hier nachgewiesen. Ein funktionierendes englisches Compendium beweist nicht, dass sämtliche maschinenlesbaren Creator-Daten bereits englisch vorliegen.

Abnahme: vier explizite Sprachkombinationen plus „automatisch“, Reload und erneutes Öffnen bestehender Entwürfe; Klassen-/Herkunftsnamen, Weisheit/Wisdom, einfache Waffen/Simple Weapons, Methoden, Talente, Zauber und Invocation-Auswahl samt Detailansicht prüfen. Derselbe Entwurf behält kanonische IDs, Auswahlen und abgeleitete Regelwerte beim Sprachwechsel. Regeln, Quellenreferenzen, eigenes Material und Berechtigungen dürfen nicht durch eine Anzeigeübersetzung umgedeutet werden. Character-Editor-Einstieg zusätzlich prüfen; die Aufnahme zeigt vor allem den Ersteller und beweist noch nicht jeden Sheet-Pfad.

## Erweiterung der vorhandenen Arbeitspakete

Die ursprünglichen sechs M-Pakete bleiben die vollständige Übergabe für E01–E27. Für ein gemeinsames Backlog werden neue Beobachtungen angehängt und vorhandene Tickets vertieft:

| Nächster Umfang | Enthaltene Beobachtungen | Abhängigkeit / Grenze |
| --- | --- | --- |
| T1 Sitzungseinstieg | N18 | Vor Komfortarbeit untersuchen; Start-/Status- und Rollenvertrag zusammen prüfen. |
| T2 Gemeinsame Navigation und stabile Seiten | N19–N21 | Reproduktionswege vor Layoutfix; aktueller Bereich bleibt bei geschlossenem Menü sichtbar. |
| T3 Charaktermodul: Sprache | N26 | Bestätigte Produktvorgabe; Anzeigedaten, UI-Katalog und Entwurfs-/Regelidentität müssen zusammenpassen. |
| T4 Charaktermodul: Darstellung | N22–N25 | Palette und Klassentext zuerst; Inhaltsausbau separat von Darstellungsfehlern. |
| M2 ergänzen: Kartenplatzierung/Raster | N01, N03–N07, N09, N10, N16 | Raster-/Dokumentänderungen brauchen eigenen Apply-Vertrag; kompakte Bedienkorrekturen nicht daran koppeln. |
| M1/M3 ergänzen: Bildpinsel und Beschriftung | N02, N12–N15 | Bestehende Originalfarben, Rotation und Fontwahl bewahren; Ghost-Vorschau und Modusverständnis vor neuer Textgeometrie. |
| M4/M5 vertiefen | N08, N17 | Zuerst E26 und Picker-Datenquelle, anschließend belegte Motivlücken; keine doppelten Filtertickets. |
| T5 Atlas/Welt-Kampagnen-Ablauf | N11 | Vorhandene Brücke als Ist-Basis; Beziehungen/Rechte/Mehrkampagnenumfang getrennt entwerfen. |

Empfohlene Reihenfolge nach Aufnahme des neuen Reviews: **T1**, dann T2/T3 als klar getrennte Korrekturschnitte; ursprüngliche M1a/M4a bleiben der kleinste eigenständige Editor-Start. Bei Rasterarbeit N03/N05/N06 vor weiteren Fangpunkten oder Rotation klären. Vorschau/Bedienbarkeit vor Textkrümmung, verifizierter Katalog vor zusätzlichen Assets. Das ist eine Priorisierung für Apply, keine Umsetzung oder zusammengefasste Großfreigabe.

## Inventar, Abhängigkeiten und passende Nachweise

| Bereich | Verifizierte Code-Einstiege | Vorhandene Prüfeinstiege; in dieser Aufgabe nicht ausgeführt |
| --- | --- | --- |
| Hub → Start → Tischplatz | `vtt/static/js/book-scene.js`, `auth.js`, `play-ui.js`; `vtt/endpoints/sessions.py`, `vtt/campaigns/routes.py`, `vtt/play/contexts.py` | `tests/test_session_prep_surface_before_table.py`, `test_campaign_hub_session_prep_productization.py`, `test_table_contexts.py`, `test_table_contexts_browser.py` |
| Hauptnavigation, Route, Seitenaufbau | `vtt/static/js/vtt-main-nav.js`, `book-scene.js`, `book-shell.js`, `book-routes.js` | `tests/test_c01_navigation_browser.py`, `test_creation_engine_navigation.py`, `test_dashboard_social_hub_guild_navigation.py` |
| Kachel-/Stempel-/Labelbedienung | `vtt/static/mapmaker/js/app.js`, `ui.js`, `tools.js`, `render.js`, `document.js`; `vtt/mapmaker_document.py` | `tests/test_mapmaker_browser.py`, `test_mapmaker_tiles_server.py`, `test_review_maps_browser.py` |
| Atlas-Brücke | `vtt/static/mapmaker/js/atlas-bridge.js`; `vtt/atlas.py`, `vtt/atlas_domain.py` | `tests/test_atlas.py`, `test_atlas_browser.py` |
| Charakterdaten und Sprache | `vtt/static/js/srd-creator.js`, `srd-creator-steps.js`, `display-preferences.js`; `vtt/characters/srd_creator.py`, `vtt/rules_content/creator_rules.py`, `creator_data.py` | `tests/test_srd_creator_api.py`, `test_srd_creator_browser.py`, `test_regelwerk_creator_data.py`, `test_regelwerk_creator_rules.py` |
| Charakterdarstellung | `vtt/templates/srd-creator.html`, `vtt/static/css/srd-creator.css`; Detail-Renderer in `srd-creator.js` | Gezielt Browserdarstellung für DE/EN, Nacht/Pergament, Standard/Bronze/Petrol und schmale/breite Ansicht prüfen. |

Kurze Dateinamen innerhalb einer Tabellenzelle liegen im zuvor genannten Verzeichnis. Bei späteren Änderungen den tatsächlich geladenen Client und Live-Stand prüfen; Tests mit statischen Stringannahmen ersetzen keine Browser-/Rollenabnahme. Normale Einstiege bleiben Hub → Sitzung, Karteneditor → Werkzeug, Einstellungen → Regelsprache und Charakterübersicht → Ersteller/Editor. Keine nicht verlinkte Debug-URL als gelieferte Bedienung ausgeben.

## Risiken, offene Entscheidungen und Erhaltungsbedingungen

- **Hoch, funktional:** N18 blockiert den Kernzugang für die berichtete Konstellation. Der Kontextfehler ist statisch plausibel, die konkrete Live-Anfrage noch nicht reproduziert. Rollen-/Kontextschutz muss bei jeder Korrektur erhalten bleiben.
- **Hoch, Datenintegrität:** Rastergröße/-rotation und Textgeometrie können Dokumentvertrag, Positionen, Auswahl, Undo und sämtliche Export-/Atlas-Pfade verändern. Vorhandene Projekte dürfen nicht stillschweigend migriert, gerastert oder umpositioniert werden. Sichtbares Raster, Snapping und Inhaltstransformation getrennt spezifizieren; die Darstellungslösung ist noch nicht gewählt.
- **Mittel, Sprache/Regeln:** feste DE-Daten sind belegt, der vollständige EN-Datenpfad ist offen. Anzeigeübersetzung darf weder Regeln noch Quellenidentität oder gespeicherte IDs verändern. Keine Regelkorrektur allein aus einer unlesbaren Anzeige ableiten.
- **Mittel, Befundqualität:** Layout-/Cache-/Doppelladeursachen sind bislang Hypothesen. Repro mit Pfad, Browser, Viewport und geladenem Stand erforderlich. Vorhandene Palette-Overrides und `has-active` beachten; Codeexistenz beweist keine korrekte Laufzeitdarstellung.
- **Mittel, Umfang:** Welt-/Mehrkampagnenablauf, Assetbeschaffung und zusätzliche Herkunftsinhalte sind keine beiläufigen UI-Fixes. Quellen-/Nutzungsrechte und gewünschter Inhaltsumfang bleiben offen. Die öffentliche KI-Inhaltspolitik aus E25 ist weiterhin nicht entschieden.

Offene Apply-Fragen: präzises Fangpunktmuster aus N04; welches Raster eine freie Platzierung anzeigen soll; positionsstabiles Verhalten bei Rasterwechsel gegenüber bewusster Kartenskalierung; typgerechte gemeinsame Ebenenbedienung; Umfang der Textkurve und freien Laufweite; Welt-/Orts-/Kampagnenrelationen; Quelle der EN-Anzeigedaten. Diese Fragen blockieren nicht die getrennte Reproduktion des Sitzungseinstiegs oder der klaren Filter-/Bedienfehler.

Als positiv bestätigt erhalten: direkte Kachelplatzierung (00:21), unabhängig einstellbare Symbol-/Textgröße (14:55–15:08), verbesserte nummerierte auswählbare Würfe „Wurf 1 / Wurf 2“ (30:39–31:11), verbesserte Listen und englisches Compendium (33:40, 38:05–38:52). Dazu gelten die bisherigen Playtable-Erhaltungsbedingungen: getrennte DM-/Player-Oberflächen, Nachtpalette, frei platzierbare Fenster, lesbare Szenen und freie Kamera über die Kartenränder mit FIT.

## Abschluss und nächster Schritt

Artefakte: dieses Discover und das Claude-Übergabepapier permanent im Repository; Rohanhänge bleiben unverändert. Prüfung dieser Aufgabe: beide Quellen gelesen, statischer Abgleich der genannten Pfade, Herkunft/Prüfsumme, Index-/Paketabdeckung und Dokumentlinks geprüft. Keine neuen Browserreisen, Regeltests oder funktionalen Korrekturen ausgeführt; kein App-Deploy erforderlich. Keine Agents oder Claude-Aufrufe gestartet.

Nächster Schritt: getrenntes Apply für **T1/N18**, zuerst eine frische Hub-Sitzung ohne vorhandenen Tischkontext reproduzieren und Start-/Kontextreihenfolge belegen. Anschließend den begrenzten Korrekturvertrag mit unveränderten Rollenrechten festhalten. Für die ursprünglichen 27 Punkte ist das [Claude-Übergabepapier](CLAUDE_HANDOFF_MAPMAKER_27_2026-11-23.md) direkt verwendbar; neue N-Punkte werden nur im ausdrücklich aufgenommenen Schnitt ergänzt.
