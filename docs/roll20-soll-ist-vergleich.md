# Roll20 Soll-Ist-Vergleich

Stand: 2026-03-27

## Quellen

- Roll20 Home / Marketing / Einstieg: [roll20.net](https://roll20.net/)
- Offizieller Roll20 Help Center Artikel "Creating your game lobby on Roll20": [help.roll20.net](https://help.roll20.net/hc/en-us/articles/29257513100183-1-Creating-your-game-lobby-on-Roll20)
- Offizieller Roll20 Help Center Artikel "My Games": [help.roll20.net](https://help.roll20.net/hc/en-us/articles/29619836768791-My-Games)
- Offizieller Roll20 Help Center Artikel "Game Details Page (GM Only)": [help.roll20.net](https://help.roll20.net/hc/en-us/articles/29620064514071-Game-Details-Page-GM-Only)
- Offizieller Roll20 Help Center Artikel "Invite, Promote and Manage Players": [help.roll20.net](https://help.roll20.net/hc/en-us/articles/29620515876375-Invite-Promote-and-Manage-Players)
- Offizieller Roll20 Help Center Artikel "Using Our Looking for Group Tool": [help.roll20.net](https://help.roll20.net/hc/en-us/articles/360037774473-How-to-Use-Looking-for-Group)
- Offizieller Roll20 Help Center Artikel "Player Directory": [help.roll20.net](https://help.roll20.net/hc/en-us/articles/360039178994-How-to-Use-the-Player-Directory)
- Offizieller Roll20 Help Center Artikel "Page Toolbar & Folders": [help.roll20.net](https://help.roll20.net/hc/en-us/articles/360039675413-Page-Toolbar)
- Offizieller Roll20 Help Center Artikel "My Settings": [help.roll20.net](https://help.roll20.net/hc/en-us/articles/360039675153-My-Settings)
- Offizieller Roll20 Help Center Artikel "Game Settings": [help.roll20.net](https://help.roll20.net/hc/en-us/articles/29620477106711-Game-Settings)

## Zielbild

Das Ziel ist nicht nur "irgendwie spielbar", sondern der erste Roll20-Workflow muss in der Bedienlogik wiedererkennbar sein:

1. Konto anlegen oder anmelden.
2. Zu `My Games` gelangen.
3. Spiel erstellen oder beitreten.
4. Im `Game Details`-Bereich vorbereiten.
5. `Launch Game` starten.
6. Im Tabletop die Kernwerkzeuge benutzen:
   - Seiten / Karten
   - Tokens
   - Initiative / Turn Order
   - Chat
   - Journal / My Settings / Page Toolbar

## Soll-Ist DM-Flow

### 1. Einstieg

Soll bei Roll20:
- Nutzer erstellt ein kostenloses Konto auf der Hauptseite.
- Nach Login landet er in der Roll20-Navigation.

Ist bei uns:
- Login ist eine einfache Username/Password-Seite.
- Registrierung ist aktuell separiert und funktioniert mit Registrierungsschlüssel.

Impact:
- Niedrig bis mittel.
- Funktional okay, aber Roll20 hat mehr Orientierung über die Hauptnavigation.

### 2. My Games / Übersicht

Soll bei Roll20:
- `Games`-Menü oder `My Games`.
- Suchfeld für Spiele.
- Liste aller Spiele.
- `Create New Game`.
- `Join A Game`.
- `Launch Game` direkt von der Liste.

Ist bei uns:
- Kampagnenübersicht existiert.
- Es gibt DM- und Spieler-Ansichten.
- Quickstart für die erste Session ist vorhanden.
- Der visuelle und semantische Fokus ist aber noch nicht so klar wie `My Games`.

Impact:
- Mittel.
- Der Nutzer versteht das Ziel, aber die Roll20-artige Übersicht fehlt noch in der Menülogik.

### 3. Game Details / Lobby

Soll bei Roll20:
- Eigene Game-Details-Seite pro Spiel.
- Dort: Spielinfos, private Foren, Einstellungen, Spieler verwalten, Invite Players.
- `Launch Game` ist klar sichtbar.

Ist bei uns:
- Kampagnendetailseite ist vorhanden.
- Session-Start- und Upload-Workflow ist bereits angelegt.
- Die Trennung zwischen `Lobby`, `Settings`, `Invite`, `Launch` ist noch nicht so stark wie bei Roll20.

Impact:
- Hoch.
- Genau hier entscheidet sich, ob der DM den Flow ohne Nachdenken versteht.

### 4. Einladung / Spielerverwaltung

Soll bei Roll20:
- `Invite Players` in der Game Details Page.
- Link/Email-Einladung.
- Rollen wie Creator / Player / GM / Co-GM.

Ist bei uns:
- Registrierung mit Schlüssel statt offener Roll20-Einladungslogik.
- Player-Journey ist eher kampagnenbasiert als invite-link-basiert.

Impact:
- Mittel bis hoch.
- Für DAU-Freundlichkeit gut, für Roll20-Parität noch nicht vollständig.

### 5. Erste Session starten

Soll bei Roll20:
- Spiel aus `My Games` oder `Game Details` öffnen.
- `Launch Game`.
- Im Tabletop landen, mit Toolbar, Seiten, Chat, Journal, Turn Order.

Ist bei uns:
- Quickstart existiert.
- Session, Kartenstapel und Spieloberfläche sind vorhanden.
- Die neue Session-Oberfläche bildet jetzt die Kern-Elemente deutlich besser ab.

Impact:
- Hoch.
- Das ist euer kritischer Kernflow und mittlerweile deutlich näher am Ziel.

## Soll-Ist Spieler-Flow

### 1. Einladung / Beitritt

Soll bei Roll20:
- Spieler loggt sich ein.
- Klickt auf Einladung oder `Join A Game`.
- landet auf Game Details / Join Path.
- Klick auf `Launch Game`.

Ist bei uns:
- Spieler nutzt den Session-/Kampagnenkontext und den Login.
- Der Einstieg ist verständlicher, aber weniger Roll20-nah in der Navigation.

Impact:
- Mittel.

### 2. Im Spiel

Soll bei Roll20:
- Spieler sieht Tabletop.
- Rechte Seitenleiste mit Chat, Journal, Artefakten und Settings.
- Bei Bedarf Character Sheet.

Ist bei uns:
- Session-Oberfläche hat jetzt:
  - Map-Mitte
  - linke Toolbar
  - rechte Sidebar mit Chat / Tools / Session
  - Turn Order / Tokens / Layers

Impact:
- Hoch.
- Hier ist der Flow jetzt grundlegend passend, aber einige Interaktionen sind noch vereinfachte Eigenlogik.

## Soll-Ist UI-Elemente

### Bereits abgedeckt oder nahe dran

- `Launch Game`-Gedanke durch Session-Start und Quickstart.
- `Turn Order`-Element.
- `Page Toolbar`-ähnliche Karten-/Layer-Steuerung.
- `My Settings`-ähnliche Session-/Werkzeugsteuerung.
- Chat rechts.
- Tokens und Kartenebenen.

### Noch nicht Roll20-paritätisch

- `Games`-Topnavigation mit klarer `My Games`-Hierarchie.
- `Game Details`-Seite als zentraler Lobby-Hub.
- `Invite Players`-Dialog mit klarer Rollenverwaltung.
- `Player Directory` / `LFG`-Alternative für offene Gruppensuche.
- `Exit Game` / `Re-Join as Player` / `Re-Join as GM` im Roll20-Stil.

## UX-Risiken

1. Die Hauptnavigation ist noch nicht sauber in `My Games -> Game Details -> Launch Game` zerlegt.
2. Die Session-Ansicht ist jetzt funktional näher dran, aber die Detailmenüs der rechten Sidebar sind noch Eigenentwicklung.
3. Für echte Roll20-Parität fehlen wahrscheinlich noch 1 bis 3 Screenshots der folgenden Roll20-Bereiche:
   - `My Games`-Seite
   - `Game Details`-Seite
   - geöffneter VTT mit Sidebar / Page Toolbar / My Settings

## Priorisierte Luecke

Der wichtigste Soll-Ist-Abstand ist aktuell nicht die Technik, sondern die "mentale Karte" des Nutzers:

1. Wo ist mein Spiel?
2. Wo lade ich Freunde ein?
3. Wo starte ich die Session?
4. Wo sehe ich Karte, Token und Turn Order?

Wenn wir diese vier Fragen in 5 Sekunden beantworten, sind wir funktional auf dem richtigen Weg.

## Naechster Schritt

Für einen exakten, visuellen Abgleich brauche ich am sinnvollsten Screenshots von:

1. eurer aktuellen `My Games` / Kampagnenübersicht
2. eurer `Game Details` / Lobby-Seite
3. Roll20 `My Games` oder `Game Details` als Referenz, falls ihr die exakte Menüanordnung pixelgenau nachbauen wollt

Bis dahin ist dieser Vergleich textlich belastbar genug, um die nächste UI-Runde zu planen.
