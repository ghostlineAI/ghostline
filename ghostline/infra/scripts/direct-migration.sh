#!/bin/bash
set -e

echo "🚀 Running direct database migration..."
echo "⚠️  Note: This requires access to the RDS instance from your current network"
echo ""

# Database connection details
DB_HOST="ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com"
DB_PORT="5432"
DB_NAME="ghostline"
DB_USER="ghostline"
DB_PASS="ghostline123!"

# Test connection
echo "🔍 Testing database connection..."
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version();" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "❌ Cannot connect to database. This script requires:"
    echo "   1. VPN connection to the VPC, or"
    echo "   2. Running from an EC2 instance in the VPC, or"
    echo "   3. Temporarily opening RDS security group to your IP"
    echo ""
    echo "Alternative: Use the ECS-based migration script instead."
    exit 1
fi

echo "✅ Database connection successful!"

# Create pgvector extension
echo "🔧 Creating pgvector extension..."
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run migrations from the API directory
echo "📊 Running Alembic migrations..."
cd ../../api
export DATABASE_URL="postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME"
alembic upgrade head

# Verify schema
echo "🔍 Verifying schema..."
python -c "
from sqlalchemy import create_engine, inspect
engine = create_engine('$DATABASE_URL')
inspector = inspect(engine)
tables = sorted(inspector.get_table_names())
print(f'✅ Found {len(tables)} tables:')
for table in tables:
    print(f'  - {table}')
"

echo "✅ Migration completed successfully!" 