# Gemeinsames Backlog der beiden neuen Feedbackrunden

Stand: 13.11.2026 · vorgesehen für Donutarian · **40 kanonische Karten**. Der wiederholte Wunsch nach Pinselformen ist mit N08 verknüpft. Diese Übersicht erfasst Anforderungen und Befunde; daraus ist noch keine neue Anwendungsversion ausgeliefert.

Quellen: [Charakterbau/Karteneditor vom 11.11.](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) und [VTT/Spieltisch/Karteneditor vom 12.11.](FEEDBACK_UI_PLAYTABLE_2026-11-13.md). Die [vorige technische Lieferung](../proofs/feedback-final-2026-11-13/delivery.json) bleibt abgeschlossen; die menschliche Abnahme ist weiterhin separat.

## Verbindlich aufzunehmende neue Richtung

- Einstellungseinstieg als Zahnrad ganz rechts; dort Darstellung und Sprache bündeln. Menübegriff noch vereinheitlichen.
- Verbrannte Buch-/Pergamentoptik im Nachtmodus, bevorzugt rote statt goldener Akzente. Die gelieferte Kontrastkorrektheit ersetzt diesen Gestaltungswunsch nicht.
- Vollständige englische SRD-5.2.1-Inhalte passend zur Sprachwahl, zusätzlich zur vorhandenen englischen Bedienoberfläche. Originalquelle ist konkret benannt.
- Voller Monatskalender mit Wochentagen/Wochenzeilen auch ohne Sessions. Raster existiert; die aktuelle Standardansicht ist noch die 30-Tage-Liste.
- Chat links, Journal rechts; Journal als zentraler berechtigter Zugang zu Session-Dateien, Assets und Tokens.
- Karteneditor in die gemeinsame Oberfläche einordnen; DM-Kartenverwaltung/Übernahme auch im Kampagnenhub.

## Zuerst zu bearbeiten

1. **N01 und S10:** bestätigte Anrufungsprüfungslücke und abgelehntes Back-Maps-Ziel. N18 bleibt eine eigene Ursachenuntersuchung; der Maps-Befund erklärt nicht automatisch den früheren Creation-Engine-Ausstieg.
2. **S06/S07:** Licht und Wände im tatsächlichen DM-/Sichtkontext reproduzieren. Noch kein Defekt als bestätigt markieren.
3. **S01/S09/S11/S13 sowie S04/S05:** Einstellungseinstiege, klare Tischbereiche, Kalenderstandard und Bibliotheksvorschauen.
4. **N15/N14/N10/N17/N16/N12/N13, dann N02/N03/N05/N06:** konkrete Editor- und Creator-Bedienung.
5. **S12/S20/S03:** größere Inhalts-/Verwaltungspakete mit gesondertem Apply-Vertrag für Rollen, Quellen und Datenkompatibilität.
6. **S02/S17, N08/N09/S18, S14:** gemeinsame Gestaltung, zusätzliche Pinsel/Bildpinsel, optionales Kontobild.

Die Reihenfolge ist ein Übergabevorschlag für begrenzte Apply-Slices. Sie trifft noch keine Architektur-, Cache- oder Releaseentscheidung und behauptet keine unabhängige Agentenarbeit.

## Bereits geklärt oder nur teilweise neu

- **S19:** Landmasse erzeugt eine neue Rasterebene, wählt sie aus und lässt sich in einem Schritt rückgängig machen. Keine neue Layer-Implementierung aus einer offenen Frage ableiten.
- **S04:** Beide leeren Monatsfälle wurden mit dem tatsächlichen Renderer geprüft: November 2026/30 Tage und Schaltfebruar 2028/29 Tage, jeweils sieben Wochentagsköpfe. Noch keine neue Browserabnahme in diesem Pass.
- **S05:** Einzelvorschau nach Auswahl existiert; die gewünschte bebilderte Auswahlliste ist zusätzlich.
- **N08/S18:** Pinselformen und aus Bildern erzeugte weiche Pinsel sind verwandte, unterschiedliche Anforderungen. Normales bedarfsgesteuertes Stempelbildladen ist keine fertige Bildpinsel-Funktion.
- **N19/S02/S17:** Gelobte Werkstattoptik erhalten, ihre Einordnung aber anhand der jüngeren Owner-Vorgabe planen.

## Offene Grenzen

N04: konkrete zusätzliche Hintergründe. N07: Umfang von DM-Baufreigaben. N11: konkreter 0%-Regler. N18/S06/S07/S16: reproduzierbarer Zustand. S15: berechtigter Weg zur Kampagnenplatzerweiterung und Produktgrenze; keine neue Slotanzahl beschlossen und keine Kontingente geändert. Die allgemeine Anforderung beantwortet nicht die bestehende Frage nach einem zusätzlichen Donutarian-Testplatz.

Englische SRD-Inhalte sind dagegen nicht mehr mangels benannter Quelle/Sprachfassung offen: **I04 → S03**. Umsetzung und kompatible Inhaltszuordnung stehen noch aus. Unbenannte zusätzliche Kunst, Monsterbilder und fremde Zusatzregelwerke bleiben getrennte Eingaben.

## Vollständiger Index

| Karte | Priorität | Aufgabe | Status | Detailquelle |
| --- | --- | --- | --- | --- |
| N01 | P1 | Anrufungsvoraussetzungen tatsächlich prüfen | Für Apply erfasst | [N01](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N02 | P2 | Klassenauswahl beruhigen und Details lesbar gliedern | Für Apply erfasst | [N02](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N03 | P2 | Gewürfelte Werte als einzelne verfügbare Ergebnisse zeigen | Für Apply erfasst | [N03](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N04 | P2 | Hintergrundauswahl und erlaubte Attributkombinationen erweitern | Inhalt konkretisieren | [N04](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N05 | P2 | Unterklassenmerkmale beim Aufstieg verständlich einblenden | Für Apply erfasst | [N05](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N06 | P2 | Zauber nach Grad und Name sortieren können | Für Apply erfasst | [N06](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N07 | P3 | DM-Freigaben für zusätzliche Bauoptionen abgrenzen | Produktgrenze klären | [N07](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N08 | P2 | Mehr Pinselspitzen und abwechslungsreiche Striche | Für Apply erfasst | [N08](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N09 | P2 | Farbe, Textur und Kontur bewusst beeinflussen | Für Apply erfasst | [N09](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N10 | P2 | Radierer mit sinnvollen eigenen Startwerten | Für Apply erfasst | [N10](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N11 | P3 | Skalieren auf 0 % einem konkreten Regler zuordnen | Angabe klären | [N11](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N12 | P2 | Wegpunkte auffindbar bearbeiten und Kurven ermöglichen | Für Apply erfasst | [N12](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N13 | P2 | Freie Assetplatzierung und Kachelgröße verständlich trennen | Für Apply erfasst | [N13](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N14 | P1 | Auswahlrahmen und gemeinsame Bearbeitung ermöglichen | Für Apply erfasst | [N14](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N15 | P1 | Dekosymbole ohne erzwungenen Ortsnamen setzen | Für Apply erfasst | [N15](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N16 | P2 | Ort, Symbol, Kachel und Beschriftung verständlich organisieren | Für Apply erfasst | [N16](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N17 | P2 | Rückgängig und Wiederholen leichter finden | Für Apply erfasst | [N17](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N18 | P1 | Editor-Ausstieg, Anmeldung und Entwurfsstatus unterscheiden | Reproduzieren | [N18](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N19 | P3 | Kartenwerkstatt-Optik als positive Referenz erhalten | Vorhanden / erhalten | [N19](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| N20 | P3 | Assetbestand gegen nur Kenney abgleichen | Beobachtung teilweise überholt | [N20](FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md) |
| S01 | P2 | Einstellungen im Zahnrad rechts bündeln | Für Apply erfasst | [S01](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S02 | P2 | Nachtmodus als verbranntes Buch mit roten Akzenten | Für Apply erfasst | [S02](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S03 | P2 | Englisches SRD 5.2.1 als sprachabhängige Inhaltsfassung | Für Apply erfasst | [S03](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S04 | P2 | Vollen Monatskalender als reguläre Ansicht zeigen | Für Apply erfasst | [S04](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S05 | P2 | Vorschaubild und kurzes Label in Own Library | Für Apply erfasst | [S05](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S06 | P1 | Gemeldete Lichtfunktion im tatsächlichen DM-Kontext prüfen | Reproduzieren | [S06](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S07 | P1 | Gemeldete Wandfunktion mit Sicht-/Lichtwirkung prüfen | Reproduzieren | [S07](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S08 | P2 | Measure-Auswahl für Kegel, Kreis/Kugel und Quadrat | Für Apply erfasst | [S08](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S09 | P2 | Hamburger, Zurück und App-Menü unterscheidbar machen | Für Apply erfasst | [S09](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S10 | P1 | Toten Back-Maps-Einstieg korrigieren | Für Apply erfasst | [S10](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S11 | P2 | Chat links und Journal rechts einordnen | Für Apply erfasst | [S11](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S12 | P2 | Journal als zentralen Datei- und Assetzugang nutzen | Für Apply erfasst | [S12](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S13 | P2 | DM-Bereiche als Karteireiter unten links bündeln | Für Apply erfasst | [S13](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S14 | P3 | Discord-Profilbild im Kontobereich anzeigen | Für Apply erfasst | [S14](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S15 | P2 | Erweiterung der Kampagnenplätze erreichbar machen | Produktgrenze klären | [S15](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S16 | P2 | Gruppen- und Leerzustandstexte passend anzeigen | Reproduzieren | [S16](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S17 | P2 | Karteneditor visuell in die übrige VTT-Oberfläche einordnen | Für Apply erfasst | [S17](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S18 | P2 | Stempel oder Kachelausschnitte als weichen Bildpinsel verwenden | Für Apply; Cachefrage offen | [S18](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S19 | P3 | Layer-Verhalten von Generate Landmass klären | Vorhanden / Frage geklärt | [S19](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |
| S20 | P2 | Karten im Kampagnenhub übernehmen und verwalten | Für Apply erfasst | [S20](FEEDBACK_UI_PLAYTABLE_2026-11-13.md) |

[Maschinenlesbarer Index](FEEDBACK_NEXT_ROUND_2026-11-13.json). Alle Karten haben `implementation_started=false`; bestehende Funktionen sind anhand der jeweiligen Belege gekennzeichnet.
