# Homebrew backend and Advanced studio release — 29 September 2026

The user requested deployment of the completed work and continued Guided creation,
then clarified that the entire hosted VTT is the shared development environment,
not a production service. Authoring and private tests are enabled for this use.
This release packages the verified race/navigation/import changes, executable
class/race/spell backend and Advanced studio. Guided development follows from the
same committed baseline and is kept out of this initial release image.

## Discovery and Apply boundary

The live app is `roll-drauf-vtt-app:ce-ece5f29edcbc`, with Creation Engine flags
unset/off. Database, Redis, mailserver, network and asset volume are running under
the canonical Compose project `roll-drauf-vtt`. The Advanced candidate records 192
passing checks, with the opt-in WebKit case skipped. Unrelated untracked research
documents are excluded from the release commit and build context.

Deploy from an exact Git archive, retain the running image and a protected
PostgreSQL backup, and verify production startup against disposable dependencies.
Replace only `app` using `--no-deps --no-build`; verify image/source identity,
HTTPS liveness, authenticated readiness and the unchanged operational release
gate. Restore the previous app image on rollout failure. An app rollback retains
any append-only CE records; it never restores the database automatically.

The user's environment clarification resolves the earlier activation question.
Enabling authoring requires M73–M80
applied in order and `CE_AUTHORING`/`CE_LEGACY_ADAPTER`; `CE_RUNTIME` and `CE_SHADOW`
remain off. Before applying migrations, inspect the existing table state and
verify the migration sequence on the disposable production-startup database.
Authoring activation was selected for the shared development service. No campaign scope cutover or
human acceptance is implied.

## Risks and treatment

- Medium startup risk: pinned image, existing dependency versions, in-image
  checks and default Gunicorn startup before replacement.
- Medium persistence risk on activation: protected backup, additive migration
  inspection/rehearsal, transaction and lock/statement timeouts, trigger checks.
- Medium release identity risk: commit only the scoped files, build from the Git
  archive, verify source hashes in the image and retain unrelated working files.
- Medium service disruption risk: app-only replacement, automatic app rollback,
  continuous HTTPS observation and dependency/service identity checks.

## Deploy/Monitor handoff

Retain executed logs, backup metadata, exact image/commit identities, migration
and activation decisions, smoke results, rollback override and release gate in
the task workspace's `deployment-2026-09-29/`. These are observed results, not
inferences from this procedure. Continue Guided composition after the first
deployment; its design, changes and verification get their own bounded record.

## Executed Advanced deployment

Commit `fb12e6e64bc387a84bd5a485a76286d0e922b534` is deployed as
`roll-drauf-vtt-app:ce-fb12e6e64bc3`. The default Gunicorn startup, all eight
migrations and authenticated authoring/private catalogue were rehearsed against
disposable PostgreSQL/Redis. M73–M80 then installed 43 CE tables and 58 trigger
events on the shared development database in one transaction.

The image passed 109 selected server tests. The initial test selection also
included browser fixtures, which could not start because the app image contains
no Chromium binary; the matching source passed all 26 selected browser/host
checks on the development host. No browser dependency was added to the app image.

The app-only rollout matched all 287 retained runtime/package source hashes and
passed HTTPS, database, Redis and access-boundary checks. Authoring and the host
adapter are enabled; runtime/shadow/campaign cutover remain off. Database, Redis,
mailserver and asset mounts were preserved. A 322-second observation completed
200 synthetic HTTPS liveness checks with zero restarts and the unchanged release
gate reporting ready. This is deployment evidence, not human testing or a load
study. The exact result and rollback metadata are retained in
`deployment-2026-09-29/release-result.json` in the task workspace.
