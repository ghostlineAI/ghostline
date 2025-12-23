#!/usr/bin/env python3
"""
Test the comprehensive database schema.
"""

import os
import sys

from sqlalchemy import create_engine, inspect, text

# Database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ghostline:ghostline123!@ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432/ghostline",
)


def test_schema():
    """Test the database schema."""
    print("🔍 Testing GhostLine Database Schema")
    print(f"📍 Connecting to: {DATABASE_URL.split('@')[1]}")

    try:
        # Create engine
        engine = create_engine(DATABASE_URL)

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Connected to PostgreSQL: {version}")

            # Check pgvector extension
            result = conn.execute(
                text("""
                SELECT extname, extversion
                FROM pg_extension
                WHERE extname = 'vector'
            """)
            )
            vector_info = result.fetchone()
            if vector_info:
                print(f"✅ pgvector extension: v{vector_info[1]}")
            else:
                print("❌ pgvector extension not found")

            # Get all tables
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"\n📊 Found {len(tables)} tables:")

            expected_tables = [
                "billing_plans",
                "users",
                "api_keys",
                "projects",
                "source_materials",
                "content_chunks",
                "voice_profiles",
                "book_outlines",
                "chapters",
                "chapter_revisions",
                "generation_tasks",
                "token_transactions",
                "qa_findings",
                "exported_books",
                "notifications",
            ]

            for table in expected_tables:
                if table in tables:
                    # Get row count
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"  ✅ {table:<25} ({count} rows)")
                else:
                    print(f"  ❌ {table:<25} (MISSING)")

            # Check for unexpected tables
            unexpected = set(tables) - set(expected_tables)
            if unexpected:
                print(f"\n⚠️  Unexpected tables: {unexpected}")

            # Test some key relationships
            print("\n🔗 Testing Key Relationships:")

            # Test foreign keys
            fk_tests = [
                ("users", "billing_plan_id", "billing_plans"),
                ("projects", "owner_id", "users"),
                ("source_materials", "project_id", "projects"),
                ("content_chunks", "source_material_id", "source_materials"),
                ("chapters", "project_id", "projects"),
                ("chapter_revisions", "chapter_id", "chapters"),
                ("token_transactions", "user_id", "users"),
                ("notifications", "user_id", "users"),
            ]

            for table, column, ref_table in fk_tests:
                if table in tables:
                    fks = inspector.get_foreign_keys(table)
                    fk_found = any(fk["constrained_columns"] == [column] for fk in fks)
                    if fk_found:
                        print(f"  ✅ {table}.{column} → {ref_table}")
                    else:
                        print(f"  ❌ {table}.{column} → {ref_table} (FK missing)")

            # Test indexes
            print("\n🔍 Testing Key Indexes:")

            index_tests = [
                ("users", "ix_users_email"),
                ("users", "ix_users_cognito_sub"),
                ("api_keys", "ix_api_keys_key_hash"),
                ("content_chunks", "idx_content_chunks_embedding"),
            ]

            for table, index_name in index_tests:
                if table in tables:
                    indexes = inspector.get_indexes(table)
                    index_found = any(idx["name"] == index_name for idx in indexes)
                    if index_found:
                        print(f"  ✅ {index_name}")
                    else:
                        print(f"  ❌ {index_name} (MISSING)")

            # Test enum types
            print("\n🏷️  Testing Enum Types:")

            result = conn.execute(
                text("""
                SELECT typname
                FROM pg_type
                WHERE typtype = 'e'
                AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                ORDER BY typname
            """)
            )

            enums = [row[0] for row in result]
            expected_enums = [
                "bookgenre",
                "projectstatus",
                "materialtype",
                "processingstatus",
                "outlinestatus",
                "tasktype",
                "taskstatus",
                "transactiontype",
                "findingtype",
                "findingstatus",
                "exportformat",
                "notificationtype",
                "notificationchannel",
            ]

            for enum in expected_enums:
                if enum in enums:
                    print(f"  ✅ {enum}")
                else:
                    print(f"  ❌ {enum} (MISSING)")

            print("\n✅ Schema test complete!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure you're connected to the VPC (use bastion host or VPN)")
        print("2. Check database credentials")
        print("3. Run migrations: alembic upgrade head")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(test_schema())
