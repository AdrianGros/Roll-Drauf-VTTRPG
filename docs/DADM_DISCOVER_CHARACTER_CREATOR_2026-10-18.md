# DAD-M Discover: Roll Drauf Character Creator (SRD 5.2.1, Parität)

Date: 2026-10-18
Status: Discover abgeschlossen, wartet auf Review (Zuständig: Content Lead / Abnahme-Owner)
Vorgänger: Regelwerk 1.0.0 (live), Compendium C1 + C2 (live, Image `regelwerk-113e001`)

## 1. Ziel

Ein Charakter-Ersteller im Roll Drauf VTT mit dem Funktionsumfang eines modernen
Online-Creators (Parität in der Nutzerführung und im Funktionsumfang), vollständig
eigenständig umgesetzt auf den veröffentlichten SRD-5.2.1-Daten (`srd-5.2.1-de`).

Owner-Vorgabe (2026-10-18): **Vollparität** zu D&D Beyond im Funktionsumfang. Jede dort
vorhandene Ersteller- und Bogenfunktion wird hier ebenfalls gebaut; das ist die Baseline,
die später verbessert wird. Nur der Inhaltsumfang bleibt rechtlich auf SRD 5.2.1 und
eigene/lizenzierte Pakete begrenzt (siehe 4.6); darüber hinaus über Homebrew der
Creation Engine.

## 2. Rechtliche und technische Leitplanken

- Keine fremden Quellcodes, Assets, Texte oder nicht-SRD-Inhalte; kein REA-Repo
  (vom Owner ausdrücklich verworfen). Wir bauen aus Funktionsbeschreibungen und
  eigenen Entwürfen, nicht durch Übernahme fremder Implementierung.
- Regelinhalt ausschließlich aus dem veröffentlichten Paket (CC BY 4.0); die
  Namensnennung bleibt in jeder Ansicht erreichbar, die SRD-Text zeigt.
- Berechnete Regeln (Modifikatoren, Übungsbonus, TP, RK, Zauberplätze) sind
  eigener Code gegen Regeln, nicht gegen Fremdcode.
- Kein Zugriff auf Fremdkonten, keine Anmelde-Imports, kein Scraping.
- Der Ersteller schreibt nie ins Regelwerk-Paket; das Paket bleibt unveränderlich.

## 3. Ist-Zustand (aus dem Code, nur gelesen)

| Baustein | Stand |
|---|---|
| `models/character.py` | Zeilenmodell mit 6 Attributen, TP, RK, Übungsbonus, `character_data` (JSON), Relationen Spells / Equipment / Inventory. Kein Regelsystem-Bezug außer `character_data.roll_drauf_light`. |
| Roll-Drauf-Light-Ersteller (`characters.html`, 3 Schritte) | Identität (Spezies, Fraktion, Klasse, Hintergrund), Attribute, "Bereit für den Bogen". Auf eigenen Katalog `vtt/roll_drauf/catalog.py` mit Stufen 1-5 begrenzt, `progression.py`, `POST /characters/<id>/level-up`. |
| Charakterbogen (`character-sheet.html`) | Kernwerte, Zauber, Ausrüstung, Inventar als freie Eingabe (Name, Stufe, Schule). Keine Regelverknüpfung, keine Berechnung aus Klasse/Spezies. |
| D&D-5e-Portabel-Import (`dnd5e_portable.py`) | Versioniertes JSON `dnd5e_character`, importierter Regeltext wird nie ausgeführt. |
| Creation Engine (`vtt/creation_engine/`) | Versionierte Entwürfe, Revisionen, Spezies-Homebrew-Profil mit Übergabe auf neue oder bestehende Charaktere (`race-to-sheet-2026-09-28.md`); geführter Modus. Bestehende Verträge (1.1.4 / core 1.1.3 / A1) bleiben eingefroren. |
| Regelwerk-Compendium | Abfragbare Entitäten mit stabilen IDs, Facetten und Detailansicht; Zauberlisten je Klasse aus Zauberzeilen abgeleitet; Endpunkt `/api/rulesets/srd-5.2.1-de/compendium(/entry/<id>)`. |

Folgerung: Es gibt keinen Ersteller für SRD 5.2.1. Der vorhandene Ersteller ist ein
anderes System (`roll_drauf_light`, Stufe 1-5). Beide müssen nebeneinander laufen.

## 4. Paritäts-Matrix (Vollparität, Owner-Vorgabe 2026-10-18)

Vorgabe des Owners: Der Ersteller wird vollständig paritätisch zu D&D Beyond gebaut;
alle dort vorhandenen Funktionen brauchen wir auch. Das ist die Baseline, die später
verbessert wird. Es gibt daher keine "kann später"-Funktionen, nur eine Reihenfolge.
Die Liste ist aus allgemeinem Funktionswissen über das Produkt zusammengestellt und
wird in Zyklus P0 gegen die Erfahrung des Owners abgeglichen (fehlende Funktionen
ergänzt, bevor P1 beginnt). Inhalts-Umfang ist davon getrennt (siehe 4.6).

Spalte "Daten": vorhanden = Compendium-Daten reichen; Struktur = maschinenlesbare
Ergänzung nötig; Eigenbau = neue Logik/UI ohne Regeldaten.

### 4.1 Ersteller-Assistent (Builder)

| # | Funktion | Daten |
|---|---|---|
| 1 | Zwei Wege: geführter Assistent (Schritt für Schritt) und Schnellbau (alle Wahlen auf einer Seite) | Eigenbau |
| 2 | Klassenwahl mit Vorschau (TW, Hauptattribut, Rettungswürfe, Übungen, Stufe-1-Merkmale) | vorhanden + Struktur |
| 3 | Herkunft: Spezies mit Größe, Bewegung, Merkmalen, Wahlmerkmalen; Hintergrund mit Boni, Ursprungstalent, Fertigkeiten, Werkzeug | vorhanden + Struktur |
| 4 | Eigene Herkunft/Anpassung (frei gewählte Boni, Sprachen, Übungen nach SRD-Regel "Hintergrund anpassen") | Struktur |
| 5 | Attribute: Standardreihe, Punktekauf, Würfeln (4W6), manuell; Hintergrundboni; Empfehlung nach Klasse | Eigenbau |
| 6 | Ausrüstung: Startpaket A/B oder Gold, Einkauf aus dem Katalog mit Suche und Filter | vorhanden + Struktur |
| 7 | Zauberauswahl: Zaubertricks, bekannte/vorbereitete Zauber, Zauberbuch, Rituale, Filter | vorhanden |
| 8 | Beschreibung: Name, Gesinnung, Glaube, Lebensstil, Alter/Größe/Gewicht/Augen/Haare/Haut, Persönlichkeit, Ideale, Bindungen, Makel, Hintergrundgeschichte, Notizen | Eigenbau |
| 9 | Fortschritt/Zusammenfassung während des Baus, Zurück/Weiter ohne Datenverlust | Eigenbau |
| 10 | Entwürfe speichern, fortsetzen, duplizieren, verwerfen; Handy-tauglich | Eigenbau |
| 11 | Prüfer mit Warnungen und Regelverweis bei unvollständigen oder ungültigen Wahlen | Eigenbau |
| 12 | Zufallsgenerator (zufällige Spezies/Klasse/Attribute/Name) | Eigenbau |
| 13 | Direktstart auf höherer Stufe (inkl. Ausrüstung/Zauber der Stufe) | Struktur |
| 14 | Quellen-/Regelumfang wählen (SRD, Homebrew, Kampagnenfreigaben) | Eigenbau |

### 4.2 Fortschritt und Stufenaufstieg

| # | Funktion | Daten |
|---|---|---|
| 15 | Stufenaufstieg-Assistent 2-20 (TW/feste TP, Unterklasse, Merkmale, Zauber, Wahlen) | vorhanden + Struktur |
| 16 | Attributserhöhung oder Talent mit Voraussetzungsprüfung | Struktur |
| 17 | Mehrklassigkeit (Voraussetzungen, kombinierte Zauberplätze, Übungen, Merkmale) | Struktur, hohes Risiko |
| 18 | Erfahrungspunkte und Meilenstein-Aufstieg, XP-Verwaltung | Eigenbau |
| 19 | Umbau/Respec (Wahl nachträglich ändern, Stufe zurücknehmen) mit Verlauf | Eigenbau |
| 20 | Klassenwahl-Merkmale (Kampfstil, Metamagie, Anrufungen, Expertise usw.) | vorhanden |

### 4.3 Charakterbogen (Spielansicht)

| # | Funktion | Daten |
|---|---|---|
| 21 | Alle abgeleiteten Werte live (Modifikatoren, Übungsbonus, Rettungswürfe, Fertigkeiten, passive Sinne, Initiative, RK, TP, Bewegung, Zauber-SG/Angriffsbonus) | Eigenbau |
| 22 | TP-Verwaltung (Schaden, Heilung, temporäre TP, Trefferwürfel, TP-Maximum-Änderungen) | Eigenbau |
| 23 | Todesrettungswürfe, Inspiration, Erschöpfung, Zustände mit Regelverweis | vorhanden + Eigenbau |
| 24 | Kurze/lange Rast mit automatischer Erholung (Trefferwürfel, Plätze, Merkmale) | Struktur |
| 25 | Ressourcen-Zähler (Merkmale mit Anwendungen, Kurz-/Langrast-Erholung) | Struktur |
| 26 | Zauberplätze, vorbereitete Zauber umschalten, Zauberbuch, Konzentration, Rituale | Struktur |
| 27 | Aktionen-Ansicht (Angriffe mit Bonus/Schaden, Aktionen, Bonusaktionen, Reaktionen) | Struktur |
| 28 | Würfe aus dem Bogen (Fertigkeit, Rettungswurf, Angriff, Schaden, Zauber) mit Vorteil/Nachteil, Ergebnis im Chat/Log des VTT | Eigenbau + vorhandener Würfler |
| 29 | Inventar: Behälter, Menge, Gewicht, Tragelast, Währung/Umrechnung, ausgerüstet/eingestimmt, Einstimmungs-Limit, Magische Gegenstände | vorhanden + Eigenbau |
| 30 | Eigene Gegenstände, Waffen, Zauber, Merkmale, Aktionen (Eigenbau/Homebrew im Bogen) | Eigenbau + Creation Engine |
| 31 | Überschreibungen: jeden berechneten Wert manuell überschreiben, mit Kennzeichnung | Eigenbau |
| 32 | Übungen, Sprachen, Resistenzen/Immunitäten/Verwundbarkeiten, Sinne, Werkzeuge, Fertigkeitsstufen (Übung/Expertise/halb) | vorhanden + Struktur |
| 33 | Begleiter und Gestalten (Wildgestalt, Vertraute, Tierbegleiter) als eigene Statblöcke | vorhanden (creature) |
| 34 | Notizen (Organisation, Verbündete, Feinde, Ziele, Schätze, Kampagne) und Hintergrundgeschichte | Eigenbau |
| 35 | Regelverweise überall: Klick auf Merkmal, Zauber, Gegenstand, Zustand öffnet Compendium-Detail | vorhanden (entry-API) |
| 36 | Mobile Spielansicht (Daumenbedienung, Tabs) und Desktop-Ansicht | Eigenbau |

### 4.4 Verwaltung, Weitergabe, Kampagne

| # | Funktion | Daten |
|---|---|---|
| 37 | Charakterliste mit Suche, Sortierung, Filter, Duplizieren, Archivieren, Löschen/Wiederherstellen | Eigenbau (teilweise vorhanden) |
| 38 | Charakter einer Kampagne zuordnen; Party-Ansicht für die Spielleitung (Werte, TP, Sinne, Zustände) | Eigenbau (Kampagnenmodell vorhanden) |
| 39 | Teilen: privater Ansicht-Link, öffentlich/privat, Nur-Lese-Ansicht | Eigenbau |
| 40 | Export: PDF (Roll-Drauf-Lila `#4b235a`), Druckansicht, JSON (Portabel-Format); Import | Eigenbau (Portabel-Import vorhanden) |
| 41 | Änderungsverlauf des Charakters (wer/was/wann), Rückgängig | Eigenbau |
| 42 | Avatar, Token, Rahmen/Themes der Bogenansicht | vorhanden (Avatar/Token) + Eigenbau |
| 43 | Spielleitung-Werkzeuge: Charakter zusammen mit Spieler bearbeiten, Stufen vergeben, Inhaltsfreigaben je Kampagne | Eigenbau |
| 44 | Token-Verknüpfung: Bogenwerte (TP, RK, Sinne, Zustände) laufen live auf dem Token der Karte | Eigenbau (VTT-Karte vorhanden) |

### 4.5 Inhalte und Homebrew

| # | Funktion | Daten |
|---|---|---|
| 45 | Quellen: Inhalte als Pakete (SRD 5.2.1 jetzt, weitere lizenzierte oder eigene Pakete später), je Charakter/Kampagne an- und abschaltbar | Eigenbau |
| 46 | Homebrew-Spezies, -Klassen, -Unterklassen, -Hintergründe, -Talente, -Zauber, -Gegenstände, -Kreaturen mit Erstellern (Creation Engine als Grundlage) | Creation Engine erweitern |
| 47 | Homebrew teilen, sammeln, versionieren, in Kampagnen freigeben | Creation Engine (Revisionen) |
| 48 | Eigene Regeln als strukturierte Effekte (Boni, Übungen, Resistenzen), nie ausführbarer Fremdtext | Struktur (bestehende Vertragsregel: keine Ausführung von Text) |

### 4.6 Inhalts-Umfang (Abgrenzung zu den Funktionen)

Alle Funktionen oben sind unabhängig vom Inhaltsumfang. Der Inhalt selbst ist rechtlich
auf SRD 5.2.1 (CC BY 4.0) und eigene/lizenzierte Pakete begrenzt: 12 Klassen mit je
1 Unterklasse, 9 Spezies, 4 Hintergründe, 17 Talente, 339 Zauber. Mehr Inhalt kommt
ausschließlich über Pakete (Punkt 45) mit geprüfter Lizenz oder über Spielende selbst.
Nicht übernommen werden proprietäre Inhalte, Konto-/Kaufsysteme anderer Anbieter und
deren Code/Assets.

## 5. Zielarchitektur (Vorschlag)

1. **Strukturdaten ergänzen (Paket-unabhängig).** Maschinenlesbare Ersteller-Metadaten
   (`creator-rules.json`, abgeleitet aus dem Paket durch `tools/build_regelwerk.py`,
   ohne Paketversion zu ändern): Klassen (Fertigkeitswahl, Übungen, Startausrüstung A/B,
   Zauberfähigkeit, Zauberplätze je Stufe), Spezies-Wahlen, Hintergrund-Boni und
   Ausrüstung. Was sich nicht sicher parsen lässt, wird in einer geprüften,
   handgepflegten Ergänzungstabelle mit Quellverweis auf die Regelstelle geführt und
   per Test gegen den Quelltext abgesichert (wie bei den Zauberlisten).
2. **Rechenkern** `creator_rules.py`: reine Funktionen (kein Flask, keine DB), voll
   getestet; liefert Zustand + Warnungen. Gleicher Kern für Ersteller und Level-up.
3. **Datenmodell.** SRD-Charakter: `character_data.system_id = "srd_5_2_1_de"` und
   Block `character_data.srd` (Auswahlen mit Compendium-IDs, nie Kopien von Regeltext).
   Die bestehenden Spalten (Attribute, TP, RK, Stufe) werden aus dem Kern geschrieben,
   damit Karte, Initiative und andere Verbraucher unverändert funktionieren. Die
   Rollen-Drauf-Light-Charaktere und der Portabel-Import bleiben unberührt.
4. **API.** `POST /api/srd-creator/drafts` (+ `PUT` je Schritt, `POST …/finalize`,
   `POST /characters/<id>/srd-level-up`). Serverseitige Prüfung bei jedem Schritt;
   der Client rechnet nur zur Anzeige. Auth, CSRF und Besitzerprüfung wie bei den
   bestehenden Charakter-Routen.
5. **UI.** Neuer Assistent (eigene Seite, Handy zuerst), Auswahlkarten mit
   Compendium-Detail als Seitenfenster, Live-Zusammenfassung. Einstieg im Dialog
   "Charakter erstellen" als Systemwahl (Roll Drauf Light | SRD 5.2.1).
6. **Creation Engine.** Nur Anbindung über vorhandene Verträge (Homebrew-Spezies per
   Revisions-Referenz als Herkunft), keine Vertragsänderung an 1.1.4/core 1.1.3/A1.
7. **Bogen.** SRD-Charaktere erhalten eine regelbasierte Bogenansicht (berechnete
   Werte, Zauberplätze, Merkmale mit Regelverweis); Freitext-Bogen bleibt für andere
   Systeme.

## 6. Meilensteine (je ein DAD-M-Zyklus, Status-DM nach jedem)

Jeder Zyklus nennt die Matrix-Nummern aus Abschnitt 4, die er schließt. Vollparität ist
erreicht, wenn alle 48 Punkte abgenommen sind.

| Zyklus | Inhalt | Matrix | Abnahme |
|---|---|---|---|
| P0 | Funktionsabgleich: Owner prüft die Liste (fehlende Funktionen ergänzen), Abnahmekriterium je Funktion | alle | Owner |
| P1 | Strukturdaten + Quellabgleich (Klassen, Spezies, Hintergründe, Startausrüstung, Zauberplätze, Ressourcen, Rast-Erholung, Talent-Voraussetzungen) | Basis für 2-4, 6, 13, 15-17, 24-27, 32 | Tests, Quellabgleich |
| P2 | Rechenkern + Prüfer (Stufen 1-20), Attribut-Methoden, Überschreibungen | 5, 11, 21, 31 | Tests, Rechenbeispiele je Klasse |
| P3 | Entwurfs-API, Finalisieren, Persistenz, Quellen-/Paketmodell | 10, 14, 45 | API-Tests, Live-Smoketest |
| P4 | Assistent-UI: geführt + Schnellbau, Herkunft, Ausrüstung, Zauber, Beschreibung, Zufall | 1-4, 6-9, 12, 13 | Handy-Abnahme |
| P5 | Regelbasierter Bogen: Werte, TP, Zustände, Rasten, Ressourcen, Zauberplätze, Aktionen, Regelverweise | 21-27, 32, 34-36 | Handy-Abnahme |
| P6 | Würfe aus dem Bogen mit VTT-Würfler und Log; Token-Verknüpfung | 28, 44 | Live-Test mit Karte |
| P7 | Inventar: Behälter, Last, Währung, Einstimmung, eigene Gegenstände | 29, 30 | Handy-Abnahme |
| P8 | Stufenaufstieg 2-20 mit Unterklasse, Talent/Attribute, Zauber; XP/Meilenstein | 15, 16, 18, 20 | Tests je Klasse |
| P9 | Mehrklassigkeit | 17 | Tests, Owner-Abnahme |
| P10 | Verwaltung: Liste, Duplizieren, Archiv, Verlauf, Respec, Begleiter | 19, 33, 37, 41 | Abnahme |
| P11 | Kampagne und Teilen: Zuordnung, Party-Ansicht, Link, Spielleitungs-Werkzeuge | 38, 39, 43 | Abnahme mit zwei Konten |
| P12 | Export/Import: PDF (lila), Druck, JSON; Avatar/Token/Themes | 40, 42 | Abnahme |
| P13 | Homebrew-Ersteller und Pakete: alle Typen, teilen, versionieren, Kampagnenfreigabe | 46-48 | Abnahme |

Reihenfolge ist ein Vorschlag; P2-P5 liefern das erste benutzbare Gesamtbild (Charakter
bauen und spielen), der Rest erweitert bis zur Vollparität. Nach jedem Zyklus wird die
Matrix mit Status (offen / in Arbeit / abgenommen) fortgeschrieben.

Parallel: echter Browser-Test (Playwright oder vergleichbar) einführen, weil bisher nur
jsdom getestet wird; Voraussetzung für die Abnahme von P4.

## 7. Risiken

- **Quellqualität:** Gedruckte Tabellen haben Fehler (Klassen-Zauberlisten). Der
  Ersteller muss weiter abgeleitete Listen verwenden und Abweichungen testen.
- **Parsen von Regeltext:** Fertigkeitswahlen, Startausrüstung A/B und Wahlmerkmale
  sind Prosa. Kontrollierte Ergänzungstabelle mit Quellverweis statt Heuristik.
- **Mehrklassigkeit** und Zauberplatz-Kombination sind fehleranfällig; bewusst spät.
- **Umfang der Handy-Oberfläche:** Der Assistent ist die größte UI-Fläche; wir
  liefern in Schritten, jeder Schritt auf dem Live-VTT abnehmbar.
- **Kopplung:** Bestehende Verbraucher von `Character`-Spalten dürfen nicht brechen;
  deshalb Spalten weiter schreiben, `srd`-Block additiv.

## 8. Offene Entscheidungen (Standardannahme in Klammern)

1. Funktionsabgleich P0: Owner ergänzt Funktionen, die in der Liste fehlen (Liste ist aus
   allgemeinem Produktwissen, nicht aus einem Abgleich mit deiner Nutzung).
2. Reihenfolge der Schritte: Klasse zuerst wie im SRD 5.2 (ja).
3. Attribut-Methoden: alle vier, Kampagne kann einschränken (ja).
4. Korrigierte Paketversion 1.0.1 für die Zauberlistentabellen (offen seit C2;
   blockiert nichts).
5. Browser-Test-Werkzeug auf dem Server (Playwright im Container) (ja).
6. Inhaltspakete jenseits SRD: nur mit geprüfter Lizenz; welche Quellen sollen wir
   prüfen (keine, bis du etwas nennst)?

## 9. Nächster Schritt

Zyklus P0 (Funktionsabgleich) und anschließend P1 (Strukturdaten + Quellabgleich).
Bis zur Freigabe keine Code-Änderung am Ersteller; dieses Dokument ist das einzige Ergebnis.
