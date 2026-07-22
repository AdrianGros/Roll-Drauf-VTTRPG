# DAD-M Research: Entry Scale and 3D Page Flip Realign

Date: 2026-04-01
Status: completed

## Quelle

- Snippflow: `CSS Book Effect with 3D Animation`
  - https://snippflow.com/snippet/css-book-effect-with-3d-animation/

## Relevante Erkenntnisse

- die staerkste visuelle Idee des Snippets ist nicht das exakte Styling, sondern die Staffelung mehrerer Blattlagen
- der Effekt lebt von `perspective`, `transform-style: preserve-3d`, klaren `rotateY()`-Bewegungen und leicht versetzten Seitenebenen
- fuer unser VTT ist die sinnvolle Uebersetzung: dieselben Prinzipien auf performante `transform`-/`opacity`-Animationen im vorhandenen Buchsystem anwenden, statt ein neues Demo-Book nachzubauen

## Uebersetzung in unser Zielbild

- Login bleibt als kleines Entry-Ritual
- nach erfolgreichem Login verschwindet die Entry-Flaeche symbolisch in die Buchseiten
- spaetere Seiten erscheinen als Folio-Ankunft mit 3D-Page-Flip statt als normales Interface-Fade
