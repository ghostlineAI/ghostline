#!/bin/bash
# Restore data using COPY commands to avoid pg_dump version issues

set -euo pipefail

echo "🔄 Data Restore Script for GhostLine (Using COPY)"
echo "================================================"
echo "⚠️  DANGER: This script can DESTROY ALL DATA!"
echo ""

# Safety check 1: Require explicit database name
if [ "$#" -ne 1 ]; then
    echo "❌ ERROR: Must provide target database name as argument"
    echo "Usage: $0 <database-name>"
    echo "Example: $0 ghostline"
    exit 1
fi

TARGET_DB="$1"

# Safety check 2: Prevent running on production
if [[ "$TARGET_DB" == *"prod"* ]] || [[ "$TARGET_DB" == *"production"* ]]; then
    echo "❌ ERROR: Cannot run on production databases!"
    echo "This script detected 'prod' or 'production' in the database name."
    exit 1
fi

# Safety check 3: Require explicit confirmation
echo "⚠️  WARNING: This will PERMANENTLY DELETE all data in database: $TARGET_DB"
echo "⚠️  This action cannot be undone!"
echo ""
echo "Type the database name '$TARGET_DB' to confirm:"
read -r CONFIRM_DB

if [ "$CONFIRM_DB" != "$TARGET_DB" ]; then
    echo "❌ Confirmation failed. Exiting."
    exit 1
fi

# Safety check 4: Second confirmation
echo ""
echo "⚠️  FINAL WARNING: About to DELETE ALL DATA in $TARGET_DB"
echo "Type 'DESTROY-ALL-DATA' to proceed:"
read -r FINAL_CONFIRM

if [ "$FINAL_CONFIRM" != "DESTROY-ALL-DATA" ]; then
    echo "❌ Final confirmation failed. Exiting."
    exit 1
fi

# Connection details
SOURCE_PORT="5434"
TARGET_PORT="5433"
DB_NAME="ghostline"
ADMIN_USER="ghostlineadmin"
ADMIN_PASS="YO,_9~5]Vp}vrNGl"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}⚠️  WARNING: This will restore data to production database!${NC}"
echo ""
read -p "Type 'RESTORE' to continue: " confirmation

if [ "$confirmation" != "RESTORE" ]; then
    echo -e "${RED}❌ Restore cancelled${NC}"
    exit 1
fi

# Step 1: Test connections
echo -e "\n${GREEN}Step 1: Testing connections...${NC}"
PGPASSWORD=$ADMIN_PASS psql -h localhost -p $SOURCE_PORT -U $ADMIN_USER -d $DB_NAME -c "SELECT 1;" > /dev/null
echo "✓ Source database accessible"
PGPASSWORD=$ADMIN_PASS psql -h localhost -p $TARGET_PORT -U $ADMIN_USER -d $DB_NAME -c "SELECT 1;" > /dev/null
echo "✓ Target database accessible"

# Step 2: Clear target database
echo -e "\n${GREEN}Step 2: Clearing target database...${NC}"
PGPASSWORD=$ADMIN_PASS psql -h localhost -p $TARGET_PORT -U $ADMIN_USER -d $DB_NAME << 'EOF'
BEGIN;
SET session_replication_role = 'replica';
TRUNCATE TABLE 
    notifications,
    exported_books,
    qa_findings,
    token_transactions,
    generation_tasks,
    chapter_revisions,
    chapters,
    book_outlines,
    voice_profiles,
    content_chunks,
    source_materials,
    projects,
    api_keys,
    users,
    billing_plans
CASCADE;
SET session_replication_role = 'origin';
COMMIT;
EOF
echo "✓ Target database cleared"

# Step 3: Copy data table by table
echo -e "\n${GREEN}Step 3: Copying data...${NC}"

# Array of tables in dependency order
TABLES=(
    "billing_plans"
    "users"
    "api_keys"
    "projects"
    "source_materials"
    "content_chunks"
    "voice_profiles"
    "book_outlines"
    "chapters"
    "chapter_revisions"
    "generation_tasks"
    "token_transactions"
    "qa_findings"
    "exported_books"
    "notifications"
)

for table in "${TABLES[@]}"; do
    echo -n "  Copying $table..."
    
    # Export from source
    PGPASSWORD=$ADMIN_PASS psql -h localhost -p $SOURCE_PORT -U $ADMIN_USER -d $DB_NAME -c "\COPY $table TO '/tmp/${table}.csv' WITH CSV HEADER"
    
    # Import to target
    PGPASSWORD=$ADMIN_PASS psql -h localhost -p $TARGET_PORT -U $ADMIN_USER -d $DB_NAME -c "\COPY $table FROM '/tmp/${table}.csv' WITH CSV HEADER"
    
    # Clean up
    rm -f /tmp/${table}.csv
    
    echo " ✓"
done

# Step 4: Apply app_user permissions
echo -e "\n${GREEN}Step 4: Setting up app_user permissions...${NC}"
PGPASSWORD=$ADMIN_PASS psql -h localhost -p $TARGET_PORT -U $ADMIN_USER -d $DB_NAME -f scripts/setup-app-user.sql
echo "✓ Permissions applied"

# Step 5: Verify
echo -e "\n${GREEN}Step 5: Verifying restoration...${NC}"
USER_COUNT=$(PGPASSWORD=$ADMIN_PASS psql -h localhost -p $TARGET_PORT -U $ADMIN_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM users;")
PROJECT_COUNT=$(PGPASSWORD=$ADMIN_PASS psql -h localhost -p $TARGET_PORT -U $ADMIN_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM projects;")
echo "✓ Users restored:$USER_COUNT"
echo "✓ Projects restored:$PROJECT_COUNT"

echo -e "\n${GREEN}✅ Data restoration complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Test the application"
echo "2. Close the restored DB tunnel: kill \$(lsof -ti:$SOURCE_PORT)"
echo "3. Delete the restored database:"
echo "   aws rds delete-db-instance --db-instance-identifier ghostline-dev-restored --skip-final-snapshot" 