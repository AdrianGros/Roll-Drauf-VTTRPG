# Apply: drei Bedienkonzepte für den DM-Playtable

Status: drei Research-Entwürfe zur Präsentation; keine Freigabe oder Umsetzung einer neuen Produktionsoberfläche. Grundlage: [Discover und Inventar](DADM_DISCOVER_PLAYTABLE_UX_2026-11-22.md), [drei Studien und vier Fachartikel](DADM_RESEARCH_PLAYTABLE_UX_2026-11-22.md). Begonnen am 22.11., Konzeptstand 23.11.2026. Die Empfehlung ist eine zu testende Designhypothese.

## Ziel und gemeinsamer Vertrag

Der DM soll erkennen können, **was er gerade tut**, **welches Fenster offen ist**, **welche Figur betroffen ist** und **wo eine weitere Funktion zu finden ist**. Alle drei Alternativen erhalten die vorhandenen Fähigkeiten. Die wiederkehrende Anatomie ist gleich: eine Iconfamilie, sichtbarer kurzer Name, gleiche Typografie, gleiche Abstände, einheitliche Zustände. Kein Nebeneinander von Emoji-Buttons, reinen Textnachrüstungen und individuell gestalteten Sonderfällen.

Einheitlichkeit bedeutet gemeinsame Bausteine, nicht identische Bedeutung: ein aktives Werkzeug hat einen gedrückten Zustand; ein Fensteröffner einen offenen Zustand; ein Schalter zeigt ein/aus; reine Information sieht nicht wie eine ausführbare Aktion aus. Destruktive Sitzungsaktionen bleiben bewusst erkennbar und bestätigt. „Verlassen“ ist Navigation, „Sitzung beenden“ eine Zustandsänderung.

Vorgeschlagene, zunächst zu prüfende Maße: Dockhöhe je Button 52 Pixel, Icon 20 Pixel, sichtbarer Name 12 Pixel, Touchziel mindestens 44 × 44. Für dieselbe Familie gelten identische Maße; kompakte Fensterrahmen bleiben eine eigene konsistente Familie. Alle Flächen, Felder, Selects, Beschreibungen und Menüs verwenden die vorhandenen Palette-Rollen. Nacht: Ink, Natural und Edo; Edo als gefüllter aktiver Zustand mit hellem Text, nicht als dunkle Schrift auf Ink. Kein neues Farbsystem pro Feature.

## Draft „Werkzeuggruppen“

**Prinzip:** die heutige freie Tischfläche und ihre Fenster erhalten, das untere Band aber nach Bedienart gliedern.

- **Werkzeug wählen:** Auswählen, Bewegen, Messen. Wand- und Lichtplatzierung sind weiterhin Werkzeuge, werden aber aus dem benannten Kartenbereich aktiviert; der aktuelle Modus bleibt im Status sichtbar und mit Escape beendbar.
- **Tischfenster öffnen:** Szenen, Figuren, Initiative, Karte & Sicht. Darunter liegen die spezialisierten Funktionen mit klaren Namen. Etagen stehen beispielsweise unter Karte & Sicht → Etagen und Balkonsicht; Initiative enthält die Kampfsteuerung.
- **Kommunikation und Weitere:** Chat, Würfeln, Mehr. Mehr führt zu Journal/Materialien, Beyond20, vollständiger Befehlsübersicht und Tischverwaltung. Navigation zur Kampagne heißt ausdrücklich Tisch verlassen.

Das sind im gezeigten Desktopstart zehn dauerhaft sichtbare Zugänge statt 16 ungegliederter Buttons. Das ist eine Zählung des Entwurfs, kein nachgewiesener Effizienzgewinn. Der Maßstab ist nicht möglichst wenig Klicks um jeden Preis: häufige Werkzeuge bleiben direkt, komplexe Kartenoptionen erhalten einen benannten Ort. Initiative bleibt direkt sichtbar und heißt in allen drei Entwürfen gleich.

**Vorteil:** geringster konzeptioneller Bruch mit der vorhandenen Oberfläche und den gerade reparierten freien Fenstern. **Nachteil:** einige bislang direkte Befehle benötigen den Karten-/Figurenbereich; deren Auffindbarkeit muss getestet werden. Im Mockup ist exemplarisch ein einheitlich gerahmtes Kartenfenster dargestellt. In einer Umsetzung dürfen weiterhin mehrere Instanzen unterschiedlicher Fenster offen sein; derselbe Inhalt wird nur einmal montiert.

## Draft „Arbeitsbereiche“

**Prinzip:** der DM entscheidet bewusst zwischen Leiten, Kampf und Vorbereiten. Die Hauptwerkzeuge bleiben an festen Positionen; ein gemeinsamer Inspektor stellt die zur gewählten Aufgabe gehörigen Optionen bereit.

- **Leiten:** Szenen, Figuren, Journal und Kommunikation.
- **Kampf:** Initiative/Zugfolge, Figuren und Zustände. Das Mockup zeigt Runde und aktuellen Zug gemeinsam im Inspektor.
- **Vorbereiten:** Szenen, Raster, Sicht, Wände, Licht und Etagen.

Der Wechsel ist eine Navigation innerhalb der DM-Oberfläche. Er startet keinen Kampf, pausiert keine Session und ändert weder Tischplatz noch Berechtigung. Kein automatischer Arbeitsbereichswechsel aufgrund eines Serverereignisses. Die gleiche Funktion heißt in jedem Arbeitsbereich gleich und verwendet denselben Handler.

**Vorteil:** weniger konkurrierende Aufgabengruppen gleichzeitig; zusammengehörige mehrstufige Tätigkeiten bleiben räumlich beieinander. **Nachteil:** ein weiterer Modus muss verstanden werden, und Mischaufgaben verlangen Wechsel. Der feste Inspektor beansprucht Kartenbreite; die zusätzliche Arbeitsbereichsreihe kostet Höhe. Die Zahl sichtbarer Bedienelemente wird deshalb nicht als automatisch geringer oder besser dargestellt. Bei einer Umsetzung wäre ein bewusstes Abdocken des Inspektors vorzusehen, ohne das freie Fensterverhalten anderer Ansichten zu verlieren.

## Draft „Persönliches Dock“

**Prinzip:** drei stabile Grundwerkzeuge plus bewusst gewählte Favoriten; „Alle Werkzeuge“ bleibt immer sichtbar.

Das Startdock enthält exemplarisch Initiative, Licht und Chat als Pins. Es ist sofort benutzbar und startet nicht leer. In der Befehlsübersicht sind Funktionen nach Namen auffindbar; der DM heftet sie ausdrücklich an oder löst sie. Bestehende Begriffe und Suchsynonyme wie Tokens/Figuren oder Seiten/Szenen bleiben berücksichtigt. Ein optionaler Tastaturzugang ergänzt den sichtbaren Öffner.

Es gibt keine unsichtbare Lernlogik, die Reihenfolgen eigenständig verändert. Pins sind Verknüpfungen auf dieselben Befehle, keine Kopien der Implementierung. Funktionen bleiben nach dem Lösen über die vollständige Übersicht erreichbar. Im Mockup lässt sich „Etagen“ suchen und anheften; maximal fünf persönliche Pins halten die untere Reihe begrenzt.

**Vorteil:** unterschiedliche DM-Arbeitsweisen passen in dieselbe Oberfläche, ohne einen generellen „Einfachmodus“ mit Funktionsverlust. **Nachteil:** Personalisierung hat Einrichtungsaufwand; die Qualität der Startbelegung und Suchbegriffe ist besonders wichtig. Die Startpins sind eine Hypothese, keine ausgemessenen häufigsten Befehle. Seltene Aufgaben können zusätzliche Suchschritte benötigen.

## Gemeinsame Zuordnung des bisherigen Menübandes

Die Tabelle ist eine Funktionszuordnung für alle 18 registrierten Positionen; sie löscht keine dieser Fähigkeiten. Originale Texte und Quellen bleiben im [vollständigen Menübandindex](research/playtable-ux-2026-11-22/footer-index.md).

| Originalindex | Bisher | Werkzeuggruppen | Arbeitsbereiche | Persönliches Dock |
|---|---|---|---|---|
| PT-B-001 | Seiten | Szenen | Leiten/Vorbereiten → Szenen | Übersicht → Szenen, optional Pin |
| PT-B-003 | Initiative | Initiative mit Kampfsteuerung | Kampf → Initiative | Startpin Initiative |
| PT-B-005 | Tokens | Figuren | Leiten/Kampf → Figuren | Übersicht → Figuren, optional Pin |
| PT-B-007 | Layers | Figuren → Token-Sichtbarkeit | Figureninspektor → Token-Sichtbarkeit | Übersicht → Token-Sichtbarkeit |
| PT-B-009 | Raster & Licht | Karte & Sicht | Vorbereiten → Karte & Sicht | Übersicht → Karte & Sicht |
| PT-B-010 | Wählen | festes Werkzeug | festes Werkzeug | festes Werkzeug |
| PT-B-014 | Bewegen | festes Werkzeug | festes Werkzeug | festes Werkzeug |
| PT-B-018 | Messen | festes Werkzeug | festes Werkzeug | festes Werkzeug |
| PT-B-022 | Einrasten | Messoptionen, am aktiven Werkzeug | identische Messoptionen | identische Messoptionen |
| PT-B-026 | Wand | Karte & Sicht → Wand zeichnen | Vorbereiten → Wand zeichnen | Übersicht/Pin → Wand zeichnen |
| PT-B-030 | Licht | Karte & Sicht → Licht setzen | Vorbereiten → Licht setzen | exemplarischer Startpin Licht |
| PT-B-034 | Markierungen | Kartenbereich → Markierungen | Vorbereiten → Markierungen | Übersicht → Markierungen |
| PT-B-038 | Tisch | deaktivierter Altöffner bleibt ersetzt | kein Wiederaufbau des Altcontainers | kein Wiederaufbau des Altcontainers |
| PT-B-042 | Chat | direkter Öffner | dauerhaft erreichbar | exemplarischer Startpin Chat |
| PT-B-045 | Würfeln | direkter Öffner | Kommunikation/Übersicht | Übersicht oder selbst angeheftet |
| PT-B-046 | Beyond20 | Mehr → Beyond20 | Mehr → Beyond20 | Übersicht → Beyond20 |
| PT-B-047 | Journal | Mehr → Journal | Leiten → Journal | Übersicht → Journal |
| PT-B-051 | Zurück | Tischmenü; benanntes Tisch verlassen | identisches Tischmenü | identisches Tischmenü |

Neue starke Funktionen bleiben ausdrücklich zugeordnet: PT-W-392 Etagen → Karte & Sicht; PT-W-383 Spielersichtvorschau → Karte & Sicht → Spielerperspektive. Vorschau der Spielersicht und tatsächlicher Wechsel des Tischplatzes sind getrennte Befehle. Kartenetagen und Token-Sichtbarkeit sind verschiedene Ressourcen und erhalten verschiedene Namen. Persönliche Figurenaktionen/Begleiter bleiben am ausgewählten eigenen Charakterkontext oberhalb des Docks; sie werden nicht pauschal in DM-Verwaltung umgedeutet.

## Qualitativer Vergleich und Empfehlung

| Kriterium | Werkzeuggruppen | Arbeitsbereiche | Persönliches Dock |
|---|---|---|---|
| Einstieg ohne Einrichtung | direkt mit gemeinsamer Startanordnung | verständliche Aufgabenwahl nötig | gemeinsame Startpins, danach anpassbar |
| Beständige Position | feste Gruppen | fest innerhalb des bewusst gewählten Bereichs | fest bis zur bewussten Anpassung |
| Kartenfläche | ähnlich dem heutigen freien Fenstermodell | feste Breite/Höhe wird für Inspektor/Navigation verwendet | kompaktes Dock, Übersicht bei Bedarf |
| Seltene Fähigkeiten finden | benannte Fachbereiche und vollständige Übersicht | Fachbereich oder vollständige Übersicht | sichtbare Übersicht mit Suchsynonymen |
| Gefahr | neue Unterwege werden übersehen | Arbeitsbereich wird verwechselt | Funktionen werden zu spät angeheftet/gefunden |
| Eingriff in vorhandene Struktur | begrenzter | größer | zusätzlicher persönlicher Zustand |

**Empfehlung für den ersten Vergleichstest:** Werkzeuggruppen als Ausgangshypothese, weil damit die konkret beobachtete Vermischung mit geringerem Modellwechsel bearbeitet wird. Persönliche Pins sind danach eine plausible freiwillige Ergänzung. Arbeitsbereiche bleiben eine ernsthafte Alternative für vorwiegend vorbereitende oder kampforientierte DMs. Das ist ein fachliches Urteil aus Befund und Evidenz, kein bereits gemessenes Siegergebnis. Keiner der Entwürfe ist durch die drei Studien als Ganzes validiert.

## Vorgeschlagener späterer Implementierungsvertrag

Noch keine Implementierung. Vor einem Deploy wäre ein gemeinsamer, deklarativer Befehlsbestand zu vereinbaren: stabile Befehls-ID; bestehender Handler/Fenster-ID; Rolle/Scope; semantischer Typ; Name, Beschreibung, Icon, Suchsynonyme; Aktiv-/Offen-/Verfügbarkeitszustand; Zugang pro View. Inventar-ID und Befehls-ID sind verschieden: mehrere Labels und Öffner können denselben Befehl referenzieren. Eine neue Ansicht darf nicht zu einem zweiten API-Schreibweg führen.

Die tatsächliche DM-/Player-Komposition bleibt getrennt und serverautorisiert. Ein Owner im Player-Tischplatz erhält keine DM-Elemente. Eine clientseitige Suchliste oder ein Pin ist keine Berechtigungsprüfung. Alle vorhandenen CAS-/Idempotenz-/Privatsphäreverträge bleiben unverändert. Keine neuen Abhängigkeiten oder neuen Inhaltsfunktionen nötig.

Fenster/Inspektoren erhalten eine gemeinsame Hülle: Titel, Schließen, Drag-/Tastaturbewegung im freien Modus, sinnvolle Größen und genau ein Inhalts-Scrollbereich. Fokus, Textauswahl, geöffnete Abschnitte und Entwürfe bleiben beim Aktualisieren erhalten. Aktive Werkzeuge werden nicht durch das Öffnen eines Fensters unbeabsichtigt gewechselt. Escape beendet einen begonnenen Werkzeugvorgang bzw. den obersten lokalen Dialog nach einer definierten Priorität; keine versteckte Sitzungsänderung.

Responsive Regel im Konzept: schmale Ansichten ordnen Bereiche bewusst um und bieten eine beschriftete vollständige Befehlsübersicht. Kritische Auswege liegen nicht ausschließlich rechts außerhalb eines horizontalen Scrollstreifens. Die Mockups umbrechen Gruppen und stellen das Detailpanel unter die Karte; ein späteres Produktionslayout muss die echte Touch-/Bildschirmtastatur und 200%-Textvergrößerung separat prüfen. Tooltipps ergänzen sichtbare Namen, ersetzen sie nicht.

## Vergleich mit echten DM-Aufgaben

Vorgeschlagene formative Studie: zwölf DMs, je sechs mit wenig bzw. viel VTT-Erfahrung. Alle sehen alle drei Entwürfe; die sechs möglichen Reihenfolgen werden je einmal pro Erfahrungsgruppe verwendet. Gleichwertige Szenarien reduzieren Erinnerung an die Lösung. Der aktuelle Tisch dient als nachvollziehbare Referenz. Die Stichprobe dient dem Finden von Problemen und begründet ohne Poweranalyse keine allgemeine statistische Überlegenheit.

Aufgaben: Karte bewegen und mit Einrasten messen; eine geheime Figur sichtbar machen; Initiative finden und zum nächsten Zug gelangen; Rastermaßstab ändern; Balkonetage mit Öffnung finden; Spielersicht prüfen, ohne den Tischplatz zu wechseln; normal würfeln; Beyond20-Hilfe sowie Tisch verlassen finden und von Sitzung beenden unterscheiden. Die ersten Schritte können als Auffindetest im Mockup erfolgen; schreibende Aktionen und echte Rollenfolgen benötigen später isolierte integrierte VTT-Fixtures.

Messen: Aufgabenerfolg, Zeit bis zum korrekten Einstieg, Fehlklicks/Rückwege, Verwechslung von Sichtbarkeit und Zugriff, Kartenverdeckung sowie subjektiver Aufwand und begründete Präferenz. Präferenz und Leistung werden getrennt berichtet. Nach einer echten Spielsitzung ist zu prüfen, ob seltene Funktionen noch gefunden werden. Bisher wurden keine Menschen mit diesen Entwürfen getestet und keine Produktivitätsgewinne gemessen.

Abnahmekriterien für eine spätere Umsetzung: jede bestehende Fähigkeit bleibt für ihre Rolle erreichbar; aktiver Modus und offenes Fenster sind unterscheidbar; alle Kernaufgaben haben einen sichtbaren Einstieg; Tastatur- und Touchwege funktionieren; kein Rollendatenleck; keine Verwechslung von Tisch verlassen/Sitzung beenden oder Spielerperspektive/Tischplatz; Palette und Textkontrast bleiben konsistent; kein neuer Fenster-/Scrollregressionsfehler. Gemessene Nutzungshäufigkeiten dürfen die Startbelegung informieren, jedoch nicht heimlich während einer Sitzung umordnen.

## Mockup-Umfang und nächster Schritt

Die drei lokalen Entwürfe zeigen Menüband, Karte, Figurenkontext und gemeinsame Detailansichten. Werkzeugwahl, Messoptionen, Bereichswechsel, Etagenzugang, Suche/Anheften und Palettenwechsel sind simuliert. Die durchblätterbare Befehlsübersicht enthält einen repräsentativen Ausschnitt, nicht sämtliche Inventareinträge als ausführbare Funktionen. Beispielwürfe und Beispielzüge bleiben lokale Demonstrationen. Fensterdrag, vollständige API-Aktionen, Kartenimport, tatsächlicher Chatversand und Produktionsberechtigungen werden im Mockup nicht nachgebildet. Die Karte ist eine schematische Illustration, keine echte Spielkarte.

Artefakte: [Inline-Mockups](research/playtable-ux-2026-11-22/playtable-varianten.html), [Browserprüfprotokoll](research/playtable-ux-2026-11-22/evidence/mockup-verification.json), vollständiger Index, Quellenreview und Discover. Aufbewahrungsklasse Research/Audit. Nächster Schritt ist die Präsentation und Auswahl eines Ansatzes für einen begrenzten Vergleichstest; ein Produktionsumbau benötigt einen anschließenden ausdrücklichen Umsetzungsauftrag.
