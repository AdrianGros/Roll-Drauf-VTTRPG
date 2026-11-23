# Deploy: ausgewählte Playtable-Werkzeuggruppen

Status: Umsetzung der am 23.11. freigegebenen Empfehlung. Dieser Bericht dokumentiert den Implementierungsschnitt; der abschließende Live- und Lieferstatus steht im zugehörigen Monitor-Bericht.

## Input und Grenze

Grundlage: [freigegebenes Konzept](DADM_APPLY_PLAYTABLE_UX_2026-11-23.md) und [Liefervertrag](DADM_APPLY_TOOL_GROUPS_DELIVERY_2026-11-23.md). Die Research-Entwürfe bleiben unverändert. Keine neuen Spielregeln, Tabellen, Pakete oder API-Schreibwege. Kein Agent oder Orchestrator wurde für die Umsetzung aufgerufen.

Die tatsächliche Live-Basis wurde erneut geprüft: Quelle `a6abcce9e34b289efb88cb525a0c4c3ae87037e4`, Image `sha256:5726f87c57a3106b3e2337b5761b9449b80f7d8b093810e56aef0cdc682443b3`. Die neuere Fenster-/Palettenkorrektur und das bisherige Protokollpaket bleiben über diese Imagebasis erhalten.

## Implementierung

Drei feste Gruppen ersetzen die lange uneinheitliche Zeile: Auswählen/Bewegen/Messen; Szenen/Figuren/Initiative/Karte & Sicht; Chat/Würfeln/Mehr. Player haben neun Hauptzugänge und laden keine DM-Befehlsdefinitionen. Jeder Hauptzugang verwendet ein lokales monochromes Symbol und einen sichtbaren Namen, dieselbe 52-Pixel-Höhe, Schrift, Farbrollen und Fokusdarstellung. Ein gedrücktes Werkzeug und ein geöffnetes Fenster haben verschiedene Zustände. Schmale Ansichten brechen ganze Gruppen um.

`PlayToolGroups` registriert und verschiebt bestehende Buttons mit ihren bereits gebundenen Handlern. Bestehende Element-IDs, Formularinstanzen, Datenverträge und Autorisierung bleiben erhalten. `PlayToolGroupsDM` wird ausschließlich im vorhandenen serverautorisierten DM-Ladepfad geladen. Wand/Licht/Markierungen liegen in Karte & Sicht, Token-Sichtbarkeit in Figuren, Etagen weiterhin im Kartenfenster und Einrasten im Messkontext. Mehr enthält Journal, Beyond20, eine durchsuchbare Befehlsübersicht, Tischmenü, Einstellungen, Fenster-Reset, Hilfe und Tisch verlassen; die DM-Komposition ergänzt Sitzungsverwaltung.

Mehr schließt vor dem Ausführen einer gewählten Funktion. Fenster bleiben separat verschiebbar, scrollen unabhängig und behalten Positionen nach Reload. Verdeckte Fensteröffner erhalten sichtbare Fokusrücksprünge. Änderungen der unteren Leistenhöhe fließen in die bestehende Fensterbegrenzung ein. Die Messoptionen liegen oberhalb der unteren Leisten, jedoch unter geöffneten Fenstern; ihre Felder übernehmen dieselbe Palette. Die persönliche Aktionsleiste bleibt ein eigener Bereich.

Geänderte Laufzeitdateien: `play.html`, neue Module `play-tool-groups.js`/`play-tool-groups-dm.js`, neue CSS-Datei und lokaler SVG-Symbolsatz; begrenzte Integrationsstellen in `play-ui.js`, `play-feedback-dm.js` und `play-windows.js`. Die neuen Namen werden über das vorhandene i18n-Fragment generiert. Browserreisen folgen den neuen Einstiegen; sie ersetzen keine echten Handler durch Testkopien.

## Verifikation und Abnahme

Befehle, Ergebnisse und bekannte Vorbefunde werden in [verification.json](proofs/tool-groups-2026-11-23/verification.json) erfasst. Die Prüfung umfasst Chromium/Firefox, DE/EN, 320/390/1024/1440, Owner im Spielerplatz, die vorhandenen Rollen-APIs, Nacht/Pergament, echte Messschalter, Formularentwürfe, frei verschiebbare Fenster, Begleiter, Initiative, Journal, Token-Sichtbarkeit und Beyond20. Mobile Zusatzreisen prüfen Chromium/WebKit einschließlich Touch und Rotation. Der komplette Repository-Testbestand wird nicht als grün behauptet.

Die alten Quelltext-Stringtests `test_public_surface_and_playtable_contract.py` haben acht identische Fehler auf unveränderter Baseline und Umsetzung. Ein initialer Begleiter-Browserlauf scheiterte beim asynchronen Laden; die isolierte Wiederholung bestand in beiden Engines. Weitere ältere Mess-/Nebelreisen scheitern bereits auf der Baseline; Ergebnisse werden explizit getrennt erfasst. Aus der Messkontextprüfung gefundene neue Paletten-/Überlagerungsfehler wurden vor Veröffentlichung behoben. Der Kalibrierungstest betätigt jetzt ausdrücklich das von ihm vorausgesetzte Einrasten.

## Lieferung und Rückweg

App-only-Overlay auf dem tatsächlich laufenden unveränderlichen Image; Quelldateien werden im gebauten Image per Hash geprüft. Vor Aktivierung: PostgreSQL-Archiv sichern und Lesbarkeit prüfen, keine Migration ausführen. Ein Restore wird nicht als getestet behauptet. Compose-Identitäten und Startzeiten der übrigen VTT-Dienste sowie der aktive Reminder-Timer bleiben erhalten. Commit/Push und tatsächliche Image-/Rollback-Identität werden im Monitor protokolliert.

Live-Abnahme führt isolierte temporäre QA-Konten über Kampagnen-Hub → Sitzung in DM- und Player-Kontexte. Sie betätigt die neue Leiste einschließlich echtem Raster-Speichern und prüft Fensterbewegung, Scrollen, Reload und berechnete Palettenwerte. Die Fixture wird anschließend mitsamt temporären Zugangsdaten entfernt. Discord-OAuth und eine menschliche Usability-Vergleichsstudie werden dadurch nicht nachgewiesen.

Risiken/Annahmen: niedrig — bestehende Sitzungen müssen die neuen Dateien neu laden; bekannte ältere Testlücken bleiben gesondert sichtbar. Die Wirksamkeit der vereinfachten Gruppierung muss sich im tatsächlichen Spielbetrieb zeigen. Nächster Schritt: abschließender Testnachweis, Commit/Push, Live-Aktivierung und Monitor-Abnahme.

Artefakte: dieser Deploy-Bericht, Test-/Screenshotbelege und Lieferidentität — permanent im Projekt; Datenbankarchiv und Rollback — zugriffsbeschränkt im Release-Verzeichnis; Zugangsdaten — nur temporär, nach Abnahme zu entfernen.
