# ⚠️ CRITICAL TEST SAFETY WARNING ⚠️

## 🚨 NEVER RUN TESTS AGAINST PRODUCTION DATABASE 🚨

### What Happened
On July 1, 2025, we discovered a catastrophic bug where pytest was **DELETING ALL PRODUCTION TABLES** after each test run. This happened because:
1. The test fixtures in `conftest.py` were calling `Base.metadata.drop_all()`
2. When `TEST_DATABASE_URL` was set to production, it destroyed everything

### Safety Measures Implemented
We've added multiple safety checks to prevent this:
- Production patterns are blocked (port 5433, rds.amazonaws.com, etc.)
- Production password is blocked
- Tables are only dropped for SQLite or databases with 'test' in name
- Clear warnings are shown when using PostgreSQL

### How to Run Tests Safely

#### 1. Unit Tests (Safe - uses SQLite)
```bash
poetry run pytest tests/unit/
```

#### 2. Integration Tests (Requires Test Database)
```bash
# Create a local test database first
createdb ghostline_test

# Set safe test database URL
export TEST_DATABASE_URL='postgresql://postgres:postgres@localhost:5432/ghostline_test'

# Run integration tests
poetry run pytest tests/integration/
```

#### 3. E2E Tests Against Production API (Safe)
```bash
# This script ONLY uses API calls, never touches database directly
cd ../.. && poetry run python run_safe_e2e_tests.py
```

### Docker Test Database (Recommended)
```bash
# Start PostgreSQL in Docker
docker run -d --name ghostline-test-db \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=test_db \
  postgres

# Use it for tests
export TEST_DATABASE_URL='postgresql://postgres:testpass@localhost:5432/test_db'
```

### Emergency Recovery
If production tables are missing:
```bash
# 1. Run migrations
cd ghostline/api
alembic upgrade head

# 2. Create default billing plan
PGPASSWORD='YO,_9~5]Vp}vrNGl' psql -h localhost -p 5433 -U ghostlineadmin -d ghostline -c "
INSERT INTO billing_plans (id, name, display_name, description, monthly_token_quota, price_cents, is_active) 
VALUES ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 'free', 'Free Plan', 'Free plan', 10000, 0, true)
ON CONFLICT (id) DO NOTHING;"
```

### Remember
- **ALWAYS** check `echo $TEST_DATABASE_URL` before running tests
- **NEVER** use port 5433 (production SSH tunnel) for tests
- **NEVER** use production password in test configuration
- When in doubt, use the safe E2E test script 