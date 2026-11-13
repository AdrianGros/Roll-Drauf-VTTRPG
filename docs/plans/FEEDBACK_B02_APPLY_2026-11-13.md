# B02 – Navigation, Kalender und Tischbereiche

Status: Apply abgeschlossen. Input: S01/S04/S09/S11/S13/S16 und vorhandene Navigation,
Kalender-, Widget- und Rollenkomposition. S14 erhält vor Schemaänderung einen eigenen Anhang.

## Ziel / begrenzte Schnittstellen

- Gemeinsames Zahnrad mit zugänglichem Namen „Einstellungen“ am rechten Rand der Kopfzeile,
  außerhalb der horizontal scrollenden Routen. Derselbe Begriff im Tisch-App-Menü und Dialog.
  Bestehende IDs und gespeicherte Präferenzen bleiben gültig.
  Auf dem bildschirmfüllenden Tisch sitzt das gleiche Zahnrad rechts in dessen vorhandener
  kompakter Statuszeile; die absichtlich ausgeblendete Buch-Kopfzeile wird dafür nicht aufgeklappt.
- Der eigene Kalender startet in `month`; die API liefert weiterhin seine Datumsspanne.
  Die explizite 30-Tage-Ansicht bleibt erreichbar. Leere Monate zeigen alle Tage/Wochentage.
- Links ein unabhängiger Chatbereich, rechts Journal und Werkzeuge. Beide erhalten sichtbare,
  eindeutig benannte Öffnen-/Schließen-Buttons. Auf kleinen Ansichten öffnet nur eine Seitenleiste
  zugleich. Chat-Log, Nachrichteneingabe, Würfelabläufe und Journal-Notizen behalten ihre IDs.
- Der bisherige Session-Reiter entfällt. Hinweise wandern ins Journal; erforderliche
  DM-Sessionsteuerung wird dort als aufklappbarer Bereich montiert, ausschließlich durch den
  vorhandenen DM-Slot. Player mountet weiterhin weder DM-Fragmente noch DM-Handler.
- Seiten/Initiative/Tokens liegen in einem gemeinsamen Karteireiterbereich unten links,
  getrennt von der Aktionsleiste. Drei benannte Reiter, ein Bereich zur Zeit. Es werden die
  vorhandenen Widgets umgehängt, keine zusätzlichen privilegierten Kopien erstellt.
  Die Player-Komposition erhält nur die bereits erlaubten Ansichten und eigenen Aktionen.
  Ehemalige freie Widgetpositionen werden für diese drei ersetzten Fenster nicht mehr angewandt;
  der Tokenplatzierungsdialog behält seine freie Platzierung.
- Der Kartenreiter enthält bereits Kartenebenen; kein zusätzlicher inhaltsgleicher Layer-Reiter.
  Mobile Tisch-Schublade und Desktop verwenden denselben Inhalt. Zurück bleibt als klarer
  App-Menüeinstieg sichtbar; ein separater Chat-/Journalzugang ersetzt den unklaren Hamburger.
- Im Charakterarchiv bezeichnet der Bereich die tatsächlich geteilten Kampagnencharaktere.
  Ohne zugehörige Kampagne erklärt der Leertext den ersten Schritt. Bestehende Ladefehler bleiben sichtbar.

## Kriterien und Risiken

Gear/Dialog sind auf Buch-, Regeln-, Editor- und Tischseiten per Tastatur erreichbar und rechts
sichtbar. DE/EN, Paper/Night und 390px werden geprüft. Monatsraster startet auch leer vollständig.
Chat ist links, Journal rechts, Nachrichten bleiben nach dem Wechsel vorhanden. DM kann die
Sessionsteuerung und alle drei Tischreiter öffnen; Player besitzt keinen DM-Code oder dessen
Kontrollen. Reiter unterstützen Pfeiltasten/Home/End und setzen `aria-selected`/zugehörige Bereiche
konsistent. Aktionsleiste, Zoom und Kartenfläche bleiben nutzbar.

Medium-Risiko Rollenvermischung: kein neuer Datenweg, kein neuer Action-Handler, vorhandene
serverautorisierte Komposition und die Rollenregressionen bleiben verbindlich.
Medium-Risiko unerreichbare bestehende Funktionen: IDs erhalten, alle versetzten Bereiche im
Browser einzeln öffnen; Tests werden auf tatsächliche neue UI-Einstiege angepasst.
Low: gespeicherte Positionen der bewusst ersetzten Fenster gelten nicht mehr; keine Benutzerdaten löschen.

Keine neue Abhängigkeit oder Schemaänderung für diesen Grundumfang. Deploy-Handoff:
implementieren → gezielte Kalender/Nav-/Tisch- und Rollenchecks → Commit/Push → mit tatsächlichem
Live-Image abgleichen → bestehender App-Release → angemeldete Live-Reisen beider Rollen,
kleine Ansicht, Belege mit Commit/Image/Rollback. Danach B03.

Retention: dauerhaft. Der allgemeine Umsetzungsauftrag deckt diesen begrenzten Entwurf.
