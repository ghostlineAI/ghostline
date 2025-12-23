# Real Tests vs Mocked Tests: What We Found

## Summary

By migrating from mocked tests to real integration tests, we discovered **multiple critical issues** that were completely hidden by mocked tests.

## Issues Found by Real Tests

### 1. CORS and Redirect Issues ❌
- **Problem**: FastAPI redirects `/projects` → `/projects/` causing CORS failures
- **Impact**: Complete API failure in production
- **Mocked tests**: Passed ✅ (didn't test real HTTP behavior)
- **Real tests**: Failed ❌ (caught the issue immediately)

### 2. Inconsistent Status Codes
- **Auth without token**: Returns 403 instead of standard 401
- **Create project**: Returns 200 instead of standard 201
- **Mocked tests**: Assumed standard REST conventions
- **Real tests**: Revealed actual API behavior

### 3. Missing Response Fields
- **Problem**: API doesn't return expected fields
  - `target_word_count` missing from project creation response
  - `chapters` and `book_outline` missing from project GET response
- **Mocked tests**: Returned whatever we mocked
- **Real tests**: Showed actual API response structure

### 4. Error Handling Bugs
- **Problem**: Non-existent resources return 500 instead of 404
- **Impact**: Can't distinguish between server errors and missing resources
- **Mocked tests**: Always returned the "correct" error codes
- **Real tests**: Revealed broken error handling

### 5. Inconsistent Trailing Slash Behavior
- **Collection endpoints**: Require trailing slash (`/projects/`)
- **Resource endpoints**: Reject trailing slash (`/projects/{id}`)
- **Mocked tests**: Didn't test this at all
- **Real tests**: Found the inconsistency

## Test Migration Results

### Before (Mocked)
```typescript
// 71 tests passing ✅
// False confidence
// Tested our assumptions, not reality
```

### After (Real)
```typescript
// Projects API: 11/13 passing (2 document API bugs)
// Auth API: All passing after adjusting for actual behavior
// Found 5+ critical issues
```

## Lessons Learned

1. **Mocked tests hide real problems**
   - They test what you think the API does
   - Not what it actually does

2. **Real tests catch production issues**
   - CORS problems
   - Redirect issues
   - Missing fields
   - Error handling bugs

3. **API documentation vs Reality**
   - Docs said 401, API returns 403
   - Docs said 201, API returns 200
   - Expected fields missing

4. **Network behavior matters**
   - Redirects break CORS
   - Status codes affect client behavior
   - Response structure must match expectations

## Recommendations

1. **Always write real integration tests** for API endpoints
2. **Keep mocked tests only for**:
   - UI component logic
   - Business logic functions
   - Hard-to-reproduce error scenarios

3. **Run real tests in CI/CD** against staging environment
4. **Document API bugs** found by tests (we found 5+ issues)
5. **Fix the API** based on test findings:
   - Consistent trailing slash behavior
   - Proper 404 handling
   - Include all expected fields
   - Follow REST conventions

## Next Steps

1. Fix the API bugs we discovered
2. Migrate remaining mocked tests
3. Set up E2E tests with Playwright
4. Add real tests to CI/CD pipeline
5. Never trust mocked integration tests again!

## The Bottom Line

**Mocked tests gave us 100% coverage and 0% confidence.**
**Real tests gave us actual confidence and found real bugs.**

The 307 redirect CORS issue that took hours to debug would have been caught in minutes with real tests. 