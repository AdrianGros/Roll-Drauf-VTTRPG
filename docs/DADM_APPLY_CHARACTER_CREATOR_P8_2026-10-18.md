# DAD-M Apply: Character Creator P8 (Stufenaufstieg 2-20, EP und Meilensteine)

Stand: 2026-10-18, Branch `feat/creation-engine-g1`. Aufbauend auf P7. Parität: Discover-Punkte Stufenaufstieg, Erfahrungspunkte, Meilenstein-Fortschritt, Trefferpunkte pro Stufe, Unterklasse, Attributswerterhöhung/Talent, Klassenwahlen, Zauber beim Aufstieg.

## Entscheidung

- **Eine Regelrechnung für alles**: Ein Stufenaufstieg hängt eine Stufe an `state.levels` an und läuft durch dieselbe `creator_rules.evaluate` wie die Erstellung. Der Server speichert nur, wenn keine Blocker offen sind; damit ist jede Stufe 1-20 aller 12 Klassen regelkonform (Zauber, Unterklassen, Epische Gabe, Expertise, Anrufungen, Metamagie).
- **Erfahrung nur noch über den Fortschrittsweg**: `xp` ist für SRD-Charaktere im allgemeinen `PUT /api/characters/<id>` gesperrt (409 `srd_character_managed`). Das Feld im Bogen ist gesperrt, der Abschnitt "Stufe und Erfahrung" ersetzt es.
- **Zwei Modi**: Erfahrungspunkte (Stufe laut SRD-Tabelle) oder Meilensteine (Spielleitung gibt bis Zielstufe frei). EP/Modus/Freigabe verwaltet die Spielleitung der Kampagne, bei Charakteren ohne Kampagne die Besitzerin oder der Besitzer. Aufsteigen darf nur die Besitzerin bzw. der Besitzer.
- **Bestehende Wahlen bleiben fest**: Unterklasse, einmalige Wahlen, Zauberbuch-Einträge und Expertise können beim Aufstieg nur ergänzt, nicht entfernt werden (409 `*_locked`). Optimistische Sperre über `expectedLevel` (409 `level_conflict`).

## Ergebnis

- **API** (`vtt/characters/srd_progression.py`, Endpunkte in `srd_creator.py`): `GET/PUT /api/srd-creator/characters/<id>/progression` (Status, Verlauf, EP vergeben/setzen, Modus, Freigabe, Notiz), `POST .../level-up/preview` (was der nächste Aufstieg verlangt, Blocker, TP-Zuwachs), `POST .../level-up`.
- **Trefferpunkte**: fest (Würfel/2+1) oder gewürfelt (1 bis Würfel), plus Konstitutionsmodifikator; aktuelle TP steigen um den Zuwachs. Stufe, Klasse, RK, TP max., Attribute, Übungsbonus und EP-Schwelle werden mitgeführt; offene Tische erhalten die Werte (Token-Push).
- **Oberfläche** (`srd-progression-ui.js`): Stufenbalken mit EP, Verwaltung für die SL (EP vergeben, Notiz, Modus, Freigabe), Schritt-für-Schritt-Assistent im Bogen: TP, Unterklasse, Attributswerterhöhung (+2 / +1+1) oder Talent bzw. Epische Gabe, Klassenwahlen (Waffenbeherrschung, Anrufungen, Metamagie, Sprachen …), Expertise, Zauber/Zauberbuch mit Suche, Live-Prüfung mit Blockern, Bestätigen erst bei vollständiger Wahl. Verlauf einklappbar.
- **Layout**: Der Charakterbogen ist jetzt eine durchgehende, längere Seite statt zweier Spalten, damit rechts keine leere Fläche bleibt (auf Wunsch).
- Creation Engine bleibt unangetastet.

## Tests

- Neu `tests/test_srd_progression.py` (23 Tests): alle 12 Klassen von 1 bis 20 (generischer Ausfüller über `needs`), Anforderungen je Stufe, EP-Schwelle/Meilenstein, Rechte (SL vergibt, Fremde 403), `xp` nicht über Generic-API, Magier 5 -> 6 per API, gewürfelte TP, Sperren/Validierung, Attributswert auf Stufe 8, Token-Aktualisierung, Nicht-SRD-Charaktere.
- Neu `tests/test_srd_progression_browser.py` (Chromium, 1440/390): EP vergeben, Bereit-Hinweis, Assistent bis zur Bestätigung (Magier 5 -> 6), kein horizontaler Überlauf.
- Regression grün: Ersteller-API, Bogen, Würfe, Inventar (API und Browser), Charakter-Suiten, Herkunfts-Bogen.

## Bekannte Lücken (ehrlich)

- Kein Mehrklassen-Aufstieg in der Oberfläche (die Regelrechnung kann es; kommt mit P9). Kein Zurücksetzen/Stufenabstieg (P10).
- Kein Tausch von Zaubern über die freie Zauberwahl hinaus; Trefferwürfel, Ruhephasen und verbrauchte Zauberplätze sind noch nicht modelliert.
- EP-Vergabe nur durch die SL bzw. Besitzerin/Besitzer (Charaktere ohne Kampagne).
- Abstammungs-/Spezieszauber werden wie im Ersteller noch nicht automatisch eingetragen.
