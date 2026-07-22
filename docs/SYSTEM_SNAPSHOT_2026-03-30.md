# System Snapshot

Date: 2026-03-30
Repository: `roll-drauf-vtt`
Branch: `main`
Snapshot basis: repository contents, registered Flask blueprints, deployment files, test inventory, and current uncommitted worktree state.

## Executive Summary

`roll-drauf-vtt` is a Flask-based virtual tabletop application for Discord-centric tabletop play. It has moved beyond MVP-only concerns and already contains:

- modular backend domains for auth, campaigns, characters, community, play/session handling, ops, assets, admin, and profile administration
- persistent SQLAlchemy models for users, campaigns, sessions, combat, moderation, assets, and theming
- real-time multiplayer behavior via Flask-SocketIO
- cookie-based JWT auth with CSRF protection and MFA flows
- production-oriented deployment assets for PostgreSQL, Redis, Gunicorn, Docker Compose, Nginx, TLS enablement, health endpoints, metrics, release-gate evidence, and operational runbooks
- a broad automated test inventory, although the current checkout is not fully verification-ready in the present shell environment

The system is best described as an in-progress product platform rather than a single-feature prototype.

## Product Purpose

The repo presents itself as a D&D virtual tabletop for Discord sessions. The current product surface supports:

- player authentication and account management
- campaign creation, membership, invite acceptance, and ownership
- character creation and sheet management
- live session bootstrap and scene handling
- token placement and updates
- combat state and initiative flows
- community chat, moderation reports, and moderation actions
- asset upload, library access, preview, rollback, and admin asset workflows
- admin dashboards and registration key issuance

## Runtime and Stack

Observed stack from `requirements.txt`, `Dockerfile`, and app registration:

- Python 3.12 container runtime in `Dockerfile`
- Flask 2.3
- Flask-SocketIO with Eventlet
- Flask-SQLAlchemy and Flask-Migrate
- Flask-JWT-Extended using cookies
- Flask-Limiter
- Flask-CORS
- PostgreSQL in production
- Redis for rate limiting and Socket.IO message queue
- Gunicorn as the production process server

## System Architecture

The app uses a Flask application factory in `vtt_app/__init__.py` and registers multiple blueprints behind API prefixes.

### Registered backend domains

- `auth`: registration, login, refresh, MFA, and in-progress Discord OAuth login
- `campaigns`: campaign CRUD, invites, maps, sessions, tokens, and combat
- `characters`: character CRUD plus spells, equipment, inventory, and sheet views
- `community`: chat, reporting, sanctions, moderation, and voice configuration
- `play`: session bootstrap, ready-check, scene stack, transitions, and action execution
- `ops`: liveness, readiness, release-gate, and Prometheus-style metrics
- `assets`: campaign asset listing, upload, preview, download, versions, rollback, active-layer
- `admin_dashboard`: admin search, audit logs, storage metrics
- `profile_m18` and `admin_m18`: deletion/deactivation lifecycle and admin restore flows
- `registration_keys`: batch key generation, export, stats, revoke, unrestrict, PDF export
- `theme`: theme settings and admin customization
- `admin_assets`: asset ingestion and batch processing workflows

### Realtime layer

Two Socket.IO handler sets exist:

- the main handler set in `vtt_app/socket_handlers.py`
- an optional session-oriented handler set in `vtt_app/socket_handlers_sessions.py`, enabled by `USE_SESSION_SOCKET_V2`

Realtime events cover session joins/leaves, moderation rooms, map changes, token create/update/delete or movement, combat state, chat activity, initiative changes, and sheet/play actions.

## Data Model Surface

The repo contains 32 model files under `vtt_app/models`. Major domains include:

- identity and access: `user`, `role`, `session`, `mfa_backup_code`, `registration_key`, `discord_identity_link`
- campaign and play state: `campaign`, `campaign_member`, `game_session`, `session_state`, `session_snapshot`, `session_token`, `session_map_layer`, `session_initiative`
- map and token systems: `campaign_map`, `token_state`, `scene_stack`, `scene_layer`
- character systems: `character`, `spell`, `equipment`, `inventory_item`
- community and governance: `chat_message`, `moderation_report`, `moderation_action`, `audit_log`
- combat systems: `combat_encounter`, `combat_event`
- assets and presentation: `asset`, `app_theme_settings`

This indicates the system already has a durable domain model for a multiplayer game platform with moderation and operational controls.

## Security and Identity Posture

Current implemented posture from code and config:

- cookie-based JWT access and refresh tokens
- CSRF protection enabled by default for cookie auth
- bcrypt password hashing
- TOTP MFA support
- security headers set globally in the app factory
- rate limiting on mutating auth and gameplay-adjacent endpoints
- production config validation that rejects missing secrets and SQLite in production

### In-progress identity expansion

The current worktree also includes in-progress Discord OAuth and bot-backed authorization work:

- new Discord-related config keys in `.env.example` and `.env.vtt.roll-drauf.de.example`
- `vtt_app/auth/discord_oauth.py`
- `vtt_app/models/discord_identity_link.py`
- added auth routes for `/api/auth/discord/start`, `/api/auth/discord/status`, and `/api/auth/discord/callback`

This work is not yet documented as fully verified production behavior.

## Operations and Production Readiness

The repo already includes a meaningful operations baseline:

- `docker-compose.vtt.roll-drauf.de.yml` for app, Postgres, Redis, and Nginx
- `deploy_vtt_roll-drauf-de.sh` for deployment bootstrap
- `ops/nginx/*` for reverse proxy configuration
- `ops/runbooks/backup_restore.md`
- `ops/runbooks/failover.md`
- `ops/monitor/release_gate_evidence.py`
- `ops/monitor/mvp_rehearsal.py`
- `/health/live`, `/health/ready`, `/health/release`, and `/metrics`

The release gate evaluates dependency health, uptime, request/error budgets, latency, socket resync/conflict thresholds, and required runbook presence.

## Testing Status

The repo contains 25 top-level test files under `tests/`, covering:

- auth
- campaigns
- characters
- maps
- play bootstrap and permissions
- ready checks
- session state and state machine
- tokens and combat realtime
- moderation and reports
- asset library
- ops endpoints

### Snapshot verification result

Verification attempted on 2026-03-30:

- `venv/bin/pytest -q` failed during collection because pytest traversed into `ops/certbot/conf/accounts` and hit a filesystem permission error
- `venv/bin/pytest -q tests` failed during collection because the current shell invocation lacked a working test import setup and at least one dependency import (`requests`) was unavailable in the active virtual environment

Result:

- test inventory is present and substantial
- this checkout is not currently in a clean, reproducible, one-command verification state from the present terminal environment

## Documentation Already Present

The repo already contains a large amount of process and milestone documentation, including:

- README and quickstart material
- milestone plans and outputs across multiple workstreams
- DAD-M runtime material under `dadm-framework/`
- deployment guides
- implementation summaries
- operational runbooks

The documentation volume is high, but it is uneven in audience and formality. Some files reflect planning snapshots, some are execution artifacts, and some are design intent rather than current runtime truth.

## Current Gaps Visible From This Snapshot

- no single authoritative system overview that ties together product scope, architecture, operations, security, and current status in one place
- no enterprise-style project brief or charter document
- no consolidated functional specification or product requirements document
- no formal software architecture document with diagram set, interfaces, data flows, and decision record index
- no visible traceability matrix linking business goals, requirements, tests, deployments, and incidents
- no single production readiness or go-live packet beyond the existing ops scripts and runbooks
- no formal incident response plan document for application/security incidents
- no explicit data classification, privacy, retention, or access-control policy packet in the repo root docs

## Practical Interpretation

As of 2026-03-30, the project has:

- enough code and ops structure to be treated as a real product system
- enough surface area that enterprise documentation is now justified
- enough ongoing change in auth and UI that documentation should clearly distinguish approved baseline from active branch work

This snapshot should be paired with an enterprise documentation baseline that defines which documents become authoritative going forward.
