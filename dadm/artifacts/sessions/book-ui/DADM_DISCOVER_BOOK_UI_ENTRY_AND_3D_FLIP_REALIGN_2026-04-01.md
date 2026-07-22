# DAD-M Discover: Entry Scale and 3D Page Flip Realign

Date: 2026-04-01
Status: completed

## Ausgangslage

- der Login nutzt bereits das Buchobjekt, wirkt aber als Entry noch zu grossraeumig
- nach dem Laden der spaeteren Seiten bleibt ein unnnoetiger dunkler Restlook des Buchkoerpers wahrnehmbar
- spaetere Ansichten haben bereits Bewegung, aber noch keinen konsequenten 3D-Folio-Load ueber alle Buchfamilien

## Kernbefunde

- der `dashboard`-Zustand setzt Cover/Pages/Back bisher nur auf `opacity: 0.1`, was den dunklen Filtereindruck beguenstigt
- der Login-Sprung in die erste Folio-Seite ist noch eher ein allgemeiner Zoom als ein symbolisches Verschwinden des Readers in den Seiten
- direkte Route-Ladungen ausserhalb des Logins brauchen ebenfalls einen klareren 3D-Folio-Auftakt
