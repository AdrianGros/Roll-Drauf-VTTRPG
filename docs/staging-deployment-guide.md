# Staging Deployment Guide
**Date:** 2026-03-27
**Status:** Ready for Execution
**Environment:** Linux/Unix with Python 3.8+

---

## Prerequisites

### System Requirements
- Python 3.8 or higher
- SQLite3 (or PostgreSQL for production-like staging)
- Git
- 2GB minimum disk space
- Virtual environment support

### Required Tools
```bash
python3 --version          # Verify Python 3.8+
sqlite3 --version         # Verify SQLite3
git --version             # Verify Git
```

---

## Step 1: Install Dependencies

### Create Virtual Environment
```bash
cd /home/admin/projects/roll-drauf-vtt
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install Requirements
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Verify Installation
```bash
python3 -c "import flask; print(f'Flask {flask.__version__} installed')"
python3 -c "import sqlalchemy; print(f'SQLAlchemy {sqlalchemy.__version__} installed')"
```

---

## Step 2: Initialize Database

### Create Instance Directory
```bash
mkdir -p instance
```

### Initialize Database Schema
```bash
# Set environment for staging
export FLASK_ENV=staging
export DATABASE_URL='sqlite:///instance/vtt_staging.db'

# Run Flask initialization script
python3 << 'INIT_SCRIPT'
import os
from vtt_app import create_app
from vtt_app.extensions import db

app = create_app('development')
app.config['AUTO_CREATE_SCHEMA'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/vtt_staging.db'

with app.app_context():
    print("Creating base database schema...")
    db.create_all()
    print("✓ Schema created successfully")

    # Verify
    inspector = db.inspect(db.engine)
    print(f"✓ Created {len(inspector.get_table_names())} tables")
INIT_SCRIPT
```

---

## Step 3: Apply Migrations

### Execute M17 Migration
```bash
# Add platform roles and audit logging
sqlite3 instance/vtt_staging.db < migrations/migration_m17_add_platform_roles_and_audit.sql

if [ $? -eq 0 ]; then
    echo "✓ M17 migration applied successfully"
else
    echo "✗ M17 migration failed - check database"
    exit 1
fi
```

### Execute M18 Migration
```bash
# Add user lifecycle fields
sqlite3 instance/vtt_staging.db < migrations/migration_m18_user_lifecycle.sql

if [ $? -eq 0 ]; then
    echo "✓ M18 migration applied successfully"
else
    echo "✗ M18 migration failed - check database"
    exit 1
fi
```

### Execute M19 Migration
```bash
# Add asset storage model
sqlite3 instance/vtt_staging.db < migrations/migration_m19_add_assets.sql

if [ $? -eq 0 ]; then
    echo "✓ M19 migration applied successfully"
else
    echo "✗ M19 migration failed - check database"
    exit 1
fi
```

### Complete Migration Script
```bash
#!/bin/bash
set -e

cd /home/admin/projects/roll-drauf-vtt

echo "Executing M17 migration..."
sqlite3 instance/vtt_staging.db < migrations/migration_m17_add_platform_roles_and_audit.sql

echo "Executing M18 migration..."
sqlite3 instance/vtt_staging.db < migrations/migration_m18_user_lifecycle.sql

echo "Executing M19 migration..."
sqlite3 instance/vtt_staging.db < migrations/migration_m19_add_assets.sql

echo "✓ All migrations applied successfully"
sqlite3 instance/vtt_staging.db "SELECT COUNT(*) as table_count FROM sqlite_master WHERE type='table';"
```

---

## Step 4: Run Test Suite

### Prerequisites for Testing
```bash
pip install pytest pytest-flask pytest-cov
```

### Run Permission Tests
```bash
pytest tests/test_permissions_m17.py -v --tb=short
```

**Expected Result:** 37/37 tests PASS

### Run All Tests
```bash
pytest tests/ -v --tb=short -x  # Stop on first failure
```

### Generate Coverage Report
```bash
pytest tests/ --cov=vtt_app --cov-report=html
# Coverage report in htmlcov/index.html
```

---

## Step 5: Start Application

### Development Mode
```bash
# Set environment
export FLASK_ENV=staging
export DATABASE_URL='sqlite:///instance/vtt_staging.db'
export FLASK_APP='vtt_app:create_app'

# Run development server
flask run --host=0.0.0.0 --port=5000

# Or use gunicorn for production-like behavior
gunicorn -w 4 -b 0.0.0.0:5000 "vtt_app:create_app()"
```

### Verify Application Started
```bash
# In another terminal
curl http://localhost:5000/
# Should redirect to /login.html
```

---

## Step 6: Verify Deployment

### Health Check Endpoints
```bash
# Check API health
curl http://localhost:5000/api/health

# Check ops metrics
curl http://localhost:5000/ops/metrics
```

### Verify Blueprints Registered
```bash
curl http://localhost:5000/api/assets/campaigns
# Should return: {"error": "Unauthorized"} (no JWT token)
```

### Verify Database Connectivity
```bash
sqlite3 instance/vtt_staging.db ".tables"
# Should list all 24 tables

sqlite3 instance/vtt_staging.db ".schema users"
# Should show users table with all M17 fields
```

### Verify Security Headers
```bash
curl -I http://localhost:5000/
# Should include:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
```

---

## Step 7: Integration Testing

### Test Asset Upload Endpoint
```bash
# Get auth token (requires valid user in DB)
TOKEN=$(curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  | jq -r '.access_token')

# Test asset upload
curl -X POST http://localhost:5000/api/assets/campaigns/1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_image.png" \
  -F "asset_type=map"

# Should return 201 with asset_id
```

### Test Quota Enforcement
```bash
# Attempt upload that exceeds quota
curl -X POST http://localhost:5000/api/assets/campaigns/1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@huge_file.zip" \
  -F "asset_type=map"

# Should return 400 if quota exceeded
```

### Test Admin Dashboard
```bash
# Get admin metrics
curl http://localhost:5000/api/admin/dashboard/metrics \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Should return: {"requests_total": N, "by_status": {...}, ...}
```

---

## Step 8: Load Testing (Optional)

### Using Apache Bench
```bash
# Install
sudo apt-get install apache2-utils

# Test asset upload endpoint with 100 concurrent requests
ab -n 1000 -c 100 http://localhost:5000/api/assets/campaigns/1/list
```

### Using wrk
```bash
# Install wrk (https://github.com/wg/wrk)
wrk -t4 -c100 -d30s http://localhost:5000/api/health
```

---

## Step 9: Database Verification

### Check Migration Status
```bash
sqlite3 instance/vtt_staging.db << 'SQL'
-- Verify M17 tables
SELECT COUNT(*) as audit_log_count FROM audit_logs;
SELECT COUNT(DISTINCT platform_role) as roles FROM users;

-- Verify M18 tables
SELECT COUNT(DISTINCT account_state) as states FROM users;

-- Verify M19 tables
SELECT COUNT(*) as asset_count FROM assets;
SELECT COUNT(*) as indexes FROM sqlite_master WHERE type='index';
SQL
```

### Check Audit Trail
```bash
sqlite3 instance/vtt_staging.db \
  "SELECT action, COUNT(*) FROM audit_logs GROUP BY action;"
```

---

## Complete Deployment Script

```bash
#!/bin/bash
set -e

PROJECT_DIR="/home/admin/projects/roll-drauf-vtt"
cd "$PROJECT_DIR"

echo "======================================"
echo "VTT Staging Deployment"
echo "======================================"

# Step 1: Activate venv
echo "[1/9] Setting up virtual environment..."
python3 -m venv venv || true
source venv/bin/activate

# Step 2: Install dependencies
echo "[2/9] Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Step 3: Initialize database
echo "[3/9] Initializing database..."
mkdir -p instance
export FLASK_ENV=staging
export DATABASE_URL='sqlite:///instance/vtt_staging.db'
python3 -c "
from vtt_app import create_app
from vtt_app.extensions import db
app = create_app('development')
app.config['AUTO_CREATE_SCHEMA'] = True
with app.app_context():
    db.create_all()
    print(f'Created schema with {len(db.inspect(db.engine).get_table_names())} tables')
"

# Step 4: Apply migrations
echo "[4/9] Applying M17 migration..."
sqlite3 instance/vtt_staging.db < migrations/migration_m17_add_platform_roles_and_audit.sql

echo "[5/9] Applying M18 migration..."
sqlite3 instance/vtt_staging.db < migrations/migration_m18_user_lifecycle.sql

echo "[6/9] Applying M19 migration..."
sqlite3 instance/vtt_staging.db < migrations/migration_m19_add_assets.sql

# Step 5: Run tests
echo "[7/9] Running test suite..."
pytest tests/test_permissions_m17.py -q --tb=line || echo "⚠ Some tests failed - review output"

# Step 6: Verify database
echo "[8/9] Verifying database..."
TABLE_COUNT=$(sqlite3 instance/vtt_staging.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
echo "✓ Database has $TABLE_COUNT tables"

# Step 7: Display next steps
echo "[9/9] Deployment ready"
echo ""
echo "======================================"
echo "✓ STAGING DEPLOYMENT COMPLETE"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Start application:"
echo "   export DATABASE_URL='sqlite:///instance/vtt_staging.db'"
echo "   flask run"
echo ""
echo "2. Verify endpoints:"
echo "   curl http://localhost:5000/"
echo ""
echo "3. Run integration tests:"
echo "   pytest tests/ -v"
echo ""
```

---

## Troubleshooting

### Migration Fails: "no such table"
**Issue:** Base tables don't exist
**Solution:** Run Step 2 (Initialize Database Schema) before migrations

### Test Failures: "ModuleNotFoundError"
**Issue:** Dependencies not installed
**Solution:** Run `pip install -r requirements.txt`

### Database Locked
**Issue:** Another process using database
**Solution:** Kill other Flask processes: `pkill -f flask`

### Port Already in Use
**Issue:** Port 5000 already in use
**Solution:** Use different port: `flask run --port 5001`

---

## Rollback Procedure

### If Migrations Fail
```bash
# Restore from backup
cp instance/vtt_staging.db.backup instance/vtt_staging.db

# Or start fresh
rm instance/vtt_staging.db
# Re-run from Step 3
```

### If Tests Fail
```bash
# Review test output
pytest tests/ -v --tb=long

# Fix code issues, then re-run tests
pytest tests/ -v --tb=short
```

---

## Monitoring

### View Application Logs
```bash
# Development server logs
# (printed to console)

# Production logs (if using gunicorn)
gunicorn -w 4 "vtt_app:create_app()" --log-level debug
```

### Monitor Database Size
```bash
du -h instance/vtt_staging.db
```

### Check Active Connections
```bash
lsof | grep vtt_staging.db
```

---

## Post-Deployment Verification Checklist

- [ ] Virtual environment activated
- [ ] Dependencies installed (pip list | grep -E "flask|sqlalchemy|pytest")
- [ ] Database created (ls -lh instance/vtt_staging.db)
- [ ] M17 migration applied
- [ ] M18 migration applied
- [ ] M19 migration applied
- [ ] All tests passing (pytest tests/test_permissions_m17.py -v)
- [ ] Application starts without errors (flask run)
- [ ] Health endpoint responds (curl http://localhost:5000/)
- [ ] Security headers present (curl -I http://localhost:5000/)
- [ ] Database has 24+ tables (sqlite3 instance/vtt_staging.db ".tables")
- [ ] Audit logs exist (sqlite3 instance/vtt_staging.db "SELECT COUNT(*) FROM audit_logs;")

---

## Support & Documentation

- **Application Logs:** `instance/logs/` (if configured)
- **Database Queries:** Use sqlite3 CLI: `sqlite3 instance/vtt_staging.db`
- **API Documentation:** See `MILESTONES_M19_M36.md`
- **Operating Playbook:** See `docs/OPERATING_PLAYBOOK_v2.md`
- **Troubleshooting:** See `docs/SECURITY_COMPLIANCE_M34.md`

---

**Status:** Ready for Staging Deployment ✅

Execute the complete deployment script above to deploy to staging in ~5 minutes.

