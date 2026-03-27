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
echo -e "${YELLOW}[1/8] Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi
source venv/bin/activate

# Step 2: Install dependencies
echo -e "${YELLOW}[2/8] Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt 2>/dev/null
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 3: Create instance directory
echo -e "${YELLOW}[3/8] Creating instance directory...${NC}"
mkdir -p instance
export FLASK_ENV=staging
export DATABASE_URL='sqlite:///instance/vtt_staging.db'
echo -e "${GREEN}✓ Instance directory ready${NC}"

# Step 4: Initialize database
echo -e "${YELLOW}[4/8] Initializing base database schema...${NC}"
python3 << 'INIT_SCRIPT'
import os
import sys
os.environ['DATABASE_URL'] = 'sqlite:///instance/vtt_staging.db'
os.environ['FLASK_ENV'] = 'staging'

try:
    from vtt_app import create_app
    from vtt_app.extensions import db

    app = create_app('development')
    app.config['AUTO_CREATE_SCHEMA'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/vtt_staging.db'

    with app.app_context():
        db.create_all()
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"✓ Schema created with {len(tables)} base tables")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
INIT_SCRIPT

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Database initialization failed${NC}"
    echo "Possible fix: pip install -r requirements.txt"
    exit 1
fi

# Step 5: Apply migrations
echo -e "${YELLOW}[5/8] Applying M17 migration...${NC}"
if sqlite3 instance/vtt_staging.db < migrations/migration_m17_add_platform_roles_and_audit.sql 2>/dev/null; then
    echo -e "${GREEN}✓ M17 migration applied${NC}"
else
    echo -e "${RED}✗ M17 migration failed${NC}"
    exit 1
fi

echo -e "${YELLOW}[6/8] Applying M18 migration...${NC}"
if sqlite3 instance/vtt_staging.db < migrations/migration_m18_user_lifecycle.sql 2>/dev/null; then
    echo -e "${GREEN}✓ M18 migration applied${NC}"
else
    echo -e "${RED}✗ M18 migration failed${NC}"
    exit 1
fi

echo -e "${YELLOW}[7/8] Applying M19 migration...${NC}"
if sqlite3 instance/vtt_staging.db < migrations/migration_m19_add_assets.sql 2>/dev/null; then
    echo -e "${GREEN}✓ M19 migration applied${NC}"
else
    echo -e "${RED}✗ M19 migration failed${NC}"
    exit 1
fi

# Step 6: Verify database
echo -e "${YELLOW}[8/8] Verifying database...${NC}"
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
echo "Environment: DATABASE_URL=sqlite:///instance/vtt_staging.db"
echo ""
echo "Next steps:"
echo "  1. Start application:"
echo "     export DATABASE_URL='sqlite:///instance/vtt_staging.db'"
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
