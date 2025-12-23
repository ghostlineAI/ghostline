-- Setup restricted app_user for application use
-- This user has limited permissions to prevent accidental data loss

-- IMPORTANT: Set a strong password for app_user
-- Generate with: openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
-- Store in AWS Secrets Manager as part of DATABASE_URL

-- SAFETY: This script is IDEMPOTENT - safe to run multiple times
-- It will NOT change the password if the user already exists

-- Create the app_user if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'app_user') THEN
        -- REPLACE_WITH_STRONG_PASSWORD should be a 25+ character random string
        CREATE USER app_user WITH PASSWORD 'REPLACE_WITH_STRONG_PASSWORD';
        RAISE NOTICE 'Created new app_user - REMEMBER TO SET A STRONG PASSWORD!';
    ELSE
        RAISE NOTICE 'app_user already exists - password NOT changed';
    END IF;
END $$;

-- Grant connection privilege (idempotent)
GRANT CONNECT ON DATABASE ghostline TO app_user;

-- Grant usage on public schema (idempotent)
GRANT USAGE ON SCHEMA public TO app_user;

-- Grant permissions on existing tables (idempotent - GRANT is additive)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;

-- Grant permissions on sequences (idempotent)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Ensure future tables also get the same permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT USAGE, SELECT ON SEQUENCES TO app_user;

-- Explicitly REVOKE dangerous permissions (idempotent - safe to run multiple times)
REVOKE CREATE ON SCHEMA public FROM app_user;
REVOKE ALL ON DATABASE ghostline FROM app_user;
GRANT CONNECT ON DATABASE ghostline TO app_user;

-- Verify permissions
\echo ''
\echo 'Current app_user status:'
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM pg_user WHERE usename = 'app_user') 
        THEN 'app_user exists ✓' 
        ELSE 'app_user NOT FOUND ✗' 
    END as user_status;

\echo ''
\echo 'Permissions for app_user:'
SELECT 
    'Table' as object_type,
    tablename as object_name,
    string_agg(privilege_type, ', ' ORDER BY privilege_type) as privileges
FROM information_schema.table_privileges
WHERE grantee = 'app_user'
    AND table_schema = 'public'
GROUP BY tablename
ORDER BY tablename; 