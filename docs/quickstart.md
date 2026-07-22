# Quickstart

## 1) Run the app

```bash
pip install -r requirements.txt
python app.py
```

App URL: `http://localhost:5000`

### Production run (containerized)

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

Health checks:

```bash
curl http://localhost/health/live
curl http://localhost/health/ready
curl http://localhost/health/release
curl http://localhost/metrics
```

### Production run (without Docker)

Use Gunicorn (do not run `python app.py` in production):

```bash
gunicorn --worker-class eventlet --workers 1 --bind 0.0.0.0:5000 app:app
```

## 2) Use DAD-M runtime (dad-m-light)

Before milestone work:

1. Open [`dadm-framework/runtime/AI_BIOS.md`](dadm-framework/runtime/AI_BIOS.md)
2. Load [`dadm-framework/runtime/file-registry.yaml`](dadm-framework/runtime/file-registry.yaml)
3. Select runtime profile (`standard` by default for this project)
4. Load route cards by current phase (`discover`, `apply`, `deploy`, `monitor`)

## 3) Auth smoke test (cookie-based)

Register:

```bash
curl -X POST http://localhost:5000/api/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"player1\",\"email\":\"player1@example.com\",\"password\":\"SecurePass123!\"}"
```

Login (store cookies):

```bash
curl -c cookies.txt -X POST http://localhost:5000/api/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"player1\",\"password\":\"SecurePass123!\"}"
```

Check current user with cookie session:

```bash
curl -b cookies.txt http://localhost:5000/api/auth/check
```

## 4) Run tests

```bash
.\.venv\Scripts\python.exe -m pytest -q tests/test_auth.py tests/test_campaigns.py tests/test_characters.py
```

## 5) Ops scripts

```bash
./ops/scripts/migrate_db.ps1
./ops/scripts/backup_db.ps1 -DatabaseUrl $env:DATABASE_URL
./ops/scripts/restore_db.ps1 -DatabaseUrl $env:DATABASE_URL -BackupFile "./backups/<file>.sql.gz"
python ops/monitor/release_gate_evidence.py
python ops/monitor/mvp_rehearsal.py
```
