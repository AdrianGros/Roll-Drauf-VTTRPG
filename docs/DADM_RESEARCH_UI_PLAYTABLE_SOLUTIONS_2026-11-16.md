# VTT UI und Playtable: orchestrierte Lösungsrecherche

**Datum:** 16.11.2026. **Phase:** Discover / Lösungsvergleich. **Profil:** standard.
**Status:** Claude- und Codex-Recherche abgeschlossen und zusammengeführt; begrenzte Apply-Kandidaten liegen vor. Keine Implementierung.
**Aufbewahrung:** dauerhaft. **Umfang:** alle 14 Pakete der
[Feedbackaufnahme](DADM_DISCOVER_UI_PLAYTABLE_FEEDBACK_2026-11-16.md).
Der Owner hat die Delegation an Claude und den Start der Lösungsrecherche autorisiert.
Dieser Bericht entscheidet noch keine Architektur und erteilt keinen Deploy-Handoff.

## Tatsächliche Orchestrierung und Quellbasis

| Ausführender | Begrenzter Auftrag | Rückgabe |
| --- | --- | --- |
| Claude Code, tatsächlicher CLI-Lauf im vorhandenen Abo | U01/U05/U06: Book-UI, Farben, Beschriftung; U09/U10/U11: Measurement/Grid/Select-Pan; U12 Bibliothek zuerst; U14 Seitenhierarchie | [Vollständiger Claude-Teilbericht](proofs/ui-playtable-solutions-2026-11-16/claude-research.md). |
| Codex | U02 Altchat; U03/U04 englische Inhalte; U07/U08 Licht, Sicht und Wände; U13 Initiative; Primärquellen, begrenzte Experimente und Synthese | [Domänenrecherche](proofs/ui-playtable-solutions-2026-11-16/codex-domain-research.md). |

Keine GPT-Unteragenten, keine rekursive Delegation. Claude erhält nur
Read/Grep/Glob/WebSearch/WebFetch; keine Schreib-, Shell-, MCP-, Git- oder Deploymentwerkzeuge.
Die CLI läuft über `claude.ai`, First Party, Pro; API-/Provider-Overrides sind nicht
vorhanden und Extra Usage war vor Start deaktiviert. Der Verbindungscheck war erfolgreich;
der erste Kontingentabruf wurde nach Tokenauffrischung erfolgreich wiederholt.
Vor dem Recherchelauf: 0 % im Fünfstundenfenster, 7 % im Wochenfenster.
Eine Werkzeugbeschränkung ist keine Behauptung einer Host-Sandbox.
[Aufteilung](proofs/ui-playtable-solutions-2026-11-16/orchestration.json),
[Laufnachweis](proofs/ui-playtable-solutions-2026-11-16/claude-research-run.json).


Claude hat den Auftrag erfolgreich abgeschlossen (CLI-Exit 0, kein Fehlerstatus).
Sein Originalbericht bleibt unverändert. Die
[Koordinationsprüfung](proofs/ui-playtable-solutions-2026-11-16/synthesis-review.md)
hält Quellenabgleich, Ergänzungen und Korrekturen fest; insbesondere sind seine
ursprünglich offenen Palettenwerte durch die zusätzliche Recherche unten ergänzt.
Modelle laut CLI-Laufmetadaten: `claude-opus-5-5` und `claude-haiku-5-5`;
keine explizite Modellauswahl oder Provider-Ausweichlösung wurde angefordert.

Untersucht wird der neuere Arbeitsbaum
`/home/admin/projects/roll-drauf-vtt-session-feedback-20261116`, HEAD
`3939766e72a2cd72bc7e69fb0382c9fc96d2edba`, Anwendungscommit
`d4ff7e4fe2ef77a4a36ca41fa205ef5db2ad5b02`. Die laufende Image-ID bleibt
`sha256:7d8f4a54b36b125611ac116b37d10c09632dbea9a920c8c5b0413ea63efd4617`.
Die Feedbackaufnahme enthält den 30-Dateien-Abgleich. Der ursprüngliche Checkout
ist weiterhin dirty; daraus werden keine älteren Funktionsstände übernommen.

## Neue konkrete Befunde

### Farbpalette mit passenden Originalangaben gefunden

Der Herausgeber von [Edo Purple & Mouse Grey](https://colorcombinations.org/palettes/edo-murasaki-nezumi/)
veröffentlicht exakt die vier im Protokoll genannten Farben:

| Owner-Bezeichnung | Bezeichnung der Quelle | Hexwert der Quelle |
| --- | --- | --- |
| Edo Purple | Edo-murasaki | `#5E4A8C` |
| Mouse Gray | Nezumi | `#8A8A8A` |
| Ink Black | Sumi | `#1C1C1C` |
| Natural | Kinari | `#F8F4E9` |

Die Übereinstimmung macht die Seite zu einem sehr passenden Quellenkandidaten;
dass genau diese Website im Gespräch offen war, bleibt eine Schlussfolgerung.
Es ist eine eigene redaktionelle Palette dieses Herausgebers, keine historische
Wada-Tafel. Die Farbwerte sind damit belegt, ihre semantische Zuordnung im VTT noch offen.

Die eigene sRGB-/WCAG-Rechnung ergibt folgende Kontraste:

| Paar | Verhältnis | Eignung für normalen Text bei AA |
| --- | --- | --- |
| Natural ↔ Ink Black | 15,51:1 | geeignet |
| Natural ↔ Edo Purple | 6,74:1 | geeignet |
| Mouse Gray ↔ Ink Black | 4,94:1 | geeignet |
| Natural ↔ Mouse Gray | 3,14:1 | für normalen Text nicht ausreichend |
| Edo Purple ↔ Ink Black | 2,30:1 | nicht ausreichend |
| Edo Purple ↔ Mouse Gray | 2,15:1 | nicht ausreichend |

Normale Texte benötigen nach dem herangezogenen AA-Kriterium 4,5:1; wichtige
nichttextliche Erkennungsmerkmale 3:1 gegen angrenzende Farben. Purple auf Schwarz
braucht deshalb etwa zusätzliche kontrastierende Kennzeichnung, wenn es ein
wichtiges Bedienelement markiert. Diese Rechnung betrifft opake Farbpaare,
noch keine gemessenen echten Seiten mit Transparenz oder Verläufen.
[W3C Textkontrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html),
[W3C Nichttextkontrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast),
[Rechenbeleg](proofs/ui-playtable-solutions-2026-11-16/palette-contrast.json).

### Licht braucht getrennte fachliche und visuelle Arbeit

Im bestehenden Geometriemodul stoppt die Sichtsperre einer Wand die Tokenstrahlen;
die separate Lichtsperre verändert die Berechnung noch nicht. Eine neu ausgeführte
reine Geometrieprobe belegt das mit identischen Wänden und veränderter `light`-Eigenschaft.
Die kleine synthetische Laufzeitprobe zeigt zudem steigende Kosten mit mehr
Lichtquellen; sie ist kein Browser-/Produktionsbenchmark.
[Geometrieprobe](proofs/ui-playtable-solutions-2026-11-16/geometry-probes.json).

Für Apply sind ein erweiterter Zellansatz und Licht-/Sichtpolygone zu vergleichen.
SVG-Maske und Canvas-Compositing sind mögliche Darstellungen; ein neuer GPU-Pfad
ist ein wesentlich größerer separater Kandidat. Eine schöne Maske ersetzt keine
korrekte serverseitige Playerprojektion. DM-Vorschau und echter Player-Kontext
müssen unterscheidbar bleiben. Die technische Machbarkeit der Masken ist dokumentiert,
die Leistung hier noch nicht gemessen.
[MDN SVG mask](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/mask),
[MDN Canvas-Compositing](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/globalCompositeOperation).

### Chat, Initiative und englische Inhalte haben bereits nutzbare Grundlagen

Altchat und neuer Kampagnenchat liegen in verschiedenen Tabellen mit verschiedenen
Metadaten. Der erste Prüfkandidat ist ein autorisierter historischer Leseweg;
ein Import braucht einen eigenen Datenvertrag. Ein globaler Cursor darf unabhängige
Tabellen-IDs nicht als gemeinsame Reihenfolge behandeln.

Initiative wird bereits aus internen und externen Quellen übernommen. Neu zu
entwerfen sind echte Wurfkandidaten, DM-Bestätigung und ihre Abgrenzung zu bloßen
Wiederzustellungen. Der zusätzliche Beyond20-`update-combat`-Weg und direkte
Tokenänderungen gehören in dieselbe Prüfung. Der gemeldete Combatfehler ist noch
nicht reproduziert. Die externe API unterscheidet Initiative und Turn-Tracker-Updates
bereits ausdrücklich. [Beyond20-API](https://beyond20.here-for-more.info/api).

Das vorhandene englische PDF stimmt bytegenau mit dem offiziellen SRD-5.2.1-Download
überein. Es fehlt der strukturierte englische Inhalt im eigenen Stil samt Sprachzuordnung;
auch die bisher deutschgebundenen Compendium-Extraktoren sind betroffen.
Prüfkandidat ist ein versioniertes EN-Paket auf der vorhandenen Pipeline, zunächst
mit einem repräsentativen Inhaltsdurchstich. Keine neuen Regeltexte wurden erzeugt.
[Wizards: SRD](https://www.dndbeyond.com/srd),
[Download-/Hashbeleg](proofs/ui-playtable-solutions-2026-11-16/english-source.json).

### Zusätzliche UI-Befunde aus Claudes Recherche, von Codex gegengeprüft

- **Book-UI:** Eine gemeinsame Dokument-Buchschale nach vorhandenem Muster ist
  ein passender Prüfkandidat. Die große `BookScene`-Laufzeit ersetzt Routeninhalt;
  ihre Erweiterung um alle Editoren hätte andere Lebenszyklusrisiken. Eagle-Fenster
  liegen außerhalb der Hauptseite und brauchen weiter eigenen erreichbaren Platz.
- **Pink/Night:** `display-preferences.js` setzt den Night-Standardakzent auf
  `#f29a90`; CSS allein würde diesen dynamischen Akzent nicht vollständig ersetzen.
- **Grid:** `btnMeasureSnap` heißt auf Englisch „Grid“ und schaltet Einrasten,
  ohne ein Parameterfenster zu öffnen. Dass der Call genau diesen Einstieg meinte,
  ist eine plausible, noch nicht im Browser bestätigte Zuordnung.
- **Measurement:** Snap verändert derzeit zugleich die Diagonalregel. Die 12px-
  Beschriftung liegt innerhalb der skalierten Kartenebene. Lesbare Bildschirmgröße,
  Punktsnap und Messregel sind daher ausdrücklich getrennt zu betrachten.
- **Token:** Der Abbruch leert `pendingTokenTemplate` nicht. Das ist eine bestätigte
  Zustandslücke im Code; eine konkrete Folgefehlplatzierung ist noch nicht reproduziert.
- **Hierarchie:** `SceneStack` ist sessiongebunden; reine Gruppen ohne Karte gibt es
  im aktuellen nicht-nullbaren Kartenbezug noch nicht. Kampagnenweite Dauerhaftigkeit,
  Karten-Eltern und reine Ordner sind unterschiedliche zu klärende Verträge.

Die Seitenliste enthält derzeit interaktive Elemente in Listbox-Optionen. Für
hierarchische Bedienung sollten Navigation und Aktionen bewusst getrennt oder
als geeignetes interaktives Muster entworfen werden. W3C beschreibt die Grenzen
von Listbox und die unterschiedlichen Baum-/Treegrid-Interaktionen ausdrücklich.
[W3C Listbox](https://www.w3.org/WAI/ARIA/apg/patterns/listbox/),
[Tree View](https://www.w3.org/WAI/ARIA/apg/patterns/treeview/),
[Treegrid](https://www.w3.org/WAI/ARIA/apg/patterns/treegrid/).

**Präzisierung zum Grid-Vertrag:** Ein neuer Tischendpunkt ist eine Option.
Der vorhandene Kampagnenweg berücksichtigt über `_is_dm`/`restrict_campaign_role`
und den HTTP-Guard bereits getragene Player-Kontexte. Ein bestehender Bypass wurde
hier nicht bewiesen. Apply muss unabhängig von der Routenwahl autorisierte
Tischrechte, Versionierung und die Aktualisierung anderer Clients festlegen.

## Vollständiger Lösungsraum und nächste begrenzte Apply-Pakete

Die Favoriten sind Kandidaten für den nächsten Entwurf. Die endgültige Wahl
setzt voraus, dass die jeweiligen Medium-Risiken und Produktfragen bearbeitet sind.

| Paket | Zu vergleichende Lösungswege | Nächste begrenzte Klärung |
| --- | --- | --- |
| U01 Book-UI | gemeinsame Dokument-Buchschale mit bestehendem Lebenszyklus; Erweiterung von BookScene; CSS-/Ribbon-Angleichung als Vorstufe | Editor-/Canvasbreite, Dialoge, Lebenszyklus und Deep Links je Oberfläche inventarisieren; CSS allein belegt keine gemeinsame Buchkomposition. |
| U02 Altchat | historische Leseprojektion; kontrollierter Import in erweitertes Verlaufsmodell | Welche Sessions/Typen, welche Rollen, welche Gesamtpagination? Private und verdeckte Inhalte schützen. |
| U03 englisches Compendium | versioniertes EN-Paket; sprachneutrale Strukturdaten mit Sprachschichten | Datenquelle, Such-/Filterfelder, IDs/Pins, Generator und Cache sprachbewusst klären. |
| U04 englisches SRD | redaktionelle EN-Fassung auf belegter Quelle; gemeinsames mehrsprachiges Inhaltsmodell | Umfang, Terminologie, mechanische Gleichheit, Querverweise und Attribution abnehmen. |
| U05 Farbwelt | bestehende semantische Tokens umstellen; größere Vereinheitlichung der Stylesysteme | Obige Palette und tatsächliche Kontrastpaare je Oberfläche prüfen; Kartenbilder nicht automatisch umfärben. |
| U06 Sicht/Licht | eindeutige Funktionsnamen plus Tooltip; getrennte Vorschau-/Markierungsaktionen | „Side“ aus dem Transkript nicht als verbindlichen neuen Namen behandeln. |
| U07 Licht | erweiterte Licht-Raycast-Zellen; Sicht-/Lichtpolygone mit Maske; größerer GPU-Pfad | Sicht-/Lichtsemantik und Referenzszenen vor Rendererentscheidung. |
| U08 Wände | bestehendes Popover besser erreichbar machen; Wandliste/Untermenü als zusätzlicher Einstieg | CRUD wiederverwenden, Sicht und Licht getrennt abnehmen, Auswahl bei Kartenwechsel bereinigen. |
| U09 Measurement | freie Cursorposition mit optionalem Snap; getrennte Regeln je Form | Koordinatentransformation, Radius-/Cursorlabel, alle Ziehrichtungen, Zoom und Einheiten prüfen. |
| U10 Grid | echtes Kartenparameter-Menü; reine lokale Einblendung separat anbieten | Snap-Label von Parametern trennen; Größe/Anzeige/Ausrichtung gegenüber Meterkalibrierung und gespeicherten Fogzellen abgrenzen. |
| U11 Select/Pan | getrennte Werkzeuge mit temporärer Pan-Geste; dauerhafter Modusschalter | Pan-Annahme bestätigen; Maus, Tastatur, Touch und versehentliche Tokenbewegung prüfen. |
| U12 Tokenbibliothek zuerst | Bibliotheksauswahl → bewusster Zielklick; automatisch gewählte Zielposition | Bestehende Vorlagen und Serverprüfung erhalten; leere Bibliothek, neues Token und Abbruch definieren. |
| U13 Initiative | Erstwurf automatisch, Rerolls zur DM-Auswahl; alle Würfe zunächst vormerken | Erstwurf, Gleichzeitigkeit, Replay, Encountergrenze, NPCs und verbleibende Legacywege festlegen. |
| U14 Seitenhierarchie | Baum; gruppierte Liste; Breadcrumb-Navigation | Zuerst Session-/Kampagnenpersistenz und Ordner/Karten-Eltern; dann Sicht/Löschen, aktive Seite und Umhängen ohne Drag. |

## Risiken und Apply-Reihenfolge

**Mittel:** historische Zugriffsgrenzen (U02); getrennte Rollen und Sichtdaten
bei Lichtvorschau (U07/U08); Leistungsbudget und Geometrieparität (U07);
Bestätigungsrennen/Legacywege (U13); redaktionelle Qualität und Pins (U03/U04);
Editorlebenszyklus bei Book-UI (U01); Hierarchie-/Sicht-/Löschregeln (U14).
Kein Risiko wird durch diese Recherche pauschal akzeptiert.

Empfohlene Reihenfolge für begrenzte Entwürfe:

1. Farbwelt und Book-UI-Grenze U05/U01/U06. Gleichzeitig die gemeldeten Fehler
   bei Combat, Grid und Quadrat an konkreten Reisen eingrenzen.
2. Bibliothek-zuerst und Mess-/Werkzeugabläufe U12/U09/U10/U11 mit den bestehenden APIs.
3. Altchat U02 und Initiative U13 als getrennte Daten-/Fachverträge.
4. Licht/Wände U07/U08: Referenzszenen, Berechnungs-/Rendervergleich und echte Playergrenze.
5. Englisches SRD/Compendium U03/U04: repräsentativer strukturierter Durchstich,
   danach vollständiges redaktionelles Paket.
6. Seitenhierarchie U14 mit expliziten Eltern-, Sicht- und Löschregeln.

Dies ist eine Lieferreihenfolge zur Prüfung, keine vorgeschriebene Abhängigkeit
aller Pakete voneinander. Delay bleibt unverändert; der Character Importer ist
kein zusätzlicher Auftrag. Getrennte Player-/DM-Komposition und serverautorisierte
Kontexte einschließlich Owner-as-Player bleiben verbindlich.

## Verifikation und Evidenzgrenzen

Neu ausgeführt: tatsächliche Claude-Delegation, lokale Quellprüfung,
Primärquellenrecherche, sechs Kontrastpaar-Berechnungen, isolierter Geometrievergleich
mit drei kleinen synthetischen Laufzeitfällen sowie Hashvergleich des englischen PDFs.
[Quellenregister](proofs/ui-playtable-solutions-2026-11-16/source-register.json),
[Dokumentations-/Evidenzcheck](proofs/ui-playtable-solutions-2026-11-16/documentation-checks.json).
Nicht ausgeführt: angemeldete Browserreproduktion, echte Beyond20-Erweiterung,
produktive Chat-/Kampfdatenabfrage, neue Renderprototypen, Anwendungs-Testsuite,
Migration, Produktcodeänderungen, Commit/Push oder Deployment.

Nächster Schritt: je gewähltem Paket ein Apply-Vertrag
mit konkreter Nutzerreise, Rollen, akzeptierten Risiken, Interfaces und gezielten
Abnahmekriterien. Erst dessen expliziter Deploy-Handoff führt zur Implementierung;
die spätere Lieferung folgt der bestehenden Live-Regel einschließlich Commit,
Image-/Compose-Abgleich, normalem UI-Einstieg, Rollenprüfung und Rollback.
