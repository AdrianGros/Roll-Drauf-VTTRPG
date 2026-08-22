# UI-Analyse: World Atlas als Standard-Home für das Browser Game

**Projekt:** Roll Drauf VTT  
**Datum:** 2026-08-18  
**Status:** Discover / Apply – Zielbild und Implementierungsempfehlung  
**Entscheidungsthema:** Soll der World Atlas die standardmäßige Home-Ansicht werden und die bisherigen Home-Controls aufnehmen?

## Kurzfassung

Ja: Der World Atlas sollte die Standard-Home-Ansicht werden.

Der entscheidende Caveat lautet: Er sollte zunächst nicht als „globale Weltkarte“ verstanden werden, in die wir unbesehen alle vorhandenen Kartenbilder legen. Die aktuelle Datenbasis enthält vor allem Kampagnen, Charaktere, Sessions, Gilden und kampagnenbezogene `CampaignMap`-Objekte. Das ist noch kein vollständiges World-Atlas-Modell.

Die sinnvollste Zielrichtung ist daher eine **Atlas Command Surface**:

- Der Atlas ist der visuelle und räumliche Mittelpunkt des Homes.
- Kampagnen, Charaktere, Sessions, Gilden und Vorbereitungsstatus erscheinen als verständliche Atlas-Nodes oder Layer.
- Die bisherigen Home-Controls werden nicht als separates Discord-artiges Dashboard daneben gestellt, sondern als Rail, Filter, Inspector und Command Dock in den Atlas eingebettet.
- Der rechte Inspector beantwortet nach Auswahl sofort: „Was ist das?“ und „Was kann ich jetzt tun?“
- Die wichtigste nächste Aktion – Live-Session, Session-Prep, Kampagnen-Hub oder erster Setup-Schritt – bleibt jederzeit sichtbar.
- Der Chronicle-/Social-Feed bleibt erhalten, wird aber zur sekundären Ansicht bzw. zum Drawer. Er darf nicht die primäre räumliche Orientierung verdrängen.
- Der Kampagnen-Hub bleibt die operative Detailfläche für Kartenverwaltung, Mitglieder, Sessions und Assets.
- Play bleibt die separate, dichte Tabletop-Workspace-Ausnahme mit eigener Interaktionslogik.

Das ist eine deutliche Abkehr von einem Discord-inspirierten Home. Sie passt besser zu einem VTT, weil der zentrale Nutzerbedarf nicht „Welchen Channel lese ich?“ lautet, sondern:

> „In welcher Welt, Kampagne oder Session befinde ich mich – und was ist mein nächster sinnvoller Schritt?“

---

## 1. Ausgangspunkt und Untersuchungsbasis

Diese Analyse baut auf dem bereits erstellten Best-Practices-Bericht auf:

- [Browser-Game Best Practices – kompletter Bericht](/home/admin/browser-game-best-practices.md)

Zusätzlich wurde der aktuelle Projektstand in den relevanten Home-, Book-Shell-, Kampagnen-, Karten- und Play-Dateien geprüft:

- [Dynamische Home-Komposition in `book-scene.js`](/home/admin/projects/roll-drauf-vtt/vtt/static/js/book-scene.js:911)
- [Home-Snapshot-API in `dashboard_home.py`](/home/admin/projects/roll-drauf-vtt/vtt/endpoints/dashboard_home.py:418)
- [CampaignMap-Modell](/home/admin/projects/roll-drauf-vtt/vtt/models/campaign_map.py:8)
- [Kartenverwaltung im Kampagnen-Hub](/home/admin/projects/roll-drauf-vtt/vtt/templates/campaigns.html:2882)
- [Play-Workspace](/home/admin/projects/roll-drauf-vtt/vtt/templates/play.html:310)
- [Home- und Book-Scene-Styles](/home/admin/projects/roll-drauf-vtt/vtt/static/css/book-scene.css:227)
- [Bestehende Home-Social- und Guild-Tests](/home/admin/projects/roll-drauf-vtt/tests/test_dashboard_social_hub_guild_navigation.py:1)

Die Empfehlungen berücksichtigen außerdem die bestehenden Book-UI-Entscheidungen aus:

- [Book-UI Ist-Zustand](/home/admin/projects/roll-drauf-vtt/docs/DADM_DISCOVER_BOOK_UI_IST_ZUSTAND_2026-03-30.md)
- [Book-UI Soll-Zustand](/home/admin/projects/roll-drauf-vtt/docs/DADM_DISCOVER_BOOK_UI_SOLL_ZUSTAND_2026-03-30.md)
- [Book-UI Architektur](/home/admin/projects/roll-drauf-vtt/docs/DADM_DISCOVER_BOOK_UI_ARCHITECTURE_2026-03-30.md)
- [Book-UI Layout-Regeln](/home/admin/projects/roll-drauf-vtt/docs/DADM_SOLL_BOOK_UI_LAYOUT_RULES_2026-04-01.md)

Es wurden in diesem Schritt keine Produktdateien implementiert oder umgebaut. Dieses Dokument ist der fachliche und technische Soll-Plan.

---

## 2. Klare Produktentscheidung

### Empfehlung

Den authentifizierten Home-Route weiterhin unter `dashboard` führen, aber die Standard-Ansicht innerhalb dieser Route auf `atlas` umstellen.

Vorgeschlagenes Verhalten:

```text
/dashboard                 -> Atlas Command Surface
/dashboard?view=atlas      -> Atlas explizit
/dashboard?view=chronicle  -> Feed-/Social-Ansicht
/dashboard?classic=1       -> konservativer Fallback während des Rollouts
```

Die URL-Struktur ist nur ein Vorschlag. Wichtig ist die Trennung der Zustände, nicht die exakte Query-Syntax.

### Was der Atlas nicht sein sollte

Der Atlas sollte nicht:

- den Kampagnen-Hub vollständig ersetzen;
- die taktische Session-Karte aus Play nachbauen;
- ein zweiter Discord-Channel- oder Feed-Browser werden;
- eine dekorative Karte ohne klare Labels und Aktionen sein;
- alle vorhandenen Informationen gleichzeitig als kleine Marker darstellen;
- ausschließlich über Farbe, Position oder Hover verständlich sein;
- Nutzer zwingend zu Pan und Zoom zwingen, um normale Navigation zu erledigen.

### Was der Atlas sein sollte

Der Atlas sollte:

- Orientierung, Status und nächste Aktion in einer Oberfläche verbinden;
- auf Desktop den vorhandenen Raum konsequent nutzen;
- auf kleinen Screens in Drawer-, Bottom-Sheet- und Listen-Zustände reflowen;
- eine räumliche Übersicht mit klassischer zugänglicher Liste synchronisieren;
- stabile, wiedererkennbare Positionen und Gruppierungen verwenden;
- die Book-Identität behalten, aber die alte „zwei Seiten plus Feed“-Komposition zugunsten einer App-artigen Command Surface öffnen;
- die Grenze zwischen Social Home und Session-Chat weiterhin respektieren.

---

## 3. Ist-Zustand des aktuellen Homes

### 3.1 Die Home-Ansicht ist bereits dynamisch genug für einen Umbau

Die aktuelle BookScene rendert die Dashboard-Ansicht über eine gemeinsame Seitenstruktur. `buildDashboardMarkup()` setzt momentan zusammen:

- `buildDashboardHero()` – Begrüßung, Kennzahlen und primäre Aktion;
- `buildDashboardNavigationRail()` – Social, Guilds, Kampagnen, Charaktere, Session-Prep und Play;
- `buildDashboardGuildPanel()` – primäre Gilde und Gildenwechsel;
- `buildDashboardFeed()` – Chronicle-/Social-Feed;
- `buildDashboardContext()` – Prioritäten und Quick Links.

Das ist eine gute inhaltliche Basis. Das Problem liegt weniger in fehlenden Daten als in der räumlichen Komposition:

- Der Home-Screen liest sich noch wie eine Sammlung von Karten und Bereichen.
- Navigation, Status, Social-Information und operative Aktionen konkurrieren um dieselbe Aufmerksamkeit.
- Die sechs Home-Bereiche werden als klassische Rail-Buttons und Scrollziele behandelt.
- Der Feed bekommt durch die Spread-Struktur ein hohes visuelles Gewicht, obwohl die nächste operative Aktion häufig wichtiger ist.
- Die zentrale räumliche Metapher des Spiels wird nicht zum primären Navigationsmodell.

### 3.2 Der aktuelle Home-Snapshot enthält bereits die wichtigsten Entscheidungsdaten

`GET /api/dashboard/home` liefert bereits:

- sichtbare Kampagnen;
- Charaktere;
- Sessions;
- Gilden und primäre Gilde;
- Home-Zählwerte;
- `primary_action` und `secondary_action`;
- Prioritäten;
- Feed Preview;
- Quick Links;
- Social-Scope-Informationen.

Das ist für eine erste Atlas-Version ausreichend, wenn die Nodes zunächst aus diesen Entitäten abgeleitet werden.

### 3.3 Die Kartenbasis ist derzeit kampagnenbezogen

`CampaignMap` enthält unter anderem:

- `campaign_id`;
- Name und Beschreibung;
- Breite, Höhe, Grid-Typ und Grid-Größe;
- `background_url`;
- Fog-/Light-Regeln;
- Archivierungs- und Zeitstempel.

Diese Struktur beschreibt eine wiederverwendbare Karte innerhalb einer Kampagne. Sie beschreibt noch nicht:

- eine globale Welt- oder Regionenzugehörigkeit;
- eine Position im World Atlas;
- Beziehungen zwischen Orten;
- eine Sichtbarkeit im globalen Home;
- eine Thumbnail-/Preview-Variante;
- ein semantisches Node-Icon oder einen Node-Typ;
- eine Trennung zwischen Weltkarte, Reiseübersicht und taktischer Battlemap.

Daraus folgt: Für einen MVP-Atlas sollten Kampagnen, Sessions und Gilden die primären Nodes sein. Kartenbilder sollten zunächst als Preview im Inspector erscheinen, nicht automatisch als gesamte Weltoberfläche.

### 3.4 Play ist bereits als eigener Workspace behandelt

Die Play-Ansicht besitzt:

- einen breiten Map-Viewport;
- Zoom- und Pan-Controls;
- Tool-Leiste;
- rechte Sidebar für Journal, Chat, Tools und Session;
- explizite Übergänge zwischen Book- und Tabletop-Modus.

Diese Trennung ist sinnvoll und sollte nicht durch den Home-Atlas verwischt werden. Der Atlas ist die Übersicht und Vorbereitung. Play ist der eigentliche Tisch.

---

## 4. Warum die Abkehr vom Discord-Design sinnvoll ist

Discord ist vor allem für dauerhafte Kommunikation optimiert:

- Server und Channels bilden die primäre Informationsarchitektur.
- Listen und Feeds sind die zentrale Orientierung.
- Inhalte werden chronologisch oder kanalbezogen entdeckt.
- Die wichtigste Aktion ist häufig Lesen, Antworten oder Wechseln des Channels.

Ein Browser-VTT hat andere primäre Jobs:

- Kampagnenzustand verstehen;
- Session vorbereiten;
- Charaktere und Rollen verwalten;
- Karten und Assets finden;
- in eine aktive Session springen;
- Fortschritt und Blocker erkennen;
- zwischen Weltübersicht und operativer Detailfläche wechseln.

Deshalb sollte das Home nicht wie ein kleiner Discord-Client aussehen. Social-Funktionen bleiben wichtig, aber sie sind ein Kontextlayer. Der Produktkern ist die Welt- und Session-Orientierung.

Die Book-Visualität muss deshalb nicht verschwinden. Sie sollte nur anders eingesetzt werden:

- **Book als Identität:** Rahmen, Materialität, Typografie, Kapitelgefühl, Übergänge.
- **Atlas als Arbeitsfläche:** großzügige, flexible, responsive Oberfläche innerhalb dieses Rahmens.
- **Chronicle als soziales Kapitel:** Feed, Gildenhinweise und Community-Updates als sekundärer View.
- **Play als Tisch:** eigene Workspace-Logik, eigene Dichte, eigene Toolbar.

Damit wird die Buchmetapher nicht zum Layout-Gefängnis. Sie bleibt das visuelle Betriebssystem, während der Atlas die produktive Home-Oberfläche bildet.

---

## 5. Zielbild: Atlas Command Surface

### 5.1 Desktop-Wireframe

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Brand / Kapitel     Atlas   Chronicle   Suche             Hilfe  Profil  ⏵  │
├───────────────┬─────────────────────────────────────────────┬───────────────┤
│ ATLAS-LAYER   │                                             │ INSPECTOR     │
│               │                                             │               │
│ ◉ Welt        │              WORLD ATLAS                    │ Ausgewählt:   │
│ ◌ Kampagnen   │                                             │ Kampagne      │
│ ◌ Charaktere  │       ✦ Kampagne A                          │               │
│ ◌ Sessions    │                    ◇ Session                  │ Kurzinfo      │
│ ◌ Gilden      │                                             │ Status        │
│               │  ✦ Kampagne B       ○ Charakter              │ Fortschritt   │
│ Filter        │                                             │               │
│ Status        │              ○ Gilde                         │ [Öffnen]      │
│ Suche         │                                             │ [Prep]        │
│               │                                             │ [Karte]       │
├───────────────┴─────────────────────────────────────────────┴───────────────┤
│ NEXT ACTION / COMMAND DOCK                                                   │
│ [Zur Live-Session] [Session-Prep] [Neue Kampagne] [Held anlegen] [Chronicle] │
└─────────────────────────────────────────────────────────────────────────────┘
```

Die Darstellung muss nicht exakt so aussehen. Die Informationsverteilung ist entscheidend:

1. **Oben:** globale Navigation und System-Controls.
2. **Links:** Atlas-Layer und Filter.
3. **Mitte:** räumliche Übersicht.
4. **Rechts:** kontextabhängiger Inspector.
5. **Unten:** nächste Aktionen und Erstellungsaktionen.

### 5.2 Der Atlas braucht einen Default-Fokus

Ein leerer oder vollständig unselektierter Atlas erzeugt Orientierungskosten. Bei jedem Laden sollte es einen sinnvollen Ausgangszustand geben:

- Bei einer aktiven Session: Live-Session prominent selektieren.
- Bei Prep-Blockern: die erste blockierte Session selektieren.
- Sonst: primäre Kampagne oder primäre Gilde selektieren.
- Bei einem komplett neuen Nutzer: Setup-/Create-Node selektieren.

Der Inspector muss beim ersten Render bereits erklären, warum dieses Objekt relevant ist und welche Aktion als Nächstes möglich ist.

### 5.3 Zwei Home-Modi statt Überladung

Der Atlas sollte nicht alle bisherigen Home-Inhalte gleichzeitig anzeigen. Empfohlen werden zwei eng verbundene Modi:

#### Atlas

Der Standardmodus für:

- Kampagnenübersicht;
- Sessionstatus;
- Gilden- und Social-Kontext;
- Charakterbezug;
- nächste Aktionen;
- Karten-/Asset-Previews nach Auswahl.

#### Chronicle

Die sekundäre, eher lineare Ansicht für:

- Social-Updates;
- Gildenhinweise;
- Chronik-Feed;
- Aktivitäten und Hinweise;
- Quick Links.

Der Nutzer wechselt zwischen beiden Modi, ohne den Home-Kontext zu verlassen. Der Feed wird also nicht gelöscht, sondern aus der visuellen Führungsrolle genommen.

---

## 6. Einbettung der bestehenden Home-Controls

| Aktueller Control / Bereich | Neue Atlas-Position | Empfohlenes Verhalten |
|---|---|---|
| Home / Campaigns / Characters im Ribbon | globale Topbar oder kompakter linker Rail | Einmalige primäre Navigation; keine doppelte Navigation im Atlas-Inhalt |
| Play | persistente Resume-Aktion oben rechts und im Command Dock | Label abhängig vom Zustand: „Zur Live-Session“, „Session-Prep fortsetzen“ oder „Play-Pfad öffnen“ |
| Logout | Profil-/Account-Menü | Logout ist wichtig, aber kein gleichrangiger Home-Content-Button |
| Home-Hero | Inspector oder „Next Action“-Card | Keine lange Begrüßung als dominantes Element; kurze Statuszeile plus konkrete Aktion |
| Primäre Aktion | Command Dock und Inspector | Immer prominent, maximal eine primäre CTA gleichzeitig |
| Sekundäre Aktion | Command Dock als Secondary CTA | z. B. „Charakterarchiv öffnen“ oder „Held anlegen“ |
| Navigation Rail mit sechs Bereichen | Atlas-Layer-Rail | Layer ein-/ausblendbar, mit Icon und Text; keine sechs großen Karten im Spread |
| Primäre Gilde | Filter-/Context-Chip links oben und ausgewählter Node | Gildenwechsel als kompakter Selector; Gildenpanel nur im Inspector ausklappen |
| Guild-Cards | Guild-Nodes oder Guild-Filter | Nicht als große statische Kartengruppe im Home rendern |
| Chronicle Feed | rechte Drawer-Ansicht oder Modus „Chronicle“ | Social bleibt lesbar, aber nicht als Standard-Hauptfläche |
| Prioritäten | Inspector-Abschnitt „Als Nächstes“ | Jede Priorität sollte eine konkrete Aktion oder einen Deep Link besitzen |
| Quick Links | Command Dock oder „Mehr“-Menü | Nur häufige Aktionen sichtbar; seltene Bereiche über „Mehr“ |
| Kampagnenlisten | Atlas-Nodes plus zugängliche Listenansicht | Node-Auswahl und Listen-Auswahl müssen dieselbe Selection steuern |
| Charaktere | eigener Layer und Inspector-Sublist | Charaktere nicht mit Kampagnenmarkern visuell gleich behandeln |
| Session-Prep | Session-Node mit Blocker-Badges | Blocker direkt am Node und im Inspector mit Lösung anzeigen |
| Map-Management | Inspector-Preview und Link in Kampagnen-Hub | Keine vollständige Kartenverwaltung im Home duplizieren |
| Social Scope | Status-/Info-Hinweis im Chronicle | Klarstellen, dass Home-Social vom Session-Chat getrennt bleibt |

### 6.1 Konkrete Controls im Atlas

Die erste Version sollte höchstens folgende sichtbare Primär-Controls besitzen:

- Atlas / Chronicle Umschalter;
- Suche;
- Layer-Filter;
- „Ansicht zurücksetzen“ oder „Auf meine Welt zentrieren“;
- „Zur nächsten Aktion“;
- primäre Resume-/Prep-Aktion;
- Erstellen-Menü;
- Profil-/Account-Menü.

Weitere Aktionen gehören in den Inspector des ausgewählten Nodes. Das verhindert, dass jede mögliche Funktion dauerhaft im Hauptlayout liegt.

---

## 7. Atlas-Informationsarchitektur

### 7.1 Empfohlene Layer

Die Layer sollten nicht alle standardmäßig gleich stark sichtbar sein.

| Layer | Default | Darstellung | Zweck |
|---|---:|---|---|
| Kampagnen | an | große Nodes oder Regionen | primäre Welt-/Projektorientierung |
| Live-/Prep-Sessions | an | Status-Badge am Kampagnen-Node oder verbundener Node | nächster operativer Schritt |
| Primäre Gilde | an | Banner, Aura oder kleiner Gruppierungsmarker | soziale Zugehörigkeit |
| weitere Gilden | aus oder gedimmt | Filter-/Context-Layer | soziale Orientierung ohne Überladung |
| Charaktere | aus oder kompakt | kleine Satelliten/Cluster | Identität und persönliche Relevanz |
| Karten | nicht als Voll-Layer | Preview im Inspector | taktische Assets nicht mit Weltmodell verwechseln |
| Chronicle | aus | Drawer / separater Modus | zeitliche und soziale Updates |

### 7.2 Node-Hierarchie

Die visuelle Hierarchie sollte eindeutig sein:

1. Aktive oder blockierte Session.
2. Primäre Kampagne.
3. Weitere eigene oder geteilte Kampagnen.
4. Primäre Gilde.
5. Charaktere und sekundäre soziale Beziehungen.
6. Dekorative Weltstruktur.

Ein Node darf nicht allein über seinen Standort verständlich sein. Jeder Node braucht mindestens:

- sichtbares Label;
- eindeutigen Typ;
- Status oder Rolle;
- fokussierbaren Button;
- Inspector-Inhalt;
- mindestens eine sinnvolle Aktion.

### 7.3 Gruppierung statt Marker-Teppich

Bei wenigen Objekten kann jeder Node einzeln erscheinen. Bei mehr Objekten braucht der Atlas:

- Cluster;
- Zoom-Schwellen;
- Layer-Filter;
- Suche;
- „Nur relevante Nodes“;
- Gruppierung nach Kampagne, Gilde oder Status.

Die Positionen sollten deterministisch und stabil sein. Ein Nutzer darf nicht bei jedem Reload eine neu angeordnete Welt sehen.

---

## 8. Visuelles Design

### 8.1 Was aus dem Book-Design erhalten bleiben sollte

- dunkler, hochwertiger Außenrahmen;
- Papier-/Pergament-Oberflächen;
- typografische Hierarchie mit Kapitel- und Randnotiz-Charakter;
- Gold als Akzent für aktive oder wichtige Zustände;
- violette/dunkle Shell als Kontrast zum Atlas-Surface;
- dezente Book-Transitions zwischen größeren Routen;
- Materialität in Textur und Rahmen, nicht in jedem einzelnen Control.

### 8.2 Was sich ändern sollte

Der Atlas braucht mehr funktionale Klarheit und weniger dekorative Gleichförmigkeit:

- weniger große Karten mit identischer Oberfläche;
- weniger Text im ersten Viewport;
- stärkerer Kontrast zwischen Surface, Node, Inspector und Command Dock;
- mehr freie Fläche im Zentrum;
- klarere Primär-/Sekundär-Button-Hierarchie;
- weniger visuelles Gewicht für Social-Hinweise;
- weniger parallele Überschriften;
- keine lange Hero-Erklärung über der eigentlichen Arbeitsfläche.

Der Atlas darf sich wie eine hochwertige Karten-/Command-Oberfläche anfühlen, nicht wie eine Buchseite, auf der zufällig ein Diagramm liegt.

### 8.3 Farb- und Statuslogik

Farbe darf niemals das einzige Statussignal sein.

Empfohlene zusätzliche Signale:

- **Live:** Label „LIVE“, Punkt-/Pulse-Symbol nur zurückhaltend, Aktion „Zur Session“;
- **Prep offen:** Text „Vorbereitung offen“, Warnsymbol, konkrete Blocker-Liste;
- **Bereit:** Label „Bereit“, Check-Symbol, Aktion „Öffnen“;
- **Archiviert:** gedimmte Darstellung plus Text „Archiviert“;
- **Privat / Rolle:** sichtbares Rollenlabel wie „DM“ oder „Spieler“;
- **Nicht verfügbar:** erklärende Beschriftung statt bloß deaktiviertem Button.

### 8.4 Node- und Button-Design

Atlas-Nodes sollten technisch native Buttons oder klar fokussierbare interaktive Elemente sein.

Jeder Node braucht Zustände für:

- default;
- hover;
- focus-visible;
- pressed/selected;
- disabled/unavailable;
- loading;
- error.

Empfehlungen:

- Icon plus Label statt Icon-only, zumindest in der Standardansicht;
- ausreichende Touch-Ziele, idealerweise mindestens 44–48 CSS-Pixel;
- sichtbarer Fokusrahmen;
- klare pressed-/selected-Darstellung;
- keine Aktion, die nur über Hover erscheint;
- Tooltips nur ergänzend, nie als einzige Erklärung;
- Primärbutton im Inspector oben oder im Dock, nicht versteckt im Karteninhalt;
- gefährliche Aktionen wie Löschen nicht neben der primären Navigation platzieren;
- Disabled nur dann verwenden, wenn der Zustand wirklich nicht verfügbar ist und ein Grund genannt werden kann.

### 8.5 Motion

Die bestehende Book-Shell darf weiterhin expressive Übergänge nutzen. Innerhalb des Atlas sollte Motion funktional bleiben:

- Node-Auswahl mit kurzer Opacity-/Transform-Änderung;
- Inspector-Wechsel ohne lange Seitenanimation;
- Pan/Zoom nur direkt aus Nutzerinteraktion;
- kein kontinuierlich schwebender oder pulsierender Hintergrund;
- `prefers-reduced-motion` vollständig respektieren;
- keine 3D-Transformation des gesamten Atlas bei jeder Auswahl.

Das reduziert die Risiken, die bereits in der Book-UI-Dokumentation für 3D-Transforms, Flattening und Overflow beschrieben sind.

---

## 9. Technisches Zielbild

### 9.1 Bestehende BookScene als Shell behalten

Die BookScene sollte weiterhin für folgende Verantwortlichkeiten zuständig sein:

- Route-Lifecycle;
- Authentifizierung und geschützte Home-Initialisierung;
- Book-Transition;
- globale Ribbon-/Topbar-Anbindung;
- Route-Wechsel;
- Reduzierte-Bewegung-Zustände;
- Home-Snapshot-Laden.

Sie sollte nicht dauerhaft die komplette Atlas-Interaktionslogik, Layoutlogik und Node-Rendering in einer immer größer werdenden Datei tragen.

### 9.2 Atlas als eigenständige UI-Komponente

Empfohlene Struktur:

```text
vtt/static/js/book-scene.js
  - Route-/Shell-Lifecycle
  - bindet Atlas bei routeKey === "dashboard"

vtt/static/js/world-atlas.js
  - Atlas-State
  - Node- und Layer-Rendering
  - Selection
  - Filter
  - Pan/Zoom
  - Inspector-Bindings
  - List-Fallback

vtt/static/css/world-atlas.css
  - Desktop-/Tablet-/Mobile-Layout
  - Surface, Rail, Inspector, Dock
  - Node-Zustände
  - Atlas-spezifische responsive Regeln

vtt/static/css/book-scene.css
  - Shell, Route-Kamera, Book-Übergänge
  - möglichst wenig neue Atlas-Sonderfälle
```

Falls ein separates JavaScript-Modul zunächst nicht in die bestehende Asset-Struktur passt, sollte die Atlas-Logik zumindest intern in klar getrennte Builder und Binder aufgeteilt werden:

- `buildAtlasHomeMarkup()`;
- `buildAtlasToolbar()`;
- `buildAtlasSurface()`;
- `buildAtlasInspector()`;
- `buildAtlasCommandDock()`;
- `bindAtlasInteractions()`;
- `renderAtlasSelection()`.

### 9.3 DOM/SVG vor Canvas

Für den ersten Atlas wird DOM plus SVG empfohlen:

- Nodes bleiben semantisch und zugänglich;
- SVG kann Verbindungen und dekorative Linien zeichnen;
- Fokus, Labels und Screenreader-Text sind leichter abbildbar;
- responsive Layouts sind einfacher;
- kein unnötiger Canvas-Rendering-/Hit-Test-Komplex.

Canvas oder WebGL ist erst gerechtfertigt, wenn der Atlas tatsächlich sehr viele Nodes, große Zoomstufen oder komplexe Weltgeometrie benötigt. Für die aktuelle Home-Datengröße wäre das wahrscheinlich unnötige Komplexität.

### 9.4 Atlas-Interaktionszustand

Der Client sollte einen klaren, kleinen State besitzen:

```js
{
  view: "atlas",
  selectedNodeId: "campaign:42",
  activeLayers: ["campaigns", "sessions", "primary-guild"],
  query: "",
  statusFilter: "all",
  viewport: {
    scale: 1,
    x: 0,
    y: 0,
  },
  inspectorOpen: true,
}
```

Wichtig:

- Viewport-Position darf nicht die semantische Auswahl ersetzen.
- Auswahl muss auch über eine Liste steuerbar sein.
- `Escape` schließt Inspector oder hebt eine Auswahl auf.
- Tastatur-Navigation muss auf die Node-Liste oder eine definierte Node-Reihenfolge zugreifen können.
- URL-Deep-Links sollten später eine Auswahl wiederherstellbar machen.

---

## 10. API- und Datenempfehlung

### 10.1 MVP: vorhandenen Home-Snapshot erweitern

Für den ersten Atlas kann `/api/dashboard/home` der einzige Initial-Request bleiben. Das vermeidet eine Kaskade aus Einzelrequests beim Home-Load.

Empfohlene zusätzliche Struktur:

```json
{
  "atlas": {
    "version": 1,
    "default_node_id": "campaign:42",
    "nodes": [
      {
        "id": "campaign:42",
        "kind": "campaign",
        "title": "Die Bernsteinfahrt",
        "subtitle": "DM · 4 Mitglieder",
        "status": "prep",
        "x": 0.42,
        "y": 0.36,
        "href": "/campaigns?campaign_id=42&classic=1",
        "permissions": {
          "can_open": true,
          "can_edit": true
        },
        "badges": ["Session-Prep offen"],
        "related_ids": ["session:7", "character:18"]
      }
    ],
    "edges": [
      {
        "from": "campaign:42",
        "to": "session:7",
        "kind": "campaign-session"
      }
    ]
  }
}
```

Die IDs sollten typisiert sein, zum Beispiel `campaign:42` statt einer kollisionsanfälligen nackten Zahl.

### 10.2 Was aus den vorhandenen Daten abgeleitet werden kann

Im MVP können Nodes abgeleitet werden aus:

- `campaigns` → Kampagnen-Nodes;
- `sessions` → Session-Nodes oder Session-Badges;
- `characters` → Charakter-Nodes oder kompakte Satelliten;
- `primary_guild` / `guilds` → Gilden-Kontext;
- `primary_action` → Command-Dock-CTA;
- `priorities` → Inspector-Abschnitt „Als Nächstes“.

Die Positionen können zunächst aus einem stabilen Layout-Algorithmus entstehen. Sie sollten nicht zufällig sein und nicht bei jedem Laden springen.

### 10.3 Karten-Previews erst nach Auswahl laden

Die Home-API serialisiert Kampagnen aktuell ohne vollständige Maps. Das ist für den initialen Atlas sogar hilfreich. Vollständige Kartenbilder sollten nicht für jede Kampagne beim Home-Load geladen werden.

Empfehlung:

1. Initial nur `maps_available` und optional eine kleine Preview-URL liefern.
2. Nach Node-Auswahl den Inspector mit Kartendaten ergänzen.
3. Vollständige Kartenverwaltung weiterhin im Kampagnen-Hub belassen.
4. Für große Hintergrundbilder später echte Thumbnails oder serverseitige Preview-Größen anbieten.

### 10.4 Performance-Hinweis für den bestehenden Endpoint

Bei einer Atlas-Erweiterung sollte geprüft werden:

- sichtbare Kampagnen nur einmal pro Request zu laden und wiederzuverwenden;
- mögliche Lazy-Loads der Campaign-Relationships zu vermeiden;
- `campaign.maps`, `campaign.members` und `campaign.sessions` bei größerer Datenmenge nicht unkontrolliert als N+1-Abfragen zu verwenden;
- Initialdaten von Previewdaten und Detaildaten zu trennen.

Die genaue Optimierung sollte mit Profiling entschieden werden, nicht durch vorsorgliche Komplexität.

### 10.5 Späteres echtes World-Atlas-Modell

Wenn Nutzer Atlas-Positionen, Regionen und Beziehungen selbst pflegen sollen, braucht es ein eigenständiges Modell. `CampaignMap` sollte dafür nicht überladen werden, weil es eine taktische Kartenressource beschreibt.

Möglicher späterer Modellkern:

```text
world_atlas_nodes
  id
  owner_scope / visibility scope
  kind
  title
  description
  x
  y
  parent_id
  icon_key
  color_key
  status
  sort_order
  linked_campaign_id
  linked_map_id
  linked_guild_id
  linked_character_id
  metadata
```

Die konkrete Normalisierung muss noch entschieden werden. Für den MVP ist eine solche Migration nicht notwendig.

---

## 11. Responsive Layout

Der freie Browserraum auf Desktop ist ein Vorteil, aber keine Entschuldigung für ein Layout, das auf Laptop-Höhen oder Mobilgeräten nicht reflowt.

### 11.1 Große Desktops ab etwa 1280–1440 Pixeln

Empfohlene Struktur:

```text
left rail: 200–240 px
atlas:     flexibel, mindestens ca. 560 px
inspector: 300–360 px
topbar/dock: volle Breite
```

Der Atlas sollte den meisten Raum bekommen. Rail und Inspector dürfen nicht zu zwei weiteren Hauptseiten werden.

### 11.2 Kleine Desktops und Tablets

- linker Rail auf schmale Icon-Leiste oder Drawer reduzieren;
- Inspector als ausfahrbares Panel behandeln;
- Atlas bleibt sichtbar und wird nicht unter drei Karten-Spalten begraben;
- Command Dock auf zwei Reihen oder primäre plus „Mehr“-Aktion reduzieren;
- keine Mindestbreite erzwingen, die horizontalen Body-Scroll erzeugt.

### 11.3 Mobile

Auf Mobile sollte der Atlas nicht versuchen, drei Desktop-Spalten zu simulieren.

Empfohlener Aufbau:

1. kompakte Topbar;
2. Atlas-Fläche im Hauptbereich;
3. Filter als horizontaler Scrollbereich oder Bottom Sheet;
4. Inspector als Bottom Sheet;
5. Command Dock mit einer primären Aktion plus „Mehr“;
6. immer erreichbare Listenansicht.

Der Nutzer darf auf Mobile nicht zwingend auf kleine Nodes tippen. Eine Liste mit großen Zeilen und identischen Actions ist Pflicht.

### 11.4 Viewport- und Höhenregeln

Zu vermeiden:

- starre `min-width`-Regeln aus dem Spread-Layout, die den Atlas auf kleinen Viewports überbreit machen;
- gleichzeitig scrollbare Book-Seite, Atlas-Fläche, Inspector und Body-Ebene;
- abgeschnittene Command Docks bei geringer Höhe;
- Hover-Interaktionen als zentrale Navigation.

Der Atlas braucht eine bewusst definierte Scroll-Strategie:

- Desktop: Atlas pan/zoom, Inspector intern scrollbar;
- Mobile: Seite normal scrollen oder Inspector als Sheet;
- Listenansicht: normaler Dokumentfluss;
- nie mehrere konkurrierende Scrollcontainer ohne klaren Fokus.

---

## 12. Accessibility und Bedienbarkeit

### 12.1 Räumliche und lineare Darstellung synchronisieren

Der Atlas ist eine visuelle Darstellung, darf aber nicht die einzige Darstellung sein.

Zusätzlich braucht es:

- eine semantische Node-Liste;
- sichtbare Labels oder zugängliche Namen;
- Status als Text;
- Rollen- und Berechtigungsinformationen als Text;
- dieselben Aktionen in Liste und Inspector;
- eine Möglichkeit, den Atlas zu „überspringen“ und direkt zur Liste oder nächsten Aktion zu gelangen.

### 12.2 Tastatur

Mindestens:

- `Tab` führt durch Topbar, Layer, Nodes, Inspector und Dock;
- `Enter` öffnet einen fokussierten Node;
- `Space` aktiviert Buttons wie erwartet;
- `Escape` schließt Inspector/Drawer;
- Pfeiltasten können innerhalb einer Node-Liste oder eines Clusters navigieren;
- `Home` oder ein dedizierter Button setzt den Fokus auf die erste relevante Aktion.

### 12.3 Screenreader und semantisches HTML

- Native `<button>`-Elemente für Nodes und Controls;
- `aria-pressed` für Layer-/Filter-Schalter;
- `aria-current` für aktive Home-Ansicht;
- `aria-expanded` für Inspector und Drawer;
- keine Information nur über Farbe, Größe oder Position;
- Statusänderungen wie „Live-Session“ oder „Session-Prep fortsetzen“ in verständlichem Text;
- Live-Regionen nur sparsam einsetzen, damit der Atlas nicht permanent meldet.

### 12.4 Kontrast und Fokus

Die Book-Palette darf nicht dazu führen, dass Gold auf Pergament oder violette Schrift auf dunklem Hintergrund zu wenig Kontrast hat. Für jeden Control-Zustand müssen Kontrast, Fokus und Selected-State separat geprüft werden.

### 12.5 Reduced Motion und Low-Power

Zusätzlich zu `prefers-reduced-motion` ist ein reduzierter Atlas-Modus sinnvoll:

- weniger Parallax-/Textur-Effekte;
- kein animierter Hintergrund;
- keine automatische Pan-Bewegung;
- optional direkte Listenansicht.

---

## 13. Zustände, die der Atlas von Anfang an beherrschen muss

### 13.1 Neuer Nutzer ohne Kampagne

Nicht zeigen:

- leere Karte;
- sieben ausgegraute Panels;
- lange Produktbeschreibung ohne Aktion.

Zeigen:

- freundlichen „Deine Welt beginnt hier“-State;
- einen klaren Create-Node;
- eine sekundäre Option „Held anlegen“;
- kurze Erklärung, warum der Atlas später wächst.

### 13.2 Eine Kampagne ohne Karte

Die Kampagne ist sichtbar. Der Inspector zeigt:

- Kampagnenname;
- Rolle;
- Sessionstatus;
- „Noch keine Karte“;
- Button „Kampagnen-Hub öffnen“;
- bei Berechtigung „Karte hochladen“ als Link in den Hub.

Der Atlas darf nicht so tun, als wäre eine taktische Karte vorhanden.

### 13.3 Session mit Prep-Blockern

Der Node zeigt mindestens:

- Sessionname;
- Blockeranzahl;
- lesbare Blocker, zum Beispiel „Session-Karte fehlt“;
- direkte Aktion „Session-Prep fortsetzen“.

### 13.4 Live-Session

Die aktive Session wird automatisch als Default-Fokus gewählt und erhält die höchste Priorität. Die Aktion muss klar sagen, wohin sie führt.

Wichtig: Die bestehende `primary_action`-Semantik darf nicht verloren gehen. Der Atlas verändert die Oberfläche, nicht die Zustandslogik.

### 13.5 Viele Kampagnen

- Gruppierung oder Clustering;
- Suchfeld;
- Statusfilter;
- „Nur meine aktiven“;
- Listenansicht als schnelle Alternative;
- keine unlesbare Markerwolke.

### 13.6 Fehler beim Home-Snapshot

Der Shell-Frame muss sichtbar bleiben. Der Fehlerzustand braucht:

- verständliche Fehlermeldung;
- „Erneut versuchen“;
- gegebenenfalls eine reduzierte lokale Fallback-Darstellung;
- keine scheinbar leere Welt, die wie „keine Daten“ wirkt.

### 13.7 Berechtigungen

Der Atlas muss dieselben Sichtbarkeitsregeln wie der Home-Snapshot anwenden:

- nur sichtbare Kampagnen und Beziehungen ausgeben;
- DM-Aktionen nur für berechtigte Rollen zeigen;
- Spieleransicht nicht mit Edit-Controls überladen;
- private oder archivierte Inhalte klar kennzeichnen;
- kein clientseitiges Verstecken als alleinige Security-Schicht.

---

## 14. Button- und Control-System für den Atlas

### Primäre Aktion

Eine primäre CTA pro Kontext:

- „Zur Live-Session“;
- „Session-Prep fortsetzen“;
- „Kampagnen-Hub öffnen“;
- „Erste Kampagne anlegen“.

Die primäre CTA darf nicht gleichzeitig mit drei gleichgewichteten Goldbuttons konkurrieren.

### Sekundäre Aktionen

- „Charakterarchiv öffnen“;
- „Held anlegen“;
- „Chronicle öffnen“;
- „Karte ansehen“.

### Tertiäre Aktionen

- Filter;
- Layer-Toggle;
- Ansicht zurücksetzen;
- Gilde wechseln;
- Details ein-/ausblenden.

### Zustandsregeln

| Zustand | Darstellung | Verhalten |
|---|---|---|
| Default | klarer, ruhiger Button | aktiviert |
| Hover | leichte Oberflächen-/Rahmenänderung | nur Zusatzfeedback |
| Focus | deutlich sichtbarer Fokusrahmen | Tastatur sichtbar |
| Selected | dauerhaft aktive Fläche oder Marker-Ring | Auswahl bleibt erkennbar |
| Loading | Label/Spinner oder Statuswechsel | keine Doppelaktionen |
| Disabled | reduzierte Darstellung plus Grund | nicht stillschweigend blockieren |
| Error | Fehlermeldung in Kontext | Retry oder alternative Aktion |

Icons sollten Text ergänzen, nicht ersetzen. Ein Icon-only-Button ist nur dann akzeptabel, wenn sein zugänglicher Name und sein Tooltip eindeutig sind.

---

## 15. Implementierungsempfehlung nach Phasen

### Phase 0 – Fachliche Festlegung

**Ziel:** Atlas-Bedeutung festlegen, bevor CSS- und Datenmodell-Komplexität wächst.

Aufgaben:

- Node-Typen und Statuswerte verbindlich definieren;
- entscheiden, ob `x/y` nur visuelle Ableitungen oder persistente Nutzerdaten sind;
- Atlas versus CampaignMap versus Play-Map begrifflich trennen;
- Desktop-, Tablet- und Mobile-Wireframes abnehmen;
- Default-Fokus und Zero-State festlegen;
- Social-/Chat-Grenze bestätigen;
- Feature-Flag oder View-Query für sicheren Rollout bestimmen.

Ergebnis: akzeptiertes UI- und Daten-Schema, noch ohne Produktumbau.

### Phase 1 – Atlas-Frontend mit vorhandenen Daten

**Ziel:** Der Atlas wird als alternative Home-Ansicht sichtbar, ohne sofort ein neues Persistenzmodell einzuführen.

Aufgaben:

- neue Atlas-Surface in der Dashboard-BookScene;
- vorhandenen Home-Snapshot verwenden;
- Kampagnen, Sessions, Gilden und Charaktere als abgeleitete Nodes rendern;
- stabilen Client-seitigen Layout-Algorithmus verwenden;
- Inspector und Command Dock anbinden;
- Atlas-/Chronicle-Umschalter einführen;
- `classic=1` oder äquivalenten Fallback erhalten;
- aktuelle primäre/sekundäre Aktionen weiterverwenden.

Nicht in dieser Phase:

- komplettes neues World-Atlas-Datenmodell;
- vollständige Kartenverwaltung im Home;
- Drag-and-drop-Persistenz;
- Canvas-/WebGL-Rendering;
- Entfernung aller alten Templates.

### Phase 2 – API sauber auf Atlas-Nodes ausrichten

**Ziel:** Der Client erhält eine explizite, testbare Atlas-Struktur statt impliziter Ableitungen aus mehreren Arrays.

Aufgaben:

- `atlas.version`, `default_node_id`, `nodes` und `edges` ergänzen;
- Berechtigungen und verfügbare Aktionen mitliefern;
- `primary_action` und `priorities` mit Atlas-Nodes verknüpfen;
- Home-Endpoint auf wiederverwendete Query-Ergebnisse und kontrollierte Relationships prüfen;
- Snapshot-Contract mit Backend-Tests absichern.

### Phase 3 – Inspector und Karten-Previews

**Ziel:** Der Atlas wird nützlich für Kampagnen- und Kartenorientierung, ohne den Kampagnen-Hub zu duplizieren.

Aufgaben:

- Map-Anzahl und Preview-Metadaten verwenden;
- Preview lazy nach Auswahl laden;
- „Kampagnen-Hub öffnen“ als Detailpfad beibehalten;
- fehlende Karte als lösbaren Zustand darstellen;
- Thumbnail-/Preview-Strategie für große `background_url`-Assets definieren.

### Phase 4 – Chronicle-Drawer und personalisierte Ansichten

**Ziel:** Social und Atlas werden in einem Home zusammengeführt, ohne die Oberfläche zu überladen.

Aufgaben:

- Feed als Drawer oder sekundären Modus ausarbeiten;
- Nutzerpräferenz für letzten Home-Modus optional speichern;
- Default Atlas zunächst beibehalten;
- Gildenwechsel im Inspector/Context-Selector konsistent machen;
- Social Scope sichtbar, aber nicht dominant halten.

### Phase 5 – echtes Atlas-Modell, falls fachlich bestätigt

**Ziel:** Nutzer können Weltstruktur, Regionen, Beziehungen und Positionen selbst pflegen.

Nur umsetzen, wenn das Produkt diese Freiheit wirklich braucht:

- eigenes `world_atlas_nodes`-Modell;
- persistente Node-Positionen;
- Parent-/Region-Beziehungen;
- Sichtbarkeit und Rollenrechte;
- Migration und Versionierung;
- Undo/Reset für Layout-Änderungen.

---

## 16. Konkrete Datei- und Modul-Empfehlungen

### Bestehende Dateien ändern

- [BookScene](/home/admin/projects/roll-drauf-vtt/vtt/static/js/book-scene.js:911): Dashboard-Komposition auf Atlas-View umstellen und Social/Chronicle als sekundären Modus integrieren.
- [Home-Endpoint](/home/admin/projects/roll-drauf-vtt/vtt/endpoints/dashboard_home.py:418): optionalen `atlas`-DTO ergänzen, ohne die bestehende Home-Semantik zu brechen.
- [Dashboard-Template](/home/admin/projects/roll-drauf-vtt/vtt/templates/dashboard.html:1): alte statische Dashboard-Komposition perspektivisch auf Shell/Fallback reduzieren, damit keine doppelte IA bestehen bleibt.
- [Book-Scene-CSS](/home/admin/projects/roll-drauf-vtt/vtt/static/css/book-scene.css:1114): alte Home-Rail-/Feed-Komposition nach Migration nicht weiter als primäres Layout ausbauen.

### Neue Dateien empfehlen

- `vtt/static/js/world-atlas.js`
- `vtt/static/css/world-atlas.css`
- `tests/test_dashboard_atlas_home.py`
- optional: `tests/test_world_atlas_accessibility_contract.py`

### Später, nur bei echtem Bedarf

- `vtt/models/world_atlas_node.py`
- Migration für persistente Atlas-Nodes;
- Preview-/Thumbnail-Endpunkt oder Asset-Transform.

---

## 17. Teststrategie

### Backend-Tests

Neue oder erweiterte Tests sollten prüfen:

- Atlas ist im Home-Snapshot vorhanden;
- Default-Node folgt Live-/Prep-/Campaign-Reihenfolge;
- nur sichtbare Kampagnen erscheinen;
- Rollen und `can_edit` sind korrekt;
- private Daten werden nicht über Nodes oder Edges geleakt;
- Sessions mit fehlender Karte tragen einen verständlichen Blocker;
- leere Nutzerkonten liefern einen validen Zero-State;
- Snapshot bleibt kompatibel, wenn Atlas-Daten fehlen oder Versionen wechseln.

Die vorhandenen Social-/Guild-Tests bleiben relevant. Insbesondere dürfen diese Invarianten nicht verloren gehen:

- Home-Social bleibt read-only;
- Session-Chat bleibt getrennt;
- Gildenwechsel berührt keine Rollenrechte;
- Quick Links und primäre Aktionen bleiben echte Pfade.

### Frontend- und Integrations-Tests

- Dashboard lädt standardmäßig im Atlas-Modus;
- Atlas-/Chronicle-Umschalter funktioniert;
- Node-Auswahl öffnet den richtigen Inspector;
- Auswahl über Liste und Karte bleibt synchron;
- Layer-Filter ändern nur die Darstellung, nicht die Berechtigungen;
- Resume-/Prep-CTA führt zum erwarteten Pfad;
- Classic-/Fallback-Ansicht bleibt erreichbar;
- Deep-Link-Auswahl kann später wiederhergestellt werden;
- Inspector lässt sich per Escape schließen;
- Tastatur erreicht alle primären Aktionen;
- Mobile-Layout erzeugt keinen horizontalen Body-Overflow.

### Visuelle Regressionstests

Mindestens folgende Zustände:

- Desktop mit einer Kampagne;
- Desktop mit vielen Kampagnen;
- Live-Session;
- Prep-Blocker;
- keine Kampagne;
- Kampagne ohne Karte;
- Chronicle-Ansicht;
- Tablet;
- Mobile;
- Reduced Motion;
- hohe Kontraste.

### Performance-Checks

- Home-Initialrequest bleibt möglichst bei einem Snapshot;
- keine Vollbilder für alle Maps beim initialen Render;
- Node-Auswahl darf keine vollständige Atlas-Rekonstruktion erzwingen;
- keine sichtbaren Layoutsprünge beim Öffnen des Inspectors;
- Atlas bleibt auch bei vielen Nodes bedienbar;
- `innerHTML`-Vollrendern nicht bei jedem Pan-/Zoom-Schritt;
- Core Web Vitals und Interaktionslatenz prüfen.

---

## 18. Akzeptanzkriterien für die erste produktive Atlas-Version

Die erste Version sollte erst als abgeschlossen gelten, wenn:

1. Authentifizierte Nutzer landen standardmäßig im Atlas.
2. Der Atlas einen klaren Default-Fokus besitzt.
3. Live-Session oder Prep-Blocker mit maximal einer primären Entscheidung sichtbar sind.
4. Jede bisher wichtige Home-Funktion in höchstens einem zusätzlichen Schritt erreichbar ist.
5. Kampagnen und Sessions räumlich erkennbar, aber zusätzlich als Liste zugänglich sind.
6. Der Chronicle-Feed erreichbar bleibt, aber die Atlas-Orientierung nicht überlagert.
7. Session-Chat nicht in den Home-Social-Snapshot eingebaut wird.
8. Karten ohne vorhandene Map nicht irreführend als fertige taktische Fläche erscheinen.
9. DM-/Spieler-Rechte im Atlas korrekt abgebildet werden.
10. Tastaturbedienung und sichtbarer Fokus funktionieren.
11. Mobile und kleine Laptop-Höhen ohne horizontales Gesamt-Scrolling funktionieren.
12. Reduced Motion die Atlas-Interaktion nicht unbenutzbar macht.
13. `classic=1` beziehungsweise ein gleichwertiger Fallback während des Rollouts funktioniert.
14. Der Home-Snapshot bei Fehlern einen verständlichen Retry-State rendert.
15. Der Atlas nicht nur dekorativ ist, sondern jede zentrale Auswahl mit einer konkreten Aktion verbindet.

---

## 19. Risiken und Gegenmaßnahmen

### Risiko: Der Atlas wird schön, aber unverständlich

**Gegenmaßnahme:** Default-Fokus, sichtbare Labels, Inspector, Listenansicht und klare Status-Badges. Keine reine Punktwolke.

### Risiko: Zu viele Inhalte auf einmal

**Gegenmaßnahme:** Layer, Filter, Cluster, Statuspriorisierung und nur ein primärer Call-to-Action pro Kontext.

### Risiko: Das vorhandene `CampaignMap`-Modell wird semantisch überladen

**Gegenmaßnahme:** Im MVP Kampagnen und Sessions als Atlas-Entitäten verwenden; Karten nur als verknüpfte Previews. Später eigenes Atlas-Modell.

### Risiko: Book-Shell und Atlas konkurrieren visuell

**Gegenmaßnahme:** Book als Shell/Identität, Atlas als flexible Arbeitsfläche. Keine weitere harte Spread-Komposition innerhalb der Atlas-Fläche.

### Risiko: Der Atlas wird zu einem zweiten Play

**Gegenmaßnahme:** Pan/Zoom im Home nur zur Übersicht. Token, Fog, Measure, Draw, Chat und taktische Tools bleiben in Play.

### Risiko: Social-Funktionen verschwinden aus der Wahrnehmung

**Gegenmaßnahme:** Chronicle als sichtbarer Modus bzw. Drawer, Gilden- und Feed-Hinweise als Atlas-Layer/Inspector-Kontext, aber ohne Rückkehr zum Feed-first-Home.

### Risiko: Nutzer wollen eine klassische Liste

**Gegenmaßnahme:** Liste als gleichwertige Accessibility- und Power-User-Ansicht anbieten; nicht als minderwertigen Notbehelf.

### Risiko: Performance durch große Kartengrafiken

**Gegenmaßnahme:** Lazy Previews, Thumbnail-Strategie, keine Vollbilder im Initialload, Inspector erst nach Auswahl.

### Risiko: Zu großer Big-Bang-Umbau

**Gegenmaßnahme:** Atlas zunächst als `view=atlas` neben bestehendem Home testen und schrittweise zum Default machen. Alte Pfade erst nach Akzeptanz entfernen.

---

## 20. Priorisierte Umsetzungsliste

### Must have

- Atlas als neuer Default-Home-Modus;
- Default-Fokus und Next-Action-Logik;
- Kampagnen-/Session-Nodes;
- Inspector mit Öffnen-, Prep- und Resume-Aktionen;
- Atlas-/Chronicle-Umschalter;
- zugängliche Listenalternative;
- Layer-/Statusfilter;
- responsive Desktop-/Mobile-Komposition;
- Berechtigungs- und Social-Chat-Grenzen;
- Fallback-/Classic-Pfad;
- Tests für Snapshot, Auswahl, Rechte und zentrale Flows.

### Should have

- Gilden-Context-Selector;
- Karten-Preview nach Auswahl;
- URL-Deep-Link für ausgewählten Node;
- Cluster bei vielen Nodes;
- Telemetrie für Atlas-Nutzung und nächste Aktionen;
- Low-Power-/Reduced-Effects-Modus;
- persistierte Präferenz für Atlas oder Chronicle, nachdem Atlas als Default validiert ist.

### Could have

- Drag-and-drop für Nutzerpositionen;
- frei definierbare Regionen;
- Beziehungen zwischen Nodes;
- animierte Reise-/Kapitelpfade;
- Weltkartenbilder als eigener Atlas-Layer;
- kollaborative Atlas-Notizen.

### Nicht für den ersten Wurf

- WebGL-Weltkarte;
- komplette Kampagnenverwaltung im Atlas;
- Chat- und Social-Feed als dauerhaftes Overlay;
- globale freie Node-Positionierung ohne validiertes Datenmodell;
- automatische Weltgenerierung ohne klare Informationsarchitektur.

---

## 21. Messbare Produktziele

Nach dem Rollout sollte nicht nur visuell bewertet werden, ob der Atlas „schön“ ist. Wichtiger sind messbare Nutzersignale:

- Zeit vom Home-Load bis zur ersten sinnvollen Aktion;
- Anteil Home → Live-Session;
- Anteil Home → Session-Prep;
- Anteil Home → Kampagnen-Hub;
- Anzahl der Fehlklicks oder Backtracks;
- Zeit bis zur Auswahl einer Kampagne;
- Nutzung der Listenalternative;
- Nutzung von Atlas- und Chronicle-Modus;
- Abbruchrate beim Öffnen des Homes;
- Home-Initial-Ladezeit und Interaktionslatenz;
- Anzahl der Nutzer, die den Default-Fokus ändern oder den Classic-Fallback wählen.

Ein wichtiger qualitativer Test ist die Ein-Satz-Aufgabe:

> „Du hast fünf Sekunden Zeit: Finde heraus, was du als Nächstes tun solltest, und öffne den richtigen Bereich.“

Wenn Nutzer dafür zuerst den Feed lesen, mehrere Karten öffnen oder die Bedeutung der Marker erraten müssen, ist die Atlas-IA noch nicht klar genug.

---

## 22. Schlussfolgerung

Der World Atlas ist als Standard-Home fachlich sinnvoll und wahrscheinlich die stärkere Produktentscheidung als eine weitere Discord-ähnliche Dashboard-Ansicht.

Die richtige Umsetzung ist jedoch kein „Map-Hintergrund mit ein paar Buttons“. Sie ist eine neue Home-Informationsarchitektur:

```text
Atlas = Orientierung + Status + Auswahl
Inspector = Erklärung + Kontext + Details
Command Dock = nächste Aktion
Chronicle = Social-/Feed-Kontext
Campaign Hub = operative Verwaltung
Play = taktischer Tisch
```

Die vorhandene technische Basis reicht für einen ersten Atlas-MVP aus. Der Home-Snapshot liefert bereits viele relevante Daten, und die BookScene bietet einen geeigneten Einstiegspunkt. Die größte fachliche Lücke ist nicht das Frontend, sondern die noch fehlende explizite Bedeutung eines globalen World Atlas gegenüber kampagnenbezogenen taktischen Karten.

Daher lautet die finale Empfehlung:

1. **Atlas als Default-Home beschließen.**
2. **Zunächst eine Atlas Command Surface aus vorhandenen Kampagnen-, Session-, Gilden- und Charakterdaten bauen.**
3. **Chronicle als sekundären Home-Modus erhalten.**
4. **Kampagnen-Hub und Play bewusst getrennt lassen.**
5. **Kartenbilder zunächst als ausgewählte Previews behandeln, nicht als globale Weltkarte.**
6. **Erst nach validiertem Nutzerverhalten ein persistentes `world_atlas_nodes`-Modell einführen.**
7. **Die Umsetzung schrittweise hinter einem Fallback/Feature-Flag ausrollen und anhand von Aufgaben-Erfolg, Zeit bis zur nächsten Aktion und Performance bewerten.**

Damit nutzt das Spiel den verfügbaren Browserraum besser, löst sich sinnvoll vom Discord-Muster und baut die bestehende Book-Identität zu einer produktiveren, räumlich orientierten Home-Erfahrung aus.

---

## 23. Referenzen zu Web-Best-Practices

Die folgenden offiziellen Quellen bilden die allgemeine Grundlage für die Best-Practices-Aussagen zu Bedienung, Accessibility, Performance und Browser-Interaktion:

- [W3C – Web Content Accessibility Guidelines (WCAG) 2.2](https://www.w3.org/TR/WCAG22/)
- [MDN – `<button>` element](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/button)
- [MDN – Keyboard accessible](https://developer.mozilla.org/en-US/docs/Web/Accessibility/Guides/Keyboard-accessible)
- [MDN – Pointer events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events)
- [MDN – Canvas API](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API)
- [MDN – prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)
- [web.dev – Core Web Vitals](https://web.dev/articles/vitals)
- [web.dev – Responsive web design basics](https://web.dev/articles/responsive-web-design-basics)
- [web.dev – Progressive Web App design](https://web.dev/learn/pwa/design-and-ux)
- [Material Design – Buttons](https://m3.material.io/components/buttons/overview)
- [Material Design – Interaction states](https://m3.material.io/foundations/interaction/states)
- [OWASP – HTML5 Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html)
- [OWASP – WebSocket Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html)
