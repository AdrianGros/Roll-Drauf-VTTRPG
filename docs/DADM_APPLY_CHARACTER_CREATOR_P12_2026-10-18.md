# DAD-M Apply: Character Creator P12 (Export, Import, PDF, Farben)

Stand: 2026-10-18, Branch `feat/creation-engine-g1`. Aufbauend auf P11. Parität: Charakterbogen als PDF, Sicherung/Import als Datei, Farbgestaltung des Bogens, Avatar auf dem Ausdruck.

## Entscheidung

- **Nur SRD-Charaktere**: Neue Endpunkte unter `/api/srd-creator/…`; Creation Engine und alte Routen bleiben unangetastet.
- **Sicherungsformat** `roll-drauf-srd-character` Version 1 (`<name>.rollcharakter.json`): Regelstand (State), Inventar mit Münzen, Begleiter, Fortschrittsmodus, Erfahrung, aktuelle TP, Farbe. Keine Konto-, Kampagnen-, Freigabe- oder Verlaufsdaten und keine IDs. Nur der Besitzer darf exportieren (403 sonst, `no-store`).
- **Import ist streng**: Größenlimit 400 KB (413), Format/Version/Regelwerk müssen passen, der State läuft durch dieselbe Bereinigung und Prüfung wie im Ersteller (kein Einschleusen berechneter Werte). Es entsteht immer ein neuer, unabhängiger Charakter des importierenden Kontos ohne Kampagne; Fehler legen nichts an (Rollback, 422 `import_invalid`). 20 Importe pro Stunde.
- **PDF**: A4 mit reportlab auf dem Server; Überschriftsbalken und Tabellenköpfe in Roll-Drauf-Violett `#4b235a`. Inhalt: Kopf mit Name/Untertitel/Avatar, Werte, Attribute, Fertigkeiten, Zauber (SG, Angriff, Plätze), Talente, Ausrüstung mit wörtlichen Texten magischer Gegenstände, Münzen, Begleiter, Persönliches. Lange Persönlichkeitstexte (Hintergrund, Notizen) nur im PDF des Besitzers; Kampagnenmitglieder lesen das PDF ohne diese Texte. Fußzeile mit Quelle und CC BY 4.0.
- **Farben**: sechs Akzentfarben (Violett Standard, Waldgrün, Glutrot, Meerblau, Schiefer, Bernstein); der Besitzer wählt, Leser sehen sie auf dem Bogen, in der Gruppenübersicht (Kartenrand und Titel) und im Freigabelink.
- **Avatar**: Hochladen/Entfernen nutzt die bereits vorhandene Identitätskarte; neu ist, dass der Avatar im PDF-Kopf erscheint.

## Ergebnis

- **API**: `GET /characters/<id>/export`, `GET /characters/<id>/pdf`, `POST /characters/import`, `GET/PUT /characters/<id>/appearance`.
- **Oberfläche**: Charakterbogen-Abschnitt "Darstellung, Export und Druck" (PDF, Datei sichern, Farbwahl); Startseite des Erstellers mit Karte "Charakter einlesen".

## Tests

- `tests/test_srd_export.py` (8): Export nur für Besitzer ohne Konto-Daten, Rundlauf mit gleicher Berechnung/Inventar/Begleitern/Farbe, abgelehnte fremde/manipulierte/zu große Dateien, kein Rest bei Fehlern, PDF (A4, Violett, Inhalt, privater Text nur beim Besitzer), PDF für Kampagnenmitglieder, seltsame Zeichen, Farbrechte.
- `tests/test_srd_export_browser.py` (1440 und 390 px): PDF-Download, Datei-Download, Farbe wählen und nach Neuladen sichtbar, Import mit leerer/kaputter/gültiger Datei, Weiterleitung auf den neuen Bogen; kein Überlauf, kein pageerror.

## Bekannte Lücken (ehrlich)

- Das PDF bleibt immer violett, unabhängig von der gewählten Farbe (bewusst, Vorgabe Roll-Drauf-Violett); die Farbe wirkt nur auf dem Bildschirm.
- Keine Klassen-/Spezies-Merkmalstexte im PDF, nur Namen und Werte.
- Kein ausfüllbares Formular-PDF, kein PDF des Spielfigur-Tokens.
- Import verwirft offene Ausrüstungsentscheidungen des Starts und den Verlauf (ein einziger Eintrag "Import").
- Der Avatar-Upload nutzt weiterhin die allgemeine (englischsprachige) Identitätskarte.
- Keine Fremdformate (z. B. D&D-Beyond-JSON); nur das eigene Format.
