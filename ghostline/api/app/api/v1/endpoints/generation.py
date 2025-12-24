"""
Generation endpoints for AI-powered book creation.

These endpoints trigger async generation tasks and return task status.
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.models.generation_task import GenerationTask, TaskStatus, TaskType
from app.models.project import Project
from app.models.user import User
from app.tasks.generation import (
    generate_book_task,
    generate_outline_task,
    generate_chapter_task,
    analyze_voice_task,
    resume_workflow_task,
)

router = APIRouter()


class OutlineApprovalRequest(BaseModel):
    """Request to approve or provide feedback on an outline."""
    approve: bool = True
    feedback: Optional[str] = None


class FeedbackRequest(BaseModel):
    """Request to provide feedback on generated content."""
    feedback: str
    target: str = "general"  # "outline", "chapter", "general"
    chapter_number: Optional[int] = None


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
    
    The workflow will:
    1. Ingest and embed source materials
    2. Generate an outline (pauses for approval)
    3. Draft chapters one by one
    4. Apply voice/style editing
    5. Run fact-checking and cohesion analysis
    6. Finalize the book
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
        GenerationTask.status.in_([TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.PAUSED])
    ).first()
    
    if existing_task:
        return {
            "message": "Generation already in progress",
            "task_id": str(existing_task.id),
            "status": existing_task.status.value,
            "progress": existing_task.progress,
            "current_step": existing_task.current_step,
        }
    
    # Create a new generation task
    task = GenerationTask(
        project_id=project_id,
        task_type=TaskType.CHAPTER_GENERATION,
        status=TaskStatus.QUEUED,
        agent_name="orchestrator",
        current_step="Queued for processing...",
        progress=0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Queue the task to Celery for async processing
    generate_book_task.delay(str(task.id))
    
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
    The outline will be generated using the Planner ↔ Critic loop
    for iterative refinement.
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
        status=TaskStatus.QUEUED,
        agent_name="outline_planner",
        current_step="Queued for outline generation...",
        progress=0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Queue to Celery
    generate_outline_task.delay(str(task.id))
    
    return {
        "message": "Outline generation started",
        "task_id": str(task.id),
        "status": task.status.value,
    }


@router.post("/{project_id}/chapter/{chapter_number}")
async def generate_single_chapter(
    project_id: UUID,
    chapter_number: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Generate a single chapter.
    
    This generates one chapter at a time, useful for:
    - Regenerating a specific chapter
    - Manual step-by-step generation
    - Testing and iteration
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
    
    # Create chapter generation task
    task = GenerationTask(
        project_id=project_id,
        task_type=TaskType.CHAPTER_GENERATION,
        status=TaskStatus.QUEUED,
        agent_name="content_drafter",
        current_step=f"Queued for chapter {chapter_number} generation...",
        progress=0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Queue to Celery
    generate_chapter_task.delay(str(task.id), chapter_number)
    
    return {
        "message": f"Chapter {chapter_number} generation started",
        "task_id": str(task.id),
        "status": task.status.value,
    }


@router.post("/{project_id}/analyze-voice")
async def analyze_voice(
    project_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Analyze source materials to create a voice profile.
    
    This extracts stylistic patterns from writing samples
    to ensure generated content matches the author's voice.
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
    
    # Create voice analysis task
    task = GenerationTask(
        project_id=project_id,
        task_type=TaskType.VOICE_ANALYSIS,
        status=TaskStatus.QUEUED,
        agent_name="voice_analyzer",
        current_step="Queued for voice analysis...",
        progress=0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Queue to Celery
    analyze_voice_task.delay(str(task.id))
    
    return {
        "message": "Voice analysis started",
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
            "output_data": task.output_data,
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


@router.post("/tasks/{task_id}/approve-outline")
async def approve_outline(
    task_id: UUID,
    request: OutlineApprovalRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Approve or provide feedback on a generated outline.
    
    When a book generation workflow pauses for outline approval,
    use this endpoint to approve and continue, or provide feedback
    for regeneration.
    """
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
    
    if task.status != TaskStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is not awaiting approval. Current status: {task.status.value}"
        )
    
    # Prepare user input
    user_input = {"approve_outline": request.approve}
    if request.feedback:
        user_input["feedback"] = {"text": request.feedback, "target": "outline"}
    
    # Queue resume task
    resume_workflow_task.delay(str(task.id), user_input)
    
    return {
        "message": "Outline approval processed",
        "task_id": str(task.id),
        "approved": request.approve,
    }


@router.post("/tasks/{task_id}/feedback")
async def provide_feedback(
    task_id: UUID,
    request: FeedbackRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Provide feedback on generated content.
    
    Use this to request changes or improvements to:
    - Outlines
    - Individual chapters
    - The overall book
    """
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
    
    # Store feedback
    feedback_data = {
        "text": request.feedback,
        "target": request.target,
        "chapter_number": request.chapter_number,
    }
    
    # If task is paused, resume with feedback
    if task.status == TaskStatus.PAUSED:
        resume_workflow_task.delay(str(task.id), {"feedback": feedback_data})
        return {
            "message": "Feedback submitted and workflow resumed",
            "task_id": str(task.id),
        }
    
    # Otherwise just store the feedback for later use
    if not task.output_data:
        task.output_data = {}
    if "feedback_history" not in task.output_data:
        task.output_data["feedback_history"] = []
    task.output_data["feedback_history"].append(feedback_data)
    db.commit()
    
    return {
        "message": "Feedback recorded",
        "task_id": str(task.id),
    }


@router.post("/tasks/{task_id}/resume")
async def resume_task(
    task_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Resume a paused task.
    
    Use this after the user has reviewed generated content
    and is ready to proceed without changes.
    """
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
    
    if task.status != TaskStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is not paused. Current status: {task.status.value}"
        )
    
    # Resume the workflow
    resume_workflow_task.delay(str(task.id))
    
    return {
        "message": "Task resumed",
        "task_id": str(task.id),
    }


@router.get("/tasks/{task_id}/conversation-logs")
async def get_conversation_logs(
    task_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get conversation logs for a task.
    
    Returns the full agent conversation history if available.
    """
    import json
    from pathlib import Path
    
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
    
    # Check if task output has conversation log path
    conversation_log = None
    
    if task.output_data and "conversation_log" in task.output_data:
        log_path = Path(task.output_data["conversation_log"])
        if log_path.exists():
            try:
                with open(log_path, 'r') as f:
                    conversation_log = json.load(f)
            except Exception as e:
                print(f"Failed to read conversation log: {e}")
    
    # If no log file, try to find by workflow ID
    if not conversation_log and task.output_data and "workflow_id" in task.output_data:
        logs_dir = Path("../agents/logs/conversations")
        if logs_dir.exists():
            for log_file in logs_dir.glob(f"*{task.output_data['workflow_id']}*.json"):
                try:
                    with open(log_file, 'r') as f:
                        conversation_log = json.load(f)
                    break
                except Exception as e:
                    print(f"Failed to read log file {log_file}: {e}")
    
    if not conversation_log:
        return {
            "session_id": str(task_id),
            "workflow_type": task.task_type.value if task.task_type else "unknown",
            "status": "no_logs",
            "stats": {
                "total_tokens": task.token_usage or 0,
                "total_cost": f"${task.estimated_cost or 0:.4f}",
                "total_duration_ms": 0,
                "total_duration_sec": 0,
                "message_count": 0,
                "agent_calls": {},
            },
            "messages": [],
        }
    
    return conversation_log
