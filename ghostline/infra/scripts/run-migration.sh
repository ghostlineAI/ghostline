#!/bin/bash
set -e

echo "🚀 Running database migration in GhostLine VPC..."

# Get private subnets
SUBNETS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=vpc-00d75267879c8f631" "Name=tag:Name,Values=*private*" \
  --query 'Subnets[0:2].SubnetId' \
  --output json | jq -r 'join(",")')

# Get ECS security group
SECURITY_GROUP=$(aws ec2 describe-security-groups \
  --filters "Name=vpc-id,Values=vpc-00d75267879c8f631" "Name=tag:Name,Values=*ecs*" \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

# Get latest task definition revision
TASK_DEF_REVISION=$(aws ecs describe-task-definition --task-definition ghostline-dev-api --query 'taskDefinition.revision' --output text)
TASK_DEFINITION="ghostline-dev-api:${TASK_DEF_REVISION}"

echo "📍 Using subnets: $SUBNETS"
echo "🔒 Using security group: $SECURITY_GROUP"
echo "📋 Using task definition: $TASK_DEFINITION"

# First, create pgvector extension
echo "🔧 Creating pgvector extension..."
PGVECTOR_TASK=$(aws ecs run-task \
  --cluster ghostline-dev \
  --task-definition $TASK_DEFINITION \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}" \
  --overrides '{
    "containerOverrides": [{
      "name": "api",
      "command": ["python", "-c", "import psycopg2; conn = psycopg2.connect('\''postgresql://ghostline:ghostline123!@ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432/ghostline'\''); conn.autocommit = True; cur = conn.cursor(); cur.execute('\''CREATE EXTENSION IF NOT EXISTS vector'\''); print('\''✅ pgvector extension created'\''); cur.close(); conn.close()"]
    }]
  }' \
  --query 'tasks[0].taskArn' \
  --output text)

aws ecs wait tasks-stopped --cluster ghostline-dev --tasks $PGVECTOR_TASK

# Run migration task
echo "📊 Running database migrations..."
TASK_ARN=$(aws ecs run-task \
  --cluster ghostline-dev \
  --task-definition $TASK_DEFINITION \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}" \
  --overrides '{
    "containerOverrides": [{
      "name": "api",
      "command": ["sh", "-c", "cd /app && alembic upgrade head"]
    }]
  }' \
  --query 'tasks[0].taskArn' \
  --output text)

echo "📋 Started migration task: ${TASK_ARN##*/}"
echo "⏳ Waiting for migration to complete..."

# Wait for task to complete
aws ecs wait tasks-stopped --cluster ghostline-dev --tasks $TASK_ARN

# Get exit code
EXIT_CODE=$(aws ecs describe-tasks \
  --cluster ghostline-dev \
  --tasks $TASK_ARN \
  --query 'tasks[0].containers[0].exitCode' \
  --output text)

if [ "$EXIT_CODE" = "0" ]; then
    echo "✅ Database migration completed successfully!"
    
    # Run verification
    echo "🔍 Verifying schema..."
    VERIFY_ARN=$(aws ecs run-task \
      --cluster ghostline-dev \
      --task-definition $TASK_DEFINITION \
      --launch-type FARGATE \
      --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}" \
      --overrides '{
        "containerOverrides": [{
          "name": "api",
          "command": ["python", "-c", "from sqlalchemy import create_engine, inspect; engine = create_engine('\''postgresql://ghostline:ghostline123!@ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432/ghostline'\''); inspector = inspect(engine); tables = sorted(inspector.get_table_names()); print(f'\''✅ Found {len(tables)} tables:'\''); [print(f'\''  - {t}'\'') for t in tables]"]
        }]
      }' \
      --query 'tasks[0].taskArn' \
      --output text)
    
    aws ecs wait tasks-stopped --cluster ghostline-dev --tasks $VERIFY_ARN
    
    # Show logs
    echo "📋 Schema verification:"
    sleep 5  # Give logs time to appear
    aws logs tail /ecs/ghostline-dev --since 2m --follow=false | grep -E "(Found|tables|-)" || true
    
else
    echo "❌ Migration failed with exit code: $EXIT_CODE"
    echo "📋 Error logs:"
    aws logs tail /ecs/ghostline-dev --since 5m --follow=false
    exit 1
fi 