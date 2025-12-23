"""Admin endpoints for system management."""
import subprocess
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api import deps
from app.models.user import User
from app.core.config import settings

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
        
        # Check if source_materials table exists now
        check_result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'source_materials'
            );
        """)).scalar()
        
        return {
            "status": "success",
            "output": result.stdout,
            "source_materials_exists": check_result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration error: {str(e)}"
        )


@router.get("/check-schema")
async def check_schema(
    db: Session = Depends(deps.get_db),
):
    """Check database schema (public endpoint for debugging)."""
    try:
        # Check tables
        tables_result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)).fetchall()
        
        # Check enums
        enums_result = db.execute(text("""
            SELECT typname 
            FROM pg_type 
            WHERE typtype = 'e' 
            ORDER BY typname;
        """)).fetchall()
        
        # Check source_materials specifically
        source_materials_columns = []
        if any(t[0] == 'source_materials' for t in tables_result):
            columns_result = db.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'source_materials' 
                ORDER BY ordinal_position;
            """)).fetchall()
            source_materials_columns = [
                {"name": col[0], "type": col[1]} for col in columns_result
            ]
        
        return {
            "tables": [t[0] for t in tables_result],
            "enums": [e[0] for e in enums_result],
            "source_materials_exists": any(t[0] == 'source_materials' for t in tables_result),
            "source_materials_columns": source_materials_columns
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__
        } 