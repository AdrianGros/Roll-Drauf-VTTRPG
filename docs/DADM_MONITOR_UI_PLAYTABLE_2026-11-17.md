# Monitor: UI und Playtable nach vollständiger Lieferung

17.11.2026 · DAD-M standard / Monitor · Status: abgeschlossen · Empfehlung: schließen.
Aufbewahrung: dauerhaft. Eingaben sind das Owner-Protokoll vom 16.11., der
vollständige Apply-Vertrag, die Implementierungsnachweise und die Produktionsabnahme.
Der Owner hat alle 14 Punkte bis zur Umsetzung und Live-Lieferung autorisiert.

## Beobachtetes Ergebnis

Alle U01–U14 erfüllen die Kriterien in
`DADM_DEPLOY_UI_PLAYTABLE_2026-11-17.md`. Die Anwendung ist unter
https://vtt.roll-drauf.de über die normale Kampagnen-/Buchnavigation erreichbar.
Funktionscommit `6a2fcedce2d2396a52109e1093194da902a7912e` wurde gepusht;
das tatsächlich laufende Image ist
`sha256:3de96a3ce53034adc559e5bca92b27d6adcb571848b75022d0bf3735493b358d`.
Die anschließenden Belegänderungen sind ausschließlich Dokumentation.

Die acht abschließenden Produktionsreisen bestehen mit Chromium als DM und
Firefox als Player, ohne Seitenfehler. Der Kampagnenbesitzer bleibt im Player-
Einstieg auch nach Reload Player und erhält auf den DM-Vorschauendpunkt 403.
Die Player-Fläche lädt keine DM-Controller. Einstellungen erreichen den zweiten
Client; Wandbearbeitung, begrenzte Beleuchtung, Tokenvorschau, Seitenhierarchie,
native Initiative und bestätigter Beyond20-Reroll funktionieren über sichtbare
Bedienelemente. Bibliothek und Messung, historische öffentliche Nachrichten,
alle sechs Buchflächen sowie englische Inhalte und 390px-Darstellung bestehen.
Zusätzlich sind Bewegen, Ziehen leerer Fläche mit Wählen und mittlere Maustaste
in beiden Rollen mit unveränderten Token-Weltpositionen live geprüft.

## Nachweise

Alle Dateien unter `proofs/ui-playtable-2026-11-17/`:

- `delivery.json`: Zuordnung jedes Feedbackpunkts zu Navigation, Rolle,
  Kriterium, Prüfung, Quellcommit, Image und Rollback.
- `checks.json` und zugehörige Pass-Logs: gezielte Backend-/Browserprüfungen;
  überlappende Zählungen werden nicht zu einer Gesamtsumme addiert.
- `english-final-checks.json`: 79 englische native Dokumente, vollständiger
  Regelkörper und 1.639 Compendium-Entitäten; Quellen-/Lizenzzuordnung und
  eigener redaktioneller Anteil bleiben unterscheidbar.
- `release.json`, `initial-release.json`, `dialog-release.json`: tatsächliche
  Compose-Konfiguration, additive Tabellen, lesbare Datenbankarchive,
  Imageidentitäten und erhaltene Vorgängerimages.
- `runtime-source-verification.json`: 80.959 Dateien im gebauten Image
  vollständig geprüft und 129 relevante Dateien zusätzlich im laufenden
  Container; keine Abweichungen oder Quell-Bindmounts.
- `live.json`, `live-pan.json` und vier finale Screenshots: echte
  Produktionsabnahme durch die vorhandene Oberfläche.
- `cleanup.json`, `cleanup-pan.json`, `post-cleanup-health.json`: beide
  synthetischen Prüfsätze und Zugangsdateien entfernt; öffentliche Gesundheit
  danach bestätigt. Keine fremden Benutzer- oder Kampagnendaten entfernt.

## Gefundene und behobene Abnahmeprobleme

Die erste Abnahme ist unter `initial-acceptance/` ausdrücklich als
nachzubessern erhalten. Wand-/Lichteditoren wurden vom schwebenden Manager
überlagert; sie werden jetzt wie die anderen Tischfenster darüber eingebunden.
Die visuelle Kontrolle fand anschließend sichtbare DM-SVG-Markierungen in der
Spielervorschau. Das HTML-`hidden`-Verhalten war für SVG angenommen worden;
tatsächliches Attribut und CSS korrigieren es. Eine gezielte Browserprüfung und
die abschließende Produktionsaufnahme bestätigen die Unsichtbarkeit.

Der abschließende Optionsvergleich korrigierte außerdem Sicht ohne platzierte
Lichter und Aufklärung bei ausgeschaltetem dynamischem Licht. Acht Backendtests
prüfen diese Verträge einschließlich gleicher DM-Tokenvorschau. Diese begrenzten
Korrekturen wurden im Apply-Vertrag festgehalten, im Deploy-Schritt implementiert,
committed, gepusht und vor der erneuten Monitor-Abnahme ausgeliefert.

## Restrisiken und nächste Aktion

- Niedrig: sehr komplexe Wandkarten können Rechenzeit verursachen. Eine kalte
  400-Wand-Probe brauchte 0,732 s; Projektion, Speicher und Cache sind begrenzt.
- Prüflücke: Beyond20 wurde über den DOM-Vertrag ausgeführt, nicht als
  installierte Browsererweiterung. Dieser Unterschied ist in den Belegen benannt.
- Prüflücke: Datenbankarchive sind lesbar, Wiederherstellung und Rollback wurden
  nicht tatsächlich ausgeführt. Syntaxgeprüfte Skripte und Vorimages sind erhalten.
- Inhaltliche Einordnung: Das englische SRD enthält lizenzierte Originalregeln
  mit eigenem Buchaufbau und Lesehinweisen; es wird nicht als vollständig
  paraphrasierter Regeltext ausgegeben.

Keine offenen Medium-/High-Befunde oder Lieferblocker. Delay bleibt gemäß
Owner-Entscheidung bestehen; der Character Importer gehört nicht zu diesem Auftrag.
Nächste Aktion: diesen Lieferzyklus schließen und reguläres Betriebsmonitoring
fortsetzen. Es ist kein weiterer Freigabe- oder Implementierungsschritt offen.
