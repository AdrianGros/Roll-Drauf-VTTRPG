# DAD-M Apply: Character Creator P1 – Strukturdaten + Quellabgleich (2026-10-18)

Ergebnis: `vtt/rules_content/srd-5.2.1-de/generated/creator-data.json` (`regelwerk.creator-data.v1`), erzeugt von `vtt/rules_content/creator_data.py` aus den veröffentlichten Regelwerk-Dokumenten und dem Compendium. Paketversion bleibt 1.0.0.

Inhalt: Attribute, 18 Fertigkeiten, Stufen 1–20 (EP, Übungsbonus), Attributsmethoden (Standardsatz, Punktekauf 27, 4W6, Hintergrundbonus), Formeln, Trefferpunkte, Mehrklassigkeit (Voraussetzung 13, Zauberplatztabelle, Zauberstufen), Ausrüstung ab Stufe 2, 12 Klassen (Progression, Zauberwirken, Ressourcen mit Erholung, Merkmalwahlen, Mehrklassen-Zugaben, Standardwerte), 38 Klassenoptionen, 9 Spezies mit Wahlen, 4 Hintergründe, 17 Talente, Waffen/Rüstungen/Gegenstände/Pakete, Sprachen, Gesinnungen, 100 Schnickschnack-Einträge.

Prinzipien:
- Alles, was die Quelle nur als Prosa nennt, ist ein kuratierter Eintrag `{ruleId, quote}`; der Build bricht ab, wenn der Block fehlt oder das Zitat nicht wörtlich enthalten ist (Test prüft zusätzlich alle Zitate).
- Querprüfungen: Modifikatortabelle gegen Formel, feste TP gegen Trefferwürfel, Standardsätze gegen 15/14/13/12/10/8, Klassen-Zauberplätze gegen die Mehrklassentabelle, Ausrüstung gegen Compendium-IDs.

Quelldefekt (Entscheidung): Tabelle „Trefferpunkte auf Stufe 1“ nennt für Kämpfer, Paladin und Waldläufer „10 + GES-Modifikator“. Das ist ein Tippfehler; Tabelle „Feste Trefferpunkte“ und alle anderen Klassen nutzen KON. Der Ersteller rechnet Trefferwürfel + KON; der Defekt steht in `hitPoints.level1.sourceNotes`. Kandidat für Paket 1.0.1 (zusammen mit unvollständigen/falsch platzierten Klassen-Zauberlisten-Tabellen).

Bekannte Lücken für spätere Meilensteine: Ressourcen nur für die Hauptmerkmale (weitere folgen in P5), Unterklassenmerkmale als Compendium-Einträge ohne Strukturierung.
