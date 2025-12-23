"""
Main LangGraph workflow for book generation.

This is the outer graph that coordinates the full pipeline:
  Ingest → Embed → OutlineSubgraph → UserApproveOutline → 
  DraftChapterSubgraph (loop) → UserEdits → Finalize → Export
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Annotated, Optional, TypedDict
from uuid import UUID, uuid4

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field


class WorkflowPhase(str, Enum):
    """Phases of the book generation workflow."""
    INITIALIZED = "initialized"
    INGESTING = "ingesting"
    EMBEDDING = "embedding"
    OUTLINE_GENERATION = "outline_generation"
    OUTLINE_REVIEW = "outline_review"
    DRAFTING = "drafting"
    EDITING = "editing"
    REVIEWING = "reviewing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"


class WorkflowState(TypedDict, total=False):
    """
    State for the book generation workflow.
    
    This state is persisted at checkpoints and passed between nodes.
    """
    # Identifiers
    workflow_id: str
    project_id: str
    user_id: str
    
    # Phase tracking
    phase: str
    current_step: str
    progress: int  # 0-100
    
    # Source materials
    source_material_ids: list[str]
    source_chunks: list[dict]  # {id, content, embedding}
    voice_profile: Optional[dict]
    
    # Outline
    outline: Optional[dict]
    outline_approved: bool
    outline_feedback: list[str]
    
    # Chapters
    chapters: list[dict]  # {number, title, content, status}
    current_chapter: int
    chapter_summaries: list[str]
    
    # Quality tracking
    voice_scores: list[float]
    fact_check_scores: list[float]
    cohesion_scores: list[float]
    
    # Cost tracking
    total_tokens: int
    total_cost: float
    
    # User interaction
    pending_user_action: Optional[str]
    user_feedback: list[dict]
    
    # Timestamps
    started_at: str
    last_updated: str
    completed_at: Optional[str]
    
    # Errors
    error: Optional[str]


def create_initial_state(
    project_id: str,
    user_id: str,
    source_material_ids: list[str],
) -> WorkflowState:
    """Create initial workflow state."""
    return WorkflowState(
        workflow_id=str(uuid4()),
        project_id=project_id,
        user_id=user_id,
        phase=WorkflowPhase.INITIALIZED.value,
        current_step="Initializing workflow",
        progress=0,
        source_material_ids=source_material_ids,
        source_chunks=[],
        voice_profile=None,
        outline=None,
        outline_approved=False,
        outline_feedback=[],
        chapters=[],
        current_chapter=0,
        chapter_summaries=[],
        voice_scores=[],
        fact_check_scores=[],
        cohesion_scores=[],
        total_tokens=0,
        total_cost=0.0,
        pending_user_action=None,
        user_feedback=[],
        started_at=datetime.utcnow().isoformat(),
        last_updated=datetime.utcnow().isoformat(),
        completed_at=None,
        error=None,
    )


# Node functions for the workflow
def ingest_sources(state: WorkflowState) -> WorkflowState:
    """Load and process source materials."""
    state["phase"] = WorkflowPhase.INGESTING.value
    state["current_step"] = "Loading source materials"
    state["progress"] = 5
    state["last_updated"] = datetime.utcnow().isoformat()
    
    # In real implementation, this would:
    # 1. Load source materials from database
    # 2. Extract text using DocumentProcessor
    # 3. Store extracted content
    
    return state


def embed_sources(state: WorkflowState) -> WorkflowState:
    """Generate embeddings for source chunks."""
    state["phase"] = WorkflowPhase.EMBEDDING.value
    state["current_step"] = "Generating embeddings"
    state["progress"] = 15
    state["last_updated"] = datetime.utcnow().isoformat()
    
    # In real implementation, this would:
    # 1. Chunk source text
    # 2. Generate embeddings using EmbeddingService
    # 3. Store in vector database
    
    return state


def generate_outline(state: WorkflowState) -> WorkflowState:
    """Generate book outline using OutlineSubgraph."""
    state["phase"] = WorkflowPhase.OUTLINE_GENERATION.value
    state["current_step"] = "Generating book outline"
    state["progress"] = 25
    state["last_updated"] = datetime.utcnow().isoformat()
    
    # In real implementation, this would:
    # 1. Run OutlineSubgraph (Planner ↔ Critic loop)
    # 2. Store generated outline
    
    # Placeholder outline
    if not state.get("outline"):
        state["outline"] = {
            "title": "Generated Book",
            "chapters": [
                {"number": i+1, "title": f"Chapter {i+1}", "summary": "TBD"}
                for i in range(10)
            ]
        }
    
    return state


def request_outline_approval(state: WorkflowState) -> WorkflowState:
    """Pause for user to approve outline."""
    state["phase"] = WorkflowPhase.OUTLINE_REVIEW.value
    state["current_step"] = "Waiting for outline approval"
    state["pending_user_action"] = "approve_outline"
    state["progress"] = 30
    state["last_updated"] = datetime.utcnow().isoformat()
    
    return state


def draft_chapter(state: WorkflowState) -> WorkflowState:
    """Draft the current chapter."""
    current = state.get("current_chapter", 0)
    state["phase"] = WorkflowPhase.DRAFTING.value
    state["current_step"] = f"Drafting chapter {current + 1}"
    state["last_updated"] = datetime.utcnow().isoformat()
    
    # Calculate progress (chapters are 30-90% of work)
    total_chapters = len(state.get("outline", {}).get("chapters", []))
    if total_chapters > 0:
        chapter_progress = (current / total_chapters) * 60  # 60% for all chapters
        state["progress"] = int(30 + chapter_progress)
    
    # In real implementation, this would:
    # 1. Get chapter outline
    # 2. Retrieve relevant source chunks
    # 3. Run ChapterSubgraph (Drafter ↔ Voice ↔ FactCheck)
    # 4. Store chapter content
    
    return state


def edit_chapter(state: WorkflowState) -> WorkflowState:
    """Edit chapter for voice and quality."""
    state["phase"] = WorkflowPhase.EDITING.value
    state["current_step"] = f"Editing chapter {state.get('current_chapter', 0) + 1}"
    state["last_updated"] = datetime.utcnow().isoformat()
    
    return state


def review_chapter(state: WorkflowState) -> WorkflowState:
    """Review chapter with fact-check and cohesion analysis."""
    state["phase"] = WorkflowPhase.REVIEWING.value
    state["current_step"] = f"Reviewing chapter {state.get('current_chapter', 0) + 1}"
    state["last_updated"] = datetime.utcnow().isoformat()
    
    return state


def finalize_book(state: WorkflowState) -> WorkflowState:
    """Finalize the complete book."""
    state["phase"] = WorkflowPhase.FINALIZING.value
    state["current_step"] = "Finalizing book"
    state["progress"] = 95
    state["last_updated"] = datetime.utcnow().isoformat()
    
    return state


def complete_workflow(state: WorkflowState) -> WorkflowState:
    """Mark workflow as complete."""
    state["phase"] = WorkflowPhase.COMPLETED.value
    state["current_step"] = "Generation complete"
    state["progress"] = 100
    state["completed_at"] = datetime.utcnow().isoformat()
    state["last_updated"] = datetime.utcnow().isoformat()
    
    return state


def handle_error(state: WorkflowState) -> WorkflowState:
    """Handle workflow errors."""
    state["phase"] = WorkflowPhase.FAILED.value
    state["last_updated"] = datetime.utcnow().isoformat()
    
    return state


# Conditional routing functions
def should_continue_chapters(state: WorkflowState) -> str:
    """Check if there are more chapters to draft."""
    current = state.get("current_chapter", 0)
    total = len(state.get("outline", {}).get("chapters", []))
    
    if current < total:
        return "draft_chapter"
    else:
        return "finalize"


def outline_decision(state: WorkflowState) -> str:
    """Check if outline is approved."""
    if state.get("outline_approved", False):
        return "start_drafting"
    else:
        return "wait_approval"


class BookGenerationWorkflow:
    """
    LangGraph workflow for generating complete books.
    
    Uses a state machine with:
    - Durable checkpoints for pause/resume
    - User approval gates
    - Bounded agent conversations in subgraphs
    - Cost/token tracking
    """
    
    def __init__(self, checkpointer=None):
        self.checkpointer = checkpointer or MemorySaver()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("ingest", ingest_sources)
        workflow.add_node("embed", embed_sources)
        workflow.add_node("generate_outline", generate_outline)
        workflow.add_node("request_approval", request_outline_approval)
        workflow.add_node("draft_chapter", draft_chapter)
        workflow.add_node("edit_chapter", edit_chapter)
        workflow.add_node("review_chapter", review_chapter)
        workflow.add_node("finalize", finalize_book)
        workflow.add_node("complete", complete_workflow)
        workflow.add_node("error", handle_error)
        
        # Add edges
        workflow.add_edge(START, "ingest")
        workflow.add_edge("ingest", "embed")
        workflow.add_edge("embed", "generate_outline")
        workflow.add_edge("generate_outline", "request_approval")
        
        # Conditional edges based on approval
        workflow.add_conditional_edges(
            "request_approval",
            outline_decision,
            {
                "start_drafting": "draft_chapter",
                "wait_approval": END,  # Pause for user
            }
        )
        
        # Chapter loop
        workflow.add_edge("draft_chapter", "edit_chapter")
        workflow.add_edge("edit_chapter", "review_chapter")
        
        workflow.add_conditional_edges(
            "review_chapter",
            should_continue_chapters,
            {
                "draft_chapter": "draft_chapter",
                "finalize": "finalize",
            }
        )
        
        workflow.add_edge("finalize", "complete")
        workflow.add_edge("complete", END)
        workflow.add_edge("error", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    def start(
        self,
        project_id: str,
        user_id: str,
        source_material_ids: list[str],
    ) -> dict:
        """Start a new book generation workflow."""
        initial_state = create_initial_state(
            project_id=project_id,
            user_id=user_id,
            source_material_ids=source_material_ids,
        )
        
        config = {"configurable": {"thread_id": initial_state["workflow_id"]}}
        
        # Run until first pause point
        result = self.graph.invoke(initial_state, config)
        
        return {
            "workflow_id": initial_state["workflow_id"],
            "state": result,
        }
    
    def resume(
        self,
        workflow_id: str,
        user_input: Optional[dict] = None,
    ) -> dict:
        """Resume a paused workflow."""
        config = {"configurable": {"thread_id": workflow_id}}
        
        # Get current state
        state = self.graph.get_state(config)
        
        if user_input:
            # Apply user input to state
            state_values = dict(state.values)
            if user_input.get("approve_outline"):
                state_values["outline_approved"] = True
                state_values["pending_user_action"] = None
            if user_input.get("feedback"):
                state_values["user_feedback"].append(user_input["feedback"])
            
            # Update state
            self.graph.update_state(config, state_values)
        
        # Continue execution
        result = self.graph.invoke(None, config)
        
        return {
            "workflow_id": workflow_id,
            "state": result,
        }
    
    def get_state(self, workflow_id: str) -> dict:
        """Get current workflow state."""
        config = {"configurable": {"thread_id": workflow_id}}
        state = self.graph.get_state(config)
        return dict(state.values) if state.values else {}

