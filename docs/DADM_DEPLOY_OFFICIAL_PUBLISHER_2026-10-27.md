# Deploy — Roll Drauf Default publisher and global Duckfolk

## Status and input summary
`complete`. The user authorized a dedicated Roll Drauf Default account to own official publications. This deployment creates that durable non-login identity and publishes the reviewed Duckfolk starter to all VTT players.

## Implementation summary and files changed
- `vtt/creation_engine/official_publisher.py` provides a check-only command and an explicit `--publish` path. It validates the Eagle source, typed supplement, 2024 playability, and canonical digests; creates the official author and source; and writes an immutable global revision in one transaction. `--revise` is required to change an existing official source. The account has ordinary Player role, no platform role, no usable password, `is_active=false`, and `account_state=deactivated`.
- `tests/test_official_species_publisher.py` covers the non-login identity, global catalog visibility, idempotency, revision history, and refusal of unplayable content without partial writes.
- The Discover and Apply records are `docs/DADM_DISCOVER_OFFICIAL_PUBLISHER_2026-10-27.md` and `docs/DADM_APPLY_OFFICIAL_PUBLISHER_2026-10-27.md`.

## Verification and proofs
- Targeted tests: **3 passed**, covering the new official publisher and the existing unrelated-contributor global publication flow. Python compile and `git diff --check` passed.
- A check-only run against `vtt/static/examples/duckfolk-2024.json` returned playable 2024 Duckfolk with source digest `sha256:7df489677f204a2778e9ef644e0a498bbe0fdfd4c954afcae1fa67e563abe106` and profile digest `sha256:608675fb37964e6e72c4ea07cd0fdbd39a1c70972087c4c23d9ab0ce9b0cf160`.
- Production image `roll-drauf-vtt-app:official-publisher-20261027-v4` was built from the prior live image and only adds the operator module. The previous Compose override is backed up as `production.duck-species.override.yml.bak-official-publisher-20261027`. The app was recreated and started successfully.
- Production `--publish` created user **28**, official Eagle source `Item.RollDraufDuckfolk2024`, and global Species revision **1**. A repeat returned `created: false` for the same revision.
- A read through the live catalog for unrelated active player 2 returned `homebrew.species.1`, name Duckfolk, scope global, author Roll Drauf Default. The publisher user is not usable for login. HTTP health returned 200; the container was running with zero restarts and no recent errors.

## Acceptance checklist
1. Durable official author, no ordinary login: **met**.
2. Duckfolk global revision attributed to that author and visible to another player: **met**.
3. Repeat idempotent; revision and invalid-input behavior covered: **met**.
4. No migration, new dependency, or campaign/character write: **met**.
5. Production smoke and catalog read: **met**.

## Risks, assumptions, and next step
- **Low:** Official publishing requires an operator with app-host access. This is intentional while the identity is non-login; human users still publish from their own accounts through the editor.
- **Low:** The command covers playable Species. Other official content categories need their own rule adapters and publication contracts.
Next: monitor the catalog in real character creation and use the same check-only then `--publish` workflow for future official Species bundles.

## Artifacts
Repository code, tests, and phase notes are retained. Production image, Compose override backup, immutable DB revision, and command output are operational artifacts.
