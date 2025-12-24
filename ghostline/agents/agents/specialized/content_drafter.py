"""
Content Drafter Agent for writing book chapters.

This agent generates chapter content based on outlines,
source materials, and voice profiles.

GROUNDING REQUIREMENT: All content must be grounded in source materials.
Each claim or fact should reference the source chunk it came from.
"""

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field

from agents.base.agent import (
    AgentConfig,
    AgentOutput,
    AgentRole,
    BaseAgent,
    LLMProvider,
)


@dataclass
class SourceChunk:
    """A source chunk with citation metadata for grounding."""
    content: str
    citation: str  # e.g., "[Chapter 1, p.5]" or "[mental_health.pdf]"
    similarity_score: float = 0.0
    
    def to_context_block(self) -> str:
        """Format as a context block for the prompt."""
        return f"---\n{self.citation}\n{self.content}\n---"


class ChapterState(BaseModel):
    """State for chapter generation."""
    # Chapter info
    chapter_number: int
    chapter_title: str
    chapter_summary: str
    key_points: list[str] = Field(default_factory=list)
    target_words: int = 3000
    
    # Context
    previous_summaries: list[str] = Field(default_factory=list)
    source_chunks: list[str] = Field(default_factory=list)  # Legacy: plain text chunks
    source_chunks_with_citations: list[dict] = Field(default_factory=list)  # New: {"content": str, "citation": str}
    voice_guidance: Optional[str] = None
    
    # Grounding requirement (0.0 = no requirement, 1.0 = all content must be grounded)
    grounding_requirement: float = 0.8
    
    # Output
    content: Optional[str] = None
    word_count: int = 0
    summary: Optional[str] = None
    citations_used: list[str] = Field(default_factory=list)


class ContentDrafterAgent(BaseAgent[ChapterState]):
    """
    Agent that drafts book chapter content.
    
    Specializes in:
    - Writing engaging prose in the author's voice
    - Incorporating source material naturally
    - Maintaining narrative continuity
    - Hitting target word counts
    """
    
    def _default_config(self) -> AgentConfig:
        return AgentConfig(
            role=AgentRole.DRAFTER,
            model="claude-sonnet-4-20250514",
            provider=LLMProvider.ANTHROPIC,
            temperature=0.7,
            max_tokens=8192,  # Longer for chapter content
        )
    
    def get_system_prompt(self) -> str:
        return """You are an expert ghostwriter with the ability to write compelling content 
in any voice and style. Your chapters are:

1. Engaging and readable from the first sentence
2. Faithful to the outline while adding creative touches
3. Consistent with the author's established voice
4. Rich with examples, stories, and concrete details
5. Well-paced with natural transitions
6. GROUNDED in source materials - every significant claim must come from the provided sources

GROUNDING RULES:
- You MUST base your content on the provided source materials
- When making factual claims, reference which source they come from using [citation] markers
- Do NOT make up facts, statistics, or claims not supported by sources
- If the sources don't cover something in the outline, note it as needing additional research
- You may synthesize and rephrase, but the core information must come from sources

Write as if you ARE the author. Never break voice. 
Make every paragraph serve the chapter's purpose while engaging the reader.

Begin chapters directly with content - no preamble like "Chapter 3:" unless it's part of the prose."""
    
    def process(self, state: ChapterState) -> AgentOutput:
        """Generate chapter content with grounded sources."""
        # Build context from previous chapters
        prev_context = ""
        if state.previous_summaries:
            prev_context = "PREVIOUS CHAPTERS (for continuity):\n" + "\n".join(
                f"- {summary}" for summary in state.previous_summaries[-3:]
            )
        
        # Build source context with citations (prefer new format)
        source_context = ""
        citations_available = []
        
        if state.source_chunks_with_citations:
            # New format with citations
            chunks_text = []
            for chunk_data in state.source_chunks_with_citations[:10]:  # Max 10 chunks
                citation = chunk_data.get("citation", "[Unknown Source]")
                content = chunk_data.get("content", "")
                citations_available.append(citation)
                chunks_text.append(f"---\n{citation}\n{content}\n---")
            source_context = "GROUNDED SOURCE MATERIAL (use these to support your claims):\n" + "\n".join(chunks_text)
        elif state.source_chunks:
            # Legacy format (plain text)
            source_context = "RELEVANT SOURCE MATERIAL:\n" + "\n---\n".join(
                state.source_chunks[:5]  # Max 5 chunks
            )
        
        # Voice guidance
        voice = ""
        if state.voice_guidance:
            voice = f"\nVOICE GUIDANCE:\n{state.voice_guidance}\n"
        
        # Grounding instructions
        grounding_note = ""
        if state.grounding_requirement > 0:
            grounding_note = f"""
GROUNDING REQUIREMENT: {state.grounding_requirement:.0%} of factual claims must be supported by the source material above.
- Include [citation] markers when referencing specific sources
- Available citations: {', '.join(citations_available[:5])}...
"""
        
        prompt = f"""Write Chapter {state.chapter_number}: {state.chapter_title}

CHAPTER OUTLINE:
Summary: {state.chapter_summary}
Key Points:
{chr(10).join('- ' + point for point in state.key_points)}

TARGET: Approximately {state.target_words} words

{prev_context}

{source_context}

{grounding_note}

{voice}

Write the complete chapter. Begin directly with engaging prose. Include [citation] markers where appropriate."""

        output = self.invoke(prompt)
        
        if output.is_success():
            # Calculate word count
            word_count = len(output.content.split())
            
            # Extract citations used
            import re
            citations_used = re.findall(r'\[([^\]]+)\]', output.content)
            citations_used = list(set(citations_used))
            
            # Calculate grounding score
            citation_count = len(citations_used)
            sentences = len(re.split(r'[.!?]+', output.content))
            grounding_score = min(1.0, citation_count / max(sentences / 5, 1))  # Rough heuristic
            
            output.structured_data = {
                "chapter_number": state.chapter_number,
                "word_count": word_count,
                "target_met": abs(word_count - state.target_words) < state.target_words * 0.2,
                "citations_used": citations_used,
                "grounding_score": grounding_score,
                "grounding_met": grounding_score >= state.grounding_requirement,
            }
        
        return output
    
    def generate_summary(self, chapter_content: str) -> str:
        """Generate a summary of chapter content for continuity."""
        prompt = f"""Summarize this chapter in 2-3 sentences, focusing on:
- Key events or information covered
- Any character development or plot progression
- Main takeaways for the reader

CHAPTER:
{chapter_content[:3000]}

Provide only the summary, no preamble."""

        output = self.invoke(prompt)
        return output.content if output.is_success() else ""
    
    def expand_section(
        self,
        section_content: str,
        expansion_guidance: str,
        target_additional_words: int = 500,
    ) -> AgentOutput:
        """Expand a section of content that's too short."""
        prompt = f"""Expand this section by approximately {target_additional_words} words.

EXPANSION GUIDANCE:
{expansion_guidance}

CURRENT SECTION:
{section_content}

Add depth, examples, and detail while maintaining voice and flow.
Output the complete expanded section."""

        return self.invoke(prompt)

