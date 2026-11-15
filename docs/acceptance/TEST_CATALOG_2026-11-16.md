# VTT-Testkatalog für 16.–22.11.2026

Status: zur menschlichen Durchführung vorbereitet; **alle 20 Ergebnisse NOT_RUN**.
Ziel: https://vtt.roll-drauf.de über die normale Hauptnavigation. Eine DM und ein
Firefox-Spieler; optional zweiter Player-Tab derselben DM. Desktop und 390-px-Mobilansicht.
Eigene Testfiguren/Kartenkopien verwenden. Bestehende Kampagnen/Quotas nicht überschreiben.
Technische Checks im Lieferbeleg sind separate Nachweise und keine Owner-Abnahme.

Montag zuerst P1 (Geheimnisse, Regeln, Datenbestand); anschließend P2-Funktionsreisen;
zum Ende eine vollständige Begegnung. N07/S15 sind noch keine testbereiten Lieferungen,
N11 bleibt zurückgestellt. Ein vierter echter Donutarian-Testplatz benötigt weiterhin
seine konkrete Freigabe; vorhandene Tests oder technische Fixtures blockiert das nicht.

| ID | Prio | Rollen / Einstieg | Beobachtbares Abnahmekriterium | Bezug |
| --- | --- | --- | --- | --- |
| T01 | P1 | Player → Charaktere → Erstellen | Unzulässige Anrufung ohne nötige Voraussetzung bleibt gesperrt; erlaubte Wahl lässt sich finalisieren. | N01/B01 |
| T02 | P2 | Player → Creator → Klasse/Attribute/Hintergrund/Aufstieg/Zauber | Details lesbar, doppelte Würfelergebnisse einzeln zuweisbar, erlaubte Boni korrekt; Unterklassenmerkmale sichtbar; Sortierung Grad/Name bleibt nachvollziehbar. | N02–N06/B04 |
| T03 | P1 | Autor → Creation Engine → veröffentlichte Revision → Player-Creator | Entwurf verändert keine fertige Figur; nur bereits berechtigte Inhalte nutzbar. Neue kampagnenbezogene Allowlist N07 ausdrücklich noch offen. | frühere P3/C02, N07 Grenze |
| T04 | P2 | Player → eigene Figur → Bogen/Bilder/Inventar | Bild ersetzen/entfernen und Kopie ändern; Münzen/Ausrüstung/Bonusquellen nach Reload korrekt. Compendium → Zum Charakter führt zum bestätigten Bestand/regelkonformen Aufstieg. | C02/C08 |
| T05 | P2 | Beide → Zahnrad → Papier/Nacht, DE/EN | Lesbare Buchoberfläche/rote Nachtakzente, einheitlicher Editor; Zahnrad rechts; eigene Namen unverändert, Discordbild/Leertexte sinnvoll; Einstellungen nach Reload erhalten. | S01/02/09/14/16/17, N19 |
| T06 | P2 | Beide → Kampagnen → Kalender/Hub | Voller Monat auch leer; DM legt Sitzung/Abstimmung an, Player stimmt ab; beide sehen dieselbe bestätigte Sitzung einmal; Serie gezielt beenden. | S04/C06 |
| T07 | P1 | Beide → Hub → Charakter/Chat → Gespräche | Nachricht bleibt privat, antworten/reload; kein Eintrag im öffentlichen Tischchat. | C07/B02 Chatordnung |
| T08 | P2 | DM → Hub → Kartenbibliothek; Tisch → Seiten → Bibliothek | Vorschau und Label, Übernahme der richtigen Karte; Quelle bleibt private editierbare Kopie; Player sieht nur freigegebenes Bild. | S05/S20/B08, S10/B01 |
| T09 | P2 | Beide → Tisch → Journal | Eigene Dateien/Tokens erreichbar; hochladen/auswählen/entfernen im berechtigten Umfang; Player erhält keine privaten DM-Dateien; Journal rechts, Chat links. | S11/S12/B02/B08 |
| T10 | P1 | DM + Player → Tisch → Licht/Wand/Fog | DM erstellt Licht/Wand, Auswirkung für Player prüfen; Player-Reconnect erhält gültige Sicht, keine geheimen Wanddaten; Änderungen nach Reload da. | S06/S07/B07 |
| T11 | P2 | Beide → Tisch → Messen | Menü mit Weg/Kegel/Kreis/Quadrat; Abbruch entfernt lokale Messung; Einheiten plausibel. Maßstab speichern/löschen mit Player-Rückmeldung erneut prüfen (bekannter älterer Testfehler). | S08/B07, C01 Maßstab |
| T12 | P1 | DM → Tisch → Layers | DM-Layer wählen, mehrere Tokens dort platzieren: Player sieht weder Tokens noch Namen/Anzahl. Wechsel zur Player-Ebene gibt die Tokens nicht automatisch frei. | neuer Layer-Slice |
| T13 | P1 | DM → Layers → Wählen; Player parallel | Auswahlrahmen/Shift-Klick zeigt Bild bzw. Initialen, Grundname und Anzahl; etwa Goblin × 2. „Spielern zeigen“ macht genau diese sichtbar; „Verbergen“ entfernt sie wieder, auch nach Player-Reload/Reconnect. | neuer Layer-Slice |
| T14 | P2 | DM → Wählen → Strg/Cmd+C/V | Einzel-/Gruppenkopie am Zeiger, Abstand bleibt; Kopien erhalten neue Namen und volle HP. Einfügen erfolgt im gewählten Layer; Tippen im Chat löst keine Kopie aus. | 4158a0c4b + Layer-Slice |
| T15 | P1 | DM ausdrücklich als Player, daneben DM-Tab | Player lädt keine DM-Steuerung/Handler und erhält keine Geheimnisse; Reload/Reconnect/zweiter Tab ändern seine Rechte nicht. Wieder DM nur durch ausdrücklichen Eintritt. | P1/C01 + Layer-Slice |
| T16 | P2 | Autor → Karten → eigene Kopie | Objekte/Kacheln gemeinsam auswählen, skalieren/verschieben, namenloses Symbol, gekrümmten Weg, Undo/Redo; Speichern/Öffnen/JSON/ZIP/PNG erhält Ergebnis und Credits. | N12–N17/B05, B06a |
| T17 | P2 | Autor → Karten → Pinsel/Radierer | Form/Farbe/Textur und Bildpinsel aus Stempel/Kachel; eigener Radierwert; Wechsel überschreibt Pinsel nicht; Desktop und schmal klickbar. | N08–N10/S18/B06 |
| T18 | P1 | Autor → Karten → ungesicherte Arbeit → Verlassen/erneute Anmeldung | Warnung nachvollziehbar, Abbruch erhält Arbeit; Entwurf nach erneuter Anmeldung wiederherstellbar, kein unbeabsichtigtes Überschreiben. | N18/B06 |
| T19 | P2 | Autor → Landmasse; Atlas → Welt/Leservorschau; Regelwerk → English original | Seed reproduzierbar; Übernehmen neue Ebene, Undo/Redo korrekt. Atlas private Lore bleibt geheim bis bewusster Veröffentlichung, Backup/Restore korrekt. Englisches PDF öffnet/lädt, deutsche Quellen bleiben erhalten. | S19, C05/C09, S03/B09 |
| T20 | P1 | DM + Firefox-Player → echte kurze Begegnung | Eintritt, eigene Hotbar, Würfel einmal bei beiden, Initiative, Bewegung, Angriff/Zauber, Schaden/Inventar, Layer-Reveal und Kartenwechsel; kurzer Reconnect, normales Verlassen. | A12/B11 und gesamter Release |

Für jedes Ergebnis erfassen: Datum, Tester, Rolle, Browser/Breite, Releasecommit,
Status PASS/FAIL/BLOCKED, konkreter Klickweg und erwartet/tatsächlich; Screenshot
bei Fehlern. Keine Abnahme aus einem anderen Build übernehmen. FAIL erhält einen
begrenzten Folgeauftrag und eine gezielte Nachprüfung, keine pauschale Gesamtfreigabe.

Maschinenlesbare Ergebnisvorlage: [TEST_RESULTS_2026-11-16.csv](TEST_RESULTS_2026-11-16.csv).
Abnahme gilt erst nach tatsächlicher Durchführung. Der Layer-Lieferbeleg enthält
die technischen Tests und die bei der Bereitstellung beobachteten Live-Reisen.

## Ergänzung für echte Handys

Die Gerätefälle M-H01–M-H07 stehen im
[Handy-Katalog](../MOBILE_COMPATIBILITY_2026-11-15.md). Sie ergänzen die 20 Fälle
oben und bleiben auf Hardware NOT_RUN, bis ein tatsächliches Ergebnis vorliegt.
Chromium-/WebKit-Automatik ist keine menschliche Geräteabnahme.
