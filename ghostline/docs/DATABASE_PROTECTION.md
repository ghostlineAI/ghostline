# Database Protection and Recovery Guide

## Overview

This document outlines the multiple layers of protection implemented to prevent accidental data loss and ensure quick recovery.

## Protection Layers

### 1. Database-Level Protection

- **Restricted Application User**: The API uses `app_user` which has NO permissions to:
  - DROP tables
  - CREATE tables
  - ALTER schema
  - TRUNCATE tables
  
- **Admin User**: `ghostlineadmin` is reserved ONLY for migrations and must be used with extreme caution

### 2. Application-Level Protection

- **Safe Migration Script**: Located at `infra/scripts/safe-migration.sh`
  - Requires typing "MIGRATE" to confirm
  - Automatically creates snapshot before migration
  - Shows warnings for production environments

### 3. Automated Backups

#### RDS Automated Backups
- **Retention**: 30 days
- **Schedule**: Daily at 03:00 UTC
- **Point-in-Time Recovery**: Available for last 30 days

#### AWS Backup Service
- **Daily Backups**: Retained for 30 days
- **Weekly Backups**: Retained for 90 days
- **Backup Vault**: Separate secure storage

### 4. Monitoring and Alerts
- CloudWatch alarm for backup failures
- All snapshots tagged for easy identification

## Recovery Procedures

### Option 1: Point-in-Time Recovery
```bash
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier ghostline-dev \
  --target-db-instance-identifier ghostline-dev-recovery \
  --restore-time "2025-06-29T15:00:00.000Z"
```

### Option 2: Snapshot Recovery
```bash
# List available snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier ghostline-dev \
  --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime]' \
  --output table

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier ghostline-dev-recovery \
  --db-snapshot-identifier <snapshot-id>
```

### Option 3: AWS Backup Recovery
1. Go to AWS Backup Console
2. Select the backup vault
3. Choose recovery point
4. Follow restore wizard

## Prevention Checklist

Before ANY database operation:

- [ ] Am I using the correct user? (app_user for normal operations)
- [ ] Have I created a manual snapshot?
- [ ] Have I tested in development first?
- [ ] Do I have a rollback plan?
- [ ] Have I notified the team?

## Emergency Contacts

- **Database Admin**: [Your contact]
- **AWS Support**: [Support plan details]
- **Escalation**: [Manager contact]

## Common Mistakes to Avoid

1. **NEVER** run raw SQL with DDL commands in production
2. **NEVER** use ghostlineadmin for application connections
3. **NEVER** skip the backup step before migrations
4. **NEVER** delete snapshots without verification
5. **ALWAYS** test migrations in development first

## Audit Trail

All database operations should be logged:
- Who performed the operation
- When it was performed
- What was changed
- Snapshot ID created before change 

## Security Best Practices

1. **Strong Password Policy**
   - Production passwords must be at least 25 characters
   - Use cryptographically secure random generation
   - Example: `openssl rand -base64 32 | tr -d "=+/" | cut -c1-25`
   - Current app_user uses a 25-character random password

2. **Principle of Least Privilege**

## How We Accidentally Bypassed Our Own Protections

Despite having excellent database-level protections, we accidentally destroyed data because:

1. **Admin Credentials in Migrations**: When running database migrations or restore scripts with admin credentials, ALL protections are bypassed
2. **Docker Images Can Contain Old Scripts**: Even after deleting dangerous scripts from Git, they persisted in Docker images
3. **ECS Tasks with Admin Access**: The db-init task had admin credentials and could drop tables

### Lessons Learned:
- **NEVER give admin credentials to automated processes**
- **NEVER store admin credentials in environment variables** 
- **ALWAYS use app_user for application access**
- **Admin access should be manual-only via jump host**

## Operational Safety Guidelines

### 1. Script Safety Requirements
All database scripts MUST:
- Be idempotent (safe to run multiple times)
- Have explicit confirmations for destructive operations
- Refuse to run on production databases
- Log all actions clearly
- Use transactions where possible

### 2. Access Control Matrix
| User | Purpose | Can Do | Cannot Do |
|------|---------|--------|-----------|
| app_user | Application runtime | SELECT, INSERT, UPDATE, DELETE | DROP, CREATE, ALTER, TRUNCATE |
| ghostlineadmin | Manual migrations only | Everything | Should never be in code |
| postgres | Emergency recovery | Everything | Should never be used |

### 3. Migration Safety
- Run migrations manually via jump host
- Never automate migrations in ECS/Docker
- Always backup before migrations
- Test migrations on dev first

### 4. Preventing Future Incidents
1. **Remove all admin credentials from:**
   - Environment variables
   - ECS task definitions  
   - Docker images
   - GitHub secrets (except for manual use)

2. **Audit regularly:**
   - Check which credentials are in use
   - Review ECS task definitions
   - Scan for hardcoded passwords
   - Verify least privilege

3. **Use separate secrets:**
   - `database-url` - app_user for runtime
   - `admin-database-url` - admin for manual migrations only
   - Never mix these up!

<!-- CHECKPOINT: app_user security implementation complete - 2025-06-29 --> 