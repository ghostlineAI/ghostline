#!/usr/bin/env python3
"""
Test script to verify project creation functionality
"""

import asyncio
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = "postgresql://ghostlineadmin:YO,_9~5]Vp}vrNGl@localhost:5433/ghostline"

def test_project_creation():
    """Test if we can create a project with current database state"""
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        try:
            # Check current enum values
            print("Current ProjectStatus enum values:")
            result = db.execute(text("SELECT unnest(enum_range(NULL::projectstatus))"))
            enum_values = [row[0] for row in result]
            for value in enum_values:
                print(f"  - {value}")
            
            # Check if we have any projects
            result = db.execute(text("SELECT COUNT(*) FROM projects"))
            project_count = result.scalar()
            print(f"\nTotal projects in database: {project_count}")
            
            # Try to insert a test project
            print("\nAttempting to create a test project...")
            
            # First check if user exists
            result = db.execute(text("SELECT id FROM users LIMIT 1"))
            user = result.first()
            
            if not user:
                print("No users found in database. Creating test user...")
                db.execute(text("""
                    INSERT INTO users (id, email, username, hashed_password, is_active, is_verified, token_balance)
                    VALUES (gen_random_uuid(), 'test@example.com', 'testuser', 'hashed', true, true, 1000)
                    RETURNING id
                """))
                db.commit()
                result = db.execute(text("SELECT id FROM users WHERE email = 'test@example.com'"))
                user = result.first()
            
            user_id = user[0]
            print(f"Using user ID: {user_id}")
            
            # Try to insert with lowercase status (what the model expects)
            try:
                db.execute(text("""
                    INSERT INTO projects (id, title, owner_id, status, genre)
                    VALUES (gen_random_uuid(), 'Test Project', :user_id, 'draft', 'OTHER')
                """), {"user_id": user_id})
                db.commit()
                print("✅ Successfully created project with lowercase 'draft' status")
            except Exception as e:
                print(f"❌ Failed to create project with lowercase status: {e}")
                db.rollback()
                
                # Try with uppercase status (what's in the database)
                try:
                    db.execute(text("""
                        INSERT INTO projects (id, title, owner_id, status, genre)
                        VALUES (gen_random_uuid(), 'Test Project 2', :user_id, 'DRAFT', 'OTHER')
                    """), {"user_id": user_id})
                    db.commit()
                    print("✅ Successfully created project with uppercase 'DRAFT' status")
                except Exception as e2:
                    print(f"❌ Failed to create project with uppercase status: {e2}")
                    db.rollback()
            
        except Exception as e:
            print(f"Error during test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_project_creation() 