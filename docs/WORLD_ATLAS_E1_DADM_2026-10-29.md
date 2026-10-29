# Weltatlas E1 — gemeinsamer kleiner Atlas — DAD-M-Protokoll

**Meilenstein:** ATLAS-E1 · **Stand:** 29.10.2026 · **Profil:** standard, Governance-Regeln wie strict
**Rollen:** Claude Opus 5.5 plant und implementiert; Codex prüft unabhängig.
**Grundlage:** [Weltatlas-Plan (Apply-Entwurf, 25.10.)](WORLDBUILDING_ATLAS_PLAN_2026-10-25.md) §8 „E1“ und §9 Handoff,
[Atlas-Discover D01–D10](proofs/world-atlas-research-2026-10-25/DISCOVER.md),
[Kartenwerkstatt-Prototyp](MAPMAKER_PROTOTYPE_DADM_2026-10-24.md), [Turtonia-Fixes](MAPMAKER_TURTONIA_FIXES_2026-10-26.md),
[Turtonia-Editorpass](MAPMAKER_TURTONIA_EDITOR_PASS_2026-10-26.md), [Navigation/Rollout](MAIN_NAV_MAPMAKER_DADM_2026-10-26.md).

---

## 1. DISCOVER (E1-Backend und E0-Abschluss) — Status: **abgeschlossen**

**input_summary:** Der Nutzer will den Welt-DAD-M-Plan fortsetzen. Laut Plan-Handoff folgt nach E0 ein eigenes
E1-Apply-/Deploy-Paket mit endgültigem Datenvertrag, Migration/Rückweg, Rollenmatrix, Konfliktfällen und
Artefaktfreigabe. Vorher sind vier Entscheidungen (a)–(d) zu schließen. Diese Discover-Runde sammelt die
dafür fehlenden Backend-Fakten; die UX-Recherche vom 25.10. wird nicht wiederholt.

**artifacts:** dieser Abschnitt (Aufbewahrung: unveränderlich nach Abschluss).

### 1.1 E0-Stand (Entscheidung d)
| Plan-Befund (D09 / Interpretation) | Behoben durch | Beleg |
|---|---|---|
| Ungeschütztes Dateiöffnen ersetzt ungesicherte Karte | Ersetzen-Dialog (speichern / verwerfen / abbrechen) vor Öffnen und „Neue Karte“ | Turtonia-Fixes, Deploy/Monitor abgeschlossen; Browsertests |
| Riskanter Wiederherstellungseinstieg | „Wiederherstellen“ ist Standardfokus, Esc verwirft nie | ebd. |
| Verschieben malt je nach Fokus | Leertaste-Ziehen schwenkt auch bei Button-Fokus | ebd. |
| Material-/Ebenenworkflow unklar | Materialien wählen kanonische Ebene (Land / Gelände / Flüsse & Wege) | ebd. |
| Verdecktes Objekt nicht auswählbar | Alt+Klick wechselt durch überlappende Objekte | ebd. |
| Wege nur als Raster | Werkzeug „Wege“ mit editierbaren Pfaden (Ebenenart `paths`) | Turtonia-Editorpass, 42 Browsertests |

**Restbefunde (noch nicht ausdrücklich akzeptiert):**
- **Mittel, Bedienung:** dichte Berge und Beschriftungen überlappen.
- **Niedrig:** kleine Desktop-Viewports (1024×576-Äquivalent) zeigen nur etwa 600×400 px Karte; eine Fokusansicht fehlt.
- **Niedrig:** Projektkatalog und Papierkorb fehlen im lokalen Editor. Das gehört ohnehin zu E1 (Serverprojekte).
- **Niedrig:** stabile Turtonia-Replay mit exakten Zahleneingaben steht noch aus.

### 1.2 Editor heute
- Format `rd-mapmaker` v1 mit Ebenenarten `raster`, `paths`, `stamps`, `labels`. Optionale Felder sind additiv:
  `meta.showTitle`, Orts-`symbol`.
- PNG-, JSON- und ZIP-Export (PNG + `.rdmap.json`) aus demselben Dokumentstand.
- Speicherung nur im Browser (IndexedDB) plus Dateien; **kein Server-Endpunkt**.
- Live unter `/mapmaker`, über die Hauptnavigation (Image-Kette: `mapmaker-nav-20261026-v2` →
  `research-survey-20261029`, jeweils dünne Overlays auf dem laufenden Image).
- Koordinaten: festes Dokument-x/y (x nach rechts, y nach unten); Größe 256–4096 px je Seite; Positionen werden
  auf die Karte begrenzt. Das passt zum lokalen Koordinatenrahmen aus Plan §6.

### 1.3 Backend-Bausteine
| Baustein | Fundstelle | Wiederverwendbar für E1? |
|---|---|---|
| JWT im Cookie + CSRF-Doppelcookie, `jwt_required`, `_current_usable_user()`-Muster, `limiter` | `vtt/config.py:76-81`, `vtt/endpoints/research_survey.py` | ja, als Vorlage |
| SQL-Migrationen, fortlaufend nummeriert, `CREATE TABLE IF NOT EXISTS`; Tests nutzen `AUTO_CREATE_SCHEMA` | `migrations/migration_m82_research_survey.sql` (nächste Nummer: **m83**) | ja |
| Speicheradapter (lokal / S3): `upload`, `download`, `delete`, `exists` | `vtt/storage/__init__.py:7-121` | ja, für Revisionsbilder und Projektdateien |
| Upload-Prüfung (MIME-Liste, 50 MB, Pillow-Inhaltsprüfung) und atomare Quote | `vtt/upload_security.py`, `vtt/permissions.py:277` `try_reserve_storage` | ja |
| Asset-Lese- und Downloadpfade | `vtt/endpoints/assets.py` | **nein**: kampagnengebunden, Karten gelten dort als nicht geheim (D01) |
| Kampagnenrechte `can_view_campaign` / `can_edit_campaign` | `vtt/permissions.py:100,125` | **nein**: Weltrechte sind eigenständig (Plan §5) |
| Einladungen `InviteToken` | `vtt/models/invite_token.py` | **nein**: an `campaign_id` gebunden; Muster (Token, Ablauf, Nutzungen) übertragbar |
| Benutzer: eindeutiger `username`, `platform_role`, `is_usable()` | `vtt/models/user.py` | ja, Einladung per Benutzername möglich |
| Registrierung von Blueprint und Modell | `vtt/__init__.py`, `vtt/models/__init__.py` (beide **vom Nutzer geändert**) | kleine additive Hunks nötig; Vorbild m82 |
| Rollout: dünnes Overlay-Image auf das laufende Image, Compose-Override, Rückweg per altem Image | Survey-Deploy-Protokoll | ja; Produktion braucht eine eigene Freigabe |
| Tests: Flask-Testclient, Playwright-Fixture, Test-venv `/tmp/roll-drauf-mapmaker/test-venv` | `tests/test_mapmaker_browser.py`, `tests/test_research_survey.py` | ja |

### 1.4 Abhängigkeiten und Einschränkungen
- Keine neue Laufzeitabhängigkeit ohne Freigabe. Leaflet wäre eine neue (vendorte) Abhängigkeit, siehe Entscheidung (c).
- Die Migration m83 ist additiv: neue Tabellen, keine Änderung bestehender Tabellen. Rückweg = Tabellen löschen
  (nur, solange keine echten Weltdaten existieren).
- Rasterkarten werden als ganze Revisionen gespeichert (PNG + Projektdatei). Gleichzeitiges Malen auf derselben
  Karte bleibt ausgeschlossen (Plan §5: ein aktiver Bearbeiter pro Karte per Lease).

### 1.5 Risiken
| ID | Schwere | Befund |
|---|---|---|
| E1-D1 | hoch (Sicherheit) | Private Lore oder unveröffentlichte Kartenrevisionen könnten über Asset-, Such- oder Bildpfade an Leser gelangen (D01, D07). Weltdateien brauchen einen eigenen, rechtegeprüften Download und dürfen nicht über `/api/assets/*` laufen |
| E1-D2 | hoch | Ohne Basisrevision / `If-Match` überschreiben sich zwei DMs still (D02) |
| E1-D3 | mittel | Die Registrierung berührt zwei vom Nutzer geänderte Dateien; nur additive Hunks, Diff vorher und nachher prüfen |
| E1-D4 | mittel | Der E1-Umfang (Welt, Mitglieder, Orte, Karten-Revisionen, Platzierungen, Veröffentlichung, Leseransicht, Gruppe, Export, Lease) ist groß. Er braucht Teilaufträge mit gemeinsamer Endabnahme |
| E1-D5 | mittel | Speicherverbrauch: Revisionen à 2–15 MB pro Speichervorgang. Quote und Aufbewahrungsregel nötig |
| E1-D6 | niedrig | Einladen per Benutzername verrät, ob ein Konto existiert. Nur für Besitzer, mit Rate-Limit |

### 1.6 Offene Entscheidungen (blockieren Apply)
- **(a)** Separates Welt-/Ortsmodell (eigene Tabellen) freigeben, vorhandene Dienste (Auth, Speicher, Upload-Prüfung, Quote) wiederverwenden.
- **(b)** Sehen alle eingeladenen DMs (Editoren) die privaten Notizen, und wer darf veröffentlichen?
- **(c)** Viewer für den Atlas: vorhandener Canvas-Renderer oder Leaflet (neue Abhängigkeit) oder zuerst ein begrenzter Vergleich.
- **(d)** E0 schließen und die Restbefunde aus §1.1 akzeptieren oder zuerst beheben.

**next_step:** Entscheidungen (a)–(d) durch den Nutzer, danach Apply (E1-Paket).
