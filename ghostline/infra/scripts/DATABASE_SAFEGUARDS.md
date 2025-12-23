# Database Safeguards Implementation

## Overview
This document describes the enhanced database protection measures implemented after the db-init incident on 2025-06-29.

## What Happened
1. A `db-init` ECS task was running with admin credentials
2. It executed `init_db.py` which dropped and recreated tables
3. This bypassed all database-level protections because it used admin credentials

## New Protection Measures

### 1. Credential Separation ✅
- **App User**: `app_user` - Used by the API for normal operations
  - Password: Stored in `ghostline/dev/database-url` secret
  - Permissions: SELECT, INSERT, UPDATE, DELETE only
  - NO permissions for: CREATE, DROP, ALTER, TRUNCATE
  
- **Admin User**: `ghostlineadmin` - Used ONLY for migrations
  - Password: Stored in `ghostline/dev/database-url-admin` secret
  - Full permissions but should NEVER be used by applications

### 2. ECS Task Updates ✅
- All `db-init` task definitions have been deregistered
- API service updated to use `app_user` credentials
- No ECS tasks have admin credentials

### 3. Database Backups ✅
- Automated daily backups at 03:00 UTC
- 30-day retention period
- Latest snapshot: `rds:ghostline-dev-2025-06-29-18:30`
- Restore in progress to: `ghostline-dev-restored`

### 4. Secret Management ✅
- `ghostline/dev/database-url` - App user connection (for API)
- `ghostline/dev/database-url-admin` - Admin connection (for migrations only)

## How to Apply the Safeguards

### Step 1: When Database Restore Completes
```bash
# 1. Connect to the restored database
./db_connect.sh connect-restored

# 2. Run the permission setup script
psql -h localhost -p 5433 -U ghostlineadmin -d ghostline -f scripts/setup-app-user.sql

# 3. Test the app_user connection
PGPASSWORD='AppUser#Secure2025!' psql -h localhost -p 5433 -U app_user -d ghostline -c "\dt"
```

### Step 2: Switch Production to Restored Database
```bash
# Update the API to point to the restored database
aws secretsmanager put-secret-value \
  --secret-id "ghostline/dev/database-url" \
  --secret-string "postgresql://app_user:AppUser%23Secure2025%21@ghostline-dev-restored.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432/ghostline"

# Force service restart
aws ecs update-service --cluster ghostline-dev --service api --force-new-deployment
```

### Step 3: Safe Migration Process
For future migrations, use ONLY this process:
```bash
# Use the safe migration script
./infra/scripts/safe-migration.sh

# This script:
# 1. Creates a backup before migration
# 2. Uses admin credentials temporarily
# 3. Requires manual confirmation
# 4. Logs all operations
```

## Monitoring

### Check Current Permissions
```sql
-- Check app_user permissions
SELECT 
    tablename,
    string_agg(privilege_type, ', ' ORDER BY privilege_type) as privileges
FROM information_schema.table_privileges
WHERE grantee = 'app_user'
GROUP BY tablename;
```

### Verify No DDL Permissions
```sql
-- This should return 0 rows
SELECT * FROM information_schema.role_table_grants
WHERE grantee = 'app_user' 
AND privilege_type IN ('CREATE', 'DROP', 'ALTER', 'TRUNCATE');
```

## Emergency Procedures

### If Tables Are Dropped Again
1. DO NOT PANIC - We have backups
2. Find the latest snapshot:
   ```bash
   aws rds describe-db-snapshots --db-instance-identifier ghostline-dev --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime]' --output table
   ```
3. Restore from snapshot (see Step 1 above)
4. Investigate CloudWatch logs to find the cause

### Regular Backup Verification
Weekly task:
```bash
# List recent backups
aws rds describe-db-snapshots \
  --db-instance-identifier ghostline-dev \
  --query 'DBSnapshots[?SnapshotCreateTime >= `'$(date -u -d '7 days ago' '+%Y-%m-%d')'`].[DBSnapshotIdentifier,SnapshotCreateTime]' \
  --output table
```

## Lessons Learned
1. Database-level protections only work if apps use restricted users
2. Any process with admin credentials bypasses all protections
3. Docker images can contain old scripts even after deletion
4. Multiple layers of protection are essential
5. Regular backup verification is critical

## Next Steps
- [ ] Wait for database restore to complete
- [ ] Apply app_user permissions to restored database
- [ ] Update API to use restored database
- [ ] Verify API works with app_user credentials
- [ ] Delete the compromised `ghostline-dev` instance
- [ ] Set up monitoring alerts for DDL operations

---
Last Updated: 2025-06-29
Incident Response Team: [Your Name] 