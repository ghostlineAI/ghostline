# ⚠️ WARNING: Database Scripts

## IMPORTANT: Dangerous Scripts Have Been Removed

The following scripts have been **permanently deleted** to prevent accidental database destruction:

- `create_all_tables.py` - Used `Base.metadata.create_all()` which could wipe existing data
- `init_db.py` - Used `Base.metadata.create_all()` 
- `init_db_without_index.py` - Used `Base.metadata.create_all()`
- `../infra/scripts/fix-pgvector-migration.sh` - Contained `DROP TABLE CASCADE` commands
- `../infra/scripts/create-tables-simple.sh` - Created tables directly

## ✅ Safe Database Operations

**For ALL database schema changes, use Alembic migrations:**

```bash
# Create a new migration
alembic revision -m "description of change"

# Apply migrations (use the safe script!)
../infra/scripts/safe-migration.sh
```

## ❌ NEVER DO THIS

- **NEVER** use `Base.metadata.create_all()` or `drop_all()` in production
- **NEVER** run raw SQL with `DROP TABLE`, `TRUNCATE`, or `CREATE TABLE`
- **NEVER** bypass the safe migration script

## 📚 Safe Scripts in This Directory

- `seed_billing_plans.py` - Only inserts data, doesn't modify schema
- `test_models.py` - Only tests model definitions
- `test_schema.py` - Only validates schema consistency
- `validate_schema.py` - Only checks schema, doesn't modify

## 🛡️ Database Protection

The database is protected by:
1. Restricted `app_user` with no DDL permissions
2. 30-day backup retention
3. AWS Backup with daily/weekly snapshots
4. CloudWatch monitoring
5. Safe migration script requiring confirmation

See `/docs/DATABASE_PROTECTION.md` for full details.

## Security Note

All scripts in this directory should use `app_user` credentials from the DATABASE_URL secret, never admin credentials. Admin access is reserved for manual migrations via jump host only.

<!-- Checkpoint: app_user implementation - 2025-06-29 --> 