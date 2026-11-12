# Apply C06 – ein eigener Kalender mit bedienbarer Terminplanung

Status: Design abgeschlossen; Deploy nach C01-Integration und genauem WIP-Diff.
Profil standard, dauerhaft. Input C06-Discover/R01–R04, R2 als spätere Präzisierung,
freigegebenes Gesamtprogramm. Private Gespräche bleiben C07.

## Hub und Projektion

Die Kampagnenübersicht trennt eigene/aktiv beigetretene Runden von einem zunächst
eingeklappten öffentlichen Verzeichnis. Vorhandene Suche, Seitenwechsel, Join/
Invite und Moderation bleiben erhalten; öffentliche Seiten haben eine begrenzte
Anzahl sichtbarer Zeilen. Links stehen die vorhandenen Kampagnenwerkzeuge,
rechts oben derselbe Kalender für DM und Player. Bei 390 px folgt der Kalender
ohne horizontales Scrollen unter der Auswahl. Kein zweiter Player-/DM-Kalender.
Vorbereitung bleibt pro Session über den bekannten Hub-Einstieg erreichbar.

Neuer authentifizierter GET `/api/campaigns/my-session-calendar` mit `scope`
(`rolling30` oder `month`), `anchor` (ISO-Datum), `timezone` (IANA) und optionalen
eigenen campaign_ids. Die serverseitige Grundmenge ist Owner oder aktive
Mitgliedschaft in einer nicht gelöschten Kampagne. Invite/Pending/Left/Kicked
und bloß öffentlich sichtbare Runden liefern keine Sessions. Fremde explizite
Filter-IDs werden abgewiesen. Zeitraum maximal ein Monat/30 lokale Tage; Anker
höchstens zehn Jahre zurück oder zwölf Monate voraus. Maximal 200 Einträge pro
Seite mit stabiler UTC-Zeit/Session-ID-Sortierung und weiterem Cursor; keine
still abgeschnittene Vollständigkeitsbehauptung. Membership wird je Seite geprüft.

Eintrag: campaign_id/name, session_id/name, ursprünglicher status,
scheduled_at als UTC mit Z, lokales Datum/Uhrzeit, duration_minutes, normale
Hub-Navigation. Keine session_log, Passwörter oder DM-Vorbereitungsdaten. Absage
bleibt „abgesagt“ und wird nicht aus runtime_status=paused abgeleitet. Monat
verwendet den echten lokalen Monat; rolling30 beginnt am gewählten lokalen Tag.
Sommerzeitgrenzen werden per ZoneInfo in UTC übersetzt, nicht durch Addieren von
24 Stunden pro Tag. UI formatiert nach DE/EN, trennt lokale Zeit und Zeitzone.

Unter dem Kalender zeigt ein begrenztes Alert-Board eigene verwaltete aktive
Sessions ohne Termin und offene Abstimmungen, für die die eigene Antwort noch
nicht vollständig ist. Nur laufende Mitgliedschaft entscheidet den Zugriff;
öffentliche Liste oder globaler DM-Titel reichen nicht.

## Serien-WIP selektiv übernehmen

SessionSeries/SessionOccurrence, Monatsanker, ZoneInfo-Arithmetik, Request-Key/
Digest und Campaign-Writer-Lock aus e2a7a5859 werden selektiv integriert. Keine
alte Navigations- oder Livebasis vollständig übernehmen. Once/weekly/biweekly/
monthly und Absage/Serienende bleiben verfügbar. Erster Termin muss existieren;
Frühlingslücke wird bei Eingabe erklärt, spätere Serienvorkommen folgen dem
bestehenden normalisierten WIP-Vertrag; Herbst verwendet die erste Instanz.

GET-Kalender bleibt eine reine Datenprojektion und erzeugt keine GameSessions.
Serien werden bei autorisierter Erstellung sowie über einen expliziten begrenzten
DM/Co-DM-POST auf einen Horizont von zwölf Monaten materialisiert. Der Hub darf
diesen POST vor seinem Kalenderlesen für berechtigte Verwalter ausführen; Player
tun das nicht. Ein sichtbarer Aktualisieren-Weg bleibt vorhanden. Keine neue
Cron-/Queue-Infrastruktur. Alle Berechnungen erfolgen vom originalen Anker;
Abbruch betrifft nur künftige nicht gestartete Sessions. Alle Schreiber prüfen
aktuelle Kampagnenrechte, darunter `_is_dm` mit carried Player-Kontext, und
serialisieren über denselben Campaign-Lock. Grenzen und Fehler sichtbar machen.

## Terminabstimmung

Neue additive Modelle `SessionDatePoll`, `SessionDateOption`, `SessionDateVote`
in einem eigenen Modellmodul. Poll: Kampagne, noch nicht gestartete Session,
Ersteller, Titel max.100, status open/closed/cancelled, Revision, Request-UUID/
Inputdigest, ausgewählte Option nullable, Zeitstempel. Option: Poll-ID,
Zeitpunkt UTC, optionale Dauer 1–1440 min. Vote: Option-ID, User-ID, value
yes/maybe/no, Zeitstempel; eindeutiges Paar Option/User. Maximal 20 verschiedene
künftige Optionen pro Poll innerhalb von zwölf Monaten. Keine beliebigen HTML-
oder Client-User-IDs. Kandidaten werden nach Erstellung nicht still verändert;
eine neue Auswahl erfordert bewussten Abbruch und neue Abstimmung.

Kampagnengebundene JWT/CSRF-Routen: Poll erstellen/abbrechen/festlegen nur
DM/Co-DM; lesen nur aktive Mitglieder/Owner; eigene Stimmen setzen für aktive
Mitglieder/Owner. Nur der authentifizierte Nutzer stimmt ab. Der Server prüft
bei jeder Option Poll→Session→Kampagne, aktuellen Status und Mitgliedschaft.
Kein Zugriff über eine fremde verschachtelte Option. Poll-Lesen liefert
Optionen, Summen und eigene Stimmen; eine Übersicht pro namentlichem Teilnehmer
erhalten nur Kampagnenverwalter. Kein neuer externer Benachrichtigungsversand.

Erstellung hat Request-UUID/Digest; gleiche Wiederholung liefert denselben Poll,
abweichende Nutzlast 409. Unter Campaign-Lock höchstens ein offener Poll je
Session. Schreiben eigener Stimmen ist PUT/Upsert für bekannte Optionen;
fehlende Antworten bleiben ausdrücklich offen, Reload erhält sie. Abschließen
erfordert erwartete Poll-Revision und ausgewählte eigene Option; setzt in einer
Transaktion scheduled_at/duration der noch nicht gestarteten Session und Poll-
Status. Ist die Session inzwischen gestartet oder anderweitig terminiert,
409 statt Überschreiben. Identische Wiederholung des bereits erfolgreichen
Abschlusses liefert dieselbe Session; andere Auswahl wird verweigert. Damit
erscheint der festgelegte Termin im gemeinsamen Kalender ohne zweite Session.

## Abnahme, Migration und Handoff

Medium-Risiken WIP-Überschreiben, Rechte, Zeitzonen und konkurrierende Schreiber
sind über selektive Dateien, reine Projektionen, Writer-Lock, CAS und additive
Tabellen behandelt. Fokusprüfungen: Owner/Co-DM/Player/Observer/Invited/Removed,
fremde Filter/Session/Poll/Option, carried Player-Kontext, Stimmen nur selbst,
Retry und konkurrierender Abschluss. Kalender: Monatsende, Jahreswechsel,
Europe/Berlin Sommerzeit, UTC/andere IANA-Zone, Absagen, mehrere Kampagnen,
30-Tage-Ansicht und Pagination. Bestehende Serien-/Postgres-Prüfungen anpassen
und im disposable Test-DB-Schema ausführen, niemals in Produktion.

Browser: Kampagnenbuch→Kalenderfilter→Hub→fehlender Termin→Abstimmung erstellen,
Firefox-Player stimmt ab→Reload erhält Antwort→DM legt fest→beide sehen denselben
Termin. Vorbereitung, Join/Invite und P1-Tischrollen bleiben erreichbar. DE/EN,
beide Darstellungen und 390 px prüfen. Migrations-Handoff nur neue Kalender-/
Pollmodelle, Schemaabbild prüfen und vorher DB-Dump. Altes Image kann zusätzliche
Tabellen ignorieren; vorhandene GameSessions bleiben der Rückweg. Exakten
Dateibesitz, Quellencommit, Prüfnachweise und getrennten Claude-Review vor Deploy.

Primärquellen am 2026-11-12 geprüft: [Python ZoneInfo](https://docs.python.org/3/library/zoneinfo.html)
für IANA-Zonen und fold; [SQLAlchemy FOR UPDATE](https://docs.sqlalchemy.org/en/20/core/selectable.html#sqlalchemy.sql.expression.Select.with_for_update)
für zeilenbezogene Writer-Locks. Konkrete Projektions-/Materialisierungsgrenzen
sind Repo-Entscheidungen aus Discover, keine Zusage eines externen Kalenders.
