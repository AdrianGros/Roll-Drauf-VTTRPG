# Konsolidierter Playtable-Auftrag: Apply und Deploy-Handoff

Status: Apply abgeschlossen, Umsetzung durch Owner am 16.11.2026 autorisiert.
Profil standard; retention permanent. Input: erster Sessiondurchgang, Discover vom
15.11. und ausdrückliche Freigabe sämtlicher bisheriger Playtable-Arbeit.

## Konsolidierung und Ziel

Basis ist der live laufende Commit 78133813e. Rollen-/Kontexttrennung, persönliche
Aktionen, DM-Layer/Clipboard, Journal/Assets, Sicht und mobile Gesten bleiben erhalten.
Die bisherigen Playtable-Lieferungen und ihre allgemeine Spielabnahme gelten gemäß
heutiger Owner-Aussage als approved. Historische technische Ergebnisse bleiben
unverändert; daraus werden keine erfundenen einzelnen Hardwaretests abgeleitet.

R01–R06 sind die neue autorisierte Änderung. Die feste Dockplatzierung aus B02 wird
durch frei bewegliche Fenster ersetzt. N07 (Creator-Homebrew), S15/B10 (Kontingente)
und der zurückgestellte N11-Regler sind keine offenen Playtable-Implementierungen
dieser Lieferung. Alte G1-Dateien und andere dirty Worktrees werden nicht übernommen.

## Verträge

1. **Beyond20:** sichtbarer Einstieg in der Tischwerkzeugleiste öffnet kurze Hilfe
   mit Kopierbutton und drei verständlichen Aufgabenblöcken. Browserberechtigung,
   Apply und Reload bleiben erklärt; technische API-Details sind nachgeordnet.
   Status unterscheidet geladene Erweiterung und zuletzt zugestellten Wurf.
2. **Tokens:** ein einziges gleichnamiges Tokenfenster; der zusätzliche Tokenbutton
   zum Werkzeugwechsel entfällt. Im Fenster stehen Platzieren, Bildupload und eigene
   Bibliothek. Der Upload ist gemeinsamer erlaubter Player-/DM-Code, keine Montage
   eines DM-Fragments im Player. Kartenklick öffnet weiterhin den Platzierungsdialog.
3. **Fenster:** bestehende Inhalte werden ohne Kopien in lokale Fenster übernommen:
   Seiten, Initiative, Tokens, DM-Layers, Chat, Journal, Würfelwerkzeuge. Charakterbogen,
   Einstellungen und dynamische Dialoge erhalten denselben Drag-/Positionsmechanismus.
   Öffnen/schließen verändert keine Rolle. Positionen liegen pro Nutzer/Kampagne/Rolle
   lokal im Browser, überleben Reload; Reset ist sichtbar. Pointer-Drag funktioniert
   auch mit Touch, Resize/Vollbild klemmt Köpfe in den sichtbaren Bereich. Hotbar und
   Werkzeuglauncher bleiben fest. Lokale Untermenüs bleiben beim zugehörigen Fenster.
4. **Tokenbibliothek:** additive Tabelle `token_templates`, Besitzer + Kampagne + Tischmodus,
   Revision, Name und erlaubte Vorlagewerte. Lesen/Ändern nur eigene Vorlagen im
   servervalidierten Tischkontext; aktives Kampagnenmitglied erforderlich. Speichern
   aus einem zugänglichen eigenen Token (DM darf zugängliche Tokens als eigene Vorlage
   speichern); Player kann keine DM-verdeckten Werte übernehmen. Nur Bildreferenz,
   Größe, Typ, Rotation, HP-Maximum und Sichtweite; kein aktueller HP-Verlust, Initiative,
   Position, Zustände, Loot oder Geheimnis-Metadaten. Eine berechtigte Charakterbindung wird gespeichert und bei Platzierung auf der
   aktuellen Karte erneut geprüft; pro Karte ist nur eine Bindung derselben Figur erlaubt. Bibliothek ist
   zunächst kampagnenintern und persönlich. Löschen/Ändern verändert keine Instanzen.
   Platzierung nutzt den bestehenden autorisierten Token-Erstellweg mit neuen IDs.
5. **Würfe:** ausgewählter Akteur wird als Token-ID transportiert und serverseitig
   auf Kampagne, Session, Sichtbarkeit und Besitz geprüft. Wurftyp bleibt explizit;
   generische Würfe verändern keine Initiative. Interne Initiative würfelt serverseitig,
   Bogen nutzt den vorhandenen serverseitigen Regelwurf, Beyond20 liefert sein externes
   Ergebnis. Alle nutzen einen gemeinsamen Initiative-Anwendungsdienst. Automatischer
   Kampfstart würfelt künftig nur fehlende Werte; UI startet manuell und würfelt
   fehlende NPC-Werte im dafür definierten Startmodus. Player-Werte werden erhalten.
   Neusortierung bewahrt den aktuellen Akteur, sperrt Encounter gegen konkurrierende
   Updates und sendet rollenprojizierte Combatdaten. Wiederholte Request-/Event-IDs
   werden über vorhandene Receipts bzw. Chat-Event-IDs dedupliziert. Keine Öffnung des
   bestehenden DM-Verwaltungsendpunkts für Player. Angriff/Schaden/Attribut/Save/Skill
   erhalten dieselbe Akteurzuordnung und Anzeige; keine automatische HP-Anwendung.
6. **Kampagnenchat:** additive `campaign_chat_messages`, stabiler Gruppenraum je
   Kampagne, ohne eigens anzulegenden Raumdatensatz. Normale Tischtexte und Gespräche
   verwenden denselben Raum. Sessionwürfe und alte Sessionnachrichten bleiben unverändert
   sitzungsgebunden; private Paare bleiben privat. Kein ungeprüftes Zusammenkopieren.
   Auf `/conversations` erscheinen alle aktiven eigenen Kampagnen plus private Paare.
   Tischlink wählt seine Kampagne explizit. Verlauf per ID-Cursor, Schreiben mit UUID
   als Deduplizierungsschlüssel, Mitgliedschaft/Mute/Ban bei jedem Aufruf. Polling wie
   bestehende private Gespräche, kein neuer Socketraum; Fehler/Entzug löscht sichtbaren
   gecachten Raum. Mitgelieferter Tischkontext muss zur Kampagne passen, Observer dürfen
   daraus nicht schreiben. Keine Owner-/Admin-Sonderleserechte für private Gespräche.

## Risiken und Abnahme

Medium-Risiken aus Discover werden durch diese Grenzen und gezielte Negativ-/Browsertests
behandelt: fremde Vorlagen/Token, Owner-as-Player, verdeckte Layer, konkurrierende
Initiative, Reload/Reconnect, doppelte Würfe, Entzug von Chatmitgliedschaft, Positions-
wiederöffnung und 390px. Kein neues Laufzeitpaket. Neue Tabellen sind additiv und vom
vorherigen Image ignorierbar; vorhandene Nachrichten oder Kampagnen werden nicht migriert.
Die interne Mechanik wird durch gezielte Tests und authentifizierte Live-Reisen belegt;
die echte installierte Beyond20-Erweiterung bleibt zusätzlich durch den Owner testbar.

Deploy-Handoff: isolierter Branch auf 78133813e → Änderungen und gezielte Tests →
Commit/Push → aktuelles Image/Compose prüfen → Datenbankbackup und additive Tabellen →
commitbasiertes App-Image → App-only-Aktivierung → DM-/Player-Live-Reisen durch vorhandene
Navigation. Vorimage und Rollbackscript erhalten; Herkunft/Checks/Schema/Live-Belege
pro Lieferung dokumentieren. Keine separate Staging-Umgebung voraussetzen.

## Begrenzter R05-Rework vor Freigabe des Releases

Die Vorlage erhält die berechtigte Charakterbindung, damit eine Playerfigur auf der
neuen Karte ihre Bogen-/Hotbar-Anbindung behält. Zulässig bleibt ein Token pro
Charakter und Karte innerhalb derselben Session; die bisher sessionweite Sperre
wird auf diese Kartengrenze präzisiert. Bestehende HTTP-/Socket- und Bogenwege
verwenden denselben serverseitigen Linkvalidator. Besitzer, Kampagne, aktuelle
Karte und aktuelle Berechtigung werden erneut geprüft. Vorlagen können niemals
einen fremden Charakter freischalten. Aktuelle HP kommen bei gebundenen Figuren
weiterhin aus dem Bogen; keine Heilung durch erneute Platzierung. Der vorherige
Satz zur grundsätzlich ungespeicherten Bindung wird dadurch ersetzt. Abnahme:
Bibliothek speichert eigene Bindung, neue Karte übernimmt sie, dieselbe Karte
verweigert eine zweite Bindung; bestehender Token und persönliche Hotbar bleiben.

## Begrenzter R03-Rework nach Live-Sichtkontrolle

Die direkte Montage der festen Werkzeugleiste am Body hat die nur unter
`.tabletop-shell` geltenden Reihen-/Labelregeln verloren. Dadurch stapelten sich
die Werkzeuge im ehemaligen Spacer, die Leiste war etwa 235px hoch und Labels
fehlten. Die bereits entworfene feste Leiste bleibt; ihre kompakte Zeile,
Beschriftung, Farbkontraste und `[hidden]`-Behandlung werden ausdrücklich auf die
neue Montageposition begrenzt. Keine Änderung an Aktionen, Rollen oder Daten.
Abnahme: höchstens 90px Leistenhöhe, sichtbare Labels, normale Buttonbreiten,
verdeckte Werkzeuge bleiben verborgen; Menü/Chat/Journal sind horizontal
erreichbar. Browserauswahl und Live-Reisen werden auf diesem Stand wiederholt.
