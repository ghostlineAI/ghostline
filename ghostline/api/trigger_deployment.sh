#!/bin/bash

# Script to manually trigger the deployment of the API backend

echo "🚀 Triggering manual deployment of GhostLine API..."

# Option 1: Push an empty commit to trigger GitHub Actions
echo "📝 Creating empty commit to trigger deployment..."
git commit --allow-empty -m "trigger: Manual deployment to fix genre field support"
git push origin main

echo "✅ Deployment triggered!"
echo ""
echo "📋 Next steps:"
echo "1. Go to https://github.com/ghostlineAI/api/actions"
echo "2. Watch the 'Deploy API to ECS' workflow"
echo "3. If it doesn't appear, check:"
echo "   - GitHub Actions are enabled in repository settings"
echo "   - Required secrets are configured"
echo ""
echo "🔑 Required GitHub Secrets:"
echo "   - AWS_ACCESS_KEY_ID"
echo "   - AWS_SECRET_ACCESS_KEY" 
echo "   - ECS_SERVICE=api"
echo "   - ECS_CLUSTER=ghostline-dev"
echo "   - ECS_TASK_DEFINITION=ghostline-dev-api"
echo ""
echo "📊 Monitor deployment at:"
echo "   - GitHub Actions: https://github.com/ghostlineAI/api/actions"
echo "   - AWS ECS Console: https://console.aws.amazon.com/ecs"
echo "   - CloudWatch Logs: https://console.aws.amazon.com/cloudwatch" 