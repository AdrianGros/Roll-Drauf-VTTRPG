# Deploy – Darstellung, UI-Sprache und physischer Kartenmaßstab

Profil `standard`; Grenze gemäß Apply. Implementiert, gezielt lokal geprüft;
Live-Identität und Live-Abnahme werden nach der Auslieferung in Monitor ergänzt.

Gemeinsamer browserlokaler Präferenzdienst und Navigationseinstieg für Pergament/
Nacht, sichere Akzente, DE/EN, Meter/Fuß und optionales Desktop-Sticky-Porträt.
Am Vollbildtisch: Zurück → Ansicht und Sprache. Bogenpräferenzen werden übernommen.
2.190 explizite UI-Quellen/-Schlüssel einschließlich 410 bestehender Eagle-Schlüssel;
Quellpositionen und Kataloge prüfbar, vollständige EN-Werte, gleiche Platzhalter.
Benutzer-/Regelinhalte werden nicht pauschal übersetzt. Eagle-Anbindung über dessen
vorhandene Shim-i18n und den VTT-eigenen Host-Einstieg, dokumentierte Bundle-Patches.

Additive Tabelle `campaign_map_scales`, numerische Skala mit Revision. Geschütztes
DM-Fragment und DM-Controller; Player erhält nur öffentliche Maßstabsdaten.
GET/PUT im bestehenden serverautorisierten Tischkontext; CAS, Ressourcen- und
Rollenprüfung. Maßstabänderung gleicht den Bootstrap ab und zeichnet vorhandene
Messungen sofort neu. Ohne Maßstab Felder, ohne Raster Pixel. Pixelraster und
kanonische Charakterwerte bleiben unverändert. Keine bestehenden Tabellen geändert.

## Gezielte Nachweise vor Live

- 35 API-Fälle: 11 Maßstab-/Zahlengrenzen-/CAS-/Fremdressourcenfälle und 24
  bestehende Tischkontextfälle bestanden; zusätzliche 2 Eigentums-/Ausrüstungsfälle
  bestanden (37 API-Fälle im gemeinsamen Lauf).
- 5 neue reale Browserreisen bestanden: DE/Pergament/1440 Chromium,
  EN/Nacht/1440 Firefox, EN/Pergament/320 Chromium, DE/Nacht/390 Firefox;
  Hauptnavigation → Präferenzen → Bogen → Creator → Karten → Compendium → Eagle.
  Prüfungen: Persistenz, echte Kontroll-/Dialogkontraste ≥4,5, kein horizontaler
  Überlauf, UI-Wort als unveränderter Charaktername, kanonische Figur unverändert,
  optionales Porträt nur am Desktop. Fünfter Fall: DM-Chromium + Player-Firefox,
  echte Messklicks, Kalibrieren/Löschen und unmittelbarer m/ft-Wechsel.
- 6 bestehende Homebrew-Bogenbrowserfälle bestanden. Ein erster Lauf war wegen
  fehlender Chromium-Einbindung nicht ausführbar; mit vorhandenem Browser nachgeholt.
- 6 vorherige deutsche Origin-/Hotbar-/Reconnect-Browserfälle bestanden.
- 3 Creator-/Bogen-Einstiegsprüfungen bestanden; alten quelltextwörtlichen CTA-Test
  an den eingeführten UI-Wrapper angepasst, Ziel unverändert.
- 37 konfigurierte JavaScript-Dateien und alle konfigurierten Inline-Skripte
  syntaktisch geprüft; finale Adapter und Eagle-Bundle zusätzlich geprüft.
  Katalog-Rebuild/Placeholderprüfung und `git diff --check` bestanden.

Vor Live gefundene und behobene Fälle: Parser-UTF16-Quellpositionen, interne IDs
und Fontkonstanten aus UI-Migration ausgeschlossen; neue Messung bei Maßstabwechsel
sofort zeichnen; sichtbarer Präferenzeinstieg im Vollbild-Sitzungsmenü. Zwei
englische Testbeschriftungen wurden an den tatsächlichen Katalog angeglichen.
Bekannte Eventlet-/SQLAlchemy-Warnungen sind unverändert; kein Full-Suite-Versprechen.

## Liefervertrag

Quelle committen/pushen. Aktuelles Image/Compose unmittelbar abgleichen und neuere
Karten-Assetveröffentlichungen erhalten. Nur App über bestehende Compose-Dateien
aktualisieren. Private PostgreSQL-Sicherung vor Anlegen der additiven Tabelle,
Schemareflexion und Image-Hashprüfung. Voriges Image mit Rückweg erhalten; P3 liest
die neue Tabelle nicht und bleibt ein kompatibler Rückweg. Danach normale
Live-UI-Reise mit getrennten DM-/Player-Browsern, eigene temporäre Daten bereinigen,
öffentliche Nachweise ohne Zugangsdaten und Monitor erfassen. Owner-A01–A12 bleiben
bis zum gemeinsamen menschlichen Test ausdrücklich NOT_RUN.

## Nachtrag – noch keine Live-Freigabe

Nach den beschriebenen lokalen Zwischenprüfungen wurden fehlende Buch-Builder-
UI-Quellen ergänzt. Diese Nacharbeit und die neuen Owner-Reviews werden vor
Auslieferung erneut abgeglichen. Das gebaute Image `8d77cab47` ist nicht aktiviert.
Diese Datei dokumentiert die Zwischenprüfungen; sie ist keine Bereitmeldung.
Aktueller Handoff: `docs/plans/VTT_REVIEW_CLAUDE_EXECUTION_2026-11-11.md`.
