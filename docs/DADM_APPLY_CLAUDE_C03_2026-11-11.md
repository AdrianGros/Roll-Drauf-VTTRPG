# Apply C03 – absolute Anmeldegrenze ohne neues Sitzungsschema

Status: Design abgeschlossen; eigener Deploy nach Quellabgleich. Profil standard,
dauerhaft. Grundlage C03-Discover; Ownerentscheidung sechs Stunden und „Go ahead“.

## Vertrag

Gemeinsamer kleiner Auth-Lifetime-Helper für Registrierung, Passwort- und Discord-
Login sowie Refresh. Neue Access-/Refresh-Tokens tragen signierte ganzzahlige
Claims `vtt_auth_started` und `vtt_auth_until`, genau sechs Stunden auseinander.
Teilweise vorhandene, unplausible oder abgelaufene Claims werden verweigert.
Keine Clientangabe setzt diese Zeiten. Access maximal bestehende Stunde und nie
über das absolute Ende; Refresh endet am selben absoluten Zeitpunkt. Refresh
erhält beide Werte unverändert. Remember-me verlängert die Anmeldung nicht.
Cookie-Max-Age ebenfalls höchstens verbleibende Anmeldedauer.

Bestehende Session-Tabelle wiederverwenden: beide Token-JTIs registrieren,
Auditfelder beibehalten, expires_at bei neuen Tokens als absolute Anmeldegrenze
speichern. Damit bleiben bestehender Logout aller Nutzersessions und Widerruf
auch für neue Refresh-JTIs wirksam. Kein Schema-/Datenmigrationsauftrag.
Zentraler JWT-Blocklist-/Claims-Seam und Socketparser prüfen denselben Helper.
Erfolgreiches reines decode_token ersetzt keine Lebensdauer-/Widerrufsprüfung.

Neue TableContexts enden spätestens am signierten Anmeldeende; bei Legacy-Access
höchstens an dessen JWT-exp. `contexts.validate` berücksichtigt künftig zusätzlich
expires_at der ausgebenden Session. Neue Session-Auditzeilen laufen bis zum
Anmeldeende, deshalb bleibt die bestehende serverseitige Tischdelegation über
Access-Refresh hinweg verwendbar. P2-Resume verändert weder Kontext-ID/Modus noch
Ablauf oder Receipt-Identität. Socket-Eingänge und gefilterte Ausgänge bleiben an
Kontext/Mitgliedschaft/Widerruf gebunden. Kein DM-Fallback.

## Bestehende Anmeldung und Rückweg

Keine SQL-Massenabmeldung. Bereits ausgestellte Access-Tokens ohne neue Claims
bleiben bis zum bestehenden kurzen JWT-exp verwendbar. Alter Refresh erhält beim
ersten Übergang die signierte ursprüngliche iat als Anmeldestart, nie „jetzt“.
Ist iat+6 Stunden bereits vorbei, muss erneut angemeldet werden; sonst werden neue
begrenzte Tokens ausgegeben. Auch alte delegierte Tischkontexte beachten die
bestehende ausgebende Session-Ablaufzeit und laufen natürlich aus. Die Koordination
nennt die Wirkung vor Live-Auslieferung ausdrücklich; ein alter Tisch braucht
gegebenenfalls einen normalen erneuten Player-/DM-Einstieg, keine Privilegienrettung.

Für unregistrierte Legacy-Refresh-JTIs muss ein bestehender Nutzer-Logout nach der
signierten iat berücksichtigt werden; vorhandene neue nicht widerrufene JTI-Zeilen
bleiben für frische Logins maßgeblich, auch wenn Logout/Login in dieselbe Sekunde
fallen. Fehlende/kaputte iat oder Teilclaims erhalten keinen Legacy-Ausweichpfad.
Die zwei normalen zeitsignierten Tokenarten sind kein Anlass neue dauerhafte
Geheimnisse oder frei vom Client bestimmte Anker einzuführen.

Vorheriges Image erhalten; additive JWT-Claims liest das alte Image ohne Schema-
bruch. Rückkehr würde die neue absolute Policy wieder aufheben und darf deshalb
nicht als erfüllte Sechs-Stunden-Abnahme berichtet werden. Keine geheimen Werte
in Logs/Prüfdaten; keine Token-/Passkey-/MFA-Neugestaltung.

## Gezielte Abnahme

Kontrollierte Uhr: Login/Registrierung/Discord, Access nach 59/61 Minuten, Refresh
kurz vor und nach sechs Stunden, wiederholter Refresh und Remember-me. Legacy-
Access läuft normal aus; Legacy-Refresh wird niemals zu einer neuen Sechs-Stunden-
Anmeldung; Logout und erneuter Login einschließlich derselben Sekunde korrekt.
HTTP, Socket mit abgelaufenem Access aber gültiger Delegation, absolutes Ende,
Audiencefilter, Reconnect/Resync, Player-/DM-Tabs und fehlender Kontext prüfen.
Regelwerk öffnen ändert den Loginstatus nicht eigenständig. Bestehende P1/P2-
Regression gezielt beibehalten. Live kurze reale Reise plus Zeitgrenznachweise;
Owner braucht keinen sechsstündigen Warte-Test. Separater Claude-Review vor Release.

Die Medium-Risiken aus Discover werden durch die gemeinsame signierte Zeitgrenze,
expliziten Legacy-Vertrag und Transportmatrix behandelt. Wenn die Implementierung
ein neues Schema oder einen anderen Bestandsvertrag benötigt, zurück zu Apply.
