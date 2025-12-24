"""
Workflow Service - Bridge between API and LangGraph agents.

This service provides the API layer with access to the book generation
workflows while handling persistence and state management.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
from uuid import UUID
import json
import os

from sqlalchemy.orm import Session

# Add agents module to path
AGENTS_PATH = Path(__file__).parent.parent.parent.parent / "agents"
if str(AGENTS_PATH) not in sys.path:
    sys.path.insert(0, str(AGENTS_PATH))

from app.models.generation_task import GenerationTask, TaskStatus
from app.models.project import Project
from app.models.source_material import SourceMaterial


class WorkflowService:
    """
    Service for managing book generation workflows.
    
    Responsibilities:
    - Starting and resuming LangGraph workflows
    - Persisting workflow state to database
    - Tracking progress and costs
    - Handling user feedback/approval gates
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._workflow = None
        self._outline_subgraph = None
        self._chapter_subgraph = None
    
    @property
    def workflow(self):
        """Lazy load the workflow to avoid import issues."""
        if self._workflow is None:
            from orchestrator.workflow import BookGenerationWorkflow
            self._workflow = BookGenerationWorkflow()
        return self._workflow
    
    @property
    def outline_subgraph(self):
        """Lazy load outline subgraph."""
        if self._outline_subgraph is None:
            from orchestrator.subgraphs import OutlineSubgraph
            self._outline_subgraph = OutlineSubgraph()
        return self._outline_subgraph
    
    @property
    def chapter_subgraph(self):
        """Lazy load chapter subgraph."""
        if self._chapter_subgraph is None:
            from orchestrator.subgraphs import ChapterSubgraph
            self._chapter_subgraph = ChapterSubgraph()
        return self._chapter_subgraph
    
    def start_book_generation(
        self,
        task: GenerationTask,
        project: Project,
    ) -> dict:
        """
        Start the full book generation workflow.
        
        Args:
            task: The GenerationTask to track progress
            project: The project to generate a book for
            
        Returns:
            Dict with workflow_id and initial state
        """
        # Get source materials for the project
        source_materials = self.db.query(SourceMaterial).filter(
            SourceMaterial.project_id == project.id
        ).all()
        
        source_material_ids = [str(sm.id) for sm in source_materials]
        
        # Start the workflow
        result = self.workflow.start(
            project_id=str(project.id),
            user_id=str(project.owner_id),
            source_material_ids=source_material_ids,
        )
        
        # Store workflow_id in task output_data
        task.output_data = task.output_data or {}
        task.output_data["workflow_id"] = result["workflow_id"]
        task.output_data["workflow_state"] = result["state"]
        
        # Update task progress based on workflow state
        state = result["state"]
        task.progress = state.get("progress", 0)
        task.current_step = state.get("current_step", "Running workflow...")
        
        # Check if workflow paused for user action
        if state.get("pending_user_action"):
            task.status = TaskStatus.PAUSED
            task.current_step = f"Waiting for: {state['pending_user_action']}"
        elif state.get("phase") == "completed":
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
        
        self.db.commit()
        
        return result
    
    def resume_workflow(
        self,
        task: GenerationTask,
        user_input: Optional[dict] = None,
    ) -> dict:
        """
        Resume a paused workflow.
        
        Args:
            task: The paused GenerationTask
            user_input: Optional user input (e.g., outline approval)
            
        Returns:
            Dict with workflow state
        """
        workflow_id = task.output_data.get("workflow_id") if task.output_data else None
        
        if not workflow_id:
            raise ValueError("No workflow_id found in task output_data")
        
        # Resume the workflow
        result = self.workflow.resume(
            workflow_id=workflow_id,
            user_input=user_input,
        )
        
        # Update task state
        state = result["state"]
        task.output_data["workflow_state"] = state
        task.progress = state.get("progress", 0)
        task.current_step = state.get("current_step", "Running workflow...")
        task.status = TaskStatus.RUNNING
        
        # Check if workflow paused again or completed
        if state.get("pending_user_action"):
            task.status = TaskStatus.PAUSED
            task.current_step = f"Waiting for: {state['pending_user_action']}"
        elif state.get("phase") == "completed":
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.progress = 100
        elif state.get("phase") == "failed":
            task.status = TaskStatus.FAILED
            task.error_message = state.get("error", "Workflow failed")
        
        self.db.commit()
        
        return result
    
    def generate_outline(
        self,
        task: GenerationTask,
        project: Project,
    ) -> dict:
        """
        Generate a book outline using the OutlineSubgraph.
        
        This runs the Planner ↔ Critic bounded conversation.
        
        Args:
            task: The GenerationTask to track progress
            project: The project to generate outline for
            
        Returns:
            Dict with generated outline
        """
        # Get source materials
        source_materials = self.db.query(SourceMaterial).filter(
            SourceMaterial.project_id == project.id
        ).all()
        
        # Create summaries from source materials
        # In real implementation, these would be extracted/embedded chunks
        source_summaries = []
        for sm in source_materials:
            summary = f"Source: {sm.original_filename}"
            if sm.metadata:
                meta = sm.metadata if isinstance(sm.metadata, dict) else json.loads(sm.metadata)
                if "summary" in meta:
                    summary += f"\n{meta['summary']}"
            source_summaries.append(summary)
        
        # Update task status
        task.current_step = "Running outline generation..."
        task.progress = 20
        self.db.commit()
        
        # Run the outline subgraph
        result = self.outline_subgraph.run(
            source_summaries=source_summaries,
            project_title=project.name,
            project_description=project.description or "",
            target_chapters=10,  # Could be configurable
            voice_guidance="",
        )
        
        # Store results
        task.output_data = task.output_data or {}
        task.output_data["outline"] = result["outline"]
        task.output_data["iterations"] = result["iterations"]
        task.output_data["tokens_used"] = result["tokens_used"]
        task.output_data["cost"] = result["cost"]
        
        task.progress = 100
        task.current_step = "Outline generation complete"
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.token_usage = result["tokens_used"]
        task.estimated_cost = result["cost"]
        
        self.db.commit()
        
        return result
    
    def generate_chapter(
        self,
        task: GenerationTask,
        project: Project,
        chapter_number: int,
        chapter_outline: dict,
        source_chunks: list[str] = None,
        previous_summaries: list[str] = None,
        voice_profile: dict = None,
    ) -> dict:
        """
        Generate a single chapter using the ChapterSubgraph.
        
        This runs the Drafter ↔ Voice ↔ FactCheck bounded conversation.
        
        Args:
            task: The GenerationTask to track progress
            project: The project
            chapter_number: Which chapter to generate
            chapter_outline: The chapter's outline/plan
            source_chunks: Relevant source material chunks
            previous_summaries: Summaries of previous chapters
            voice_profile: Voice/style profile to match
            
        Returns:
            Dict with generated chapter content
        """
        task.current_step = f"Drafting chapter {chapter_number}..."
        task.progress = 10
        self.db.commit()
        
        # Run the chapter subgraph
        result = self.chapter_subgraph.run(
            chapter_outline=chapter_outline,
            source_chunks=source_chunks or [],
            previous_summaries=previous_summaries or [],
            voice_profile=voice_profile or {},
            target_words=3000,  # Could be configurable
        )
        
        # Store results
        task.output_data = task.output_data or {}
        task.output_data["chapter"] = {
            "number": chapter_number,
            "content": result["content"],
            "word_count": result["word_count"],
            "voice_score": result["voice_score"],
            "fact_score": result["fact_score"],
            "cohesion_score": result["cohesion_score"],
        }
        task.output_data["iterations"] = result["iterations"]
        task.output_data["tokens_used"] = result["tokens_used"]
        task.output_data["cost"] = result["cost"]
        
        task.progress = 100
        task.current_step = f"Chapter {chapter_number} complete"
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.token_usage = result["tokens_used"]
        task.estimated_cost = result["cost"]
        
        self.db.commit()
        
        return result
    
    def get_workflow_state(self, task: GenerationTask) -> dict:
        """Get the current workflow state for a task."""
        if task.output_data and "workflow_id" in task.output_data:
            workflow_id = task.output_data["workflow_id"]
            return self.workflow.get_state(workflow_id)
        return {}
    
    def approve_outline(self, task: GenerationTask) -> dict:
        """
        Approve the outline and resume the workflow.
        
        This is called when the user approves the generated outline,
        allowing the workflow to proceed to chapter drafting.
        """
        return self.resume_workflow(
            task=task,
            user_input={"approve_outline": True},
        )
    
    def provide_feedback(
        self,
        task: GenerationTask,
        feedback: dict,
    ) -> dict:
        """
        Provide feedback on generated content.
        
        Args:
            task: The task receiving feedback
            feedback: Dict with feedback details
            
        Returns:
            Updated workflow state
        """
        return self.resume_workflow(
            task=task,
            user_input={"feedback": feedback},
        )

