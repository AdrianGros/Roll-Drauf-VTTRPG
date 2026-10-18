# DAD-M Apply: Character Creator P5 (regelbasierter Bogen, Ersteller-Umstellung)

Stand: 2026-10-18, Branch `feat/creation-engine-g1`. Aufbauend auf P1 (Daten), P2 (Rechenkern), P3 (Entwurfs-API), P4 (Wizard UI).

## Entscheidung (Owner)

"Replace, not layer": Der Roll-Drauf-Light-Ersteller (RDL) wird ersetzt, nicht parallel betrieben. Die Creation Engine (`vtt/creation_engine`, `ce_compat.py`, `/creation-engine`, `/api/ce`) bleibt ausdrücklich unangetastet. Umgestellt werden nur Charaktererstellung und Charakterbogen.

## Ergebnis

- Jede Charaktererstellung läuft über den Regelwerk-Ersteller `/srd-creator`: `/characters?intent=create` leitet dorthin um, die Modal-Erstellung auf `/characters` ist entfernt (ca. 1300 Zeilen), "Held anlegen"-Links in Dashboard und Buchszene zeigen auf `/srd-creator`.
- Der generische Anlege-Endpunkt `POST /api/characters` legt nur noch schlichte Charaktere an (kein RDL-Pfad, kein `species`-Alias).
- Backend-RDL entfernt: Paket `vtt/roll_drauf` (Katalog, Fortschritt), RDL-Level-up, RDL-Export/-Import. Export nutzt `dnd5e_portable`; Import akzeptiert nur noch `dnd5e_character`, sonst 400 mit Hinweis auf den Ersteller.
- `character-sheet.html`: RDL-Bereiche (Profil, Fortschritt, Merkmale, Level-up, Fraktion) entfernt. Neuer Abschnitt "SRD 5.2.1 · Regelwerk-Bogen" zeigt serverseitig berechnete Werte: Volk, Hintergrund, Klasse/Unterklasse, Gesinnung, RK mit Formel, Trefferpunkte und -würfel, Übungsbonus, Initiative, Bewegung, passive Wahrnehmung, sechs Attribute mit Rettungswürfen, 18 Fertigkeiten (Übung/Expertise), Zauberwirken (SG, Angriff, Plätze, Zaubertricks, Zauberbuch, vorbereitet), Talente. Verwaltete Felder (Volk, Klasse, Stufe, Attribute, RK, TP-Max) sind gesperrt; Name, Erfahrung und aktuelle TP bleiben editierbar. Hinweis mit Link zurück zum Ersteller.
- Altcharaktere mit RDL-Daten bleiben lesbar (schlichter Bogen ohne RDL-Bereiche).
- Tests angepasst: RDL-spezifische Suiten (Vertrag, M24-Fortschritt, M26-Level-up, M27-Export/Import, Bogen-Darstellung) entfernt; CE-Test der Signaturwahlen prüft nun gegen einen festen Snapshot statt gegen den entfernten Katalog.

## Tests

- Neu `tests/test_srd_sheet.py`: 6 HTTP-Tests (Auswertung, Sperre verwalteter Felder, Export, Import-Ablehnung) und Browsertest bei 1440 und 390 px (Werte, Expertise, Zauberplätze, gesperrte Eingaben, kein horizontales Scrollen, kein HTML-Injection-Effekt im Namen). Zweimal in Folge grün (8 Tests).
- Regression: Regelwerk-Suite, `test_srd_creator_api.py`, Journey-/Shell-/Feedback-Tests, gesamte `tests/creation_engine` grün; Chromium-Browsertests grün.
- Firefox-Fälle von `test_character_campaign_feedback.py` laufen im Testimage nicht (Firefox nicht installiert), kein Codefehler.

## Bekannte Lücken (ehrlich)

- Verlinkung aus der Charakterliste auf den Ersteller (Fortsetzen, Duplizieren, Stufenaufstieg) folgt in P10/P8.
- Würfe in das VTT-Protokoll und Token-Verknüpfung folgen in P6, Inventar in P7.
- Einige englische Restbeschriftungen des alten Bogens (z. B. "Core", "No spells yet") bleiben bis zur Überarbeitung in P6/P7.
- Lange Kachelbeschriftungen (z. B. "Rüstungsklasse") und die Trefferpunkte der Kurzübersicht werden in der schmalen Spalte abgeschnitten (kosmetisch, bei 1440 px sichtbar; 390 px nicht gesondert geprüft).
- Altcharaktere mit RDL-Daten verlieren RDL-Panes und Level-up bewusst (Ersetzen statt Schichten).
