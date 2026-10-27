# Apply — official Roll Drauf publication owner

## Status and design summary
`complete`. Create one durable user named **Roll Drauf Default** with a reserved, non-deliverable email, ordinary Player role, an unrecoverable random password hash, `is_active=false`, and `account_state=deactivated`. This row is provenance only; it receives no browser login, OAuth link, JWT, platform role, or campaign permission. Official content is published by a server-side operator command that validates the bundle and writes the source and immutable global revision in one database transaction.

## Solution boundary and contracts
- A small repository-owned command accepts a JSON bundle `{source, supplement}` and an alphanumeric Eagle document ID. It defaults to check-only; `--publish` is required for a write. `--revise` explicitly permits replacing an official source under the same ID and incrementing its source revision. A repeated identical publication returns the existing revision.
- The command creates or verifies the exact official user identity. A collision on username or reserved email with incompatible properties is an error. The account stays non-login before and after a publication.
- The command applies `check_json`/`check_document`, the Species converter with the current skill catalog, and canonical source/profile digests. It refuses non-playable or malformed content before any commit. The source uses personal scope owned by the official user; the publication uses `scope_kind=global`, `scope_id=0`, an author-specific lineage, and `published_by` equal to that user.
- Publication and account/source creation commit together. An exception rolls back the whole operation. No live campaign, character, or human account is changed.
- First use: publish `vtt/static/examples/duckfolk-2024.json` as `Item.RollDraufDuckfolk2024`. Future official Species can use the same command and their own bundles; other Eagle document types remain outside this command until playable adapters exist.

## Acceptance criteria
1. The official user is visibly named Roll Drauf Default and cannot authenticate through the normal account predicate.
2. Duckfolk is a global revision attributed to that user and visible in the Species catalog to an unrelated player.
3. Re-running the same command is idempotent; a changed source requires explicit `--revise` and creates an immutable next revision.
4. Invalid or unplayable bundles leave no partial writes. No migration or new dependency is required.
5. Production smoke confirms the account state, publication provenance, catalog visibility, and unchanged app health.

## Risks and tradeoffs
The official account cannot use the web editor. This is deliberate: server-side publication is auditable through operator access and avoids a shared password. Human contributors keep their normal personal publishing path. The command covers official playable Species only, matching the adapter currently available.

## Deploy handoff and artifacts
Implement the command and targeted tests, then run a check-only pass against the Duckfolk asset. After verification, run one production publication through the command, confirm catalog visibility through the app's code path, and record the resulting user and revision IDs. Retain this design in the repository.
