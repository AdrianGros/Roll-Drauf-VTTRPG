# DAD-M Apply: Character Creator P4 (Wizard UI)

Stand: 2026-10-18, Branch `feat/creation-engine-g1`. Aufbauend auf P1 (Daten), P2 (Rechenkern), P3 (Entwurfs-API).

## Ergebnis

Neue Seite `/srd-creator` (Rolltisch-Pergament-Look, Roll-Drauf-Lila `#4b235a`), vollständig auf der veröffentlichten SRD-5.2.1-Datenbasis (`srd-5.2.1-de`).

- Startseite: neuer Charakter (geführt, Schnellbau, Zufallscharakter), offene Entwürfe (fortsetzen, duplizieren, verwerfen).
- Geführter Modus mit acht Schritten: Klasse, Herkunft, Attribute, Wahlen, Ausrüstung, Zauber, Beschreibung, Prüfung. Schnellbau zeigt alle Schritte auf einer Seite.
- Klasse: Stufe 1–20, Stufenverlauf mit Klassenwahl je Stufe (Mehrklassigkeit, Server prüft Voraussetzungen), Trefferpunkte fest oder gewürfelt.
- Herkunft: Volk (inkl. Wahlen), Hintergrund mit +2/+1 oder +1/+1/+1.
- Attribute: Standardsatz (mit Klassenempfehlung), Punktekauf, Würfeln (4W6), Manuell.
- Wahlen: Klassenfertigkeiten, Expertise, Unterklasse, Klassenmerkmale (Kampfstil, Waffenbeherrschung, Anrufungen, Metamagie, Sprachen), Attributserhöhungen/Talente/Epische Gaben.
- Ausrüstung: Klassen- und Hintergrundpaket A/B, Rüstung, Schild (RK live).
- Zauber: Zaubertricks, vorbereitete Zauber, Zauberbuch (Magier), Suche und Stufenfilter.
- Beschreibung: Identität, Gesinnung, Freitexte.
- Prüfung: alle Befunde, manuelle Überschreibungen mit Begründung, Quellenangabe, Charakter erstellen (optional einer Kampagne zuordnen).
- Autosave mit optimistischer Versionierung, Konfliktbanner (neueste laden / meine behalten), Server-Rechenergebnis ist maßgeblich (der Client berechnet keine abgeleiteten Werte).
- Zufallsgenerator erzeugt regelgültige Charaktere Stufe 1–20.
- Mobil: Zusammenfassung einklappbar, Schritte scrollbar, kein horizontales Scrollen.

## Tests

- `tests/test_srd_creator_browser.py` (Chromium, 7 Tests): geführter Durchlauf Kämpfer bis Charakter, Zufallscharakter erstellen, 96 Zufallscharaktere (Stufen 1–20) ohne Blocker, Zwei-Tab-Konflikt, Entwurfsliste (fortsetzen, duplizieren, verwerfen), Schnellbau und 390-px-Layout, Attributmethoden plus Mehrklassigkeit. Keine JS-Fehler.
- Regression: Regelwerk-Suite und `test_srd_creator_api.py` (202 Tests) grün.
- In den Browsertests gefundene und behobene Fehler: Fehlerhafte Initialisierung der Überschreibungsliste beim Laden, Klassen mit beliebiger Fertigkeitswahl (Barde), mehrfach gewählte Metamagie in Zauberer-Stufen, Ergebnis des Erstellens wurde durch Neuzeichnen überschrieben.

## Bekannte Lücken (ehrlich)

- Unterwahlen der Herkunftstalente (z. B. Zauberkundiger) werden noch nicht abgebildet.
- Eigener Hintergrund und vom Volk gewährte Zauber noch nicht.
- Sprachen sind nicht modelliert; Gelehrten-Expertise ohne Einschränkung auf die Gelehrten-Fertigkeiten.
- Kein Einstieg von der Charakterseite aus (Seite `/characters` ist eine Buchszene mit eigenen, ungeklärten Änderungen). Aufruf direkt über `/srd-creator`; Verlinkung folgt in P10.
- Der fertige Charakter erscheint in der Liste und im bisherigen Bogen; der regelbasierte Bogen folgt in P5.
- Nur Chromium getestet (Firefox/WebKit nicht im Testimage).
- Live-Deploy steht aus (Freigabe für den Container-Neustart fehlt).
