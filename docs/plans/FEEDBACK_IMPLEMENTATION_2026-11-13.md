# Umsetzung der beiden Feedbackrunden

Status: Apply / laufende Lieferung. Auftrag: Owner „researchrn planen und Implementieren“.
Die abgeschlossenen Discover-Berichte und ihre 40 Karten bleiben als historische Eingaben erhalten.
Fortschritt und Lieferbelege werden hier sowie in den jeweiligen Paketbelegen geführt.

## Reihenfolge und Grenze

| Paket | Karten | Lieferumfang | Stand |
| --- | --- | --- | --- |
| B01 | N01, S10 | Anrufungsvoraussetzungen serverseitig und in beiden Auswahloberflächen; Zurück → Karten | [Live geliefert](../proofs/feedback-b01-2026-11-13/delivery.json); Owner-Abnahme offen |
| B02 | S01, S04, S09, S11, S13, S14, S16 | Einstellungen, Kalenderstandard, eindeutige Navigation, getrennte Tischbereiche, Kontobild, Leertexte | [Live geliefert](../proofs/feedback-b02-2026-11-13/delivery.json); Owner-Abnahme offen |
| B03 | S02, S17, N19 | Gemeinsame Buchoberfläche, verbrannter Nachtstil mit roten Standardakzenten | [Live geliefert](../proofs/feedback-b03-2026-11-13/delivery.json); Owner-Abnahme offen |
| B04 | N02, N03, N04, N05, N06, N07 | Creator-Übersicht, einzelne Würfelergebnisse, vorhandene eigene Hintergründe, Merkmale, Zaubersortierung; getrennte DM-Freigabe | geplant; Freigabegrenze vor Deploy festhalten |
| B05 | N12, N13, N14, N15, N16, N17 | Objekt-/Kachelauswahl, gemeinsame Bearbeitung, namenlose Symbole, Werkzeugordnung, Wegkurven, Undo/Redo | geplant |
| B06 | N08, N09, N10, N11, N18, S18 | Pinselspitzen und Materialwahl, eigener Radierer, Bildpinsel, nachvollziehbarer Entwurfs-/Anmeldestatus | geplant; N11 wartet auf konkrete Reglerangabe |
| B07 | S06, S07, S08 | Licht/Wände im berechtigten Kontext prüfen, bestätigte Fehler beheben, Messformen | geplant |
| B08 | S05, S12, S20 | Bibliotheksvorschauen, Journal-Dateizugang, Kartenübernahme im Kampagnenhub | geplant |
| B09 | S03 | Englisches Original-SRD mit stabiler Zuordnung zur bestehenden Mechanik und Sprachwahl | geplant |
| B10 | S15 | Vorhandenen berechtigten Weg zur Kontingenterweiterung prüfen und erreichbar machen; keine automatische Kontingentänderung | geplant; Produktgrenze vor Deploy festhalten |
| B11 | alle | Kombinierter Live-Durchlauf und Owner-Testcheckliste | ausstehend |

S19 ist bereits vorhanden und belegt. N20 ist durch neuere Asset-Pakete teilweise überholt;
unbenannte weitere Kunst ist keine stillschweigende Importfreigabe. N04 verwendet zunächst
vorhandene erlaubte Hintergründe/eigene Inhalte; unbekannte Zusatzregelwerke bleiben außerhalb.
Kein Paket darf allein als Abschluss des Gesamtauftrags bezeichnet werden.

Jedes Paket erhält vor der Implementierung einen begrenzten Apply-Vertrag mit Schnittstellen,
Rollen, Kriterien und Rollout. Danach: gezielte Checks, Commit/Push, Abgleich mit tatsächlich
laufendem Image, App-Deployment auf vtt.roll-drauf.de und Prüfung über normale UI-Einstiege.
Player- und DM-Komposition sowie serverseitige Kontexte bleiben getrennt. Keine neuen
Abhängigkeiten oder externe Agenten. Unbeteiligte Änderungen im ursprünglichen Checkout bleiben unangetastet.

## Recherche und Ableitungen

- [Offizielles SRD 5.2.1](https://www.dndbeyond.com/srd) und
  [englisches Original](https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf):
  Quellen für Regelabhängigkeiten und die spätere englische Inhaltsfassung. Bestehende kanonische IDs
  bleiben erhalten; englische Anzeigenamen dürfen gespeicherte deutsche Figuren nicht umschlüsseln.
- [W3C Toolbar](https://www.w3.org/WAI/ARIA/apg/patterns/toolbar/): benannte Gruppen und
  passende Tastaturbedienung; ARIA-Rollen nur mit tatsächlich implementierter Interaktion.
- [MDN beforeunload](https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeunload_event):
  Navigation nur bei ungesicherten Änderungen warnen; Entwurfssicherung nicht allein vom Verlassen abhängig machen.
- [MDN Canvas-Komposition](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/globalCompositeOperation):
  vorhandene Canvas-Werkzeuge für Masken, Radierer und Bildpinsel weiterverwenden; unabhängige Werkzeugeinstellungen.

## Offene Eingaben

Die Bedeutung des gemeldeten „Skalieren 0 %“ ist bereits angefragt. Sie blockiert nur N11.
Der zusätzliche Donutarian-Testplatz ist separat angefragt und nicht durch diesen Arbeitsauftrag genehmigt;
synthetische Live-Fixtures ermöglichen technische Prüfung ohne Änderungen an seinen echten Kampagnen.
Konkrete Grenzen für zusätzliche DM-Bauoptionen und Slot-Erweiterungen werden anhand vorhandener APIs
festgelegt; erforderliche Produktentscheidungen bleiben sichtbar und blockieren nur den betroffenen Teil.

Retention: dauerhaft. Nächster Schritt: B01-Deploy gemäß nachstehendem separatem Vertrag.
