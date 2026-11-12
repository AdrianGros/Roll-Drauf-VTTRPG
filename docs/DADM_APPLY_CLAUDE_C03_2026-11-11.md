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

## Präzisierung nach unabhängigem Review am 2026-11-12

M1: Die endgültige JWT-exp wird ausdrücklich aus dem gemeinsamen ganzzahligen
Anker berechnet: Refresh exp=until, Access exp=min(now+Accessdauer,until).
Kein erneutes relatives Ableiten von einer zweiten Bibliotheksuhr. Ein kontrollierter
Sekundenwechsel zwischen Helper und JWT-Bibliothek darf keinen exp>until erzeugen.

M2: Passwortänderung erhält das aktuelle Login einschließlich eines gültigen
aktuellen Refreshpfads, während andere Geräte widerrufen werden. Ausgenommen
werden nur konkrete geprüfte JTI-Werte, niemals pauschal alle Zeilen mit gleicher
expires_at (zwei Logins in derselben Sekunde teilen diesen Wert). Ein zum
aktuellen Login gehörender Refresh-Cookie muss signatur-/typ-/user-/lifetime-
geprüft werden; neue Claims müssen denselben Anker tragen. Fehlende/fremde/
ungültige Cookies verleihen keine Ausnahme. Ein gültiger Legacy-Refresh darf
vor dem Widerruf explizit als geprüfter eigener JTI bis zu seiner ursprünglichen
iat+6h-Grenze registriert werden, sodass der Legacy-Logout-Cutoff ihn nicht
versehentlich zur fremden Sitzung macht. Kein neuer Startanker. Das aktuelle
Access-JTI und daran gebundene Kontexte bleiben erhalten. Reset ohne aktuelle
Passwortauthentifizierung und Logout behalten ihre vollständige Widerrufspolitik.

Zusatzabnahme: Sekundenwechsel beim Signieren; aktuelles Gerät nach Passwort-
änderung und Accessablauf kann refreshen, zweites auch in derselben Sekunde
angemeldetes Gerät nicht; fremder/fehlender/ungültiger Cookie wird nicht geschont;
gültiger Legacy-Refresh bleibt am ursprünglichen Ende begrenzt. Der bestehende
Low-Befund Logout mit bereits abgelaufenem Access wird separat verfolgt und hier
nicht als zusätzliche Featurearbeit eingeschoben.

### Browser-Cookies gehören zur M2-Grenze

Der Worker hat den noch nicht im ersten Review berücksichtigten Istzustand
bestätigt: Refresh-JWT **und** Refresh-CSRF-Cookie haben aktuell Path
`/api/auth/refresh`. Daher erhält `/api/auth/password/change` keinen Refresh-JWT;
die normale Seite kann den für Auth.refreshAccessToken benötigten CSRF-Wert
ebenfalls nicht über document.cookie lesen. Ein Testclient mit Cookies auf `/`
beweist diesen Browserweg nicht.

Festlegung: Refresh-JWT bleibt HttpOnly/Secure/SameSite nach bestehender Policy
und bekommt den begrenzten Path `/api/auth`. Refresh-CSRF bekommt Path `/`, damit
die vorhandenen Seiten den Double-Submit-Header lesen können. Kein JWT in JS,
LocalStorage, URL oder Antwort-JSON. Die normalen Auth-Endpunkte prüfen weiter
Tokenart und CSRF. Beim Ausstellen eines neuen Refreshpaars werden die alten
beiden Cookies mit Path `/api/auth/refresh` ausdrücklich gelöscht, damit sie
nicht durch längeres Path-Matching die neuen Cookies verdecken. Logout löscht
auch diese alten Pfadvarianten. Domain-/Secure-/SameSite-Konfiguration erhalten.

Neue Browserprüfung mit aktiviertem JWT_COOKIE_CSRF_PROTECT und tatsächlich vom
Server ausgestellten Cookies: normale Regelwerkseite kann refreshen, Passwort-
änderung schont aktuelles Gerät, zweites Gerät wird abgewiesen, alte Pathvarianten
werden beseitigt. Access-Cookie darf zur Simulation seines Ablaufs entfernt
werden; die absolute Zeitgrenze bleibt separat kontrolliert geprüft. Die alten
laufenden Anmeldungen erhalten keinen stillen neuen Zeitanker; die bereits
beschriebene normale Wiederanmeldung bleibt der Bestandsübergang.

Primärquellen am 2026-11-12 geprüft: [JWT-Cookie-Konfiguration](https://flask-jwt-extended.readthedocs.io/en/stable/options.html#JWT_REFRESH_COOKIE_PATH),
[Cookie-/Double-Submit-Beispiel](https://flask-jwt-extended.readthedocs.io/en/stable/token_locations.html)
und [Cookie-Path](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie).
Die konkrete Pfadwahl ist die hier begründete Repo-Entscheidung.
