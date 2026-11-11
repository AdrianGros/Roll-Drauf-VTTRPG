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
Overlay auf dem tatsächlich aktuellen Image → angemeldete Live-Hotbar-/Firefox-Reise → P3.

Quellenabgleich vor Veröffentlichung: Produktion wechselte während der P2-Arbeit
auf `tile-layer-20261111-f526e937` mit
`sha256:d32dd25233615598d03020860f1f0c9a81d79b5b357d0e2eadf02c0b13d76895`.
Alle 22 P1-Pfade stimmen dort unverändert mit dem P1-Manifest überein. Die bereits
laufenden Kartencommits `cb6c7d136`/`f526e937b` werden im Feedbackbranch erhalten;
die Veröffentlichung kopiert nur tatsächlich abweichende P2-Dateien auf diese
Tile-Basis. Das Quellenlabel des fremden Karten-Slices ist kein vollständiger
Git-Baum der gemeinsam laufenden VTT-Funktionen; tatsächliche Datei-Hashes sind
deshalb zusätzlich maßgeblich. Kein Rückschritt auf das ältere P1-Ausgangsimage.

Reconnect-Nachtrag umgesetzt: vergleichendes Capability-Resume desselben Kontextes,
serverbestimmter Modus, SID-Prüfung für Eingänge und Empfänger. Altsocket wird vor
neuem Join getrennt. Neu geprüft: **35** Kontext-/Aktionsfälle plus **1** explizite
Würfelquittung nach Capability-Rotation; **6** Browserfälle (beide Crossbrowser-
Reisen, beide mobilen Größen, parallele Owner-Player/DM-Tabs und Reload).
Quittungen bleiben bei Rotation identisch; Resume mit gefälschtem DM-Wunsch bleibt
Player und fehlende Capability wird verweigert. Der Live-Test wird mit einem
unterbrechbaren, ausschließlich auf den synthetischen Player begrenzten TLS-Tunnel
wiederholt: unveränderte Nutzdaten, Polling und WebSocket gemeinsam unterbrochen.
