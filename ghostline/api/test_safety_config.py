"""
Test Safety Configuration for GhostLine API

CRITICAL: This file documents how to safely run tests without destroying production data.

WHAT HAPPENED:
- The test fixtures were dropping ALL tables after each test
- When TEST_DATABASE_URL pointed to production, it deleted the entire production database
- This has now been fixed with safety checks

SAFE TESTING GUIDELINES:

1. NEVER set TEST_DATABASE_URL to production database:
   ❌ WRONG: export TEST_DATABASE_URL='postgresql://ghostlineadmin:YO,_9~5]Vp}vrNGl@localhost:5433/ghostline'
   ✅ RIGHT: export TEST_DATABASE_URL='postgresql://testuser:testpass@localhost:5432/test_db'

2. Create a separate test database:
   createdb ghostline_test
   export TEST_DATABASE_URL='postgresql://postgres:postgres@localhost:5432/ghostline_test'

3. Use Docker for isolated testing:
   docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=testpass -e POSTGRES_DB=test_db postgres
   export TEST_DATABASE_URL='postgresql://postgres:testpass@localhost:5432/test_db'

4. For E2E tests against production API (no database access):
   python run_safe_e2e_tests.py

SAFETY FEATURES ADDED:
- Production URL patterns are blocked (5433, rds.amazonaws.com, ghostline-prod, ghostline-dev)
- Production password is blocked
- Tables are only dropped for SQLite or databases with 'test' in the name
- Safety warnings are displayed when using PostgreSQL

RUNNING TESTS SAFELY:

# Unit tests (uses SQLite)
poetry run pytest tests/unit/

# Integration tests with local test database
export TEST_DATABASE_URL='postgresql://postgres:postgres@localhost:5432/ghostline_test'
poetry run pytest tests/integration/

# E2E tests against production API (safe)
poetry run python ../../run_safe_e2e_tests.py

WHAT TO DO IF YOU ACCIDENTALLY POINT TO PRODUCTION:
1. The new safety checks will prevent connection
2. You'll see: "🚨 CRITICAL ERROR: Tests attempting to connect to production database!"
3. Tests will be skipped or use SQLite instead

EMERGENCY RECOVERY:
If tables are missing in production:
1. cd ghostline/api
2. alembic upgrade head
3. Insert default billing plan:
   INSERT INTO billing_plans (id, name, display_name, description, monthly_token_quota, price_cents, is_active) 
   VALUES ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 'free', 'Free Plan', 'Free plan', 10000, 0, true);
"""

# Test configuration validation
def validate_test_database_url():
    """Validate that TEST_DATABASE_URL is safe to use."""
    import os
    
    url = os.getenv("TEST_DATABASE_URL", "")
    
    # Dangerous patterns
    forbidden = ["5433", "ghostline-prod", "ghostline-dev", "rds.amazonaws.com", "YO,_9~5]Vp}vrNGl"]
    
    for pattern in forbidden:
        if pattern in url:
            raise ValueError(f"DANGER: TEST_DATABASE_URL contains production pattern: {pattern}")
    
    if url and "test" not in url.lower():
        print("⚠️  WARNING: TEST_DATABASE_URL doesn't contain 'test' - make sure it's not production!")
    
    return True

if __name__ == "__main__":
    print("Validating test configuration...")
    try:
        validate_test_database_url()
        print("✅ Test configuration appears safe")
    except ValueError as e:
        print(f"🚨 {e}")
        exit(1) 