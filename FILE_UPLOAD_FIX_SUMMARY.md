# File Upload Fix Summary

## Issues Found and Fixed

### 1. Backend: Schema Mismatch (Critical)
**Problem**: The source materials endpoint was using `Project.user_id` but the Project model actually has `Project.owner_id`.
**Impact**: This caused a database query error resulting in 500 errors.
**Fix**: Changed all instances of `Project.user_id` to `Project.owner_id` in `source_materials.py`:
- Line 54: Upload endpoint
- Line 171: Get endpoint
- Line 193: Delete endpoint

### 2. Backend: Enum Value Mismatch (Critical)
**Problem**: Database enums are uppercase but Python enums were lowercase.
- MaterialType: DATABASE has "TEXT", "PDF", etc. but Python had "text", "pdf", etc.
- ProcessingStatus: DATABASE has "PENDING", "PROCESSING", etc. but Python had "pending", "processing", etc.
**Impact**: This caused IntegrityError when trying to save to database, resulting in 500 errors.
**Fix**: Updated both enums in `source_material.py` to use uppercase values matching the database.

### 3. Frontend: Content-Type Header Issue (Critical)
**Problem**: The frontend was explicitly setting `Content-Type: multipart/form-data` which breaks FormData uploads.
**Impact**: The browser needs to set the content-type with the boundary parameter automatically.
**Fix**: Changed the upload request in `source-materials.ts` to set `Content-Type: undefined` to let axios handle it properly.

## Root Cause Analysis

This is a classic example of the issues highlighted in the GhostLine Feature Development Blueprint:
1. **Schema mismatches** between different parts of the system
2. **Enum value mismatches** between database and code
3. **CORS errors masking 500 errors** - the real errors were database-related but appeared as CORS issues

## Testing

Created `test_file_upload.py` to verify the fixes work correctly. The script:
1. Logs in to get an auth token
2. Gets or creates a project
3. Attempts to upload a file
4. Provides debugging information if it fails

## Deployment Required

These fixes need to be deployed:
1. **Backend changes** in `ghostline/api/`:
   - `app/api/v1/endpoints/source_materials.py`
   - `app/models/source_material.py`
2. **Frontend changes** in `ghostline/web/`:
   - `lib/api/source-materials.ts`

## Lessons Learned

1. Always check that field names match between models and queries (`owner_id` vs `user_id`)
2. Always verify enum values match between database and code
3. Don't manually set Content-Type for multipart/form-data uploads
4. When you see CORS errors with 500 status, the real error is on the backend
5. Real integration tests would have caught all of these issues immediately 