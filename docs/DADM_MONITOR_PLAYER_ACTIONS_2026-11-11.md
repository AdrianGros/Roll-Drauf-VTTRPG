# Monitor P2: persönliche Aktionen und Würfelreise

status: technisch live verifiziert; Owner-Abnahme offen. input_summary:
autorisiertes P2, einschließlich Capability-Übergabe bei verzögertem Transportende.
artifacts: [Live-Proof](proofs/player-actions-2026-11-11/README.md), retention permanent.

Beobachtet: normale Kampagnennavigation funktioniert für beide Rollen. Drei Slots
bleiben nach Reload erhalten. Server prüft Charakter/Token, aktuelle Katalogfassung
und Rolle; identische Request-ID liefert dieselbe Antwort ohne erneuten Wurf, auch
nach Capability-Rotation. Firefox↔Firefox und Chromium↔Firefox wurden gegen das
Produktions-VTT mit echten Sockets geprüft. Ein Player-TLS-Tunnel wurde getrennt,
der DM würfelte während der Unterbrechung; Reconnect holte genau eine fehlende
Nachricht nach. Andere Session erhielt null Nachrichten. Mobile Belegung erreichbar.

Die erste Live-Harness-Fassung unterbrach nur einen WebSocket-Versuch, während
Polling weiterlaufen konnte. Der finale Nachweis unterbricht beide Transporte und
prüft die sichtbare Verbindungswarnung. Die beim Reload entdeckte alte SID wird
nun per authentifiziertem Resume rotiert/geschlossen; Modus und Quittungsidentität
bleiben serverbestimmt. Test-Credentials wurden während längerer Arbeit erneuert,
alle ausschließlich synthetischen Datensätze danach gelöscht.

Akzeptanz: persistente Hotbar, autorisierte Referenzen, Wiederholungsquittung,
Firefox-Sende-/Empfangsreise, echte Unterbrechung/Reconnect und Sessionisolation
technisch erfüllt. Finale Source `e8040f9e2`, Image-ID und Compose/Backups im Proof.
Nur App neu gestartet; andere VTT-Dienste unverändert. Commit gepusht. Vorherige
Images erhalten; Backup-Archiv lesbar, vollständige Wiederherstellung nicht geübt.

Residualrisiko low: 24-h-Quittungsfenster und 100-Nachrichten-Reconnectfenster;
ältere Historie über bestehenden Chatabruf. Ungewiss abgeschlossene Claims werden
abgeglichen statt erneut ausgeführt. Zauberplätze/-effekte sind ausdrücklich manuell.
VTT-31 bleibt bis zur echten menschlichen Runde offen. Empfehlung: P2 technisch
schließen, P3 fortsetzen, gemeinsame A06/A07-Abnahme in P7 vorbereiten.
