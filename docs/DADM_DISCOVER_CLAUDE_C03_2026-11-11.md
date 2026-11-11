# Discover C03 – tatsächlicher Anmelde- und Tischlebenszyklus

Status: Faktenaufnahme abgeschlossen; noch kein Auth-Deploy. Profil standard,
Aufbewahrung dauerhaft. Input: R20/R21, absolute sechs Stunden pro Anmeldung.

## Inventar

`vtt/config.py`: Access 1 Stunde, Refresh 7 Tage; Remember-me eigener längerer
Refreshpfad in `vtt/auth/routes.py`. Registrierung, Passwort- und Discord-Login
rufen Tokenfabriken getrennt auf. Refresh mintet neuen Access ohne gemeinsame
Start-/Endclaims. `_create_session_from_access_token` speichert jeweils JTI und
JWT-exp; keine Verbindung zur ursprünglichen Anmeldung.

JWT-Blocklist in `vtt/__init__.py` prüft nur vorhandenen JTI-Widerruf. Logout setzt
alle vorhandenen Session-/TableContext-Zeilen dieses Nutzers auf revoked und leert
Cookies. Refresh-Tokens werden bisher nicht als Session-Zeilen registriert.

P1 `contexts.issue`: acht Stunden Kontextlaufzeit. `contexts.validate` prüft
Kontextablauf und Widerruf der ausgebenden Access-Session, nicht deren expires_at.
Der Socketparser erlaubt nach regulärem Decodefehler `allow_expired=True`, wenn
bereits eine gültige serverseitige Tischdelegation gebunden ist; das ist absichtlich
Teil der P2-Wiederverbindung. HTTP-JWT-Callbacks alleine sichern diesen Weg nicht.

P2-Resume erhält Kontext-ID, effektiven Modus, Ablauf und Receipt-Identität. Das
muss erhalten bleiben; neuer Transport darf keine neue Anmeldung oder DM-Rechte
bedeuten. Member-/Kontorechte werden bei Ein- und Ausgabe erneut geprüft.

## Recherche

[Flask-JWT Refresh](https://flask-jwt-extended.readthedocs.io/en/stable/refreshing_tokens.html)
belegt, dass ein neu erzeugter Token seine neue Ablaufzeit hat; die absolute
Anmeldegrenze bleibt eigene Anwendungslogik. Die
[JWT-Callback-API](https://flask-jwt-extended.readthedocs.io/en/stable/api.html)
beschreibt Claims-/Blocklistprüfung. [Flask-SocketIO Implementation Notes](https://flask-socketio.readthedocs.io/en/latest/implementation_notes.html)
beschreiben die fehlenden before/after_request-Aufrufe je Socket-Ereignis.
Folgerung für dieses Repo: bestehende Socket- und Audience-Prüfung ausdrücklich
in denselben Anmeldevertrag einbeziehen, keine bloße JWT-Konfigurationsänderung.

## Risiken und nächste Grenze

Medium: Refresh darf das absolute Ende nicht verschieben; alle Loginwege müssen
identische Claims bekommen. Medium: ältere Tokens besitzen die neuen Claims noch
nicht; keine unbemerkte Datenmigration oder pauschale Bestandslöschung. Medium:
Socket-Ablauf und P2-Resume müssen dieselbe Zeitgrenze einhalten. Medium:
Widerruf bleibt bei Refresh und Legacy-Token kontrolliert; fehlende Auditzeile ist
keine neue Privilegienquelle. Ein gemeldeter Regelwerk-Logout ist weiterhin nicht
reproduziert und wird nur regressionsgeprüft.

Nächster Schritt: begrenztes Apply für signierte gemeinsame Start-/Endclaims,
Access-/Refresh-Registrierung in bestehenden Session-Feldern, natürliche Drain-
Regel für alte Access-/Tischdelegationen, dieselbe Grenze in Socket/Audience und
kontrollierte Zeitprüfungen. Ob ohne neue Tabelle umsetzbar, im Apply entscheiden;
dieser Faktenbericht trifft keine Architekturentscheidung.
