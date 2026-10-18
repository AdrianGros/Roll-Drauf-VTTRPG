# DAD-M Apply: Character Creator P11 (Kampagne und Teilen)

Stand: 2026-10-18, Branch `feat/creation-engine-g1`. Aufbauend auf P10. Parität: Charakter einer Kampagne zuordnen, Gruppenübersicht für die Spielleitung, Link zum Teilen (privat/öffentlich, nur lesen), Werkzeuge der Spielleitung (Stufen vergeben, Gegenstände ausgeben, Inhaltsfreigaben pro Kampagne).

## Entscheidung

- **Nur SRD-Charaktere**: Neue Endpunkte unter `/api/srd-creator/…`; Creation Engine und alte Routen bleiben unangetastet. Die Zuordnung nutzt die bestehende Route `assign_character_campaign`, ergänzt um die Regelprüfung.
- **Regeln pro Kampagne** (`campaign_srd_rules`, Migration m81): die Spielleitung legt fest, welche Attributsmethoden (Standardwerte, Punktekauf, Würfeln, Manuell) erlaubt sind. Durchgesetzt beim Abschluss im Ersteller (422 `ability_method_not_allowed` mit Liste `allowed`) und beim Zuordnen (422 mit `code`). Da bisher nur das SRD existiert, ist das die einzige Inhaltsfreigabe.
- **Gruppenübersicht** `/party?campaign=<id>`: alle Mitglieder der Kampagne sehen Karten mit TP, RK, Initiative, Bewegung, passender Wahrnehmung, Zauber-SG, Attributen und Zuständen. Zustände kommen aus den Spielfiguren der laufenden Sitzung. Die Spielleitung sieht zusätzlich EP/Fortschritt und die Werkzeuge.
- **Teilen**: Token `"<id>-<geheimnis>"`, Seite `/shared-sheet#<token>` (Fragment erscheint in keinem Serverlog). Die öffentliche Ansicht enthält keine Notizen, Hintergrundgeschichte, Besitzerdaten oder IDs, antwortet mit `no-store`, `noindex` und `no-referrer`. Erneuern macht den alten Link ungültig; Archivieren und Duplizieren löschen die Freigabe, Wiederherstellen schaltet sie nicht wieder an. "Öffentlich" heißt: jeder mit dem Link.
- **Werkzeuge der Spielleitung**: Erfahrung (an alle oder Auswahl, mit Notiz), Meilenstein-Zielstufe, Gegenstände ausgeben (Ausrüstung, magische Gegenstände, Münzen) über die Inventarmechanik mit Markierung `handedOutBy`; Zurücknehmen nur für ausgegebene Gegenstände (409 `not_handed_out`). Magische Gegenstände übernehmen den Compendium-Text wörtlich mit Quellenangabe (SRD 5.2.1, CC BY 4.0).

## Ergebnis

- **API**: `GET /campaigns/<id>/party`, `GET/PUT /campaigns/<id>/rules`, `POST /campaigns/<id>/award`, `GET/PUT /characters/<id>/sharing`, `GET /shared/<token>` (ohne Login), `GET /handout/items`, `POST /characters/<id>/handout`, `DELETE /characters/<id>/handout/<item_id>`.
- **Seiten**: `/party` (Karten, Werkzeuge, Dialog "Gegenstand ausgeben"), `/shared-sheet` (Lesebogen), Charakterbogen-Abschnitt Kampagne und Freigabe mit Link "Gruppenübersicht", Kampagnenbuch bekommt die Aktion "Gruppenübersicht".
- **Inventar/Verlauf**: Abzeichen "von der Spielleitung", Seltenheit/Einstimmung/Quelle; Verlauf nennt Ausgaben und EP-Vergaben mit Notiz.

## Tests

- `tests/test_srd_party.py` (12): Sichtbarkeit, Zustände, Regeln, Durchsetzung, Gruppen-EP, Freigabelebenszyklus, bereinigte Ansicht, ungültige Tokens, Ausgabe und Zurücknehmen mit Rechten.
- `tests/test_srd_party_browser.py` (1440 und 390 px, zwei Konten): Zuordnen, Link teilen, anonym lesen (ohne Hintergrundgeschichte), Erneuern macht alten Link ungültig, Beenden; Gruppenübersicht als Spieler (ohne Werkzeuge) und als Spielleitung (EP, Regeln, Ausgabe Ausrüstung/magisch/Münzen, Zurücknehmen); Abzeichen und Verlauf beim Spieler; kein horizontaler Überlauf, kein pageerror.

## Bekannte Lücken (ehrlich)

- Keine öffentliche Galerie: "öffentlich" bedeutet jeder mit dem Link.
- Inhaltsfreigaben pro Kampagne betreffen nur Attributsmethoden, weil nur das SRD existiert.
- Magische Gegenstände: Tabellen und Werteblöcke sind nur mit dem Compendium verlinkt, Gewicht 0.
- Spielleitung bearbeitet nicht den ganzen Bogen mit, nur Ausgabe/Rücknahme, EP und Meilenstein (Meilenstein wirkt nur bei Charakteren im Meilensteinmodus).
- Keine Benachrichtigung an den Spieler außer Verlauf und Abzeichen.
- Zustände in der Gruppenübersicht nur aus Spielfiguren der laufenden Sitzung.
- Freigabelink wird beim Archivieren/Duplizieren gelöscht.
