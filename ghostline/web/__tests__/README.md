# GhostLine Frontend Test Suite

This test suite helps prevent common bugs that have been introduced multiple times during development.

## What We Test

### 1. API Configuration
- **File**: `__tests__/lib/api/config.test.ts`
- **Purpose**: Validates API configuration without complex mocking
- **Common Bugs Prevented**:
  - Duplicate `/api/v1/api/v1` paths
  - Trailing slash inconsistencies  
  - HTTP URLs in production
  - Missing `/api/v1` prefix in environment variable

### 2. Next.js Configuration
- **File**: `__tests__/config/next.config.test.ts`
- **Purpose**: Validates Next.js settings
- **Common Bugs Prevented**:
  - Wrong build output directory
  - Hardcoded environment variables
  - Trailing slash configuration issues
  - Build configuration errors

## Running Tests

```bash
# Install dependencies (if not already installed)
npm install --save-dev jest @testing-library/react @testing-library/jest-dom jest-environment-jsdom @types/jest

# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage

# Run specific test file
npm test -- __tests__/lib/api/client.test.ts
```

## Test Structure

```
__tests__/
├── lib/
│   └── api/
│       └── config.test.ts      # API configuration validation tests
├── config/
│   └── next.config.test.ts     # Next.js configuration tests
└── README.md                   # This file
```

## Key Test Scenarios

1. **No Duplicate API Prefixes**: Tests ensure `/api/v1` appears exactly once in API calls
2. **HTTPS Only in Production**: Tests verify no HTTP URLs are used for production API
3. **Consistent Trailing Slashes**: Tests check that trailing slashes are handled consistently
4. **Environment Variable Usage**: Tests ensure env vars are used correctly, not hardcoded

## Adding New Tests

When adding new API endpoints or configuration:

1. Add tests to verify the endpoint path doesn't include `/api/v1`
2. Add tests to verify trailing slash consistency
3. Add tests to verify HTTPS usage in production
4. Update this README with the new test coverage 