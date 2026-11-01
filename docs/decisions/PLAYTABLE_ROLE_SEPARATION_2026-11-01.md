# Playtable: getrennte Spieler- und DM-Schichten

Datum: 2026-11-01. Status: **verbindliche Owner-Anforderung; technischer
Apply-Vertrag noch auszuarbeiten**. Aufbewahrung: dauerhaft.

## Input und Geltung

Der Owner präzisiert den [Discover-Audit](../DADM_DISCOVER_VTT_LIVE_WORKTREE_PLAYTABLE_2026-11-01.md):
Spieler und DM benötigen systematisch getrennte Oberflächen und Berechtigungsbereiche.
Eine gemeinsame privilegierte Oberfläche mit ausgeblendeten oder deaktivierten
Elementen genügt nicht. Der Audit bleibt als historischer Befund unverändert.
Dieser Beschluss ersetzt seine Empfehlung, einen isolierten Toolbar-Fix als
ersten fachlichen Abschluss des neuen Rollentrennungsauftrags zu behandeln.

## Aktueller, erneut geprüfter Befund

- `vtt/templates/play.html` und `vtt/static/js/play-ui.js` bilden derzeit eine
  gemeinsame Oberfläche. Rollen entscheiden u. a. über Hidden-/Disabled-Zustände.
- `vtt/play/service.py::get_session_role` liefert für Kampagnen-Owner immer DM.
  Eine zusätzliche eingeschränkte Spielteilnahme desselben Owners fehlt.
- `vtt/play/routes.py::_get_context` und der Socket-Join leiten Rechte und
  Empfangsräume aus der Kampagnenrolle ab. Vorhandene rollenabhängige
  Serialisierung und Aktionsprüfungen schützen tatsächliche Spieler bereits
  an den im Audit geprüften Stellen.
- Insbesondere prüft `play_execute_action` die Session, ihren Modus und den
  Tokenbesitz. Eine gemeinsame Aktionsimplementierung bedeutet deshalb nicht
  automatisch, dass jeder alle Aktionen ausführen kann. Die Behauptung eines
  allgemeinen aktuellen Rechtebypasses wäre durch diese Befunde nicht gedeckt.

## Verbindliches Ziel

| Grenze | Spieler | Spielleitung |
| --- | --- | --- |
| Oberfläche | Eigene Zusammensetzung mit Charakter-/Makroleiste und erlaubten Tischfunktionen; keine gemounteten DM-Werkzeuge oder DM-Handler | Eigene Zusammensetzung mit Szenen-, Wand-, Licht- und Sessionsteuerung |
| Aktionen | Nur für den serverseitig bestätigten Spielerkontext erlaubte Operationen auf berechtigten Ressourcen | Nur für einen ausdrücklich autorisierten DM-Kontext erlaubte Verwaltungsoperationen |
| Daten | Nur die erlaubte Spielerprojektion, einschließlich Chat, Fog, Token- und Szenendaten | Berechtigte DM-Projektion |
| Echtzeit | Nur für diesen Spielerkontext freigegebene Snapshots/Ereignisse | Nur für diesen DM-Kontext freigegebene Snapshots/Ereignisse |

Gemeinsam verwendbare Domänenlogik, etwa Würfeln oder Kartenkoordinaten, ist
zulässig. Darstellung, Autorisierung und Datenauslieferung müssen trotzdem
die jeweilige Grenze einhalten. Getrennte HTML-Dateien allein garantieren das
nicht; ebenso wenig garantieren getrennte URLs ohne serverseitige Prüfung Sicherheit.

Ein DM behält seine Kampagnenberechtigung und darf ausdrücklich wieder als DM
eintreten. **Ein Request aus seinem Spielerkontext erhält dadurch keine
automatischen DM-Rechte.** Ein gewöhnlicher Spieler darf keinen DM-Kontext
erzeugen. Rollenparameter, Button-IDs, URLs und vom Client behaupteter
Tokenbesitz sind keine Autorisierungsquelle.

## Abnahmekriterien

1. Berechtigte Spielleitungen finden die zwei Einstiege im bestehenden UI.
   Spieler erhalten ihren Spielereinstieg ohne ausführbare DM-Einstiege.
2. Spieleransicht und DM-Ansicht werden eigenständig zusammengesetzt. Der
   Spieler-DOM enthält keine DM-Steuerung, auch nicht versteckt oder deaktiviert.
3. Direkte HTTP-Aufrufe und Socket-Ereignisse aus dem Spielerkontext können
   keine DM-Operation auslösen; manipulierte Rollen und fremde Ressourcen-IDs
   ändern daran nichts. Verweigerungen verursachen keine Änderung und keinen
   privilegierten Broadcast.
4. Eine gemeinsame Aktion, beispielsweise Tokenbewegung oder Würfeln, prüft
   den tatsächlichen Akteur, den Kontext und die betroffene Ressource.
   Fremde Tokens oder Charaktere werden nicht durch einen anderen UI-Pfad nutzbar.
5. DM-Geheimnisse erreichen den Spielerkontext weder im Bootstrap noch über
   HTTP-Nachladen, Snapshot, Socket-Broadcast, Resync oder Bogen-Nebenwege.
6. Ein als Spieler eingetretener Kampagnen-Owner erfüllt dieselben Grenzen.
   Auch bei fehlendem, ungültigem oder abgelaufenem Kontext gibt es keinen
   Rückfall auf die weitergehenden Eigentümerrechte.
7. Expliziter Moduswechsel, Reload, Reconnect und parallele Tabs lassen keine
   alten DM-Daten, DM-Empfangsräume oder weiterverwendbaren DM-Aktionskontexte
   im herabgestuften Tisch zurück. Eine andere weiterhin autorisierte
   DM-Verbindung darf den Spieler-Tab nicht mit privilegierten Daten versorgen.
8. Entzogene Mitgliedschaft oder DM-Berechtigung wird auch für bestehende
   Kontexte wirksam. Ein lokaler UI-Wechsel kann sie nicht wiederherstellen.
9. Nach Umsetzung: gezielte Positiv-/Negativtests und angemeldete Live-Prüfung
   beider Rollen sowie der DM-als-Spieler-Reise, mit nachvollziehbarem
   Commit-/Image- und UI-Einstiegsnachweis.

## Scope, Risiken und Übergabe

Die Rollen-/Kontexttrennung umfasst die bestehenden Playtable-Wege, einschließlich
relevanter Legacy-APIs, Socket-Räume und Sheet-to-table-Aktionen. Sie soll weder
die alte G1-Engine zurückbringen noch die globale Konto-/Kampagnenverwaltung
ersetzen. Der vollständige Makroeditor ist ein nachfolgender Funktionsumfang;
seine Spieleroberfläche darf die Rollentrennung nicht umgehen.

**Mittel, noch zu entwerfen:** Lebensdauer und Widerruf der Kontexte,
Tab-/Verbindungsbindung, Verhalten bestehender Clients und geschützter
Legacy-Pfade sowie Datenbereinigung beim Wechsel. Die technische Umsetzung
darf nicht bloß ein neuer Clientparameter mit Fallback auf die Kampagnenrolle sein.

**Mittel, Integrationsgrenze:** Ein gemeinsamer nutzerbezogener Ereignisraum kann
zwei Tabs derselben Person mit unterschiedlichen Tischkontexten erreichen.
Apply muss jeden solchen Auslieferungsweg prüfen; das ist eine Designanforderung,
kein hier neu nachgewiesenes aktuelles Geheimnisleck.

**Nächster Schritt:** Apply für den vollständigen Rollen-/Kontextvertrag auf dem
beschlossenen Eagle-Stand samt geltenden Live-Ergänzungen. Dabei konkrete
Oberflächenmodule, API-/Socket-Verträge, Kontextspeicherung/-entzug und
Rollout/Rollback festlegen. Erst der daraus folgende Deploy-Schritt implementiert
und veröffentlicht die Trennung. Dieser Beschluss allein ist kein fertiger
technischer Deploy-Handoff und keine Behauptung bereits getrennter Live-Views.

Verifikation dieses Beschlusses: bestehende Codepfade erneut gelesen,
Anforderung mit dem Discover-Befund abgeglichen; ausschließlich Dokumentation
und Repo-Regeln geändert. Keine neuen Testläufe oder Änderungen an der
Live-Anwendung für diese Anforderungspräzisierung.
