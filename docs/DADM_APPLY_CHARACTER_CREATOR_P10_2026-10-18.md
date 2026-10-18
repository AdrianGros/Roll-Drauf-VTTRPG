# DAD-M Apply: Character Creator P10 (Verwaltung)

Stand: 2026-10-18, Branch `feat/creation-engine-g1`. Aufbauend auf P9. Parität: Discover-Punkte Charakterliste, Duplizieren, Archivieren, Verlauf, Stufenabstieg/Neuaufbau, Begleiter, Weiterführen von Entwürfen.

## Entscheidung

- **Nur SRD-Charaktere**: Die neuen Endpunkte (`/api/srd-creator/characters/<id>/…`) antworten bei allen anderen Charakteren mit 422 `not_srd`. Creation-Engine-Daten werden nicht angefasst.
- **Stufenabstieg läuft durch dieselbe Regelrechnung**: Die letzte Stufe wird aus `state.levels` entfernt, alles was an ihr hing (Talente/Attributserhöhungen, Unterklasse, Wahlen, Expertise, Zauber über der Grenze, Mehrklassen-Fertigkeiten) wird bereinigt, `creator_rules.evaluate` urteilt, gespeichert wird nur ohne Blocker. Erfahrung wird unter die Schwelle der nächsten Stufe gesetzt (Meilensteine: Freigabe auf die neue Stufe), damit der Charakter nicht sofort wieder aufsteigt.
- **Neuaufbau ist ein zweiter Charakter**: "Neuaufbau als Entwurf" kopiert den Zustand in einen Entwurf des Erstellers; abgeschlossen entsteht ein neuer Charakter, der alte bleibt unverändert und kann archiviert werden. Kein stilles Überschreiben.
- **Archiv statt Papierkorb**: Archivieren setzt `character_data.lifecycle.archivedAt`. Der Charakter verschwindet aus `/api/characters/mine` und aus den geteilten Listen, bleibt aber erhalten; Wiederherstellen oder endgültig Löschen (bestehendes DELETE, mit Rückfrage). Charaktere in einer Kampagne müssen diese zuerst verlassen (409 `in_campaign`).
- **Duplizieren** legt eine eigenständige Kopie an (Name "… (Kopie)", ohne Kampagne und Avatar, Verlauf zurückgesetzt, Inventar, Zauber, Ausrüstung und Begleiter werden kopiert).
- **Begleiter** liegen in `character_data.srdCompanions` (bis zu 20; Name, Art, TP, RK, Bewegung, Angriffe, Notizen), nur die Besitzerin oder der Besitzer schreibt, Leser sehen sie.

## Ergebnis

- **API**: `POST level-down`, `POST archive`, `POST duplicate`, `POST to-draft`, `GET/PUT companions`; Fortschrittsantwort enthält `lastLevel`, `canLevelDown`, `archived`. `GET /api/characters/mine?archived=only` liefert das Archiv.
- **Bogen**: Im Abschnitt "Stufe und Erfahrung" "Letzte Stufe rückgängig machen" mit Bestätigung; neuer Abschnitt "Begleiter und Verwaltung" (Begleiter anlegen, bearbeiten, speichern; Duplizieren, Archivieren, Neuaufbau als Entwurf, jeweils mit Bestätigung). Verlauf zeigt auch Stufenabstiege.
- **Charakterseite**: Buttons "Duplizieren" und "Archivieren" je SRD-Held, Bereich "Offene Entwürfe" mit "Weiterführen" (öffnet `/srd-creator?draft=<id>`), aufklappbares "Archiv (N)" mit "Wiederherstellen" und "Endgültig löschen".
- Creation Engine bleibt unangetastet.

## Tests

- `tests/test_srd_manage.py` (25): Stufenabstieg 20 -> 1 für alle zwölf Klassen (TP, RK, Zauberwirken, Klassenstufen und Unterklassen stimmen mit dem Zustand beim Aufstieg überein, EP liegen in der Stufenspanne), Mehrklassigkeit, API (Rechte, Konflikt, EP-Deckelung, Meilensteine, Stufe-1-Grenze), Archiv, Kopie, Entwurf, Begleiter, Nicht-SRD-Charaktere.
- `tests/test_srd_manage_browser.py` (4, 1440/390): Stufe rückgängig machen mit Bestätigung, Begleiter anlegen/speichern/entfernen, Duplizieren, Neuaufbau, Archivieren, Wiederherstellen, Löschen, Entwurfsliste, kein Überlauf.
- Regression: Suiten `tests/test_srd_*.py`, `tests/test_characters.py` u. a.

## Bekannte Lücken (ehrlich)

- Kein Papierkorb zum Zurückholen endgültig gelöschter Charaktere.
- Der Verlauf zeigt EP, Modus, Freigabe, Auf- und Abstieg; Archivieren/Duplizieren stehen nur im Datensatz, nicht in der Anzeige.
- Neuaufbau überschreibt den alten Charakter nicht; Inventar, Begleiter und Verlauf wandern nicht automatisch in den neuen Charakter.
- Begleiter sind Freitext-Karten, keine Regelrechnung (Tierbegleiter-Werte aus dem SRD-Monsterkatalog folgen nicht in P10).
- Teilen über Kampagne und Ausgabe von Gegenständen durch die Spielleitung folgen in P11.
