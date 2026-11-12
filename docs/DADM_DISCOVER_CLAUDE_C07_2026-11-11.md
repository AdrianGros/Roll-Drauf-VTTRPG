# Discover C07 – private Gespräche und Mitgliederaktionen

Status: Faktenaufnahme abgeschlossen, Apply erforderlich. Profil standard,
dauerhaft. R05/R06 verlangen interne dauerhafte DM↔Player- und Player↔Player-
Gespräche sowie kompakte Charakter/Chat/Entfernen-Aktionen im Kampagnenhub.

`models/chat_message.py` ist ausschließlich sessiongebunden: campaign_id und
game_session_id sind Pflicht, Sichtbarkeit public/gm_only/blind/self mit
Moderationsmetadaten. Socket- und Bootstrap-Projektionen in play/routes.py und
socket_handlers.py schützen diese bestehenden Tischinhalte. Das ist kein
privater, sessionunabhängiger Zweierverlauf. Neue private Inhalte dürfen nicht
über diese Tabelle, Sessionräume oder deren Broadcasts verteilt werden.

Das Hub-Ledger in book-scene.js kennt aktive/eingeladene Mitglieder und eine
Entfernen-Aktion entsprechend bestehender Moderationspolitik. Die bereits
berechtigte Hub-Antwort enthält Kampagnencharaktere/Sessionzuweisungen; persönliche
ungeteilte Figuren sind nicht allein anhand eines fremden Nutzers aufzulisten.
CampaignMember hat Status active/invited/pending/left/kicked und eine eindeutige
Campaign/User-Beziehung. Owner wird an bestehenden Mitgliedschaftsseams separat
berücksichtigt; ein bloßer globaler DM-/Admin-Titel begründet kein privates Gespräch.

Medium: neue Teilnehmer-/Objektberechtigung, insbesondere Kampagnenowner als
unbeteiligter Dritter; Medium: Widerruf/Leave/Kick während geöffneter Ansicht;
Medium: dauerhafte Nachrichten dürfen weder Tischhistorie noch Suche/Logs/Events
versehentlich erreichen; Medium: Retry darf bei unbekanntem Ergebnis nicht doppelt
senden. Low: kompakte Bedienung und klare Trennung von normalem Sessionchat.

Nächster Schritt Apply: eigener begrenzter Zweiergesprächsvertrag mit aktuellem
Kampagnenzugriff, unveränderlichen Teilnehmern, Text-/Verlaufsgrenzen, persistentem
Retry und sichtbarem Widerruf. Kein externer Nachrichtenversand, keine Discord-
oder E-Mail-Anbindung und keine Erweiterung bestehender Moderationsrechte.
