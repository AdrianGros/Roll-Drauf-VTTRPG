#!/bin/bash
# Staging Deployment Script
# Execute: bash deploy_staging.sh

set -e

PROJECT_DIR="/home/admin/projects/roll-drauf-vtt"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================"
echo "VTT Staging Deployment"
echo "======================================${NC}"
echo ""

# Step 1: Activate venv
echo -e "${YELLOW}[1/6] Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi
source venv/bin/activate

# Step 2: Install dependencies
echo -e "${YELLOW}[2/6] Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt 2>/dev/null
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 3: Create instance directory
echo -e "${YELLOW}[3/6] Creating instance directory...${NC}"
mkdir -p instance
export FLASK_ENV=staging
export DATABASE_URL="sqlite:///$PROJECT_DIR/instance/vtt_staging.db"
echo -e "${GREEN}✓ Instance directory ready${NC}"

# Step 4: Initialize database
#
# Robot audit, 2026-08-23 (Arc 0.9): this used to `from vtt_app import
# create_app` -- the real package has been `vtt` for the whole life of
# this repo (confirmed: no vtt_app/ directory has ever existed), so
# this script ImportErrored on line 1 of its own bootstrap, every time,
# for as long as it has existed. It also used to hand-apply three named
# migration files (M17/M18/M19) AFTER db.create_all() already built the
# complete current schema from the live models -- create_all() is not
# incremental, so those ALTER TABLE ADD COLUMN statements (none of them
# idempotent) would fail with "duplicate column" the moment the import
# bug was fixed and this ever got far enough to try them. There is
# nothing left for them to add: create_all() already includes every
# column those three migrations describe, because the models module is
# the one live source of schema, same as dev and prod (see
# migrations/README.md's own admission that this repo has no Alembic
# versions/ directory to replay). Dropped rather than fixed.
echo -e "${YELLOW}[4/6] Initializing base database schema...${NC}"
# Robot audit, 2026-08-23 (Arc 0.9, cont'd): a relative sqlite URI
# ('sqlite:///instance/vtt_staging.db') reliably failed here with
# "unable to open database file" even though the bash cwd is correct --
# confirmed by testing the identical create_app() call with an absolute
# path instead, which works. Using $PROJECT_DIR (already absolute)
# makes this robust regardless of cwd assumptions.
python3 << INIT_SCRIPT
import os
import sys
os.environ['DATABASE_URL'] = 'sqlite:///$PROJECT_DIR/instance/vtt_staging.db'
os.environ['FLASK_ENV'] = 'staging'

try:
    from vtt import create_app
    from vtt.extensions import db

    app = create_app('development')
    app.config['AUTO_CREATE_SCHEMA'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///$PROJECT_DIR/instance/vtt_staging.db'

    with app.app_context():
        db.create_all()
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"✓ Schema created with {len(tables)} tables (current models, complete)")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
INIT_SCRIPT

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Database initialization failed${NC}"
    echo "Possible fix: pip install -r requirements.txt"
    exit 1
fi

# Step 5: Verify database
echo -e "${YELLOW}[5/6] Verifying database...${NC}"
TABLE_COUNT=$(sqlite3 instance/vtt_staging.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
INDEX_COUNT=$(sqlite3 instance/vtt_staging.db "SELECT COUNT(*) FROM sqlite_master WHERE type='index';")
echo -e "${GREEN}✓ Database verified: $TABLE_COUNT tables, $INDEX_COUNT indexes${NC}"

# Summary
echo ""
echo -e "${GREEN}======================================"
echo "✓ STAGING DEPLOYMENT COMPLETE"
echo "======================================${NC}"
echo ""
echo "Database location: instance/vtt_staging.db"
echo "Environment: DATABASE_URL=sqlite:///$PROJECT_DIR/instance/vtt_staging.db"
echo ""
echo "Next steps:"
echo "  1. Start application:"
echo "     export DATABASE_URL='sqlite:///$PROJECT_DIR/instance/vtt_staging.db'"
echo "     source venv/bin/activate"
echo "     flask run"
echo ""
echo "  2. In another terminal, verify the API:"
echo "     curl http://localhost:5000/"
echo ""
echo "  3. Run test suite (optional):"
echo "     pytest tests/test_permissions_m17.py -v"
echo ""
echo -e "${YELLOW}Deployment time: $(date)${NC}"
