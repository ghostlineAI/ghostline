"""File serving endpoint for local development."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, Response
from pathlib import Path

from app.core.config import settings
from app.services.storage import StorageService

router = APIRouter()


@router.get("/{file_path:path}")
async def serve_file(file_path: str):
    """Serve a file from local storage.
    
    This endpoint is only used in local development when USE_LOCAL_STORAGE=true.
    In production, files are served directly from S3.
    """
    if not settings.USE_LOCAL_STORAGE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Local file serving is disabled"
        )

    storage = StorageService()
    
    try:
        content = storage.get_file_content(file_path)
        
        # Determine content type from extension
        file_ext = Path(file_path).suffix.lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
        }
        content_type = content_types.get(file_ext, 'application/octet-stream')
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{Path(file_path).name}"'
            }
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )



