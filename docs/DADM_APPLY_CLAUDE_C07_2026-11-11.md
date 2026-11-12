# Apply C07 – interne Zweiergespräche

Status: Design abgeschlossen, Deploy erst nach C02/C06 und Dateihandoff.
Profil standard, dauerhaft. Grundlage C07-Discover, R05/R06 und freigegebenes
Gesamtprogramm. Keine Gruppenräume, Anhänge, externen Zustelldienste oder
Umdeutung des Sessionchats.

## Teilnahme und Bestandsgrenze

Ein Gespräch gehört genau einer Kampagne und genau zwei verschiedenen Nutzern.
Beide müssen bei Erstellung Owner oder aktive Mitglieder dieser Kampagne sein.
Paar bleibt unveränderlich; Rollenwechsel macht keinen Dritten zum Teilnehmer.
Auch Kampagnenowner, DM, Co-DM und Plattformadmin erhalten über diese neue VTT-
API keinen Zugriff, wenn sie nicht Teilnehmer sind. Existierende rechtmäßige
DB-/Backupadministration wird dadurch nicht zu einer Ende-zu-Ende-Verschlüsselung.

Jeder List-/Read-/Write-Request prüft aktuelle Nutzbarkeit, authentifizierte
Teilnahme und eigenen aktuellen Kampagnenzugriff. Nach eigenem Leave/Kick sind
Liste und Verlauf nicht erreichbar. Ein weiterhin berechtigter Teilnehmer kann
seinen bisherigen Verlauf lesen, wenn der andere die Kampagne verlassen hat;
die Unterhaltung wird dann sichtbar schreibgeschützt. Senden verlangt beide
aktuell berechtigt. Kein neuer Zugriff aus einem mitgeführten Player-Kontext,
kein Owner-Fallback auf fremde Gespräche und keine veränderbaren Teilnehmer-IDs.

## Daten und API

Zwei additive Tabellen in einem eigenen Modellmodul: PrivateConversation mit
campaign_id, participant_low_id, participant_high_id, created_at/updated_at;
unique(campaign_id,low,high), Check low<high. PrivateMessage mit conversation_id,
author_user_id, client_event_id (UUID), content (1–2000 Zeichen), created_at;
unique(conversation_id,author_user_id,client_event_id). Normalisierte Paarbildung
und Constraint behandeln gleichzeitiges Öffnen aus beiden Richtungen. Keine
Teilnehmeränderung/Hard-Delete/automatische Retentionmigration im ersten Umfang.

JWT/CSRF-geschützte Routen in einem eigenen Blueprint: POST einer Conversation
mit campaign_id/recipient_user_id öffnet oder findet das eigene berechtigte Paar;
GET eigene Conversationliste (24 pro Seite, stabile updated_at/ID-Reihenfolge);
GET Conversation/Messageverlauf (50 pro Seite über monotone ID-Cursor);
POST Nachricht mit ausschließlich Text und client_event_id. Eingabe- und
Paginationgrenzen vor DB-Arbeit prüfen. Fremde Gesprächs-/Nachrichten-IDs liefern
ein einheitliches Not-found ohne Inhalt/Metadaten. Keine globale Nutzersuche.

Identischer Message-Retry liefert dieselbe Message-ID, abweichender Text unter
gleicher Event-ID 409. Aktuelle Teilnahme/Schreibberechtigung wird vor einem
Replay geprüft. Fremde author_user_id und HTML/Attachmentfelder werden nicht
übernommen. Gespeicherter Text wird ausschließlich als Text ausgegeben und mit
textContent gerendert. Antworten private/no-store; Rate-Limit für Erstellen und
Senden. Audit/Fehlerlogs enthalten keinen Inhalt, keine Tokens oder versteckte
Verlaufsausschnitte. Vorhandene Session-Chatmodelle/-Events bleiben unverändert.

## UI und Aktualisierung

Hub-Mitgliederzeile hat kompakte Charakter/Chat/Entfernen-Aktionen passend zur
jeweiligen bestehenden Berechtigung. Charakter öffnet nur bereits berechtigte
Kampagnenfiguren dieses Mitglieds; kein Name→private-Archiv-Suchweg. Chat öffnet
das Paar. Entfernen behält bestehende Zielrollen, Selbst-/Owner-Schutz und
Bestätigung. Eingeladene/Pending-Nutzer sind kein Chatempfänger.

Ein normaler Navigationseintrag „Gespräche“ zeigt eigene Unterhaltungen mit
Kampagne/Partner und öffnet denselben Dialog/Controller. Dieser unprivilegierte
persönliche Controller ist keine DM-Komposition. Hauptnavigation einmal, lokale
DE/EN-/Papier-/Nacht-Tokens und Mobilbreite verwenden. Verläufe sind mit Namen,
Zeit und Sendestatus erkennbar; Enter/Sendebutton, sichtbarer Fehler und Retry
mit derselben Event-ID. Keine Erfolgsmeldung ohne bestätigte Message-ID.

Erste Fassung aktualisiert nur das offene sichtbare Gespräch per begrenztem
HTTP-Polling, nicht über neue Socketräume. Pro Antwort aktuelle Serverprüfung;
Polling stoppt bei verborgenem Tab/Schließen. Abbruch-/Sequenzprüfung verwirft
alte Antworten nach Gesprächswechsel. 401/403/404 leert die betroffene offene
Ansicht und zeigt einen neutralen Zugriffsstatus. Eine weggefallene Schreib-
berechtigung sperrt auch einen noch nicht abgesendeten Text. Bereits gelesene
Informationen können technisch nicht nachträglich ungelesen gemacht werden.

## Abnahme und Deploy-Handoff

API-Matrix: DM↔Player und Player↔Player, unbeteiligter Owner/DM/Admin, anderer
Campaign-Member, fremde Kampagne, Invite/Pending/Leave/Kick, Rollenwechsel,
Kontosperre, unbekannte IDs, Retry/Texttausch und Parallelöffnung. Nachweisen,
dass kein Inhalt in Bootstrap, Tischchat, Sessionhistorie, öffentlichen Listen
oder fremden Pollantworten landet. PostgreSQL-Concurrency im isolierten
disposable Testschema; keine Produktionsschreibtests mit fremden Nutzerdaten.

Browser: Hub→Chat, zwei echte Browserkonten, Senden→Antwort→Reload, Gesprächs-
wechsel während verzögerter Antwort, Widerruf während offener Ansicht und
stabiler Sessionchat. 390/1440 px, Tastatur, DE/EN und beide Darstellungen.
Neue Tabellen nach Backup additiv anlegen; vorheriges Image ignoriert sie.
Schema, source/push/image, normaler UI-Einstieg und Rollbackreferenz dokumentieren.
Medium-Privacy-/Retry-Risiken werden durch die obigen Teilnehmer-, Transport-
und Persistenzverträge behandelt; separate Claude-Prüfung vor Integration.

Primärquelle am 2026-11-12 geprüft: [OWASP Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
für objektbezogene Rechteprüfung bei jedem Request und verweigerte fremde IDs.
Teilnahme, Verlaufserhalt und HTTP-Polling sind die hier festgelegten Produkt-
und Repo-Verträge; OWASP schreibt diese konkrete Umsetzung nicht vor.
