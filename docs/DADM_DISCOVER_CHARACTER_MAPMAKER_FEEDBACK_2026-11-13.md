# Discover: Feedbackrunde Charakterbau und Karteneditor

**Status:** Discover abgeschlossen; Übergabe in begrenzte Apply-Slices. Profil `standard`. Aufgenommen am 13.11.2026. Dauerhafte Artefakte: dieser Bericht, das [Repo-Kanban](plans/FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.md), seine [strukturierten Karten](plans/FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.json) und [Prüfbelege](proofs/feedback-round-0946-2026-11-13/checks.json). Anwendungscode und Produktion wurden in dieser Aufnahme nicht geändert. Die technische Lieferung der vorigen Runde und deren ausstehende menschliche Abnahme bleiben getrennt geführt.

## Eingabe und Abgleich

Vollständiges Protokoll `2026-11-11-0946-feedback-zu-charakterbau-und-karteneditor-1.txt`, Beginn 09:46 UTC, 17:37 min. Auswertung nach Themen und Zeitmarken; Sprecherzuordnung ist nachrangig. Anhangname und SHA256 in [source-runtime.json](proofs/feedback-round-0946-2026-11-13/source-runtime.json). Die gekürzten Action Items im Chat wurden durch den vollständigen Text ergänzt.

Abgleich gegen isolierten Feedback-Checkout `3f1857c9c` und laufende Anwendung `4b2a57332`, Image `sha256:c843eaba933bb40989b72bc9d206af177a882bea7ab89f65e69c40ad27d665f0`. Dreizehn relevante Dateien stimmen per Hash zwischen Checkout und laufendem Image überein. Das Protokoll ist älter als die letzte Lieferung; es ist kein neuer Live-Testbericht dieser Version. Der ursprüngliche Arbeitsbaum wurde nur für das ausdrücklich angehängte Protokoll gelesen und nicht verändert.

20 Karten: 14 für Apply konkretisierbar, vier mit offener Angabe/Produktgrenze/Reproduktion, zwei mit Überschneidungen zur inzwischen erfolgten Lieferung. Donutarian ist als vorgesehener Owner im Repo-Backlog erfasst; kein externer Kanban-/Nachrichtenversand wird behauptet.

## Belastbare aktuelle Befunde

| Befund | Nachweis und praktische Bedeutung |
| --- | --- |
| N01 – Anrufungsprüfung ist unvollständig. | Ein über die bestehenden Fortschrittsfunktionen aufgebauter Hexenmeister Stufe 5 wird mit Eldritch Smite ohne Pact of the Blade als `valid=true`, `complete=true`, ohne Finalisierungsblocker ausgewertet. Ein zulässiger Kontrollfall und derselbe Fall mit Voraussetzung bestehen ebenfalls. [Reproduktion](proofs/feedback-round-0946-2026-11-13/prerequisites.json). Dies ist eine reproduzierte gemeinsame Auswertungslücke, noch kein im Browser ausgeführter produktiver Charakterabschluss. |
| N03 – Würfelzählung und gewünschte Darstellung sind verschiedene Punkte. | Die bestehende Multimengen-Regelprüfung besteht. Der Creator fasst gleiche Werte weiterhin zu einer Option mit Mengen-/Verfügbarkeitstext zusammen (`srd-creator-steps.js:394`). Matt wünscht einzelne verfügbare Ergebnisse statt dieser Erklärung. |
| N04 – Hintergrund-Boni sind bereits flexibler als die Zusammenfassung vermuten lässt. | Vier SRD-Hintergründe; beide Verteilungsmuster sind in UI und Server vorhanden. Der vorhandene Hintergrundtest besteht. Zusätzliche Hintergründe sind eine Inhalts-/Auswahlfrage; P3 hat veröffentlichte eigene Hintergründe schon angebunden. |
| N05/N06 – Teilfunktionen vorhanden. | Fortschritt zeigt neue Merkmalsnamen; der Creator bietet gesonderte Unterklassentexte. Zauberauswahl besitzt einen Gradfilter. Das erfüllt weder automatisch sichtbaren vollständigen Unterklassentext noch eine Sortierung über mehrere Grade. |
| N10 – Radierer übernimmt Malwerte. | Gemeinsamer `brush` startet mit 0,9 Deckkraft und 45 Weichheit; `setTool` führt keine eigenen Radierer-Startwerte ein. Ein pauschales Skalieren auf 0 wäre aus dem unklaren Wortlaut nicht ableitbar. |
| N12/N17 – Wegpunkte und Undo funktionieren bereits. | Reale Chromium-Gesten im vorhandenen Test: Shift-Ziehen eines Wegpunkts, ganzen Weg verschieben, Undo/Redo und Projekt-Rundlauf. Kurvenmodus ist darin nicht enthalten; `drawPath` verbindet Punkte mit Geraden. Fehlende Auffindbarkeit bleibt ein echter UX-Befund. |
| N13/N14 – Stempel und Rasterkacheln verhalten sich verschieden. | Freie Stempelplatzierung existiert, Raster standardmäßig aus. Kachelebenen bestehen aus Zellen; Vergrößern kann wegen bestehender Randzellen verweigert werden. Auswahl umfasst eine ID für Vektorobjekte; Ziehen auf leerer Fläche im Auswahlmodus beginnt tatsächlich eine Pan-Geste. |
| N15 – Pflichttext ist nachvollziehbar. | Orts-/Beschriftungsobjekt startet mit Neuer Ort. UI übernimmt keinen leeren Text, Dokumentvalidator lehnt textlose Labels ab. Reine Stempel existieren separat. Ein Berg ohne Namen ist daher ein Bedarf an verständlicher Dekoration/Ortsabgrenzung, nicht zwingend ein weiterer Freitextfehler. |
| N18 – Ursache des Ausstiegs bleibt offen. | Im Protokoll folgt der Ausstieg einem Creation-Engine-Klick; ein Entwurf wird anschließend wiedergefunden. Später lässt sich das Verhalten nicht erneut auslösen. Es fehlen Ziel-URL, Antwortstatus und Alter der Anmeldung. Weder Inaktivitätslogout noch eine abgekoppelte Engine sind bewiesen. |

## Quellenprüfung und Inventar

Primärquelle ist das [offizielle SRD 5.2.1](https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf), abgerufen am 13.11.2026 über die [offizielle Downloadseite](https://www.dndbeyond.com/srd). Eldritch Smite setzt dort neben der Klassenstufe die betreffende Pakt-Anrufung voraus (S. 72–73). Die Herkunftsregeln erlauben beide genannten Bonusverteilungen auf die drei Hintergrundattribute (S. 83). Eigene Hintergründe sind im Abschnitt zur Hintergrundgestaltung beschrieben (S. 192–193). Daraus folgt keine Freigabe beliebiger zusätzlicher Regelabweichungen.

Relevante Verbraucher und bestehende Verträge:

- Creator: `creator_data.py`, generierte `creator-data.json`, `creator_rules.py`, `srd-creator-steps.js`; Fortschritt: `srd_progression.py`, `srd-progression-ui.js`. Die Anrufungsmetadaten behalten weitere Voraussetzungen bisher als Text; UI und Auswertung verwenden den numerischen Mindestlevel.
- Editor: `tools.js` für Gesten, `app.js` für Zustände/Kommandos, `ui.js` für Werkzeuge/Inspector, `document.js` für getrennte Objektverträge, `brush.js` für Spitze/Material, `render.js` für Ausgabe. History, Projektvalidierung und JSON-/ZIP-/PNG-Wege hängen an diesen Verträgen.
- Speichern/Navigation: persönlicher IndexedDB-Entwurf, Bibliotheksprojekt und private Atlas-Arbeitskopie haben unterschiedliche Lebenszyklen. Der Atlas besitzt zusätzlich Lease und explizite Publikation. Creation Engine ist ein vorhandenes Navigationsziel. Auth-Refresh und absolute Anmeldefrist sind zentral angebunden.
- Vorhandene Assets gehen heute über Kenney Tiny Town hinaus; der abgeglichene LPC-Revised-Stand ist erhalten. Zusätzliche Pinselspitzen sind damit nicht erledigt. Bekannte Nacht-/Kontrastlieferung ist im [vorigen Releasebeleg](proofs/feedback-final-2026-11-13/delivery.json) festgehalten.

## Prüfungen und Grenzen

1. Reine Auswertung mit zwei zulässigen Kontrollen und einer ungültigen Kombination; ohne Datenbank oder produktive Schreiboperation. Ausführbares Diagnoseskript im [Belegordner](proofs/feedback-round-0946-2026-11-13/prerequisites-probe.py).
2. Drei vorhandene Prüfungen bestanden in 24,46 s: Wegknoten/Undo/Redo/Projekt-Rundlauf im Chromium-Editor, Hintergrund-Bonusmuster und Zuordnung gewürfelter Werte.
3. Hashabgleich der 13 relevanten Dateien gegen das laufende Image. Dies ersetzt keine erneute Live-Abnahme einer künftigen Änderung.

Keine neue Funktion implementiert, kein neues Release ausgerollt, kein vollständiger Regel-/Browser-Regressionslauf behauptet. Der gemeldete Editor-Ausstieg wurde in diesem Discover nicht reproduziert.

## Risiken, offene Angaben und nächste Grenze

- **Medium, N01:** irreführend positives Regelprüfungsergebnis. Nächster Apply-Slice muss Creator, Fortschritt, direkte Serveranfragen und bestehende Charaktere berücksichtigen. UI-Sperren allein reichen als Prüfnachweis nicht.
- **Medium, N18:** möglicher Arbeitsverlust oder missverständlicher Speicher-/Anmeldestatus. Vor Änderungen müssen Navigation, Token-Refresh, absoluter Fristablauf, Autosave-Fehler und Atlas-Kontext getrennt reproduziert werden. Kein Beleg für eine notwendige Änderung der beschlossenen6 h-Frist.
- **Medium, N12–N16:** Änderungen an Auswahl, Kurven oder Beschriftungen können bestehende Karten, Kachelränder, Validatoren und Historygrenzen betreffen. Kompatibilität bleibt eine explizite Apply-Aufgabe; keine Objektkonvertierung ist durch dieses Discover entschieden.
- **Medium, N07:** zusätzliche DM-Bauoptionen benötigen einen klaren Geltungsbereich. Vorhandene serverautorisierte Player-/DM-Kontexte bleiben verbindlich. Allgemeines Abschalten der Regelprüfung ist aus dem Wunsch nicht ableitbar.
- **Low:** zeitlich überholte Beobachtungen könnten zu doppelter Arbeit führen. Undo, Shift-Wegpunkte, freie Stempel, Entwurfswiederherstellung, aktuelle Assets und letzte Darstellungskorrekturen erhalten.

Offen: konkrete weitere Hintergründe/Kombinationen (N04), Umfang zusätzlicher DM-Freigaben (N07), gemeinter Skalierungsregler (N11; kurze Rückfrage gestellt), Reproduktion des Ausstiegs (N18). Diese Fragen betreffen ihre jeweiligen Karten und verhindern nicht die Bearbeitung unabhängiger Punkte.

Übergabe: zuerst begrenzter Apply-Vertrag für N01 sowie Ursachenuntersuchung N18, danach Pflichtnamen/Auswahl und die aufgeführten Creator-/Editor-UX-Karten. Die vollständige vorgeschlagene Reihenfolge steht im Repo-Kanban. Architektur, Datenänderungen und Releasegrenzen sind erst in Apply festzulegen; dieser Bericht ist keine behauptete Umsetzung oder neue Deploymentfreigabe.
