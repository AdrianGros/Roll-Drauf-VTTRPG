# Apply C08 – Kataloggegenstände und geprüfter Fortschrittsweg

Status: Design abgeschlossen, Deploy nach C02 und C01-Compendiumintegration.
Profil standard, dauerhaft. Grundlage C08-Discover/R22–R24; Gesamtfreigabe gilt.

## Verhalten und Berechtigung

Compendiumdetails erhalten „Zum Charakter“ mit Such-/Kampagnenfilter über eigene
berechtigte SRD-Figuren. Serverentscheidungen bestimmen verfügbare Aktionen.
Unterstützte Gegenstände sind ausschließlich Einträge, deren stabile ID im
vorhandenen typisierten srd_inventory.catalog vorhanden ist. Übernahme verwendet
add_catalog_item, bekannte Mengen-/Pack-/Inventargrenzen und keine Clientwerte
für Gewicht, Kosten oder Effekte. Keine automatische Ausstattung, Kaufabbuchung
oder automatische Aktivierung magischer Eigenschaften. Nicht unterstützte Typen
werden erklärt statt als erfolgreich hinzugefügt gemeldet.

Inventarschreiben bleibt Ownerrecht. Eine DM-Auswahl kann lesbare Kampagnenfiguren
und bestehende XP-/Meilensteinwege zeigen, verleiht aber keine neue Erlaubnis für
deren Gegenstände oder Stufenchoices. Alle IDs und aktuellen Leserechte/Ownerrechte
werden am Server neu geprüft; carried Player-Kontext erhöht keine DM-Rechte.
Archivierte/gelöschte Figuren und falsches System sind keine Übernahmeziele.

Für Zauber/Talente/Klassenentscheidungen führt die Aktion zur vorhandenen
servergeprüften Fortschrittsfläche der gewählten eigenen Figur. Ein offenes
Stufenangebot wird aus dem echten progression.status abgeleitet, keine erfundene
Zahl fehlender Zauber. Es wird kein Zauber direkt in generische Spell-Zeilen
geschrieben und kein Talent unabhängig von einem gültigen Choice-Slot angehängt.
Der Link `/character-sheet?id=<id>&section=progression` öffnet den festen
Verwalten-/Fortschrittsbereich nach dessen asynchronem Laden. Abschnittsparameter
werden gegen eine feste ID-Map geprüft, nicht als beliebiger Selector oder Code
ausgewertet. Offene XP-/Zauber-/Talentwahl benutzt die bestehenden Vorschau-
und Abschlussendpunkte unverändert mit deren Regelvalidierung.

## Dauerhafte Aktion und Parallelität

Neue additive Tabelle CharacterCatalogReceipt: character_id, actor_user_id,
request_id(UUID), request_digest, response(JSON), created_at/expires_at;
unique(character_id,actor_user_id,request_id). Laufzeit 24h, keine unbegrenzte
Retryzusage. Keine Geheimnisse im Receipt. Neuer begrenzter POST unter dem
bestehenden SRD-Creator-Charakterpfad für catalog-add mit entity_id, quantity und
request_id; unbekannte Felder verleihen keine Effekte/Rechte. Dieselben
normalisierten Felder bestimmen den Digest. Gleicher Retry liefert dieselbe
Bestätigung, neue Nutzlast unter gleichem Schlüssel 409. Autorisierung vor Replay.

Vorhandene Inventarschreiber und die neue Aktion nehmen denselben Character-
Writer-Lock und laden danach den aktuellen Zustand, damit gleichzeitige Mengen-
änderungen nicht aneinander vorbeischreiben. Receipt, Mengen-/Itemänderung und
Antwort werden gemeinsam committet; Fehler rollen alle Teile zurück. Abgelaufene
Receipts nur im gesperrten eigenen Charakterbereich bereinigen. PostgreSQL-
Contention separat im disposable Testschema nachweisen; SQLite allein beweist
keinen Zeilenlock. Nach Commit denselben vorhandenen berechtigten Token-Push
verwenden. Ein Pushfehler macht die bereits gespeicherte Aktion nicht erneut
ausführbar und wird entsprechend berichtet.

UI hält pro tatsächlichem Klick dieselbe Request-ID für Netzwerk-Retry. Ein neuer
bewusster Hinzufügen-Klick erhält eine neue ID und darf die Menge erneut erhöhen.
Keine stille Doppelübernahme bei Reload/Zurück. Erfolgszustand zeigt bestätigte
Figur/Gegenstand/Menge und normalen Bogenlink; Dialogwechsel verwirft alte
Antworten. DE/EN, Papier/Nacht, 390 px und Tastatur bleiben aus C01 erhalten.

## Abnahme und Handoff

API: Owner/fremder Owner/DM-lesbar/Player-Kontext, falsche Kampagne/Figur/System,
archiviert, unbekannte ID, unzulässige Menge, Packauflösung, Retry/Digesttausch
und echte konkurrierende Inventarschreiber. Unterbrechung vor Commit hinterlässt
keine Menge/Receipt, Antwortverlust führt beim Retry zu genau einer Übernahme.
Pins/Creatorstate/Level bleiben beim Gegenstand unverändert. Zauber/Talent-
Direktaufnahme wird nicht erlaubt; reguläre ungültige Stufenwahl bleibt ungültig.

Browser: Compendium→bekannte Waffe→eigene Figur→Bogeninventar, gleiche Aktion nach
Reload nicht erneut; fremde Figur kein Schreibziel. Stufenangebot→richtiger
Bogenbereich→bestehende Preview→vollständige Stufenwahl, Zauber/Talentlimit am
Server. Filter/Zurück bedienbar und deutsche Regeltexte unter EN-UI unverändert.
Neue reine Receipt-Modelltabelle nach Backup additiv anlegen, vorheriges Image
ignoriert sie. Quellcommit/Push/Image/Normalnavigation/Prüfungen/Rollback dokumentieren.
Medium-Risiken sind über Ownergrenze, gemeinsamen Writer-Lock, transaktionales
Receipt und vorhandene Regelcontroller behandelt. Unabhängiger Claude-Review
vor Integration; keine globale neue DM-/Regelberechtigung.
