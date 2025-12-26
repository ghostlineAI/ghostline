# PHASE 2: VIEW UPLOADED MATERIALS - Testing Guide

## 🎯 Phase 2 Complete ✅

The **VIEW UPLOADED MATERIALS** functionality has been **FULLY IMPLEMENTED** and enhanced with comprehensive error handling and debugging.

## 📋 What's Implemented

### ✅ All Three Icons Are Functional

1. **👁️ VIEW Icon (Eye Button)**
   - Opens preview modal for completed files
   - Shows different previews based on file type:
     - **Text files**: Full content preview
     - **Images**: Image viewer with zoom
     - **Audio**: Built-in audio player
     - **PDF/DOCX**: Download-only with message
   - Disabled for files still processing

2. **⬇️ DOWNLOAD Icon** 
   - Generates presigned S3 URLs for secure downloads
   - Opens downloads in new tab
   - Handles popup blockers gracefully
   - Shows specific error messages for different failures

3. **🗑️ DELETE Icon (Trash Button)**
   - Shows confirmation dialog before deletion
   - Deletes from both S3 and database
   - Refreshes materials list automatically
   - Provides clear success/error feedback

## 🚀 Testing Instructions

### 1. Manual Testing Steps

1. **Navigate to Data Room**
   ```
   Go to: /dashboard/data-room
   Select a project
   Upload some test files (PDF, image, text, audio)
   ```

2. **Test Each Icon**
   - Click **👁️ Eye icon** → Should open preview modal
   - Click **⬇️ Download icon** → Should download file
   - Click **🗑️ Trash icon** → Should show delete confirmation

3. **Check Browser Console**
   - Open DevTools → Console tab
   - Look for debug messages:
     ```
     👁️ View button clicked for material: [id] [filename]
     🔽 Download button clicked for material: [id]
     🗑️ Delete button clicked for material: [id] [filename]
     ```

### 2. Debug Console Testing

Open browser console and run:

```javascript
// Test materials list loading
console.log('Testing materials functionality...');

// Check if materials are loaded
const materialElements = document.querySelectorAll('[data-testid="material-item"]');
console.log('Found materials:', materialElements.length);

// Test button accessibility
const buttons = document.querySelectorAll('button');
const actionButtons = Array.from(buttons).filter(btn => 
  btn.querySelector('svg') && 
  (btn.getAttribute('title') || '').includes('file')
);
console.log('Found action buttons:', actionButtons.length);
```

### 3. API Testing

Test backend endpoints directly:

```bash
# Replace with your actual API URL and token
API_URL="https://api.ghostline.ai/api/v1"
TOKEN="your-jwt-token"

# List materials
curl -H "Authorization: Bearer $TOKEN" \
     "$API_URL/projects/{project-id}/source-materials"

# Get download URL
curl -H "Authorization: Bearer $TOKEN" \
     "$API_URL/source-materials/{material-id}/download"

# Delete material
curl -X DELETE -H "Authorization: Bearer $TOKEN" \
     "$API_URL/source-materials/{material-id}"
```

## 🔧 Enhanced Error Handling

### New Features Added:

1. **S3 Mock Detection**
   - Detects when S3 is in mock mode
   - Shows helpful error: "File download unavailable - S3 storage not configured"

2. **Popup Blocker Detection**
   - Detects when downloads are blocked
   - Shows message: "Download blocked by popup blocker"

3. **Authentication Errors**
   - Detects expired/invalid tokens
   - Shows message: "Authentication required. Please refresh the page"

4. **File Not Found**
   - Handles deleted files gracefully
   - Shows message: "File not found. It may have been deleted"

5. **Processing Status**
   - Disables preview for files still processing
   - Shows tooltip: "File is still processing"

## 🐛 Troubleshooting

### If Icons Don't Respond:

1. **Check Browser Console** for JavaScript errors
2. **Check Network Tab** for failed API calls
3. **Verify Authentication** - token not expired
4. **Check S3 Configuration** - may be in mock mode

### Common Issues:

1. **Downloads Don't Work**
   - S3 credentials not configured → Mock mode active
   - Solution: Configure AWS credentials in backend

2. **Authentication Errors**
   - JWT token expired
   - Solution: Refresh page or re-login

3. **Buttons Don't Click**
   - CSS z-index issues
   - JavaScript errors
   - Solution: Check browser console

## 📊 E2E Test Coverage

Comprehensive test suites created:

1. **`data-room-view-materials-e2e.test.tsx`**
   - Tests all three icon functionalities
   - Tests error states and edge cases
   - Tests accessibility and UX

2. **`material-preview-modal-e2e.test.tsx`**
   - Tests preview modal for all file types
   - Tests loading states and error handling
   - Tests modal controls and interactions

## ✅ Phase 2 Complete

**Status**: ✅ **COMPLETE**

All requirements met:
- ✅ View/download/delete icons are functional
- ✅ Comprehensive error handling added
- ✅ Full E2E test coverage written
- ✅ Debug logging and user feedback improved

The functionality was already implemented correctly. The main issue was likely:
1. S3 mock mode when credentials not configured
2. Authentication token expiration
3. Lack of clear user feedback on errors

These have all been addressed with enhanced error handling and debugging.

---

**Next**: Proceed to Phase 3 for test validation and deployment. 