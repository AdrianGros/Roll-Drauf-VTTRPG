# DAD-M Apply: Character Creator P6 (Würfe aus dem Bogen, Token-Verknüpfung)

Stand: 2026-10-18, Branch `feat/creation-engine-g1`. Aufbauend auf P5 (regelbasierter Bogen). Parität: Discover-Punkte 28 (Würfe in das Tischprotokoll) und 44 (Token-Verknüpfung).

## Ergebnis

- **Würfe vom Bogen**: Im Abschnitt "SRD 5.2.1 · Regelwerk-Bogen" sind alle Werte anklickbar: Attributsprobe und Rettungswurf je Attribut, alle 18 Fertigkeiten, Initiative, Todesrettungswurf, Zauberangriff je Zauberklasse. Ein Umschalter wählt Normal, Vorteil oder Nachteil. Das Ergebnis erscheint oben am Bogen (mit kritisch/Patzer-Hinweis, Verlauf der letzten Würfe).
- **Serverseitig**: `POST /api/srd-creator/characters/<id>/roll` (`kind`, `key`, `mode`, `visibility`). Der Client wählt nur, *was* gewürfelt wird; Modifikator und Würfel kommen vom Server aus der frisch ausgewerteten Regelrechnung (Mira: Arkane Kunde +10, INT-Probe +4, INT-Rettungswurf +7). Berechtigt sind Besitzer und Spielleitung der Kampagne.
- **Tischprotokoll**: Läuft eine Sitzung (`in_progress`) der Kampagne des Charakters (bevorzugt die des Charakter-Tokens), wird der Wurf als `dice_roll`-Chatnachricht gespeichert und per Echtzeit an den Tisch gesendet ("Mira Eulenfeder · Arkane Kunde (Vorteil): würfelt 1d20+10: 14 +10 = 24"). Ohne laufende Sitzung bleibt der Wurf auf dem Bogen sichtbar ("nur hier"). Blind-/Nur-ich-Würfe sind der Spielleitung vorbehalten, bei Spielern wird öffentlich gewürfelt.
- **Token-Verknüpfung**: Beim Platzieren eines Tokens (Tisch, Socket und REST) kann ein Charakter der Kampagne gewählt werden (Auswahlfeld "Charakter verknüpfen", nur wenn es verknüpfbare Charaktere gibt; `GET /api/play/campaigns/<c>/sessions/<s>/linkable-characters`). Der Token übernimmt TP, TP-Max und einen Bogenauszug (RK, Stufe, Initiative, Übungsbonus, passive Wahrnehmung, Bewegung) in `metadata_json.sheet`.
- **Prüfung der Verknüpfung**: gleiche Kampagne, Spieler nur eigene Charaktere, Spielleitung alle, höchstens ein Token pro Charakter und Sitzung. Das schließt auch die bisher ungeprüfte REST-Anlage mit beliebiger `character_id`.
- **Trefferpunkte in beide Richtungen** (nur SRD-Charaktere): TP-Änderung am Token wird auf den Charakter geschrieben (auf 0..Maximum begrenzt, TP-Max bleibt der Wert aus der Regelrechnung). Änderung der aktuellen TP am Bogen wird an alle offenen Tokens in nicht abgeschlossenen Sitzungen gesendet (`token:updated`).
- **Nebenbei behoben**: REST-Token-Anlage versteht nun das vom Client gesendete verschachtelte `token`-Objekt (der REST-Ausweichweg schlug sonst mit "token name required" fehl). Beschriftungen der Kacheln im Bogen brechen um statt abgeschnitten zu werden.
- Creation Engine bleibt unangetastet; für deren Charaktere ändert sich am Token-Verhalten nichts (Link-Logik greift nur ohne CE-Adapter, TP-Durchschreiben nur für SRD-Charaktere).

## Tests

- Neu `tests/test_srd_rolls.py` (10 Tests): Modifikatoren aus der Regelrechnung, Vorteil/Nachteil, ungültige/verbotene Würfe, Protokollierung in laufender Sitzung (Besitzer und SL), keine Protokollierung ohne laufende Sitzung, Verknüpfungsregeln (fremder Charakter, andere Kampagne, doppelt, unbekannt), TP-Fluss in beide Richtungen inkl. Klammerung und abgeschlossene Sitzung, Socket-Anlage und -Update.
- `tests/test_srd_sheet.py`: neuer Browsertest (1440/390 px) klickt Fertigkeit, Rettungswurf mit Vorteil und Zauberangriff, prüft Ergebnisanzeige, Verlauf, kein horizontales Scrollen.
- Regression grün: Regelwerk-Suite, Ersteller-API, Token-/Kampf-/Spieltisch-Tests, `tests/creation_engine`, Playwright-Chromium-Tests der Spieltisch-Oberfläche.

## Bekannte Lücken (ehrlich)

- Waffen-Angriffs- und Schadenswürfe fehlen bis zum Inventar (P7).
- Zustände (Conditions) werden nicht zwischen Bogen und Token synchronisiert.
- Die Auswahl im Platzieren-Panel des Spieltischs ist nicht per Browsertest abgedeckt (Backend und Socket sind getestet).
- Ein Wurf ohne laufende Sitzung wird nicht nachträglich protokolliert.
- Bogen-Änderungen von TP-Max/RK wirken erst über den Ersteller; Respec/Stufenaufstieg (P8/P10) schieben die neuen Werte dann über denselben Push an die Tokens.
