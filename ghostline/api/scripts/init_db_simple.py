#!/usr/bin/env python3
"""
Simple database initialization script.
Can be run from anywhere with proper environment variables.
"""

import os
import sys

from sqlalchemy import create_engine, text

# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://ghostline:ghostline@localhost/ghostline"
)

print("Connecting to database...")
print(
    f"Database URL: {DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('//')[1], '***:***')}"
)

try:
    # Create engine
    engine = create_engine(DATABASE_URL)

    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.scalar()
        print(f"✓ Connected to PostgreSQL: {version}")

        # Create pgvector extension
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("✓ pgvector extension created/verified")
        except Exception as e:
            print(f"Warning: Could not create pgvector extension: {e}")
            # Continue anyway

        # Check if tables exist
        result = conn.execute(
            text("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        )
        table_count = result.scalar()
        print(f"✓ Found {table_count} existing tables")

        if table_count == 0:
            print("\n⚠️  No tables found. Run 'alembic upgrade head' to create tables.")
        else:
            # List tables
            result = conn.execute(
                text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            )
            print("\nExisting tables:")
            for row in result:
                print(f"  - {row[0]}")

    print("\n✅ Database connection successful!")

except Exception as e:
    print(f"\n❌ Database connection failed: {e}")
    print("\nPlease check:")
    print("  1. DATABASE_URL environment variable is set correctly")
    print("  2. PostgreSQL server is running and accessible")
    print("  3. Database credentials are correct")
    sys.exit(1)
