"""
Generation endpoints for AI-powered book creation.

These endpoints trigger async generation tasks and return task status.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.generation_task import GenerationTask, TaskStatus, TaskType
from app.models.project import Project
from app.models.user import User

router = APIRouter()


@router.post("/{project_id}/generate")
async def start_book_generation(
    project_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Start the full book generation process for a project.
    
    This creates a generation task and queues it for async processing.
    The frontend can poll the task status endpoint to track progress.
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
    
    # Check if there's already a running generation task
    existing_task = db.query(GenerationTask).filter(
        GenerationTask.project_id == project_id,
        GenerationTask.status.in_([TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING])
    ).first()
    
    if existing_task:
        return {
            "message": "Generation already in progress",
            "task_id": str(existing_task.id),
            "status": existing_task.status.value,
            "progress": existing_task.progress,
        }
    
    # Create a new generation task
    task = GenerationTask(
        project_id=project_id,
        task_type=TaskType.CHAPTER_GENERATION,
        status=TaskStatus.PENDING,
        agent_name="orchestrator",
        current_step="Initializing book generation...",
        progress=0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # TODO: Queue the task to Celery for async processing
    # from app.tasks.generation import generate_book_task
    # generate_book_task.delay(str(task.id))
    
    return {
        "message": "Book generation started",
        "task_id": str(task.id),
        "status": task.status.value,
        "progress": task.progress,
    }


@router.post("/{project_id}/outline")
async def generate_outline(
    project_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Generate a book outline from source materials.
    
    This is typically the first step before chapter generation.
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
    
    # Create outline generation task
    task = GenerationTask(
        project_id=project_id,
        task_type=TaskType.OUTLINE_GENERATION,
        status=TaskStatus.PENDING,
        agent_name="outline_planner",
        current_step="Analyzing source materials...",
        progress=0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # TODO: Queue to Celery
    # from app.tasks.generation import generate_outline_task
    # generate_outline_task.delay(str(task.id))
    
    return {
        "message": "Outline generation started",
        "task_id": str(task.id),
        "status": task.status.value,
    }


@router.get("/{project_id}/tasks")
async def get_project_tasks(
    project_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Get all generation tasks for a project."""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    tasks = db.query(GenerationTask).filter(
        GenerationTask.project_id == project_id
    ).order_by(GenerationTask.created_at.desc()).all()
    
    return [
        {
            "id": str(task.id),
            "task_type": task.task_type.value,
            "status": task.status.value,
            "progress": task.progress,
            "current_step": task.current_step,
            "agent_name": task.agent_name,
            "token_usage": task.token_usage,
            "estimated_cost": task.estimated_cost,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
        for task in tasks
    ]


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Get the status of a specific generation task."""
    task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Verify user owns the project
    project = db.query(Project).filter(
        Project.id == task.project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return {
        "id": str(task.id),
        "project_id": str(task.project_id),
        "task_type": task.task_type.value,
        "status": task.status.value,
        "progress": task.progress,
        "current_step": task.current_step,
        "agent_name": task.agent_name,
        "token_usage": task.token_usage,
        "estimated_cost": task.estimated_cost,
        "error_message": task.error_message,
        "output_data": task.output_data,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }

