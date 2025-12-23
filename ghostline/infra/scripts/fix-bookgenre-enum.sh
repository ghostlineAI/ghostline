#!/bin/bash
# Fix BookGenre enum in production database

set -e

echo "🔧 Fixing BookGenre enum in production database..."

# Get the current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# SQL commands to fix the enum
SQL_COMMANDS=$(cat <<'EOF'
-- Check current enum values
SELECT 'Current values:' as info;
SELECT unnest(enum_range(NULL::bookgenre))::text AS value ORDER BY 1;

-- Add new values (IF NOT EXISTS is not supported in older PostgreSQL versions)
-- So we'll try each one and ignore errors if they already exist
DO $$
BEGIN
    BEGIN
        ALTER TYPE bookgenre ADD VALUE 'fiction';
    EXCEPTION WHEN duplicate_object THEN
        RAISE NOTICE 'Value fiction already exists';
    END;
    
    BEGIN
        ALTER TYPE bookgenre ADD VALUE 'non_fiction';
    EXCEPTION WHEN duplicate_object THEN
        RAISE NOTICE 'Value non_fiction already exists';
    END;
    
    BEGIN
        ALTER TYPE bookgenre ADD VALUE 'business';
    EXCEPTION WHEN duplicate_object THEN
        RAISE NOTICE 'Value business already exists';
    END;
    
    BEGIN
        ALTER TYPE bookgenre ADD VALUE 'self_help';
    EXCEPTION WHEN duplicate_object THEN
        RAISE NOTICE 'Value self_help already exists';
    END;
    
    BEGIN
        ALTER TYPE bookgenre ADD VALUE 'academic';
    EXCEPTION WHEN duplicate_object THEN
        RAISE NOTICE 'Value academic already exists';
    END;
    
    BEGIN
        ALTER TYPE bookgenre ADD VALUE 'technical';
    EXCEPTION WHEN duplicate_object THEN
        RAISE NOTICE 'Value technical already exists';
    END;
    
    BEGIN
        ALTER TYPE bookgenre ADD VALUE 'other';
    EXCEPTION WHEN duplicate_object THEN
        RAISE NOTICE 'Value other already exists';
    END;
END$$;

-- Verify the changes
SELECT 'Updated values:' as info;
SELECT unnest(enum_range(NULL::bookgenre))::text AS value ORDER BY 1;
EOF
)

# Run the SQL commands via SSM
echo "📡 Connecting to database via AWS Systems Manager..."
aws ssm start-session \
    --target i-0a881a8e0e3f5d5a0 \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters "{\"host\":[\"ghostline-dev.cvh6mnzrpkyq.us-west-2.rds.amazonaws.com\"],\"portNumber\":[\"5432\"],\"localPortNumber\":[\"5432\"]}" &

# Wait for tunnel to establish
echo "⏳ Waiting for tunnel to establish..."
sleep 5

# Run the SQL commands
echo "🚀 Running SQL commands..."
PGPASSWORD="${DB_PASSWORD:-$(aws secretsmanager get-secret-value --secret-id ghostline/dev/database-url --query SecretString --output text | grep -oP '(?<=postgresql://ghostlineadmin:)[^@]*')}" \
psql -h localhost -p 5432 -U ghostlineadmin -d ghostline -c "$SQL_COMMANDS"

# Kill the SSM session
echo "🧹 Cleaning up..."
pkill -f "aws ssm start-session"

echo "✅ BookGenre enum fixed successfully!" 