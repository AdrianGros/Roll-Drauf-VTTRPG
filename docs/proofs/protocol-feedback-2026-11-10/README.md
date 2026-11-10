# Nachweise: Protokollfeedback, 10.11.2026

Funktionscommit `32cc5bfee66419176d38248f68d5941144dad79f`;
öffentliche Anwendung `https://vtt.roll-drauf.de`.

| Datei | Beleg |
| --- | --- |
| [deployment.json](deployment.json) | Finales Image, Commit, Umschalt-/Prüfzeit, Health, Rollback, unveränderte andere Dienste. |
| [release-manifest.json](release-manifest.json) | 17 neue App-Pfade mit SHA-256, Ausgangs-/vorheriges und finales Image. |
| [image-integrity.json](image-integrity.json) | 225 erwartete Quell-Hashes und erfolgreicher App-Factory-Start im fertigen Image. |
| [public-static.json](public-static.json) | 13 geänderte Static-Dateien über öffentliche HTTPS-URLs mit identischen Hashes. |
| [tests.json](tests.json) | 195 verschiedene bestandene Fälle und transparente Zählweise ohne doppelte Wiederholungen. |
| [regression.txt](regression.txt) | 159 Creator-/Bogen-/Inventar-/Verwaltungs-/Kartenfälle. |
| [creator-map.txt](creator-map.txt) | 5 gezielte neue Creator-/Finalisierungs-/Pan-Fälle. |
| [navigation-sheet.txt](navigation-sheet.txt) | 28 Navigation-/Layout-/Bogenfälle, Chromium und Firefox. |
| [campaign-fifty.txt](campaign-fifty.txt) | 50 Kampagnen: Suche/Seiten/Navigationsziele in beiden Browsern. |
| [map-navigation.txt](map-navigation.txt) | 4 letzte Kartenfälle: Kontokarte Desktop/Mobil, Pan/Weiterzeichnen, mobile Ortsauswahl. |
| [live-acceptance.json](live-acceptance.json) | Erfolgreiche normale Benutzerwege für Player und DM, einschließlich Firefox-Karteneditor. |
| [cleanup.json](cleanup.json) | Ausschließlich eigene synthetische Konten/Inhalte entfernt; keine synthetischen Konten/Charaktere/Karten übrig. |

Screenshots `sheet-*` stammen aus isolierten Browserprüfungen, `live-*` aus der
öffentlichen Produktion. `campaign-*`, `browser-back-*` und `session-return-*`
belegen lokale Navigationsregressionen. Sichtbare Namen und Inhalte sind synthetisch.
Keine Cookies, Zugriffstokens, echten Benutzerinhalte oder Produktions-Umgebungswerte
sind Bestandteil dieser Nachweise.

Die Prüfungen liefen mit `python -m pytest -q --tb=short --disable-warnings` im
separaten Image `roll-drauf-vtt-feedback-tests:20261110`, mit gemountetem isoliertem
Worktree, passendem Chromium und Firefox und ohne externes Netz. Auswahl und
Ergebnis stehen in den Logdateien und im Deploy-Bericht. Live-Prüfungen liefen
anschließend gegen die öffentliche Produktions-URL, ausschließlich mit eigenen
temporären Testkonten.
