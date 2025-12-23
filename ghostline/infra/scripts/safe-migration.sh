#!/bin/bash
# Safe Migration Script - Requires explicit confirmation for DDL operations

set -euo pipefail

echo "🔐 GhostLine Safe Migration Script"
echo "=================================="
echo ""

# Safety check 1: Must be run manually, not in automation
if [ -n "${ECS_CONTAINER_METADATA_URI:-}" ] || [ -n "${AWS_EXECUTION_ENV:-}" ]; then
    echo "❌ ERROR: This script cannot be run in ECS/Lambda/automated environments!"
    echo "Migrations must be run manually via jump host."
    exit 1
fi

# Safety check 2: Require environment
if [ "$#" -ne 1 ]; then
    echo "❌ ERROR: Must specify environment"
    echo "Usage: $0 <environment>"
    echo "Example: $0 dev"
    exit 1
fi

ENV="$1"

# Safety check 3: Extra confirmation for production
if [ "$ENV" = "prod" ] || [ "$ENV" = "production" ]; then
    echo "⚠️  WARNING: Production migration requested!"
    echo "Have you:"
    echo "  - Tested this migration on dev? (y/n)"
    read -r tested
    echo "  - Created a database backup? (y/n)"
    read -r backed_up
    echo "  - Notified the team? (y/n)"
    read -r notified
    
    if [ "$tested" != "y" ] || [ "$backed_up" != "y" ] || [ "$notified" != "y" ]; then
        echo "❌ Cannot proceed without all confirmations"
        exit 1
    fi
fi

# Safety check 4: Show what will happen
echo ""
echo "📋 Migration Plan:"
echo "  - Environment: $ENV"
echo "  - Will use admin credentials from AWS Secrets Manager"
echo "  - Will run Alembic migrations"
echo ""
echo "Type 'MIGRATE-$ENV' to proceed:"
read -r confirm

if [ "$confirm" != "MIGRATE-$ENV" ]; then
    echo "❌ Confirmation failed"
    exit 1
fi

# Get admin credentials (never echo them!)
echo "🔑 Retrieving admin credentials..."
export DATABASE_URL=$(aws secretsmanager get-secret-value \
    --secret-id "ghostline/$ENV/admin-database-url" \
    --query SecretString \
    --output text)

if [ -z "$DATABASE_URL" ]; then
    echo "❌ Failed to retrieve admin credentials"
    exit 1
fi

# Run migrations
echo "🚀 Running migrations..."
cd /path/to/api
alembic upgrade head

echo "✅ Migration completed successfully!"
echo ""
echo "📌 Post-migration checklist:"
echo "  - [ ] Test application functionality"
echo "  - [ ] Verify app_user permissions are intact"
echo "  - [ ] Check logs for any errors"

# IMPORTANT: This script uses admin credentials only for migrations
# All application access must use app_user via DATABASE_URL secret
# Checkpoint: app_user security implementation - 2025-06-29 