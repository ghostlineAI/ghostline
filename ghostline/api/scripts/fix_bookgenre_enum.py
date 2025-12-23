#!/usr/bin/env python3
"""
Fix BookGenre enum by adding missing values.
This can be run directly or through Alembic.
"""

import os
import psycopg2
from urllib.parse import urlparse


def fix_bookgenre_enum():
    """Add missing values to the bookgenre enum type."""
    # Get database URL from environment or use default
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://ghostlineadmin:YOUR_PASSWORD@localhost:5432/ghostline"
    )
    
    # Parse the URL
    parsed = urlparse(database_url)
    
    # Connect to database
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:],  # Remove leading /
        user=parsed.username,
        password=parsed.password
    )
    
    try:
        # Get existing enum values
        with conn.cursor() as cur:
            cur.execute("""
                SELECT unnest(enum_range(NULL::bookgenre))::text AS value
            """)
            existing_values = {row[0] for row in cur.fetchall()}
            print(f"Existing enum values: {existing_values}")
        
        # Values we need
        required_values = [
            'fiction',
            'non_fiction',
            'business', 
            'self_help',
            'academic',
            'technical',
            'other'
        ]
        
        # Add missing values
        # Note: ALTER TYPE ... ADD VALUE cannot run in a transaction
        conn.autocommit = True
        
        with conn.cursor() as cur:
            for value in required_values:
                if value not in existing_values:
                    try:
                        cur.execute(f"ALTER TYPE bookgenre ADD VALUE '{value}'")
                        print(f"Added enum value: {value}")
                    except psycopg2.Error as e:
                        print(f"Could not add {value}: {e}")
        
        # Verify
        with conn.cursor() as cur:
            cur.execute("""
                SELECT unnest(enum_range(NULL::bookgenre))::text AS value
                ORDER BY 1
            """)
            final_values = [row[0] for row in cur.fetchall()]
            print(f"\nFinal enum values: {final_values}")
            
    finally:
        conn.close()


if __name__ == "__main__":
    fix_bookgenre_enum() 