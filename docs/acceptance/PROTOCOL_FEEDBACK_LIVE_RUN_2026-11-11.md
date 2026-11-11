# Ein gemeinsamer Live-Abnahmelauf für das Protokollfeedback

Status: **vorbereitet / NOT_RUN**. Stand: 11.11.2026. Aufbewahrung: dauerhaft.
Dies ist ein geplanter Sollablauf, kein Nachweis bereits gelieferter neuer Pakete.
[Programmplan](../plans/PROTOCOL_FEEDBACK_PROGRAM_2026-11-11.md) ·
[Ausführungsstatus](../plans/PROTOCOL_FEEDBACK_EXECUTION_2026-11-11.json).

## Wann der Owner startet

Erst nach technischer Bereitmeldung für P1–P6 und gemeinsamer Prüfung in P7.
Die Zwischenabnahmen übernimmt der Agent. Der Owner erhält einen Terminablauf,
einen Releasezustand und einen normalen UI-Einstieg auf
[Live-VTT](https://vtt.roll-drauf.de), keine versteckte Sonder-URL.
Zusatzinhalte mit fehlender Quelle/Freigabe werden vorab konkret genannt.

Ein zusammenhängender Termin mit Charaktervorbereitung, Kartenarbeit und einer
kurzen abgeschlossenen Spielsitzung ist vorgesehen. Planungsannahme: ungefähr
90–150 Minuten, abhängig von Runde und Rückmeldungen; keine Zeitgarantie.
Für VTT-31 braucht es eine reale DM und mindestens einen weiteren menschlichen
Player, davon einen in Firefox. Ein alleiniger Zwei-Browser-Test prüft Funktionen,
schließt aber die menschliche Spielabend-Karte nicht ab. Owner kann die private
Abnahme vorbereiten; eine öffentliche Streamingfreigabe entsteht daraus nicht.

## Vorbereitete, isolierte Testdaten

Der Agent legt vor der Bereitmeldung ausschließlich gekennzeichnete eigene
Testdaten an bzw. nutzt ausdrücklich dafür bereitgestellte Konten. Keine
bestehenden privaten Kampagnen oder Charaktere umschreiben.

| Objekt | Erforderlicher Zustand |
| --- | --- |
| Kampagne und Tisch | „Feedback-Abnahme“, aktive DM und Player; separate zweite Session für Isolationsprüfung. |
| Charaktere | Martialischer und zauberkundiger Charakter; Rüstung/Schild, Münzen, mehrere Zaubergrade, nachvollziehbare Boni. |
| Homebrew | Ein erlaubter Hintergrund und ein Merkmal mit gepinnter Revision; zusätzlich ungültiger eigener Entwurf nur zur Diagnose. |
| Tisch | Eigene zugeordnete Tokens, erlaubtes Angriffsziel; persönliche belegbare Aktionsleiste. |
| Karten | Leeres eigenes Projekt plus wieder ladbares Projekt mit zwei Ebenen und Ort. Keine bestehende Ownerkarte überschreiben. |
| Atlas | Eine eigene Testwelt mit Welt-, Regional- und Ortskarte, zwei Autoren, einem Leser; deutlich unterscheidbare private und veröffentlichte Lore. |
| Datenende | Als Testdaten markiert; nach Ergebnisaufnahme gezielt entfernen. Auf Wunsch bleibende Beispiele getrennt benennen. |

Die sichtbaren Namen/konkreten Navigationslabels werden bei P7 mit der tatsächlichen
UI abgeglichen. „Als Spieler/DM eintreten“, „Aktionen belegen“, „Landmasse“ und
„Atlas“ sind unten **geplante** Einstiege, heute keine Existenzbehauptung.

## Technische Vorbedingungen – bereits vor dem Owner-Termin prüfen

- Release-Commit, Pushstatus, Image-ID, aktive Compose-Dateien und Rückweg erfasst.
- Rollen-/Ressourcen-/Tabmatrix einschließlich direkter HTTP-/Socket-/Legacy-
  Negativfälle bestanden. Der Owner muss keine manipulierten Anfragen bauen.
- Firefox↔Firefox und Chromium↔Firefox, Reconnect, Request-Dedup und Sessionisolation
  automatisiert geprüft. Aktuelle Browser-/Versionsdaten im Beleg erfassen.
- Migration/Backup und Rückweg für neue Datenverträge geprüft; keine Behauptung
  eines ausgeführten Rückrollens, wenn nur dessen Plan geprüft wurde.
- Hauptwege in DE/EN, Pergament/Nacht und kleinen Viewports geprüft; alle neuen
  Seiten über normale Navigation für die vorgesehenen Rollen erreichbar.
- Keine offenen technischen Befunde mittlerer oder höherer Schwere im freizugebenden
  Umfang. Offene externe Angaben sind einzeln sichtbar abgegrenzt.

## Der zusammenhängende Owner-Lauf

| ID | Rolle / Einstieg | Tätigkeit | Erwartetes Ergebnis |
| --- | --- | --- | --- |
| A01 | Player → Übersicht → Charaktere → Held anlegen | Würfelset mit Duplikaten zuweisen, Ausrüstungspaket wechseln, Stufenmerkmale/Zauberauswahl prüfen, finalisieren; Kampagnensuche/Gruppenübersicht öffnen. | Keine verlorenen Würfelsummen, passende Startausrüstung, lesbare Auswahl, richtige Stufen; direkte Creator-Route und erlaubte Gruppenübersicht. |
| A02 | Autor/DM → Creation Engine → bestehender Homebrew-Arbeitsplatz → Charaktererstellung | Eigenen Hintergrund/Merkmal prüfen und veröffentlichen; berechtigten Inhalt auswählen. Einen ungültigen eigenen Entwurf prüfen. | Fehler sind verständlich, ungültiger Inhalt bleibt unveröffentlicht; erlaubte Revision erscheint im Creator/Bogen. Ein späterer Entwurf verändert die fertige Figur nicht. |
| A03 | Player → eigener Bogen | Spielen/Zauber/Inventar/Merkmale/Verwaltung wechseln, Münzen und angelegte Gegenstände ändern; mehrere Bonus-Herleitungen öffnen. | Kompakter Bogen, Bilder/Klasse/Stufe, Gradfilter und Inventarwerte stimmen. Herleitung erklärt angezeigten Wert; keine doppelt addierten Beiträge. |
| A04 | Player/DM → Darstellungs-/Sprachauswahl; danach Bogen und Tisch | Pergament/Nacht, DE/EN und m/ft wechseln, neu laden; kalibrierte Tischdistanz messen. Optional Sticky-Porträt probieren. | Einstellung bleibt; Texte und Zustände lesbar; Einheit verändert keinen Spielwert. Unkalibrierte Karte zeigt keine erfundenen Meter. |
| A05 | Berechtigter Owner/DM → Kampagne → Tisch: ausdrücklich als Player; separater DM-Tab | Player-Einstieg und DM-Einstieg getrennt nutzen; Player-Tab neu laden und reconnecten; ausdrücklich wieder als DM eintreten. | Player-Oberfläche hat keine DM-Werkzeuge/Geheimnisse; anderer DM-Tab verändert seine Rechte nicht. Rückkehr zu DM erfolgt nur ausdrücklich. Technische Negativtests sind separat belegt. |
| A06 | Player → Tisch → eigener Token → Aktionen belegen | Fertigkeit, Rettungswurf, Waffe und unterstützten Zauber belegen, umordnen, entfernen, neu laden, auslösen; beim Chatten Ziffern eingeben; Zielwahl abbrechen. | Persönliche Belegung bleibt; nur berechtigte Aktionen, korrekte Ziele, kein unbeabsichtigter Würfelwurf während Texteingabe; Ressourcen-/Nichtunterstützungsgrenzen klar. |
| A07 | DM und Player/Firefox → derselbe Tisch | Beide würfeln, Ergebnisse vergleichen; Player-Verbindung kurz unterbrechen, wieder beitreten und weiterwürfeln. | Gleiche bestätigte Ergebnisse, keine Doppelanzeige durch Replay, klarer Resync. Andere Session bekommt nichts. Sessionisolation zusätzlich automatisiert nachgewiesen. |
| A08 | DM/Autor → Karten → leere/eigene Karte | Malen → rechts ziehen → weitermalen; Ebene hinzufügen/wechseln, Ort auswählen/umbenennen, speichern/neu öffnen. | Kein ungefragtes Silbermark-Template; Pan verändert keine Dokumentrevision/Undo; Werkzeug, Ebenen und Ortsänderung bleiben korrekt. |
| A09 | Autor → Karteneditor → Landmasse | Seed-Vorschau erzeugen, abbrechen; erneut mit gleichem Seed erzeugen, bewusst übernehmen, Undo/Redo und Export/Import. | Gleiche Vorschau bei gleichen Parametern; Abbruch erhält Karte; Übernahme ist eine Undo-Aktion; vorhandene Inhalte und Rundlauf bleiben erhalten. |
| A10 | Autor → Atlas → Welt → Karte → Ort; danach Leser | Ort mit Region/Detailkarte verknüpfen, private und öffentliche Lore setzen, gezielt publizieren; Leser folgt Links. Zweiter Autor öffnet dieselbe Karte. | Stabile Links; Leser sieht nur freigegebene Inhalte/Assets, keinen Entwurf. Bearbeitungskonflikt überschreibt nichts unbemerkt; Welt nach Reload/Export-Import konsistent. |
| A11 | Player/Autor → vorhandener Assetkatalog/Credits und Regelquellen | Repräsentatives vorhandenes Asset und Quellenangabe öffnen; Liste inputabhängiger Zusätze mit Bereitmeldung vergleichen. | Bestehender Katalog/Attribution erhalten. Keine als fertig ausgegebene neue Datei oder Regelübersetzung ohne Quelle/Rechte. Fehlende Zusätze bleiben ausdrücklich offen. |
| A12 | Menschliche DM-/Player-Runde → vorbereitete kurze Spielsitzung | Einen abgeschlossenen Erkundungs-/Begegnungsablauf mit Initiative, Bewegung, Angriff, Zauber, Schadens-/Inventaränderung und Ortswechsel spielen; Feedback erfassen, normal abmelden. | Der gesamte Ablauf funktioniert zusammen; Firefox-Player bleibt handlungsfähig, Rechte gelten weiter, Feedback enthält Repro und Soll/Ist; Logout erreichbar. |

A01–A04 bereiten Figuren vor, A08–A10 die Welt; A05–A07 werden beim Tischbeitritt
und während A12 genutzt. So entsteht ein Termin mit einer echten Spielsitzung,
kein Zwang zu zwölf getrennten Abnahmen. Bereits gelieferte Punkte laufen mit.

## Ergebnisbogen – erst bei Durchführung ausfüllen

- Zeitpunkt, Durchführende und Rollen: **nicht durchgeführt**.
- Sourcecommit / Remote-Push / Image-ID: **für Gesamtrelease noch offen**.
- Browser-/Versionsdaten und UI-Einstiege: **bei P7 einzutragen**.
- Technische Prüfbelege / Migration / Rückweg: **für neue Pakete noch offen**.
- Pro A01–A12: `NOT_RUN`, danach `PASS`, `FAIL` oder `BLOCKED` mit Beleg.
- Feedbackfelder: Fall-ID, Rolle, Weg, Soll, Ist, Reproduktion, Schwere,
  Screenshot/Log ohne Geheimnisse, Folgepaket, Status.
- Weiter offene Eingaben/Produktentscheidungen: I01–I05 laut Ausführungsdatei;
  sie werden weder automatisch erledigt noch durch allgemeine Zustimmung ersetzt.

Technische Fehler werden gezielt behoben und die betroffenen zusammenhängenden
Schritte erneut geprüft. Nach einem Code-/Imagewechsel wird die Releaseidentität
aktualisiert. Erst dokumentierte echte Ergebnisse schließen Akzeptanzfälle;
VTT-31 erst nach der tatsächlich gespielten menschlichen Runde.
