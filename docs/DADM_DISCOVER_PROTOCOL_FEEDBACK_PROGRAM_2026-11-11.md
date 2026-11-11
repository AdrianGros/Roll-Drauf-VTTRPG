# Discover: verbleibendes Protokollfeedback als Lieferprogramm

Status: Bestandsaufnahme abgeschlossen; Übergabe an Apply **auf Programmebene**.
Profil: `standard`. Aufbewahrung: dauerhaft. Stand: 11.11.2026.

## Input und Grenze

Der Owner möchte die nächsten Feedbackpunkte sinnvoll ordnen und so weit autonom
ausführen lassen, dass eine gemeinsame Abnahme auf dem Live-VTT möglich wird.
Grundlage sind die [40 Feedbackkarten](PROTOCOL_FEEDBACK_SPECIFICATIONS_2026-11-10.md),
die bereits veröffentlichte erste Lieferung und die verbindliche
[Player-/DM-Entscheidung](decisions/PLAYTABLE_ROLE_SEPARATION_2026-11-01.md).
Dieser Discover-Bericht erhebt Fakten; die folgenden Paketentscheidungen stehen
im separaten [Programmplan](plans/PROTOCOL_FEEDBACK_PROGRAM_2026-11-11.md).

## Aktueller Stand und relevante Inventur

| Bereich | Nachgeprüfter Bestand | Noch nicht nachgewiesen / offen |
| --- | --- | --- |
| Lieferung 1 | Creator, kompakter SRD-Bogen, Kampagnensuche und Kartenbedienung live; Nachweise im [Monitor-Bericht](DADM_MONITOR_PROTOCOL_FEEDBACK_2026-11-10.md). | Keine Behauptung, alle 40 Karten seien erledigt. |
| Tischrechte | `vtt/play/service.py::get_table_role` senkt einen Operator über `TableSeat` auf Player ab; Mitgliedschaft wird erneut gelesen. `table_seats` ist je Session/Nutzer eindeutig. | Kein unabhängiger Kontext je Tab; gemeinsam komponierte `play.html`/`play-ui.js`. |
| Ereignisse | `vtt/socket_handlers.py` verwendet rollenbezogene Räume, nutzerbezogene Räume und Sitzwechsel. | Vollständiger Nachweis für parallele Player-/DM-Tabs, Widerruf, Bootstrap, Resync, Sheet- und Legacy-Pfade fehlt. |
| Aktionsleiste | `play-ui.js::_renderActionHotbar` rendert den vorhandenen Katalog; Zielauswahl und Schutz vor Tastenkürzeln beim Tippen bestehen. `tests/test_action_bar_v1.py` prüft u. a. eigenen/fremden Token. | Keine gespeicherte persönliche Belegung mit Charakteraktionen. Bestehende Zielauswahl ist zu erhalten; ein alter Befund dazu ist kein aktueller Bugnachweis. |
| Homebrew | Aktuelle Creation Engine verwendet Eagle; `creation_engine/routes.py` bietet persönliche und geleitete Kampagnen-Arbeitsräume. `species_routes.py` prüft/veröffentlicht spielbare Spezies. | Hintergrund-/Merkmalsvertrag und vollständige Creator-/Evaluatorbindung fehlen. Ein Authoring-„world“-Scope ist kein vorhandenes geografisches Atlas-Datenmodell. |
| Regelherkunft | Creator-Daten enthalten Merkmals-/Quellenbezüge; Ausrüstungspakete werden erklärt. | Einheitliche, nachvollziehbare Herleitung aller angezeigten Boni fehlt. Konkrete fehlende Talent-/Unterklassen-IDs sind unbekannt. |
| Darstellung | Globales administratives Theme-Modell und lokale SRD-Bogenpräferenz existieren. | Durchgängige Nutzerdarstellung und UI-Sprachkatalog fehlen. Globale Admin-Farben dürfen nicht durch eine Nutzerpräferenz überschrieben werden. |
| Distanzen | Bogen kann m/ft anzeigen. `play-ui.js` dokumentiert `CampaignMap.grid_size` ausdrücklich als Pixel je Rasterfeld. | Physische Rasterkalibrierung fehlt; Pixel sind keine Meter. |
| Karten | Eigene Projektbibliothek, Revisionskontrolle, Raster-/Orts-/Ebenenmodell und Import/Export bestehen. | Kein Landmassengenerator, kein nachgewiesenes Atlas-Domänenmodell. Der [ältere Atlas-Plan](WORLDBUILDING_ATLAS_PLAN_2026-10-25.md) ist ein Entwurf, kein Implementierungsnachweis. |
| Externe Inhalte | Bestehender Assetkatalog mit Credits bleibt erhalten. | Zusätzliche angebotene Dateien/Lizenzen, eindeutige Übersetzungsquelle und Streamingumfang liegen nicht vor. |

## Produktionsidentität und Arbeitsgrenze

Am 11.11. erneut mit `docker inspect` geprüft:

- Container: `roll-drauf-vtt-app-1`, Zustand `running`.
- Image: `roll-drauf-vtt-app:protocol-feedback-20261110-32cc5bfee`.
- Image-ID: `sha256:f6bc1008f0bb03962fba266d3f3477e5edf7c81fcfe205586dab6bd2cc0b445a`.
- Funktionscommit: `32cc5bfee66419176d38248f68d5941144dad79f`.
- Dokumentationsbasis: `f942c74eb53b59a3849a9c88e2b558ee912fbc86`.
- Isolierter, anfangs sauberer Arbeitsbaum:
  `/home/admin/projects/roll-drauf-vtt-feedback-20261110`, Branch
  `feat/protocol-feedback-20261110`; ursprünglichen schmutzigen Arbeitsbaum erhalten.
- Etablierte Compose-Dateien laut bestehendem Releasebeleg:
  `/srv/migration/2026-10-07/setup/production.compose.json` und
  `production.duck-species.override.yml`; vor jeder neuen Lieferung erneut ermitteln.

Die [erste Lieferung samt Rollback](DADM_DEPLOY_PROTOCOL_FEEDBACK_2026-11-10.md)
bleibt die Vergleichsbasis. Ein neueres laufendes Image muss vor Umsetzung erneut
abgeglichen werden. Produktion ist die Abnahmeumgebung; Staging ist keine Voraussetzung.

## Abhängigkeiten und Risiken

| ID / Schwere | Befund / Annahme | Für den Übergang nötig |
| --- | --- | --- |
| R01 – mittel | Vollständige Kontexttrennung ist eine offene Sicherheitsanforderung; dieser Bericht weist keinen pauschalen bestehenden Rechtebypass nach. | Eigenständiger Apply-Vertrag mit vollständiger Pfadinventur, Lebenszyklus und Negativmatrix vor Implementierung des Pakets. |
| R02 – mittel | Reconnect und Mehrfachzustellung können die neue Aktionsleiste betreffen; bisherige Browserabnahme prüfte nicht die geforderte Firefox-Mehrteilnehmerreise. | Ausführungs-/Ereignisvertrag, Wiederaufnahme und Mehrclient-Nachweise definieren. |
| R03 – mittel | Homebrew-/Atlas-Erweiterungen können neue Daten und Migrationen benötigen. | Pro Paket Datenumfang, Rechte, Migration, Backup und kompatiblen Rückweg entwerfen. Kein pauschaler Image-Rollback bei verändertem Datenvertrag. |
| R04 – mittel | Fehlende Quellen-/Lizenzangaben und unklarer 200-%-Bezug verhindern belastbare Einzelabnahmen. | Nur betroffene Zusatzumfänge als inputabhängig führen; keine Inhalte oder Grenzwerte erfinden. |
| R05 – mittel | Ein Atlas-Leser darf keine privaten Orte, Suchtreffer oder Assets erhalten. | Veröffentlichung und getrennte Leserprojektion in Apply prüfen; keine reine UI-Ausblendung. |
| R06 – niedrig | Programm ist deutlich größer als ein Release. | Kleine technisch vollständig geprüfte Lieferungen und einen gemeinsamen abschließenden Owner-Test planen. |

## Offene Angaben

Es fehlen weiterhin konkrete IDs/Quellen fehlender Talente/Unterklassen, das
betroffene 200-%-Bedienelement, neue Assetdateien mit Lizenz und die eindeutige
Regelwerksquelle für Übersetzungen. Öffentliche Partner-/Streamingtests benötigen
eine konkrete Produktentscheidung. Diese Angaben sind kein Hindernis für die
übrigen technischen Pakete. Eine echte menschliche Spielsitzung ist noch ausstehend.

## Verifikation und nächster Schritt

Repo-Status, Releaseidentität, aktuelle Rollen-/Hotbarpfade, Authoring-Einstiege
und vorhandene Nachweise gelesen. Keine Anwendung geändert, keine neue
Anwendungsprüfung oder Veröffentlichung ausgeführt.

Übergabe an Apply: geordnetes Programm, vollständige Kartenzuordnung, technische
Freigabekriterien je Paket und ein zusammenhängender Live-Abnahmeplan. Der
Programmplan ersetzt nicht die noch fehlenden detaillierten Paketverträge.
