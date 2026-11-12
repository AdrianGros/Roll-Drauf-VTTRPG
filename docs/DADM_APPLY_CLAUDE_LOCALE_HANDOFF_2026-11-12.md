# Apply – getrennte UI-Quellen für C02/C04

Discover: C02 und C04 verwenden dieselben vorhandenen VTTUi-Aufrufe, müssten aber
beide extra-messages.json verändern. Der gespeicherte Ausführungsplan erlaubt
höchstens zwei Implementierungen mit disjunktem Dateibesitz. Kein Runtimewechsel
und keine neuen Dependencies sind nötig.

Entscheidung: Der Koordinator erweitert den bestehenden Build um sortierte
tools/i18n/tasks/<task>.json. Dasselbe Format und dieselben DE/EN-, Leerwert- und
Platzhalterprüfungen gelten. Doppelte JSON-Schlüssel werden verweigert; identische
Quellenübersetzungen dürfen wiederholt werden, abweichende vorhandene Übersetzungen
werden verweigert. Nur die vorher geprüften Haupt-Extras behalten ihren expliziten
Override-Vertrag. Kein Browser lädt neue Dateien; der eine vorhandene Bundlepfad
bleibt bestehen.

Deploy-Handoff: Koordinator besitzt Generator, README und erzeugte Dateien. C02
besitzt ausschließlich tasks/c02.json, C04 ausschließlich tasks/c04.json. Prüfung:
Build ohne Fragmente unverändert, positives neues Fragment, doppelter Schlüssel,
Konflikt, fehlende/leerwertige Sprache und Platzhalterfehler werden geprüft.
Rückweg ist der bisherige Generator plus bisheriges Bundle; noch kein Produktfeature
und keine separate App-Auslieferung allein für dieses Build-Hilfsmittel.
