# Discover: VTT-Oberfläche, Spieltisch und Karteneditor

**Status:** Discover abgeschlossen, Profil `standard`. Dauerhaft: dieser Bericht, [20 Karten](plans/FEEDBACK_UI_PLAYTABLE_2026-11-13.md), [strukturierte Aufnahme](plans/FEEDBACK_UI_PLAYTABLE_2026-11-13.json), [gemeinsamer Index beider Runden](plans/FEEDBACK_NEXT_ROUND_2026-11-13.md) und [Diagnosebelege](proofs/feedback-round-1803-2026-11-13/checks.json). Keine neue Anwendungsimplementierung oder Auslieferung aus dieser Aufnahme.

## Eingabe und aktueller Stand

Vollständiges Protokoll `2026-11-12-1803-vtt-oberflache-und-karteneditor-1.txt`, Beginn 12.11.2026, 18:03 UTC, Dauer 13:13 min. Der vollständige Text ergänzt die abgeschnittenen Action Items um Licht, Wände, Navigation, Arbeitsbereiche, Kampagnenplätze, Bildpinsel und Kampagnenhub. Die Abschlussbemerkung über einen laufenden Run beschreibt den damaligen Zeitpunkt, keine aktuelle Abnahme der späteren Lieferung.

Isolierter Arbeitsstand `8e16b3cc4`, laufende Quelle `4b2a57332`, Image `sha256:c843eaba933bb40989b72bc9d206af177a882bea7ab89f65e69c40ad27d665f0`. Fünfzehn relevante Dateien sind per Hash mit dem laufenden Image abgeglichen; [Anhang-SHA und Laufzeitbeleg](proofs/feedback-round-1803-2026-11-13/source-runtime.json). Der ursprüngliche Arbeitsbaum bleibt unverändert.

20 zusätzliche kanonische Karten S01–S20; wiederholte Pinselformen werden mit **N08** verknüpft. Zusammen mit der vorherigen Aufnahme sind es 40 Karten, nicht 40 behauptete offene Fehler. Vorhandene Funktionen, neue Gestaltungsvorgaben, bestätigte Fehler und ungeklärte Berichte haben unterschiedliche Status. Donutarian ist vorgesehener Owner im Repo-Backlog; keine externe Aufgaben-App oder Nachricht wurde geändert.

## Neu konkretisierte Vorgaben

- **S01:** gemeinsamer Einstellungseinstieg als Zahnrad ganz rechts statt Textbutton Ansicht und Sprache. Dasselbe Einstellungsziel soll im Back-Menü verständlich benannt sein; endgültiger Wortlaut ist offen.
- **S02/S17:** Buchcharakter auch nachts erhalten, verbrannte Pergamentoptik und rote statt goldener Standardakzente. Der Editor soll zur gemeinsamen VTT-Oberfläche passen. Früheres Lob der Werkstattoptik bleibt nützlich, ersetzt diese jüngere Vorgabe nicht.
- **S03:** echte englische SRD-5.2.1-Inhalte passend zur Sprachwahl, nicht nur englische Bedienlabels. Die vorhandene UI-Sprache lässt deutsche Regeln bislang absichtlich unverändert.
- **S04:** sichtbare volle Monatsübersicht mit Wochentagen und Wochenzeilen, auch ohne Termine.
- **S11/S12:** Chat links und Journal rechts; Journal als zentraler Einstieg für berechtigte Session-Dateien, Assets und Tokens. Vorhandene Aktivität/Notizen sowie erforderliche DM-Sessionsteuerung dürfen bei der Neuordnung nicht verloren gehen.
- **S20:** DM-Kartenverwaltung und Übernahme zusätzlich vom Kampagnenhub aus erreichen.

Das sind aus dem Protokoll erfasste Produktvorgaben. Es sind noch keine Framework-, Datenformat-, Cache-, Renderer- oder Releaseentscheidungen getroffen.

## Geprüfte Befunde und Abgrenzungen

| Thema | Heutiger Nachweis | Bedeutung |
| --- | --- | --- |
| S10: Back → Maps | Menü bietet `/mapmaker`; originale `_normalizeBookReturnTarget`-Methode gibt dafür `null` zurück. Dashboard, Charaktere und Creation Engine werden akzeptiert. `returnToBook` wirft bei `null` einen Fehler. | Konkrete Logiklücke reproduziert. Normaler Kartenweg und weitere Rückwege müssen im nächsten Slice geprüft werden. Kein frisch ausgeführter produktiver Browserklick behauptet. |
| S04: leerer Monatskalender | Originaler `renderGrid` mit null Einträgen erzeugt für November 2026 30 Tage und sieben Wochentagsköpfe, für Februar 2028 29 Tage und sieben Köpfe. CSS nutzt sieben Spalten. | Raster bereits vorhanden; Standardzustand ist noch `rolling30`. Die gewünschte regelmäßige Monatspräsentation ist daher nicht automatisch erledigt. |
| S05: eigene Bibliothek | Liste besteht aus Namen und Größen; große Vorschau entsteht erst nach Auswahl. | Gewünschte kleine Vorschaubilder in der Auswahl sind eine zusätzliche Präsentation. Vorhandenen Snapshot-/Freigabeweg erhalten. |
| S06/S07: Licht und Wände | DM-Handler, Vorlagen und Geometrie-/Sichttests existieren. Protokoll nennt weder Klickfolge noch aktiven Kontext/Sichtmodus oder Status. | Als gemeldete, nicht reproduzierte Funktionsprobleme führen. Kein Rollen-/Sichtschutz wird aufgrund der Vermutung gelockert. |
| S08: Messformen | Vorhandenes Modell enthält Messwegpunkte und Streckenlabels. | Kegel/Kreis- bzw. Kugelprojektion/Quadrat brauchen einen abgegrenzten Formenmodus. Bisherige Maße/Abbruchwege bleiben erforderlich. |
| S11/S13: Arbeitsbereiche | Aktuelle Sidebar-Reihenfolge Journal/Chat/Tools/Session; Session enthält Hinweise und einen DM-Slot. Tischbereiche haben unterschiedliche Lese-/Schreibrechte. | Präsentation ändern, keine pauschale Löschung der Sessionfunktionen oder aller Player-Zugänge zu erlaubten Token-/Initiativeinformationen. |
| S16: Charaktertext | Rubrik geteilte Gruppencharaktere und eigener Leer-/Fehlerzustand vorhanden. | Der unklare Ausdruck no check reicht nicht als Ursache; tatsächlichen störenden Zustand identifizieren. |
| S18: Bildpinsel | Stempelbilder werden teilweise schon bedarfsgesteuert geladen; ausstehende Bildladevorgänge werden wiederverwendet. | Das ist keine fertige Umwandlung von Kachelausschnitten zu weichen Pinseln. Erstnutzung/Cache ist ein Vorschlag zur Abwägung. |
| S19: Landmassen-Layer | `adopt` erstellt eine neue Rasterebene, wählt sie aus und legt einen Undo-/Redo-Schritt an. Vorige aktive Ebene wird bei Undo wiederhergestellt. Derselbe Quellstand ist im finalen Live-Lauf belegt. | Offene Layerfrage beantwortet. Malen in eine vorhandene Ebene wäre ein anderer Umfang. |
| S15: Kampagnenplätze | Konto-Kontingent und Erstellungsprüfung vorhanden. Im Protokoll fehlt eine neue Zahl oder Freigaberegel. | Erweiterungsweg planen; weder neues Limit noch Erhöhung eines konkreten Kontos daraus ableiten. Offene vierte Testkampagne bleibt eine separate Frage. |

Die Quellenmethoden wurden ohne Server, Datenbank oder produktive Schreiboperation ausgewertet: [Diagnoseergebnis](proofs/feedback-round-1803-2026-11-13/probe-result.json), [ausführbares Skript](proofs/feedback-round-1803-2026-11-13/probe-existing-ui.cjs). Kein neuer Browserlauf, keine volle Regression und keine neue Live-Abnahme in diesem Pass. Für Landmasse wurde der [vorhandene Live-Beleg desselben Images](proofs/feedback-final-2026-11-13/live-landmass.json) verwendet.

## Englische Inhalte und frühere offene Angabe I04

Die [offizielle SRD-Seite](https://www.dndbeyond.com/srd) verlinkt die [englische Originalfassung 5.2.1](https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf) und die lokalisierte deutsche Ausgabe; das SRD wird dort unter CC BY 4.0 bereitgestellt. Geprüft am 13.11.2026. Das vorhandene veröffentlichte Inhaltsmanifest ist `de-DE`, die Generierung verwendet derzeit das deutsche Paket als Standard.

Der neue Auftrag benennt nun Regelversion, Zielsprache und den Umfang der englischen Inhalte in den betroffenen Ansichten. **I04/VTT-40 erhält daher `scope_defined_pending_apply` bzw. einen Verweis auf S03.** Es wird keine bereits gelieferte englische Regeldatenbasis behauptet. Im Apply bleiben unter anderem Inhaltszuordnung, Quellenverweise, Such-/Compendiumkatalog und bestehende Charakterreferenzen zu prüfen. Unbenannte Zusatzregelwerke oder neue Kunst werden damit nicht automatisch bereitgestellt.

## Relevantes Inventar und Abhängigkeiten

- Gemeinsame Navigation/Darstellung: `vtt-main-nav.js`, `display-preferences.js/.css`; Kontobereich und Präferenzdialog existieren bereits.
- Tischoberflächen: `play.html`, gemeinsame `play-ui.js`, getrennte `play-dm.js` und `play-player.js`; ihre serverautorisierten Kontexte bleiben verbindlich. Eigene Dialoge oder neue Positionen sind keine Autorisierung.
- Kalender: `session-calendar.js/.css`; Datumsspannen kommen vom autorisierten API-Weg. Monatsdarstellung nicht parallel neu erfinden.
- Karten: `play-map-library.js`, Hub-Markup in `book-scene.js`, `landmass-dialog.js`, `stamps.js`; persönliche Projekte, veröffentlichte Snapshots und Kampagnenkarten sind heute unterschiedliche Ressourcen.
- Inhalte: `rules_content/generator.py`, Paketmanifest, generierte Reader-/Such-/Creator-/Compendiumdaten. Englische UI-Literale und englischer Regelinhaltskatalog bleiben unterschiedliche Ebenen.

## Risiken, offene Fragen und nächster Schritt

- **Medium, S10:** bestätigter normaler Navigationsweg scheitert. Begrenzter Apply-Vertrag muss gültige Rückwege und Entwurfsschutz berücksichtigen.
- **Medium, S06/S07:** Ursache unbestätigter Licht-/Wandprobleme offen. Zuerst Kontext, Sichtkonfiguration und konkrete Wirkung reproduzieren.
- **Medium, S03:** Sprach-/Quellenwechsel kann Referenzen und bestehende Figuren betreffen. Gültige gespeicherte Werte/Namen nicht durch eine globale Textübersetzung verändern.
- **Medium, S12/S13/S20:** gemeinsame Verwaltungsoberflächen betreffen Rollen, Datei-/Assetbesitz und private Quellen. Rechte und getrennte Player-Komposition bleiben Voraussetzung.
- **Medium, S18:** Bildpinsel können Speicher-/Cache-/Historygrenzen betreffen. Keine ungeprüfte Vorberechnung des gesamten Assetbestands.
- **Low:** ältere Beobachtungen können durch bereits gelieferte Funktionen überholt sein. Bestehende Monatsdaten, Layer-/Undo-Verhalten, Fit, Hilfe und Tastenkürzel erhalten.

Offen sind die endgültige Menübenennung, Licht-/Wandreproduktion, der konkrete Charakter-Leerzustand, die Kontingentpolitik sowie die Bildpinsel-/Cachegrenze. Sie blockieren jeweils ihren betroffenen Umfang; bereits klare Navigations- und Bedienkorrekturen sind unabhängig entwerfbar.

Übergabe in Apply anhand des gemeinsamen Index: bestätigte Fehler N01/S10 zuerst, N18 und S06/S07 als getrennte Ursachenuntersuchungen, anschließend klar begrenzte Navigation-/Kalender-/Bibliotheks- und Creator-/Editor-Slices. Journal/Kampagnenhub, SRD-Inhalte und Bildpinsel erhalten eigene Daten-/Berechtigungs-/Kompatibilitätsgrenzen. Die vorherige technische Lieferung wird nicht rückwirkend als unvollständig oder die neue Runde als umgesetzt bezeichnet.
