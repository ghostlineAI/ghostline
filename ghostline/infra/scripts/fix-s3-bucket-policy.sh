#!/bin/bash
set -e

BUCKET_NAME="ghostline-dev-frontend-820242943150"

echo "Updating S3 bucket policy for $BUCKET_NAME..."

# Create a proper bucket policy for static website hosting
cat > /tmp/bucket-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::ghostline-dev-frontend-820242943150/*"
        }
    ]
}
EOF

# Apply the bucket policy
echo "Applying bucket policy..."
aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file:///tmp/bucket-policy.json

# Ensure public access block is configured correctly
echo "Configuring public access block settings..."
aws s3api put-public-access-block \
    --bucket $BUCKET_NAME \
    --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

echo "Done! The S3 bucket should now allow public access."
echo "Try accessing the site again in a few moments." 