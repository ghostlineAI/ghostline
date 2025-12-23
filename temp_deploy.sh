#!/bin/bash
set -e

echo "🚀 Manual deployment to fix auth issue"

# Build with correct API URL
echo "🔨 Building..."
NEXT_PUBLIC_API_URL=https://api.dev.ghostline.ai npm run build

# Create out directory structure
echo "📦 Creating deployment structure..."
rm -rf out
mkdir -p out/_next

# Copy files
cp -r .next/static out/_next/
cp -r .next/server/app/* out/
cp -r public/* out/ 2>/dev/null || true

echo "☁️ Deploying to S3..."
# Clear bucket
aws s3 rm s3://ghostline-dev-frontend-820242943150/ --recursive

# Upload all files
aws s3 sync out/ s3://ghostline-dev-frontend-820242943150/ \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "*.html" \
  --exclude "*.json"

# Upload HTML and JSON with no cache
aws s3 sync out/ s3://ghostline-dev-frontend-820242943150/ \
  --delete \
  --cache-control "public, max-age=0, must-revalidate" \
  --exclude "*" \
  --include "*.html" \
  --include "*.json"

echo "🔄 Invalidating CloudFront..."
aws cloudfront create-invalidation \
  --distribution-id E3PE8KOGXI4I9Q \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text

echo "✅ Deployment complete!"
echo "🌐 https://dev.ghostline.ai" 