# Codex: Lösungsrecherche zu Daten, Licht und Initiative

Datum 16.11.2026. Phase Discover; Recherche abgeschlossen, Architektur und Umsetzung offen.
Aufbewahrung dauerhaft. Teilauftrag U02/U03/U04/U07/U08/U13. Quellbasis:
`/home/admin/projects/roll-drauf-vtt-session-feedback-20261116`, HEAD `3939766e72a2cd72bc7e69fb0382c9fc96d2edba`,
App `d4ff7e4fe2ef77a4a36ca41fa205ef5db2ad5b02`. Optionen und Prüffavoriten sind
Recherchefolgerungen, keine beschlossenen Verträge oder neuen Owner-Entscheidungen.

## U02: historischen Verlauf erreichbar machen

**Codebefund.** `vtt/campaign_rooms.py::messages` liest nur `CampaignChatMessage`.
Diese Texttabelle hat keinen Sessionbezug, Nachrichtentyp oder Sichtbarkeitswert.
`vtt/models/chat_message.py::ChatMessage` hat dagegen Session, Nachrichtentyp,
Moderation, Löschzustand und `public/gm_only/blind/self`.
`vtt/play/routes.py::_chat_row_for_role` projiziert Sessionhistorie bereits
rollenabhängig. Die letzte Lieferung hat die Bestände bewusst getrennt.
Ein einfaches Kopieren von `content` würde relevante Herkunft und Schutzinformation verlieren.

| Option | Nutzen | Aufwand, Risiken und Voraussetzungen |
| --- | --- | --- |
| A: geschützte historische Leseprojektion im Kampagnenraum | Originale bleiben erhalten, frühere Sitzungen werden auffindbar. | Mittel. Sitzungsauswahl oder gemeinsamer Feed klären; Mitgliedschaft und Sessionzugriff bei jedem Lesen prüfen. |
| B: kontrollierter Import in einen erweiterten Kampagnenverlauf | Einheitliches Verlaufsmodell und Nachladen möglich. | Größer. Erst Metadaten, Herkunft, Idempotenz, Moderationssynchronisierung und Rollback bestimmen; heutige reine Texttabelle genügt nicht. |
| C: nur neue Kampagnentexte | Keine Datenarbeit. | Klein, erfüllt den verlangten Altverlauf nicht vollständig. |

**Prüffavorit A:** zuerst eine begrenzte Leseprojektion untersuchen. Eine geschützte
Sitzungsauswahl vermeidet das sofortige Zusammenkopieren. Ob sie dem gewünschten
Gesamtverlauf genügt, ist eine Produktfrage für Apply.
Für einen vereinigten Feed sind Quellart und Quell-ID zusätzlich zur Zeit relevant:
Die unabhängigen IDs zweier Tabellen bilden keine globale Reihenfolge.
Eindeutige Sortierung und effizientes Nachladen sind ausdrücklich zu prüfen.
[PostgreSQL 16: LIMIT/OFFSET](https://www.postgresql.org/docs/16/queries-limit.html).

**Apply-Fragen:** Welche alten Sessions und Nachrichtentypen? Welchen Zugriff haben
nachträglich beigetretene Mitglieder? Benötigt Conversations privilegierte Historie,
und welchen expliziten Kontext dafür? Wie wirken Moderation, Löschung und Mitgliedschaftsentzug?

**Akzeptanzkandidaten:** normale Kampagnenauswahl führt zum Altverlauf; gleiche
Zeitstempel/überlappende IDs verdoppeln oder überspringen nichts; Fremdkampagne und
entzogene Mitgliedschaft verweigert; `gm_only` bleibt aus der Playerhistorie,
`blind/self` behält erlaubte Platzhalter; private Paargespräche bleiben außerhalb.
Historische Produktivdaten wurden nicht ausgelesen.

## U07/U08: Lichtausbreitung, Wände und Playerprojektion

**Codebefund.** `vtt/play/vision.py` führt 180 Strahlen pro Token aus und klassifiziert
anschließend Zellen anhand von Sichtweite und Lichtradien. `SceneWall.sight` blockiert
diese Strahlen; `SceneWall.light` wird nicht als unabhängige Lichtbarriere ausgewertet.
Das ist eine dokumentierte Bestandsvereinfachung. `play-ui.js::_renderVisionLayer`
zeichnet Radiuskreise/Wände, `_fogCellMarkup` einzelne Zellen. Eine sichtbare Aura
ist noch keine vollständige dynamische Beleuchtung oder DM-Spielervorschau.

**Neu ausgeführte Probe:** Gleiche Wand mit `sight=none` liefert für `light=normal`
und `light=none` identische sichtbare Zellen; Zelle (4,0) hinter der Wand bleibt
sichtbar. `sight=normal` blockiert diese Zelle. Nur bestehende reine Geometriedatei
mittels `runpy`, ohne Flask-Initialisierung, Datenbank oder Produktionseingriff.
[Parameter, Quellhash und Ergebnisse](geometry-probes.json).

Für einen Token, 20 Wände, Sichtweite 500, Raster 32 und 180 Strahlen ergab die
synthetische Probe mit 0/10/40 Lichtquellen rund 15/54/223 ms Median aus je drei Läufen.
Das ist keine Browserlatenz, kein Lasttest und keine Messung einer Alternative.
Die Zahlen begründen, Leistungsbudget und Wiederverwendung von Berechnungen zu untersuchen.

Foundrys offizielle Referenzen beschreiben wandbegrenztes Licht, getrennte
Wandeigenschaften und polygonbasierte Sichtberechnung mit Kanten/Eckpunkten/Strahlen.
Sie sind Vergleichsmaterial; Foundry wird dadurch keine Abhängigkeit dieses VTT.
[Lighting](https://foundryvtt.com/article/lighting/),
[Walls](https://foundryvtt.com/article/walls/),
[ClockwiseSweepPolygon](https://foundryvtt.com/api/classes/foundry.canvas.geometry.ClockwiseSweepPolygon.html).

| Option | Nutzen | Aufwand / Risiken |
| --- | --- | --- |
| A: Zellansatz um echte Licht-zu-Zelle-Blockade erweitern | Begrenzte fachliche Erweiterung, vorhandenes Fogformat weiter nutzbar. | Mittel bis größer. Mehr Rechenarbeit, grobe Rasterkanten; Caches, Invalidierung und Größenbudget prüfen. |
| B: getrennte Sicht-/Lichtpolygone mit Maskendarstellung | Unabhängige Sicht-/Lichtblockade und glattere sichtbare Grenzen. | Größer. Robuste Ecken/Überlappung, Server-/Client-Parität, Reconnect und Koordinaten brauchen Nachweise. |
| C: neuer GPU-/Shader-Renderpfad | Raum für viele spätere Effekte. | Sehr groß. Neue Ressourcen-/Browserabhängigkeit; Serverprojektion weiterhin separat nötig. Bedarf für das heutige Ziel nicht belegt. |

**Prüffavorit:** A als begrenzte Korrektheitsreferenz und B als visuellen Kandidaten
auf demselben Szenensatz vergleichen. Noch keine Wahl eines Algorithmus oder Renderers.
„Raytracing“ legt weder Hardware noch eine Bibliothek fest.
SVG-Masken passen zur vorhandenen Ebene, können aber viele DOM-Knoten erzeugen.
Canvas-Compositing reduziert diese Knotenzahl und braucht einen eigenen Redraw-/Skalierungsablauf.
Die dokumentierten APIs belegen Mechanismen, keine Leistung dieser App.
[MDN SVG mask](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/mask),
[MDN Canvas-Compositing](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/globalCompositeOperation).

**Apply-Fragen:** Natürliche Sicht ohne Licht, Umgebungslicht/Dunkelsicht,
Bright/Dim/Darkness; Vorschau eines Tokens versus Vereinigung eigener Tokens
(heutiges Fogverhalten). Vorschau darf persistierte Player-Aufklärung nicht
versehentlich erweitern. Maske, sichtbare Entitäten und autorisierte Datenlieferung
müssen jeweils dieselben ausdrücklich festgelegten Regeln beachten.
Die Probe behauptet keinen neu nachgewiesenen Autorisierungsbypass.

**Wall-UI:** Bestehende CRUD-/Popover-Wege können einen besseren zentralen Einstieg
bekommen. Wandklick und explizite Wandliste sind Vergleichskandidaten; eine Liste
hilft bei kleinen Displays und überlappenden Segmenten. Auswahlzustände müssen
bei Löschen/Kartenwechsel konsistent bleiben. Keine zweite CRUD-/Rechteimplementierung beschließen.

**Akzeptanzkandidaten:** Lichtblockade bei freier Sicht und umgekehrt; Ecken/Spalten,
überlappende Bright/Dim-Quellen und Darkness; Bearbeiten/Entfernen/Bewegen;
Zoom/Pan/Resize; DM/Player/Owner-as-Player, Vorschauwechsel, Reload, Reconnect,
zwei Tabs; keine fremden Fogdaten oder volle Geometrie im Playerpayload.
Leistungsbudgets später an einer vereinbarten Szenenmatrix messen.

## U13: Initiative passiv erfassen und Mehrfachwürfe bestätigen

**Codebefund.** `vtt/play/rolls.py::actor_token` prüft Kontext, Session, aktive Karte,
Sichtbarkeit und Besitz; `apply_initiative` ersetzt sofort den Wert und aktualisiert
einen laufenden Encounter. Bogenwürfe nutzen `sheet_link.py::execute_sheet_roll`.
Receipts deduplizieren Transport, verwalten aber keine DM-bestätigten verschiedenen
Rerolls. Zusätzlich verarbeitet `play-ui.js::updateCombatTracker` externe Turn-Tracker-
Updates. Dieser und direkte Tokenänderungen müssen denselben neuen Fachvertrag beachten.
Beyond20 unterscheidet explizite Initiativewürfe von `update-combat`; externe Namen
oder Ereignisse autorisieren keinen fremden Token.
[Offizielle Beyond20-API](https://beyond20.here-for-more.info/api).

| Option | Nutzen | Aufwand / Risiken |
| --- | --- | --- |
| A: erster eindeutiger Wurf automatisch, weitere als Kandidaten | Passiver Tracker mit DM-Auswahl mehrfacher Würfe. | Mittel bis größer. Erstwurfrennen, Begegnungsgrenze, Identitäten und Bestätigungszustand klären. |
| B: sämtliche Würfe bis DM-Freigabe vormerken | Einheitliche Freigabe und Warteliste. | Mittel bis größer. Zusätzliche DM-Arbeit; Freigabe schon beim Erstwurf wurde noch nicht verlangt. |
| C: letzten Wert ersetzen, nur Verlauf hinzufügen | Kleine Bestandserweiterung. | Erfüllt Bestätigung/Auswahl allein nicht. |

**Prüffavorit A**, mit ausdrücklich noch offener Erstwurfregel.
Zu untersuchen: Wurfidentität und Quelle, Session/Begegnung oder Sammelrunde,
Token-/Charakterbindung, Akteur, Ergebnis, Sichtbarkeit, Empfangszeit und Annahmestatus.
Das ist eine Informationsinventur, kein festgelegtes Schema/API. Zwei echte Würfe
mit derselben Zahl sind verschieden; dasselbe Ereignis erneut zugestellt ist kein neuer Kandidat.

Bei gleichzeitigem Bestätigen und Würfeln sind Revisionen, eindeutige Constraints
und konsistente Sperrreihenfolge zu prüfen. Bestehende Token-/Encounter-Locks sind
Ausgangspunkt; PostgreSQL dokumentiert Zeilensperren und Deadlockrisiken.
[PostgreSQL 16: Explicit Locking](https://www.postgresql.org/docs/16/explicit-locking.html).

**Akzeptanzkandidaten:** Sheet/Beyond20/NPC, fehlende/mehrdeutige Bogenbindung,
fremder Token, Replay versus echte gleiche Totals, zwei Spieler gleichzeitig,
zwei DMs bestätigen Verschiedenes, Bestätigung nach neuem Wurf/Kampfende,
aktiver Zug bei Neusortierung, generischer W20 bleibt generisch.
Direct-Patch- und `update-combat`-Wege in die Testmatrix aufnehmen.

**Combatfehler bleibt offen:** `_startCombat` verwendet Modus `players`.
„Request failed“ ist keine reproduzierte Ursache. Vor Fix Sessionstatus,
Kontext, Karten-/Tokenbestand, Request und Antwortstatus erfassen.
Hier wurde kein Kampf in einer echten Kampagne ausgeführt.

## U03/U04: englisches SRD und Compendium

**Codebefund.** `regelwerk-compendium.js:4` und `vtt/rules.py` binden das Compendium
an Deutsch. `compendium.py::_spells` liest deutsche Begriffe wie Zeitaufwand,
Reichweite und Wirkungsdauer. Andere Extraktoren haben ebenfalls sprachgebundene
Annahmen. Übersetzte UI-Labels oder bloß übersetztes JSON lösen diese Parsergrenze nicht.
`generator.py`, `validator.py`, Manifest und zentrale `source-locks.json` bieten
bereits einen Ausgangspunkt für versionierte Quellen und generierte Artefakte.

Das englische Original SRD 5.2.1 ist offiziell verfügbar und im bestehenden
`/regelwerk/en` als PDF erreichbar. Es kann die belegte Grundlage der gewünschten
Stilfassung bleiben. [Wizards/D&D Beyond: SRD](https://www.dndbeyond.com/srd).
Ein neuer Bytevergleich bestätigt: Das bereits mitgelieferte englische PDF stimmt
mit dem offiziellen Download überein (SHA-256 `8974902d109d6e63672d7c490bde9ccf052410503d9cfa768237154fbc5e3d87`).
[Download-/Hashbeleg](english-source.json). Ein englischer Paket-Source-Lock wurde dabei nicht ergänzt.
CC BY 4.0 erlaubt Bearbeitung unter seinen Bedingungen, darunter Attribution und
Kennzeichnung von Änderungen. Die konkrete SRD-Attribution und vorhandene Quell-/Lizenzanzeige
im neuen Paket berücksichtigen. [Creative Commons BY 4.0](https://creativecommons.org/licenses/by/4.0/).

| Option | Nutzen | Aufwand / Risiken |
| --- | --- | --- |
| A: versioniertes EN-Paket über erweiterte bestehende Pipeline | Separate Textprüfung und Sprache, vorhandene Paket-/Quellwege als Basis. | Größerer Inhaltsscope. Extraktoren, Generator/API/Cache müssen Sprache bewusst zuordnen. |
| B: sprachneutrale strukturierte Daten plus lokalisierte Textschichten | Langfristig gemeinsame Mechanik und explizite Übersetzungsbeziehungen. | Größer. Bestands-Pins, Creator-/Bogenverträge betroffen; als eigenes Datenvorhaben bewerten. |
| C: dynamische Übersetzung deutscher Ergebnisse | Rasch sichtbare englische Texte. | Terminologie, Suche, Quelle, Cache und redaktionelle Revision nicht ausreichend gesichert; keine endgültige Erfüllung. |

**Prüffavorit A:** repräsentativer Inhaltsdurchstich vor Volltextbearbeitung.
Fließtext, Felder, Querverweise, Compendium und Creatorwerte gemeinsam prüfen.
B bleibt ein eigenständig zu bewertender Lösungsraum.
UI-Locale, Inhalts-Locale, Dokument-/Entitätsidentitäten und bestehende Charakter-
Pins müssen definiert werden; fehlende EN-Einträge brauchen sichtbaren Zustand.
Sprachkennzeichnung ist sinnvoll, ersetzt aber die Datenzuordnung nicht.
[W3C: Language tags](https://www.w3.org/International/articles/language-tags/index.en.html).

**Akzeptanzkandidaten:** Sprachwechsel, direkter Detail-Link, englische Suche/Filter,
Zauber mit strukturierten Werten, Monster/Gegenstand/Creator-Entität,
Quell-/Lizenzansicht, fehlende Übersetzung, Cachewechsel, Deutsch unverändert,
vorhandene Charaktere/Revisionen behalten ihre Regelbedeutung.
Vollständigkeit später gegen eine explizite Inhaltsinventur abnehmen.

## Risiken, Übergabe und tatsächliche Verifikation

**Mittel:** historische Zugriffsränder (U02), Geometrie-Leistungsbudget und
Server-/Client-Parität (U07/U08), Bestätigungsrennen und Legacywege (U13),
Textqualität, Parserannahmen und bestehende Pins (U03/U04). Vor einem jeweiligen
Deploy-Handoff lösen; dieser Vergleich nimmt die Risiken nicht pauschal an.

**Nächste Apply-Arbeit:** U02 historische Quell-/Sichtmatrix und U13 Wurfzustände
getrennt festlegen; U07 Sicht-/Lichtsemantik und kleinen Szenensatz definieren,
danach Verfahren vergleichen; U03/U04 Inhalts-/Identitätsmatrix erstellen.
Unabhängige UX-/Farbpakete können gleichzeitig vorbereitet werden.

Neu durchgeführt: Code/Primärquellen gelesen, isolierte Geometrieprobe und kleine
synthetische Laufzeitmessung. Abrufdatum externer Quellen: 16.11.2026.
Nicht durchgeführt: Browserreise, produktive Chat-/Kampfdatenabfrage, neuer
Renderingprototyp, Migration, Funktionssuite, Commit oder Deployment.
