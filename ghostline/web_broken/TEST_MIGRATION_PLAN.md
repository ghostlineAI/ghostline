# Test Migration Plan: Mocked → Real

## Phase 1: High Priority (Do Now)
These tests are currently mocked but should make real API calls:

### 1. `api-client.test.ts` → `api-client.real.test.ts`
- [ ] Authentication flow with real API
- [ ] Project CRUD operations
- [ ] Error handling (401, 403, 500)
- [ ] CORS validation
- [ ] Redirect handling

### 2. `form-submission.test.tsx` → Keep hybrid
- [ ] Real API calls for happy path
- [ ] Keep mocked for complex error scenarios
- [ ] Real validation testing

### 3. Auth Store Tests
- [ ] Real login/logout flow
- [ ] Token refresh testing
- [ ] Session persistence

## Phase 2: E2E Tests (Next Sprint)
Replace integration tests with Playwright E2E:

### 1. Project Creation Flow
```typescript
// Instead of: project-creation.test.tsx (mocked)
// Create: e2e/create-project.spec.ts (real browser)
test('user can create a project', async ({ page }) => {
  await loginUser(page);
  await page.goto('/dashboard/projects/new');
  // ... real browser interactions
});
```

### 2. Authentication Flow
- Login with valid credentials
- Register new account
- Password reset
- Session timeout

## Phase 3: Keep Mocked (Good as Unit Tests)

### 1. Component Tests
- `Button.test.tsx` - UI behavior
- `Modal.test.tsx` - Open/close logic
- `Form.test.tsx` - Field validation

### 2. Utility Tests  
- Date formatting
- String manipulation
- Calculations

### 3. Store Tests (Partial)
- State updates
- Computed values
- But use real API for async actions

## Implementation Strategy

### Step 1: Create Test Environments
```bash
# .env.test.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=testpass123
```

### Step 2: Test Utilities
```typescript
// __tests__/utils/test-api.ts
export const testApi = {
  async createTestUser() {
    // Real API call to create test user
  },
  async cleanupTestData() {
    // Clean up after tests
  }
};
```

### Step 3: Parallel Test Structure
```
__tests__/
├── unit/          # Fast, mocked tests
├── integration/   # Real API tests
└── e2e/          # Browser tests
```

## Migration Checklist

- [ ] Set up local test database
- [ ] Create test user accounts
- [ ] Update CI to run test API
- [ ] Migrate auth tests first
- [ ] Then project tests
- [ ] Finally, complex flows

## Benefits of This Approach

1. **Catch real bugs** - Like the 307 redirect issue
2. **Keep fast feedback** - Unit tests still run quickly
3. **Test confidence** - Know the app actually works
4. **Better debugging** - Real error messages

## Example: Before/After

### Before (Mocked)
```typescript
mockApiClient.post.mockResolvedValueOnce({
  data: { id: '123', name: 'Test Project' }
});
```

### After (Real)
```typescript
const response = await fetch('/api/v1/projects/', {
  method: 'POST',
  body: JSON.stringify({ name: 'Test Project' })
});
expect(response.status).toBe(201);
```

## Timeline
- Week 1: Migrate auth tests
- Week 2: Migrate project tests  
- Week 3: Set up E2E tests
- Week 4: Update CI/CD pipeline 