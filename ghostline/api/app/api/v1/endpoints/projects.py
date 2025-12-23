"""Project management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.api import deps
from app.models.book_outline import BookOutline
from app.models.chapter import Chapter
from app.models.project import BookGenre, Project, ProjectStatus
from app.models.source_material import SourceMaterial
from app.models.user import User

router = APIRouter()


def project_to_response(project: Project, db: Session) -> dict:
    """Convert Project model to response format."""
    # Add computed fields
    chapter_count = (
        db.query(Chapter).filter(Chapter.project_id == project.id).count()
    )
    word_count = (
        db.query(Chapter)
        .filter(Chapter.project_id == project.id)
        .with_entities(func.sum(Chapter.word_count))
        .scalar()
        or 0
    )
    
    return {
        "id": str(project.id),
        "title": project.title,
        "description": project.description,
        "user_id": str(project.owner_id),
        "status": project.status.value if hasattr(project.status, 'value') else str(project.status),
        "genre": project.genre.value if project.genre and hasattr(project.genre, 'value') else None,
        "created_at": project.created_at,
        "updated_at": project.updated_at or project.created_at,
        "chapter_count": chapter_count,
        "word_count": word_count,
    }


@router.get("/")
def list_projects(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
):
    """List all projects for the current user."""
    projects = (
        db.query(Project)
        .filter(Project.owner_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [project_to_response(project, db) for project in projects]


@router.post("/")
def create_project(
    project_data: dict,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Create a new project."""
    # Map genre string to enum
    genre_str = project_data.get('genre', 'other')
    genre_map = {
        'fiction': BookGenre.FICTION,
        'non_fiction': BookGenre.NON_FICTION,
        'biography': BookGenre.MEMOIR,
        'memoir': BookGenre.MEMOIR,
        'business': BookGenre.BUSINESS,
        'self_help': BookGenre.SELF_HELP,
        'academic': BookGenre.ACADEMIC,
        'technical': BookGenre.TECHNICAL,
        'other': BookGenre.OTHER,
    }
    genre_enum = genre_map.get(genre_str.lower(), BookGenre.OTHER)
    
    db_project = Project(
        title=project_data.get('title', 'Untitled Project'),
        description=project_data.get('description'),
        owner_id=current_user.id,
        status=ProjectStatus.DRAFT,
        genre=genre_enum,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return project_to_response(db_project, db)


@router.get("/{project_id}")
def get_project(
    project_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Get a specific project."""
    project = (
        db.query(Project)
        .filter(and_(Project.id == project_id, Project.owner_id == current_user.id))
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    return project_to_response(project, db)


@router.patch("/{project_id}")
def update_project(
    project_id: str,
    project_update: dict,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Update a project."""
    project = (
        db.query(Project)
        .filter(and_(Project.id == project_id, Project.owner_id == current_user.id))
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    # Update fields
    if 'title' in project_update:
        project.title = project_update['title']
    if 'description' in project_update:
        project.description = project_update['description']
    if 'status' in project_update:
        project.status = ProjectStatus(project_update['status'])

    db.commit()
    db.refresh(project)
    return project_to_response(project, db)


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Delete a project and all associated data."""
    project = (
        db.query(Project)
        .filter(and_(Project.id == project_id, Project.owner_id == current_user.id))
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    db.delete(project)
    db.commit()
    return {"detail": "Project deleted successfully"}


@router.post("/{project_id}/fork")
def fork_project(
    project_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Fork (duplicate) a project."""
    project = (
        db.query(Project)
        .filter(and_(Project.id == project_id, Project.owner_id == current_user.id))
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    # Create forked project
    forked = Project(
        title=f"{project.title} (Copy)",
        description=project.description,
        owner_id=current_user.id,
        status=ProjectStatus.DRAFT,
        genre=project.genre,
        forked_from_project_id=project.id,
    )
    db.add(forked)
    db.commit()
    db.refresh(forked)

    return project_to_response(forked, db)


@router.get("/{project_id}/source-materials")
def list_source_materials(
    project_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """List all source materials for a project."""
    # Verify project ownership
    project = (
        db.query(Project)
        .filter(and_(Project.id == project_id, Project.owner_id == current_user.id))
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    materials = (
        db.query(SourceMaterial).filter(SourceMaterial.project_id == project_id).all()
    )

    return [
        {
            "id": str(material.id),
            "filename": material.filename,
            "material_type": material.material_type.value if hasattr(material.material_type, 'value') else str(material.material_type),
            "file_size": material.file_size,
            "mime_type": material.mime_type,
            "processing_status": material.processing_status.value if hasattr(material.processing_status, 'value') else str(material.processing_status),
            "created_at": material.created_at.isoformat() if material.created_at else None,
            "s3_url": material.s3_url,
        }
        for material in materials
    ]


@router.get("/{project_id}/chapters")
def get_project_chapters(
    project_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Get all chapters for a project."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == current_user.id)
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    chapters = (
        db.query(Chapter)
        .filter(Chapter.project_id == project_id)
        .order_by(Chapter.order)
        .all()
    )

    return [
        {
            "id": str(chapter.id),
            "chapter_number": chapter.order,
            "title": chapter.title,
            "content": chapter.content,
            "status": chapter.status,
            "word_count": chapter.word_count,
            "created_at": chapter.created_at.isoformat() if chapter.created_at else None,
        }
        for chapter in chapters
    ]


@router.get("/{project_id}/outline")
def get_project_outline(
    project_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Get project outline."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == current_user.id)
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    outline = db.query(BookOutline).filter(BookOutline.project_id == project_id).first()

    if not outline:
        return {"chapters": []}

    return {
        "id": str(outline.id),
        "structure": outline.structure,
        "created_at": outline.created_at.isoformat() if outline.created_at else None,
    }

