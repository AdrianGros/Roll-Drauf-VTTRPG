# Discover: VTT- und Karteneditor-Feedback aus den Oktober-/Novemberprotokollen

Status: abgeschlossen für Spezifikation. Profil: standard. Aufbewahrung: dauerhaft.

## Auftrag und Eingang

Owner-Auftrag vom 10.11.2026: das bereits kategorisierte VTT-/Karteneditor-Feedback
technisch spezifizieren, mit Webrecherche einen passenden Umsetzungsweg bestimmen,
implementieren, committen/pushen und auf `https://vtt.roll-drauf.de` verifizieren.
Geschäftsmodell, Discordorganisation und Charaktervorgeschichte gehören nicht zur
Anwendungsänderung. Die 40 Kanbanpunkte bleiben die Rückverfolgbarkeitsgrundlage.

## Iststand und Inventar

- Laufendes Image: `roll-drauf-vtt-app:oglan-oc1-20261109-8167236`,
  `sha256:496595790afb006e6907fe6ecef49ea617d65802583e300bbb91aeeb01908cf4`.
- Tatsächliche Compose-Dateien:
  `/srv/migration/2026-10-07/setup/production.compose.json` und
  `production.duck-species.override.yml`, Projekt `migration-production`, Service `app`.
  Die alte Repo-Compose-Datei ist nicht der aktive Lieferweg.
- Das Ausgangs-Worktree ist umfangreich dirty; keine seiner Änderungen wird mitgenommen.
  Isolierter Zweig `feat/protocol-feedback-20261110`, Ausgangspunkt `635816d23`.
- Der Live-Stand enthält zusätzliche Engine-, Survey-, Sitzplatz-, Beyond20- und
  Fullscreen-Arbeit. Alle 223 produktiven Python-/JS-/CSS-/HTML-Dateien wurden per
  SHA-256 inventarisiert; abweichende Pfade im isolierten Zweig aus dem laufenden
  Container rekonstruiert. Diese Abgleichbasis ist getrennt von der neuen Umsetzung.
- Aktiver Creator: `srd-creator-steps.js`, `srd-creator.js`, `srd-creator.css`,
  `vtt/characters/srd_creator.py`, Regelberechnung in `creator_rules.py`.
- Spielbogen: `character-sheet.html`, Inventar-/Stufen-/Verwaltungs-Module.
  Vorhandene Inventar- und Rollenschnittstellen bleiben relevant.
- Karteneditor: `vtt/static/mapmaker/`, private Bibliothek und Startauswahl bereits live.
  Ebenen hinzufügen/löschen/umbenennen und Orte bearbeiten sind bereits vorhanden.
- Bereits vorhanden: Karten-Startauswahl statt erzwungener Silbermark, große lizenzierte
  Assetbibliothek, Inventar, Homebrew-Spezies, teilweise kompakterer Spielbogen.
  Diese Punkte dürfen nicht pauschal neu gebaut oder als weiterhin defekt behauptet werden.
- Noch sichtbar: Rüstungswahl umfasst alle Katalogrüstungen ohne Bezug auf Startpakete;
  gewürfelte Werte verschwinden aus Zuordnungslisten; Stufenverlauf zeigt keine
  Klassenmerkmale; Zauberlisten und Detailbereiche vergrößern den Spielbogen erheblich;
  Rechtsziehen ist noch keine Pan-Geste im Karteneditor.
- Vorhandene Tabelle `table_seats` senkt eine Person global je Session auf Spieler ab.
  Das erfüllt noch nicht die vollständige getrennte Darstellung und unabhängige
  Tab-Kontexte aus der Owner-Entscheidung vom 01.11.2026. Eine bloße Hotbar-/Toolbar-
  Änderung darf nicht als Erfüllung dieser Anforderung veröffentlicht werden.

## Abhängigkeiten und Risiken

| Schwere | Befund | Behandlung |
| --- | --- | --- |
| Mittel | Git-/Live-Differenz kann neuere Features überschreiben | Produktive Codebasis isoliert rekonstruiert; Release auf unverändertem vorherigem Image mit ausschließlich protokollierten Overlay-Dateien aufbauen; vor Umschalten Image erneut vergleichen. |
| Mittel | Ungeprüfte historische Bugs können bereits behoben sein | Je Karte Iststand, Spezifikation und Prüfergebnis getrennt führen. |
| Mittel | Rüstungswahl und Inventar können auseinanderlaufen | Nicht nur Beschriftung ändern; Besitz aus gewählten Startpaketen und Finalisierung gemeinsam prüfen. |
| Mittel | Rollenänderung benötigt vollständigen Kontextvertrag | Eigenes Funktionspaket mit HTTP-/Socket-/Sheet-/Legacy-Abnahme; keine scheinbare Absicherung durch Ausblenden. |
| Mittel | Gesten können Zeichnung oder Autosave beschädigen | Pan darf weder Dokumentrevision noch Undo verändern; Cancel/Touch/Pointer Capture separat prüfen. |
| Niedrig | Browserlaufzeit auf diesem Executor nach Neustart unvollständig | Browser-Testimage mit offiziellen Playwright-Abhängigkeiten vorbereiten; Produktionsimage bleibt dabei unberührt. |

Ausgangsprüfung: 42 API-/Static-/Sheet-Fälle bestanden. Vier enthaltene Browserfälle
scheiterten vor dem Seitenstart am fehlenden Browserbinary; kein fachlicher Fehler
aus diesem Lauf abgeleitet. Der Browserzugang wird für die folgenden Prüfungen hergestellt.

## Offene Fragen und Übergabe

Die unklare 200-Prozent-Einstellung ist ohne reproduzierbares Bedienelement kein
begründeter Anlass, Zoom oder Symbolgröße zu beschneiden. Vollständige Übersetzungen,
Worldbuilding und öffentliche Partnerfreigabe benötigen jeweils einen klaren eigenen
Vertrag; die Recherche ist keine Streaming-/Veröffentlichungsentscheidung.

Nächster Schritt: Apply für nachvollziehbare Teilpakete mit Quellen, konkreten
Oberflächen-/Datenverträgen und Abnahmekriterien. Der Owner hat Design, Umsetzung
und Live-Lieferung im aktuellen Auftrag autorisiert; keine weitere pauschale
Releasebestätigung wird als Voraussetzung eingeführt.
