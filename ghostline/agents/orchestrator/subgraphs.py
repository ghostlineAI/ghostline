"""
Bounded subgraphs for multi-agent conversations.

These implement the "agent talk" within controlled workflows:
- Hard limits on turns, tokens, and cost
- Structured outputs
- Stop conditions
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TypedDict

from langgraph.graph import StateGraph, START, END


@dataclass
class SubgraphConfig:
    """Configuration for bounded subgraphs."""
    max_turns: int = 5
    max_tokens: int = 10000
    max_cost: float = 1.0  # USD
    timeout_seconds: int = 300


class OutlineSubgraphState(TypedDict, total=False):
    """State for outline generation subgraph."""
    # Input
    source_summaries: list[str]
    project_title: str
    project_description: str
    target_chapters: int
    voice_guidance: str
    
    # Working state
    current_outline: Optional[dict]
    iteration: int
    feedback: list[str]
    approved: bool
    
    # Tracking
    tokens_used: int
    cost_incurred: float
    turns: int


class ChapterSubgraphState(TypedDict, total=False):
    """State for chapter generation subgraph."""
    # Input
    chapter_outline: dict
    source_chunks: list[str]
    previous_summaries: list[str]
    voice_profile: dict
    target_words: int
    
    # Working state
    draft_content: str
    edited_content: str
    final_content: str
    
    # Quality scores
    voice_score: float
    fact_score: float
    cohesion_score: float
    
    # Tracking
    iteration: int
    tokens_used: int
    cost_incurred: float


class OutlineSubgraph:
    """
    Subgraph for outline generation with Planner ↔ Critic loop.
    
    Bounded conversation:
    1. Planner generates initial outline
    2. Critic reviews and provides feedback
    3. Planner refines based on feedback
    4. Loop until approved or max iterations
    """
    
    def __init__(self, config: Optional[SubgraphConfig] = None):
        self.config = config or SubgraphConfig()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the outline generation subgraph."""
        workflow = StateGraph(OutlineSubgraphState)
        
        # Nodes
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("critique", self._critique_node)
        workflow.add_node("refine", self._refine_node)
        
        # Edges
        workflow.add_edge(START, "plan")
        workflow.add_edge("plan", "critique")
        
        workflow.add_conditional_edges(
            "critique",
            self._should_refine,
            {
                "refine": "refine",
                "done": END,
            }
        )
        
        workflow.add_edge("refine", "critique")
        
        return workflow.compile()
    
    def _plan_node(self, state: OutlineSubgraphState) -> OutlineSubgraphState:
        """Generate initial outline."""
        state["iteration"] = 0
        state["turns"] = 1
        
        # In real implementation, use OutlinePlannerAgent
        # Placeholder
        state["current_outline"] = {
            "title": state.get("project_title", "Book"),
            "chapters": [
                {"number": i+1, "title": f"Chapter {i+1}"}
                for i in range(state.get("target_chapters", 10))
            ]
        }
        
        return state
    
    def _critique_node(self, state: OutlineSubgraphState) -> OutlineSubgraphState:
        """Critique the current outline."""
        state["turns"] = state.get("turns", 0) + 1
        
        # In real implementation, use OutlineCriticAgent
        # For now, approve after first iteration
        if state.get("iteration", 0) >= 1:
            state["approved"] = True
            state["feedback"] = []
        else:
            state["feedback"] = ["Consider adding more detail to chapter summaries"]
        
        return state
    
    def _refine_node(self, state: OutlineSubgraphState) -> OutlineSubgraphState:
        """Refine outline based on feedback."""
        state["iteration"] = state.get("iteration", 0) + 1
        state["turns"] = state.get("turns", 0) + 1
        
        # In real implementation, use OutlinePlannerAgent with feedback
        
        return state
    
    def _should_refine(self, state: OutlineSubgraphState) -> str:
        """Determine if refinement is needed."""
        # Check if approved
        if state.get("approved", False):
            return "done"
        
        # Check bounds
        if state.get("iteration", 0) >= self.config.max_turns:
            return "done"
        
        if state.get("tokens_used", 0) >= self.config.max_tokens:
            return "done"
        
        if state.get("cost_incurred", 0.0) >= self.config.max_cost:
            return "done"
        
        # Has feedback, needs refinement
        if state.get("feedback"):
            return "refine"
        
        return "done"
    
    def run(
        self,
        source_summaries: list[str],
        project_title: str,
        project_description: str = "",
        target_chapters: int = 10,
        voice_guidance: str = "",
    ) -> dict:
        """Run the outline generation subgraph."""
        initial_state = OutlineSubgraphState(
            source_summaries=source_summaries,
            project_title=project_title,
            project_description=project_description,
            target_chapters=target_chapters,
            voice_guidance=voice_guidance,
            current_outline=None,
            iteration=0,
            feedback=[],
            approved=False,
            tokens_used=0,
            cost_incurred=0.0,
            turns=0,
        )
        
        result = self.graph.invoke(initial_state)
        
        return {
            "outline": result.get("current_outline"),
            "iterations": result.get("iteration", 0),
            "approved": result.get("approved", False),
            "tokens_used": result.get("tokens_used", 0),
            "cost": result.get("cost_incurred", 0.0),
        }


class ChapterSubgraph:
    """
    Subgraph for chapter generation with Drafter ↔ Voice ↔ Checker loop.
    
    Bounded conversation:
    1. Drafter generates initial chapter
    2. VoiceEditor checks and adjusts style
    3. FactChecker verifies accuracy
    4. CohesionAnalyst checks flow
    5. If issues found, Drafter revises
    6. Loop until quality thresholds met or max iterations
    """
    
    def __init__(self, config: Optional[SubgraphConfig] = None):
        self.config = config or SubgraphConfig()
        self.graph = self._build_graph()
        
        # Quality thresholds
        self.voice_threshold = 0.85
        self.fact_threshold = 0.90
        self.cohesion_threshold = 0.80
    
    def _build_graph(self) -> StateGraph:
        """Build the chapter generation subgraph."""
        workflow = StateGraph(ChapterSubgraphState)
        
        # Nodes
        workflow.add_node("draft", self._draft_node)
        workflow.add_node("voice_edit", self._voice_edit_node)
        workflow.add_node("fact_check", self._fact_check_node)
        workflow.add_node("cohesion_check", self._cohesion_check_node)
        workflow.add_node("revise", self._revise_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # Edges
        workflow.add_edge(START, "draft")
        workflow.add_edge("draft", "voice_edit")
        workflow.add_edge("voice_edit", "fact_check")
        workflow.add_edge("fact_check", "cohesion_check")
        
        workflow.add_conditional_edges(
            "cohesion_check",
            self._should_revise,
            {
                "revise": "revise",
                "done": "finalize",
            }
        )
        
        workflow.add_edge("revise", "voice_edit")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def _draft_node(self, state: ChapterSubgraphState) -> ChapterSubgraphState:
        """Generate initial chapter draft."""
        state["iteration"] = 0
        
        # In real implementation, use ContentDrafterAgent
        # Placeholder
        state["draft_content"] = f"Chapter content for: {state.get('chapter_outline', {}).get('title', 'Untitled')}"
        
        return state
    
    def _voice_edit_node(self, state: ChapterSubgraphState) -> ChapterSubgraphState:
        """Edit for voice consistency."""
        # In real implementation, use VoiceEditorAgent
        state["voice_score"] = 0.88  # Placeholder
        state["edited_content"] = state.get("draft_content", "")
        
        return state
    
    def _fact_check_node(self, state: ChapterSubgraphState) -> ChapterSubgraphState:
        """Check factual accuracy."""
        # In real implementation, use FactCheckerAgent
        state["fact_score"] = 0.95  # Placeholder
        
        return state
    
    def _cohesion_check_node(self, state: ChapterSubgraphState) -> ChapterSubgraphState:
        """Check cohesion and flow."""
        # In real implementation, use CohesionAnalystAgent
        state["cohesion_score"] = 0.85  # Placeholder
        
        return state
    
    def _revise_node(self, state: ChapterSubgraphState) -> ChapterSubgraphState:
        """Revise chapter based on feedback."""
        state["iteration"] = state.get("iteration", 0) + 1
        
        # In real implementation, use ContentDrafterAgent.revise()
        
        return state
    
    def _finalize_node(self, state: ChapterSubgraphState) -> ChapterSubgraphState:
        """Finalize the chapter."""
        state["final_content"] = state.get("edited_content", state.get("draft_content", ""))
        
        return state
    
    def _should_revise(self, state: ChapterSubgraphState) -> str:
        """Determine if revision is needed."""
        # Check iteration limit
        if state.get("iteration", 0) >= self.config.max_turns:
            return "done"
        
        # Check quality thresholds
        voice_ok = state.get("voice_score", 0) >= self.voice_threshold
        fact_ok = state.get("fact_score", 0) >= self.fact_threshold
        cohesion_ok = state.get("cohesion_score", 0) >= self.cohesion_threshold
        
        if voice_ok and fact_ok and cohesion_ok:
            return "done"
        
        return "revise"
    
    def run(
        self,
        chapter_outline: dict,
        source_chunks: list[str],
        previous_summaries: list[str] = None,
        voice_profile: dict = None,
        target_words: int = 3000,
    ) -> dict:
        """Run the chapter generation subgraph."""
        initial_state = ChapterSubgraphState(
            chapter_outline=chapter_outline,
            source_chunks=source_chunks,
            previous_summaries=previous_summaries or [],
            voice_profile=voice_profile or {},
            target_words=target_words,
            draft_content="",
            edited_content="",
            final_content="",
            voice_score=0.0,
            fact_score=0.0,
            cohesion_score=0.0,
            iteration=0,
            tokens_used=0,
            cost_incurred=0.0,
        )
        
        result = self.graph.invoke(initial_state)
        
        return {
            "content": result.get("final_content"),
            "word_count": len(result.get("final_content", "").split()),
            "voice_score": result.get("voice_score", 0.0),
            "fact_score": result.get("fact_score", 0.0),
            "cohesion_score": result.get("cohesion_score", 0.0),
            "iterations": result.get("iteration", 0),
            "tokens_used": result.get("tokens_used", 0),
            "cost": result.get("cost_incurred", 0.0),
        }

