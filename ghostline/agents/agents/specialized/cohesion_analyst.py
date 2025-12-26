"""
Cohesion Analyst Agent for ensuring narrative flow and consistency.

This agent analyzes chapters for coherence, flow, and overall
structural integrity of the book.
"""

import json
import re
from typing import Optional

from pydantic import BaseModel, Field, ValidationError

from agents.base.agent import (
    AgentConfig,
    AgentOutput,
    AgentRole,
    BaseAgent,
    LLMProvider,
)
from agents.specialized.schemas import CohesionResultModel


class CohesionState(BaseModel):
    """State for cohesion analysis."""
    content: str
    chapter_number: int = 1
    book_outline: Optional[dict] = None
    previous_summaries: list[str] = Field(default_factory=list)
    following_outline: Optional[dict] = None
    
    # Results
    cohesion_score: Optional[float] = None
    issues: list[dict] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class CohesionAnalystAgent(BaseAgent[CohesionState]):
    """
    Agent that analyzes narrative cohesion and flow.
    
    Specializes in:
    - Checking transitions between sections and chapters
    - Ensuring logical flow of ideas
    - Verifying alignment with book outline
    - Identifying pacing issues
    """
    
    def _default_config(self) -> AgentConfig:
        return AgentConfig(
            role=AgentRole.COHESION,
            model="claude-sonnet-4-20250514",
            provider=LLMProvider.ANTHROPIC,
            temperature=0.4,
            max_tokens=4096,
        )
    
    def get_system_prompt(self) -> str:
        return """You are an expert developmental editor specializing in narrative structure and flow.
Your job is to analyze content for:

1. Logical progression of ideas
2. Smooth transitions between paragraphs and sections
3. Consistent pacing throughout
4. Alignment with the overall book structure
5. Reader engagement and momentum

For each chapter, consider:
- Does it fulfill its role in the larger narrative?
- Do sections flow naturally into each other?
- Is the pacing appropriate for the content?
- Does it set up the next chapter appropriately?
- Are there any jarring transitions or logical gaps?

Provide specific, actionable feedback with examples from the text."""
    
    def process(self, state: CohesionState) -> AgentOutput:
        """Analyze content for cohesion and flow."""
        # Build context
        outline_context = ""
        if state.book_outline:
            outline_context = f"BOOK OUTLINE:\n{json.dumps(state.book_outline, indent=2)}"
        
        prev_context = ""
        if state.previous_summaries:
            prev_context = "PREVIOUS CHAPTER SUMMARIES:\n" + "\n".join(
                f"- Chapter {i+1}: {s}" 
                for i, s in enumerate(state.previous_summaries)
            )
        
        following_context = ""
        if state.following_outline:
            following_context = f"NEXT CHAPTER OUTLINE:\n{json.dumps(state.following_outline, indent=2)}"
        
        prompt = f"""Analyze this chapter (Chapter {state.chapter_number}) for cohesion and narrative flow.

{outline_context}

{prev_context}

{following_context}

CHAPTER TO ANALYZE:
{state.content}

Provide analysis as JSON:
{{
    "cohesion_score": 0.0-1.0,
    "structure_analysis": {{
        "opening_effectiveness": 0.0-1.0,
        "body_flow": 0.0-1.0,
        "closing_effectiveness": 0.0-1.0,
        "outline_alignment": 0.0-1.0
    }},
    "issues": [
        {{
            "type": "transition|pacing|structure|alignment|gap",
            "location": "describe where in the chapter",
            "description": "what the issue is",
            "severity": "low|medium|high",
            "suggestion": "how to fix"
        }}
    ],
    "strengths": ["what works well"],
    "summary": "Overall assessment"
}}"""

        output = self.invoke(prompt)
        
        if output.is_success():
            results = self._parse_json(output.content)
            output.structured_data = results
            output.confidence = results.get("cohesion_score", 0.5)
            
            # Check for major issues
            issues = results.get("issues", [])
            high_severity = [i for i in issues if i.get("severity") == "high"]
            if high_severity:
                output.reasoning = f"Found {len(high_severity)} high-severity cohesion issues"
        
        return output
    
    def analyze_transitions(self, content: str) -> AgentOutput:
        """Specifically analyze paragraph and section transitions."""
        prompt = f"""Analyze all transitions in this content - between paragraphs and sections.

CONTENT:
{content}

For each transition point:
1. Is it smooth or jarring?
2. Does it maintain logical flow?
3. Does it maintain reader engagement?

Rate each transition and provide overall score:
{{
    "transitions_analyzed": 10,
    "smooth_transitions": 7,
    "needs_work": [
        {{
            "location": "after paragraph about X",
            "current_transition": "what happens now",
            "issue": "why it's jarring",
            "suggestion": "how to improve"
        }}
    ],
    "overall_score": 0.7
}}"""

        output = self.invoke(prompt)
        
        if output.is_success():
            output.structured_data = self._parse_json(output.content)
        
        return output
    
    def check_outline_alignment(
        self,
        content: str,
        chapter_outline: dict,
    ) -> AgentOutput:
        """Check if content aligns with its outline."""
        prompt = f"""Compare this chapter content with its intended outline.

INTENDED OUTLINE:
{json.dumps(chapter_outline, indent=2)}

ACTUAL CONTENT:
{content}

Analyze alignment:
{{
    "alignment_score": 0.0-1.0,
    "summary_match": true/false,
    "key_points_covered": [
        {{"point": "key point from outline", "covered": true/false, "notes": "any comments"}}
    ],
    "unexpected_additions": ["content not in outline"],
    "missing_elements": ["outline elements not in content"],
    "recommendation": "overall assessment"
}}"""

        output = self.invoke(prompt)
        
        if output.is_success():
            output.structured_data = self._parse_json(output.content)
        
        return output
    
    def suggest_improvements(
        self,
        content: str,
        issues: list[dict],
    ) -> AgentOutput:
        """Provide specific improvement suggestions."""
        issues_text = "\n".join(
            f"- {i.get('type', 'issue')}: {i.get('description', '')}" 
            for i in issues
        )
        
        prompt = f"""Based on these identified issues, provide specific rewrites or improvements.

ISSUES FOUND:
{issues_text}

CONTENT:
{content}

For each issue, provide a specific fix:
{{
    "improvements": [
        {{
            "issue": "which issue this addresses",
            "original": "original problematic text",
            "suggested": "improved version",
            "explanation": "why this is better"
        }}
    ]
}}"""

        output = self.invoke(prompt)
        
        if output.is_success():
            output.structured_data = self._parse_json(output.content)
        
        return output
    
    def _parse_json(self, content: str) -> dict:
        """Parse JSON from response."""
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r'^```\w*\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
        
        try:
            raw = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                try:
                    raw = json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raw = {"cohesion_score": 0.5, "issues": [], "summary": "Could not parse results"}

        # Validate / normalize against schema (best-effort)
        try:
            model = CohesionResultModel.model_validate(raw)
            return model.model_dump()
        except ValidationError:
            return raw if isinstance(raw, dict) else {"cohesion_score": 0.5, "issues": [], "summary": "Invalid results"}

