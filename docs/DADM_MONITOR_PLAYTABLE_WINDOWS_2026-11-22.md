# Monitor: verschiebbare Playtable-Fenster und Farbpalette

Status: geliefert, gepusht und live geprüft am 22.11.2026. Der Owner meldete Fenster im Seitenfluss und forderte die Darkmode-Palette für alle Textboxen und Menüs. Ursache war `body.book-shell-app > * {position:relative}` gegenüber dem schwächeren Fensterselektor; außerdem erreichten die an `.tabletop-shell` gebundenen Farbregeln ausgelagerte Fenster nicht.

Die Korrektur bindet ausschließlich die eigenen Bildschirmfenster an `position:fixed`, hält den Header außerhalb des flexiblen Scrollinhalts und bindet schwebende UI-Flächen, Menüs, Formularfelder und Überschriften an die vorhandenen `--ui-*`-Farbrollen. Karten- und Tokenbilder bleiben Dokumentinhalt. Fünf gezielte Browsertests bestehen: berechnete Position, tatsächliche unabhängige Bewegung und Scrollbereiche, Reload-Speicherung sowie Nacht-/Pergament- und Akzentübernahme.

Laufende Funktionsquelle: `07f4bf075`, Image `sha256:5113f840a7b6e60cf22bf9b1d2e80ad9f26ddd296bed9d10da3bab205c2e8137`. App-only-Deployment; andere VTT-Dienste behalten Identität und Startzeit. Keine Schemaänderung. Datenbanksicherung ist vorhanden und als Archiv geprüft; ein Restore wurde nicht ausgeführt. Rollback: `/srv/migration/2026-11-11/feedback-playtable-windows-20261122/07f4bf075/rollback.sh`.

Normale Live-Reise über Kampagnen-Hub → Sitzung: Chromium-DM bei 1440/Nacht, Firefox-Player bei 1440/Pergament und Chromium-Player bei 390/Nacht mit tatsächlicher Touch-Eingabe. Alle drei Reisen bestätigen Drag-Distanz, ruhendes Nachbarfenster, isoliertes Scrollen, Position nach Reload und berechnete Farbwerte für Fenster, Panels, Chat-Textbox, Menü und Menüeintrag. Der Player lädt keine DM-Komposition. Die QA-Konten, Kampagne, Sitzungseinträge und temporären Zugangsdaten wurden anschließend entfernt. Keine Aussage über Discord-OAuth; die Prüfung verwendete isolierte synthetische Kontositzungen.

Belege: [Lieferidentität](proofs/windows-2026-11-22/delivery.json), [Live-Prüfungen](proofs/windows-2026-11-22/live/live.json), [Bereinigung](proofs/windows-2026-11-22/live/cleanup.json), [lokale Prüfungen](proofs/windows-2026-11-22/verification.json). Der vorherige reine Positionsbuild `cc42b9ee9` wurde nicht aktiviert; die Owner-Ergänzung zur Palette ist im tatsächlich aktivierten Nachfolgecommit enthalten.

Residual: bereits geöffnete Browserseiten müssen die neue CSS-Datei durch Neuladen beziehen. Das größere Protokoll-Review-Paket bleibt ein separater Integrations-/Lieferumfang und wurde durch diesen Hotfix nicht versehentlich veröffentlicht.

Nachtrag: Das Review-Paket wurde anschließend separat integriert und geliefert. Die Fenster-/Palettenkorrektur ist im neuen Image erhalten und dort mit allen drei Rollen-/Browserreisen erneut live geprüft. Aktuelle Lieferidentität und Belege: [Review-Monitor](DADM_MONITOR_REVIEW_WEB_2026-11-22.md). Die obigen Imageangaben dokumentieren weiterhin das frühere Hotfixdeployment.
