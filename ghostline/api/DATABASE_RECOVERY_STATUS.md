# Database Recovery Status

## Critical Issue Discovered

During E2E testing for the Schema Fix feature, we discovered that **ALL database tables have been dropped** except for the `alembic_version` table. This explains why:

1. Registration endpoints return 500 errors
2. All E2E tests fail
3. The API cannot function properly

## Current Database State

- **Tables present**: Only `alembic_version`
- **Alembic version**: `a5539dbb4d4e` (thinks all migrations have been applied)
- **Custom types**: Missing (including `projectstatus` enum)
- **All application tables**: MISSING

## Recovery Scripts Created

### 1. `scripts/recreate_database_schema.sh`
**Purpose**: Recreate all database tables from scratch using Alembic migrations

**What it does**:
- Resets alembic version to allow migrations to rerun
- Runs all migrations to recreate tables
- Verifies table creation

**Usage**: `sudo ./scripts/recreate_database_schema.sh`

### 2. `scripts/fix_projectstatus_enum_migration.sh`
**Purpose**: Fix the ProjectStatus enum mismatch (uppercase vs lowercase)

**Note**: This script is currently NOT usable because the projects table doesn't exist.
It should be used AFTER recreating the database if enum issues persist.

**Usage**: `sudo ./scripts/fix_projectstatus_enum_migration.sh`

### 3. `scripts/test_project_creation.py`
**Purpose**: Test script to verify project creation functionality

**What it tests**:
- Current enum values
- Project creation with different status values
- Database connectivity

**Usage**: `poetry run python scripts/test_project_creation.py`

## Recommended Recovery Steps

1. **URGENT**: Run the database recreation script to restore all tables:
   ```bash
   sudo ./scripts/recreate_database_schema.sh
   ```

2. After recreation, verify the database state:
   ```bash
   # Check tables
   PGPASSWORD='YO,_9~5]Vp}vrNGl' psql -h localhost -p 5433 -U ghostlineadmin -d ghostline -c "\dt"
   
   # Check enums
   PGPASSWORD='YO,_9~5]Vp}vrNGl' psql -h localhost -p 5433 -U ghostlineadmin -d ghostline -c "\dT+"
   ```

3. Run the test script to verify functionality:
   ```bash
   poetry run python scripts/test_project_creation.py
   ```

4. If enum issues persist after recreation, use the enum fix script.

## Important Notes

- All scripts require `sudo` for security (as requested)
- Scripts create backups before making changes
- The SSH tunnel must be active: `./db_connect.sh tunnel`

## Root Cause

The database tables were accidentally dropped at some point, but Alembic still thinks all migrations have been applied. This prevents normal migration commands from working. 