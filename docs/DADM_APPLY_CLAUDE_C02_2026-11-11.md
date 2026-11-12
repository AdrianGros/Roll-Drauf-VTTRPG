# Apply C02 – erlaubte Bearbeitung, Bilder und Korrekturweg

Status: Design abgeschlossen; Deploy erst auf integriertem C01 mit aktuellem
Dateibesitz. Profil standard; dauerhaft. Input: C02-Discover und R09–R13.

## Begrenzte Lösung

Bestehende Upload-, Kopier- und Regelmechanik weiterverwenden. Additive
`character.permissions`-Projektion nur in GET `/api/characters/:id/sheet`:
`editCore`, `editIdentity`, `copy`, jeweils aus bereits geprüfter Eigentümerschaft.
Kein gespeichertes Feld und kein neues Recht: PUT/POST/DELETE prüfen unverändert
unabhängig. Shared Reader und fremde Figuren erhalten false. Kein globaler DM-
oder Kampagnenowner-Fallback für Eigentümeraktionen, auch nicht als Player.

Ohne explizites mode=view sind erlaubte Eigentümerfelder nach erfolgreichem Laden
bearbeitbar. Reader bleiben schreibgeschützt; berechnete SRD-Felder bleiben trotz
Editmodus gesperrt. Ein klar beschrifteter lokaler Lock kann den Bogen sperren.
Explizites mode=view bleibt ein schreibgeschützter Einstieg. Umschalten erhält
Tischkontext und alle Kampagnen-/Sessionparameter; keine stillen DM-Rechte.

Avatar-/Token-Upload vom eigenen Bogen über sichtbare beschriftete Bildaktion
oder direkten Einstieg zum Verwaltungsbereich. Aktuelle Picker-/Multipart- und
Storagefunktionen nutzen, Ersetzen/Entfernen beibehalten. Shared Reader erhalten
keine mutierenden Bildaktionen. Nach Erfolg Bild und Status sichtbar aktualisieren.

Unabhängige Kopie über vorhandenes Manage-/Archiv-UI: neue ID, eigenes tief
kopiertes Dokument und Beziehungen, Original unverändert. Bisheriger Vertrag
ohne Kampagne/Avatarübernahme bleibt; keine neue Slotzahl, kein zweites Backend.

Findings-Liste erhält pro korrigierbarer Meldung eine Aktion, die den bereits
bekannten Pfad über `stepOf`/`SC.goStep` zum richtigen Schritt führt. Bekannte
Felder danach fokussieren/anscrollen; unbekanntes Feld führt zum Schrittinhalt.
Kein eval und keine ungeprüften Selektoren aus Meldungstext. Fehlertext und
Quellenzitat bleiben sichtbar. Ungültige Talentwiederholung bleibt serverseitig
blockiert; Auswahl bietet bereits an anderen Verbesserungsslots verbrauchte,
nicht wiederholbare Talente nicht erneut als gültige Wahl an. Aktuell gespeicherte
Fehlwahl bleibt erklärbar, statt andere Entscheidungen still zu löschen.

## Abnahme und Rückweg

Echte UI-Uploads/Ersetzen/Entfernen in DE/EN und schmalem Bogen; Eigentümer/Reader
und mutierende Fremdanfrage prüfen. Erlaubte Kernwerte speichern, SRD-Rechenwerte
weiter gesperrt, Lock und explizite Ansicht erhalten. Kopie ändern und Original
unverändert lesen. Creator-Multiclass-/Weapon-Mastery-/Talentfehlwahl führt zur
Korrektur; doppelter Ringer wird erklärt und bleibt serverseitig ungültig.

Gezielt vorhandene Identitäts-, Creator- und Manage-API-/Browserfälle ergänzen;
keine Tests bloßer CSS-Implementierungsdetails. Kein neues Schema/Dependency,
keine Änderung von P1/P2/P3. Alter Präsentationsstand liest die additive Projektion
nicht. Getesteten C01 als Rückweg behalten. Vor Deploy Quell-/Live-Abgleich, separater
Claude-Review und normale Live-Reise mit eigenen Testfiguren; danach Monitor.

## Fester Abschnittslink für C08

Zusätzlich zum sichtbaren Identitätsweg versteht der Bogen den begrenzten
Parameter `section=identity|progression`. Die feste Map verweist auf die
vorhandenen Identitäts-/Fortschrittswurzeln; nach asynchroner Komposition wird
der richtige Tab geöffnet und der Bereich fokussiert. Unbekannte Werte werden
ignoriert, nicht als Selector/Code interpretiert. Vorhandene Kampagnen-/Session-
und Kontextparameter bleiben beim Moduswechsel erhalten. Der Link gewährt
keine Schreibrechte und löst keine automatische Charakteränderung aus.

## Konkretisierung nach erstem C02-Check am 12.11.

42 Prüfungen bestehen, acht Browserfälle zeigen echte Integrationslücken:
SheetFeedback überschreibt den Modusbutton noch mit einer URL ohne campaign_id
und unbekannte Parameter; das CSS macht den hidden-Readerbutton sichtbar; der
neue Bilder-einstieg wird nicht tatsächlich in die fertige Komposition eingesetzt.
Diese vorhandenen Seams werden innerhalb C02 korrigiert.

Außerdem muss die Rechteprojektion bei fehlenden/ungültigen permissions geschlossen
bleiben. Kein Rückfall auf mode=edit als Eigentümernachweis. Der lokale Bogenlock
und explizites mode=view müssen auch bereits komponierte Inventar-/Fortschritts-/
Verwaltungsaktionen sperren, ohne serverseitige Fähigkeiten zu erfinden oder
bestehende zulässige DM-XP-Aktionen im normalen Einstieg pauschal zu entfernen.
Dazu wird der C02-Besitz um srd-inventory-ui.js, srd-progression-ui.js und
srd-manage-ui.js erweitert. Vorhandene Komponenten neu zeichnen/ihre bestehenden
Capabilities mit dem lokalen Ansichtszustand verknüpfen; kein neuer Controller.
Unbekannte Rechte liefern false; lokale Sperre ist nur UI, jede Mutation bleibt
serverseitig unabhängig geprüft. Lock-/View-Test muss auch SRD-Panels abdecken.
