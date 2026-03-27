# roll drauf vtt

A D&D virtual tabletop for Discord sessions, built with Flask and managed with DAD-M.

## Setup

1. Install Python 3.14+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the app:
   ```bash
   python app.py
   ```
4. Open `http://localhost:5000`

## Production Baseline (M8)

- Runtime:
  - Run behind reverse proxy and TLS.
  - Use container image (`Dockerfile`) and process manager (`gunicorn`).
- Data:
  - Production requires PostgreSQL + Redis.
  - Configure `DATABASE_URL`, `REDIS_URL`, `RATELIMIT_STORAGE_URL`.
- Ops endpoints:
  - `GET /health/live`
  - `GET /health/ready`
  - `GET /health/release` (go/no-go gate)
  - `GET /metrics`
- Runbooks:
  - [backup_restore.md](ops/runbooks/backup_restore.md)
  - [failover.md](ops/runbooks/failover.md)
- CI/CD:
  - `.github/workflows/ci.yml`
  - `.github/workflows/deploy.yml`

## Tech Stack

- Backend: Python + Flask
- Realtime: Socket.IO
- Database: SQLite (MVP), later PostgreSQL

## Ops Evidence Commands

- `python ops/monitor/release_gate_evidence.py`
- `python ops/monitor/mvp_rehearsal.py`

## DAD-M Working Method (dad-m-light aligned)

This project now follows the updated DAD-M runtime model from `dadm-framework/runtime`.

1. Start from [`dadm-framework/runtime/AI_BIOS.md`](dadm-framework/runtime/AI_BIOS.md)
2. Load [`dadm-framework/runtime/file-registry.yaml`](dadm-framework/runtime/file-registry.yaml)
3. Select profile: `fast`, `development`, `standard`, or `strict`
4. Load only required route cards (`bootstrap`, `discover`, `apply`, `deploy`, `monitor`, `human_decision`)
5. Escalate to full framework/governance docs only when needed

Default project profile: `standard`.

## Status

- M1: Dice Rolling API complete
- M2: Map Display and Token Placement complete
- M3: Auth v2 (cookie + CSRF) complete
- M4: Campaign and session management in progress
