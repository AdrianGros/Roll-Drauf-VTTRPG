# B04 – verständlicher Charakterbau

Status: Apply abgeschlossen. Input: N02–N06; N07 erhält vor seiner getrennten Umsetzung
einen eigenen Vertrag für serverseitige DM-Freigaben. Retention: dauerhaft.

## Fakten und Grenze

Die Klasse hat bereits eine Detaildefinition, wird jedoch als ungegliedertes `dl` angezeigt.
4W6 speichert sechs Würfe und Attributswerte; die UI verdichtet gleiche Summen zu einem Eintrag.
Der Server prüft die Multimenge korrekt. Eigene veröffentlichte CE-Hintergründe und deren
zulässige Attributtripel sind bereits vorhanden und serverseitig zugriffsgeschützt.
Unterklassen im Kompendium nennen einzelne Merkmals-IDs mit der jeweiligen Klassenstufe.
Creator und Aufstiegsdialog haben bisher keinen sichtbaren Text am Auswahlort.
Zauber haben numerische Grade, der Creator filtert bereits, beide Auswahlen können sortiert werden.

## Entwurf / Schnittstellen

Klassenkarten bleiben kompakt. Detaildaten bekommen ein responsives Faktenraster und getrennte
Merkmalsliste. Keine zusätzliche mechanische Zusammenfassung erfinden.
Die sechs Würfelsummen erscheinen einzeln mit Wurfnummer und Zuordnung; Dropdowns enthalten
alle sechs Vorkommen, verbrauchte Vorkommen deaktiviert. Die UI ordnet gespeicherte Zahlen
deterministisch nach Attributreihenfolge den ersten freien passenden Würfen zu. Persistenz und
serverseitige Multimengenprüfung bleiben unverändert. Ein Duplikat ist kein zusätzlicher Wurf.

Hintergründe zeigen ihre erlaubten Attributtripel schon auf der Karte. Ein erklärter Link öffnet
die vorhandene CE-Herkunftswerkstatt in einem neuen Tab; ein expliziter Aktualisieren-Knopf
lädt den zugelassenen Katalog neu, ohne den Entwurf zu ersetzen. Keine fremden Buchinhalte.

Das vorhandene Aufstiegs-Needs-Objekt erhält additiv `subclassId` für die bereits gewählte Unterklasse.
Ein kleines gemeinsam genutztes DOM-Modul lädt kanonische Kompendiumseinträge mit Cache und
zeigt Unterklassenmerkmale bis einschließlich der gewählten Klassenstufe inline. Feature-IDs
und `level` aus dem bestehenden Kompendium sind die Quelle; zukünftige Merkmale werden als
solche getrennt angeboten. Sichere Textknoten/strukturierte Blöcke, keine `innerHTML`-Regeltexte.
Ladefehler sind sichtbar und verhindern weder Speichern noch die vorhandene Regeltextansicht.
Creator-Schritt heißt „Merkmale und Talente“. Der Aufstiegsdialog zeigt auch beim späteren
Aufstieg die bereits gewählte Unterklasse und ihre neu erreichten Merkmale.

Zauberauswahl: explizit „Grad, dann Name“ oder „Name“, Standard Grad. Bei Änderung nur DOM-Reihenfolge;
Filter, gesetzte Häkchen, gesperrte Buchzauber und Fokus bleiben funktionsfähig. DE/EN-Beschriftungen.

## Risiken / Kriterien / Deploy

Medium: doppelte Würfe dürfen nicht dupliziert/verschluckt werden → Browser-Zuordnung mit
identischen Summen, Speichern/Reload und Server-Validator prüfen. Medium: Unterklassentext darf
keine falsche Stufe suggerieren → echte Kompendium-IDs und Stufen prüfen. Medium: Katalogrefresh
darf Entwurf und veröffentlichte Versionsbindung nicht ändern → bestehende Auswahlen behalten,
Server bleibt Autorität. Keine Schema-, Auth-, Rollen- oder Abhängigkeitsänderung.

Gezielte Creator-/Aufstiegs-Browserprüfungen und bestehende Regeltests; dann Commit/Push,
aktuelles Produktionsimage abgleichen, bestehender App-Release und Live-Prüfung über
Charakterarchiv → Ersteller bzw. Bogen → Aufstieg. Beleg mit Rollen, Quelle, Image,
Rollback und offener Owner-Abnahme. N07 bleibt im Gesamtplan ausdrücklich offen.
