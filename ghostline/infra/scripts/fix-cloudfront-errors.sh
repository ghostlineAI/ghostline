#!/bin/bash
set -e

# Get CloudFront distribution ID
DISTRIBUTION_ID=$(aws cloudfront list-distributions --query "DistributionList.Items[?Aliases.Items[0]=='dev.ghostline.ai'].Id" --output text)

if [ -z "$DISTRIBUTION_ID" ]; then
    echo "Error: Could not find CloudFront distribution for dev.ghostline.ai"
    exit 1
fi

echo "Found CloudFront distribution: $DISTRIBUTION_ID"

# Get current distribution config
echo "Getting current distribution config..."
aws cloudfront get-distribution-config --id $DISTRIBUTION_ID > /tmp/dist-config.json

# Extract the config and ETag
ETAG=$(jq -r '.ETag' /tmp/dist-config.json)
jq '.DistributionConfig' /tmp/dist-config.json > /tmp/dist-config-only.json

# Remove custom error responses that return homepage
echo "Removing problematic custom error responses..."
jq '.CustomErrorResponses = [
  {
    "ErrorCode": 404,
    "ResponseCode": 404,
    "ResponsePagePath": "/404.html",
    "ErrorCachingMinTTL": 0
  },
  {
    "ErrorCode": 403,
    "ResponseCode": 403,
    "ResponsePagePath": "/404.html",
    "ErrorCachingMinTTL": 0
  }
]' /tmp/dist-config-only.json > /tmp/dist-config-updated.json

# Update the distribution
echo "Updating CloudFront distribution..."
aws cloudfront update-distribution \
    --id $DISTRIBUTION_ID \
    --distribution-config file:///tmp/dist-config-updated.json \
    --if-match $ETAG

echo "CloudFront distribution updated successfully!"
echo "Note: Changes may take 5-10 minutes to propagate globally."

# Create invalidation
echo "Creating CloudFront invalidation..."
aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*"

echo "Done! The navigation should work once the changes propagate." 