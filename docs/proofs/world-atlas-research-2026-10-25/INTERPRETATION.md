# Monitor: unabhängige Desktop-Prüfung und Einordnung

25.10.2026. Reihenfolge: frische Claude-Opus-5.5-Review abgeschlossen, danach eigenständige Codex-Browserprüfung. Produktcode unverändert. **Die Recherche ist abgeschlossen; die strenge Desktop-Abnahme des Editors ist wegen bestätigter Befunde noch offen. Ein Weltatlas ist noch nicht implementiert.**

## Ergebnis und Belege

Claude hat [28 Aufgaben bewertet](claude-desktop/report.md): 16 bestanden, 8 teilweise, 2 fehlgeschlagen, 1 Funktionslücke, 1 Messung. Sein Replay reproduziert 14/14 Erwartungen einschließlich Fehlern; das ist ausdrücklich keine fehlerfreie Produktabnahme.

Codex hat anschließend eine andere Karte vom leeren Dokument aus erstellt und [24 Prüfpunkte](codex-desktop/results.json) durchgeführt: **20 bestanden, 2 teilweise, 2 fehlgeschlagen**. Vier zusätzliche [Beobachtungen](codex-desktop/edges.json) prüfen Leertasten-Verschieben mit Button-/Canvas-Fokus, Materialrouting und Entwurfswiederherstellung. Diese Zahlen werden wegen überlappender Aufgaben nicht mit Claudes Zahlen zu einer Erfolgsquote addiert.

Die Codex-Prüfung lief auf einem separaten Loopback-Server mit dem **aktuellen CSP-Header aus `vtt/__init__.py`**. Claude nutzte den bestehenden Preview-Server ohne CSP und dokumentiert das. Beide nutzten frische Playwright-Chromium-Kontexte. Root-Skripte: [review.py](codex-desktop/review.py), [edge_review.py](codex-desktop/edge_review.py). Keine produktinterne Mutation per API; `rdMapmaker.ready` diente nur zum Warten. Pointer, Tastatur, sichtbare Bedienelemente, tatsächliche Downloads und DOM-Messungen bilden die Belege.

Gesicherte Ergebnisse:

- Eigene Karte aus leerem Dokument: Land, Wald, Fluss, Weg, Gebirgs-/Stadtsymbol, drei benannte Orte mit Lore und zusätzliche reine Titelbeschriftung.
- Ebenen anlegen/umbenennen/löschen/wiederherstellen, Stempel bearbeiten/löschen/wiederherstellen und Ortsbeschreibung erneut finden/ändern funktionieren über die UI.
- Rasterdaten vor Radieren und nach Rückgängig sind in real heruntergeladenen Projektdateien identisch.
- [Projektdatei](codex-desktop/codex-waldmark.rdmap.json) und [PNG](codex-desktop/codex-waldmark.png) wurden tatsächlich heruntergeladen. PNG: 2400×1600 Pixel, SHA-256 `131889856d8d3b3de3aac397c4f737addfd7528678280d0657af9be0eb1c3bba`.
- In einem frischen Kontext wieder geöffnet: alle drei Orte und Lore vorhanden; erneut exportierte Raster-/Objektinhalte stimmen überein. [Screenshot](codex-desktop/screenshots/07-fresh-reopened.png).
- Keine JavaScript-Laufzeitfehler in den Codex-Läufen. Hilfe öffnet in allen fünf Desktop-Layouts am Anfang; der ältere mobile Hilfe-Befund wurde hier nicht als Desktop-Fehler bestätigt.

Die PNGs beider Reviewer und die hier verlinkten Workspace-/Fehlerbilder wurden tatsächlich visuell angesehen. Es sind Werkzeugprüfkarten, keine fertigen Weltkarten als Qualitätsversprechen. Farben, Typografie und Symbolstil passen zum vorhandenen VTT-Auftritt. Auf kleiner Fläche werden Text-/Symbolüberlagerungen und kurze Werkzeuglabels wie „Auswählen“ jedoch sichtbar eng.

## Bestätigte Befunde und Gewichtung

| Befund | Unabhängiger Beleg / Einordnung | Priorität |
|---|---|---|
| Datei öffnen verwirft ungesicherte Änderungen | Nach zusätzlichem Stempel: „Ungespeicherte Änderungen“. Öffnen der gesicherten Datei zeigt weder nativen noch Seitendialog; anschließend Undo deaktiviert. [Vorher](codex-desktop/screenshots/08-unsaved-extra-stamp.png), [nachher](codex-desktop/screenshots/09-open-replaced-unsaved-stamp.png) | **Hoch: E0 blockiert.** Es geht um noch nicht extern gesicherte lokale Änderungen, nicht um das Löschen vorhandener Download-Dateien |
| Leertaste + Ziehen malt bei Button-Fokus | Vorher kein Undo; nach Klick auf Pinsel und Leertasten-Drag Undo aktiv, „Rückgängig: Pinselstrich“. Gleiche Geste mit Canvas-Fokus erzeugt keinen Verlaufseintrag. [Bild](codex-desktop/screenshots/edge-space-after-tool-click.png) | **Mittel: E0 blockiert.** Die ausdrücklich erklärte Verschiebegeste darf keinen unerwarteten Strich erzeugen |
| Wiederherstellung startet mit Fokus auf Verwerfen | `restoreNo` fokussiert. Enter startet Silbermark. Nach vollständig geladener Startkarte und nächster Änderung bietet der nächste Reload nur den neuen Entwurf an. [Dialog](codex-desktop/screenshots/edge-restore-discard-default.png) | **Mittel: E0 blockiert.** Reload allein löscht den alten Entwurf noch nicht; die Abfolge Enter → neue Änderung überschreibt den einzigen Entwurfsplatz |
| Materialwechsel bleibt auf Landebene | Land → Wald → Fluss zeigt jeweils „Malt auf: Land“. Tatsächliche Datei: Land hat Alpha bis 230; Gelände und Flüsse/Wege sind vollständig transparent. [Datei](codex-desktop/routing.rdmap.json) | **Mittel: Einstiegsworkflow.** Manuelle Ebenenwahl ermöglicht die Aufgabe, ist aber ein notwendiger Umweg. Automatische Zuordnung aller Materialien ist eine mögliche Produktentscheidung, keine bereits belegte Verpflichtung aus GIMP/Inkarnate |
| Doppelklick-Ebenenname startet Umbenennen nicht | Bestätigt; expliziter Umbenennen-Button funktioniert. Erster Klick baut die Liste neu auf (`ui.js:466–469`) | **Niedrig:** funktionierender Ausweichweg |
| Überlappende Beschriftung fängt Symbolauswahl ab | Stempel bleibt bei x=1300, darüberliegender Text wird beim vermeintlichen Symbol-Drag nach x=1400 bewegt. [Bild](codex-desktop/screenshots/10-overlap-captures-label.png), [Datei](codex-desktop/overlap-inspection.rdmap.json) | **Bedienlücke:** oberstes Objekt auszuwählen ist nachvollziehbar; es fehlt ein einfacher Weg zum verdeckten Objekt |
| Projekttitel und gemalter Titel sind unabhängig | Download-Metadatum „Codex Waldmark Revision 2“, Beschriftung „DIE WALDMARK“ bleibt unverändert | **Verständlichkeit:** getrennte Titel sind legitim. Klare Benennung/Hinweis ist sinnvoller als automatisch eine bewusst gesetzte Beschriftung zu überschreiben |

Nicht jede Anmerkung von Claude wird als Fehler übernommen: Ein weicher Radierer mit 90% Deckkraft kann Restpixel hinterlassen; das folgt seinen Einstellungen. Die 500-Zeichen-Kurzbeschreibung ist ein sichtbares Limit des Prototyps, kein Nachweis beschädigter Speicherung. Eine neue Ebene über der aktiven Ebene entspricht einem üblichen Schichtenmodell. Diese Punkte brauchen verständliche Bedienung, aber keine Behauptung defekter Rasterlogik.

Auch „sichtbare IDs“ sind keine notwendige Benutzeroberflächen-Anforderung: stabile interne Referenzen werden für einen Atlas benötigt; Benutzer sollen lesbare Namen, Auswahl und Beziehungen sehen. Ebenso muss nicht jeder dekorative Baum ein Welt-Ort werden. Symbol-/Ortsverknüpfungen und eine Objektliste sind gezielte Erweiterungen für den Atlas; Gruppen, Sperren und Mehrfachauswahl sind gesondert zu priorisieren.

## Tatsächliche CRUD-Abdeckung

`Ja` bezeichnet vorhandene UI-Funktionen. Rasterkorrektur ist bewusst nicht mit dauerhaftem Einzelobjekt-CRUD gleichgesetzt. Die vollständige [Claude-Matrix](claude-desktop/crud-matrix.json) trennt zusätzlich UI-Belege und reine Quellenbefunde.

| Ebene / Element | Create | Read / wiederfinden | Update | Delete / Wiederherstellen | Urteil |
|---|---|---|---|---|---|
| Einzelprojekt | Neue leere Karte / Vorlage | Datei öffnen, ein Browserentwurf | Titel und Inhalt | Durch andere Karte ersetzbar; kein Projektkatalog/Papierkorb | **Nur teilweise Projekt-CRUD**; Öffnen unsicher |
| Rasterebene | Ja | Ebenenliste / Sichtbarkeit | Name, Reihenfolge, Deckkraft, Küsteneffekt / Pixel | Ebene löschen + Undo | **Vorhanden**, Doppelklick-Umweg |
| Rasterstrich / gemalter Wald / Fluss / Weg | Malen | Sichtbares Raster | Übermalen / Radieren | Radieren / begrenzter zeitlicher Verlauf | **Kein eigenständiges Objekt-CRUD** nach dem Zusammenführen |
| Stempel | Ja | Sichtbar auswählen | Position, Größe, Drehung, Spiegelung | Löschen + Undo | **Vorhanden**; verdeckte Objekte schwer erreichbar |
| Reine Beschriftung | Ja: Ortsart „Nur Beschriftung“ | Sichtbar auswählen | Text, Stil, Größe, Position usw. | Löschen + Undo | **Vorhanden**; keine vollständige Objektliste |
| Ort mit Art / Kurzbeschreibung | Ja | Ortsliste + Auswahl | Name, Art, Lore, Darstellung | Löschen + Undo | **Vorhanden**, derzeit Metadaten am Textobjekt |
| Eigenständige editierbare Fluss-/Weglinie oder Regionsfläche | Nein | Nein | Nein | Nein | **Nicht implementiert** |
| Welt / Kontinent / Region / Stadt mit verknüpften Karten | Nein | Nein | Nein | Nein | **Nicht implementiert** |
| Weltmitglieder, Rollen, gemeinsame Serverentwürfe | Nein | Nein | Nein | Nein | **Nicht implementiert** |
| Dauerhafte Gruppenpositionen / Atlasfreigaben | Nein | Nein | Nein | Nein | **Nicht implementiert** |

Damit ist die Antwort auf „komplette CRUD-Hierarchie schon vorhanden?“ **Nein.** Basis-CRUD für die vorhandenen Ebenen, Stempel und Orts-/Textobjekte ist weitgehend vorhanden; vollständige Projektverwaltung, semantische Rasterelemente und Welt-Hierarchie fehlen.

## Arbeitsfläche und visuelle Struktur

| Desktop-Layout | Canvas-Element | Eingepasste 2400×1600-Karte | Einordnung |
|---|---|---|---|
| 1440×900 | 1052×848 CSS-Pixel | ca. 1020×680 | Gut nutzbare Grundfläche |
| 1280×720 | 892×668 | ca. 860×573 | Durchgängiger Desktop-Weg möglich |
| 1024×768 | 636×716 | ca. 604×403 | Karte belegt nur ca. 31% der gesamten Ansichtsfläche; fixe 312-Pixel-Seitenleiste fällt stark ins Gewicht |
| 1440×900 bei 125%-Layoutäquivalent | 764×668 im CSS-Viewport 1152×720 | ca. 732×488 | Weniger Platz, Hauptaktionen erreichbar |
| 1280×720 bei 125%-Layoutäquivalent | 636×524 im CSS-Viewport 1024×576 | ca. 604×403 | Eigenschaften/Palette teilweise scrollbar; Fokusansicht wäre wertvoll |

Canvas-Elemente wurden von Codex gemessen; ungefähre Bildgrößen werden hier aus der Fit-Formel mit 32-Pixel-Rand berechnet. Claude schätzt sie aus gerundetem Zoom geringfügig anders (z.B. 600 statt 604 Pixel). Das ist keine Layoutregression. [1024-Screenshot](codex-desktop/screenshots/1024x768-workspace.png).

Die 125%-Fälle emulieren CSS-Viewport und DPR 1,25. Sie testen den verfügbaren Layoutplatz, **nicht** die tatsächliche Zoom-Bedienung eines nativen Browserfensters. Keine Behauptung über Firefox/Safari, echten Stiftdruck, mobile Geräte oder authentifizierten Roll20-/Kampagnenbetrieb.

## Grenzen und Nachvollziehbarkeit

Zwei Hilfsskript-Annahmen wurden vor dem gültigen Abschlusslauf korrigiert: Eine Beschriftung ohne Nadel ist weiterhin ein Ort, solange die Ortsart nicht „Nur Beschriftung“ ist; außerdem muss nach „Neue Startkarte“ das Laden abgeschlossen sein, bevor der nächste Edit geprüft wird. Erste Ausgaben/Dateien liegen unter `codex-desktop/attempt1/`. Diese Anläufe werden weder als Produktfehler noch als bestandene Abnahme gezählt. Es gab keine Produktkorrektur zwischen den beiden Reviewern.

Die ausstehenden mobilen und früheren Security-Prüfungen bleiben eigene Themen; diese Desktop-/Recherchearbeit ersetzt sie nicht. Es wurde keine neue allgemeine pytest-Runde durchgeführt: ohne Codeänderung war der neue Endnutzerweg mit tatsächlichem Speichern/Öffnen und gezielter Reproduktion die relevante Verifikation. Bereits vorhandene Prüfzähler wurden nicht wiederverwendet.

## Empfohlene nächste Aktion

Den [Apply-Plan](../../WORLDBUILDING_ATLAS_PLAN_2026-10-25.md) als Planungsgrundlage verwenden. Als nächsten begrenzten Claude-Auftrag zunächst E0 schließen: Speicherschutz, sicherer Wiederherstellungseinstieg, fokusunabhängiges Verschieben und verständlicher Material-/Ebenenworkflow. Codex reproduziert danach genau diese Fälle und den Datei-Rundlauf erneut. Erst anschließend E1 als vollständigen kleinen, bereits gemeinsamen Weltatlas umsetzen. Die vorliegenden mittel-/hochgradigen Befunde sind offen, nicht still akzeptiert.
