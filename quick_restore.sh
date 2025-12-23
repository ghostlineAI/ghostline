#!/bin/bash

echo "🔄 Quick data restore..."

# Use the production backup file that should exist
BACKUP_FILE="ghostline/infra/ghostline-prod-backup-20250629-134848.sql"

if [ -f "$BACKUP_FILE" ]; then
    echo "Found backup file: $BACKUP_FILE"
    
    # Check if it has content
    if [ -s "$BACKUP_FILE" ]; then
        echo "Backup file has content. Restoring..."
        PGPASSWORD='YO,_9~5]Vp}vrNGl' psql -h localhost -p 5433 -U ghostlineadmin -d ghostline < "$BACKUP_FILE"
        echo "✅ Restore complete!"
    else
        echo "❌ Backup file is empty!"
        
        # Try to find the June 30 data mentioned in scripts
        echo "Looking for June 30 backup data..."
        
        # Create a manual dump from the current database first
        echo "Creating backup of current state..."
        PGPASSWORD='YO,_9~5]Vp}vrNGl' pg_dump -h localhost -p 5433 -U ghostlineadmin -d ghostline --data-only --inserts > current_backup.sql
        
        echo "Current database has:"
        PGPASSWORD='YO,_9~5]Vp}vrNGl' psql -h localhost -p 5433 -U ghostlineadmin -d ghostline -c "SELECT COUNT(*) as user_count FROM users;"
    fi
else
    echo "❌ Backup file not found!"
fi

# Check what we have in the current database
echo ""
echo "Current database status:"
PGPASSWORD='YO,_9~5]Vp}vrNGl' psql -h localhost -p 5433 -U ghostlineadmin -d ghostline -c "SELECT email FROM users;" 