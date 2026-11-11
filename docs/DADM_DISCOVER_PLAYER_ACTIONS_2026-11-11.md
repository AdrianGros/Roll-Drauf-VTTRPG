# Discover P2: persönliche Aktionen und Würfelwiederaufnahme

status: abgeschlossen. input_summary: P1 live verifiziert; Programm P2 autorisiert.
artifacts: Bericht und nachfolgender Apply-Vertrag, retention permanent.

Der aktuelle Katalog `play/actions.py` hat drei generische Aktionen. Hotbar und
Zielwahl existieren, persönliche Belegung fehlt. Verknüpfte Tokens haben eine
`character_id`. SRD-Bögen berechnen Fertigkeiten, Rettungswürfe, Initiative,
Zauberangriff sowie Inventar-Waffenwürfe bereits serverseitig; `srd_creator.py`
und `sheet_link.py` liefern dafür autorisierte Würfe und persistente Chat-IDs.
Bekannte/vorbereitete Zauber liegen in den gepinnten Charakterdaten. Eine komplette
automatische Effekt-/Zauberslotengine ist kein vorhandener Vertrag.

`play-socket.js` verwendet Sequenzen. Join setzt den bisherigen Sequenzstand vor
dem ersten Snapshot; Wiederaufnahme berücksichtigt keinen Serverneustart. Lücken
fordern nur einen Snapshot an. Bootstrap-Historie wird nur bei leerem Chat geladen;
die Chatdarstellung behält Nachrichten-IDs bisher nicht. `roll_dice` hat noch
keinen dauerhaften Request-Dedup-Vertrag. Socket.IO-Standardzustellung garantiert
keine vollständige Wiederholung verpasster Ereignisse.

risks_and_assumptions: mittel – Wiederholung darf keine zweite Aktion ausführen;
mittel – Autorisierung muss auf jedem Ausführungspfad erhalten bleiben;
mittel – Katalog-/Inventarwechsel müssen veraltete Referenzen erkennbar machen;
niedrig – begrenzter historischer Abruf benötigt einen sichtbaren Umfang.
next_step: Apply konkretisiert gespeicherte Layouts, begrenzte Quittungen,
vorhandene Würfelausführung und autoritativen Wiederabgleich.
