# Deploy / Monitor: Konsolidierung und DM-Token-Layer

Status: technischer Layer-Slice vollständig committed, gepusht und live verifiziert.
Aufbewahrung: dauerhaft. Menschliche Gesamt-Spielabnahme bleibt NOT_RUN.

## Umsetzung und Dateien
- Isolierter Release-Branch `feat/consolidation-dm-layers-20261115`; ursprüngliche
  Arbeitsverzeichnisse unverändert erhalten und inventarisiert.
- Neuer DM-only Layer-/Auswahlbaustein `play-token-layers-dm.js` mit eigener CSS;
  Hooks in `play-ui.js` und `play-dm.js`, vollständige DE/EN-Labels.
- Layers im bestehenden Tisch-Dock, öffentlich/DM-verdeckt platzieren, fremde Ebene
  blass und unselektierbar, Shift-/Rahmenauswahl, gruppierte Anzahl/Bild oder Initialen,
  gemeinsame Freigabe/Rücknahme und Clipboard-Zielebene. Dock überdeckt die Werkzeugleiste nicht.
- `campaigns/routes.py` und `socket_handlers.py`: Leseberechtigung zusätzlich zum
  Tokenbesitz vor Änderung/Löschung/Versionskonflikt; Sichtbarkeit ändern/private Tokens
  erstellen ausschließlich im DM-Kontext. Erlaubte öffentliche Player-Bewegung bleibt.
- Benötigte bereits ausgelieferte Eagle-Build-Artefakte und Duckfolk-Beispiel versioniert;
  zwei obsolete Templatebackups aus dem Image entfernt; keine G1-Wiederbelebung.
- Commit-only Releasewerkzeug `tools/release_committed_vtt.py`, vollständiger Dateiabgleich,
  [Konsolidierung](CONSOLIDATION_2026-11-15.md), [20 Testreisen](acceptance/TEST_CATALOG_2026-11-16.md)
  und CSV-Ergebnisvorlage. Keine Schema- oder Dependency-Änderung.

## Belege

Quellcommit **714f277c8546676a98db9d1cf3aba0fa1041027a**.
Aktives Image **sha256:f2ecedaf58119284a424437389a4e1b36799b65968abbd0900f88bbeb298a345**.
Lieferziel https://vtt.roll-drauf.de. Normale Reise:
Kampagnen → eigener Hub → Sitzung ausdrücklich als DM → Dock neben Tokens → **Layers**.
Player- und Owner-as-Player-Einstiege bleiben unabhängig eingeschränkt.

[Lieferbeleg](proofs/consolidation-layers-2026-11-15/delivery.json),
[Runtimeintegrität](proofs/consolidation-layers-2026-11-15/runtime-integrity.json),
[Live-Reisen](proofs/consolidation-layers-2026-11-15/live.json),
[Prüfungen](proofs/consolidation-layers-2026-11-15/checks.json),
[Cleanup](proofs/consolidation-layers-2026-11-15/cleanup.json).

39 unterschiedliche gezielte Testfälle abgedeckt: 32 im finalen Autorisierungs-/Layerlauf,
5 Darstellungsfälle und 2 zusätzliche Kontext-Browserfälle aus dem Rollenlauf.
Testläufe überlappen; ihre Gesamtsummen wurden nicht als unterschiedliche Tests addiert.
3343 UI-Quellen mit DE/EN-/Platzhalterprüfung. Gesamte Repository-Testsuite nicht ausgeführt.
Die sieben alten Token-Tests ohne Pflichtkontext scheitern bereits auf unverändertem
4158a0c4b; der Beleg bleibt sichtbar. Es wurde kein unsicherer Fallback eingeführt.

Alle **80.855 ausgelieferten Anwendungsdateien** stimmen mit versionierten Quellen überein;
keine zusätzlichen uncommitteten Anwendungsdateien, keine Source-Bindmounts und keine
nachträglichen /app-Änderungen. 81 absichtlich nicht ausgelieferte Altdateien bleiben
außerhalb des Images. Der zuerst verwendete geerbte Compose-Labelwert ist im
[Herkunfts-Erratum](proofs/consolidation-layers-2026-11-15/image-identity-correction.md)
korrigiert; maßgeblich waren tatsächliche Image-ID und Source-Hashes.

## Beobachtetes Ergebnis und Abnahmecheck

- [x] Gruppen-DM-Auswahl zeigt etwa Goblin × 2; beide Tokens sichtbar/verdeckt schalten.
- [x] Versteckte Platzierung erreicht Player weder per HTTP noch Socket.
- [x] Clipboard kopiert und fügt im gewählten Layer an der Mausposition ein.
- [x] Kampagnen-Owner im Player-Kontext erhält bei unerlaubtem Reveal 403;
  auch Socket-/Konflikt-/Löschpfade lehnen ab und geben keine geheimen Daten zurück.
- [x] DM und Firefox-Player über normalen Hub-Einstieg; Owner-as-Player parallel.
- [x] Reload und 390-px-Ansicht, Dock-Tastaturbedienung, keine JavaScript-Seitenfehler.
- [x] Health ok; DB/Redis/Mail beim App-Wechsel unverändert; Backup archivlesbar.
- [x] Nur synthetische Testkonten, Kampagnen und Tokens entfernt, Zugangsdaten gelöscht.
- [ ] Menschlicher Spieltest nächste Woche und Abzeichnung der 20 Testreisen.

Die serverseitige Lücke wurde durch den ersten echten Live-Negativtest sichtbar.
Der zunächst veröffentlichte UI-Slice wurde deshalb nicht als vollständig abgenommen
bezeichnet; ein dokumentierter [Discover/Apply-Rework](DADM_REWORK_TOKEN_LAYER_AUTHORIZATION_2026-11-15.md)
führte zur Reparatur und zum erfolgreichen Wiederholungstest. Reproduktion erfolgte
mit eigenen synthetischen Daten; daraus wird keine Aussage über sonstige historische
Zugriffe abgeleitet.

## Rollback und Restarbeit

Rollback: `/srv/migration/2026-11-11/feedback-consolidation-layer-auth/714f277c8/rollback.sh`.
Vorheriges Image ist erhalten. Skript syntaktisch geprüft, tatsächlicher Rollback und
DB-Restore nicht ausgeführt. Rückkehr zu 3253ad0b0 öffnet die reproduzierte
Autorisierungslücke wieder; dieser Umstand bleibt im Lieferbeleg ausdrücklich sichtbar.

Restarbeit des übergeordneten Feedbackprogramms: N07 (konkrete veröffentlichte
Homebrew-Optionen je Kampagne), S15/B10 (Kontingenterweiterung erreichbar machen),
N11 (Owner-zurückgestellter unbekannter Regler) und B11 (vollständige gemeinsame
Spielabnahme). Kein separater Dev-Zugang ist Voraussetzung der jetzigen Lieferung;
die spätere Dev-Umgebung bleibt für den geplanten Februarstart vorgesehen.

Nächste begrenzte Aktion: zuerst T12/T13/T15 und T01 des Wochenkatalogs gemeinsam
abnehmen, danach die zusammenhängende Begegnung T20. Ergebnis pro Test protokollieren.
