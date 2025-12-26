# CORS/500 Error Status

## Current Issue
Production is showing CORS errors when creating projects:
```
Origin https://dev.ghostline.ai is not allowed by Access-Control-Allow-Origin. Status code: 500
```

## Root Cause
The backend API in production doesn't have the `genre` field support yet. When the frontend sends:
```json
{
      "title": "My Project",
  "description": "Description",
  "genre": "fiction"  // Backend doesn't recognize this field
}
```

The backend throws a 500 error, and FastAPI doesn't add CORS headers on unhandled exceptions.

## What We've Done

### Frontend (Deployed ✅)
- Added trailing slashes to all endpoints
- Added genre field to project creation
- Improved error handling for CORS/500 errors
- Shows user-friendly messages

### Backend (Not Deployed Yet ❌)
- Added genre field to ProjectCreate schema
- Added genre validation and mapping
- Fixed model/schema field mapping issues

## Temporary Workaround
The frontend now shows a helpful error message:
> "Server error: The backend may not be fully deployed yet. Please try again in a few minutes."

## Solution
Deploy the backend changes from the `api` repository:
1. The genre field support in `app/schemas/project.py`
2. The genre handling in `app/api/v1/endpoints/projects.py`

## How to Verify It's Fixed
Once backend is deployed:
```bash
curl -X POST "https://api.dev.ghostline.ai/api/v1/projects/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"name": "Test", "description": "Test", "genre": "fiction"}'
```

Should return 200/201 instead of 500.

## Lesson Learned
This is exactly why real integration tests are crucial. Our mocked tests passed, but the real API failed because:
1. Frontend and backend were out of sync
2. CORS errors masked the real issue (500 error)
3. Mocked tests didn't catch the schema mismatch 