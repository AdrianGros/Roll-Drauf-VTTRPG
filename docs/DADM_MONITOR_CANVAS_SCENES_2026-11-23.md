# Monitor: freie Kartenansicht und lesbare Szenen

Status: am 23.11.2026 geliefert, gepusht und über normale Live-Wege abgenommen. Input: Owner-Screenshot zum unübersichtlichen Szenenfenster und Auftrag, Karten frei über ihre Ränder zu bewegen, Ecken zu zentrieren und die vollständige Karte einzupassen. [Discover](DADM_DISCOVER_CANVAS_SCENES_2026-11-23.md), [Apply](DADM_APPLY_CANVAS_SCENES_2026-11-23.md), [Deploy](DADM_DEPLOY_CANVAS_SCENES_2026-11-23.md).

Die Szene hat jetzt einen lesbaren Kartenkopf mit Namen, Thumbnail und Aktivstatus. „Anzeigen“ ist die Hauptaktion; „Optionen“ enthält Namen, übergeordnete Szene, Reihenfolge, Freigabe, Duplizieren und Entfernen. Diese Verwaltung lädt ausschließlich für autorisierte DM. Offene Optionen bleiben nach Änderungen offen. Die Smartphone-Prüfung bestätigt breite Eingaben und lesbare Namen statt der vorher zusammengepressten Reihe aus sechs Symbolbuttons.

Die Kartenwelt verwendet eine lokale freie Translation mit gemeinsamer Skalierung. Pan stoppt nicht mehr am Dokumentrand. Rad, Buttons und Pinch halten ihren Weltanker; FIT zeigt die gesamte Karte zwischen Kopf-/Bedienleisten und funktioniert auch unter 20 Prozent. Kameraänderungen verändern keine Figurenkoordinaten. Der sichtbare Mittelpunkt ist unabhängig von den gespeicherten Dokument-/Objektgrenzen.

## Belege

Vier neue isolierte Browserfälle bestehen in DE/EN für DM, Player und Owner im Spielerplatz bei 320/390/1024/1440 Pixeln. Sie bewegen alle vier Ecken in die Mitte, verschieben die Karte vollständig aus dem alten Begrenzungsbereich, stellen sie mit FIT wieder her, prüfen Rad-/Pinch-Anker und unveränderten Tokenzustand. Echte Umbenennung und Hierarchieänderung werden über die neuen Szenenfelder geprüft. Ein zusätzlicher gezielter Copy/Paste-Test nach Pan und Zoom besteht mit gespeicherten Weltkoordinaten. Die vorhandene echte Android-Reise für Tokenziehen, Pan, Pinch und Abbruch besteht ebenfalls.

Finale Live-Abnahme über Kampagnen-Hub → Sitzung: Chromium-DM 1440/Pergament, Firefox-Player 1440/Nacht, Chromium-DM 390/Nacht und Chromium-Player 320/Nacht. Eine synthetische Karte mit 6000×4000 Pixeln wird vollständig unter 20 Prozent eingepasst; alle Ecken/Anker, freie Randnavigation, lesbare Szenenkarten und unveränderter Tokenzustand bestehen. DM benennen eine Szene um, ändern ihren Elternknoten, aktivieren sie und stellen die erste Szene wieder her. Beide Smartphone-Reisen verwenden echte Touch-/Pinch-Ereignisse. Keine Browserfehler. Die isolierte QA-Fixture einschließlich zweier Benutzer und Zugangsdaten wurde entfernt. Discord-OAuth wurde nicht getestet.

Belege: [Lieferidentität](proofs/canvas-scenes-2026-11-23/delivery.json), [Live-Reisen](proofs/canvas-scenes-2026-11-23/live/live.json), [Bereinigung](proofs/canvas-scenes-2026-11-23/live/cleanup.json), [Betriebsnachprüfung](proofs/canvas-scenes-2026-11-23/postcheck.json), [lokale Prüfungen/Vorbefunde](proofs/canvas-scenes-2026-11-23/verification.json), [Szenen am Smartphone](proofs/canvas-scenes-2026-11-23/live/scenes-dm-chromium-390.png), [aufgeklappte Optionen](proofs/canvas-scenes-2026-11-23/live/scene-options-dm-chromium-390.png).

## Lieferidentität und Rückweg

Funktionsquelle `ca61fc4fd0d28ee524bb6353114c30bf8ea83e1b`, Image `sha256:16304c0ba8313ac37b3129878e3303e74e1cfae4a8010fb1b628181484aa0b7f`. Branch `fix/canvas-scenes-20261123`. Acht Frontenddateien als Overlay auf der tatsächlich laufenden Werkzeuggruppen-Version; 332 Quelldateien im Build und alle acht Änderungen im laufenden Container ohne Hashabweichung geprüft. Andere VTT-Dienste behielten Identität und Startzeit. Reminder-Timer aktiv, zuletzt geprüfter Worker erfolgreich. Keine Backend-/Schemaänderung. PostgreSQL-Sicherung als Archiv lesbar; Restore nicht ausgeführt.

Rollback: `/srv/migration/2026-11-11/feedback-canvas-scenes-20261123/ca61fc4fd/rollback.sh`, syntaktisch geprüft, nicht ausgeführt. Er stellt das unveränderte Vorgängerimage `sha256:4c87060242643b534394516c0a458974c716fd84bc742a84d587b7e72451e516` wieder her.

## Vorbefunde und nächster Schritt

Keine grüne Gesamtsuite behauptet: Der alte Marquee-Test nutzt eine inzwischen nicht mehr gültige Geste ohne Umschalt und eine veraltete Fixture; der gezielte Copy/Paste-Koordinatentest besteht. Die bestehende Initiative-Reise erreicht im kombinierten Lauf ihre Kandidatenerwartung nicht, während der unveränderte Ausgangsstand bereits früher an seiner Speicherbereitschaft scheitert. Der separate Etagen-Modulhost, der keine geänderte Kamera-/Szenendatei lädt, scheitert im kombinierten Lauf an einer Pixelprobe; allein auf unverändertem Stand besteht er. Diese Prüf-/Timinglücken bleiben sichtbar und wurden nicht durch sachfremde Runtimeänderungen verdeckt.

Niedrig: vorhandene Browserseiten müssen neu geladen werden; eine menschliche Vergleichsstudie wird nicht behauptet. Empfehlung: den beauftragten Playtable-Schnitt schließen. Das neu eingereichte Karteneditor-Protokoll ist separat als [27-Punkte-Discover](DADM_DISCOVER_MAPMAKER_REVIEW_2026-11-23.md) mit Zeitmarken und Codeabgleich erfasst. Priorisierte nächste Editor-Untersuchung: deutsche Hotkeys, Assetgrößen pro Sitzung und Katalogfilter; vorhandene Wegpunkte/Namen/Upload bleiben bestehende Basis. Keine Editorfunktion wurde mit diesem UI-Release als umgesetzt bezeichnet.

Artefakte permanent im Projekt; Sicherung und Rückweg zugriffsbeschränkt im Release-Verzeichnis; QA-Zugänge temporär und entfernt. Keine neuen Agents oder Orchestrator-Aufrufe.
