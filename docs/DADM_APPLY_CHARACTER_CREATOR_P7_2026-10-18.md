# DAD-M Apply: Character Creator P7 (Inventar, Ausrüstung, Münzen, Waffenwürfe)

Stand: 2026-10-18, Branch `feat/creation-engine-g1`. Aufbauend auf P6. Parität: Discover-Punkte Inventar/Ausrüstung, Ausgangsausrüstung, Münzen, Traglast, getragene Rüstung und Waffenangriffe.

## Entscheidung

- Kein Schema-Umbau: Gegenstände liegen weiter in `InventoryItem` (Marker in `effects["srd"]`: `itemId`, `kind`, `equipped`; Gewicht in kg). Münzen, "übernommen"-Flag und offene Auswahlen liegen in `character_data["srdInventory"]`.
- Die Rüstungsklasse wird **nie** von Hand gesetzt: angelegte Rüstung/Schild werden in `state.equipment` geschrieben, die Regelrechnung berechnet RK neu (Bogen, `char.ac`, `derived`, offene Tokens).
- Schreibzugriff nur für die Besitzerin oder den Besitzer. Die Spielleitung darf lesen; Ausgabe von Gegenständen durch die SL kommt mit P11.
- Würfe für Waffen sind wie in P6 serverseitig (Trefferbonus, Schadenswürfel und Typ kommen aus Regelrechnung und Katalog) und gehen ins Tischprotokoll.

## Ergebnis

- **Katalog**: 184 SRD-Einträge (Rüstungen, Waffen, Ausrüstung, Werkzeuge, Pakete) aus `creator-data.json`; Pakete (z. B. Entdeckerausrüstung) werden beim Hinzufügen in ihre Einzelteile aufgelöst, gleiche Gegenstände werden gestapelt.
- **Ausgangsausrüstung** (`POST .../inventory/starting-equipment`, einmalig, 409 bei Wiederholung): Paket A/B von Klasse und Hintergrund wird ins Inventar übernommen, Gold aus Paket B bzw. Zusatzgold ab Stufe 2 (Mira Stufe 5: 500 GM). Offene Wahlen (arkaner Fokus, heiliges Symbol, Instrument, Werkzeug) erscheinen als "Noch zu wählen" mit Auswahlliste. Das Zauberbuch wird als eigener Gegenstand angelegt. Passende Rüstung/Schild wird sofort angelegt (Kämpfer: Kettenpanzer, RK 16).
- **Anlegen**: eine Rüstung und ein Schild gleichzeitig, Tausch legt die alte ab. Fehlende Übung und Heimlichkeitsnachteil erscheinen als Hinweise am Inventar. Entfernen einer getragenen Rüstung stellt die RK wieder her.
- **Münzen**: PM/GM/EM/SM/KM absolut setzen oder per Delta ändern (nicht genug Münzen, negative Werte, unbekannte Münzen und Überlauf werden abgelehnt).
- **Traglast** (SRD-Glossar): Stärke × Faktor der Größe (Klein/Mittelgroß 7,5 kg), Heben/Schieben das Doppelte, Münzen 0,01 kg; Anzeige als Balken, über der Tragkraft Hinweis auf Bewegungsrate höchstens 1,5 m. "Kräftiger Körperbau" wird berücksichtigt.
- **Angriffe**: je Waffe und Waffenloser Schlag: Trefferbonus (Finesse nimmt das bessere von STR/DEX, Fernkampf DEX), Übung aus Klasse/Mehrklassen-Gewährungen, Schaden mit Typ, Vielseitig (zweihändig), aktive Waffenmeisterschaft. Knöpfe: Angriff, Schaden, Kritisch (doppelte Würfel), Zweihändig. Ergebnisse stehen im Tischprotokoll ("Mira Eulenfeder · Schaden: Dolch (Stich) (Kritisch): würfelt 2d4+1: 3 + 2 +1 = 6").
- **Eigene Gegenstände** (Name, Gewicht, Anzahl, Beschreibung); Beutestücke aus dem alten Beute-Weg erscheinen als eigene Gegenstände und zählen beim Gewicht mit.
- **Oberfläche**: Block "Inventar und Angriffe" im SRD-Bogen (Suche im Regelwerk, Anzahl, Anlegen/Ablegen, Entfernen, Münzen, Übernahme der Ausgangsausrüstung). In der Ansicht ohne Bearbeiten sind alle Steuerelemente gesperrt. Die alten Abschnitte "Ausrüstung" und "Inventar" sind bei SRD-Charakteren ausgeblendet.
- Creation Engine bleibt unangetastet.

## Tests

- Neu `tests/test_srd_inventory.py` (18 Tests): Übernahme einmalig/Paket fehlt/Gold-Pakete/Kämpfer mit Kettenpanzer, RK-Fluss (Leder, Schild, Tausch, Ablegen, Entfernen, `char.ac`, Token-Push), Stapeln und Paketauflösung, eigene und alte Beutezeilen, Münzen, Traglast, Waffenwerte (Dolch, Kampfstab, Langschwert, unbewaffnet, Meisterschaft), Würfe inkl. Kritisch, Zweihändig, Protokoll, Berechtigungen (Fremde 403, SL nur lesen, Nicht-SRD 422), offene Wahlen.
- Neu `tests/test_srd_inventory_browser.py` (Chromium, 1440/390 px): Übernahme, Wahl, Hinzufügen, Anlegen mit RK 11 -> 12 -> 11, Waffenwürfe, Münzen mit Fehlermeldung, Überlast und Rückbau, Ansichtsmodus ohne Steuerelemente.
- Regression grün: Regelwerk-Suite, Ersteller-API, Würfe/Bogen, Charakter-/Token-/Spieltisch-Tests, `tests/creation_engine`.

## Bekannte Lücken (ehrlich)

- Zustände (Conditions) werden nicht zwischen Bogen und Token synchronisiert; keine Abzüge durch Traglast außer dem Hinweis.
- Das Zauberbuch hat Gewicht 0 (SRD-Daten nennen keines).
- Waffenübung nur aus Klasse und Mehrklassen-Gewährung, nicht aus Talenten oder Spezies. Hände/Zweiwaffenkampf werden nicht modelliert ("In der Hand" ist nur eine Markierung).
- Gewürfeltes Gold und magische Gegenstände bei höherer Startstufe sind Sache der Spielleitung (Hinweis im Bogen), Ausgabe durch die SL folgt mit P11.
- Der alte Weg `/api/characters/<id>/inventory` besteht weiter (unmarkierte Zeilen zählen als kg und eigene Gegenstände).
- Würfe ohne laufende Sitzung werden nicht nachträglich protokolliert; Eigene Gegenstände lassen sich in der Oberfläche nicht umbenennen (nur per API); Mehrfachwürfel-Anzeige am Bogen ist textuell.
