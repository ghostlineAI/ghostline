"""
Outline Planner Agent for creating book outlines.

This agent analyzes source materials and creates a structured book outline
with chapters, key points, and estimated word counts.
"""

import json
import re
from typing import Optional

from pydantic import BaseModel, Field

from agents.base.agent import (
    AgentConfig,
    AgentOutput,
    AgentRole,
    BaseAgent,
    ConversationAgent,
    LLMProvider,
)


class OutlineState(BaseModel):
    """State for outline generation."""
    project_title: str
    project_description: Optional[str] = None
    source_summaries: list[str] = Field(default_factory=list)
    target_chapters: int = 10
    target_words: int = 50000
    voice_guidance: Optional[str] = None
    
    # Output
    outline: Optional[dict] = None
    iteration: int = 0
    feedback: list[str] = Field(default_factory=list)


class OutlinePlannerAgent(BaseAgent[OutlineState]):
    """
    Agent that creates book outlines from source materials.
    
    Specializes in:
    - Analyzing source material to identify key themes
    - Structuring content into logical chapters
    - Creating engaging chapter summaries
    - Balancing content across chapters
    """
    
    def _default_config(self) -> AgentConfig:
        return AgentConfig(
            role=AgentRole.PLANNER,
            model="claude-sonnet-4-20250514",
            provider=LLMProvider.ANTHROPIC,
            temperature=0.7,
            max_tokens=4096,
        )
    
    def get_system_prompt(self) -> str:
        return """You are an expert book architect and outline specialist. Your task is to create 
compelling, well-structured book outlines that:

1. Capture the essential themes and ideas from source materials
2. Organize content into a logical, engaging narrative flow
3. Balance depth and accessibility for the target audience
4. Create chapter titles that intrigue and inform

CRITICAL GROUNDING RULES:
- You MUST base the outline ONLY on the provided source material summaries.
- Do NOT introduce new named techniques, protocols, acronyms, or frameworks that are not explicitly present in the source materials.
  Bad (invented): "BRIDGE protocol", "Glance and Ground technique", "80% rule", "XYZ framework".
  Good: Use the exact phrasing from the notes, or describe an idea plainly without naming it.
- Do NOT add external therapy modalities (CBT/DBT/ACT/etc.) unless those words appear in the sources.
- Respect the requested chapter count exactly: output EXACTLY the requested number of chapters.

When creating outlines, always output valid JSON with this structure:
{
    "title": "Book Title",
    "premise": "One paragraph describing the book's central premise",
    "chapters": [
        {
            "number": 1,
            "title": "Chapter Title",
            "summary": "2-3 sentence summary",
            "key_points": ["point 1", "point 2", "point 3"],
            "estimated_words": 3000,
            "sources_referenced": ["source1.pdf", "source2.docx"]
        }
    ],
    "themes": ["theme 1", "theme 2"],
    "target_audience": "Description of ideal reader"
}

Make each chapter compelling and distinct, but do not invent content beyond the sources."""
    
    def process(self, state: OutlineState) -> AgentOutput:
        """Generate or refine a book outline."""
        if state.outline and state.feedback:
            # Refine existing outline based on feedback
            return self._refine_outline(state)
        else:
            # Create initial outline
            return self._create_outline(state)
    
    def _create_outline(self, state: OutlineState) -> AgentOutput:
        """Create the initial outline."""
        source_context = "\n\n---\n\n".join(state.source_summaries[:10])
        
        prompt = f"""Create a detailed book outline for:

Title: {state.project_title}
Description: {state.project_description or "Not provided"}

Target: {state.target_chapters} chapters, approximately {state.target_words} total words

{f"Voice/Style Guidance: {state.voice_guidance}" if state.voice_guidance else ""}

SOURCE MATERIAL SUMMARIES:
{source_context}

Hard requirements:
- Output EXACTLY {state.target_chapters} chapters.
- Do NOT invent named techniques/protocols/frameworks/acronyms.
- Do NOT add external information not in the summaries.

Create a compelling, well-structured outline grounded in the summaries. Output only valid JSON."""

        output = self.invoke(prompt)
        
        if output.is_success():
            # Parse the outline
            outline = self._parse_outline(output.content)
            output.structured_data = outline
        
        return output
    
    def _refine_outline(self, state: OutlineState) -> AgentOutput:
        """Refine an existing outline based on feedback."""
        feedback_text = "\n".join(f"- {f}" for f in state.feedback)
        
        prompt = f"""Refine this book outline based on feedback:

CURRENT OUTLINE:
{json.dumps(state.outline, indent=2)}

FEEDBACK:
{feedback_text}

Apply the feedback while maintaining the overall structure and quality.
Output the complete revised outline as valid JSON."""

        output = self.invoke(prompt)
        
        if output.is_success():
            outline = self._parse_outline(output.content)
            output.structured_data = outline
        
        return output
    
    def _parse_outline(self, content: str) -> dict:
        """Parse outline JSON from response."""
        content = content.strip()
        
        # Remove markdown code blocks
        if content.startswith("```"):
            content = re.sub(r'^```\w*\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {}


class OutlineCriticAgent(ConversationAgent):
    """
    Agent that critiques outlines for quality and completeness.
    
    Used in the bounded subgraph for outline refinement:
    Planner ↔ Critic ↔ Planner (max 3 iterations)
    """
    
    def _default_config(self) -> AgentConfig:
        return AgentConfig(
            role=AgentRole.CRITIC,
            model="claude-sonnet-4-20250514",
            provider=LLMProvider.ANTHROPIC,
            temperature=0.5,
            max_tokens=2048,
        )
    
    def get_system_prompt(self) -> str:
        return """You are a critical editor specializing in book structure and narrative flow.
Your role is to review book outlines and provide constructive feedback.

When critiquing, focus on:
1. Logical flow between chapters
2. Balance of content across chapters
3. Engagement and reader interest
4. Clarity of chapter summaries
5. Completeness of coverage

Provide specific, actionable feedback. If the outline is excellent, say "APPROVED" 
as your first word. Otherwise, list 3-5 specific improvements needed.

Be constructive but critical. The goal is a better book."""
    
    def process(self, state: OutlineState) -> AgentOutput:
        """Critique the current outline."""
        if not state.outline:
            return AgentOutput(
                content="No outline to critique.",
                error="Missing outline",
            )
        
        prompt = f"""Review this book outline and provide feedback:

{json.dumps(state.outline, indent=2)}

Target: {state.target_chapters} chapters, {state.target_words} words

Is this outline ready for chapter drafting, or does it need improvement?
If improvements needed, list specific changes. If ready, start with "APPROVED"."""

        return self.invoke(prompt)
    
    def is_approved(self, output: AgentOutput) -> bool:
        """Check if the critic approved the outline."""
        return output.content.strip().upper().startswith("APPROVED")

