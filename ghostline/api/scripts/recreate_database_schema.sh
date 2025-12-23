#!/bin/bash

# Script to recreate all database tables after accidental deletion
# This script requires sudo permissions to run

# Check if script is run with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "This database recreation script must be run with sudo for security reasons."
    echo "Please run: sudo $0"
    exit 1
fi

# Prompt for confirmation
echo "===================================="
echo "DATABASE RECREATION WARNING"
echo "===================================="
echo "This script will recreate ALL database tables in the production database."
echo ""
echo "Current situation:"
echo "- All tables have been dropped except alembic_version"
echo "- Alembic thinks we're at migration a5539dbb4d4e"
echo ""
echo "This script will:"
echo "1. Reset alembic to start fresh"
echo "2. Run all migrations to recreate tables"
echo ""
echo "Database: ghostline (production)"
echo ""
read -p "Are you ABSOLUTELY SURE you want to proceed? Type 'yes' to continue: " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Database recreation cancelled."
    exit 0
fi

# Set up connection parameters
DB_HOST="localhost"
DB_PORT="5433"
DB_USER="ghostlineadmin"
DB_NAME="ghostline"
DB_PASSWORD='YO,_9~5]Vp}vrNGl'
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
API_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Create a backup of current state (even though it's mostly empty)
echo "Creating backup of current state..."
BACKUP_FILE="ghostline_backup_before_recreation_$(date +%Y%m%d_%H%M%S).sql"
PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME > $BACKUP_FILE
echo "Backup created: $BACKUP_FILE"

# Reset alembic version to allow migrations to run
echo "Resetting alembic version..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << EOF
DELETE FROM alembic_version;
EOF

# Change to API directory
cd "$API_DIR"

# Run alembic migrations
echo "Running alembic migrations to recreate all tables..."
export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"

# First, downgrade to base (in case there are any partial tables)
poetry run alembic downgrade base

# Then upgrade to head
poetry run alembic upgrade head

if [ $? -eq 0 ]; then
    echo ""
    echo "Database recreation completed successfully!"
    echo ""
    echo "Verifying tables..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dt"
    
    echo ""
    echo "Checking custom types..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dT+"
else
    echo ""
    echo "Database recreation failed!"
    echo "Backup is available at: $BACKUP_FILE"
    exit 1
fi 