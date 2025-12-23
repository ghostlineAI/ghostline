#!/bin/bash
# Fix DATABASE_URL in ECS task definition

# Get RDS endpoint
RDS_ENDPOINT=$(aws rds describe-db-instances \
  --query 'DBInstances[?contains(DBInstanceIdentifier, `ghostline-dev`)].Endpoint.Address' \
  --output text)

if [ -z "$RDS_ENDPOINT" ]; then
  echo "ERROR: Could not find RDS endpoint"
  exit 1
fi

echo "Found RDS endpoint: $RDS_ENDPOINT"

# Create DATABASE_URL
DATABASE_URL="postgresql://ghostlineadmin:YO,_9~5]Vp}vrNGl@${RDS_ENDPOINT}:5432/ghostline"
echo "DATABASE_URL: $DATABASE_URL"

# Store in SSM Parameter Store
aws ssm put-parameter \
  --name "/ghostline/dev/api/database-url" \
  --value "$DATABASE_URL" \
  --type "SecureString" \
  --overwrite \
  --description "Database URL for GhostLine API"

echo "✓ Stored DATABASE_URL in SSM Parameter Store"

# Update task definition to use the secret
echo "Next steps:"
echo "1. Update task definition to include secret:"
echo '   "secrets": ['
echo '     {'
echo '       "name": "DATABASE_URL",'
echo '       "valueFrom": "/ghostline/dev/api/database-url"'
echo '     }'
echo '   ]'
echo "2. Force new deployment: aws ecs update-service --cluster ghostline-dev --service api --force-new-deployment" 