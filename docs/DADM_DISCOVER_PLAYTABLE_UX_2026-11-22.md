# Discover: Inventar und Bewertung der Playtable-Oberfläche

Status: Bestandsaufnahme abgeschlossen, Übergang in den beauftragten Konzeptvergleich. Input: Owner-Auftrag, sämtliche Buttons, Labels und Beschreibungen zu indexieren, Kontrolle/Information und Position zu unterscheiden sowie besonders das DM-Menüband zu vereinheitlichen. Keine Änderungen an `vtt/`, Diensten, Datenbank oder Produktionsoberfläche.

## Erfasster Stand und Methode

Laufende Funktionsquelle `a6abcce9e34b289efb88cb525a0c4c3ae87037e4`, Image `sha256:5726f87c57a3106b3e2337b5761b9449b80f7d8b093810e56aef0cdc682443b3`. Forschungs-Worktree basiert auf dem zugehörigen Dokumentationsstand `9e33bf706`. Die App-Quellen sind identisch; Prüfsummen der untersuchten Dateien stehen im [Inventarsummenbeleg](research/playtable-ux-2026-11-22/inventory-summary.json).

Chromium-Aufnahme des Quellstands mit eigener wegwerfbarer SQLite-Datenbank, ohne externes Netzwerk oder Produktionskonten. 29 Zustände: DM-Grundansicht bei 1440 × 1000, 1024 × 768 und 390 × 844; sämtliche zehn Tischfenster; Sitzungsverwaltung, Tischmenü, Anzeigepräferenzen, Messoptionen, Figurenauswahl, Zustände, Platzierung, Beute, Wand-/Lichteditor, Kartenbibliothek und Etagenkarten; separate Player-Grundansicht, Aktionsbelegung und Begleiterdialog. Die Aufnahme wartet auf abgeschlossenen Bootstrap statt den kurzzeitig unvollständigen Ladezustand zu zählen. [Erfassungsprotokoll](research/playtable-ux-2026-11-22/evidence/capture-coverage.json).

Für wiederholbare Etagenkarten wurden ausschließlich im lokalen Browser synthetische Ansichtsmetadaten an den vorhandenen Renderer gegeben. Sonstige Daten stammen aus der isolierten Fixture. Ein Referenzzugriff auf das bestehende UI-Objekt dient dem gezielten Öffnen vorhandener Fenster, ohne CSS oder Komponenten zu ersetzen. Das ist eine Laboraufnahme des ausgelieferten Quellstands, keine Beobachtung einer echten Spielsitzung und keine Messung tatsächlicher Nutzungshäufigkeiten.

## Index und Abdeckung

Das [CSV-Gesamtinventar](research/playtable-ux-2026-11-22/inventory.csv) und das [JSON mit Geometrie, Darstellungswerten und Quellen](research/playtable-ux-2026-11-22/inventory.json) enthalten **875 DOM-Elementfamilien: 294 Kontrollelemente (K) und 581 Informationselemente (I)**. Weitere **241 indizierte Quelltexttexte** erfassen bedingtes Feedback, Bestätigungen und Beschriftungen, ohne eine beobachtete Bildschirmposition vorzutäuschen. Kein mit fester ID deklariertes Kontrollelement der gemeinsamen HTML-Vorlage oder der DM-Fragmente fehlt in der montierten Erfassung. Das beweist keine vollständige Ausführung aller möglichen dynamischen Zustände.

Jeder Eintrag hat einen eingefrorenen Index, Typ, Text, Rolle, Position/Container, Selektor, Sichtbarkeitszustände und Quellenstellen. Für sichtbare Beobachtungen stehen CSS-Pixelrechteck, Viewport und berechnete Darstellungswerte im JSON. Wiederholbare Zeilen sind Familien, etwa die Steuerung einer Etagenkarte; Namen von Figuren, Nachrichten, Dateien, Regeln und Karten sind variable Inhalte. Ein Label oder Tooltip bekommt einen eigenen I-Index neben seinem K-Kontrollelement. Es werden deshalb weder Funktionen noch gleichzeitig sichtbare Buttons durch die Gesamtzahl beschrieben.

| Präfix | Position |
|---|---|
| PT-B | Unteres Menüband, links nach rechts; Werkzeug- und Fensteröffner |
| PT-H | Obere Sitzungs-/Ansichtsleiste, Rolle, Zustand, Seite, Zoom |
| PT-K | Kartenfläche, Messoptionen und Etagenstatus |
| PT-W | Freies Tischfenster; konkrete Fenster-ID steht in jedem Datensatz |
| PT-D | Dialog oder Popover; konkrete Dialog-ID steht im Datensatz |
| PT-M | Tischmenü, über „Zurück“ geöffnet |
| PT-T | Schwebende Tokenauswahl oder Platzierung |
| PT-P / PT-A | Persönliche bzw. generische Aktionsleiste oberhalb des Docks |
| PT-S | Charakterbogen-Lade, Rahmen und Öffner |
| PT-N / PT-R | Rahmennavigation, sonstiger Rahmen oder inaktiver Altcontainer |
| PT-Q | Nur im Quelltext nachgewiesene bedingte Texte; Position noch nicht beobachtet |

Scope: Playtable samt eigener Bedienfenster, Menüs, Formularen, Feedback und Einstiegspunkten. Die vollständigen Inhalte eingebetteter Unteranwendungen — Charakterbogen und Beyond20-Anleitung — sind eigene Oberflächen; deren Rahmen, Öffner und Links sind hier erfasst. Keine Behauptung, jede beliebige Kombination aus Regeln, Benutzerdaten und Fehlern vollständig im Browser ausgelöst zu haben. Sichtbarkeit „nicht beobachtet“ wird nicht als „entfernte Funktion“ interpretiert. Der Index wird bei Erweiterung ergänzt und nicht neu nummeriert.

## Menüband: konkreter Befund

Der [Menübandindex](research/playtable-ux-2026-11-22/footer-index.md) führt alle **18 registrierten Bedienpositionen** auf: normalerweise 16 sichtbar, zusätzlich „Einrasten“ im Messkontext und der im Freifenstermodus deaktivierte alte „Tisch“-Öffner. Beispiele: PT-B-001 Seiten, PT-B-003 Initiative, PT-B-007 Layers, PT-B-009 Raster & Licht, PT-B-010 Wählen, PT-B-014 Bewegen, PT-B-018 Messen, PT-B-026 Wand, PT-B-030 Licht, PT-B-034 Markierungen und PT-B-051 Zurück.

Beobachtungen, keine bloßen Geschmacksaussagen:

- **Vermischte Bedeutung:** Fensteröffner, gegenseitig ausschließende Werkzeugmodi, Interaktions-/Ansichtsschalter und Navigation teilen dieselbe Reihe. „Zurück“ öffnet zunächst ein Menü; es führt nicht unmittelbar zurück.
- **Uneinheitliche Anatomie:** dynamisch ergänzte Öffner bestehen aus Text, andere aus Emoji/Symbol plus separatem Text. Die Zeile mischt Beschriftungen wie „Layers“, „Tokens“ und „Seiten“ ohne erklärtes gemeinsames Vokabular. „Seiten“ meint Karten-/Szenenseiten; „Layers“ meint dagegen Token-Sichtbarkeit für Player bzw. DM.
- **Uneinheitliche Maße:** bei 1440 Pixeln sind Buttons 44 bzw. rund 44,2 Pixel hoch, „Zurück“ rund 55,2. Die tatsächlichen Icon-/Label-Anordnungen unterscheiden sich trotz gleicher Grundklasse. Kleiner Text im Dock liegt in dieser Aufnahme bei rund 11,5 Pixeln, Unterlabels nochmals darunter.
- **Seitlicher Suchaufwand:** bei 1440 Pixeln liegen alle 16 sichtbaren Buttons im Viewport; bei 1024 sind 14 und bei 390 nur fünf zumindest teilweise im sichtbaren Ausschnitt. Der Rest ist horizontal erreichbar, aber anfänglich nicht sichtbar. Diese Zahlen beschreiben den ungescrollten Zustand, keine grundsätzlich unerreichbaren Befehle.
- **Mehrere untere Ebenen:** persönliche und generische Aktionsleisten können zusätzlich darüber erscheinen. Tokenauswahl, Karte und aktive Werkzeuge benötigen einen nachvollziehbaren Kontext, damit „aktiv“, „offen“, „ausgewählt“ und „öffentlich“ nicht verwechselt werden.

Screenshots: [DM 1440](research/playtable-ux-2026-11-22/evidence/dm-desktop-baseline.png), [DM 1024](research/playtable-ux-2026-11-22/evidence/dm-1024-baseline.png), [DM 390](research/playtable-ux-2026-11-22/evidence/dm-390-baseline.png). Die dunkle Palette ist der vorhandene Ink-/Natural-/Edo-Stand, kein vorgeschlagener neuer Skin.

## Risiken und Übergang

Mittel: gleiche Optik ohne semantische Trennung würde Fehlbedienung erhalten; automatisch wechselnde Positionen würden Routinewege unsicher machen; blindes Verbergen könnte die Auffindbarkeit neuer Funktionen verschlechtern. Diese Befunde sind durch explizite Kategorien, stabile Zugänge und vergleichende Aufgaben im Apply zu bearbeiten. Niedrig: tatsächliche Befehlsfrequenzen und Nutzerpräferenzen sind unbekannt; sie werden als Hypothesen geführt. Kein neuer Sicherheits-/Berechtigungsentwurf erforderlich: getrennte Player-/DM-Komposition und serverseitige Rechte bleiben verbindliche Grenzen.

Artefakte haben Aufbewahrungsklasse Research/Audit. Die ausführliche reproduzierbare Rohaufnahme bleibt außerhalb des Git-Archivs im Forschungsordner; veröffentlichte Nachweise enthalten ausschließlich synthetische Daten. Nächster Schritt: [Evidenzreview](DADM_RESEARCH_PLAYTABLE_UX_2026-11-22.md) in drei unterscheidbare, lokal prüfbare UI-Konzepte übersetzen und als Mockups zur Entscheidung präsentieren. Noch kein Produktionsumbau.
