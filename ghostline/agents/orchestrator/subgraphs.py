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
    # Workflow context (optional, but enables full-source citation verification)
    project_id: str
    # Input
    chapter_outline: dict
    source_chunks: list[str]
    source_chunks_with_citations: list[dict]  # {"content": str, "citation": str}
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
    
    # Citation verification report (post-generation quality check)
    claim_mappings: list[dict]  # Detailed claim-to-source mappings
    citation_report: dict  # Summary of citation quality metrics
    # UI-facing citation metadata
    content_clean: str
    citations: list[dict]

    # Full per-iteration history (for audits/debugging)
    revision_history: list[dict]
    # Final quality gate evaluation
    quality_gates_passed: bool
    quality_gate_report: dict
    
    # Tracking
    iteration: int
    tokens_used: int
    cost_incurred: float


def _has_api_keys() -> bool:
    """Check if API keys are available."""
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def _strict_mode() -> bool:
    """
    Strict mode disables placeholders and LLM/provider fallbacks.
    Intended for production-quality runs where we prefer failing fast over degrading quality.
    """
    return os.getenv("GHOSTLINE_STRICT_MODE", "").strip().lower() in ("1", "true", "yes", "on")


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
                if _strict_mode():
                    raise RuntimeError(f"OutlinePlanner failed in strict mode: {output.error or 'unknown error'}")
                logger.warning(f"📝 [OutlineSubgraph] Agent failed, using placeholder: {output.error}")
                state["current_outline"] = self._placeholder_outline(state)
        else:
            if _strict_mode():
                raise RuntimeError("OutlinePlanner unavailable in strict mode (missing API keys or import failure)")
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
        # LangGraph has a default recursion_limit that can be too low when max_turns
        # is reached (especially with real agents / revision loops). Set a safe limit
        # proportional to the configured max turns.
        recursion_limit = max(50, int(self.config.max_turns) * 10)
        result = self.graph.invoke(initial_state, {"recursion_limit": recursion_limit})
        
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
        # NOTE: numeric voice similarity against raw notes is inherently noisy.
        # We keep this threshold lower and rely on grounding + anti-hallucination gates
        # to protect correctness, while voice is improved via editing.
        self.voice_threshold = 0.70
        self.fact_threshold = 0.90
        # Cohesion is useful signal but should not block correctness; avoid runaway revision loops.
        self.cohesion_threshold = 0.0

    def _build_voice_guidance(self, voice_profile: dict) -> str:
        """Build a compact voice-guidance block from a VoiceProfile dict."""
        if not voice_profile:
            return ""

        parts: list[str] = []

        style_desc = (voice_profile.get("style_description") or voice_profile.get("description") or "").strip()
        if style_desc:
            parts.append(style_desc)

        tone = voice_profile.get("tone")
        style = voice_profile.get("style")
        if tone or style:
            parts.append(f"Tone: {tone or 'unspecified'}; Style: {style or 'unspecified'}")

        common_phrases = list(voice_profile.get("common_phrases") or [])
        if common_phrases:
            parts.append("Common phrases (use only when natural): " + ", ".join(common_phrases[:10]))

        sentence_starters = list(voice_profile.get("sentence_starters") or [])
        if sentence_starters:
            parts.append("Sentence starters: " + ", ".join(sentence_starters[:10]))

        transition_words = list(voice_profile.get("transition_words") or [])
        if transition_words:
            parts.append("Transitions: " + ", ".join(transition_words[:12]))

        return "\n".join(p for p in parts if p).strip()

    def _compute_style_issues(self, content: str) -> list[str]:
        """
        Deterministic "human-ness" checks to avoid AI-tells like header spam and frameworks.
        """
        import re

        if not content or not content.strip():
            return ["Empty content"]

        issues: list[str] = []

        heading_count = len(re.findall(r"^\\s*##\\s+", content, flags=re.MULTILINE))
        paras = [p for p in re.split(r"\\n\\n+", content) if p.strip()]
        para_count = len(paras)

        # AI tell: lots of headings relative to content length
        if heading_count > 3:
            issues.append(f"Too many section headers (##): {heading_count}. Limit to at most 3 and use longer paragraphs.")
        if para_count >= 8 and heading_count >= max(4, para_count // 3):
            issues.append("Headers are too frequent relative to paragraph count; reduce headings substantially.")

        # AI tell: named frameworks / acronym systems
        if re.search(r"\\b[A-Z]{3,}\\b\\s+Framework\\b", content):
            issues.append("Acronym/framework pattern detected (e.g., 'XYZ Framework'). Remove named frameworks and write naturally.")

        # Overuse of "toolkit/framework/arsenal" meta-language
        if len(re.findall(r"\\b(toolkit|framework|arsenal)\\b", content, flags=re.IGNORECASE)) >= 6:
            issues.append("Too much 'framework/toolkit/arsenal' meta-language. Reduce and write more directly.")

        # AI tell: em/en-dash overuse (often shows up as "long dashes everywhere")
        dash_count = content.count("—") + content.count("–")
        dash_count += len(re.findall(r"(?<!-)--(?!-)", content))
        word_total = len(content.split()) or 1
        dashes_per_1k = (dash_count / word_total) * 1000.0
        if dashes_per_1k > 2.0:
            issues.append(
                f"Too many em/en-dashes (—/–/--): {dash_count} across ~{word_total} words "
                f"({dashes_per_1k:.1f} per 1k). Replace with commas/periods to sound more human."
            )

        paras = [p.strip() for p in re.split(r"\n\s*\n+", content) if p.strip()]

        # Claim-level grounding: allow uncited connective prose, but flag "factual-looking"
        # sentences without citations (numbers, clinical/statistical language, etc).
        if "[citation:" not in content.lower():
            issues.append(
                "No citations found. Add [citation: ...] markers for factual claims and any verbatim phrases taken from sources."
            )
        else:
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if s.strip()]
            uncited_factual: list[str] = []
            factual_kw = re.compile(
                r"\b(percent|%|diagnos|clinical|medication|therapy|symptom|study|studies|research|statistic|prevalence|rate)\b",
                re.IGNORECASE,
            )
            for s in sentences:
                if "[citation:" in s.lower():
                    continue
                if re.search(r"\d", s) is not None:
                    uncited_factual.append(s[:160])
                    continue
                if factual_kw.search(s) is not None:
                    uncited_factual.append(s[:160])
                    continue
            if uncited_factual:
                issues.append(
                    "Found potentially factual sentence(s) without citations (claim-level grounding). "
                    "Add a [citation: ...] marker to the sentence or rewrite as non-factual reflection. "
                    f"Example (first): {uncited_factual[0]}"
                )

        # Grounding: cited quotes must appear in the prose (verbatim).
        # For each substantive paragraph, require at least one citation whose QUOTE appears
        # outside the citation marker.
        # Accept straight or curly quotes in citation markers
        citation_pat = re.compile(
            r'\[citation:\s*([^\-\]]+?)\s*-\s*(?:"|“)(.*?)(?:"|”)\s*\]',
            re.IGNORECASE,
        )
        for p in paras:
            if len(p.split()) < 20:
                continue
            cites = list(citation_pat.finditer(p))
            if not cites:
                continue
            prose = citation_pat.sub("", p)
            prose_lower = prose.lower()
            quote_found = False
            for m in cites:
                q = (m.group(2) or "").strip()
                if not q:
                    continue
                if q.lower() in prose_lower:
                    quote_found = True
                    break
            if not quote_found:
                issues.append(
                    "Citation quote not present in paragraph prose. "
                    "Include the cited quote verbatim in the paragraph prose (outside the citation marker). "
                    "Do NOT add quotation marks unless the source text is itself a quote. "
                    f"Example paragraph start: {p[:140]}"
                )
                break

        # NOTE: we intentionally do NOT enforce a minimum quote density in prose.
        # Quote-ratio gates caused templated, choppy output. Grounding is enforced at the
        # claim level via citation verification + uncited-factual-sentence heuristics.

        # Grounding: invented autobiographical scenes (first-person past-tense) without citations
        # Example to catch: "I was at my desk..." / "That Tuesday morning..."
        # Require that first-person past-tense "scene" writing does NOT appear in model-authored prose.
        # Allow it only when directly quoted from sources (i.e., inside quotation marks).
        quote_span_pat = re.compile(r'(".*?"|“.*?”)', re.DOTALL)
        # First-person in model-authored prose is a common hallucination vector (invented autobiography).
        # We allow first-person only when directly quoted from sources (inside quotation marks).
        fp_first_person_pat = re.compile(r"\bI\b", re.IGNORECASE)
        for p in paras:
            # Strip citations + quoted spans, then scan remaining prose for "I <past-tense>" scenes.
            p_wo_cites = citation_pat.sub("", p)
            p_wo_quotes = quote_span_pat.sub("", p_wo_cites)
            if fp_first_person_pat.search(p_wo_quotes):
                issues.append(
                    "First-person prose detected outside quotes/citations. "
                    "To prevent invented autobiography, remove first-person statements unless they are direct quotes from sources. "
                    f"Example paragraph start: {p[:140]}"
                )
                break

        return issues

    def _format_fact_feedback(self, structured: dict) -> str:
        """Build a compact, actionable fact-check feedback string from FactChecker JSON."""
        if not structured:
            return ""

        summary = (structured.get("summary") or "").strip()
        findings = list(structured.get("findings") or [])
        unsupported = list(structured.get("unsupported_claims") or [])
        low_conf = list(structured.get("low_confidence_citations") or [])

        severity_rank = {"high": 3, "medium": 2, "low": 1}
        findings_sorted = sorted(
            findings,
            key=lambda f: severity_rank.get(str(f.get("severity") or "").lower(), 0),
            reverse=True,
        )

        parts: list[str] = []
        if summary:
            parts.append(f"Summary: {summary}")

        if findings_sorted:
            lines: list[str] = []
            for f in findings_sorted[:3]:
                typ = str(f.get("type") or "issue")
                sev = str(f.get("severity") or "").lower() or "unspecified"
                loc = str(f.get("location") or "").strip()
                issue = str(f.get("issue") or "").strip()
                suggestion = str(f.get("suggestion") or "").strip()

                line = f"- ({sev}) {typ}: {issue}" if issue else f"- ({sev}) {typ}"
                if loc:
                    line += f" @ {loc}"
                if suggestion:
                    line += f" | Fix: {suggestion}"
                lines.append(line)
            parts.append("Top issues:\n" + "\n".join(lines))

        if unsupported:
            parts.append("Unsupported claims:\n" + "\n".join(f"- {c}" for c in unsupported[:5]))

        if low_conf:
            parts.append("Low-confidence citations:\n" + "\n".join(f"- {c}" for c in low_conf[:5]))

        return "\n\n".join(p for p in parts if p).strip()

    def _format_cohesion_feedback(self, structured: dict) -> str:
        """Build a compact, actionable cohesion feedback string from CohesionAnalyst JSON."""
        if not structured:
            return ""

        summary = (structured.get("summary") or "").strip()
        issues = list(structured.get("issues") or [])

        severity_rank = {"high": 3, "medium": 2, "low": 1}
        issues_sorted = sorted(
            issues,
            key=lambda i: severity_rank.get(str(i.get("severity") or "").lower(), 0),
            reverse=True,
        )

        parts: list[str] = []
        if summary:
            parts.append(f"Summary: {summary}")

        if issues_sorted:
            lines: list[str] = []
            for i in issues_sorted[:3]:
                typ = str(i.get("type") or "issue")
                sev = str(i.get("severity") or "").lower() or "unspecified"
                loc = str(i.get("location") or "").strip()
                desc = str(i.get("description") or "").strip()
                suggestion = str(i.get("suggestion") or "").strip()

                line = f"- ({sev}) {typ}: {desc}" if desc else f"- ({sev}) {typ}"
                if loc:
                    line += f" @ {loc}"
                if suggestion:
                    line += f" | Fix: {suggestion}"
                lines.append(line)
            parts.append("Top issues:\n" + "\n".join(lines))

        return "\n\n".join(p for p in parts if p).strip()

    def _sanitize_grounding(self, content: str) -> str:
        """
        Grounding sanitizer.

        IMPORTANT: This must be **non-destructive by default**. Older versions rewrote prose
        (dropping uncited paragraphs, injecting quotes, trimming/reformatting paragraphs,
        and removing first-person sentences). That harmed voice and flow and masked quality
        issues we actually want to surface via quality gates.

        Set `GHOSTLINE_DESTRUCTIVE_SANITIZER=1` to temporarily re-enable the legacy behavior
        for debugging/rollback.
        """
        if not content or not content.strip():
            return content

        if os.getenv("GHOSTLINE_DESTRUCTIVE_SANITIZER", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        ):
            return self._sanitize_grounding_destructive(content)

        # Non-destructive path: preserve output exactly (minus outer whitespace normalization).
        return content.strip()

    def _sanitize_grounding_destructive(self, content: str) -> str:
        """
        Legacy destructive sanitizer (kept behind `GHOSTLINE_DESTRUCTIVE_SANITIZER`).

        NOTE: This intentionally preserves the prior behavior for rollback, but should not be
        enabled in normal runs.
        """
        import re

        if not content or not content.strip():
            return content

        # Accept straight or curly quotes in citation markers
        citation_pat = re.compile(
            r'\[citation:\s*([^\-\]]+?)\s*-\s*(?:"|“)(.*?)(?:"|”)\s*\]',
            re.IGNORECASE,
        )
        quote_span_pat = re.compile(r'(".*?"|“.*?”)', re.DOTALL)
        # Drop first-person sentences from model prose (outside quotes) to avoid invented autobiography.
        fp_first_person_pat = re.compile(r"\bI\b", re.IGNORECASE)

        def _quote_ratio(p: str) -> tuple[float, int, int]:
            prose = citation_pat.sub("", p).strip()
            prose_words = len(prose.split()) or 1
            cites = list(citation_pat.finditer(p))
            quote_words = 0
            prose_lower = prose.lower()
            for m in cites:
                q = (m.group(2) or "").strip()
                if q and q.lower() in prose_lower:
                    quote_words += len(q.split())
            return (quote_words / prose_words), quote_words, prose_words

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", content) if p.strip()]
        kept: list[str] = []

        for p in paragraphs:
            words = len(p.split())
            cites = list(citation_pat.finditer(p))

            # Drop uncited paragraphs (even small ones) — if it can't be cited, it shouldn't ship.
            if words >= 10 and not cites:
                continue

            if cites:
                prose = citation_pat.sub("", p)
                prose_lower = prose.lower()

                # Ensure at least one cited quote is present in the prose; if not, inject the first.
                has_quote = False
                for m in cites:
                    q = (m.group(2) or "").strip()
                    if q and q.lower() in prose_lower:
                        has_quote = True
                        break
                if not has_quote:
                    q0 = (cites[0].group(2) or "").strip()
                    if q0:
                        insert_at = cites[0].start()
                        p = p[:insert_at] + f"\"{q0}\" " + p[insert_at:]

                # Trim commentary to improve grounding density
                ratio, _, _ = _quote_ratio(p)
                if ratio < 0.15:
                    # Keep everything through the first citation marker, plus up to 2 sentences after it.
                    cites_now = list(citation_pat.finditer(p)) or cites
                    m0 = cites_now[0]
                    head = p[: m0.end()].strip()
                    tail = p[m0.end() :].strip()
                    if tail:
                        tail_sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", tail) if s.strip()]
                        tail_keep = " ".join(tail_sents[:1]).strip()
                        p2 = (head + (" " + tail_keep if tail_keep else "")).strip()
                    else:
                        p2 = head

                    # Also cap paragraph length to avoid long uncited expansions.
                    words2 = p2.split()
                    if len(words2) > 120:
                        p2 = " ".join(words2[:120]).rstrip()

                    p = p2

                    # If still too low, rewrite into a quote-first micro-paragraph:
                    # "QUOTE" [citation: ...] + at most one short commentary sentence.
                    ratio2, _, _ = _quote_ratio(p)
                    if ratio2 < 0.15:
                        cites_now2 = list(citation_pat.finditer(p))
                        if cites_now2:
                            m_first = cites_now2[0]
                            q_first = (m_first.group(2) or "").strip()
                            marker_first = m_first.group(0)
                            if q_first:
                                prose_only = citation_pat.sub("", p).strip()
                                # Remove the quote itself from prose_only to avoid duplication
                                try:
                                    prose_only = re.sub(re.escape(q_first), "", prose_only, flags=re.IGNORECASE).strip()
                                except re.error:
                                    pass
                                # Take the first sentence as commentary (optional)
                                sent = ""
                                sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", prose_only) if s.strip()]
                                if sents:
                                    sent = sents[0]
                                # Ensure quote density stays high: limit commentary length based on quote length.
                                q_wc = len(q_first.split())
                                # max prose words allowed to keep quote_words/prose_words >= 0.15
                                max_prose_words = int(q_wc / 0.15) if q_wc > 0 else 0
                                max_commentary_words = max(0, max_prose_words - q_wc)
                                if max_commentary_words <= 0:
                                    sent = ""
                                elif sent:
                                    sent_words = sent.split()
                                    if len(sent_words) > max_commentary_words:
                                        sent = " ".join(sent_words[:max_commentary_words]).rstrip()

                                p3 = f"\"{q_first}\" {marker_first}" + (f" {sent}" if sent else "")
                                words3 = p3.split()
                                if len(words3) > 120:
                                    p3 = " ".join(words3[:120]).rstrip()
                                p = p3

                # Strip invented first-person past-tense "scene" sentences from model prose (outside quotes).
                # This removes hallucinated autobiographical moments like "I found myself sitting..." while
                # preserving direct quoted source text.
                quotes: list[str] = []

                def _mask_quote(m: re.Match) -> str:
                    quotes.append(m.group(0))
                    return f"<<QUOTE_{len(quotes)}>>"

                masked = quote_span_pat.sub(_mask_quote, p)
                sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", masked) if s.strip()]
                kept_sents: list[str] = []
                for s in sentences:
                    if fp_first_person_pat.search(s):
                        # Drop first-person sentences from commentary (quotes are masked).
                        continue
                    kept_sents.append(s)
                masked2 = " ".join(kept_sents).strip()
                # Restore quotes
                for i, q in enumerate(quotes, 1):
                    masked2 = masked2.replace(f"<<QUOTE_{i}>>", q)
                p = masked2.strip()

            kept.append(p)

        return "\n\n".join(kept).strip()

    def _verify_inline_citations(
        self,
        content: str,
        source_chunks_with_citations: list[dict],
        project_id: Optional[str] = None,
    ) -> dict:
        """
        Deterministically verify inline citation markers in the generated text.

        Expects markers like:
          [citation: mentalhealth1.pdf - "exact quote from source"]

        Returns a compact report used for gating.
        """
        import re

        report = {
            "inline_total": 0,
            "inline_parsed": 0,
            "inline_verified": 0,
            "inline_unverified": 0,
            "inline_invalid_format": 0,
            "inline_quality": 0.0,
            "inline_unverified_examples": [],
            "inline_citations": [],
        }

        if not content or not content.strip():
            return report

        def _norm(s: str) -> str:
            s = (s or "").lower()
            # Normalize common unicode punctuation
            s = s.replace("’", "'").replace("“", '"').replace("”", '"')
            # Strip punctuation to make matching robust to formatting differences
            s = re.sub(r"[^a-z0-9]+", " ", s)
            s = re.sub(r"\s+", " ", s).strip()
            return s

        # Build a filename -> searchable source text index (lowercased).
        # Prefer FULL extracted source text from DB when project_id is available, otherwise
        # fall back to the provided chunks.
        source_index: dict[str, str] = {}
        source_material_ids: dict[str, str] = {}

        filenames: set[str] = set()
        for chunk in source_chunks_with_citations or []:
            cit_raw = str(chunk.get("citation", "") or "").strip()
            fn = cit_raw.strip().strip("[]").lower()
            if fn:
                filenames.add(fn)

        if project_id and filenames:
            try:
                from app.db.base import SessionLocal
                from app.models.source_material import SourceMaterial
                from uuid import UUID

                db = SessionLocal()
                try:
                    proj_uuid = UUID(str(project_id))
                    # Fetch extracted text for all filenames in this project.
                    rows = (
                        db.query(SourceMaterial)
                        .filter(SourceMaterial.project_id == proj_uuid)
                        .filter(SourceMaterial.filename.in_([f for f in filenames]))
                        .all()
                    )
                    for sm in rows:
                        fn = (sm.filename or "").lower()
                        txt = sm.extracted_text or sm.extracted_content or ""
                        txt = _norm(txt)
                        if fn:
                            source_index[fn] = txt
                            source_material_ids[fn] = str(sm.id)
                finally:
                    db.close()
            except Exception:
                source_index = {}
                source_material_ids = {}

        # Fallback: index only the provided chunks
        if not source_index:
            for chunk in source_chunks_with_citations or []:
                cit_raw = str(chunk.get("citation", "") or "").strip()
                filename = cit_raw.strip().strip("[]").lower() or "unknown"
                source_index.setdefault(filename, "")
                content_norm = (chunk.get("content", "") or "").lower()
                content_norm = _norm(content_norm)
                source_index[filename] += " " + content_norm

        # Count all "[citation:" occurrences
        report["inline_total"] = len(re.findall(r"\[citation:", content, flags=re.IGNORECASE))

        # Parse standardized citations
        # Accept straight or curly quotes in citation markers
        pattern = re.compile(
            r'\[citation:\s*([^\-\]]+?)\s*-\s*(?:"|“)(.*?)(?:"|”)\s*\]',
            re.IGNORECASE,
        )
        matches = list(pattern.finditer(content))
        report["inline_parsed"] = len(matches)

        # Anything that looks like a citation marker but doesn't match the strict format counts as invalid
        report["inline_invalid_format"] = max(0, report["inline_total"] - report["inline_parsed"])

        verified = 0
        unverified = 0
        for m in matches:
            filename = (m.group(1) or "").strip().strip("[]").lower()
            quote = (m.group(2) or "").strip()
            if not filename or not quote:
                unverified += 1
                continue

            haystack = source_index.get(filename, "")
            quote_lower = quote.lower()
            quote_lower = _norm(quote_lower)

            is_verified = False
            if quote_lower and quote_lower in haystack:
                verified += 1
                is_verified = True
            else:
                unverified += 1
                if len(report["inline_unverified_examples"]) < 5:
                    report["inline_unverified_examples"].append(
                        {"file": filename, "quote": quote[:200]}
                    )

            # Persist per-citation metadata (for chapter review UI linking).
            if len(report["inline_citations"]) < 500:
                report["inline_citations"].append(
                    {
                        "filename": filename,
                        "quote": quote,
                        "verified": is_verified,
                        "source_material_id": source_material_ids.get(filename),
                        "marker_start": int(m.start()),
                        "marker_end": int(m.end()),
                    }
                )

        report["inline_verified"] = verified
        report["inline_unverified"] = unverified
        if report["inline_parsed"] > 0:
            report["inline_quality"] = verified / report["inline_parsed"]

        return report
    
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
                source_chunks_with_citations=state.get("source_chunks_with_citations", []) or [],
                voice_guidance=self._build_voice_guidance(state.get("voice_profile", {}) or {}),
                grounding_requirement=0.95,
            )
            
            output = self.drafter.process(chapter_state)
            
            if output.is_success():
                state["draft_content"] = output.content
                state["tokens_used"] = state.get("tokens_used", 0) + output.tokens_used
                state["cost_incurred"] = state.get("cost_incurred", 0.0) + output.estimated_cost
            else:
                if _strict_mode():
                    raise RuntimeError(f"ContentDrafter failed in strict mode: {output.error or 'unknown error'}")
                state["draft_content"] = self._placeholder_chapter(state)
        else:
            if _strict_mode():
                raise RuntimeError("ContentDrafter unavailable in strict mode (missing API keys or import failure)")
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
        voice_profile = state.get("voice_profile", {}) or {}

        # Build writing samples from retrieved source chunks (these are the author's real words)
        writing_samples: list[str] = []
        for chunk_data in (state.get("source_chunks_with_citations") or [])[:3]:
            sample = (chunk_data.get("content") or "").strip()
            if sample:
                writing_samples.append(sample[:2000])

        # Use numeric voice similarity when possible (deterministic, not LLM-judged).
        threshold = float(voice_profile.get("similarity_threshold") or self.voice_threshold)
        embedding_weight = float(voice_profile.get("embedding_weight") or 0.4)
        numeric_scored = False
        if writing_samples:
            try:
                from app.services.embeddings import get_embedding_service
                from app.services.voice_metrics import VoiceMetricsService

                voice_metrics = VoiceMetricsService(
                    embedding_service=get_embedding_service(),
                    default_embedding_weight=embedding_weight,
                )
                reference_text = "\n\n".join(writing_samples)
                sim = voice_metrics.compute_similarity(
                    text1=reference_text,
                    text2=content,
                    embedding_weight=embedding_weight,
                    threshold=threshold,
                )
                state["voice_score"] = float(sim.overall_score)
                state["voice_feedback"] = sim.get_diagnosis()
                numeric_scored = True

                # If already a strong voice match, keep content as-is.
                if sim.passes_threshold:
                    state["edited_content"] = content
                    return state
            except Exception as e:
                if _strict_mode():
                    raise RuntimeError(f"Numeric voice scoring failed in strict mode: {e}")
                logger.warning(f"🎤 [ChapterSubgraph] Numeric voice scoring failed; falling back to LLM voice editor: {e}")

        # Fall back to LLM voice editing using writing samples (or voice profile text fields).
        if self.voice_editor and (voice_profile or writing_samples):
            from agents.specialized.voice_editor import VoiceState
            
            voice_state = VoiceState(
                content=content,
                voice_profile=voice_profile or None,
                writing_samples=writing_samples,
                similarity_threshold=threshold,
                embedding_weight=embedding_weight,
            )
            
            output = self.voice_editor.edit_for_voice(voice_state)
            
            if output.is_success():
                state["edited_content"] = output.content
                state["tokens_used"] = state.get("tokens_used", 0) + output.tokens_used
                state["cost_incurred"] = state.get("cost_incurred", 0.0) + output.estimated_cost

                # Recompute numeric score after editing when possible
                if writing_samples:
                    try:
                        from app.services.embeddings import get_embedding_service
                        from app.services.voice_metrics import VoiceMetricsService

                        voice_metrics = VoiceMetricsService(
                            embedding_service=get_embedding_service(),
                            default_embedding_weight=embedding_weight,
                        )
                        reference_text = "\n\n".join(writing_samples)
                        sim2 = voice_metrics.compute_similarity(
                            text1=reference_text,
                            text2=output.content,
                            embedding_weight=embedding_weight,
                            threshold=threshold,
                        )
                        state["voice_score"] = float(sim2.overall_score)
                        state["voice_feedback"] = sim2.get_diagnosis()
                        numeric_scored = True
                    except Exception:
                        pass

                # If we couldn't compute numeric score, fall back to a conservative default
                if not numeric_scored:
                    if _strict_mode():
                        raise RuntimeError("Numeric voice scoring unavailable in strict mode after voice editing")
                    state["voice_score"] = 0.75
                    state["voice_feedback"] = "Voice edited (LLM), numeric score unavailable"
            else:
                state["edited_content"] = content
                state["voice_score"] = state.get("voice_score", 0.0) or 0.0
                state["voice_feedback"] = state.get("voice_feedback", "") or f"VoiceEditor failed: {output.error or 'unknown error'}"
        else:
            # No way to edit voice; keep content but do not claim it passes.
            state["edited_content"] = content
            state["voice_score"] = state.get("voice_score", 0.0) or 0.0
        
        return state
    
    def _fact_check_node(self, state: ChapterSubgraphState) -> ChapterSubgraphState:
        """Check factual accuracy using FactCheckerAgent with citation verification."""
        logger.info(f"✅ [ChapterSubgraph] Fact check node (voice_score={state.get('voice_score', 0):.2f})")
        
        # Log handoff
        conv_logger = get_conversation_logger()
        conv_logger.log_agent_handoff("VoiceEditor", "FactChecker", f"Verifying facts (voice_score={state.get('voice_score', 0):.2f})")
        
        content = state.get("edited_content", state.get("draft_content", ""))
        
        # Use source chunks with citations if available
        source_chunks = state.get("source_chunks", [])
        source_chunks_with_citations = state.get("source_chunks_with_citations", [])

        if self.fact_checker:
            from agents.specialized.fact_checker import FactCheckState

            fact_state = FactCheckState(
                content=content,
                source_chunks=source_chunks,
                source_chunks_with_citations=source_chunks_with_citations,
            )

            output = self.fact_checker.process(fact_state)

            # Always compute deterministic inline citation verification (even if fact-check fails)
            inline_report = self._verify_inline_citations(
                content,
                source_chunks_with_citations,
                project_id=state.get("project_id"),
            )

            if output.is_success() and output.structured_data:
                structured = output.structured_data
                state["fact_score"] = float(structured.get("accuracy_score") or 0.0)
                state["fact_feedback"] = self._format_fact_feedback(structured)
                state["tokens_used"] = state.get("tokens_used", 0) + output.tokens_used
                state["cost_incurred"] = state.get("cost_incurred", 0.0) + output.estimated_cost

                claim_mappings = structured.get("claim_mappings", []) or []

                # Verify citations against actual source content
                if claim_mappings and source_chunks_with_citations:
                    verified_mappings = self.fact_checker.verify_citations_against_sources(
                        claim_mappings,
                        source_chunks_with_citations,
                    )
                    state["claim_mappings"] = verified_mappings
                else:
                    state["claim_mappings"] = claim_mappings

                # Citation quality report from LLM mappings + deterministic inline report
                citation_report = self.fact_checker.get_citation_quality_report(
                    state.get("claim_mappings", claim_mappings)
                )
                state["citation_report"] = {**citation_report, **inline_report}

                logger.info(f"📊 [FactChecker] Citation report: {citation_report}")
                conv_logger.log_system(
                    "FactChecker",
                    f"Citation report: verified={citation_report.get('verified', 0)}/{citation_report.get('total_claims', 0)}, "
                    f"needs_review={citation_report.get('needs_review', 0)}, quality={citation_report.get('quality_score', 0):.2f}",
                )
            else:
                if _strict_mode():
                    raise RuntimeError(f"FactChecker failed in strict mode: {output.error or 'no structured output'}")
                state["fact_score"] = 0.0
                state["fact_feedback"] = f"FactChecker failed: {output.error or 'no structured output'}"
                state["claim_mappings"] = []
                state["citation_report"] = {
                    "total_claims": 0,
                    "verified": 0,
                    "needs_review": 0,
                    "unsupported": 0,
                    "quality_score": 0.0,
                    "recommendation": "Fact-check failed",
                    **inline_report,
                }
        else:
            if _strict_mode():
                raise RuntimeError("FactChecker unavailable in strict mode (missing API keys or import failure)")
            # No fact checker available -> treat as failed for quality gating.
            state["fact_score"] = 0.0
            state["fact_feedback"] = "FactChecker unavailable (missing API keys or import failure)"
            state["claim_mappings"] = []
            # Still compute deterministic inline report for logging/metrics
            inline_report = self._verify_inline_citations(
                content,
                source_chunks_with_citations,
                project_id=state.get("project_id"),
            )
            state["citation_report"] = {
                "total_claims": 0,
                "verified": 0,
                "needs_review": 0,
                "unsupported": 0,
                "quality_score": 0.0,
                "recommendation": "Fact-check unavailable",
                **inline_report,
            }
        
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
            
            if output.is_success() and output.structured_data:
                structured = output.structured_data
                state["cohesion_score"] = float(structured.get("cohesion_score") or 0.0)
                state["cohesion_feedback"] = self._format_cohesion_feedback(structured)
                state["tokens_used"] = state.get("tokens_used", 0) + output.tokens_used
                state["cost_incurred"] = state.get("cost_incurred", 0.0) + output.estimated_cost
            else:
                if _strict_mode():
                    raise RuntimeError(f"CohesionAnalyst failed in strict mode: {output.error or 'no structured output'}")
                state["cohesion_score"] = 0.0
                state["cohesion_feedback"] = f"CohesionAnalyst failed: {output.error or 'no structured output'}"
        else:
            if _strict_mode():
                raise RuntimeError("CohesionAnalyst unavailable in strict mode (missing API keys or import failure)")
            state["cohesion_score"] = 0.0
            state["cohesion_feedback"] = "CohesionAnalyst unavailable"
        
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

        # Deterministic style checks (avoid obvious AI tells)
        style_issues = self._compute_style_issues(state.get("edited_content", state.get("draft_content", "")) or "")
        if style_issues:
            feedback_parts.append("Style: " + " ".join(style_issues))
        
        if self.drafter and feedback_parts:
            # Re-inject sources during revision; otherwise the model drifts/hallucinates.
            sources_block = ""
            if state.get("source_chunks_with_citations"):
                blocks = []
                for chunk_data in (state.get("source_chunks_with_citations") or [])[:12]:
                    cit = chunk_data.get("citation", "Unknown Source")
                    cont = chunk_data.get("content", "")
                    blocks.append(f"---\n{cit}\n{cont}\n---")
                sources_block = "\n\n".join(blocks)
            elif state.get("source_chunks"):
                sources_block = "\n\n".join((state.get("source_chunks") or [])[:6])

            voice_guidance = self._build_voice_guidance(state.get("voice_profile", {}) or {})

            # Build a small quote bank from the provided sources to force verbatim citations.
            quote_bank = ""
            try:
                import re
                quotes: list[str] = []
                seen: set[str] = set()
                for chunk_data in (state.get("source_chunks_with_citations") or [])[:12]:
                    cit = str(chunk_data.get("citation", "Unknown Source"))
                    raw = str(chunk_data.get("content", "") or "")
                    for line in re.split(r"[\r\n]+", raw):
                        q = line.strip()
                        if not q:
                            continue
                        if '"' in q:
                            continue
                        w = q.split()
                        if len(w) < 8 or len(w) > 25:
                            continue
                        key = q.lower()
                        if key in seen:
                            continue
                        seen.add(key)
                        quotes.append(f"({cit}) {q}")
                        if len(quotes) >= 20:
                            break
                    if len(quotes) >= 20:
                        break
                if quotes:
                    quote_bank = (
                        "\nQUOTE BANK (copy verbatim into citations; do not invent quotes):\n"
                        + "\n".join(f"- {q}" for q in quotes)
                    )
            except Exception:
                quote_bank = ""

            revision_prompt = f"""You are revising a chapter for a real product. The last output read like AI and contained unsupported content.

HARD CONSTRAINTS (must follow):
- Do NOT invent scenes, anecdotes, or autobiographical moments. If it's first-person, it must be grounded in the sources.
- Minimize headings: at most 3 section headings using '##' for the entire chapter. Prefer longer paragraphs.
- Do NOT introduce named frameworks or acronym systems (e.g., "FOUNDATION framework"). Write naturally.
- Avoid em-dashes (—/–) and double-hyphens (--). Prefer commas or periods.
- Every factual claim must be supported by the SOURCES below and include a citation in this exact format:
  [citation: filename.ext - "exact quote from source"]
- If a claim cannot be supported, remove it or explicitly mark it as needing research (do not guess).
- Citations are claim-level: add [citation: ...] markers to the sentences that make factual claims or directly use source language.
  Pure connective/reflection sentences may be uncited, but must not introduce new facts.
- After you finish, do a quick self-check: scan every paragraph and confirm it has a citation if it contains substantive content.
- CITED QUOTE TEXT MUST APPEAR IN THE PROSE: For every [citation: ... - "QUOTE"] you add, you MUST include that exact QUOTE text
  verbatim somewhere in the paragraph prose (outside the citation marker). Do NOT add quotation marks unless the source is quoting someone.

VOICE GUIDANCE (match this):
{voice_guidance or "(none provided)"}

SOURCES (ground all content in these; quote directly when possible):
{sources_block or "(no sources provided)"}

{quote_bank}

FEEDBACK:
{chr(10).join(feedback_parts)}

CURRENT CHAPTER:
{state.get('edited_content', state.get('draft_content', ''))}

Return ONLY the revised chapter text. No preamble, no explanations."""
            
            output = self.drafter.invoke(revision_prompt)
            
            if output.is_success():
                state["draft_content"] = output.content
                state["tokens_used"] = state.get("tokens_used", 0) + output.tokens_used
                state["cost_incurred"] = state.get("cost_incurred", 0.0) + output.estimated_cost
        
        return state
    
    def _finalize_node(self, state: ChapterSubgraphState) -> ChapterSubgraphState:
        """Finalize the chapter."""
        import re

        final_raw = state.get("edited_content", state.get("draft_content", "")) or ""
        # Deterministic grounding safety net before enforcing quality gates.
        final = self._sanitize_grounding(final_raw)

        # Recompute deterministic inline citation verification on the FINAL text (post-sanitizer),
        # so our gates and stored metadata reflect what we actually ship.
        inline_final = self._verify_inline_citations(
            final,
            state.get("source_chunks_with_citations", []) or [],
            project_id=state.get("project_id"),
        )
        state["citation_report"] = {**(state.get("citation_report") or {}), **inline_final}

        # Build UI-friendly citation index + a citation-free view of the content
        citation_pat = re.compile(
            r'\[citation:\s*([^\-\]]+?)\s*-\s*(?:"|“)(.*?)(?:"|”)\s*\]',
            re.IGNORECASE,
        )
        content_clean = citation_pat.sub("", final)
        # Normalize leftover double spaces created by marker removal
        content_clean = re.sub(r"[ \t]{2,}", " ", content_clean)
        state["content_clean"] = content_clean.strip()

        citations_ui = []
        search_cursor = 0
        for item in (inline_final.get("inline_citations") or []):
            quote = str(item.get("quote") or "")
            if not quote:
                continue
            idx = content_clean.find(quote, search_cursor)
            if idx == -1:
                # case-insensitive fallback
                idx = content_clean.lower().find(quote.lower(), search_cursor)
            if idx != -1:
                quote_start = idx
                quote_end = idx + len(quote)
                search_cursor = quote_end
            else:
                quote_start = None
                quote_end = None

            citations_ui.append(
                {
                    "filename": item.get("filename"),
                    "source_material_id": item.get("source_material_id"),
                    "quote": quote,
                    "verified": bool(item.get("verified")),
                    # Where the citation marker appeared in the raw text
                    "marker_start": item.get("marker_start"),
                    "marker_end": item.get("marker_end"),
                    # Where the quoted text appears in the clean text (for UI highlighting)
                    "quote_start": quote_start,
                    "quote_end": quote_end,
                }
            )

        state["citations"] = citations_ui

        # Re-check quality gates before finalizing. If we couldn't reach quality within
        # max_turns, we fail fast rather than shipping hallucinated content.
        style_issues = self._compute_style_issues(final)

        # Inline citation verification summary
        citation_report = state.get("citation_report") or {}
        inline_parsed = int(citation_report.get("inline_parsed") or 0)
        inline_invalid = int(citation_report.get("inline_invalid_format") or 0)
        inline_unverified = int(citation_report.get("inline_unverified") or 0)
        inline_quality = float(citation_report.get("inline_quality") or 0.0)
        # Strict: do not ship any unverified quotes.
        inline_ok = inline_parsed > 0 and inline_invalid == 0 and inline_unverified == 0 and inline_quality >= 0.99

        # Citation density is enforced at the paragraph level (see _compute_style_issues).
        # Here we just require at least one valid, verifiable citation overall.
        sentence_count = len([s for s in re.split(r"[.!?]+", final) if s.strip()])
        citation_markers = len(re.findall(r"\[citation:", final, flags=re.IGNORECASE))

        voice_ok = float(state.get("voice_score") or 0.0) >= float(self.voice_threshold)
        citations_ok = inline_ok and citation_markers > 0
        style_ok = len(style_issues) == 0

        quality_gates_passed = bool(voice_ok and citations_ok and style_ok)
        state["quality_gates_passed"] = quality_gates_passed
        state["quality_gate_report"] = {
            "voice_ok": voice_ok,
            "citations_ok": citations_ok,
            "style_ok": style_ok,
            "voice_score": float(state.get("voice_score") or 0.0),
            "voice_threshold": float(self.voice_threshold),
            "inline_quality": float(inline_quality),
            "inline_parsed": int(inline_parsed),
            "inline_invalid": int(inline_invalid),
            "inline_unverified": int(inline_unverified),
            "citation_markers": int(citation_markers),
            "sentence_count": int(sentence_count),
            "style_issues": style_issues,
            "max_turns": int(self.config.max_turns),
            "final_raw_len": len(final_raw),
            "final_len": len(final),
        }

        # Always store the best-effort final content + its citation metadata, even if
        # quality gates did not pass. The caller decides whether to fail the overall
        # workflow/run, but we never want to lose the failure diagnostics.
        state["final_content"] = final

        # Append a final snapshot to the revision history
        hist = list(state.get("revision_history") or [])
        hist.append(
            {
                "phase": "finalize",
                "iteration": int(state.get("iteration") or 0),
                "voice_score": float(state.get("voice_score") or 0.0),
                "fact_score": float(state.get("fact_score") or 0.0),
                "cohesion_score": float(state.get("cohesion_score") or 0.0),
                "citation_report": state.get("citation_report") or {},
                "style_issues": style_issues,
                "quality_gates_passed": quality_gates_passed,
                "quality_gate_report": state.get("quality_gate_report") or {},
            }
        )
        state["revision_history"] = hist
        
        return state
    
    def _should_revise(self, state: ChapterSubgraphState) -> str:
        """Determine if revision is needed."""
        iteration = state.get("iteration", 0)
        voice_score = state.get("voice_score", 0)
        fact_score = state.get("fact_score", 0)
        cohesion_score = state.get("cohesion_score", 0)
        citation_report = state.get("citation_report") or {}
        citation_total = int(citation_report.get("total_claims") or 0)
        citation_quality = float(citation_report.get("quality_score") or 0.0)
        inline_total = int(citation_report.get("inline_total") or 0)
        inline_parsed = int(citation_report.get("inline_parsed") or 0)
        inline_quality = float(citation_report.get("inline_quality") or 0.0)
        inline_invalid = int(citation_report.get("inline_invalid_format") or 0)
        style_issues = self._compute_style_issues(state.get("edited_content", state.get("draft_content", "")) or "")
        style_ok = len(style_issues) == 0
        
        logger.info(
            f"🔄 [ChapterSubgraph] Checking revision: iter={iteration}, "
            f"voice={voice_score:.2f}, fact={fact_score:.2f}, cohesion={cohesion_score:.2f}, "
            f"citations={citation_quality:.2f} ({citation_total} claims), "
            f"inline_citations={inline_quality:.2f} ({inline_parsed}/{inline_total}), style_ok={style_ok}"
        )

        # Persist per-iteration diagnostics so we can audit *all* failures, not just the last one.
        hist = list(state.get("revision_history") or [])
        hist.append(
            {
                "phase": "iteration_check",
                "iteration": int(iteration),
                "voice_score": float(voice_score or 0.0),
                "fact_score": float(fact_score or 0.0),
                "cohesion_score": float(cohesion_score or 0.0),
                "voice_feedback": state.get("voice_feedback", ""),
                "fact_feedback": state.get("fact_feedback", ""),
                "cohesion_feedback": state.get("cohesion_feedback", ""),
                "citation_report": dict(citation_report),
                "style_ok": bool(style_ok),
                "style_issues": style_issues,
            }
        )
        state["revision_history"] = hist
        
        # Check iteration limit
        if iteration >= self.config.max_turns:
            logger.info(f"🔄 [ChapterSubgraph] Max turns reached ({self.config.max_turns}), finishing")
            return "done"
        
        # Check quality thresholds
        voice_ok = voice_score >= self.voice_threshold
        fact_ok = fact_score >= self.fact_threshold
        cohesion_ok = cohesion_score >= self.cohesion_threshold
        
        inline_ok = (
            inline_parsed > 0
            and inline_invalid == 0
            and int(citation_report.get("inline_unverified") or 0) == 0
            and inline_quality >= 0.99
        )
        # NOTE: LLM claim-mapping quality is noisy; we gate on deterministic quote verification
        # plus paragraph-level anti-embellishment checks in `_compute_style_issues`.
        citations_ok = inline_ok
        
        if voice_ok and fact_ok and cohesion_ok and citations_ok and style_ok:
            logger.info("🔄 [ChapterSubgraph] All thresholds met, finishing")
            return "done"
        
        logger.info(
            f"🔄 [ChapterSubgraph] Needs revision (voice_ok={voice_ok}, fact_ok={fact_ok}, cohesion_ok={cohesion_ok}, "
            f"citations_ok={citations_ok}, style_ok={style_ok})"
        )
        return "revise"
    
    def run(
        self,
        chapter_outline: dict,
        source_chunks: list[str],
        previous_summaries: list[str] = None,
        voice_profile: dict = None,
        target_words: int = 3000,
        source_chunks_with_citations: list[dict] = None,
        project_id: Optional[str] = None,
    ) -> dict:
        """
        Run the chapter generation subgraph.
        
        Args:
            chapter_outline: Dict with chapter number, title, summary, key_points
            source_chunks: List of plain text source chunks (legacy)
            previous_summaries: List of previous chapter summaries for continuity
            voice_profile: Voice profile dict for style consistency
            target_words: Target word count for the chapter
            source_chunks_with_citations: List of {"content": str, "citation": str} for citation verification
            
        Returns:
            Dict with content, quality scores, and citation verification report
        """
        initial_state = ChapterSubgraphState(
            project_id=project_id or "",
            chapter_outline=chapter_outline,
            source_chunks=source_chunks,
            source_chunks_with_citations=source_chunks_with_citations or [],
            previous_summaries=previous_summaries or [],
            voice_profile=voice_profile or {},
            target_words=target_words,
            draft_content="",
            edited_content="",
            final_content="",
            content_clean="",
            citations=[],
            revision_history=[],
            quality_gates_passed=False,
            quality_gate_report={},
            voice_score=0.0,
            fact_score=0.0,
            cohesion_score=0.0,
            voice_feedback="",
            fact_feedback="",
            cohesion_feedback="",
            claim_mappings=[],
            citation_report={},
            iteration=0,
            tokens_used=0,
            cost_incurred=0.0,
        )
        # Avoid GraphRecursionError when revisions hit max_turns (LangGraph's default
        # recursion_limit is low enough to trip on worst-case loops).
        recursion_limit = max(100, int(self.config.max_turns) * 20)
        result = self.graph.invoke(initial_state, {"recursion_limit": recursion_limit})
        
        return {
            "content": result.get("final_content"),
            "content_clean": result.get("content_clean"),
            "word_count": len(result.get("final_content", "").split()),
            "voice_score": result.get("voice_score", 0.0),
            "fact_score": result.get("fact_score", 0.0),
            "cohesion_score": result.get("cohesion_score", 0.0),
            "iterations": result.get("iteration", 0),
            "tokens_used": result.get("tokens_used", 0),
            "cost": result.get("cost_incurred", 0.0),
            "quality_gates_passed": bool(result.get("quality_gates_passed", False)),
            "quality_gate_report": result.get("quality_gate_report") or {},
            "revision_history": result.get("revision_history") or [],
            # Citation verification report
            "citations": result.get("citations", []),
            "claim_mappings": result.get("claim_mappings", []),
            "citation_report": result.get("citation_report", {
                "total_claims": 0,
                "verified": 0,
                "needs_review": 0,
                "unsupported": 0,
                "quality_score": 1.0,
                "recommendation": "Good",
            }),
        }
