# Discover Ducky originals for FV11/FV16

Status: source inventory complete for nine artist-owned archived threads; original graphics candidates preserved. Permanent sanitized evidence. Input: owner instruction to scan the RD Team Discord, generate no new images and use none of Ducky’s artwork in a generative workflow. This is source discovery, not a public asset release or permission expansion.

## Source and access

The canonical bot repository's `docs/review/2026-09-08_server_instance_cutover.md` identifies RD_TEAM's guild as Speck of Holding. The existing bot connection confirms that guild, and member search identifies Ducky with the Administrative Artist display role. The personal Ducky channel is empty; the art is in nine archived Sternenstaub threads. Read-only bot REST GET requests listed channels, threads and messages. No Discord message was posted, no permissions changed and no bot code/configuration/service/database was changed. No new integration was installed.

Raw messages, signed CDN URLs and original files remain in the protected local archive `/srv/migration/2026-11-24/rd-team-ducky-asset-audit/`, outside Git. Only summary counts and constraints are recorded here. No credential or database URL appears in the evidence.

## Inventory

77 artist-uploaded attachments were found across Visitenkarte, Banner und Co Kg, Dices, Profilbilder, Teamsteckbrief, Vorlagen, QR-Code, Backgrounds and Rollen-Icons. This pass preserved 51 graphics-candidate attachment records as 50 unique original PNG files (44,467,887 attachment bytes, including repeated uploads); the two profile-related groups remain in the private source inventory.

The preserved groups include 17 dice uploads, 12 role-icon uploads, 13 banner uploads, three background uploads, four business-card uploads and one each for templates and QR code. These names describe the source groups, not approved VTT module bindings. In particular, the image-background group supplies no new character-background rules.

The QR-code source explicitly credits **Anne**, although Ducky uploaded it. Its creator credit is retained separately from the uploader. Other candidate creator attribution is based on the owner's identification of Ducky plus her verified upload account; no Creative Commons or unrestricted-public license was invented.

Originals were downloaded from the source attachment URLs without a bot credential being forwarded to the CDN. Declared size limits were enforced, byte hashes recorded and rechecked, duplicates identified by hash, and originals made read-only. There was no decoding, editing, synthesis, generative input, AI image processing or image generation. [Sanitized summary](proofs/ducky-asset-discovery-2026-11-24/summary.json).

## Risks and next boundary

- Medium, handled for this pass: source restrictions and publication scope. The owner's no-generation/no-generative-use rule is mandatory. Preserving private originals does not declare every graphic a public map asset. Actual integration must carry original provenance and source-specific permission context; a rights checkbox or AI label never grants generative rights to this work.
- Low: duplicate uploads and revisions. Keep source records and hashes so variants are selected deliberately; no original was overwritten or repainted.
- Input-dependent: no English Oglan text, new character-background mechanics or additional-system rules were identified in these nine art threads. Those FV02/FV16 inputs remain visible; artwork is not substituted for rules content.
- The previously clipped tree asset is still unidentified; no replacement or reconstruction is claimed.

Next step: bounded FV11/FV16 Apply selects actual original assets and their metadata for relevant existing VTT surfaces, preserving the no-generative-use restriction and truthful creator credits. Continue the remaining technical packets independently. This discovery does not mark FV11 or FV16 complete.
