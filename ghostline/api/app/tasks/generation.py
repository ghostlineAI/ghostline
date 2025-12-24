"""
Celery tasks for AI-powered book generation.

These tasks handle the async execution of AI generation workflows.
They are triggered by API endpoints and run in background workers.
"""

from celery import shared_task
from datetime import datetime
from uuid import UUID
import traceback

from app.core.celery_app import celery_app
from app.db.base import SessionLocal
from app.models.generation_task import GenerationTask, TaskStatus
from app.models.project import Project
from app.services.workflow_service import WorkflowService


def get_db_session():
    """Get a database session for task execution."""
    return SessionLocal()


@celery_app.task(bind=True, name="app.tasks.generate_book")
def generate_book_task(self, task_id: str):
    """
    Generate a complete book from source materials.
    
    This is the main orchestration task that coordinates:
    1. Outline generation
    2. Chapter-by-chapter drafting
    3. Voice/style consistency
    4. Quality checks
    
    Uses LangGraph BookGenerationWorkflow for durable execution
    with pause/resume capabilities.
    """
    db = get_db_session()
    try:
        task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if not task:
            return {"error": "Task not found"}
        
        # Update status to running
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.current_step = "Starting book generation workflow..."
        db.commit()
        
        # Get the project
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if not project:
            task.status = TaskStatus.FAILED
            task.error_message = "Project not found"
            db.commit()
            return {"error": "Project not found"}
        
        # Initialize workflow service and start generation
        workflow_service = WorkflowService(db)
        result = workflow_service.start_book_generation(task=task, project=project)
        
        # Note: The task may be in PAUSED status if waiting for user approval
        # The status is updated by the workflow_service
        
        return {
            "status": task.status.value,
            "task_id": task_id,
            "workflow_id": result.get("workflow_id"),
            "progress": task.progress,
            "current_step": task.current_step,
        }
        
    except Exception as e:
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = f"{str(e)}\n{traceback.format_exc()}"
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.generate_outline")
def generate_outline_task(self, task_id: str):
    """
    Generate a book outline from source materials.
    
    Uses the OutlineSubgraph with bounded Planner ↔ Critic conversation
    to create a structured outline for user approval.
    """
    db = get_db_session()
    try:
        task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if not task:
            return {"error": "Task not found"}
        
        # Update status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.current_step = "Analyzing source materials..."
        task.progress = 10
        db.commit()
        
        # Get the project
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if not project:
            task.status = TaskStatus.FAILED
            task.error_message = "Project not found"
            db.commit()
            return {"error": "Project not found"}
        
        # Initialize workflow service and generate outline
        workflow_service = WorkflowService(db)
        result = workflow_service.generate_outline(task=task, project=project)
        
        return {
            "status": "completed",
            "task_id": task_id,
            "outline": result.get("outline"),
            "iterations": result.get("iterations", 0),
            "tokens_used": result.get("tokens_used", 0),
            "cost": result.get("cost", 0.0),
        }
        
    except Exception as e:
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = f"{str(e)}\n{traceback.format_exc()}"
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.generate_chapter")
def generate_chapter_task(self, task_id: str, chapter_number: int, chapter_outline: dict = None):
    """
    Generate a single chapter based on outline and source materials.
    
    Uses the ChapterSubgraph with bounded Drafter ↔ Voice ↔ FactCheck
    conversation to create high-quality chapter content.
    """
    db = get_db_session()
    try:
        task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if not task:
            return {"error": "Task not found"}
        
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.current_step = f"Drafting chapter {chapter_number}..."
        db.commit()
        
        # Get the project
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if not project:
            task.status = TaskStatus.FAILED
            task.error_message = "Project not found"
            db.commit()
            return {"error": "Project not found"}
        
        # If no chapter_outline provided, try to get from project's existing outline
        if not chapter_outline:
            # Look for an existing outline in a previous task
            outline_task = db.query(GenerationTask).filter(
                GenerationTask.project_id == project.id,
                GenerationTask.status == TaskStatus.COMPLETED,
            ).order_by(GenerationTask.created_at.desc()).first()
            
            if outline_task and outline_task.output_data:
                outline = outline_task.output_data.get("outline", {})
                chapters = outline.get("chapters", [])
                if chapters and chapter_number <= len(chapters):
                    chapter_outline = chapters[chapter_number - 1]
        
        if not chapter_outline:
            chapter_outline = {
                "number": chapter_number,
                "title": f"Chapter {chapter_number}",
                "summary": "Auto-generated chapter",
            }
        
        # Initialize workflow service and generate chapter
        workflow_service = WorkflowService(db)
        result = workflow_service.generate_chapter(
            task=task,
            project=project,
            chapter_number=chapter_number,
            chapter_outline=chapter_outline,
        )
        
        return {
            "status": "completed",
            "task_id": task_id,
            "chapter": chapter_number,
            "word_count": result.get("word_count", 0),
            "voice_score": result.get("voice_score", 0.0),
            "fact_score": result.get("fact_score", 0.0),
            "cohesion_score": result.get("cohesion_score", 0.0),
        }
        
    except Exception as e:
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = f"{str(e)}\n{traceback.format_exc()}"
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.analyze_voice")
def analyze_voice_task(self, task_id: str):
    """
    Analyze source materials to create a voice profile.
    
    Uses sentence-transformers to:
    1. Generate embeddings from writing samples
    2. Extract stylistic patterns
    3. Create a VoiceProfile for the project
    """
    db = get_db_session()
    try:
        task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if not task:
            return {"error": "Task not found"}
        
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.current_step = "Analyzing writing style..."
        db.commit()
        
        # Get project and source materials
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if not project:
            task.status = TaskStatus.FAILED
            task.error_message = "Project not found"
            db.commit()
            return {"error": "Project not found"}
        
        # Import services
        from app.services.embeddings import EmbeddingService
        from app.services.document_processor import DocumentProcessor
        from app.models.source_material import SourceMaterial
        
        embedding_service = EmbeddingService()
        doc_processor = DocumentProcessor()
        
        # Get writing samples
        source_materials = db.query(SourceMaterial).filter(
            SourceMaterial.project_id == project.id
        ).all()
        
        task.progress = 20
        task.current_step = "Extracting text from samples..."
        db.commit()
        
        # Extract text and generate embeddings
        all_text = []
        for sm in source_materials:
            if sm.file_path:
                try:
                    # Extract text
                    chunks = doc_processor.process_file(sm.file_path)
                    for chunk in chunks:
                        all_text.append(chunk["content"])
                except Exception:
                    # Skip files that can't be processed
                    pass
        
        task.progress = 50
        task.current_step = "Generating voice embeddings..."
        db.commit()
        
        # Generate embeddings for voice analysis
        if all_text:
            embeddings = embedding_service.embed_batch(all_text[:100])  # Max 100 chunks
            
            # Simple voice profile: average embedding
            import numpy as np
            avg_embedding = np.mean(embeddings, axis=0).tolist()
            
            voice_profile = {
                "embedding": avg_embedding,
                "sample_count": len(all_text),
                "avg_sentence_length": sum(len(t.split()) for t in all_text) / len(all_text) if all_text else 0,
            }
        else:
            voice_profile = {
                "embedding": None,
                "sample_count": 0,
                "avg_sentence_length": 0,
            }
        
        task.output_data = task.output_data or {}
        task.output_data["voice_profile"] = voice_profile
        
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.progress = 100
        task.current_step = "Voice analysis complete"
        db.commit()
        
        return {"status": "completed", "task_id": task_id, "voice_profile": voice_profile}
        
    except Exception as e:
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = f"{str(e)}\n{traceback.format_exc()}"
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.resume_workflow")
def resume_workflow_task(self, task_id: str, user_input: dict = None):
    """
    Resume a paused workflow.
    
    Called when user provides input (e.g., outline approval, feedback).
    """
    db = get_db_session()
    try:
        task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if not task:
            return {"error": "Task not found"}
        
        if task.status != TaskStatus.PAUSED:
            return {"error": f"Task is not paused, current status: {task.status.value}"}
        
        task.current_step = "Resuming workflow..."
        db.commit()
        
        # Initialize workflow service and resume
        workflow_service = WorkflowService(db)
        result = workflow_service.resume_workflow(task=task, user_input=user_input)
        
        return {
            "status": task.status.value,
            "task_id": task_id,
            "progress": task.progress,
            "current_step": task.current_step,
        }
        
    except Exception as e:
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = f"{str(e)}\n{traceback.format_exc()}"
            db.commit()
        raise
    finally:
        db.close()
