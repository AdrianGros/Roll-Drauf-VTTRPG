# Creation Engine release — 28 September 2026

The user explicitly requested committing and deploying the current engine work. This
release packages WP5–WP8, the three editor slices and the manual authoring/task-readiness
follow-up on `feat/creation-engine-g1`, together with the reconciled documentation.
Unrelated untracked project documents are excluded.

The [active contract](active-contract.json) remains specification 1.1.4, core wire 1.1.3
and registry A1. Deploying the application is not G1 acceptance or production character
cutover. The live configuration currently has all Creation Engine flags off; the release
preserves that configuration unless the user separately selects activation. Tuesday's
human study, manual-task depth decision and remaining browser/accessibility work stay open.

## Release procedure and verification

1. Retain the running image as `roll-drauf-vtt-app:rollback-20260928` and create a protected
   PostgreSQL backup outside the repository. Record container/image identities and feature
   flags without exposing environment secrets.
2. Verify the 299 source/contract files against the previous candidate manifest. Its
   selected regression and keyboard follow-up establish 199 distinct passing cases;
   WebKit remains unavailable on the host. No application source has changed since those runs.
3. Commit the engine work plus `.dockerignore` exclusions for local environment files.
   Export the committed tree as the Docker build context. This prevents unrelated working
   files, credentials and machine state from entering the release image.
4. Build an image tagged and labelled with the exact Git revision. Run targeted legacy and
   compiler checks inside that image on Python 3.12 using isolated test data, plus factory,
   asset and packaging checks. Before replacing the live app, start the image with its
   default Gunicorn command, production configuration and disposable PostgreSQL/Redis
   containers. Require HTTP liveness and authenticated readiness. Factory tests using
   SQLite do not establish production startup. Reuse existing browser evidence for unchanged code.
5. Use the canonical Compose project `roll-drauf-vtt` and live compose file, with a release
   override selecting the pinned image. Replace only `app` with `--no-deps --no-build`.
   Keep database, Redis, mailserver, network and persistent asset volume intact.
6. Verify HTTPS liveness, database/Redis connectivity, public pages/assets, authentication
   boundaries, feature-flag behavior and running-source/image identity. No CE migration or
   campaign cutover is necessary for a release with all engine flags off.

The exact commands, commit/image identities, protected backup metadata, logs and executed
post-deployment results are retained in the task workspace's `deployment-2026-09-28/`.
This document defines the release boundary; executed results are recorded in its
`release-result.json`, not inferred from this procedure.

## First rollout and dependency correction

The initial `52760c4` image passed 104 selected tests and the factory/package checks,
but failed production startup on 28 September (Berlin time). Its unpinned transitive
SQLAlchemy dependency resolved to 2.1.1; the live `postgresql://` URL selected `psycopg`,
while the installed driver was `psycopg2-binary`. The rollout automatically restored the
previous image and verified HTTPS liveness at 01:53:44 CEST. Database, Redis and mailserver
containers were preserved; no database restore was needed.

The correction pins SQLAlchemy to the previous production image's 2.0.52 and adds an
installed-driver regression check. The retry must also pass the production startup check
above. Retain the failed attempt's evidence separately from the successful retry.

## Rollback

Set the app image to `roll-drauf-vtt-app:rollback-20260928` through the retained rollback
Compose override and recreate only `app` with `--no-deps --no-build`. Keep the existing
runtime configuration and volumes. Verify liveness and dependency readiness afterward.
The database dump is retained for recovery; restoring it is not part of an app-image rollback.

Activating authoring later requires the explicit M73–M78 migrations, exact host/worker
registrations and the checks in the [runtime integration guide](runtime-integration.md).
`db.create_all()` is not a substitute for the append-only triggers.
