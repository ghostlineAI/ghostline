-- Fix BookGenre enum by adding missing values
-- Run this script with: psql -U ghostlineadmin -d ghostline -f fix_bookgenre_enum.sql

-- First, check existing values
\echo 'Current bookgenre enum values:'
SELECT unnest(enum_range(NULL::bookgenre))::text AS value ORDER BY 1;

-- Add new values (these commands must run outside a transaction)
\echo ''
\echo 'Adding new enum values...'

-- Each ALTER TYPE must be in its own statement
ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS 'fiction';
ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS 'non_fiction';
ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS 'business';
ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS 'self_help';
ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS 'academic';
ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS 'technical';
ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS 'other';

-- Verify the changes
\echo ''
\echo 'Updated bookgenre enum values:'
SELECT unnest(enum_range(NULL::bookgenre))::text AS value ORDER BY 1; 