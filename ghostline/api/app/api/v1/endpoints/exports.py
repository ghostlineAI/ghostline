"""
Book Export API endpoints.

Allows exporting generated books to various formats:
- PDF, EPUB, DOCX, TXT, HTML, Markdown
"""

from uuid import UUID
from typing import Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import io

from app.api import deps
from app.models.generation_task import GenerationTask, TaskStatus
from app.models.project import Project
from app.models.user import User
from app.services.book_export import (
    BookExportService,
    BookMetadata,
    Chapter,
    ExportFormat,
)

router = APIRouter()


class ExportFormatRequest(str, Enum):
    """Export format options."""
    PDF = "pdf"
    EPUB = "epub"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"
    MARKDOWN = "md"


class ExportRequest(BaseModel):
    """Request for book export."""
    format: ExportFormatRequest
    author_name: Optional[str] = None  # Override author name


class ExportAllResponse(BaseModel):
    """Response for export all formats."""
    exports: dict[str, str]  # format -> file path or error


# MIME types for each format
MIME_TYPES = {
    ExportFormat.PDF: "application/pdf",
    ExportFormat.EPUB: "application/epub+zip",
    ExportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ExportFormat.TXT: "text/plain",
    ExportFormat.HTML: "text/html",
    ExportFormat.MARKDOWN: "text/markdown",
}


def _get_chapters_from_task(task: GenerationTask) -> list[Chapter]:
    """Extract chapters from a completed generation task."""
    output_data = task.output_data or {}
    workflow_state = output_data.get("workflow_state", {})
    chapters_data = workflow_state.get("chapters", [])
    
    if not chapters_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No chapters found in task output. Is the generation complete?"
        )
    
    return [
        Chapter(
            number=ch.get("number", i + 1),
            title=ch.get("title", f"Chapter {i + 1}"),
            content=ch.get("content", ""),
            word_count=ch.get("word_count", 0),
        )
        for i, ch in enumerate(chapters_data)
    ]


def _get_metadata_from_project(
    project: Project,
    author_override: Optional[str] = None,
) -> BookMetadata:
    """Create book metadata from project."""
    return BookMetadata(
        title=project.title or "Untitled Book",
        author=author_override or getattr(project, 'author_name', None) or "Anonymous",
        description=project.description or "",
    )


@router.get("/{project_id}/export/{format}")
async def export_book(
    project_id: UUID,
    format: ExportFormatRequest,
    author_name: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Export a generated book to the specified format.
    
    Returns the file as a downloadable attachment.
    
    Supported formats:
    - pdf: Professional print-ready PDF
    - epub: E-reader compatible EPUB
    - docx: Microsoft Word format
    - txt: Plain text
    - html: Web-ready HTML
    - md: Markdown source
    """
    # Verify project exists and user owns it
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Find the latest completed generation task
    task = db.query(GenerationTask).filter(
        GenerationTask.project_id == project_id,
        GenerationTask.status == TaskStatus.COMPLETED
    ).order_by(GenerationTask.completed_at.desc()).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No completed generation found for this project"
        )
    
    # Extract chapters and metadata
    chapters = _get_chapters_from_task(task)
    metadata = _get_metadata_from_project(project, author_name)
    
    # Export
    export_format = ExportFormat(format.value)
    service = BookExportService()
    
    try:
        content = service.export(chapters, metadata, export_format)
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Export format requires additional dependencies: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {e}"
        )
    
    # Create filename
    safe_title = "".join(c for c in project.title if c.isalnum() or c in ' -_').strip()
    safe_title = safe_title.replace(' ', '_')[:50] or "book"
    filename = f"{safe_title}.{format.value}"
    
    # Return as downloadable file
    mime_type = MIME_TYPES.get(export_format, "application/octet-stream")
    
    if isinstance(content, bytes):
        return Response(
            content=content,
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    else:
        return Response(
            content=content.encode('utf-8'),
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )


@router.get("/{project_id}/export")
async def list_available_exports(
    project_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    List available export formats and book info.
    """
    # Verify project exists and user owns it
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Find the latest completed generation task
    task = db.query(GenerationTask).filter(
        GenerationTask.project_id == project_id,
        GenerationTask.status == TaskStatus.COMPLETED
    ).order_by(GenerationTask.completed_at.desc()).first()
    
    if not task:
        return {
            "available": False,
            "message": "No completed generation found for this project",
            "formats": [],
        }
    
    # Get chapter info
    chapters = _get_chapters_from_task(task)
    total_words = sum(c.word_count for c in chapters)
    
    return {
        "available": True,
        "book_info": {
            "title": project.title,
            "chapters": len(chapters),
            "total_words": total_words,
            "estimated_pages": total_words // 250,
            "generated_at": task.completed_at.isoformat() if task.completed_at else None,
        },
        "formats": [
            {
                "format": "pdf",
                "name": "PDF",
                "description": "Professional print-ready document",
                "extension": ".pdf",
            },
            {
                "format": "epub",
                "name": "EPUB",
                "description": "E-reader compatible format (Kindle, Apple Books, etc.)",
                "extension": ".epub",
            },
            {
                "format": "docx",
                "name": "Word Document",
                "description": "Microsoft Word format for editing",
                "extension": ".docx",
            },
            {
                "format": "txt",
                "name": "Plain Text",
                "description": "Simple text format",
                "extension": ".txt",
            },
            {
                "format": "html",
                "name": "HTML",
                "description": "Web-ready format with styling",
                "extension": ".html",
            },
            {
                "format": "md",
                "name": "Markdown",
                "description": "Source format for further editing",
                "extension": ".md",
            },
        ],
    }


@router.post("/{project_id}/task/{task_id}/export-all")
async def export_all_formats(
    project_id: UUID,
    task_id: UUID,
    author_name: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Export book to all available formats.
    
    Returns paths to all exported files on the server.
    """
    # Verify project exists and user owns it
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get the specific task
    task = db.query(GenerationTask).filter(
        GenerationTask.id == task_id,
        GenerationTask.project_id == project_id,
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is not completed (status: {task.status.value})"
        )
    
    # Extract chapters and metadata
    chapters = _get_chapters_from_task(task)
    metadata = _get_metadata_from_project(project, author_name)
    
    # Create output directory
    import os
    output_dir = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "..", "exports",
        str(project_id)
    )
    os.makedirs(output_dir, exist_ok=True)
    
    # Export all formats
    service = BookExportService(output_dir)
    results = service.export_all(chapters, metadata)
    
    return {
        "message": "Export complete",
        "exports": {fmt.value: path for fmt, path in results.items()},
    }

