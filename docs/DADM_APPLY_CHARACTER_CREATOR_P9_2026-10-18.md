# DAD-M Apply: Character Creator P9 (Mehrklassigkeit)

Stand: 2026-10-18, Branch `feat/creation-engine-g1`. Aufbauend auf P8. Parität: Discover-Punkte Multiclassing, Voraussetzungen, Zauberplätze aus kombinierter Zauberstufe, Übungen bei Klassenwechsel.

## Entscheidung

- **Eine Regelrechnung**: Eine neue Klasse ist ein weiterer Eintrag in `state.levels`. Voraussetzung (Hauptattribut mindestens 13 für alle bisherigen Klassen und die neue), kombinierte Zauberstufe und Zauberplätze, Rüstungs-/Waffenübungen berechnet weiterhin `creator_rules.evaluate`; Speichern nur ohne Blocker.
- **Fertigkeit bei Klassenwechsel** (SRD: Fertigkeit je nach Klasse): neu `state.skills.multiclass[klasse]`. Die Regelrechnung verlangt die Anzahl laut `multiclassGrants` (Barde, Schurke, Waldläufer … je 1), prüft die Klassenliste bzw. "beliebig", warnt bei doppelter Übung und setzt die Übung vor der Expertise-Prüfung.
- **Aufstieg in eine neue Klasse** läuft über denselben Weg wie P8 (`level-up/preview`, `level-up`); `build_state` akzeptiert jetzt jede SRD-Klasse (unbekannt: 422 `invalid_class`). Stufe-20-Grenze gilt für die Gesamtstufe.

## Ergebnis

- **API**: Fortschrittsantwort enthält `multiclassOptions` (je Klasse: besessen/Stufe, zulässig, Grund bei Unzulässigkeit). `needs.multiclass` liefert bei einer neuen Klasse die Übungen (`grants`) und die Fertigkeitswahl; Nutzlast `multiclassSkills`.
- **Aufstiegs-Assistent**: Klassenauswahl mit eigenen Klassen (Stufe) und neuen Klassen; nicht erfüllte Voraussetzungen sind gesperrt, die Gründe stehen aufklappbar darunter. Zusätzlicher Schritt "Mehrklassigkeit" (Übungen + Fertigkeitswahl), danach Stufe-1-Wahlen der neuen Klasse (Unterklasse nicht, Kampfstil, Heilige Rolle, Zauber …).
- **Ersteller** (Schritt Wahlen): Fertigkeitswahl für jede Zweit-/Dritt-Klasse; Aufräumen beim Ändern der Klassenfolge.
- Creation Engine bleibt unangetastet.

## Tests

- `tests/test_srd_progression.py` (+7): Optionen mit Zulässigkeit, Kämpfer 1 -> Magier 1 per API (Zauberbuch, Zauberwirken), Voraussetzung blockiert, Fertigkeitswahl Pflicht/gültig/ungültig, Fertigkeit für eigene Klasse abgelehnt, unbekannte Klasse, Zauberplätze aus kombinierter Zauberstufe.
- `tests/test_srd_progression_browser.py` (+2, 1440/390): Assistent wählt neue Klasse, Mehrklassigkeitsschritt, Bestätigen, kein Überlauf.
- Regression: Suiten `tests/test_srd_*.py`.

## Bekannte Lücken (ehrlich)

- Werkzeugübungen aus Mehrklassigkeit (Musikinstrument, Diebeswerkzeug) werden angezeigt, aber nicht modelliert (Werkzeuge fehlen in der Regelrechnung insgesamt).
- Trefferwürfel je Klasse und Rasten sind weiterhin nicht modelliert; Zauber der Zweitklasse sind freie Auswahl wie in P8.
- Kein Stufenabstieg/Zurücksetzen (P10).
