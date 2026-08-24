# Beyond20, öffentlicher Einstieg und Playtable — Emergency Research

**Datum:** 2026-08-24
**Scope:** Repository-Zustand, anonymer Live-Zustand von `https://vtt.roll-drauf.de`,
Beyond20-Integrationsvertrag, Browser-Extension-Grenzen und Discord-OAuth2.
**Sicherheitsgrenze:** Diese Recherche hat keinen Anwendungscode, keine Deployment-Datei
und keine Live-Daten verändert. Live-Prüfungen waren ausschließlich lesende HTTP-Aufrufe.

## Kurzfazit

Das aktuelle Problem ist kein einzelner „DC-Block“ vor dem Webserver:

1. `https://vtt.roll-drauf.de/` antwortet öffentlich mit `302 -> /login.html`.
2. `/login.html` ist öffentlich ladbar, aber der Live-Status meldet `{"enabled":true}`
   für Discord-Login. Die Seite erklärt ausdrücklich, dass der Zugang ausschließlich
   über Discord, Servermitgliedschaft und Bot-Freischaltung läuft.
3. `/dashboard` und `/play` liefern zwar ihr HTML an anonyme Besucher aus, die
   JavaScript-Runtime fordert danach Authentifizierung; der Play-Bootstrap und die
   Mutations-APIs sind JWT-geschützt. Damit kann ein Beyond20-Reviewer ohne Discord-
   Freischaltung keine echte Sitzung inspizieren.
4. Im Playtable ist die direkte Karten-Dateiauswahl im Template zunächst mit dem
   `hidden`-Attribut versehen (`#mapUploadRow`). Die Runtime schaltet diese Zeile beim
   Operator-Bootstrap über `uploadRow.hidden = !operator || this.readOnly` sichtbar;
   der Audit-Verdacht, die Runtime entferne `hidden` nicht, war falsch. Die reproduzierte
   Blockade lag im still deaktivierten Karten-Auswahl-Empty-State.
5. `#layerAddBtn` wird deaktiviert, wenn keine noch nicht verwendete CampaignMap
   verfügbar ist. Das ist fachlich korrekt, aber die Oberfläche erklärt den Zustand
   nicht und sieht deshalb wie ein toter Knopf aus. Die Screenshot-Symptomatik passt
   genau zu diesem Fall: `+ Seite hinzufügen...` plus deaktiviertes `Hinzufügen`.

Die empfohlene Richtung ist deshalb: eine ausdrücklich öffentliche, schreibgeschützte
Showcase-/Demo-Fläche für Review und Beyond20 bereitstellen, den privaten Spieltisch
privat lassen und anschließend die Playtable-Empty-States sowie den direkten Upload als
echte, getestete Operator-Aktionen reparieren. Discord-OAuth darf dafür nicht abgeschaltet
und kein Testkonto im Frontend veröffentlicht werden.

## Repository-Befunde

### Authentifizierung und öffentlicher Einstieg

| Befund | Beleg im Repository | Konsequenz |
|---|---|---|
| Root leitete vor dem Emergency-Patch immer auf Login um | [`vtt/__init__.py`](../vtt/__init__.py#L286-L289) | Es gab keine öffentliche Produkt-Landingpage unter `/`. |
| Discord ist der kanonische Einstieg | [`vtt/templates/login.html`](../vtt/templates/login.html#L376-L404) | Besucher ohne Discord-Freischaltung bleiben vor dem Produkt. |
| Signup/Register werden bei aktiviertem Discord-Gate zurückgeleitet | [`vtt/__init__.py`](../vtt/__init__.py#L296-L300), [`tests/test_discord_only_login_guild_access_gate.py`](../tests/test_discord_only_login_guild_access_gate.py#L75-L98) | Die Sperre ist absichtlich und getestet, nicht nur ein kaputter Link. |
| Dashboard und Play erzwingen Auth im Browser | [`vtt/static/js/auth.js`](../vtt/static/js/auth.js#L53-L70), [`vtt/static/js/play-ui.js`](../vtt/static/js/play-ui.js#L69-L76) | HTML-Auslieferung allein ist keine öffentliche Vorschau. |
| Play-Bootstrap ist JWT-geschützt | [`vtt/play/routes.py`](../vtt/play/routes.py#L75-L81) | Eine echte Session kann nicht anonym über Beyond20 getestet werden. |

### Beyond20-Bridge

Die vorhandene Bridge ist konzeptionell nahe am offiziellen Vertrag:

- [`vtt/static/js/beyond20-bridge.js`](../vtt/static/js/beyond20-bridge.js#L1-L22)
  beschreibt eine reine Adapter-Schicht und hält den Serververtrag systemneutral.
- Sie hört auf `Beyond20_RenderedRoll`, `Beyond20_UpdateHP`,
  `Beyond20_UpdateConditions` und `Beyond20_UpdateCombat`, nimmt bei einem Array-
  Detail dessen erstes Element und queued Ereignisse, bis `rolldrauf:table-ready`
  eintrifft ([Bridge](../vtt/static/js/beyond20-bridge.js#L31-L59),
  [Bridge events](../vtt/static/js/beyond20-bridge.js#L188-L278)).
- Der Browser-Robot testet den vollständigen Weg DOM-Event → Normalisierung → Socket
  → Sanitization/Persistenz → Broadcast → Reload ([`tools/robots/flows.py`](../tools/robots/flows.py#L365-L372)).

Das offene Integrationsrisiko ist nicht primär die Normalisierung, sondern Erreichbarkeit:
`window.RollDraufTable.sendExternalRoll` verwirft bei Read-only, fehlendem Socket oder
fehlender Authentifizierung ([`vtt/static/js/play-ui.js`](../vtt/static/js/play-ui.js#L269-L278)).
Eine öffentliche Showcase-Seite darf deshalb nicht einfach den privaten `/play`-Bootstrap
umgehen; sie braucht einen getrennten, absichtlich read-only Daten- und Interaktionsvertrag.

### Playtable-Layer-Controls

Der aktuelle Layer-Block enthält zwei unterschiedliche Produktaktionen:

- direkte Dateiaktion: `#mapUploadRow` mit `#btnMapUpload`, im HTML zunächst versteckt
  und beim DM-Bootstrap sichtbar geschaltet
  ([`vtt/templates/play.html`](../vtt/templates/play.html#L1263-L1280),
  [`vtt/static/js/play-ui.js`](../vtt/static/js/play-ui.js#L1834-L1835));
- Auswahl einer bereits vorhandenen Kampagnenkarte: `#layerAddSelect` + `#layerAddBtn`.

Die Runtime bindet die Dateiauswahl und den Multipart-Upload
([`vtt/static/js/play-ui.js`](../vtt/static/js/play-ui.js#L1176-L1210)) und macht die
Zeile für Operatoren sichtbar. Für die zweite Aktion filtert sie bereits verwendete Maps heraus und setzt
`addBtn.disabled = available.length === 0`
([`vtt/static/js/play-ui.js`](../vtt/static/js/play-ui.js#L1669-L1685)). Der Fehler ist
damit ein UX-/Reachability-Fehler: „keine weitere vorhandene Karte“ wird als stilles
deaktiviertes UI dargestellt, obwohl „neue Karte aus Datei anlegen“ die passende nächste
Aktion wäre.

### Landing-/Placeholder-Befund

Die Produktoberfläche enthält weiterhin bewusst deaktivierte Zukunftsaktionen, zum Beispiel
„Session-Prep folgt im Hub“, „Map Workspace folgt“ und „Import / Export folgt hier“ in
[`vtt/templates/campaigns.html`](../vtt/templates/campaigns.html#L1394-L1398),
[`vtt/templates/campaigns.html`](../vtt/templates/campaigns.html#L2618-L2624) und
[`vtt/templates/campaigns.html`](../vtt/templates/campaigns.html#L3452-L3458). Diese sind
für einen internen Produkt-Hub als Roadmap-Hinweis vertretbar, für eine öffentliche
Review-Landingpage aber irreführend: Ein Button ohne aktuelle Nachbedingung sollte kein
Button sein. Auf der öffentlichen Fläche müssen nur fertige Aktionen erscheinen; geplante
Funktionen gehören in eine klar als Roadmap markierte, nicht klickbare Darstellung.

## Primärquellen und daraus abgeleitete Regeln

### Beyond20

- Die [offizielle Beyond20-API](https://beyond20.here-for-more.info/api) dokumentiert,
  dass Custom-Domain-VTTs den Content-Support der Extension laden können (API, Abschnitt
  `activate-icon`), und dass eine Custom-Website die DOM-Events
  `Beyond20_RenderedRoll`, `Beyond20_UpdateHP`, `Beyond20_UpdateConditions` und
  `Beyond20_UpdateCombat` erhält. Sie dokumentiert außerdem, dass `event.detail` ein
  Array mit dem Request als erstem Element ist und für Rückkanal-Nachrichten
  `Beyond20_SendMessage` ebenfalls ein Array erwartet.
- Die [offizielle Beyond20-Installationsseite](https://beyond20.here-for-more.info/install)
  verweist für Review/Entwicklung auf das [öffentliche Quellrepository](https://github.com/kakaroto/Beyond20).
  Für eine Upstream-PR sind daher ein stabiler HTTPS-Origin, ein reproduzierbarer
  Integrationspfad und ein klarer Testfall sinnvoller als ein temporärer Login-Bypass.
- Das [Beyond20-README](https://github.com/kakaroto/Beyond20/blob/master/README.md)
  bestätigt den Extension-Charakter und den Entwicklungsweg über das Quellverzeichnis.
  Die Roll-Drauf-Bridge sollte deshalb weiterhin eine kleine Website-Seite/Adapter-Schicht
  bleiben und keine Beyond20-Interna nachbauen.

### Browser-Extension-Grenzen

- [MDN: Content scripts](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Content_scripts)
  verlangt Host-Permissions für die Origin, bevor ein Content Script Seiteninhalte lesen
  oder verändern kann. Das erklärt, warum ein Upstream-PR oder die Nutzerkonfiguration
  den Domain-Origin kennen muss.
- MDN beschreibt außerdem, dass Content Scripts in einer isolierten Welt laufen und
  JavaScript-Globals der Seite nicht automatisch sehen. Die robuste gemeinsame Naht für
  diese Integration ist daher der dokumentierte DOM-CustomEvent-Vertrag, nicht ein
  Zugriff auf `window`-Interna.
- [MDN: `scripting.ExecutionWorld`](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/scripting/ExecutionWorld)
  warnt, dass `MAIN`-World-Code von der Seite gelesen und beeinflusst werden kann. Die
  Bridge darf keine Secrets oder privilegierten Tokens in das DOM legen; sie verarbeitet
  nur bereits vom Extension-API geliefertes Roll-/Status-Payload.

### Discord OAuth2

- [Discord OAuth2](https://docs.discord.com/developers/topics/oauth2) beschreibt den
  Authorization-Code-Flow: registrierte `redirect_uri`, Rückgabe von `code` und `state`,
  serverseitiger Token-Austausch sowie Validierung von `state` gegen CSRF/Session.
- Das Repository folgt diesem Grundmuster in [`vtt/auth/routes.py`](../vtt/auth/routes.py#L383-L409)
  und [`vtt/auth/discord_oauth.py`](../vtt/auth/discord_oauth.py#L27-L75). Die öffentlich
  sichtbare Vorschau darf diesen Identitäts- und Bot-Verifikationspfad nicht als
  „Review-Abkürzung“ umgehen.

## Implementierungsoptionen

| Option | Nutzen | Sicherheits-/Produkttrade-off | Bewertung |
|---|---|---|---|
| A. Öffentliche Showcase-Seite `/showcase` oder `/demo` | Beyond20-Team kann Landing, Buch-Look, erklärten Roll-Event-Test und Playtable-Mock ohne Konto sehen | Kein echter privater Sessionzustand; braucht strikt read-only Fixtures | **Empfohlen als Sofortmaßnahme** |
| B. Öffentliche, signierte Read-only-Demo-Session | Zeigt realere Layer-/Roll-Flows und kann einen echten Bridge-Smoke ausführen | Token-/Replay-/Rate-Limit-/Datenisolationsrisiko; darf keine Produktionskampagne öffnen | Sinnvoll als Phase 2 |
| C. Upstream-Beyond20-PR für `vtt.roll-drauf.de` als Custom-Origin | Nutzer müssen nicht manuell eine Custom-Domain pflegen; beste langfristige Integration | PR/Review/Release-Zyklus liegt teilweise außerhalb dieses Repos; Origin muss stabil bleiben | Parallel vorbereiten |
| D. Discord-Gate für Reviewer abschalten | Sofort scheinbar sichtbar | Bricht die gewollte Zugangspolitik, kann private Daten/Mutationen exponieren und invalidiert die bestehenden Auth-Tests | **Nicht empfehlen** |
| E. Screenshots/Video-only | Keine neue Angriffsfläche und schnell publizierbar | Kein echter Beyond20-/Button-/Upload-Beweis | Nur als Fallback/Evidence-Anhang |

## Empfohlene Notfall-Patch-Kette

### Patch 0 — Zugang und Beweise

1. Eine öffentliche `/showcase`-Route mit statischen oder serverseitig fest verdrahteten
   Demo-Fixtures anlegen; keine Kampagnen-, Nutzer-, Socket- oder Asset-Mutations-API
   aufrufen.
2. Einen klaren Link „Mit Discord anmelden“ zum echten Login lassen und daneben erklären,
   was öffentlich sichtbar ist und was eine Freischaltung benötigt.
3. Einen reproduzierbaren Beyond20-Testpfad dokumentieren: Origin, Browser, Extension-
   Berechtigung/Custom-Domain, erwartete DOM-Events und sichtbare Erfolgsanzeige.

### Patch 1 — Playtable Layer als echte DM-Aktion

1. Nach erfolgreichem Bootstrap `#mapUploadRow.hidden` für Operatoren entfernen; für
   Read-only-/Spielerrollen bleibt die Aktion verborgen oder wird mit erklärtem Status
   deaktiviert. Diese Runtime-Schaltung ist bereits vorhanden und bleibt durch den
   Regressionstest geschützt.
2. Einen expliziten Statusknoten neben der Auswahl ergänzen. Bei null verfügbaren Maps:
   „Keine weiteren Kampagnenkarten. Nutze ‚Datei hinzufügen‘ für eine neue Seite.“
3. `Hinzufügen` nur für eine valide Auswahl aktivieren; `aria-describedby`, Tooltip und
   disabled-State müssen den Grund benennen. Die direkte Dateiaktion ist die primäre CTA,
   nicht der deaktivierte Fallback.
4. Upload-Fehler, Dateityp, Größe, Asset-Erzeugung, CampaignMap-Erzeugung, Layer-Anlage
   und Aktivierung jeweils in einer sichtbaren Statuszeile abbilden.

### Patch 2 — Landingpage ohne tote Versprechen

1. Öffentliche Review-Seite auf eine kurze Zahl echter Aktionen reduzieren: Demo ansehen,
   Beyond20-Anleitung öffnen, Discord-Login öffnen.
2. Zukunftsfunktionen als Text/Roadmap-Karten statt deaktivierte Buttons rendern.
3. Einen Button-Crawler-Vertrag für jeden sichtbaren Button eintragen: Klick oder Tastatur-
   aktivierung muss Navigation, Dialog, File Chooser oder `aria-live`-Nachbedingung liefern.

### Patch 3 — Beyond20-PR und Sicherheits-Härtung

1. Upstream-PR mit stabilem Origin, exakten Event-Namen/Payloads, Browser-Matrix und
   Rückwärtskompatibilität der Bridge vorbereiten.
2. Im Repository Contract-Tests für alle vier eingehenden offiziellen Events behalten und
   um `Beyond20_Loaded`-Erkennung sowie „Bridge nicht geladen / Socket nicht bereit“-
   Diagnose ergänzen.
3. Keine Discord-Cookies, JWTs, Shared Secrets oder Bot-URLs in Demo-DOM, CustomEvents,
   Screenshots oder öffentlichen Logs ausgeben.

### Patch 4 — Release-Gates

1. Red-first: den Test zuerst gegen eine leere CampaignMap-Liste und einen Operator-
   Bootstrap ausführen; er muss den aktuell fehlenden sichtbaren Upload/Empty-State rot
   melden.
2. Disposable-Stack: DM kann Datei auswählen, Upload durchführen, Seite anlegen,
   aktivieren, umbenennen und neu laden; Player sieht die Aktion nicht und erhält keine
   Mutation.
3. Öffentlicher Smoke: `/`, `/showcase`, `/login.html`, `/health/live`; keine unerwarteten
   5xx, keine Platzhalter-Buttons auf der Showcase-Seite, keine privaten Daten.
4. Beyond20-Smoke: offizielles Eventformat in Chromium und Firefox gegen eine explizite
   Demo-/Testseite; danach erst Upstream-PR und Deployment.

## Status dieser Recherche

- Worktree zum Recherchezeitpunkt: Die uncommittete Änderung in
  [`tools/robots/flows.py`](../tools/robots/flows.py) war bereits vorhanden; die Recherche
  selbst hat keine Anwendungscode- oder Deployment-Datei verändert.
- Live read-only am 2026-08-24 geprüft: `/` `302`, `/login.html` `200`, `/dashboard`
  `200` HTML, `/play` `200` HTML, `/health/live` `200`, Discord-Status `{"enabled":true}`.
- Die vorhandenen Beyond20-Server-/Browser-Smokes sind ein guter Integrationskern, beweisen
  aber keinen anonymen Reviewer-Zugang. Dafür braucht es Option A oder B.

## Emergency-Patch-Ergebnis

Die empfohlene Sofortvariante ist jetzt umgesetzt:

- `/`, `/showcase` und `/showcase.html` liefern eine öffentliche, statische Landingpage
  ohne Kampagnen-, Socket- oder Asset-Daten.
- `/beyond20.html` dokumentiert die vier eingehenden DOM-Ereignisse und verlinkt die
  offizielle API-Dokumentation; der private Spieltisch bleibt hinter Discord/Auth.
- Der Playtable zeigt bei null verfügbaren Karten einen sichtbaren Empty-State, hält die
  vorhandene Kartenaktion nur bei gültiger Auswahl aktiv und benennt den Datei-Upload als
  nächsten Schritt.
- Der rote Browser-Smoke wurde vor der Änderung mit genau diesem fehlenden Empty-State
  reproduziert und danach mit 0 Findings bestanden. Der vollständige Disposable-Flow für
  Dice, Map-/Token-Datei-Dialog und Beyond20 bestand ebenfalls mit 0 Findings.
