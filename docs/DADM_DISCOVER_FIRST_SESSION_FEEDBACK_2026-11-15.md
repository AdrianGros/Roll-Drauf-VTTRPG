# Erste Spielsession: Befunde und Research-Plan

**Datum:** 15.11.2026. **Phase:** Discover. **Profil:** standard.
**Status:** Bestandsaufnahme abgeschlossen; sechs begrenzte Recherche-/Apply-Kandidaten,
keine neue Funktionsimplementierung und kein Deployment aus diesem Auftrag.
**Aufbewahrung:** dauerhaft für diesen Bericht und den
[Laufzeit-/Quellenbeleg](proofs/first-session-feedback-2026-11-15/discovery-evidence.json).

## Eingabe und fachlicher Umfang

Die erste gespielte Session hat grundsätzlich funktioniert. Das heutige Owner-Feedback
nennt folgende Verbesserungen:

- Beyond20-Einrichtung leichter finden; das Einfügen der Adresse einfacher erklären.
- Tokenbilder direkt im Token-Menü hochladen; die zwei wahrgenommenen Token-Menüs auflösen.
- Spieler und DM können Tokens speichern, verwalten und auf anderen Karten wiederverwenden.
- Spieler würfeln ihre Initiative selbst; der Wurf des gewählten Tokens gelangt in die
  Kampfreihenfolge. Beyond20 bleibt vorerst im Einsatz. Weitere Würfelwege sollen dieselbe
  nachvollziehbare Zuordnung erhalten.
- Durch Buttons geöffnete Menüs/Fenster frei verschieben und an der letzten Position
  wieder öffnen. Die Hotbar selbst bleibt fest.
- Für jede Kampagne, an der jemand teilnimmt, einen Chatraum anbieten; die Unterhaltung
  der laufenden Session im Konversationsbereich erreichbar machen.
- Steuerung insgesamt verständlicher machen, zunächst an diesen konkreten Reisen.

Das ist eine Research-/Planungsaufnahme. Datenmodell, API-Verträge und Fensterarchitektur
werden hier nicht festgelegt. Keine Ablösung von Beyond20, kein neuer Makroeditor,
kein allgemeiner Messenger-Umbau und keine neue Staging-Pflicht gehören zum Umfang.

## Tatsächlicher Untersuchungsstand

Der ursprüngliche Checkout `/home/admin/projects/roll-drauf-vtt` steht auf
`66edde994cd72479df62fd2a1593c4fda382ba1e` und enthält umfangreiche bestehende Änderungen.
Er ist für diese Themen keine verlässliche alleinige Beschreibung der Produktion.
Diese Änderungen wurden weder übernommen noch verworfen oder committed.

Live läuft `roll-drauf-vtt-app-1`, Tag
`roll-drauf-vtt-app:feedback-seat-memory-20261111-78133813e`, Image-ID
`sha256:1e8614e7855b0f203ef4c3976e2d41ec2bf34c9af7d70c6209bd01d340559aac`.
Der neuere Quellstand liegt im Arbeitsbaum
`/home/admin/projects/roll-drauf-vtt-consolidation-20261115`, Commit
`78133813e7f8ee2ed77db0d1fa15ab972447d2bc`. Dessen tracked Status war bei Erhebung sauber.
**23 ausgewählte betroffene Dateien stimmen per SHA-256 mit dem laufenden Container
überein.** Das ist kein vollständiger Image-Audit.

Die Containerlabels nennen Compose-Projekt `migration-production`, Arbeitsverzeichnis
`/srv/migration/2026-10-07/setup` und die Dateien `production.compose.json` sowie
`production.duck-species.override.yml`. Es gibt keinen Source-Bindmount. Die Labels sind
ein Betriebsbefund, kein Ersatz für den erneuten Abgleich der effektiven Konfiguration
vor einer späteren Auslieferung. Der ausgewählte Source-/Image-Abgleich ist im Beleg
einzeln nachvollziehbar.

Alle folgenden **Codeverweise beziehen sich auf diesen neueren Quellstand**, nicht
auf gleichnamige ältere Dateien im ursprünglichen Checkout. Ältere Audits vom 01.11.
dürfen insbesondere nicht als Beweis weiterhin fehlender Rollen-/Kontexttrennung dienen:
der aktuelle Stand hat getrennte Player-/DM-Komposition und serverseitige Tischkontexte.
Die Owner-Anforderung in `docs/decisions/PLAYTABLE_ROLE_SEPARATION_2026-11-01.md`
bleibt für alle sechs Pakete verbindlich.

## Befunde mit relevanter Inventur

| Thema | Beleg im aktuellen Quellstand | Bedeutung |
| --- | --- | --- |
| Beyond20-Anleitung | `vtt/templates/beyond20.html:52` enthält vier Hauptschritte mit mehreren Browseraktionen und weitere Fehlerhilfe. Der normale Tisch-Link liegt bei `vtt/templates/play.html:2940` unter den Werkzeugen. | Eine Anleitung und Kopierfunktion existieren bereits. Auffindbarkeit, Verständlichkeit und tatsächliche Browseraktionen müssen untersucht werden; bloß weniger nummerierte Absätze belegen keine Vereinfachung. |
| Zwei Token-Einstiege | Werkzeugbutton bei `play.html:2753`; Handler bei `play-ui.js:1019`; `_openTokenMenu()` bei `:1199` öffnet dasselbe `tokenWidget`, das auch der Dock-Reiter bei `:2870` verwendet. | Im untersuchten Code sind es zwei Einstiege mit unterschiedlichem Bedienkontext, keine nachgewiesenen zwei getrennten Token-Datenverwaltungen. Der vom Owner beschriebene doppelte Menüeindruck bleibt ein UX-Befund. |
| Token-Upload | `play.html:2581` hat den Upload im Platzierungsdialog; `:2657` bietet Bildwechsel für ausgewählte Tokens. `vtt/play/surfaces/dm.json`, Schlüssel `token-upload`, enthält zusätzlich „Token-Datei hinzufügen“. `play-ui.js:3017` bindet diesen Shortcut. | Der direkte Upload im Token-Bereich ist im Code bereits als DM-Fragment vorhanden, für Player dort nicht montiert. Warum er in der gespielten DM-Reise nicht auffiel/erreichbar war, ist ohne Rollen-/Klickreproduktion offen. Nicht pauschal als fehlendes Upload-Backend verbuchen. |
| Wiederverwendung | `vtt/models/token_state.py:9` bindet Tokeninstanzen an Session und Karte. `vtt/static/js/play-journal.js:25` listet unter anderem Token-Assets; `vtt/endpoints/assets.py:99` stellt die Kampagnen-Assetbibliothek bereit. | Bilddateien sind bereits wiederverwendbar. In den untersuchten Modellen und Token-Pfaden wurde keine vollständige speicherbare Tokenvorlage mit Verwaltung und erneutem Platzieren gefunden. DM-Clipboard ist ebenfalls vorhanden, aber keine dauerhafte Player-/DM-Bibliothek. |
| Initiative | `play-ui.js:453` startet Combat ausdrücklich mit `"auto"`. `vtt/combat/service.py:117` kennt `auto` und `manual`; `auto` würfelt für alle Teilnehmer neu. `vtt/campaigns/routes.py:1874` setzt Initiative und sortiert neu, derzeit nur für DM. | Ein vorheriger Tokenwert kann beim automatischen Start überschrieben werden. Ein bloßes Umschalten des Startmodus reicht für selbst gewürfelte Player-Initiative einschließlich Autorisierung und Neusortierung nicht aus. |
| Eingehende Würfe | `vtt/static/js/beyond20-bridge.js:113` normalisiert RenderedRoll; `vtt/socket_handlers.py:1598` speichert das Ergebnis als Chatnachricht und sendet es weiter. `play-ui.js:3419` zeigt es an. | Dieser Pfad aktualisiert derzeit keine Encounter-Initiative und führt keine belastbare Token-ID-Zuordnung mit. `UpdateCombat` ist ein anderer Pfad: er ordnet per Namen Tokenwerte zu, ersetzt aber nicht die Integration eines einzelnen Initiativewurfs. Die Bridge leitet den Wurftyp aus Teilwürfen ab; die ursprüngliche Initiative-Semantik ist gesondert zu prüfen. |
| Fensterbewegung | `play-ui.js:14` nennt nur `tokenCreatePanel` als Drag-Ziel. `_setupTableSheet()` bei `:2862` verschiebt Seiten/Initiative/Tokens in ein festes Dock. `vtt/static/css/play-workspace.css:31` erzwingt dort `position: static`. | Es gibt eine konkrete Ursache für die fehlende freie Bewegung. Eine Erweiterung der Drag-ID-Liste allein löst das nicht. Der Platzierungsdialog setzt seine Position beim Öffnen außerdem erneut am Kartenklick (`play-ui.js:1578`). |
| Chat/Konversationen | `vtt/models/chat_message.py:14` verlangt eine Session-ID. `vtt/community/routes.py:73` und der Tisch-Bootstrap liefern sessionbezogenen Verlauf. `/conversations` nutzt `vtt/static/js/private-conversations.js:11` und feste private Paare aus `vtt/models/private_conversation.py:5`. | Sitzungschat und private Zweiergespräche existieren. Ein automatisch angebotener Gruppenraum je Kampagne ist in diesen Pfaden nicht vorhanden. Ein zusätzlicher Menülink allein erzeugt weder dessen Lebensdauer noch Verlauf oder Mitgliedschaftsregeln. |

### Abgleich mit jüngeren Produktentscheidungen

Der ältere Apply-Vertrag `docs/plans/FEEDBACK_B02_APPLY_2026-11-13.md` hat die drei
früher freien Widgets bewusst durch das feste Dock ersetzt. Die heutige Owner-Anforderung
ändert diese Präsentationsvorgabe. Sie rechtfertigt nicht das Zurückkopieren einer alten
Gesamtdatei: Rollenkomposition, Layerauswahl, Touch-Bedienung, Tischkontext und neuere
Würfel-/Bogenwege müssen erhalten bleiben.

Chat links, Journal rechts und die vorhandene DM-Sessionverwaltung sind weitere geltende
Funktionen. Ob deren Buttons künftig verschiebbare Fenster öffnen, wird im Fensterpaket
entworfen; aus diesem Bericht folgt keine ungeprüfte Rücknahme dieser Funktionen.

## Research-Plan und vorgeschlagene Reihenfolge

Die Reihenfolge ist eine Empfehlung für begrenzte Folgeschritte, keine technische
Freigabe aller Pakete. Abnahmekriterien beschreiben gewünschte Nutzerergebnisse;
ihre Umsetzung und Schnittstellen gehören in den jeweiligen Apply-Vertrag.

### R01 – Beyond20 schnell einrichten und Verbindung erkennen

**Priorität:** zuerst. **Umfang:** klein bis mittel, browserabhängig.

Untersuchen: Einstieg vom laufenden Tisch, frische und bereits eingerichtete Erweiterung,
Chromium/Firefox, tatsächliche Klickzahl und verständliche Statusmeldungen. Browser- und
Erweiterungsschritte getrennt von Roll-Drauf-Schritten zählen. Die aktuelle Anleitung
gegen die installierte Beyond20-Version prüfen, technische Integrationsdetails als
Hauptinhalt hinterfragen. Einen möglichen direkteren Optionsaufruf erst verifizieren.

Abnahme: Beide Rollen finden die Hilfe unmittelbar am Tisch; Adresse lässt sich direkt
kopieren; eine kurze verständliche Hauptanleitung deckt Speichern/Berechtigung und nötigen
Reload ab. Ein echter Testwurf macht sichtbar, dass er **an dieser Session** angekommen
ist. „Erweiterung geladen“ und „Wurf erfolgreich zugestellt“ nicht gleichsetzen.

Abhängigkeit: Die [offizielle Beyond20-API](https://beyond20.here-for-more.info/api)
dokumentiert Custom-Domains, DOM-Ereignisse und Initiative als Wurftyp. Eine Aufnahme
als bekannte Domain ist eine mögliche spätere externe Abstimmung, kein gesicherter
kurzfristiger Weg. Keine Kontaktaufnahme oder Erweiterungsänderung aus diesem Auftrag.
Eine browserübergreifende automatische Ersteinrichtung ist hier nicht nachgewiesen.

### R02 – Eindeutiges Token-Menü mit direktem Bildupload

**Priorität:** zuerst, mit R01. **Umfang:** mittel.

Untersuchen: Player-, DM- und Owner-als-Player-Reise über Werkzeug, Dock, Journal und
Kartenklick. Ermitteln, welcher Einstieg in der gespielten Session benutzt wurde und
ob der vorhandene DM-Upload verborgen, übersehen oder fehlerhaft war. „Token platzieren“,
„Token bearbeiten“ und Bildauswahl anhand derselben konkreten Aufgabe vergleichen.

Abnahme: Ein verständlicher Token-Arbeitsbereich ist über die normale Oberfläche
erreichbar. Der direkte Bildupload funktioniert dort auch für erlaubte eigene
Player-Tokens; erneutes Hochladen beim Kartenwechsel ist nicht nötig. Erstellen,
Bildwechsel und Abbrechen bleiben nachvollziehbar. Player erhält dafür keine
DM-Fragmente oder DM-Befugnisse. R02 liefert noch keine vollständige Vorlagenbibliothek.

### R03 – Verschiebbare Fenster und verlässliche Wiederöffnung

**Priorität:** erste Bedienungsrunde nach der Inventur. **Umfang:** mittel bis größer.

Untersuchen: Alle durch Buttons geöffneten Tischbereiche einzeln inventarisieren:
Tokens, Initiative, Seiten/Layer, Chat, Journal, Würfelwerkzeuge, Charakterbogen,
Einstellungen sowie bestehende Untermenüs. Aktuelle Dock-/Drawer-, Fokus-, Escape-,
Scroll- und Touch-Wege dokumentieren. Nicht jedes kleine Auswahl-Popover stillschweigend
zu einem eigenen dauerhaften Fenster erklären; Fenster und Untermenüs im Apply auflisten.

Abnahme: Die vorgesehenen Funktionsfenster lassen sich frei verschieben und öffnen
beim nächsten Klick an ihrer zuletzt gesetzten Position. Mehrere offene Fenster bleiben
bedienbar; Inhalte, Fokus und Schließen funktionieren. Die Hotbar bleibt fest, ihre
gegebenenfalls geöffneten Fenster folgen derselben Wiederöffnungsregel. Positionsrücksetzung
ist erreichbar; nach Resize, Vollbildwechsel und auf kleinen Displays bleibt der
Fensterkopf erreichbar. Speicherdauer und Geltungsbereich ausdrücklich in Apply festlegen.

### R04 – Eigene Initiative und zugeordnete Würfe

**Priorität:** nach der ersten Bedienungsrunde; höchste funktionale Session-Priorität.
**Umfang:** mittel bis größer.

Untersuchen: Einzelner Initiativewurf aus Beyond20, interner Würfler und Charakterbogen;
vor/nach Combatstart, gleiche Tokennamen, mehrere eigene Tokens, zwei Player gleichzeitig,
Reroll und Reconnect. Originale Beyond20-Nachricht und normalisierten Wurf vergleichen.
Player darf über den vorhandenen DM-Initiativendpunkt nicht einfach freigeschaltet werden.
Encounter-Reihenfolge, Tokenwert und angezeigter aktueller Zug müssen gemeinsam betrachtet
werden. Regeln für wartende Teilnehmer und NPC-Initiative im Apply festhalten.

Abnahme: Player wählt einen berechtigten eigenen Token, würfelt Initiative und sieht
genau dieses Ergebnis für diesen Teilnehmer in der Turn Order. Andere Clients sehen
denselben Stand; Combatstart überschreibt den angenommenen Player-Wurf nicht ungefragt.
Fehlende, mehrdeutige oder unberechtigte Zuordnungen verursachen keine fremde Änderung.
Gleichzeitige Würfe, doppelte Zustellung und erneute Verbindung erzeugen keine doppelte
Übernahme. Die Spielleitung behält die erlaubte Kampf- und Zugverwaltung.

Weitere Würfel als begrenzte Folgematrix erfassen: Attribut, Fertigkeit, Rettungswurf,
Angriff und Schaden. Jeweils Akteur, optionales Ziel, Ergebnisdarstellung und zulässige
Zustandsänderung benennen. Ein allgemeiner W20 ist ohne fachliche Kennzeichnung keine
Initiative. Aus „gleiche Mechanik“ folgt keine Freigabe automatischer HP-Abzüge.
Beyond20 bleibt eine Quelle neben den internen Würfelwegen.

### R05 – Wiederverwendbare Token-Bibliotheken für Player und DM

**Priorität:** nach R02; unabhängig von R04 untersuchbar. **Umfang:** größer.

Untersuchen: Vorhandene Bild-Assets, Journal, Charakterverknüpfung und DM-Clipboard;
welche Tokenattribute tatsächlich wiederverwendet werden sollen. Vorlage, Bilddatei
und platzierte Spielinstanz fachlich unterscheiden, ohne hier ein Schema festzulegen.
Persönlicher Besitz, Kampagnenfreigabe und DM-Geheimnisse sind getrennte Berechtigungsfragen.

Abnahme: Beide Rollen können berechtigte Tokens mit Bild und vereinbarten Eigenschaften
speichern, benennen, wiederfinden, ändern, entfernen und auf einer anderen Karte neu
platzieren. Andere Nutzer können fremde persönliche Vorlagen nicht verändern.
Bestehende Platzierungen werden durch eine Vorlagenänderung/-löschung nur nach einer
ausdrücklich festgelegten Regel beeinflusst. Keine versehentliche Übernahme alter
Initiative, Kartenposition, Kampfzustände oder geheimer DM-Einstellungen.

Vor Apply zu klären: zunächst kampagnenintern oder auch kampagnenübergreifend;
welche Eigenschaften gespeichert werden; welche Player-Freigaben gelten; wie dauerhafte
Charakterwerte gegenüber momentanen Spielzuständen behandelt werden. Die bestehende
Kampagnen-Assetliste ist kein nachgewiesener privater persönlicher Vorlagenspeicher.

### R06 – Kampagnenräume im Konversationsbereich

**Priorität:** eigenes zusammenhängendes Paket nach Klärung der Raumsemantik.
**Umfang:** größer, mit Daten-/Verlaufsfragen.

Untersuchen: normale Kampagnenliste, Sitzungschat, globale Gespräche, Kampagnen-Hub,
Mitgliedschaft und Entzug sowie Verlauf nach Sitzungswechsel. Vorhandene private
Zweiergespräche als weiterhin private Funktion berücksichtigen. Übernahme bisheriger
Sessionnachrichten, Pagination, Echtzeit, ungelesener Status und Offline-Senden abgrenzen.

Abnahme: Jede eigene Kampagne hat einen eindeutig benannten erreichbaren Gruppenraum.
Die gerade gespielte Session landet über ihren Konversationseinstieg zuverlässig in der
zugehörigen Unterhaltung. Unbeteiligte oder ausgeschiedene Mitglieder können keine
Nachrichten lesen, nachladen oder per Socket weiterempfangen. Private Zweiergespräche
werden nicht in den Gruppenraum übernommen; verdeckte Würfel-/DM-Inhalte bleiben geschützt.

**Arbeitsannahme, noch kein Datenvertrag:** Ein Kampagnenraum behält seinen Verlauf
zwischen Sessions, und der aktive Tisch öffnet den zugehörigen Raum. Offen bleibt, ob
„Chatroom aus der Session“ stattdessen einen eigenen Sessionraum innerhalb der Kampagne
meint. Diese Unterscheidung vor Datenmodell/Migration festhalten; nicht durch eine
beliebige neueste Session-ID ersetzen. Frühere Nachrichten weder löschen noch ungeprüft
zu einem gemeinsamen Verlauf vereinigen.

## Risiken, Annahmen und offene Entscheidungen

| Schwere | Befund / Risiko | Behandlung für Apply |
| --- | --- | --- |
| Mittel | Ursprünglicher Checkout und aktuelle Live-Quelle unterscheiden sich deutlich. | Am verifizierten neueren Quellstand ansetzen; vor Auslieferung erneut abgleichen. Keine alten Playtable-Gesamtdateien übernehmen. |
| Mittel | Neues Fensterverhalten ändert das bewusst ausgelieferte Dock und kann Touch, Layerauswahl oder Fokus regressieren. | R03 mit vollständiger Fensterliste, Desktop-/Mobilvertrag und vorhandenen Bedienungsnachweisen entwerfen. Die heutige Owner-Anforderung ist die neue Zielvorgabe. |
| Mittel | Würfe zeigen bislang Namen und Werte, aber keine belastbare Autorisierung für eine neue automatische Token-/Encounter-Mutation. | Zuordnungs-, Besitz-, Kontext-, Konkurrenz- und Wiederholungsvertrag in R04 vor Implementierung lösen. Kein neu nachgewiesener bestehender Rechtebypass wird behauptet. |
| Mittel | Persönliche Vorlagen und DM-Geheimnisse passen nicht automatisch in die bestehende gemeinsame Assetliste. | Eigentum/Freigabe, gespeicherte Werte und Lebenszyklus in R05 festlegen. |
| Mittel | Kampagnenraum, Sitzungschat und private Gespräche haben verschiedene Teilnehmer-/Verlaufsgrenzen. | Raumsemantik und Migration in R06 festlegen; auch History, Reconnect, Rollenwechsel und Mitgliedschaftsentzug abnehmen. |
| Niedrig | Anleitung hängt von installiertem Browser und Beyond20-Version ab. | Tatsächliche Erweiterungsreise prüfen; keine unbestätigten Optionen-Links oder Klickzahlversprechen. |
| Offen | Reichweite „alle Menüs“ und Positionspersistenz über Reload, Login oder Geräte. | R03 spezifiziert die konkrete Liste und Speicherdauer. |
| Offen | „Andere Würfel“ könnte Darstellung oder zusätzlich Spielzustandsänderungen meinen. | In R04 je Wurftyp eine kleine Wirkungsmatrix abstimmen. |

Die Medium-Risiken sind Eingaben für die jeweiligen Entwürfe, keine bereits gelösten
Designfragen. Dieser Bericht erteilt keinen pauschalen Deploy-Handoff.

## Verifikation und nächster begrenzter Schritt

**Durchgeführt:** ausgewählte Quellpfade und jüngere Produkt-/Lieferdokumente gelesen;
Containeridentität und Mounts ermittelt; 23/23 Dateihashes mit dem neueren Quellstand
abgeglichen; fünf statische Quellbefunde bestätigt. Öffentliche GET-Prüfung liefert
HTTP 200 für `/health/live`, `/beyond20.html` und drei betroffene JS-/CSS-Assets.
Die vier geprüften HTML-/Assetantworten stimmen mit dem Containerinhalt überein.
Berichtsstruktur, lokaler Beleglink, JSON, Hash-/HTTP-Ergebnisse und Whitespace wurden
abschließend geprüft.

**Nicht durchgeführt:** angemeldete Browserreise, echte Beyond20-Erweiterungsinstallation,
echter D&D-Beyond-Wurf, Funktions-/Regressionstests oder Datenbankänderungen.
Ein öffentliches 200 belegt keine erfolgreiche Player-/DM-Nutzerreise. Für diese reine
Dokumentationsaufnahme wurde keine Anwendung neu gebaut oder ausgeliefert.

Vorhandene Ausgangspunkte für spätere gezielte Prüfungen sind im neueren Quellstand
`test_feedback_b02_browser.py`, `test_external_rolls.py`, `test_combat_api.py`,
`test_token_upload_2026_09_23.py`, `test_table_contexts.py`,
`test_table_contexts_browser.py`, `test_token_layer_permissions.py`,
`test_token_layers_browser.py`, `test_playtable_token_clipboard_browser.py`,
`test_chat_api.py` und `test_private_conversations*.py` unter `tests/`.
Ihre Existenz ist kein neuer erfolgreicher Testlauf; alte Annahmen/Fixtures vor Verwendung prüfen.

**Nächster Schritt:** Apply für R01/R02 auf dem verifizierten Quellstand mit konkreten
UI-Reisen, Rollen und kleinen Abnahmekriterien; anschließend die Fensterliste für R03
und den Player-Initiativeablauf R04 präzisieren.
Danach pro freigegebenem Funktionsslice gezielt prüfen, committen/pushen, auf
`https://vtt.roll-drauf.de` ausliefern und beide vorgesehenen Rollen über das normale UI
prüfen. Quelle, Image, effektive Compose-Konfiguration, Tests, Live-Ergebnis und
Rollback müssen je Slice belegt sein. Eine separate Entwicklungsumgebung ist keine
Lieferbedingung. Keine im Research nur vorgeschlagene Funktion ist damit als geliefert markiert.
