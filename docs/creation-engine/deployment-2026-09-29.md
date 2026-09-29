# Homebrew backend and Advanced studio release — 29 September 2026

The user requested deployment of the completed work and continued Guided creation.
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

Authoring activation is a separate setting requested from the user because the
previous release explicitly reserved it. Enabling authoring requires M73–M80
applied in order and `CE_AUTHORING`/`CE_LEGACY_ADAPTER`; `CE_RUNTIME` and `CE_SHADOW`
remain off. Before applying migrations, inspect the existing table state and
verify the migration sequence on the disposable production-startup database.
Only explicitly selected activation is performed. No campaign scope cutover or
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
