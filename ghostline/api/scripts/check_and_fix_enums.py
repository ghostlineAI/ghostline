#!/usr/bin/env python3
"""
Check and fix enum values in the database.
This script ensures all enum values expected by the Python code exist in PostgreSQL.
"""

import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

async def check_and_fix_enums():
    """Check and add missing enum values to the database."""
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    
    try:
        async with engine.begin() as conn:
            # Check existing enum values for bookgenre
            result = await conn.execute(text("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'bookgenre'
                )
                ORDER BY enumsortorder;
            """))
            existing_values = [row[0] for row in result]
            
            print(f"Existing bookgenre enum values: {existing_values}")
            
            # Expected values
            expected_values = ['fiction', 'non_fiction', 'memoir', 'business', 
                             'self_help', 'academic', 'technical', 'other']
            
            # Find missing values
            missing_values = [v for v in expected_values if v not in existing_values]
            
            if missing_values:
                print(f"Missing values: {missing_values}")
                
                # Add missing values
                for value in missing_values:
                    try:
                        await conn.execute(text(f"""
                            ALTER TYPE bookgenre ADD VALUE IF NOT EXISTS '{value}';
                        """))
                        print(f"Added missing value: {value}")
                    except Exception as e:
                        print(f"Error adding {value}: {e}")
            else:
                print("All expected enum values are present!")
                
            # Check projectstatus enum
            result = await conn.execute(text("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'projectstatus'
                )
                ORDER BY enumsortorder;
            """))
            status_values = [row[0] for row in result]
            
            print(f"\nExisting projectstatus enum values: {status_values}")
            
            expected_status = ['draft', 'processing', 'ready', 'published', 'archived']
            missing_status = [v for v in expected_status if v not in status_values]
            
            if missing_status:
                print(f"Missing status values: {missing_status}")
                for value in missing_status:
                    try:
                        await conn.execute(text(f"""
                            ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS '{value}';
                        """))
                        print(f"Added missing status: {value}")
                    except Exception as e:
                        print(f"Error adding {value}: {e}")
            else:
                print("All expected status values are present!")
                        
    except Exception as e:
        print(f"Database error: {e}")
        return False
    finally:
        await engine.dispose()
    
    return True

if __name__ == "__main__":
    success = asyncio.run(check_and_fix_enums())
    sys.exit(0 if success else 1) 