#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}GhostLine Frontend Deployment Script${NC}"
echo "======================================"

# Check if environment is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Environment not specified${NC}"
    echo "Usage: $0 <environment>"
    echo "Example: $0 dev"
    exit 1
fi

ENVIRONMENT=$1

# Change to the web directory
cd ../web

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
npm install

# Build and export the Next.js app
echo -e "${YELLOW}Building and exporting Next.js application...${NC}"
npm run build

# Get the S3 bucket name from Terraform outputs
echo -e "${YELLOW}Getting S3 bucket name from Terraform...${NC}"
cd ../infra/terraform/environments/$ENVIRONMENT
S3_BUCKET=$(terraform output -raw frontend_s3_bucket 2>/dev/null || echo "")
CLOUDFRONT_ID=$(terraform output -raw cloudfront_distribution_id 2>/dev/null || echo "")

if [ -z "$S3_BUCKET" ]; then
    echo -e "${RED}Error: Could not get S3 bucket name from Terraform outputs${NC}"
    echo "Make sure you have run 'terraform apply' first"
    exit 1
fi

# Sync files to S3
echo -e "${YELLOW}Syncing files to S3 bucket: $S3_BUCKET${NC}"
cd ../../../../web

# Upload with proper cache headers
# HTML files - no cache
aws s3 sync out/ s3://$S3_BUCKET/ \
    --delete \
    --exclude "*" \
    --include "*.html" \
    --cache-control "public, max-age=0, must-revalidate"

# CSS and JS files - long cache
aws s3 sync out/ s3://$S3_BUCKET/ \
    --delete \
    --exclude "*.html" \
    --cache-control "public, max-age=31536000, immutable"

# Invalidate CloudFront cache
if [ ! -z "$CLOUDFRONT_ID" ]; then
    echo -e "${YELLOW}Invalidating CloudFront cache...${NC}"
    aws cloudfront create-invalidation --distribution-id $CLOUDFRONT_ID --paths "/*"
    echo -e "${GREEN}CloudFront invalidation created${NC}"
fi

echo -e "${GREEN}Frontend deployment complete!${NC}"
echo -e "Your site should be available at: https://${ENVIRONMENT}.ghostline.ai" 