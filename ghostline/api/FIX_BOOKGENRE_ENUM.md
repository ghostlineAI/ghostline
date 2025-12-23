# Fix BookGenre Enum Issue

## Problem
The frontend sends new genre values (e.g., `fiction`, `non_fiction`) but the PostgreSQL enum type `bookgenre` in production doesn't have these values. This causes:
1. Backend returns 500 error
2. FastAPI doesn't add CORS headers on 500 errors
3. Browser shows "CORS error" instead of the real error

## Solution
Run the Alembic migration to add the missing enum values.

## Steps to Fix

### Option 1: Run Alembic Migration (Recommended)
```bash
# From the api directory
cd ghostline/api

# Set the database URL (or export it)
export DATABASE_URL="postgresql://ghostlineadmin:PASSWORD@localhost:5432/ghostline"

# Run the migration
alembic upgrade head
```

### Option 2: Run SQL Script Directly
```bash
# Connect to database
cd /Users/ageorges/Desktop/GhostLine
./db_connect.sh tunnel &
sleep 5

# Run the SQL script
psql -h localhost -p 5432 -U ghostlineadmin -d ghostline -f ghostline/api/scripts/fix_bookgenre_enum.sql
```

### Option 3: Run Python Script
```bash
# From the api directory
cd ghostline/api

# Set database URL
export DATABASE_URL="postgresql://ghostlineadmin:PASSWORD@localhost:5432/ghostline"

# Run the script
python scripts/fix_bookgenre_enum.py
```

## Verification
After running any of the above options, verify the fix:

```bash
# Test with curl
curl -X POST https://api.dev.ghostline.ai/api/v1/projects/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Project","description":"Test","genre":"fiction"}'
```

Should return 201 Created (or 401 if no valid token).

## What the Migration Does
Adds these values to the `bookgenre` enum:
- `fiction`
- `non_fiction`
- `business`
- `self_help`
- `academic`
- `technical`
- `other`

The migration handles cases where values already exist, so it's safe to run multiple times. 