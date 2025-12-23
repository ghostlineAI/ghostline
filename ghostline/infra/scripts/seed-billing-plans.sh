#!/bin/bash
set -e

echo "🚀 Seeding billing plans in GhostLine database..."

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

# Run seed task
echo "💰 Seeding billing plans..."
TASK_ARN=$(aws ecs run-task \
  --cluster ghostline-dev \
  --task-definition $TASK_DEFINITION \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}" \
  --overrides '{
    "containerOverrides": [{
      "name": "api",
      "command": ["python", "scripts/seed_billing_plans.py"]
    }]
  }' \
  --query 'tasks[0].taskArn' \
  --output text)

echo "📋 Started seed task: ${TASK_ARN##*/}"
echo "⏳ Waiting for seeding to complete..."

# Wait for task to complete
aws ecs wait tasks-stopped --cluster ghostline-dev --tasks $TASK_ARN

# Get exit code
EXIT_CODE=$(aws ecs describe-tasks \
  --cluster ghostline-dev \
  --tasks $TASK_ARN \
  --query 'tasks[0].containers[0].exitCode' \
  --output text)

if [ "$EXIT_CODE" = "0" ]; then
    echo "✅ Billing plans seeded successfully!"
    
    # Verify the data
    echo "🔍 Verifying billing plans..."
    VERIFY_ARN=$(aws ecs run-task \
      --cluster ghostline-dev \
      --task-definition $TASK_DEFINITION \
      --launch-type FARGATE \
      --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}" \
      --overrides '{
        "containerOverrides": [{
          "name": "api",
          "command": ["python", "-c", "from sqlalchemy import create_engine, text; engine = create_engine('\''postgresql://ghostline:ghostline123!@ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432/ghostline'\''); result = engine.execute(text('\''SELECT name, display_name, monthly_token_quota, price_cents FROM billing_plans ORDER BY price_cents'\'')); plans = result.fetchall(); print(f'\''✅ Found {len(plans)} billing plans:'\''); [print(f'\''  - {p[1]} ({p[0]}): {p[2]} tokens/month, ${p[3]/100}'\'') for p in plans]"]
        }]
      }' \
      --query 'tasks[0].taskArn' \
      --output text)
    
    aws ecs wait tasks-stopped --cluster ghostline-dev --tasks $VERIFY_ARN
    
    # Show logs
    echo "📋 Billing plans:"
    sleep 5  # Give logs time to appear
    aws logs tail /ecs/ghostline-dev --since 2m --follow=false | grep -E "(Found|billing|Basic|Premium|Professional)" || true
    
else
    echo "❌ Seeding failed with exit code: $EXIT_CODE"
    echo "📋 Error logs:"
    aws logs tail /ecs/ghostline-dev --since 5m --follow=false
    exit 1
fi

echo "🎉 Billing plans seeding complete! Users can now register with the Basic plan." 