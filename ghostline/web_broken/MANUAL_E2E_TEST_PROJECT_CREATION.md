# Manual E2E Test: Project Creation Flow

## Test Date: ___________
## Tester: ___________
## Environment: https://dev.ghostline.ai

## Prerequisites
- [ ] Have access to dev environment
- [ ] Clear browser cache and cookies
- [ ] Open browser developer console (F12)

## Test Steps

### 1. User Registration/Login
- [ ] Navigate to https://dev.ghostline.ai
- [ ] If not logged in, click "Sign Up" or "Login"
- [ ] Register a new account or login with existing credentials
- [ ] Verify successful redirect to dashboard

### 2. Navigate to Project Creation
- [ ] From dashboard, click "Projects" in sidebar
- [ ] Click "Create New Project" button
- [ ] Verify URL is: https://dev.ghostline.ai/dashboard/projects/new

### 3. Fill Project Form
- [ ] Enter project title: "E2E Test Project [timestamp]"
- [ ] Select genre: "Fiction" or "Non-Fiction"
- [ ] Enter description: "This is a manual e2e test project"
- [ ] Leave form empty and click "Create Project"
- [ ] **Expected**: Validation errors appear for required fields
- [ ] Fill in all required fields

### 4. Submit Project
- [ ] Click "Create Project" button
- [ ] Watch network tab in browser console
- [ ] **Expected**: POST request to /api/v1/projects/
- [ ] **Expected**: Success toast message appears: "Project created successfully!"

### 5. Verify Redirect
- [ ] **Expected**: Automatic redirect to projects list page
- [ ] **Expected**: URL is now: https://dev.ghostline.ai/dashboard/projects
- [ ] **Expected**: NO 404 ERROR

### 6. Verify Project in List
- [ ] Look for the newly created project in the list
- [ ] **Expected**: Project appears with correct title and genre
- [ ] **Expected**: Project status is "draft"
- [ ] Click "Open" button
- [ ] **Expected**: Button shows "Open (Coming Soon)" and is disabled

### 7. Error Handling Tests
- [ ] Go back to create new project
- [ ] Try submitting with network disabled
- [ ] **Expected**: Error message appears gracefully
- [ ] Re-enable network
- [ ] Try invalid genre by modifying HTML select
- [ ] **Expected**: API returns validation error

## Results
- [ ] All tests passed
- [ ] Issues found: _________________________________

## Console Errors
Check browser console for any errors during the test:
- [ ] No 404 errors
- [ ] No uncaught exceptions
- [ ] No CORS errors (except those masking 500 errors)

## Notes
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________ 