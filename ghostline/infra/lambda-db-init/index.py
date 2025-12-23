import json
import psycopg2
import os

def lambda_handler(event, context):
    """
    Lambda function to initialize the GhostLine database.
    """
    
    # Database connection parameters
    db_host = os.environ.get('DB_HOST', 'ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'ghostline')
    db_user = os.environ.get('DB_USER', 'ghostline')
    db_password = os.environ.get('DB_PASSWORD', 'ghostline123!')
    
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        
        cursor = conn.cursor()
        
        # Create pgvector extension
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.commit()
            message = "pgvector extension created successfully"
        except Exception as e:
            conn.rollback()
            message = f"pgvector extension already exists or error: {str(e)}"
        
        # Check existing tables
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_count = cursor.fetchone()[0]
        
        # Get list of tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Database initialization successful',
                'pgvector': message,
                'table_count': table_count,
                'tables': tables
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Database initialization failed'
            })
        } 