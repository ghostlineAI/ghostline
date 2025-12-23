# Fixing 500 Errors in GhostLine API

## Problem

When creating projects through the API, you might encounter 500 Internal Server errors that appear as CORS errors in the browser. This is because FastAPI's CORS middleware only adds Access-Control-Allow-Origin headers on successful responses (2xx/4xx), not on 500 errors.

## Root Cause

The most common cause is database schema mismatches, specifically missing enum values in PostgreSQL. The Python code expects certain enum values that don't exist in the database.

## Quick Fix

Run this script to check and add missing enum values:

```bash
cd ghostline/api
python scripts/check_and_fix_enums.py
```

## Manual Fix

If the script doesn't work, you can manually add the missing enum values:

```sql
-- Add missing bookgenre values
ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS 'fiction';
ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS 'non_fiction';
ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS 'memoir';
ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS 'business';
ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS 'self_help';
ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS 'academic';
ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS 'technical';
ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS 'other';

-- Add missing projectstatus values
ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'draft';
ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'processing';
ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'ready';
ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'published';
ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'archived';
```

## How to Debug

1. **Check server logs** - The actual error will be in the FastAPI/Uvicorn logs, not in the browser console
2. **Test with curl** - CORS errors only affect browsers, so test with curl to see the real error:
   ```bash
   curl -X POST http://localhost:8000/api/v1/projects/ \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title": "Test", "genre": "fiction"}'
   ```
3. **Check database enums**:
   ```sql
   -- List bookgenre values
   SELECT enumlabel FROM pg_enum 
   WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'bookgenre');
   
   -- List projectstatus values
   SELECT enumlabel FROM pg_enum 
   WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'projectstatus');
   ```

## Prevention

1. Always run Alembic migrations when deploying
2. Include enum value checks in your deployment scripts
3. Add proper error handling to return 4xx errors instead of 500s for validation issues 