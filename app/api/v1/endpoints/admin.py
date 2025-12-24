"""Admin endpoints for system management."""
import subprocess
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import settings
from app.models.user import User

router = APIRouter()


@router.post("/run-migrations")
async def run_migrations(
    current_user: User = Depends(deps.get_current_superuser),
    db: Session = Depends(deps.get_db),
):
    """Run database migrations (admin only)."""
    try:
        # Run alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd="/app"  # Assuming the API runs from /app in the container
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Migration failed: {result.stderr}"
            )
            
        return {
            "status": "success",
            "message": "Migrations completed successfully",
            "output": result.stdout
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run migrations: {str(e)}"
        )


@router.get("/check-schema")
async def check_schema(
    db: Session = Depends(deps.get_db),
):
    """Check database schema (public endpoint for debugging)."""
    try:
        # Get all tables
        result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        tables = [row[0] for row in result]
        
        # Check if source_materials table exists
        source_materials_exists = "source_materials" in tables
        
        # Get columns if table exists
        source_materials_columns = []
        if source_materials_exists:
            result = db.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'source_materials'
                ORDER BY ordinal_position;
            """))
            source_materials_columns = [
                {"name": row[0], "type": row[1]} 
                for row in result
            ]
        
        # Check enums
        result = db.execute(text("""
            SELECT typname 
            FROM pg_type 
            WHERE typtype = 'e'
            ORDER BY typname;
        """))
        enums = [row[0] for row in result]
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "database_url": settings.DATABASE_URL.split("@")[-1],
            "tables": tables,
            "source_materials_exists": source_materials_exists,
            "source_materials_columns": source_materials_columns,
            "enums": enums,
            "total_tables": len(tables)
        }
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        } 