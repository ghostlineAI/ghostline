#!/bin/bash
set -e

echo "🚀 Deploying GhostLine Web to dev.ghostline.ai"

# Configuration
S3_BUCKET="ghostline-dev-frontend-820242943150"
CLOUDFRONT_ID="E3PE8KOGXI4I9Q"
AWS_REGION="us-west-2"

# Change to web directory
cd "$(dirname "$0")/../web"

echo "📦 Installing dependencies..."
npm ci

echo "🔨 Building application..."
NEXT_PUBLIC_API_URL=https://api.dev.ghostline.ai npm run build

echo "☁️ Syncing to S3..."
# Upload static assets with long cache
aws s3 sync out/ s3://${S3_BUCKET}/ \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "*.html" \
  --exclude "*.json" \
  --region ${AWS_REGION}

# Upload HTML files with no cache
aws s3 sync out/ s3://${S3_BUCKET}/ \
  --delete \
  --cache-control "public, max-age=0, must-revalidate" \
  --exclude "*" \
  --include "*.html" \
  --include "*.json" \
  --region ${AWS_REGION}

echo "🔄 Invalidating CloudFront cache..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id ${CLOUDFRONT_ID} \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text \
  --region ${AWS_REGION})

echo "⏳ Waiting for invalidation to complete..."
aws cloudfront wait invalidation-completed \
  --distribution-id ${CLOUDFRONT_ID} \
  --id ${INVALIDATION_ID} \
  --region ${AWS_REGION}

echo "✅ Deployment complete!"
echo "🌐 Site URL: https://dev.ghostline.ai"
echo "📊 CloudFront Distribution: ${CLOUDFRONT_ID}"
echo "🪣 S3 Bucket: ${S3_BUCKET}" 