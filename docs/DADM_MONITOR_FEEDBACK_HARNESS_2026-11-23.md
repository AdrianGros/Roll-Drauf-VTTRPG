# Monitor: gemeinsamer Feedback-Schnitt vom 23.11.2026

Status: abgeschlossen für diesen Schnitt; live ausgeliefert und abgenommen, QA vollständig bereinigt. Die unterbrochene Arbeit wurde anhand der vorhandenen Apply-/Deploy-Artefakte, des vorbereiteten Release-Verzeichnisses und des tatsächlichen laufenden Images fortgesetzt. Keine neue Anwendungsscheibe hinzugefügt.

## Quelle, Lieferung und Rückweg

- Quelle: `7e0a3c8595c161eb7ca3442b2d3c7b777366c116`, Branch `fix/feedback-harness-20261123`; der Remote-Branch wurde mit dem vorhandenen Admin-SSH-Schlüssel auf genau diesem Commit bestätigt.
- Live-Ziel: `https://vtt.roll-drauf.de`; Image `roll-drauf-vtt-app:feedback-feedback-harness-20261123-20261111-7e0a3c859`, Identität `sha256:fd604eee0ca2481eddad4658262a32cc112327a60db847b4a18a02893abc1af7`.
- Vorgänger: Funktionsquelle `ca61fc4fd`, Image `sha256:16304c0ba8313ac37b3129878e3303e74e1cfae4a8010fb1b628181484aa0b7f`. Der Stand war vor Aktivierung unverändert. Der geschützte Rückweg liegt unter `/srv/migration/2026-11-11/feedback-feedback-harness-20261123/7e0a3c859/rollback.sh`; Syntax geprüft, nicht ausgeführt.
- Vor Aktivierung: PostgreSQL-Archiv `database-before.dump`, 539343 Bytes; `pg_restore --list` erfolgreich, keine vollständige Wiederherstellung behauptet. Keine Migration, neue Tabelle oder Abhängigkeit. Compose hat ausschließlich die App neu erstellt; Datenbank, Redis und Mailserver behalten Containeridentität und Startzeit.
- Hashabgleich: 334 ausgelieferte Quelldateien stimmen mit dem Commit überein. Alle 17 Overlaydateien stimmen zusätzlich im laufenden Container überein. Geerbte Bildassets wurden nicht verändert oder erneut vollständig gehasht.

Die maschinenlesbaren Belege stehen unter [proofs/feedback-harness-2026-11-23](proofs/feedback-harness-2026-11-23). Das private Release-Verzeichnis enthält Sicherung und Betriebsdaten; Zugangstoken werden nicht in Git übernommen.

## Abnahme und Grenzen

Der erste Live-Lauf bestand Solo-Start einer `ready`-Sitzung, Anlage/Start einer neuen Solo-Sitzung bei 390 Pixeln, Owner als DM, Owner als Player, Mitglied als Player in Firefox sowie die Karteneditor-Reise. Beide Solo-Fälle benötigen weder Karte noch Termin noch weitere Spieler; Doppelklick erzeugt genau einen Start und höchstens die beabsichtigte neue Sitzung. Reload erhält den Sitzplatz. Der private DM-Sentinel erscheint ausschließlich im DM-Bootstrap; die Player-Oberfläche lädt keinen DM-Controller. Der bestehende Kamera-Fit bleibt bedienbar.

Der erste Lauf stoppte anschließend am falschen Testselektor für den Ersteller-Einstieg. Das normale Charakterarchiv erzeugt „Held anlegen“ als Schaltfläche mit `data-dashboard-href`, nicht als Anchor. Der Prüfskript-Selektor wurde auf die tatsächlich sichtbare Schaltfläche korrigiert; keine Produktnavigation wurde dafür geändert. Die sechs bereits bestandenen Reisen und der Timeout bleiben im Erstlaufbeleg sichtbar. Die ersten zwei QA-Benutzer und ihre drei Kampagnen wurden vollständig entfernt, anschließend beginnt ein frischer Gesamtlauf.

Der frische Gesamtlauf besteht **alle sieben Reisen**. Der siebte Weg folgt Übersicht → Spiel & Figuren → Charaktere → „Held anlegen“ → geführter Ersteller → Kämpfer → Einstellungen → Bronze/Petrol → „Klassentext lesen“. Bei 390 Pixeln ändern sich die tatsächlichen Flächen; die Definitionslisten sind als Grid lesbar. Keine Browserfehler in den sieben Reisen. Screenshot und Ergebnisse: [live.json](proofs/feedback-harness-2026-11-23/live.json), [Klassentext](proofs/feedback-harness-2026-11-23/class-facts-teal-night-390.png).

Die zweite Fixture wurde anschließend ebenfalls vollständig entfernt: zwei QA-Benutzer, drei Kampagnen, drei Sitzungen, ein Entwurf sowie abhängige Mitgliedschaften, Kontexte, Karten-/Szenen-/Tokenzustände und Anmeldungssitzungen. Beide geschützten Zugangsdatenmanifeste auf Host und Container sind gelöscht. [Bereinigungsbeleg](proofs/feedback-harness-2026-11-23/qa-cleanup.json).

Gezielte Vorabprüfungen: zehn neue Karteneditorfälle, drei Kartenregressionen, 32 Session-/Rollenfälle, sechs abschließend bestandene Hub-Reisen und drei Navigationskombinationen einschließlich des bestandenen Firefox-Wiederholungslaufs. Die zwölf Ersteller-Palettenfälle und responsiven Klassentexte bleiben unter `creator/probe.json` belegt. Die zuvor noch als laufend gespeicherte Hub-Prüfung ist nachweislich mit `6 passed` beendet.

Keine vollständig grüne Gesamtsuite behauptet: ältere Capability-/Disclosure-/Login-Link-Erwartungen scheitern auch auf unverändertem Ausgangsstand; ein nicht reproduzierter Firefox-Navigationsabbruch bleibt dokumentiert. Eine physische deutsche Tastatur wurde nicht getestet; reale US-Tasten und synthetische AltGr-/Option-Ereignisse sind getrennt ausgewiesen. T2 schließt den berichteten transienten Doppelheader oder alle Atlas-/Gespräche-Layoutbefunde nicht pauschal.

## Unabhängige Quellprüfung und Folgehinweise

Claude Code wurde über dasselbe `claude.ai`-Pro-Abo erneut eingesetzt. Der erste wiederaufgenommene Read-only-Lauf erreichte seine 15-Turn-Grenze ohne Schlussbericht. Ein anschließender werkzeugloser Schlusslauf erhielt den vollständigen Diff und die 20 bereits gelesenen Quellauszüge und lieferte den [abgeschlossenen Quellreview](proofs/feedback-harness-2026-11-23/claude-review.md): keine belegten blockierenden High-/Medium-Befunde. Keine Tests oder Live-Prüfungen durch Claude; Extra Usage wurde im wiederaufgenommenen Lauf nicht benutzt. Rohlogs bleiben außerhalb Git, ihre Prüfsummen und Werkzeuggrenzen stehen im [Ausführungsbeleg](proofs/feedback-harness-2026-11-23/claude-runs.json).

Codex schloss die ausdrücklich unbewerteten Belegfragen: `assetAvailable` ist in `app.js` vorhanden; der `other_session`-Hub-Fall ist Bestandteil des bestandenen Sechserlaufs; die zwölf berechneten Palettenkontraste sind im Creator-Probe belegt. Zusätzlich wurde die Inhaltsverzeichnis-Regressionsprüfung um echte Klicks auf Gespräche, Karteneditor, Atlas und Compendium samt Rückkehr zur Übersicht ergänzt: **1 passed, 7 warnings in 27.19s**. Der bestehende BookShell-Pfad unterstützt diese normalen Navigationen.

**Low, Folgearbeit:** Escape im geöffneten Karteneditor-Dateimenü kann nach dem Schließen bis zum Platzierungs-Handler weiterlaufen und zusätzlich ins Auswahlwerkzeug wechseln. Der Review wertet das als nicht blockierend; in Monitor wurde dafür keine undokumentierte Produktänderung eingeführt. Die zusätzliche Charakterarchiv-Probe bei 390 Pixeln liefert einen 432 Pixel breiten Vollseitenscreenshot; die Kopf-/Buchbreite bleibt ein gesondert zu reproduzierender Layoutbefund und wird durch diesen Schnitt nicht als behoben bezeichnet.

## Restumfang und nächste Grenze

Dieser Schnitt liefert T1/N18, T2/N21 und den Inhaltsverzeichnisteil von N19, C27-S1/E03+E22+E26+E11 mit N02/N17/N16a sowie T4a/N24–N25. Er behauptet keine vollständige Umsetzung aller 27 Editorpunkte.

Nächste getrennte Apply-Pakete: T3/N26 für die durchgängige Regelsprache des Charaktermoduls sowie M2/S2 für bewusst gewählte Ebenenziele und kompakte Ebenenbedienung. Die weiteren Geometrie-, Raster-, Tileset-, Personalisierungs- und Weltverträge bleiben im [Claude-Plan](DADM_APPLY_CLAUDE_MAPMAKER_2026-11-23.md) und [27-Punkte-Papier](CLAUDE_HANDOFF_MAPMAKER_27_2026-11-23.md) vollständig verzeichnet. Die öffentliche KI-Inhaltspolitik E25 bleibt eine offene Produktentscheidung.

Empfehlung: diesen gelieferten Schnitt schließen; für T3/N26 und M2/S2 die nächsten begrenzten Apply-Verträge ausarbeiten. Dokumentation und die erweiterte Prüfskriptabnahme ändern keine ausgelieferten Anwendungsdateien und benötigen kein weiteres App-Deployment.
