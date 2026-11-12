# Monitor C03 – sechs Stunden Anmeldung live

Status: technisch ausgeliefert und über normale Live-Wege geprüft. Gesamtprogramm
noch offen. Quelle `7df79fb3f6ef31f739afb4095552ce6abe1a1fb4`, Push erfolgreich;
Image `sha256:e5d675977e9b86b7a421d34d007e86683339b1f1215dbd3240c3c470227fde16`.
Vollständige Daten: [Delivery](proofs/auth-lifetime-2026-11-12/delivery.json).

Sechs Auth-Dateien wurden auf das laufende Kenney-/P1–P3-Image gelegt. 241 bereits
vorhandene Quelldateien nach Hash geprüft; kein lokales P4/C01-UI versehentlich
mitgenommen. Compose/App-only; andere VTT-Dienste unverändert. Vorimage erhalten,
DB-Dump lesbar, kein Schema geändert. Rückweg im Delivery-Beleg, syntaxgeprüft,
nicht ausgeführt. Ein Rollback hebt die neue absolute Policy auf.

Zwei unabhängige Claude-Reviews; Medium-Funde Uhrgrenze und aktueller Refresh bei
Passwortänderung nachgearbeitet. 118 eindeutige Testfälle erfolgreich über zwei
Läufe (109 bestanden, neun Testharnessfehler korrigiert und gezielt bestanden).
Die Anwendung änderte sich zwischen diesen Läufen nicht. Reale Browsercookies
mit CSRF in Chromium und Firefox geprüft; absolute Zeit mit kontrollierter Uhr.

Live: echte Loginformulare, Kampagnenhub-Schaltflächen zum DM-/Player-Tisch,
gegenseitige Präsenz, kein DM-Controller im Firefox-Player bei 390 px. Regelwerk
bleibt angemeldet; tatsächlicher Client-Refresh erhält den ursprünglichen Anker.
Player-Reload bleibt Player. Passwortänderung schont aktuellen Browserrefresh,
zweiter Browser wird abgewiesen. Cookiepfade/Secure/HttpOnly und Abmeldung geprüft.
Eigene temporäre Nutzer, Kampagne, Sessions, Kontexte und Zugangsdaten entfernt;
[Cleanup](proofs/auth-lifetime-2026-11-12/cleanup.json) bestätigt den begrenzten Umfang.

Low-Reste: sehr langsames Signieren unmittelbar am absoluten Ende kann 500 statt
401 erzeugen, ohne Rechte zu verlängern. Bereits vor C03 vorhandenes Logout mit
abgelaufenem Access bleibt separat offen. Legacy-Anmeldungen/Tischkontexte dürfen
wie angekündigt normal auslaufen. Reale externe Discord-OAuth-Interaktion und
Live-Rollback nicht ausgeführt; lokale Callbackfälle erfolgreich. Nächster
begrenzter Schritt: C01 fertigstellen; Low-Reste als eigene Nacharbeit behandeln,
kein stilles Monitor-Feature hinzufügen.
