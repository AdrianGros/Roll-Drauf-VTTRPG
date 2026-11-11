# Deploy P2: persönliche Aktionsleiste und Würfelwiederaufnahme

status: implementiert und lokal geprüft; Veröffentlichung/Live-Monitor noch offen.
input_summary: autorisierter Apply-Vertrag P2. artifacts: Laufzeit, Modelle,
Tests und nachfolgender Live-Nachweis, retention permanent.

## implementation_summary / files_changed

`personal_actions.py`, `character_hotbar.py` und `play-personal.js/.css` ergänzen
den aktuellen Tisch: verknüpften eigenen Charaktertoken wählen → persönliche
Leiste → Belegen. Zehn mögliche Plätze, benannte aktuelle Bogenaktionen,
speicherbare Reihenfolge, Entfernen, Tastatur und ergänzendes Drag-and-drop.
Generische Tischaktionen bleiben über „Allgemeine“ und bestehende Werkzeuge erreichbar.
Vollständige fremde Ressourcen sind auch mit geratenen Referenzen nicht bedienbar.

Alle Zahlen kommen aus der bestehenden Charakter-/Inventarauswertung. Bogen und
Hotbar teilen `sheet_link.execute_sheet_roll`; kein zweiter Würfelevaluator.
Benannte vorbereitete/bekannte Zauber sind ausdrücklich Ankündigungen mit manueller
Platz-/Effektverwaltung. Zauberangriffe verwenden den vorhandenen serverseitigen Wurf.

`receipts.py` speichert kontextgebundene Requests und Quittungen für 24 Stunden.
Gleicher Request liefert dasselbe Ergebnis ohne erneuten Broadcast; abweichender
Inhalt zur ID und offene/unterbrochene Claims werden verweigert. Aktuelle UI sendet
IDs; ältere APIs ohne ID behalten ihren bisherigen Vertrag.

Socket-/Play-UI übernehmen Chat-IDs, Sequenzneustart, gleichsequenzige autoritative
Snapshots und erneutes Laden jüngster Historie nach Join/Lücke. Letzte 100 sichtbare
Nachrichten werden aus dem Serverzustand ergänzt. Andere Sessions bleiben isoliert.
Würfe sind vor RNG auf 100 Würfel, 100000 Seiten und Modifikatorbetrag 100000 begrenzt.
Ein optionaler vorhandener Socket.IO-Async-Modus ist für reale lokale Threading-
Transporttests konfigurierbar; Produktion behält den unveränderten Eventlet-Default.

## proofs / acceptance_checklist

- **37** API-/Socket-/Aktionsfälle bestanden: neue persönliche Aktionen sowie
  P1-Rollen-/Widerrufsmatrix und bisherige generische Aktionen.
- **12** weitere Fälle bestanden: bestehender SRD-Bogen und Player-/DM-Komposition.
- **2** echte Mehrteilnehmerreisen: Firefox↔Firefox und Chromium↔Firefox. Ein
  bestehender Transport wird serverseitig geschlossen, Reconnect zeitweise blockiert,
  währenddessen gewürfelt und danach die verpasste Chat-ID genau einmal angezeigt.
  Die isolierte zweite Session empfängt keinen der Würfe.
- **2** mobile UI-Fälle bei 390/320 px bestanden: Belegen, per Schaltfläche
  umordnen, Speichern, sichtbare Slots und kein horizontaler Seitenüberlauf.
  Die neue Leiste liegt über dem vorhandenen mobilen Token-Sheet; dessen untere
  Bedienung bleibt durch zusätzlichen Scrollraum zugänglich.
- `git diff --check` und Python-Kompilierung vor Commit. Live-Einstieg, Release-
  identität, additive Tabellen, Backup, Rückweg und Bereinigung werden im Monitor
  ergänzt; diese lokalen Nachweise behaupten keine bereits veröffentlichte P2-Lieferung.

## risks_and_assumptions / next_step

Niedrig: additive Layout-/Quittungstabellen; vorheriges P1-Image ignoriert sie.
Keine bestehenden Charakterwerte werden migriert. Ein offener Claim nach einem
Prozessabbruch erfordert Zustandsabgleich statt blindem erneuten Ausführen.
Das ist die dokumentierte begrenzte Ausführungsgarantie, kein Exactly-once-Transport.
next_step: Commit/Push → Backup und gezielte Tabellenerstellung → app-only
Overlay auf aktuellem P1-Image → angemeldete Live-Hotbar-/Firefox-Reise → P3.
