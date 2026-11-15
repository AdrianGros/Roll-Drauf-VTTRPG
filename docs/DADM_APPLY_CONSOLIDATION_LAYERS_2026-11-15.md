# Apply: konsolidierter Release und DM-Token-Layer

Status: ausführungsbereit im expliziten Owner-Auftrag vom 15.11.; retention permanent.
Input: abgeschlossener Discover dieser Sitzung. Keine neuen Abhängigkeiten/Schemaänderungen.

## Ziel und Schnittstellen
1. Reiter **Layers** neben Seiten/Initiative/Tokens im bestehenden Dock.
   Nur DM-Komposition erzeugt Widget, Handler und Auswahlleiste. Player lädt sie nicht.
2. Zwei Bearbeitungsebenen: Player (`public`, inklusive vorhandener owner_only
   Sonderfälle) und Dungeon Master (`dm_only`). Standard ist Player. Umschalten ist
   eine lokale Bearbeitungsentscheidung und ändert keine Tischrolle oder Tokenrechte.
   Andere Ebene bleibt als blasser Orientierungshintergrund sichtbar und unselektierbar.
3. Erstellen im DM-Layer startet mit dm_only; Zwischenablage fügt im aktiven Layer ein.
   Alle Schreibwege bleiben bestehende versionierte serverautorisierte Token-APIs.
4. Klick, Shift-Klick und Auswahlrahmen wählen nur Tokens des aktiven Layers.
   Kompakte Auswahlleiste zeigt Bild (bei erlaubtem Assetpfad), sonst Initialen,
   Name/Typ und Anzahl, gruppiert nach gleichem Bild und Grundnamen (ohne Kopiennummer).
   Sichtbar machen / Verbergen verschiebt ausgewählte Tokens über bestehende
   visibility-Patches; jede bestätigte Änderung wird neu geladen. Bei Teilausfall
   ehrliche Fehlermeldung und erneutes Laden. Keine erfundene atomare Gruppenoperation.
5. Layerwechsel leert Auswahl und offenen Platzierungsdialog. Leere/veraltete Auswahl
   wird beim Repaint bereinigt. Read-only sperrt Schreiben; andere Seite/Reload
   verleiht keine zusätzlichen Rechte. Bestehende Hotbar und Karten-/Seitenlayer bleiben.
6. Quellabgleich: benötigte ignorierte build.json, Sourcemap und Duckfolk-Beispiel aus
   dem Live-Image in eigenen Herkunftscommit übernehmen. Zwei nicht verwendete
   .html.orig werden im neuen Image entfernt, recoverable im vorherigen Image.
   requirements.txt im Image wird dem bestehenden Commit angeglichen; kein pip-Lauf,
   keine Abhängigkeitsänderung. Alle übrigen 80k Dateien müssen identische Hashes haben.
7. Konsolidierungsbericht und Testkatalog ordnen Protokoll → Karte → Paket →
   Commit/Image/Beleg → menschlichen Test. Original-Discover-Register bleiben historische
   Eingaben. Keine Addition überlappender VTT/C/B-Zahlen als Feature-Gesamtzahl.

## Abnahme und Rollout
- DM erreicht Layers im üblichen Tisch-Dock; Keyboard- und schmale Ansicht bedienbar.
- Verdeckte Tokens erscheinen weder in Player-UI noch Bootstrap/Resync/Socketdaten.
- Owner im Player-Kontext kann weder Surface laden noch Tokens verdecken/freigeben.
- Gruppenauswahl, Anzahl, sichtbare Freigabe und Rücknahme in Chromium/Firefox prüfen;
  Reload/Reconnect behalten Sichtbarkeit und trennen Tabs. Clipboard regressions prüfen.
- Vor Release: gezielte Browser-/Rollen-/Tokenprüfungen, UI-Katalogprüfung,
  Commit und Pushversuch, vollständiger Hashabgleich mit dem tatsächlich laufenden Image.
- App-only Image aus tatsächlicher Live-Basis mit begrenztem committed Overlay;
  vorbereitete DB-Sicherung, unveränderte Nebendienste, recoverable Rollback-Image.
  Bei zwischenzeitlichem Produktionswechsel Abgleich erneut durchführen.
- Danach angemeldete Live-Reise DM/Player/Owner-as-Player, Desktop/schmal,
  technische Fixtures entfernen, Commit/Image/Navigation/Checks/Rollback dokumentieren.
  Menschliche Abnahme bleibt offen bis zum tatsächlich beobachteten Test.

## Deploy-Übergabe
Umsetzung innerhalb dieses Vertrags autorisiert durch den aktuellen Funktionsauftrag.
Kein weiterer Architekturentscheid nötig. N07/S15/N11 werden nicht durch den Layer-Slice
als erledigt markiert. Nach gezielter Prüfung dieselbe Sitzung bis Live-Monitor fortführen.
