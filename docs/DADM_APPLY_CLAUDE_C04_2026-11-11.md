# Apply C04 – 2D-Werkzeuge und private Bibliothek zum Tisch

Status: Design abgeschlossen, Deploy erst nach C01 und exaktem Dateihandoff.
Profil standard, dauerhaft. Grundlage: C04-Discover, R15–R19/R25–R28 und
Owner-Freigabe des Gesamtprogramms. Kein neuer Renderer, kein 3D und kein
öffentliches Projekt-Sharing.

## Navigation und Snapshot

Im Editor stehen Bibliothek, Speichern, Dateiimport und Export als beschriftete
Aktionen sichtbar zur Verfügung; das bestehende Dateimenü bleibt als zweiter
Zugriff erhalten. Auf dem DM-Tisch führt „Seite hinzufügen → Eigene Bibliothek“
in einen Dialog mit Suche, Seitennavigation, eigenem Kartentitel, Vorschau und
ausdrücklicher Übernahme. Player-Komposition lädt diesen Dialog und seinen
Controller nicht. Der normale Menüpunkt Karten öffnet weiterhin den Editor.

Die Vorschau liest nur das eigene gespeicherte Projekt über den bestehenden
Library-Endpunkt. Ein kleiner gemeinsamer Snapshot-Helper nutzt validateDocument,
materialize, loadPalette/ensureDocumentImages, Renderer und embedCredits. Der
Editor-Export verwendet denselben Helper, soweit ohne Controllerwechsel möglich.
Keine Editor-Instanz im Spieltisch, keine versteckten Zeichenhandler, kein iframe
und keine Weitergabe einer Tisch-Capability in URLs. Nicht geladene Assets und
überholte Auswahlantworten führen zu sichtbarem Abbruch statt falscher Vorschau.

Eine unveränderliche Browser-Auswahl enthält Projekt-ID, gespeicherte Revision,
PNG-Blob, Pixelmaße, Titel und Credits. Wechsel der Auswahl verwirft die Vorschau
und deren Übernahmefreigabe. Der Benutzer bestätigt, dass dieses Bild im Tisch
sichtbar wird. Das private Quelldokument und seine Storage-Keys werden nicht
an Mitspieler weitergegeben. Dies ist ein Snapshot; spätere Projektänderungen
ändern eine bereits übernommene Tischkarte nicht.

## Serververtrag

Neuer begrenzter Multipart-POST unter
`/api/play/campaigns/<c>/sessions/<s>/map-library-snapshots` mit bestehendem JWT,
CSRF sowie X-VTT-Context/X-VTT-Tab. `_get_context` und tatsächliche Operatorrolle
sind erforderlich; Eigentum an der Kampagne hebt Player-Modus nicht an.
Felder: project_id (UUID), revision (Integer), request_id (8–120 Zeichen),
grid_size (16–300), name (1–120), file (PNG). Der Server prüft vor Dateiarbeit
eigenes Projekt, aktive Kampagne/Session, gültigen Kontext und Grenzen. Unter
dem vorhandenen User-Writer-Lock wird die Projekt-Revision erneut gelesen;
abweichend ergibt 409. Dimensionen müssen zum gespeicherten Projekt passen.
Bekannte PNG-/Uploadvalidierung, Größenlimit und atomare Storagequote verwenden;
keine vom Client gelieferten Storagepfade oder Download-URLs akzeptieren.

Die existierende Receipt-Tabelle wird mit Kontext-ID/Request-ID und einem Digest
über normalisierte Felder samt PNG-SHA256 verwendet. Identisches Retry liefert
dieselbe Asset-/Karten-ID, andere Nutzlast unter gleicher ID 409. Ein unklarer
abgebrochener Auftrag bleibt als solcher erkennbar und wird nicht blind erneut
ausgeführt. Asset, CampaignMap und erfolgreiches Receipt werden gemeinsam
committet; bei vorherigem Scheitern werden neue Storageobjekte/Quotaänderungen
zurückgenommen. Kein neues Schema. Die Karte speichert einen lesbaren
Projektrevisions-/Credits-Hinweis in description; PNG-Credits bleiben erhalten.
Client-PNG plus Revisionsprüfung ist kein Beweis serverseitiger Pixelherkunft;
ein berechtigter DM darf ohnehin eigene Kartenbilder hochladen.

Danach nutzt die UI addLayer/activateLayer aus dem vorhandenen Scene-Stack.
Scheitert diese zweite Stufe, bleiben die erzeugte Karten-ID und ein sichtbarer
„Zum Tisch hinzufügen“-Retry erhalten. Kein zweiter Snapshot-Upload beim Retry,
keine falsche Erfolgsmeldung vor tatsächlicher Aktivierung. Rollen-/Kontextwiderruf
zwischen Schritten wird durch jeden bestehenden Endpunkt erneut geprüft.

## Werkzeugvertrag

Radierer bietet „Aktive Ebene“ als Standard und eine ausdrückliche Auswahl
„Alle sichtbaren, entsperrten Ebenen“. Standard radiert die aktive unterstützte
Ebene oder erklärt die Sperre; kein stiller Wechsel auf irgendeine Rasterebene.
Raster nutzt bestehende StrokeEngine, Tiles entfernen berührte Zellen, Symbole
entfernen berührte Stempel anhand vorhandener Geometrie. Beschriftungen und Wege
bleiben erhalten; die UI nennt den begrenzten Wirkbereich Raster/Kacheln/Symbole.
Versteckte/gesperrte Ebenen bleiben immer erhalten. Pointer-Cancel stellt den
Zustand vor der Geste her. Eine Geste ist eine gemeinsame Undo-/Redo-Aktion.
Vor Mutation wird das benötigte Historybudget begrenzt; zu große Aktionen werden
vorher verweigert oder die laufende Geste vollständig zurückgesetzt. Kein
verlustbehaftetes „Rückgängig möglich“ nach Verwerfen des eigenen Undo-Schritts.

Stempelraster ist optional, standardmäßig aus, Rasterweite begrenzt; die sichtbare
Vorschau und tatsächliche Platzierung verwenden dieselbe gerundete Position.
Rotation/Flip/Vary bleiben erhalten. Kachelpinsel hat Radius/Abdeckung in ganzen
Zellen, bleibt unabhängig von Pixelraster und physischem Maßstab. Mehrfachauswahl
bekannter Kachelvarianten erlaubt Variation; eine Zelle wird innerhalb derselben
Geste höchstens einmal neu zufällig belegt, damit Rückwärtsziehen kein Flimmern
erzeugt. Alle gesetzten Asset-IDs müssen schon im vorhandenen Katalog stehen.

## Prüfung, Risiken und Übergabe

Medium-Risiken Revisionsrennen, private Quellen, Retry-Duplikate und Undoverlust
sind durch die obigen Verträge behandelt. Gezielte API-Prüfung: fremdes Projekt,
Player-Kontext eines Owners, falsche Session, Widerruf, alte Revision, falsches PNG,
Quota/Storagefehler, identisches Retry und Nutzlasttausch. Browserprüfung: Bibliothek
über normalen DM-Weg, echte Vorschau→aktive Karte auch beim Firefox-Player,
unveränderte Quelle, Fehler/Retry und keine DM-Initialisierung beim Player.
Editorprüfung über Pointergesten: Raster/Tile/Symbol, aktive/alle Ebenen, Locks,
Cancel und genau ein Undo/Redo, Kachelpinsel und Stempelraster; JSON/ZIP/PNG-Credits
und bestehende Assetpakete bleiben erhalten. DE/EN, Papier/Nacht und 390 px.

Primärquellen, am 2026-11-11 geprüft: [Canvas-Bildpipeline](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Using_images)
für geladene Bildquellen und drawImage; [Flask-Dateiupload](https://flask.palletsprojects.com/en/stable/patterns/fileuploads/)
für Multipart/request.files und harte Größenlimits. Die konkrete Wiederverwendung
und Transaktionsgrenze sind Entscheidungen aus der Repo-Inventur.

Claude implementiert ausschließlich den festgelegten Dateibesitz. Die Koordination
führt Tests aus, lässt einen separaten Claude-Diffreview durchführen, integriert,
pusht und liefert mit erhaltenem Vorimage app-only nach der Live-Regel. C05 beginnt
erst auf dem geprüften C04-Editor. Neue Architektur-/Schemafragen gehen nach Apply.
