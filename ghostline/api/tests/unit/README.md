# GhostLine API Test Suite

This test suite ensures the API configuration and routing work correctly to prevent common bugs.

## What We Test

### 1. API Configuration (`test_config.py`)
Tests the core configuration to prevent:
- Missing or duplicate `/api/v1` prefixes
- Incorrect trailing slash handling
- HTTP URLs in CORS origins for production
- Missing environment variables
- Weak JWT secret keys

### 2. Main Application (`test_main.py`)
Tests the FastAPI application setup to prevent:
- Routes not being mounted under `/api/v1`
- Duplicate API prefixes in route paths
- Inconsistent trailing slash handling
- Missing CORS headers
- HTTP redirect loops at application level
- Missing health check endpoints

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/unit/

# Run with coverage
pytest tests/unit/ --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_config.py

# Run with verbose output
pytest tests/unit/ -v
```

## Test Safety Notes

### Environment Variables
The tests mock environment variables to ensure they don't depend on actual deployment secrets. This makes them safe to run in any environment.

### Database Connections
These unit tests don't connect to actual databases. Integration tests (in a separate directory) would handle database testing.

## Key Test Scenarios

1. **API Prefix Configuration**
   - Verifies `API_V1_STR = "/api/v1"`
   - Ensures no duplicate prefixes
   - Checks proper slash handling

2. **HTTPS Security**
   - CORS origins use HTTPS (except localhost)
   - No HTTP redirects at app level (should be at ALB)
   - Secure headers configuration

3. **Trailing Slash Consistency**
   - API prefix has no trailing slash
   - CORS origins have no trailing slash
   - FastAPI handles trailing slashes consistently

4. **Environment Safety**
   - Production settings are applied correctly
   - Secret keys are strong enough
   - Required environment variables are validated

## Adding New Tests

When adding new API functionality:

1. Test any new environment variables in `test_config.py`
2. Test new route mounting in `test_main.py`
3. Ensure no hardcoded HTTP URLs
4. Verify trailing slash consistency
5. Check for duplicate API prefixes

## Common Issues These Tests Prevent

1. **404 Errors**: Routes not properly mounted under `/api/v1`
2. **CORS Errors**: Origins not properly configured
3. **Mixed Content**: HTTP URLs in production
4. **Security Issues**: Weak secrets, exposed endpoints
5. **Routing Bugs**: Duplicate prefixes, trailing slash issues 