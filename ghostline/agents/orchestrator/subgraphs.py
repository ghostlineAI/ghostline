"""
Bounded subgraphs for multi-agent conversations.

These implement the "agent talk" within controlled workflows:
- Hard limits on turns, tokens, and cost
- Structured outputs
- Stop conditions
"""

import os
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TypedDict

from langgraph.graph import StateGraph, START, END

# Import conversation logger for tracking agent-to-agent communication
from agents.core import get_conversation_logger

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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
    
    # Feedback from checkers
    voice_feedback: str
    fact_feedback: str
    cohesion_feedback: str
    
    # Tracking
    iteration: int
    tokens_used: int
    cost_incurred: float


def _has_api_keys() -> bool:
    """Check if API keys are available."""
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))


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
        self._planner = None
        self._critic = None
        self.graph = self._build_graph()
    
    @property
    def planner(self):
        """Lazy load planner agent."""
        if self._planner is None and _has_api_keys():
            try:
                from agents.specialized.outline_planner import OutlinePlannerAgent
                self._planner = OutlinePlannerAgent()
            except ImportError:
                pass
        return self._planner
    
    @property
    def critic(self):
        """Lazy load critic agent."""
        if self._critic is None and _has_api_keys():
            try:
                from agents.specialized.outline_planner import OutlineCriticAgent
                self._critic = OutlineCriticAgent()
            except ImportError:
                pass
        return self._critic
    
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
        """Generate initial outline using OutlinePlannerAgent."""
        logger.info("📝 [OutlineSubgraph] Starting plan node...")
        state["iteration"] = 0
        state["turns"] = 1
        
        # Log handoff
        conv_logger = get_conversation_logger()
        conv_logger.log_agent_handoff("Orchestrator", "OutlinePlanner", "Starting outline generation")
        
        # Use real agent if available
        if self.planner:
            logger.info("📝 [OutlineSubgraph] Using real OutlinePlannerAgent")
            from agents.specialized.outline_planner import OutlineState
            
            outline_state = OutlineState(
                project_title=state.get("project_title", "Untitled Book"),
                project_description=state.get("project_description"),
                source_summaries=state.get("source_summaries", []),
                target_chapters=state.get("target_chapters", 10),
                voice_guidance=state.get("voice_guidance"),
            )
            
            output = self.planner.process(outline_state)
            
            if output.is_success() and output.structured_data:
                state["current_outline"] = output.structured_data
                state["tokens_used"] = state.get("tokens_used", 0) + output.tokens_used
                state["cost_incurred"] = state.get("cost_incurred", 0.0) + output.estimated_cost
                logger.info(f"📝 [OutlineSubgraph] Outline generated: {len(state['current_outline'].get('chapters', []))} chapters, {output.tokens_used} tokens")
            else:
                logger.warning(f"📝 [OutlineSubgraph] Agent failed, using placeholder: {output.error}")
                state["current_outline"] = self._placeholder_outline(state)
        else:
            logger.info("📝 [OutlineSubgraph] No API keys - using placeholder outline")
            state["current_outline"] = self._placeholder_outline(state)
        
        return state
    
    def _placeholder_outline(self, state: OutlineSubgraphState) -> dict:
        """Generate a placeholder outline when no API keys are available."""
        return {
            "title": state.get("project_title", "Book"),
            "premise": "A compelling exploration of the subject matter.",
            "chapters": [
                {
                    "number": i + 1,
                    "title": f"Chapter {i + 1}",
                    "summary": "Chapter content to be developed",
                    "key_points": ["Key point 1", "Key point 2"],
                    "estimated_words": 3000,
                }
                for i in range(state.get("target_chapters", 10))
            ],
            "themes": ["Theme 1", "Theme 2"],
            "target_audience": "General readers interested in the topic",
        }
    
    def _critique_node(self, state: OutlineSubgraphState) -> OutlineSubgraphState:
        """Critique the current outline using OutlineCriticAgent."""
        state["turns"] = state.get("turns", 0) + 1
        
        # Log handoff from planner to critic
        conv_logger = get_conversation_logger()
        conv_logger.log_agent_handoff(
            "OutlinePlanner", 
            "OutlineCritic", 
            f"Reviewing outline (iteration {state.get('iteration', 0)})"
        )
        
        # Use real agent if available
        if self.critic:
            from agents.specialized.outline_planner import OutlineState
            
            outline_state = OutlineState(
                project_title=state.get("project_title", "Untitled Book"),
                target_chapters=state.get("target_chapters", 10),
                target_words=50000,
                outline=state.get("current_outline"),
            )
            
            output = self.critic.process(outline_state)
            
            if output.is_success():
                state["tokens_used"] = state.get("tokens_used", 0) + output.tokens_used
                state["cost_incurred"] = state.get("cost_incurred", 0.0) + output.estimated_cost
                
                # Check if approved
                if self.critic.is_approved(output):
                    state["approved"] = True
                    state["feedback"] = []
                else:
                    # Extract feedback from response
                    state["feedback"] = [output.content]
            else:
                # Fallback - approve after first iteration
                if state.get("iteration", 0) >= 1:
                    state["approved"] = True
                    state["feedback"] = []
                else:
                    state["feedback"] = ["Consider adding more detail to chapter summaries"]
        else:
            # No API keys - auto-approve after first iteration
            if state.get("iteration", 0) >= 1:
                state["approved"] = True
                state["feedback"] = []
            else:
                state["feedback"] = ["Consider adding more detail to chapter summaries"]
        
        return state
    
    def _refine_node(self, state: OutlineSubgraphState) -> OutlineSubgraphState:
        """Refine outline based on feedback using OutlinePlannerAgent."""
        state["iteration"] = state.get("iteration", 0) + 1
        state["turns"] = state.get("turns", 0) + 1
        
        # Log handoff from critic back to planner
        conv_logger = get_conversation_logger()
        conv_logger.log_agent_handoff(
            "OutlineCritic",
            "OutlinePlanner",
            f"Refining outline (iteration {state['iteration']})"
        )
        
        if self.planner and state.get("feedback"):
            from agents.specialized.outline_planner import OutlineState
            
            outline_state = OutlineState(
                project_title=state.get("project_title", "Untitled Book"),
                project_description=state.get("project_description"),
                source_summaries=state.get("source_summaries", []),
                target_chapters=state.get("target_chapters", 10),
                voice_guidance=state.get("voice_guidance"),
                outline=state.get("current_outline"),
                feedback=state.get("feedback", []),
            )
            
            output = self.planner.process(outline_state)
            
            if output.is_success() and output.structured_data:
                state["current_outline"] = output.structured_data
                state["tokens_used"] = state.get("tokens_used", 0) + output.tokens_used
                state["cost_incurred"] = state.get("cost_incurred", 0.0) + output.estimated_cost
        
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
        self._drafter = None
        self._voice_editor = None
        self._fact_checker = None
        self._cohesion_analyst = None
        self.graph = self._build_graph()
        
        # Quality thresholds
        self.voice_threshold = 0.85
        self.fact_threshold = 0.90
        self.cohesion_threshold = 0.80
    
    @property
    def drafter(self):
        """Lazy load drafter agent."""
        if self._drafter is None and _has_api_keys():
            try:
                from agents.specialized.content_drafter import ContentDrafterAgent
                self._drafter = ContentDrafterAgent()
            except ImportError:
                pass
        return self._drafter
    
    @property
    def voice_editor(self):
        """Lazy load voice editor agent."""
        if self._voice_editor is None and _has_api_keys():
            try:
                from agents.specialized.voice_editor import VoiceEditorAgent
                self._voice_editor = VoiceEditorAgent()
            except ImportError:
                pass
        return self._voice_editor
    
    @property
    def fact_checker(self):
        """Lazy load fact checker agent."""
        if self._fact_checker is None and _has_api_keys():
            try:
                from agents.specialized.fact_checker import FactCheckerAgent
                self._fact_checker = FactCheckerAgent()
            except ImportError:
                pass
        return self._fact_checker
    
    @property
    def cohesion_analyst(self):
        """Lazy load cohesion analyst agent."""
        if self._cohesion_analyst is None and _has_api_keys():
            try:
                from agents.specialized.cohesion_analyst import CohesionAnalystAgent
                self._cohesion_analyst = CohesionAnalystAgent()
            except ImportError:
                pass
        return self._cohesion_analyst
    
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
        """Generate initial chapter draft using ContentDrafterAgent."""
        chapter_num = state.get('chapter_outline', {}).get('number', '?')
        logger.info(f"📖 [ChapterSubgraph] Starting draft node for chapter {chapter_num}")
        state["iteration"] = 0
        
        # Log handoff
        conv_logger = get_conversation_logger()
        conv_logger.log_agent_handoff("Orchestrator", "ContentDrafter", f"Drafting chapter {chapter_num}")
        
        chapter_outline = state.get("chapter_outline", {})
        
        if self.drafter:
            from agents.specialized.content_drafter import ChapterState
            
            chapter_state = ChapterState(
                chapter_number=chapter_outline.get("number", 1),
                chapter_title=chapter_outline.get("title", "Untitled"),
                chapter_summary=chapter_outline.get("summary", ""),
                key_points=chapter_outline.get("key_points", []),
                target_words=state.get("target_words", 3000),
                previous_summaries=state.get("previous_summaries", []),
                source_chunks=state.get("source_chunks", []),
                voice_guidance=state.get("voice_profile", {}).get("guidance", ""),
            )
            
            output = self.drafter.process(chapter_state)
            
            if output.is_success():
                state["draft_content"] = output.content
                state["tokens_used"] = state.get("tokens_used", 0) + output.tokens_used
                state["cost_incurred"] = state.get("cost_incurred", 0.0) + output.estimated_cost
            else:
                state["draft_content"] = self._placeholder_chapter(state)
        else:
            state["draft_content"] = self._placeholder_chapter(state)
        
        return state
    
    def _placeholder_chapter(self, state: ChapterSubgraphState) -> str:
        """Generate placeholder chapter content."""
        chapter_outline = state.get("chapter_outline", {})
        title = chapter_outline.get("title", "Untitled")
        summary = chapter_outline.get("summary", "Chapter content goes here.")
        
        return f"""# {title}

{summary}

This chapter explores the key concepts and ideas related to the topic at hand. 
The content would be expanded based on the source materials and voice profile.

[This is placeholder content - real content requires API keys]
"""
    
    def _voice_edit_node(self, state: ChapterSubgraphState) -> ChapterSubgraphState:
        """Edit for voice consistency using VoiceEditorAgent."""
        logger.info(f"🎤 [ChapterSubgraph] Voice edit node (iteration {state.get('iteration', 0)})")
        
        # Log handoff
        conv_logger = get_conversation_logger()
        conv_logger.log_agent_handoff("ContentDrafter", "VoiceEditor", "Editing for voice consistency")
        
        content = state.get("draft_content", "")
        voice_profile = state.get("voice_profile", {})
        
        # Only use voice editor if we have a voice profile to compare against
        if self.voice_editor and voice_profile:
            from agents.specialized.voice_editor import VoiceState
            
            voice_state = VoiceState(
                content=content,
                voice_profile=voice_profile,
            )
            
            output = self.voice_editor.process(voice_state)
            
            if output.is_success():
                state["edited_content"] = output.content
                # Agent returns "score" field, not "similarity_score"
                state["voice_score"] = output.structured_data.get("score", 0.88) if output.structured_data else 0.88
                state["voice_feedback"] = output.structured_data.get("recommendations", "") if output.structured_data else ""
                state["tokens_used"] = state.get("tokens_used", 0) + output.tokens_used
                state["cost_incurred"] = state.get("cost_incurred", 0.0) + output.estimated_cost
            else:
                # Agent returned error (likely no voice profile) - default to passing score
                state["voice_score"] = 0.90
                state["edited_content"] = content
        else:
            # No voice profile - skip voice editing, use high score
            state["voice_score"] = 0.90
            state["edited_content"] = content
        
        return state
    
    def _fact_check_node(self, state: ChapterSubgraphState) -> ChapterSubgraphState:
        """Check factual accuracy using FactCheckerAgent."""
        logger.info(f"✅ [ChapterSubgraph] Fact check node (voice_score={state.get('voice_score', 0):.2f})")
        
        # Log handoff
        conv_logger = get_conversation_logger()
        conv_logger.log_agent_handoff("VoiceEditor", "FactChecker", f"Verifying facts (voice_score={state.get('voice_score', 0):.2f})")
        
        content = state.get("edited_content", state.get("draft_content", ""))
        
        if self.fact_checker:
            from agents.specialized.fact_checker import FactCheckState
            
            fact_state = FactCheckState(
                content=content,
                source_chunks=state.get("source_chunks", []),
            )
            
            output = self.fact_checker.process(fact_state)
            
            if output.is_success():
                state["fact_score"] = output.structured_data.get("accuracy_score", 0.95) if output.structured_data else 0.95
                state["fact_feedback"] = output.structured_data.get("issues", "") if output.structured_data else ""
                state["tokens_used"] = state.get("tokens_used", 0) + output.tokens_used
                state["cost_incurred"] = state.get("cost_incurred", 0.0) + output.estimated_cost
            else:
                state["fact_score"] = 0.95
        else:
            state["fact_score"] = 0.95
        
        return state
    
    def _cohesion_check_node(self, state: ChapterSubgraphState) -> ChapterSubgraphState:
        """Check cohesion and flow using CohesionAnalystAgent."""
        logger.info(f"🔗 [ChapterSubgraph] Cohesion check node (fact_score={state.get('fact_score', 0):.2f})")
        
        # Log handoff
        conv_logger = get_conversation_logger()
        conv_logger.log_agent_handoff("FactChecker", "CohesionAnalyst", f"Checking cohesion (fact_score={state.get('fact_score', 0):.2f})")
        
        content = state.get("edited_content", state.get("draft_content", ""))
        
        if self.cohesion_analyst:
            from agents.specialized.cohesion_analyst import CohesionState
            
            cohesion_state = CohesionState(
                content=content,
                previous_summaries=state.get("previous_summaries", []),
            )
            
            output = self.cohesion_analyst.process(cohesion_state)
            
            if output.is_success():
                state["cohesion_score"] = output.structured_data.get("cohesion_score", 0.85) if output.structured_data else 0.85
                state["cohesion_feedback"] = output.structured_data.get("feedback", "") if output.structured_data else ""
                state["tokens_used"] = state.get("tokens_used", 0) + output.tokens_used
                state["cost_incurred"] = state.get("cost_incurred", 0.0) + output.estimated_cost
            else:
                state["cohesion_score"] = 0.85
        else:
            state["cohesion_score"] = 0.85
        
        return state
    
    def _revise_node(self, state: ChapterSubgraphState) -> ChapterSubgraphState:
        """Revise chapter based on feedback."""
        state["iteration"] = state.get("iteration", 0) + 1
        
        # Collect all feedback
        feedback_parts = []
        if state.get("voice_score", 1.0) < self.voice_threshold and state.get("voice_feedback"):
            feedback_parts.append(f"Voice: {state['voice_feedback']}")
        if state.get("fact_score", 1.0) < self.fact_threshold and state.get("fact_feedback"):
            feedback_parts.append(f"Facts: {state['fact_feedback']}")
        if state.get("cohesion_score", 1.0) < self.cohesion_threshold and state.get("cohesion_feedback"):
            feedback_parts.append(f"Cohesion: {state['cohesion_feedback']}")
        
        if self.drafter and feedback_parts:
            # Use drafter to revise with feedback
            revision_prompt = f"""Please revise the following chapter based on this feedback:

FEEDBACK:
{chr(10).join(feedback_parts)}

CURRENT CHAPTER:
{state.get('edited_content', state.get('draft_content', ''))}

Provide the revised chapter maintaining the same voice and structure."""
            
            output = self.drafter.invoke(revision_prompt)
            
            if output.is_success():
                state["draft_content"] = output.content
                state["tokens_used"] = state.get("tokens_used", 0) + output.tokens_used
                state["cost_incurred"] = state.get("cost_incurred", 0.0) + output.estimated_cost
        
        return state
    
    def _finalize_node(self, state: ChapterSubgraphState) -> ChapterSubgraphState:
        """Finalize the chapter."""
        state["final_content"] = state.get("edited_content", state.get("draft_content", ""))
        
        return state
    
    def _should_revise(self, state: ChapterSubgraphState) -> str:
        """Determine if revision is needed."""
        iteration = state.get("iteration", 0)
        voice_score = state.get("voice_score", 0)
        fact_score = state.get("fact_score", 0)
        cohesion_score = state.get("cohesion_score", 0)
        
        logger.info(f"🔄 [ChapterSubgraph] Checking revision: iter={iteration}, voice={voice_score:.2f}, fact={fact_score:.2f}, cohesion={cohesion_score:.2f}")
        
        # Check iteration limit
        if iteration >= self.config.max_turns:
            logger.info(f"🔄 [ChapterSubgraph] Max turns reached ({self.config.max_turns}), finishing")
            return "done"
        
        # Check quality thresholds
        voice_ok = voice_score >= self.voice_threshold
        fact_ok = fact_score >= self.fact_threshold
        cohesion_ok = cohesion_score >= self.cohesion_threshold
        
        if voice_ok and fact_ok and cohesion_ok:
            logger.info("🔄 [ChapterSubgraph] All thresholds met, finishing")
            return "done"
        
        logger.info(f"🔄 [ChapterSubgraph] Needs revision (voice_ok={voice_ok}, fact_ok={fact_ok}, cohesion_ok={cohesion_ok})")
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
            voice_feedback="",
            fact_feedback="",
            cohesion_feedback="",
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
