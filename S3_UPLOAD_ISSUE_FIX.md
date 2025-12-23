# S3 Upload Issue - Root Cause and Fix

## Issue Description
Files are not being uploaded to S3, causing 404 errors when trying to view/download them. The upload appears to succeed but files are not actually stored in S3.

## Root Cause
The ECS task IAM role does not have proper permissions to upload to the S3 buckets. 

### The Problem:
1. S3 bucket names include AWS account ID: `ghostline-dev-source-materials-820242943150`
2. IAM policy only allowed access to pattern: `ghostline-dev-*`
3. This pattern doesn't match buckets with account IDs in the name

### Result:
- S3 client fails to initialize and falls back to "mock mode"
- Files appear to upload successfully but are not actually stored
- Presigned URLs return 404 because files don't exist

## Fix Applied

### 1. Infrastructure Fix (Terraform)
Updated ECS task IAM policy in `ghostline/infra/terraform/modules/ecs/main.tf`:
```hcl
Resource = [
  "arn:aws:s3:::${var.project_name}-${var.environment}-*",
  "arn:aws:s3:::${var.project_name}-${var.environment}-*/*",
  "arn:aws:s3:::${var.project_name}-${var.environment}-*-*",        # Added
  "arn:aws:s3:::${var.project_name}-${var.environment}-*-*/*"      # Added
]
```

### 2. API Error Handling
Added detection for mock mode in `source_materials.py` to fail fast:
```python
if "mock-s3.localhost" in file_url:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="File upload service is temporarily unavailable..."
    )
```

## Next Steps

1. **Apply Terraform changes** to update IAM permissions:
   ```bash
   cd ghostline/infra/terraform/environments/dev
   terraform plan
   terraform apply
   ```

2. **Restart ECS service** to pick up new IAM role:
   ```bash
   aws ecs update-service --cluster ghostline-dev --service api --force-new-deployment
   ```

3. **Verify S3 uploads work**:
   - Upload a test file
   - Check S3 bucket to confirm file exists
   - Test view/download functionality

## Prevention
- Always test file uploads in dev environment after infrastructure changes
- Monitor CloudWatch logs for S3 connection failures
- Consider adding health checks for S3 connectivity 