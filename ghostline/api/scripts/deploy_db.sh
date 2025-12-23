#!/bin/bash
# Deploy database schema to production

set -e

echo "🚀 Deploying database schema to production..."

# Get RDS endpoint from Terraform output
cd ../../infra
RDS_ENDPOINT=$(terraform output -raw rds_endpoint 2>/dev/null || echo "")

if [ -z "$RDS_ENDPOINT" ]; then
    echo "❌ Could not get RDS endpoint from Terraform"
    exit 1
fi

echo "✓ RDS Endpoint: $RDS_ENDPOINT"

# Set environment variables
export POSTGRES_SERVER=$RDS_ENDPOINT
export POSTGRES_USER=ghostline
export POSTGRES_PASSWORD=ghostline123!  # This should come from secrets manager in production
export POSTGRES_DB=ghostline
export DATABASE_URL="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_SERVER/$POSTGRES_DB"
export ENVIRONMENT=production

# Go back to API directory
cd ../api

# Run database initialization
echo "📦 Installing dependencies..."
pip install sqlalchemy psycopg2-binary alembic pgvector

echo "🔧 Initializing database..."
python scripts/init_db.py

echo "🔄 Running migrations..."
alembic upgrade head

echo "✅ Database deployment complete!" 