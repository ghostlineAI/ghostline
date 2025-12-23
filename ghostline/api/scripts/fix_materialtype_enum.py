#!/usr/bin/env python3
"""
Fix MaterialType enum values in the database to match Python code.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import psycopg2
from urllib.parse import urlparse

from app.core.config import settings


def fix_materialtype_enum():
    """Add missing MaterialType enum values to database."""
    
    # Parse database URL
    parsed = urlparse(settings.DATABASE_URL)
    
    # Connect to database
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:],
        user=parsed.username,
        password=parsed.password
    )
    
    try:
        with conn.cursor() as cur:
            # Check if materialtype enum exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'materialtype'
                );
            """)
            
            result = cur.fetchone()
            if not result or not result[0]:
                print("❌ materialtype enum does not exist!")
                return False
            
            # Get existing values
            cur.execute("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'materialtype')
                ORDER BY enumsortorder;
            """)
            
            existing_values = [row[0] for row in cur.fetchall()]
            print(f"Existing materialtype values: {existing_values}")
            
            # Expected values from Python enum
            expected_values = [
                'TEXT', 'PDF', 'DOCX', 'AUDIO', 'IMAGE', 'VIDEO',
                'MARKDOWN', 'HTML', 'NOTE', 'VOICE_MEMO', 'OTHER'
            ]
            
            # Add missing values
            missing_values = set(expected_values) - set(existing_values)
            
            if missing_values:
                print(f"\n🔧 Adding missing values: {missing_values}")
                
                for value in missing_values:
                    try:
                        cur.execute(f"ALTER TYPE materialtype ADD VALUE IF NOT EXISTS '{value}';")
                        print(f"   ✅ Added: {value}")
                    except Exception as e:
                        print(f"   ❌ Failed to add {value}: {e}")
                
                conn.commit()
                print("\n✅ MaterialType enum fixed!")
            else:
                print("\n✅ All MaterialType values already exist!")
            
            # Also check ProcessingStatus enum
            cur.execute("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'processingstatus')
                ORDER BY enumsortorder;
            """)
            
            existing_status = [row[0] for row in cur.fetchall()]
            print(f"\nExisting processingstatus values: {existing_status}")
            
            expected_status = [
                'UPLOADING', 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'READY'
            ]
            
            missing_status = set(expected_status) - set(existing_status)
            
            if missing_status:
                print(f"\n🔧 Adding missing ProcessingStatus values: {missing_status}")
                
                for value in missing_status:
                    try:
                        cur.execute(f"ALTER TYPE processingstatus ADD VALUE IF NOT EXISTS '{value}';")
                        print(f"   ✅ Added: {value}")
                    except Exception as e:
                        print(f"   ❌ Failed to add {value}: {e}")
                
                conn.commit()
                print("\n✅ ProcessingStatus enum fixed!")
            else:
                print("\n✅ All ProcessingStatus values already exist!")
                
            return True
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("🔍 Checking and fixing MaterialType enum values...")
    db_url = settings.DATABASE_URL or ""
    print(f"Database: {db_url.split('@')[1] if '@' in db_url else 'unknown'}")
    
    if fix_materialtype_enum():
        print("\n✅ Database enums are ready for file uploads!")
        sys.exit(0)
    else:
        print("\n❌ Failed to fix database enums!")
        sys.exit(1) 