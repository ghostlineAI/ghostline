#!/usr/bin/env python3
"""
Diagnostic script to understand why S3 initialization is failing in the container
"""
import boto3
import os
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config

# Simulate the same environment as the container
print("🔍 S3 Initialization Diagnostic")
print("="*60)

# Check environment variables like the container would see them
print("\n1️⃣ Environment Variables Check:")
env_vars = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY", 
    "AWS_DEFAULT_REGION",
    "S3_SOURCE_MATERIALS_BUCKET",
    "S3_OUTPUTS_BUCKET"
]

for var in env_vars:
    value = os.getenv(var)
    if value:
        if "SECRET" in var or "KEY" in var:
            print(f"   {var}: {'*' * 8}...{value[-4:] if len(value) > 4 else '***'}")
        else:
            print(f"   {var}: {value}")
    else:
        print(f"   {var}: NOT SET")

# Test the exact same S3 initialization logic as StorageService
print("\n2️⃣ Testing S3 Client Initialization (like StorageService):")
try:
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_DEFAULT_REGION", "us-west-2")
    
    # Create config for S3v4 signature version (required for KMS encrypted buckets)
    s3_config = Config(
        signature_version='s3v4',
        region_name=aws_region,
    )
    
    if aws_access_key_id and aws_secret_access_key:
        print("   Using explicit credentials...")
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            config=s3_config,
        )
    else:
        print("   Using default credential chain...")
        s3_client = boto3.client(
            "s3",
            config=s3_config,
        )
    
    print("   ✅ S3 client created successfully")
    
except Exception as e:
    print(f"   ❌ S3 client creation failed: {type(e).__name__}: {e}")
    print("   This would cause StorageService to fall back to mock mode")
    exit(1)

# Test head_bucket call (this is what actually fails in StorageService)
print("\n3️⃣ Testing S3 Bucket Access (head_bucket call):")
bucket_name = os.getenv("S3_SOURCE_MATERIALS_BUCKET", "ghostline-dev-source-materials-820242943150")
print(f"   Testing bucket: {bucket_name}")

try:
    response = s3_client.head_bucket(Bucket=bucket_name)
    print("   ✅ head_bucket successful - StorageService would work!")
    print(f"   Response metadata: {response.get('ResponseMetadata', {}).get('HTTPStatusCode')}")
    
except ClientError as e:
    error_code = e.response['Error']['Code']
    print(f"   ❌ head_bucket failed with ClientError: {error_code}")
    print(f"   Error message: {e.response['Error']['Message']}")
    
    if error_code == '403':
        print("   🔍 This is a permissions issue - check IAM policy")
    elif error_code == '404':
        print("   🔍 Bucket doesn't exist or wrong name")
    elif error_code == '301':
        print("   🔍 Wrong region - bucket is in a different region")
    else:
        print(f"   🔍 Unexpected error code: {error_code}")
        
    print("   This would cause StorageService to fall back to mock mode")
    
except NoCredentialsError as e:
    print(f"   ❌ head_bucket failed with NoCredentialsError: {e}")
    print("   🔍 No AWS credentials found")
    print("   This would cause StorageService to fall back to mock mode")
    
except Exception as e:
    print(f"   ❌ head_bucket failed with unexpected error: {type(e).__name__}: {e}")
    print("   This would cause StorageService to fall back to mock mode")

# Test a simple S3 operation to verify credentials work
print("\n4️⃣ Testing Simple S3 Operation (list buckets):")
try:
    response = s3_client.list_buckets()
    print(f"   ✅ list_buckets successful - found {len(response['Buckets'])} buckets")
    
    # Check if our specific bucket is in the list
    bucket_names = [bucket['Name'] for bucket in response['Buckets']]
    if bucket_name in bucket_names:
        print(f"   ✅ Target bucket '{bucket_name}' found in account")
    else:
        print(f"   ⚠️  Target bucket '{bucket_name}' not found in account")
        print(f"   Available buckets: {bucket_names[:5]}..." if len(bucket_names) > 5 else f"   Available buckets: {bucket_names}")
        
except Exception as e:
    print(f"   ❌ list_buckets failed: {type(e).__name__}: {e}")

# Test KMS access (S3 bucket uses KMS encryption)
print("\n5️⃣ Testing KMS Access (bucket uses KMS encryption):")
try:
    kms_client = boto3.client('kms', region_name=aws_region)
    if aws_access_key_id and aws_secret_access_key:
        kms_client = boto3.client(
            'kms',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )
    
    # List KMS keys to test access
    response = kms_client.list_keys(Limit=10)
    print(f"   ✅ KMS access successful - found {len(response['Keys'])} keys")
    
except Exception as e:
    print(f"   ❌ KMS access failed: {type(e).__name__}: {e}")
    print("   🔍 This could cause S3 operations to fail if bucket uses KMS encryption")

print("\n6️⃣ Summary:")
print("   If StorageService is in mock mode, the issue is likely:")
print("   - The head_bucket call in step 3 failed")
print("   - Check the specific error above for the root cause")
print("   - Common causes: IAM permissions, wrong region, bucket doesn't exist")

print("\n" + "="*60)
print("🏁 Diagnostic completed!") 