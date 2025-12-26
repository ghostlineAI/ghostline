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

    def _push_cost_context(
        self,
        *,
        project_id: UUID,
        task_id: Optional[UUID],
        workflow_run_id: Optional[str],
        chapter_number: Optional[int] = None,
    ):
        """
        Ensure cost tracking is enabled for *all* agent calls in this workflow invocation.
        
        This is critical for non-Celery/synchronous runs (scripts, direct service calls),
        where the Celery task wrapper isn't present to set the context.
        """
        try:
            from agents.base.agent import set_cost_context

            return set_cost_context(
                project_id=project_id,
                task_id=task_id,
                workflow_run_id=workflow_run_id,
                chapter_number=chapter_number,
                db_session=self.db,
            )
        except Exception:
            return None

    def _pop_cost_context(self, token):
        """Pop/restore the previous cost context (safe for nesting)."""
        if token is None:
            return
        try:
            from agents.base.agent import clear_cost_context

            clear_cost_context(token)
        except Exception:
            pass
    
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
        
        # Get page/chapter configuration from task input_data
        input_data = task.input_data or {}
        target_pages = input_data.get("target_pages")
        target_chapters = input_data.get("target_chapters", 3)
        words_per_page = input_data.get("words_per_page", 250)
        
        token = self._push_cost_context(
            project_id=project.id,
            task_id=task.id,
            workflow_run_id=f"book_{task.id}",
        )
        try:
            # Start the workflow with page configuration
            result = self.workflow.start(
                project_id=str(project.id),
                user_id=str(project.owner_id),
                source_material_ids=source_material_ids,
                target_pages=target_pages,
                target_chapters=target_chapters,
                words_per_page=words_per_page,
            )
        finally:
            self._pop_cost_context(token)
        
        # Store workflow_id in task output_data
        existing_output = task.output_data or {}
        task.output_data = {
            **dict(existing_output),
            "workflow_id": result.get("workflow_id"),
            "workflow_state": result.get("state"),
            "conversation_log": result.get("conversation_log"),
        }
        
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
        
        token = self._push_cost_context(
            project_id=task.project_id,
            task_id=task.id,
            workflow_run_id=f"resume_{workflow_id}",
        )
        try:
            # Resume the workflow
            result = self.workflow.resume(
                workflow_id=workflow_id,
                user_input=user_input,
            )
        finally:
            self._pop_cost_context(token)
        
        # Update task state
        state = result["state"]
        existing_output = task.output_data or {}
        task.output_data = {
            **dict(existing_output),
            "workflow_state": state,
            "conversation_log": result.get("conversation_log"),
        }
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
            summary = f"Source: {sm.filename}"
            if sm.file_metadata:
                meta = sm.file_metadata if isinstance(sm.file_metadata, dict) else json.loads(sm.file_metadata)
                if "summary" in meta:
                    summary += f"\n{meta['summary']}"
            source_summaries.append(summary)
        
        # Update task status
        task.current_step = "Running outline generation..."
        task.progress = 20
        self.db.commit()
        
        token = self._push_cost_context(
            project_id=project.id,
            task_id=task.id,
            workflow_run_id=f"outline_{task.id}",
        )
        try:
            # Run the outline subgraph
            input_data = task.input_data or {}
            target_chapters = int(input_data.get("target_chapters") or 10)
            result = self.outline_subgraph.run(
                source_summaries=source_summaries,
                project_title=project.title,
                project_description=project.description or "",
                target_chapters=target_chapters,
                voice_guidance="",
            )
        finally:
            self._pop_cost_context(token)
        
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
        source_chunks_with_citations: list[dict] = None,
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
        
        token = self._push_cost_context(
            project_id=project.id,
            task_id=task.id,
            workflow_run_id=f"chapter_{task.id}_ch{chapter_number}",
            chapter_number=chapter_number,
        )
        try:
            # Run the chapter subgraph
            input_data = task.input_data or {}
            # Optional: allow callers to specify approximate length targets
            target_words = int(input_data.get("target_words") or 3000)
            result = self.chapter_subgraph.run(
                chapter_outline=chapter_outline,
                source_chunks=source_chunks or [],
                source_chunks_with_citations=source_chunks_with_citations or [],
                previous_summaries=previous_summaries or [],
                voice_profile=voice_profile or {},
                target_words=target_words,
                project_id=str(project.id),
            )
        finally:
            self._pop_cost_context(token)
        
        # Store results
        task.output_data = task.output_data or {}
        quality_gates_passed = bool(result.get("quality_gates_passed", False))
        task.output_data["chapter"] = {
            "number": chapter_number,
            "content": result["content"],
            "content_clean": result.get("content_clean"),
            "word_count": result["word_count"],
            "voice_score": result["voice_score"],
            "fact_score": result["fact_score"],
            "cohesion_score": result["cohesion_score"],
            "citations": result.get("citations", []),
            "citation_report": result.get("citation_report", {}),
            "claim_mappings": result.get("claim_mappings", []),
            "quality_gates_passed": quality_gates_passed,
            "quality_gate_report": result.get("quality_gate_report") or {},
            "revision_history": result.get("revision_history") or [],
        }
        task.output_data["iterations"] = result["iterations"]
        task.output_data["tokens_used"] = result["tokens_used"]
        task.output_data["cost"] = result["cost"]
        
        task.progress = 100
        task.current_step = f"Chapter {chapter_number} complete"
        strict_mode = str(os.getenv("GHOSTLINE_STRICT_MODE", "")).strip().lower() in ("1", "true", "yes", "on")
        if strict_mode and not quality_gates_passed:
            task.status = TaskStatus.FAILED
            task.error_message = (
                f"Chapter {chapter_number} quality gates not met: "
                f"{result.get('quality_gate_report') or {}}"
            )
        else:
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
            user_input={
                "approve_outline": True,
                "project_id": str(task.project_id),  # Ensure project_id is preserved on resume
            },
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


