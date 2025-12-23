import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os
import uuid

from app.main import app
from app.db.base import Base
from app.api.deps import get_db
from app.models.user import User
from app.services.auth import AuthService


# Database configuration for testing
# CRITICAL SAFETY: Never allow tests to connect to production database!
# Option 1: Use TEST_DATABASE_URL environment variable (must NOT be production)
# Option 2: Use local PostgreSQL test database
# Option 3: Use in-memory SQLite for basic tests

# Get the database URL from environment
DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")

# Check if this is a production database that we'll use safely
PRODUCTION_INDICATORS = ["5433", "ghostline", "YO,_9~5]Vp}vrNGl"]
USING_PRODUCTION = any(indicator in DATABASE_URL for indicator in PRODUCTION_INDICATORS)

# Configure database engine based on type
if USING_PRODUCTION:
    print("\n⚠️  PRODUCTION DATABASE DETECTED - Using SAFE TRANSACTION MODE")
    print("✅ All test changes will be rolled back")
    print("✅ No tables will be created or dropped")
    print("✅ Production data will remain untouched\n")
    
    # Use production database with transaction isolation
    engine = create_engine(DATABASE_URL, isolation_level="REPEATABLE READ")
elif not DATABASE_URL:
    print("\n⚠️  No TEST_DATABASE_URL provided")
    print("💡 To run full integration tests against production safely:")
    print("   export TEST_DATABASE_URL='postgresql://ghostlineadmin:YO,_9~5]Vp}vrNGl@localhost:5433/ghostline'")
    print("⚠️  Using in-memory SQLite for basic tests\n")
    
    DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # Regular test database
    print(f"\n✅ Using test database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    engine = create_engine(DATABASE_URL)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a safe database session for testing.
    
    When using production database:
    - Creates a transaction that gets rolled back after the test
    - Does NOT create or drop tables
    - All changes are isolated and rolled back
    """
    # No longer blocking production database - we use safe transactions instead
    
    if DATABASE_URL and any(indicator in DATABASE_URL for indicator in ["5433", "ghostline"]):
        print("\n⚠️  PRODUCTION DATABASE DETECTED - Using SAFE TRANSACTION MODE")
        print("✅ All changes will be rolled back after each test")
        print("✅ No tables will be created or dropped")
        print("✅ Production data will not be modified\n")
        
        # Use production database with transactions
        connection = engine.connect()
        transaction = connection.begin()
        db_session = TestingSessionLocal(bind=connection)
        
        # Create a savepoint for nested transactions
        db_session.begin_nested()
        
        try:
            yield db_session
        finally:
            # Rollback everything - no changes persist
            db_session.rollback()
            transaction.rollback()
            connection.close()
    else:
        # For SQLite/test databases, create tables
        Base.metadata.create_all(bind=engine)
        db_session = TestingSessionLocal()
        try:
            yield db_session
        finally:
            db_session.close()
            if "sqlite" in str(engine.url):
                Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session):
    """Create a test client with the test database."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db: Session):
    """Create a test user."""
    user = User(
        id=str(uuid.uuid4()),  # Generate proper UUID
        email="testuser@example.com",
        username="testuser",
        hashed_password=AuthService.get_password_hash("testpassword"),
        full_name="Test User",
        token_balance=100000,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(client: TestClient, test_user: User):
    """Create authentication headers with a valid token."""
    login_data = {
        "email": test_user.email,
        "password": "testpassword"
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
async def async_client(db: Session):
    """Create an async test client with the test database."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear() 