# C02 bounded live rework handoff, 2026-11-12

Native session bf179ad0-fa5c-431a-a44a-56d286808cb2, source dab01217b,
integrated/deployed in5ce072109 (later C04 source8848c621c preserves it).
This is authorized Deploy rework inside C02. Do not rewrite C01/C04. Claude quota
hit100%, resets19:10 Europe/Berlin; no API/extrausage or Codex feature fallback.

Medium reproduced LIVE in Firefox390 after normal archive→Open sheet→images:
2×2 avatar decoded initially; real replace POST of different3×3 PNG returns200;
storage download decodes3×3; current #sheetIdentityGrid img still decodes2×2 with
unchanged canonical /api/characters/<ownid>/identity/avatar URL. APIalready sends
private,no-store,max-age=0. canEditIdentity true; body.sheetImages=true, one grid,
one filepicker. Stale decoded media is a confirmed finding, exact cache layer not
proven. In another sequential Firefox probe the next filechooser also did not
open after first upload+async recomposition; investigate filepicker disabled/inert/
placement, do not mistake readonly permission or silently remove controls.

Required bounded fix: refresh all visible identity representations on successful
replacement without persisting transient query/nonce URLs in Character/API fields.
Keep actual server owner guards, local lock/explicit view failclosed, current
book composition, fixed section links, computed SRD values and permissions.
Inspect renderIdentityCard, portraits in sheet-feedback.js, handleIdentityFilePicked,
BookScene composition and picker placement with minimal relevant reads.

Regression must use DIFFERENT valid PNG bytes+dimensions (e.g2×2 then3×3), serial
POST+visible save completion, both Chromium and Firefox including390. Existing
identical-PNG replace checks never proved freshness. Assert actual naturalWidth
in imagegrid+header/sticky images after replace; second real picker works; token
upload/remove and avatarremove; local lock and Reader get no actions. Finish the
live own copy/no-shared-assets/name independence and DM Reader/explicit view path.
Coordinator owns tests/generator/review/integration/deployment/live accounts,
no worker Bash/git/credentials/production. Worker owns existing C02 files only;
request exact extension for any BookScene edit instead of taking shared ownership.

Sanitized evidence in integration tree docs/proofs/characters-presentation-2026-11-12/
firefox-identity-replacement.json and live-findings.md. No remaining test account
or credential should be assumed: coordinator cleans them at delivery end.
