#!/bin/bash

# Script to fix ProjectStatus enum mismatch in the database
# This script requires sudo permissions to run

# Check if script is run with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "This migration script must be run with sudo for security reasons."
    echo "Please run: sudo $0"
    exit 1
fi

# Prompt for confirmation
echo "===================================="
echo "DATABASE MIGRATION WARNING"
echo "===================================="
echo "This script will modify the ProjectStatus enum in the production database."
echo "It will change the enum values from UPPERCASE to lowercase to match the application code."
echo ""
echo "The following changes will be made:"
echo "- DRAFT → draft"
echo "- PROCESSING → processing"
echo "- READY → ready"
echo "- PUBLISHED → published"
echo "- ARCHIVED → archived"
echo ""
echo "Database: ghostline (production)"
echo ""
read -p "Are you ABSOLUTELY SURE you want to proceed? Type 'yes' to continue: " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Migration cancelled."
    exit 0
fi

# Set up connection parameters
DB_HOST="localhost"
DB_PORT="5433"
DB_USER="ghostlineadmin"
DB_NAME="ghostline"
DB_PASSWORD='YO,_9~5]Vp}vrNGl'

# Create a backup first
echo "Creating backup..."
BACKUP_FILE="ghostline_backup_before_enum_fix_$(date +%Y%m%d_%H%M%S).sql"
PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME > $BACKUP_FILE

if [ $? -eq 0 ]; then
    echo "Backup created: $BACKUP_FILE"
else
    echo "Backup failed! Aborting migration."
    exit 1
fi

# Execute the migration
echo "Executing migration..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << EOF
BEGIN;

-- Show current state
SELECT 'Current enum values:' as status;
SELECT unnest(enum_range(NULL::projectstatus));

-- Check if any projects exist with current values
SELECT 'Projects using current enum:' as status;
SELECT status, COUNT(*) FROM projects GROUP BY status;

-- Convert column to text temporarily
ALTER TABLE projects ALTER COLUMN status TYPE text;

-- Drop the old enum type
DROP TYPE IF EXISTS projectstatus;

-- Create new enum with lowercase values
CREATE TYPE projectstatus AS ENUM ('draft', 'processing', 'ready', 'published', 'archived');

-- Convert existing data to lowercase and cast back to enum
ALTER TABLE projects ALTER COLUMN status TYPE projectstatus 
USING CASE 
    WHEN LOWER(status) IN ('draft', 'processing', 'ready', 'published', 'archived') 
    THEN LOWER(status)::projectstatus 
    ELSE 'draft'::projectstatus 
END;

-- Set default value
ALTER TABLE projects ALTER COLUMN status SET DEFAULT 'draft'::projectstatus;

-- Show new state
SELECT 'New enum values:' as status;
SELECT unnest(enum_range(NULL::projectstatus));

COMMIT;
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "Migration completed successfully!"
    echo "The ProjectStatus enum has been updated to use lowercase values."
else
    echo ""
    echo "Migration failed! The database has been rolled back."
    echo "Backup is available at: $BACKUP_FILE"
    exit 1
fi 