# Neue Feedbackrunde: Charakterbau und Karteneditor

Quelle: 11.11.2026, 09:46 UTC, 17:37 min · Abgleich: 13.11.2026 · vorgesehen für Donutarian.

**Status:** Discover abgeschlossen. Die Karten sind im Repository erfasst; kein externes Kanban wurde geändert. Neue Umsetzung/Live-Auslieferung aus dieser Runde hat noch nicht begonnen. Bestehende Lieferung bleibt separat nachgewiesen.

| Karte | Priorität | Kategorie | Aufgabe | Status | Stelle |
| --- | --- | --- | --- | --- | --- |
| N01 | P1 | Charakterregeln | Anrufungsvoraussetzungen tatsächlich prüfen | Für Apply erfasst | 02:05–03:01 |
| N02 | P2 | Creator-Bedienung | Klassenauswahl beruhigen und Details lesbar gliedern | Für Apply erfasst | 01:04–01:56 |
| N03 | P2 | Creator-Bedienung | Gewürfelte Werte als einzelne verfügbare Ergebnisse zeigen | Für Apply erfasst | 01:19–02:05 |
| N04 | P2 | Hintergründe/Inhalte | Hintergrundauswahl und erlaubte Attributkombinationen erweitern | Inhalt konkretisieren | 02:05–02:53 |
| N05 | P2 | Creator-Bedienung | Unterklassenmerkmale beim Aufstieg verständlich einblenden | Für Apply erfasst | 02:05–02:53 |
| N06 | P2 | Creator-Bedienung | Zauber nach Grad und Name sortieren können | Für Apply erfasst | 02:05–02:53 |
| N07 | P3 | Kampagnenentscheidung | DM-Freigaben für zusätzliche Bauoptionen abgrenzen | Produktgrenze klären | 03:05–04:09 |
| N08 | P2 | Malen | Mehr Pinselspitzen und abwechslungsreiche Striche | Für Apply erfasst | 03:05–05:01 |
| N09 | P2 | Malen | Farbe, Textur und Kontur bewusst beeinflussen | Für Apply erfasst | 04:09–05:01 |
| N10 | P2 | Malen | Radierer mit sinnvollen eigenen Startwerten | Für Apply erfasst | 05:01–05:45 |
| N11 | P3 | Unklare Bedienangabe | Skalieren auf 0 % einem konkreten Regler zuordnen | Angabe klären | 05:01–05:45 |
| N12 | P2 | Objektbearbeitung | Wegpunkte auffindbar bearbeiten und Kurven ermöglichen | Für Apply erfasst | 05:45–06:59 |
| N13 | P2 | Objektbearbeitung | Freie Assetplatzierung und Kachelgröße verständlich trennen | Für Apply erfasst | 07:18–09:20 |
| N14 | P1 | Objektbearbeitung | Auswahlrahmen und gemeinsame Bearbeitung ermöglichen | Für Apply erfasst | 09:20–10:02;12:38–13:20 |
| N15 | P1 | Objektbearbeitung | Dekosymbole ohne erzwungenen Ortsnamen setzen | Für Apply erfasst | 10:13–12:20 |
| N16 | P2 | Editor-Navigation | Ort, Symbol, Kachel und Beschriftung verständlich organisieren | Für Apply erfasst | 10:13–12:38 |
| N17 | P2 | Editor-Navigation | Rückgängig und Wiederholen leichter finden | Für Apply erfasst | 13:20–13:38 |
| N18 | P1 | Navigation/Speichern | Editor-Ausstieg, Anmeldung und Entwurfsstatus unterscheiden | Reproduzieren | 13:43–15:37 |
| N19 | P3 | Bereits geliefert/positiv | Kartenwerkstatt-Optik als positive Referenz erhalten | Bereits geliefert / erhalten | 15:31–15:54 |
| N20 | P3 | Bereits überholt/Inhalte | Assetbestand gegen nur Kenney abgleichen | Beobachtung teilweise überholt | 08:50–09:20 |

## Befunde und gewünschtes Ergebnis

### N01 – Anrufungsvoraussetzungen tatsächlich prüfen

**Heute:** Eldritch Smite ohne Pact of the Blade wird auf Stufe 5 als valid und complete akzeptiert; beide Kontrollfälle ebenfalls ohne Blocker. Daten und UI kennen bisher nur die Mindestklassenstufe als prüfbare Voraussetzung.

**Anforderung für Apply:** Ungültige Kombination ist in Creator und Fortschritt erkennbar gesperrt; der Server weist sie auch bei direkter Anfrage zurück. Zulässige Kombinationen bleiben möglich.

**Belege:** `vtt/rules_content/creator_rules.py:488; vtt/rules_content/creator_data.py:1023; vtt/static/js/srd-creator-steps.js:513; vtt/static/js/srd-progression-ui.js:605`. Zeitmarke:02:05–03:01.

### N02 – Klassenauswahl beruhigen und Details lesbar gliedern

**Heute:** Klassenkarten enthalten Wurf-/Hauptattribut-Kurzinfos; daneben gibt es bereits eine Detailansicht mit Definitionsliste und Regeltextlink.

**Anforderung für Apply:** Klasse lässt sich unmittelbar wählen; ausführliche Informationen sind nach Auswahl verständlich formatiert. Markdown ist ein Vorschlag aus dem Feedback, keine bereits gewählte Technik.

**Belege:** `vtt/static/js/srd-creator-steps.js:151,178`. Zeitmarke:01:04–01:56.

### N03 – Gewürfelte Werte als einzelne verfügbare Ergebnisse zeigen

**Heute:** Dropdowns fassen gleiche Werte zusammen und zeigen Anzahl-/Verfügbarkeitstexte. Die Mehrfachzuweisung wird bereits gezählt; vorhandene Würfel-Multimengenprüfung besteht.

**Anforderung für Apply:** Sechs Ergebnisse bleiben erkennbar; gleiche Zahlen erscheinen entsprechend ihrer verfügbaren Häufigkeit. Mehrfachwerte werden weder verloren noch zu oft zugewiesen.

**Belege:** `vtt/static/js/srd-creator-steps.js:394; tests/test_regelwerk_creator_rules.py:369`. Zeitmarke:01:19–02:05.

### N04 – Hintergrundauswahl und erlaubte Attributkombinationen erweitern

**Heute:** Vier SRD-Hintergründe sind enthalten. +2/+1 sowie +1/+1/+1 auf deren drei Attribute sind bereits verfügbar und geprüft; veröffentlichte Homebrew-Hintergründe sind seit P3 angebunden.

**Anforderung für Apply:** Gewünschte weitere Hintergründe mit Quelle benennen; gewünschte Kombination von fehlendem Inhalt oder schwer auffindbarer bestehender Wahl trennen. Bestehende freigegebene Homebrew-Wege berücksichtigen.

**Belege:** `vtt/static/js/srd-creator-steps.js:274; vtt/rules_content/creator_rules.py:194; docs/DADM_DEPLOY_ORIGINS_PROVENANCE_2026-11-11.md`. Zeitmarke:02:05–02:53.

### N05 – Unterklassenmerkmale beim Aufstieg verständlich einblenden

**Heute:** Creator zeigt Unterklassenkarten mit separatem Textlink. Fortschrittsdialog zeigt bereits neue Merkmalsnamen; vollständige erreichbare Unterklassenbeschreibung ist damit nicht belegt. Begriffe Wahlen/Unterklassentext sind weiterhin sichtbar.

**Anforderung für Apply:** Neue Unterklassenmerkmale sind beim betreffenden Level ohne zusätzlichen Textmenü-Klick verständlich sichtbar. Benennungen werden eindeutig; Klassen-/Unterklassenstufen bleiben korrekt zugeordnet.

**Belege:** `vtt/static/js/srd-creator-steps.js:478; vtt/static/js/srd-progression-ui.js:422,729; vtt/characters/srd_progression.py:157`. Zeitmarke:02:05–02:53.

### N06 – Zauber nach Grad und Name sortieren können

**Heute:** Alphabetische Reihenfolge und ein Gradfilter sind vorhanden. Filtern ersetzt keine Sortierung mehrerer Grade; im Fortschrittsweg ist eine gesonderte Auswahl vorhanden.

**Anforderung für Apply:** Wählbare Sortierung nach Grad mit nachvollziehbarer Namensreihenfolge innerhalb des Grades; bestehende Suche/Filter und gültige Zauberwahlen bleiben erhalten.

**Belege:** `vtt/static/js/srd-creator-steps.js:742; vtt/static/js/srd-progression-ui.js`. Zeitmarke:02:05–02:53.

### N07 – DM-Freigaben für zusätzliche Bauoptionen abgrenzen

**Heute:** Gewünscht sind beispielsweise zusätzliche Talente über das Kampagnen-Dashboard. Bestehende numerische Overrides und veröffentlichte Homebrew-Inhalte decken diese neue Berechtigungsfrage nicht automatisch ab.

**Anforderung für Apply:** Vor Apply klären: erlaubte Zusatzoptionen, freigebende Rolle, Geltungsbereich und sichtbare Regelabweichung. Kampagnenbesitz darf einen Player-Kontext weiterhin nicht privilegieren.

**Belege:** `vtt/static/js/srd-creator-steps.js:799; docs/decisions/PLAYTABLE_ROLE_SEPARATION_2026-11-01.md`. Zeitmarke:03:05–04:09.

### N08 – Mehr Pinselspitzen und abwechslungsreiche Striche

**Heute:** Pinselspitze ist rund; Größe, Deckkraft, Weichheit und Material beeinflussen bereits den Strich. Mehr Stempel oder Texturen lösen diesen Spitzenwunsch nicht.

**Anforderung für Apply:** Mehr als eine sichtbar unterscheidbare Pinselspitze; bestehende Druck-/Deckkraft-/Undo- und Speicherfunktionen bleiben nutzbar. Auswahl konkreter Spitzen gehört in Apply.

**Belege:** `vtt/static/mapmaker/js/brush.js:138; vtt/static/mapmaker/js/ui.js:205`. Zeitmarke:03:05–05:01.

### N09 – Farbe, Textur und Kontur bewusst beeinflussen

**Heute:** Terrainmaterialien koppeln Grundfarbe, Motive bzw. geladene Texturen. Eine freie Terrainfarbwahl ist damit nicht vorhanden; Beschriftungsfarbe ist eine andere Funktion.

**Anforderung für Apply:** Terrain lässt sich individuell färben und seine Textur/Kontur bewusst wählen; bisherige Materialpresets und gespeicherte Projekte bleiben nachvollziehbar.

**Belege:** `vtt/static/mapmaker/js/brush.js:7,38; vtt/static/mapmaker/js/ui.js:205`. Zeitmarke:04:09–05:01.

### N10 – Radierer mit sinnvollen eigenen Startwerten

**Heute:** Pinsel und Radierer verwenden dieselben brush-Einstellungen; Ausgangswerte sind90% Deckkraft und 45% Weichheit. Ein Werkzeugwechsel setzt diese Werte nicht auf 100/0.

**Anforderung für Apply:** Radieren startet deckend und mit dem gewünschten klaren Rand; spätere bewusste Anpassung bleibt möglich. Malwerte dürfen dabei nicht unbeabsichtigt verloren gehen. Unklare Skalierung gesondert N11.

**Belege:** `vtt/static/mapmaker/js/app.js:49,1480; vtt/static/mapmaker/js/ui.js:205`. Zeitmarke:05:01–05:45.

### N11 – Skalieren auf 0 % einem konkreten Regler zuordnen

**Heute:** Das Protokoll benennt keinen konkreten Regler. Pinsel- oder Symbolgröße ist nicht mit Größenvariation gleichzusetzen; eine Nullgröße wäre keine sichere Interpretation.

**Anforderung für Apply:** Bedienelement und beabsichtigter Effekt benennen; kein pauschales Größen-Clamping auf 0. Rückfrage läuft, alle unabhängigen Karten sind davon unberührt.

**Belege:** `Quelle05:01–05:45; vtt/static/mapmaker/js/ui.js:205`. Zeitmarke:05:01–05:45.

### N12 – Wegpunkte auffindbar bearbeiten und Kurven ermöglichen

**Heute:** Shift-Ziehen einzelner Wegpunkte ist bereits implementiert und browsergeprüft inklusive Undo/Redo und Projekt-Rundlauf. Der Renderer verbindet Punkte mit Geraden; ein pro Knoten wählbarer Kurvenmodus ist damit nicht vorhanden.

**Anforderung für Apply:** Sichtbarer Einstieg in Punktbearbeitung; gewünschter Gerade/Kurve-Wechsel und Verschieben sind erreichbar. Doppelklick/Rechtsklick sind Bedienvorschläge, noch keine Architekturentscheidung.

**Belege:** `vtt/static/mapmaker/js/tools.js:149; vtt/static/mapmaker/js/render.js:99; tests/test_mapmaker_browser.py:840`. Zeitmarke:05:45–06:59.

### N13 – Freie Assetplatzierung und Kachelgröße verständlich trennen

**Heute:** Stempel sind frei platzierbar, Raster ist optional und standardmäßig aus. Echte Kachelebenen verwenden Zellen; eine Rastervergrößerung wird verweigert, wenn belegte Zellen außerhalb der Karte lägen.

**Anforderung für Apply:** Dekorative Assets lassen sich frei setzen/skaliert verwenden; bei echten Kacheln ist Rasterbindung verständlich und die Größenbegrenzung erklärbar. Keine stillschweigende Umwandlung aller Kacheln in Stempel.

**Belege:** `vtt/static/mapmaker/js/app.js:712,931; vtt/static/mapmaker/js/document.js`. Zeitmarke:07:18–09:20.

### N14 – Auswahlrahmen und gemeinsame Bearbeitung ermöglichen

**Heute:** Auswahlmodus auf leerer Fläche beginnt aktuell eine Pan-Geste. hitTestAll berücksichtigt Stempel, Beschriftungen und Wege, keine Rasterzellen; Auswahl ist eine einzelne ID.

**Anforderung für Apply:** Leeres Ziehen im Auswahlwerkzeug markiert einen Bereich; Mehrfachauswahl und gemeinsames Löschen/Bearbeiten haben einen klaren Umfang. Verschieben der Ansicht bleibt bewusst zugänglich.

**Belege:** `vtt/static/mapmaker/js/tools.js:149,166; vtt/static/mapmaker/js/app.js:903`. Zeitmarke:09:20–10:02;12:38–13:20.

### N15 – Dekosymbole ohne erzwungenen Ortsnamen setzen

**Heute:** Orts-/Beschriftungsobjekte starten mit Neuer Ort. UI und Dokumentvalidator verweigern leeren Text; das beobachtete übrig bleibende N passt dazu. Reine Stempel sind schon ohne Beschriftung möglich.

**Anforderung für Apply:** Berg/Busch kann als Dekoration ohne Pflichttext stehen. Echte Orte und separate Beschriftungen bleiben sinnvoll benennbar; bestehende Projekte bleiben lesbar.

**Belege:** `vtt/static/mapmaker/js/app.js:960; vtt/static/mapmaker/js/ui.js:678; vtt/static/mapmaker/js/document.js:386`. Zeitmarke:10:13–12:20.

### N16 – Ort, Symbol, Kachel und Beschriftung verständlich organisieren

**Heute:** Benutzer verwechselt die verschiedenen Assetwege. Im Modell sind Stempel, Labels mit Ortsdaten und echte Kacheln unterschiedliche Typen.

**Anforderung für Apply:** Eine verständliche Werkzeug-/Sidebar-Struktur führt zur gewünschten Dekoration, Beschriftung oder Rasterkachel. Die Aussage alles eins ist ein UX-Wunsch, kein Auftrag zum Ersetzen aller Datenmodelle.

**Belege:** `vtt/static/mapmaker/js/ui.js:148; vtt/static/mapmaker/js/app.js:24`. Zeitmarke:10:13–12:38.

### N17 – Rückgängig und Wiederholen leichter finden

**Heute:** Toolbarbuttons und Strg+Z/Strg+Umschalt+Z sind vorhanden. Der gezielte Pfadtest hat beide tatsächlich ausgeführt. Historie ist also nicht neu zu erfinden.

**Anforderung für Apply:** Rückgängig/Wiederholen sind bei normaler Bedienung leicht auffindbar und erklären ihren Zustand; vorhandene Verlaufslimits bleiben sichtbar und verlässlich.

**Belege:** `vtt/static/mapmaker/index.html:39,403; vtt/static/mapmaker/js/app.js:1260`. Zeitmarke:13:20–13:38.

### N18 – Editor-Ausstieg, Anmeldung und Entwurfsstatus unterscheiden

**Heute:** Berichtet wird ein Klick auf Creation Engine, anschließend ein wiederherstellbarer Entwurf; später tritt der Effekt nicht erneut auf. Kein URL-/HTTP-/Zeitbeleg für einen Inaktivitätslogout. Persönlicher Entwurf, Bibliothek, Atlas-Lease und absolute6 h-Anmeldung haben unterschiedliche Lebenszyklen.

**Anforderung für Apply:** Reproduktionsmatrix mit normalem Navigationsklick, Access-Refresh innerhalb der Frist, echtem Fristablauf, fehlgeschlagenem Autosave und Atlas-Kontext. Ungespeicherte Arbeit/Entwurfsstatus verständlich; keine pauschale Verlängerung der6 h-Frist. Keine Kontodaten protokollieren.

**Belege:** `vtt/static/mapmaker/js/app.js:105,117; vtt/static/js/creation-engine-nav.js:58; vtt/static/mapmaker/js/library.js:81; vtt/auth/lifetime.py`. Zeitmarke:13:43–15:37.

### N19 – Kartenwerkstatt-Optik als positive Referenz erhalten

**Heute:** Werkstattlayout wird ausdrücklich gelobt. Nacht-/Papiermodus und Kontraste auf den VTT-Hauptwegen wurden inzwischen geliefert und final geprüft.

**Anforderung für Apply:** Positiven Markenstil erhalten; weitere konkrete visuelle Unterschiede bei aktueller Abnahme nennen. Kein neuer Komplettumbau allein aus dem historischen Vergleich.

**Belege:** `docs/proofs/feedback-final-2026-11-13/live-contrast.json; docs/proofs/feedback-final-2026-11-13/delivery.json`. Zeitmarke:15:31–15:54.

### N20 – Assetbestand gegen nur Kenney abgleichen

**Heute:** Die damalige Beobachtung nur Kenney Tiny Town beschreibt den heutigen Bestand nicht: weitere vorhandene Pakete und der abgeglichene LPC-Revised-Stand sind inzwischen live. Dies erfüllt weder weitere unbekannte Art-Wünsche noch die neue Pinselspitzen-Anforderung.

**Anforderung für Apply:** Aktuelle Palette als Ausgangspunkt verwenden; neue konkret gewünschte Assets mit Quelle getrennt erfassen. Keine vorhandenen neueren Pakete ersetzen.

**Belege:** `docs/DADM_RECONCILE_LIVE_LPC_2026-11-13.md; docs/proofs/feedback-final-2026-11-13/delivery.json`. Zeitmarke:08:50–09:20.

## Reihenfolge für den nächsten begrenzten Durchlauf

1. N01: Regelprüfung; N18 parallel als getrennte Ursachenuntersuchung, noch kein behaupteter Logout-Fix.
2. N15/N14: Pflichtnamen und Auswahlverhalten; danach N10/N17 für sinnvolle Startwerte und sichtbares Undo.
3. N02/N03/N05/N06: Creator-Übersicht, Würfelergebnisse, Unterklassen und Zaubersortierung.
4. N16/N12/N13: Werkzeugzugänge, Punkt-/Kurvenbearbeitung und Raster-/Freiplatzierung.
5. N08/N09: zusätzliche Pinselspitzen und unabhängige Materialgestaltung.

N04, N07 und N11 bleiben getrennt konkretisierbar; sie blockieren die unabhängigen Fehlerkorrekturen nicht. N19/N20 dokumentieren Überschneidungen, keine erneute Neuimplementierung. Reihenfolge ist ein Apply-Handoff, kein Releaseplan mit behaupteter Umsetzung.

Vollständige Fakten, Abhängigkeiten, Risiken und offene Angaben: [strukturierte Karten](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.json). [Discover-Bericht](../DADM_DISCOVER_CHARACTER_MAPMAKER_FEEDBACK_2026-11-13.md).
