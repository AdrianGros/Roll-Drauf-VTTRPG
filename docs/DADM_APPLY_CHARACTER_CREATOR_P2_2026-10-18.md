# DAD-M Apply – Character Creator P2: Rechenkern + Prüfer

Stand 2026-10-18, Branch `feat/creation-engine-g1`. Matrixpunkte 5, 11, 21, 31 des Discover-Dokuments.

## Ergebnis

- `vtt/rules_content/creator_rules.py`: reine Funktionen (kein Flask, keine Datenbank). `evaluate(data, state)` liefert abgeleitete Werte und eine Liste von Befunden `{severity, code, message, path, ref}`. `ref` ist `{ruleId, quote}` aus den Strukturdaten, das Zitat steht wörtlich im Regelblock.
- Schweregrade: `error` (blockiert später das Finalisieren), `incomplete` (Entwurf noch offen), `warning`, `info`.
- Abgedeckt: Stufen 1–20, Mehrklassigkeit (Voraussetzung 13, kombinierte Zauberplätze, getrennte Paktmagie, Trefferwürfel je Klasse), Attributsmethoden (Standardsatz, Punktekauf 27, 4W6 mit Würfelnachweis, manuell), Hintergrundbonus (+2/+1, +1/+1/+1), Attributswerterhöhungen und Talente je Klassenstufe (Kämpfer 6/14, Schurke 10, Epische Gabe auf 19 mit Obergrenze 30 nur für das Gabenattribut), Spezies- und Klassenwahlen, Fertigkeiten und Expertise, Übungsbonus, Rettungswürfe, Fertigkeiten, TP (Stufe 1 maximal + KON, danach fest oder gewürfelt, Zwergen-Zähigkeit, Drachenzauberer-Widerstandskraft), RK (Rüstung, Schild, Ungerüstete Verteidigung, Kampfstil Verteidigung), Initiative (Wachsam), Bewegungsrate (Schnelle Bewegung, Ungerüstete Bewegung), Passive Wahrnehmung, Zauber-SG und -Angriff, Zaubertricks/Zauberanzahl/Zaubergrad, Zauberbuch.
- Überschreibungen (`overrides`): `hp.max`, `armorClass`, `speed`, `initiative`, `proficiencyBonus`, `passivePerception`, `spellSaveDc`, `spellAttack`, `ability.<id>`, jeweils `set` oder `add` mit Begründung. Berechneter Wert und gesetzter Wert werden festgehalten und als Hinweis ausgegeben.
- Robust gegen Müll im Zustand (Test mit beliebigen Fehltypen in jedem Feld).

## Datenkorrekturen aus der Prüfung

- **Hexenmeister-Paktmagie**: In der Tabelle „Hexenmeistermerkmale“ sind die Spaltenköpfe „Grad der Zauberplätze“ und „Zauberplätze“ vertauscht (Werte unter „Grad…“ sind die Anzahl, unter „Zauberplätze“ der Grad). Maßgeblich ist das gedruckte Beispiel „Stufe 5: zwei Zauberplätze des 3. Grades“. Der Build prüft das jetzt und vermerkt den Quellfehler in `spellcasting.sourceNotes`. P1 hatte die Spalten wie gedruckt übernommen; Beispiel-Tests zeigten den Fehler.
- Elfen-Scharfe-Sinne: Fertigkeits-ID `uberlebenskunst` war ein Tippfehler (`ueberlebenskunst`).
- Quellfehler Stufe-1-TP (GES statt KON bei Kämpfer, Paladin, Waldläufer) bleibt wie in P1 entschieden: Rechnung mit KON, Hinweis in den Daten.

## Bekannte Lücken (laufen in P3/P4 mit)

- Wahlen der Herkunftstalente (Geschickt, Begabt) und die Zaubertricks aus Spezies-/Talentwahlen sind noch nicht im Prüfzustand.
- Hexenmeister: Unterklasse-Zauber, Mystisches Arkanum; Magier „Gelehrter“-Einschränkung der Expertise.
- Klassenmerkmal-Effekte außerhalb der Tabellen (z. B. Waffenmeisterschaft im Angriff) gehören zum Blatt (P5).
- Zauberlisten stammen aus den Zauberkopfzeilen; die Klassen-Zauberlisten-Tabellen im Quelltext sind unvollständig (Kandidat Paket 1.0.1).
